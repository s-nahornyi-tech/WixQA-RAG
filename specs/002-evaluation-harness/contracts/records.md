# Contract: records

**Feature**: `002-evaluation-harness` | **Date**: 2026-11-27 | **Plan**: [../plan.md](../plan.md)

The JSON files that the commands of this feature read and write: the question-set record and the three files of a run record. The constitution leaves to this feature "the file names, the field names, the form of a run id and the form of a question identifier"; they are fixed here and in [../data-model.md](../data-model.md).

Every file is UTF-8 text. Times are in UTC in the form `2026-11-01T10:00:00Z`. A SHA-256 is written as 64 lower-case hexadecimal characters. The values in the examples are illustrations with a known answer, not results. A text in angle brackets, such as `<the SHA-256 of …>`, stands for the value it describes.

A later spec may add fields to a record or files to a run's directory; it does not rename or remove one without amending this contract.

## Question-set record

`<sets directory>/<version>.json`: `evals/golden/<version>.json` for a set of the pinned dataset. Written once by `set build` (FR-003 to FR-005) and read by `set check`, by `index audit --set` and by the three `run` commands.

**The canonical form**, which `set build` writes: one JSON document; the keys in the order of the tables below; an indentation of two spaces; the separators `, ` and `: ` as `json.dumps(document, indent=2, ensure_ascii=False)` of Python writes them; non-ASCII characters written as they are; one line feed after the closing brace. The example records under `tests/data/sets/` are written in this form.

**The fingerprint** of a question set is the SHA-256 of the bytes of this file.

A set whose rule draws, `tests/data/sets/harness-half.json`:

```json
{
  "version": "harness-half",
  "role": "golden",
  "dataset": {
    "name": "harness",
    "revision": null,
    "parts": [
      {
        "name": "hxa",
        "rows": 5,
        "sha256": "<the SHA-256 of tests/data/harness/hxa.jsonl>"
      },
      {
        "name": "hxb",
        "rows": 3,
        "sha256": "<the SHA-256 of tests/data/harness/hxb.jsonl>"
      }
    ]
  },
  "rule": {
    "kind": "draw",
    "method": "sha256-order-v1",
    "seed": 7,
    "take": [
      {
        "part": "hxa",
        "questions": 3
      },
      {
        "part": "hxb",
        "questions": 1
      }
    ]
  },
  "questions": [
    {
      "id": "hxa-002",
      "article_ids": [
        "hx-002"
      ]
    },
    {
      "id": "hxa-003",
      "article_ids": [
        "hx-001",
        "hx-003"
      ]
    },
    {
      "id": "hxa-005",
      "article_ids": [
        "hx-005"
      ]
    },
    {
      "id": "hxb-002",
      "article_ids": [
        "hx-006"
      ]
    }
  ],
  "count": 4
}
```

A set whose rule is a complement, `tests/data/sets/harness-half-rest.json`:

```json
{
  "version": "harness-half-rest",
  "role": "held-out",
  "dataset": {
    "name": "harness",
    "revision": null,
    "parts": [
      {
        "name": "hxa",
        "rows": 5,
        "sha256": "<the SHA-256 of tests/data/harness/hxa.jsonl>"
      },
      {
        "name": "hxb",
        "rows": 3,
        "sha256": "<the SHA-256 of tests/data/harness/hxb.jsonl>"
      }
    ]
  },
  "rule": {
    "kind": "complement",
    "of": "harness-half",
    "of_fingerprint": "<the SHA-256 of tests/data/sets/harness-half.json>"
  },
  "questions": [
    {
      "id": "hxa-001",
      "article_ids": [
        "hx-001"
      ]
    },
    {
      "id": "hxa-004",
      "article_ids": [
        "hx-002",
        "hx-003",
        "hx-004"
      ]
    },
    {
      "id": "hxb-001",
      "article_ids": [
        "hx-004",
        "hx-005"
      ]
    },
    {
      "id": "hxb-003",
      "article_ids": [
        "hx-001",
        "hx-006"
      ]
    }
  ],
  "count": 4
}
```

| Field | Type | Meaning |
|---|---|---|
| `version` | string | The version; equal to the name of the file without `.json` |
| `role` | string | `golden` or `held-out` |
| `dataset.name` | string | The dataset name from the manifest of the data directory |
| `dataset.revision` | string or `null` | The dataset revision from the manifest |
| `dataset.parts[]` | list of objects | The parts the set takes questions from, in the order of the rule; for a complement, those of the complemented set |
| `dataset.parts[].name` | string | The name of the part |
| `dataset.parts[].rows` | integer | Its row count, from the manifest |
| `dataset.parts[].sha256` | string | Its fingerprint, from the manifest |
| `rule.kind` | string | `draw` or `complement` |
| `rule.method` | string | Draw only: `sha256-order-v1` |
| `rule.seed` | integer | Draw only: the seed, 0 or greater |
| `rule.take[]` | list of objects | Draw only: `part` and `questions`, the number drawn from that part |
| `rule.of` | string | Complement only: the version of the complemented set |
| `rule.of_fingerprint` | string | Complement only: the fingerprint of the complemented set's record |
| `questions[]` | list of objects | The questions, parts in the order of the rule, rows ascending |
| `questions[].id` | string | The question identifier |
| `questions[].article_ids` | list of strings | The gold article ids, exactly as the row of the dataset gives them: same order, repeats kept |
| `count` | integer | The number of questions |

## Run record

The directory `<runs directory>/<run id>/`: `evals/runs/<run id>/` for a run of the study. It holds three files, each written once. Spec 3 writes them; this feature reads and checks them. The rules that hold for the fields are in [../data-model.md](../data-model.md), "Run record"; the tables here give names and types.

### `run.json`: identity and config

One JSON document. `tests/data/runs/20261101T100000Z-example-a/run.json`:

```json
{
  "run_id": "20261101T100000Z-example-a",
  "started_at": "2026-11-01T10:00:00Z",
  "commit": "0123456789abcdef0123456789abcdef01234567",
  "uncommitted_changes": false,
  "config": {
    "dataset": {
      "name": "harness",
      "revision": null
    },
    "question_set": {
      "version": "harness",
      "role": "golden",
      "fingerprint": "<the SHA-256 of tests/data/sets/harness.json>"
    },
    "index": "harness",
    "models": {
      "generation": "example-model"
    },
    "prompts": {
      "generation": "Answer from the context only."
    },
    "retrieval": {
      "top_k": 3
    },
    "reranking": {
      "enabled": false
    },
    "context": {
      "max_articles": 2
    },
    "limits": {
      "timeout_seconds": 20,
      "max_calls": 4
    },
    "seeds": {},
    "concurrency": 1,
    "prices": [
      {
        "model": "example-model",
        "usd_per_million_input_tokens": 1.0,
        "usd_per_million_output_tokens": 2.0
      }
    ],
    "experiment": null
  }
}
```

| Field | Type | Meaning |
|---|---|---|
| `run_id` | string | The run identifier; the name of the directory |
| `started_at` | string | The start of the run |
| `commit` | string | The commit of the code that produced the run, as a full hash |
| `uncommitted_changes` | boolean | `true` when the working tree differed from that commit |
| `config.dataset.name`, `config.dataset.revision` | string; string or `null` | The dataset of the run |
| `config.question_set.version` | string | The question set of the run |
| `config.question_set.role` | string | `golden` or `held-out`, as the set's record says |
| `config.question_set.fingerprint` | string | The fingerprint of the set's record |
| `config.index` | string | The index used |
| `config.models` | object | What each model is used for → its identifier |
| `config.prompts`, `config.retrieval`, `config.reranking`, `config.context`, `config.seeds` | object | Fixed by spec 3. The keys in the example are illustrations |
| `config.limits.timeout_seconds` | number | The time limit for one question |
| `config.limits.max_calls` | integer | The limit on model or tool calls for one question |
| `config.concurrency` | integer | How many questions are worked on at a time |
| `config.prices[]` | list of objects | `model`, `usd_per_million_input_tokens`, `usd_per_million_output_tokens` |
| `config.experiment` | object or `null` | `null`, or the four fields below |
| `config.experiment.baseline` | string | The run identifier of the baseline run |
| `config.experiment.parameter` | string | The one parameter that differs, as a dotted path inside `config`, for example `reranking.enabled` |
| `config.experiment.baseline_value` | any JSON value | The value of that parameter in the baseline's config; `null` when the baseline does not have it |
| `config.experiment.value` | any JSON value | Its value in this run's config |

The `config.experiment` of `tests/data/runs/20261102T100000Z-example-b/run.json`:

```json
"experiment": {
  "baseline": "20261101T100000Z-example-a",
  "parameter": "reranking.enabled",
  "baseline_value": false,
  "value": true
}
```

### `results.jsonl`: one entry per question

JSON Lines: one JSON object per line, one line per question of the run's question set, in the order of the set, each line ended by a line feed. The entry of `hxa-001` in `example-a`, shown on several lines for reading:

```json
{
  "question_id": "hxa-001",
  "status": "answered",
  "retrieved_list": ["hx-001", "hx-002", "hx-003"],
  "generation_list": ["hx-001", "hx-002"],
  "context": "<the exact text passed to the generator>",
  "answer": "<the answer>",
  "answer_sha256": "<the SHA-256 of the UTF-8 bytes of the answer>",
  "tokens": [{"model": "example-model", "input_tokens": 1000, "output_tokens": 100}],
  "cost_usd": 0.0012,
  "latency_seconds": 1.0
}
```

The entry of `hxa-005`, which failed before anything was retrieved:

```json
{
  "question_id": "hxa-005",
  "status": "error",
  "retrieved_list": null,
  "generation_list": null,
  "context": null,
  "answer": null,
  "answer_sha256": null,
  "tokens": [],
  "cost_usd": 0.0,
  "latency_seconds": 5.0
}
```

| Field | Type | Meaning |
|---|---|---|
| `question_id` | string | The question identifier |
| `status` | string | `answered`, `no_answer`, `error`, `timeout` or `call_limit` |
| `retrieved_list` | list of strings, or `null` | The list before reranking as ordered article ids; `null` when it was not produced; `[]` when it was produced and is empty |
| `generation_list` | list of strings, or `null` | The list passed to generation, in the same form |
| `context` | string or `null` | The exact text passed to the generator |
| `answer` | string or `null` | The answer |
| `answer_sha256` | string or `null` | The SHA-256 of the UTF-8 bytes of `answer` |
| `tokens[]` | list of objects | `model`, `input_tokens`, `output_tokens`: the token counts of this question, summed per model |
| `cost_usd` | number | The cost of answering this question |
| `latency_seconds` | number | Wall-clock seconds from receiving the question to returning an answer or failing |

### `summary.json`: the audit result and the numbers

One JSON document, written with `json.dumps(document, indent=2, ensure_ascii=False)` and a line feed at the end. Its content, apart from `audit`, is what `runs.summary_document` returns ([harness.md](harness.md)). `tests/data/runs/20261101T100000Z-example-a/summary.json`:

```json
{
  "run_id": "20261101T100000Z-example-a",
  "question_set": {
    "version": "harness",
    "role": "golden",
    "fingerprint": "<the SHA-256 of tests/data/sets/harness.json>"
  },
  "questions": 8,
  "audit": {
    "index": "harness",
    "dataset": {
      "name": "harness",
      "revision": null
    },
    "question_set": {
      "description": "question set harness (golden)",
      "parts": [
        "hxa",
        "hxb"
      ],
      "questions": 8,
      "version": "harness",
      "role": "golden",
      "fingerprint": "<the SHA-256 of tests/data/sets/harness.json>"
    },
    "articles_in_corpus": 6,
    "articles_in_index": 6,
    "missing_from_index": [],
    "not_in_corpus": [],
    "unknown_references": [],
    "questions_without_article_ids": 0,
    "outcome": "passed",
    "audited_at": "2026-11-01T09:59:00Z"
  },
  "breakdowns": {
    "all": {
      "questions": 8,
      "status": {
        "answered": 4,
        "no_answer": 1,
        "error": 1,
        "timeout": 1,
        "call_limit": 1
      },
      "generation_list": {
        "questions": 6,
        "mean_share_found": 0.5277777777777778,
        "all_found": 2,
        "share_all_found": 0.3333333333333333
      },
      "retrieved_list": {
        "questions": 7,
        "mean_share_found": 0.7857142857142857,
        "all_found": 5,
        "share_all_found": 0.7142857142857143
      },
      "cost_usd": {
        "total": 0.0128,
        "per_question": 0.0016
      },
      "latency_seconds": {
        "median": 4.5,
        "p95": 30.0
      }
    },
    "single_article": {
      "questions": 4,
      "status": {
        "answered": 2,
        "no_answer": 0,
        "error": 1,
        "timeout": 0,
        "call_limit": 1
      },
      "generation_list": {
        "questions": 3,
        "mean_share_found": 0.3333333333333333,
        "all_found": 1,
        "share_all_found": 0.3333333333333333
      },
      "retrieved_list": {
        "questions": 3,
        "mean_share_found": 0.6666666666666666,
        "all_found": 2,
        "share_all_found": 0.6666666666666666
      },
      "cost_usd": {
        "total": 0.006,
        "per_question": 0.0015
      },
      "latency_seconds": {
        "median": 3.5,
        "p95": 7.0
      }
    },
    "multi_article": {
      "questions": 4,
      "status": {
        "answered": 2,
        "no_answer": 1,
        "error": 0,
        "timeout": 1,
        "call_limit": 0
      },
      "generation_list": {
        "questions": 3,
        "mean_share_found": 0.7222222222222222,
        "all_found": 1,
        "share_all_found": 0.3333333333333333
      },
      "retrieved_list": {
        "questions": 4,
        "mean_share_found": 0.875,
        "all_found": 3,
        "share_all_found": 0.75
      },
      "cost_usd": {
        "total": 0.0068,
        "per_question": 0.0017
      },
      "latency_seconds": {
        "median": 6.0,
        "p95": 30.0
      }
    }
  },
  "retrieval_misses": [
    "hxa-002",
    "hxa-003",
    "hxa-004",
    "hxb-002"
  ],
  "questions_without_gold_articles": 0
}
```

| Field | Type | Meaning |
|---|---|---|
| `run_id` | string | The run |
| `question_set` | object | `version`, `role`, `fingerprint`, as in `run.json` |
| `questions` | integer | The size of the question set |
| `audit` | object | The audit result of the index, in the form of spec 1's contracts/records.md, "Audit result", with the three fields `question_set.version`, `question_set.role` and `question_set.fingerprint` that an audit with `--set` writes |
| `breakdowns.all`, `breakdowns.single_article`, `breakdowns.multi_article` | object | The numbers for all questions, for single-article and for multi-article questions |
| `breakdowns.*.questions` | integer | The questions of the breakdown |
| `breakdowns.*.status` | object | The count of each status, with the five keys in the order `answered`, `no_answer`, `error`, `timeout`, `call_limit` |
| `breakdowns.*.generation_list`, `breakdowns.*.retrieved_list` | object | `questions`, `mean_share_found`, `all_found`, `share_all_found` |
| `breakdowns.*.cost_usd` | object | `total` and `per_question`, the cost of answering in US dollars |
| `breakdowns.*.latency_seconds` | object | `median` and `p95` |
| `retrieval_misses` | list of strings | Question identifiers, in the order of the set |
| `questions_without_gold_articles` | integer | Questions of the set without a gold article |

A number over no question is `null`, except a total cost, which is `0.0` (data-model.md, "Summary").

The summary holds no number of the judge. Spec 4 adds those, and the cost of judging, in files of its own in the same directory.
