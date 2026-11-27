# Contract: the harness as Python modules

**Feature**: `002-evaluation-harness` | **Date**: 2026-11-27 | **Plan**: [../plan.md](../plan.md)

FR-017 requires one computation of the numbers of a run, used when a run is recorded and when it is checked. This file fixes the Python names of that computation and of what stands around it, for two readers: the testing agent, who writes unit tests before the code exists, and spec 3, whose pipeline calls these functions when it writes a run record.

Only the names in this file are a contract. Everything else in the three modules, and every name that starts with an underscore, may change without notice. "Document" means the parsed JSON of a record of [records.md](records.md): dictionaries, lists, texts, numbers, truth values and `None`.

## `wixqa_rag.questionsets`

The question identifier, the draw, and the record of a question set.

```python
from wixqa_rag import questionsets

questionsets.question_id("hxa", 3)                      # "hxa-003"
questionsets.draw_key(7, "hxa-001")                     # "b007c1a9…b35a"
questionsets.draw(["hxa-001", …, "hxa-005"], 3, 7)      # ["hxa-002", "hxa-003", "hxa-005"]

question_set = questionsets.read("harness", Path("tests/data/sets"))
examination = questionsets.examine("harness-half", Path("tests/data/harness"), Path("tests/data/sets"))
```

| Name | Kind | Meaning |
|---|---|---|
| `DRAW_METHOD` | text | `"sha256-order-v1"` |
| `ROLES` | tuple | `("golden", "held-out")` |
| `question_id(part, row)` | function | The question identifier of a row, counted from 1. `audit.question_reference` of spec 1 stays and returns the same text |
| `is_valid_version(version)` | function | Whether a text has the form of a version |
| `draw_key(seed, identifier)` | function | The draw key, as 64 hexadecimal characters |
| `draw(identifiers, number, seed)` | function | The identifiers that the draw selects, in the order in which they were given. Raises `ValueError` when `number` is below 1 or above the number of identifiers, or when `seed` is below 0 |
| `QuestionSet` | value | One record that was read: `version`, `role`, `dataset_name`, `dataset_revision`, `rule` (the document of the rule), `questions` (a tuple of pairs of a question identifier and a tuple of its gold article ids, in the order of the record), `fingerprint`, and `document` (the whole record) |
| `QuestionSet.pairs()` | method | The questions as pairs of an identifier and its list of article ids: the form that `audit_index` takes as `questions` |
| `QuestionSet.gold(question)` | method | The set of distinct gold article ids of a question |
| `SetError` | exception | A record does not exist or cannot be read as a question-set record. The message names the file |
| `read(version, sets_dir=None)` | function | Reads `<sets_dir>/<version>.json` and returns a `QuestionSet`; without `sets_dir`, from `evals/golden`. It reads the record as it is and does not check it against a dataset. Raises `SetError` |
| `record(version, role, rule, data_dir, sets_dir=None)` | function | The document of the record that `set build` would write for this rule and data directory. It writes nothing |
| `canonical(document)` | function | The bytes of the canonical form of a record |
| `SetExamination` | value | The outcome of the check of one record: `question_set`, `differences` (a list of texts, without the `difference: ` in front), `counts` (a dictionary with the keys of the report: the part names, `questions`, `single-article`, `multi-article`, `questions without gold articles`, `repeated question texts`, and for a complement `in both sets`, `in neither set`, `question texts in both sets`) |
| `examine(version, data_dir=None, sets_dir=None)` | function | The check of `set check` for one record, without printing. The data directory must already have passed the dataset check. Raises `SetError` when the record, or the record it complements, cannot be read |
| `build(version, role, take, seed, complement_of, data_dir=None, sets_dir=None)` | function | The command `set build`: prints the lines and the verdict and returns the exit code. `take` is a list of pairs of a part name and a number, or `None`; `complement_of` is a version or `None` |
| `check(version, data_dir=None, sets_dir=None)` | function | The command `set check`: prints the lines and the verdict and returns the exit code |

## `wixqa_rag.metrics`

The one computation (FR-009 to FR-017, FR-027, FR-028). Every function is pure: it reads no file, no clock and no setting, and it does not change its arguments. An *entry* is the document of one line of `results.jsonl`.

```python
from wixqa_rag import metrics

metrics.share_found({"hx-002", "hx-003", "hx-004"}, ["hx-002", "hx-003", "hx-005"])   # Fraction(2, 3)
metrics.all_found({"hx-002", "hx-003", "hx-004"}, ["hx-002", "hx-003", "hx-005"])     # 0
metrics.share_found({"hx-005"}, None)                                                 # None
metrics.share_found({"hx-006"}, [])                                                   # Fraction(0, 1)
```

| Name | Kind | Meaning |
|---|---|---|
| `STATUSES` | tuple | `("answered", "no_answer", "error", "timeout", "call_limit")` |
| `BREAKDOWNS` | tuple | `("all", "single_article", "multi_article")` |
| `LISTS` | tuple | `("generation_list", "retrieved_list")` |
| `share_found(gold, items)` | function | A `fractions.Fraction`: the gold article ids among the distinct items, divided by the number of gold article ids. `None` when `gold` is empty or `items` is `None` |
| `all_found(gold, items)` | function | `1` or `0`; `None` in the same two cases |
| `kind_of(gold)` | function | `"single_article"`, `"multi_article"`, or `None` for a question without a gold article |
| `entry_cost(tokens, prices)` | function | The cost of one entry as a floating-point number: `tokens` and `prices` as the documents of `tokens` and of `config.prices`. Raises `ValueError` for a model without a price |
| `median(values)` | function | The median of FR-016; `None` for no value |
| `percentile_95(values)` | function | The 95th percentile of FR-016: the value at position ⌈0.95 × *n*⌉ of the sorted values; `None` for no value |
| `summarize(questions, entries, prices)` | function | The numbers of a run. `questions`: the pairs of a question set, in its order. `entries`: the entries of the run, exactly one per question. Returns a dictionary with the keys `breakdowns`, `retrieval_misses` and `questions_without_gold_articles`, exactly as they stand in `summary.json`. Raises `ValueError` when the entries are not one per question |
| `per_question(questions, entries)` | function | For every question, in order, a dictionary with `question_id`, `status`, and for each of the two lists the numbers found and to be found and `all_found`, or `None` for a list that is absent or a question without a gold article: what `run report --per-question` prints |
| `compare(questions, first_entries, second_entries)` | function | The pairwise comparison: a dictionary with `compared` (a number) and `left_out`, `gained` and `lost` (lists of question identifiers in the order of the set) |

Numbers are computed exactly and turned into floating-point numbers once, at the end (research.md, section 7). `summarize` computes the cost of each entry from its `tokens`, not from its `cost_usd`.

## `wixqa_rag.runs`

The run identifier, the record of a run, its check, and the three commands.

```python
from wixqa_rag import runs

runs.run_id(datetime(2026, 12, 1, 9, 30, tzinfo=UTC), "baseline")   # "20261201T093000Z-baseline"

summary = runs.summary_document(run_document, question_set, entries, audit_document)
examination = runs.examine("20261101T100000Z-example-a", Path("tests/data/runs"), Path("tests/data/sets"))
```

| Name | Kind | Meaning |
|---|---|---|
| `RUN_FILE`, `RESULTS_FILE`, `SUMMARY_FILE` | texts | `"run.json"`, `"results.jsonl"`, `"summary.json"` |
| `run_id(started_at, name)` | function | The run identifier for a start time with a time zone and a name. Raises `ValueError` for a name of another form or a time without a time zone |
| `is_valid_run_id(text)` | function | Whether a text has the form of a run identifier |
| `summary_document(run_document, question_set, entries, audit_document)` | function | The whole document of `summary.json`: `run_id`, `question_set` and `questions` from the first two arguments, `audit` as given, and the three keys of `metrics.summarize`. `question_set` is a `QuestionSet`; `audit_document` is the JSON document of an `AuditResult` of spec 1 (`result.to_document()`). **Spec 3 writes exactly this document** |
| `config_differences(first_config, second_config)` | function | The parameters in which two configs differ, as a sorted list of dotted paths; `experiment` is not compared |
| `RunExamination` | value | The outcome of the check of one record: `run_id`, `differences` (a list of texts, without the `difference: ` in front), `question_set` (the `QuestionSet`, or `None` when it could not be read), `role` (the `config.question_set.role` of the record, or `None`), `run_document`, `entries` and `summary` (each `None` when its file could not be read) |
| `RunNotFound` | exception | The run does not exist in the runs directory |
| `examine(run, runs_dir=None, sets_dir=None)` | function | The check of `run check` for one record, without printing. Without `runs_dir`, in `evals/runs`. Raises `RunNotFound` |
| `run_ids(runs_dir=None)` | function | The names of the directories of a registry, sorted |
| `check(run=None, runs_dir=None, sets_dir=None)` | function | The command `run check`, for one run or, with `run=None`, for the registry: prints the lines and the verdict and returns the exit code |
| `report(run, per_question=False, runs_dir=None, sets_dir=None)` | function | The command `run report` |
| `compare(first, second, runs_dir=None, sets_dir=None)` | function | The command `run compare` |

## `wixqa_rag.settings`: additions

| Name | Kind | Meaning |
|---|---|---|
| `SETS_DIR` | path | `Path("evals", "golden")`: the default sets directory |
| `RUNS_DIR` | path | `Path("evals", "runs")`: the default runs directory |

## `wixqa_rag.cli`: additions

The groups `set` and `run` are added in `build_parser` with the existing helpers. Each command is carried out through `carry_out`, as the four commands of spec 1 are, so an error that a command does not expect ends as `not carried out` with exit code 2.

## `wixqa_rag.audit`: additions

Fixed in spec 1's [contracts/audit-gate.md](../../001-corpus-and-audit/contracts/audit-gate.md), which is edited for this feature: `audit_index` and `require_passed_audit` take the keyword arguments `question_set` and `sets_dir`, and `command` takes them as its fourth and fifth argument.

## How spec 3 records a run with these names

A sketch of the order, to show that nothing is missing; spec 3 fixes the pipeline and the writing of the files.

1. `question_set = questionsets.read("golden-001")`.
2. `result = audit.require_passed_audit("wixqa-001", question_set="golden-001")`: the gate of Principle I. A run that receives `AuditNotPassed` stops here.
3. The run identifier: `runs.run_id(started_at, name)`. `run.json` is written with the identity and the config.
4. For each question of `question_set.questions`, in order, the pipeline produces one entry; `metrics.entry_cost` gives its `cost_usd`. The entries are written to `results.jsonl`.
5. `runs.summary_document(run_document, question_set, entries, result.to_document())` gives the document of `summary.json`.
6. `runs.examine(run_id)` has no difference for the record just written; the command `run check --run <run id>` says the same.

## Rules

1. `metrics` imports nothing of the project. `questionsets` imports `dataset`, `settings` and `cli`. `runs` imports `questionsets`, `metrics`, `settings` and `cli`. `audit` imports `questionsets` for the new argument. Neither `metrics` nor `runs` imports `store`, `embedding` or `audit`, so the three `run` commands cannot reach the store or a provider (FR-031).
2. No function of this file changes a file that exists. `questionsets.build` is the only one that writes, and it writes one new file.
3. A function named as "the command" prints result lines and a verdict and returns an exit code; every other function prints nothing.
