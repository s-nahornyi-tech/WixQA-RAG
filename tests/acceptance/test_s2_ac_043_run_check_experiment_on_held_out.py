"""Acceptance test of check AC-043 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir
      tests/data/sets --run 20261103T100100Z-experiment-on-held-out

(one line)

→ exit code 1, the line `run check: failed`, and a `difference:` line that names the held-out set
`harness-hxc` and states that an experiment run is made on a golden set.

Covers US3, FR-035, SC-004 and SC-008.

The record names `20261103T100000Z-example-c` as its baseline and differs from it in the one
parameter it names; both are on the held-out set `harness-hxc`. contracts/cli.md, "`run
check`", fixes the wording of the line. The command reads the run record and the question-set
record and writes nothing. The test needs neither the store, the provider nor the dataset host
and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir"
    " tests/data/sets --run 20261103T100100Z-experiment-on-held-out"
)

EXPECTED = (
    "the run is an experiment on the held-out set harness-hxc;"
    " an experiment run is made on a golden set"
)


def test_ac_043_an_experiment_run_on_a_held_out_set_fails_its_check(run_command):
    """AC-043: a held-out set is never used to choose a setting, so an experiment run on one fails
    its check."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-043: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "run check: failed" in result.lines, (
        "AC-043: the output contains the line `run check: failed`"
    )
    assert result.last_line == "run check: failed"
    assert EXPECTED in result.differences, (
        "AC-043: a `difference:` line names the held-out set `harness-hxc` and says that an "
        "experiment run is made on a golden set; "
        f"got {result.differences}"
    )
