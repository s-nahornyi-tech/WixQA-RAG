"""Acceptance test of check AC-031 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run compare --runs-dir tests/data/runs --sets-dir tests/data/sets
      --first 20261101T100000Z-example-a --second 20261103T100000Z-example-c

(one line)

→ exit code 2 and the line `run compare: refused`, with a reason that names the question sets
`harness` and `harness-hxc`.

Covers US4, FR-029, FR-033 and SC-005.

The first run is on the golden set `harness` and the second on the held-out set
`harness-hxc`; both records pass their check. contracts/cli.md, "`run compare`", fixes the
wording of the reason. The command reads the two run records and the question-set records and
writes nothing. The test needs neither the store, the provider nor the dataset host and
carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag run compare --runs-dir tests/data/runs --sets-dir tests/data/sets"
    " --first 20261101T100000Z-example-a --second 20261103T100000Z-example-c"
)


def test_ac_031_two_runs_on_different_question_sets_are_not_compared(run_command):
    """AC-031: questions of different sets are never put into one number; the comparison is
    refused and names both sets."""
    result = run_command(COMMAND)

    assert result.exit_code == 2, (
        f"AC-031: exit code 2 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "run compare: refused" in result.lines, (
        "AC-031: the output contains the line `run compare: refused`"
    )
    assert result.last_line == "run compare: refused"
    assert "the runs are on different question sets: harness and harness-hxc" in result.reasons, (
        "AC-031: a `reason:` line names the question sets `harness` and `harness-hxc`; "
        f"got {result.reasons}"
    )
