"""Acceptance test of check AC-019 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run check --runs-dir tests/data/runs --sets-dir tests/data/sets

→ exit code 0; the output contains `runs: 4`, `failed runs: 0`, `runs on golden sets: 2`, `runs
on held-out sets: 2` and `run check: passed`.

Covers US3, FR-023, FR-024, FR-034 and SC-008.

`tests/data/runs` holds four sound records: two on the golden set `harness`, one of them an
experiment run that names the other as its baseline, and two on the held-out set `harness-hxc`.
The command reads the run record and the question-set record and writes nothing. The test needs
neither the store, the provider nor the dataset host and carries no marker.
"""

COMMAND = "python -m wixqa_rag run check --runs-dir tests/data/runs --sets-dir tests/data/sets"

EXPECTED_LINES = (
    "runs: 4",
    "failed runs: 0",
    "runs on golden sets: 2",
    "runs on held-out sets: 2",
    "run check: passed",
)


def test_ac_019_the_check_of_a_registry_counts_its_runs_and_their_roles(run_command):
    """AC-019: every run of the registry is checked, and the runs on golden sets and on held-out
    sets are counted."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-019: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in EXPECTED_LINES:
        assert line in result.lines, f"AC-019: the output contains the line `{line}`"
