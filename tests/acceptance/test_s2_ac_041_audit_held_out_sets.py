"""Acceptance test of check AC-041 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag index audit --index wixqa-001 --set held-out-001
    && python -m wixqa_rag index audit --index wixqa-001 --set synthetic-001

(one line)

→ exit code 0; the output contains `question set: held-out-001 (held-out)` with
`questions: 200`, `question set: synthetic-001 (held-out)` with `questions: 300`, and for
both audits `unknown question references: 0` and `audit: passed`.

Covers US1, FR-008 and SC-002.

The two commands audit the index of the published dataset with each of the two held-out
sets as the question set. The test has no fixture that fetches or builds: it relies on the
copy of the dataset that the test of spec 1's AC-001 left, on the index `wixqa-001` that the
workflow restored from its snapshot, and on the three records under `evals/golden/`, which
the tests of AC-001, AC-037 and AC-038 wrote before it in the same run or which are in the
checkout (tasks.md, "How the tests are run"). It runs only in the scope `full` on GitHub
Actions. The audit calls no provider, so the test carries `real_data` and `store` only. The
audit results go to `data/audits/` of the checkout, which Git ignores.
"""

import pytest

pytestmark = [pytest.mark.real_data, pytest.mark.store]

COMMAND = (
    "python -m wixqa_rag index audit --index wixqa-001 --set held-out-001"
    " && python -m wixqa_rag index audit --index wixqa-001 --set synthetic-001"
)

AUDITS = (
    ("question set: held-out-001 (held-out)", "questions: 200"),
    ("question set: synthetic-001 (held-out)", "questions: 300"),
)


def test_ac_041_every_gold_article_of_the_held_out_sets_is_in_the_index(run_command):
    """AC-041 and SC-002: each audit names its question set and the number of its questions
    and finds every gold article in the index."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-041: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    blocks = result.blocks()
    assert len(blocks) == 2, "AC-041: two audits, each with its verdict line"
    for block, (question_set, questions) in zip(blocks, AUDITS, strict=True):
        for line in (question_set, questions, "unknown question references: 0", "audit: passed"):
            assert line in block, (
                f"AC-041: the audit with `{question_set}` prints the line `{line}`"
            )
