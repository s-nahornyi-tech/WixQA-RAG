"""Acceptance test of check AC-018 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    env -u DATABASE_URL -u OPENAI_API_KEY python -m wixqa_rag run check --runs-dir
      tests/data/runs --sets-dir tests/data/sets --run 20261101T100000Z-example-a

(one line)

→ exit code 0; the output contains `run: 20261101T100000Z-example-a`, `question set: harness
(golden)`, `questions: 8` and `run check: passed`.

Covers US3, FR-017, FR-018, FR-019, FR-020, FR-021, FR-022, FR-031 and SC-006.

The command line itself removes the two settings from the environment: the check of a run
record needs neither the store nor a provider. The command reads the run record and the
question-set record and writes nothing. The test needs neither the store, the provider nor the
dataset host and carries no marker.
"""

COMMAND = (
    "env -u DATABASE_URL -u OPENAI_API_KEY python -m wixqa_rag run check --runs-dir"
    " tests/data/runs --sets-dir tests/data/sets --run 20261101T100000Z-example-a"
)

EXPECTED_LINES = (
    "run: 20261101T100000Z-example-a",
    "question set: harness (golden)",
    "questions: 8",
    "run check: passed",
)


def test_ac_018_a_sound_run_record_passes_its_check_without_any_setting(run_command):
    """AC-018: the example record has every part that a run record must have, and its summary is
    what the one computation gives."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-018: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in EXPECTED_LINES:
        assert line in result.lines, f"AC-018: the output contains the line `{line}`"
    assert result.settings_printed == (), "AC-018: no value of a setting is printed"
