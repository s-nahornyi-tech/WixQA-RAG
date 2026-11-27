"""Acceptance test of check AC-008 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets
      --version harness-other-gold

(one line)

→ exit code 1, the line `set check: failed`, and a `difference:` line that names `hxa-003` and
the article `hx-003`.

Covers US1, FR-006 and SC-004.

In `harness-other-gold` the only gold article of `hxa-003` is `hx-001`; the dataset gives
`hx-001` and `hx-003` (data-model.md, "Example data"). The command reads the two directories
and writes nothing. The test needs neither the store, the provider nor the dataset host and
carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets"
    " --version harness-other-gold"
)


def test_ac_008_gold_articles_that_differ_from_the_dataset_are_named(run_command):
    """AC-008: the check fails and names the question and the gold article that differs."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-008: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "set check: failed" in result.lines, (
        "AC-008: the output contains the line `set check: failed`"
    )
    assert result.last_line == "set check: failed"
    assert any("hxa-003" in text and "hx-003" in text for text in result.differences), (
        "AC-008: a `difference:` line names `hxa-003` and the article `hx-003`; "
        f"got {result.differences}"
    )
