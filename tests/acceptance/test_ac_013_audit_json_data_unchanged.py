"""Acceptance test of check AC-013 (specs/001-corpus-and-audit/spec.md, "Acceptance Checks").

    python -m wixqa_rag index build --data-dir tests/data/example --index example
    && python -m wixqa_rag index audit --data-dir tests/data/example --index example
       --json data/audit-example.json
    && python -m wixqa_rag dataset check --data-dir tests/data/example

(one line)

→ exit code 0; `data/audit-example.json` is one JSON document with `"outcome": "passed"` and
the empty lists `missing_from_index`, `not_in_corpus` and `unknown_references`; the last line
of the output is `dataset check: passed`.

Covers US3, FR-005, FR-015 and SC-004.

The build embeds the five example passages with the provider, unless an earlier test of the
same run has already built `example`; the test needs the store and the provider key and runs
in the scope `example` on GitHub Actions. The result file is written where the check says,
under `data/` of the checkout, which Git ignores; a file left there by an earlier run is
replaced (contracts/cli.md, "`index audit`").
"""

import json

import pytest

pytestmark = [pytest.mark.store, pytest.mark.provider]

COMMAND = (
    "python -m wixqa_rag index build --data-dir tests/data/example --index example"
    " && python -m wixqa_rag index audit --data-dir tests/data/example --index example"
    " --json data/audit-example.json"
    " && python -m wixqa_rag dataset check --data-dir tests/data/example"
)
RESULT_FILE = "data/audit-example.json"


def test_ac_013_the_audit_result_is_written_and_the_data_is_unchanged(run_command, repository_root):
    """AC-013: the audit of the example index against its own data passes and writes its
    result in a machine-readable form, and the data still passes the dataset check."""
    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-013: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    document = json.loads((repository_root / RESULT_FILE).read_text(encoding="utf-8"))
    assert isinstance(document, dict), f"AC-013: {RESULT_FILE} is one JSON document"
    assert document["outcome"] == "passed", 'AC-013: the document has `"outcome": "passed"`'
    for name in ("missing_from_index", "not_in_corpus", "unknown_references"):
        assert document[name] == [], f"AC-013: the list `{name}` is empty"
    assert result.last_line == "dataset check: passed", (
        "AC-013: the last line of the output is `dataset check: passed`"
    )
