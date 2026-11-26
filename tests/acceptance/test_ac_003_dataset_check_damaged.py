"""Acceptance test of check AC-003 (specs/001-corpus-and-audit/spec.md, "Acceptance Checks").

    python -m wixqa_rag dataset check --data-dir tests/data/example-damaged

→ exit code 1, the line `dataset check: failed`, and a line that names the repeated article
id `ex-002`.

Covers US1 and FR-004.

`tests/data/example-damaged` holds the row of `ex-002` twice, and its manifest matches its own
files, so the repeated id is its one difference (data-model.md, "Example datasets"). The
command reads the directory and writes nothing. The test needs neither the store, the
provider nor the dataset host and carries no marker.
"""

COMMAND = "python -m wixqa_rag dataset check --data-dir tests/data/example-damaged"


def test_ac_003_a_repeated_article_id_fails_the_dataset_check(run_command):
    """AC-003: the dataset check fails for a corpus with a repeated article id and names it."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-003: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "dataset check: failed" in result.lines, (
        "AC-003: the output contains the line `dataset check: failed`"
    )
    assert any("ex-002" in line for line in result.lines), (
        "AC-003: a line of the output names the repeated article id `ex-002`"
    )
