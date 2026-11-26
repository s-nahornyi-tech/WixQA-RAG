"""Acceptance test of check AC-014 (specs/001-corpus-and-audit/spec.md, "Acceptance Checks").

    env -u OPENAI_API_KEY python -m wixqa_rag index build --data-dir tests/data/example
        --index needs-key

→ exit code 2 and a line that names `OPENAI_API_KEY` as missing.

Covers US2 and FR-017.

The key is asked for in the fifth step of the build, after the store was reached and showed
that `needs-key` has to be built (contracts/cli.md, "`index build`"), so the test needs the
store and carries the marker `store`. It calls no provider. No index `needs-key` exists: no
test builds one, and this command is not carried out.
"""

import pytest

pytestmark = pytest.mark.store

COMMAND = (
    "env -u OPENAI_API_KEY python -m wixqa_rag index build"
    " --data-dir tests/data/example --index needs-key"
)


def test_ac_014_without_the_provider_key_the_build_names_the_missing_setting(run_command):
    """AC-014: a missing credential is named by its variable; the command is not carried out."""
    result = run_command(COMMAND)

    assert result.exit_code == 2, (
        f"AC-014: exit code 2 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert any("OPENAI_API_KEY" in line for line in result.lines), (
        "AC-014: a line of the output names `OPENAI_API_KEY` as missing"
    )
