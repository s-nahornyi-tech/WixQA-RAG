"""Acceptance test of check AC-027 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir
      tests/data/sets

(one line)

→ exit code 1; the output contains `runs: 9`, `failed runs: 7` and `run check: failed`.

Covers US3 and FR-024.

`tests/data/runs-invalid` holds two sound records and seven records with one defect each
(data-model.md, "Example data"). The command reads the run record and the question-set record
and writes nothing. The test needs neither the store, the provider nor the dataset host and
carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir tests/data/sets"
)

EXPECTED_LINES = (
    "runs: 9",
    "failed runs: 7",
    "run check: failed",
)


def test_ac_027_the_check_of_a_registry_fails_when_a_run_fails(run_command):
    """AC-027: every run of the registry is checked; the number of runs and the number of runs
    that failed are reported."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-027: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in EXPECTED_LINES:
        assert line in result.lines, f"AC-027: the output contains the line `{line}`"
