"""Acceptance test of check AC-032 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run compare --runs-dir tests/data/runs-invalid
      --sets-dir tests/data/sets --first 20261101T100000Z-example-a
      --second 20261101T100400Z-wrong-hash

(one line)

→ exit code 2 and the line `run compare: refused`, with the reason that the run check failed
for `20261101T100400Z-wrong-hash`.

Covers US4 and FR-025.

In the second record the hash recorded for the answer of `hxa-001` is not the hash of that
answer, so the record does not pass its check, and no comparison is made from it.
contracts/cli.md, "`run compare`", fixes the wording of the reason. The command reads the two
run records and the question-set record and writes nothing. The test needs neither the store,
the provider nor the dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag run compare --runs-dir tests/data/runs-invalid"
    " --sets-dir tests/data/sets --first 20261101T100000Z-example-a"
    " --second 20261101T100400Z-wrong-hash"
)


def test_ac_032_no_comparison_is_made_from_a_record_that_fails_its_check(run_command):
    """AC-032: a comparison is made only from records that pass the check; otherwise it is
    refused, with the reason."""
    result = run_command(COMMAND)

    assert result.exit_code == 2, (
        f"AC-032: exit code 2 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "run compare: refused" in result.lines, (
        "AC-032: the output contains the line `run compare: refused`"
    )
    assert result.last_line == "run compare: refused"
    assert "the run check failed for 20261101T100400Z-wrong-hash" in result.reasons, (
        "AC-032: a `reason:` line says that the run check failed for "
        f"`20261101T100400Z-wrong-hash`; got {result.reasons}"
    )
