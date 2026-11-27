"""Acceptance test of check AC-012 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets
      --run 20261101T100000Z-example-a

(one line)

→ exit code 0; the output contains the three lines `status, all questions: ...`, `status,
single-article: ...` and `status, multi-article: ...` that are listed below, and ends with `run
report: done`.

Covers US2, FR-014, FR-015 and SC-003.

The run `example-a` of `tests/data/runs` has four answered questions and one each with the
status `no_answer`, `error`, `timeout` and `call_limit` (data-model.md, "Example data"). The
command reads the run record and the question-set record and writes nothing. The test needs
neither the store, the provider nor the dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets"
    " --run 20261101T100000Z-example-a"
)

EXPECTED_LINES = (
    "status, all questions: 8 questions, answered 4, no_answer 1, error 1, timeout 1, call_limit 1",
    "status, single-article: 4 questions, answered 2, no_answer 0, error 1,"
    " timeout 0, call_limit 1",
    "status, multi-article: 4 questions, answered 2, no_answer 1, error 0, timeout 1, call_limit 0",
)


def test_ac_012_the_report_counts_each_status_in_the_three_breakdowns(run_command):
    """AC-012: the count of each of the five statuses, for all questions, for single-article and
    for multi-article questions."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-012: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in EXPECTED_LINES:
        assert line in result.lines, f"AC-012: the output contains the line `{line}`"
    assert result.last_line == "run report: done", "AC-012: the output ends with `run report: done`"
