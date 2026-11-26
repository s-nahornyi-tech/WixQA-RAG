"""Acceptance test of check AC-004 (specs/001-corpus-and-audit/spec.md, "Acceptance Checks").

    python -m wixqa_rag index build --index wixqa-001

→ exit code 0; the output contains `articles: 6221`; afterwards the file
`evals/indexes/wixqa-001/build.json` names the pinned revision, the embedding model, the
splitting rule and `cost_usd`.

Covers US2, FR-006, FR-007, FR-009, FR-010 and SC-005.

The command builds the index of the published dataset, which the provider charges for, or
reports the index that the workflow restored as already complete. The test therefore runs
only in the scope `full` on GitHub Actions, and not before the task that records the index
(tasks.md, "How the tests are run"). It has no fixture that fetches or builds: it relies on
the copy that the test of AC-001 left. It sets no time limit; the first build takes many
minutes. The build record under `evals/` of the checkout is the one file it may leave.
"""

import json

import pytest

pytestmark = [pytest.mark.real_data, pytest.mark.store, pytest.mark.provider]

COMMAND = "python -m wixqa_rag index build --index wixqa-001"
BUILD_RECORD = "evals/indexes/wixqa-001/build.json"


def test_ac_004_the_index_of_the_published_dataset_is_built_and_recorded(
    run_command, repository_root
):
    """AC-004: the index `wixqa-001` holds the 6,221 articles, and its build record tells how
    to repeat the build and what it cost."""
    pinned = json.loads((repository_root / "dataset.json").read_text(encoding="utf-8"))

    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-004: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "articles: 6221" in result.lines, "AC-004: the output contains `articles: 6221`"

    file = repository_root / BUILD_RECORD
    assert file.is_file(), f"AC-004: afterwards the file {BUILD_RECORD} exists"
    record = json.loads(file.read_text(encoding="utf-8"))
    # The fields are those of contracts/records.md, "`build.json`".
    assert record["dataset"]["revision"] == pinned["revision"], (
        "AC-004: the build record names the pinned revision"
    )
    assert record["embedding"]["model_requested"] == "text-embedding-3-small", (
        "AC-004: the build record names the embedding model (FR-006)"
    )
    assert record["splitting"]["rule"] == "line-pack-v1", (
        "AC-004: the build record names the splitting rule"
    )
    assert "cost_usd" in record, "AC-004: the build record names `cost_usd` (SC-005)"
