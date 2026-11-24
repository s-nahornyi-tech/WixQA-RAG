# Implementation Plan: Corpus and audit

**Branch**: `001-corpus-and-audit` | **Date**: 2026-11-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-corpus-and-audit/spec.md`

## Summary

The feature gives the study its data, its first index, and the audit that Principle I of the constitution requires. An operator fetches `Wix/WixQA` at the pinned revision, builds an index from the corpus, and audits the index against the dataset; the audit ends as passed, failed or not carried out, and names every id that differs.

The technical approach:

- **Four commands** in one Python package: `python -m wixqa_rag dataset fetch`, `dataset check`, `index build` and `index audit`. Their output and exit codes are fixed in [contracts/cli.md](contracts/cli.md).
- **Dataset**: the four published files are downloaded at the commit hash recorded in `dataset.json`. A manifest next to the files records the row count and the SHA-256 of each one.
- **Index**: each article is split into passages by one rule defined on lines and characters, each passage is embedded with OpenAI `text-embedding-3-small`, and the passages are stored in PostgreSQL with pgvector, one schema per index. A build is one database transaction, so an index is either complete or absent. Every build leaves a build record with its settings, its token count and its cost.
- **Audit**: the article ids are read from the table that retrieval will query and are compared with the corpus and with the `article_ids` of every question. Later specs call the same audit as a gate ([contracts/audit-gate.md](contracts/audit-gate.md)).
- **Where it runs**: on GitHub Actions, as the owner decided on 2026-11-24. The PostgreSQL of a job lives only for that job, so the index built from the pinned dataset is kept as a database dump attached to a GitHub release; each later job restores it and audits it before use.
- **Tooling**: Python 3.14, uv with a lock file, pytest, GitHub Actions. This resolves `TODO(PYTHON_TOOLING)` of the constitution.

The reasons for each choice, and the alternatives, are in [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: `openai` (the embedding provider's library) and `psycopg` 3 (the PostgreSQL driver). Everything else comes from the Python standard library. Development: pytest and Ruff. Environment and lock file: uv.

**Storage**: PostgreSQL 18 with the pgvector extension, one schema per index, in a service container that lives for one CI job. The index built from the pinned dataset is kept between jobs as a `pg_dump` file attached to a GitHub release. Files: `data/`, outside version control, holds the fetched dataset and the records of indexes built from example data; `evals/indexes/`, in version control, holds the records of an index built from the pinned dataset.

**Testing**: pytest. Acceptance tests run the command lines of the spec unchanged; integration tests run against PostgreSQL with an embedder double; unit tests need nothing. Three markers, `store`, `provider` and `real_data`, select what a run may use (research.md, section 3).

**Target Platform**: Linux, on the GitHub-hosted runner `ubuntu-24.04`. Commands are typed in a POSIX shell.

**Project Type**: cli: one Python package with a command-line entry point.

**Performance Goals**: The study operates no service, so there is no latency or throughput target. Working limits: the full build and its audit finish within one CI job of at most 60 minutes at the provider's usage tier 1; the example scope finishes within 5 minutes; an audit of the real index takes less than a minute.

**Constraints**:

- The agents' workspaces reach neither the dataset host nor the embedding provider. Every test that needs one of them runs on GitHub Actions.
- A run that calls the provider starts only when a person starts it.
- Exit code 1 means only "a difference was found". Every other failure, an unexpected error included, ends with exit code 2.
- The provider accepts at most 8,192 tokens per input, 2,048 inputs per request and 300,000 tokens per request. The passage size and the request size respect these limits by arithmetic, without a tokenizer (research.md, sections 12 and 13).
- No command changes a dataset file. No credential appears in the repository, in a record or in the output of a command.
- The repository is private, and the Free plan includes 2,000 Actions minutes a month.

**Scale/Scope**: 6,221 articles in one file of 53.7 MB and 6,621 questions in three files. Estimated, not measured: 25 to 30 thousand passages, 10 to 14 million tokens and 0.20 to 0.28 US dollars for one build of the index; the build record of the first build states the real numbers. Four commands, 17 functional requirements, 14 acceptance checks.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Rule of the constitution | Applies | How this plan meets it |
|---|---|---|
| I. Index Audit | Yes: this feature implements it | The audit reads the article ids from the `passages` table of the index, the table that retrieval will query, through the one module that holds all SQL. It compares them with the corpus ids and with the `article_ids` of every question. Until the golden set exists the question set is every question, which includes every question a golden set can contain. Any difference ends the audit as failed, and the result is written as JSON |
| II. Article-level metrics | Not yet: nothing is retrieved | Every passage stores the `id` of its article, so a retrieved passage can be mapped to its article |
| III. Fixed golden set | Not yet: spec 2 | The audit takes its question set as an argument, so the golden set can be passed in without a change to the audit |
| IV, V. Labels and judge | No | — |
| VI. One change, one run | No run yet | The settings of a build are stored next to its result, in the build record. Two builds with different settings cannot share an identifier |
| VII. Failures are separate | In spirit | An audit that could not be completed is "not carried out"; it is never counted as failed or passed, and it has its own exit code |
| VIII. Breakdowns | No | — |
| IX. Cost and latency | For the index | The build record states the tokens embedded, the price used and the cost in US dollars ("Metric Definitions", Cost: building an index is recorded with its own cost) |
| X. Evidence before decisions | Yes | The embedding model, the vector store and the splitting rule are recorded as chosen as a starting point, with no run. The plan states no quality target. Tooling choices do not change what the pipeline retrieves or answers |
| Scope and non-goals | Yes | No service is operated. The dataset is never edited (FR-005). The code serves one dataset, one provider and one store; it has no plug-in layer |
| Stack: pinned revision | Yes | `dataset.json` holds a full commit hash; every command reads it |
| Stack: most specific model identifier | Yes | The build record stores the model name as requested and as the provider reports it |
| Stack: lock file | Yes | `uv.lock` is committed; CI installs with `uv sync --locked` |
| Stack: secrets | Yes | Settings are read from the environment only and are never printed. The provider key is a repository secret. The job's database has no password, so none exists to commit |
| Stack: `TODO(PYTHON_TOOLING)` | Resolved here | Python 3.14, uv, pytest, GitHub Actions. The amendment that records them (version 1.1.0) is a task of this feature and becomes binding when the owner merges the pull request |
| Workflow: approved spec | Yes | The owner approved the spec on 2026-11-24 |
| Workflow: tests first | Yes | The testing agent writes the acceptance tests before the implementation; a CI run shows that they fail; the coding agent does not change them |
| Workflow: evaluation run | No | No pipeline exists yet, so this feature cannot change what a pipeline retrieves or answers: `Run: none` |
| Workflow: one branch, one pull request | Yes | One pull request from `001-corpus-and-audit`, squash-merged by the owner. The acceptance workflow adds one commit with three record files to the branch; it never writes to `main` |
| Workflow: no link to a private agent session | Yes | The commit that the workflow adds names the identifier of the workflow run and nothing else |
| Public texts | Yes | The README's status line changes in the same pull request, and only to what the repository then contains |
| Governance: amendments | Yes | The amendment updates the version and the date and changes `PROJECT.md` in the same pull request |

**Result before research**: pass. No rule is violated, and nothing needs a justification under "Complexity Tracking".

**Result after design**: pass. The design adds two things that the spec does not name, the snapshot of an index and the label that starts a run; both follow from the owner's decision to run on GitHub Actions and conflict with no rule above.

## Project Structure

### Documentation (this feature)

```text
specs/001-corpus-and-audit/
├── spec.md              # The specification, approved by the owner
├── plan.md              # This file
├── research.md          # Each choice with its reasons and alternatives; facts checked
├── data-model.md        # Entities, rules, the layout of an index in the store
├── quickstart.md        # How to see that the feature works, on GitHub and on a computer
├── contracts/
│   ├── cli.md           # The four commands: arguments, output lines, exit codes
│   ├── records.md       # The JSON files the commands read and write
│   └── audit-gate.md    # The call that later specs make before they retrieve
├── checklists/
│   └── requirements.md  # Quality checklist of the spec
└── tasks.md             # Created by /speckit-tasks, not by this plan
```

### Source Code (repository root)

```text
.github/
└── workflows/
    ├── checks.yml          # Every pull request: lint, format, tests that need no secret
    └── acceptance.yml      # Started by hand, scope example or full, with the provider key
dataset.json                # The pinned revision of Wix/WixQA and the row count of each part
pyproject.toml              # Project, dependencies, settings of pytest and Ruff
uv.lock                     # The lock file
.python-version             # 3.14
.env.example                # The names of the two settings, without values
.gitattributes              # Adds: the example data keeps its bytes on every platform

src/
└── wixqa_rag/
    ├── __init__.py
    ├── __main__.py         # python -m wixqa_rag
    ├── cli.py              # Arguments, output lines, exit codes
    ├── settings.py         # Paths and settings read from the environment
    ├── dataset.py          # Pinned revision, manifest, fetch, check, reading the parts
    ├── splitting.py        # The splitting rule line-pack-v1
    ├── embedding.py        # Calls to the embedding provider, token counts, price
    ├── store.py            # Every SQL statement: schema, build transaction, article ids
    ├── index.py            # The build and its record
    └── audit.py            # The audit, its result, the gate for later specs

tests/
├── acceptance/             # One test per acceptance check, AC-001 to AC-014
├── integration/            # Build and audit against PostgreSQL, with an embedder double
├── unit/                   # Splitting rule, dataset check, records, output, exit codes
└── data/
    ├── example/
    ├── example-damaged/
    ├── example-one-more-article/
    ├── example-one-less-article/
    └── example-unknown-reference/

evals/
└── indexes/
    └── wixqa-001/          # Written by the first full run on GitHub Actions
        ├── build.json      # The build record
        ├── audit.json      # The audit made right after the build
        └── snapshot.json   # Where the dump of the index is kept, and its fingerprint

data/                       # Outside version control
├── wixqa/<revision>/       # The fetched dataset and its manifest
├── indexes/<index>/        # Build records of indexes built from example data
└── audits/<index>/         # Audit results written without --json
```

**Structure Decision**: One project with a `src` layout: the package `src/wixqa_rag/`, tests under `tests/` sorted by kind, and records under `evals/`. The folders `src/`, `tests/`, `evals/` and `data/` already exist in the repository and keep the meaning the README gives them. `evals/indexes/` is new; the README and `evals/README.md` each get a line for it, and for `dataset.json`, when the files are added. The modules follow the entities of [data-model.md](data-model.md): one module per concern, and `store.py` as the only place that talks to PostgreSQL, so that the audit and the later retrieval read the same table through the same code.

## Where the commands run

| Workflow | Starts | Uses | Runs |
|---|---|---|---|
| `checks.yml` | By itself, for every pull request and every push to `main` | PostgreSQL; no secret | Ruff, then the tests that need neither the provider nor the dataset host |
| `acceptance.yml`, scope `example` | When a person starts it: the label `acceptance:example` on the pull request, or "Run workflow" | PostgreSQL and `OPENAI_API_KEY` | Every test except those that need the published dataset |
| `acceptance.yml`, scope `full` | When a person starts it: the label `acceptance:full`, or "Run workflow" | PostgreSQL, `OPENAI_API_KEY` and the dataset host | Restores the snapshots listed under `evals/indexes/`, runs every test, and after the first build of an index records it and saves its snapshot |

The steps that record an index run only when every test of the `full` scope has passed, so a record and a snapshot are published only for an index that was audited with zero mismatches. Details: research.md, sections 4, 6 and 7.

## How the work is delivered

One pull request from the branch `001-corpus-and-audit`, opened as a draft when the implementation starts, so that the workflows have a pull request to run for.

1. **Setup** (coding agent, DevOps agent): `pyproject.toml`, `uv.lock`, `.python-version`, `dataset.json`, the empty package, the two workflows, the constitution amendment and the two entries in `PROJECT.md`.
2. **Tests first** (testing agent): the example datasets, the fourteen acceptance tests, the integration and unit tests. A run of `checks` and a run of `acceptance` show them red.
3. **Implementation** (coding agent), story by story: dataset, index, audit. The acceptance tests are not changed.
4. **Green on example data**: `checks` and `acceptance` with the scope `example`.
5. **Review** (code review agent): the diff against the spec and the constitution.
6. **The real index, last**: `acceptance` with the scope `full`. It builds `wixqa-001`, audits it, commits the three record files and creates the release with the snapshot.
7. **Texts**: the README's status line and tables, `evals/README.md`.
8. **Merge**: the owner squash-merges. The description ends with `Spec: specs/001-corpus-and-audit`, `Closes #3` and `Run: none`.

The real index is built last on purpose: its record names the commit of the code, and a snapshot made from code that then changes would have to be made again under a new identifier.

Step 7 follows step 6 for a second reason. GitHub starts no workflow for a commit that a job pushes with its own token, so the commit with the record files gets no run of `checks`. The commit of step 7 is pushed by an agent, and `checks` then runs on the final state of the branch.

## Requirement coverage

| Requirement | Met by | Checked by |
|---|---|---|
| FR-001 | `dataset.json`, read by `dataset.py` | AC-001 |
| FR-002 | `dataset fetch` | AC-001; unit tests for a differing row count and a failed download |
| FR-003 | `manifest.json` with SHA-256; a fetch over a matching copy | AC-001 |
| FR-004 | `dataset check` | AC-002, AC-003; a unit test for each kind of difference |
| FR-005 | No command writes to a part file | AC-013; a test that the fingerprints are unchanged after a build and an audit |
| FR-006 | Step 2 of `index build`; model and store fixed in the code | AC-004, AC-007 |
| FR-007 | `splitting.py`; the column `article_id` of `passages` | AC-004; unit tests that pin the output of the rule |
| FR-008 | The decision table of research.md, section 15 | AC-005, AC-006; integration tests for each row of the table |
| FR-009 | One transaction; the `build` row as the mark of completion | AC-012; integration tests for a build that stops and for a schema without its `build` row |
| FR-010 | `index.py`, the build record | AC-004; a test of every field |
| FR-011 | `store.py`: the audit reads `passages` | AC-008 to AC-011 |
| FR-012 | `audit.py`: the two id lists | AC-009, AC-010 |
| FR-013 | `audit.py`: the pairs of question and id | AC-011; unit tests for an empty list and for an id named twice |
| FR-014 | Three outcomes, three exit codes | AC-008 to AC-012 |
| FR-015 | The audit result as JSON | AC-013 |
| FR-016 | `require_passed_audit` | AC-008, AC-012; integration tests of the gate |
| FR-017 | `settings.py`; values are never printed or recorded | AC-014; a test that no output and no record contains the value of a setting |
| SC-001 | The audit of `wixqa-001` | AC-008 |
| SC-002 | The fetch | AC-001 |
| SC-003 | The three altered example datasets | AC-009, AC-010, AC-011 |
| SC-004 | A second build, a second audit | AC-005, AC-013 |
| SC-005 | `cost_usd` in the build record | AC-004 |

The six edge cases of the spec are covered by unit and integration tests: a download that fails, a row count that differs, an article without text, a question without `article_ids`, an article named twice by one question, and a missing setting.

## Points the spec leaves open

The spec is silent on the points below. The plan reads them as follows, in each case in the direction of the requirement named. If the owner or the code review agent reads one of them differently, the spec is amended first (constitution, "Development Workflow").

1. **Where the store runs and how long it lives.** The spec assumes access to a vector store. Here the store lives for one job, and the index is carried between jobs as a snapshot (research.md, sections 6 and 7).
2. **A build record exists, and the store does not hold the index.** The build is refused, because a record is written once (FR-010).
3. **A build that stops part-way.** It leaves nothing in the store, so the audit reports the identifier as not existing. An index without its mark of completion can exist only when it was made by hand; the audit reports it as not complete (User Story 2, scenario 5; FR-009).
4. **How a question is named.** The data has no question identifier. Until spec 2 fixes one, a question is named by its part and its row number (research.md, section 14).
5. **The parts of an example dataset.** An example has one corpus part and one question part; the parts of any dataset are read from its manifest (research.md, section 11).
6. **When the provider key is needed.** Only when passages have to be embedded. An index that is already complete is reported without the key (FR-008, FR-017).
7. **Where an audit result goes without `--json`.** To `data/audits/<index>/<time>.json` (FR-015).
8. **A dataset check without a local copy.** It is not carried out, with the advice to fetch first; it is not reported as failed (FR-004).

## The owner's part

1. Before the first run that calls the provider: add the repository secret `OPENAI_API_KEY`. For the full build the account with the provider has to be at usage tier 1, which the provider grants after 5 US dollars have been paid.
2. Start a run when an agent cannot: one label on the pull request.
3. Merge the pull request. The merge also approves the constitution amendment (version 1.1.0) and the two new entries under "Decided" in `PROJECT.md`.

Expected spending, estimated: 0.20 to 0.28 US dollars for the one build of the real index, and less than one cent for all runs on example data. Nothing is installed on the owner's computer.

## Risks

| Risk | What happens | What is done |
|---|---|---|
| A path or a row count at the pinned revision differs from `dataset.json` | The fetch stops and names the path, or both numbers | The finding is recorded, `PROJECT.md` and `dataset.json` are corrected, and the spec is amended with the owner's approval (spec, "Assumptions") |
| The real data has an article without text, or a question that names an article outside the corpus | The audit of the real index fails and names the ids; AC-008 stays red | The finding is recorded and the owner decides; the data stays as published (spec, "Assumptions") |
| The provider account is below usage tier 1 | The full build is slow and may exceed the time limit of the job; the build is rolled back, and nothing is recorded | The owner raises the tier, and the run is started again |
| An agent cannot start a run or read its log through the REST API | The agent cannot go on by itself | The owner starts the run; the result is read from the run, its steps and its annotations |
| The record files cannot be committed, or the release cannot be created, after a paid build | The index would be lost with the job | The workflow first saves the dump and the three files as a short-lived artifact, so they can be recovered by hand |
| The code that splits or embeds changes after `wixqa-001` was recorded | The record would no longer describe what the code does | The real index is built last; a change of the rule's output requires a new rule name and a new index identifier |

## Complexity Tracking

No rule of the constitution is violated, so this table is not needed.
