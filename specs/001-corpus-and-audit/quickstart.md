# Quickstart: Corpus and audit

**Feature**: `001-corpus-and-audit` | **Date**: 2026-11-24 | **Plan**: [plan.md](plan.md)

How to see, end to end, that this feature works once it is implemented. Part A is the way the study itself runs it: on GitHub, with nothing installed on a computer. Part B is the same on a computer, for a reader who prefers that. The commands, their output and the files they write are described in [contracts/cli.md](contracts/cli.md) and [contracts/records.md](contracts/records.md).

The commands on example data and the fetch and check of the published dataset have run on GitHub Actions. The build and the audit of the real index have not run yet. The expected outcomes below are those of the spec's acceptance checks.

## A. On GitHub

### What is needed

- The repository secret `OPENAI_API_KEY`: a key of an account with the embedding provider. Only the owner of the repository can add it (Settings → Secrets and variables → Actions). For the `full` scope the account has to be at usage tier 1 or higher.
- A pull request for the branch, for the label way of starting a run.

### Steps and expected outcomes

| # | Step | Expected outcome |
|---|---|---|
| 1 | Open or update the pull request | The workflow "checks" starts by itself and ends green: lint, format, and every test that needs neither the provider nor the dataset host, AC-003, AC-007, AC-012 and AC-014 among them |
| 2 | Start "acceptance" with the scope `example`: put the label `acceptance:example` on the pull request, or use "Run workflow" once the workflow is on `main` | The run ends green. On top of step 1 it passes AC-005, AC-006, AC-009, AC-010, AC-011 and AC-013: an index is built from the example dataset, a second build embeds nothing, and each of the three kinds of mismatch is caught and named. The provider is called for a few hundred tokens |
| 3 | Start "acceptance" with the scope `full`, for the first time | The run ends green and passes all fourteen checks. The dataset is fetched at the pinned revision with 6,221, 200, 200 and 6,221 rows; the index `wixqa-001` is built; its audit reports zero mismatches. The run then adds one commit to the branch with `evals/indexes/wixqa-001/build.json`, `audit.json` and `snapshot.json`, and creates the release `index-wixqa-001` with the dump of the index |
| 4 | Start "acceptance" with the scope `full` again | The run ends green. The index is restored from the release, `index build` reports it as already complete with `tokens embedded: 0`, and the audit passes again. The provider is called only for the example dataset |

Before a story is implemented, the runs that include its tests end red: the tests exist and the commands do not. Those red runs are what the constitution asks for before an implementation starts.

### Reading a result without opening a log

The run and each of its steps have a conclusion. Each failed test appears as an annotation of the run, and the verdict lines of the real-data commands appear as notices. All of these can be read on the page of the run and through the REST API of the repository.

## B. On a computer

### What is needed

- uv, and Docker or another way to run a PostgreSQL with pgvector.
- For the steps that embed: a key of an account with the embedding provider.

### Setting up

```sh
uv sync --locked
source .venv/bin/activate

docker run --name wixqa-store --detach --publish 5432:5432 \
  --env POSTGRES_HOST_AUTH_METHOD=trust --env POSTGRES_DB=wixqa \
  pgvector/pgvector:<the tag pinned in .github/workflows/acceptance.yml>

export DATABASE_URL=postgresql://postgres@localhost:5432/wixqa
export OPENAI_API_KEY=<your key>   # keep it out of files that are committed
```

### The example dataset

```sh
python -m wixqa_rag dataset check --data-dir tests/data/example
python -m wixqa_rag index build --data-dir tests/data/example --index example
python -m wixqa_rag index audit --data-dir tests/data/example --index example
python -m wixqa_rag index audit --data-dir tests/data/example-one-more-article --index example
```

| Command | Expected outcome |
|---|---|
| `dataset check` | exit code 0, last line `dataset check: passed` |
| `index build` | exit code 0, `articles: 5`, last line `index build: done`; the record is at `data/indexes/example/build.json` |
| `index audit`, same dataset | exit code 0, three count lines with 0, last line `audit: passed` |
| `index audit`, one more article | exit code 1, `missing from index: 1`, the id `ex-006`, last line `audit: failed` |

### The published dataset

```sh
python -m wixqa_rag dataset fetch
python -m wixqa_rag dataset check
```

Expected: the fetch names the pinned revision and the four row counts, and the check ends with `dataset check: passed`. Neither command needs the store or the provider key.

Once `evals/indexes/wixqa-001/` exists in the repository, the index itself can be restored and audited without embedding anything:

```sh
gh release download index-wixqa-001 --pattern wixqa-001.dump
sha256sum wixqa-001.dump          # compare with "sha256" in evals/indexes/wixqa-001/snapshot.json
docker exec wixqa-store psql --username postgres --dbname wixqa --command 'CREATE EXTENSION IF NOT EXISTS vector'
docker exec --interactive wixqa-store pg_restore --username postgres --dbname wixqa --no-owner < wixqa-001.dump

python -m wixqa_rag index build --index wixqa-001
python -m wixqa_rag index audit --index wixqa-001
```

Expected: the build reports `index: wixqa-001 (already complete)` and `tokens embedded: 0`, and the audit ends with `audit: passed`.

A reader who wants to embed the corpus anew builds under an identifier of their own, for example `python -m wixqa_rag index build --index wixqa-rerun`. The identifier `wixqa-001` already has a build record in the repository, so a build under it is refused while the store does not hold that index.

### The tests

```sh
uv run pytest -m "not store and not provider and not real_data"   # needs nothing
uv run pytest -m "not provider and not real_data"                 # needs the store
uv run pytest -m "not real_data"                                  # needs the store and the key
uv run pytest                                                     # needs the store, the key and the dataset host
```

### Starting over

This feature has no command that removes an index. To start over on a computer, remove the container (`docker rm --force wixqa-store`) and the folders `data/indexes/` and `data/audits/`, then set up again.
