"""Acceptance test of check AC-010 (specs/001-corpus-and-audit/spec.md, "Acceptance Checks").

    python -m wixqa_rag index build --data-dir tests/data/example --index example
    && python -m wixqa_rag index audit --data-dir tests/data/example-one-less-article
       --index example

(one line)

→ exit code 1; the output contains `not in corpus: 1`, the id `ex-005` and `audit: failed`.

Covers US3, FR-011, FR-012, FR-014 and SC-003.

`example-one-less-article` lacks the article `ex-005`, which an index built from `example`
holds. The build embeds the five example passages with the provider, unless an earlier test of
the same run has already built `example`; the test needs the store and the provider key and
runs in the scope `example` on GitHub Actions. The audit result goes to `data/audits/` of
the checkout, which Git ignores.
"""

import pytest

pytestmark = [pytest.mark.store, pytest.mark.provider]

COMMAND = (
    "python -m wixqa_rag index build --data-dir tests/data/example --index example"
    " && python -m wixqa_rag index audit --data-dir tests/data/example-one-less-article"
    " --index example"
)


def test_ac_010_an_article_that_the_corpus_does_not_contain_is_named(run_command):
    """AC-010: an index that holds one article which the corpus does not contain; the audit
    fails and names that article id as not in the corpus."""
    result = run_command(COMMAND)

    assert result.exit_code == 1, (
        f"AC-010: exit code 1 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert "not in corpus: 1" in result.lines, (
        "AC-010: the output contains the line `not in corpus: 1`"
    )
    assert any("ex-005" in line for line in result.lines), "AC-010: the output names `ex-005`"
    assert "audit: failed" in result.lines, "AC-010: the output contains `audit: failed`"
