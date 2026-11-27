"""Acceptance test of check AC-005 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets
      --version harness --role golden --take hxa=5 --take hxb=3 --seed 1
    && python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir data/sets
      --version harness
    && python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets
      --version harness

(one line)

→ exit code 0; both checks print `role: golden`, `seed: 1`, `questions: 8`,
`single-article: 4`, `multi-article: 4`, `questions without gold articles: 0` and
`set check: passed`, and no line for `hxc`.

Covers US1, FR-003, FR-006 and FR-007.

The first check reads the record that the build has just written to `data/sets` of the
checkout, which Git ignores; the second reads the record that was written by hand under
`tests/data/sets`. The fixture `built_sets` empties `data/sets` before and after the test.
The test needs neither the store, the provider nor the dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets"
    " --version harness --role golden --take hxa=5 --take hxb=3 --seed 1"
    " && python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir data/sets"
    " --version harness"
    " && python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets"
    " --version harness"
)

EXPECTED_LINES = (
    "role: golden",
    "seed: 1",
    "questions: 8",
    "single-article: 4",
    "multi-article: 4",
    "questions without gold articles: 0",
    "set check: passed",
)


def test_ac_005_the_built_record_and_the_recorded_one_pass_the_check(run_command, built_sets):
    """AC-005: the record that the build writes and the record written beforehand both pass
    the check, with the same reported numbers."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-005: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    blocks = result.blocks()
    assert len(blocks) == 3, "AC-005: one build and two checks, each with its verdict line"
    for name, block in (("first", blocks[1]), ("second", blocks[2])):
        for line in EXPECTED_LINES:
            assert line in block, f"AC-005: the {name} check prints the line `{line}`"
        assert not any(line.startswith("hxc:") for line in block), (
            f"AC-005: the {name} check prints no line for `hxc`"
        )
