# Research: Corpus and audit

**Feature**: `001-corpus-and-audit` | **Date**: 2026-11-24 | **Plan**: [plan.md](plan.md)

Each section records one choice of the plan: what was decided, why, and what else was considered. Facts about tools and services were checked on 2026-11-24 and are listed with their sources under "Facts checked". What could not be checked from the planning workspace is listed under "Not checked"; the first runs confirm it.

None of these choices is a finding of the study. The tooling choices do not change what the pipeline retrieves or answers. The splitting rule, the embedding model and the vector store do, and they are recorded as chosen as a starting point, with no run behind them (constitution, Principle X).

## 1. Python version

**Decision**: Python 3.14. `pyproject.toml` states `requires-python = ">=3.14,<3.15"`, and `.python-version` holds `3.14`.

**Rationale**: Python 3.14 was first released on 2025-10-07, is in its bugfix phase and is supported until 2030-10. A scratch project on CPython 3.14.6 resolved and installed every planned dependency from prebuilt packages (see "Facts checked").

**Alternatives considered**:

- Python 3.15: its first release was scheduled for 2026-10-01, at most eight weeks before this plan. A version that new has little maintenance history, and uv 0.11.32 listed no final 3.15 build for Linux on the day of the plan.
- Python 3.13: it works, and its support ends a year earlier. A project that starts now has no reason to start on the older version.

## 2. Dependency manager and lock file

**Decision**: uv. Dependencies are declared in `pyproject.toml` and pinned in `uv.lock`, which is committed. The environment is created with `uv sync --locked`. `pyproject.toml` also states the range of uv versions that may be used (`[tool.uv] required-version`). The package is built with uv's own build backend, `uv_build`.

**Rationale**: The constitution requires a lock file committed to the repository. uv installs the interpreter named in `.python-version`, creates the environment and installs exactly what the lock file lists, with one tool and one command. Its lock file covers every platform, so the CI job and a reader's computer install the same versions. `uv sync --locked` fails when the lock file no longer matches `pyproject.toml`, so CI cannot run on dependencies that are not locked.

**Alternatives considered**:

- pip with pip-tools: two tools and a separately installed interpreter, and the compiled requirements file depends on the platform and the Python version it was compiled on.
- Poetry or PDM: both would do the job. uv was preferred because the same tool also provides the interpreter, and its CI setup is one action and one command.
- conda: the project has no dependency that needs it. PostgreSQL runs as a container.

## 3. Test runner and kinds of tests

**Decision**: pytest. Tests live in three folders and are selected by three markers.

| Folder | What it tests | What it needs |
|---|---|---|
| `tests/acceptance/` | One test per acceptance check: it runs the command line of the check as written, through a POSIX shell, and checks the exit code, the output lines and the files | Depends on the check |
| `tests/integration/` | Building and auditing against a real store, with an embedder double (section 17) | PostgreSQL with pgvector |
| `tests/unit/` | The splitting rule, the dataset check, the records, the output lines, the exit codes | Nothing |

| Marker | Meaning |
|---|---|
| `store` | Needs a PostgreSQL with pgvector, reached through `DATABASE_URL` |
| `provider` | Calls the embedding provider and needs `OPENAI_API_KEY` |
| `real_data` | Needs the dataset host: it fetches or reads `Wix/WixQA` |

| Tier | Selection | Where it runs | How it starts |
|---|---|---|---|
| workspace | `-m "not store and not provider and not real_data"` | Anywhere, also in an agent's workspace | By the agent |
| checks | `-m "not provider and not real_data"` | GitHub Actions, with PostgreSQL | Automatically, for every pull request |
| example | `-m "not real_data"` | GitHub Actions, with PostgreSQL and the provider key | By hand |
| full | every test | GitHub Actions, with PostgreSQL and the provider key | By hand |

Markers of the acceptance checks:

| Checks | Markers | First tier that runs them |
|---|---|---|
| AC-003, AC-007 | none | workspace |
| AC-012, AC-014 | `store` | checks |
| AC-005, AC-006, AC-009, AC-010, AC-011, AC-013 | `store`, `provider` | example |
| AC-001, AC-002 | `real_data` | full |
| AC-004 | `real_data`, `store`, `provider` | full |
| AC-008 | `real_data`, `store` | full |

The four real-data tests have no fixture that fetches or builds. In one run they execute in the order of their numbers, and each relies on what the one before it left, as the checks of the spec do: AC-002 on the fetch of AC-001, and AC-008 on the index that AC-004 built or that the workflow restored from its snapshot. A real-data test can therefore be run alone before its command exists, to show that it fails, without fetching or building anything.

Tests are written and shown to fail story by story, before the implementation of that story. The red runs of the first two stories cannot call the provider, because the command that embeds does not exist yet. The red run of the third story embeds only the example dataset: its checks build the example index before they reach the command that is missing. The one exception is AC-008. When its test is written, the command `index build` already exists, and a run with the scope `full` would build the real index and lose it; the red run of AC-008 is therefore made in the agent's workspace, where the test fails because the command `index audit` does not exist.

An agent may also run the `store` tests in its own workspace against a PostgreSQL started from the Python package `pgserver`, which brings PostgreSQL 16 with pgvector 0.6 and needs no installation rights. This shortens the loop while code is written. The run that counts is the one on GitHub Actions, with the planned versions.

**Rationale**: Markers give the four tiers with one test tree, and fixtures hold the store connection and the example data. Because an acceptance test runs the command line of the spec unchanged, a check and its test cannot drift apart.

**Alternatives considered**:

- `unittest` from the standard library: no dependency, but selecting tiers and sharing fixtures would need hand-written code.

## 4. CI system

**Decision**: GitHub Actions (the owner's decision of 2026-11-24), with two workflows.

- `.github/workflows/checks.yml` runs for every pull request and for every push to `main`: lint, format check and the "checks" tier of tests. It uses no secret.
- `.github/workflows/acceptance.yml` runs only when a person starts it, with a scope, `example` or `full`. It receives `OPENAI_API_KEY` from the repository's secrets. It is started in one of two ways: with the "Run workflow" button (`workflow_dispatch`), or by putting the label `acceptance:example` or `acceptance:full` on the pull request.

Both run on the GitHub-hosted runner `ubuntu-24.04`, start PostgreSQL as a service container (section 6), install uv and run `uv sync --locked`. Every action is pinned to a full commit SHA. The acceptance job has a time limit of 60 minutes, and two acceptance runs for the same branch never run at the same time.

**Rationale**:

- Two workflows keep the secret away from everything that starts automatically. The label starts the workflow through the `pull_request` event, not through `pull_request_target`, so a pull request from a fork never receives the secret, and only a person who may label pull requests can start a run.
- Two ways to start are needed because GitHub shows the "Run workflow" button only for a workflow file that is on the default branch, and its documentation states the same of the event. Until this feature is merged, the workflow file exists only on the feature branch. A label on the pull request starts the version of the workflow that the pull request contains. After the merge, and in a reader's copy of the repository, the button works.
- Agents reach this repository only through its REST API and cannot open log pages. The workflow therefore publishes what matters as data that the API returns: the run and each step have a conclusion, every failed test is published as an annotation, and the verdict lines of the real-data commands are published as notices. The annotations are made from pytest's JUnit report by a step of the workflow, so no further dependency is needed.
- A workflow fails when its tests added or changed a file outside the ignored folders. A test must never leave a file under `evals/`: in the scope `full`, a new build record there is what starts the recording of an index (section 7). The acceptance workflow removes its label when it finishes, so that adding the label again starts the next run.

**Alternatives considered**:

- Runs on the owner's computer: ruled out by the owner's decision; nothing is installed there.
- One workflow for everything: the secret would be available to runs that nobody started.
- Starting only with `workflow_dispatch`: before the first merge this depends on behaviour that GitHub does not document (a workflow file outside the default branch can sometimes be started through the API after it has run once).
- A first pull request that only adds the workflow files to `main`: the constitution allows one pull request per slice, but this adds a merge for the owner and splits one spec over two reviews.

## 5. Lint and format

**Decision**: Ruff: `ruff check` and `ruff format --check` in `checks.yml`. No type checker for now.

**Rationale**: One tool with one block of settings in `pyproject.toml`, and it runs in seconds. It keeps the diffs that the code review agent reads free of style noise.

**Alternatives considered**:

- Black with Flake8: two tools for the same result.
- A type checker such as mypy: useful once there is more code. A later spec can add it; here it would be a second gate before any code exists.

## 6. Where the vector store runs

**Decision**: PostgreSQL 18 with pgvector, started for each CI job as a service container from the image `pgvector/pgvector`, with a tag of the form `<pgvector version>-pg18`, pinned by tag and digest. The newest pgvector release on the day of the plan is 0.8.7. The database accepts connections without a password (`POSTGRES_HOST_AUTH_METHOD=trust`); it is reachable only inside the job and is discarded with it. The commands reach it through `DATABASE_URL`.

**Rationale**:

- The owner decided that the commands run on GitHub Actions and that nothing is installed on the owner's computer. A service container is how a job there gets a database.
- A reader repeats it with one `docker run` of the same image.
- No database password exists, so there is none to commit and none to store as a secret (constitution, "Stack").
- PostgreSQL 18 is the newest major version with a year of minor releases behind it. PostgreSQL 19 was at release candidate 1 on 2026-10-15.

**Alternatives considered**:

- A hosted PostgreSQL that stays up between jobs: one more account and one more secret for the owner, and a cost or a size limit to watch. A reader could not reach the owner's database, so a reader's repeat would not use the same store anyway.
- PostgreSQL installed on the runner by its package manager: the version would follow the runner image, and pgvector would have to be installed in every job.

## 7. How an index is kept between jobs

**Decision**: The index built from the pinned dataset is kept as a database dump, called its *snapshot*. After a successful `full` run that built a new index, the acceptance workflow

1. audits the index and writes the result to `evals/indexes/<index>/audit.json`;
2. dumps the schema of the index with `pg_dump` in custom format, using the `pg_dump` inside the service container;
3. saves the dump and the two record files as an artifact that is kept for 7 days, so that a failure in a later step loses nothing;
4. creates a GitHub release with the tag `index-<index>` on the commit the index was built from, and attaches the dump to it;
5. writes `evals/indexes/<index>/snapshot.json`: the file name, its size, its SHA-256, the PostgreSQL and pgvector versions, the repository and the release tag;
6. commits `build.json`, `audit.json` and `snapshot.json` to the branch the run was started for.

These steps never run for `main`. `main` changes only through pull requests (constitution, "Development Workflow"), so a run for `main` that built a new index stops with a message: a new index is built on a branch and reaches `main` through its pull request.

Every later job that needs the index downloads the dump named in `snapshot.json`, compares its SHA-256, restores it with `pg_restore` into its own PostgreSQL, and audits the index before anything else uses it.

**Rationale**:

- The store of a CI job disappears with the job. Without a snapshot, every job would embed the corpus again, and the study would have no way to show that two jobs used the same vectors. A baseline run and an experiment run must differ in one parameter only (Principle VI), so they have to read the same index.
- The spec treats an index as something that stays: its build record is written once (FR-010), and a second build under the same identifier embeds nothing (FR-008). The snapshot lets both statements hold while the store itself lives for one job: the record in the repository describes a file that exists and has a fingerprint.
- The audit of Principle I keeps its purpose. It runs after every restore, against the store that the job then queries, so a restore that lost rows is caught.
- Release assets fit the size. The dump of this index is estimated at about 200 MB; one release asset may be up to 2 GiB, and GitHub sets no limit on the total size of a release or on downloads.
- No new command is needed. `pg_dump` and `pg_restore` belong to PostgreSQL, and the commands of the application stay exactly those of the spec. After a restore, `index build --index <index>` reports the index as already complete, so AC-004 and AC-008 can be repeated at no provider cost: by the study, and by a reader once the repository is public.

**Alternatives considered**:

- Building again in every job: the provider is paid each time, the job takes longer, and every job holds different vectors.
- A workflow artifact in place of a release asset: artifacts expire, and in a private repository they count against the storage included in the plan (500 MB on the Free plan).
- The Actions cache: GitHub removes cache entries that have not been used for some time, so it cannot hold something that must stay.
- A snapshot format of our own, with export and import commands in the application: more code, and two commands that the spec does not have.
- Git LFS or the repository itself: hundreds of megabytes in the history or in a storage quota.
- A hosted database: see section 6.

## 8. Layout of an index in the store

**Decision**: One PostgreSQL schema per index. An index identifier consists of lower-case letters, digits and single hyphens, and has at most 40 characters; the schema name is `idx_` followed by the identifier with every hyphen replaced by an underscore (`wixqa-001` becomes `idx_wixqa_001`). The schema holds two tables: `passages` (article id, passage number, text, embedding of type `vector(1536)`) and `build` (one row: the build record and the time of completion). The article ids of an index are the distinct `article_id` values of its `passages` table. Every SQL statement of the project lives in one module, `store.py`; retrieval (spec 3) is added to that module and reads the same table.

A build runs in one database transaction: it creates the schema and the tables, inserts every passage, inserts the `build` row last, and commits. This feature creates no approximate-search index; how an index is searched is decided in spec 3.

**Rationale**:

- FR-011: the audit reads the table that retrieval will read, and one module holds both statements.
- FR-009: the `build` row is the mark of completion, and it is written only after every article has been processed. Because the build is one transaction, a build that stops part-way leaves nothing in the store.
- A schema is a unit that `pg_dump` and `pg_restore` handle (section 7): one index, one dump.
- An index made later with another embedding model brings its own table with its own vector size. Nothing is shared between indexes.
- The fixed alphabet maps an identifier to a schema name one-to-one and without quoting, because an identifier cannot contain an underscore.

**Alternatives considered**:

- One shared `passages` table with an index column: the simplest SQL, but dumping one index needs a row filter that `pg_dump` does not have, and every index would have to share one vector size.
- Inserting in committed batches with a status column: a stopped build would leave an unusable identifier behind, and the spec has no command that removes an index.
- pgvector's Python adapter with NumPy: not needed. Vectors are sent to PostgreSQL in pgvector's text form, which saves two dependencies.

## 9. Fetching the dataset

**Decision**: `dataset fetch` downloads the four published files over HTTPS from `https://huggingface.co/datasets/Wix/WixQA/resolve/<revision>/<path>`, with the Python standard library. Each file is downloaded under a temporary name, its rows are counted and its SHA-256 is computed, and only then is it moved into `data/wixqa/<revision>/`. `manifest.json` is written last. A fetch over a complete, matching copy downloads nothing.

**Rationale**: The dataset is four JSON Lines files, 60.3 MB together. An address with a commit hash returns the file as it was at that revision, and a reader can repeat the download with any tool. The files stay exactly as published, which is what the fingerprints are taken of (FR-003, FR-005). One directory per revision means that a later change of the pinned revision never overwrites data. Writing the manifest last means that an interrupted fetch never looks complete.

**Alternatives considered**:

- `huggingface_hub`, the hub's client library: a dependency with its own tree of dependencies, for four downloads.
- `datasets`: it loads the data into a cache format of its own. The published files, which the fingerprints describe, would no longer be what the commands read.

## 10. Pinned revision

**Decision**: `d662dc42479c14e202eccd832f8c4b66a035c4cc`, recorded in `dataset.json` at the repository root together with the name, the role, the path and the row count of each part.

**Rationale**: It is the newest of the 16 commits of `Wix/WixQA` on 2026-11-24, as the spec assumes, and it was made on 2025-07-02. The data files were last uploaded on 2025-05-14; the three commits after that have the message "Update README.md".

The row counts written into `dataset.json` are those of the dataset card: 6,221, 200, 200 and 6,221. The first fetch confirms them. If a count differs, the fetch fails and names both numbers, and the spec's assumption applies: the finding is recorded, `PROJECT.md` is corrected, and the spec is amended with the owner's approval.

**Alternatives considered**:

- The branch name `main` in place of a commit hash: a branch moves, so two operators could get different data.

## 11. Data directory, manifest and fingerprints

**Decision**: A *data directory* is a folder that holds the part files and a `manifest.json`. The manifest gives the dataset name, the revision, and for each part its name, its role (`corpus` or `questions`), its path, its row count, its size in bytes and its SHA-256. `dataset check` compares the files with the manifest and, for the default directory, the manifest with `dataset.json`. The example datasets under `tests/data/` are data directories of the same form, each with one corpus part, `ex`, and one question part, `exq`. `.gitattributes` marks the files under `tests/data/` so that Git never converts their line endings.

**Rationale**: FR-003 and FR-004 need a recorded fingerprint and a recorded row count for every part. SHA-256 is in the standard library, and the constitution already uses it for answers. Because the parts are read from the manifest, the same code checks the published dataset with its four parts and an example with its two: the commands have no second path for test data. A fingerprint is taken of bytes, so the example files must have the same bytes on every platform; on Windows, Git would otherwise change their line endings on checkout.

**Alternatives considered**:

- Part names fixed in the code: every example would have to imitate the four published names, and the question names of the spec (`exq-001` to `exq-003`) could not be produced by the rule of section 14.

## 12. Splitting rule of the first index

**Decision**: The rule `line-pack-v1` with the parameter `max_chars = 2000`.

1. Line breaks are normalised: `\r\n` and `\r` become `\n`.
2. The article's `contents` is cut at every `\n` into lines. Each line is stripped of leading and trailing whitespace, and empty lines are dropped.
3. A line longer than `max_chars` characters is cut into pieces: at the last whitespace within its first `max_chars` characters, or after exactly `max_chars` characters when it has no whitespace there. Each piece is stripped, and the cutting repeats on the rest.
4. The lines and pieces are packed in order. The next one joins the current passage, after a `\n`, when the passage stays within `max_chars` characters; otherwise it starts a new passage.
5. The passages of an article are numbered from 0. An article without any non-empty line produces no passage.

Length is counted in Unicode characters, and whitespace is every character that Python's `str.isspace` accepts. The text of a passage is what is embedded and what is stored, with nothing added.

**Status**: chosen as a starting point, no run (spec, "Evidence"). Passage size, overlap and the article title at the start of a passage are candidates for later experiments.

**Rationale**:

- The rule uses characters and lines only, so it gives the same passages in every environment. It needs no tokenizer and loads no file at run time.
- It respects the provider's limit by arithmetic. A character costs at most four tokens, because a character is at most four bytes in UTF-8 and a token of a byte-level tokenizer covers at least one byte. A passage of 2,000 characters is therefore at most 8,000 tokens, below the limit of 8,192 tokens per input.
- 2,000 characters of English text are roughly 400 to 500 tokens.
- Whole lines keep a heading or a step of an instruction in one piece wherever it fits.
- The name carries a version. Whenever the output of the rule could change, the rule gets a new name, and a unit test pins the output of `line-pack-v1` on fixed inputs.

**Alternatives considered**:

- Windows of a fixed number of tokens, with overlap: it needs a tokenizer package and its vocabulary file, and it cuts through words and sentences.
- Splitting into sentences with a language library: a heavier dependency, and its output can change with the library's version.
- One passage per article: an article longer than the provider's limit for one input could not be embedded whole, and one vector would have to stand for an article that covers several topics.
- Overlap between passages: left to an experiment, so that its effect is measured on its own.

## 13. Embedding calls, limits and cost

**Decision**: OpenAI's Python library, `openai`. The model is `text-embedding-3-small` with its default vector size, 1536. Each passage is one input, and its text is sent unchanged. Requests are sent one after another; one request carries at most 96 passages and at most 75,000 characters. The library's built-in retries, with a raised retry count, handle rate-limit answers and temporary errors. Any other error stops the build, and the transaction is rolled back.

The number of tokens embedded is the sum of `usage.total_tokens` over the responses. The cost is that number multiplied by the price. The price, 0.02 US dollars per million tokens, is kept in the code next to the model name, with the date on which it was read, and it is copied into every build record. The record stores the model name as requested and as the provider's response reports it.

**Rationale**:

- The provider accepts at most 2,048 inputs and at most 300,000 tokens in one request. By the bound of section 12, 75,000 characters are at most 300,000 tokens, so no request can exceed a limit, whatever the text is.
- The usage that the provider reports is the number the provider charges for.
- The official library brings retries that wait, time limits and typed errors.
- Rate limits set the duration. For its embedding models the provider lists 1,000,000 tokens per minute at usage tier 1 and 40,000 on the free tier. The corpus is estimated at 10 to 14 million tokens, so a full build needs at least 10 to 14 minutes at tier 1 and several hours on the free tier. The full build therefore assumes usage tier 1, which the provider grants after 5 US dollars have been paid.

**Alternatives considered**:

- Plain HTTPS calls with the standard library: the waiting and retrying would be written by hand.
- The provider's batch interface: results arrive later, which does not fit a job that builds and audits in one go.
- Several requests at the same time: not needed. The rate limit sets the duration, not the number of requests in flight.

## 14. Naming a question before spec 2

**Decision**: The question files carry no identifier: a row has `question`, `answer` and `article_ids`. Until spec 2 fixes the form of a question identifier, this feature names a question by its part and its row: `<part>-<row>`, where the row is counted from 1 in file order and written with at least three digits. Examples: `wixqa_expertwritten-017`, `wixqa_synthetic-6221`, `exq-003`.

**Rationale**: FR-013 requires the audit to list question and article pairs, so a question needs a name. At a pinned revision with checked fingerprints, the position of a row never changes. The audit accepts its question set as an argument (see [contracts/audit-gate.md](contracts/audit-gate.md)), so the golden set of spec 2 can bring its own identifiers without a change to the audit.

**Alternatives considered**:

- A hash of the question text: stable across revisions, but unreadable in a report, and two rows with the same text would collide.
- An `id` field read only when a row has one: the examples would use a path through the code that the published data never uses.

## 15. Records, their places, and "written once"

**Decision**:

| Record | Written by | Place | In version control |
|---|---|---|---|
| Pinned revision | an agent, in a pull request | `dataset.json` | yes |
| Manifest of the fetched dataset | `dataset fetch` | `data/wixqa/<revision>/manifest.json` | no |
| Manifest of an example dataset | the testing agent | `tests/data/<name>/manifest.json` | yes |
| Build record, pinned dataset | `index build` without `--data-dir` | `evals/indexes/<index>/build.json` | yes |
| Build record, other data | `index build` with `--data-dir` | `data/indexes/<index>/build.json` | no |
| Audit result | `index audit` | the file given with `--json`; otherwise `data/audits/<index>/<time>.json` | no, unless `--json` points into `evals/` |
| Audit made after the build | the acceptance workflow | `evals/indexes/<index>/audit.json` | yes |
| Snapshot record | the acceptance workflow | `evals/indexes/<index>/snapshot.json` | yes |

The build record is also stored inside the index, in the `build` table. A build writes the record file under a temporary name, commits the transaction, and then gives the file its final name; a failure before the commit therefore leaves neither an index nor a record.

"Written once" (FR-010) is read strictly: a build never overwrites a build record. `index build` therefore decides as follows.

| Index in the store | Build record file | Corpus and settings | What `index build` does |
|---|---|---|---|
| complete | present, equal to the record in the store | same | reports the index as already complete; embeds nothing |
| complete | absent | same | writes the file from the record in the store; reports the index as already complete |
| complete | present, different from the record in the store | any | refuses: the file and the index do not belong together |
| complete | any | different | refuses: the identifier exists with another corpus, or with other settings |
| present, without its `build` row | any | any | refuses: the identifier exists and is not complete |
| absent | present | any | refuses: a record of this identifier exists, and the store does not hold the index |
| absent | absent | any | builds |

"Same corpus and settings" means: the same SHA-256 of the corpus file, the same embedding model and vector size, and the same splitting rule with the same parameters.

**Rationale**: The constitution states for runs that an identifier is never reused and that recorded files are never edited; the same holds here for indexes. The sixth row protects a paid job: if a restore failed without notice, the build would otherwise embed the whole corpus again and leave a record that contradicts the one in the repository. Keeping the record inside the index lets a restored snapshot be compared with the record in the repository.

**Alternatives considered**:

- Overwriting the record when the store does not hold the index: a record would silently change its start time and its cost, and the vectors would differ from those the earlier runs used.
- The record only in the store: the repository would not show what an index is made of.

## 16. Command line and exit codes

**Decision**: `argparse` from the standard library. The package is `wixqa_rag` and runs as `python -m wixqa_rag`, with the two groups `dataset` and `index`. Result lines go to standard output and progress messages to standard error. The last line of the output is the verdict. Exit code 1 is reserved for a difference that a check or an audit found; every other reason for not finishing, including an error the program did not expect, ends with exit code 2 and a verdict of "not carried out". The details are in [contracts/cli.md](contracts/cli.md).

**Rationale**: FR-014 requires three outcomes that a program can tell apart. An uncaught Python error would end with exit code 1 and look like "a difference was found". Four commands with a handful of options do not need a command-line library.

**Alternatives considered**:

- Click or Typer: a dependency for something the standard library does.

## 17. Embedder double for tests

**Decision**: The function that builds an index takes the embedder as a parameter. Integration tests pass a double that returns fixed vectors and reports the model name `embedder-double`. The command line has no option and reads no setting that selects a double: `python -m wixqa_rag index build` always calls the provider.

**Rationale**: Integration tests cover what the acceptance checks cannot reach at no cost, such as a build that stops in the middle. A switch on the command line could one day produce an index of made-up vectors with a record that looks real, so there is none.

**Alternatives considered**:

- Recorded provider responses replayed in tests: the recordings would have to be kept in step with the example data and with the provider's library.

## Facts checked on 2026-11-24

| Fact | Source |
|---|---|
| Python 3.14: first release 2025-10-07, bugfix phase, end of life 2030-10. Python 3.15: first release scheduled for 2026-10-01 | Python developer guide, "Status of Python versions", <https://devguide.python.org/versions/> |
| `Wix/WixQA` has 16 commits; the newest is `d662dc42479c14e202eccd832f8c4b66a035c4cc`, "Update README.md", of 2025-07-02 | <https://huggingface.co/datasets/Wix/WixQA/commits/main> |
| The repository holds the folders `wix_kb_corpus`, `wixqa_expertwritten`, `wixqa_simulated` and `wixqa_synthetic`, a README and `.gitattributes`; 60.3 MB together | <https://huggingface.co/datasets/Wix/WixQA/tree/main> |
| `wix_kb_corpus/wix_kb_corpus.jsonl` is 53.7 MB; `wixqa_expertwritten/test.jsonl` is 256 kB | the two folder pages under the address above |
| A question row has `question`, `answer` and `article_ids` and no identifier; an article id is a string of 64 hexadecimal characters; the card lists `id`, `url`, `contents` and `article_type` for an article | <https://huggingface.co/datasets/Wix/WixQA> |
| Embedding requests: at most 8,192 tokens per input, at most 2,048 inputs, at most 300,000 tokens per request; an empty string is not accepted | <https://developers.openai.com/api/reference/resources/embeddings/methods/create> |
| `text-embedding-3-small` costs 0.02 US dollars per million tokens; its model page names `text-embedding-3-small` as the default snapshot | <https://developers.openai.com/api/docs/models/text-embedding-3-small> |
| Rate limits listed on the model page of `text-embedding-3-large`: free tier 100 requests per minute, 2,000 requests per day and 40,000 tokens per minute; tier 1 3,000 requests and 1,000,000 tokens per minute | <https://developers.openai.com/api/docs/models/text-embedding-3-large> |
| Usage tier 1 is reached after 5 US dollars paid | <https://developers.openai.com/api/docs/guides/rate-limits> |
| pgvector 0.8.7 was released on 2026-10-05 | <https://www.postgresql.org/about/newsarchive/related/20261005/> |
| PostgreSQL 19 was at release candidate 1 on 2026-10-15 | <https://www.postgresql.org/about/newsarchive/related/20261007/> |
| A release asset must be under 2 GiB; a release has no limit on its total size or on bandwidth | <https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases> |
| The Free plan includes 2,000 Actions minutes and 500 MB of artifact storage a month for private repositories; standard runners are free for public repositories | <https://docs.github.com/en/billing/concepts/product-billing/github-actions> |
| GitHub's documentation states that a workflow must be in the default branch to be started with `workflow_dispatch`; users report that the "Run workflow" button is missing for a workflow file that is only on another branch | <https://docs.github.com/en/enterprise-server@3.20/actions/using-workflows/manually-running-a-workflow> and <https://github.com/orgs/community/discussions/178194> |
| `uv sync --locked` and the `astral-sh/setup-uv` action are the documented way to use uv in GitHub Actions | <https://docs.astral.sh/uv/guides/integration/github/> |
| A scratch project resolved and installed on CPython 3.14.6 with uv 0.11.32: openai 3.58.0, psycopg 3.3.9 with its bundled client library for PostgreSQL 18, pytest 9.2.0, ruff 0.17.6, build backend `uv_build` 0.11.32 | run in the planning workspace |
| The rule of section 12, written as a throwaway function, kept its properties on 20,000 random texts: every passage is non-empty and within `max_chars`, the passages keep every non-whitespace character in order, and the same text gives the same passages | run in the planning workspace |
| The store design of sections 7 and 8, tried with a throwaway script: a build in one transaction that stops part-way leaves no schema; a second build under the same identifier is rejected by the database; vectors are accepted in text form; nearest-neighbour search works without an approximate index; one schema dumped with `pg_dump` in custom format and restored with `pg_restore` into another database has the same rows and vectors, compared by a fingerprint over all rows, and the build record travels with it. The dump took about 7 kB per passage | run in the planning workspace on PostgreSQL 16.2 with pgvector 0.6.2, which are not the planned versions; the integration tests of this feature repeat these checks on the planned versions |
| Through the REST API of this repository an agent can read workflows, workflow runs, artifacts, check runs, releases, labels and issue comments; it cannot read the Actions settings or the secrets | requests from the planning workspace |
| The planning workspace reaches neither `huggingface.co` nor `api.openai.com` from its shell | requests from the planning workspace |

## Not checked

The first runs confirm these points. A wrong path, a wrong row count or an id that does not match stops a command with a message that names it, so none of them can pass unnoticed.

- The paths `wixqa_simulated/test.jsonl` and `wixqa_synthetic/test.jsonl`. They are assumed from the layout of `wixqa_expertwritten`.
- The row counts at the pinned revision. They come from the dataset card.
- The shape of `contents`: whether it has line breaks, and how long articles are. The rule of section 12 handles text without line breaks too.
- The number of passages, the number of tokens and the cost. The estimate from the size of the corpus file is about 50 million characters, 25 to 30 thousand passages, 10 to 14 million tokens and 0.20 to 0.28 US dollars for one build. The build record of the first build states the real numbers.
- The size of the dump. At about 7 kB per passage the estimate is 180 to 220 MB.
- That the image tag `pgvector/pgvector:0.8.7-pg18` exists. The DevOps agent pins the tag and the digest when it writes the workflow.
- Whether an agent can start a workflow, put a label on a pull request, or read a log through the REST API. If it cannot, the owner starts the run, and results are read from the run, its steps and its annotations.
- The rate limits of `text-embedding-3-small` and the usage tier of the owner's account with the embedding provider. The numbers in section 13 are those listed for `text-embedding-3-large`; the limits page of the owner's account is the authority.
- Whether every article has text and every `article_ids` value names an article of the corpus. The spec assumes both. If the real data shows otherwise, the audit of the real index fails, the finding is recorded, and the owner decides (spec, "Assumptions").

## Constitution amendment that this plan leads to

The constitution leaves the tooling open under `TODO(PYTHON_TOOLING)` and says that the plan of spec 1 chooses it and that an amendment records it. The amendment is a task of this feature and becomes binding when the owner merges the pull request.

- "Stack", the `TODO(PYTHON_TOOLING)` line is replaced by: "Python tooling: Python 3.14; uv manages the environment and the dependencies, and `uv.lock` is the lock file; tests run with pytest; CI runs on GitHub Actions."
- Version 1.0.0 becomes 1.1.0: a section is materially expanded (MINOR). "Last Amended" becomes the date of the amendment.
- `PROJECT.md`, "Decided", gains two entries in the same pull request: the tooling above, and the owner's decision of 2026-11-24 that every command which needs the dataset host or the embedding provider runs on GitHub Actions, started by hand, with the provider key stored as a repository secret.
