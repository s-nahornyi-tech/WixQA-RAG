"""Acceptance test of check AC-002 (specs/001-corpus-and-audit/spec.md, "Acceptance Checks").

    python -m wixqa_rag dataset check

→ exit code 0 and the line `dataset check: passed`.

Covers US1 and FR-004.

The command checks the default data directory, the local copy of the published dataset. The
test has no fixture that fetches: it relies on the copy that the test of AC-001 left, which
runs before it in the same run (tasks.md, "How the tests are run"). It runs only in the
scope `full` on GitHub Actions (research.md, section 3).
"""

import pytest

pytestmark = pytest.mark.real_data

COMMAND = "python -m wixqa_rag dataset check"


def test_ac_002_the_fetched_dataset_passes_the_dataset_check(run_command):
    """AC-002: the local copy of the pinned dataset passes the dataset check."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-002: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "dataset check: passed" in result.lines, (
        "AC-002: the output contains the line `dataset check: passed`"
    )
