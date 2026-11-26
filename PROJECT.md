# Project: RAG over a support knowledge base (WixQA)

The single source of project facts for agents. The goal and the spec order are a working version from discussion; the owner may revise them. Dataset facts come from the Wix/WixQA dataset card on Hugging Face.

## Goal

Find out what actually makes a support knowledge-base assistant answer better, as an open, reproducible study on WixQA: every pipeline decision is backed by a measurement that can be re-run.

The project succeeds when a reader of the repository can find, for any decision (model, retrieval method, reranker, chunking), the run that justified it.

## Context

- Positioning: an open engineering study. Public texts state what was measured, how to re-run it, and what was found.
- The project is led by its **owner**.
- Working mode: the owner owns specs and evaluation; agents write the implementation.

## Data

Dataset `Wix/WixQA`, MIT license.

| Part | Rows | What it is |
|---|---|---|
| `wixqa_expertwritten` | 200 | Real user queries; expert-written, step-by-step answers that often draw on several articles |
| `wixqa_simulated` | 200 | Concise answers distilled from multi-turn chats; also often multi-article |
| `wixqa_synthetic` | 6,221 | LLM-generated pairs; each grounded in a single article |
| `wix_kb_corpus` | 6,221 | Snapshot of the Wix Help Center; the retrieval corpus |

- Question fields: `question`, `answer` (Markdown), `article_ids` — the articles needed for the answer; this is the retrieval ground truth.
- Article fields: `id` (matches the values in `article_ids`), `url`, `contents` (plain text, HTML removed), `article_type` — `article`, `feature_request`, or `known_issue`.

## Measurement invariants

Binding on every spec. The constitution gives the exact definitions; this section gives the rule and the reason. The origin of each rule is traced in the owner's private notes (`personal-notes/`, kept out of the repository).

1. **Index audit.** The index is checked against every corpus `id` and every `article_ids` value in the golden set; a mismatch stops the run. Reason: in the project analysed in the notes, more than half of the retrieval misses came from documents absent from the index, and its disk-versus-index check did not catch them.
2. **Retrieval metrics are article-level and computed on the actual list.** They are computed on the ordered list passed to generation, and separately on the list before reranking. For a question with several gold articles: the share found and an "all found" flag.
3. **The golden set is fixed.** The ID list, the seed, and the selection rule live in the repository; pipeline versions are compared on it pairwise: how many questions became correct and how many became incorrect.
4. **A human label belongs to an answer.** A label stores the run identifier and the answer hash; calibration accepts only labels from its own run.
5. **The judge is calibrated on every labelled run.** The report carries TPR and TNR; the judge checks groundedness against the context the generator saw.
6. **One change, one run.** The run config sits next to the results; an experiment differs from baseline by one parameter.
7. **Failures are separate categories.** An "I don't know" answer, an error, a timeout, and an exhausted call limit are counted apart from retrieval misses.
8. **Breakdowns.** Every metric is reported separately for single-article and multi-article questions.
9. **Cost and latency are part of a run's result.**

## Spec order

Measurement first, pipeline second: without the evaluation harness, no decision about retrieval or models can be justified.

Row 0 is the Spec Kit constitution. Each later row is one Spec Kit feature, and each experiment is its own feature.

| # | Spec | What it fixes | Acceptance |
|---|---|---|---|
| 0 | Constitution | Non-goals, stack, exact metric definitions, run file format, task-tracking convention | Owner approval |
| 1 | Corpus and audit | Corpus loading, index, audit per invariant 1 | Test: zero mismatches |
| 2 | Evaluation harness | Golden set, retrieval metrics, run registry | Tests on a small example with a known answer |
| 3 | End-to-end skeleton | Dense retrieval → generation → answer with sources; the first full run becomes baseline | Test: the run completes and the run file is valid |
| 4 | Judge and calibration | Rubric for step-by-step answers, human label format, judge, TPR and TNR | Tests; the owner sets the calibration threshold after the first labelling |
| 5 | Experiments | One spec per experiment | Threshold relative to baseline |
| 6 | Application | API and UI: answer, sources, cost, latency | Tests |

Experiment candidates; the owner picks the order after baseline, cheapest first:

- generation model;
- context size;
- hybrid retrieval, dense + keyword search; the keyword side (built-in Postgres full-text ranking or a BM25 extension) is chosen in that experiment's spec;
- embedding model; a change means re-indexing the whole corpus;
- reranker;
- article title at the start of each chunk;
- multi-article questions: larger k, query decomposition with a call limit;
- filter or boost by `article_type`.

## Process: GitHub Spec Kit with our additions

Taken from Spec Kit unchanged: its steps (constitution, specify, clarify, plan, tasks, implement, converge) and its folder layout. Tasks stay in each spec's `tasks.md`; one GitHub issue tracks each spec.

Our seven additions, adopted by the owner on 2026-11-19:

| # | Addition | What it means | Where it lives |
|---|---|---|---|
| 1 | Measurement rules | The nine measurement invariants bind every feature | Constitution principles |
| 2 | Order of work | Measurement first, then the pipeline, then improvements; see "Spec order" | Constitution; one Spec Kit feature per row of the spec order |
| 3 | Machine-run acceptance checks | Next to the Given/When/Then scenarios, every spec lists checks of the form "command → observable result"; each check is red before implementation | Spec template, in a section of its own |
| 4 | Experiment document | A separate form for experiments: hypothesis, one changed parameter, decision rule relative to baseline | A project experiment template |
| 5 | Separate agents | The implement step is split: the testing agent writes the tests first, the coding agent implements, the code review agent checks the diff against the spec, the DevOps agent owns CI/CD | Constitution; tasks ordered tests-first |
| 6 | Owner's hand labelling as a gate | The owner labels a sample of answers on every labelled run; the judge's numbers count only after calibration against those labels (invariants 4–5) | Constitution; a gate before a run's judge scores are reported |
| 7 | Run registry as evidence | Every decision cites the run that justified it; numeric targets appear only after baseline (invariant 6) | Constitution; an "Evidence" section in the spec template |

Notes for whoever wires these in:

- Spec Kit keeps a spec technology-agnostic. The checks of addition 3 name commands, so they sit in their own section, apart from the user scenarios and success criteria.
- Spec Kit offers presets, project-local template overrides, and extensions for changes like these. Additions 3, 5 and 7 are carried by project-local overrides in `.specify/templates/overrides/`: `spec-template.md` adds the "Acceptance Checks" and "Evidence" sections, and `tasks-template.md` makes tests required and first. Spec Kit reads an override in place of its own template, which stays unchanged. The constitution (version 1.1.0) states the rules of additions 1, 2, 5, 6 and 7. The experiment template of addition 4 is not implemented yet; its mechanism is chosen when it is implemented.

## Roles and cycle

- **Owner** approves specs and acceptance criteria, labels answers by hand, and makes the decisions listed under "Open".
- **Spec agent** writes specs with GitHub Spec Kit.
- **Testing agent** writes the tests.
- **Coding agent** writes the implementation and executes runs.
- **Code review agent** checks the diff against the spec.
- **DevOps agent** owns CI/CD.

Cycle for one spec:

1. The owner approves the spec.
2. The testing agent writes the acceptance tests; they are red.
3. The coding agent writes the implementation until the tests are green.
4. The evaluation run is recorded in the run registry and compared pairwise with the previous one.
5. The code review agent checks the diff against the spec. If the implementation exposed a gap, the spec is amended.

## Decisions

### Decided

- Dataset: WixQA.
- Approach: spec-driven development with GitHub Spec Kit, plus the seven additions listed under "Process".
- Spec Kit version 1.4.2, initialised for Claude Code with shell scripts; its files live in `.specify/` and `.claude/skills/`.
- Templates: the spec and tasks templates in `.specify/templates/overrides/` are this project's versions, made from the Spec Kit 1.4.2 templates. After a Spec Kit upgrade they are compared with the new stock templates.
- Constitution: version 1.1.0, in `.specify/memory/constitution.md`. Version 1.0.0 was approved by the owner on 2026-11-23; the amendment of 2026-11-25 records the Python tooling.
- Implementation language: Python.
- Language of specs, README, and UI: English.
- Source code: GitHub. Task tracking: a GitHub Project, one issue per spec; a spec's tasks stay in its `tasks.md`.
- Changes reach `main` through one pull request per spec, squash-merged by the owner; titles follow Conventional Commits. The convention is in the constitution under "Development Workflow".
- Out of scope: operating a service, claims beyond WixQA, training models, editing the dataset, a general-purpose framework. See the constitution, "Scope and Non-Goals".
- Embedding model: OpenAI `text-embedding-3-small`.
- Vector store: PostgreSQL with the pgvector extension.
- Python tooling: Python 3.14; uv manages the environment and the dependencies, and `uv.lock` is the lock file; tests run with pytest; CI runs on GitHub Actions.
- Where the commands run (owner's decision of 2026-11-24): every command that needs the dataset host or the embedding provider runs on GitHub Actions, started by hand, with the provider key stored as a repository secret.
- Golden set (owner's decision of 2026-11-26): all questions of the two parts `wixqa_expertwritten` and `wixqa_simulated`, 200 + 200 = 400 questions. The part `wixqa_synthetic` is not in it and may become a separate set later.
- Lessons from another project are collected in the owner's private notes (`personal-notes/`, kept out of the repository).

### Open

The owner decides. Answers move to "Decided".

| # | Decision | Blocks spec |
|---|---|---|
| 1 | Hand labelling: how many questions of the golden set are hand-labelled | 4 |
| 2 | Generation model for baseline | 3 |
| 3 | Budget for one full evaluation run | 3 |
| 4 | Judge model | 4 |
| 5 | Application scope: API only, or also UI and deployment | 6 |
| 6 | After an experiment's change is adopted: later experiments start from the baseline, or from the configuration that includes the change | 5 |

## Glossary

- **Gold article** — an article listed in a question's `article_ids`.
- **Golden set** — the fixed list of questions on which all pipeline versions are compared.
- **Run** — one execution of the pipeline on the golden set, with config and results recorded.
- **Run registry** — where all runs are stored; the source of numbers for specs.
- **Baseline** — the first full run of the end-to-end skeleton; the reference point for thresholds.
- **Judge** — an LLM that scores an answer against a rubric.
- **Calibration** — comparing judge verdicts with human labels; it yields TPR (the share of correct answers the judge accepted) and TNR (the share of incorrect answers the judge rejected).
- **Slice** — a thin end-to-end piece of functionality that can be accepted on its own.

## Links

- Dataset: https://huggingface.co/datasets/Wix/WixQA
- Dataset paper: https://arxiv.org/abs/2505.08643
- Analysis of another project: the owner's private notes in `personal-notes/` (not in the repository)
