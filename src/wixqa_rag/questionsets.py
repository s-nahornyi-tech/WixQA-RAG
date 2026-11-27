"""The question sets: the question identifier, the draw, the record of a set, its check, and
the commands `set build` and `set check` (specs/002-evaluation-harness: data-model.md,
"Question set", "Selection rule" and "Check of a question set"; contracts/harness.md,
"`wixqa_rag.questionsets`"; contracts/cli.md, "`set build`" and "`set check`").

- `question_id`, `is_valid_version`, `draw_key` and `draw` depend on their arguments alone.
- `read` reads a record as it is; `record` computes the record of a rule; `examine` is the
  check of a record against a data directory that has already passed the dataset check.
- `build` and `check` are the work of the two commands: they print the lines of the contract
  and return the exit code.

No function changes a file that exists. `build` is the only one that writes, and it writes
one new file.
"""

import hashlib
import json
import os
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from wixqa_rag import cli, dataset, settings

DRAW_METHOD = "sha256-order-v1"
ROLES = ("golden", "held-out")

# data-model.md, "Version of a question set".
_VERSION = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_LONGEST_VERSION = 40

# A question identifier: the part, a hyphen and the row number (data-model.md).
_QUESTION_ID = re.compile(r"(.+)-([0-9]+)")


# --- The question identifier, the version and the draw ------------------------------------------


def question_id(part: str, row: int) -> str:
    """The question identifier of a row, counted from 1: the name of the part, a hyphen and
    the row number with at least three digits (FR-002)."""
    return f"{part}-{row:03d}"


def is_valid_version(version: object) -> bool:
    """Whether a text has the form of a version of a question set."""
    return (
        isinstance(version, str)
        and len(version) <= _LONGEST_VERSION
        and _VERSION.fullmatch(version) is not None
    )


def draw_key(seed: int, identifier: str) -> str:
    """The draw key of a question identifier with a seed, as 64 hexadecimal characters."""
    return hashlib.sha256(f"{DRAW_METHOD}:{seed}:{identifier}".encode()).hexdigest()


def draw(identifiers: Iterable[str], number: int, seed: int) -> list[str]:
    """The identifiers that the draw selects, in the order in which they were given: the
    `number` identifiers with the smallest draw keys, equal keys ordered by identifier."""
    given = list(identifiers)
    if seed < 0:
        raise ValueError(f"the seed of a draw is 0 or greater, not {seed}")
    if number < 1 or number > len(given):
        raise ValueError(f"a draw takes from 1 to {len(given)} of these identifiers, not {number}")
    ordered = sorted(given, key=lambda identifier: (draw_key(seed, identifier), identifier))
    selected = set(ordered[:number])
    return [identifier for identifier in given if identifier in selected]


# --- The record ---------------------------------------------------------------------------------


class SetError(Exception):
    """A record does not exist or cannot be read as a question-set record. The message names
    the file."""


class SetNotFound(SetError):
    """The record does not exist, or the version has another form than a version. `reason`
    is the line that a command prints for it."""

    def __init__(self, message: str, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


class RuleNotApplicable(ValueError):
    """A rule cannot be applied to a data directory; the message is the reason, ready to be
    printed."""


class ComplementedSetFailed(Exception):
    """The record that a set complements does not pass its own check, so the check of the
    set is not carried out. `version` is the complemented set, `differences` those of its
    check."""

    def __init__(self, version: str, differences: Sequence[str]) -> None:
        super().__init__(f"the check of question set {version} failed")
        self.version = version
        self.differences = list(differences)


@dataclass(frozen=True)
class QuestionSet:
    """One record that was read, as it is."""

    version: str
    role: str
    dataset_name: str
    dataset_revision: str | None
    # The document of the rule.
    rule: dict
    # Pairs of a question identifier and the tuple of its gold article ids, in record order.
    questions: tuple[tuple[str, tuple[str, ...]], ...]
    # The SHA-256 of the bytes of the file.
    fingerprint: str
    # The whole record.
    document: dict

    def pairs(self) -> list[tuple[str, list[str]]]:
        """The questions as pairs of an identifier and its list of article ids: the form that
        `audit_index` takes as `questions`."""
        return [(question, list(article_ids)) for question, article_ids in self.questions]

    def gold(self, question: str) -> set[str]:
        """The set of distinct gold article ids of a question of the set."""
        for identifier, article_ids in self.questions:
            if identifier == question:
                return set(article_ids)
        raise KeyError(question)


def _is_whole_number(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_text(value: object) -> bool:
    return isinstance(value, str)


def _what_is_wrong(document: object) -> str | None:
    """Why a parsed file is not a question-set record (contracts/records.md, "Question-set
    record"), or None when it has the form of one. The rules of the values are for the check."""
    if not isinstance(document, dict):
        return "it is not a JSON object"
    if not _is_text(document.get("version")):
        return "version is not a text"
    if document.get("role") not in ROLES:
        return "role is neither golden nor held-out"

    recorded = document.get("dataset")
    if not isinstance(recorded, dict):
        return "dataset is not an object"
    if not _is_text(recorded.get("name")):
        return "dataset.name is not a text"
    if recorded.get("revision") is not None and not _is_text(recorded.get("revision")):
        return "dataset.revision is neither a text nor null"
    parts = recorded.get("parts")
    if not isinstance(parts, list):
        return "dataset.parts is not a list"
    for part in parts:
        if not (
            isinstance(part, dict)
            and _is_text(part.get("name"))
            and _is_whole_number(part.get("rows"))
            and _is_text(part.get("sha256"))
        ):
            return "a part of dataset.parts lacks its name, its rows or its sha256"

    rule = document.get("rule")
    if not isinstance(rule, dict):
        return "rule is not an object"
    if rule.get("kind") == "draw":
        if not _is_text(rule.get("method")):
            return "rule.method is not a text"
        if not _is_whole_number(rule.get("seed")):
            return "rule.seed is not a whole number"
        take = rule.get("take")
        if not isinstance(take, list):
            return "rule.take is not a list"
        for entry in take:
            if not (
                isinstance(entry, dict)
                and _is_text(entry.get("part"))
                and _is_whole_number(entry.get("questions"))
            ):
                return "an entry of rule.take lacks its part or its number of questions"
    elif rule.get("kind") == "complement":
        if not _is_text(rule.get("of")):
            return "rule.of is not a text"
        if not _is_text(rule.get("of_fingerprint")):
            return "rule.of_fingerprint is not a text"
    else:
        return "rule.kind is neither draw nor complement"

    questions = document.get("questions")
    if not isinstance(questions, list):
        return "questions is not a list"
    for question in questions:
        if not (
            isinstance(question, dict)
            and _is_text(question.get("id"))
            and isinstance(question.get("article_ids"), list)
            and all(_is_text(article_id) for article_id in question["article_ids"])
        ):
            return "a question lacks its id or its list of article ids"
    if not _is_whole_number(document.get("count")):
        return "count is not a whole number"
    return None


def _sets_directory(sets_dir: Path | None) -> Path:
    return settings.SETS_DIR if sets_dir is None else Path(sets_dir)


def read(version: str, sets_dir: Path | None = None) -> QuestionSet:
    """Read `<sets_dir>/<version>.json`; without `sets_dir`, from `evals/golden`. The record
    is read as it is and is not checked against a dataset."""
    directory = _sets_directory(sets_dir)
    file = directory / f"{version}.json"
    reason = f"question set {version} does not exist in {directory.as_posix()}"
    if not is_valid_version(version):
        message = f"{file.as_posix()}: {version} is not a valid version of a question set"
        raise SetNotFound(message, reason)
    if not file.is_file():
        raise SetNotFound(f"{file.as_posix()} does not exist", reason)
    data = file.read_bytes()
    try:
        document = json.loads(data)
    except ValueError:
        raise SetError(f"{file.as_posix()} is not a question-set record: it is not JSON") from None
    wrong = _what_is_wrong(document)
    if wrong is not None:
        raise SetError(f"{file.as_posix()} is not a question-set record: {wrong}")
    return QuestionSet(
        version=document["version"],
        role=document["role"],
        dataset_name=document["dataset"]["name"],
        dataset_revision=document["dataset"]["revision"],
        rule=document["rule"],
        questions=tuple(
            (question["id"], tuple(question["article_ids"])) for question in document["questions"]
        ),
        fingerprint=hashlib.sha256(data).hexdigest(),
        document=document,
    )


def canonical(document: dict) -> bytes:
    """The bytes of the canonical form of a record (contracts/records.md)."""
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


class _Data:
    """The question parts of one data directory that passed the dataset check."""

    def __init__(self, data_dir: Path | None) -> None:
        self.directory = settings.default_data_dir() if data_dir is None else Path(data_dir)
        self.manifest = dataset.read_manifest(self.directory)
        self.parts = {part.name: part for part in self.manifest.parts if part.role == "questions"}
        self._rows: dict[str, list[dict]] = {}

    def rows(self, part: str) -> list[dict]:
        """The rows of a question part, in file order."""
        if part not in self._rows:
            data = (self.directory / self.parts[part].path).read_bytes()
            self._rows[part] = [json.loads(line) for line in data.split(b"\n") if line.strip()]
        return self._rows[part]

    def identifiers(self, part: str) -> list[str]:
        """The question identifiers of a question part, by ascending row number."""
        return [question_id(part, number) for number in range(1, len(self.rows(part)) + 1)]

    def row_of(self, identifier: str) -> dict | None:
        """The row of a question, or None when the identifier names no question of a
        question part of this directory."""
        found = _QUESTION_ID.fullmatch(identifier)
        if found is None or found.group(1) not in self.parts:
            return None
        part, number = found.group(1), int(found.group(2))
        if question_id(part, number) != identifier or not 1 <= number <= len(self.rows(part)):
            return None
        return self.rows(part)[number - 1]


def _take_of(rule: dict) -> list[tuple[str, int]]:
    return [(entry["part"], entry["questions"]) for entry in rule["take"]]


def record(
    version: str, role: str, rule: dict, data_dir: Path | None, sets_dir: Path | None = None
) -> dict:
    """The document of the record that `set build` would write for this rule and data
    directory. It writes nothing. A rule that cannot be applied raises `RuleNotApplicable`."""
    if role not in ROLES:
        raise ValueError(f"the role of a question set is golden or held-out, not {role}")
    data = _Data(data_dir)
    kind = rule.get("kind")
    if kind == "draw":
        take, seed = _take_of(rule), rule["seed"]
        if not _is_whole_number(seed) or seed < 0:
            raise ValueError(f"the seed of a draw is a whole number of 0 or more, not {seed}")
        if not take:
            raise ValueError("a draw takes from at least one part")
        selected = []
        for part, number in take:
            if [name for name, _ in take].count(part) > 1:
                raise ValueError(f"the rule takes from the part {part} more than once")
            if not _is_whole_number(number) or number < 1:
                raise ValueError(f"the rule takes {number} questions of {part}")
            if part not in data.parts:
                raise RuleNotApplicable(
                    f"{part} is not a question part of {data.directory.as_posix()}"
                )
            identifiers = data.identifiers(part)
            if number > len(identifiers):
                raise RuleNotApplicable(
                    f"the rule takes {number} questions of {part}, which has {len(identifiers)}"
                )
            selected.extend(draw(identifiers, number, seed))
        parts = [part for part, _ in take]
        recorded_rule = {
            "kind": "draw",
            "method": DRAW_METHOD,
            "seed": seed,
            "take": [{"part": part, "questions": number} for part, number in take],
        }
    elif kind == "complement":
        of = rule["of"]
        complemented = read(of, sets_dir)
        if complemented.rule["kind"] != "draw":
            raise RuleNotApplicable(
                f"question set {of} is itself a complement: only a set whose rule is a draw "
                "is complemented"
            )
        parts = [part["name"] for part in complemented.document["dataset"]["parts"]]
        held = {question for question, _ in complemented.questions}
        selected = []
        for part in parts:
            if part not in data.parts:
                raise RuleNotApplicable(
                    f"{part} is not a question part of {data.directory.as_posix()}"
                )
            selected.extend(
                identifier for identifier in data.identifiers(part) if identifier not in held
            )
        if not selected:
            raise RuleNotApplicable(f"the complement of question set {of} is empty")
        recorded_rule = {
            "kind": "complement",
            "of": of,
            "of_fingerprint": complemented.fingerprint,
        }
    else:
        raise ValueError(f"the kind of a rule is draw or complement, not {kind}")

    return {
        "version": version,
        "role": role,
        "dataset": {
            "name": data.manifest.name,
            "revision": data.manifest.revision,
            "parts": [
                {"name": part, "rows": data.parts[part].rows, "sha256": data.parts[part].sha256}
                for part in parts
            ],
        },
        "rule": recorded_rule,
        "questions": [
            {"id": identifier, "article_ids": list(data.row_of(identifier)["article_ids"])}
            for identifier in selected
        ],
        "count": len(selected),
    }


# --- The check of a record ----------------------------------------------------------------------


@dataclass(frozen=True)
class SetExamination:
    """The outcome of the check of one record."""

    question_set: QuestionSet
    # Every difference, without the `difference: ` in front.
    differences: list[str]
    # The numbers of the report, under the names of its lines and in their order.
    counts: dict[str, int]


def _part_of(identifier: str) -> str | None:
    """The part that a question identifier names, or None for a text of another form."""
    found = _QUESTION_ID.fullmatch(identifier)
    return None if found is None else found.group(1)


def _distinct(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _ids(article_ids: Sequence[str]) -> str:
    """contracts/cli.md, "`set check`": ids separated by a comma and a space; an empty list is
    written `none`."""
    return ", ".join(article_ids) if article_ids else "none"


def _numbers(document: dict) -> dict[str, int]:
    """The numbers that describe a record as it is: the questions of each part of
    `dataset.parts`, the questions, and the three numbers of the gold articles."""
    questions = document["questions"]
    numbers: dict[str, int] = {}
    for part in _distinct(part["name"] for part in document["dataset"]["parts"]):
        numbers[part] = sum(1 for question in questions if _part_of(question["id"]) == part)
    distinct = [len(set(question["article_ids"])) for question in questions]
    numbers["questions"] = len(questions)
    numbers["single-article"] = sum(1 for number in distinct if number == 1)
    numbers["multi-article"] = sum(1 for number in distinct if number >= 2)
    numbers["questions without gold articles"] = sum(1 for number in distinct if number == 0)
    return numbers


def _texts(data: _Data, identifiers: Iterable[str]) -> list[str]:
    """The question texts of the questions that the data directory has, as they are. A value
    that is not a text is compared in its JSON form."""
    texts = []
    for identifier in _distinct(identifiers):
        row = data.row_of(identifier)
        if row is not None:
            text = row.get("question")
            texts.append(text if isinstance(text, str) else json.dumps(text, sort_keys=True))
    return texts


def _differences_of_the_dataset(document: dict, data: _Data) -> list[str]:
    """Differences 1 and 2: the dataset that the record names, and its parts."""
    found = []
    recorded, manifest = document["dataset"], data.manifest
    if recorded["name"] != manifest.name:
        found.append(
            f"the question set records the dataset {recorded['name']}, "
            f"the data directory has the dataset {manifest.name}"
        )
    if recorded["revision"] != manifest.revision:
        found.append(
            f"the question set records the revision {recorded['revision'] or 'none'}, "
            f"the data directory has the revision {manifest.revision or 'none'}"
        )
    for name, times in Counter(part["name"] for part in recorded["parts"]).items():
        if times > 1:
            found.append(f"the question set records the part {name} {times} times")
    for part in recorded["parts"]:
        name = part["name"]
        if name not in data.parts:
            found.append(_no_question_part(name))
            continue
        if part["rows"] != data.parts[name].rows:
            found.append(
                f"the question set records {part['rows']} rows of {name}, "
                f"the data directory has {data.parts[name].rows}"
            )
        if part["sha256"] != data.parts[name].sha256:
            found.append(
                f"the question set records the SHA-256 {part['sha256']} of {name}, "
                f"the data directory has {data.parts[name].sha256}"
            )
    return found


def _no_question_part(name: str) -> str:
    return (
        f"the question set records the part {name}, "
        "the data directory has no question part of that name"
    )


def _differences_of_a_draw(
    version_ids: list[str], rule: dict, data: _Data
) -> tuple[list[str], list[str]]:
    """Differences 8, 3, 4 and 6 of a set whose rule draws, and the parts of the rule in its
    order. A rule that breaks its own rules selects nothing that could be compared, so
    differences 3, 4 and 6 are looked for only when difference 8 is not found."""
    found = []
    take = _take_of(rule)
    parts = _distinct(part for part, _ in take)
    if rule["method"] != DRAW_METHOD:
        found.append(f"the method of the draw is {rule['method']}, not {DRAW_METHOD}")
    if rule["seed"] < 0:
        found.append(f"the seed of the draw is {rule['seed']}, which is below 0")
    if not take:
        found.append("the rule takes from no part")
    for part, times in Counter(part for part, _ in take).items():
        if times > 1:
            found.append(f"the rule takes from {part} {times} times")
    for part, number in take:
        if number < 1:
            found.append(f"the rule takes {number} questions of {part}")
        elif part in data.parts and number > len(data.rows(part)):
            found.append(
                f"the rule takes {number} questions of {part}, which has {len(data.rows(part))}"
            )
    if found:
        return found, parts

    selected = []
    for part, number in take:
        if part in data.parts:
            selected.extend(draw(data.identifiers(part), number, rule["seed"]))
    held = set(version_ids)
    found.extend(
        f"{question} is selected by the rule and is not in the question set"
        for question in selected
        if question not in held
    )
    chosen = set(selected)
    found.extend(
        f"{question} is in the question set and is not selected by the rule"
        for question in _distinct(version_ids)
        if question not in chosen
    )
    for part, number in take:
        holds = sum(1 for question in version_ids if _part_of(question) == part)
        if holds != number:
            found.append(
                f"the question set holds {holds} questions of {part}, the rule takes {number}"
            )
    return found, parts


def _differences_of_a_complement(
    version: str, version_ids: list[str], rule: dict, complemented: QuestionSet, data: _Data
) -> tuple[list[str], list[str], dict[str, int]]:
    """Differences 9, 10 and 11 of a complement, the parts of its rule in their order, and
    the three numbers that only a complement reports."""
    found = []
    of = rule["of"]
    if complemented.rule["kind"] == "draw":
        parts = _distinct(part for part, _ in _take_of(complemented.rule))
    else:
        found.append(
            f"{of} is itself a complement: only a set whose rule is a draw is complemented"
        )
        parts = _distinct(part["name"] for part in complemented.document["dataset"]["parts"])
    if complemented.fingerprint != rule["of_fingerprint"]:
        found.append(f"{of} has changed since {version} was produced")

    other = {question for question, _ in complemented.questions}
    held = set(version_ids)
    in_both = [question for question in _distinct(version_ids) if question in other]
    found.extend(f"{question} is in both {version} and {of}" for question in in_both)
    of_the_parts = [
        question for part in parts if part in data.parts for question in data.identifiers(part)
    ]
    in_neither = [
        question for question in of_the_parts if question not in held and question not in other
    ]
    found.extend(f"{question} is in neither {version} nor {of}" for question in in_neither)
    # A question outside the parts of the complemented set is in neither count: the rule
    # does not select it.
    known = set(of_the_parts) | other
    found.extend(
        f"{question} is in the question set and is not selected by the rule"
        for question in _distinct(version_ids)
        if question not in known
    )

    shared_texts = set(_texts(data, version_ids)) & set(_texts(data, other))
    numbers = {
        "in both sets": len(in_both),
        "in neither set": len(in_neither),
        "question texts in both sets": len(shared_texts),
    }
    return found, parts, numbers


def examine(
    version: str, data_dir: Path | None = None, sets_dir: Path | None = None
) -> SetExamination:
    """The check of `set check` for one record, without printing (data-model.md, "Check of a
    question set"). The data directory must already have passed the dataset check. The
    record that a complement names is read and compared with; whether it passes its own
    check is asked by `examine_with_complemented`."""
    question_set = read(version, sets_dir)
    document, rule = question_set.document, question_set.rule
    complemented = read(rule["of"], sets_dir) if rule["kind"] == "complement" else None
    data = _Data(data_dir)
    version_ids = [question for question, _ in question_set.questions]

    differences = []
    if document["version"] != version:
        differences.append(
            f"the question set records the version {document['version']}, "
            f"its file is named {version}.json"
        )
    differences.extend(_differences_of_the_dataset(document, data))

    counts = _numbers(document)
    counts["repeated question texts"] = sum(
        1 for times in Counter(_texts(data, version_ids)).values() if times > 1
    )
    if complemented is None:
        of_the_rule, parts = _differences_of_a_draw(version_ids, rule, data)
    else:
        of_the_rule, parts, numbers = _differences_of_a_complement(
            version, version_ids, rule, complemented, data
        )
        counts.update(numbers)
    differences.extend(of_the_rule)

    # A part that only the rule names and the data directory lacks.
    recorded_parts = [part["name"] for part in document["dataset"]["parts"]]
    differences.extend(
        _no_question_part(part)
        for part in parts
        if part not in data.parts and part not in recorded_parts
    )
    if recorded_parts != parts:
        differences.append(
            f"the question set records the parts {_ids(recorded_parts)}, "
            f"its rule gives the parts {_ids(parts)}"
        )

    # Difference 5: the gold article ids, compared with the row of the question.
    for question, article_ids in dict.fromkeys(question_set.questions):
        row = data.row_of(question)
        if row is not None and list(article_ids) != list(row["article_ids"]):
            differences.append(
                f"{question} has the gold articles {_ids(article_ids)} in the question set "
                f"and {_ids(row['article_ids'])} in the dataset"
            )

    # Difference 6, `count`, and difference 7.
    if document["count"] != len(version_ids):
        differences.append(
            f"count is {document['count']}, the question set holds {len(version_ids)} questions"
        )
    for question, times in Counter(version_ids).items():
        if times > 1:
            differences.append(f"{question} occurs {times} times in the question set")
    if version_ids != sorted(version_ids, key=lambda question: _place(question, parts)):
        differences.append("the questions of the question set are not in the order of the dataset")

    return SetExamination(question_set=question_set, differences=differences, counts=counts)


def _place(identifier: str, parts: list[str]) -> tuple[int, str, int]:
    """Where a question stands in the order of a record: the parts in the order of the rule,
    and within a part by ascending row number. A question of no part of the rule comes last."""
    found = _QUESTION_ID.fullmatch(identifier)
    if found is None:
        return len(parts) + 1, identifier, 0
    part, number = found.group(1), int(found.group(2))
    return (parts.index(part) if part in parts else len(parts)), part, number


def examine_with_complemented(
    version: str, data_dir: Path | None = None, sets_dir: Path | None = None
) -> SetExamination:
    """The check of one record as `set check` and the audit carry it out: for a complement,
    the complemented record must pass this same check first (FR-032). Raises `SetError` when
    a record cannot be read and `ComplementedSetFailed` when the complemented record has a
    difference."""
    rule = read(version, sets_dir).rule
    if rule["kind"] == "complement":
        complemented = examine(rule["of"], data_dir, sets_dir)
        if complemented.differences:
            raise ComplementedSetFailed(rule["of"], complemented.differences)
    return examine(version, data_dir, sets_dir)


# --- The two commands ---------------------------------------------------------------------------


def _checked_data_dir(data_dir: Path | None) -> Path | None:
    """The data directory when it passes the dataset check. Otherwise the lines of the check
    and the reason are printed, and None is returned: the command is not carried out."""
    try:
        if data_dir is None:
            pinned = dataset.read_pinned()
            directory = settings.data_dir_of_revision(pinned.revision)
            examination = dataset.examine(directory, pinned)
        else:
            directory = Path(data_dir)
            examination = dataset.examine(directory)
    except dataset.DatasetError as error:
        cli.reason(str(error))
        return None
    if examination.differences:
        dataset.print_examination(examination)
        cli.reason(f"the dataset check failed for {directory.as_posix()}")
        return None
    return directory


def _print_report(document: dict, numbers: dict[str, int], already_written: bool = False) -> None:
    """The lines of a report up to the numbers (contracts/cli.md, "`set build`" and "`set
    check`")."""
    rule = document["rule"]
    name = document["version"] + (" (already written)" if already_written else "")
    cli.result("question set", name)
    cli.result("role", document["role"])
    cli.result("dataset", document["dataset"]["name"])
    cli.result("revision", document["dataset"]["revision"] or "none")
    if rule["kind"] == "draw":
        cli.result("rule", f"draw {rule['method']}")
        cli.result("seed", rule["seed"])
    else:
        cli.result("rule", "complement")
        cli.result("complement of", rule["of"])
    for line, number in numbers.items():
        cli.result(line, number)


def _selection(rule: object) -> object:
    """What of a rule is its selection: the kind and, for a draw, the method, the parts and
    the numbers; for a complement, the complemented set. The seed is not part of it."""
    if not isinstance(rule, dict):
        return None
    if rule.get("kind") == "draw":
        return "draw", rule.get("method"), json.dumps(rule.get("take"), sort_keys=True)
    return rule.get("kind"), rule.get("of")


def _why_refused(version: str, existing: bytes, document: dict) -> str:
    """The reason for which a build over an existing version with other bytes is refused."""
    try:
        recorded = json.loads(existing)
    except ValueError:
        recorded = None
    old = recorded.get("rule") if isinstance(recorded, dict) else None
    new = document["rule"]
    if isinstance(old, dict) and _selection(old) != _selection(new):
        return f"question set {version} exists with another selection"
    if isinstance(old, dict) and new["kind"] == "draw" and old.get("seed") != new["seed"]:
        return f"question set {version} exists with another seed"
    return f"question set {version} exists with other content"


def build(
    version: str,
    role: str,
    take: Sequence[tuple[str, int]] | None,
    seed: int | None,
    complement_of: str | None,
    data_dir: Path | None = None,
    sets_dir: Path | None = None,
) -> int:
    """The command `set build`, in the six steps of contracts/cli.md. `take` is a list of
    pairs of a part name and a number, with `seed`, or `complement_of` is a version."""
    name = "set build"
    if (complement_of is None) == (take is None and seed is None):
        raise ValueError("a build has exactly one rule: a draw or a complement")
    if complement_of is None and (not take or seed is None):
        raise ValueError("a draw has at least one part to take from, and a seed")
    sets = _sets_directory(sets_dir)

    # Step 1: the versions.
    for given in (version, complement_of):
        if given is not None and not is_valid_version(given):
            cli.reason(f"{given} is not a valid version of a question set")
            return cli.verdict(name, "not carried out")

    # Step 2: `evals/golden` takes only sets of the pinned dataset.
    if data_dir is not None and sets.resolve() == settings.SETS_DIR.resolve():
        cli.reason(f"{settings.SETS_DIR.as_posix()} takes only question sets of the pinned dataset")
        return cli.verdict(name, "refused")

    # Step 3: the dataset check.
    directory = _checked_data_dir(data_dir)
    if directory is None:
        return cli.verdict(name, "not carried out")

    # Step 4: the rule can be applied.
    if complement_of is None:
        rule = {
            "kind": "draw",
            "seed": seed,
            "take": [{"part": part, "questions": number} for part, number in take],
        }
    else:
        try:
            complemented = read(complement_of, sets)
        except SetNotFound as error:
            cli.reason(error.reason)
            return cli.verdict(name, "not carried out")
        except SetError as error:
            cli.reason(str(error))
            return cli.verdict(name, "not carried out")
        if complemented.rule["kind"] != "draw":
            cli.reason(
                f"question set {complement_of} is itself a complement: only a set whose rule "
                "is a draw is complemented"
            )
            return cli.verdict(name, "refused")
        examination = examine(complement_of, directory, sets)
        if examination.differences:
            for text in examination.differences:
                cli.difference(text)
            cli.reason(f"the check of question set {complement_of} failed")
            return cli.verdict(name, "not carried out")
        rule = {"kind": "complement", "of": complement_of}
    try:
        document = record(version, role, rule, directory, sets)
    except RuleNotApplicable as error:
        cli.reason(str(error))
        return cli.verdict(name, "refused")

    # Step 5: a version is written once.
    data = canonical(document)
    file = sets / f"{version}.json"
    already_written = False
    if file.exists():
        existing = file.read_bytes()
        if existing != data:
            cli.reason(_why_refused(version, existing, document))
            return cli.verdict(name, "refused")
        already_written = True

    # Step 6: the record, under a temporary name first, and the report.
    if not already_written:
        sets.mkdir(parents=True, exist_ok=True)
        temporary = sets / f".{version}.json.{os.getpid()}.tmp"
        try:
            temporary.write_bytes(data)
            os.replace(temporary, file)
        finally:
            temporary.unlink(missing_ok=True)
    _print_report(document, _numbers(document), already_written)
    cli.result("record", file.as_posix())
    return cli.verdict(name, "done")


def check(version: str, data_dir: Path | None = None, sets_dir: Path | None = None) -> int:
    """The command `set check`, in the four steps of contracts/cli.md."""
    name = "set check"
    sets = _sets_directory(sets_dir)
    try:
        # Step 1: the record exists and can be read.
        read(version, sets)
        # Step 2: the dataset check.
        directory = _checked_data_dir(data_dir)
        if directory is None:
            return cli.verdict(name, "not carried out")
        # Steps 3 and 4: the complemented record passes its check, and the record is compared.
        examination = examine_with_complemented(version, directory, sets)
    except SetNotFound as error:
        cli.reason(error.reason)
        return cli.verdict(name, "not carried out")
    except SetError as error:
        cli.reason(str(error))
        return cli.verdict(name, "not carried out")
    except ComplementedSetFailed as error:
        for text in error.differences:
            cli.difference(text)
        cli.reason(str(error))
        return cli.verdict(name, "not carried out")

    _print_report(examination.question_set.document, examination.counts)
    for text in examination.differences:
        cli.difference(text)
    return cli.verdict(name, "failed" if examination.differences else "passed")
