"""A run record with a number that is no number of a record: infinity, "not a number", or a
whole number too large to compute with (review finding B3).

Covers:

- spec.md, FR-022 and FR-024: the check of a run record fails and names every defect; the
  check of the registry checks every run in it and reports the number of runs and the
  number of runs that failed; FR-030: a record with a defect is failed, and "not carried
  out" is for a check that could not be made; FR-025: no report and no comparison is made
  from a record that fails its check;
- data-model.md, "Check of a run record", differences 1 and 2: a file that "is not JSON of
  the stated form", and a field that "has the wrong type"; difference 9: `cost_usd` is the
  cost computed from `tokens` and `config.prices`;
- contracts/records.md: every file is JSON, and its numbers are those of the tables: a
  latency of 0 or more, a price in US dollars, token counts that are whole numbers of 0 or
  more.

`Infinity`, `-Infinity` and `NaN` are no JSON numbers. Python's `json` reads and writes them
all the same, so a record can hold one. The documents leave open whether such a record fails
by difference 1 (the file is not JSON) or by difference 2 (the field has the wrong type), so
a test accepts a `difference:` line that names the field or one that names the file.

A whole number of any size is a valid token count: data-model.md sets no upper limit. A
count of 10**400 is far more than a floating-point number can hold. For it the tests ask
what the documents fix: the check is carried out, and the record fails, because its recorded
cost is not the cost that its tokens and the prices give (difference 9).

Every test works on a temporary copy of the example registries, the fixture `registry_copy`
of tests/conftest.py, changed by hand; no file of the checkout is written. All documents
named here are in specs/002-evaluation-harness/.
"""

import importlib
import json

import pytest

RUN_A = "20261101T100000Z-example-a"
RUN_B = "20261102T100000Z-example-b"
RUN_C = "20261103T100000Z-example-c"

RUNS = "data/runs"
SETS = "data/sets"
DIRECTORIES = f"--runs-dir {RUNS} --sets-dir {SETS}"

HUGE = 10**400


def set_latency(value: float):
    def change(copy) -> None:
        copy.change_entries(RUN_A, lambda rows: rows[2].update(latency_seconds=value))

    return change


def set_cost(value: float):
    def change(copy) -> None:
        copy.change_entries(RUN_A, lambda rows: rows[2].update(cost_usd=value))

    return change


def set_price(field: str, value: float):
    def change(copy) -> None:
        copy.change_run(
            RUN_A, lambda document: document["config"]["prices"][0].update({field: value})
        )

    return change


def set_timeout(value: float):
    def change(copy) -> None:
        copy.change_run(
            RUN_A, lambda document: document["config"]["limits"].update(timeout_seconds=value)
        )

    return change


def set_summary_number(value: float):
    def change(copy) -> None:
        copy.change_summary(
            RUN_A,
            lambda document: document["breakdowns"]["all"]["latency_seconds"].update(p95=value),
        )

    return change


# What is changed in `example-a`, and the words of which a `difference:` line names one: the
# field, or the file that is then no JSON.
NOT_FINITE = {
    "a latency of Infinity": (
        set_latency(float("inf")),
        ("latency_seconds", "results.jsonl"),
    ),
    "a latency of -Infinity": (
        set_latency(float("-inf")),
        ("latency_seconds", "results.jsonl"),
    ),
    "a latency of NaN": (set_latency(float("nan")), ("latency_seconds", "results.jsonl")),
    "a cost of NaN": (set_cost(float("nan")), ("cost_usd", "results.jsonl")),
    "a cost of Infinity": (set_cost(float("inf")), ("cost_usd", "results.jsonl")),
    "an input price of Infinity": (
        set_price("usd_per_million_input_tokens", float("inf")),
        ("usd_per_million_input_tokens", "prices", "run.json"),
    ),
    "an output price of NaN": (
        set_price("usd_per_million_output_tokens", float("nan")),
        ("usd_per_million_output_tokens", "prices", "run.json"),
    ),
    "an input price of NaN": (
        set_price("usd_per_million_input_tokens", float("nan")),
        ("usd_per_million_input_tokens", "prices", "run.json"),
    ),
    "a time limit of Infinity": (
        set_timeout(float("inf")),
        ("timeout_seconds", "limits", "run.json"),
    ),
    "a time limit of NaN": (set_timeout(float("nan")), ("timeout_seconds", "limits", "run.json")),
    "a latency of NaN in the summary": (
        set_summary_number(float("nan")),
        ("p95", "latency_seconds", "summary.json", "summary"),
    ),
    "a latency of Infinity in the summary": (
        set_summary_number(float("inf")),
        ("p95", "latency_seconds", "summary.json", "summary"),
    ),
}


@pytest.fixture
def typed(registry_copy, run_command):
    """Type a command of the program in the temporary repository root."""

    def command(arguments: str):
        return run_command(f"python -m wixqa_rag {arguments}", cwd=registry_copy.root)

    return command


@pytest.fixture(params=NOT_FINITE)
def not_finite(request, registry_copy) -> tuple[str, ...]:
    """`example-a` of the temporary copy with one number that is not finite; the words of
    which a difference names one."""
    change, words = NOT_FINITE[request.param]
    change(registry_copy)
    return words


def assert_failed_not_crashed(result, name: str = "run check") -> None:
    """Exit code 1 and the verdict `failed`: the check was carried out, and no error of the
    program reached either stream."""
    assert result.exit_code == 1, f"{result.stdout}\n{result.stderr}"
    assert result.last_line == f"{name}: failed"
    assert f"{name}: not carried out" not in result.lines
    assert not result.reasons, "a failed check has differences, and no reason"
    assert "Traceback" not in result.stderr, result.stderr
    assert result.settings_printed == ()


# --- The record holds what the tests say it holds ----------------------------------------------


def test_the_changed_record_really_holds_a_number_that_is_not_finite(registry_copy):
    """The ground of the tests below: Python's `json` writes `Infinity` and `NaN` into the
    files of the copy, and reads them back."""
    set_latency(float("inf"))(registry_copy)
    set_price("usd_per_million_input_tokens", float("nan"))(registry_copy)

    assert b'"latency_seconds": Infinity' in registry_copy.file(RUN_A, "results.jsonl").read_bytes()
    assert b"NaN" in registry_copy.file(RUN_A, "run.json").read_bytes()
    assert registry_copy.entries(RUN_A)[2]["latency_seconds"] == float("inf")


# --- The check of one run ----------------------------------------------------------------------


def test_the_check_of_a_run_with_a_number_that_is_not_finite_fails(typed, not_finite):
    """FR-022 and data-model.md, differences 1 and 2: the record has a defect, so its check
    fails with exit code 1 and a `difference:` line that names the field, or the file that
    is no JSON. It does not end as not carried out."""
    result = typed(f"run check {DIRECTORIES} --run {RUN_A}")

    assert_failed_not_crashed(result)
    assert result.lines[0] == f"run: {RUN_A}"
    assert any(any(word in text for word in not_finite) for text in result.differences), (
        f"a `difference:` line names one of {not_finite}; got {result.differences}"
    )


def test_examine_does_not_raise_for_a_number_that_is_not_finite(
    registry_copy, not_finite, monkeypatch
):
    """contracts/harness.md, `examine`: the check of `run check` for one record, without
    printing. It raises `RunNotFound` for a run that does not exist, and for nothing that a
    record holds: the defect is a difference."""
    runs = importlib.import_module("wixqa_rag.runs")
    monkeypatch.chdir(registry_copy.root)

    examination = runs.examine(RUN_A, registry_copy.runs_dir, registry_copy.sets_dir)

    assert any(any(word in text for word in not_finite) for text in examination.differences), list(
        examination.differences
    )


# --- The check of the registry (FR-024) --------------------------------------------------------


def test_the_registry_counts_a_run_with_a_number_that_is_not_finite_as_failed(typed, not_finite):
    """FR-024: "The check of the registry MUST check every run in it and MUST report the
    number of runs and the number of runs that failed." One record of the four has the
    defect. `example-b` names it as its baseline and fails with it (data-model.md, difference
    13); the two runs on the held-out set pass."""
    result = typed(f"run check {DIRECTORIES}")

    assert_failed_not_crashed(result)
    assert result.lines[:2] == ["runs: 4", "failed runs: 2"]
    assert result.lines[2].startswith("runs on golden sets: ")
    assert result.lines[3] == "runs on held-out sets: 2"
    assert any(text.startswith(f"{RUN_A}: ") for text in result.differences)
    assert any(text.startswith(f"{RUN_B}: the baseline {RUN_A} ") for text in result.differences)
    assert not any(text.startswith(f"{RUN_C}: ") for text in result.differences)


@pytest.mark.parametrize("value", [float("inf"), float("nan")], ids=["Infinity", "NaN"])
def test_the_registry_counts_exactly_the_one_run_as_failed(registry_copy, typed, value):
    """The same for a run that no other run names: `example-c` gets a latency that is not
    finite. `runs: 4`, `failed runs: 1`, exit code 1."""
    registry_copy.change_entries(RUN_C, lambda rows: rows[0].update(latency_seconds=value))

    result = typed(f"run check {DIRECTORIES}")

    assert_failed_not_crashed(result)
    assert result.lines[:4] == [
        "runs: 4",
        "failed runs: 1",
        "runs on golden sets: 2",
        "runs on held-out sets: 2",
    ]
    assert result.differences and all(
        text.startswith(f"{RUN_C}: ") for text in result.differences
    ), result.differences
    assert any("latency_seconds" in text or "results.jsonl" in text for text in result.differences)


# --- The experiment run whose baseline has the defect ------------------------------------------


def test_the_check_of_an_experiment_whose_baseline_has_such_a_number_fails(typed, not_finite):
    """data-model.md, difference 13: the baseline's "own record has one of the differences 1
    to 12". The check of `example-b` is carried out and fails."""
    result = typed(f"run check {DIRECTORIES} --run {RUN_B}")

    assert_failed_not_crashed(result)
    assert any(text.startswith(f"the baseline {RUN_A} ") for text in result.differences), (
        result.differences
    )


# --- No report and no comparison (FR-025) ------------------------------------------------------


def test_no_report_is_made_from_a_run_with_a_number_that_is_not_finite(typed, not_finite):
    """FR-025 and contracts/cli.md, "`run report`": the record does not pass its check, so
    the report is refused with `reason: the run check failed for <ID>`. It is not "not
    carried out", and no number is printed."""
    result = typed(f"run report {DIRECTORIES} --run {RUN_A}")

    assert result.exit_code == 2, f"{result.stdout}\n{result.stderr}"
    assert result.reasons == [f"the run check failed for {RUN_A}"]
    assert result.last_line == "run report: refused"
    assert not any(line.startswith(("status,", "latency_seconds,")) for line in result.lines)
    assert "Traceback" not in result.stderr, result.stderr


@pytest.mark.parametrize("order", ["first", "second"])
def test_no_comparison_is_made_from_a_run_with_a_number_that_is_not_finite(
    typed, not_finite, order
):
    """FR-025 and contracts/cli.md, "`run compare`": refused with `reason: the run check
    failed for <ID>`, whichever of the two runs has the defect. `example-d` does not name
    `example-a`, so the other record of each pair passes."""
    sound = "20261104T100000Z-example-d"
    first, second = (RUN_A, sound) if order == "first" else (sound, RUN_A)

    result = typed(f"run compare {DIRECTORIES} --first {first} --second {second}")

    assert result.exit_code == 2, f"{result.stdout}\n{result.stderr}"
    assert result.reasons == [f"the run check failed for {RUN_A}"]
    assert result.last_line == "run compare: refused"
    assert "Traceback" not in result.stderr, result.stderr


# --- A token count that is too large to compute with -------------------------------------------


@pytest.fixture(params=["input_tokens", "output_tokens"])
def huge_count(request, registry_copy) -> str:
    """`example-a` of the temporary copy, in which one token count of `hxa-001` is 10**400."""
    registry_copy.change_entries(
        RUN_A, lambda rows: rows[0]["tokens"][0].update({request.param: HUGE})
    )
    assert registry_copy.entries(RUN_A)[0]["tokens"][0][request.param] == HUGE
    return request.param


def test_the_check_of_a_run_with_a_huge_token_count_is_carried_out_and_fails(typed, huge_count):
    """data-model.md, `tokens`: "whole numbers of 0 or more", without an upper limit, so the
    count is a valid count. Difference 9: the recorded `cost_usd` of `hxa-001`, 0.0012, is
    not the cost that 10**400 tokens and the prices give, so the record fails, and a
    `difference:` line names the question. The check does not end as not carried out."""
    result = typed(f"run check {DIRECTORIES} --run {RUN_A}")

    assert_failed_not_crashed(result)
    assert any("hxa-001" in text for text in result.differences), result.differences


def test_the_registry_counts_a_run_with_a_huge_token_count(typed, huge_count):
    """FR-024: the four lines are printed, and the run is one of the failed runs, together
    with the experiment run that names it as its baseline."""
    result = typed(f"run check {DIRECTORIES}")

    assert_failed_not_crashed(result)
    assert result.lines[:2] == ["runs: 4", "failed runs: 2"]


def test_no_report_is_made_from_a_run_with_a_huge_token_count(typed, huge_count):
    """FR-025: the report is refused, as for every record that fails its check."""
    result = typed(f"run report {DIRECTORIES} --run {RUN_A}")

    assert result.exit_code == 2, f"{result.stdout}\n{result.stderr}"
    assert result.reasons == [f"the run check failed for {RUN_A}"]
    assert result.last_line == "run report: refused"


def test_a_huge_token_count_is_written_as_a_whole_number(registry_copy, huge_count):
    """The ground of the three tests above: the file holds the count as a whole number of
    401 digits, which is JSON."""
    line = registry_copy.file(RUN_A, "results.jsonl").read_text(encoding="utf-8").split("\n")[0]

    assert "1" + "0" * 400 in line
    assert json.loads(line)["tokens"][0][huge_count] == HUGE
