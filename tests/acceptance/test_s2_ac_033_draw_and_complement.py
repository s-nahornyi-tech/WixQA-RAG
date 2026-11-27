"""Acceptance test of check AC-033 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets
      --version harness-half --role golden --take hxa=3 --take hxb=1 --seed 7
    && python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets
      --version harness-half-rest --role held-out --complement-of harness-half
    && python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir data/sets
      --version harness-half
    && python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir data/sets
      --version harness-half-rest

(one line)

→ exit code 0; the first check prints `role: golden`, `seed: 7`, `hxa: 3`, `hxb: 1` and
`questions: 4`; the second prints `role: held-out`, `complement of: harness-half`, `hxa: 2`,
`hxb: 2`, `questions: 4`, `in both sets: 0` and `in neither set: 0`; both end with
`set check: passed`.

Covers US1, FR-004, FR-032 and SC-006.

The builds write to `data/sets` of the checkout, which Git ignores; the fixture `built_sets`
empties that folder before and after the test. The test needs neither the store, the
provider nor the dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets"
    " --version harness-half --role golden --take hxa=3 --take hxb=1 --seed 7"
    " && python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets"
    " --version harness-half-rest --role held-out --complement-of harness-half"
    " && python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir data/sets"
    " --version harness-half"
    " && python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir data/sets"
    " --version harness-half-rest"
)

FIRST_CHECK = ("role: golden", "seed: 7", "hxa: 3", "hxb: 1", "questions: 4")
SECOND_CHECK = (
    "role: held-out",
    "complement of: harness-half",
    "hxa: 2",
    "hxb: 2",
    "questions: 4",
    "in both sets: 0",
    "in neither set: 0",
)


def test_ac_033_a_drawn_set_and_its_complement_are_built_and_pass_their_checks(
    run_command, built_sets
):
    """AC-033: a set drawn with a seed and the set that complements it are produced, and
    each passes its check; the complement shares no question with the drawn set and leaves
    none out."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-033: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    blocks = result.blocks()
    assert len(blocks) == 4, "AC-033: two builds and two checks, each with its verdict line"
    for line in FIRST_CHECK:
        assert line in blocks[2], f"AC-033: the first check prints the line `{line}`"
    for line in SECOND_CHECK:
        assert line in blocks[3], f"AC-033: the second check prints the line `{line}`"
    for name, block in (("first", blocks[2]), ("second", blocks[3])):
        assert block[-1] == "set check: passed", (
            f"AC-033: the {name} check ends with `set check: passed`"
        )
