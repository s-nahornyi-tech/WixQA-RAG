"""Acceptance test of check AC-035 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets
      --version harness-half-swapped

(one line)

→ exit code 1, the line `set check: failed`, and exactly two `difference:` lines, each naming
a question of `hxa`: one selected by the rule and not in the question set, one in the
question set and not selected by the rule.

Covers US1, FR-006 and SC-004.

`harness-half-swapped` is `harness-half` with `hxa-005`, which the draw with the seed 7
selects, replaced by `hxa-001`, which it does not select (data-model.md, the table of the eight
draw keys and "What the checks of the four records around the draw find"). The command reads
the two directories and writes nothing. The test needs neither the store, the provider nor the
dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets"
    " --version harness-half-swapped"
)


def test_ac_035_a_swapped_question_gives_exactly_two_differences(run_command):
    """AC-035: the draw is made again with the recorded seed, and the check names both questions."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-035: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "set check: failed" in result.lines, (
        "AC-035: the output contains the line `set check: failed`"
    )
    assert result.last_line == "set check: failed"
    assert len(result.differences) == 2, (
        f"AC-035: exactly two `difference:` lines; got {result.differences}"
    )
    assert all("hxa-" in text for text in result.differences), (
        "AC-035: each `difference:` line names a question of `hxa`"
    )
    assert sorted(result.differences) == [
        "hxa-001 is in the question set and is not selected by the rule",
        "hxa-005 is selected by the rule and is not in the question set",
    ], (
        "AC-035: one question selected by the rule and not in the question set, one in the "
        f"question set and not selected by the rule; got {result.differences}"
    )
