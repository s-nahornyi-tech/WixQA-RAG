"""Acceptance test of check AC-009 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag index audit --index wixqa-001 --set golden-001

→ exit code 0; the output contains `question set: golden-001 (golden)`, `questions: 200`,
`missing from index: 0`, `not in corpus: 0`, `unknown question references: 0` and
`audit: passed`.

Covers US1, FR-008 and SC-002.

The command audits the index of the published dataset with the golden set as its question
set. The test has no fixture that fetches or builds: it relies on the copy of the dataset
that the test of spec 1's AC-001 left, on the index `wixqa-001` that the workflow restored
from its snapshot, and on the record `evals/golden/golden-001.json` that the test of AC-001
of this feature wrote or that is in the checkout (tasks.md, "How the tests are run"). It
runs only in the scope `full` on GitHub Actions. The audit calls no provider, so the test
carries `real_data` and `store` only. The audit result goes to `data/audits/` of the
checkout, which Git ignores.
"""

import pytest

pytestmark = [pytest.mark.real_data, pytest.mark.store]

COMMAND = "python -m wixqa_rag index audit --index wixqa-001 --set golden-001"

EXPECTED_LINES = (
    "question set: golden-001 (golden)",
    "questions: 200",
    "missing from index: 0",
    "not in corpus: 0",
    "unknown question references: 0",
    "audit: passed",
)


def test_ac_009_every_gold_article_of_the_golden_set_is_in_the_index(run_command):
    """AC-009 and SC-002: the audit takes the golden set as its question set and finds
    every gold article of its 200 questions in the index."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-009: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in EXPECTED_LINES:
        assert line in result.lines, f"AC-009: the output contains the line `{line}`"
