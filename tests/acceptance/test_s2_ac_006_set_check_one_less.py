"""Acceptance test of check AC-006 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets
      --version harness-one-less

(one line)

→ exit code 1, the line `set check: failed`, and a `difference:` line that names `hxb-003` as
selected by the rule and not in the question set.

Covers US1, FR-006 and SC-004.

`harness-one-less` is `harness` without `hxb-003`, which its rule selects (data-model.md,
"Example data"). contracts/cli.md, "`set check`", fixes the wording of the line. The command
reads the two directories and writes nothing. The test needs neither the store, the provider
nor the dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets"
    " --version harness-one-less"
)


def test_ac_006_a_question_that_the_rule_selects_and_the_set_lacks_is_named(run_command):
    """AC-006: the check fails and names the question that is missing from the record."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-006: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "set check: failed" in result.lines, (
        "AC-006: the output contains the line `set check: failed`"
    )
    assert result.last_line == "set check: failed"
    expected = "hxb-003 is selected by the rule and is not in the question set"
    assert expected in result.differences, (
        "AC-006: a `difference:` line names `hxb-003` as selected by the rule and not in the "
        f"question set; got {result.differences}"
    )
