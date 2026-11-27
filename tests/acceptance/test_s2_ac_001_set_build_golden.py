"""Acceptance test of check AC-001 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set build --version golden-001 --role golden
      --take wixqa_expertwritten=100 --take wixqa_simulated=100 --seed 20261127

(one line)

→ exit code 0; the output names the pinned revision and contains `wixqa_expertwritten: 100`,
`wixqa_simulated: 100`, `questions: 200` and `set build: done`, and no line for
`wixqa_synthetic`; afterwards the file `evals/golden/golden-001.json` names the pinned
revision, the role `golden`, the rule, the seed `20261127` and 200 question identifiers, 100
that start with `wixqa_expertwritten-` and 100 that start with `wixqa_simulated-`.

Covers US1, FR-001, FR-002, FR-003, FR-004, FR-005 and SC-001.

The command produces the golden set of the study from the default data directory. The test
has no fixture that fetches: it relies on the copy of the dataset that the test of spec 1's
AC-001 left, which runs before it in the same run (tasks.md, "How the tests are run"). It
runs only in the scope `full` on GitHub Actions. On the first run the command writes
`evals/golden/golden-001.json` in the checkout, by design: the workflow records the file on
the branch (research.md, section 13). On every later run the file is in the checkout and
the build reports it as already written, with the same lines. The test removes nothing.
"""

import json

import pytest

pytestmark = pytest.mark.real_data

COMMAND = (
    "python -m wixqa_rag set build --version golden-001 --role golden"
    " --take wixqa_expertwritten=100 --take wixqa_simulated=100 --seed 20261127"
)


def pinned_revision(repository_root) -> str:
    """The pinned revision, read from `dataset.json` at the repository root."""
    return json.loads((repository_root / "dataset.json").read_text(encoding="utf-8"))["revision"]


def test_ac_001_the_golden_set_is_produced_from_the_pinned_dataset(run_command, repository_root):
    """AC-001: 100 questions of each of the two parts of real questions, none of the
    synthetic part, drawn with the decided seed and recorded with the pinned revision."""
    revision = pinned_revision(repository_root)

    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-001: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert any(revision in line for line in result.lines), (
        "AC-001: the output names the pinned revision"
    )
    for line in (
        "wixqa_expertwritten: 100",
        "wixqa_simulated: 100",
        "questions: 200",
        "set build: done",
    ):
        assert line in result.lines, f"AC-001: the output contains the line `{line}`"
    assert not any(line.startswith("wixqa_synthetic:") for line in result.lines), (
        "AC-001: the output has no line for `wixqa_synthetic`"
    )

    file = repository_root / "evals" / "golden" / "golden-001.json"
    assert file.is_file(), "AC-001: afterwards the file `evals/golden/golden-001.json` exists"
    record = json.loads(file.read_text(encoding="utf-8"))
    assert record["dataset"]["revision"] == revision, "AC-001: the file names the pinned revision"
    assert record["role"] == "golden", "AC-001: the file names the role `golden`"
    assert record["rule"]["kind"] == "draw", "AC-001: the file names the rule"
    assert record["rule"]["take"] == [
        {"part": "wixqa_expertwritten", "questions": 100},
        {"part": "wixqa_simulated", "questions": 100},
    ], "AC-001: the file names the rule"
    assert record["rule"]["seed"] == 20261127, "AC-001: the file names the seed `20261127`"
    identifiers = [question["id"] for question in record["questions"]]
    assert len(identifiers) == 200 and len(set(identifiers)) == 200, (
        "AC-001: the file names 200 question identifiers"
    )
    for part in ("wixqa_expertwritten", "wixqa_simulated"):
        of_part = [identifier for identifier in identifiers if identifier.startswith(f"{part}-")]
        assert len(of_part) == 100, f"AC-001: 100 identifiers start with `{part}-`"
