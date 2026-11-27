"""Acceptance test of check AC-045 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets
      --version harness-too-many --role held-out --take hxc=3 --seed 1

(one line)

→ exit code 2 and the line `set build: refused`, with a reason that names `hxc` and the
numbers 3 and 2; no record `harness-too-many` is written.

Covers US1, FR-006 and FR-030.

The part `hxc` has two questions, and the rule asks for three. The command would write to
`data/sets` of the checkout, which Git ignores; the fixture `built_sets` empties that folder
before and after the test. The test needs neither the store, the provider nor the dataset
host and carries no marker.
"""

import re

COMMAND = (
    "python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets"
    " --version harness-too-many --role held-out --take hxc=3 --seed 1"
)


def numbers_of(text: str) -> list[str]:
    """The whole numbers that stand in a text as words of their own."""
    return re.findall(r"(?<![\w-])\d+(?![\w-])", text)


def test_ac_045_a_rule_that_takes_more_than_a_part_has_is_refused(run_command, built_sets):
    """AC-045: the request is refused, the reason names the part and both numbers, and no
    record is written."""
    result = run_command(COMMAND)

    assert result.exit_code == 2, (
        f"AC-045: exit code 2 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "set build: refused" in result.lines, (
        "AC-045: the output contains the line `set build: refused`"
    )
    assert result.last_line == "set build: refused"
    assert any(
        "hxc" in reason and {"3", "2"} <= set(numbers_of(reason)) for reason in result.reasons
    ), f"AC-045: a `reason:` line names `hxc` and the numbers 3 and 2; got {result.reasons}"
    assert not (built_sets / "harness-too-many.json").exists(), (
        "AC-045: no record `harness-too-many` is written"
    )
    left = sorted(file.name for file in built_sets.rglob("*")) if built_sets.is_dir() else []
    assert left == [], f"AC-045: nothing is written to `data/sets`; found {left}"
