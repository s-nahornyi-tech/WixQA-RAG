"""Acceptance test of check AC-034 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets
      --version harness-half
    && python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets
      --version harness-half-rest

(one line)

→ exit code 0; both checks end with `set check: passed`: the draw that the command makes with
the seed 7 selects exactly the questions of the record that was written beforehand.

Covers US1, FR-004, FR-006, FR-032 and SC-006.

The two records under `tests/data/sets` were written by hand from the table of the eight
draw keys in data-model.md, without code of the package; tests/unit/
test_harness_example_data.py shows that they follow from those keys. The command reads the
two directories and writes nothing. The test needs neither the store, the provider nor the
dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets"
    " --version harness-half"
    " && python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets"
    " --version harness-half-rest"
)


def test_ac_034_the_records_written_beforehand_pass_the_check(run_command):
    """AC-034: the draw of the command, made again with the recorded seed, selects exactly
    the questions of the record written beforehand, and the complement is exactly the rest."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-034: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    blocks = result.blocks()
    assert len(blocks) == 2, "AC-034: two checks, each with its verdict line"
    for name, block in (("first", blocks[0]), ("second", blocks[1])):
        assert block[-1] == "set check: passed", (
            f"AC-034: the {name} check ends with `set check: passed`"
        )
