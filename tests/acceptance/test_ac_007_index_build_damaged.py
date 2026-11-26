"""Acceptance test of check AC-007 (specs/001-corpus-and-audit/spec.md, "Acceptance Checks").

    python -m wixqa_rag index build --data-dir tests/data/example-damaged --index damaged

→ exit code 2 and the line `index build: refused`, with the reason that the dataset check
failed.

Covers US2 and FR-006.

The dataset check is the second step of the build, before the store and the provider are
needed (contracts/cli.md, "`index build`"), so the test needs neither and carries no marker.
The command is refused and writes nothing.
"""

COMMAND = "python -m wixqa_rag index build --data-dir tests/data/example-damaged --index damaged"


def test_ac_007_a_corpus_that_fails_the_dataset_check_is_not_built(run_command):
    """AC-007: an index is built only from a corpus that passes the dataset check."""
    result = run_command(COMMAND)

    assert result.exit_code == 2, (
        f"AC-007: exit code 2 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "index build: refused" in result.lines, (
        "AC-007: the output contains the line `index build: refused`"
    )
    # contracts/cli.md, "`index build`": `reason: the dataset check failed for <DIR>`.
    reasons = [line for line in result.lines if line.startswith("reason:")]
    assert any("dataset check failed" in line for line in reasons), (
        "AC-007: the reason says that the dataset check failed; got: " + " | ".join(reasons)
    )
