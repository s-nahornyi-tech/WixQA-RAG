# Research: Evaluation harness

**Feature**: `002-evaluation-harness` | **Date**: 2026-11-27 | **Plan**: [plan.md](plan.md)

Each section records one choice of the plan: what was decided, why, and what else was considered. Facts were checked on 2026-11-27 and are listed with their sources under "Facts checked". What could not be checked from the planning workspace is listed under "Not checked"; the first runs confirm it.

None of these choices is a finding of the study, and none changes what a pipeline retrieves or answers: no pipeline exists. The composition of the question sets is the owner's decision of 2026-11-27. The method of the draw and the seed are recorded as chosen before any draw, with no run behind them (constitution, Principle X).

## 1. Dependencies

**Decision**: No new dependency. Everything this feature adds uses the Python standard library: `hashlib`, `json`, `fractions`, `math`, `argparse`, `pathlib`, `dataclasses`, `re`.

**Rationale**: The feature reads and writes JSON files, sorts by a hash, and adds and divides small numbers. `uv.lock` stays as it is, so the pull request cannot change what the index build of spec 1 installs.

**Alternatives considered**:

- `numpy` or `pandas` for the means and percentiles: eight to four hundred numbers per run do not need them, and their percentile functions offer several methods, of which the spec fixes one (FR-016).
- `pydantic` or `jsonschema` for the check of a record: the check has to name each defect in words that the acceptance checks read (FR-022), and it compares across files (results against the question set, the summary against a recomputation). A schema covers the smaller half of that and adds a second way of saying what a record is.

## 2. The method of the draw: `sha256-order-v1`

**Decision**: A draw of *N* questions from a part with the seed *S* is made as follows.

1. The questions of the part are named by their question identifiers (FR-002).
2. For each identifier, its *draw key* is the SHA-256, written as 64 lower-case hexadecimal characters, of the UTF-8 bytes of the text `sha256-order-v1:<S>:<identifier>`. *S* is a whole number, zero or greater, written in decimal digits without a sign and without leading zeros. Example: `sha256-order-v1:7:hxa-001`.
3. The identifiers are put in ascending order of their draw key, compared as text. Two identifiers with the same key are put in ascending order of the identifier.
4. The draw selects the first *N* identifiers of that order.
5. In the record the selected questions stand in the order of the dataset: the parts in the order of the rule, and within a part by ascending row number. The order of step 3 is not recorded.

A rule that takes from several parts makes one draw per part, each with the same seed. The method is named in every record that draws (FR-003).

A reader can repeat a draw key with one command and compare:

```sh
printf 'sha256-order-v1:7:hxa-001' | sha256sum
# b007c1a99f194f36e77ddff1287444edf952051575fc10e8920235c10574b35a
```

**Rationale**:

- FR-004 requires that the same dataset, rule and seed give the same record on every machine and with every version of a tool. SHA-256 is a published standard with one result for a given input, so the draw depends on nothing but the identifiers, *N* and *S*. A random generator of a language or a library is defined by its implementation and may change between versions.
- The selection can be checked without the implementation: the testing agent writes the two example records marked "drawn" from the eight keys in [data-model.md](data-model.md), and a reader repeats any key with `sha256sum`.
- The key contains the name of the method, so a later method with another name gives other keys even with the same seed.
- For a fixed seed the questions drawn with *N* = 100 are a subset of those drawn with a larger *N*. Nothing in this feature uses that, and nothing is harmed by it.
- A draw of every question of a part selects all of them whatever the seed, which gives the example sets `harness`, `harness-hxc` and `example` a content that is known without computing a key.

**Alternatives considered**:

- The seeded random generator of the Python standard library, `random.Random(seed)`, with its functions for drawing and shuffling: its documentation promises the same sequence for a seed only for the basic generator, and says that the other functions, drawing and shuffling among them, may change between Python versions; the result would rest on the Python version, which FR-004 excludes.
- A random generator written out in the plan (for example a linear congruential generator with a Fisher-Yates shuffle): it meets FR-004, but a reader can only check it by running the same loop, and a mistake of one step changes every selection after it. With a key per identifier each question is decided on its own.
- A hash of the question text as the key: two rows with the same text would always fall into the same set. Whether a text repeats is a finding about the data that the check reports (FR-007, FR-032); it does not decide the draw.
- Every second row: reproducible, but not a random draw, and the order of the published file may follow the time or the topic.

## 3. The seed

**Decision**: `20261127` for both draws of the study, as the approved spec states. It is the day of the owner's decision, written as a number.

**Rationale**: A seed has to be fixed before the draw, and a date that everyone can see was fixed beforehand is not chosen for its result. The same seed for both draws is harmless: the keys of the two draws differ in the identifier.

**Alternatives considered**: a seed per set, or a small number such as 1 or 42: no advantage, and the spec already names the seed.

## 4. The question-set record

**Decision**: One file per question set, `<sets directory>/<version>.json`: one JSON document in a fixed, *canonical* form (keys in a fixed order, two spaces of indentation, UTF-8 without escaping of non-ASCII characters, one line feed at the end). The *fingerprint* of a question set is the SHA-256 of the bytes of its file. The fields are in [contracts/records.md](contracts/records.md).

- The default sets directory is `evals/golden/`. Another directory is named with `--sets-dir`.
- A version has the form of an index identifier of spec 1: lower-case letters, digits and single hyphens, at most 40 characters.
- The record holds no time and no commit of the code.
- `set build` writes the canonical form. `set check` accepts any JSON formatting of a record and judges its content; the fingerprint is always that of the bytes as they are.

**Rationale**:

- FR-004 asks for "the same record" everywhere. With one canonical form and nothing that changes from one production to the next, the same record means the same bytes, and "written once" (FR-005) can be decided by comparing bytes.
- A run names its question set by version and fingerprint (FR-019). A fingerprint of the file is the simplest thing a reader can verify: `sha256sum evals/golden/golden-001.json`.
- Because the record names no commit, it does not go stale when the code changes afterwards. This is what allows the real records to be produced early (plan.md, "How the work is delivered").
- One file per set and one directory for all sets keeps the complement rule simple: a held-out set names the golden set it complements by version, and the check finds it next to itself.

**Alternatives considered**:

- A fingerprint of the ordered question identifiers only: it would not notice a change of a gold article id in the record, and the gold article ids are what the metrics are computed with.
- One file for all three sets: a version would then cover three sets that are produced by three commands, and a run would have to name a set inside a file.
- A folder per version with the questions in JSON Lines: 200 to 300 short entries do not need it.

## 5. Where the three real records live

**Decision**: `evals/golden/golden-001.json`, `evals/golden/held-out-001.json` and `evals/golden/synthetic-001.json`. A `set build` with `--data-dir` is refused when its sets directory is `evals/golden`: that directory takes only sets of the pinned dataset.

**Rationale**: Principle III places the golden set in `evals/golden/` and asks that a held-out set is recorded in the repository in the same form; the approved spec names these three files. The refusal keeps an example set from ever standing next to the sets of the study.

**Alternatives considered**: a folder `evals/sets/`, with the name saying what it holds: it would contradict Principle III for the golden set, or split the three records over two folders while the complement rule wants them side by side.

## 6. The run record: three files

**Decision**: A run is the directory `<runs directory>/<run id>/` with three files, each written once:

| File | Holds | Form |
|---|---|---|
| `run.json` | The identity and the config | One JSON document |
| `results.jsonl` | One entry per question, in the order of the question set | JSON Lines |
| `summary.json` | The audit result and the numbers of the run | One JSON document |

The default runs directory is `evals/runs/`. The fields are in [contracts/records.md](contracts/records.md).

**Rationale**: The constitution lists four parts; identity and config are both written before the first question is asked and are read together, so they share a file. The results are the large part and are written one question at a time, which JSON Lines suits: a run that stops leaves complete lines. The summary is derived and stands apart, so that "recompute and compare" (constitution, "Run Record Format") is a comparison of one file with the other two. Judging (spec 4) adds files and changes none of these.

**Alternatives considered**:

- One JSON document for everything: a run of 200 questions with their contexts would be one object of several megabytes that has to be written at the end, and a later step could not add to it without rewriting it.
- A separate `config.json`: one more file with no reader that needs it alone.
- A database table for runs: the registry has to be readable in the repository and diffable in a pull request.

## 7. Exact numbers

**Decision**: Every number of a summary is computed with exact fractions and turned into a floating-point number once, at the end.

- `share_found` of a question is a fraction of two whole numbers. A mean is the exact sum of the fractions divided by their number.
- A price is read as the decimal number that the JSON text states (`0.02` is 2/100). The cost of an entry is the exact sum, over its token counts, of tokens × price ÷ 1,000,000. A total is the exact sum of the exact costs of the entries, recomputed from the token counts.
- A median of an even number of latencies is the exact mean of the two middle values; the 95th percentile is one of the recorded values.
- The result is written to JSON in the shortest form that reads back as the same number.

The check of a run record therefore compares numbers for equality, with no tolerance.

**Rationale**: SC-006 and the constitution require that recomputing a summary gives the same numbers. Sums of floating-point numbers depend on the order of the additions; exact fractions do not, and the conversion of a fraction to the nearest floating-point number has one result. The pipeline of spec 3 obtains its numbers from the same functions (section 8), so a record written by the pipeline and a hand-written example are held to the same equality.

**Alternatives considered**:

- Floating-point sums with a tolerance in the check: a tolerance has to be chosen, and a stale summary that is wrong by less than the tolerance would pass.
- Storing numerators and denominators instead of the mean: exact as well, but a reader of `summary.json` wants the number, and the denominators are stored anyway (FR-012).
- `decimal` for costs only: fractions cover costs and shares with one rule.

## 8. The one computation, and the modules

**Decision**: Three new modules.

| Module | Holds |
|---|---|
| `questionsets.py` | The question identifier, the draw, the record of a question set, its production and its check; the commands `set build` and `set check` |
| `metrics.py` | The one computation of FR-017: per-question metrics, the breakdowns of a run, the cost of an entry, the pairwise comparison. Pure functions on plain data; it reads no file |
| `runs.py` | The run identifier, reading a run record, the summary document, the check of a record and of the registry; the commands `run report`, `run check` and `run compare` |

The Python names that the tests and spec 3 use are fixed in [contracts/harness.md](contracts/harness.md). Spec 3 calls `runs.summary_document(...)` to obtain the document it writes as `summary.json`; `runs.examine(...)` calls the same function and compares.

**Rationale**: FR-017 asks for one computation used when a run is recorded and when it is checked. A module without file access can be tested on plain values and cannot disagree with itself. Naming the functions in the plan lets the testing agent write unit tests before the code exists without inventing an interface that the coding agent then has to match by guessing.

**Alternatives considered**:

- The computation inside the command functions: spec 3 would have to call a command or copy the arithmetic.
- A class `Run` with methods: nothing here has state that changes; functions on the documents are enough.

## 9. A config parameter

**Decision**: For FR-023 a *parameter* is a leaf of the `config` object of `run.json`, named by the path of keys to it joined with dots, for example `reranking.enabled`. Objects are descended into; a list, a text, a number, a truth value and `null` are leaves. The object `config.experiment` is not compared. Two configs differ in a parameter when its value differs or when only one of them has it.

An experiment run names its baseline, the parameter, the baseline's value and its own value in `config.experiment`. The check fails when the set of differing parameters is not exactly that one parameter, or when a recorded value is not the value in the respective config.

**Rationale**: Principle VI asks for exactly one differing parameter, named with the old and the new value. A dotted path names a setting in words a reader can find in the file. Treating a list as one leaf means that a change of the price list or of a list of prompts is one parameter, which is how a reader would count it.

**Alternatives considered**:

- Top-level keys as parameters: a change of `retrieval.top_k` and of `retrieval.method` in one run would count as one.
- Comparing list elements one by one: the "parameter" would be `prices.0.usd_per_million_input_tokens`, and inserting one entry would shift every index after it.

## 10. What the check of a run record does not need

**Decision**: `run report`, `run check` and `run compare` read the run records and the question-set records and nothing else. They do not read the data directory, the store or the environment's settings. They do read `dataset.json`, as every command does (contracts/cli.md of spec 1, "Where a command is typed"); its content is not used.

The check of a run record compares the config's question set with the record of the set (version, role, fingerprint). It does not repeat the check of the set against the dataset.

**Rationale**: FR-031. The gold article ids are in the question-set record (the owner's answer of 2026-11-26), so the metrics need no dataset. That a set matches the dataset is the task of `set check` and of the audit, which do need the data directory.

**Alternatives considered**: repeating `set check` inside `run check` when a data directory happens to be present: the outcome of a check would then depend on what lies in `data/`.

## 11. The audit takes a question set by version

**Decision**: `audit_index` and `require_passed_audit` of spec 1 get two keyword arguments, `question_set` (a version) and `sets_dir`. With `question_set` the audit, after the dataset check, reads the record, checks it against the same data directory with the check of `set check`, and uses its questions and gold article ids as the question set. The command gets the options `--set VERSION` and `--sets-dir DIR`. The audit result gains three fields inside `question_set`: `version`, `role` and `fingerprint`, present only when a question set was named. Without `question_set` everything is as before (the owner's answer of 2026-11-26).

The edits of spec 1's contracts are made in place and marked with the date: `contracts/cli.md`, `contracts/audit-gate.md` and `contracts/records.md` of `specs/001-corpus-and-audit/`.

**Rationale**: FR-008. Spec 3 will call the gate with one argument more and get a result that names the set, which the summary of the run then carries (FR-021). The existing argument `questions` stays for callers that bring their own pairs; a caller that names a set cannot pass pairs that differ from the record.

**Alternatives considered**:

- A new command `set audit`: two commands would then print an audit verdict, and the gate would still need the new argument.
- Passing the pairs through `questions` and the name through a second argument: the name and the questions could disagree.

## 12. Tests: names, markers, order

**Decision**: The acceptance tests of this feature are `tests/acceptance/test_s2_ac_NNN_<words>.py`, one per check. The three markers of spec 1 stay as they are.

| Checks | Markers | First tier that runs them |
|---|---|---|
| AC-003 to AC-008, AC-012 to AC-036, AC-042 to AC-046 | none | workspace |
| AC-010, AC-011 | `store`, `provider` | example |
| AC-001, AC-002, AC-037 to AC-040 | `real_data` | full |
| AC-009, AC-041 | `real_data`, `store` | full |

The 36 checks without a marker are AC-003 to AC-008, AC-012 to AC-036 and AC-042 to AC-046. They run in an agent's workspace, in `checks` for every pull request and in both scopes of `acceptance`.

**Rationale**:

- Spec 1 already has `test_ac_001_…` to `test_ac_014_…`; pytest cannot hold two test files of the same name in folders without packages. The prefix `s2` keeps the number of the check in the name.
- pytest runs the files of a folder in the order of their names, so in a `full` run the tests of spec 1 come first: the dataset is fetched (its AC-001) and the index `example` is built (its AC-005) before the tests of this feature need them. Within this feature the order of the names is the order that the first `full` run needs: AC-001 writes `golden-001` before AC-002 checks it and AC-009 audits with it, and AC-037 and AC-038 write the two held-out sets before AC-039 to AC-041 read them.
- AC-010 and AC-011 build the index `example`; when a test of spec 1 has built it in the same run, nothing is embedded.

**Alternatives considered**: a folder per spec with `__init__.py` files: it would change how the existing tests are imported; a marker `harness`: nothing needs to select these tests apart from the others.

## 13. How the three real records reach the branch

**Decision**: The acceptance workflow, scope `full`, records them, by the pattern that spec 1 uses for an index.

1. The tests of AC-001, AC-037 and AC-038 run `set build` without `--data-dir`. On the first run this writes up to three new files under `evals/golden/`; on every later run the files are in the checkout and the builds report "already written".
2. After the tests, `check-worktree.sh` allows, besides a new build record, new files `evals/golden/<version>.json`. A changed file under `evals/golden/` is still an error.
3. When every test passed and new question-set records exist, the job copies them to a folder outside the checkout, runs `set check` for each, publishes the result lines of each check (role, numbers per part, single-article and multi-article) as a notice, and saves the files as an artifact.
4. A second job, the only one with the right to write to the repository, adds the files to the branch in one commit. It runs no code of the repository and never runs for `main`.

No provider is called for any of this: the dataset host is read, and the index `wixqa-001` is restored from its snapshot for AC-009 and AC-041.

**Rationale**: The owner decided on 2026-11-24 that commands which need the dataset host run on GitHub Actions. The records then have to travel from a job to the branch, and the index records of spec 1 already travel that way with a path that was reviewed and has run. Recording only after every test passed means that a record reaches the branch only when its check and its audit passed in the same run.

**Alternatives considered**:

- A workflow of its own for question sets: a second place that fetches the dataset and installs the project, for three small files.
- Uploading the records as an artifact and committing them by hand: the owner would have to do it, and a hand-made commit is what "produced by its rule and never typed by hand" (FR-004) wants to avoid seeing.
- Producing the records in an agent's workspace: the workspace cannot reach the dataset host.

## 14. Line endings of recorded files

**Decision**: `.gitattributes` gets two lines, `evals/golden/** -text` and `evals/runs/** -text`.

**Rationale**: The fingerprint of a question set is taken of the bytes of its file, and a run names that fingerprint. On a checkout that converts line endings the bytes would change and every run would fail its check. The example data under `tests/data/` already has this protection.

**Alternatives considered**: a fingerprint of the parsed content: it needs a canonical form anyway, and a reader could no longer verify it with `sha256sum`.

## 15. Output formats

**Decision**: In the output of a command, a mean and a share are printed with four digits after the decimal point, a cost in US dollars with eight (as `index build` prints it), a latency in seconds with three. A number that is undefined is printed as `undefined`. The records hold the full numbers. The lines are in [contracts/cli.md](contracts/cli.md).

**Rationale**: The acceptance checks of the spec read these lines with these digits.

## Facts checked on 2026-11-27

| Fact | How it was checked |
|---|---|
| The draw key of `hxa-001` with the seed 7 is `b007c1a9…b35a` | Computed twice in the planning workspace: with `printf 'sha256-order-v1:7:hxa-001' \| sha256sum` (GNU coreutils) and with `hashlib` of CPython 3.14.6; both give the same 64 characters |
| The eight draw keys and the two selections in data-model.md | Computed with `hashlib` of CPython 3.14.6 in the planning workspace |
| Every number of the four example summaries in contracts/records.md and data-model.md | Computed with `fractions.Fraction` from the tables of the spec, in the planning workspace; the printed forms agree with the lines that AC-012 to AC-016, AC-042 and AC-046 expect |
| `float(Fraction(19, 36))` is `0.5277777777777778`, and JSON text written by `json.dumps` reads back as the same number | Tried on CPython 3.14.6 |
| `Fraction("0.02")` is 1/50: a price read from its decimal text is exact | Tried on CPython 3.14.6 |
| The project's environment has CPython 3.14.6, and the standard library holds every module of section 1 | `.venv/bin/python --version`; the modules were imported |
| `carry_out` in `src/wixqa_rag/cli.py` stops a command when `dataset.json` is not in the current directory | Read in the code at commit `21be7ad` |
| `audit_index` and `require_passed_audit` take `questions` as pairs of an identifier and its article ids | Read in `src/wixqa_rag/audit.py` at commit `21be7ad` |
| `check-worktree.sh` allows one kind of new file, `evals/indexes/<index>/build.json`, and only with `--allow-new-build-record` | Read in `.github/scripts/check-worktree.sh` at commit `21be7ad` |
| The audit of all 6,621 questions against `wixqa-001` found no question without `article_ids` and no unknown reference | `evals/indexes/wixqa-001/audit.json` |

## Not checked

| Point | Why not | Confirmed by |
|---|---|---|
| How many of the 200 questions of `golden-001` and of `held-out-001` are single-article and how many multi-article | The workspace cannot reach the dataset host | The first `full` run: the lines of `set check` for both sets |
| Whether a question text repeats within a set, or occurs in both the golden set and the held-out set | The same | The same lines |
| That every synthetic question has exactly one gold article, as the dataset card says | The same | The lines of `set check --version synthetic-001` |
| That the job which records the question sets can push to the branch | It needs GitHub | The first `full` run after the DevOps agent's change |
| The wording of the Python documentation on which functions of `random` keep their results across versions (section 2, first alternative) | The workspace did not read the documentation on the day of the plan; the statement is from memory. The decision does not depend on it: the chosen method uses no random generator | Nothing to run; a reader can look it up under "Notes on Reproducibility" of the module `random` |
| That a draw of 100 from 200 identifiers with the seed `20261127` gives 100 questions per part | Follows from the method; computed here for made-up identifiers of the same form, not for the dataset | AC-001 |

## Constitution

This plan leads to no amendment. It is written against version 1.2.0. Two readings of the constitution that the approved spec states under "Assumptions" stay as they are: the method of the median and of the 95th percentile (FR-016), and the judge's numbers, which spec 4 adds in files of its own.
