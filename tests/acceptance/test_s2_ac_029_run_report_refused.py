"""Acceptance test of check AC-029 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run report --runs-dir tests/data/runs-invalid --sets-dir
      tests/data/sets --run 20261101T100500Z-stale-summary

(one line)

→ exit code 2 and the line `run report: refused`, with the reason that the run check failed.

Covers US3 and FR-025.

The summary of the record states a number that its results do not give, so the record does not
pass its check, and no report is made from it. contracts/cli.md, "`run report`", fixes the
wording of the reason. The command reads the run record and the question-set record and writes
nothing. The test needs neither the store, the provider nor the dataset host and carries no
marker.
"""

COMMAND = (
    "python -m wixqa_rag run report --runs-dir tests/data/runs-invalid --sets-dir"
    " tests/data/sets --run 20261101T100500Z-stale-summary"
)


def test_ac_029_no_report_is_made_from_a_record_that_fails_its_check(run_command):
    """AC-029: a report is made only from a record that passes the check; otherwise it is refused,
    with the reason."""
    result = run_command(COMMAND)

    assert result.exit_code == 2, (
        f"AC-029: exit code 2 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "run report: refused" in result.lines, (
        "AC-029: the output contains the line `run report: refused`"
    )
    assert result.last_line == "run report: refused"
    assert "the run check failed for 20261101T100500Z-stale-summary" in result.reasons, (
        f"AC-029: a `reason:` line says that the run check failed; got {result.reasons}"
    )
