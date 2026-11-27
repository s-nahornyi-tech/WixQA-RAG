"""Acceptance test of check AC-007 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets
      --version harness-one-more

(one line)

→ exit code 1, the line `set check: failed`, and a `difference:` line that names `hxc-001` as
in the question set and not selected by the rule.

Covers US1, FR-006 and SC-004.

`harness-one-more` is `harness` with `hxc-001` added, which its rule does not select
(data-model.md, "Example data"). contracts/cli.md, "`set check`", fixes the wording of the
line. The command reads the two directories and writes nothing. The test needs neither the
store, the provider nor the dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets"
    " --version harness-one-more"
)


def test_ac_007_a_question_that_the_rule_does_not_select_is_named(run_command):
    """AC-007: the check fails and names the question that the rule does not select."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-007: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "set check: failed" in result.lines, (
        "AC-007: the output contains the line `set check: failed`"
    )
    assert result.last_line == "set check: failed"
    expected = "hxc-001 is in the question set and is not selected by the rule"
    assert expected in result.differences, (
        "AC-007: a `difference:` line names `hxc-001` as in the question set and not selected "
        f"by the rule; got {result.differences}"
    )
