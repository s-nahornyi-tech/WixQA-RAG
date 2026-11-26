"""Acceptance test of check AC-001 (specs/001-corpus-and-audit/spec.md, "Acceptance Checks").

    python -m wixqa_rag dataset fetch && python -m wixqa_rag dataset fetch

→ exit code 0; the output names the pinned revision and contains the lines
`wix_kb_corpus: 6221`, `wixqa_expertwritten: 200`, `wixqa_simulated: 200` and
`wixqa_synthetic: 6221`; the second fetch prints `nothing downloaded`.

Covers US1, FR-001, FR-002, FR-003 and SC-002.

The test needs the dataset host, so it runs only in the scope `full` on GitHub Actions
(research.md, section 3). It has no fixture: it fetches into `data/` of the checkout, which
Git ignores, and the test of AC-002 relies on the copy it leaves.
"""

import json

import pytest

pytestmark = pytest.mark.real_data

COMMAND = "python -m wixqa_rag dataset fetch && python -m wixqa_rag dataset fetch"

ROW_COUNT_LINES = (
    "wix_kb_corpus: 6221",
    "wixqa_expertwritten: 200",
    "wixqa_simulated: 200",
    "wixqa_synthetic: 6221",
)

# The verdict line that ends the output of a fetch (contracts/cli.md, "Verdict lines").
DONE = "dataset fetch: done"


def test_ac_001_fetching_twice_reports_the_pinned_dataset_and_downloads_once(
    run_command, repository_root
):
    """AC-001: the dataset is fetched at the pinned revision with the recorded row counts, and
    a fetch over a complete, matching copy downloads nothing."""
    pinned = json.loads((repository_root / "dataset.json").read_text(encoding="utf-8"))

    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-001: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert any(pinned["revision"] in line for line in result.lines), (
        f"AC-001: the output names the pinned revision {pinned['revision']} (FR-001, FR-002)"
    )
    for line in ROW_COUNT_LINES:
        assert line in result.lines, f"AC-001: the output contains the line `{line}` (SC-002)"

    # The output of the second fetch is what follows the verdict line of the first.
    assert DONE in result.lines, f"AC-001: the first fetch ends with the line `{DONE}`"
    second_fetch = result.lines[result.lines.index(DONE) + 1 :]
    assert "nothing downloaded" in second_fetch, (
        "AC-001: the second fetch prints `nothing downloaded` (FR-003)"
    )
