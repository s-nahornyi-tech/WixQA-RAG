# Implementation Plan: Evaluation harness

**Branch**: `002-evaluation-harness` | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-evaluation-harness/spec.md`

## Summary

The feature gives the study its ruler: the fixed question sets, the numbers of a run, the form of a run record with its check, and the pairwise comparison of two runs. It builds nothing that is measured. No pipeline exists, so no run is recorded and no result number appears; every number in these documents belongs to example data written by hand.

The technical approach:

- **Five commands** in the existing package, in two new groups: `python -m wixqa_rag set build`, `set check`, `run report`, `run check` and `run compare`, and two new options of `index audit`, `--set` and `--sets-dir`. Their output and exit codes are fixed in [contracts/cli.md](contracts/cli.md).
- **Question sets**: one JSON file per set in `evals/golden/`, in a canonical form, with the gold article ids of every question. A set is produced by a rule: a draw with a seed, or the complement of another set. The draw is the method `sha256-order-v1`: the questions of a part are ordered by the SHA-256 of a text made of the method's name, the seed and the question identifier, and the first *N* are taken. It depends on no random generator, so it gives the same record on every machine (FR-004), and a reader can repeat any step with `sha256sum`.
- **Run record**: a directory per run with three files, `run.json` (identity and config), `results.jsonl` (one entry per question) and `summary.json` (the audit result and the numbers). The names and the fields are fixed in [contracts/records.md](contracts/records.md).
- **One computation**: the module `metrics.py`, pure functions with exact arithmetic. The summary of a run is what these functions return, so the check of a record recomputes it and compares for equality. Spec 3 calls the same functions when it writes a run record ([contracts/harness.md](contracts/harness.md)).
- **No new dependency**: the Python standard library suffices.
- **Where it runs**: 36 of the 46 acceptance checks need only the checkout and run everywhere. The three real question sets are produced on GitHub Actions, because only there the dataset can be fetched; the acceptance workflow adds them to the branch in one commit, as it does for the record of an index.

The reasons for each choice, and the alternatives, are in [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.14 (unchanged)

**Primary Dependencies**: none added. `hashlib`, `json`, `fractions`, `math`, `argparse`, `pathlib`, `dataclasses` and `re` of the standard library. `openai` and `psycopg` stay for the commands of spec 1; no module of this feature imports them, apart from `audit.py`, which reaches the store as before.

**Storage**: files. `evals/golden/<version>.json` for the question sets and `evals/runs/<run id>/` for run records, both in version control. `tests/data/` holds the example data. `data/sets/`, outside version control, receives the sets that acceptance checks build from example data. The store of spec 1 is read only by `index audit`.

**Testing**: pytest, with the three folders and the three markers of spec 1. One acceptance test per check, `tests/acceptance/test_s2_ac_NNN_<words>.py`; unit tests on plain values for the draw, the metrics, the records and the config comparison; integration tests for the audit with a question set, against PostgreSQL with the embedder double. Which check runs in which tier: research.md, section 12.

**Target Platform**: Linux, on the GitHub-hosted runner `ubuntu-24.04`; the commands without a marker also run in an agent's workspace. Commands are typed in a POSIX shell.

**Project Type**: cli: one Python package with a command-line entry point.

**Performance Goals**: none as a target; the study operates no service. Working expectation, not measured: every command of this feature ends within seconds, for a set of 300 questions and a run of 200.

**Constraints**:

- The agents' workspaces reach neither the dataset host nor a provider. The three real question sets can be produced only on GitHub Actions.
- The same dataset, rule and seed give the same record everywhere (FR-004): nothing in a draw or in a record may depend on a machine, a time or the version of a tool.
- Recomputing a summary gives the same numbers (SC-006): sums are exact, and numbers are compared for equality.
- `run report`, `run check` and `run compare` need neither the store, nor a provider, nor the dataset host, nor a credential (FR-031).
- Exit code 1 means only "a check found a difference". Every other failure ends with exit code 2.
- No command changes a record that exists, or the dataset (FR-026).
- The spec is approved and is not edited. A gap found here goes to the owner as a proposed amendment ("Points the spec leaves open").

**Scale/Scope**: three question sets of 200, 200 and 300 questions; run records of 200 or 300 entries. Five commands and two options, 36 functional requirements, 8 success criteria, 46 acceptance checks. Example data: one data directory with ten questions, ten question-set records, and two registries with four and nine run records.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against version 1.2.0.

| Rule of the constitution | Applies | How this plan meets it |
|---|---|---|
| I. Index Audit | Yes | The audit of spec 1 takes a question set by version and checks every gold article of every question of that set against the index. The gate of spec 1 gets the same argument, so a run on any set is audited against that set. The summary of a run carries the audit result, and the check of a run record fails when it is absent, not passed, or made for another index, dataset or set |
| II. Article-level metrics on the actual lists | Yes: this feature implements it | The entry of a question records both lists as ordered article ids, one per item, or as absent. `metrics.py` computes `share_found` and `all_found` on the distinct ids of each list, for both lists, and on nothing else. It has no parameter for a cut-off |
| III. Fixed golden set; held-out sets | Yes: this feature implements it | The golden set and both held-out sets are records in `evals/golden/` with the identifiers, the rule, the seed and a version, written once. A run names its set by version, role and fingerprint. An experiment run on a held-out set fails the check of its record. A comparison across sets or versions is refused. The registry check counts the runs on held-out sets. What only discipline can keep is stated in the spec and is not claimed by any check |
| IV. A label belongs to one answer | In part | The entry records the SHA-256 of the answer's UTF-8 text, and the check verifies it; labels arrive with spec 4 |
| V. Judge and calibration | No | The summary holds no number of the judge; spec 4 adds its numbers in files of its own |
| VI. One change, one run | Yes | The config is in `run.json`, next to the results. For an experiment the check compares the two configs leaf by leaf and fails unless exactly the named parameter differs, with the recorded old and new value. `TODO(REFERENCE_AFTER_ADOPTION)` is not decided here: the check compares with the run that the record names |
| VII. Failures are separate | Yes | Five statuses, one per question; the counts add up to the size of the set. A question without a generation list is never a retrieval miss |
| VIII. Breakdowns | Yes | The status counts, both retrieval metrics on both lists, the cost and the latency are computed for all, single-article and multi-article questions, each with its number of questions |
| IX. Cost and latency | Yes | Every entry has its token counts, its cost and its latency; an entry without them is a defect. The summary and the report carry the totals, the cost per question, the median and the 95th percentile |
| X. Evidence before decisions | Yes | The plan decides nothing about a pipeline and states no quality target. The method of the draw and the seed are recorded as chosen before any draw, with no run |
| Scope and non-goals | Yes | No service. The dataset is not edited: a question-set record copies identifiers and gold article ids as published, and the check compares them with the dataset. The code serves this study's records only |
| Stack: pinned revision | Yes | A question-set record states the dataset revision and the fingerprint of every part it takes from; a run's config states the revision |
| Stack: most specific model identifier | Yes | `config.models` holds the identifiers; spec 3 fills them |
| Stack: lock file | Yes | No dependency is added; `uv.lock` does not change |
| Stack: secrets | Yes | The new commands read no setting. No record holds a credential |
| Metric Definitions | Yes | Implemented as written. Where the constitution names the median and the 95th percentile without a method, the spec's FR-016 fixes one, and the plan follows it |
| Run Record Format | Yes | Identity, config, one entry per question of the run's question set, summary; unique run identifiers; files written once; a summary that is derived and recomputable; file names, field names and the two forms fixed here, as the constitution asks of this feature |
| Workflow: approved spec | Yes | The owner approved the spec on 2026-11-27 |
| Workflow: tests first | Yes | For each story the testing agent writes the acceptance tests and the example data before the implementation, and a run shows them red. The coding agent does not change them |
| Workflow: evaluation run | No | No pipeline exists, so this feature cannot change what a pipeline retrieves or answers: `Run: none` |
| Workflow: one branch, one pull request | Yes | One pull request from `002-evaluation-harness`. The acceptance workflow adds one commit with three record files to the branch; its recording job never runs for `main` |
| Workflow: no link to a private agent session | Yes | The commit that the workflow adds names the identifier of the workflow run and nothing else |
| Public texts | Yes | The README's status line and `evals/README.md` change in the same pull request, and only to what the repository then contains: three question sets, no run |
| Governance | Yes | No amendment follows from this plan |

**Result before research**: pass. No rule is violated, and nothing needs a justification under "Complexity Tracking".

**Result after design**: pass. The design adds three things that the spec does not name: the canonical form of a question-set record, the refusal to put a set of example data into `evals/golden/`, and the field `uncommitted_changes` in the identity of a run. Each serves a requirement (FR-004 and FR-005; FR-001; the constitution's "commit of the code that produced it") and conflicts with no rule above.

## Project Structure

### Documentation (this feature)

```text
specs/002-evaluation-harness/
├── spec.md              # The specification, approved by the owner on 2026-11-27
├── plan.md              # This file
├── research.md          # Each choice with its reasons and alternatives; facts checked
├── data-model.md        # Entities, rules, the checks, and the example data in full
├── quickstart.md        # How to see that the feature works
├── contracts/
│   ├── cli.md           # The five commands and the two options: arguments, output lines, exit codes
│   ├── records.md       # The question-set record and the three files of a run record
│   └── harness.md       # The Python names that the tests and spec 3 use
├── checklists/
│   └── requirements.md  # Quality checklist of the spec
└── tasks.md             # Created by /speckit-tasks, not by this plan

specs/001-corpus-and-audit/contracts/
├── cli.md               # Edited: the options --set and --sets-dir of index audit, marked 2026-11-27
├── audit-gate.md        # Edited: the arguments question_set and sets_dir
└── records.md           # Edited: three fields of the audit result when a question set is named
```

### Source Code (repository root)

```text
.github/
├── workflows/
│   └── acceptance.yml      # Changed by the DevOps agent: records new question sets (scope full)
└── scripts/
    └── check-worktree.sh   # Changed: may allow new evals/golden/<version>.json
.gitattributes              # Adds: evals/golden/** and evals/runs/** keep their bytes

src/
└── wixqa_rag/
    ├── cli.py              # Adds the groups set and run, and two options of index audit
    ├── settings.py         # Adds SETS_DIR and RUNS_DIR
    ├── audit.py            # Adds question_set and sets_dir to the audit, the gate and the command
    ├── questionsets.py     # New: question identifier, draw, record, set build, set check
    ├── metrics.py          # New: the one computation; pure functions
    └── runs.py             # New: run identifier, record, check, run report, run check, run compare

tests/
├── acceptance/             # Adds test_s2_ac_001_… to test_s2_ac_046_…, one per check
├── integration/            # Adds: the audit and the gate with a question set
├── unit/                   # Adds: draw, records of a set, metrics, config comparison, run check
└── data/
    ├── harness/            # New: a data directory, 6 articles, the question parts hxa, hxb, hxc
    ├── sets/               # New: ten question-set records
    ├── runs/               # New: a registry of four sound run records
    └── runs-invalid/       # New: a registry of nine run records, seven with one defect each

evals/
├── golden/                 # Written by the first full run after User Story 1
│   ├── golden-001.json
│   ├── held-out-001.json
│   └── synthetic-001.json
└── runs/                   # Stays empty: no run exists

data/
└── sets/                   # Outside version control: sets built by acceptance checks
```

**Structure Decision**: The package of spec 1 grows by three modules, one per concern: question sets, numbers, run records. `metrics.py` imports nothing of the project and reads no file, which is what makes it the one computation: the pipeline of spec 3 and the check of a record can only reach the numbers through it. `runs.py` and `metrics.py` do not import `store`, `embedding` or `audit`, so the three `run` commands cannot touch the store or a provider (FR-031). The example data keeps the layout of spec 1: data directories and records under `tests/data/`, each in a folder that says what it is. The modules `dataset.py`, `index.py`, `store.py`, `splitting.py` and `embedding.py` are not changed.

## Where the commands run

| Workflow | Starts | Uses | Runs of this feature |
|---|---|---|---|
| An agent's workspace | By the agent | Nothing | The 36 checks without a marker, and every unit test |
| `checks.yml` | By itself, for every pull request | PostgreSQL; no secret | The same, and the integration tests of the audit with a question set. The workflow file does not change |
| `acceptance.yml`, scope `example` | When a person starts it | PostgreSQL and `OPENAI_API_KEY` | The same, and AC-010 and AC-011 |
| `acceptance.yml`, scope `full` | When a person starts it | PostgreSQL, `OPENAI_API_KEY`, the dataset host | Every check: AC-001, AC-002 and AC-037 to AC-040 on the fetched dataset, AC-009 and AC-041 on the restored index `wixqa-001`. It records new question sets |

**Cost.** Only AC-010 and AC-011 can reach the embedding provider, through `index build` of the example index of spec 1: five passages, a few hundred tokens, and nothing when a test of spec 1 has built that index earlier in the same run. No check of this feature embeds anything else. The index `wixqa-001` is restored from its snapshot and is not built again.

### What the DevOps agent builds

One change of the acceptance workflow and of one script, by the pattern of the index record (research.md, section 13).

1. `check-worktree.sh` gets a second switch, `--allow-new-question-sets`: with it, new files `evals/golden/<version>.json` may appear, where the version has the form of an index identifier. A file under `evals/golden/` that existed and was changed is still reported. The scope `full` calls the script with both switches; `checks` and the scope `example` call it with none, as today.
2. In the scope `full`, after the tests, a step looks for new, untracked files `evals/golden/*.json`. When there are none, it says so in a notice and nothing more happens.
3. When there are some and every step of the job succeeded: for each new record the job runs `python -m wixqa_rag set check --version <version>`, publishes its result lines as a notice (so that the numbers of single-article and multi-article questions of each set can be read without opening a log), copies the records to a folder outside the checkout, and saves them as an artifact.
4. A job `record-question-sets`, with the right to write to the contents of the repository and with no code of the repository run in it, adds the records to the branch in one commit, `chore(evals): record the question sets <versions> (workflow run <id>)`. It runs only when the job before it succeeded, and never for `main`. It runs after the job `record-index` when both have something to record, so that two pushes never race.
5. Nothing is recorded when a test failed. Unlike an index, a question set costs nothing to produce, so nothing needs to be rescued: the next run produces it again.
6. The real-data tests may leave three new files in the checkout. The step "The checkout is exactly its commit before the real-data tests" stays as it is: it runs before them.

The DevOps agent also adds the two lines to `.gitattributes` (research.md, section 14).

## How the work is delivered

One pull request from the branch `002-evaluation-harness`, which already exists with the spec; it is opened as a draft when the implementation starts.

1. **Setup** (coding agent, DevOps agent): `SETS_DIR` and `RUNS_DIR` in `settings.py`, the empty groups `set` and `run` in `cli.py`, `.gitattributes`, and the change of the acceptance workflow and of `check-worktree.sh`.
2. **Example data** (testing agent): `tests/data/harness/`, the ten records of `tests/data/sets/`, the two registries. All of it is copied from data-model.md and contracts/records.md; unit tests check that the example data agrees with itself (fingerprints, hashes of answers, costs).
3. **User Story 1, question sets**: the testing agent writes the tests of AC-003 to AC-008, AC-010, AC-011, AC-033 to AC-036, AC-044 and AC-045, the unit tests of the draw and of the record, and the integration tests of the audit with a set; a run shows them red. The coding agent implements `questionsets.py` and the additions to `audit.py` and `cli.py` until they are green in `checks` and in the scope `example`.
4. **The real question sets, early**: the testing agent adds the tests of AC-001, AC-002, AC-009 and AC-037 to AC-041. The code review agent looks at the draw and at the record of a set. Then one run of the scope `full` produces the three records, checks them, audits the index with each, and adds them to the branch. The owner reads the numbers of single-article and multi-article questions of the golden set and of the held-out set.
5. **User Stories 2 and 3, the numbers and the record of a run**: the tests of AC-012 to AC-029, AC-042 and AC-043 and the unit tests of `metrics.py` and of the check, red; then `metrics.py`, the check of a record in `runs.py`, and the report, in this order, because a report is made only from a record that passes its check (FR-025).
6. **User Story 4, the comparison**: the tests of AC-030 to AC-032 and AC-046, red; then the comparison.
7. **Review** (code review agent): the whole diff against the spec and the constitution.
8. **A last run of the scope `full`**: every check of the feature in one run. The three builds report the records as already written, which shows that the final code draws the same questions as the code of step 4.
9. **Texts** (coding agent): the README's status line and its table, `evals/README.md`.
10. **Merge**: the owner squash-merges. The description ends with `Spec: specs/002-evaluation-harness`, `Closes #11` and `Run: none`.

The tasks are in `tasks.md`, which the next Spec Kit step writes.

**Why the real question sets are produced early, and why that is safe.** The record of an index names the commit of the code, so spec 1 built its index last. A question-set record names no commit and no time: it depends on the dataset, the rule and the seed only, and that is a requirement (FR-004), not a convenience. Producing it early has three gains. The dataset's own facts, which no workspace can see, are known while there is time to act on them: how the single-article and multi-article questions fell into the two halves, and whether a question text repeats. The audit of Principle I for the three sets is done once before anything else is built on them. And the records are then checked again by every later `full` run. It is safe because the draw is covered before it is used: AC-034 passes only when the implementation selects exactly the questions that this plan computed by hand, and the code review agent has read the draw. If a later change altered the draw, AC-034 would fail in an agent's workspace, and the last `full` run would refuse to rebuild the recorded sets. Should the owner want another rule after seeing the numbers, the remedy is a new version by an amendment of the spec, never another seed; the first records have then been used by no run.

A commit that a job pushes with its own token starts no workflow, so the commit of step 4 gets no run of `checks`. The commits of step 5 are pushed by agents, and `checks` then runs on the branch with the three records in it.

## Requirement coverage

| Requirement | Met by | Checked by |
|---|---|---|
| FR-001 | The three `set build` commands of the spec; the records in `evals/golden/` | AC-001, AC-037, AC-038 |
| FR-002 | `questionsets.question_id` | AC-001; a unit test of the form |
| FR-003 | The question-set record of contracts/records.md | AC-001, AC-005; unit tests of every field and of the canonical form |
| FR-004 | The method `sha256-order-v1`; a record without time or commit | AC-001, AC-003, AC-033, AC-034; unit tests that pin the eight draw keys and compare the bytes of a built record with the example record |
| FR-005 | Step 5 of `set build`: same bytes, or refused | AC-001, AC-003, AC-004, AC-044 |
| FR-006 | `questionsets.examine`, differences 1 to 8 | AC-002, AC-005 to AC-008, AC-034, AC-035, AC-039, AC-040, AC-045; a unit test for each kind of difference |
| FR-007 | The report of `set check` | AC-002, AC-005, AC-039, AC-040; a unit test with repeated question texts |
| FR-008 | `--set` and `--sets-dir` of `index audit`; `question_set` of the gate | AC-009, AC-010, AC-011, AC-041; integration tests of the gate with a set |
| FR-009 | `metrics.share_found` and `metrics.all_found` on both lists; no cut-off | AC-013, AC-014 |
| FR-010 | The same two functions; `metrics.per_question` | AC-013, AC-014, AC-017 |
| FR-011 | `null` against `[]` in the entry and in the functions | AC-013, AC-014, AC-017; unit tests of both cases |
| FR-012 | `metrics.summarize`: the four numbers of a list | AC-013, AC-014 |
| FR-013 | `retrieval_misses` of `metrics.summarize` | AC-015 |
| FR-014 | `metrics.STATUSES`; difference 6 of the run check | AC-012, AC-022, AC-023 |
| FR-015 | The three breakdowns of `metrics.summarize` | AC-012 to AC-016 |
| FR-016 | `metrics.entry_cost`, `metrics.median`, `metrics.percentile_95` | AC-016; unit tests of an odd and an even number of values |
| FR-017 | `metrics.py`, called by `runs.summary_document` and by `runs.examine` | AC-018, AC-025 |
| FR-018 | `runs.run_id`, `runs.is_valid_run_id`; the directory named by the identifier | AC-018; unit tests of the form and of difference 3 |
| FR-019 | `run.json`, `results.jsonl`, `summary.json` | AC-018 |
| FR-020 | The entry of contracts/records.md and the rules of data-model.md | AC-018; unit tests of each rule |
| FR-021 | `runs.summary_document` | AC-018 |
| FR-022 | `runs.examine`, differences 1 to 12 | AC-018, AC-021 to AC-025; a unit test for each difference that no check reads |
| FR-023 | `runs.config_differences`; differences 13, 14 and 16 | AC-019, AC-026; unit tests of a baseline that is absent, on another set, and not differing |
| FR-024 | `runs.check` without a run | AC-019, AC-020, AC-027 |
| FR-025 | Step 2 of `run report` and of `run compare` | AC-029, AC-032 |
| FR-026 | No function but `questionsets.build` writes; it writes one new file | AC-020; a test that the fingerprints of the example records are the same after every command |
| FR-027 | `metrics.compare` | AC-030 |
| FR-028 | `left_out` of `metrics.compare` | AC-030 |
| FR-029 | Step 3 of `run compare` | AC-031; a unit test of one version with two fingerprints |
| FR-030 | Three verdicts and three exit codes for `set check` and `run check`; `carry_out` for every error | AC-011, AC-020, AC-028, AC-045 |
| FR-031 | The imports of `metrics.py` and `runs.py`; no setting is read | AC-018, AC-030, both typed with `env -u DATABASE_URL -u OPENAI_API_KEY` |
| FR-032 | The rule `complement`; differences 9 to 11 | AC-033, AC-034, AC-036, AC-037, AC-039 |
| FR-033 | One question set per run in the config; step 3 of `run compare` | AC-031, AC-038 |
| FR-034 | The line `question set: <version> (<role>)`; the two counts of the registry check | AC-019, AC-042, AC-046 |
| FR-035 | Difference 15 of the run check | AC-043 |
| FR-036 | The line `held-out set: …` of `run compare` | AC-046 |
| SC-001 | The three records and their checks | AC-001, AC-002, AC-037 to AC-040 |
| SC-002 | The three audits | AC-009, AC-041 |
| SC-003 | The report of `example-a` | AC-012 to AC-016 |
| SC-004 | The defective example records | AC-006 to AC-008, AC-021 to AC-026, AC-035, AC-036, AC-043 |
| SC-005 | The two comparisons | AC-030, AC-031 |
| SC-006 | Exact numbers; the canonical form | AC-003, AC-018, AC-025, AC-033, AC-034 |
| SC-007 | `run check` on `evals/runs/` | AC-020 |
| SC-008 | The marks of a held-out run | AC-019, AC-042, AC-043 |

All 46 checks appear in the table. The edge cases of the spec are covered by unit tests where no check reads them: a question without a gold article, a list with the same article several times, a gold article named twice, a breakdown without questions, a repeated question text, a missing data directory, and a comparison of a run with itself.

## Points the spec leaves open

The spec is silent on the points below. The plan reads them as follows, in each case in the direction of the requirement named. None changes a requirement or an acceptance check. If the owner or the code review agent reads one of them differently, the spec is amended first.

1. **The method of the draw.** The spec leaves it to the plan (its "Assumptions"). It is `sha256-order-v1` (research.md, section 2).
2. **What "the same record" means.** The same bytes: a record has one canonical form, and its fingerprint is the SHA-256 of its file (FR-004, FR-005, FR-019).
3. **A set of example data in `evals/golden/`.** Refused, so that only sets of the pinned dataset stand there (FR-001).
4. **A complement of what.** Only of a set whose rule is a draw, and never an empty one (FR-032).
5. **When two question texts are "the same".** When they are equal as they stand, without changing case or spaces (FR-007).
6. **The fields of the config.** This feature fixes the thirteen fields and the shape of seven of them; the six that describe the pipeline are objects whose content spec 3 fixes (FR-019).
7. **What a config parameter is.** A leaf of the config, named by a dotted path; a list is one leaf (FR-023).
8. **The context of an entry.** The exact text, as one string, or `null` when nothing was passed (FR-020: "a form from which its exact text can be restored").
9. **Token counts of an entry.** One count of input and of output tokens per model, and a price per model in the config (FR-016, FR-020).
10. **Equality of numbers.** The check of a record compares for equality, with no tolerance; this is possible because every number is computed exactly (FR-017, FR-022).
11. **A question without a gold article in a comparison.** Left out and counted as left out: it has no `all_found` (FR-028 names only the missing generation list).
12. **A directory of the registry whose name is not a run identifier.** A failed run (FR-018, FR-024).
13. **Which role the registry counts.** The role that the record of the run states, also when the record fails its check for another reason (FR-034).
14. **The differences of a failed run in the check of the registry.** Printed with the run in front (FR-024, FR-030).
15. **A further field in an entry.** Allowed and ignored, so that a later spec can add one without a change here.
16. **`uncommitted_changes` in the identity.** Added, as in the build record of spec 1, so that the commit of a run is not taken for more than it is.
17. **Writing a run record.** Spec 3. This feature gives it `runs.run_id` and `runs.summary_document`, and the check that the written record has to pass.

## The owner's part

1. Start a run when an agent cannot: the label `acceptance:full` on the pull request, once after User Story 1 and once at the end; the label `acceptance:example` when asked.
2. After the first of the two `full` runs: read the numbers of single-article and multi-article questions of the golden set and of the held-out set, which the run shows in a notice and the agents report. If the two halves look lopsided, say so. The remedy is then a new version with a balanced rule, by an amendment of the spec; never another seed. If nothing is said, the work goes on with `golden-001`.
3. Merge the pull request.

No new secret, no new account, nothing installed on the owner's computer. Expected spending: less than one cent, for the example index only.

## Risks

| Risk | What happens | What is done |
|---|---|---|
| The single-article and multi-article questions fall unevenly into the golden set and the held-out set | The numbers by kind of the two sets are harder to compare | The check prints the numbers for both sets after the first `full` run, before any run is made on them. The owner decides; the remedy is a new version with a balanced rule |
| A question text occurs in the golden set and in the held-out set | The held-out set is a little less independent | The check reports the number. The data stays as published; the owner decides whether a rule has to take it into account |
| A question of the real data has no gold article, or names an article outside the index | AC-002, AC-009 or AC-041 stays red | The audit of all 6,621 questions against `wixqa-001` found neither (`evals/indexes/wixqa-001/audit.json`). If it happens, the finding is recorded and the owner decides |
| The job cannot push the three records | The records are in the artifact of the run and not on the branch | They are added by hand from the artifact; a later `full` run confirms them as already written |
| The example records are not in the canonical form | A unit test that compares the bytes of a built record with the example record fails | The testing agent writes the records with the two-line recipe of contracts/records.md; the test names the first byte that differs |
| A stale file in `data/sets/` of a workspace | `set build` of an acceptance check is refused | `data/` is outside version control; the folder is removed (quickstart.md). CI starts from a clean checkout |
| Spec 3 needs a field that this plan did not foresee | A run record could not hold it | A later spec may add fields and files (contracts/records.md); the six pipeline objects of the config are open by design |
| A later change of the code alters the draw | The recorded sets could no longer be reproduced | AC-034 and the unit test of the eight draw keys fail in every workspace; the last `full` run refuses to rebuild the records |

## Complexity Tracking

No rule of the constitution is violated, so this table is not needed.
