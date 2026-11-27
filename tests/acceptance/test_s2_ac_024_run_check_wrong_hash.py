"""Acceptance test of check AC-024 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir
      tests/data/sets --run 20261101T100400Z-wrong-hash

(one line)

→ exit code 1, the line `run check: failed`, and a `difference:` line that names `hxa-001` and
the hash of its answer.

Covers US3, FR-022 and SC-004.

The record is `example-a` under an identifier of its own, and `answer_sha256` of `hxa-001` is
64 zeros. contracts/cli.md, "`run check`", fixes the wording of the line. The command reads the
run record and the question-set record and writes nothing. The test needs neither the store,
the provider nor the dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir"
    " tests/data/sets --run 20261101T100400Z-wrong-hash"
)

EXPECTED = "hxa-001 has an answer_sha256 that is not the hash of its answer"


def test_ac_024_a_hash_that_is_not_the_hash_of_its_answer_is_named(run_command):
    """AC-024: the recorded hash of an answer is the SHA-256 of that answer's text; a hash that is
    not is named with its question."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-024: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "run check: failed" in result.lines, (
        "AC-024: the output contains the line `run check: failed`"
    )
    assert result.last_line == "run check: failed"
    assert EXPECTED in result.differences, (
        "AC-024: a `difference:` line names `hxa-001` and the hash of its answer; "
        f"got {result.differences}"
    )
