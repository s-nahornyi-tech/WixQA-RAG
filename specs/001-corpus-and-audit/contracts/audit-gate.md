# Contract: the audit as a gate

**Feature**: `001-corpus-and-audit` | **Date**: 2026-11-24 | **Plan**: [../plan.md](../plan.md)

FR-016 requires that later features can use the audit as a gate: one call before a run retrieves anything, whose outcome other than passed stops that run. This file fixes that call. The command `python -m wixqa_rag index audit` is a thin layer over it: it prints the report, writes the result file and turns the outcome into an exit code.

## The call

```python
from wixqa_rag.audit import AuditNotPassed, AuditOutcome, audit_index, require_passed_audit

# Reports the outcome; does not raise for any of the three outcomes.
result = audit_index("wixqa-001")

# The gate: returns the result when the audit passed, raises AuditNotPassed otherwise.
result = require_passed_audit("wixqa-001")
```

| Name | Kind | Meaning |
|---|---|---|
| `audit_index(index, data_dir=None, questions=None)` | function | Audits the index and returns an `AuditResult` |
| `require_passed_audit(index, data_dir=None, questions=None)` | function | Calls `audit_index`; returns the result when its outcome is passed, raises `AuditNotPassed` otherwise |
| `AuditResult` | value | The fields of the audit result in [records.md](records.md), an `outcome`, and a `reason` that is set only when the audit was not carried out |
| `AuditOutcome` | enumeration | `PASSED`, `FAILED`, `NOT_CARRIED_OUT` |
| `AuditNotPassed` | exception | Carries the `AuditResult`, so the caller can record why the run stopped |

**Arguments.**

- `index`: the index identifier.
- `data_dir`: the data directory to audit against. Without it, the default data directory of the pinned dataset.
- `questions`: the question set, as pairs of a question identifier and its list of article ids. Without it, every question of every question part of the data directory, named by question reference (data-model.md, "Question"). Spec 2 passes the golden set here.

## Rules

1. The call reads the article ids from the store, from the table that retrieval queries. It does not read them from a file (FR-011).
2. The call reads `DATABASE_URL` from the environment. It never calls the embedding provider and needs no provider key.
3. The call changes nothing: not the store, not the data directory, not a record. Writing the result into a run record is the caller's task (spec 2 fixes how).
4. `audit_index` returns `NOT_CARRIED_OUT` with a reason when the store cannot be reached, the index does not exist or is not complete, the data directory fails the dataset check, or an error occurs. It does not let such an error look like `FAILED`, and it does not raise it.
5. A caller that is about to retrieve uses `require_passed_audit`. A run that receives `AuditNotPassed` stops before it retrieves anything.
6. The result converts to the JSON document of [records.md](records.md) and back without loss.
