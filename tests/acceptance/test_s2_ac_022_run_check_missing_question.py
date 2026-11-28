"""Acceptance test of check AC-022 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir
      tests/data/sets --run 20261101T100200Z-missing-question

(one line)

→ exit code 1, the line `run check: failed`, and a `difference:` line that names `hxb-003` as a
question of the run's question set without an entry.

Covers US3, FR-014, FR-022 and SC-004.

The record is `example-a` under an identifier of its own, and its results have no line for
`hxb-003`. contracts/cli.md, "`run check`", fixes the wording of the line. The command reads
the run record and the question-set record and writes nothing. The test needs neither the
store, the provider nor the dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir"
    " tests/data/sets --run 20261101T100200Z-missing-question"
)

EXPECTED = "hxb-003 is a question of the question set and has no entry"


def test_ac_022_a_question_of_the_set_without_an_entry_is_named(run_command):
    """AC-022: the results hold exactly one entry for every question of the run's question set; a
    question without one is named."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-022: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "run check: failed" in result.lines, (
        "AC-022: the output contains the line `run check: failed`"
    )
    assert result.last_line == "run check: failed"
    assert EXPECTED in result.differences, (
        "AC-022: a `difference:` line names `hxb-003` as a question of the question set "
        "without an entry; "
        f"got {result.differences}"
    )
