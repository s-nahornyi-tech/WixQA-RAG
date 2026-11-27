# Contract: records

**Feature**: `001-corpus-and-audit` | **Date**: 2026-11-24 | **Plan**: [../plan.md](../plan.md)

The JSON files that the commands of this feature read and write. Every file is UTF-8 text and holds one JSON document. Times are in UTC in the form `2026-11-24T10:15:00Z`. A SHA-256 is written as 64 lower-case hexadecimal characters. The values in the examples are illustrations, not results.

A file listed as "written once" is never changed after it has been written. A later spec may add fields to a record; it does not rename or remove one without amending this contract.

## `dataset.json`: the pinned revision

At the repository root, in version control. Written by an agent in a pull request and read by every command (FR-001).

```json
{
  "name": "Wix/WixQA",
  "revision": "d662dc42479c14e202eccd832f8c4b66a035c4cc",
  "parts": [
    {"name": "wix_kb_corpus", "role": "corpus", "path": "wix_kb_corpus/wix_kb_corpus.jsonl", "rows": 6221},
    {"name": "wixqa_expertwritten", "role": "questions", "path": "wixqa_expertwritten/test.jsonl", "rows": 200},
    {"name": "wixqa_simulated", "role": "questions", "path": "wixqa_simulated/test.jsonl", "rows": 200},
    {"name": "wixqa_synthetic", "role": "questions", "path": "wixqa_synthetic/test.jsonl", "rows": 6221}
  ]
}
```

| Field | Type | Meaning |
|---|---|---|
| `name` | string | The dataset on the Hugging Face hub |
| `revision` | string | A full commit hash of the dataset |
| `parts[].name` | string | The name of the part; unique |
| `parts[].role` | string | `corpus` for exactly one part, `questions` for the others |
| `parts[].path` | string | The path of the file inside the dataset |
| `parts[].rows` | integer | The number of rows the part has at this revision |

## `manifest.json`: a data directory

In the data directory, next to the part files. `dataset fetch` writes it for the default data directory (FR-002, FR-003); the testing agent writes it for an example dataset. Written once for a given data directory, except that a fetch which replaces a missing or changed file writes it again.

```json
{
  "name": "example",
  "revision": null,
  "fetched_at": null,
  "parts": [
    {"name": "ex", "role": "corpus", "path": "ex.jsonl", "rows": 5, "bytes": 1840, "sha256": "…"},
    {"name": "exq", "role": "questions", "path": "exq.jsonl", "rows": 3, "bytes": 612, "sha256": "…"}
  ]
}
```

| Field | Type | Meaning |
|---|---|---|
| `name` | string | The dataset name: `Wix/WixQA`, or a name of the example |
| `revision` | string or `null` | The commit hash the files were fetched at; `null` for a dataset that is not published |
| `fetched_at` | string or `null` | The time the fetch finished; `null` for a dataset that was not fetched |
| `parts[]` | | As in `dataset.json`, with two more fields |
| `parts[].bytes` | integer | The size of the file |
| `parts[].sha256` | string | The fingerprint of the file |

## `build.json`: a build record

Written once by `index build` (FR-010), at `evals/indexes/<index>/build.json` for a build from the pinned dataset and at `data/indexes/<index>/build.json` otherwise. The same document is stored in the `build` table of the index.

```json
{
  "index": "example",
  "dataset": {
    "name": "example",
    "revision": null,
    "corpus_sha256": "…"
  },
  "embedding": {
    "provider": "openai",
    "model_requested": "text-embedding-3-small",
    "model_reported": "text-embedding-3-small",
    "dimensions": 1536
  },
  "splitting": {
    "rule": "line-pack-v1",
    "max_chars": 2000
  },
  "articles": 5,
  "passages": 5,
  "articles_without_passages": [],
  "tokens_embedded": 180,
  "price_usd_per_million_tokens": 0.02,
  "cost_usd": 0.0000036,
  "started_at": "2026-11-24T10:14:00Z",
  "commit": "…",
  "uncommitted_changes": false
}
```

| Field | Type | Meaning |
|---|---|---|
| `index` | string | The index identifier |
| `dataset.name` | string | The dataset name from the manifest |
| `dataset.revision` | string or `null` | The dataset revision from the manifest |
| `dataset.corpus_sha256` | string | The fingerprint of the corpus file the index was built from |
| `embedding.provider` | string | `openai` |
| `embedding.model_requested` | string | The model name sent to the provider |
| `embedding.model_reported` | string | The model name in the provider's responses: the most specific identifier the provider offers |
| `embedding.dimensions` | integer | The size of a vector |
| `splitting.rule` | string | The name of the splitting rule |
| `splitting.*` | | Every parameter of the rule; for `line-pack-v1` this is `max_chars` |
| `articles` | integer | The number of rows of the corpus part |
| `passages` | integer | The number of passages in the index |
| `articles_without_passages` | list of strings | The ids of the articles that produced no passage, sorted |
| `tokens_embedded` | integer | The sum of the token counts that the provider reported |
| `price_usd_per_million_tokens` | number | The price used for the cost |
| `cost_usd` | number | `tokens_embedded` × `price_usd_per_million_tokens` ÷ 1,000,000 |
| `started_at` | string | The time the build started |
| `commit` | string | The commit of the code that built the index, as a full hash |
| `uncommitted_changes` | boolean | `true` when the working tree differed from that commit |

## Audit result

Written by `index audit` when the audit ran to the end (FR-015): to the file given with `--json`, otherwise to `data/audits/<index>/<time>.json`, where `<time>` has the form `20261124T101500Z`.

```json
{
  "index": "example",
  "dataset": {"name": "example", "revision": null},
  "question_set": {
    "description": "every question of the question parts",
    "parts": ["exq"],
    "questions": 3
  },
  "articles_in_corpus": 6,
  "articles_in_index": 5,
  "missing_from_index": ["ex-006"],
  "not_in_corpus": [],
  "unknown_references": [],
  "questions_without_article_ids": 0,
  "outcome": "failed",
  "audited_at": "2026-11-24T10:15:00Z"
}
```

| Field | Type | Meaning |
|---|---|---|
| `index` | string | The index identifier |
| `dataset.name`, `dataset.revision` | string; string or `null` | The dataset the index was audited against |
| `question_set.description` | string | Which questions were checked |
| `question_set.parts` | list of strings | The question parts they come from; empty when the caller passed its own question set |
| `question_set.questions` | integer | The number of questions checked |
| `articles_in_corpus` | integer | The number of distinct article ids in the corpus part |
| `articles_in_index` | integer | The number of distinct article ids in the index |
| `missing_from_index` | list of strings | Ids in the corpus and not in the index, in full, sorted |
| `not_in_corpus` | list of strings | Ids in the index and not in the corpus, in full, sorted |
| `unknown_references` | list of objects | Each object has `question` and `article_id`: a question that names an article which is not in the index. In full, sorted |
| `questions_without_article_ids` | integer | The number of questions with an empty `article_ids` list |
| `outcome` | string | `passed` or `failed` |
| `audited_at` | string | The time of the audit |

**Added on 2026-11-27 by spec 2** (`specs/002-evaluation-harness`, FR-008): an audit that names a question set (`index audit --set V`) writes three more fields inside `question_set`, after `questions`. An audit that names none writes the document above, unchanged, and a document without the three fields is read as one of an audit that named no set.

```json
"question_set": {
  "description": "question set golden-001 (golden)",
  "parts": ["wixqa_expertwritten", "wixqa_simulated"],
  "questions": 200,
  "version": "golden-001",
  "role": "golden",
  "fingerprint": "…"
}
```

| Field | Type | Meaning |
|---|---|---|
| `question_set.description` | string | `question set <version> (<role>)` |
| `question_set.parts` | list of strings | The parts the set takes questions from |
| `question_set.version` | string | The version of the question set |
| `question_set.role` | string | `golden` or `held-out` |
| `question_set.fingerprint` | string | The SHA-256 of the set's record |

An audit that is not carried out writes no file; its exit code is 2 (see [cli.md](cli.md)).

## `snapshot.json`: where the dump of an index is kept

At `evals/indexes/<index>/snapshot.json`, in version control. Written once by the acceptance workflow after the build and the audit of an index from the pinned dataset. No command of the application reads it.

```json
{
  "index": "wixqa-001",
  "file": "wixqa-001.dump",
  "bytes": 0,
  "sha256": "…",
  "format": "pg_dump custom format, schema idx_wixqa_001",
  "postgresql": "…",
  "pgvector": "…",
  "repository": "s-nahornyi-tech/WixQA-RAG",
  "release_tag": "index-wixqa-001",
  "created_at": "…",
  "workflow_run": 0
}
```

| Field | Type | Meaning |
|---|---|---|
| `index` | string | The index identifier |
| `file` | string | The name of the dump file, an asset of the release |
| `bytes` | integer | The size of the dump file |
| `sha256` | string | The fingerprint of the dump file; a job compares it before it restores the dump |
| `format` | string | How the dump was made |
| `postgresql`, `pgvector` | string | The versions of the server and of the extension that made the dump |
| `repository` | string | The GitHub repository whose release holds the dump, so that a copy of the repository still finds it |
| `release_tag` | string | The tag of the GitHub release that holds the dump |
| `created_at` | string | The time the dump was made |
| `workflow_run` | integer | The identifier of the workflow run that built the index |
