"""Acceptance test of check AC-003 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets
      --version harness --role golden --take hxa=5 --take hxb=3 --seed 1
    && python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets
      --version harness --role golden --take hxa=5 --take hxb=3 --seed 1

(one line)

→ exit code 0; the output contains `hxa: 5`, `hxb: 3` and `questions: 8`; the second build
prints `question set: harness (already written)`.

Covers US1, FR-004, FR-005 and SC-006.

The builds write to `data/sets` of the checkout, which Git ignores; the fixture `built_sets`
empties that folder before and after the test, so the first build always writes. The test
needs neither the store, the provider nor the dataset host and carries no marker.
"""

BUILD = (
    "python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets"
    " --version harness --role golden --take hxa=5 --take hxb=3 --seed 1"
)
COMMAND = f"{BUILD} && {BUILD}"


def test_ac_003_a_second_build_of_the_same_set_reports_it_as_already_written(
    run_command, built_sets
):
    """AC-003: the same dataset, rule and seed under the same version: the second build
    reports that the version is already written."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-003: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in ("hxa: 5", "hxb: 3", "questions: 8"):
        assert line in result.lines, f"AC-003: the output contains the line `{line}`"

    blocks = result.blocks()
    assert len(blocks) == 2, "AC-003: two builds, each with its verdict line"
    assert "question set: harness (already written)" in blocks[1], (
        "AC-003: the second build prints `question set: harness (already written)`"
    )
    assert "question set: harness (already written)" not in blocks[0], (
        "AC-003: the first build writes the record"
    )
