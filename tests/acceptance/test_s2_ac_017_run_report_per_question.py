"""Acceptance test of check AC-017 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets
      --run 20261101T100000Z-example-a --per-question

(one line)

→ exit code 0; the output contains the lines ` hxa-004: no_answer; ...`, ` hxa-005: error; ...`
and ` hxb-002: call_limit; ...` that are listed below.

Covers US2, FR-010 and FR-011.

`hxa-004` has two of its three gold articles in the generation list and all three in the
retrieved list; `hxa-005` has neither list, which is told apart from the empty generation list
of `hxb-002`. The command reads the run record and the question-set record and writes nothing.
The test needs neither the store, the provider nor the dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets"
    " --run 20261101T100000Z-example-a --per-question"
)

EXPECTED_LINES = (
    "  hxa-004: no_answer; generation list 2 of 3, all_found 0; retrieved list 3 of 3, all_found 1",
    "  hxa-005: error; generation list absent; retrieved list absent",
    "  hxb-002: call_limit; generation list 0 of 1,"
    " all_found 0; retrieved list 0 of 1, all_found 0",
)


def test_ac_017_the_report_gives_the_numbers_of_each_question(run_command):
    """AC-017: with `--per-question` the report gives, for each question, the gold articles found
    in each list, and says when a list is absent."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-017: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in EXPECTED_LINES:
        assert line in result.lines, f"AC-017: the output contains the line `{line}`"
