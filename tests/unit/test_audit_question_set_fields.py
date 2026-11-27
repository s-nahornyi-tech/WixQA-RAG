"""The question set in the audit result (task T041): `src/wixqa_rag/audit.py`.

Covers the blocks that spec 2 added on 2026-11-27 to the contracts of spec 1 (spec.md of
spec 2, FR-008: the result of an audit "MUST name the question set by version"):

- specs/001-corpus-and-audit/contracts/records.md, "Audit result": an audit that names a
  question set writes three more fields inside `question_set`, after `questions`:
  `version`, `role` and `fingerprint`. An audit that names none writes the document of
  spec 1, unchanged, and a document without the three fields is read as one of an audit
  that named no set;
- specs/001-corpus-and-audit/contracts/audit-gate.md, "The call": the result names the set
  in `question_set_version`, `question_set_role` and `question_set_fingerprint` of the
  `AuditResult`, which are `None` when no set was named; rule 6: the result converts to the
  JSON document and back without loss; `question_set` and `questions` are not given
  together: a call with both raises `ValueError`.

The tests need no store. Besides the names of contracts/audit-gate.md they use
`AuditResult.to_document()` and `AuditResult.from_document(document)`, described in
tests/unit/test_audit_compare.py.
"""

import copy
import dataclasses
import hashlib
import importlib
import inspect
import json
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SETS = REPOSITORY_ROOT / "tests" / "data" / "sets"
RECORDED_AUDIT = REPOSITORY_ROOT / "evals" / "indexes" / "wixqa-001" / "audit.json"

FINGERPRINT = hashlib.sha256((SETS / "example.json").read_bytes()).hexdigest()

# The document of an audit that named the question set `example` (spec 1's
# contracts/records.md, "Audit result", with the block added on 2026-11-27).
WITH_SET = {
    "index": "example",
    "dataset": {"name": "example", "revision": None},
    "question_set": {
        "description": "question set example (golden)",
        "parts": ["exq"],
        "questions": 3,
        "version": "example",
        "role": "golden",
        "fingerprint": FINGERPRINT,
    },
    "articles_in_corpus": 6,
    "articles_in_index": 5,
    "missing_from_index": ["ex-006"],
    "not_in_corpus": [],
    "unknown_references": [{"question": "exq-002", "article_id": "ex-003"}],
    "questions_without_article_ids": 0,
    "outcome": "failed",
    "audited_at": "2026-11-27T10:15:00Z",
}

# The document of an audit that named no question set: the document of spec 1.
WITHOUT_SET = WITH_SET | {
    "question_set": {
        "description": "every question of the question parts",
        "parts": ["exq"],
        "questions": 3,
    }
}

THREE_FIELDS = ("question_set_version", "question_set_role", "question_set_fingerprint")


def load_audit():
    return importlib.import_module("wixqa_rag.audit")


def result_with_set():
    """An `AuditResult` of an audit that named the question set `example`, made from its
    fields and not from a document."""
    audit = load_audit()
    return audit.AuditResult(
        index="example",
        outcome=audit.AuditOutcome.FAILED,
        dataset_name="example",
        dataset_revision=None,
        question_set_description="question set example (golden)",
        question_set_parts=("exq",),
        questions=3,
        articles_in_corpus=6,
        articles_in_index=5,
        missing_from_index=("ex-006",),
        not_in_corpus=(),
        unknown_references=(("exq-002", "ex-003"),),
        questions_without_article_ids=0,
        audited_at="2026-11-27T10:15:00Z",
        question_set_version="example",
        question_set_role="golden",
        question_set_fingerprint=FINGERPRINT,
    )


# --- The three fields of the result ------------------------------------------------------------


def test_an_audit_result_has_the_three_fields_of_a_question_set():
    """contracts/audit-gate.md: `question_set_version`, `question_set_role` and
    `question_set_fingerprint` of the `AuditResult`."""
    result = result_with_set()

    assert result.question_set_version == "example"
    assert result.question_set_role == "golden"
    assert result.question_set_fingerprint == FINGERPRINT


def test_the_three_fields_are_none_when_no_set_was_named():
    """contracts/audit-gate.md: the three fields "are `None` when no set was named": a
    result that is made without them, as every result of spec 1 was."""
    audit = load_audit()

    result = audit.AuditResult(index="example", outcome=audit.AuditOutcome.PASSED)

    for field in THREE_FIELDS:
        assert getattr(result, field) is None, field


def test_a_result_that_was_not_carried_out_names_no_set():
    """contracts/audit-gate.md, rule 4: an audit that was not carried out has a reason; its
    three fields are `None`."""
    audit = load_audit()

    result = audit.AuditResult(
        index="example",
        outcome=audit.AuditOutcome.NOT_CARRIED_OUT,
        reason="question set harness does not match the dataset of tests/data/example",
    )

    for field in THREE_FIELDS:
        assert getattr(result, field) is None, field


# --- To the document and back -------------------------------------------------------------------


def test_a_result_with_a_question_set_converts_to_the_document_with_the_three_fields():
    """contracts/records.md, the block added on 2026-11-27: `question_set.version`,
    `question_set.role` and `question_set.fingerprint`, "after `questions`"; every other
    field as in spec 1."""
    document = result_with_set().to_document()

    assert document == WITH_SET
    assert list(document["question_set"]) == [
        "description",
        "parts",
        "questions",
        "version",
        "role",
        "fingerprint",
    ]
    assert list(document) == list(WITH_SET)
    json.dumps(document)


def test_a_document_with_a_question_set_converts_to_the_result_and_back_without_loss():
    """contracts/audit-gate.md, rule 6: the result converts to the JSON document of
    records.md and back without loss."""
    audit = load_audit()
    document = copy.deepcopy(WITH_SET)

    result = audit.AuditResult.from_document(document)

    assert document == WITH_SET, "the document is left as it was"
    assert result == result_with_set()
    assert result.to_document() == WITH_SET
    assert audit.AuditResult.from_document(result.to_document()) == result


def test_a_result_with_a_question_set_survives_json_text():
    """The same through the text of a file, as `summary.json` of a run carries the audit
    result (specs/002-evaluation-harness/contracts/records.md, "`summary.json`")."""
    audit = load_audit()
    text = json.dumps(result_with_set().to_document(), indent=2, ensure_ascii=False)

    assert audit.AuditResult.from_document(json.loads(text)) == result_with_set()


@pytest.mark.parametrize("role", ["golden", "held-out"])
def test_the_role_of_the_question_set_is_kept(role):
    """contracts/records.md: `question_set.role` is `golden` or `held-out`."""
    audit = load_audit()
    document = copy.deepcopy(WITH_SET)
    document["question_set"]["role"] = role
    document["question_set"]["description"] = f"question set example ({role})"

    result = audit.AuditResult.from_document(document)

    assert result.question_set_role == role
    assert result.to_document() == document


# --- A document without the three fields ---------------------------------------------------------


def test_a_document_without_the_three_fields_reads_as_an_audit_that_named_no_set():
    """contracts/records.md: "a document without the three fields is read as one of an audit
    that named no set"."""
    audit = load_audit()

    result = audit.AuditResult.from_document(copy.deepcopy(WITHOUT_SET))

    for field in THREE_FIELDS:
        assert getattr(result, field) is None, field
    assert result.question_set_description == "every question of the question parts"
    assert result.questions == 3


def test_an_audit_that_named_no_set_writes_the_document_of_spec_1_unchanged():
    """contracts/records.md: "An audit that names none writes the document above,
    unchanged": no key `version`, `role` or `fingerprint`, not even with the value null."""
    audit = load_audit()

    result = audit.AuditResult.from_document(copy.deepcopy(WITHOUT_SET))
    document = result.to_document()

    assert result.question_set_version is None
    assert document == WITHOUT_SET
    assert list(document["question_set"]) == ["description", "parts", "questions"]


def test_a_result_with_a_set_and_one_without_are_not_equal():
    """The three fields are part of the result: two results that differ only in them are
    told apart."""
    audit = load_audit()
    with_set = result_with_set()
    without = dataclasses.replace(
        with_set,
        question_set_version=None,
        question_set_role=None,
        question_set_fingerprint=None,
    )

    assert with_set != without
    assert set(without.to_document()["question_set"]) == {"description", "parts", "questions"}
    assert audit.AuditResult.from_document(without.to_document()) == without


def test_the_recorded_audit_of_wixqa_001_reads_as_an_audit_that_named_no_set():
    """tasks.md, T041: `evals/indexes/wixqa-001/audit.json`, written by spec 1 before the
    three fields existed, reads so, and converts back to the document it holds. The file is
    read and never written."""
    audit = load_audit()
    before = RECORDED_AUDIT.read_bytes()
    document = json.loads(before)
    assert set(document["question_set"]) == {"description", "parts", "questions"}

    result = audit.AuditResult.from_document(copy.deepcopy(document))

    for field in THREE_FIELDS:
        assert getattr(result, field) is None, field
    assert result.index == "wixqa-001"
    assert result.outcome is audit.AuditOutcome.PASSED
    assert result.to_document() == document
    assert RECORDED_AUDIT.read_bytes() == before


# --- `questions` and `question_set` are not given together ---------------------------------------


@pytest.mark.parametrize("call", ["audit_index", "require_passed_audit"])
def test_a_call_with_both_questions_and_question_set_raises_value_error(
    call, temporary_root, monkeypatch
):
    """contracts/audit-gate.md: "`question_set` and `questions` are not given together; a
    call with both raises `ValueError`." The error is raised for the arguments themselves:
    the call needs no store, and `DATABASE_URL` is not set here."""
    audit = load_audit()
    monkeypatch.chdir(temporary_root)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    questions = [("exq-001", ["ex-001"])]

    with pytest.raises(ValueError):
        getattr(audit, call)(
            "example",
            data_dir=REPOSITORY_ROOT / "tests" / "data" / "example",
            questions=questions,
            question_set="example",
            sets_dir=SETS,
        )


@pytest.mark.parametrize("call", ["audit_index", "require_passed_audit"])
def test_the_two_calls_take_the_keyword_arguments_question_set_and_sets_dir(call):
    """contracts/audit-gate.md, the block added on 2026-11-27: "two keyword arguments of
    `audit_index` and of `require_passed_audit`", `question_set` and `sets_dir`, both
    optional; the three arguments of spec 1 stay in their places."""
    parameters = inspect.signature(getattr(load_audit(), call)).parameters

    assert list(parameters)[:3] == ["index", "data_dir", "questions"]
    for name in ("question_set", "sets_dir"):
        assert name in parameters, f"{call} takes the keyword argument `{name}`"
        assert parameters[name].default is None


def test_the_command_takes_the_set_and_the_sets_directory_as_its_fourth_and_fifth_argument():
    """contracts/audit-gate.md: `command(index, data_dir=None, json_file=None,
    question_set=None, sets_dir=None)` is the command `index audit` with the two new
    options."""
    parameters = inspect.signature(load_audit().command).parameters

    assert list(parameters) == ["index", "data_dir", "json_file", "question_set", "sets_dir"]
    for name in ("data_dir", "json_file", "question_set", "sets_dir"):
        assert parameters[name].default is None
