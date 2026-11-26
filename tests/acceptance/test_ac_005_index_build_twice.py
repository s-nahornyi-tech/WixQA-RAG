"""Acceptance test of check AC-005 (specs/001-corpus-and-audit/spec.md, "Acceptance Checks").

    python -m wixqa_rag index build --data-dir tests/data/example --index example
    && python -m wixqa_rag index build --data-dir tests/data/example --index example

→ exit code 0; the second build prints `index: example (already complete)` and
`tokens embedded: 0`.

Covers US2 and FR-008.

The first build embeds the five example passages with the provider, unless an earlier test
of the same run has already built `example` from the same directory. The test needs the
store and the provider key and runs in the scope `example` on GitHub Actions. The build
record goes to `data/indexes/example/` of the checkout, which Git ignores.
"""

import pytest

pytestmark = [pytest.mark.store, pytest.mark.provider]

BUILD = "python -m wixqa_rag index build --data-dir tests/data/example --index example"
COMMAND = f"{BUILD} && {BUILD}"

# The verdict line that ends the output of a build (contracts/cli.md, "Verdict lines").
DONE = "index build: done"


def test_ac_005_a_second_build_under_the_same_identifier_embeds_nothing(run_command):
    """AC-005: building again under the same identifier, with the same corpus and settings,
    reports the existing index and embeds nothing."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-005: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    # The output of the second build is what follows the verdict line of the first.
    assert DONE in result.lines, f"AC-005: the first build ends with the line `{DONE}`"
    second_build = result.lines[result.lines.index(DONE) + 1 :]
    assert "index: example (already complete)" in second_build, (
        "AC-005: the second build prints `index: example (already complete)`"
    )
    assert "tokens embedded: 0" in second_build, (
        "AC-005: the second build prints `tokens embedded: 0`"
    )
