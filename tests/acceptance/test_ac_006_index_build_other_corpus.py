"""Acceptance test of check AC-006 (specs/001-corpus-and-audit/spec.md, "Acceptance Checks").

    python -m wixqa_rag index build --data-dir tests/data/example --index example
    && python -m wixqa_rag index build --data-dir tests/data/example-one-more-article
       --index example

(one line)

→ exit code 2 and the line `index build: refused`, with the reason that `example` exists with
another corpus.

Covers US2 and FR-008.

`example-one-more-article` holds the article `ex-006` on top of those of `example`, so its
corpus file has another fingerprint. The test needs the store and the provider key and runs
in the scope `example` on GitHub Actions.
"""

import pytest

pytestmark = [pytest.mark.store, pytest.mark.provider]

COMMAND = (
    "python -m wixqa_rag index build --data-dir tests/data/example --index example"
    " && python -m wixqa_rag index build --data-dir tests/data/example-one-more-article"
    " --index example"
)


def test_ac_006_another_corpus_under_an_existing_identifier_is_refused(run_command):
    """AC-006: building under an identifier that exists with another corpus is refused."""
    result = run_command(COMMAND)

    assert result.exit_code == 2, (
        f"AC-006: exit code 2 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "index build: refused" in result.lines, (
        "AC-006: the output contains the line `index build: refused`"
    )
    # contracts/cli.md, "`index build`": `reason: index <ID> exists with another corpus`.
    reasons = [line for line in result.lines if line.startswith("reason:")]
    assert any("example" in line and "another corpus" in line for line in reasons), (
        "AC-006: the reason says that `example` exists with another corpus; got: "
        + " | ".join(reasons)
    )
