"""Acceptance test of check AC-002 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set check --version golden-001

→ exit code 0; the output contains `role: golden`, `seed: 20261127`,
`wixqa_expertwritten: 100`, `wixqa_simulated: 100`, `questions: 200`,
`questions without gold articles: 0`, a line `single-article:` and a line `multi-article:`
whose two numbers add up to 200, and `set check: passed`.

Covers US1, FR-006, FR-007 and SC-001.

The command checks the golden set against the default data directory. The test has no
fixture that fetches or builds: it relies on the copy of the dataset that the test of spec
1's AC-001 left and on the record `evals/golden/golden-001.json`, which the test of AC-001
of this feature wrote before it in the same run or which is in the checkout (tasks.md, "How
the tests are run"). It runs only in the scope `full` on GitHub Actions.
"""

import re

import pytest

pytestmark = pytest.mark.real_data

COMMAND = "python -m wixqa_rag set check --version golden-001"

EXPECTED_LINES = (
    "role: golden",
    "seed: 20261127",
    "wixqa_expertwritten: 100",
    "wixqa_simulated: 100",
    "questions: 200",
    "questions without gold articles: 0",
    "set check: passed",
)


def number_of(lines: list[str], name: str) -> int:
    """The whole number of the one result line `name: <number>`."""
    values = [line[len(name) + 2 :] for line in lines if line.startswith(f"{name}: ")]
    assert len(values) == 1, f"AC-002: one line `{name}:` expected; got {values}"
    assert re.fullmatch(r"\d+", values[0]), f"AC-002: `{name}:` gives a whole number"
    return int(values[0])


def test_ac_002_the_golden_set_passes_its_check(run_command):
    """AC-002: the golden set is what its rule selects from the pinned dataset, and the
    check reports its role, its seed and its numbers."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-002: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in EXPECTED_LINES:
        assert line in result.lines, f"AC-002: the output contains the line `{line}`"
    single = number_of(result.lines, "single-article")
    multi = number_of(result.lines, "multi-article")
    assert single + multi == 200, (
        "AC-002: the numbers of the lines `single-article:` and `multi-article:` add up to "
        f"200; got {single} and {multi}"
    )
