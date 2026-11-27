"""The audit of an index with a question set as its question set, against a real store (task
T042): `src/wixqa_rag/audit.py` and the command `python -m wixqa_rag index audit --set`.

Covers:

- specs/002-evaluation-harness/spec.md, FR-008, and User Story 1, scenario 10; Principle I
  of the constitution;
- specs/002-evaluation-harness/contracts/cli.md, "`index audit`: the options `--set` and
  `--sets-dir`": step 4a, the line `question set: V (<role>)` after `revision:`, the two
  situations of the table, and `--sets-dir` without `--set` as a wrong argument;
- specs/001-corpus-and-audit/contracts/audit-gate.md, the block added on 2026-11-27: the
  keyword arguments `question_set` and `sets_dir` of `audit_index` and of
  `require_passed_audit`, and the three fields of the result;
- specs/001-corpus-and-audit/contracts/records.md, "Audit result", the block added on
  2026-11-27: the three fields inside `question_set` of the result file.

The indexes are built from `tests/data/example` with the embedder double, through the
fixture `build`; the audit calls no provider, so the key is removed for every test. The
question sets are the records of `tests/data/sets`: `example`, which was produced from
`tests/data/example`, and `harness`, which was produced from another dataset. The command
line is typed in the temporary repository root.

Every test is marked `store`: it runs in `checks` on GitHub Actions and in both scopes of
`acceptance`, and not in an agent's workspace.
"""

import hashlib
import importlib
import json
import shutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.store

SETS = Path(__file__).resolve().parents[1] / "data" / "sets"
EXAMPLE_FINGERPRINT = hashlib.sha256((SETS / "example.json").read_bytes()).hexdigest()

THREE_FIELDS = ("question_set_version", "question_set_role", "question_set_fingerprint")


def load_audit():
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


def audit_command(run_command, root: Path, index: str, *options: object):
    """Type `index audit` in the temporary repository root, without the provider key."""
    command = " ".join(["python -m wixqa_rag index audit --index", index, *map(str, options)])
    return run_command(command, env={"OPENAI_API_KEY": None}, cwd=root)


def assert_not_carried_out(audit, result) -> str:
    """The outcome NOT_CARRIED_OUT with a reason (contracts/audit-gate.md, rule 4)."""
    assert isinstance(result, audit.AuditResult)
    assert result.outcome is audit.AuditOutcome.NOT_CARRIED_OUT
    assert isinstance(result.reason, str) and result.reason.strip()
    return result.reason


def assert_not_carried_out_line(result) -> str:
    """Exit code 2, `audit: not carried out` last, one `reason:` line before it."""
    assert result.exit_code == 2, result.stdout
    assert result.last_line == "audit: not carried out"
    assert len(result.reasons) == 1, result.stdout
    assert result.lines[-2] == f"reason: {result.reasons[0]}"
    assert result.settings_printed == ()
    return result.reasons[0]


def assert_names_the_example_set(audit, result) -> None:
    """The result names the set `example`: the three fields of contracts/audit-gate.md and
    the six keys of `question_set` in the document of contracts/records.md."""
    assert result.question_set_version == "example"
    assert result.question_set_role == "golden"
    assert result.question_set_fingerprint == EXAMPLE_FINGERPRINT
    assert result.to_document()["question_set"] == {
        "description": "question set example (golden)",
        "parts": ["exq"],
        "questions": 3,
        "version": "example",
        "role": "golden",
        "fingerprint": EXAMPLE_FINGERPRINT,
    }


# --- The gate with a question set ---------------------------------------------------------------


def test_the_audit_with_the_example_set_passes_and_names_the_set(example_index, examples):
    """tasks.md, T042, and FR-008: `audit_index` with `question_set="example"` and
    `sets_dir` passes on an index built from `tests/data/example` and returns a result that
    names the set, with `questions` 3."""
    audit = load_audit()

    result = audit.audit_index(
        example_index, examples / "example", question_set="example", sets_dir=SETS
    )

    assert isinstance(result, audit.AuditResult)
    assert result.outcome is audit.AuditOutcome.PASSED
    assert result.reason is None
    assert result.questions == 3
    assert_names_the_example_set(audit, result)
    document = result.to_document()
    assert document["unknown_references"] == []
    assert document["missing_from_index"] == []
    assert (document["articles_in_corpus"], document["articles_in_index"]) == (5, 5)


def test_require_passed_audit_with_the_example_set_returns_the_result(example_index, examples):
    """contracts/audit-gate.md: `require_passed_audit` takes the same two keyword arguments
    and returns the result of a passed audit, which names the set."""
    audit = load_audit()

    result = audit.require_passed_audit(
        example_index, examples / "example", question_set="example", sets_dir=SETS
    )

    assert result.outcome is audit.AuditOutcome.PASSED
    assert result.questions == 3
    assert_names_the_example_set(audit, result)


def test_the_result_with_a_set_converts_to_the_document_and_back(example_index, examples):
    """contracts/audit-gate.md, rule 6, for a result that an audit with a set returned."""
    audit = load_audit()

    result = audit.audit_index(
        example_index, examples / "example", question_set="example", sets_dir=SETS
    )

    assert audit.AuditResult.from_document(result.to_document()) == result


def test_the_audit_checks_the_gold_articles_of_the_questions_of_the_set(
    store, example_index, examples
):
    """FR-008: the audit "checks every gold article of every question of that set against
    the index". An article that a question of the set names is removed in the store: the
    audit fails and names the question by its identifier in the set, and the result still
    names the set."""
    audit = load_audit()
    assert store.remove_passages_of(example_index, "ex-004") > 0

    result = audit.audit_index(
        example_index, examples / "example", question_set="example", sets_dir=SETS
    )

    assert result.outcome is audit.AuditOutcome.FAILED
    document = result.to_document()
    assert document["missing_from_index"] == ["ex-004"]
    assert document["unknown_references"] == [{"question": "exq-003", "article_id": "ex-004"}]
    assert_names_the_example_set(audit, result)

    with pytest.raises(audit.AuditNotPassed) as raised:
        audit.require_passed_audit(
            example_index, examples / "example", question_set="example", sets_dir=SETS
        )
    assert raised.value.result.outcome is audit.AuditOutcome.FAILED
    assert raised.value.result.question_set_version == "example"


def test_without_a_question_set_the_result_is_the_result_of_spec_1(example_index, examples):
    """FR-008: "An audit that names no question set MUST keep checking every question of
    every question part, as it does today". The three fields are `None`, and the document
    has no key for them."""
    audit = load_audit()

    result = audit.audit_index(example_index, examples / "example")

    assert result.outcome is audit.AuditOutcome.PASSED
    for field in THREE_FIELDS:
        assert getattr(result, field) is None, field
    assert result.to_document()["question_set"] == {
        "description": "every question of the question parts",
        "parts": ["exq"],
        "questions": 3,
    }


def test_a_question_set_of_the_caller_still_names_no_set(example_index, examples):
    """contracts/audit-gate.md: the argument `questions` of spec 1 stays for callers that
    bring their own pairs; its result names no set."""
    audit = load_audit()

    result = audit.audit_index(
        example_index, examples / "example", questions=[("own-question", ["ex-005"])]
    )

    assert result.outcome is audit.AuditOutcome.PASSED
    for field in THREE_FIELDS:
        assert getattr(result, field) is None, field
    assert set(result.to_document()["question_set"]) == {"description", "parts", "questions"}


def test_without_a_sets_directory_the_set_is_read_from_evals_golden(
    example_index, build_root, examples
):
    """contracts/audit-gate.md: "`sets_dir`: where the record is read; without it,
    `evals/golden`", below the current directory, which is the temporary repository root."""
    audit = load_audit()
    golden = build_root.root / "evals" / "golden"
    golden.mkdir(parents=True)
    shutil.copyfile(SETS / "example.json", golden / "example.json")

    result = audit.audit_index(example_index, examples / "example", question_set="example")

    assert result.outcome is audit.AuditOutcome.PASSED
    assert_names_the_example_set(audit, result)


# --- The gate: not carried out (step 4a) --------------------------------------------------------


@pytest.mark.parametrize("version", ["no-such-set", "Not_A_Version"])
def test_a_set_that_does_not_exist_is_not_carried_out(example_index, examples, version):
    """contracts/cli.md, "`index audit`": "The record `V` does not exist, or `V` is not a
    valid version": `question set <V> does not exist in <sets directory>`. The audit returns
    `NOT_CARRIED_OUT` with the reason and does not raise; the gate raises `AuditNotPassed`,
    which carries the result."""
    audit = load_audit()

    result = audit.audit_index(
        example_index, examples / "example", question_set=version, sets_dir=SETS
    )

    reason = assert_not_carried_out(audit, result)
    assert reason == f"question set {version} does not exist in {SETS.as_posix()}"

    with pytest.raises(audit.AuditNotPassed) as raised:
        audit.require_passed_audit(
            example_index, examples / "example", question_set=version, sets_dir=SETS
        )
    assert raised.value.result.outcome is audit.AuditOutcome.NOT_CARRIED_OUT
    assert raised.value.result.reason == reason


def test_a_set_of_another_dataset_is_not_carried_out(example_index, examples):
    """FR-008: "An audit that names a question set which does not pass its check against the
    same dataset MUST end as not carried out." contracts/cli.md: `question set <V> does not
    match the dataset of <DIR>`. The set `harness` was produced from `tests/data/harness`."""
    audit = load_audit()
    data_dir = examples / "example"

    result = audit.audit_index(example_index, data_dir, question_set="harness", sets_dir=SETS)

    reason = assert_not_carried_out(audit, result)
    assert reason == f"question set harness does not match the dataset of {data_dir.as_posix()}"

    with pytest.raises(audit.AuditNotPassed) as raised:
        audit.require_passed_audit(example_index, data_dir, question_set="harness", sets_dir=SETS)
    assert raised.value.result.outcome is audit.AuditOutcome.NOT_CARRIED_OUT
    assert raised.value.result.reason == reason


def test_a_set_that_no_longer_matches_its_own_dataset_is_not_carried_out(
    example_index, examples, tmp_path
):
    """The same for a set of the right dataset whose record does not pass its check: the
    record `example` with other gold articles for `exq-003` than the dataset gives."""
    audit = load_audit()
    document = json.loads((SETS / "example.json").read_text(encoding="utf-8"))
    document["questions"][2]["article_ids"] = ["ex-005"]
    text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    (tmp_path / "example.json").write_text(text, encoding="utf-8")

    result = audit.audit_index(
        example_index, examples / "example", question_set="example", sets_dir=tmp_path
    )

    reason = assert_not_carried_out(audit, result)
    assert "question set example does not match the dataset" in reason


def test_the_index_and_the_dataset_are_looked_at_before_the_set(store, build_root, examples):
    """contracts/cli.md: step 4a is "added after the dataset check"; the order of spec 1's
    steps stays. An index that does not exist and a data directory that fails the dataset
    check are reported before a set that does not exist."""
    audit = load_audit()
    absent = store.new_index()

    result = audit.audit_index(
        absent, examples / "example", question_set="no-such-set", sets_dir=SETS
    )

    reason = assert_not_carried_out(audit, result)
    assert absent in reason and "does not exist" in reason
    assert "question set" not in reason


def test_the_dataset_check_comes_before_the_set(example_index, examples):
    """The same order for step 4, the dataset check, and step 4a."""
    audit = load_audit()

    result = audit.audit_index(
        example_index, examples / "example-damaged", question_set="no-such-set", sets_dir=SETS
    )

    reason = assert_not_carried_out(audit, result)
    assert "dataset check failed" in reason


def test_the_call_with_a_set_changes_neither_the_store_nor_a_record(
    store, example_index, examples, tmp_path
):
    """contracts/audit-gate.md, rule 3: "The call changes nothing: not the store, not the
    data directory, not a record." The sets directory is a copy, so that a change would
    not reach the checkout."""
    audit = load_audit()
    sets_dir = tmp_path / "sets"
    shutil.copytree(SETS, sets_dir)
    sets_before = files_of(sets_dir)
    data_before = files_of(examples / "example")
    passages_before = store.passages(example_index)

    audit.audit_index(
        example_index, examples / "example", question_set="example", sets_dir=sets_dir
    )
    audit.audit_index(
        example_index, examples / "example", question_set="harness", sets_dir=sets_dir
    )
    audit.audit_index(example_index, examples / "example", question_set="absent", sets_dir=sets_dir)

    assert files_of(sets_dir) == sets_before
    assert files_of(examples / "example") == data_before
    assert store.passages(example_index) == passages_before


# --- The command `index audit --set` ------------------------------------------------------------


def test_the_command_prints_the_line_of_the_question_set_after_the_revision(
    example_index, build_root, examples, run_command
):
    """contracts/cli.md, "`index audit`: the options `--set` and `--sets-dir`": "The report
    gains one line, after `revision:` and before `questions:`"; `questions:` is the number
    of questions of the set; the result file names the set (AC-010 reads four of these
    lines)."""
    result = audit_command(
        run_command,
        build_root.root,
        example_index,
        "--data-dir",
        examples / "example",
        "--json result.json --sets-dir",
        SETS,
        "--set example",
    )

    assert result.exit_code == 0, result.stdout
    assert result.lines == [
        f"index: {example_index}",
        "dataset: example",
        "revision: none",
        "question set: example (golden)",
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
    assert document["question_set"] == {
        "description": "question set example (golden)",
        "parts": ["exq"],
        "questions": 3,
        "version": "example",
        "role": "golden",
        "fingerprint": EXAMPLE_FINGERPRINT,
    }
    assert list(document["question_set"]) == [
        "description",
        "parts",
        "questions",
        "version",
        "role",
        "fingerprint",
    ]
    assert document["outcome"] == "passed"


def test_the_command_without_set_prints_the_report_of_spec_1(
    example_index, build_root, examples, run_command
):
    """contracts/cli.md: "Without it the command is exactly the command of spec 1": no line
    `question set:`, and a result file without the three fields."""
    result = audit_command(
        run_command,
        build_root.root,
        example_index,
        "--data-dir",
        examples / "example",
        "--json result.json",
    )

    assert result.exit_code == 0, result.stdout
    assert not any(line.startswith("question set:") for line in result.lines)
    assert result.lines[2:4] == ["revision: none", "questions: 3"]
    document = json.loads((build_root.root / "result.json").read_text(encoding="utf-8"))
    assert document["question_set"] == {
        "description": "every question of the question parts",
        "parts": ["exq"],
        "questions": 3,
    }


def test_the_command_with_a_set_and_a_failed_audit_names_the_question_of_the_set(
    store, example_index, build_root, examples, run_command
):
    """FR-008 and contracts/cli.md: "the question references checked are those of the set".
    An article that `exq-003` names is removed in the store; the audit fails with exit code
    1 and lists the pair."""
    assert store.remove_passages_of(example_index, "ex-004") > 0

    result = audit_command(
        run_command,
        build_root.root,
        example_index,
        "--data-dir",
        examples / "example",
        "--sets-dir",
        SETS,
        "--set example",
    )

    assert result.exit_code == 1, result.stdout
    assert "question set: example (golden)" in result.lines
    assert "unknown question references: 1" in result.lines
    assert "  exq-003 -> ex-004" in result.lines
    assert result.last_line == "audit: failed"


@pytest.mark.parametrize("version", ["no-such-set", "Not_A_Version"])
def test_the_command_does_not_audit_with_a_set_that_does_not_exist(
    example_index, build_root, examples, run_command, version
):
    """contracts/cli.md, the table of `--set`: `reason: question set <V> does not exist in
    <sets directory>`, `audit: not carried out`, exit code 2, and no result file."""
    result = audit_command(
        run_command,
        build_root.root,
        example_index,
        "--data-dir",
        examples / "example",
        "--json result.json --sets-dir",
        SETS,
        "--set",
        version,
    )

    reason = assert_not_carried_out_line(result)
    assert reason == f"question set {version} does not exist in {SETS.as_posix()}"
    assert not (build_root.root / "result.json").exists()
    assert build_root.files_below("data/audits") == {}


def test_the_command_does_not_audit_with_a_set_of_another_dataset(
    example_index, build_root, examples, run_command
):
    """contracts/cli.md, the table of `--set`: "the `difference:` lines of that check, then
    `reason: question set <V> does not match the dataset of <DIR>`", `audit: not carried
    out`, exit code 2, and no result file (AC-011)."""
    data_dir = examples / "example"

    result = audit_command(
        run_command,
        build_root.root,
        example_index,
        "--data-dir",
        data_dir,
        "--json result.json --sets-dir",
        SETS,
        "--set harness",
    )

    reason = assert_not_carried_out_line(result)
    assert reason == f"question set harness does not match the dataset of {data_dir.as_posix()}"
    assert result.differences, "the differences of the check of the set stand before the reason"
    assert "audit: failed" not in result.lines and "audit: passed" not in result.lines
    assert not (build_root.root / "result.json").exists()
    assert build_root.files_below("data/audits") == {}


@pytest.mark.parametrize(
    "options",
    [
        f"--sets-dir {SETS.as_posix()}",
        "--sets-dir evals/golden",
        "--set",
        "--set example --sets-dir",
        "--set example --set harness-hxc extra-argument",
    ],
    ids=[
        "--sets-dir without --set",
        "--sets-dir evals/golden without --set",
        "--set without its value",
        "--sets-dir without its value",
        "an argument too many",
    ],
)
def test_wrong_arguments_of_the_two_options_end_as_not_carried_out(
    example_index, build_root, examples, run_command, options
):
    """contracts/cli.md: "`--sets-dir` without `--set` is a wrong argument"; "General
    rules": a `reason:` line, the verdict `audit: not carried out`, exit code 2. Nothing is
    audited, and no result is written."""
    result = audit_command(
        run_command,
        build_root.root,
        example_index,
        "--data-dir",
        examples / "example",
        "--json result.json",
        options,
    )

    assert_not_carried_out_line(result)
    assert not any(line.startswith("index:") for line in result.lines)
    assert not (build_root.root / "result.json").exists()
