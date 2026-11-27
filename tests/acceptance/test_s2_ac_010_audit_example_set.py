"""Acceptance test of check AC-010 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag index build --data-dir tests/data/example --index example
    && python -m wixqa_rag index audit --data-dir tests/data/example --index example
       --sets-dir tests/data/sets --set example

(one line)

→ exit code 0; the output contains `question set: example (golden)`, `questions: 3`,
`unknown question references: 0` and `audit: passed`.

Covers US1 and FR-008.

The build embeds the five example passages with the provider, unless an earlier test of the
same run has already built `example`; the test needs the store and the provider key and runs
in the scope `example` on GitHub Actions. The audit reads the record
`tests/data/sets/example.json`. The audit result goes to `data/audits/` of the checkout,
which Git ignores.
"""

import pytest

pytestmark = [pytest.mark.store, pytest.mark.provider]

COMMAND = (
    "python -m wixqa_rag index build --data-dir tests/data/example --index example"
    " && python -m wixqa_rag index audit --data-dir tests/data/example --index example"
    " --sets-dir tests/data/sets --set example"
)

EXPECTED_LINES = (
    "question set: example (golden)",
    "questions: 3",
    "unknown question references: 0",
    "audit: passed",
)


def test_ac_010_the_audit_takes_a_question_set_as_its_question_set(run_command):
    """AC-010: the audit of the example index with the question set `example` names the set
    and checks the gold articles of its three questions."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-010: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in EXPECTED_LINES:
        assert line in result.lines, f"AC-010: the output contains the line `{line}`"
