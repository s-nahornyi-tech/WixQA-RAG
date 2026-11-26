"""Acceptance test of check AC-009 (specs/001-corpus-and-audit/spec.md, "Acceptance Checks").

    python -m wixqa_rag index build --data-dir tests/data/example --index example
    && python -m wixqa_rag index audit --data-dir tests/data/example-one-more-article
       --index example

(one line)

→ exit code 1; the output contains `missing from index: 1`, the id `ex-006` and `audit: failed`.

Covers US3, FR-011, FR-012, FR-014 and SC-003.

`example-one-more-article` holds the article `ex-006`, which an index built from `example` does
not hold. The build embeds the five example passages with the provider, unless an earlier test of
the same run has already built `example`; the test needs the store and the provider key and
runs in the scope `example` on GitHub Actions. The audit result goes to `data/audits/` of
the checkout, which Git ignores.
"""

import pytest

pytestmark = [pytest.mark.store, pytest.mark.provider]

COMMAND = (
    "python -m wixqa_rag index build --data-dir tests/data/example --index example"
    " && python -m wixqa_rag index audit --data-dir tests/data/example-one-more-article"
    " --index example"
)


def test_ac_009_an_article_missing_from_the_index_is_named(run_command):
    """AC-009: a corpus with one article that the index does not hold; the audit fails and
    names that article id as missing from the index."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-009: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "missing from index: 1" in result.lines, (
        "AC-009: the output contains the line `missing from index: 1`"
    )
    assert any("ex-006" in line for line in result.lines), "AC-009: the output names `ex-006`"
    assert "audit: failed" in result.lines, "AC-009: the output contains `audit: failed`"
