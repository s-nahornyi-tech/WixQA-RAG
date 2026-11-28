"""Acceptance test of check AC-025 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir
      tests/data/sets --run 20261101T100500Z-stale-summary

(one line)

→ exit code 1, the line `run check: failed`, and a `difference:` line that names the generation
list and both numbers, 3 and 2.

Covers US3, FR-017, FR-022, SC-004 and SC-006.

The record is `example-a` under an identifier of its own, and its summary states 3 questions
with every gold article in the generation list where the results give 2. contracts/cli.md,
"`run check`", gives this very line as its example. The command reads the run record and the
question-set record and writes nothing. The test needs neither the store, the provider nor the
dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir"
    " tests/data/sets --run 20261101T100500Z-stale-summary"
)

EXPECTED = (
    "the summary states all_found 3 for the generation list, all questions; the results give 2"
)


def test_ac_025_a_number_of_the_summary_that_the_results_do_not_give_is_named(run_command):
    """AC-025: the summary is recomputed from the other files by the one computation and compared
    for equality; the number that differs is named with both values."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-025: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "run check: failed" in result.lines, (
        "AC-025: the output contains the line `run check: failed`"
    )
    assert result.last_line == "run check: failed"
    assert EXPECTED in result.differences, (
        "AC-025: a `difference:` line names the generation list and both numbers, 3 and 2; "
        f"got {result.differences}"
    )
