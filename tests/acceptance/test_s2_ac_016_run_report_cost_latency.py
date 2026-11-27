"""Acceptance test of check AC-016 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets
      --run 20261101T100000Z-example-a

(one line)

→ the output contains the three lines `cost_usd answering, ...` and the three lines
`latency_seconds, ...` that are listed below, each for all questions, for single-article and
for multi-article questions.

Covers US2, FR-015, FR-016 and SC-003.

The command is that of AC-012. The cost follows from the token counts and the prices of the run
config, 1.00 US dollar per million input tokens and 2.00 per million output tokens; the median
of an even number of latencies is the mean of the two middle values, and the 95th percentile of
eight values is the eighth. The command reads the run record and the question-set record and
writes nothing. The test needs neither the store, the provider nor the dataset host and carries
no marker.
"""

COMMAND = (
    "python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets"
    " --run 20261101T100000Z-example-a"
)

EXPECTED_LINES = (
    "cost_usd answering, all questions: 8 questions, total 0.01280000, per question 0.00160000",
    "cost_usd answering, single-article: 4 questions, total 0.00600000, per question 0.00150000",
    "cost_usd answering, multi-article: 4 questions, total 0.00680000, per question 0.00170000",
    "latency_seconds, all questions: 8 questions, median 4.500, p95 30.000",
    "latency_seconds, single-article: 4 questions, median 3.500, p95 7.000",
    "latency_seconds, multi-article: 4 questions, median 6.000, p95 30.000",
)


def test_ac_016_the_report_gives_cost_and_latency_in_the_three_breakdowns(run_command):
    """AC-016: the cost of answering as a total and per question, and the latency as the median
    and the 95th percentile."""
    result = run_command(COMMAND)

    for line in EXPECTED_LINES:
        assert line in result.lines, f"AC-016: the output contains the line `{line}`"
