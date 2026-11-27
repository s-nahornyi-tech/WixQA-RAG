"""Acceptance test of check AC-004 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets
      --version harness --role golden --take hxa=5 --take hxb=3 --seed 1
    && python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets
      --version harness --role golden --take hxa=5 --seed 1

(one line)

→ exit code 2 and the line `set build: refused`, with the reason that `harness` exists with
another selection.

Covers US1 and FR-005.

The second build asks for the same version with five questions of `hxa` only. The builds write
to `data/sets` of the checkout, which Git ignores; the fixture `built_sets` empties that folder
before and after the test. The test needs neither the store, the provider nor the dataset host
and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets"
    " --version harness --role golden --take hxa=5 --take hxb=3 --seed 1"
    " && python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets"
    " --version harness --role golden --take hxa=5 --seed 1"
)


def test_ac_004_another_selection_under_an_existing_version_is_refused(run_command, built_sets):
    """AC-004: a version is written once; the request is refused and says why."""
    result = run_command(COMMAND)

    assert result.exit_code == 2, (
        f"AC-004: exit code 2 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "set build: refused" in result.lines, (
        "AC-004: the output contains the line `set build: refused`"
    )
    assert result.last_line == "set build: refused"
    assert any(
        "harness" in reason and "another selection" in reason for reason in result.reasons
    ), (
        "AC-004: a `reason:` line says that `harness` exists with another selection; "
        f"got {result.reasons}"
    )
