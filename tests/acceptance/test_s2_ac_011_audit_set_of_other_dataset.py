"""Acceptance test of check AC-011 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag index build --data-dir tests/data/example --index example
    && python -m wixqa_rag index audit --data-dir tests/data/example --index example
       --sets-dir tests/data/sets --set harness

(one line)

→ exit code 2 and the line `audit: not carried out`, with the reason that the question set
`harness` does not match the dataset.

Covers US1, FR-008 and FR-030.

The question set `harness` was produced from `tests/data/harness`, not from
`tests/data/example`, so it does not pass its check against the data directory of the audit.
The build embeds the five example passages with the provider, unless an earlier test of the
same run has already built `example`; the test needs the store and the provider key and runs
in the scope `example` on GitHub Actions. An audit that is not carried out writes no result.
"""

import pytest

pytestmark = [pytest.mark.store, pytest.mark.provider]

COMMAND = (
    "python -m wixqa_rag index build --data-dir tests/data/example --index example"
    " && python -m wixqa_rag index audit --data-dir tests/data/example --index example"
    " --sets-dir tests/data/sets --set harness"
)


def test_ac_011_an_audit_with_a_set_of_another_dataset_is_not_carried_out(run_command):
    """AC-011: an audit that names a question set which does not pass its check against the
    same dataset ends as not carried out, never as passed or failed."""
    result = run_command(COMMAND)

    assert result.exit_code == 2, (
        f"AC-011: exit code 2 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "audit: not carried out" in result.lines, (
        "AC-011: the output contains the line `audit: not carried out`"
    )
    assert result.last_line == "audit: not carried out"
    assert any(
        "question set harness" in reason and "does not match the dataset" in reason
        for reason in result.reasons
    ), (
        "AC-011: a `reason:` line says that the question set `harness` does not match the "
        f"dataset; got {result.reasons}"
    )
