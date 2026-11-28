"""Acceptance test of check AC-015 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets
      --run 20261101T100000Z-example-a

(one line)

→ the output contains the line `retrieval misses: 4`, followed by the four lines ` hxa-002`, `
hxa-003`, ` hxa-004` and ` hxb-002`; it names neither `hxa-005` nor `hxb-001` as a miss.

Covers US2, FR-013 and SC-003.

The command is that of AC-012. `hxa-005` and `hxb-001` have no generation list: a question
without that list is never a retrieval miss, whatever its status. The command reads the run
record and the question-set record and writes nothing. The test needs neither the store, the
provider nor the dataset host and carries no marker.
"""

COMMAND = (
    "python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets"
    " --run 20261101T100000Z-example-a"
)

MISSES = ["  hxa-002", "  hxa-003", "  hxa-004", "  hxb-002"]


def test_ac_015_the_report_lists_the_retrieval_misses(run_command):
    """AC-015: the questions whose generation list exists and lacks a gold article, and no
    question without a generation list."""
    result = run_command(COMMAND)

    assert "retrieval misses: 4" in result.lines, (
        "AC-015: the output contains the line `retrieval misses: 4`"
    )
    start = result.lines.index("retrieval misses: 4")
    assert result.lines[start + 1 : start + 5] == MISSES, (
        "AC-015: the line is followed by the four lines `  hxa-002`, `  hxa-003`, `  hxa-004` "
        "and `  hxb-002`"
    )
    listed = []
    for line in result.lines[start + 1 :]:
        if not line.startswith("  "):
            break
        listed.append(line.strip())
    assert "hxa-005" not in listed, "AC-015: `hxa-005` is not named as a miss"
    assert "hxb-001" not in listed, "AC-015: `hxb-001` is not named as a miss"
