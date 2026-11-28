"""The check of a run record (task T080): `summary_document` and `examine` of
`src/wixqa_rag/runs.py`.

Covers:

- spec.md, FR-020 to FR-023 and FR-035, and SC-004 and SC-006;
- data-model.md, "Run record" and "Check of a run record": the differences 1 to 16, with
  the cases that no acceptance check reads; "every difference that can still be found is
  reported"; a further field of an entry is ignored;
- contracts/cli.md, "`run check`": the wording of a difference as far as the contract fixes
  it;
- contracts/harness.md, "`wixqa_rag.runs`": the names below, and no other.

    summary_document(run_document, question_set, entries, audit_document) -> dict
    examine(run, runs_dir=None, sets_dir=None) -> RunExamination
    RunExamination                         # run_id, differences, question_set, role,
                                           # run_document, entries, summary
    RunNotFound

Every test works on a temporary copy of the example registries, the fixture `registry_copy`
of tests/conftest.py: a temporary repository root with `data/sets`, `data/runs` and
`data/runs-invalid`. A test changes the copies by hand, without code of the package, and no
file of the checkout. Where the contract leaves the wording of a difference free, a test
reads only that a difference names the question, the field, the run or the parameter
concerned. All documents named here are in specs/002-evaluation-harness/.
"""

import hashlib
import importlib
import json
import re
import shutil

import pytest

RUN_A = "20261101T100000Z-example-a"
RUN_B = "20261102T100000Z-example-b"
RUN_C = "20261103T100000Z-example-c"
RUN_D = "20261104T100000Z-example-d"
SOUND = {RUN_A: "harness", RUN_B: "harness", RUN_C: "harness-hxc", RUN_D: "harness-hxc"}
ROLES = {"harness": "golden", "harness-hxc": "held-out"}

# data-model.md, "`tests/data/runs-invalid/`": the difference that the check names for each
# of the seven records, in the wording of contracts/cli.md, "`run check`".
DEFECTS = {
    "20261101T100100Z-no-latency": "hxa-003 lacks the field latency_seconds",
    "20261101T100200Z-missing-question": (
        "hxb-003 is a question of the question set and has no entry"
    ),
    "20261101T100300Z-unknown-status": (
        "hxa-004 has the status skipped, which is not one of the five"
    ),
    "20261101T100400Z-wrong-hash": (
        "hxa-001 has an answer_sha256 that is not the hash of its answer"
    ),
    "20261101T100500Z-stale-summary": (
        "the summary states all_found 3 for the generation list, all questions; the results give 2"
    ),
    "20261101T100600Z-two-changes": (
        f"the config differs from the baseline {RUN_A} in retrieval.top_k, "
        "which is not the parameter the experiment names"
    ),
    "20261103T100100Z-experiment-on-held-out": (
        "the run is an experiment on the held-out set harness-hxc; "
        "an experiment run is made on a golden set"
    ),
}
# data-model.md: these three "have exactly the one difference".
EXACTLY_ONE = (
    "20261101T100400Z-wrong-hash",
    "20261101T100600Z-two-changes",
    "20261103T100100Z-experiment-on-held-out",
)


def load_runs():
    """Import the module; it fails while `src/wixqa_rag/runs.py` does not exist (plan.md,
    "Project Structure")."""
    return importlib.import_module("wixqa_rag.runs")


@pytest.fixture
def examine(registry_copy, monkeypatch):
    """`examine` for a run of the temporary copy `data/runs`, or of another registry of the
    copy; the current directory is the temporary repository root."""
    monkeypatch.chdir(registry_copy.root)

    def of(run: str, registry=None):
        runs_dir = registry_copy.runs_dir if registry is None else registry
        return load_runs().examine(run, runs_dir, registry_copy.sets_dir)

    return of


@pytest.fixture
def differences(examine):
    """The differences of a run of `data/runs`, as a list of texts."""

    def of(run: str, registry=None) -> list[str]:
        return list(examine(run, registry).differences)

    return of


def names(text: str, word: str) -> bool:
    """Whether a text holds a word as a word of its own."""
    return re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", text) is not None


def naming(found: list[str], *words: str) -> list[str]:
    """The differences that name every one of the words."""
    return [text for text in found if all(names(text, word) for word in words)]


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- `summary_document` (FR-017, FR-021) -------------------------------------------------------


@pytest.mark.parametrize("run", SOUND)
def test_summary_document_gives_exactly_the_summary_of_a_sound_record(registry_copy, run):
    """tasks.md, T080, and contracts/harness.md: "The whole document of `summary.json`:
    `run_id`, `question_set` and `questions` from the first two arguments, `audit` as given,
    and the three keys of `metrics.summarize`." Written as contracts/records.md says, it has
    the bytes of the file."""
    questionsets = importlib.import_module("wixqa_rag.questionsets")
    question_set = questionsets.read(SOUND[run], registry_copy.sets_dir)
    recorded = registry_copy.summary(run)

    document = load_runs().summary_document(
        registry_copy.run_document(run), question_set, registry_copy.entries(run), recorded["audit"]
    )

    assert document == recorded
    text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    assert text.encode("utf-8") == registry_copy.file(run, "summary.json").read_bytes()


def test_summary_document_takes_the_audit_as_it_is_given(registry_copy):
    """contracts/harness.md: "`audit` as given": the function does not make, check or change
    the audit result; spec 3 passes the result of the gate."""
    questionsets = importlib.import_module("wixqa_rag.questionsets")
    question_set = questionsets.read("harness", registry_copy.sets_dir)
    audit = {"index": "another-index", "outcome": "passed", "note": "as given"}

    document = load_runs().summary_document(
        registry_copy.run_document(RUN_A), question_set, registry_copy.entries(RUN_A), audit
    )

    assert document["audit"] == audit
    assert list(document) == [
        "run_id",
        "question_set",
        "questions",
        "audit",
        "breakdowns",
        "retrieval_misses",
        "questions_without_gold_articles",
    ]
    assert document["run_id"] == RUN_A
    assert document["questions"] == 8
    assert document["question_set"] == {
        "version": "harness",
        "role": "golden",
        "fingerprint": question_set.fingerprint,
    }


def test_summary_document_writes_nothing_and_changes_no_argument(registry_copy):
    """contracts/harness.md, "Rules", 2: no function changes a file that exists; writing the
    files of a run is the task of spec 3."""
    questionsets = importlib.import_module("wixqa_rag.questionsets")
    question_set = questionsets.read("harness", registry_copy.sets_dir)
    run_document = registry_copy.run_document(RUN_A)
    entries = registry_copy.entries(RUN_A)
    audit = registry_copy.summary(RUN_A)["audit"]
    before = registry_copy.files()

    load_runs().summary_document(run_document, question_set, entries, audit)

    assert registry_copy.files() == before
    assert run_document == registry_copy.run_document(RUN_A)
    assert entries == registry_copy.entries(RUN_A)
    assert audit == registry_copy.summary(RUN_A)["audit"]


# --- Records that pass --------------------------------------------------------------------------


@pytest.mark.parametrize("run", SOUND)
def test_examine_finds_no_difference_in_a_sound_record(registry_copy, examine, run):
    """tasks.md, T080: `examine` finds no difference in the four sound records.
    contracts/harness.md, `RunExamination`: the fields of the outcome."""
    examination = examine(run)

    assert list(examination.differences) == []
    assert examination.run_id == run
    assert examination.role == ROLES[SOUND[run]]
    assert examination.question_set.version == SOUND[run]
    assert examination.run_document == registry_copy.run_document(run)
    assert list(examination.entries) == registry_copy.entries(run)
    assert examination.summary == registry_copy.summary(run)


@pytest.mark.parametrize("run", [RUN_A, RUN_C])
def test_the_sound_records_of_the_invalid_registry_pass_as_well(registry_copy, examine, run):
    """data-model.md: `runs-invalid` holds two sound records, byte for byte those of `runs`."""
    assert list(examine(run, registry_copy.runs_invalid_dir).differences) == []


def test_examine_changes_no_file(registry_copy, examine):
    """FR-026: no command of this feature changes a run record or a question-set record."""
    before = registry_copy.files()

    for run in SOUND:
        examine(run)
    for run in DEFECTS:
        examine(run, registry_copy.runs_invalid_dir)

    assert registry_copy.files() == before


def test_without_directories_examine_reads_evals_runs_and_evals_golden(registry_copy, monkeypatch):
    """contracts/harness.md, `examine`: "Without `runs_dir`, in `evals/runs`"; the default
    sets directory is `evals/golden` (contracts/cli.md, "Directories"). Both lie below the
    current directory, which stands for the repository root."""
    shutil.copytree(registry_copy.runs_dir / RUN_C, registry_copy.root / "evals" / "runs" / RUN_C)
    golden = registry_copy.root / "evals" / "golden"
    golden.mkdir(parents=True)
    shutil.copyfile(registry_copy.sets_dir / "harness-hxc.json", golden / "harness-hxc.json")
    monkeypatch.chdir(registry_copy.root)

    examination = load_runs().examine(RUN_C)

    assert list(examination.differences) == []
    assert examination.role == "held-out"


# --- The seven records with one defect each ------------------------------------------------------


@pytest.mark.parametrize("run", DEFECTS)
def test_a_record_with_one_defect_gives_the_difference_of_the_table(
    registry_copy, differences, run
):
    """data-model.md, "`tests/data/runs-invalid/`", the column "The difference the check
    names", in the wording of contracts/cli.md, "`run check`"."""
    found = differences(run, registry_copy.runs_invalid_dir)

    assert DEFECTS[run] in found, found


@pytest.mark.parametrize("run", EXACTLY_ONE)
def test_three_of_the_records_have_exactly_the_one_difference(registry_copy, differences, run):
    """data-model.md: "`wrong-hash`, `two-changes` and `experiment-on-held-out` have exactly
    the one difference"."""
    assert differences(run, registry_copy.runs_invalid_dir) == [DEFECTS[run]]


def test_the_stale_summary_has_no_other_difference(registry_copy, differences):
    """data-model.md, `stale-summary`: the one change is `all_found` 3 where the results give
    2. "Each number is reported on its own" (difference 12), and no other number differs."""
    found = differences("20261101T100500Z-stale-summary", registry_copy.runs_invalid_dir)

    assert found == [DEFECTS["20261101T100500Z-stale-summary"]]


# --- Difference 1: a file is missing or cannot be read --------------------------------------------


@pytest.mark.parametrize(
    ("name", "field"),
    [("run.json", "run_document"), ("results.jsonl", "entries"), ("summary.json", "summary")],
)
def test_difference_1_a_file_that_is_missing(registry_copy, examine, name, field):
    """data-model.md, difference 1: "One of the three files is missing". The check does not
    raise; the difference names the file, and the field of the outcome is `None`
    (contracts/harness.md, `RunExamination`: "each `None` when its file could not be read")."""
    registry_copy.file(RUN_A, name).unlink()

    examination = examine(RUN_A)

    assert any(name in text for text in examination.differences), list(examination.differences)
    assert getattr(examination, field) is None
    assert examination.run_id == RUN_A


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("run.json", b"\xff\xfe not UTF-8"),
        ("run.json", b"this is not JSON\n"),
        ("run.json", b'["a", "list"]\n'),
        ("results.jsonl", b"\xff\xfe not UTF-8\n"),
        ("results.jsonl", b"this is not JSON\n"),
        ("results.jsonl", b'["a", "list"]\n'),
        ("summary.json", b"this is not JSON\n"),
        ("summary.json", b'"a text"\n'),
    ],
    ids=[
        "run.json is not UTF-8",
        "run.json is not JSON",
        "run.json is a JSON list",
        "results.jsonl is not UTF-8",
        "a line of results.jsonl is not JSON",
        "a line of results.jsonl is a JSON list",
        "summary.json is not JSON",
        "summary.json is a JSON text",
    ],
)
def test_difference_1_a_file_that_is_not_of_the_stated_form(registry_copy, examine, name, content):
    """data-model.md, difference 1: a file "is not UTF-8, or is not JSON of the stated
    form". The difference names the file."""
    registry_copy.file(RUN_A, name).write_bytes(content)

    found = list(examine(RUN_A).differences)

    assert any(name in text for text in found), found


def test_difference_1_one_line_of_the_results_that_is_not_json(registry_copy, differences):
    """The same for one line among sound lines: the last line is cut off, as a run that
    stopped would leave it."""
    file = registry_copy.file(RUN_A, "results.jsonl")
    file.write_bytes(file.read_bytes()[:-40])

    found = differences(RUN_A)

    assert any("results.jsonl" in text for text in found), found


def test_a_file_that_cannot_be_read_does_not_hide_the_other_differences(registry_copy, differences):
    """data-model.md: "A file that cannot be read stops the examination of what depends on
    it; every difference that can still be found is reported." Without the summary the hash
    of an answer is still compared."""
    registry_copy.file(RUN_A, "summary.json").unlink()
    registry_copy.change_entries(RUN_A, lambda rows: rows[0].update(answer_sha256="0" * 64))

    found = differences(RUN_A)

    assert any("summary.json" in text for text in found), found
    assert "hxa-001 has an answer_sha256 that is not the hash of its answer" in found


# --- Difference 2: a field is absent or has the wrong type ---------------------------------------


@pytest.mark.parametrize(
    "field", ["run_id", "started_at", "commit", "uncommitted_changes", "config"]
)
def test_difference_2_a_field_of_run_json_that_is_absent(registry_copy, differences, field):
    """data-model.md, difference 2, and "Identity and config": the five fields of
    `run.json`."""
    registry_copy.change_run(RUN_A, lambda document: document.pop(field))

    assert naming(differences(RUN_A), field), differences(RUN_A)


@pytest.mark.parametrize(
    "field",
    [
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
    ],
)
def test_difference_2_a_field_of_the_config_that_is_absent(registry_copy, differences, field):
    """data-model.md, "Identity and config": "All thirteen fields are required", also
    `seeds`, which may be empty, and `experiment`, which may be `null`."""
    registry_copy.change_run(RUN_A, lambda document: document["config"].pop(field))

    assert naming(differences(RUN_A), field), differences(RUN_A)


@pytest.mark.parametrize(
    ("change", "field"),
    [
        (lambda d: d.update(uncommitted_changes="no"), "uncommitted_changes"),
        (lambda d: d.update(commit="0123456"), "commit"),
        (lambda d: d.update(commit="0123456789ABCDEF0123456789ABCDEF01234567"), "commit"),
        (lambda d: d.update(started_at=1793527200), "started_at"),
        (lambda d: d["config"].update(index=7), "index"),
        (lambda d: d["config"].update(retrieval=["top_k", 3]), "retrieval"),
        (lambda d: d["config"].update(seeds=None), "seeds"),
        (lambda d: d["config"].update(models="example-model"), "models"),
        (lambda d: d["config"].update(concurrency=0), "concurrency"),
        (lambda d: d["config"].update(concurrency="1"), "concurrency"),
        (lambda d: d["config"]["limits"].update(timeout_seconds=0), "timeout_seconds"),
        (lambda d: d["config"]["limits"].update(max_calls=0), "max_calls"),
        (lambda d: d["config"]["limits"].pop("max_calls"), "max_calls"),
        (lambda d: d["config"]["dataset"].pop("revision"), "revision"),
        (lambda d: d["config"]["question_set"].pop("role"), "role"),
        (lambda d: d["config"].update(prices={"example-model": 1.0}), "prices"),
        (lambda d: d["config"].update(experiment="none"), "experiment"),
    ],
    ids=[
        "uncommitted_changes is a text",
        "commit is not a full hash",
        "commit is in upper case",
        "started_at is a number",
        "index is a number",
        "retrieval is a list",
        "seeds is null",
        "models is a text",
        "concurrency is 0",
        "concurrency is a text",
        "timeout_seconds is 0",
        "max_calls is 0",
        "max_calls is absent",
        "dataset.revision is absent",
        "question_set.role is absent",
        "prices is an object",
        "experiment is a text",
    ],
)
def test_difference_2_a_field_of_run_json_of_the_wrong_type(
    registry_copy, differences, change, field
):
    """data-model.md, difference 2, with the types and the rules of "Identity and config":
    a full commit hash in lower case, a boolean, an object for each of the six fields that
    spec 3 fixes, limits above 0, a concurrency of at least 1."""
    registry_copy.change_run(RUN_A, change)

    assert naming(differences(RUN_A), field), differences(RUN_A)


def test_difference_2_a_model_that_has_two_prices(registry_copy, differences):
    """data-model.md, `prices`: "No model occurs twice"."""
    registry_copy.change_run(
        RUN_A, lambda d: d["config"]["prices"].append(dict(d["config"]["prices"][0]))
    )

    assert naming(differences(RUN_A), "example-model"), differences(RUN_A)


@pytest.mark.parametrize(
    "field",
    [
        "status",
        "retrieved_list",
        "generation_list",
        "context",
        "answer",
        "answer_sha256",
        "tokens",
        "cost_usd",
    ],
)
def test_difference_2_a_field_of_an_entry_that_is_absent(registry_copy, differences, field):
    """data-model.md, "Results", rule 4: "The ten fields above are required: a field that is
    absent is a defect". contracts/cli.md: `<question> lacks the field <field>`. AC-021
    reads this for `latency_seconds`."""
    registry_copy.change_entries(RUN_A, lambda rows: rows[5].pop(field))

    assert f"hxb-001 lacks the field {field}" in differences(RUN_A)


@pytest.mark.parametrize(
    ("change", "field"),
    [
        (lambda row: row.update(latency_seconds="fast"), "latency_seconds"),
        (lambda row: row.update(latency_seconds=-1.0), "latency_seconds"),
        (lambda row: row.update(latency_seconds=None), "latency_seconds"),
        (lambda row: row.update(cost_usd="0.0012"), "cost_usd"),
        (lambda row: row.update(tokens=None), "tokens"),
        (lambda row: row.update(tokens={"example-model": 1000}), "tokens"),
        (lambda row: row["tokens"][0].update(input_tokens=-1), "input_tokens"),
        (lambda row: row["tokens"][0].update(output_tokens=1.5), "output_tokens"),
        (lambda row: row["tokens"][0].pop("output_tokens"), "output_tokens"),
        (lambda row: row.update(context=17), "context"),
        (lambda row: row.update(status=None), "status"),
    ],
    ids=[
        "the latency is a text",
        "the latency is below 0",
        "the latency is null",
        "the cost is a text",
        "tokens is null",
        "tokens is an object",
        "a token count below 0",
        "a token count that is not whole",
        "a token count that is absent",
        "the context is a number",
        "the status is null",
    ],
)
def test_difference_2_a_field_of_an_entry_of_the_wrong_type(
    registry_copy, differences, change, field
):
    """data-model.md, difference 2, with the types of "Results": a latency of 0 or more,
    token counts that are whole numbers of 0 or more, `null` "only where the table says so"."""
    registry_copy.change_entries(RUN_A, lambda rows: change(rows[0]))

    assert naming(differences(RUN_A), "hxa-001", field), differences(RUN_A)


@pytest.mark.parametrize(
    "field",
    [
        "run_id",
        "question_set",
        "questions",
        "audit",
        "breakdowns",
        "retrieval_misses",
        "questions_without_gold_articles",
    ],
)
def test_difference_2_a_field_of_the_summary_that_is_absent(registry_copy, differences, field):
    """data-model.md, difference 2, and "Summary": the seven fields of `summary.json`."""
    registry_copy.change_summary(RUN_A, lambda document: document.pop(field))

    assert naming(differences(RUN_A), field), differences(RUN_A)


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["breakdowns"].pop("multi_article"),
        lambda d: d["breakdowns"]["all"].pop("latency_seconds"),
        lambda d: d["breakdowns"]["all"]["status"].pop("timeout"),
        lambda d: d["breakdowns"]["single_article"]["retrieved_list"].pop("share_all_found"),
        lambda d: d["breakdowns"].update(all="eight questions"),
    ],
    ids=[
        "a breakdown is absent",
        "the latency of a breakdown is absent",
        "the count of a status is absent",
        "a number of a list is absent",
        "a breakdown is a text",
    ],
)
def test_difference_2_a_part_of_a_breakdown_that_is_absent(registry_copy, differences, change):
    """data-model.md, "One breakdown": the six fields of each of the three breakdowns."""
    registry_copy.change_summary(RUN_A, change)

    assert differences(RUN_A), "a summary without a required part does not pass"


# --- Difference 3: the run identifier -------------------------------------------------------------


def test_difference_3_a_run_id_that_is_not_the_name_of_the_directory(registry_copy, differences):
    """data-model.md, difference 3: `run_id` "is not the name of the directory". The
    directory is `example-a`; the record names another, valid identifier."""
    other = "20261101T100000Z-another-name"
    registry_copy.change_run(RUN_A, lambda document: document.update(run_id=other))
    registry_copy.change_summary(RUN_A, lambda document: document.update(run_id=other))

    found = differences(RUN_A)

    assert naming(found, other) or naming(found, "run_id"), found


def test_difference_3_a_run_id_that_is_not_a_run_identifier(registry_copy, differences):
    """data-model.md, difference 3: "`run_id` is not a run identifier"."""
    registry_copy.change_run(RUN_A, lambda document: document.update(run_id="example-a"))

    assert naming(differences(RUN_A), "run_id") or naming(differences(RUN_A), "example-a")


@pytest.mark.parametrize(
    "started_at",
    ["2026-11-01T10:00:01Z", "2026-11-02T10:00:00Z", "2026-11-01T09:59:59Z", "yesterday"],
)
def test_difference_3_a_start_time_that_the_run_id_does_not_state(
    registry_copy, differences, started_at
):
    """data-model.md, difference 3: the time part of `run_id` "is not `started_at`"; FR-022:
    the run identifier "does not agree with the recorded start time". `started_at` is in
    UTC in the form `2026-11-01T10:00:00Z` (contracts/records.md)."""
    registry_copy.change_run(RUN_A, lambda document: document.update(started_at=started_at))

    assert naming(differences(RUN_A), "started_at"), differences(RUN_A)


# --- Difference 4: the question set of the config -------------------------------------------------


def test_difference_4_a_question_set_that_is_not_in_the_sets_directory(registry_copy, examine):
    """data-model.md, difference 4; contracts/cli.md: `question set <V> does not exist in
    <sets directory>`. The set could not be read, so the outcome has none."""
    (registry_copy.sets_dir / "harness-hxc.json").unlink()

    examination = examine(RUN_C)

    assert (
        f"question set harness-hxc does not exist in {registry_copy.sets_dir.as_posix()}"
        in examination.differences
    )
    assert examination.question_set is None
    assert examination.role == "held-out", "the role is that of the record's config"


def test_difference_4_a_role_that_differs_from_the_record_of_the_set(registry_copy, differences):
    """data-model.md, difference 4; contracts/cli.md: `the config records the <role or
    fingerprint> <x> for question set <V>, its record has <y>`."""
    registry_copy.change_run(
        RUN_A, lambda document: document["config"]["question_set"].update(role="held-out")
    )

    assert (
        "the config records the role held-out for question set harness, its record has golden"
        in differences(RUN_A)
    )


def test_difference_4_a_fingerprint_that_differs_from_the_record_of_the_set(
    registry_copy, differences
):
    """The same for the fingerprint: the record of the set changed after the run, here by
    one more line feed at its end, so the run names bytes that are no longer there."""
    file = registry_copy.sets_dir / "harness.json"
    recorded = hashlib.sha256(file.read_bytes()).hexdigest()
    file.write_bytes(file.read_bytes() + b"\n")
    present = hashlib.sha256(file.read_bytes()).hexdigest()

    assert (
        f"the config records the fingerprint {recorded} for question set harness, "
        f"its record has {present}"
    ) in differences(RUN_A)


def test_the_check_does_not_repeat_the_check_of_the_set_against_the_dataset(
    registry_copy, differences
):
    """research.md, section 10: the check of a run record "compares the config's question
    set with the record of the set (version, role, fingerprint). It does not repeat the check
    of the set against the dataset": the temporary root holds no data directory at all."""
    assert not (registry_copy.root / "data" / "harness").exists()

    assert differences(RUN_A) == []


# --- Difference 5: one entry per question ---------------------------------------------------------


def test_difference_5_an_entry_for_a_question_outside_the_set(registry_copy, differences):
    """data-model.md, difference 5; contracts/cli.md: `<question> has an entry and is not a
    question of the question set`."""
    entry = registry_copy.entries(RUN_C)[0]
    registry_copy.change_entries(RUN_A, lambda rows: rows.append(entry))

    assert "hxc-001 has an entry and is not a question of the question set" in differences(RUN_A)


def test_difference_5_a_question_with_two_entries(registry_copy, differences):
    """data-model.md, difference 5: "a question has two entries"."""
    registry_copy.change_entries(RUN_A, lambda rows: rows.insert(2, dict(rows[1])))

    assert naming(differences(RUN_A), "hxa-002"), differences(RUN_A)


def test_difference_5_every_question_without_an_entry_is_named(registry_copy, differences):
    """FR-022: the check names every defect: two questions of the set have no entry."""

    def change(rows):
        del rows[6]
        del rows[0]

    registry_copy.change_entries(RUN_A, change)

    found = differences(RUN_A)
    assert "hxa-001 is a question of the question set and has no entry" in found
    assert "hxb-002 is a question of the question set and has no entry" in found


# --- Difference 7: the lists and the rules across fields ------------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("retrieved_list", ["hx-001", ""]),
        ("retrieved_list", ["hx-001", 2]),
        ("retrieved_list", "hx-001"),
        ("generation_list", [None]),
        ("generation_list", [["hx-001"]]),
        ("generation_list", {"hx-001": 1}),
    ],
    ids=[
        "an empty text in the retrieved list",
        "a number in the retrieved list",
        "the retrieved list is a text",
        "null in the generation list",
        "a list in the generation list",
        "the generation list is an object",
    ],
)
def test_difference_7_a_list_that_holds_something_other_than_an_article_id(
    registry_copy, differences, field, value
):
    """data-model.md, difference 7: "A list is neither `null` nor a list of non-empty
    strings"; FR-022: "a list holds something that is not an article id"."""
    registry_copy.change_entries(RUN_A, lambda rows: rows[0].update({field: value}))

    assert naming(differences(RUN_A), "hxa-001"), differences(RUN_A)


@pytest.mark.parametrize(
    ("row", "question", "change"),
    [
        (0, "hxa-001", {"generation_list": None}),
        (0, "hxa-001", {"retrieved_list": None, "generation_list": None}),
        (0, "hxa-001", {"answer": None, "answer_sha256": None}),
        (3, "hxa-004", {"generation_list": None}),
        (3, "hxa-004", {"answer": None, "answer_sha256": None}),
    ],
    ids=[
        "answered without a generation list",
        "answered without either list",
        "answered without an answer",
        "no_answer without a generation list",
        "no_answer without an answer",
    ],
)
def test_difference_7_an_answered_entry_without_a_list_or_an_answer(
    registry_copy, differences, row, question, change
):
    """data-model.md, "Results", rule 1, and FR-020: "A question with the status `answered`
    or `no_answer` has both lists and an answer"."""
    registry_copy.change_entries(RUN_A, lambda rows: rows[row].update(change))

    assert naming(differences(RUN_A), question), differences(RUN_A)


def test_difference_7_a_generation_list_without_a_retrieved_list(registry_copy, differences):
    """data-model.md, "Results", rule 2: "A question with a `generation_list` has a
    `retrieved_list`". `hxb-002` has the status `call_limit` and an empty generation list."""
    registry_copy.change_entries(RUN_A, lambda rows: rows[6].update(retrieved_list=None))

    assert naming(differences(RUN_A), "hxb-002"), differences(RUN_A)


def test_an_entry_that_failed_may_lack_both_lists_and_the_answer(registry_copy, differences):
    """The counterpart: rule 1 holds for `answered` and `no_answer` only. In `example-a` the
    entry of `hxa-005` (`error`) has neither list, and that of `hxb-001` (`timeout`) has no
    generation list; the record passes."""
    entries = {row["question_id"]: row for row in registry_copy.entries(RUN_A)}
    assert entries["hxa-005"]["retrieved_list"] is None
    assert entries["hxb-001"]["generation_list"] is None

    assert differences(RUN_A) == []


# --- Difference 8: the hash of an answer ----------------------------------------------------------


@pytest.mark.parametrize(
    "change",
    [
        lambda row: row.update(answer_sha256=None),
        lambda row: row.update(answer_sha256=sha256(row["answer"]).upper()),
        lambda row: row.update(answer=row["answer"] + " "),
        lambda row: row.update(answer_sha256=sha256(row["context"])),
    ],
    ids=[
        "an answer without its hash",
        "the hash in upper case",
        "an answer that changed after it was hashed",
        "the hash of another text",
    ],
)
def test_difference_8_a_hash_that_is_not_the_hash_of_the_answer(registry_copy, differences, change):
    """data-model.md, difference 8: "`answer_sha256` is not the SHA-256 of `answer`, or
    exactly one of the two is `null`"; a SHA-256 is written in lower case
    (contracts/records.md)."""
    registry_copy.change_entries(RUN_A, lambda rows: change(rows[7]))

    assert naming(differences(RUN_A), "hxb-003", "answer_sha256"), differences(RUN_A)


def test_difference_8_a_hash_without_an_answer(registry_copy, differences):
    """The other half of "exactly one of the two is `null`": `hxb-001` has no answer and gets
    a hash."""
    registry_copy.change_entries(RUN_A, lambda rows: rows[5].update(answer_sha256="0" * 64))

    assert naming(differences(RUN_A), "hxb-001", "answer_sha256"), differences(RUN_A)


def test_the_hash_is_taken_of_the_utf8_bytes_of_the_answer(registry_copy, differences):
    """data-model.md, `answer_sha256`: "The SHA-256 of the UTF-8 bytes of `answer`". The
    answer of `hxb-003` holds a character of several bytes, and the record passes."""
    answer = registry_copy.entries(RUN_A)[7]["answer"]
    assert not answer.isascii()

    assert differences(RUN_A) == []


# --- Difference 9: tokens, prices and the cost ----------------------------------------------------


def test_difference_9_a_cost_that_does_not_follow_from_the_tokens(registry_copy, differences):
    """data-model.md, difference 9; contracts/cli.md: `<question> has cost_usd <n>, its
    tokens and the prices give <m>`. The summary computes its costs from the tokens, so this
    is the one difference."""
    registry_copy.change_entries(RUN_A, lambda rows: rows[0].update(cost_usd=0.5))

    assert differences(RUN_A) == ["hxa-001 has cost_usd 0.5, its tokens and the prices give 0.0012"]


def test_difference_9_a_cost_is_compared_for_equality(registry_copy, differences):
    """research.md, section 7: "The check of a run record therefore compares numbers for
    equality, with no tolerance": the cost becomes the next floating-point number above
    0.0012, and that is a difference."""
    assert 0.0012000000000000001 != 0.0012
    registry_copy.change_entries(RUN_A, lambda rows: rows[0].update(cost_usd=0.0012000000000000001))

    assert differences(RUN_A) == [
        "hxa-001 has cost_usd 0.0012000000000000001, its tokens and the prices give 0.0012"
    ]


def test_difference_9_a_cost_follows_from_the_tokens_as_they_were_changed(
    registry_copy, differences
):
    """The same from the other side: the token counts change and the cost stays. The summary
    then differs from the results as well."""
    registry_copy.change_entries(RUN_A, lambda rows: rows[0]["tokens"][0].update(input_tokens=2000))

    found = differences(RUN_A)

    assert "hxa-001 has cost_usd 0.0012, its tokens and the prices give 0.0022" in found
    assert any(text.startswith("the summary states ") for text in found), found


def test_difference_9_a_model_without_a_price(registry_copy, differences):
    """data-model.md, difference 9: "A `tokens` entry names a model without a price"."""
    registry_copy.change_entries(
        RUN_A, lambda rows: rows[0]["tokens"][0].update(model="model-without-a-price")
    )

    assert naming(differences(RUN_A), "hxa-001", "model-without-a-price"), differences(RUN_A)


def test_difference_9_a_model_that_is_named_twice_in_the_tokens(registry_copy, differences):
    """data-model.md, difference 9: a `tokens` entry "names a model twice"."""
    registry_copy.change_entries(
        RUN_A, lambda rows: rows[0]["tokens"].append(dict(rows[0]["tokens"][0]))
    )

    assert naming(differences(RUN_A), "hxa-001", "example-model"), differences(RUN_A)


# --- Difference 10: the audit result --------------------------------------------------------------


@pytest.mark.parametrize(
    "change",
    [
        lambda audit: audit.update(outcome="failed"),
        lambda audit: audit.update(outcome="not carried out"),
        lambda audit: audit.update(index="another-index"),
        lambda audit: audit["dataset"].update(name="another-dataset"),
        lambda audit: audit["dataset"].update(revision="0123456789abcdef0123456789abcdef01234567"),
        lambda audit: audit["question_set"].update(version="harness-half"),
        lambda audit: audit["question_set"].update(fingerprint="0" * 64),
        lambda audit: audit["question_set"].update(questions=7),
        lambda audit: [
            audit["question_set"].pop(key) for key in ("version", "role", "fingerprint")
        ],
        lambda audit: audit.pop("missing_from_index"),
        lambda audit: audit.pop("outcome"),
        lambda audit: audit.clear(),
    ],
    ids=[
        "the outcome is failed",
        "the outcome is not carried out",
        "another index",
        "another dataset name",
        "another dataset revision",
        "another version of the question set",
        "another fingerprint of the question set",
        "another number of questions",
        "an audit that named no question set",
        "not a result of spec 1's form",
        "no outcome",
        "an empty object",
    ],
)
def test_difference_10_an_audit_result_that_does_not_belong_to_the_run(
    registry_copy, differences, change
):
    """data-model.md, difference 10: "The audit result ... is not a result of spec 1's form;
    its outcome is not `passed`; its index, its dataset name or revision, or its question
    set (version, fingerprint, number of questions) differs from the config and the set"
    (FR-021, FR-022; Principle I)."""
    registry_copy.change_summary(RUN_A, lambda document: change(document["audit"]))

    assert naming(differences(RUN_A), "audit"), differences(RUN_A)


@pytest.mark.parametrize("value", [None, "passed", []])
def test_difference_10_an_audit_result_that_is_absent(registry_copy, differences, value):
    """data-model.md, difference 10: "The audit result is absent": `null`, a text or a list
    in its place."""
    registry_copy.change_summary(RUN_A, lambda document: document.update(audit=value))

    assert naming(differences(RUN_A), "audit"), differences(RUN_A)


def test_the_time_of_the_audit_is_not_compared(registry_copy, differences):
    """data-model.md, difference 10, lists what is compared; the time of the audit is not in
    it. The audit result is taken as the gate gave it."""
    registry_copy.change_summary(
        RUN_A, lambda document: document["audit"].update(audited_at="2026-10-31T23:59:59Z")
    )

    assert differences(RUN_A) == []


# --- Difference 11: the summary names the run -----------------------------------------------------


def test_difference_11_a_summary_that_names_another_run(registry_copy, differences):
    """data-model.md, difference 11: "`summary.json` names another run ... than `run.json`"."""
    registry_copy.change_summary(RUN_A, lambda document: document.update(run_id=RUN_B))

    assert naming(differences(RUN_A), RUN_B) or naming(differences(RUN_A), "run_id")


@pytest.mark.parametrize(
    "change",
    [{"version": "harness-half"}, {"role": "held-out"}, {"fingerprint": "0" * 64}],
    ids=["another version", "another role", "another fingerprint"],
)
def test_difference_11_a_summary_that_names_another_question_set(
    registry_copy, differences, change
):
    """data-model.md, difference 11: `summary.json` names "another question set than
    `run.json`"."""
    registry_copy.change_summary(RUN_A, lambda document: document["question_set"].update(change))

    assert naming(differences(RUN_A), "question_set") or naming(differences(RUN_A), "summary")


def test_difference_11_a_number_of_questions_that_is_not_the_size_of_the_set(
    registry_copy, differences
):
    """data-model.md, difference 11: "`questions` is not the size of the set"."""
    registry_copy.change_summary(RUN_A, lambda document: document.update(questions=7))

    found = differences(RUN_A)
    assert any("7" in text and "8" in text and "questions" in text for text in found), found


# --- Difference 12: the numbers of the summary ----------------------------------------------------


@pytest.mark.parametrize(
    ("breakdown", "name", "field", "stated", "given", "line"),
    [
        ("all", "retrieved_list", "questions", 8, 7, "the retrieved list, all questions"),
        (
            "multi_article",
            "retrieved_list",
            "mean_share_found",
            0.9,
            0.875,
            "the retrieved list, multi-article",
        ),
        (
            "single_article",
            "generation_list",
            "all_found",
            2,
            1,
            "the generation list, single-article",
        ),
        (
            "multi_article",
            "retrieved_list",
            "share_all_found",
            0.5,
            0.75,
            "the retrieved list, multi-article",
        ),
    ],
)
def test_difference_12_a_number_of_a_list_is_named_with_both_values(
    registry_copy, differences, breakdown, name, field, stated, given, line
):
    """data-model.md, difference 12; contracts/cli.md: `the summary states <field> <n> for
    the <generation list or retrieved list>, <breakdown>; the results give <m>`, with the
    breakdown written `all questions`, `single-article` or `multi-article`."""
    registry_copy.change_summary(
        RUN_A, lambda document: document["breakdowns"][breakdown][name].update({field: stated})
    )

    assert differences(RUN_A) == [
        f"the summary states {field} {stated} for {line}; the results give {given}"
    ]


@pytest.mark.parametrize(
    ("change", "breakdown", "stated", "given"),
    [
        (lambda b: b["all"]["status"].update(answered=5), "all questions", "5", "4"),
        (lambda b: b["single_article"].update(questions=5), "single-article", "5", "4"),
        (lambda b: b["all"]["cost_usd"].update(total=0.5), "all questions", "0.5", "0.0128"),
        (
            lambda b: b["multi_article"]["cost_usd"].update(per_question=0.002),
            "multi-article",
            "0.002",
            "0.0017",
        ),
        (
            lambda b: b["single_article"]["latency_seconds"].update(median=3.0),
            "single-article",
            "3.0",
            "3.5",
        ),
        (lambda b: b["all"]["latency_seconds"].update(p95=8.0), "all questions", "8.0", "30.0"),
    ],
    ids=[
        "the count of a status",
        "the questions of a breakdown",
        "the total cost",
        "the cost per question",
        "the median latency",
        "the 95th percentile",
    ],
)
def test_difference_12_a_number_that_belongs_to_no_list_is_named_with_both_values(
    registry_copy, differences, change, breakdown, stated, given
):
    """contracts/cli.md: "for a number that belongs to no list: `the summary states <field>
    <n> for <breakdown>; the results give <m>`". The contract does not fix how the field of
    such a number is written, so the test reads the frame of the line, the breakdown and
    both values."""
    registry_copy.change_summary(RUN_A, lambda document: change(document["breakdowns"]))

    found = differences(RUN_A)

    assert len(found) == 1, found
    assert found[0].startswith("the summary states "), found
    assert f" for {breakdown}; the results give " in found[0], found
    assert f" {stated} for " in found[0], found
    assert found[0].endswith(f"the results give {given}"), found


def test_difference_12_a_number_is_compared_for_equality(registry_copy, differences):
    """research.md, section 7, and plan.md: no tolerance. The mean 0.5277777777777778 of the
    generation list becomes the next floating-point number above it."""
    registry_copy.change_summary(
        RUN_A,
        lambda document: document["breakdowns"]["all"]["generation_list"].update(
            mean_share_found=0.5277777777777779
        ),
    )

    assert differences(RUN_A) == [
        "the summary states mean_share_found 0.5277777777777779 for the generation list, "
        "all questions; the results give 0.5277777777777778"
    ]


def test_difference_12_each_number_is_reported_on_its_own(registry_copy, differences):
    """data-model.md, difference 12: "Each number is reported on its own": three numbers of
    the summary differ, and each has its line."""

    def change(document):
        breakdowns = document["breakdowns"]
        breakdowns["all"]["generation_list"]["all_found"] = 3
        breakdowns["multi_article"]["retrieved_list"]["all_found"] = 4
        breakdowns["single_article"]["generation_list"]["mean_share_found"] = 0.5

    registry_copy.change_summary(RUN_A, change)

    assert sorted(differences(RUN_A)) == [
        "the summary states all_found 3 for the generation list, all questions; the results give 2",
        "the summary states all_found 4 for the retrieved list, multi-article; the results give 3",
        "the summary states mean_share_found 0.5 for the generation list, single-article; "
        "the results give 0.3333333333333333",
    ]


def test_difference_12_a_number_over_no_question_is_null(registry_copy, differences):
    """data-model.md: "A number whose denominator is 0 is `null`". The summary of
    `example-c` states 0.0 where the results give no number."""
    registry_copy.change_summary(
        RUN_C,
        lambda document: document["breakdowns"]["multi_article"]["latency_seconds"].update(
            median=0.0
        ),
    )

    found = differences(RUN_C)

    assert len(found) == 1 and found[0].startswith("the summary states "), found
    assert "multi-article" in found[0]


@pytest.mark.parametrize(
    "misses",
    [
        ["hxa-002", "hxa-003", "hxa-004"],
        ["hxa-002", "hxa-003", "hxa-004", "hxb-002", "hxa-005"],
        ["hxb-002", "hxa-004", "hxa-003", "hxa-002"],
        [],
    ],
    ids=["one miss less", "a question without a generation list", "another order", "none"],
)
def test_difference_12_retrieval_misses_that_the_results_do_not_give(
    registry_copy, differences, misses
):
    """data-model.md, "Summary": `retrieval_misses` are "the questions whose generation list
    exists and has `all_found` = 0, in the order of the set" (FR-013)."""
    registry_copy.change_summary(RUN_A, lambda document: document.update(retrieval_misses=misses))

    found = differences(RUN_A)

    assert len(found) == 1, found


def test_difference_12_questions_without_gold_articles_that_the_set_does_not_have(
    registry_copy, differences
):
    """data-model.md, "Summary": `questions_without_gold_articles` is the number of questions
    of the set with an empty `article_ids` list; `harness` has none."""
    registry_copy.change_summary(
        RUN_A, lambda document: document.update(questions_without_gold_articles=1)
    )

    assert len(differences(RUN_A)) == 1


# --- Differences 13 to 16: an experiment run ------------------------------------------------------


def test_a_sound_experiment_run_differs_from_its_baseline_in_the_one_parameter(
    registry_copy, examine
):
    """FR-023 and Principle VI: `example-b` names `example-a` as its baseline and
    `reranking.enabled`, `false` -> `true`, and passes."""
    examination = examine(RUN_B)

    assert list(examination.differences) == []
    assert examination.run_document["config"]["experiment"]["baseline"] == RUN_A


def test_difference_13_a_baseline_that_is_not_in_the_registry(registry_copy, differences):
    """data-model.md, difference 13; contracts/cli.md: `the baseline <run id> …`."""
    shutil.rmtree(registry_copy.runs_dir / RUN_A)

    found = differences(RUN_B)

    assert [text for text in found if text.startswith(f"the baseline {RUN_A} ")], found


def test_difference_13_a_baseline_whose_own_record_does_not_pass(registry_copy, differences):
    """data-model.md, difference 13: the baseline's "own record has one of the differences 1
    to 12". The experiment run itself is as it was."""
    registry_copy.change_entries(RUN_A, lambda rows: rows[0].update(answer_sha256="0" * 64))

    found = differences(RUN_B)

    assert [text for text in found if text.startswith(f"the baseline {RUN_A} ")], found


def test_difference_14_a_baseline_on_another_question_set(registry_copy, differences):
    """data-model.md, difference 14: "the baseline is on another question set (version or
    fingerprint)"; FR-023. `example-b` names `example-c`, which is on `harness-hxc`."""
    registry_copy.change_run(
        RUN_B, lambda document: document["config"]["experiment"].update(baseline=RUN_C)
    )

    found = differences(RUN_B)

    assert [text for text in found if text.startswith(f"the baseline {RUN_C} ")], found


def test_difference_15_an_experiment_on_a_held_out_set_is_stated_once(registry_copy, differences):
    """data-model.md, difference 15, and FR-035, for a run of the registry `runs`: `example-d`
    is made an experiment on `example-c`. AC-043 reads the same line for the record of
    `runs-invalid`."""

    def change(document):
        document["config"]["reranking"]["enabled"] = True
        document["config"]["experiment"] = {
            "baseline": RUN_C,
            "parameter": "reranking.enabled",
            "baseline_value": False,
            "value": True,
        }

    registry_copy.change_run(RUN_D, change)

    assert differences(RUN_D) == [
        "the run is an experiment on the held-out set harness-hxc; "
        "an experiment run is made on a golden set"
    ]


def test_difference_16_the_named_parameter_does_not_differ(registry_copy, differences):
    """data-model.md, difference 16; contracts/cli.md: `the config does not differ from the
    baseline <run id> in <parameter>`. `example-b` has `reranking.enabled` `false`, as its
    baseline has."""
    registry_copy.change_run(
        RUN_B, lambda document: document["config"]["reranking"].update(enabled=False)
    )

    assert (
        f"the config does not differ from the baseline {RUN_A} in reranking.enabled"
        in differences(RUN_B)
    )


@pytest.mark.parametrize(
    ("change", "second"),
    [
        (lambda config: config["retrieval"].update(top_k=4), "retrieval.top_k"),
        (lambda config: config.update(index="harness-2"), "index"),
        (lambda config: config["context"].update(max_tokens=4000), "context.max_tokens"),
        (lambda config: config["prices"][0].update(usd_per_million_input_tokens=3.0), "prices"),
    ],
    ids=["a nested parameter", "a parameter at the top", "a parameter only this run has", "a list"],
)
def test_difference_16_every_second_parameter_is_named(registry_copy, differences, change, second):
    """data-model.md, difference 16: "the configs differ in a parameter other than the one
    named"; FR-023: "The defect names the parameter." contracts/cli.md fixes the line."""
    registry_copy.change_run(RUN_B, lambda document: change(document["config"]))

    assert (
        f"the config differs from the baseline {RUN_A} in {second}, "
        "which is not the parameter the experiment names"
    ) in differences(RUN_B)


@pytest.mark.parametrize(
    ("field", "value"),
    [("baseline_value", True), ("value", False), ("value", "true"), ("baseline_value", None)],
)
def test_difference_16_a_recorded_value_that_is_not_the_value_in_the_config(
    registry_copy, differences, field, value
):
    """data-model.md, difference 16: "`baseline_value` or `value` is not the value in the
    respective config". The baseline has `false`, and this run has `true`."""
    registry_copy.change_run(
        RUN_B, lambda document: document["config"]["experiment"].update({field: value})
    )

    assert naming(differences(RUN_B), field), differences(RUN_B)


@pytest.mark.parametrize("field", ["baseline", "parameter", "baseline_value", "value"])
def test_an_experiment_without_one_of_its_four_fields_does_not_pass(
    registry_copy, differences, field
):
    """data-model.md, `experiment`: "Otherwise `baseline` (a run identifier), `parameter` (a
    dotted path), `baseline_value` and `value`": the four fields of an experiment."""
    registry_copy.change_run(RUN_B, lambda document: document["config"]["experiment"].pop(field))

    assert naming(differences(RUN_B), field), differences(RUN_B)


def test_a_run_that_names_itself_as_its_baseline_does_not_pass(registry_copy, differences):
    """Principle VI: an experiment differs from its baseline by one parameter; a run does not
    differ from itself."""
    registry_copy.change_run(
        RUN_B, lambda document: document["config"]["experiment"].update(baseline=RUN_B)
    )

    assert differences(RUN_B), "a run that names itself as its baseline has a difference"


# --- Every difference is reported -----------------------------------------------------------------


def test_every_difference_of_a_record_is_reported(registry_copy, differences):
    """FR-022: the check "MUST fail, and name every defect". One record has a status that is
    not one of the five, a hash that is not the hash of its answer, a cost that does not
    follow from its tokens, an entry for a question outside the set, and a question without
    an entry."""
    outside = registry_copy.entries(RUN_C)[1]

    def change(rows):
        rows[0]["answer_sha256"] = "0" * 64
        rows[1]["cost_usd"] = 0.25
        rows[3]["status"] = "skipped"
        del rows[7]
        rows.append(outside)

    registry_copy.change_entries(RUN_A, change)

    found = differences(RUN_A)

    for expected in (
        "hxa-001 has an answer_sha256 that is not the hash of its answer",
        "hxa-002 has cost_usd 0.25, its tokens and the prices give 0.0012",
        "hxa-004 has the status skipped, which is not one of the five",
        "hxb-003 is a question of the question set and has no entry",
        "hxc-002 has an entry and is not a question of the question set",
    ):
        assert expected in found, f"not reported: {expected}\nreported: {found}"
    assert len(found) == len(set(found)), "no difference is reported twice"


def test_differences_of_all_three_files_are_reported_together(registry_copy, differences):
    """The same across the files: a field of `run.json`, an entry and the summary."""
    registry_copy.change_run(RUN_A, lambda document: document.update(uncommitted_changes="no"))
    registry_copy.change_entries(RUN_A, lambda rows: rows[0].update(answer_sha256="0" * 64))
    registry_copy.change_summary(
        RUN_A, lambda document: document["breakdowns"]["all"]["generation_list"].update(all_found=3)
    )

    found = differences(RUN_A)

    assert naming(found, "uncommitted_changes"), found
    assert "hxa-001 has an answer_sha256 that is not the hash of its answer" in found
    assert (
        "the summary states all_found 3 for the generation list, all questions; the results give 2"
        in found
    )


# --- What the check ignores -----------------------------------------------------------------------


def test_a_further_field_in_an_entry_is_ignored(registry_copy, differences):
    """data-model.md, "Results", rule 4: "An entry may hold further fields; the check ignores
    them." contracts/records.md: "A later spec may add fields to a record"."""

    def change(rows):
        for number, row in enumerate(rows):
            row["trace"] = {"calls": number, "notes": ["free"]}
            row["judge"] = None

    registry_copy.change_entries(RUN_A, change)

    assert differences(RUN_A) == []


def test_a_further_file_in_the_directory_of_a_run_is_ignored(registry_copy, differences):
    """contracts/records.md: "A later spec may add ... files to a run's directory"; spec 4
    adds the numbers of the judge "in files of its own in the same directory"."""
    registry_copy.file(RUN_A, "judge.json").write_text("{}\n", encoding="utf-8")

    assert differences(RUN_A) == []


def test_the_free_objects_of_the_config_may_hold_anything(registry_copy, differences):
    """data-model.md, "Identity and config": "For the six that spec 3 fixes, this feature
    requires only that they are JSON objects". `example-a` and its experiment get the same
    further keys, so the two still differ in one parameter only."""

    def change(document):
        document["config"]["models"]["embedding"] = "example-embedding"
        document["config"]["prompts"]["system"] = "Be brief."
        document["config"]["retrieval"]["method"] = "dense"
        document["config"]["context"]["separator"] = "\n\n"
        document["config"]["seeds"]["generation"] = 7

    registry_copy.change_run(RUN_A, change)
    registry_copy.change_run(RUN_B, change)

    assert differences(RUN_A) == []
    assert differences(RUN_B) == []


# --- A run that does not exist --------------------------------------------------------------------


@pytest.mark.parametrize("run", ["20261101T100000Z-no-such-run", "no-such-run", ".gitkeep"])
def test_run_not_found_for_a_run_that_does_not_exist(registry_copy, examine, run):
    """contracts/harness.md: `RunNotFound`: "The run does not exist in the runs directory";
    `examine` raises it. A file directly in the runs directory is not a run (data-model.md,
    "Check of the registry")."""
    (registry_copy.runs_dir / ".gitkeep").write_bytes(b"")

    with pytest.raises(load_runs().RunNotFound):
        examine(run)


def test_run_not_found_is_an_exception(registry_copy):
    """contracts/harness.md: `RunNotFound` is an exception."""
    assert issubclass(load_runs().RunNotFound, Exception)
