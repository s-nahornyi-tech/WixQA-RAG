"""Acceptance test of check AC-038 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set build --version synthetic-001 --role held-out
      --take wixqa_synthetic=300 --seed 20261127

(one line)

→ exit code 0; the output contains `wixqa_synthetic: 300`, `questions: 300` and
`set build: done`, and no line for another part; afterwards the file
`evals/golden/synthetic-001.json` names the pinned revision, the role `held-out`, the seed
`20261127` and 300 question identifiers that all start with `wixqa_synthetic-`.

Covers US1, FR-001, FR-033 and SC-001.

The command produces the synthetic held-out set of the study from the default data
directory. The test has no fixture that fetches: it relies on the copy of the dataset that
the test of spec 1's AC-001 left (tasks.md, "How the tests are run"). It runs only in the
scope `full` on GitHub Actions. On the first run the command writes
`evals/golden/synthetic-001.json` in the checkout, by design: the workflow records the file
on the branch (research.md, section 13). On every later run the build reports the set as
already written, with the same lines. The test removes nothing.
"""

import json

import pytest

pytestmark = pytest.mark.real_data

COMMAND = (
    "python -m wixqa_rag set build --version synthetic-001 --role held-out"
    " --take wixqa_synthetic=300 --seed 20261127"
)

OTHER_PARTS = ("wix_kb_corpus", "wixqa_expertwritten", "wixqa_simulated")


def pinned_revision(repository_root) -> str:
    """The pinned revision, read from `dataset.json` at the repository root."""
    return json.loads((repository_root / "dataset.json").read_text(encoding="utf-8"))["revision"]


def test_ac_038_the_synthetic_held_out_set_is_produced(run_command, repository_root):
    """AC-038: 300 questions of the synthetic part and no other question, drawn with the
    decided seed and recorded with the pinned revision."""
    revision = pinned_revision(repository_root)

    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-038: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in ("wixqa_synthetic: 300", "questions: 300", "set build: done"):
        assert line in result.lines, f"AC-038: the output contains the line `{line}`"
    for part in OTHER_PARTS:
        assert not any(line.startswith(f"{part}:") for line in result.lines), (
            f"AC-038: the output has no line for another part; found one for `{part}`"
        )

    file = repository_root / "evals" / "golden" / "synthetic-001.json"
    assert file.is_file(), "AC-038: afterwards the file `evals/golden/synthetic-001.json` exists"
    record = json.loads(file.read_text(encoding="utf-8"))
    assert record["dataset"]["revision"] == revision, "AC-038: the file names the pinned revision"
    assert record["role"] == "held-out", "AC-038: the file names the role `held-out`"
    assert record["rule"]["seed"] == 20261127, "AC-038: the file names the seed `20261127`"
    identifiers = [question["id"] for question in record["questions"]]
    assert len(identifiers) == 300 and len(set(identifiers)) == 300, (
        "AC-038: the file names 300 question identifiers"
    )
    assert all(identifier.startswith("wixqa_synthetic-") for identifier in identifiers), (
        "AC-038: every question identifier starts with `wixqa_synthetic-`"
    )
