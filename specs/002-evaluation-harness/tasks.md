---

description: "Task list of spec 002, evaluation harness"
---

# Tasks: Evaluation harness

**Input**: Design documents from `/specs/002-evaluation-harness/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: REQUIRED for every feature of this project (constitution, "Development Workflow"). In every user story the tests come first: the testing agent writes one acceptance test for each check in the "Acceptance Checks" of spec.md, and the tests MUST fail before any implementation task of that story starts. The coding agent MUST NOT change an acceptance test; a test that is wrong goes back to the testing agent.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. User Stories 2 and 3 share one phase, because a report is made only from a record that passes its check (FR-025; plan.md, "How the work is delivered").

**Roles**: Tasks under a "Tests" heading belong to the testing agent, tasks under a "CI/CD" heading to the DevOps agent, and all other tasks to the coding agent. The code review agent checks the diff against spec.md and the constitution at the two review checkpoints; that check is not a task in this list. A finding of a review is closed before the work goes on, and each fix has its test first: the testing agent writes or corrects the test, a run shows it red, and then the coding agent changes the code. The tick boxes of this list are kept by the orchestrator.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths are in the descriptions

## Path Conventions

Single project: the package in `src/wixqa_rag/`, tests in `tests/`, workflows in `.github/workflows/`, question sets in `evals/golden/`, the run registry in `evals/runs/`. The full tree is in plan.md, "Project Structure". The acceptance tests of this feature are named `tests/acceptance/test_s2_ac_NNN_<words>.py` (research.md, section 12).

## How the tests are run

| Tier | What it runs | Where | How it starts |
|---|---|---|---|
| workspace | The tests without a marker | The agent's workspace | By the agent: `uv run pytest -m "not store and not provider and not real_data"` |
| `checks` | Also the tests marked `store` | GitHub Actions, with PostgreSQL | By itself, for every push to the pull request |
| `acceptance`, scope `example` | Also the tests marked `provider` | GitHub Actions, with PostgreSQL and the provider key | By hand: the label `acceptance:example` on the pull request |
| `acceptance`, scope `full` | Every test | GitHub Actions, with PostgreSQL, the provider key and the dataset host | By hand: the label `acceptance:full` on the pull request |

- A run on GitHub Actions is confirmed by its conclusion, the conclusions of its steps and its annotations, read on the page of the run or through the REST API of the repository.
- **Before a label is added**: a label that is added within seconds of a push starts the run on the head before that push. A task that starts a workflow first waits until the head of the pull request on GitHub is the commit that was pushed, compares the two hashes, and only then adds the label. When the run has started, the task confirms that the commit of the run is that head.
- **While a `full` run that can record is in progress, nothing is pushed to the branch**: the run pushes a commit itself when it has something to record (T053, T103).
- **The owner's go-ahead.** A run that can call the embedding provider starts only with the owner's go-ahead. The go-ahead of 2026-11-26 covered the runs of spec 1. For this feature the owner gives one go-ahead, before T050, and it covers every run of `acceptance` of this feature: each run of either scope embeds the example datasets, a few hundred tokens and less than one cent, through the example index of spec 1's tests and of AC-010 and AC-011. No run of this feature embeds the real corpus: in the scope `full` the index `wixqa-001` is restored from its snapshot, and `index build` reports it as already complete. If a run shows that `wixqa-001` was not restored, it is stopped, and nothing is started again before the cause is found.
- The 36 acceptance tests without a marker run in every tier. AC-010 and AC-011 (`store`, `provider`) run from the scope `example` on. AC-001, AC-002 and AC-037 to AC-040 (`real_data`), and AC-009 and AC-041 (`real_data`, `store`), run in the scope `full` only.
- The eight real-data acceptance tests have no fixture that fetches or builds. In one run they execute in the order of their numbers, after the tests of spec 1, and each relies on what an earlier one left: AC-002 and AC-009 on the record that AC-001 wrote, AC-037 on the same record, AC-039 to AC-041 on the records that AC-037 and AC-038 wrote. Once the three records are on the branch, every one of these tests finds them in the checkout.
- A real-data test is shown red in the agent's workspace: before the implementation it fails because the command does not exist. It is shown green only by a run of the scope `full`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: The path by which the three real question sets reach the branch, and the pull request the workflows run for

### CI/CD (DevOps agent)

- [x] T001 [P] Add to `.gitattributes` the two lines `evals/golden/** -text` and `evals/runs/** -text`, so that a recorded file keeps its bytes on every platform (research.md, section 14)
- [x] T002 [P] Add to `.github/scripts/check-worktree.sh` the switch `--allow-new-question-sets`: with it, new files `evals/golden/<version>.json` may appear, where the version has the form of an index identifier; a file under `evals/golden/` that existed and was changed is still reported; the two switches can be given together; the usage message and the head of the script name both (plan.md, "What the DevOps agent builds", point 1)
- [x] T003 Change `.github/workflows/acceptance.yml`, scope `full`: call `check-worktree.sh` after the tests with both switches; after the tests look for new, untracked `evals/golden/*.json` and say in a notice when there are none; when there are some and every step succeeded, run `python -m wixqa_rag set check --version <version>` for each, publish the result lines of each check as a notice, copy the records to a folder outside the checkout and save them as an artifact. Add the job `record-question-sets`: it alone may write to the contents of the repository, runs no code of the repository, adds the records to the branch in one commit `chore(evals): record the question sets <versions> (workflow run <id>)`, runs only when the job before it succeeded, never for `main`, and after `record-index` when both have something to record. Nothing is recorded when a test failed. The step "The checkout is exactly its commit before the real-data tests" and the scopes `checks` and `example` stay as they are (plan.md, "What the DevOps agent builds", points 2 to 6; research.md, section 13; depends on T002)
- [x] T004 Open the pull request from `002-evaluation-harness` to `main` as a draft, with a title in the form the constitution requires, for example `feat(evals): question sets, run records and their checks`, and a description that says what exists on that day and ends with `Spec: specs/002-evaluation-harness`, `Closes #11` and `Run: none`. Confirm that `checks` runs for it and is green: the branch holds documents and the changes of T001 to T003 only

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The example data of the spec, and the two new groups of the command line, which all four stories use

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for the foundation (written first by the testing agent) ⚠️

- [x] T005 [P] Create the data directory `tests/data/harness/` with `hx.jsonl` (six articles, `hx-001` to `hx-006`), `hxa.jsonl` (five questions), `hxb.jsonl` (three), `hxc.jsonl` (two) and `manifest.json` with the name `harness` and the revision `null`; the `article_ids` of the ten questions as the table gives them; ten different question texts (data-model.md, "Example data", "`tests/data/harness/`: a data directory"; the forms of spec 1's contracts/records.md, "`manifest.json`")
- [x] T006 [P] Create the ten question-set records of `tests/data/sets/` in the canonical form: `harness`, `harness-hxc`, `harness-one-less`, `harness-one-more`, `harness-other-gold`, `harness-half`, `harness-half-rest`, `harness-half-swapped`, `harness-half-rest-overlap` and `example`, with the questions that the table lists; the selection of `harness-half` is copied from the table of the eight draw keys, not derived with code of the package (data-model.md, "Example data", "`tests/data/sets/`: question-set records"; contracts/records.md, "Question-set record"; depends on T005 for the fingerprints of the parts)
- [x] T007 [P] Create the registry `tests/data/runs/` with the four sound records `20261101T100000Z-example-a`, `20261102T100000Z-example-b`, `20261103T100000Z-example-c` and `20261104T100000Z-example-d`, each with `run.json`, `results.jsonl` and `summary.json`: the entries, the token counts, the latencies and every number of the four summaries as the tables give them (data-model.md, "Example data", "`tests/data/runs/`: a registry of four sound records"; contracts/records.md, "Run record"; depends on T006 for the fingerprints of the sets)
- [x] T008 Create the registry `tests/data/runs-invalid/` with nine records: the two sound records copied byte for byte, and the seven records with one defect each, every one with its own `run_id` and `started_at` (data-model.md, "Example data", "`tests/data/runs-invalid/`: a registry of nine records"; depends on T007)
- [x] T009 [P] Unit tests in `tests/unit/test_harness_example_data.py`, which compute everything themselves and use no code of the package: the manifest of `tests/data/harness/` matches its files; the eight draw keys of data-model.md are the SHA-256 of `sha256-order-v1:7:<identifier>`, and the three smallest of `hxa` and the smallest of `hxb` are the questions of `harness-half`; every record of `tests/data/sets/` has the bytes of its own canonical form; `of_fingerprint` of the two complements is the SHA-256 of `harness-half.json`; in every run record the fingerprint of the question set is the SHA-256 of the set's file, every `answer_sha256` is the hash of its answer except in `wrong-hash`, every `cost_usd` follows from the tokens and the prices, and `run_id` is the name of the directory; the two sound records of `runs-invalid` have the bytes of those of `runs`
- [x] T010 [P] Unit tests in `tests/unit/test_cli_groups.py` and additions to `tests/unit/test_settings.py`: the groups `set` and `run` exist next to `dataset` and `index`; a group without a command prints the usage message to standard error, nothing to standard output, and ends with exit code 2; `settings.SETS_DIR` is `evals/golden` and `settings.RUNS_DIR` is `evals/runs` (contracts/cli.md, "General rules"; contracts/harness.md, "`wixqa_rag.settings`: additions")
- [x] T011 Run the workspace tier and confirm that the tests of T010 fail because the code is missing and that the tests of T009 pass, since they test the data; then confirm the same in the run of `checks` for the pull request

**Checkpoint (red)**: The example data exists and agrees with itself, and the tests of the foundation that test code fail

### Implementation of the foundation

- [x] T012 [P] Add `SETS_DIR` and `RUNS_DIR` to `src/wixqa_rag/settings.py` (contracts/harness.md, "`wixqa_rag.settings`: additions"; data-model.md, "Question set": where it is stored, and "Run record": the default runs directory)
- [x] T013 Add the groups `set` and `run` to `build_parser` in `src/wixqa_rag/cli.py`, still without commands, with the existing helpers (contracts/cli.md, "General rules", "Groups"; contracts/harness.md, "`wixqa_rag.cli`: additions")
- [x] T014 Run the tests of the foundation and confirm that each passes, with no test changed; the run of `checks` is green

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Fix the golden set and the held-out sets (Priority: P1) 🎯 MVP

**Goal**: The operator produces a question set from a dataset by a recorded rule, a draw with a seed or the complement of another set; every operator gets the same record, can check it against the dataset, and can audit the index with it

**Independent Test**: Produce question sets from the example dataset and check them. A drawn set passes the check against a record that was written beforehand; it and its complement share no question and together are all questions of their parts; altered records fail the check, which names the difference

### Tests for User Story 1 (REQUIRED - written first by the testing agent) ⚠️

> **NOTE: Write these tests FIRST, one for each check of spec.md that covers this story. They MUST FAIL before implementation starts**

- [x] T015 [P] [US1] Acceptance test for check AC-001 in `tests/acceptance/test_s2_ac_001_set_build_golden.py` (marker `real_data`)
- [x] T016 [P] [US1] Acceptance test for check AC-002 in `tests/acceptance/test_s2_ac_002_set_check_golden.py` (marker `real_data`)
- [x] T017 [P] [US1] Acceptance test for check AC-003 in `tests/acceptance/test_s2_ac_003_set_build_twice.py` (no marker)
- [x] T018 [P] [US1] Acceptance test for check AC-004 in `tests/acceptance/test_s2_ac_004_set_build_other_selection.py` (no marker)
- [x] T019 [P] [US1] Acceptance test for check AC-005 in `tests/acceptance/test_s2_ac_005_set_check_built_and_recorded.py` (no marker)
- [x] T020 [P] [US1] Acceptance test for check AC-006 in `tests/acceptance/test_s2_ac_006_set_check_one_less.py` (no marker)
- [x] T021 [P] [US1] Acceptance test for check AC-007 in `tests/acceptance/test_s2_ac_007_set_check_one_more.py` (no marker)
- [x] T022 [P] [US1] Acceptance test for check AC-008 in `tests/acceptance/test_s2_ac_008_set_check_other_gold.py` (no marker)
- [x] T023 [P] [US1] Acceptance test for check AC-009 in `tests/acceptance/test_s2_ac_009_audit_golden.py` (markers `real_data`, `store`)
- [x] T024 [P] [US1] Acceptance test for check AC-010 in `tests/acceptance/test_s2_ac_010_audit_example_set.py` (markers `store`, `provider`)
- [x] T025 [P] [US1] Acceptance test for check AC-011 in `tests/acceptance/test_s2_ac_011_audit_set_of_other_dataset.py` (markers `store`, `provider`)
- [x] T026 [P] [US1] Acceptance test for check AC-033 in `tests/acceptance/test_s2_ac_033_draw_and_complement.py` (no marker)
- [x] T027 [P] [US1] Acceptance test for check AC-034 in `tests/acceptance/test_s2_ac_034_recorded_draw_passes.py` (no marker)
- [x] T028 [P] [US1] Acceptance test for check AC-035 in `tests/acceptance/test_s2_ac_035_set_check_swapped.py` (no marker)
- [x] T029 [P] [US1] Acceptance test for check AC-036 in `tests/acceptance/test_s2_ac_036_set_check_overlap.py` (no marker)
- [x] T030 [P] [US1] Acceptance test for check AC-037 in `tests/acceptance/test_s2_ac_037_set_build_held_out.py` (marker `real_data`)
- [x] T031 [P] [US1] Acceptance test for check AC-038 in `tests/acceptance/test_s2_ac_038_set_build_synthetic.py` (marker `real_data`)
- [x] T032 [P] [US1] Acceptance test for check AC-039 in `tests/acceptance/test_s2_ac_039_set_check_held_out.py` (marker `real_data`)
- [x] T033 [P] [US1] Acceptance test for check AC-040 in `tests/acceptance/test_s2_ac_040_set_check_synthetic.py` (marker `real_data`)
- [x] T034 [P] [US1] Acceptance test for check AC-041 in `tests/acceptance/test_s2_ac_041_audit_held_out_sets.py` (markers `real_data`, `store`)
- [x] T035 [P] [US1] Acceptance test for check AC-044 in `tests/acceptance/test_s2_ac_044_set_build_other_seed.py` (no marker)
- [x] T036 [P] [US1] Acceptance test for check AC-045 in `tests/acceptance/test_s2_ac_045_set_build_too_many.py` (no marker)
- [x] T037 [P] [US1] Unit tests in `tests/unit/test_draw.py`: `question_id` gives the form of FR-002, with at least three digits; `draw_key` gives the eight keys of data-model.md; `draw` selects `hxa-002`, `hxa-003`, `hxa-005` of the five of `hxa` and `hxb-002` of the three of `hxb` with the seed 7, returns them in the order in which the identifiers were given, selects every identifier whatever the seed when the number is the number of identifiers, and gives the same selection when the identifiers are given in another order; equal keys are ordered by identifier; `ValueError` for a number below 1 or above the number of identifiers and for a seed below 0; `is_valid_version` accepts and rejects as the form says (contracts/harness.md, "`wixqa_rag.questionsets`"; research.md, section 2; FR-002, FR-004)
- [x] T038 [P] [US1] Unit tests in `tests/unit/test_questionset_record.py`: `record` for the rules of `harness`, `harness-hxc`, `harness-half` and `harness-half-rest` on `tests/data/harness/`, turned into bytes with `canonical`, gives the bytes of the four example records, and gives them again on a second call; the record holds no time and no commit; `read` returns the fields of `QuestionSet`, its `fingerprint` is the SHA-256 of the file, `pairs()` and `gold()` give what the contract says, and a gold article that a question names twice counts once; `SetError` for a missing file and for a file that is not a question-set record (contracts/harness.md; contracts/records.md, "Question-set record"; FR-003, FR-004)
- [x] T039 [P] [US1] Unit tests in `tests/unit/test_set_check.py`, each on a temporary copy of the example data: one test for each of the differences 1 to 11 of data-model.md, "Check of a question set", and every difference is reported; the reported numbers, among them a set with a question without a gold article, a set with a question text that occurs twice, and a complement with a question text that also occurs in the complemented set; the check is not carried out for a data directory that fails the dataset check, for a record that does not exist, and for a complement whose complemented record is missing or fails; the four records around the draw give the differences of the table in data-model.md (FR-006, FR-007, FR-032; spec.md, edge cases on a repeated question text and on a missing local copy)
- [x] T040 [P] [US1] Unit tests in `tests/unit/test_set_build.py`, in a temporary repository root: the situations of the table in contracts/cli.md, "`set build`" that no acceptance check reads: a version that exists with another role, a part that is not a question part, a complement of a set whose rule is a complement, an empty complement, `--data-dir` with the sets directory `evals/golden`, an invalid version, a data directory that fails the dataset check; after every verdict of `refused` or `not carried out` the sets directory holds the files it held before; the record is written under a temporary name first; wrong arguments of `set build` and of `set check` (both rules given, none given, `--take` without `--seed`, a `--take` of another form, a part given twice, another role) end with a `reason:` line, the verdict `not carried out` and exit code 2 (contracts/cli.md, "General rules" and "`set build`"; FR-005, FR-030)
- [x] T041 [P] [US1] Unit tests in `tests/unit/test_audit_question_set_fields.py`: an `AuditResult` with a question set converts to the JSON document with `question_set.version`, `question_set.role` and `question_set.fingerprint` and back without loss; a document without the three fields reads as one of an audit that named no set, and `evals/indexes/wixqa-001/audit.json` reads so; `audit_index` with both `questions` and `question_set` raises `ValueError` (spec 1's contracts/records.md and contracts/audit-gate.md, the blocks added on 2026-11-27)
- [x] T042 [P] [US1] Integration tests in `tests/integration/test_audit_question_set.py` (marker `store`), with the embedder double: `audit_index` and `require_passed_audit` with `question_set="example"` and `sets_dir` pass on an index built from `tests/data/example/` and return a result that names the set, with `questions` 3; a set that does not exist and a set of another dataset give `NOT_CARRIED_OUT` with the reason, and the gate raises `AuditNotPassed`; without `question_set` the result is the result of spec 1; the command `index audit --set` prints the line `question set: example (golden)` after `revision:`, and `--sets-dir` without `--set` is a wrong argument (contracts/cli.md, "`index audit`: the options `--set` and `--sets-dir`"; FR-008)
- [x] T043 [US1] Run the tests of User Story 1 and confirm that each fails because the behaviour is missing: the workspace tier for the tests without a marker; the eight real-data tests and the two tests marked `provider`, run by name in the workspace, fail because the commands do not exist; then `checks` for T042. No run of `acceptance` is started for this

**Checkpoint (red)**: Every test of User Story 1 exists and fails. No implementation task of this story starts before this point

### Implementation for User Story 1

- [x] T044 [US1] Implement in `src/wixqa_rag/questionsets.py` the question identifier, the form of a version and the draw: `DRAW_METHOD`, `ROLES`, `question_id`, `is_valid_version`, `draw_key`, `draw` (data-model.md, "Question identifier"; "Version of a question set"; "Selection rule": `method`, `seed`, `take`, and the draw key; research.md, section 2; contracts/harness.md)
- [x] T045 [US1] Implement in `src/wixqa_rag/questionsets.py` the record of a question set: `QuestionSet` with `pairs` and `gold`, `SetError`, `read`, `canonical`, and `record` for both kinds of rule (data-model.md, "Question set": `version`, `role`, `dataset`, `rule`, `questions`, `count`, the order of `questions`, the fingerprint, and rules 3 to 5; "Selection rule": `kind`, `method`, `seed`, `take`, `of`, `of_fingerprint`, and the `dataset.parts` of a complement; contracts/records.md, "Question-set record" and its canonical form; depends on T044)
- [x] T046 [US1] Implement in `src/wixqa_rag/questionsets.py` the check of a record: `SetExamination` and `examine`, with the differences 1 to 11, the cases in which the check is not carried out, and the reported numbers (data-model.md, "Check of a question set"; "Question set": rule 4; "Selection rule": the rules of `take` and of `of`; FR-006, FR-007, FR-032; depends on T045)
- [x] T047 [US1] Implement the commands `set build` and `set check`: `build` and `check` in `src/wixqa_rag/questionsets.py`, and their arguments in `src/wixqa_rag/cli.py`, with the six steps of the build, the record written once under a temporary name and then renamed, and every line and verdict of the two tables (contracts/cli.md, "`set build`" and "`set check`"; data-model.md, "Question set": rules 1, 2 and 5; FR-001, FR-005, FR-030; depends on T046)
- [x] T048 [US1] Add the question set to the audit: the keyword arguments `question_set` and `sets_dir` of `audit_index` and `require_passed_audit`, step 4a, the three fields of `AuditResult` and of its JSON document, and the fourth and fifth argument of `command`, in `src/wixqa_rag/audit.py`; the options `--set` and `--sets-dir` of `index audit` in `src/wixqa_rag/cli.py`. Without them the audit, the gate and the command are unchanged (contracts/cli.md, "`index audit`: the options `--set` and `--sets-dir`"; spec 1's contracts/audit-gate.md and contracts/records.md, the blocks added on 2026-11-27; FR-008; depends on T046)
- [x] T049 [US1] Run the tests of User Story 1 without a marker in the workspace, and `checks` for the pull request, and confirm that each passes, with no test changed: AC-003 to AC-008, AC-033 to AC-036, AC-044 and AC-045 among them
- [x] T050 [US1] Start `acceptance` with the scope `example`, after the owner's go-ahead for the runs of this feature, and confirm that AC-010 and AC-011 pass and that every test of spec 1 in that scope still passes
- [x] T051 [US1] Update the sentence of `specs/002-evaluation-harness/quickstart.md` that says what has run, to what has run on that day: the commands on example data, in the workspace, in `checks` and in the scope `example`; the real question sets not yet

**Checkpoint (green)**: The tests of User Story 1 on example data pass unchanged: fourteen of its twenty-two checks. The eight real-data checks wait for the next phase

---

## Phase 4: The Real Question Sets

**Purpose**: The three records of the study, produced once from the pinned dataset, checked, audited against `wixqa-001`, and added to the branch

**Checkpoint (review of the draw)**: Before T052 starts, the code review agent has checked `src/wixqa_rag/questionsets.py`, the changes of `src/wixqa_rag/audit.py`, the tests of T037 to T042 and the workflow changes of T002 and T003 against spec.md, research.md, section 2, and the constitution, and its findings are closed, each fix with its test first. The three records are produced from the draw as reviewed

- [x] T052 Confirm that the head of the pull request holds T001 to T003 and T044 to T048, that `checks` is green on it, and that `evals/golden/` holds no record; wait until the head on GitHub is the local head and compare the two hashes
- [x] T053 Start `acceptance` with the scope `full` and push nothing to the branch until it has ended. Confirm that the commit of the run is the head of T052, that the index `wixqa-001` was restored from its snapshot and that the build of the real index reports `tokens embedded: 0`, and that all eight real-data tests of this feature pass: AC-001, AC-002, AC-009 and AC-037 to AC-041
- [x] T054 Confirm what the run of T053 recorded: one commit on the branch with `evals/golden/golden-001.json`, `evals/golden/held-out-001.json` and `evals/golden/synthetic-001.json` and nothing else; the notices of the three checks. Read from them and report to the owner: for the golden set and for the held-out set the numbers of single-article and multi-article questions; `in both sets: 0` and `in neither set: 0`; the numbers of repeated question texts and of question texts in both sets; `questions without gold articles` for the three sets (SC-001, SC-002). If a check or an audit failed, record the finding and stop: the owner decides (plan.md, "Risks")
- [x] T055 [P] Update the status line of `README.md` to what the repository then contains, the three question sets with their numbers of questions and no run, and its row for `evals/`; update the row for `golden/` in `evals/README.md`: the golden set and the two held-out sets, one record each, with the rule and the seed
- [x] T056 [P] Update the sentence of `specs/002-evaluation-harness/quickstart.md` that says what has run: the three real question sets were produced, checked and audited, with the day and the identifier of the workflow run
- [x] T057 Push the commits of T055 and T056 and confirm that `checks` runs on a head that holds the three records and is green

**Checkpoint (the owner)**: The owner has the numbers of T054. If the owner asks for another rule, the work stops here: the remedy is a new version by an amendment of the spec, never another seed. Otherwise the work goes on with `golden-001`

---

## Phase 5: User Story 2 - Read the measurements of a run (Priority: P2), and User Story 3 - Check a run record and the registry (Priority: P3)

**Goal**: The operator gets the numbers of a recorded run, for both lists and in the three breakdowns, with cost and latency; and checks a run record, or the whole registry, against the format that the constitution requires

**Independent Test**: The report of the example run equals the numbers computed by hand. The example run passes its check; each of the seven altered records fails it, and the check names the defect

### Tests for User Stories 2 and 3 (REQUIRED - written first by the testing agent) ⚠️

> **NOTE: Write these tests FIRST, one for each check of spec.md that covers these stories. They MUST FAIL before implementation starts**

- [x] T058 [P] [US2] Acceptance test for check AC-012 in `tests/acceptance/test_s2_ac_012_run_report_status.py` (no marker)
- [x] T059 [P] [US2] Acceptance test for check AC-013 in `tests/acceptance/test_s2_ac_013_run_report_generation_list.py` (no marker)
- [x] T060 [P] [US2] Acceptance test for check AC-014 in `tests/acceptance/test_s2_ac_014_run_report_retrieved_list.py` (no marker)
- [x] T061 [P] [US2] Acceptance test for check AC-015 in `tests/acceptance/test_s2_ac_015_run_report_misses.py` (no marker)
- [x] T062 [P] [US2] Acceptance test for check AC-016 in `tests/acceptance/test_s2_ac_016_run_report_cost_latency.py` (no marker)
- [x] T063 [P] [US2] Acceptance test for check AC-017 in `tests/acceptance/test_s2_ac_017_run_report_per_question.py` (no marker)
- [x] T064 [P] [US3] Acceptance test for check AC-018 in `tests/acceptance/test_s2_ac_018_run_check_passes.py` (no marker)
- [x] T065 [P] [US3] Acceptance test for check AC-019 in `tests/acceptance/test_s2_ac_019_run_check_registry.py` (no marker)
- [x] T066 [P] [US3] Acceptance test for check AC-020 in `tests/acceptance/test_s2_ac_020_run_check_study_registry.py` (no marker)
- [x] T067 [P] [US3] Acceptance test for check AC-021 in `tests/acceptance/test_s2_ac_021_run_check_no_latency.py` (no marker)
- [x] T068 [P] [US3] Acceptance test for check AC-022 in `tests/acceptance/test_s2_ac_022_run_check_missing_question.py` (no marker)
- [x] T069 [P] [US3] Acceptance test for check AC-023 in `tests/acceptance/test_s2_ac_023_run_check_unknown_status.py` (no marker)
- [x] T070 [P] [US3] Acceptance test for check AC-024 in `tests/acceptance/test_s2_ac_024_run_check_wrong_hash.py` (no marker)
- [x] T071 [P] [US3] Acceptance test for check AC-025 in `tests/acceptance/test_s2_ac_025_run_check_stale_summary.py` (no marker)
- [x] T072 [P] [US3] Acceptance test for check AC-026 in `tests/acceptance/test_s2_ac_026_run_check_two_changes.py` (no marker)
- [x] T073 [P] [US3] Acceptance test for check AC-027 in `tests/acceptance/test_s2_ac_027_run_check_invalid_registry.py` (no marker)
- [x] T074 [P] [US3] Acceptance test for check AC-028 in `tests/acceptance/test_s2_ac_028_run_check_no_such_run.py` (no marker)
- [x] T075 [P] [US3] Acceptance test for check AC-029 in `tests/acceptance/test_s2_ac_029_run_report_refused.py` (no marker)
- [x] T076 [P] [US2] Acceptance test for check AC-042 in `tests/acceptance/test_s2_ac_042_held_out_run_named.py` (no marker)
- [x] T077 [P] [US3] Acceptance test for check AC-043 in `tests/acceptance/test_s2_ac_043_run_check_experiment_on_held_out.py` (no marker)
- [x] T078 [P] [US2] Unit tests in `tests/unit/test_metrics.py`, on plain values: `share_found` and `all_found` for a list with some, all and none of the gold articles, for a list with the same article several times, for an empty list (0) and for a list that is `None` (`None`), and for a question without a gold article (`None`); `kind_of`; `entry_cost` for one and for two models, exact for a price such as 0.02, and `ValueError` for a model without a price; `median` of an odd and an even number of values and `percentile_95` at position ⌈0.95 × *n*⌉, both `None` for no value; `summarize` gives, for the entries of the four example runs, exactly the dictionaries of their `summary.json`, computes the cost from the tokens and not from `cost_usd`, gives `null` for every number over no question and `0.0` for a total cost over none, counts a question without a gold article in `all` only, and raises `ValueError` when the entries are not one per question; `per_question` gives the lines of AC-017; the module imports nothing of the project and reads no file (contracts/harness.md, "`wixqa_rag.metrics`"; data-model.md, "The numbers, defined"; FR-009 to FR-017; spec.md, edge cases)
- [x] T079 [P] [US3] Unit tests in `tests/unit/test_run_id.py` and `tests/unit/test_config_differences.py`: `run_id` and `is_valid_run_id` for the form of FR-018, and `ValueError` for a name of another form and for a time without a time zone; `config_differences` gives the dotted paths of the leaves that differ, treats a list as one leaf, reports a leaf that only one config has, and does not compare `experiment` (contracts/harness.md, "`wixqa_rag.runs`"; research.md, section 9)
- [x] T080 [P] [US3] Unit tests in `tests/unit/test_run_check.py`, each on a temporary copy of the example registries: `summary_document` gives, for each of the four sound records, exactly its `summary.json`; `examine` finds no difference in them; one test for each of the differences 1 to 16 of data-model.md, "Check of a run record", that no acceptance check reads, among them a missing file, a field of the wrong type, a `run_id` that is not the name of the directory or does not agree with `started_at`, a role or a fingerprint that differs from the set's record, an entry for a question outside the set, a list that holds something other than a non-empty string, an `answered` entry without a list, a `generation_list` without a `retrieved_list`, a cost that does not follow from the tokens, a model without a price, an audit result that is absent, not passed, or for another index or set, a baseline that is absent, a baseline on another set, a named parameter that does not differ, and a recorded value that is not the value in the config; every difference is reported; a further field in an entry is ignored; `RunNotFound` for a run that does not exist (FR-020 to FR-023, FR-035)
- [x] T081 [P] [US3] Unit tests in `tests/unit/test_run_registry.py` and `tests/unit/test_run_commands.py`: the check of a registry counts a directory whose name is not a run identifier as a failed run, ignores a file in the runs directory, passes for a registry without runs with `runs: 0`, counts the roles as the records state them (7 and 2 for `tests/data/runs-invalid/`), and prints the differences of a failed run with the run in front; a runs directory that does not exist is not carried out; wrong arguments of `run report`, `run check` and `run compare` end with a `reason:` line, the verdict `not carried out` and exit code 2; `runs` and `metrics` import neither `store`, nor `embedding`, nor `audit`, and the three commands run with `DATABASE_URL` and `OPENAI_API_KEY` removed from the environment; the files of `tests/data/sets/`, `tests/data/runs/` and `tests/data/runs-invalid/` have the same bytes after every command of this feature as before (contracts/cli.md, "`run check`"; contracts/harness.md, "Rules"; FR-024, FR-026, FR-030, FR-031, FR-034)
- [x] T082 [US2] Run the tests of User Stories 2 and 3 in the workspace and confirm that each fails because the behaviour is missing; then confirm the same in the run of `checks`

**Checkpoint (red)**: Every test of User Stories 2 and 3 exists and fails. No implementation task of these stories starts before this point

### Implementation for User Stories 2 and 3

- [ ] T083 [US2] Implement `src/wixqa_rag/metrics.py`, without the comparison: `STATUSES`, `BREAKDOWNS`, `LISTS`, `share_found`, `all_found`, `kind_of`, `entry_cost`, `median`, `percentile_95`, `summarize` and `per_question`, with exact fractions and one conversion at the end (data-model.md, "The numbers, defined"; "Run record", "Results": `status`, `retrieved_list`, `generation_list`, `tokens`, `cost_usd`, `latency_seconds`; "Summary": `breakdowns`, `retrieval_misses`, `questions_without_gold_articles`, and of one breakdown `questions`, `status`, `generation_list`, `retrieved_list`, `cost_usd`, `latency_seconds`, and of a list `questions`, `mean_share_found`, `all_found`, `share_all_found`; research.md, section 7; FR-009 to FR-017)
- [ ] T084 [US3] Implement in `src/wixqa_rag/runs.py` the run identifier and the reading of a record: `RUN_FILE`, `RESULTS_FILE`, `SUMMARY_FILE`, `run_id`, `is_valid_run_id`, `run_ids`, `RunNotFound`, the reading of the three files, `summary_document` and `config_differences`; the module imports neither `store`, nor `embedding`, nor `audit`, and reads no setting (FR-031; contracts/harness.md, "Rules") (data-model.md, "Run identifier"; "Run record", "Identity and config": `run_id`, `started_at`, `commit`, `uncommitted_changes`, `config`, and of the config `dataset`, `question_set`, `index`, `models`, `prompts`, `retrieval`, `reranking`, `context`, `limits`, `seeds`, `concurrency`, `prices`, `experiment`; "Summary": `run_id`, `question_set`, `questions`, `audit`; research.md, sections 6 and 9; FR-018, FR-019, FR-021; depends on T083)
- [ ] T085 [US3] Implement in `src/wixqa_rag/runs.py` the check of a record: `RunExamination` and `examine`, with the differences 1 to 16 and equality of numbers without a tolerance (data-model.md, "Check of a run record"; "Run record", "Results": `question_id`, `status`, `retrieved_list`, `generation_list`, `context`, `answer`, `answer_sha256`, `tokens`, `cost_usd`, `latency_seconds`, and the four rules across fields; "Identity and config": `limits`, `concurrency`, `prices`, `experiment`; "Role"; FR-020, FR-022, FR-023, FR-035; depends on T084)
- [ ] T086 [US3] Implement the command `run check`, for one run and for the registry: `check` in `src/wixqa_rag/runs.py` and its arguments in `src/wixqa_rag/cli.py`, with the lines of both outputs, the two counts by role and every verdict of the table (contracts/cli.md, "`run check`"; data-model.md, "Check of a run record", "Check of the registry"; FR-024, FR-030, FR-034; depends on T085)
- [ ] T087 [US2] Implement the command `run report`: `report` in `src/wixqa_rag/runs.py` and its arguments in `src/wixqa_rag/cli.py`, with the three steps, the lines of the report in their order, the block of `--per-question`, the digits of each kind of number and `undefined`, and the refusal for a record that fails its check (contracts/cli.md, "`run report`" and "Numbers in the output"; FR-014 to FR-016, FR-025, FR-034; depends on T086)
- [ ] T088 [US2] Run the tests of User Stories 2 and 3 in the workspace, and `checks` for the pull request, and confirm that each passes, with no test changed: AC-012 to AC-029, AC-042 and AC-043 among them
- [ ] T089 [US2] Update the sentence of `specs/002-evaluation-harness/quickstart.md` that says what has run, and the status line of `README.md` if it no longer says what the repository contains: a run record can be checked and reported; no run exists

**Checkpoint (green)**: User Stories 1, 2 and 3 work on the example data, and their tests pass unchanged

---

## Phase 6: User Story 4 - Compare two runs pairwise (Priority: P4)

**Order changed on 2026-11-28 (orchestrator)**: T081 tests the wrong arguments and the settings of `run compare`, which T097 implements. So that no test stays red between T088 and T097, the tests T090 to T094 are written right after the red run of T082, and T096 and T097 are implemented together with T083 to T087. Tests still come first: the red run of T095 is made before T096 starts, and the green runs of T088 and T098 are one run.

**Goal**: The operator names two runs on the same question set and learns which questions were gained and which were lost

**Independent Test**: The comparison of the two example runs reports two questions gained and one lost and names them

### Tests for User Story 4 (REQUIRED - written first by the testing agent) ⚠️

> **NOTE: Write these tests FIRST, one for each check of spec.md that covers this story. They MUST FAIL before implementation starts**

- [x] T090 [P] [US4] Acceptance test for check AC-030 in `tests/acceptance/test_s2_ac_030_run_compare.py` (no marker)
- [x] T091 [P] [US4] Acceptance test for check AC-031 in `tests/acceptance/test_s2_ac_031_run_compare_other_set.py` (no marker)
- [x] T092 [P] [US4] Acceptance test for check AC-032 in `tests/acceptance/test_s2_ac_032_run_compare_failed_record.py` (no marker)
- [x] T093 [P] [US4] Acceptance test for check AC-046 in `tests/acceptance/test_s2_ac_046_run_compare_held_out.py` (no marker)
- [x] T094 [P] [US4] Unit tests in `tests/unit/test_run_compare.py`: `metrics.compare` gives the two comparisons of data-model.md, leaves out a question without a generation list in either run and a question without a gold article, keeps the order of the set, and gives nothing gained and nothing lost for a run compared with itself; the command refuses two runs on one version with different fingerprints and names both, is not carried out for a run that does not exist, checks the first run first, and prints no difference of the two numbers (contracts/harness.md, "`wixqa_rag.metrics`"; contracts/cli.md, "`run compare`"; data-model.md, "Pairwise comparison"; FR-027 to FR-029, FR-033, FR-036)
- [ ] T095 [US4] Run the tests of User Story 4 in the workspace and confirm that each fails because the behaviour is missing; then confirm the same in the run of `checks`

**Checkpoint (red)**: Every test of User Story 4 exists and fails. No implementation task of this story starts before this point

### Implementation for User Story 4

- [ ] T096 [US4] Implement `compare` in `src/wixqa_rag/metrics.py` (data-model.md, "Pairwise comparison": left out, compared, gained, lost; FR-027, FR-028)
- [ ] T097 [US4] Implement the command `run compare`: `compare` in `src/wixqa_rag/runs.py` and its arguments in `src/wixqa_rag/cli.py`, with the four steps, the lines of the output, the line for a held-out set, and every verdict of the table (contracts/cli.md, "`run compare`"; data-model.md, "Role"; FR-025, FR-029, FR-033, FR-034, FR-036; depends on T096)
- [ ] T098 [US4] Run the tests of User Story 4 in the workspace, and `checks` for the pull request, and confirm that each passes, with no test changed; every test of the feature without a marker passes

**Checkpoint (green)**: All four stories work on the example data: 36 of the 46 checks pass in every tier, AC-010 and AC-011 passed in the scope `example` (T050), and the eight real-data checks passed in the scope `full` (T053)

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: The texts, the review of the whole diff, and the last run of every check

### Texts

- [ ] T099 [P] Update `README.md`: the status line, true to that day; the rows for `evals/golden/` (the golden set and the two held-out sets) and `evals/runs/` (the form of a run record; no run yet); the commands of this feature that can be tried with nothing else installed; a pointer to `specs/002-evaluation-harness/quickstart.md`
- [ ] T100 [P] Update `evals/README.md`: the rows for `golden/` and `runs/`, each with the file names of its records and the command that checks them; the sentence "File formats are fixed by the specs" names the two contracts
- [ ] T101 [P] Run part A of `specs/002-evaluation-harness/quickstart.md` in the workspace, step by step, and confirm each expected outcome; correct in quickstart.md what does not match the commands as built, and update its sentence on what has run

**Checkpoint (review)**: Before T102 starts, the code review agent has checked the whole diff of the pull request against spec.md and the constitution, and its findings are closed, each fix with its test first. The last run is made on the code as reviewed

### Acceptance and evidence (REQUIRED - last)

- [ ] T102 Confirm that `checks` is green on the head of the pull request; wait until the head on GitHub is the local head and compare the two hashes. Start `acceptance` with the scope `example` and confirm that it is green: every test of the feature but the eight real-data tests
- [ ] T103 Run every check of the "Acceptance Checks" of spec.md exactly as written and confirm the observable result of each: start `acceptance` with the scope `full` on the head of T102, and push nothing to the branch until it has ended. All 46 acceptance tests pass in this one run. The three builds of AC-001, AC-037 and AC-038 report `(already written)`: the code as reviewed draws the questions of the three records. The run embeds nothing for the real index and adds no commit to the branch
- [ ] T104 Confirm that the run of T103 recorded nothing: the head of the pull request is the head of T102, `evals/golden/` holds exactly the three records with the bytes of T054, and `evals/runs/` holds no run (SC-001, SC-007; FR-026)
- [ ] T105 Rewrite the description of the pull request to what was built and found: the commands, the three question sets with their numbers of questions and of single-article and multi-article questions, what the checks and the audits reported, that no run exists, and the additions to the contracts of spec 1; it ends with `Spec: specs/002-evaluation-harness`, `Closes #11` and `Run: none`. Mark the pull request as ready for review. Tell the owner: merge by squash with the title and the description of the pull request as the commit message, and delete the two footer lines that the system appends to the message before confirming (constitution, "Development Workflow")

> **NOTE: This feature cannot change what a pipeline retrieves or answers, because no pipeline exists yet. It has no task that records an evaluation run, and its pull request states `Run: none`**

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on the Foundational phase
- **The real question sets (Phase 4)**: Depends on User Story 1 being green on the example data, on T001 to T003, and on the review of the draw
- **User Stories 2 and 3 (Phase 5)**: Depend on the Foundational phase and on `questionsets.read` of User Story 1. Their tests are written after T057, so that the run of T053 holds no test that is red by design
- **User Story 4 (Phase 6)**: Depends on Phase 5
- **Polish (Phase 7)**: Depends on all four stories being green

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Foundational (Phase 2). No dependency on another story
- **User Story 2 (P2) and User Story 3 (P3)**: Start after User Story 1, whose record of a question set gives them the gold article ids. They are delivered together: the report of User Story 2 is made only from a record that passes the check of User Story 3. They are tested on their own with the example registries
- **User Story 4 (P4)**: Starts after User Stories 2 and 3. A comparison needs two records that pass the check, and the numbers of `metrics.py`

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- The modules of a story before the command that uses them
- The command before the run that confirms the story
- Story complete before moving to next priority

### Parallel Opportunities

- T001 and T002 in Setup
- T005, T009 and T010 in the Foundational phase; T006, T007 and T008 follow one another, because each needs fingerprints of the one before
- The test tasks marked [P] within one "Tests" block: each writes its own file
- T055 and T056 in Phase 4; T099, T100 and T101 in Phase 7
- The stories themselves do not run in parallel: each depends on the one before it

---

## Parallel Example: User Story 1

```bash
# Write all tests of User Story 1 together (each in its own file):
Task: "Acceptance test for check AC-003 in tests/acceptance/test_s2_ac_003_set_build_twice.py"
Task: "Acceptance test for check AC-034 in tests/acceptance/test_s2_ac_034_recorded_draw_passes.py"
Task: "Unit tests in tests/unit/test_draw.py"
Task: "Unit tests in tests/unit/test_set_check.py"
Task: "Integration tests in tests/integration/test_audit_question_set.py"

# After the red checkpoint the implementation is one chain in one module:
# T044 → T045 → T046 → T047, and T048 beside T047 (another module)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run the tests of User Story 1; they pass unchanged on the example data
5. Complete Phase 4: the three real question sets exist, are checked and audited, and the owner has their numbers. User Story 1 can be accepted on its own, as the first slice

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → A question set is produced, checked and audited on example data (MVP!)
3. Phase 4 → The golden set and the two held-out sets of the study are recorded
4. Add User Stories 2 and 3 → Test independently → A run record is checked and reported
5. Add User Story 4 → Test independently → Two runs are compared
6. Phase 7 → Texts, review, and the one run with all 46 checks
7. Each story adds value without breaking previous stories

### One Pull Request

All phases reach `main` through one pull request, opened as a draft in T004 and marked ready in T105. The owner squash-merges it.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Verify tests fail before implementing; the coding agent never changes an acceptance test
- Commit after each task or logical group
- Stop at any checkpoint to validate a story on its own
- The run that counts for a test marked `store`, `provider` or `real_data` is the one on GitHub Actions; an agent may also run the `store` tests in its workspace
- The README's status line and the sentence of quickstart.md on what has run are kept true at each stage (T051, T055, T056, T089, T099, T101), not only at the end
- The spec is approved and is not edited. A gap found during the work goes to the owner as a proposed amendment; no task works around it
- Any finding about the published data (a question without a gold article, a reference outside the index, a repeated question text, an uneven fall of the two kinds of question) is recorded and goes to the owner; the data stays as published
- A draw whose result is not wanted is remedied by a new version with another rule, by an amendment of the spec, never by another seed
