"""Acceptance test of check AC-023 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir
      tests/data/sets --run 20261101T100300Z-unknown-status

(one line)

→ exit code 1, the line `run check: failed`, and a `difference:` line that names `hxa-004` and
the status `skipped`.

Covers US3, FR-014, FR-022 and SC-004.

The record is `example-a` under an identifier of its own, and the status of `hxa-004` is
`skipped`, which is none of the five statuses. contracts/cli.md, "`run check`", fixes the
wording of the line. The command reads the run record and the question-set record and writes
nothing. The test needs neither the store, the provider nor the dataset host and carries no
marker.
"""

COMMAND = (
    "python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir"
    " tests/data/sets --run 20261101T100300Z-unknown-status"
)

EXPECTED = "hxa-004 has the status skipped, which is not one of the five"


def test_ac_023_a_status_that_is_not_one_of_the_five_is_named(run_command):
    """AC-023: every question has exactly one of the five statuses; another status is named with
    its question."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-023: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "run check: failed" in result.lines, (
        "AC-023: the output contains the line `run check: failed`"
    )
    assert result.last_line == "run check: failed"
    assert EXPECTED in result.differences, (
        "AC-023: a `difference:` line names `hxa-004` and the status `skipped`; "
        f"got {result.differences}"
    )
