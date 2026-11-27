"""Acceptance test of check AC-036 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets
      --version harness-half-rest-overlap

(one line)

→ exit code 1; the output contains `in both sets: 1`, `in neither set: 1` and
`set check: failed`.

Covers US1, FR-032 and SC-004.

`harness-half-rest-overlap` is the complement `harness-half-rest` with `hxa-004` replaced by
`hxa-002`, which is in `harness-half` (data-model.md, "Example data"). The command reads the
two directories and writes nothing. The test needs neither the store, the provider nor the
dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets"
    " --version harness-half-rest-overlap"
)


def test_ac_036_a_complement_that_overlaps_and_leaves_out_a_question_fails(run_command):
    """AC-036: a held-out set that shares a question with the set it complements and leaves
    out a question of their parts fails its check, and both numbers are reported."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-036: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in ("in both sets: 1", "in neither set: 1", "set check: failed"):
        assert line in result.lines, f"AC-036: the output contains the line `{line}`"
    assert result.last_line == "set check: failed"
