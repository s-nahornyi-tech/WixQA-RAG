# Contract: command line

**Feature**: `001-corpus-and-audit` | **Date**: 2026-11-24 | **Plan**: [../plan.md](../plan.md)

The four commands of this feature: what they take, what they print and how they end. The acceptance checks of the spec are written against this contract, and later specs call the same commands. The numbers in the example outputs are illustrations, not results.

## General rules

**Where a command is typed.** In a POSIX shell, at the repository root, in the project's Python environment. A command reads `dataset.json` from the current directory; without it the command is not carried out. The same holds when `dataset.json` or the manifest of the data directory breaks a rule of [data-model.md](../data-model.md): the revision is not a full commit hash, no part or several parts have the role `corpus`, or a part name is used twice.

**Settings.** Read from the environment and from nowhere else (FR-017).

| Variable | Read by | Meaning |
|---|---|---|
| `DATABASE_URL` | `index build`, `index audit` | Connection string of the vector store, for example `postgresql://postgres@localhost:5432/wixqa` |
| `OPENAI_API_KEY` | `index build`, and only when passages have to be embedded | Key of the embedding provider |

A command names a setting by its variable name and never prints its value, on either output stream. No value of a setting is written to a record.

**Exit codes.**

| Code | Meaning |
|---|---|
| 0 | The command did its work, or the check or the audit passed |
| 1 | A check or an audit ran to the end and found a difference |
| 2 | The command was not carried out or was refused. This includes wrong arguments and every error the program did not expect |

**Output.**

1. Result lines go to standard output. Progress messages go to standard error. The acceptance checks read standard output.
2. A result line has the form `name: value`. A line that lists an id is indented by two spaces.
3. The last line of standard output is the verdict line of the command.
4. Before a verdict of `failed`, every difference is printed on a line that starts with `difference:`.
5. Before a verdict of `refused` or `not carried out`, the reason is printed on a line that starts with `reason:`.
6. Ids and pairs are printed in sorted order.
7. Wrong arguments. When the command line names one of the four commands but its arguments are wrong (an unknown option, an argument too many, a required option or its value missing), standard output gets a `reason:` line and the verdict `not carried out` of that command, and the exit code is 2. When the command line names no command (no arguments, an unknown group or command, a group without a command), no verdict line exists: the usage message goes to standard error, standard output stays empty, and the exit code is 2.

**Verdict lines.**

| Command | Exit code 0 | Exit code 1 | Exit code 2 |
|---|---|---|---|
| `dataset fetch` | `dataset fetch: done` | `dataset fetch: failed` | `dataset fetch: not carried out` |
| `dataset check` | `dataset check: passed` | `dataset check: failed` | `dataset check: not carried out` |
| `index build` | `index build: done` | never | `index build: refused` or `index build: not carried out` |
| `index audit` | `audit: passed` | `audit: failed` | `audit: not carried out` |

`refused` means that the request conflicts with what already exists or with a condition the spec sets. `not carried out` means that something outside the request stopped the command: a missing setting, a store or a provider that cannot be reached, an invalid argument, an error.

The verdict lines and the names of the result lines in this file are fixed. The wording after `difference:` and `reason:` is fixed only as far as a check of the spec reads it: the line names the part, the id, the question, the index or the setting concerned.

## `dataset fetch`

```sh
python -m wixqa_rag dataset fetch
```

Fetches `Wix/WixQA` at the pinned revision into the default data directory, `data/wixqa/<revision>/` (FR-001 to FR-003).

1. If the default data directory already passes the dataset check, nothing is downloaded.
2. Otherwise every part that is missing or differs is downloaded under a temporary name, its rows are counted and compared with `dataset.json`, and its SHA-256 is computed.
3. When every part matches, the files are moved into place and `manifest.json` is written.

Output of a first fetch:

```text
dataset: Wix/WixQA
revision: d662dc42479c14e202eccd832f8c4b66a035c4cc
wix_kb_corpus: 6221
wixqa_expertwritten: 200
wixqa_simulated: 200
wixqa_synthetic: 6221
downloaded: 4 files
data directory: data/wixqa/d662dc42479c14e202eccd832f8c4b66a035c4cc
dataset fetch: done
```

A fetch over a complete, matching copy prints the line `nothing downloaded` in place of the `downloaded:` line.

| Situation | Lines before the verdict | Verdict | Exit code |
|---|---|---|---|
| The copy is complete and matches | as above | `dataset fetch: done` | 0 |
| A row count at the pinned revision differs from `dataset.json` | `difference: <part> has <n> rows, dataset.json records <m>` | `dataset fetch: failed` | 1 |
| A file cannot be downloaded, or any other error | `reason: …` | `dataset fetch: not carried out` | 2 |

After a verdict other than `done`, an existing local copy is as it was before the command.

## `dataset check`

```sh
python -m wixqa_rag dataset check [--data-dir DIR]
```

Checks a data directory against its manifest and, for the default directory, against `dataset.json` (FR-004). Without `--data-dir` it checks the default data directory.

Output when the check passes, here for `tests/data/example`:

```text
dataset: example
revision: none
ex: 5
exq: 3
dataset check: passed
```

One line per part gives the number of rows found. `revision: none` stands for a dataset that is not published.

| Situation | Lines before the verdict | Verdict | Exit code |
|---|---|---|---|
| No difference | as above | `dataset check: passed` | 0 |
| The file of a part is missing | `difference: <part> is missing (<path>)` | `dataset check: failed` | 1 |
| A row count differs | `difference: <part> has <n> rows, the manifest records <m>` | `dataset check: failed` | 1 |
| A fingerprint differs | `difference: <part> has changed since its fingerprint was recorded` | `dataset check: failed` | 1 |
| A row is not a JSON object | `difference: <part> row <n> is not a JSON object` | `dataset check: failed` | 1 |
| A required field is absent | `difference: <part> row <n> lacks the field <field>` | `dataset check: failed` | 1 |
| A field has the wrong type | `difference: <part> row <n> has the field <field> with a wrong type` | `dataset check: failed` | 1 |
| An article id occurs more than once | `difference: article id <id> occurs <n> times in <part>` | `dataset check: failed` | 1 |
| Default directory: the manifest differs from `dataset.json` | `difference: the manifest differs from dataset.json: <what>` | `dataset check: failed` | 1 |
| The directory has no `manifest.json`, or any other error | `reason: …` | `dataset check: not carried out` | 2 |

Every difference found is printed, each on its own line.

## `index build`

```sh
python -m wixqa_rag index build --index ID [--data-dir DIR]
```

Builds the index `ID` from the corpus of a data directory (FR-006 to FR-010). Without `--data-dir` it uses the default data directory, and the build record goes to `evals/indexes/ID/build.json`. With `--data-dir` the build record goes to `data/indexes/ID/build.json`.

The command works in this order, and it stops at the first step that does not hold:

1. `ID` is a valid index identifier.
2. The data directory passes the dataset check.
3. `DATABASE_URL` is set, and the store can be reached.
4. The store and the build record file allow a build, or show that the index is already complete (see the table below).
5. `OPENAI_API_KEY` is set. This step is reached only when passages have to be embedded.
6. The articles are split, the passages are embedded and stored, the transaction is committed, and the build record file is written.

Output of a build:

```text
index: example
dataset: example
revision: none
embedding model: text-embedding-3-small
splitting rule: line-pack-v1 (max_chars=2000)
articles: 5
passages: 5
articles without passages: 0
tokens embedded: 180
cost_usd: 0.00000360
build record: data/indexes/example/build.json
index build: done
```

`cost_usd` is printed with eight digits after the decimal point. When articles produced no passage, their ids follow the line `articles without passages:`, one per line.

Output when the index is already complete with the same corpus and settings:

```text
index: example (already complete)
articles: 5
passages: 5
tokens embedded: 0
build record: data/indexes/example/build.json
index build: done
```

| Situation | Lines before the verdict | Verdict | Exit code |
|---|---|---|---|
| The index was built | as above | `index build: done` | 0 |
| The index is already complete, same corpus and settings | as above | `index build: done` | 0 |
| The data directory does not pass the dataset check | the lines of the check, then `reason: the dataset check failed for <DIR>` | `index build: refused` | 2 |
| The index exists with another corpus | `reason: index <ID> exists with another corpus` | `index build: refused` | 2 |
| The index exists with other settings | `reason: index <ID> exists with other settings` | `index build: refused` | 2 |
| The index exists and is not complete | `reason: index <ID> exists and is not complete` | `index build: refused` | 2 |
| The build record file differs from the record in the store | `reason: <file> does not match the index <ID> in the store` | `index build: refused` | 2 |
| A build record file exists, and the store does not hold the index | `reason: <file> records a build of <ID>, and the store does not hold that index` | `index build: refused` | 2 |
| `ID` is not a valid identifier | `reason: <ID> is not a valid index identifier` | `index build: not carried out` | 2 |
| A setting is missing | `reason: the environment variable <NAME> is not set` | `index build: not carried out` | 2 |
| The store cannot be reached | `reason: the vector store cannot be reached` | `index build: not carried out` | 2 |
| The commit of the code cannot be read, because the command does not run in a Git checkout | `reason: the commit of the code cannot be read` | `index build: not carried out` | 2 |
| The provider returns an error that retries do not cure, or any other error | `reason: …` | `index build: not carried out` | 2 |

After a verdict of `refused` or `not carried out`, the store holds exactly the indexes it held before, and no build record file was written.

## `index audit`

```sh
python -m wixqa_rag index audit --index ID [--data-dir DIR] [--json FILE]
```

Audits the index `ID` against a data directory (FR-011 to FR-016). Without `--data-dir` it uses the default data directory. The result is written to `FILE`, or to `data/audits/ID/<time>.json` when `--json` is not given.

The command works in this order, and it stops at the first step that does not hold:

1. `ID` is a valid index identifier.
2. `DATABASE_URL` is set, and the store can be reached.
3. The index `ID` exists in the store and is complete.
4. The data directory passes the dataset check.
5. The article ids are read from the index and compared with the corpus and with the questions. The result is written, and the report is printed.

Output of an audit that found one difference:

```text
index: example
dataset: example
revision: none
questions: 3
articles in corpus: 6
articles in index: 5
missing from index: 1
  ex-006
not in corpus: 0
unknown question references: 0
questions without article ids: 0
audit result: data/audits/example/20261124T101500Z.json
audit: failed
```

Under `unknown question references:` each pair is printed as the question, an arrow and the article id:

```text
unknown question references: 1
  exq-003 -> ex-999
```

Every id and every pair is printed; the lists are not shortened.

| Situation | Lines before the verdict | Verdict | Exit code |
|---|---|---|---|
| The three lists are empty | the report | `audit: passed` | 0 |
| At least one list is not empty | the report | `audit: failed` | 1 |
| The index does not exist | `reason: index <ID> does not exist` | `audit: not carried out` | 2 |
| The index is not complete | `reason: index <ID> is not complete` | `audit: not carried out` | 2 |
| The data directory does not pass the dataset check | the lines of the check, then `reason: the dataset check failed for <DIR>` | `audit: not carried out` | 2 |
| `ID` is not a valid identifier, a setting is missing, the store cannot be reached, or any other error | `reason: …` | `audit: not carried out` | 2 |

A result file is written only when the audit ran to the end. A file that already exists at `FILE` is replaced.

## The checks of the spec and this contract

| Check | Command | What it reads from this contract |
|---|---|---|
| AC-001 | `dataset fetch`, twice | the `revision:` line, the four part lines, `nothing downloaded`, exit code 0 |
| AC-002 | `dataset check` | `dataset check: passed` |
| AC-003 | `dataset check --data-dir` | `dataset check: failed`, the `difference:` line with `ex-002`, exit code 1 |
| AC-004 | `index build` | `articles: 6221`, the build record file under `evals/indexes/` |
| AC-005 | `index build`, twice | `index: example (already complete)`, `tokens embedded: 0` |
| AC-006 | `index build`, another corpus | `index build: refused`, the reason "exists with another corpus", exit code 2 |
| AC-007 | `index build`, damaged data | `index build: refused`, the reason "the dataset check failed", exit code 2 |
| AC-008 | `index audit` | the three count lines with 0, `audit: passed` |
| AC-009 | `index audit`, one more article | `missing from index: 1`, `ex-006`, `audit: failed`, exit code 1 |
| AC-010 | `index audit`, one article less | `not in corpus: 1`, `ex-005`, `audit: failed`, exit code 1 |
| AC-011 | `index audit`, unknown reference | `unknown question references: 1`, `exq-003`, `ex-999`, `audit: failed`, exit code 1 |
| AC-012 | `index audit`, unknown index | `audit: not carried out`, the reason "does not exist", exit code 2 |
| AC-013 | `index audit --json`, then `dataset check` | the result file, and `dataset check: passed` as the last line |
| AC-014 | `index build` without the key | the reason that names `OPENAI_API_KEY`, exit code 2 |
