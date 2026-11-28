"""Acceptance test of check AC-021 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir
      tests/data/sets --run 20261101T100100Z-no-latency

(one line)

→ exit code 1, the line `run check: failed`, and a `difference:` line that names `hxa-003` and
the latency.

Covers US3, FR-022 and SC-004.

The record is `example-a` under an identifier of its own, and the entry of `hxa-003` has no
field `latency_seconds` (data-model.md, "Example data"). contracts/cli.md, "`run check`", fixes
the wording of the line. The command reads the run record and the question-set record and
writes nothing. The test needs neither the store, the provider nor the dataset host and carries
no marker.
"""

COMMAND = (
    "python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir"
    " tests/data/sets --run 20261101T100100Z-no-latency"
)

EXPECTED = "hxa-003 lacks the field latency_seconds"


def test_ac_021_an_entry_without_its_latency_is_named(run_command):
    """AC-021: a field that an entry must have is absent; the check names the question and the
    field."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-021: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "run check: failed" in result.lines, (
        "AC-021: the output contains the line `run check: failed`"
    )
    assert result.last_line == "run check: failed"
    assert EXPECTED in result.differences, (
        f"AC-021: a `difference:` line names `hxa-003` and the latency; got {result.differences}"
    )
