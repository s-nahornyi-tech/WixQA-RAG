"""Acceptance test of check AC-039 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set check --version held-out-001

→ exit code 0; the output contains `role: held-out`, `complement of: golden-001`,
`wixqa_expertwritten: 100`, `wixqa_simulated: 100`, `questions: 200`, `in both sets: 0`,
`in neither set: 0`, a line `question texts in both sets:`,
`questions without gold articles: 0` and `set check: passed`.

Covers US1, FR-006, FR-007, FR-032 and SC-001.

The command checks the held-out set against the default data directory and against the
golden set that it complements. The test has no fixture that fetches or builds: it relies
on the copy of the dataset that the test of spec 1's AC-001 left and on the records
`golden-001` and `held-out-001` under `evals/golden/`, which the tests of AC-001 and AC-037
wrote before it in the same run or which are in the checkout (tasks.md, "How the tests are
run"). It runs only in the scope `full` on GitHub Actions.
"""

import pytest

pytestmark = pytest.mark.real_data

COMMAND = "python -m wixqa_rag set check --version held-out-001"

EXPECTED_LINES = (
    "role: held-out",
    "complement of: golden-001",
    "wixqa_expertwritten: 100",
    "wixqa_simulated: 100",
    "questions: 200",
    "in both sets: 0",
    "in neither set: 0",
    "questions without gold articles: 0",
    "set check: passed",
)


def test_ac_039_the_held_out_set_passes_its_check(run_command):
    """AC-039: the held-out set shares no question with the golden set, leaves out none of
    the two parts, and the check reports the number of question texts in both sets."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-039: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in EXPECTED_LINES:
        assert line in result.lines, f"AC-039: the output contains the line `{line}`"
    assert any(line.startswith("question texts in both sets:") for line in result.lines), (
        "AC-039: the output contains a line `question texts in both sets:`"
    )
