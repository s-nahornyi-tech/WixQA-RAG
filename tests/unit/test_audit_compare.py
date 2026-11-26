"""The comparison of the audit, on plain sets and lists without a store (tasks T055):
`src/wixqa_rag/audit.py`.

Covers:

- data-model.md, "Audit result": the definitions of `missing_from_index`, `not_in_corpus`,
  `unknown_references`, `questions_without_article_ids` and `outcome` (FR-012, FR-013,
  FR-014), and the edge cases "an empty `article_ids` list" and "one question names the same
  article twice";
- data-model.md, "Question", and research.md, section 14: the question reference;
- contracts/audit-gate.md: the names `AuditOutcome`, `AuditResult` and `AuditNotPassed`, and
  rule 6: the result converts to the JSON document of contracts/records.md, "Audit result",
  and back without loss.

contracts/audit-gate.md fixes the names of the gate. For what it leaves without a name, these
tests need four more from `audit.py`:

    compare(corpus_ids, index_ids, questions) -> dict
        # `corpus_ids` and `index_ids`: any collections of article ids; `questions`: pairs of
        # a question identifier and its list of article ids. The dict has the five keys
        # `missing_from_index`, `not_in_corpus`, `unknown_references`,
        # `questions_without_article_ids` and `outcome`, with the values of the JSON
        # document: sorted lists of ids, a sorted list of {"question", "article_id"}
        # objects, a number, and "passed" or "failed".
    question_reference(part: str, row: int) -> str
    AuditResult.to_document() -> dict            # the JSON document of contracts/records.md
    AuditResult.from_document(document) -> AuditResult

All documents named here are in specs/001-corpus-and-audit/.
"""

import copy
import importlib
import json

import pytest

EMPTY = {
    "missing_from_index": [],
    "not_in_corpus": [],
    "unknown_references": [],
    "questions_without_article_ids": 0,
    "outcome": "passed",
}


def load_audit():
    """Import the module; it fails while `src/wixqa_rag/audit.py` does not exist (plan.md)."""
    return importlib.import_module("wixqa_rag.audit")


def compare(corpus_ids, index_ids, questions=()):
    return load_audit().compare(corpus_ids, index_ids, questions)


def pair(question: str, article_id: str) -> dict:
    return {"question": question, "article_id": article_id}


# --- The three lists and the outcome (data-model.md, "Audit result") -------------------------


def test_equal_sets_and_known_references_pass():
    """data-model.md, "Audit result": `outcome` is `passed` when the three lists are empty.
    The result has the five fields of the definition and no other."""
    ids = ["ex-001", "ex-002", "ex-003"]
    questions = [("exq-001", ["ex-001"]), ("exq-002", ["ex-002", "ex-003"])]

    assert compare(ids, ids, questions) == EMPTY


def test_missing_from_index_are_the_ids_in_the_corpus_and_not_in_the_index():
    """data-model.md, "Audit result": `missing_from_index` = the ids in C and not in I, sorted
    (FR-012). One list that is not empty makes the outcome `failed` (FR-014)."""
    result = compare({"ex-001", "ex-002", "ex-003"}, {"ex-002"})

    assert result == {**EMPTY, "missing_from_index": ["ex-001", "ex-003"], "outcome": "failed"}


def test_not_in_corpus_are_the_ids_in_the_index_and_not_in_the_corpus():
    """data-model.md, "Audit result": `not_in_corpus` = the ids in I and not in C, sorted."""
    result = compare({"ex-002"}, {"ex-005", "ex-002", "ex-004"})

    assert result == {**EMPTY, "not_in_corpus": ["ex-004", "ex-005"], "outcome": "failed"}


def test_both_lists_can_be_filled_at_once():
    """FR-012: the audit lists every id of either kind; one does not hide the other."""
    result = compare(["a", "b", "c"], ["b", "c", "d"])

    assert result == {
        **EMPTY,
        "missing_from_index": ["a"],
        "not_in_corpus": ["d"],
        "outcome": "failed",
    }


def test_unknown_references_are_the_pairs_whose_article_is_not_in_the_index():
    """data-model.md, "Audit result": `unknown_references` = every pair of a question and one
    of its `article_ids` values that is not in I (FR-013)."""
    ids = ["ex-001", "ex-002"]
    questions = [("exq-001", ["ex-001"]), ("exq-002", ["ex-002", "ex-999"])]

    result = compare(ids, ids, questions)

    assert result == {
        **EMPTY,
        "unknown_references": [pair("exq-002", "ex-999")],
        "outcome": "failed",
    }


def test_a_reference_is_judged_by_the_index_and_not_by_the_corpus():
    """data-model.md, "Audit result": "not in I". An article of the corpus that the index
    does not hold is an unknown reference; an article that only the index holds is not."""
    questions = [("q-1", ["only-in-corpus"]), ("q-2", ["only-in-index"]), ("q-3", ["in-both"])]

    result = compare(["only-in-corpus", "in-both"], ["only-in-index", "in-both"], questions)

    assert result == {
        "missing_from_index": ["only-in-corpus"],
        "not_in_corpus": ["only-in-index"],
        "unknown_references": [pair("q-1", "only-in-corpus")],
        "questions_without_article_ids": 0,
        "outcome": "failed",
    }


def test_an_id_that_a_question_names_twice_counts_once():
    """data-model.md, "Audit result": "An id that a question names twice counts once" (the
    edge case "one question names the same article twice")."""
    questions = [("exq-001", ["ex-999", "ex-001", "ex-999"])]

    result = compare(["ex-001"], ["ex-001"], questions)

    assert result["unknown_references"] == [pair("exq-001", "ex-999")]


def test_two_questions_that_name_the_same_unknown_article_are_two_pairs():
    """data-model.md, "Audit result": every pair of a question and an id; an id counts once
    for each question that names it."""
    questions = [("exq-002", ["ex-999"]), ("exq-001", ["ex-999"])]

    result = compare(["ex-001"], ["ex-001"], questions)

    assert result["unknown_references"] == [pair("exq-001", "ex-999"), pair("exq-002", "ex-999")]


def test_a_question_without_article_ids_is_counted_and_produces_no_pair():
    """data-model.md, "Audit result": `questions_without_article_ids` is the number of
    questions whose `article_ids` list is empty (the edge case "a question has an empty
    `article_ids` list"). Such a question is no difference: the outcome stays `passed`."""
    questions = [("exq-001", []), ("exq-002", ["ex-001"]), ("exq-003", [])]

    result = compare(["ex-001"], ["ex-001"], questions)

    assert result == {**EMPTY, "questions_without_article_ids": 2}


def test_the_lists_are_sorted():
    """data-model.md, "Audit result": the id lists are sorted, and the pairs are sorted by
    question and id, whatever the order of what came in."""
    questions = [
        ("q-b", ["z-9", "known", "a-1"]),
        ("q-a", ["m-5"]),
        ("q-c", []),
        ("q-b2", ["a-1"]),
    ]

    result = compare(["known", "c-3", "c-1", "c-2"], ["i-2", "known", "i-1"], questions)

    assert result["missing_from_index"] == ["c-1", "c-2", "c-3"]
    assert result["not_in_corpus"] == ["i-1", "i-2"]
    assert result["unknown_references"] == [
        pair("q-a", "m-5"),
        pair("q-b", "a-1"),
        pair("q-b", "z-9"),
        pair("q-b2", "a-1"),
    ]


def test_an_id_that_occurs_several_times_is_one_id():
    """data-model.md, "Audit result": C and I are sets of ids; the index names an article once
    for each of its passages, and the lists name it once."""
    result = compare(["a", "a", "b"], ["b", "b", "c", "c", "c"])

    assert result["missing_from_index"] == ["a"]
    assert result["not_in_corpus"] == ["c"]


def test_the_comparison_reads_any_collection_and_changes_none():
    """contracts/audit-gate.md, rule 3: the call changes nothing. Sets, lists and tuples are
    read, and the lists of the caller are as they were."""
    corpus = ("b", "a")
    index = frozenset({"a"})
    article_ids = ["z", "a", "z"]

    result = compare(corpus, index, iter([("q", article_ids)]))

    assert result["missing_from_index"] == ["b"]
    assert result["unknown_references"] == [pair("q", "z")]
    assert article_ids == ["z", "a", "z"]


@pytest.mark.parametrize(
    ("corpus", "index", "questions", "outcome"),
    [
        (["a"], ["a"], [], "passed"),
        ([], [], [], "passed"),
        (["a"], ["a"], [("q", [])], "passed"),
        (["a", "b"], ["a"], [], "failed"),
        (["a"], ["a", "b"], [], "failed"),
        (["a"], ["a"], [("q", ["b"])], "failed"),
    ],
    ids=["equal", "both empty", "only a question without ids", "missing", "extra", "unknown"],
)
def test_the_outcome_is_passed_only_when_the_three_lists_are_empty(
    corpus, index, questions, outcome
):
    """data-model.md, "Audit result": `passed` when the three lists are empty, otherwise
    `failed` (FR-014). Each list alone makes the audit fail."""
    assert compare(corpus, index, questions)["outcome"] == outcome


def test_the_known_answers_of_the_example_directories():
    """SC-003 on plain data: an index built from `example` holds `ex-001` to `ex-005`; against
    the corpus with `ex-006`, the corpus without `ex-005` and the question `exq-003` that
    names `ex-999`, the comparison names exactly that difference."""
    index = ["ex-001", "ex-002", "ex-003", "ex-004", "ex-005"]
    questions = [
        ("exq-001", ["ex-001"]),
        ("exq-002", ["ex-002", "ex-003"]),
        ("exq-003", ["ex-004"]),
    ]
    unknown = [*questions[:2], ("exq-003", ["ex-004", "ex-999"])]

    assert compare(index, index, questions) == EMPTY
    assert compare([*index, "ex-006"], index, questions) == {
        **EMPTY,
        "missing_from_index": ["ex-006"],
        "outcome": "failed",
    }
    assert compare(index[:4], index, questions) == {
        **EMPTY,
        "not_in_corpus": ["ex-005"],
        "outcome": "failed",
    }
    assert compare(index, index, unknown) == {
        **EMPTY,
        "unknown_references": [pair("exq-003", "ex-999")],
        "outcome": "failed",
    }


# --- The question reference (data-model.md, "Question") ---------------------------------------


@pytest.mark.parametrize(
    ("part", "row", "reference"),
    [
        ("wixqa_expertwritten", 17, "wixqa_expertwritten-017"),
        ("wixqa_synthetic", 6221, "wixqa_synthetic-6221"),
        ("exq", 3, "exq-003"),
        ("exq", 1, "exq-001"),
        ("wixqa_simulated", 200, "wixqa_simulated-200"),
        ("wixqa_synthetic", 1000, "wixqa_synthetic-1000"),
    ],
)
def test_a_question_reference_is_the_part_a_hyphen_and_the_row_number(part, row, reference):
    """data-model.md, "Question": the name of the part, a hyphen, and the row number counted
    from 1 and written with at least three digits. The first three rows are the examples of
    the document."""
    assert load_audit().question_reference(part, row) == reference


# --- The names of the gate (contracts/audit-gate.md) ------------------------------------------


def test_the_three_outcomes_can_be_told_apart():
    """contracts/audit-gate.md and FR-014: `AuditOutcome` is an enumeration with `PASSED`,
    `FAILED` and `NOT_CARRIED_OUT`."""
    outcome = load_audit().AuditOutcome

    assert {member.name for member in outcome} == {"PASSED", "FAILED", "NOT_CARRIED_OUT"}
    assert len({outcome.PASSED, outcome.FAILED, outcome.NOT_CARRIED_OUT}) == 3


def test_the_gate_offers_the_names_of_the_contract():
    """contracts/audit-gate.md, "The call": the five names that later specs import."""
    audit = load_audit()

    assert callable(audit.audit_index)
    assert callable(audit.require_passed_audit)
    assert isinstance(audit.AuditResult, type)
    assert issubclass(audit.AuditNotPassed, Exception)


# --- The JSON document and back (contracts/audit-gate.md, rule 6) -----------------------------

# The example of contracts/records.md, "Audit result".
FAILED_DOCUMENT = {
    "index": "example",
    "dataset": {"name": "example", "revision": None},
    "question_set": {
        "description": "every question of the question parts",
        "parts": ["exq"],
        "questions": 3,
    },
    "articles_in_corpus": 6,
    "articles_in_index": 5,
    "missing_from_index": ["ex-006"],
    "not_in_corpus": [],
    "unknown_references": [],
    "questions_without_article_ids": 0,
    "outcome": "failed",
    "audited_at": "2026-11-24T10:15:00Z",
}

PASSED_DOCUMENT = {
    "index": "wixqa-001",
    "dataset": {"name": "Wix/WixQA", "revision": "d662dc42479c14e202eccd832f8c4b66a035c4cc"},
    "question_set": {
        "description": "every question of the question parts",
        "parts": ["wixqa_expertwritten", "wixqa_simulated", "wixqa_synthetic"],
        "questions": 6621,
    },
    "articles_in_corpus": 6221,
    "articles_in_index": 6221,
    "missing_from_index": [],
    "not_in_corpus": [],
    "unknown_references": [],
    "questions_without_article_ids": 4,
    "outcome": "passed",
    "audited_at": "2026-12-01T08:00:59Z",
}

EVERY_LIST_DOCUMENT = {
    **FAILED_DOCUMENT,
    "question_set": {"description": "a question set of the caller", "parts": [], "questions": 2},
    "not_in_corpus": ["ex-005", "ex-007"],
    "unknown_references": [pair("exq-002", "ex-998"), pair("exq-003", "ex-999")],
    "questions_without_article_ids": 1,
}

DOCUMENTS = {
    "failed": FAILED_DOCUMENT,
    "passed": PASSED_DOCUMENT,
    "every list": EVERY_LIST_DOCUMENT,
}


@pytest.mark.parametrize("name", DOCUMENTS)
def test_a_result_converts_to_its_json_document_and_back_without_loss(name):
    """contracts/audit-gate.md, rule 6: the result converts to the JSON document of
    contracts/records.md and back without loss. The document survives being written as JSON
    text, read again and converted twice."""
    audit = load_audit()
    document = json.loads(json.dumps(DOCUMENTS[name]))
    given = copy.deepcopy(document)

    result = audit.AuditResult.from_document(document)

    assert isinstance(result, audit.AuditResult)
    assert result.to_document() == given
    assert json.loads(json.dumps(result.to_document())) == given
    assert audit.AuditResult.from_document(result.to_document()) == result
    assert document == given, "converting leaves the document of the caller as it was"


@pytest.mark.parametrize(
    ("name", "member"), [("failed", "FAILED"), ("passed", "PASSED"), ("every list", "FAILED")]
)
def test_a_result_read_from_a_document_has_its_outcome_and_no_reason(name, member):
    """contracts/audit-gate.md: an `AuditResult` has an `outcome`, and a `reason` that is set
    only when the audit was not carried out. A document exists only for an audit that ran to
    the end (contracts/records.md)."""
    audit = load_audit()

    result = audit.AuditResult.from_document(copy.deepcopy(DOCUMENTS[name]))

    assert result.outcome is audit.AuditOutcome[member]
    assert result.reason is None


def test_the_document_has_exactly_the_fields_of_the_records_contract():
    """contracts/records.md, "Audit result": the fields of the document; the conversion adds
    none, and `reason` is not one of them."""
    audit = load_audit()

    document = audit.AuditResult.from_document(copy.deepcopy(FAILED_DOCUMENT)).to_document()

    assert set(document) == {
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
    }
