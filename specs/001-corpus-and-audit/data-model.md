# Data Model: Corpus and audit

**Feature**: `001-corpus-and-audit` | **Date**: 2026-11-24 | **Plan**: [plan.md](plan.md)

The entities of the spec: their fields, the rules that hold for them, and where each one is stored. The exact shape of every JSON file is in [contracts/records.md](contracts/records.md); the reasons behind the choices are in [research.md](research.md).

## Overview

```text
dataset.json ──fetch──▶ data directory ──check──▶ passed / failed
(pinned revision)       (part files + manifest.json)
                              │
                              │ corpus part
                              ▼
                        split into passages ──embed──▶ index in the store ──▶ build record
                                                       (schema idx_<identifier>)
                                                              │
        data directory (corpus ids, questions) ───────────────┤
                                                              ▼
                                                        audit ──▶ audit result
                                                                  passed / failed / not carried out
```

## Pinned revision

The one revision of `Wix/WixQA` that the study uses (FR-001).

- **Stored in**: `dataset.json` at the repository root, in version control.
- **Fields**: the dataset name, `Wix/WixQA`; the revision, a commit hash of 40 hexadecimal characters; the list of parts, each with a name, a role, a path inside the dataset and a row count.
- **Rules**:
  - The revision is a full commit hash, never a branch name.
  - Exactly one part has the role `corpus`; every other part has the role `questions`. Part names are unique.
  - Every command of this feature reads the revision from this file and from nowhere else.
  - The file changes only through a pull request. A change of the revision or of a row count is an amendment of the spec.

Values on the day of the plan:

| Part | Role | Path | Rows |
|---|---|---|---|
| `wix_kb_corpus` | `corpus` | `wix_kb_corpus/wix_kb_corpus.jsonl` | 6,221 |
| `wixqa_expertwritten` | `questions` | `wixqa_expertwritten/test.jsonl` | 200 |
| `wixqa_simulated` | `questions` | `wixqa_simulated/test.jsonl` | 200 |
| `wixqa_synthetic` | `questions` | `wixqa_synthetic/test.jsonl` | 6,221 |

Revision: `d662dc42479c14e202eccd832f8c4b66a035c4cc`. The last two paths and all four row counts are confirmed by the first fetch (research.md, "Not checked").

## Part

One file of a dataset in JSON Lines form: one JSON object per line. A *row* is a non-empty line.

- **Role `corpus`**: every row is an article.
- **Role `questions`**: every row is a question.

## Data directory

A folder that holds the part files of one dataset and a `manifest.json` (FR-002, FR-003).

- **The default data directory** is `data/wixqa/<revision>/`, written by `dataset fetch`. It is outside version control.
- **An example data directory** is a folder under `tests/data/`, written by the testing agent and kept in version control.
- **Manifest fields**: the dataset name; the revision, or `null` for a dataset that is not published; the time of the fetch in UTC, or `null`; the list of parts, each with name, role, path, row count, size in bytes and SHA-256 of the file.
- **Rules of the manifest**: the same as for `dataset.json`: one corpus part, unique part names.
- **The manifest is written last.** A data directory without a manifest is not a local copy.

The dataset check (FR-004) reports a *difference* for each of the following, and passes when there is none:

| # | Difference | Compared with |
|---|---|---|
| 1 | The file of a part is missing | the manifest |
| 2 | The row count of a part differs | the manifest |
| 3 | The SHA-256 of a part differs | the manifest |
| 4 | A row is not a JSON object | |
| 5 | An article row lacks `id`, `url`, `contents` or `article_type`, or a question row lacks `question`, `answer` or `article_ids` | the fields listed under "Data" in `PROJECT.md` |
| 6 | An `id` is not a string, or `article_ids` is not a list of strings | |
| 7 | An article `id` occurs more than once in the corpus part | |
| 8 | Default directory only: the dataset name, the revision, a part or a row count of the manifest differs from `dataset.json` | `dataset.json` |

A field is absent when the row has no such key or the value is `null`. An empty `contents` and an empty `article_ids` list are not differences; the build and the audit report them (see "Passage" and "Audit result").

No command writes to a part file after it has been stored (FR-005).

## Article

One row of the corpus part.

| Field | Type | Use in this feature |
|---|---|---|
| `id` | string | The article id. Passages carry it, questions refer to it, and the audit compares it |
| `url` | string | Checked for presence only |
| `contents` | string | The text that is split into passages |
| `article_type` | string | Checked for presence only |

## Question

One row of a question part.

| Field | Type | Use in this feature |
|---|---|---|
| `question` | string | Checked for presence only |
| `answer` | string | Checked for presence only |
| `article_ids` | list of strings | The articles the audit looks for in the index |

A question row carries no identifier. Until spec 2 fixes the form of a question identifier, a question is named by a *question reference*: the name of its part, a hyphen, and its row number counted from 1 in file order and written with at least three digits. Examples: `wixqa_expertwritten-017`, `wixqa_synthetic-6221`, `exq-003`.

## Passage

A piece of the text of one article (FR-007).

| Field | Type | Rule |
|---|---|---|
| `article_id` | string | The `id` of the article the passage comes from |
| `passage_no` | integer | Position within the article, counted from 0 |
| `text` | string | Not empty; at most `max_chars` characters |
| `embedding` | vector of 1536 numbers | What the embedding model returned for `text` |

Passages are produced by the splitting rule `line-pack-v1` with `max_chars = 2000`, defined step by step in research.md, section 12. The rule is the same for every article of an index. An article whose `contents` has no non-empty line produces no passage: the build lists it under "articles without passages", and the audit then names it as missing from the index.

## Index

The passages of one corpus, embedded with one model under one splitting rule (FR-006 to FR-009).

**Identifier.** Lower-case letters, digits and single hyphens; it starts and ends with a letter or a digit; at most 40 characters. `wixqa-001`, `example` and `no-such-index` are valid. A command given any other identifier is not carried out.

**In the store.** One PostgreSQL schema per index, named `idx_` followed by the identifier with each hyphen replaced by an underscore.

```sql
CREATE SCHEMA idx_wixqa_001;

CREATE TABLE idx_wixqa_001.passages (
    article_id  text         NOT NULL,
    passage_no  integer      NOT NULL CHECK (passage_no >= 0),
    text        text         NOT NULL CHECK (text <> ''),
    embedding   vector(1536) NOT NULL,
    PRIMARY KEY (article_id, passage_no)
);

CREATE TABLE idx_wixqa_001.build (
    only_row     boolean     PRIMARY KEY DEFAULT true CHECK (only_row),
    record       jsonb       NOT NULL,
    completed_at timestamptz NOT NULL
);
```

- `passages` is the table that retrieval will query (spec 3). The audit reads the article ids of the index from it: the distinct `article_id` values.
- `build` holds at most one row. The row is the mark of completion (FR-009), and `record` is the build record.
- The `vector` type comes from the pgvector extension, which the build enables in the database before it creates the first index.

**Life of an identifier.**

```text
absent ──build (one transaction)──▶ complete
```

- A build creates the schema and both tables, inserts every passage, inserts the `build` row last and commits. Until the commit, no other connection sees any of it.
- A build that stops for any reason is rolled back, and the identifier stays absent.
- This feature has no command that changes or removes a complete index.
- A schema `idx_…` without its `build` row cannot result from a build. If one exists, for example because it was made by hand, the index is *not complete*: the audit is not carried out for it, and a build under its identifier is refused.

**Same corpus and settings** (FR-008) means that all of these are equal: the SHA-256 of the corpus file, the embedding model, the vector size, the splitting rule and its parameters. The table in research.md, section 15, lists what `index build` does in every case.

## Build record

What one build was made of and what it cost (FR-010, SC-005).

- **Stored in**: the `build` table of the index, and a file `build.json`. For a build from the pinned dataset, which is a build without `--data-dir`, the file is `evals/indexes/<index>/build.json`, in version control. For a build with `--data-dir` the file is `data/indexes/<index>/build.json`, outside version control.
- **Fields**: the index identifier; the dataset name, its revision and the SHA-256 of the corpus file; the embedding model as requested and as the provider reported it, and the vector size; the splitting rule and its parameters; the number of articles and of passages; the ids of the articles without passages; the number of tokens embedded; the price in US dollars per million tokens; the cost in US dollars; the start time in UTC; the commit of the code, and whether the working tree had uncommitted changes.
- **Rules**:
  - A record is written once and never changed. The build writes the file under a temporary name, commits the transaction, and then gives the file its final name.
  - `cost_usd` = `tokens_embedded` × `price_usd_per_million_tokens` ÷ 1,000,000.
  - `articles` is the number of rows of the corpus part. The number of articles in the index is `articles` minus the number of articles without passages.
  - The record contains no credential (FR-017).

## Audit result

The outcome of one audit of one index against one data directory (FR-011 to FR-015).

With *C* the set of `id` values of the corpus part, *I* the set of distinct `article_id` values of the index's `passages` table, and *Q* the question set:

| Field | Definition |
|---|---|
| `missing_from_index` | The ids in *C* and not in *I*, sorted |
| `not_in_corpus` | The ids in *I* and not in *C*, sorted |
| `unknown_references` | Every pair of a question in *Q* and one of its `article_ids` values that is not in *I*, sorted by question and id. An id that a question names twice counts once |
| `questions_without_article_ids` | The number of questions in *Q* whose `article_ids` list is empty |
| `outcome` | `passed` when the three lists are empty, otherwise `failed` |

- **The question set** is, until the golden set exists, every question of every question part of the data directory (FR-013). A caller may pass another question set (see [contracts/audit-gate.md](contracts/audit-gate.md)).
- **Other fields**: the index identifier; the dataset name and revision; a description of the question set with its number of questions; the number of articles in the corpus and in the index; the time of the audit in UTC.
- **Stored in**: the file given with `--json`, otherwise `data/audits/<index>/<time>.json`. The audit made right after the build of an index from the pinned dataset is kept as `evals/indexes/<index>/audit.json`.

**Three outcomes** (FR-014):

| Outcome | When | Exit code | Result file |
|---|---|---|---|
| passed | The audit ran to the end, and the three lists are empty | 0 | written |
| failed | The audit ran to the end, and at least one list is not empty | 1 | written |
| not carried out | The store cannot be reached, the index does not exist or is not complete, the data directory fails the dataset check, or any other error | 2 | not written |

An audit that is not carried out is never reported as passed or as failed.

## Snapshot record

Where the dump of an index is kept (research.md, section 7). The acceptance workflow writes it; no command of the application reads it.

- **Stored in**: `evals/indexes/<index>/snapshot.json`, in version control.
- **Fields**: the index identifier; the name, the size in bytes and the SHA-256 of the dump file; the format; the PostgreSQL and pgvector versions it was made with; the repository and the release tag it is attached to; the time in UTC; the identifier of the workflow run.

## Example datasets

Five data directories under `tests/data/`, written for the acceptance checks and not taken from `Wix/WixQA` (spec, "Assumptions"). Each has a corpus part `ex` and a question part `exq`, and a manifest whose row counts and fingerprints match its own files, so each directory differs from `example` in exactly one way.

| Directory | Articles | Questions | The one difference |
|---|---|---|---|
| `example` | `ex-001` to `ex-005` | `exq-001` to `exq-003` | none |
| `example-damaged` | as `example`, with the row of `ex-002` twice | as `example` | fails the dataset check: a repeated article id |
| `example-one-more-article` | `ex-001` to `ex-006` | as `example` | one article that an index built from `example` does not hold |
| `example-one-less-article` | `ex-001` to `ex-004` | as `example` | lacks one article that an index built from `example` holds |
| `example-unknown-reference` | as `example` | `exq-003` also names `ex-999` | one question reference to an article that no index holds |

The questions name only the articles `ex-001` to `ex-004`, and one question names two articles, so that every audit of these directories shows exactly the difference in the table and nothing else.
