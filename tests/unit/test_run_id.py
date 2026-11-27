"""The run identifier (task T079): `run_id` and `is_valid_run_id` of `src/wixqa_rag/runs.py`.

Covers:

- spec.md, FR-018: "A run identifier MUST consist of the run's start time in UTC, to the
  second, a hyphen, and a short name of lower-case letters, digits and single hyphens, for
  example `20261201T093000Z-baseline`";
- data-model.md, "Run identifier": the time in the form `20261201T093000Z`; the name starts
  and ends with a letter or a digit and has at most 40 characters;
- contracts/harness.md, "`wixqa_rag.runs`": the names below, and no other.

    run_id(started_at, name) -> str        # ValueError for a name of another form or a time
                                           # without a time zone
    is_valid_run_id(text) -> bool

All documents named here are in specs/002-evaluation-harness/.
"""

import importlib
from datetime import UTC, datetime, timedelta, timezone

import pytest


def load_runs():
    """Import the module; it fails while `src/wixqa_rag/runs.py` does not exist (plan.md,
    "Project Structure")."""
    return importlib.import_module("wixqa_rag.runs")


# --- `run_id` ----------------------------------------------------------------------------------


def test_run_id_of_the_example_of_the_contract():
    """contracts/harness.md: `runs.run_id(datetime(2026, 12, 1, 9, 30, tzinfo=UTC),
    "baseline")` is `"20261201T093000Z-baseline"`."""
    assert load_runs().run_id(datetime(2026, 12, 1, 9, 30, tzinfo=UTC), "baseline") == (
        "20261201T093000Z-baseline"
    )


@pytest.mark.parametrize(
    ("started_at", "name", "identifier"),
    [
        (datetime(2026, 11, 1, 10, 0, 0, tzinfo=UTC), "example-a", "20261101T100000Z-example-a"),
        (datetime(2026, 11, 1, 10, 1, 0, tzinfo=UTC), "no-latency", "20261101T100100Z-no-latency"),
        (datetime(2027, 1, 2, 3, 4, 5, tzinfo=UTC), "a", "20270102T030405Z-a"),
        (datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC), "top-k-10", "20261231T235959Z-top-k-10"),
        (datetime(2026, 12, 1, 0, 0, 0, tzinfo=UTC), "x" * 40, "20261201T000000Z-" + "x" * 40),
        (datetime(2026, 12, 1, 9, 30, tzinfo=UTC), "7", "20261201T093000Z-7"),
    ],
)
def test_run_id_is_the_start_time_a_hyphen_and_the_name(started_at, name, identifier):
    """FR-018 and data-model.md, "Run identifier": the start time in UTC to the second, in
    the form `20261201T093000Z`, a hyphen, and the name."""
    assert load_runs().run_id(started_at, name) == identifier


@pytest.mark.parametrize(
    "started_at",
    [
        datetime(2026, 12, 1, 11, 30, tzinfo=timezone(timedelta(hours=2))),
        datetime(2026, 12, 1, 4, 30, tzinfo=timezone(timedelta(hours=-5))),
        datetime(2026, 12, 1, 15, 0, tzinfo=timezone(timedelta(hours=5, minutes=30))),
    ],
)
def test_run_id_states_the_start_time_in_utc(started_at):
    """FR-018: "the run's start time in UTC": a time with another time zone is the same
    moment, written in UTC."""
    assert load_runs().run_id(started_at, "baseline") == "20261201T093000Z-baseline"


def test_run_id_states_the_start_time_to_the_second():
    """FR-018: "to the second": a part of a second is left out, not rounded up."""
    started_at = datetime(2026, 12, 1, 9, 30, 59, 999_999, tzinfo=UTC)

    assert load_runs().run_id(started_at, "baseline") == "20261201T093059Z-baseline"


def test_run_id_raises_value_error_for_a_time_without_a_time_zone():
    """contracts/harness.md, `run_id`: "Raises `ValueError` for ... a time without a time
    zone": such a time does not say which moment it is."""
    with pytest.raises(ValueError):
        load_runs().run_id(datetime(2026, 12, 1, 9, 30), "baseline")


@pytest.mark.parametrize(
    "name",
    [
        "",
        "Baseline",
        "BASELINE",
        "base_line",
        "base line",
        "two--hyphens",
        "-baseline",
        "baseline-",
        "-",
        "baseline.json",
        "runs/baseline",
        "bäseline",
        "baseline\n",
        "x" * 41,
    ],
)
def test_run_id_raises_value_error_for_a_name_of_another_form(name):
    """contracts/harness.md, `run_id`: "Raises `ValueError` for a name of another form".
    data-model.md: lower-case letters, digits and single hyphens; it starts and ends with a
    letter or a digit; at most 40 characters."""
    with pytest.raises(ValueError):
        load_runs().run_id(datetime(2026, 12, 1, 9, 30, tzinfo=UTC), name)


# --- `is_valid_run_id` -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "20261201T093000Z-baseline",
        "20261101T100000Z-example-a",
        "20261101T100600Z-two-changes",
        "20261103T100100Z-experiment-on-held-out",
        "20261101T100000Z-no-such-run",
        "20270102T030405Z-a",
        "20261201T093000Z-7",
        "20261201T093000Z-top-k-10",
        "20261201T093000Z-" + "x" * 40,
    ],
)
def test_is_valid_run_id_accepts_the_form(text):
    """FR-018: the identifiers of the example registries and of the documents."""
    assert load_runs().is_valid_run_id(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "",
        "baseline",
        "example-a",
        "not-a-run",
        "20261201T093000Z",
        "20261201T093000Z-",
        "20261201T093000Zbaseline",
        "20261201T093000Z_baseline",
        "20261201T093000-baseline",
        "20261201t093000z-baseline",
        "2026-12-01T09:30:00Z-baseline",
        "20261201-093000Z-baseline",
        "20261201T0930Z-baseline",
        "202612011T093000Z-baseline",
        "20261201T093000Z-Baseline",
        "20261201T093000Z-base_line",
        "20261201T093000Z-two--hyphens",
        "20261201T093000Z--baseline",
        "20261201T093000Z-baseline-",
        "20261201T093000Z-base line",
        "20261201T093000Z-baseline\n",
        " 20261201T093000Z-baseline",
        "20261201T093000Z-" + "x" * 41,
        "runs/20261201T093000Z-baseline",
        ".gitkeep",
    ],
)
def test_is_valid_run_id_rejects_every_other_text(text):
    """FR-018 and data-model.md, "Run identifier": no time, no name, a time of another form,
    and a name of another form."""
    assert load_runs().is_valid_run_id(text) is False


def test_what_run_id_gives_is_a_valid_run_id():
    """The two functions agree: an identifier that `run_id` gives has the form."""
    runs = load_runs()

    identifier = runs.run_id(datetime(2026, 12, 1, 9, 30, tzinfo=UTC), "baseline-2")

    assert runs.is_valid_run_id(identifier) is True


def test_the_names_of_the_three_files_of_a_run_record():
    """contracts/harness.md: `RUN_FILE`, `RESULTS_FILE` and `SUMMARY_FILE` are `"run.json"`,
    `"results.jsonl"` and `"summary.json"` (contracts/records.md, "Run record")."""
    runs = load_runs()

    assert (runs.RUN_FILE, runs.RESULTS_FILE, runs.SUMMARY_FILE) == (
        "run.json",
        "results.jsonl",
        "summary.json",
    )
