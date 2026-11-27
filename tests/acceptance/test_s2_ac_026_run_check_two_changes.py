"""Acceptance test of check AC-026 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir
      tests/data/sets --run 20261101T100600Z-two-changes

(one line)

→ exit code 1, the line `run check: failed`, and a `difference:` line that names the second
config parameter that differs from `20261101T100000Z-example-a`.

Covers US3, FR-023 and SC-004.

The record names `20261101T100000Z-example-a` as its baseline and `reranking.enabled` as the
one parameter that changed, and its config also has `retrieval.top_k` 4 where the baseline has
3. contracts/cli.md, "`run check`", fixes the wording of the line. The command reads the run
record and the question-set record and writes nothing. The test needs neither the store, the
provider nor the dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir"
    " tests/data/sets --run 20261101T100600Z-two-changes"
)

EXPECTED = (
    "the config differs from the baseline 20261101T100000Z-example-a in retrieval.top_k,"
    " which is not the parameter the experiment names"
)


def test_ac_026_a_second_parameter_that_differs_from_the_baseline_is_named(run_command):
    """AC-026: an experiment run differs from its baseline in exactly the parameter it names; a
    second parameter that differs is named."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-026: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "run check: failed" in result.lines, (
        "AC-026: the output contains the line `run check: failed`"
    )
    assert result.last_line == "run check: failed"
    assert EXPECTED in result.differences, (
        "AC-026: a `difference:` line names `retrieval.top_k` as differing from the baseline; "
        f"got {result.differences}"
    )
