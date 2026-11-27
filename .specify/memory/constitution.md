# WixQA-RAG Constitution

The binding rules of the study. `PROJECT.md` records the project's facts and decisions and states
each measurement rule with its reason; this file gives the exact definitions. The terms *gold
article*, *golden set*, *held-out set*, *run*, *run registry*, *baseline*, *judge*, *calibration*
and *slice* are defined in the glossary of `PROJECT.md`.

## Core Principles

Principles I–IX are the nine measurement invariants of `PROJECT.md`, in the same order.

### I. Index Audit

Before a run retrieves anything, the index MUST be audited against the dataset:

- the article ids held in the index MUST be exactly the `id` values of `wix_kb_corpus`: none
  missing, none extra;
- every `article_ids` value of every question of the question set that the run is made on MUST
  be among them.

The audit queries the index that retrieval uses; a check of files on disk does not satisfy it. Any
difference stops the run, and the audit result is part of the run record.

Rationale: an article that is absent from the index looks exactly like a retrieval miss. Without
the audit the two cannot be told apart.

### II. Article-Level Retrieval Metrics on the Actual Lists

Retrieval metrics MUST be computed on article ids and on the lists the pipeline produced:

- every retrieved item is mapped to the `id` of the article it comes from;
- the metrics are computed on the *generation list*, the ordered list passed to generation
  exactly as passed, and separately on the *retrieved list*, the ordered list as it stood before
  reranking;
- no metric is computed on a cut-off or a list that the pipeline did not use.

For each question the run reports the share of gold articles found and an "all found" flag, as
defined under "Metric Definitions".

Rationale: an answer can draw only on what the generator received. A metric on any other list
describes a pipeline that did not run.

### III. Fixed Golden Set

The golden set MUST live in `evals/golden/` as the list of question identifiers together with the
selection rule and the seed that produce that list from the dataset at a recorded revision. Every
pipeline version MUST be evaluated on the same golden set. Two versions are compared pairwise: the
number of questions that became correct and the number that became incorrect are both reported.

The golden set changes only by an amendment that the owner approves and that gives it a new
version.

Besides the golden set the study may keep *held-out sets*. A *question set* is the golden set or
a held-out set. A held-out set is recorded in the repository as the golden set is: the list of
question identifiers together with the selection rule and, where the rule draws at random, the
seed, under a version; it changes only as the golden set does.

- A held-out set MUST NOT be used to choose a setting of the pipeline.
- A held-out set is run only at the baseline and at milestones that the owner names.
- An experiment run and its baseline run MUST be on the golden set.
- Runs on different question sets, or on different versions of one question set, MUST NOT be
  compared.

Rationale: an average can stay flat while single questions flip in both directions. Only a fixed
set shows which ones. A pipeline whose every setting was chosen on one set of questions can
become fitted to that set; questions that took part in no decision show whether it also works on
others.

### IV. A Human Label Belongs to One Answer

A human label MUST store the identifier of the run and the hash of the answer it judges.
Calibration of a run MUST accept a label only when its run identifier is that run's and its answer
hash equals the hash of that run's answer to the same question. Every other label is rejected and
reported.

Rationale: a label describes one text. Applied to a later answer, it would score an answer that
nobody read.

### V. Judge Calibrated on Every Labelled Run

A run is *labelled* when the owner has hand-labelled answers of that run; which answers are
labelled is open decision 1 in `PROJECT.md`.

- For every labelled run the report MUST carry the judge's TPR and TNR measured against that
  run's labels.
- Judge scores of a run MUST NOT be reported unless the run is labelled and its TPR and TNR are
  reported next to them.
- TODO(CALIBRATION_THRESHOLD): the minimum TPR and TNR below which judge scores are withheld; the
  owner sets it after the first labelling (spec 4).
- The judge MUST check groundedness against the context the generator received in that run, taken
  from the run record.

Rationale: the judge is a measuring instrument. Its error rate has to be known on the answers it
is used on.

### VI. One Change, One Run

The config of a run MUST be stored next to its results. An experiment run MUST differ from the
baseline run in exactly one config parameter, and its record names that parameter with the old
and the new value.

TODO(REFERENCE_AFTER_ADOPTION): whether experiments that follow an adopted change start from the
baseline or from the configuration that includes the adopted change is not decided; the owner
decides before the first experiment's decision is recorded.

Rationale: when two parameters change together, the effect of each cannot be separated.

### VII. Failures Are Separate Categories

Every question of a run's question set ends in exactly one status: answered, no answer ("I don't
know"), error, timeout, or call limit exhausted. The count of each status MUST be reported for
every run. A failure that kept retrieval from completing is never counted as a retrieval miss.

Rationale: a timeout and a wrong document call for different fixes. One number for both hides
which of them happened.

### VIII. Breakdowns

Every metric MUST be reported for all questions, for single-article questions, and for
multi-article questions, each with the number of questions it is computed on.

Rationale: an overall average can look steady while the questions that need several articles fail.

### IX. Cost and Latency Belong to the Result

Every run MUST report its cost and its latency next to its quality metrics. A run record without
them is invalid.

Rationale: a change that improves answers at several times the cost or the delay is a different
decision from one that improves them at no cost.

### X. Evidence Before Decisions

- Every decision to adopt or reject a change to the pipeline (a model, a retrieval method, a
  reranker, chunking, a prompt, a parameter value) MUST cite the identifiers of the runs that
  justify it.
- A decision cites only runs on the golden set. A run on a held-out set justifies no decision
  about the pipeline (Principle III).
- The configuration that produces the baseline is a starting point. It is recorded as chosen, not
  as found.
- No spec states a numeric quality target before the baseline run exists. From then on, targets
  are stated relative to the baseline's numbers.

Rationale: the study's claim is that each decision can be traced to a measurement that anyone can
repeat.

## Scope and Non-Goals

The study answers one question on one dataset: what makes a support knowledge-base assistant
answer better, measured on `Wix/WixQA`.

Out of scope:

- **Operating a service.** The study has no users, no customers and no availability targets, and
  no spec assumes them.
- **Claims beyond WixQA.** Findings are stated for this dataset and its corpus snapshot. Nothing
  is claimed about other knowledge bases.
- **Training models.** Models are used as their providers offer them; fine-tuning is not part of
  the study.
- **Editing the dataset.** Questions, reference answers and articles are used as published. A
  defect found in the data is recorded in the repository; the data stays as it is.
- **A general-purpose framework.** Code is written for this pipeline and this dataset. Support
  for other datasets, providers or plug-ins is added only when a spec requires it.

## Stack

Decided (recorded under "Decided" in `PROJECT.md`):

- Implementation language: Python.
- Dataset: `Wix/WixQA` from Hugging Face, MIT license.
- Embedding model: OpenAI `text-embedding-3-small`.
- Vector store: PostgreSQL with the pgvector extension.
- Process: GitHub Spec Kit 1.4.2, initialised for Claude Code with shell scripts.
- Source code on GitHub; work items in a GitHub Project.
- Language of specs, README and UI: English.

The generation model and the judge model are open decisions in `PROJECT.md`. A spec that needs
one of them waits for the owner's decision.

Rules for every feature:

- The dataset is loaded at a pinned revision, and every run records that revision.
- A run config names each model by the most specific identifier its provider offers.
- Dependencies are pinned by a lock file committed to the repository.
- Secrets such as API keys and database passwords are read from the environment and are never
  committed.
- Python tooling: Python 3.14; uv manages the environment and the dependencies, and `uv.lock` is
  the lock file; tests run with pytest; CI runs on GitHub Actions.

## Metric Definitions

For a question, *G* is the set of its gold articles (its `article_ids`). For a list, *A* is the
set of distinct article ids of its items.

**Retrieval** (Principle II), computed for the generation list and for the retrieved list:

- `share_found` = the number of gold articles that are in *A*, divided by the number of gold
  articles;
- `all_found` = 1 when every gold article is in *A*, otherwise 0;
- for a run: the mean of `share_found` and the share of questions with `all_found` = 1, over the
  questions that have a gold article and for which the list exists; that number of questions is
  reported with them;
- a *retrieval miss* is a question whose generation list exists and has `all_found` = 0.

When nothing reorders or cuts the list between retrieval and generation, the two lists are the
same list, and both sets of numbers are still reported.

**Status** (Principle VII). Each question of a run's question set has exactly one:

| Status | Meaning |
|---|---|
| `answered` | The pipeline returned an answer |
| `no_answer` | The pipeline stated that it cannot answer ("I don't know") |
| `error` | The pipeline raised an error or returned output that cannot be read |
| `timeout` | The time limit for one question was exceeded |
| `call_limit` | The limit on model or tool calls for one question was exhausted |

The limits are parameters of the run config. The status counts add up to the size of the run's
question set.

**Answer quality** (Principle V). `correct` = 1 when the judge accepts the answer under the rubric
of spec 4, otherwise 0; a question whose status is not `answered` has `correct` = 0. For a run:
the share of the questions of the run's question set with `correct` = 1.

**Calibration** (Principle V), on the labelled answers of one run:

- TPR = answers labelled correct and accepted by the judge, divided by answers labelled correct;
- TNR = answers labelled incorrect and rejected by the judge, divided by answers labelled
  incorrect.

Each rate is reported with its numerator and denominator. A rate with a zero denominator is
reported as undefined.

**Pairwise comparison** (Principle III), for two runs on the same version of the same question
set and one 0/1 outcome per question (`all_found` on the generation list, or `correct`):

- `gained` = the number of questions with outcome 0 in the first run and 1 in the second;
- `lost` = the number of questions with outcome 1 in the first run and 0 in the second.

Both numbers are reported together with the identifiers of the questions behind them; their
difference alone is never reported. For `all_found`, a question that lacks a generation list in
either run is left out, and the number left out is reported.

**Breakdown** (Principle VIII). A question is *single-article* when it has exactly one gold
article and *multi-article* when it has two or more.

**Cost** (Principle IX). In US dollars: token counts multiplied by the prices recorded in the run
config, summed over the model calls of the run. Cost is reported for answering (retrieval,
reranking, generation) and for judging separately, each as a run total and per question. Building
an index is recorded with its own cost; a run names the index it used.

**Latency** (Principle IX). For each question: wall-clock seconds from the moment the pipeline
receives the question until it returns an answer or fails. For a run: the median and the 95th
percentile over all questions of the run's question set. The concurrency setting is part of the
run config; latencies measured under different settings are not compared.

## Run Record Format

The run registry is `evals/runs/`. One run is one directory, `evals/runs/<run-id>/`, of UTF-8 text
files in JSON or JSON Lines. A run record MUST contain:

- **Identity:** the run id, the start time in UTC, and the commit of the code that produced it.
- **Config:** everything needed to repeat the run: the dataset revision, the question set with
  its version and whether it is the golden set or a held-out set, the index used, each model's
  identifier, the prompts, the retrieval and reranking settings, the context size, the limits,
  the seeds, the concurrency setting, and the price list used for cost. An experiment run also
  names the baseline run and the one parameter that differs.
- **Results, one entry per question of the run's question set:** the question identifier; the
  status; the retrieved list and the generation list as ordered article ids; the context passed
  to the generator in a form from which its exact text can be restored; the answer and its hash
  (SHA-256 of the answer's UTF-8 text); token counts, cost and latency.
- **Summary:** the audit result of Principle I, the status counts, and every metric of "Metric
  Definitions" in the three breakdowns with its denominators.

Rules:

- A run id is unique and is never reused.
- Recorded files are written once and never edited. A correction is a new run. Later steps such
  as judging add files to the run's directory; they do not change the files already there.
- The summary is derived from the other files and can be recomputed at any time; recomputing it
  MUST give the same numbers.
- Human labels live in `evals/labels/` and point to their run by its identifier (Principle IV).
- The evaluation-harness spec (spec 2) fixes the file names, the field names, the form of a run
  id and the form of a question identifier, and provides the test that checks a run record
  against this section.

## Development Workflow

**Order of work.** Specs are implemented in the order of the "Spec order" table in `PROJECT.md`:
measurement first, then the pipeline, then improvements. Each row is one Spec Kit feature, and
each experiment is its own feature. No experiment starts before the baseline run exists.

**Cycle for one spec.**

1. The owner approves the spec and its acceptance criteria. No test and no implementation is
   written for a spec that is not approved.
2. The testing agent writes the acceptance tests before the implementation exists, and the tests
   MUST fail at that point. Task lists place test tasks before the implementation tasks they
   cover.
3. The coding agent writes the implementation until the acceptance tests pass. The coding agent
   MUST NOT change an acceptance test; a test that is wrong goes back to the testing agent.
4. For a spec that changes what the pipeline retrieves or answers, an evaluation run is recorded
   in the run registry and compared pairwise with the previous run.
5. The code review agent checks the diff against the spec and this constitution. A gap in the
   spec is closed by amending the spec with the owner's approval, never by departing from it.

The DevOps agent owns CI/CD. The owner hand-labels the answers of every labelled run, and judge
scores wait for calibration (Principle V). The owner makes the decisions listed under "Open" in
`PROJECT.md`; an agent that needs one of them stops and asks.

**Task tracking and commits.**

- Work items are GitHub issues in the project's GitHub Project. One issue stands for one spec;
  the tasks of a spec stay as the checklist in its `tasks.md`.
- One spec has one branch, named like the spec's directory (`NNN-short-name`), and reaches `main`
  through one pull request. A large spec may use one pull request per slice.
- `main` changes only through pull requests, and the owner merges them. The commit that starts
  the repository's history is the only exception.
- A pull request is merged only when the automated checks pass and the code review agent has
  checked the diff.
- Pull requests are squash-merged: each lands on `main` as one commit. Its first line is the pull
  request's title followed by its number, and its body is the pull request's description.
  Commits inside a branch are working notes, and their messages are free-form.
- A pull-request title follows Conventional Commits 1.0.0, `type(scope): summary`. The types are
  `feat`, `fix`, `docs`, `test`, `refactor`, `ci`, `chore`, and `exp` for an experiment: a run
  together with the decision it supports. The scope is optional and names the area, for example
  `corpus`, `evals`, `pipeline`, `judge` or `app`.
- A pull-request description ends with these lines:
  - `Spec: specs/<NNN-short-name>`, or `Spec: none` for a change outside any spec;
  - `Closes #<number>` for every issue the pull request completes;
  - `Run: <run-id>` for the run that justifies the change, with `Compared-With: <run-id>`; a
    change that cannot alter what the pipeline retrieves or answers states `Run: none`.
- A commit written by an agent keeps the authorship line that the agent adds, for example
  `Co-Authored-By:`.
- Commit messages and pull-request descriptions contain no link to a private agent session;
  readers of the repository cannot open it.

**Public texts.** The README, the specs, pull requests, commit messages and the repository's
pages on GitHub state what was measured, how to re-run it, and what was found, or that it has not
been measured yet. A public text claims only what the repository contains at that commit.

## Governance

- This constitution binds every spec, plan, task list, test and agent in the repository. Where a
  spec or a template conflicts with it, the constitution prevails until it is amended.
- `PROJECT.md` records facts and decisions and is the working reference for agents; this file
  records the rules and the exact definitions. A contradiction between the two is an error: work
  on the affected spec stops until the owner resolves it.
- **Amendments.** Only the owner approves an amendment. An amendment is a pull request that
  changes this file, states the reason, updates the version and the "Last Amended" date, and
  updates `PROJECT.md` in the same pull request when a fact or decision recorded there changes.
- **Versioning.** Semantic versioning. MAJOR: a principle or a metric definition is removed or
  redefined. MINOR: a principle or a section is added or materially expanded. PATCH: wording is
  clarified without changing a rule.
- **Comparability.** An amendment that changes a metric definition or the run record format
  states which recorded runs remain comparable. Where the recorded results allow it, the metrics
  of earlier runs are recomputed under the new definition. Numbers computed under different
  definitions are never placed in one comparison.
- **Compliance.** Every plan passes a constitution check before tasks are generated. The code
  review agent checks every pull request against the principles. A violation blocks the merge
  until the change is corrected or the constitution is amended.

**Version**: 1.2.0 | **Ratified**: 2026-11-23 | **Last Amended**: 2026-11-27
