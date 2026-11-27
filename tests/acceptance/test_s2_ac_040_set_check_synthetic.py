"""Acceptance test of check AC-040 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set check --version synthetic-001

→ exit code 0; the output contains `role: held-out`, `seed: 20261127`,
`wixqa_synthetic: 300`, `questions: 300`, `questions without gold articles: 0` and
`set check: passed`.

Covers US1, FR-006, FR-007 and SC-001.

The command checks the synthetic held-out set against the default data directory. The test
has no fixture that fetches or builds: it relies on the copy of the dataset that the test of
spec 1's AC-001 left and on the record `evals/golden/synthetic-001.json`, which the test of
AC-038 wrote before it in the same run or which is in the checkout (tasks.md, "How the tests
are run"). It runs only in the scope `full` on GitHub Actions.
"""

import pytest

pytestmark = pytest.mark.real_data

COMMAND = "python -m wixqa_rag set check --version synthetic-001"

EXPECTED_LINES = (
    "role: held-out",
    "seed: 20261127",
    "wixqa_synthetic: 300",
    "questions: 300",
    "questions without gold articles: 0",
    "set check: passed",
)


def test_ac_040_the_synthetic_held_out_set_passes_its_check(run_command):
    """AC-040: the synthetic held-out set is what its rule selects from the pinned dataset."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-040: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in EXPECTED_LINES:
        assert line in result.lines, f"AC-040: the output contains the line `{line}`"
