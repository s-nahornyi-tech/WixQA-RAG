"""Acceptance test of check AC-011 (specs/001-corpus-and-audit/spec.md, "Acceptance Checks").

    python -m wixqa_rag index build --data-dir tests/data/example --index example
    && python -m wixqa_rag index audit --data-dir tests/data/example-unknown-reference
       --index example

(one line)

→ exit code 1; the output contains `unknown question references: 1`, the question
`exq-003`, the id `ex-999` and `audit: failed`.

Covers US3, FR-013, FR-014 and SC-003.

In `example-unknown-reference` the question `exq-003` also names the article `ex-999`, which no
index holds. The build embeds the five example passages with the provider, unless an earlier test of
the same run has already built `example`; the test needs the store and the provider key and
runs in the scope `example` on GitHub Actions. The audit result goes to `data/audits/` of
the checkout, which Git ignores.
"""

import pytest

pytestmark = [pytest.mark.store, pytest.mark.provider]

COMMAND = (
    "python -m wixqa_rag index build --data-dir tests/data/example --index example"
    " && python -m wixqa_rag index audit --data-dir tests/data/example-unknown-reference"
    " --index example"
)


def test_ac_011_a_question_reference_outside_the_index_is_named(run_command):
    """AC-011: a question whose `article_ids` names an article that the index does not hold;
    the audit fails and names the question and the article id."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-011: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "unknown question references: 1" in result.lines, (
        "AC-011: the output contains the line `unknown question references: 1`"
    )
    assert any("exq-003" in line for line in result.lines), "AC-011: the output names `exq-003`"
    assert any("ex-999" in line for line in result.lines), "AC-011: the output names `ex-999`"
    assert "audit: failed" in result.lines, "AC-011: the output contains `audit: failed`"
