"""Acceptance test of check AC-014 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets
      --run 20261101T100000Z-example-a

(one line)

→ the output contains the three lines `retrieved list, all questions: ...`, `retrieved list,
single-article: ...` and `retrieved list, multi-article: ...` that are listed below.

Covers US2, FR-009, FR-010, FR-011, FR-012, FR-015 and SC-003.

The command is that of AC-012. The numbers are those of the list before reranking: seven
questions have a gold article and a retrieved list; `hxa-005` has none and is left out
(data-model.md, "The numbers of the four summaries"). The command reads the run record and the
question-set record and writes nothing. The test needs neither the store, the provider nor the
dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets"
    " --run 20261101T100000Z-example-a"
)

EXPECTED_LINES = (
    "retrieved list, all questions: 7 questions, mean share_found 0.7857,"
    " all_found 5 of 7 (0.7143)",
    "retrieved list, single-article: 3 questions, mean share_found 0.6667,"
    " all_found 2 of 3 (0.6667)",
    "retrieved list, multi-article: 4 questions, mean share_found 0.8750,"
    " all_found 3 of 4 (0.7500)",
)


def test_ac_014_the_report_gives_the_numbers_of_the_retrieved_list(run_command):
    """AC-014: the same numbers on the list before reranking, reported apart from those of the
    generation list."""
    result = run_command(COMMAND)

    for line in EXPECTED_LINES:
        assert line in result.lines, f"AC-014: the output contains the line `{line}`"
