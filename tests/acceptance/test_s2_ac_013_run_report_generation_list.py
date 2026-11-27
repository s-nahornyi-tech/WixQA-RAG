"""Acceptance test of check AC-013 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets
      --run 20261101T100000Z-example-a

(one line)

→ the output contains the three lines `generation list, all questions: ...`, `generation list,
single-article: ...` and `generation list, multi-article: ...` that are listed below.

Covers US2, FR-009, FR-010, FR-011, FR-012, FR-015 and SC-003.

The command is that of AC-012. The numbers are those of the list passed to generation: six
questions have a gold article and a generation list; `hxa-005` and `hxb-001` have no generation
list and are left out, and the empty list of `hxb-002` counts with a share of 0 (data-model.md,
"The numbers of the four summaries"). The command reads the run record and the question-set
record and writes nothing. The test needs neither the store, the provider nor the dataset host
and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets"
    " --run 20261101T100000Z-example-a"
)

EXPECTED_LINES = (
    "generation list, all questions: 6 questions, mean share_found 0.5278,"
    " all_found 2 of 6 (0.3333)",
    "generation list, single-article: 3 questions, mean share_found 0.3333,"
    " all_found 1 of 3 (0.3333)",
    "generation list, multi-article: 3 questions, mean share_found 0.7222,"
    " all_found 1 of 3 (0.3333)",
)


def test_ac_013_the_report_gives_the_numbers_of_the_generation_list(run_command):
    """AC-013: the mean of `share_found` and the questions with every gold article found, on the
    list passed to generation, in the three breakdowns."""
    result = run_command(COMMAND)

    for line in EXPECTED_LINES:
        assert line in result.lines, f"AC-013: the output contains the line `{line}`"
