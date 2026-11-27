# Data Model: Evaluation harness

**Feature**: `002-evaluation-harness` | **Date**: 2026-11-27 | **Plan**: [plan.md](plan.md)

The entities of the spec: their fields, the rules that hold for them, and where each one is stored. The exact shape of every JSON file is in [contracts/records.md](contracts/records.md); the reasons behind the choices are in [research.md](research.md). The last section gives the example data of the spec's acceptance checks in full, so that it can be copied.

## Overview

```text
data directory ──────────────┐
(part files + manifest.json) │ set build (rule, seed)
                             ▼
                     question-set record ──set check──▶ passed / failed / not carried out
                     <sets directory>/<version>.json
                       │            │
   index audit --set ◀─┘            │ version, role, fingerprint, gold article ids
   (spec 1's audit, with            ▼
    the set as question set)   run record  <runs directory>/<run id>/
                                 run.json        identity and config
                                 results.jsonl   one entry per question
                                 summary.json    audit result and numbers
                                    │
                 ┌──────────────────┼──────────────────┐
                 ▼                  ▼                  ▼
            run check          run report         run compare
       passed / failed /     the numbers of      gained and lost,
       not carried out       one run             two runs on one set
```

Writing a run record is the task of spec 3. This feature fixes the record, computes its summary and checks it.

## Question identifier

The name of one question (FR-002). It is the question reference of spec 1 under its final name.

- **Form**: the name of the part, a hyphen, and the row number of the question in that part, counted from 1 in file order and written with at least three digits: `wixqa_expertwritten-017`, `wixqa_synthetic-6221`, `hxa-003`.
- **Rule**: an identifier is valid together with the dataset revision at which it was made. A question-set record states that revision and the fingerprint of every part it takes questions from.

## Version of a question set

Lower-case letters, digits and single hyphens; it starts and ends with a letter or a digit; at most 40 characters. This is the form of an index identifier of spec 1. A command given any other version is not carried out.

## Question set

A fixed list of questions with a version and a role (FR-001, FR-003).

- **Stored in**: `<sets directory>/<version>.json`. The default sets directory is `evals/golden/`, in version control; it takes only sets of the pinned dataset. Example sets are in `tests/data/sets/`; a set built by an acceptance check from example data goes to `data/sets/`, outside version control.
- **Fields**: `version`; `role`, `golden` or `held-out`; `dataset`, with the name and the revision of the dataset and, for every part that the set takes questions from, its name, its row count and its SHA-256; `rule` (see "Selection rule"); `questions`, the list of entries, each with the question identifier `id` and the gold article ids `article_ids` exactly as the dataset gives them; `count`, the number of questions.
- **Order of `questions`**: the parts in the order of the rule, and within a part by ascending row number.
- **Fingerprint**: the SHA-256 of the bytes of the file.

**Rules**:

1. A record is produced by `set build` and never typed by hand (FR-004). The example records under `tests/data/sets/` are the one exception: they are test data, written before the command exists.
2. A record is written once (FR-005). `set build` over an existing version writes nothing; it reports the version as already written when the record it would write has the same bytes, and is refused otherwise.
3. The record holds nothing that changes from one production to the next: no time, no commit, no path of a machine.
4. `count` is the length of `questions`. No identifier occurs twice.
5. A set with no question is not produced.

The three sets of the study (FR-001):

| Version | Role | Rule | Questions |
|---|---|---|---|
| `golden-001` | `golden` | draw 100 of `wixqa_expertwritten` and 100 of `wixqa_simulated`, seed `20261127` | 200 |
| `held-out-001` | `held-out` | complement of `golden-001` | 200 |
| `synthetic-001` | `held-out` | draw 300 of `wixqa_synthetic`, seed `20261127` | 300 |

## Selection rule

How the questions of a set are taken from the dataset. There are two kinds.

**`draw`**: a number of questions from each of one or more parts, selected by the method `sha256-order-v1` with a seed (research.md, section 2).

| Field | Type | Rule |
|---|---|---|
| `kind` | string | `draw` |
| `method` | string | `sha256-order-v1` |
| `seed` | integer | Zero or greater |
| `take` | list of objects | In the order given on the command line. Each has `part`, the name of a part with the role `questions`, and `questions`, a whole number from 1 to the row count of the part. No part occurs twice |

**`complement`**: every question, of the parts that another set draws from, which that set does not hold (FR-032).

| Field | Type | Rule |
|---|---|---|
| `kind` | string | `complement` |
| `of` | string | The version of the complemented set, in the same sets directory. Its rule has the kind `draw` |
| `of_fingerprint` | string | The fingerprint of the complemented set's record |

The `dataset.parts` of a complement are those of the complemented set, in the same order.

**The draw key** of a question identifier with a seed is the SHA-256, as 64 lower-case hexadecimal characters, of the UTF-8 bytes of `sha256-order-v1:<seed>:<identifier>`. The draw of *N* questions from a part selects the *N* identifiers with the smallest keys; equal keys are ordered by identifier.

## Check of a question set

`set check` examines one record against one data directory and, for a complement, against the record it complements (FR-006, FR-007, FR-032). It reports a *difference* for each of the following and passes when there is none.

| # | Difference | Compared with |
|---|---|---|
| 1 | The dataset name or the revision of the record differs from the manifest of the data directory | the manifest |
| 2 | A part of the record is not a question part of the data directory, or its row count or its SHA-256 differs | the manifest |
| 3 | A question that the rule selects is not in the record | the rule applied again, with the recorded seed |
| 4 | A question in the record is not selected by the rule | the same |
| 5 | The gold article ids of a question differ from the dataset | the row of the question |
| 6 | The number of questions of a part, or `count`, differs from the rule | the rule |
| 7 | An identifier occurs twice, or the order of `questions` is not the order of the dataset | |
| 8 | The method of a draw is not `sha256-order-v1`; a `take` names a part twice or asks for more questions than the part has | |
| 9 | Complement only: `of_fingerprint` is not the fingerprint of the complemented record | the record `of` |
| 10 | Complement only: a question is in both sets | the record `of` |
| 11 | Complement only: a question of the parts is in neither set | the record `of` and the dataset |

For a complement, differences 3 and 4 are stated as differences 11 and 10: the rule selects exactly the questions that the complemented set does not hold.

The check is *not carried out*, and never reported as passed or failed, when the data directory does not pass the dataset check, when the record does not exist or cannot be read as a question-set record, or, for a complement, when the complemented record does not exist or does not itself pass this check.

The check also *reports*, without failing for them:

| Number | Definition |
|---|---|
| single-article | Questions with exactly one distinct gold article id |
| multi-article | Questions with two or more distinct gold article ids |
| questions without gold articles | Questions whose `article_ids` list is empty |
| repeated question texts | Distinct values of the field `question` that occur in two or more questions of the set. Texts are compared as they are, without changing case or spaces |
| question texts in both sets | Complement only: distinct question texts that occur in the set and in the complemented set |
| in both sets, in neither set | Complement only: the numbers of differences 10 and 11 |

## Role

`golden` or `held-out`. It says what a set may be used for (constitution, Principle III).

| What | Golden set | Held-out set |
|---|---|---|
| A run on it | every run of the study | rarely: at the baseline and at milestones the owner names |
| An experiment run on it | yes | no: the check of the run record fails (FR-035) |
| A comparison of two runs on it | yes | yes, with the statement of FR-036 |
| Counted by the check of the registry | `runs on golden sets` | `runs on held-out sets` |

## Run identifier

The name of a run (FR-018): the start time in UTC to the second, in the form `20261201T093000Z`, a hyphen, and a name of lower-case letters, digits and single hyphens that starts and ends with a letter or a digit and has at most 40 characters. Example: `20261201T093000Z-baseline`.

- The time part is the `started_at` of the run, to the second.
- An identifier is checked by its form only: eight digits, `T`, six digits, `Z`, a hyphen and the name. Whether the digits name a day and a time that exist is not checked. `started_at` is checked by its form in the same way, and the two are compared as texts.
- The directory of a run in the registry is named by its identifier, so an identifier cannot occur twice in a registry. It is never reused.

## Run record

The identity, the config, the results and the summary of one run (FR-019 to FR-021), in three files in `<runs directory>/<run id>/`. The default runs directory is `evals/runs/`. Each file is written once.

### Identity and config: `run.json`

| Field | Type | Rule |
|---|---|---|
| `run_id` | string | A run identifier; equal to the name of the directory |
| `started_at` | string | UTC, `2026-11-01T10:00:00Z`; agrees with the time part of `run_id` |
| `commit` | string | The commit of the code, 40 lower-case hexadecimal characters |
| `uncommitted_changes` | boolean | `true` when the working tree differed from that commit |
| `config` | object | See below |

The config holds everything needed to repeat the run (constitution, "Run Record Format").

| Field of `config` | Type | Fixed by this feature |
|---|---|---|
| `dataset` | object | `name` (string) and `revision` (string, or `null` for a dataset that is not published) |
| `question_set` | object | `version`, `role` and `fingerprint` of the question set of the run |
| `index` | string | The identifier of the index used |
| `models` | object | Each value is the identifier of a model, as specific as its provider offers. The keys name what the model is used for; spec 3 fixes them |
| `prompts` | object | Fixed by spec 3 |
| `retrieval` | object | Fixed by spec 3 |
| `reranking` | object | Fixed by spec 3 |
| `context` | object | The context size and what belongs to it; fixed by spec 3 |
| `limits` | object | `timeout_seconds` (number above 0) and `max_calls` (whole number of at least 1): the limits behind the statuses `timeout` and `call_limit` |
| `seeds` | object | Fixed by spec 3; may be empty |
| `concurrency` | integer | At least 1 |
| `prices` | list of objects | One per model that is charged: `model`, `usd_per_million_input_tokens`, `usd_per_million_output_tokens`. No model occurs twice |
| `experiment` | object or `null` | `null` for a run that is not an experiment. Otherwise `baseline` (a run identifier), `parameter` (a dotted path), `baseline_value` and `value` |

All thirteen fields are required. For the six that spec 3 fixes, this feature requires only that they are JSON objects.

**A parameter** of a config is a leaf, named by the path of keys to it joined with dots: `retrieval.top_k`. Objects are descended into; every other value, a list included, is a leaf. `config.experiment` is not part of the comparison (research.md, section 9).

### Results: `results.jsonl`

One line per question of the run's question set, in the order of the set.

| Field | Type | Rule |
|---|---|---|
| `question_id` | string | A question of the run's question set; each exactly once, and no other |
| `status` | string | `answered`, `no_answer`, `error`, `timeout` or `call_limit` |
| `retrieved_list` | list of strings, or `null` | The list before reranking, as article ids, one per item, in order, repeats kept. `null` when the list was not produced. An empty list is a list |
| `generation_list` | list of strings, or `null` | The list passed to generation, exactly as passed, in the same form |
| `context` | string or `null` | The exact text passed to the generator; `null` when nothing was passed |
| `answer` | string or `null` | The answer; for `no_answer`, the pipeline's statement that it cannot answer |
| `answer_sha256` | string or `null` | The SHA-256 of the UTF-8 bytes of `answer`; `null` exactly when `answer` is `null` |
| `tokens` | list of objects | One per model that was called for this question: `model`, `input_tokens`, `output_tokens`, whole numbers of 0 or more. Empty when no model was called. Every `model` is in `config.prices`, and none occurs twice |
| `cost_usd` | number | The sum over `tokens` of `input_tokens` × the model's input price ÷ 1,000,000 plus `output_tokens` × the model's output price ÷ 1,000,000 |
| `latency_seconds` | number | 0 or more |

Rules across fields:

1. A question with the status `answered` or `no_answer` has both lists and an `answer` (FR-020).
2. A question with a `generation_list` has a `retrieved_list`.
3. An article id in a list is a non-empty string. The check does not ask whether the article exists: the audit result in the summary is what ties the run to an index.
4. An entry may hold further fields; the check ignores them. The ten fields above are required: a field that is absent is a defect, and `null` is allowed only where the table says so.

### Summary: `summary.json`

Derived from the two other files and from the question-set record (FR-021); recomputing it gives the same numbers (research.md, section 7).

| Field | Type | Meaning |
|---|---|---|
| `run_id` | string | The run |
| `question_set` | object | `version`, `role` and `fingerprint`, as in the config |
| `questions` | integer | The number of questions of the set |
| `audit` | object | The audit result of spec 1, as its JSON document, made with `--set` for the run's question set; its outcome is `passed` |
| `breakdowns` | object | `all`, `single_article` and `multi_article`; see below |
| `retrieval_misses` | list of strings | The questions whose generation list exists and has `all_found` = 0, in the order of the set |
| `questions_without_gold_articles` | integer | Questions of the set with an empty `article_ids` list |

One breakdown:

| Field | Type | Meaning |
|---|---|---|
| `questions` | integer | The questions of the breakdown |
| `status` | object | The count of each of the five statuses; the counts add up to `questions` |
| `generation_list` | object | `questions`, `mean_share_found`, `all_found`, `share_all_found` (below) |
| `retrieved_list` | object | The same four numbers for the retrieved list |
| `cost_usd` | object | `total`, and `per_question` = total ÷ `questions` |
| `latency_seconds` | object | `median` and `p95` over the questions of the breakdown |

The four numbers of a list in a breakdown, over the questions of the breakdown that have a gold article and for which the list exists:

| Field | Definition |
|---|---|
| `questions` | Their number |
| `mean_share_found` | The mean of `share_found` |
| `all_found` | The number with `all_found` = 1 |
| `share_all_found` | `all_found` ÷ `questions` |

A number whose denominator is 0 is `null`: a mean or a share over no question, a cost per question and a latency of a breakdown without questions. A total cost over no question is `0.0`.

## The numbers, defined

For a question, *G* is the set of its distinct gold article ids. For a list, *A* is the set of the distinct article ids of its items (constitution, "Metric Definitions").

| Number | Definition |
|---|---|
| `share_found` of a question and a list | The number of ids in both *G* and *A*, divided by the number of ids in *G*. Not defined when *G* is empty or the list is `null` |
| `all_found` | 1 when every id of *G* is in *A*, otherwise 0. Not defined in the same two cases |
| single-article, multi-article | *G* has exactly one id; *G* has two or more. A question with an empty *G* is in `all` only |
| retrieval miss | A question whose generation list is not `null` and has `all_found` = 0 |
| cost of an entry | As `cost_usd` above, computed exactly |
| total cost of a breakdown | The exact sum of the costs of its entries |
| median of *n* latencies | Sorted ascending: the middle value when *n* is odd, the mean of the two middle values when *n* is even |
| 95th percentile of *n* latencies | Sorted ascending: the value at position ⌈0.95 × *n*⌉, counted from 1 |

## Check of a run record

`run check` examines one record against the record of its question set and, for an experiment, against the record of its baseline (FR-022, FR-023, FR-035). It reports a *difference* for each of the following and passes when there is none.

| # | Difference |
|---|---|
| 1 | One of the three files is missing, is not UTF-8, or is not JSON of the stated form |
| 2 | A required field of `run.json`, of an entry or of `summary.json` is absent, or has the wrong type |
| 3 | `run_id` is not a run identifier, is not the name of the directory, or its time part is not `started_at` |
| 4 | The question set named in the config is not in the sets directory, or its role or its fingerprint differs from the config |
| 5 | A question of the set has no entry; an entry names a question that is not in the set; a question has two entries |
| 6 | A status is not one of the five |
| 7 | A list is neither `null` nor a list of non-empty strings; rule 1 or rule 2 of the results does not hold |
| 8 | `answer_sha256` is not the SHA-256 of `answer`, or exactly one of the two is `null` |
| 9 | A `tokens` entry names a model without a price, or names a model twice; `cost_usd` is not the cost computed from `tokens` and `config.prices` |
| 10 | The audit result is absent or is not a result of spec 1's form; its outcome is not `passed`; its index, its dataset name or revision, or its question set (version, fingerprint, number of questions) differs from the config and the set |
| 11 | `summary.json` names another run or another question set than `run.json`; `questions` is not the size of the set |
| 12 | A number of the summary differs from the number that `runs.summary_document` gives from the other files. Each number is reported on its own |
| 13 | Experiment only: the baseline is not in the registry, or its own record has one of the differences 1 to 12 |
| 14 | Experiment only: the baseline is on another question set (version or fingerprint) |
| 15 | Experiment only: the run is on a set whose role is not `golden` |
| 16 | Experiment only: the configs differ in a parameter other than the one named; they do not differ in the one named; `baseline_value` or `value` is not the value in the respective config |

A file that cannot be read stops the examination of what depends on it; every difference that can still be found is reported.

How the check proceeds where the table leaves room:

- **A line that cannot be read.** A line of `results.jsonl` that is not a JSON object is reported with its number: `results.jsonl line <n> is not a JSON object`. The other lines are still examined, entry by entry. The question of the unreadable line is not known, so "has no entry" is then reported for no question.
- **Order of the entries.** The check does not compare the order of the lines of `results.jsonl` with the order of the set. An entry is found by its `question_id`, and every number is computed with the entries in the order of the set.
- **Difference 12.** The numbers of the breakdowns and the retrieval misses of the summary are compared only when they can be computed from the other files: `run.json` and the record of the question set can be read, `config.prices` has its form and names no model twice, every line of `results.jsonl` can be read, there is exactly one entry for every question of the set and no other, and every entry has a sound status, sound lists, sound `tokens` and a sound latency. Otherwise the defects of the entries are reported and these numbers of the summary are not compared. `questions` and `questions_without_gold_articles` are compared with the record of the question set in either case.
- **Difference 13.** The baseline is checked as a record, by the differences 1 to 12, and not as an experiment: when the baseline is itself an experiment run, the differences 13 to 16 are not looked for in it. A run that names itself as its baseline fails with `the baseline <run id> is the run itself`, and nothing more is compared with the baseline.
- **Differences 14 and 16.** When the baseline is on another question set, that is reported once, as difference 14. The parameters under `question_set` are then not listed again as differences of the two configs.

The check is *not carried out* when the run does not exist in the registry, or when the registry or the sets directory cannot be read.

**Check of the registry** (FR-024, FR-034): every directory of the runs directory is a run and is checked. A directory whose name is not a run identifier is a failed run. Files directly in the runs directory, such as `.gitkeep`, are not runs. The check reports the number of runs, the number of failed runs, and the numbers of runs on golden sets and on held-out sets, counted by the `config.question_set.role` of every record in which that field can be read. It fails when a run fails.

## Pairwise comparison

For two runs on the same question set, by version and fingerprint (FR-027 to FR-029, FR-036). The outcome of a question is `all_found` on the generation list.

| Number | Definition |
|---|---|
| left out | Questions without a gold article, or without a generation list in either run |
| compared | The other questions of the set |
| gained | Compared questions with outcome 0 in the first run and 1 in the second |
| lost | Compared questions with outcome 1 in the first run and 0 in the second |

Each of `left out`, `gained` and `lost` is reported with its question identifiers, in the order of the set. The difference of `gained` and `lost` is not reported. The comparison is not stored: it is derived from two records whenever it is asked for. The outcome `correct` joins with spec 4.

A comparison is *refused* when a record does not pass its check or when the two runs are on different question sets; it is *not carried out* when a run does not exist.

## Example data

Written by hand for the acceptance checks, and not taken from `Wix/WixQA`. Every number here is an illustration with a known answer, not a result.

### `tests/data/harness/`: a data directory

In the form of spec 1 (`manifest.json` with the name `harness`, the revision `null`, and the row count, size and SHA-256 of each file), and it passes the dataset check.

| Part | Role | File | Rows |
|---|---|---|---|
| `hx` | `corpus` | `hx.jsonl` | 6: `hx-001` to `hx-006` |
| `hxa` | `questions` | `hxa.jsonl` | 5 |
| `hxb` | `questions` | `hxb.jsonl` | 3 |
| `hxc` | `questions` | `hxc.jsonl` | 2 |

| Question | `article_ids` | Kind |
|---|---|---|
| `hxa-001` | `hx-001` | single-article |
| `hxa-002` | `hx-002` | single-article |
| `hxa-003` | `hx-001`, `hx-003` | multi-article |
| `hxa-004` | `hx-002`, `hx-003`, `hx-004` | multi-article |
| `hxa-005` | `hx-005` | single-article |
| `hxb-001` | `hx-004`, `hx-005` | multi-article |
| `hxb-002` | `hx-006` | single-article |
| `hxb-003` | `hx-001`, `hx-006` | multi-article |
| `hxc-001` | `hx-001` | single-article |
| `hxc-002` | `hx-002` | single-article |

The texts of the articles, the questions and the answers are free. The ten question texts are all different, so every check reports `repeated question texts: 0` and `question texts in both sets: 0`.

### `tests/data/sets/`: question-set records

| Version | Role | Rule | `questions`, in order |
|---|---|---|---|
| `harness` | `golden` | draw, seed 1, `hxa` 5 and `hxb` 3 | `hxa-001` to `hxa-005`, `hxb-001` to `hxb-003` |
| `harness-hxc` | `held-out` | draw, seed 1, `hxc` 2 | `hxc-001`, `hxc-002` |
| `harness-one-less` | `golden` | as `harness` | as `harness`, without `hxb-003`; `count` 7 |
| `harness-one-more` | `golden` | as `harness` | as `harness`, then `hxc-001`; `count` 9; `dataset.parts` as `harness` |
| `harness-other-gold` | `golden` | as `harness` | as `harness`; the `article_ids` of `hxa-003` are `hx-001` only |
| `harness-half` | `golden` | draw, seed 7, `hxa` 3 and `hxb` 1 | `hxa-002`, `hxa-003`, `hxa-005`, `hxb-002` |
| `harness-half-rest` | `held-out` | complement of `harness-half` | `hxa-001`, `hxa-004`, `hxb-001`, `hxb-003` |
| `harness-half-swapped` | `golden` | as `harness-half` | `hxa-001`, `hxa-002`, `hxa-003`, `hxb-002` |
| `harness-half-rest-overlap` | `held-out` | complement of `harness-half` | `hxa-001`, `hxa-002`, `hxb-001`, `hxb-003` |
| `example` | `golden` | draw, seed 1, `exq` 3, on `tests/data/example` | `exq-001`, `exq-002`, `exq-003` |

Every record has its own `version` and is written in the canonical form of contracts/records.md. Apart from what the table states, a defective record is its sound counterpart.

**The draw behind `harness-half`**, computed for this plan (research.md, "Facts checked"). The key of an identifier is the SHA-256 of `sha256-order-v1:7:<identifier>`.

| Identifier | Draw key with the seed 7 | Position in its part | Selected |
|---|---|---|---|
| `hxa-001` | `b007c1a99f194f36e77ddff1287444edf952051575fc10e8920235c10574b35a` | 4 | no |
| `hxa-002` | `3ab6dbb72b4a0c0ea6ac711d6dc1f5d74391faf706a742a5ba6f9392127e8bfc` | 1 | yes |
| `hxa-003` | `3d153221a5af0c19cabea03edc0c7911e80dc59e4665e9d71f3bcb5d5e22e1e3` | 2 | yes |
| `hxa-004` | `ddd57ba1f0b3ac63038adda3109582537c275bde1cd1d957e296569a1c668f3b` | 5 | no |
| `hxa-005` | `ac565ec9fabc07a8cbfe8cbb64efaf1d716272217ecb623cb8954a8f0b035bd9` | 3 | yes |
| `hxb-001` | `bdeb5dbf30b3cda7003e44daaa672c50e9ef7f6796a1f5b4fa61e5e88563be62` | 2 | no |
| `hxb-002` | `25dedc6ec7bacbd106c0818e47ab1288ccfc0f93a2a1f357497e3d1797a190fa` | 1 | yes |
| `hxb-003` | `e63b12a2e3a527e027c2b151bdff7ee0728d36c6e9417885d6fe85d70c8db68a` | 3 | no |

So `harness-half` holds `hxa-002`, `hxa-003`, `hxa-005` and `hxb-002` (three single-article questions and one multi-article question), and `harness-half-rest` holds `hxa-001`, `hxa-004`, `hxb-001` and `hxb-003` (one and three).

What the checks of the four records around the draw find:

| Version | Outcome | Differences |
|---|---|---|
| `harness-half` | passed | none |
| `harness-half-rest` | passed | none; `in both sets: 0`, `in neither set: 0` |
| `harness-half-swapped` | failed | exactly two: `hxa-005` is selected by the rule and is not in the question set; `hxa-001` is in the question set and is not selected by the rule |
| `harness-half-rest-overlap` | failed | `hxa-002` is in both sets; `hxa-004` is in neither set; `in both sets: 1`, `in neither set: 1` |

### `tests/data/runs/`: a registry of four sound records

Shared by the four runs unless stated: `config.index` is `harness`; `config.dataset` is `{"name": "harness", "revision": null}`; one model, `example-model`, at 1.00 US dollar per million input tokens and 2.00 per million output tokens; the audit result in the summary is written by hand, with the outcome `passed`, for the index `harness` and the run's question set. A full `run.json`, one entry and the full `summary.json` of `example-a` are in contracts/records.md.

| Run | Question set | Experiment |
|---|---|---|
| `20261101T100000Z-example-a` | `harness` | no |
| `20261102T100000Z-example-b` | `harness` | baseline `20261101T100000Z-example-a`, parameter `reranking.enabled`, `false` → `true` |
| `20261103T100000Z-example-c` | `harness-hxc` | no |
| `20261104T100000Z-example-d` | `harness-hxc` | no |

**`example-a`**: the table of the spec. Each entry has one `tokens` object for `example-model`; the entry of `hxa-005` has an empty `tokens` list.

| Question | Status | `retrieved_list` | `generation_list` | `latency_seconds` | Input, output tokens | `cost_usd` |
|---|---|---|---|---|---|---|
| `hxa-001` | `answered` | `hx-001`, `hx-002`, `hx-003` | `hx-001`, `hx-002` | 1.0 | 1000, 100 | 0.0012 |
| `hxa-002` | `answered` | `hx-003`, `hx-002`, `hx-001` | `hx-003`, `hx-001` | 2.0 | 1000, 100 | 0.0012 |
| `hxa-003` | `answered` | `hx-001`, `hx-004`, `hx-001` | `hx-001`, `hx-004` | 3.0 | 2000, 200 | 0.0024 |
| `hxa-004` | `no_answer` | `hx-002`, `hx-003`, `hx-005`, `hx-004` | `hx-002`, `hx-003`, `hx-005` | 4.0 | 2000, 50 | 0.0021 |
| `hxa-005` | `error` | `null` | `null` | 5.0 | none | 0.0 |
| `hxb-001` | `timeout` | `hx-004`, `hx-005` | `null` | 30.0 | 500, 0 | 0.0005 |
| `hxb-002` | `call_limit` | `hx-003` | `[]` | 7.0 | 3000, 300 | 0.0036 |
| `hxb-003` | `answered` | `hx-006`, `hx-001` | `hx-006`, `hx-001` | 8.0 | 1500, 150 | 0.0018 |

For `hxa-005` the fields `context`, `answer` and `answer_sha256` are `null`; for `hxb-001` and `hxb-002` as well. The four `answered` entries and the `no_answer` entry have a `context` and an `answer` with its hash; their texts are free.

**`example-b`**: as `example-a`, with `config.reranking.enabled` `true` and these five entries changed. Every latency and every token count that is not named stays.

| Question | Status | `retrieved_list` | `generation_list` | Input, output tokens | `cost_usd` |
|---|---|---|---|---|---|
| `hxa-002` | `answered` | `hx-003`, `hx-002`, `hx-001` | `hx-002`, `hx-003` | 1000, 100 | 0.0012 |
| `hxa-003` | `answered` | `hx-001`, `hx-003`, `hx-004` | `hx-003`, `hx-001` | 2000, 200 | 0.0024 |
| `hxa-004` | `answered` | `hx-002`, `hx-003`, `hx-005`, `hx-004` | `hx-002`, `hx-003`, `hx-005` | 2000, 50 | 0.0021 |
| `hxa-005` | `answered` | `hx-005` | `hx-005` | 1000, 100 | 0.0012 |
| `hxb-003` | `answered` | `hx-006`, `hx-002` | `hx-006`, `hx-002` | 1500, 150 | 0.0018 |

**`example-c` and `example-d`**: two entries each, both `answered`, each with 1000 input and 100 output tokens (`cost_usd` 0.0012); the latency of `hxc-001` is 1.0 and that of `hxc-002` is 2.0. The retrieved list equals the generation list.

| Run | List of `hxc-001` | List of `hxc-002` |
|---|---|---|
| `example-c` | `hx-001` | `hx-003` |
| `example-d` | `hx-001` | `hx-002` |

**The numbers of the four summaries**, computed for this plan. "gen" is `generation_list`, "ret" is `retrieved_list`; each cell is `questions` / `mean_share_found` / `all_found` / `share_all_found`.

| Run | Breakdown | `questions` | `status`: answered, no_answer, error, timeout, call_limit | gen | ret | `cost_usd`: total, per question | `latency_seconds`: median, p95 |
|---|---|---|---|---|---|---|---|
| a | `all` | 8 | 4, 1, 1, 1, 1 | 6 / 0.5277777777777778 / 2 / 0.3333333333333333 | 7 / 0.7857142857142857 / 5 / 0.7142857142857143 | 0.0128, 0.0016 | 4.5, 30.0 |
| a | `single_article` | 4 | 2, 0, 1, 0, 1 | 3 / 0.3333333333333333 / 1 / 0.3333333333333333 | 3 / 0.6666666666666666 / 2 / 0.6666666666666666 | 0.006, 0.0015 | 3.5, 7.0 |
| a | `multi_article` | 4 | 2, 1, 0, 1, 0 | 3 / 0.7222222222222222 / 1 / 0.3333333333333333 | 4 / 0.875 / 3 / 0.75 | 0.0068, 0.0017 | 6.0, 30.0 |
| b | `all` | 8 | 6, 0, 0, 1, 1 | 7 / 0.7380952380952381 / 4 / 0.5714285714285714 | 8 / 0.8125 / 6 / 0.75 | 0.014, 0.00175 | 4.5, 30.0 |
| b | `single_article` | 4 | 3, 0, 0, 0, 1 | 4 / 0.75 / 3 / 0.75 | 4 / 0.75 / 3 / 0.75 | 0.0072, 0.0018 | 3.5, 7.0 |
| b | `multi_article` | 4 | 3, 0, 0, 1, 0 | 3 / 0.7222222222222222 / 1 / 0.3333333333333333 | 4 / 0.875 / 3 / 0.75 | 0.0068, 0.0017 | 6.0, 30.0 |
| c | `all` and `single_article` | 2 | 2, 0, 0, 0, 0 | 2 / 0.5 / 1 / 0.5 | 2 / 0.5 / 1 / 0.5 | 0.0024, 0.0012 | 1.5, 2.0 |
| d | `all` and `single_article` | 2 | 2, 0, 0, 0, 0 | 2 / 1.0 / 2 / 1.0 | 2 / 1.0 / 2 / 1.0 | 0.0024, 0.0012 | 1.5, 2.0 |
| c, d | `multi_article` | 0 | 0, 0, 0, 0, 0 | 0 / `null` / 0 / `null` | 0 / `null` / 0 / `null` | 0.0, `null` | `null`, `null` |

| Run | `retrieval_misses` |
|---|---|
| a | `hxa-002`, `hxa-003`, `hxa-004`, `hxb-002` |
| b | `hxa-004`, `hxb-002`, `hxb-003` |
| c | `hxc-002` |
| d | none |

`questions_without_gold_articles` is 0 in all four.

**The comparisons**:

| First, second | compared | left out | gained | lost |
|---|---|---|---|---|
| a, b | 6 | 2: `hxa-005`, `hxb-001` | 2: `hxa-002`, `hxa-003` | 1: `hxb-003` |
| c, d | 2 | 0 | 1: `hxc-002` | 0 |

### `tests/data/runs-invalid/`: a registry of nine records

Two sound records, byte for byte the records of `tests/data/runs/`: `20261101T100000Z-example-a` and `20261103T100000Z-example-c`. Seven records with one defect each. A defective record has its own `run_id` and `started_at`, in all three files where they occur, and is otherwise the record it is made from.

| Run | Made from | The one change | The difference the check names |
|---|---|---|---|
| `20261101T100100Z-no-latency` | a | The entry of `hxa-003` has no field `latency_seconds` | `hxa-003` and `latency_seconds` |
| `20261101T100200Z-missing-question` | a | `results.jsonl` has no line for `hxb-003` | `hxb-003` has no entry |
| `20261101T100300Z-unknown-status` | a | The status of `hxa-004` is `skipped` | `hxa-004` and `skipped` |
| `20261101T100400Z-wrong-hash` | a | `answer_sha256` of `hxa-001` is 64 zeros | `hxa-001` and `answer_sha256` |
| `20261101T100500Z-stale-summary` | a | `breakdowns.all.generation_list.all_found` is 3 | the generation list, all questions, 3 and 2 |
| `20261101T100600Z-two-changes` | a | `config.experiment` names the baseline `20261101T100000Z-example-a` and the parameter `reranking.enabled`, `false` → `true`; `config.reranking.enabled` is `true`, and `config.retrieval.top_k` is 4 where the baseline has 3 | `retrieval.top_k` |
| `20261103T100100Z-experiment-on-held-out` | c | `config.experiment` names the baseline `20261103T100000Z-example-c` and the parameter `reranking.enabled`, `false` → `true`; `config.reranking.enabled` is `true` | `harness-hxc` is a held-out set |

A summary is left as the summary of the record it is made from, with the new `run_id`, except in `stale-summary`. In `no-latency`, `missing-question` and `unknown-status` the check may name further differences that follow from the one change, such as numbers of the summary; the acceptance checks read only the difference in the table. `wrong-hash`, `two-changes` and `experiment-on-held-out` have exactly the one difference.

The check of this registry reports `runs: 9`, `failed runs: 7`, `runs on golden sets: 7` and `runs on held-out sets: 2`.
