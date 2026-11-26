---

description: "Task list of spec 001, corpus and audit"
---

# Tasks: Corpus and audit

**Input**: Design documents from `/specs/001-corpus-and-audit/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: REQUIRED for every feature of this project (constitution, "Development Workflow"). In every user story the tests come first: the testing agent writes one acceptance test for each check in the "Acceptance Checks" of spec.md, and the tests MUST fail before any implementation task of that story starts. The coding agent MUST NOT change an acceptance test; a test that is wrong goes back to the testing agent.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Roles**: Tasks under a "Tests" heading belong to the testing agent, CI/CD tasks to the DevOps agent, and all other tasks to the coding agent. The code review agent checks the pull request's diff against spec.md and the constitution; that check is not a task in this list. T007 and T008 change the constitution and `PROJECT.md`; they belong to the spec agent.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are in the descriptions

## Path Conventions

Single project: the package in `src/wixqa_rag/`, tests in `tests/`, workflows in `.github/workflows/`, records in `evals/indexes/`. The full tree is in plan.md, "Project Structure".

## How the tests are run

| Tier | What it runs | Where | How it starts |
|---|---|---|---|
| workspace | The tests without a marker | The agent's workspace | By the agent: `uv run pytest -m "not store and not provider and not real_data"` |
| `checks` | Also the tests marked `store` | GitHub Actions, with PostgreSQL | By itself, for every push to the pull request |
| `acceptance`, scope `example` | Also the tests marked `provider` | GitHub Actions, with PostgreSQL and the provider key | By hand: the label `acceptance:example` on the pull request |
| `acceptance`, scope `full` | Every test | GitHub Actions, with PostgreSQL, the provider key and the dataset host | By hand: the label `acceptance:full` on the pull request |

- A run on GitHub Actions is confirmed by its conclusion, the conclusions of its steps and its annotations, read on the page of the run or through the REST API of the repository.
- A run that can call the embedding provider starts only with the owner's go-ahead. One go-ahead covers the runs with the scope `example`: each embeds the example dataset, a few hundred tokens. The run of T067 needs a go-ahead of its own, because it builds the real index.
- The scope `full` is not started between T047 and T067. Once the command `index build` exists, that scope builds the real index, and before T063 nothing would record it.
- The four real-data acceptance tests (AC-001, AC-002, AC-004, AC-008) have no fixture that fetches or builds. In one run they execute in the order of their numbers, and each relies on what the one before it left, as the checks of the spec do: AC-002 on the fetch of AC-001, AC-008 on the index that AC-004 built or that the workflow restored.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: The tooling, the pinned dataset, the two workflows and the pull request they run for

- [x] T001 Create `pyproject.toml` and `.python-version`: the project `wixqa-rag` with its package in `src/wixqa_rag/`, `requires-python = ">=3.14,<3.15"`, the dependencies `openai` and `psycopg[binary]`, a development group with `pytest` and `ruff`, the build backend `uv_build`, the range of uv versions, the pytest settings (test paths, strict markers, the markers `store`, `provider` and `real_data`) and the Ruff settings (research.md, sections 1, 2, 3 and 5)
- [x] T002 Create the empty package `src/wixqa_rag/__init__.py`, so that the project can be installed; it holds no behaviour
- [x] T003 Create `uv.lock` with `uv lock` and confirm that `uv sync --locked` builds the environment on Python 3.14 (depends on T001 and T002)
- [x] T004 [P] Create `dataset.json` at the repository root with the pinned revision and the four parts (contracts/records.md, "`dataset.json`"; data-model.md, "Pinned revision": `revision` is a full commit hash, and exactly one entry of `parts` has the role `corpus`)
- [x] T005 [P] Create `.env.example` with the names `DATABASE_URL` and `OPENAI_API_KEY` and no values (contracts/cli.md, "Settings")
- [x] T006 [P] Add to `.gitattributes` the rule that keeps every file under `tests/data/` free of line-ending conversion (research.md, section 11)
- [x] T007 [P] Amend `.specify/memory/constitution.md`: replace the `TODO(PYTHON_TOOLING)` line with the tooling of the plan, set the version to 1.1.0 and "Last Amended" to the day of the change (research.md, "Constitution amendment that this plan leads to")
- [x] T008 [P] Update `PROJECT.md` for the same amendment: add the two entries under "Decided", the tooling and where the commands run, and change its two mentions of the constitution's version to 1.1.0 (research.md, same section)

### CI/CD (DevOps agent)

- [x] T009 Create `.github/workflows/checks.yml`: it starts for every pull request and every push to `main`, uses no secret, runs on `ubuntu-24.04` with PostgreSQL and pgvector as a service container that needs no password, installs with `uv sync --locked`, runs `ruff check`, `ruff format --check` and the `checks` tier of tests with `DATABASE_URL` set, publishes every failed test as an annotation, made from pytest's JUnit report by a step of the workflow and without a further dependency, and fails when the tests added or changed a file outside the ignored folders; every action is pinned to a full commit SHA and the image to a tag and a digest (research.md, sections 3 to 6)
- [x] T010 Create `.github/workflows/acceptance.yml`: it starts only by `workflow_dispatch` with the input `scope` or by the label `acceptance:example` or `acceptance:full` on a pull request, through the `pull_request` event; it checks out the head of the branch, receives `OPENAI_API_KEY` from the repository's secrets, has a time limit of 60 minutes and never runs twice at the same time for one branch; it runs the tests of its scope, publishes failed tests as annotations and the verdict lines of the real-data commands as notices, fails when the tests added or changed a file outside the ignored folders, and removes its label from the pull request when it finishes, so that adding the label again starts the next run. In the scope `full`, the build record of a newly built index under `evals/indexes/` is the one file that may appear (research.md, sections 3, 4 and 6)
- [x] T011 Create the labels `acceptance:example` and `acceptance:full` in the repository, and open the pull request from `001-corpus-and-audit` to `main` as a draft, with a title in the form the constitution requires and a description that ends with `Spec: specs/001-corpus-and-audit`, `Closes #3` and `Run: none`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The example data, the test helper and the frame of the command line, which all three stories use

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for the foundation (written first by the testing agent) ⚠️

- [x] T012 [P] Create the five example data directories `tests/data/example/`, `tests/data/example-damaged/`, `tests/data/example-one-more-article/`, `tests/data/example-one-less-article/` and `tests/data/example-unknown-reference/`, each with `ex.jsonl`, `exq.jsonl` and `manifest.json` (data-model.md, "Example datasets", "Article" and "Question"; contracts/records.md, "`manifest.json`")
- [x] T013 [P] Unit test in `tests/unit/test_example_data.py`: for every example directory, the row count, the size and the SHA-256 in `manifest.json` equal those of the files. The test computes them itself and uses no code of the package
- [x] T014 [P] Test helper in `tests/conftest.py` that runs a command line exactly as the spec writes it, through a POSIX shell at the repository root, and returns the exit code and the standard output
- [x] T015 [P] Unit tests in `tests/unit/test_cli_frame.py` for the rules of contracts/cli.md, "General rules": wrong arguments end with exit code 2; an error that the program did not expect ends with exit code 2, a `reason:` line and the verdict `not carried out` as the last line of standard output, and never with exit code 1; a command typed where no `dataset.json` exists is not carried out
- [x] T016 [P] Unit tests in `tests/unit/test_settings.py`: a missing setting is reported by its variable name; the value of a setting never appears in a message; the default places of data-model.md ("Data directory", "Build record", "Audit result") are derived from `dataset.json` and the index identifier
- [x] T017 Run the workspace tier and confirm that the tests of T015 and T016 fail because the code is missing and that the test of T013 passes, since it tests the data; then confirm the same in the run of `checks` for the pull request, whose setup, lint and format steps pass

**Checkpoint (red)**: The tests of the foundation exist, and those that test code fail. This is also the first run of `checks`

### Implementation of the foundation

- [x] T018 [P] Implement `src/wixqa_rag/settings.py`: the repository root, the default data directory, the places of the records, and the two settings read from the environment (contracts/cli.md, "Settings"; data-model.md, "Data directory", "Build record", "Audit result")
- [x] T019 Implement the frame of the command line in `src/wixqa_rag/cli.py` and `src/wixqa_rag/__main__.py`: the groups `dataset` and `index`, still without commands; result lines to standard output and progress to standard error; the `difference:` and `reason:` lines; the verdict line last; every outcome mapped to the exit codes 0, 1 and 2 (contracts/cli.md, "General rules")
- [x] T020 Run the tests of the foundation and confirm that each passes, with no test changed; the run of `checks` is green

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Fetch the dataset at the pinned revision (Priority: P1) 🎯 MVP

**Goal**: The operator fetches `Wix/WixQA` at the pinned revision and gets the same data as every other operator; a check tells whether the local copy still matches what was fetched

**Independent Test**: On a checkout without downloaded data, run the fetch and then the check. The fetch reports the pinned revision and the row count of each part, and the check passes

### Tests for User Story 1 (REQUIRED - written first by the testing agent) ⚠️

> **NOTE: Write these tests FIRST, one for each check of spec.md that covers this story. They MUST FAIL before implementation starts**

- [x] T021 [P] [US1] Acceptance test for check AC-001 in `tests/acceptance/test_ac_001_dataset_fetch.py` (marker `real_data`)
- [x] T022 [P] [US1] Acceptance test for check AC-002 in `tests/acceptance/test_ac_002_dataset_check.py` (marker `real_data`)
- [x] T023 [P] [US1] Acceptance test for check AC-003 in `tests/acceptance/test_ac_003_dataset_check_damaged.py` (no marker)
- [x] T024 [P] [US1] Unit tests in `tests/unit/test_dataset_check.py`: one test for each of the differences 1 to 8 of data-model.md, "Data directory", each made on a temporary copy of `tests/data/example/`; a directory without `manifest.json` is not carried out; a `dataset.json` or a manifest that breaks a rule of data-model.md, "Pinned revision" (`revision` is not a full commit hash, no entry or several entries of `parts` have the role `corpus`, a part name is used twice), is not carried out; an empty `contents` and an empty `article_ids` list are not differences (data-model.md, `Article.contents`, `Question.article_ids`)
- [x] T025 [P] [US1] Unit tests in `tests/unit/test_dataset_fetch.py`, with a download double passed to the fetch: a complete, matching copy downloads nothing; a row count that differs from `dataset.json` ends as failed, names both numbers and leaves the local copy as it was; a download that fails ends as not carried out and leaves the local copy as it was; the manifest is written last; the stored files have the bytes that were downloaded (spec.md, edge cases 1 and 2; FR-002, FR-003, FR-005)
- [x] T026 [US1] Run the tests of User Story 1 and confirm that each fails because the behaviour is missing: the workspace tier for T023 to T025, then `checks`, then `acceptance` with the scope `full` for T021 and T022. This run cannot call the provider, because no command exists that embeds

**Checkpoint (red)**: Every test of User Story 1 exists and fails. No implementation task of this story starts before this point

### Implementation for User Story 1

- [x] T027 [US1] Implement in `src/wixqa_rag/dataset.py` the reading of `dataset.json`, of `manifest.json` and of the parts, with the rules of both files checked when they are read (data-model.md, "Pinned revision": `revision`, `parts`; "Part"; "Data directory": the manifest; `Article.id`, `Article.url`, `Article.contents`, `Article.article_type`, `Question.question`, `Question.answer`, `Question.article_ids`; contracts/records.md)
- [x] T028 [US1] Implement the dataset check in `src/wixqa_rag/dataset.py`: the differences 1 to 8 of data-model.md, "Data directory", every difference reported, and "not carried out" for a directory without a manifest
- [x] T029 [US1] Implement the fetch in `src/wixqa_rag/dataset.py`, with the download function as a parameter: temporary names, row counts compared with `dataset.json`, SHA-256, files moved into place, the manifest written last, and nothing downloaded over a complete, matching copy (data-model.md, "Data directory": the manifest and its fields; research.md, section 9; contracts/cli.md, "`dataset fetch`")
- [x] T030 [US1] Add the commands `dataset fetch` and `dataset check` to `src/wixqa_rag/cli.py`, with the output lines, verdicts and exit codes of contracts/cli.md
- [x] T031 [US1] Run the tests of User Story 1 and confirm that each passes, with no acceptance test changed: the workspace tier, `checks`, and `acceptance` with the scope `full`. This is the first fetch of the published dataset: it confirms the two paths and the four row counts that research.md lists under "Not checked". If the fetch stops on a path or on a count, record the finding and stop here (plan.md, "Risks")

**Checkpoint (green)**: The tests of User Story 1 pass unchanged. User Story 1 is fully functional and can be accepted on its own

---

## Phase 4: User Story 2 - Build the index from the corpus (Priority: P2)

**Goal**: The operator builds the retrieval index from the fetched corpus: one splitting rule, every passage stored with the `id` of its article, and a build record that tells how to repeat the build and what it cost

**Independent Test**: Build an index from the small example corpus and read the report: it gives the number of example articles and marks the index complete. Build again under the same identifier: nothing is embedded a second time

### Tests for User Story 2 (REQUIRED - written first by the testing agent) ⚠️

- [x] T032 [P] [US2] Acceptance test for check AC-004 in `tests/acceptance/test_ac_004_index_build_real.py` (markers `real_data`, `store`, `provider`); the test sets no time limit shorter than that of the job, since the first build takes many minutes
- [x] T033 [P] [US2] Acceptance test for check AC-005 in `tests/acceptance/test_ac_005_index_build_twice.py` (markers `store`, `provider`)
- [x] T034 [P] [US2] Acceptance test for check AC-006 in `tests/acceptance/test_ac_006_index_build_other_corpus.py` (markers `store`, `provider`)
- [x] T035 [P] [US2] Acceptance test for check AC-007 in `tests/acceptance/test_ac_007_index_build_damaged.py` (no marker)
- [x] T036 [P] [US2] Acceptance test for check AC-014 in `tests/acceptance/test_ac_014_index_build_without_key.py` (marker `store`)
- [x] T037 [P] [US2] Unit tests in `tests/unit/test_splitting.py`: fixed inputs with their exact passages for each step of the rule `line-pack-v1` (research.md, section 12), within the limits of data-model.md, `Passage.text` and `Passage.passage_no`; a text without a non-empty line gives no passage; the same text always gives the same passages
- [x] T038 [P] [US2] Unit tests in `tests/unit/test_embedding.py`, with a double in place of the provider's client: a request carries at most 96 passages and at most 75,000 characters; the tokens embedded are the sum of the usage that the provider reports; the cost follows data-model.md, "Build record" (`cost_usd`); the model name is kept as requested and as reported (research.md, section 13)
- [x] T039 [P] [US2] Fixtures in `tests/integration/conftest.py`: a connection to the store from `DATABASE_URL`; an embedder double that returns fixed vectors of 1536 numbers and reports the model name `embedder-double`; the removal of every schema that a test created; a temporary repository root with a `dataset.json` and a default data directory of its own, used by every test that builds without `--data-dir`, so that no test writes under `evals/` of the checkout (research.md, section 17)
- [x] T040 [P] [US2] Integration tests in `tests/integration/test_index_build.py` (marker `store`): a build stores at least one passage for every article with text, each with the `id` of its article (data-model.md, `Passage.article_id`), and writes the `build` row last; a build that stops in the middle leaves no schema; every row of the decision table in research.md, section 15; an identifier that breaks the rule of data-model.md, "Index" (Identifier), is not carried out; an article without text is listed under "articles without passages" and is not in the index; without `DATABASE_URL` the build is not carried out and names the variable; the fingerprints of the data files are the same after a build (FR-005)
- [x] T041 [P] [US2] Integration tests in `tests/integration/test_build_record.py` (marker `store`): every field of contracts/records.md, "`build.json`"; the place of the file with and without `--data-dir`, tried in the temporary repository root of T039; the record in the store equals the file; neither the record nor the output of a build contains the value of a setting (FR-010, FR-017)
- [x] T042 [US2] Run the tests of User Story 2 and confirm that each fails because the behaviour is missing: the workspace tier for T035, T037 and T038, then `checks` for T036 and T039 to T041, then `acceptance` with the scope `full` for T032 to T034. This run cannot call the provider, because the command that embeds does not exist yet

**Checkpoint (red)**: Every test of User Story 2 exists and fails. No implementation task of this story starts before this point

### Implementation for User Story 2

- [x] T043 [P] [US2] Implement the rule `line-pack-v1` in `src/wixqa_rag/splitting.py` (research.md, section 12; data-model.md, `Passage.text`, `Passage.passage_no`)
- [x] T044 [P] [US2] Implement the embedder in `src/wixqa_rag/embedding.py`: the model, the limits of a request, the retries, the token count, and the price with the date on which it was read (research.md, section 13); the cost follows data-model.md, "Build record" (`cost_usd`)
- [x] T045 [P] [US2] Implement in `src/wixqa_rag/store.py` the connection, the pgvector extension, the rule for an identifier and its schema name (data-model.md, "Index", Identifier), the two tables (data-model.md, `Passage.article_id`, `Passage.passage_no`, `Passage.text`, `Passage.embedding`, and the `build` table of "Index"), the insertion of the passages and of the `build` row, and the lookup of an index with its record. Every SQL statement of the project lives in this file
- [x] T046 [US2] Implement the build in `src/wixqa_rag/index.py`, with the embedder as a parameter: the order of steps of contracts/cli.md, "`index build`"; the decision table of research.md, section 15; one transaction; the build record written under a temporary name before the commit and given its final name after it (data-model.md, "Build record": `articles`, `articles_without_passages`, `cost_usd`; contracts/records.md, "`build.json`") (depends on T043, T044 and T045)
- [x] T047 [US2] Add the command `index build` to `src/wixqa_rag/cli.py`, with the output lines, verdicts and exit codes of contracts/cli.md
- [x] T048 [US2] Run the tests of User Story 2 and confirm that each passes, with no acceptance test changed: the workspace tier, `checks`, and `acceptance` with the scope `example`, which is the first run that calls the provider. AC-004 is not part of this scope; it is confirmed in T067, because the real index is built last (plan.md, "How the work is delivered")

**Checkpoint (green)**: The tests of User Stories 1 and 2 pass unchanged on the example data. AC-004 waits for the last phase

---

## Phase 5: User Story 3 - Audit the index against the dataset (Priority: P3)

**Goal**: Before anything is retrieved from an index, the operator audits it: the audit asks the index itself which articles it holds, compares the answer with the dataset, and names every id that differs

**Independent Test**: Audit an index built from the small example against the same example: the audit passes. Audit it against the three altered examples, each with one known difference: the audit fails each time and names exactly that difference

### Tests for User Story 3 (REQUIRED - written first by the testing agent) ⚠️

- [x] T049 [P] [US3] Acceptance test for check AC-008 in `tests/acceptance/test_ac_008_index_audit_real.py` (markers `real_data`, `store`)
- [x] T050 [P] [US3] Acceptance test for check AC-009 in `tests/acceptance/test_ac_009_audit_missing_from_index.py` (markers `store`, `provider`)
- [x] T051 [P] [US3] Acceptance test for check AC-010 in `tests/acceptance/test_ac_010_audit_not_in_corpus.py` (markers `store`, `provider`)
- [x] T052 [P] [US3] Acceptance test for check AC-011 in `tests/acceptance/test_ac_011_audit_unknown_reference.py` (markers `store`, `provider`)
- [x] T053 [P] [US3] Acceptance test for check AC-012 in `tests/acceptance/test_ac_012_audit_unknown_index.py` (marker `store`)
- [x] T054 [P] [US3] Acceptance test for check AC-013 in `tests/acceptance/test_ac_013_audit_json_data_unchanged.py` (markers `store`, `provider`)
- [x] T055 [P] [US3] Unit tests in `tests/unit/test_audit_compare.py`, on plain sets and lists without a store: the definitions of data-model.md, "Audit result" (`missing_from_index`, `not_in_corpus`, `unknown_references`, `questions_without_article_ids`, `outcome`); an id that a question names twice counts once; a question without `article_ids` is counted and produces no pair; the lists are sorted; a question reference follows data-model.md, "Question"; the result converts to the JSON document of contracts/records.md, "Audit result", and back without loss
- [x] T056 [P] [US3] Integration tests in `tests/integration/test_index_audit.py` (marker `store`): the audit reads the article ids from the store, so that after the passages of one article are removed directly in the store the audit names that article as missing although no file changed (FR-011); an article without text, which the build left out, is named as missing from the index; a schema without its `build` row is not complete, and the audit is not carried out; an index that does not exist, a store that cannot be reached and a data directory that fails the dataset check each end as not carried out, with a reason and without a result file; `require_passed_audit` returns the result of a passed audit and raises `AuditNotPassed` for the two other outcomes; a caller's own question set replaces the question parts; the audit changes neither the store nor the data directory (contracts/audit-gate.md, rules 1 to 6)
- [x] T057 [US3] Run the tests of User Story 3 and confirm that each fails because the behaviour is missing: the workspace tier for T055, then `checks` for T053 and T056, then `acceptance` with the scope `example` for T050 to T052 and T054, which fail at the command `index audit` after the example index was built. Run the test of T049 alone in the workspace and confirm from its output that it fails because the command `index audit` does not exist; it is not run on GitHub Actions at this point (see "How the tests are run")

**Checkpoint (red)**: Every test of User Story 3 exists and fails. No implementation task of this story starts before this point

### Implementation for User Story 3

- [x] T058 [US3] Add to `src/wixqa_rag/store.py` the reading of the distinct article ids of an index, and the test whether an index exists and is complete (data-model.md, "Index": the `build` row is the mark of completion)
- [x] T059 [US3] Implement `src/wixqa_rag/audit.py`: `AuditOutcome`, `AuditResult`, `AuditNotPassed`, `audit_index` and `require_passed_audit` as contracts/audit-gate.md fixes them; the comparison of data-model.md, "Audit result" (`missing_from_index`, `not_in_corpus`, `unknown_references`, `questions_without_article_ids`, `outcome`); the question references of data-model.md, "Question"; the conversion to and from the JSON document of contracts/records.md (depends on T058)
- [x] T060 [US3] Add the command `index audit` to `src/wixqa_rag/cli.py`: the order of steps, the report, the result file at `--json` or at the default place, the verdicts and the exit codes (contracts/cli.md, "`index audit`")
- [x] T061 [US3] Run the tests of User Story 3 and confirm that each passes, with no acceptance test changed: the workspace tier, `checks`, and `acceptance` with the scope `example`. AC-008 is not part of this scope; it is confirmed in T067

**Checkpoint (green)**: All three stories work on the example data. Twelve of the fourteen checks pass on GitHub Actions: ten with the scope `example`, and AC-001 and AC-002 with the scope `full` in T031. AC-004 and AC-008 wait for the real index

---

## Phase 6: The Real Index, Polish & Cross-Cutting Concerns

**Purpose**: The snapshot of an index, the texts, and the one build of the real index

### CI/CD (DevOps agent)

- [x] T062 Add to `.github/workflows/acceptance.yml`, in the scope `example`, a round trip after the tests: dump the schema of the index `example` with the `pg_dump` inside the service container, restore it into a second database, and audit it there with exit code 0 (research.md, section 7). It shows on the planned versions, at no cost, that a snapshot can be restored
- [x] T063 Add to `.github/workflows/acceptance.yml`, in the scope `full`: before the tests, restore every snapshot named in `evals/indexes/*/snapshot.json`, after comparing its SHA-256; after the tests, and only when all of them passed and a new `evals/indexes/<index>/build.json` appeared, write `audit.json` with `index audit --json`, dump the index, save the dump and the two record files as an artifact kept for 7 days, create the release `index-<index>` with the dump, write `snapshot.json`, and commit and push the three files to the branch the run was started for. These steps never run for `main`: there the run stops with a message, because `main` changes only through pull requests (research.md, section 7; contracts/records.md, "`snapshot.json`"; data-model.md, "Snapshot record")
- [x] T064 Start `acceptance` with the scope `example` and confirm that the tests and the round trip of T062 pass

### Texts

- [x] T065 [P] Update `README.md`: how to set up the project's Python environment, which the commands of the spec assume; the rows for `dataset.json`, `evals/indexes/` and `.github/workflows/`; a pointer to `specs/001-corpus-and-audit/quickstart.md`. The status line stays as it is until T069
- [x] T066 [P] Add the row for `indexes/` to `evals/README.md`

**Checkpoint (review)**: Before T067 starts, the code review agent has checked the diff against spec.md and the constitution, and its findings are closed. The real index is built from the code as reviewed

### Acceptance and evidence (REQUIRED - last)

- [x] T067 Run every check of the "Acceptance Checks" of spec.md exactly as written and confirm the observable result of each: start `acceptance` with the scope `full`. It builds the real index once, at an estimated 0.20 to 0.28 US dollars, and needs the owner's go-ahead of its own. Nothing is pushed to the branch while this run is in progress, because the run pushes a commit itself. All fourteen acceptance tests pass, AC-004 and AC-008 for the first time
- [x] T068 Confirm what the run of T067 recorded: the commit with `evals/indexes/wixqa-001/build.json`, `audit.json` and `snapshot.json`, and the release `index-wixqa-001`; the audit has the outcome `passed` and three empty lists (SC-001); the build record states the tokens embedded and the cost (SC-005). If the audit failed, record the finding and stop: the owner decides (plan.md, "Risks")
- [x] T069 Update the status line of `README.md` to what the repository then contains, and push; `checks` runs on this commit and is green
- [x] T070 Start `acceptance` with the scope `full` a second time and confirm that the index is restored from its snapshot, that `index build` reports it as already complete with `tokens embedded: 0`, and that the audit passes again (SC-004; quickstart.md, part A, step 4)
- [x] T071 Mark the pull request as ready for review: its description states what was built, what was found, and the amendment of the constitution with its reason, and it ends with `Spec: specs/001-corpus-and-audit`, `Closes #3` and `Run: none`. Tell the owner that the squash commit takes the title and the description of the pull request (constitution, "Development Workflow"), while the repository's default offers the commit messages

> **NOTE: This feature cannot change what a pipeline retrieves or answers, because no pipeline exists yet. It has no task that records an evaluation run, and its pull request states `Run: none`**

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3 to 5)**: All depend on the Foundational phase, and they run in priority order (P1 → P2 → P3), because each one uses what the one before it built
- **The real index and polish (Phase 6)**: Depends on all three user stories being green on the example data

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Foundational (Phase 2). No dependency on another story
- **User Story 2 (P2)**: Starts after User Story 1. A build reads the corpus and runs the dataset check of User Story 1 (FR-006). It is tested on its own with the example data
- **User Story 3 (P3)**: Starts after User Story 2. An audit needs an index to audit. It is tested on its own with the example data

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- The modules of a story before the command that uses them
- The command before the run that confirms the story
- Story complete before moving to next priority

### Parallel Opportunities

- T004 to T008 in Setup, once T001 to T003 are done
- The test tasks marked [P] within one "Tests" block: each writes its own file
- T043, T044 and T045 in User Story 2: three modules that do not depend on each other
- T065 and T066 in Phase 6
- The three stories themselves do not run in parallel: each depends on the one before it

---

## Parallel Example: User Story 2

```bash
# Write all tests of User Story 2 together (each in its own file):
Task: "Acceptance test for check AC-005 in tests/acceptance/test_ac_005_index_build_twice.py"
Task: "Acceptance test for check AC-006 in tests/acceptance/test_ac_006_index_build_other_corpus.py"
Task: "Unit tests in tests/unit/test_splitting.py"
Task: "Integration tests in tests/integration/test_index_build.py"

# After the red checkpoint, implement the three independent modules together:
Task: "Implement the rule line-pack-v1 in src/wixqa_rag/splitting.py"
Task: "Implement the embedder in src/wixqa_rag/embedding.py"
Task: "Implement the store in src/wixqa_rag/store.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run the tests of User Story 1; they pass unchanged, and the published dataset has been fetched once at the pinned revision
5. User Story 1 can be accepted on its own, as the first slice

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → The dataset is fetched and checked (MVP!)
3. Add User Story 2 → Test independently → An index is built from the example data
4. Add User Story 3 → Test independently → The index is audited, and each kind of mismatch is caught
5. Phase 6 → The real index is built once, audited, recorded and kept as a snapshot
6. Each story adds value without breaking previous stories

### One Pull Request

All phases reach `main` through one pull request, opened as a draft in T011 and marked ready in T071. The owner squash-merges it; the merge also approves the amendment of T007 and T008.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Verify tests fail before implementing; the coding agent never changes an acceptance test
- Commit after each task or logical group
- Stop at any checkpoint to validate a story on its own
- The run that counts for a test marked `store`, `provider` or `real_data` is the one on GitHub Actions; an agent may also run the `store` tests in its workspace (research.md, section 3)
- Any finding about the published data (a path, a row count, an article without text, a reference outside the corpus) is recorded and goes to the owner; no task works around it
