"""Acceptance test of check AC-012 (specs/001-corpus-and-audit/spec.md, "Acceptance Checks").

    python -m wixqa_rag index audit --index no-such-index

→ exit code 2 and the line `audit: not carried out`, with the reason that the index
`no-such-index` does not exist.

Covers US3, FR-009, FR-014 and FR-016.

Whether the index exists is the third step of the audit, after the store was reached and
before the data directory is read (contracts/cli.md, "`index audit`"), so the test needs the
store, carries the marker `store` and needs no local copy of the dataset. No test builds an
index `no-such-index`. An audit that is not carried out writes no result file.
"""

import pytest

pytestmark = pytest.mark.store

COMMAND = "python -m wixqa_rag index audit --index no-such-index"


def test_ac_012_the_audit_of_an_index_that_does_not_exist_is_not_carried_out(run_command):
    """AC-012: the audit ends as not carried out and states the reason; it is reported
    neither as passed nor as failed."""
    result = run_command(COMMAND)

    assert result.exit_code == 2, (
        f"AC-012: exit code 2 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "audit: not carried out" in result.lines, (
        "AC-012: the output contains the line `audit: not carried out`"
    )
    # contracts/cli.md, "`index audit`": `reason: index <ID> does not exist`.
    reasons = [line for line in result.lines if line.startswith("reason:")]
    assert any("no-such-index" in line and "does not exist" in line for line in reasons), (
        "AC-012: the reason says that the index `no-such-index` does not exist; got: "
        + " | ".join(reasons)
    )
