"""Acceptance test of check AC-008 (specs/001-corpus-and-audit/spec.md, "Acceptance Checks").

    python -m wixqa_rag index audit --index wixqa-001

→ exit code 0; the output contains `missing from index: 0`, `not in corpus: 0`,
`unknown question references: 0` and `audit: passed`.

Covers US3, FR-011, FR-012, FR-013, FR-014, FR-016 and SC-001.

The command audits the index of the published dataset against the fetched dataset. The test
has no fixture that fetches or builds: it relies on the copy that the test of AC-001 left
and on the index that the test of AC-004 built or that the workflow restored (tasks.md, "How
the tests are run"). It runs only in the scope `full` on GitHub Actions. The audit calls no
provider, so the test carries `real_data` and `store` only. The audit result goes to
`data/audits/` of the checkout, which Git ignores.
"""

import pytest

pytestmark = [pytest.mark.real_data, pytest.mark.store]

COMMAND = "python -m wixqa_rag index audit --index wixqa-001"

EXPECTED_LINES = (
    "missing from index: 0",
    "not in corpus: 0",
    "unknown question references: 0",
    "audit: passed",
)


def test_ac_008_the_audit_of_the_real_index_reports_zero_mismatches(run_command):
    """AC-008 and SC-001: no article missing from the index, no article in the index that is
    not in the corpus, and no question reference outside the index."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-008: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in EXPECTED_LINES:
        assert line in result.lines, f"AC-008: the output contains the line `{line}`"
