"""The audit of an index against a real store (tasks T056): `src/wixqa_rag/audit.py` and the
command `python -m wixqa_rag index audit`.

Covers:

- FR-011 to FR-016 and User Story 3, scenarios 1 to 6; Principle I of the constitution;
- contracts/audit-gate.md, "The call" and rules 1 to 6: `audit_index`,
  `require_passed_audit`, `AuditResult`, `AuditOutcome` and `AuditNotPassed`;
- contracts/cli.md, "`index audit`": the order of the steps, the report, the result file at
  `--json` or at the default place, the verdicts and the exit codes;
- contracts/records.md, "Audit result": every field of the result;
- data-model.md, "Audit result": the three outcomes; the edge cases "an article has no
  text", "an empty `article_ids` list" and "the same article twice".

The indexes are built with the embedder double, through the fixture `build`; the audit calls
no provider and needs no provider key (contracts/audit-gate.md, rule 2), so the key is removed
for every test. The gate is called directly, under the names that contracts/audit-gate.md
fixes; the tests need two more names, described in tests/unit/test_audit_compare.py:
`AuditResult.to_document()`, and the attribute `result` of an `AuditNotPassed`, which is the
`AuditResult` it carries. The command line is typed in the temporary repository root.

Every test is marked `store`. All documents named here are in specs/001-corpus-and-audit/.
"""

import hashlib
import importlib
import json
import re
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

pytestmark = pytest.mark.store

EXAMPLE_ARTICLE_IDS = ["ex-001", "ex-002", "ex-003", "ex-004", "ex-005"]

RESULT_FIELDS = {
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


def load_audit():
    """Import the module; it fails while `src/wixqa_rag/audit.py` does not exist (plan.md)."""
    return importlib.import_module("wixqa_rag.audit")


@pytest.fixture(autouse=True)
def no_provider_key(monkeypatch):
    """contracts/audit-gate.md, rule 2: the audit needs no provider key."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture
def example_index(store, build, examples) -> str:
    """An index of this test, built from `tests/data/example` with the embedder double."""
    index = store.new_index()
    built = build(index, examples / "example")
    assert built.exit_code == 0, "\n".join(built.lines)
    return index


def files_of(directory: Path) -> dict[str, bytes]:
    return {
        file.relative_to(directory).as_posix(): file.read_bytes()
        for file in sorted(directory.rglob("*"))
        if file.is_file()
    }


def changed_copy(source: Path, target: Path, part: str, change) -> Path:
    """A copy of an example directory in which the rows of one part were changed; its manifest
    is written again from its files, so the copy passes the dataset check."""
    shutil.copytree(source, target)
    file = target / f"{part}.jsonl"
    rows = [json.loads(line) for line in file.read_text("utf-8").splitlines() if line.strip()]
    change(rows)
    data = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode("utf-8")
    file.write_bytes(data)
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["parts"]:
        if entry["name"] == part:
            entry.update(rows=len(rows), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return target


def pair(question: str, article_id: str) -> dict:
    return {"question": question, "article_id": article_id}


def audit_command(run_command, root: Path, index: str, data_dir=None, json_file=None):
    """Type `index audit` in the temporary repository root, without the provider key."""
    command = f"python -m wixqa_rag index audit --index {index}"
    if data_dir is not None:
        command += f" --data-dir {data_dir}"
    if json_file is not None:
        command += f" --json {json_file}"
    return run_command(command, env={"OPENAI_API_KEY": None}, cwd=root)


def assert_not_carried_out_line(result) -> str:
    """Exit code 2, `audit: not carried out` last, one `reason:` line before it."""
    assert result.exit_code == 2, result.stdout
    assert result.last_line == "audit: not carried out"
    reasons = [line for line in result.lines[:-1] if line.startswith("reason: ")]
    assert len(reasons) == 1, result.stdout
    assert result.settings_printed == ()
    return reasons[0]


def assert_not_carried_out(audit, result) -> str:
    """The outcome NOT_CARRIED_OUT with a reason (contracts/audit-gate.md, rule 4)."""
    assert isinstance(result, audit.AuditResult)
    assert result.outcome is audit.AuditOutcome.NOT_CARRIED_OUT
    assert isinstance(result.reason, str) and result.reason.strip()
    return result.reason


# --- The gate: an audit that passes -----------------------------------------------------------


def test_the_audit_of_an_index_against_its_own_data_passes(example_index, examples):
    """User Story 3, scenario 1, and contracts/records.md, "Audit result": every field of
    the result for an index built from `example` and audited against `example`."""
    audit = load_audit()
    before = datetime.now(UTC).replace(microsecond=0)

    result = audit.audit_index(example_index, examples / "example")

    after = datetime.now(UTC)
    assert isinstance(result, audit.AuditResult)
    assert result.outcome is audit.AuditOutcome.PASSED
    assert result.reason is None, "a reason is set only when the audit was not carried out"
    document = result.to_document()
    assert set(document) == RESULT_FIELDS
    audited_at = document.pop("audited_at")
    description = document["question_set"].pop("description")
    assert document == {
        "index": example_index,
        "dataset": {"name": "example", "revision": None},
        "question_set": {"parts": ["exq"], "questions": 3},
        "articles_in_corpus": 5,
        "articles_in_index": 5,
        "missing_from_index": [],
        "not_in_corpus": [],
        "unknown_references": [],
        "questions_without_article_ids": 0,
        "outcome": "passed",
    }
    assert isinstance(description, str) and description.strip()
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", audited_at)
    time = datetime.strptime(audited_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    assert before - timedelta(seconds=1) <= time <= after + timedelta(seconds=1)


def test_without_a_data_directory_the_audit_reads_the_default_one(store, build, build_root):
    """contracts/audit-gate.md, "Arguments": without `data_dir`, the default data directory
    of the pinned dataset; without `questions`, every question of every question part
    (FR-013). The temporary root pins one corpus part and two question parts of 3 rows."""
    audit = load_audit()
    index = store.new_index()
    assert build(index).exit_code == 0

    result = audit.audit_index(index)

    assert result.outcome is audit.AuditOutcome.PASSED
    document = result.to_document()
    assert document["dataset"] == {"name": "Wix/WixQA", "revision": build_root.example.revision}
    assert document["question_set"]["parts"] == ["exq", "exq_more"]
    assert document["question_set"]["questions"] == 6
    assert (document["articles_in_corpus"], document["articles_in_index"]) == (5, 5)


# --- The gate: the three kinds of difference (SC-003) -----------------------------------------


@pytest.mark.parametrize(
    ("directory", "expected"),
    [
        (
            "example-one-more-article",
            {"articles_in_corpus": 6, "missing_from_index": ["ex-006"]},
        ),
        (
            "example-one-less-article",
            {"articles_in_corpus": 4, "not_in_corpus": ["ex-005"]},
        ),
        (
            "example-unknown-reference",
            {"articles_in_corpus": 5, "unknown_references": [pair("exq-003", "ex-999")]},
        ),
    ],
)
def test_each_kind_of_difference_fails_and_names_exactly_the_ids(
    example_index, examples, directory, expected
):
    """User Story 3, scenarios 2 to 4, and SC-003: the audit fails and names exactly the ids
    that differ. A question is named by its question reference (data-model.md, "Question")."""
    audit = load_audit()

    result = audit.audit_index(example_index, examples / directory)

    assert result.outcome is audit.AuditOutcome.FAILED
    assert result.reason is None
    document = result.to_document()
    assert {
        name: document[name]
        for name in (
            "articles_in_corpus",
            "articles_in_index",
            "missing_from_index",
            "not_in_corpus",
            "unknown_references",
            "questions_without_article_ids",
            "outcome",
        )
    } == {
        "articles_in_index": 5,
        "missing_from_index": [],
        "not_in_corpus": [],
        "unknown_references": [],
        "questions_without_article_ids": 0,
        "outcome": "failed",
        **expected,
    }


# --- FR-011: the article ids come from the store ----------------------------------------------


def test_an_article_removed_in_the_store_is_named_although_no_file_changed(
    store, example_index, build_root, examples
):
    """FR-011 and contracts/audit-gate.md, rule 1: the audit takes the article ids from the
    index itself; reading files on disk does not satisfy the requirement. The passages of
    `ex-003` are removed directly in the store; the data files and the build record are as
    they were, and the audit names `ex-003` as missing from the index."""
    audit = load_audit()
    data_before = files_of(examples / "example")
    records_before = build_root.files_below("data/indexes")
    assert audit.audit_index(example_index, examples / "example").outcome is (
        audit.AuditOutcome.PASSED
    )

    assert store.remove_passages_of(example_index, "ex-003") == 1
    result = audit.audit_index(example_index, examples / "example")

    assert files_of(examples / "example") == data_before
    assert build_root.files_below("data/indexes") == records_before
    assert result.outcome is audit.AuditOutcome.FAILED
    document = result.to_document()
    assert document["missing_from_index"] == ["ex-003"]
    assert document["articles_in_index"] == 4
    assert document["articles_in_corpus"] == 5
    assert document["not_in_corpus"] == []
    assert document["unknown_references"] == [pair("exq-002", "ex-003")], (
        "a question that names the removed article refers outside the index (FR-013)"
    )


def test_the_articles_of_an_index_are_counted_once_however_many_passages(
    store, build, examples, tmp_path
):
    """data-model.md, "Audit result": I is the set of distinct `article_id` values of the
    `passages` table. An article of three passages is one article in the index."""

    def lengthen(rows):
        rows[0]["contents"] = "\n".join(letter * 1500 for letter in "abc")

    directory = changed_copy(examples / "example", tmp_path / "long", "ex", lengthen)
    index = store.new_index()
    assert build(index, directory).exit_code == 0
    assert len(store.passages(index)) == 7
    audit = load_audit()

    result = audit.audit_index(index, directory)

    assert result.outcome is audit.AuditOutcome.PASSED
    assert result.to_document()["articles_in_index"] == 5


def test_an_article_without_text_is_named_as_missing_from_the_index(
    store, build, examples, tmp_path
):
    """The edge case "an article has no text": such an article is not in the index, so the
    audit names it as missing (data-model.md, "Passage")."""

    def empty_one(rows):
        rows[4]["contents"] = " \n\n"

    directory = changed_copy(examples / "example", tmp_path / "no-text", "ex", empty_one)
    index = store.new_index()
    assert build(index, directory).exit_code == 0
    audit = load_audit()

    result = audit.audit_index(index, directory)

    assert result.outcome is audit.AuditOutcome.FAILED
    document = result.to_document()
    assert document["missing_from_index"] == ["ex-005"]
    assert (document["articles_in_corpus"], document["articles_in_index"]) == (5, 4)
    assert document["not_in_corpus"] == [] and document["unknown_references"] == []


# --- Questions (FR-013; spec.md, "Edge Cases") ------------------------------------------------


def test_a_question_without_article_ids_is_counted_and_is_no_difference(
    example_index, examples, tmp_path
):
    """The edge case "a question has an empty `article_ids` list": the audit has nothing to
    check for it, and the result gives the number of such questions."""

    def empty_two(rows):
        rows[0]["article_ids"] = []
        rows[2]["article_ids"] = []

    directory = changed_copy(examples / "example", tmp_path / "no-ids", "exq", empty_two)
    audit = load_audit()

    result = audit.audit_index(example_index, directory)

    assert result.outcome is audit.AuditOutcome.PASSED
    document = result.to_document()
    assert document["questions_without_article_ids"] == 2
    assert document["question_set"]["questions"] == 3
    assert document["unknown_references"] == []


def test_an_article_that_a_question_names_twice_is_checked_once(example_index, examples, tmp_path):
    """The edge case "one question names the same article twice": the article is checked
    once, so one pair is listed."""

    def name_twice(rows):
        rows[1]["article_ids"] = ["ex-998", "ex-002", "ex-998"]
        rows[0]["article_ids"] = ["ex-001", "ex-001"]

    directory = changed_copy(examples / "example", tmp_path / "twice", "exq", name_twice)
    audit = load_audit()

    result = audit.audit_index(example_index, directory)

    assert result.outcome is audit.AuditOutcome.FAILED
    assert result.to_document()["unknown_references"] == [pair("exq-002", "ex-998")]


def test_a_question_set_of_the_caller_replaces_the_question_parts(example_index, examples):
    """contracts/audit-gate.md, "Arguments": `questions` is the question set, as pairs of a
    question identifier and its list of article ids; spec 2 passes the golden set here.
    contracts/records.md: `question_set.parts` is empty when the caller passed its own
    question set. The questions of the data directory, one of which names `ex-999`, are not
    checked; the corpus still is."""
    audit = load_audit()
    own = [
        ("golden-0002", ["ex-404", "ex-002"]),
        ("golden-0001", ["ex-001"]),
        ("golden-0003", []),
    ]

    result = audit.audit_index(example_index, examples / "example-unknown-reference", own)

    assert result.outcome is audit.AuditOutcome.FAILED
    document = result.to_document()
    assert document["unknown_references"] == [pair("golden-0002", "ex-404")]
    assert document["question_set"]["parts"] == []
    assert document["question_set"]["questions"] == 3
    assert isinstance(document["question_set"]["description"], str)
    assert document["questions_without_article_ids"] == 1
    assert document["missing_from_index"] == [] and document["not_in_corpus"] == []


def test_a_question_set_of_the_caller_can_pass_where_the_question_parts_fail(
    example_index, examples
):
    """contracts/audit-gate.md, "Arguments": the caller's question set stands in place of the
    question parts. Against `example-unknown-reference` the audit of every question fails,
    and the audit of a question set that names only articles of the index passes."""
    audit = load_audit()
    directory = examples / "example-unknown-reference"

    every_question = audit.audit_index(example_index, directory)
    own = audit.audit_index(example_index, directory, questions=[("golden-0001", ["ex-004"])])

    assert every_question.outcome is audit.AuditOutcome.FAILED
    assert own.outcome is audit.AuditOutcome.PASSED
    assert own.to_document()["question_set"]["questions"] == 1


# --- The gate: not carried out (contracts/audit-gate.md, rule 4) ------------------------------


def test_an_index_that_does_not_exist_is_not_carried_out(store, build_root, examples):
    """User Story 3, scenario 5, and rule 4: `audit_index` returns `NOT_CARRIED_OUT` with a
    reason when the index does not exist; it does not raise, and it is neither passed nor
    failed. contracts/cli.md: `reason: index <ID> does not exist`."""
    audit = load_audit()
    index = store.new_index()

    result = audit.audit_index(index, examples / "example")

    reason = assert_not_carried_out(audit, result)
    assert index in reason and "does not exist" in reason


def test_a_schema_without_its_build_row_is_not_complete_and_not_audited(
    store, build_root, examples
):
    """FR-009 and User Story 2, scenario 5: an index that is not marked complete is not
    accepted by the audit. data-model.md, "Index": a schema without its `build` row is not
    complete. contracts/cli.md: `reason: index <ID> is not complete`."""
    audit = load_audit()
    index = store.new_index()
    store.make_schema_without_build_row(index)

    result = audit.audit_index(index, examples / "example")

    reason = assert_not_carried_out(audit, result)
    assert index in reason and "not complete" in reason


def test_a_store_that_cannot_be_reached_is_not_carried_out(
    store, example_index, examples, monkeypatch
):
    """User Story 3, scenario 5, and rule 4: a vector store that cannot be reached ends as
    not carried out. Nothing listens on port 1 of this machine. The reason does not hold the
    value of `DATABASE_URL` (FR-017)."""
    audit = load_audit()
    unreachable = "postgresql://nobody@127.0.0.1:1/no-such-store-for-this-test?connect_timeout=5"
    monkeypatch.setenv("DATABASE_URL", unreachable)

    result = audit.audit_index(example_index, examples / "example")

    reason = assert_not_carried_out(audit, result)
    assert unreachable not in reason, "the reason holds the value of DATABASE_URL"


def test_without_database_url_the_audit_is_not_carried_out_and_names_the_variable(
    store, example_index, examples, monkeypatch
):
    """contracts/audit-gate.md, rule 2: the call reads `DATABASE_URL` from the environment.
    The edge case "a credential for the vector store is missing": not carried out, and the
    missing setting is named."""
    audit = load_audit()
    monkeypatch.delenv("DATABASE_URL")

    result = audit.audit_index(example_index, examples / "example")

    assert "DATABASE_URL" in assert_not_carried_out(audit, result)


def test_a_data_directory_that_fails_the_dataset_check_is_not_carried_out(example_index, examples):
    """Rule 4 and data-model.md, "Audit result", "Three outcomes": the data directory fails
    the dataset check → not carried out. An audit against data that cannot be trusted is
    neither passed nor failed."""
    audit = load_audit()

    result = audit.audit_index(example_index, examples / "example-damaged")

    reason = assert_not_carried_out(audit, result)
    assert "dataset check failed" in reason


def test_a_data_directory_without_a_manifest_is_not_carried_out(example_index, tmp_path):
    """Rule 4: any error ends as `NOT_CARRIED_OUT` and is not raised. A folder without a
    manifest is not a local copy of a dataset."""
    audit = load_audit()
    (tmp_path / "empty").mkdir()

    assert_not_carried_out(audit, audit.audit_index(example_index, tmp_path / "empty"))


@pytest.mark.parametrize("identifier", ["Example", "with_underscore", "two--hyphens", "x" * 41, ""])
def test_an_identifier_that_breaks_the_rule_is_not_carried_out(store, examples, identifier):
    """data-model.md, "Index", "Identifier": a command given any other identifier is not
    carried out; contracts/cli.md, "`index audit`", step 1."""
    audit = load_audit()

    assert_not_carried_out(audit, audit.audit_index(identifier, examples / "example"))


# --- The gate: require_passed_audit (FR-016) --------------------------------------------------


def test_require_passed_audit_returns_the_result_of_a_passed_audit(example_index, examples):
    """FR-016 and contracts/audit-gate.md: `require_passed_audit` returns the result when the
    audit passed."""
    audit = load_audit()

    result = audit.require_passed_audit(example_index, examples / "example")

    assert isinstance(result, audit.AuditResult)
    assert result.outcome is audit.AuditOutcome.PASSED
    assert result.to_document()["index"] == example_index


def test_require_passed_audit_raises_for_a_failed_audit(example_index, examples):
    """FR-016 and rule 5: an outcome other than passed stops the run. `AuditNotPassed`
    carries the `AuditResult`, so the caller can record why the run stopped."""
    audit = load_audit()

    with pytest.raises(audit.AuditNotPassed) as raised:
        audit.require_passed_audit(example_index, examples / "example-one-more-article")

    carried = raised.value.result
    assert isinstance(carried, audit.AuditResult)
    assert carried.outcome is audit.AuditOutcome.FAILED
    assert carried.to_document()["missing_from_index"] == ["ex-006"]


def test_require_passed_audit_raises_when_the_audit_is_not_carried_out(store, build_root, examples):
    """FR-016 and rule 5: an audit that could not be completed stops the run as well; the
    carried result says why."""
    audit = load_audit()
    index = store.new_index()

    with pytest.raises(audit.AuditNotPassed) as raised:
        audit.require_passed_audit(index, examples / "example")

    carried = raised.value.result
    assert carried.outcome is audit.AuditOutcome.NOT_CARRIED_OUT
    assert index in carried.reason and "does not exist" in carried.reason


def test_require_passed_audit_takes_the_question_set_of_the_caller(example_index, examples):
    """contracts/audit-gate.md: `require_passed_audit(index, data_dir=None, questions=None)`
    passes its arguments on to the audit."""
    audit = load_audit()

    with pytest.raises(audit.AuditNotPassed) as raised:
        audit.require_passed_audit(
            example_index, examples / "example", questions=[("golden-0001", ["ex-777"])]
        )

    assert raised.value.result.to_document()["unknown_references"] == [
        pair("golden-0001", "ex-777")
    ]


# --- The gate changes nothing (contracts/audit-gate.md, rule 3) -------------------------------


def test_the_call_changes_neither_the_store_nor_the_data_nor_a_record(
    store, example_index, build_root, examples
):
    """Rule 3: the call changes nothing: not the store, not the data directory, not a record;
    writing the result is the caller's task. SC-004: repeating the audit gives the same
    outcome and the same number of articles in the index."""
    audit = load_audit()
    data_before = {name: files_of(examples / name) for name in ("example", "example-damaged")}
    root_before = {**build_root.files_below("data"), **build_root.files_below("evals")}
    passages_before = store.passages(example_index)
    build_before = store.build_rows(example_index)
    indexes_before = store.indexes()

    first = audit.audit_index(example_index, examples / "example")
    second = audit.audit_index(example_index, examples / "example")
    audit.audit_index(example_index, examples / "example-one-more-article")
    audit.audit_index(example_index, examples / "example-damaged")
    audit.audit_index(store.new_index(), examples / "example")

    assert (first.outcome, second.outcome) == (audit.AuditOutcome.PASSED,) * 2
    assert first.to_document()["articles_in_index"] == second.to_document()["articles_in_index"]
    assert {name: files_of(examples / name) for name in data_before} == data_before
    assert {**build_root.files_below("data"), **build_root.files_below("evals")} == root_before
    assert store.passages(example_index) == passages_before
    assert store.build_rows(example_index) == build_before
    assert store.indexes() == indexes_before


# --- The command `index audit` (contracts/cli.md) ---------------------------------------------


def test_the_command_prints_the_report_of_a_passed_audit_and_writes_the_result(
    example_index, build_root, examples, run_command
):
    """contracts/cli.md, "`index audit`": the report, the result written to the file given
    with `--json`, `audit: passed` and exit code 0 (FR-014, FR-015; User Story 3, scenario
    6). The document is that of contracts/records.md."""
    result = audit_command(
        run_command, build_root.root, example_index, examples / "example", "result.json"
    )

    assert result.exit_code == 0, result.stdout
    assert result.lines == [
        f"index: {example_index}",
        "dataset: example",
        "revision: none",
        "questions: 3",
        "articles in corpus: 5",
        "articles in index: 5",
        "missing from index: 0",
        "not in corpus: 0",
        "unknown question references: 0",
        "questions without article ids: 0",
        "audit result: result.json",
        "audit: passed",
    ]
    assert result.settings_printed == ()
    document = json.loads((build_root.root / "result.json").read_text(encoding="utf-8"))
    assert set(document) == RESULT_FIELDS
    assert document["index"] == example_index
    assert document["outcome"] == "passed"
    assert document["question_set"]["parts"] == ["exq"]
    assert (document["articles_in_corpus"], document["articles_in_index"]) == (5, 5)
    assert build_root.files_below("data/audits") == {}, "with `--json` no other file is written"


def test_the_command_lists_a_missing_article_and_fails(
    example_index, build_root, examples, run_command
):
    """contracts/cli.md, "`index audit`", output of an audit that found one difference: the
    id follows its count, indented by two spaces; `audit: failed`, exit code 1. The result
    file is written for a failed audit too (data-model.md, "Three outcomes")."""
    result = audit_command(
        run_command,
        build_root.root,
        example_index,
        examples / "example-one-more-article",
        "result.json",
    )

    assert result.exit_code == 1, result.stdout
    assert result.lines == [
        f"index: {example_index}",
        "dataset: example",
        "revision: none",
        "questions: 3",
        "articles in corpus: 6",
        "articles in index: 5",
        "missing from index: 1",
        "  ex-006",
        "not in corpus: 0",
        "unknown question references: 0",
        "questions without article ids: 0",
        "audit result: result.json",
        "audit: failed",
    ]
    document = json.loads((build_root.root / "result.json").read_text(encoding="utf-8"))
    assert document["outcome"] == "failed"
    assert document["missing_from_index"] == ["ex-006"]


def test_the_command_lists_every_id_and_every_pair_in_sorted_order(
    store, example_index, build_root, examples, tmp_path, run_command
):
    """contracts/cli.md, "Output", rule 6, and "`index audit`": ids and pairs are printed in
    sorted order, each pair as the question, an arrow and the article id; the lists are not
    shortened. The corpus lacks `ex-004` and `ex-005` and holds `ex-007` and `ex-006`."""

    def other_articles(rows):
        seventh = {**rows[0], "id": "ex-007"}
        sixth = {**rows[0], "id": "ex-006"}
        rows[3:] = [seventh, sixth]

    directory = changed_copy(examples / "example", tmp_path / "many", "ex", other_articles)

    def other_references(rows):
        rows[2]["article_ids"] = ["ex-999", "ex-004", "ex-888"]
        rows[0]["article_ids"] = ["ex-001", "ex-777"]
        rows[1]["article_ids"] = []

    exq = directory / "exq.jsonl"
    rows = [json.loads(line) for line in exq.read_text("utf-8").splitlines() if line.strip()]
    other_references(rows)
    data = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode("utf-8")
    exq.write_bytes(data)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    manifest["parts"][1].update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    (directory / "manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")

    result = audit_command(run_command, build_root.root, example_index, directory, "result.json")

    assert result.exit_code == 1, result.stdout
    assert result.lines[3:-2] == [
        "questions: 3",
        "articles in corpus: 5",
        "articles in index: 5",
        "missing from index: 2",
        "  ex-006",
        "  ex-007",
        "not in corpus: 2",
        "  ex-004",
        "  ex-005",
        "unknown question references: 3",
        "  exq-001 -> ex-777",
        "  exq-003 -> ex-888",
        "  exq-003 -> ex-999",
        "questions without article ids: 1",
    ]
    assert result.last_line == "audit: failed"
    document = json.loads((build_root.root / "result.json").read_text(encoding="utf-8"))
    assert document["unknown_references"] == [
        pair("exq-001", "ex-777"),
        pair("exq-003", "ex-888"),
        pair("exq-003", "ex-999"),
    ]


def test_without_json_the_result_goes_to_the_default_place(
    example_index, build_root, examples, run_command
):
    """contracts/cli.md, "`index audit`", and plan.md, open point 7: without `--json` the
    result is written to `data/audits/<index>/<time>.json`, where `<time>` has the form
    `20261124T101500Z` and is the time of the audit (contracts/records.md)."""
    result = audit_command(run_command, build_root.root, example_index, examples / "example")

    assert result.exit_code == 0, result.stdout
    written = build_root.files_below("data/audits")
    assert len(written) == 1
    (place,) = written
    match = re.fullmatch(rf"data/audits/{example_index}/(\d{{8}}T\d{{6}}Z)\.json", place)
    assert match, place
    assert f"audit result: {place}" in result.lines
    document = json.loads(written[place])
    assert document["outcome"] == "passed"
    named = datetime.strptime(match[1], "%Y%m%dT%H%M%SZ")
    assert named == datetime.strptime(document["audited_at"], "%Y-%m-%dT%H:%M:%SZ")


def test_a_file_that_exists_at_the_json_place_is_replaced(
    example_index, build_root, examples, run_command
):
    """contracts/cli.md, "`index audit`": "A file that already exists at FILE is replaced."""
    file = build_root.root / "result.json"
    file.write_text('{"outcome": "left from an earlier audit"}\n', encoding="utf-8")

    result = audit_command(
        run_command, build_root.root, example_index, examples / "example", "result.json"
    )

    assert result.exit_code == 0, result.stdout
    assert json.loads(file.read_text(encoding="utf-8"))["outcome"] == "passed"


def test_the_command_audits_the_default_data_directory_without_data_dir(
    store, build, build_root, run_command
):
    """contracts/cli.md, "`index audit`": without `--data-dir` the command uses the default
    data directory. The report names the pinned dataset and counts the questions of both
    question parts of the temporary root."""
    index = store.new_index()
    assert build(index).exit_code == 0

    result = audit_command(run_command, build_root.root, index, json_file="result.json")

    assert result.exit_code == 0, result.stdout
    assert result.lines[:6] == [
        f"index: {index}",
        "dataset: Wix/WixQA",
        f"revision: {build_root.example.revision}",
        "questions: 6",
        "articles in corpus: 5",
        "articles in index: 5",
    ]
    assert result.last_line == "audit: passed"


@pytest.mark.parametrize("with_json", [True, False], ids=["with --json", "without --json"])
def test_the_command_writes_no_result_file_when_the_audit_is_not_carried_out(
    store, build_root, examples, run_command, with_json
):
    """contracts/cli.md, "`index audit`": the index does not exist →
    `reason: index <ID> does not exist`, `audit: not carried out`, exit code 2; "a result
    file is written only when the audit ran to the end"."""
    index = store.new_index()

    result = audit_command(
        run_command,
        build_root.root,
        index,
        examples / "example",
        "result.json" if with_json else None,
    )

    reason = assert_not_carried_out_line(result)
    assert index in reason and "does not exist" in reason
    assert not (build_root.root / "result.json").exists()
    assert build_root.files_below("data/audits") == {}


def test_the_command_does_not_audit_an_index_that_is_not_complete(
    store, build_root, examples, run_command
):
    """contracts/cli.md, "`index audit`": `reason: index <ID> is not complete`,
    `audit: not carried out`, exit code 2, and no result file (FR-009)."""
    index = store.new_index()
    store.make_schema_without_build_row(index)

    result = audit_command(run_command, build_root.root, index, examples / "example", "result.json")

    reason = assert_not_carried_out_line(result)
    assert index in reason and "not complete" in reason
    assert not (build_root.root / "result.json").exists()


def test_the_command_does_not_audit_against_data_that_fails_the_dataset_check(
    example_index, build_root, examples, run_command
):
    """contracts/cli.md, "`index audit`": the lines of the check, then
    `reason: the dataset check failed for <DIR>`, `audit: not carried out`, exit code 2, and
    no result file."""
    result = audit_command(
        run_command, build_root.root, example_index, examples / "example-damaged", "result.json"
    )

    reason = assert_not_carried_out_line(result)
    assert "dataset check failed" in reason
    assert any(line.startswith("difference: ") and "ex-002" in line for line in result.lines)
    assert not (build_root.root / "result.json").exists()
    assert build_root.files_below("data/audits") == {}


def test_the_command_looks_for_the_index_before_it_reads_the_data_directory(
    store, build_root, examples, run_command
):
    """contracts/cli.md, "`index audit`", steps 3 and 4: the command stops at the first step
    that does not hold. An index that does not exist is reported before a data directory
    that fails the dataset check."""
    index = store.new_index()

    result = audit_command(run_command, build_root.root, index, examples / "example-damaged")

    reason = assert_not_carried_out_line(result)
    assert index in reason and "does not exist" in reason
    assert not [line for line in result.lines if line.startswith("difference:")]


def test_the_command_without_database_url_names_the_variable(
    example_index, build_root, examples, run_command
):
    """contracts/cli.md, "`index audit`", step 2: `DATABASE_URL` is set. A missing setting
    ends as `audit: not carried out` and is named (FR-017)."""
    result = run_command(
        f"python -m wixqa_rag index audit --index {example_index} "
        f"--data-dir {examples / 'example'} --json result.json",
        env={"DATABASE_URL": None, "OPENAI_API_KEY": None},
        cwd=build_root.root,
    )

    assert "DATABASE_URL" in assert_not_carried_out_line(result)
    assert not (build_root.root / "result.json").exists()


def test_the_command_cannot_reach_the_store(example_index, build_root, examples, run_command):
    """contracts/cli.md, "`index audit`": the store cannot be reached → `audit: not carried
    out`, exit code 2. The value of `DATABASE_URL` appears on neither stream (FR-017)."""
    unreachable = "postgresql://nobody@127.0.0.1:1/no-such-store-for-this-test?connect_timeout=5"

    result = run_command(
        f"python -m wixqa_rag index audit --index {example_index} "
        f"--data-dir {examples / 'example'} --json result.json",
        env={"DATABASE_URL": unreachable, "OPENAI_API_KEY": None},
        cwd=build_root.root,
    )

    assert_not_carried_out_line(result)
    assert not (build_root.root / "result.json").exists()


def test_the_command_changes_neither_the_store_nor_the_data(
    store, example_index, build_root, examples, run_command
):
    """FR-005 and SC-004: repeating the audit gives the same number of articles in the index
    and the same outcome, and leaves the data unchanged; the index is as it was."""
    data_before = files_of(examples / "example")
    passages_before = store.passages(example_index)
    build_before = store.build_rows(example_index)

    first = audit_command(
        run_command, build_root.root, example_index, examples / "example", "first.json"
    )
    second = audit_command(
        run_command, build_root.root, example_index, examples / "example", "second.json"
    )

    assert (first.exit_code, second.exit_code) == (0, 0)
    assert first.lines[:-2] == second.lines[:-2]
    assert files_of(examples / "example") == data_before
    assert store.passages(example_index) == passages_before
    assert store.build_rows(example_index) == build_before
