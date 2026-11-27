"""Acceptance test of check AC-028 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run check --runs-dir tests/data/runs --sets-dir tests/data/sets
      --run 20261101T100000Z-no-such-run

(one line)

→ exit code 2 and the line `run check: not carried out`, with the reason that the run
`20261101T100000Z-no-such-run` does not exist.

Covers US3 and FR-030.

The identifier has the form of a run identifier, and `tests/data/runs` holds no run of that
name. contracts/cli.md, "`run check`", fixes the wording of the reason. The command reads the
run record and the question-set record and writes nothing. The test needs neither the store,
the provider nor the dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag run check --runs-dir tests/data/runs --sets-dir tests/data/sets"
    " --run 20261101T100000Z-no-such-run"
)


def test_ac_028_a_run_that_does_not_exist_is_not_checked(run_command):
    """AC-028: a check that cannot be made is reported as not carried out, never as passed or as
    failed."""
    result = run_command(COMMAND)

    assert result.exit_code == 2, (
        f"AC-028: exit code 2 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "run check: not carried out" in result.lines, (
        "AC-028: the output contains the line `run check: not carried out`"
    )
    assert result.last_line == "run check: not carried out"
    assert "run 20261101T100000Z-no-such-run does not exist in tests/data/runs" in result.reasons, (
        "AC-028: a `reason:` line says that the run `20261101T100000Z-no-such-run` does not exist; "
        f"got {result.reasons}"
    )
