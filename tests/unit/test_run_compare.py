"""The pairwise comparison of two runs (task T094): `compare` of `src/wixqa_rag/metrics.py`
and the command `run compare` of `src/wixqa_rag/runs.py`.

Covers:

- spec.md, FR-025, FR-027 to FR-029, FR-033 and FR-036, and the edge case "a run is compared
  with itself";
- data-model.md, "Pairwise comparison" and, under "Example data", "The comparisons";
- contracts/harness.md, "`wixqa_rag.metrics`": `compare(questions, first_entries,
  second_entries)` gives "a dictionary with `compared` (a number) and `left_out`, `gained`
  and `lost` (lists of question identifiers in the order of the set)";
- contracts/cli.md, "`run compare`": the four steps and their order, the output, the line
  for a held-out set, and the table of the verdicts.

The function is tried on plain values and on the entries of the example runs, read here with
`json`. The command is typed in a temporary repository root with a copy of the example
registries, the fixture `registry_copy` of tests/conftest.py; no file of the checkout is
written. The wrong arguments of the command are in tests/unit/test_run_commands.py. All
documents named here are in specs/002-evaluation-harness/.
"""

import copy
import hashlib
import importlib
import json
import shutil
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "data"

RUN_A = "20261101T100000Z-example-a"
RUN_B = "20261102T100000Z-example-b"
RUN_C = "20261103T100000Z-example-c"
RUN_D = "20261104T100000Z-example-d"
WRONG_HASH = "20261101T100400Z-wrong-hash"
STALE = "20261101T100500Z-stale-summary"
ABSENT = "20261101T100000Z-no-such-run"

RUNS = "data/runs"
RUNS_INVALID = "data/runs-invalid"
SETS = "data/sets"

# contracts/cli.md, "`run compare`", "Output".
COMPARISON_A_B = [
    f"first run: {RUN_A}",
    f"second run: {RUN_B}",
    "question set: harness (golden)",
    "outcome: all_found on the generation list",
    "compared: 6",
    "left out: 2",
    "  hxa-005",
    "  hxb-001",
    "gained: 2",
    "  hxa-002",
    "  hxa-003",
    "lost: 1",
    "  hxb-003",
    "run compare: done",
]
# The same output for two runs on a held-out set: "one line follows the `question set:`
# line"; the numbers of data-model.md, "The comparisons".
COMPARISON_C_D = [
    f"first run: {RUN_C}",
    f"second run: {RUN_D}",
    "question set: harness-hxc (held-out)",
    "held-out set: its questions are not used to choose a setting",
    "outcome: all_found on the generation list",
    "compared: 2",
    "left out: 0",
    "gained: 1",
    "  hxc-002",
    "lost: 0",
    "run compare: done",
]


def load_metrics():
    """Import the module; it fails while `src/wixqa_rag/metrics.py` does not exist (plan.md,
    "Project Structure")."""
    return importlib.import_module("wixqa_rag.metrics")


def pairs_of(version: str) -> list[tuple[str, list[str]]]:
    record = json.loads((DATA / "sets" / f"{version}.json").read_text(encoding="utf-8"))
    return [(question["id"], question["article_ids"]) for question in record["questions"]]


def entries_of(run: str) -> list[dict]:
    text = (DATA / "runs" / run / "results.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.split("\n") if line]


def entry(question: str, generation) -> dict:
    """An entry on plain values; `generation` is the generation list, or `None`."""
    return {
        "question_id": question,
        "status": "answered" if generation is not None else "timeout",
        "retrieved_list": ["a-1", "a-2", "a-3"],
        "generation_list": None if generation is None else list(generation),
        "context": None,
        "answer": None,
        "answer_sha256": None,
        "tokens": [],
        "cost_usd": 0.0,
        "latency_seconds": 1.0,
    }


def comparison(compared: int, left_out=(), gained=(), lost=()) -> dict:
    return {
        "compared": compared,
        "left_out": list(left_out),
        "gained": list(gained),
        "lost": list(lost),
    }


# --- `metrics.compare` on the example runs -----------------------------------------------------


def test_compare_gives_the_comparison_of_example_a_and_example_b():
    """data-model.md, "The comparisons": a, b: compared 6; left out `hxa-005` and `hxb-001`;
    gained `hxa-002` and `hxa-003`; lost `hxb-003` (AC-030)."""
    found = load_metrics().compare(pairs_of("harness"), entries_of(RUN_A), entries_of(RUN_B))

    assert found == comparison(
        6, ["hxa-005", "hxb-001"], gained=["hxa-002", "hxa-003"], lost=["hxb-003"]
    )


def test_compare_gives_the_comparison_of_example_c_and_example_d():
    """data-model.md, "The comparisons": c, d: compared 2; left out none; gained `hxc-002`;
    lost none (AC-046)."""
    found = load_metrics().compare(pairs_of("harness-hxc"), entries_of(RUN_C), entries_of(RUN_D))

    assert found == comparison(2, gained=["hxc-002"])


def test_compare_in_the_other_direction_turns_gained_and_lost_around():
    """FR-027: `gained` is 0 in the first run and 1 in the second, `lost` the other way: the
    same two runs, named in the other order."""
    found = load_metrics().compare(pairs_of("harness"), entries_of(RUN_B), entries_of(RUN_A))

    assert found == comparison(
        6, ["hxa-005", "hxb-001"], gained=["hxb-003"], lost=["hxa-002", "hxa-003"]
    )


@pytest.mark.parametrize(
    ("run", "version", "compared", "left_out"),
    [
        (RUN_A, "harness", 6, ["hxa-005", "hxb-001"]),
        (RUN_B, "harness", 7, ["hxb-001"]),
        (RUN_C, "harness-hxc", 2, []),
    ],
)
def test_a_run_compared_with_itself_gains_nothing_and_loses_nothing(
    run, version, compared, left_out
):
    """spec.md, "Edge Cases": "What happens when a run is compared with itself? Nothing is
    gained and nothing is lost." The questions without a generation list are still left
    out."""
    found = load_metrics().compare(pairs_of(version), entries_of(run), entries_of(run))

    assert found == comparison(compared, left_out)


def test_compare_gives_exactly_the_four_keys():
    """contracts/harness.md: `compared` is a number; `left_out`, `gained` and `lost` are
    lists. FR-027: "The difference of the two numbers is never reported alone": no key holds
    it."""
    found = load_metrics().compare(pairs_of("harness"), entries_of(RUN_A), entries_of(RUN_B))

    assert set(found) == {"compared", "left_out", "gained", "lost"}
    assert type(found["compared"]) is int
    for key in ("left_out", "gained", "lost"):
        assert isinstance(found[key], list), key


# --- `metrics.compare` on plain values ---------------------------------------------------------

QUESTIONS = [
    ("q-001", ["a-1"]),
    ("q-002", ["a-1", "a-2"]),
    ("q-003", ["a-3"]),
    ("q-004", ["a-2", "a-3"]),
    ("q-005", ["a-1"]),
    ("q-006", ["a-2"]),
]


def test_the_outcome_of_a_question_is_all_found_on_the_generation_list():
    """data-model.md, "Pairwise comparison": "The outcome of a question is `all_found` on the
    generation list": gained is 0 then 1, lost is 1 then 0; a question with the same outcome
    in both runs is compared and is neither. The retrieved list holds every gold article in
    every entry and decides nothing."""
    first = [
        entry("q-001", ["a-9"]),  # 0 -> 1: gained
        entry("q-002", ["a-1"]),  # 0 -> 1: gained, some of the gold articles are not all
        entry("q-003", ["a-3"]),  # 1 -> 0: lost
        entry("q-004", ["a-3", "a-2"]),  # 1 -> 1
        entry("q-005", ["a-2"]),  # 0 -> 0
        entry("q-006", ["a-2", "a-2"]),  # 1 -> 0: lost
    ]
    second = [
        entry("q-001", ["a-1"]),
        entry("q-002", ["a-2", "a-1", "a-9"]),
        entry("q-003", ["a-1", "a-2"]),
        entry("q-004", ["a-2", "a-3", "a-3"]),
        entry("q-005", ["a-3"]),
        entry("q-006", ["a-1"]),
    ]

    found = load_metrics().compare(QUESTIONS, first, second)

    assert found == comparison(6, gained=["q-001", "q-002"], lost=["q-003", "q-006"])


@pytest.mark.parametrize(
    ("first", "second"),
    [(None, ["a-1"]), (["a-1"], None), (None, None), (None, ["a-9"]), (["a-9"], None)],
    ids=[
        "no list in the first run",
        "no list in the second run",
        "no list in either run",
        "no list, then a miss",
        "a miss, then no list",
    ],
)
def test_a_question_without_a_generation_list_in_either_run_is_left_out(first, second):
    """FR-028: "A question that lacks a generation list in either run MUST be left out of the
    comparison." It is neither gained nor lost, whatever the other run holds."""
    questions = [("q-001", ["a-1"]), ("q-002", ["a-2"])]
    first_entries = [entry("q-001", first), entry("q-002", ["a-2"])]
    second_entries = [entry("q-001", second), entry("q-002", ["a-2"])]

    found = load_metrics().compare(questions, first_entries, second_entries)

    assert found == comparison(1, ["q-001"])


def test_an_empty_generation_list_is_a_list_and_is_compared():
    """FR-011: "An empty list exists": its outcome is 0, so the question is compared, and it
    is gained when the second run has every gold article. In `example-a`, `hxb-002` has an
    empty generation list and is not left out."""
    questions = [("q-001", ["a-1"]), ("q-002", ["a-2"])]
    first = [entry("q-001", []), entry("q-002", ["a-2"])]
    second = [entry("q-001", ["a-1"]), entry("q-002", [])]

    found = load_metrics().compare(questions, first, second)

    assert found == comparison(2, gained=["q-001"], lost=["q-002"])


def test_a_question_without_a_gold_article_is_left_out():
    """data-model.md, "Pairwise comparison": left out are "Questions without a gold article,
    or without a generation list in either run"."""
    questions = [("q-001", []), ("q-002", ["a-2"]), ("q-003", [])]
    first = [entry("q-001", ["a-1"]), entry("q-002", ["a-9"]), entry("q-003", None)]
    second = [entry("q-001", ["a-2"]), entry("q-002", ["a-2"]), entry("q-003", ["a-1"])]

    found = load_metrics().compare(questions, first, second)

    assert found == comparison(1, ["q-001", "q-003"], gained=["q-002"])


def test_a_gold_article_that_is_named_twice_counts_once():
    """spec.md, "Edge Cases": a gold article that a question names twice counts once, and an
    article that a list holds several times counts once."""
    questions = [("q-001", ["a-1", "a-1"]), ("q-002", ["a-1", "a-2", "a-1"])]
    first = [entry("q-001", ["a-9"]), entry("q-002", ["a-2", "a-1"])]
    second = [entry("q-001", ["a-1", "a-1"]), entry("q-002", ["a-1", "a-1"])]

    found = load_metrics().compare(questions, first, second)

    assert found == comparison(2, gained=["q-001"], lost=["q-002"])


def test_the_identifiers_keep_the_order_of_the_set():
    """contracts/harness.md: "lists of question identifiers in the order of the set", here a
    set whose identifiers are not in the order of the alphabet."""
    questions = [("q-z", ["a-1"]), ("q-m", ["a-1"]), ("q-a", ["a-1"]), ("q-k", ["a-1"])]
    questions += [("q-y", ["a-1"]), ("q-b", ["a-1"])]
    first = [entry(question, ["a-9"]) for question, _ in questions[:2]]
    first += [entry(question, ["a-1"]) for question, _ in questions[2:4]]
    first += [entry(question, None) for question, _ in questions[4:]]
    second = [entry(question, ["a-1"]) for question, _ in questions[:2]]
    second += [entry(question, ["a-9"]) for question, _ in questions[2:4]]
    second += [entry(question, ["a-1"]) for question, _ in questions[4:]]

    found = load_metrics().compare(questions, first, second)

    assert found == comparison(4, ["q-y", "q-b"], gained=["q-z", "q-m"], lost=["q-a", "q-k"])


def test_the_numbers_of_a_comparison_add_up_to_the_questions_of_the_set():
    """FR-028: "The number of questions compared and the number left out MUST be reported":
    together they are every question of the set, and gained and lost are among the
    compared."""
    questions = pairs_of("harness")

    found = load_metrics().compare(questions, entries_of(RUN_A), entries_of(RUN_B))

    assert found["compared"] + len(found["left_out"]) == len(questions)
    assert len(found["gained"]) + len(found["lost"]) <= found["compared"]
    assert not set(found["gained"]) & set(found["lost"])
    assert not set(found["left_out"]) & (set(found["gained"]) | set(found["lost"]))


def test_compare_does_not_change_its_arguments():
    """contracts/harness.md: every function of `metrics` is pure and does not change its
    arguments."""
    questions, first, second = pairs_of("harness"), entries_of(RUN_A), entries_of(RUN_B)
    before = copy.deepcopy((questions, first, second))

    load_metrics().compare(questions, first, second)

    assert (questions, first, second) == before


def test_compare_ignores_the_status_the_cost_and_the_latency():
    """FR-027: the comparison is on `all_found` of the generation list and on nothing else of
    an entry."""
    first, second = entries_of(RUN_A), entries_of(RUN_B)
    for number, row in enumerate(second):
        row["status"] = "no_answer" if row["generation_list"] is not None else "error"
        row["cost_usd"] = float(number)
        row["latency_seconds"] = 100.0 + number
        row["tokens"] = []

    found = load_metrics().compare(pairs_of("harness"), first, second)

    assert found == comparison(
        6, ["hxa-005", "hxb-001"], gained=["hxa-002", "hxa-003"], lost=["hxb-003"]
    )


# --- The command `run compare` -----------------------------------------------------------------


@pytest.fixture
def run_compare(registry_copy, run_command):
    """Type `run compare` in the temporary repository root. A directory given as `None` is
    left to its default."""

    def of(first: str, second: str, runs_dir: str | None = RUNS, sets_dir: str | None = SETS):
        command = "python -m wixqa_rag run compare"
        if runs_dir is not None:
            command += f" --runs-dir {runs_dir}"
        if sets_dir is not None:
            command += f" --sets-dir {sets_dir}"
        return run_command(f"{command} --first {first} --second {second}", cwd=registry_copy.root)

    return of


def assert_ends(result, verdict: str) -> list[str]:
    """Exit code 2, the verdict as the last line, a reason before it, and no comparison."""
    assert result.exit_code == 2, result.stdout
    assert result.last_line == f"run compare: {verdict}", result.stdout
    assert "run compare: done" not in result.lines
    assert not any(line.startswith(("compared:", "gained:", "lost:")) for line in result.lines)
    assert result.reasons and all(result.reasons), "a `reason:` line gives the reason"
    assert result.settings_printed == ()
    return result.reasons


def test_the_command_prints_the_comparison_of_the_contract(run_compare):
    """contracts/cli.md, "`run compare`", "Output": every line, in its order."""
    result = run_compare(RUN_A, RUN_B)

    assert result.exit_code == 0, result.stdout
    assert result.lines == COMPARISON_A_B
    assert result.settings_printed == ()


def test_the_command_says_what_a_held_out_set_is_for(run_compare):
    """FR-036 and contracts/cli.md: "For two runs on a held-out set, one line follows the
    `question set:` line": `held-out set: its questions are not used to choose a setting`."""
    result = run_compare(RUN_C, RUN_D)

    assert result.exit_code == 0, result.stdout
    assert result.lines == COMPARISON_C_D


def test_the_command_prints_no_line_for_a_held_out_set_when_the_set_is_golden(run_compare):
    """The counterpart: the line stands only for a held-out set."""
    result = run_compare(RUN_A, RUN_B)

    assert result.exit_code == 0, result.stdout
    assert "question set: harness (golden)" in result.lines
    assert not any(line.startswith("held-out set:") for line in result.lines)


def test_the_command_prints_no_difference_of_the_two_numbers(run_compare):
    """FR-027: "The difference of the two numbers is never reported alone." contracts/cli.md:
    "The command prints no difference of the two numbers and no statement on whether a
    difference is more than chance." Besides the identifiers, the output has the lines of the
    contract and no other: none that states a net number, a balance or a verdict on the
    change."""
    result = run_compare(RUN_A, RUN_B)

    assert result.exit_code == 0, result.stdout
    names = [line.split(":")[0] for line in result.lines if not line.startswith("  ")]
    assert names == [
        "first run",
        "second run",
        "question set",
        "outcome",
        "compared",
        "left out",
        "gained",
        "lost",
        "run compare",
    ]
    text = result.stdout.lower()
    for word in ("net", "difference", "better", "worse", "improv", "significan"):
        assert word not in text, f"the output states `{word}`"


def test_the_command_in_the_other_direction_turns_gained_and_lost_around(run_compare):
    """FR-027: the first run is the one named with `--first`."""
    result = run_compare(RUN_B, RUN_A)

    assert result.exit_code == 0, result.stdout
    assert result.lines == [
        f"first run: {RUN_B}",
        f"second run: {RUN_A}",
        "question set: harness (golden)",
        "outcome: all_found on the generation list",
        "compared: 6",
        "left out: 2",
        "  hxa-005",
        "  hxb-001",
        "gained: 1",
        "  hxb-003",
        "lost: 2",
        "  hxa-002",
        "  hxa-003",
        "run compare: done",
    ]


def test_the_command_compares_a_run_with_itself(run_compare):
    """spec.md, "Edge Cases": "Nothing is gained and nothing is lost." A number of 0 has no
    indented line below it."""
    result = run_compare(RUN_A, RUN_A)

    assert result.exit_code == 0, result.stdout
    assert result.lines == [
        f"first run: {RUN_A}",
        f"second run: {RUN_A}",
        "question set: harness (golden)",
        "outcome: all_found on the generation list",
        "compared: 6",
        "left out: 2",
        "  hxa-005",
        "  hxb-001",
        "gained: 0",
        "lost: 0",
        "run compare: done",
    ]


def test_the_default_directories_are_evals_runs_and_evals_golden(registry_copy, run_compare):
    """contracts/cli.md, "Directories": the defaults of `--runs-dir` and `--sets-dir`, below
    the directory where the command is typed."""
    missing = run_compare(RUN_C, RUN_D, runs_dir=None, sets_dir=None)
    assert assert_ends(missing, "not carried out") == [f"run {RUN_C} does not exist in evals/runs"]

    shutil.copytree(registry_copy.runs_dir, registry_copy.root / "evals" / "runs")
    shutil.copytree(registry_copy.sets_dir, registry_copy.root / "evals" / "golden")

    found = run_compare(RUN_C, RUN_D, runs_dir=None, sets_dir=None)
    assert found.exit_code == 0, found.stdout
    assert found.lines == COMPARISON_C_D


def test_the_command_changes_no_file(registry_copy, run_compare):
    """FR-026: no command of this feature changes a run record or a question-set record; the
    comparison "is not stored" (data-model.md, "Pairwise comparison")."""
    before = registry_copy.files()

    done = run_compare(RUN_A, RUN_B)
    refused = run_compare(RUN_A, RUN_C)
    run_compare(RUN_A, WRONG_HASH, runs_dir=RUNS_INVALID)
    run_compare(RUN_A, ABSENT)

    assert done.last_line == "run compare: done"
    assert refused.last_line == "run compare: refused"
    assert registry_copy.files() == before


# --- Refused (FR-025, FR-029, FR-033) ----------------------------------------------------------


@pytest.mark.parametrize(
    ("first", "second", "reason"),
    [
        (RUN_A, RUN_C, "the runs are on different question sets: harness and harness-hxc"),
        (RUN_D, RUN_B, "the runs are on different question sets: harness-hxc and harness"),
    ],
)
def test_two_runs_on_different_question_sets_are_refused_and_both_sets_are_named(
    run_compare, first, second, reason
):
    """FR-029 and contracts/cli.md: `reason: the runs are on different question sets: <V> and
    <W>`, refused, exit code 2: "between the golden set and a held-out set", in either
    order (AC-031)."""
    assert assert_ends(run_compare(first, second), "refused") == [reason]


def test_two_runs_on_two_versions_of_one_kind_of_set_are_refused(registry_copy, run_compare):
    """FR-029: "This holds between two versions of the golden set". `example-b` is moved to
    the golden set `harness-half`, a record of the same dataset: it then has entries for
    questions outside its set and no longer passes its check, so the comparison is refused
    either way and never made."""

    def change(document):
        fingerprint = registry_copy.sets_dir / "harness-half.json"
        document["config"]["question_set"] = {
            "version": "harness-half",
            "role": "golden",
            "fingerprint": hashlib.sha256(fingerprint.read_bytes()).hexdigest(),
        }
        document["config"]["experiment"] = None

    registry_copy.change_run(RUN_B, change)

    reasons = assert_ends(run_compare(RUN_A, RUN_B), "refused")

    assert len(reasons) == 1
    assert reasons[0] in (
        "the runs are on different question sets: harness and harness-half",
        f"the run check failed for {RUN_B}",
    )


def test_two_runs_on_one_version_with_different_fingerprints_are_refused(
    registry_copy, run_compare
):
    """tasks.md, T094, and FR-029: "A comparison of two runs whose question sets differ in
    version or in fingerprint MUST be refused". `example-d` records another fingerprint for
    `harness-hxc` than `example-c`, in its config, its summary and its audit result.

    contracts/cli.md gives two rows that apply here. The table has `reason: the runs are on
    different records of the question set <V>: <fingerprint> and <fingerprint>`; but step 2,
    which comes first, checks both records against the one sets directory, and a record
    whose fingerprint is not that of the set's file does not pass its check (data-model.md,
    difference 4), which gives `reason: the run check failed for <ID>`. The test holds what
    both rows have in common, the refusal, and accepts the reason of either row; with the
    first, both fingerprints are named."""
    other = "f" * 64
    recorded = registry_copy.run_document(RUN_C)["config"]["question_set"]["fingerprint"]
    assert recorded != other
    registry_copy.change_run(
        RUN_D, lambda document: document["config"]["question_set"].update(fingerprint=other)
    )

    def change(document):
        document["question_set"]["fingerprint"] = other
        document["audit"]["question_set"]["fingerprint"] = other

    registry_copy.change_summary(RUN_D, change)

    reasons = assert_ends(run_compare(RUN_C, RUN_D), "refused")

    assert len(reasons) == 1
    assert reasons[0] in (
        "the runs are on different records of the question set harness-hxc: "
        f"{recorded} and {other}",
        f"the run check failed for {RUN_D}",
    )


@pytest.mark.parametrize(
    ("first", "second", "named"),
    [(RUN_A, WRONG_HASH, WRONG_HASH), (STALE, RUN_A, STALE), (RUN_C, WRONG_HASH, WRONG_HASH)],
    ids=["the second record fails", "the first record fails", "a failed record on another set"],
)
def test_a_record_that_fails_its_check_is_not_compared(run_compare, first, second, named):
    """FR-025 and contracts/cli.md: `reason: the run check failed for <ID>`, refused, exit
    code 2 (AC-032). Step 2 comes before step 3: a failed record is reported before two
    different question sets."""
    result = run_compare(first, second, runs_dir=RUNS_INVALID)

    assert assert_ends(result, "refused") == [f"the run check failed for {named}"]


def test_the_first_run_is_checked_first(run_compare):
    """contracts/cli.md, "`run compare`", step 2: "Both records pass the check of `run
    check`; the first run is checked first." Both records fail; the reason names the first,
    in whichever order the two are given."""
    one = run_compare(STALE, WRONG_HASH, runs_dir=RUNS_INVALID)
    other = run_compare(WRONG_HASH, STALE, runs_dir=RUNS_INVALID)

    assert assert_ends(one, "refused") == [f"the run check failed for {STALE}"]
    assert assert_ends(other, "refused") == [f"the run check failed for {WRONG_HASH}"]


# --- Not carried out (FR-030) ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("first", "second", "named"),
    [
        (RUN_A, ABSENT, ABSENT),
        (ABSENT, RUN_A, ABSENT),
        (RUN_A, "no-such-run", "no-such-run"),
        ("Not_A_Run", RUN_A, "Not_A_Run"),
    ],
    ids=[
        "the second run does not exist",
        "the first run does not exist",
        "the second is not a run identifier",
        "the first is not a run identifier",
    ],
)
def test_a_run_that_does_not_exist_is_not_compared(run_compare, first, second, named):
    """contracts/cli.md, the table of `run compare`: "A run does not exist, or `ID` is not a
    run identifier": `reason: run <ID> does not exist in <runs directory>`, not carried out,
    exit code 2."""
    result = run_compare(first, second)

    assert assert_ends(result, "not carried out") == [f"run {named} does not exist in {RUNS}"]


@pytest.mark.parametrize(
    ("first", "second"), [(WRONG_HASH, ABSENT), (ABSENT, WRONG_HASH)], ids=["second", "first"]
)
def test_both_runs_are_looked_for_before_a_record_is_checked(run_compare, first, second):
    """contracts/cli.md, "`run compare`": step 1, both runs exist, comes before step 2: with a
    record that fails its check and a run that does not exist, the comparison is not carried
    out, and never refused."""
    result = run_compare(first, second, runs_dir=RUNS_INVALID)

    assert assert_ends(result, "not carried out") == [
        f"run {ABSENT} does not exist in {RUNS_INVALID}"
    ]


def test_a_runs_directory_that_does_not_exist_is_not_carried_out(run_compare):
    """contracts/cli.md: a run that is not in the runs directory does not exist, also when
    the directory itself does not."""
    result = run_compare(RUN_A, RUN_B, runs_dir="data/no-such-directory")

    assert_ends(result, "not carried out")
