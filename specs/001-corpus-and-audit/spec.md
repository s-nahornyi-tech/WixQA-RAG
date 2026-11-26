# Feature Specification: Corpus and audit

**Feature Branch**: `001-corpus-and-audit`

**Created**: 2026-11-24

**Status**: Approved by the owner on 2026-11-24

**Input**: User description: "Corpus and audit (spec 1 of the "Spec order" table in PROJECT.md). Fetch the Wix/WixQA dataset at a pinned revision (the retrieval corpus wix_kb_corpus and the three question parts), build the retrieval index from the corpus in the vector store and with the embedding model that the constitution lists as decided, and audit the index against the dataset as Principle I of the constitution requires: the article ids held in the index are exactly the id values of the corpus, and every article_ids value of every question to be asked is among them; the audit queries the index that retrieval uses, any difference stops with a failure that names the ids, and the audit result is recorded. Acceptance: zero mismatches on the real data, and every kind of mismatch is caught on a small example with a known answer."

## User Scenarios & Testing *(mandatory)*

The person who runs a command is called the *operator* in this spec: the owner, an agent, or a reader of the repository.

### User Story 1 - Fetch the dataset at the pinned revision (Priority: P1)

The operator fetches the `Wix/WixQA` dataset at the revision that the repository pins and gets the same data as every other operator: the corpus of help-center articles and the three question parts. A later check tells whether the local copy still matches what was fetched.

**Why this priority**: Every later step of this feature and every later spec reads this data. A result can be repeated only when every operator starts from the same revision.

**Independent Test**: On a checkout without downloaded data, run the fetch and then the check. The fetch reports the pinned revision and the row count of each part, and the check passes.

**Acceptance Scenarios**:

1. **Given** a checkout without downloaded data, **When** the operator fetches the dataset, **Then** the corpus and the three question parts are stored locally, outside version control, and the report names the pinned revision and the row count of each part.
2. **Given** a complete local copy, **When** the operator fetches again, **Then** nothing is downloaded and the report gives the same counts.
3. **Given** a local copy in which a row is missing, an article `id` is repeated, or a file has changed since it was fetched, **When** the operator checks the copy, **Then** the check fails and names what differs.

---

### User Story 2 - Build the index from the corpus (Priority: P2)

The operator builds the retrieval index from the fetched corpus. Each article is split into passages by one recorded rule, each passage is embedded, and each passage is stored with the `id` of its article. The build leaves a record that tells a reader how to repeat it and what it cost.

**Why this priority**: Retrieval (spec 3) reads this index, and the audit of User Story 3 needs an index to audit.

**Independent Test**: Build an index from a small example corpus and read the report: it gives the number of example articles and marks the index complete. Build again under the same identifier: nothing is embedded a second time.

**Acceptance Scenarios**:

1. **Given** a fetched corpus that passes the check, **When** the operator builds an index, **Then** every article of the corpus has at least one passage in the index, every passage carries the `id` of its article, and the index is marked complete.
2. **Given** a completed build, **When** a reader opens its build record, **Then** the record names the index, the dataset revision, the embedding model, the splitting rule with its parameters, the number of articles and passages, the tokens embedded, the price used, the cost in US dollars, the start time and the commit of the code.
3. **Given** a complete index, **When** the operator builds again under the same identifier with the same corpus and settings, **Then** nothing is embedded again and the report says that the index is already complete.
4. **Given** a complete index, **When** the operator builds under the same identifier with a different corpus or different settings, **Then** the build is refused and the existing index is unchanged.
5. **Given** a build that stopped part-way, **When** the operator audits that index, **Then** the audit is not carried out, because the index is not marked complete.

---

### User Story 3 - Audit the index against the dataset (Priority: P3)

Before anything is retrieved from an index, the operator audits it. The audit asks the index itself which articles it holds and compares the answer with the dataset: the article ids in the index must be exactly the `id` values of the corpus, and every article that a question names must be in the index. Any difference ends the audit with a failure that names the ids.

**Why this priority**: This is Principle I of the constitution. An article that is absent from the index looks exactly like a retrieval miss, and the audit is what tells the two apart. It is third only because it needs the data and an index.

**Independent Test**: Audit an index built from a small example against the same example: the audit passes. Audit it against three altered examples, each with one known difference: the audit fails each time and names exactly that difference.

**Acceptance Scenarios**:

1. **Given** a complete index built from the fetched corpus, **When** the operator audits it, **Then** the audit reports no article missing from the index, no article in the index that is not in the corpus, and no question reference outside the index, and it passes.
2. **Given** a corpus with one article that the index does not hold, **When** the operator audits, **Then** the audit fails and names that article `id` as missing from the index.
3. **Given** an index that holds one article which the corpus does not contain, **When** the operator audits, **Then** the audit fails and names that article `id` as not in the corpus.
4. **Given** a question whose `article_ids` names an article that the index does not hold, **When** the operator audits, **Then** the audit fails and names the question and the article `id`.
5. **Given** an index that does not exist or is not complete, or a vector store that cannot be reached, **When** the operator audits, **Then** the audit ends as not carried out and states the reason; it is reported neither as passed nor as failed.
6. **Given** an audit that ran to the end, **When** it finishes, **Then** its result is written in a machine-readable form: the index, the dataset revision, the question set, the three lists of differences and the outcome.

---

### Edge Cases

- What happens when the dataset cannot be downloaded? The fetch is not carried out and states the reason; an existing local copy stays as it was.
- What happens when a row count at the pinned revision differs from the count recorded with it? The fetch fails and names both numbers.
- What happens when an article has no text? The build reports every article that produced no passage. Such an article is not in the index, so the audit names it as missing.
- What happens when a question has an empty `article_ids` list? The audit has nothing to check for it, and the result gives the number of such questions.
- What happens when one question names the same article twice? The article is checked once.
- What happens when a credential for the embedding provider or the vector store is missing? The command is not carried out and names the missing setting. No secret is printed or stored.

## Requirements *(mandatory)*

### Functional Requirements

**Dataset**

- **FR-001**: The repository MUST record one revision of `Wix/WixQA` as the pinned revision, together with the row count of each of its four parts. Every command of this feature MUST use the pinned revision.
- **FR-002**: The fetch MUST store the corpus and the three question parts locally, outside version control, and MUST report the pinned revision and the row count of each part. It MUST fail when a row count differs from the one recorded with the pinned revision.
- **FR-003**: The fetch MUST record a fingerprint of each file it stores. A fetch over a complete, matching local copy MUST download nothing.
- **FR-004**: The dataset check MUST fail, and name the difference, when a part is missing, a row count differs from the recorded one, a fingerprint no longer matches, an article `id` occurs more than once, or a required field is absent. The required fields are those listed under "Data" in `PROJECT.md`.
- **FR-005**: No command of this feature changes a question, an answer or an article. A defect found in the data is reported; the data stays as published.

**Index**

- **FR-006**: An index MUST be built only from a corpus that passes the dataset check, in the vector store and with the embedding model that the constitution lists as decided under "Stack".
- **FR-007**: Every article MUST be split into passages by one splitting rule, the same for all articles of an index. Every passage MUST be stored with the `id` of the article it comes from.
- **FR-008**: Every index MUST have an identifier. Building under an identifier that already exists MUST embed nothing: with the same corpus and settings the build reports the existing index, and with any difference it is refused.
- **FR-009**: An index MUST be marked complete only after every article of the corpus has been processed. An index that is not complete MUST NOT be accepted by the audit.
- **FR-010**: Every build MUST leave a build record, written once: the index identifier, the dataset revision, the identifier of the embedding model as specific as its provider offers, the splitting rule and its parameters, the number of articles and passages, the articles that produced no passage, the number of tokens embedded, the price used, the cost in US dollars, the start time in UTC and the commit of the code. The build record of an index built from the pinned dataset is kept in the repository; the record of an index built from other data is kept outside version control.

**Audit**

- **FR-011**: The audit MUST take the article ids from the index itself: the same store and the same index that retrieval queries. Reading files on disk does not satisfy this requirement.
- **FR-012**: The audit MUST compare the article ids that have at least one passage in the index with the `id` values of the corpus, and MUST list every `id` that is in the corpus and not in the index, and every `id` that is in the index and not in the corpus.
- **FR-013**: The audit MUST check every `article_ids` value of every question in its question set, and MUST list every pair of question and article `id` whose article is not in the index. Until the golden set exists (spec 2), the question set is every question of the three question parts.
- **FR-014**: The audit MUST end in exactly one of three outcomes that a program can tell apart: passed, when all three lists are empty; failed, when at least one of them is not; not carried out, with the reason, when the audit could not be completed.
- **FR-015**: The audit MUST write its result in a machine-readable form: the index identifier, the dataset revision, the question set, the number of articles in the corpus and in the index, the three lists in full, the outcome and the time in UTC.
- **FR-016**: The audit MUST be usable as a gate by later features: one call that later specs make before a run retrieves anything, and whose outcome other than passed stops that run.

**All commands**

- **FR-017**: Credentials for the embedding provider and the vector store MUST be read from the environment. They MUST NOT appear in the repository, in a record or in the output of a command.

### Key Entities *(include if feature involves data)*

- **Pinned revision**: the one revision of `Wix/WixQA` that the study uses, recorded in the repository with the row count of each part.
- **Article**: one row of `wix_kb_corpus`; its `id` is what questions refer to.
- **Question**: one row of a question part; its `article_ids` lists the articles needed for the answer.
- **Passage**: a piece of one article's text, stored in the index with that article's `id`.
- **Index**: the passages of one corpus, embedded with one model under one splitting rule; it has an identifier and a build record.
- **Audit result**: the outcome of one audit of one index, with the three lists of differences.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the pinned dataset, the audit of the index built by this feature reports zero mismatches: no article missing from the index, no article in the index that is not in the corpus, and no question reference outside the index.
- **SC-002**: The fetched dataset holds 6,221 articles and 6,621 questions (200, 200 and 6,221 in the three parts), the counts recorded in `PROJECT.md`.
- **SC-003**: Each of the three kinds of mismatch, introduced on purpose in a small example with a known answer, is caught: the audit fails and names exactly the ids that differ.
- **SC-004**: Repeating the build and the audit on the same data gives the same number of articles in the index and the same audit outcome, and leaves the data unchanged.
- **SC-005**: The cost of building the index can be read from its build record.

## Acceptance Checks *(mandatory)*

Each check is one command and the result a reader can observe. Every check fails before the feature is implemented and passes once it is implemented. The testing agent turns each check into an automated acceptance test before any implementation is written (constitution, "Development Workflow"). This section alone names commands; the sections above stay technology-agnostic.

Every command ends with one of three exit codes: `0` when it passed or did its work, `1` when a check or an audit found a difference, `2` when it was not carried out. The folders under `tests/data/` are small example datasets written for these checks: five articles, `ex-001` to `ex-005`, and three questions, `exq-001` to `exq-003`. `example-damaged` repeats the article id `ex-002`; `example-one-more-article` adds the article `ex-006`; `example-one-less-article` lacks the article `ex-005`; in `example-unknown-reference` the question `exq-003` names the article `ex-999`.

- **AC-001** (covers US1, FR-001, FR-002, FR-003, SC-002): `python -m wixqa_rag dataset fetch && python -m wixqa_rag dataset fetch` → exit code 0; the output names the pinned revision and contains the lines `wix_kb_corpus: 6221`, `wixqa_expertwritten: 200`, `wixqa_simulated: 200` and `wixqa_synthetic: 6221`; the second fetch prints `nothing downloaded`
- **AC-002** (covers US1, FR-004): `python -m wixqa_rag dataset check` → exit code 0 and the line `dataset check: passed`
- **AC-003** (covers US1, FR-004): `python -m wixqa_rag dataset check --data-dir tests/data/example-damaged` → exit code 1, the line `dataset check: failed`, and a line that names the repeated article id `ex-002`
- **AC-004** (covers US2, FR-006, FR-007, FR-009, FR-010, SC-005): `python -m wixqa_rag index build --index wixqa-001` → exit code 0; the output contains `articles: 6221`; afterwards the file `evals/indexes/wixqa-001/build.json` names the pinned revision, the embedding model, the splitting rule and `cost_usd`
- **AC-005** (covers US2, FR-008): `python -m wixqa_rag index build --data-dir tests/data/example --index example && python -m wixqa_rag index build --data-dir tests/data/example --index example` → exit code 0; the second build prints `index: example (already complete)` and `tokens embedded: 0`
- **AC-006** (covers US2, FR-008): `python -m wixqa_rag index build --data-dir tests/data/example --index example && python -m wixqa_rag index build --data-dir tests/data/example-one-more-article --index example` → exit code 2 and the line `index build: refused`, with the reason that `example` exists with another corpus
- **AC-007** (covers US2, FR-006): `python -m wixqa_rag index build --data-dir tests/data/example-damaged --index damaged` → exit code 2 and the line `index build: refused`, with the reason that the dataset check failed
- **AC-008** (covers US3, FR-011, FR-012, FR-013, FR-014, FR-016, SC-001): `python -m wixqa_rag index audit --index wixqa-001` → exit code 0; the output contains `missing from index: 0`, `not in corpus: 0`, `unknown question references: 0` and `audit: passed`
- **AC-009** (covers US3, FR-011, FR-012, FR-014, SC-003): `python -m wixqa_rag index build --data-dir tests/data/example --index example && python -m wixqa_rag index audit --data-dir tests/data/example-one-more-article --index example` → exit code 1; the output contains `missing from index: 1`, the id `ex-006` and `audit: failed`
- **AC-010** (covers US3, FR-011, FR-012, FR-014, SC-003): `python -m wixqa_rag index build --data-dir tests/data/example --index example && python -m wixqa_rag index audit --data-dir tests/data/example-one-less-article --index example` → exit code 1; the output contains `not in corpus: 1`, the id `ex-005` and `audit: failed`
- **AC-011** (covers US3, FR-013, FR-014, SC-003): `python -m wixqa_rag index build --data-dir tests/data/example --index example && python -m wixqa_rag index audit --data-dir tests/data/example-unknown-reference --index example` → exit code 1; the output contains `unknown question references: 1`, the question `exq-003`, the id `ex-999` and `audit: failed`
- **AC-012** (covers US3, FR-009, FR-014, FR-016): `python -m wixqa_rag index audit --index no-such-index` → exit code 2 and the line `audit: not carried out`, with the reason that the index `no-such-index` does not exist
- **AC-013** (covers US3, FR-005, FR-015, SC-004): `python -m wixqa_rag index build --data-dir tests/data/example --index example && python -m wixqa_rag index audit --data-dir tests/data/example --index example --json data/audit-example.json && python -m wixqa_rag dataset check --data-dir tests/data/example` → exit code 0; `data/audit-example.json` is one JSON document with `"outcome": "passed"` and the empty lists `missing_from_index`, `not_in_corpus` and `unknown_references`; the last line of the output is `dataset check: passed`
- **AC-014** (covers US2, FR-017): `env -u OPENAI_API_KEY python -m wixqa_rag index build --data-dir tests/data/example --index needs-key` → exit code 2 and a line that names `OPENAI_API_KEY` as missing

## Evidence *(mandatory)*

| Decision or numeric target in this spec | Justified by run | Compared with run |
|---|---|---|
| FR-006: the embedding model and the vector store that the constitution lists as decided | chosen as a starting point, no run | none |
| FR-007: the splitting rule of the first index and its parameters, fixed in the plan of this spec | chosen as a starting point, no run | none |

No baseline run exists yet, so this spec states no numeric quality target.

## Assumptions

- Commands are typed in a POSIX shell at the repository root, in the project's Python environment set up as the README describes. The plan of this spec chooses the tooling for that environment (constitution, `TODO(PYTHON_TOOLING)`).
- The operator has access to the vector store and an account with the embedding provider that the constitution names. Every build, including a build from an example dataset, calls the embedding provider.
- The pinned revision is the newest revision of `Wix/WixQA` on the day the plan of this spec is written.
- The row counts in `PROJECT.md` come from the dataset card. If the pinned revision has other counts, the finding is recorded, `PROJECT.md` is corrected, and this spec is amended with the owner's approval.
- Every `article_ids` value names an article of the corpus, and every article has text. If the build or the audit shows otherwise, the finding is recorded and the owner decides how such questions and articles are treated before the golden set is fixed (spec 2). The data stays as published.
- Searching an index is not part of this feature; it arrives with spec 3. Removing an index is not part of this feature either.
- Spec 2 fixes how a run record includes the audit result. This feature fixes what the result contains.
- The example datasets under `tests/data/` are written for the acceptance checks and are not taken from `Wix/WixQA`.
