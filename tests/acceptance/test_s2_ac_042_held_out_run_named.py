"""Acceptance test of check AC-042 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets
      --run 20261103T100000Z-example-c && python -m wixqa_rag run check --runs-dir
      tests/data/runs --sets-dir tests/data/sets --run 20261103T100000Z-example-c

(one line)

→ exit code 0; the output of both commands contains `question set: harness-hxc (held-out)`; the
report contains `generation list, all questions: 2 questions, mean share_found 0.5000,
all_found 1 of 2 (0.5000)`.

Covers US2, US3, FR-034 and SC-008.

The run `example-c` is on the held-out set `harness-hxc`: one of its two questions has its gold
article in the generation list. The command reads the run record and the question-set record
and writes nothing. The test needs neither the store, the provider nor the dataset host and
carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets"
    " --run 20261103T100000Z-example-c && python -m wixqa_rag run check --runs-dir"
    " tests/data/runs --sets-dir tests/data/sets --run 20261103T100000Z-example-c"
)

GENERATION_LIST = (
    "generation list, all questions: 2 questions, mean share_found 0.5000,"
    " all_found 1 of 2 (0.5000)"
)


def test_ac_042_a_run_on_a_held_out_set_is_recognisable_in_its_report_and_its_check(run_command):
    """AC-042: the report and the check of a run state the question set and its role."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-042: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    blocks = result.blocks()
    assert len(blocks) == 2, "AC-042: a report and a check, each with its verdict line"
    for name, block in (("report", blocks[0]), ("check", blocks[1])):
        assert "question set: harness-hxc (held-out)" in block, (
            f"AC-042: the {name} prints the line `question set: harness-hxc (held-out)`"
        )
    assert GENERATION_LIST in blocks[0], f"AC-042: the report prints the line `{GENERATION_LIST}`"
