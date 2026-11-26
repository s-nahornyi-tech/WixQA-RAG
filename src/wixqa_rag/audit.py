"""The audit of an index against the dataset, its result, and the gate for later specs
(constitution, Principle I; contracts/audit-gate.md).

The audit asks the index itself which articles it holds: the ids come from the `passages`
table of the store, the table that retrieval queries, never from a file. The call changes
nothing: not the store, not the data directory, not a record. Only the command
`index audit` writes a file, the result.
"""

import enum
import json
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from wixqa_rag import cli, dataset, settings, store

NAME = "audit"

EVERY_QUESTION = "every question of the question parts"
QUESTIONS_OF_THE_CALLER = "a question set of the caller"

_TIME = "%Y-%m-%dT%H:%M:%SZ"


class AuditOutcome(enum.Enum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_CARRIED_OUT = "not carried out"


@dataclass(frozen=True)
class AuditResult:
    """The outcome of one audit of one index against one data directory.

    An audit that ran to the end has the fields of contracts/records.md, "Audit result", and
    no `reason`. An audit that was not carried out has a `reason`, and no document exists
    for it.
    """

    index: str
    outcome: AuditOutcome
    reason: str | None = None
    dataset_name: str | None = None
    dataset_revision: str | None = None
    question_set_description: str | None = None
    question_set_parts: tuple[str, ...] = ()
    questions: int = 0
    articles_in_corpus: int = 0
    articles_in_index: int = 0
    missing_from_index: tuple[str, ...] = ()
    not_in_corpus: tuple[str, ...] = ()
    # Pairs of a question and an article id that is not in the index.
    unknown_references: tuple[tuple[str, str], ...] = ()
    questions_without_article_ids: int = 0
    audited_at: str | None = None

    def to_document(self) -> dict:
        """The JSON document of contracts/records.md, "Audit result"."""
        if self.outcome is AuditOutcome.NOT_CARRIED_OUT:
            raise ValueError("an audit that was not carried out has no result document")
        return {
            "index": self.index,
            "dataset": {"name": self.dataset_name, "revision": self.dataset_revision},
            "question_set": {
                "description": self.question_set_description,
                "parts": list(self.question_set_parts),
                "questions": self.questions,
            },
            "articles_in_corpus": self.articles_in_corpus,
            "articles_in_index": self.articles_in_index,
            "missing_from_index": list(self.missing_from_index),
            "not_in_corpus": list(self.not_in_corpus),
            "unknown_references": [
                {"question": question, "article_id": article_id}
                for question, article_id in self.unknown_references
            ],
            "questions_without_article_ids": self.questions_without_article_ids,
            "outcome": self.outcome.value,
            "audited_at": self.audited_at,
        }

    @classmethod
    def from_document(cls, document: dict) -> AuditResult:
        """The result that `to_document` wrote; the document is left as it was."""
        outcome = AuditOutcome(document["outcome"])
        if outcome is AuditOutcome.NOT_CARRIED_OUT:
            raise ValueError("a result document is written only for an audit that ran to the end")
        return cls(
            index=document["index"],
            outcome=outcome,
            dataset_name=document["dataset"]["name"],
            dataset_revision=document["dataset"]["revision"],
            question_set_description=document["question_set"]["description"],
            question_set_parts=tuple(document["question_set"]["parts"]),
            questions=document["question_set"]["questions"],
            articles_in_corpus=document["articles_in_corpus"],
            articles_in_index=document["articles_in_index"],
            missing_from_index=tuple(document["missing_from_index"]),
            not_in_corpus=tuple(document["not_in_corpus"]),
            unknown_references=tuple(
                (pair["question"], pair["article_id"]) for pair in document["unknown_references"]
            ),
            questions_without_article_ids=document["questions_without_article_ids"],
            audited_at=document["audited_at"],
        )


class AuditNotPassed(Exception):
    """The audit failed or was not carried out; `result` is its `AuditResult`."""

    def __init__(self, result: AuditResult) -> None:
        super().__init__(result.reason or f"the audit of the index {result.index} failed")
        self.result = result


def question_reference(part: str, row: int) -> str:
    """The name of a question until spec 2 fixes one: its part, a hyphen and its row number,
    counted from 1 and written with at least three digits (data-model.md, "Question")."""
    return f"{part}-{row:03d}"


def compare(
    corpus_ids: Iterable[str],
    index_ids: Iterable[str],
    questions: Iterable[tuple[str, Collection[str]]],
) -> dict:
    """The comparison of data-model.md, "Audit result": the ids of the corpus, the ids of the
    index, and the questions as pairs of an identifier and its list of article ids."""
    in_corpus = set(corpus_ids)
    in_index = set(index_ids)
    unknown = set()
    without_article_ids = 0
    for question, article_ids in questions:
        named = set(article_ids)
        if not named:
            without_article_ids += 1
        unknown.update((question, article_id) for article_id in named - in_index)
    result = {
        "missing_from_index": sorted(in_corpus - in_index),
        "not_in_corpus": sorted(in_index - in_corpus),
        "unknown_references": [
            {"question": question, "article_id": article_id}
            for question, article_id in sorted(unknown)
        ],
        "questions_without_article_ids": without_article_ids,
    }
    differs = result["missing_from_index"] or result["not_in_corpus"] or unknown
    result["outcome"] = "failed" if differs else "passed"
    return result


def _rows(file: Path) -> list[dict]:
    """The rows of a part file that passed the dataset check."""
    return [json.loads(line) for line in file.read_bytes().split(b"\n") if line.strip()]


def _not_carried_out(index: str, reason: str) -> AuditResult:
    return AuditResult(index=index, outcome=AuditOutcome.NOT_CARRIED_OUT, reason=reason)


def _audit(
    index: str, data_dir: Path | None, questions
) -> tuple[AuditResult, dataset.Examination | None]:
    """The audit, in the order of contracts/cli.md, "`index audit`". Besides the result it
    returns the dataset check when that check found a difference, for the command to print."""
    # Step 1: the identifier.
    if not store.is_valid_identifier(index):
        return _not_carried_out(index, f"{index} is not a valid index identifier"), None

    pinned = dataset.read_pinned()

    # Steps 2 and 3: the store is reached, and the index exists and is complete.
    connection = store.connect()
    with connection:
        connection.read_only = True
        state, _ = store.state_of(connection, index)
        if state == store.ABSENT:
            return _not_carried_out(index, f"index {index} does not exist"), None
        if state == store.NOT_COMPLETE:
            return _not_carried_out(index, f"index {index} is not complete"), None

        # Step 4: the data directory passes the dataset check.
        if data_dir is None:
            directory = settings.data_dir_of_revision(pinned.revision)
            examination = dataset.examine(directory, pinned)
        else:
            directory = data_dir
            examination = dataset.examine(directory)
        if examination.differences:
            reason = f"the dataset check failed for {directory.as_posix()}"
            return _not_carried_out(index, reason), examination

        # Step 5: the article ids of the index, of the corpus and of the questions.
        index_ids = store.article_ids(connection, index)

    manifest = examination.manifest
    corpus = next(part for part in manifest.parts if part.role == "corpus")
    corpus_ids = {row["id"] for row in _rows(directory / corpus.path)}
    if questions is None:
        description = EVERY_QUESTION
        parts = tuple(part.name for part in manifest.parts if part.role == "questions")
        question_set = [
            (question_reference(part.name, number), row["article_ids"])
            for part in manifest.parts
            if part.role == "questions"
            for number, row in enumerate(_rows(directory / part.path), start=1)
        ]
    else:
        description = QUESTIONS_OF_THE_CALLER
        parts = ()
        question_set = [(question, list(article_ids)) for question, article_ids in questions]

    compared = compare(corpus_ids, index_ids, question_set)
    result = AuditResult(
        index=index,
        outcome=AuditOutcome(compared["outcome"]),
        dataset_name=manifest.name,
        dataset_revision=manifest.revision,
        question_set_description=description,
        question_set_parts=parts,
        questions=len(question_set),
        articles_in_corpus=len(corpus_ids),
        articles_in_index=len(index_ids),
        missing_from_index=tuple(compared["missing_from_index"]),
        not_in_corpus=tuple(compared["not_in_corpus"]),
        unknown_references=tuple(
            (pair["question"], pair["article_id"]) for pair in compared["unknown_references"]
        ),
        questions_without_article_ids=compared["questions_without_article_ids"],
        audited_at=datetime.now(UTC).strftime(_TIME),
    )
    return result, None


def _audit_without_raising(
    index: str, data_dir: Path | None, questions
) -> tuple[AuditResult, dataset.Examination | None]:
    """Every error ends as not carried out, with a reason; none looks like a failed audit."""
    try:
        return _audit(index, data_dir, questions)
    except (settings.MissingSetting, store.Unreachable, dataset.DatasetError) as error:
        return _not_carried_out(index, str(error)), None
    except Exception as error:
        text = settings.hide_values(f"unexpected error ({type(error).__name__}): {error}")
        return _not_carried_out(index, " ".join(text.split())), None


def audit_index(
    index: str,
    data_dir: Path | None = None,
    questions: Iterable[tuple[str, Sequence[str]]] | None = None,
) -> AuditResult:
    """Audit an index against a data directory and report the outcome; it raises for none of
    the three outcomes.

    Without `data_dir` the default data directory of the pinned dataset is used. Without
    `questions` the question set is every question of every question part, named by question
    reference; otherwise it is the given pairs of a question identifier and its article ids.
    """
    return _audit_without_raising(index, data_dir, questions)[0]


def require_passed_audit(
    index: str,
    data_dir: Path | None = None,
    questions: Iterable[tuple[str, Sequence[str]]] | None = None,
) -> AuditResult:
    """The gate: the result of a passed audit; `AuditNotPassed` for the two other outcomes."""
    result = audit_index(index, data_dir, questions)
    if result.outcome is not AuditOutcome.PASSED:
        raise AuditNotPassed(result)
    return result


def _print_list(name: str, items: Sequence[str]) -> None:
    cli.result(name, len(items))
    for item in items:
        print(f"  {item}")


def command(index: str, data_dir: Path | None = None, json_file: Path | None = None) -> int:
    """The command `index audit`: the report, the result file, the verdict and the exit code.

    The result is written to `json_file`, or to `data/audits/<index>/<time>.json` without
    one, and only when the audit ran to the end.
    """
    result, examination = _audit_without_raising(index, data_dir, None)
    if result.outcome is AuditOutcome.NOT_CARRIED_OUT:
        if examination is not None:
            dataset.print_examination(examination)
        cli.reason(result.reason)
        return cli.verdict(NAME, "not carried out")

    if json_file is None:
        audited_at = datetime.strptime(result.audited_at, _TIME).replace(tzinfo=UTC)
        json_file = settings.audit_result_path(index, audited_at)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(
        json.dumps(result.to_document(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    cli.result("index", result.index)
    cli.result("dataset", result.dataset_name)
    cli.result("revision", result.dataset_revision or "none")
    cli.result("questions", result.questions)
    cli.result("articles in corpus", result.articles_in_corpus)
    cli.result("articles in index", result.articles_in_index)
    _print_list("missing from index", result.missing_from_index)
    _print_list("not in corpus", result.not_in_corpus)
    _print_list(
        "unknown question references",
        [f"{question} -> {article_id}" for question, article_id in result.unknown_references],
    )
    cli.result("questions without article ids", result.questions_without_article_ids)
    cli.result("audit result", json_file.as_posix())
    return cli.verdict(NAME, result.outcome.value)
