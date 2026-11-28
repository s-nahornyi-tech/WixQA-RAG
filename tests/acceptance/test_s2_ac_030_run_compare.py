"""Acceptance test of check AC-030 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    env -u DATABASE_URL -u OPENAI_API_KEY python -m wixqa_rag run compare
      --runs-dir tests/data/runs --sets-dir tests/data/sets
      --first 20261101T100000Z-example-a --second 20261102T100000Z-example-b

(one line)

→ exit code 0; the output contains `question set: harness (golden)`; `compared: 6`;
`left out: 2`, followed by `  hxa-005` and `  hxb-001`; `gained: 2`, followed by `  hxa-002`
and `  hxa-003`; `lost: 1`, followed by `  hxb-003`; and `run compare: done`.

Covers US4, FR-027, FR-028, FR-031 and SC-005.

The two runs are on the golden set `harness`. `hxa-005` and `hxb-001` have no generation list
in the first run and are left out; of the six questions compared, two have every gold article
in the generation list only in the second run, and one only in the first (data-model.md, "The
comparisons"). The command line itself removes the two settings from the environment. The
command reads the two run records and the question-set record and writes nothing. The test
needs neither the store, the provider nor the dataset host and carries no marker.
"""

COMMAND = (
    "env -u DATABASE_URL -u OPENAI_API_KEY python -m wixqa_rag run compare"
    " --runs-dir tests/data/runs --sets-dir tests/data/sets"
    " --first 20261101T100000Z-example-a --second 20261102T100000Z-example-b"
)

# A line with a number, and the indented lines that follow it.
FOLLOWED_BY = (
    ("left out: 2", ["  hxa-005", "  hxb-001"]),
    ("gained: 2", ["  hxa-002", "  hxa-003"]),
    ("lost: 1", ["  hxb-003"]),
)


def test_ac_030_the_comparison_names_the_questions_gained_lost_and_left_out(run_command):
    """AC-030: the comparison of two runs on one question set gives the questions compared,
    left out, gained and lost, with the identifiers behind each number."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-030: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in ("question set: harness (golden)", "compared: 6", "run compare: done"):
        assert line in result.lines, f"AC-030: the output contains the line `{line}`"
    for line, identifiers in FOLLOWED_BY:
        assert line in result.lines, f"AC-030: the output contains the line `{line}`"
        start = result.lines.index(line) + 1
        assert result.lines[start : start + len(identifiers)] == identifiers, (
            f"AC-030: `{line}` is followed by {identifiers}"
        )
    assert result.settings_printed == (), "AC-030: no value of a setting is printed"
