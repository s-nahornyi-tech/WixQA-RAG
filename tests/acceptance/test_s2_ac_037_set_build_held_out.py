"""Acceptance test of check AC-037 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set build --version golden-001 --role golden
      --take wixqa_expertwritten=100 --take wixqa_simulated=100 --seed 20261127
    && python -m wixqa_rag set build --version held-out-001 --role held-out
      --complement-of golden-001

(one line)

→ exit code 0; the output of the second build contains `wixqa_expertwritten: 100`,
`wixqa_simulated: 100`, `questions: 200` and `set build: done`; afterwards the file
`evals/golden/held-out-001.json` names the pinned revision, the role `held-out`, the set
`golden-001` that it complements and 200 question identifiers.

Covers US1, FR-001, FR-032 and SC-001.

The first build finds `golden-001` written, by the test of AC-001 in the same run or in the
checkout, and reports it as already written. The second produces the held-out set of the
study as its complement. The test has no fixture that fetches: it relies on the copy of the
dataset that the test of spec 1's AC-001 left (tasks.md, "How the tests are run"). It runs
only in the scope `full` on GitHub Actions. On the first run the command writes
`evals/golden/held-out-001.json` in the checkout, by design: the workflow records the file on
the branch (research.md, section 13). The test removes nothing.
"""

import json

import pytest

pytestmark = pytest.mark.real_data

COMMAND = (
    "python -m wixqa_rag set build --version golden-001 --role golden"
    " --take wixqa_expertwritten=100 --take wixqa_simulated=100 --seed 20261127"
    " && python -m wixqa_rag set build --version held-out-001 --role held-out"
    " --complement-of golden-001"
)


def pinned_revision(repository_root) -> str:
    """The pinned revision, read from `dataset.json` at the repository root."""
    return json.loads((repository_root / "dataset.json").read_text(encoding="utf-8"))["revision"]


def test_ac_037_the_held_out_set_is_produced_as_the_complement_of_the_golden_set(
    run_command, repository_root
):
    """AC-037: the held-out set holds the other 100 questions of each of the two parts and
    names the golden set that it complements."""
    revision = pinned_revision(repository_root)

    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-037: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    blocks = result.blocks()
    assert len(blocks) == 2, "AC-037: two builds, each with its verdict line"
    for line in (
        "wixqa_expertwritten: 100",
        "wixqa_simulated: 100",
        "questions: 200",
        "set build: done",
    ):
        assert line in blocks[1], f"AC-037: the second build prints the line `{line}`"

    file = repository_root / "evals" / "golden" / "held-out-001.json"
    assert file.is_file(), "AC-037: afterwards the file `evals/golden/held-out-001.json` exists"
    record = json.loads(file.read_text(encoding="utf-8"))
    assert record["dataset"]["revision"] == revision, "AC-037: the file names the pinned revision"
    assert record["role"] == "held-out", "AC-037: the file names the role `held-out`"
    assert record["rule"]["kind"] == "complement" and record["rule"]["of"] == "golden-001", (
        "AC-037: the file names the set `golden-001` that it complements"
    )
    identifiers = [question["id"] for question in record["questions"]]
    assert len(identifiers) == 200 and len(set(identifiers)) == 200, (
        "AC-037: the file names 200 question identifiers"
    )
