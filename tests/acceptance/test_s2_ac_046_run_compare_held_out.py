"""Acceptance test of check AC-046 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run compare --runs-dir tests/data/runs --sets-dir tests/data/sets
      --first 20261103T100000Z-example-c --second 20261104T100000Z-example-d

(one line)

→ exit code 0; the output contains `question set: harness-hxc (held-out)`, the line
`held-out set: its questions are not used to choose a setting`, `compared: 2`, `left out: 0`,
`gained: 1`, followed by `  hxc-002`, `lost: 0` and `run compare: done`.

Covers US4, FR-034 and FR-036.

Both runs are on the held-out set `harness-hxc`. `hxc-002` has its gold article in the
generation list only in the second run (data-model.md, "The comparisons"). The command reads
the two run records and the question-set record and writes nothing. The test needs neither
the store, the provider nor the dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag run compare --runs-dir tests/data/runs --sets-dir tests/data/sets"
    " --first 20261103T100000Z-example-c --second 20261104T100000Z-example-d"
)

EXPECTED_LINES = (
    "question set: harness-hxc (held-out)",
    "held-out set: its questions are not used to choose a setting",
    "compared: 2",
    "left out: 0",
    "gained: 1",
    "lost: 0",
    "run compare: done",
)


def test_ac_046_a_comparison_on_a_held_out_set_says_what_the_set_is_for(run_command):
    """AC-046: two runs on a held-out set can be compared; the comparison states the set and
    its role, and that its questions are not used to choose a setting."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-046: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in EXPECTED_LINES:
        assert line in result.lines, f"AC-046: the output contains the line `{line}`"
    start = result.lines.index("gained: 1") + 1
    assert result.lines[start : start + 1] == ["  hxc-002"], (
        "AC-046: `gained: 1` is followed by `  hxc-002`"
    )
