"""The run records: the run identifier, the summary of a run, the check of a record and of
the registry, and the commands `run check`, `run report` and `run compare`
(specs/002-evaluation-harness: data-model.md, "Run identifier", "Run record", "Check of a run
record" and "Pairwise comparison"; contracts/harness.md, "`wixqa_rag.runs`"; contracts/cli.md,
"`run report`", "`run check`" and "`run compare`").

Writing a run record is the task of spec 3. This module fixes the summary that spec 3 writes
(`summary_document`) and reads and checks what was written. Every number comes from
`wixqa_rag.metrics`, the one computation (FR-017).

The module reads run records and question-set records and nothing else: no data directory,
no store, no provider and no setting (FR-031). No function changes a file.
"""

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from wixqa_rag import cli, metrics, questionsets, settings

RUN_FILE = "run.json"
RESULTS_FILE = "results.jsonl"
SUMMARY_FILE = "summary.json"

# data-model.md, "Run identifier": the start time in UTC, a hyphen and a name.
_NAME = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_LONGEST_NAME = 40
_TIME_PART = 16
_RUN_ID = re.compile(rf"[0-9]{{8}}T[0-9]{{6}}Z-({_NAME})")
_STARTED_AT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
_COMMIT = re.compile(r"[0-9a-f]{40}")

# The fields of the three files (data-model.md, "Run record").
_RUN_FIELDS = ("run_id", "started_at", "commit", "uncommitted_changes", "config")
_CONFIG_FIELDS = (
    "dataset",
    "question_set",
    "index",
    "models",
    "prompts",
    "retrieval",
    "reranking",
    "context",
    "limits",
    "seeds",
    "concurrency",
    "prices",
    "experiment",
)
_FREE_OBJECTS = ("models", "prompts", "retrieval", "reranking", "context", "seeds")
_ENTRY_FIELDS = (
    "status",
    "retrieved_list",
    "generation_list",
    "context",
    "answer",
    "answer_sha256",
    "tokens",
    "cost_usd",
    "latency_seconds",
)
_SUMMARY_FIELDS = (
    "run_id",
    "question_set",
    "questions",
    "audit",
    "breakdowns",
    "retrieval_misses",
    "questions_without_gold_articles",
)
_EXPERIMENT_FIELDS = ("baseline", "parameter", "baseline_value", "value")
_AUDIT_FIELDS = (
    "index",
    "dataset",
    "question_set",
    "articles_in_corpus",
    "articles_in_index",
    "missing_from_index",
    "not_in_corpus",
    "unknown_references",
    "questions_without_article_ids",
    "outcome",
    "audited_at",
)

# How a breakdown and a list are written in a line (contracts/cli.md).
_BREAKDOWN = {
    "all": "all questions",
    "single_article": "single-article",
    "multi_article": "multi-article",
}
_LIST = {"generation_list": "generation list", "retrieved_list": "retrieved list"}
_LIST_NUMBERS = ("questions", "mean_share_found", "all_found", "share_all_found")
# The numbers of a breakdown that are counts: whole numbers.
_COUNTS = ("questions", "all_found")


# --- The run identifier -------------------------------------------------------------------------


def is_valid_run_id(text: object) -> bool:
    """Whether a text has the form of a run identifier."""
    if not isinstance(text, str):
        return False
    found = _RUN_ID.fullmatch(text)
    return found is not None and len(found.group(1)) <= _LONGEST_NAME


def run_id(started_at: datetime, name: str) -> str:
    """The run identifier for a start time with a time zone and a name: the time in UTC to
    the second, a hyphen and the name. Raises `ValueError` for a name of another form or a
    time without a time zone."""
    if started_at.tzinfo is None or started_at.utcoffset() is None:
        raise ValueError("the start time of a run has no time zone")
    identifier = f"{started_at.astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')}-{name}"
    if not isinstance(name, str) or not is_valid_run_id(identifier):
        raise ValueError(f"{name!r} does not have the form of the name of a run")
    return identifier


def _runs_directory(runs_dir: Path | None) -> Path:
    return settings.RUNS_DIR if runs_dir is None else Path(runs_dir)


def _sets_directory(sets_dir: Path | None) -> Path:
    return settings.SETS_DIR if sets_dir is None else Path(sets_dir)


def run_ids(runs_dir: Path | None = None) -> list[str]:
    """The names of the directories of a registry, sorted. A file directly in the runs
    directory is not a run."""
    return sorted(entry.name for entry in _runs_directory(runs_dir).iterdir() if entry.is_dir())


# --- The summary and the config -----------------------------------------------------------------


def summary_document(
    run_document: dict,
    question_set: questionsets.QuestionSet,
    entries: Sequence[dict],
    audit_document: dict,
) -> dict:
    """The whole document of `summary.json`: `run_id`, `question_set` and `questions` from
    the first two arguments, `audit` as given, and the three keys of `metrics.summarize`.
    Spec 3 writes exactly this document."""
    numbers = metrics.summarize(question_set.pairs(), entries, run_document["config"]["prices"])
    return {
        "run_id": run_document["run_id"],
        "question_set": {
            "version": question_set.version,
            "role": question_set.role,
            "fingerprint": question_set.fingerprint,
        },
        "questions": len(question_set.questions),
        "audit": audit_document,
        **numbers,
    }


def _leaves(config: dict) -> dict[str, object]:
    """The parameters of a config: every leaf under its dotted path. Objects are descended
    into; every other value, a list included, is a leaf. `experiment` is not a parameter."""
    found: dict[str, object] = {}

    def descend(value: object, path: str) -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                descend(inner, f"{path}.{key}" if path else str(key))
        else:
            found[path] = value

    for key, value in config.items():
        if key != "experiment":
            descend(value, str(key))
    return found


def _same(first: object, second: object) -> bool:
    """Whether two JSON values are the same value: `true` is not 1, and `1` is not `1.0`."""
    return json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def config_differences(first_config: dict, second_config: dict) -> list[str]:
    """The parameters in which two configs differ, as a sorted list of dotted paths: a
    parameter differs when its value differs or when only one config has it. `experiment`
    is not compared."""
    first, second = _leaves(first_config), _leaves(second_config)
    return sorted(
        path
        for path in first.keys() | second.keys()
        if path not in first or path not in second or not _same(first[path], second[path])
    )


# --- The check of a run record ------------------------------------------------------------------


class RunNotFound(Exception):
    """The run does not exist in the runs directory. `reason` is the line that a command
    prints for it."""

    def __init__(self, run: str, runs_dir: Path) -> None:
        self.reason = f"run {run} does not exist in {runs_dir.as_posix()}"
        super().__init__(self.reason)
        self.run = run


@dataclass(frozen=True)
class RunExamination:
    """The outcome of the check of one record."""

    run_id: str
    # Every difference, without the `difference: ` in front.
    differences: list[str]
    # The record of the question set, or None when it could not be read.
    question_set: questionsets.QuestionSet | None
    # The `config.question_set.role` of the record, or None when it cannot be read.
    role: str | None
    # Each None when its file could not be read.
    run_document: dict | None
    entries: list[dict] | None
    summary: dict | None


def _show(value: object) -> str:
    """A value as a line states it: a number in its shortest form, `null` for no number."""
    return json.dumps(value, ensure_ascii=False)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_whole(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _not_finite(text: str):
    """`Infinity`, `-Infinity` and `NaN` are no JSON numbers, although `json` reads them."""
    raise ValueError(f"{text} is not a JSON number")


def _finite(text: str) -> float:
    """A number with a fraction or an exponent; one too large for a floating-point number,
    such as `1e999`, is no number of a record."""
    number = float(text)
    if not math.isfinite(number):
        raise ValueError(f"{text} is too large for a number of a record")
    return number


def _parse(text: str) -> object:
    """The JSON value of a text. Every number that it gives is a whole number or a finite
    floating-point number, so no number of a record can be infinite or "not a number".
    Raises `ValueError` for a text that is not such JSON."""
    return json.loads(text, parse_constant=_not_finite, parse_float=_finite)


def _exact_text(number) -> str:
    """An exact number as a line states it."""
    try:
        return str(number)
    except ValueError:
        return "a number too large to write"


def _read_text(file: Path, differences: list[str]) -> str | None:
    """The text of one of the three files, or None with difference 1."""
    if not file.is_file():
        differences.append(f"{file.name} is missing")
        return None
    try:
        return file.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        differences.append(f"{file.name} is not UTF-8")
        return None


def _read_object(file: Path, differences: list[str]) -> dict | None:
    """The document of `run.json` or of `summary.json`, or None with difference 1."""
    text = _read_text(file, differences)
    if text is None:
        return None
    try:
        document = _parse(text)
    except ValueError:
        differences.append(f"{file.name} is not JSON")
        return None
    if not isinstance(document, dict):
        differences.append(f"{file.name} is not a JSON object")
        return None
    return document


def _read_entries(file: Path, differences: list[str]) -> tuple[list[dict], bool]:
    """The entries of `results.jsonl` that can be read, and whether every line could be."""
    text = _read_text(file, differences)
    if text is None:
        return [], False
    entries, whole = [], True
    for number, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            entry = _parse(line)
        except ValueError:
            entry = None
        if isinstance(entry, dict):
            entries.append(entry)
        else:
            differences.append(f"{file.name} line {number} is not a JSON object")
            whole = False
    return entries, whole


def _config_of(document: dict | None) -> dict | None:
    config = None if document is None else document.get("config")
    return config if isinstance(config, dict) else None


def _question_set_of(config: dict | None) -> dict:
    recorded = None if config is None else config.get("question_set")
    return recorded if isinstance(recorded, dict) else {}


def _differences_of_run_json(document: dict, name: str, any_name: bool) -> list[str]:
    """Differences 2 and 3 of `run.json`."""
    found = [
        f"{RUN_FILE} lacks the field {field}" for field in _RUN_FIELDS if field not in document
    ]

    def wrong(path: str, what: str) -> None:
        found.append(f"{RUN_FILE}: {path} is not {what}")

    identifier, started_at = document.get("run_id"), document.get("started_at")
    if "run_id" in document:
        if not is_valid_run_id(identifier):
            wrong(f"run_id {_show(identifier)}", "a run identifier")
        elif identifier != name:
            found.append(f"run_id {identifier} is not the name of the directory {name}")
    if "started_at" in document:
        if not isinstance(started_at, str) or _STARTED_AT.fullmatch(started_at) is None:
            wrong(f"started_at {_show(started_at)}", "a time of the form 2026-11-01T10:00:00Z")
        elif is_valid_run_id(identifier):
            stated = started_at.replace("-", "").replace(":", "")
            if identifier[:_TIME_PART] != stated:
                found.append(f"the time part of run_id {identifier} is not started_at {started_at}")
    commit = document.get("commit")
    if "commit" in document and not (isinstance(commit, str) and _COMMIT.fullmatch(commit)):
        wrong("commit", "a full commit hash of 40 lower-case hexadecimal characters")
    if "uncommitted_changes" in document and not isinstance(document["uncommitted_changes"], bool):
        wrong("uncommitted_changes", "true or false")
    if "config" not in document:
        return found
    config = document["config"]
    if not isinstance(config, dict):
        wrong("config", "an object")
        return found

    found.extend(
        f"{RUN_FILE} lacks the field config.{field}"
        for field in _CONFIG_FIELDS
        if field not in config
    )
    for field, keys in (("dataset", ("name", "revision")), ("question_set", ())):
        if field in config and not isinstance(config[field], dict):
            wrong(f"config.{field}", "an object")
        elif field in config:
            found.extend(
                f"{RUN_FILE} lacks the field config.{field}.{key}"
                for key in keys
                if key not in config[field]
            )
    recorded = config.get("dataset")
    if isinstance(recorded, dict):
        if "name" in recorded and not isinstance(recorded["name"], str):
            wrong("config.dataset.name", "a text")
        if recorded.get("revision") is not None and not isinstance(recorded["revision"], str):
            wrong("config.dataset.revision", "a text or null")
    recorded = config.get("question_set")
    if isinstance(recorded, dict):
        for key in ("version", "role", "fingerprint"):
            if key not in recorded:
                found.append(f"{RUN_FILE} lacks the field config.question_set.{key}")
            elif not isinstance(recorded[key], str):
                wrong(f"config.question_set.{key}", "a text")
        if isinstance(recorded.get("role"), str) and recorded["role"] not in questionsets.ROLES:
            wrong(f"config.question_set.role {recorded['role']}", "golden or held-out")
    if "index" in config and not isinstance(config["index"], str):
        wrong("config.index", "a text")
    for field in _FREE_OBJECTS:
        if field in config and not isinstance(config[field], dict):
            wrong(f"config.{field}", "an object")
    models = config.get("models")
    if isinstance(models, dict) and not all(isinstance(model, str) for model in models.values()):
        wrong("config.models", "an object whose values are texts")
    limits = config.get("limits")
    if "limits" in config and not isinstance(limits, dict):
        wrong("config.limits", "an object")
    elif isinstance(limits, dict):
        for key in ("timeout_seconds", "max_calls"):
            if key not in limits:
                found.append(f"{RUN_FILE} lacks the field config.limits.{key}")
        if "timeout_seconds" in limits and not (
            _is_number(limits["timeout_seconds"]) and limits["timeout_seconds"] > 0
        ):
            wrong("config.limits.timeout_seconds", "a number above 0")
        if "max_calls" in limits and not (
            _is_whole(limits["max_calls"]) and limits["max_calls"] >= 1
        ):
            wrong("config.limits.max_calls", "a whole number of at least 1")
    if "concurrency" in config and not (
        _is_whole(config["concurrency"]) and config["concurrency"] >= 1
    ):
        wrong("config.concurrency", "a whole number of at least 1")
    if "prices" in config:
        if _prices_of(config) is None:
            wrong(
                "config.prices",
                "a list of objects with model, usd_per_million_input_tokens and "
                "usd_per_million_output_tokens",
            )
        else:
            for model, times in Counter(price["model"] for price in config["prices"]).items():
                if times > 1:
                    found.append(
                        f"{RUN_FILE}: the model {model} has {times} prices in config.prices"
                    )
    experiment = config.get("experiment")
    if experiment is not None and not isinstance(experiment, dict):
        wrong("config.experiment", "an object or null")
    elif isinstance(experiment, dict):
        found.extend(
            f"{RUN_FILE} lacks the field config.experiment.{key}"
            for key in _EXPERIMENT_FIELDS
            if key not in experiment
        )
        for key in ("baseline", "parameter"):
            if key in experiment and not isinstance(experiment[key], str):
                wrong(f"config.experiment.{key}", "a text")
    if any_name and not is_valid_run_id(name):
        found.append(f"the name of the directory {name} is not a run identifier")
    return found


def _prices_of(config: dict | None) -> list[dict] | None:
    """`config.prices` when it has its form, with or without a model named twice."""
    prices = None if config is None else config.get("prices")
    if not isinstance(prices, list):
        return None
    for price in prices:
        if not (
            isinstance(price, dict)
            and isinstance(price.get("model"), str)
            and _is_number(price.get("usd_per_million_input_tokens"))
            and _is_number(price.get("usd_per_million_output_tokens"))
            and price["usd_per_million_input_tokens"] >= 0
            and price["usd_per_million_output_tokens"] >= 0
        ):
            return None
    return prices


def _is_list_of_article_ids(value: object) -> bool:
    return value is None or (
        isinstance(value, list) and all(isinstance(item, str) and item for item in value)
    )


def _differences_of_tokens(question: str, tokens: object, prices: list[dict] | None) -> list[str]:
    """Differences 2 and 9 of the `tokens` of one entry."""
    if not isinstance(tokens, list):
        return [f"{question} has tokens that are not a list"]
    found = []
    for count in tokens:
        if not isinstance(count, dict):
            found.append(f"{question} has a tokens entry that is not an object")
            continue
        for key in ("model", "input_tokens", "output_tokens"):
            if key not in count:
                found.append(f"{question} has a tokens entry that lacks the field {key}")
            elif key == "model" and not isinstance(count[key], str):
                found.append(f"{question} has a tokens entry whose model is not a text")
            elif key != "model" and not (_is_whole(count[key]) and count[key] >= 0):
                found.append(
                    f"{question} has a tokens entry whose {key} is not a whole number of 0 or more"
                )
    if found:
        return found
    for model, times in Counter(count["model"] for count in tokens).items():
        if times > 1:
            found.append(f"{question} names the model {model} {times} times in its tokens")
    if prices is not None:
        priced = {price["model"] for price in prices}
        found.extend(
            f"{question} names the model {model} in its tokens, which has no price"
            for model in dict.fromkeys(count["model"] for count in tokens)
            if model not in priced
        )
    return found


def _differences_of_an_entry(
    entry: dict, line: int, prices: list[dict] | None
) -> tuple[list[str], bool]:
    """Differences 2 and 6 to 9 of one entry, and whether the numbers of a summary can be
    computed from it: its status, its two lists, its tokens and its latency are sound."""
    question = entry.get("question_id")
    if "question_id" not in entry:
        return [f"{RESULTS_FILE} line {line} lacks the field question_id"], False
    if not isinstance(question, str):
        return [f"{RESULTS_FILE} line {line}: question_id is not a text"], False

    found = [f"{question} lacks the field {field}" for field in _ENTRY_FIELDS if field not in entry]
    usable = not any(
        field not in entry
        for field in ("status", "retrieved_list", "generation_list", "tokens", "latency_seconds")
    )

    status = entry.get("status")
    if "status" in entry and status not in metrics.STATUSES:
        shown = status if isinstance(status, str) else _show(status)
        found.append(f"{question} has the status {shown}, which is not one of the five")
        usable = False
    for field in metrics.LISTS:
        if field in entry and not _is_list_of_article_ids(entry[field]):
            found.append(
                f"{question} has a {field} that is neither null nor a list of non-empty texts"
            )
            usable = False
    for field in ("context", "answer", "answer_sha256"):
        if entry.get(field) is not None and not isinstance(entry[field], str):
            found.append(f"{question} has a {field} that is neither a text nor null")

    # Rules 1 and 2 of the results.
    if status in ("answered", "no_answer"):
        found.extend(
            f"{question} has the status {status} and no {field}"
            for field in ("retrieved_list", "generation_list", "answer")
            if field in entry and entry[field] is None
        )
    elif entry.get("generation_list") is not None and (
        "retrieved_list" in entry and entry["retrieved_list"] is None
    ):
        found.append(f"{question} has a generation_list and no retrieved_list")

    # Difference 8: the hash of the answer.
    if "answer" in entry and "answer_sha256" in entry:
        answer, recorded = entry["answer"], entry["answer_sha256"]
        if isinstance(answer, str) and (recorded is None or isinstance(recorded, str)):
            matches = recorded == hashlib.sha256(answer.encode("utf-8")).hexdigest()
        else:
            matches = not (answer is None and isinstance(recorded, str))
        if not matches:
            found.append(f"{question} has an answer_sha256 that is not the hash of its answer")

    # Differences 2 and 9: the tokens and the cost.
    of_tokens = (
        _differences_of_tokens(question, entry["tokens"], prices) if "tokens" in entry else []
    )
    found.extend(of_tokens)
    if of_tokens:
        usable = False
    if "cost_usd" in entry and not _is_number(entry["cost_usd"]):
        found.append(f"{question} has a cost_usd that is not a number")
    elif "cost_usd" in entry and "tokens" in entry and not of_tokens and prices is not None:
        # The comparison is exact where the cost is too large for a floating-point number.
        exact = metrics.exact_entry_cost(entry["tokens"], prices)
        try:
            computed = float(exact)
        except OverflowError:
            found.append(
                f"{question} has cost_usd {_show(entry['cost_usd'])}, "
                f"its tokens and the prices give {_exact_text(exact)}"
            )
            usable = False
        else:
            if entry["cost_usd"] != computed:
                found.append(
                    f"{question} has cost_usd {_show(entry['cost_usd'])}, "
                    f"its tokens and the prices give {_show(computed)}"
                )
    if "latency_seconds" in entry and not (
        _is_number(entry["latency_seconds"]) and entry["latency_seconds"] >= 0
    ):
        found.append(f"{question} has a latency_seconds that is not a number of 0 or more")
        usable = False
    return found, usable


def _differences_of_the_audit(
    audit: object, config: dict | None, question_set: questionsets.QuestionSet | None
) -> list[str]:
    """Difference 10: the audit result in the summary."""
    if not isinstance(audit, dict):
        return ["the audit result is absent"]
    found = [
        f"the audit result lacks the field {field}" for field in _AUDIT_FIELDS if field not in audit
    ]
    recorded, named = audit.get("dataset"), audit.get("question_set")
    if "dataset" in audit and not (
        isinstance(recorded, dict) and "name" in recorded and "revision" in recorded
    ):
        found.append("the audit result has a dataset without its name and its revision")
        recorded = None
    if "question_set" in audit and not (
        isinstance(named, dict)
        and all(key in named for key in ("description", "parts", "questions"))
    ):
        found.append(
            "the audit result has a question_set without its description, its parts and its "
            "number of questions"
        )
        named = None
    for field in ("missing_from_index", "not_in_corpus", "unknown_references"):
        if field in audit and not isinstance(audit[field], list):
            found.append(f"the audit result has a {field} that is not a list")
    if "outcome" in audit and audit["outcome"] != "passed":
        found.append(f"the audit result has the outcome {_show(audit['outcome'])}, not passed")

    # A passed audit has three empty lists, and so as many articles in the index as in the
    # corpus (spec 1's data-model.md, "Audit result").
    if audit.get("outcome") == "passed":
        found.extend(
            f"the audit result has the outcome passed and {len(audit[field])} entries in {field}"
            for field in ("missing_from_index", "not_in_corpus", "unknown_references")
            if isinstance(audit.get(field), list) and audit[field]
        )
        in_corpus, in_index = audit.get("articles_in_corpus"), audit.get("articles_in_index")
        if "articles_in_corpus" in audit and "articles_in_index" in audit and in_corpus != in_index:
            found.append(
                f"the audit result has the outcome passed with {_show(in_corpus)} articles in "
                f"the corpus and {_show(in_index)} in the index"
            )
    if config is not None:
        if "index" in audit and "index" in config and audit["index"] != config["index"]:
            found.append(
                f"the audit result is of the index {_show(audit['index'])}, "
                f"the config records {_show(config['index'])}"
            )
        of_config = config.get("dataset")
        if isinstance(recorded, dict) and isinstance(of_config, dict):
            found.extend(
                f"the audit result is of the dataset {key} {_show(recorded[key])}, "
                f"the config records {_show(of_config[key])}"
                for key in ("name", "revision")
                if key in of_config and recorded[key] != of_config[key]
            )
    if isinstance(named, dict):
        of_config = _question_set_of(config)
        if "version" not in named or "fingerprint" not in named:
            found.append("the audit result names no question set")
        else:
            found.extend(
                f"the audit result names the {key} {_show(named[key])} of the question set, "
                f"the config records {_show(of_config[key])}"
                for key in ("version", "fingerprint")
                if key in of_config and named[key] != of_config[key]
            )
        if not _is_whole(named["questions"]):
            found.append(
                f"the audit result states questions {_show(named['questions'])}, "
                "which is not a whole number"
            )
        elif question_set is not None and named["questions"] != len(question_set.questions):
            found.append(
                f"the audit result is of {_show(named['questions'])} questions, "
                f"the question set holds {len(question_set.questions)}"
            )
    return found


def _differences_of_the_summary(
    summary: dict,
    run_document: dict | None,
    question_set: questionsets.QuestionSet | None,
    computed: dict | None,
) -> list[str]:
    """Differences 2, 11 and 12 of `summary.json`. `computed` is what `summary_document`
    gives from the other files, or None when it cannot be computed."""
    found = [
        f"{SUMMARY_FILE} lacks the field {field}"
        for field in _SUMMARY_FIELDS
        if field not in summary
    ]
    config = _config_of(run_document)

    # Difference 11: the run, the question set and its size.
    if run_document is not None and "run_id" in summary and "run_id" in run_document:
        if summary["run_id"] != run_document["run_id"]:
            found.append(
                f"the summary names the run {_show(summary['run_id'])}, "
                f"{RUN_FILE} names {_show(run_document['run_id'])}"
            )
    if "question_set" in summary:
        named, of_config = summary["question_set"], _question_set_of(config)
        if not isinstance(named, dict):
            found.append(f"{SUMMARY_FILE}: question_set is not an object")
        else:
            for key in ("version", "role", "fingerprint"):
                if key not in named:
                    found.append(f"{SUMMARY_FILE} lacks the field question_set.{key}")
                elif key in of_config and named[key] != of_config[key]:
                    found.append(
                        f"the summary records the {key} {_show(named[key])} of the question set, "
                        f"{RUN_FILE} records {_show(of_config[key])}"
                    )
    if "questions" in summary and question_set is not None:
        if not _is_whole(summary["questions"]) or summary["questions"] != len(
            question_set.questions
        ):
            found.append(
                f"the summary states questions {_show(summary['questions'])}, "
                f"the question set holds {len(question_set.questions)} questions"
            )

    # Differences 2 and 12: every number of the three breakdowns, each on its own.
    breakdowns = summary.get("breakdowns")
    if "breakdowns" in summary and not isinstance(breakdowns, dict):
        found.append(f"{SUMMARY_FILE}: breakdowns is not an object")
    elif isinstance(breakdowns, dict):
        for name in metrics.BREAKDOWNS:
            given = None if computed is None else computed["breakdowns"][name]
            found.extend(_differences_of_a_breakdown(name, breakdowns.get(name), given))

    if "retrieval_misses" in summary:
        misses = summary["retrieval_misses"]
        if not (isinstance(misses, list) and all(isinstance(item, str) for item in misses)):
            found.append(f"{SUMMARY_FILE}: retrieval_misses is not a list of texts")
        elif computed is not None and misses != computed["retrieval_misses"]:
            found.append(
                f"the summary states the retrieval misses {', '.join(misses) or 'none'}; "
                f"the results give {', '.join(computed['retrieval_misses']) or 'none'}"
            )
    if "questions_without_gold_articles" in summary and question_set is not None:
        stated = summary["questions_without_gold_articles"]
        without = sum(1 for _, article_ids in question_set.questions if not article_ids)
        if not _is_whole(stated) or stated != without:
            found.append(
                f"the summary states questions_without_gold_articles {_show(stated)}; "
                f"the question set gives {without}"
            )
    return found


def _differences_of_a_breakdown(name: str, stated: object, computed: dict | None) -> list[str]:
    """Differences 2 and 12 of one breakdown of the summary."""
    label = _BREAKDOWN[name]
    if not isinstance(stated, dict):
        return [f"{SUMMARY_FILE}: breakdowns.{name} is not an object"]
    found = []

    def compare(path: tuple[str, ...], line) -> None:
        """One number: absent, of a wrong kind, or another number than the results give. A
        count is a whole number: `8.0` is not one, although it is equal to 8."""
        value, given = stated, computed
        for key in path:
            if not isinstance(value, dict) or key not in value:
                found.append(f"{SUMMARY_FILE} lacks the field breakdowns.{name}.{'.'.join(path)}")
                return
            value = value[key]
            given = None if given is None else given[key]
        if path[-1] in _COUNTS or path[0] == "status":
            if not _is_whole(value):
                found.append(
                    f"{SUMMARY_FILE}: breakdowns.{name}.{'.'.join(path)} is not a whole number"
                )
                return
        if value is not None and not _is_number(value):
            found.append(f"{SUMMARY_FILE}: breakdowns.{name}.{'.'.join(path)} is not a number")
        elif computed is not None and (value != given or (value is None) != (given is None)):
            found.append(line(_show(value), _show(given)))

    def of_no_list(path: tuple[str, ...]) -> None:
        field = ".".join(path)
        compare(
            path,
            lambda value, given: (
                f"the summary states {field} {value} for {label}; the results give {given}"
            ),
        )

    def of_a_list(which: str, field: str) -> None:
        compare(
            (which, field),
            lambda value, given: (
                f"the summary states {field} {value} for the {_LIST[which]}, {label}; "
                f"the results give {given}"
            ),
        )

    of_no_list(("questions",))
    for status in metrics.STATUSES:
        of_no_list(("status", status))
    for which in metrics.LISTS:
        for field in _LIST_NUMBERS:
            of_a_list(which, field)
    for path in (
        ("cost_usd", "total"),
        ("cost_usd", "per_question"),
        ("latency_seconds", "median"),
        ("latency_seconds", "p95"),
    ):
        of_no_list(path)
    return found


def _differences_of_an_experiment(
    name: str,
    config: dict,
    question_set: questionsets.QuestionSet | None,
    runs: Path,
    sets: Path,
) -> list[str]:
    """Differences 13 to 16 of an experiment run."""
    experiment = config["experiment"]
    found = []
    recorded = _question_set_of(config)
    role = recorded.get("role") if question_set is None else question_set.role
    if role is not None and role != "golden":
        found.append(
            f"the run is an experiment on the {role} set {recorded.get('version')}; "
            "an experiment run is made on a golden set"
        )
    baseline, parameter = experiment.get("baseline"), experiment.get("parameter")
    if not isinstance(baseline, str):
        return found
    if baseline == name:
        found.append(f"the baseline {baseline} is the run itself")
        return found
    if not is_valid_run_id(baseline) or not (runs / baseline).is_dir():
        found.append(f"the baseline {baseline} does not exist in {runs.as_posix()}")
        return found

    # Difference 13: the record of the baseline, by differences 1 to 12.
    examination = _examine(baseline, runs, sets, with_experiment=False)
    if examination.differences:
        found.append(f"the baseline {baseline} does not pass its own check")
    of_baseline = _config_of(examination.run_document)
    if of_baseline is None:
        return found

    # Difference 14: the question set of the baseline.
    other = _question_set_of(of_baseline)
    on_another_set = False
    if other.get("version") != recorded.get("version"):
        on_another_set = True
        found.append(
            f"the baseline {baseline} is on the question set {other.get('version')}, "
            f"the run is on {recorded.get('version')}"
        )
    elif other.get("fingerprint") != recorded.get("fingerprint"):
        on_another_set = True
        found.append(
            f"the baseline {baseline} is on another record of the question set "
            f"{recorded.get('version')}"
        )

    # Difference 16: exactly the one parameter differs, with the two recorded values.
    if not isinstance(parameter, str):
        return found
    differing = config_differences(of_baseline, config)
    found.extend(
        f"the config differs from the baseline {baseline} in {path}, "
        "which is not the parameter the experiment names"
        for path in differing
        if path != parameter and not (on_another_set and path.startswith("question_set."))
    )
    if parameter not in differing:
        found.append(f"the config does not differ from the baseline {baseline} in {parameter}")
    if "baseline_value" in experiment:
        in_baseline = _leaves(of_baseline).get(parameter)
        if not _same(experiment["baseline_value"], in_baseline):
            found.append(
                f"the experiment records the baseline_value {_show(experiment['baseline_value'])} "
                f"for {parameter}, the config of the baseline {baseline} has {_show(in_baseline)}"
            )
    if "value" in experiment:
        in_config = _leaves(config).get(parameter)
        if not _same(experiment["value"], in_config):
            found.append(
                f"the experiment records the value {_show(experiment['value'])} for {parameter}, "
                f"the config has {_show(in_config)}"
            )
    return found


def _examine(
    name: str, runs: Path, sets: Path, *, with_experiment: bool = True, any_name: bool = False
) -> RunExamination:
    """The check of the record in the directory `name` of the registry. A file that cannot
    be read stops the examination of what depends on it; every difference that can still be
    found is reported. `with_experiment` is False for the record of a baseline, which is
    checked by the differences 1 to 12 only. `any_name` lets the check of the registry
    examine a directory whose name is not a run identifier."""
    directory = runs / name
    differences: list[str] = []

    # Difference 1: the three files.
    run_document = _read_object(directory / RUN_FILE, differences)
    entries, whole = _read_entries(directory / RESULTS_FILE, differences)
    summary = _read_object(directory / SUMMARY_FILE, differences)

    # Differences 2 and 3: `run.json`.
    if run_document is not None:
        differences.extend(_differences_of_run_json(run_document, name, any_name))
    elif any_name and not is_valid_run_id(name):
        differences.append(f"the name of the directory {name} is not a run identifier")
    config = _config_of(run_document)
    recorded = _question_set_of(config)
    role = recorded.get("role") if isinstance(recorded.get("role"), str) else None

    # Difference 4: the question set of the config.
    question_set = None
    version = recorded.get("version")
    if isinstance(version, str):
        try:
            question_set = questionsets.read(version, sets)
        except questionsets.SetNotFound as error:
            differences.append(error.reason)
        except questionsets.SetError as error:
            differences.append(str(error))
    if question_set is not None:
        for key, present in (
            ("role", question_set.role),
            ("fingerprint", question_set.fingerprint),
        ):
            if isinstance(recorded.get(key), str) and recorded[key] != present:
                differences.append(
                    f"the config records the {key} {recorded[key]} for question set {version}, "
                    f"its record has {present}"
                )

    # Differences 2 and 6 to 9: every entry.
    prices = _prices_of(config)
    usable = whole
    for line, entry in enumerate(entries, start=1):
        of_entry, sound = _differences_of_an_entry(entry, line, prices)
        differences.extend(of_entry)
        usable = usable and sound

    # Difference 5: exactly one entry for every question of the set.
    if question_set is not None:
        of_the_set = [question for question, _ in question_set.questions]
        named = Counter(
            entry["question_id"] for entry in entries if isinstance(entry.get("question_id"), str)
        )
        for question, times in named.items():
            if question not in set(of_the_set):
                differences.append(
                    f"{question} has an entry and is not a question of the question set"
                )
                usable = False
            elif times > 1:
                differences.append(f"{question} has {times} entries")
                usable = False
        if whole:
            for question in of_the_set:
                if question not in named:
                    differences.append(
                        f"{question} is a question of the question set and has no entry"
                    )
                    usable = False

    # Differences 2 and 10 to 12: the summary, against what the other files give.
    if summary is not None:
        computed = None
        if usable and question_set is not None and run_document is not None and prices is not None:
            unique = len({price["model"] for price in prices}) == len(prices)
            if unique and "run_id" in run_document:
                try:
                    computed = summary_document(
                        run_document, question_set, entries, summary.get("audit")
                    )
                except OverflowError:
                    differences.append(
                        "the numbers of the summary cannot be computed from the results: "
                        "a number of the results is too large for a floating-point number"
                    )
        differences.extend(
            _differences_of_the_summary(summary, run_document, question_set, computed)
        )
        if "audit" in summary:
            differences.extend(_differences_of_the_audit(summary["audit"], config, question_set))

    # Differences 13 to 16: an experiment run.
    if with_experiment and config is not None and isinstance(config.get("experiment"), dict):
        differences.extend(_differences_of_an_experiment(name, config, question_set, runs, sets))

    return RunExamination(
        run_id=name,
        differences=list(dict.fromkeys(differences)),
        question_set=question_set,
        role=role,
        run_document=run_document,
        entries=entries if whole else None,
        summary=summary,
    )


def examine(run: str, runs_dir: Path | None = None, sets_dir: Path | None = None) -> RunExamination:
    """The check of `run check` for one record, without printing. Without `runs_dir`, in
    `evals/runs`; without `sets_dir`, with the sets of `evals/golden`. Raises `RunNotFound`
    when the text is not a run identifier or the registry has no directory of that name."""
    runs = _runs_directory(runs_dir)
    if not is_valid_run_id(run) or not (runs / run).is_dir():
        raise RunNotFound(run, runs)
    return _examine(run, runs, _sets_directory(sets_dir))


# --- The three commands -------------------------------------------------------------------------


def _print_identity(examination: RunExamination) -> None:
    """The lines of the question set, when `run.json` and the record of the set can be read."""
    question_set = examination.question_set
    if examination.run_document is not None and question_set is not None:
        cli.result("question set", f"{question_set.version} ({question_set.role})")
        cli.result("questions", len(question_set.questions))


def check(
    run: str | None = None, runs_dir: Path | None = None, sets_dir: Path | None = None
) -> int:
    """The command `run check`, for one run or, with `run=None`, for the registry."""
    name = "run check"
    runs, sets = _runs_directory(runs_dir), _sets_directory(sets_dir)
    if run is not None:
        try:
            examination = examine(run, runs, sets)
        except RunNotFound as error:
            cli.reason(error.reason)
            return cli.verdict(name, "not carried out")
        cli.result("run", run)
        _print_identity(examination)
        experiment = (_config_of(examination.run_document) or {}).get("experiment")
        if isinstance(experiment, dict) and isinstance(experiment.get("baseline"), str):
            cli.result("baseline", experiment["baseline"])
        for text in examination.differences:
            cli.difference(text)
        return cli.verdict(name, "failed" if examination.differences else "passed")

    if not runs.is_dir():
        cli.reason(f"the runs directory {runs.as_posix()} does not exist")
        return cli.verdict(name, "not carried out")
    examinations = [_examine(found, runs, sets, any_name=True) for found in run_ids(runs)]
    failed = [examination for examination in examinations if examination.differences]
    cli.result("runs", len(examinations))
    cli.result("failed runs", len(failed))
    cli.result("runs on golden sets", sum(1 for found in examinations if found.role == "golden"))
    cli.result(
        "runs on held-out sets", sum(1 for found in examinations if found.role == "held-out")
    )
    for examination in failed:
        for text in examination.differences:
            cli.difference(f"{examination.run_id}: {text}")
    return cli.verdict(name, "failed" if failed else "passed")


def _mean(value: float | None) -> str:
    return "undefined" if value is None else f"{value:.4f}"


def _cost(value: float | None) -> str:
    return "undefined" if value is None else f"{value:.8f}"


def _latency(value: float | None) -> str:
    return "undefined" if value is None else f"{value:.3f}"


def _of_a_list(numbers: dict | None, gold: Sequence[str], label: str) -> str:
    """One list of one question in the block of `--per-question`."""
    if not gold:
        return f"{label} no gold articles"
    if numbers is None:
        return f"{label} absent"
    return f"{label} {numbers['found']} of {numbers['gold']}, all_found {numbers['all_found']}"


def report(
    run: str,
    per_question: bool = False,
    runs_dir: Path | None = None,
    sets_dir: Path | None = None,
) -> int:
    """The command `run report`: the numbers of one run, computed from its results."""
    name = "run report"
    try:
        examination = examine(run, runs_dir, sets_dir)
    except RunNotFound as error:
        cli.reason(error.reason)
        return cli.verdict(name, "not carried out")
    if examination.differences:
        cli.reason(f"the run check failed for {run}")
        return cli.verdict(name, "refused")

    question_set, entries = examination.question_set, examination.entries
    questions = question_set.pairs()
    numbers = metrics.summarize(questions, entries, examination.run_document["config"]["prices"])
    breakdowns = numbers["breakdowns"]

    cli.result("run", run)
    _print_identity(examination)
    for key, label in _BREAKDOWN.items():
        of_status = breakdowns[key]["status"]
        counts = ", ".join(f"{status} {of_status[status]}" for status in metrics.STATUSES)
        cli.result(f"status, {label}", f"{breakdowns[key]['questions']} questions, {counts}")
    for which in metrics.LISTS:
        for key, label in _BREAKDOWN.items():
            of_list = breakdowns[key][which]
            cli.result(
                f"{_LIST[which]}, {label}",
                f"{of_list['questions']} questions, "
                f"mean share_found {_mean(of_list['mean_share_found'])}, "
                f"all_found {of_list['all_found']} of {of_list['questions']} "
                f"({_mean(of_list['share_all_found'])})",
            )
    cli.result("retrieval misses", len(numbers["retrieval_misses"]))
    for question in numbers["retrieval_misses"]:
        print(f"  {question}")
    cli.result("questions without gold articles", numbers["questions_without_gold_articles"])
    for key, label in _BREAKDOWN.items():
        cost = breakdowns[key]["cost_usd"]
        cli.result(
            f"cost_usd answering, {label}",
            f"{breakdowns[key]['questions']} questions, total {_cost(cost['total'])}, "
            f"per question {_cost(cost['per_question'])}",
        )
    for key, label in _BREAKDOWN.items():
        latency = breakdowns[key]["latency_seconds"]
        cli.result(
            f"latency_seconds, {label}",
            f"{breakdowns[key]['questions']} questions, median {_latency(latency['median'])}, "
            f"p95 {_latency(latency['p95'])}",
        )
    if per_question:
        rows = metrics.per_question(questions, entries)
        cli.result("per question", len(rows))
        for row, (_, gold) in zip(rows, questions, strict=True):
            print(
                f"  {row['question_id']}: {row['status']}; "
                f"{_of_a_list(row['generation_list'], gold, 'generation list')}; "
                f"{_of_a_list(row['retrieved_list'], gold, 'retrieved list')}"
            )
    return cli.verdict(name, "done")


def compare(
    first: str, second: str, runs_dir: Path | None = None, sets_dir: Path | None = None
) -> int:
    """The command `run compare`: two runs on one question set, question by question, on
    `all_found` of the generation list."""
    name = "run compare"
    runs, sets = _runs_directory(runs_dir), _sets_directory(sets_dir)

    # Step 1: both runs exist.
    for run in (first, second):
        if not is_valid_run_id(run) or not (runs / run).is_dir():
            cli.reason(RunNotFound(run, runs).reason)
            return cli.verdict(name, "not carried out")

    # Step 2: both records pass their check; the first run is checked first.
    examinations = []
    for run in (first, second):
        examination = examine(run, runs, sets)
        if examination.differences:
            cli.reason(f"the run check failed for {run}")
            return cli.verdict(name, "refused")
        examinations.append(examination)

    # Step 3: both runs are on the same question set, by version and fingerprint.
    one, other = (examination.question_set for examination in examinations)
    if one.version != other.version:
        cli.reason(f"the runs are on different question sets: {one.version} and {other.version}")
        return cli.verdict(name, "refused")
    if one.fingerprint != other.fingerprint:
        cli.reason(
            f"the runs are on different records of the question set {one.version}: "
            f"{one.fingerprint} and {other.fingerprint}"
        )
        return cli.verdict(name, "refused")

    # Step 4: the comparison.
    compared = metrics.compare(one.pairs(), examinations[0].entries, examinations[1].entries)
    cli.result("first run", first)
    cli.result("second run", second)
    cli.result("question set", f"{one.version} ({one.role})")
    if one.role == "held-out":
        cli.result("held-out set", "its questions are not used to choose a setting")
    cli.result("outcome", "all_found on the generation list")
    cli.result("compared", compared["compared"])
    for label, key in (("left out", "left_out"), ("gained", "gained"), ("lost", "lost")):
        cli.result(label, len(compared[key]))
        for question in compared[key]:
            print(f"  {question}")
    return cli.verdict(name, "done")
