# Quickstart: Evaluation harness

**Feature**: `002-evaluation-harness` | **Date**: 2026-11-27 | **Plan**: [plan.md](plan.md)

How to see, end to end, that this feature works once it is implemented. Part A needs nothing but the checkout and runs anywhere, also in an agent's workspace: it covers 36 of the 46 acceptance checks. Part B is the way the study produces and checks its three real question sets: on GitHub, with nothing installed on a computer. Part C is part B on a computer, for a reader who prefers that. The commands, their output and the files are described in [contracts/cli.md](contracts/cli.md) and [contracts/records.md](contracts/records.md).

On 2026-11-27 the commands for question sets (`set build`, `set check`, and `index audit` with `--set`) have run on example data: in a workspace, in `checks` (run 46015502985) and in `acceptance` with the scope `example` (run 46015628918). The three real question sets are not produced yet, and the commands of the group `run` do not exist yet. The expected outcomes below are those of the spec's acceptance checks, and the numbers are those of the example data in [data-model.md](data-model.md). They are illustrations with a known answer, not results.

## A. On example data, with nothing else installed

### What is needed

uv, as the README describes:

```sh
uv sync --locked
source .venv/bin/activate
```

No database, no key, no network.

### Steps and expected outcomes

| # | Command | Expected outcome |
|---|---|---|
| 1 | `python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets --version harness-half --role golden --take hxa=3 --take hxb=1 --seed 7` | `hxa: 3`, `hxb: 1`, `questions: 4`, `set build: done`. The file `data/sets/harness-half.json` lists `hxa-002`, `hxa-003`, `hxa-005` and `hxb-002` and has the same bytes as `tests/data/sets/harness-half.json` |
| 2 | `python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets --version harness-half-rest --role held-out --complement-of harness-half` | `hxa: 2`, `hxb: 2`, `questions: 4`, `set build: done` |
| 3 | `python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir data/sets --version harness-half-rest` | `in both sets: 0`, `in neither set: 0`, `set check: passed` |
| 4 | `python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets --version harness-half-swapped` | Exit code 1; two `difference:` lines, for `hxa-005` and `hxa-001`; `set check: failed` |
| 5 | `python -m wixqa_rag run check --runs-dir tests/data/runs --sets-dir tests/data/sets` | `runs: 4`, `failed runs: 0`, `runs on golden sets: 2`, `runs on held-out sets: 2`, `run check: passed` |
| 6 | `python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets --run 20261101T100000Z-example-a` | The report of contracts/cli.md, "`run report`": for example `generation list, all questions: 6 questions, mean share_found 0.5278, all_found 2 of 6 (0.3333)` |
| 7 | `python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir tests/data/sets --run 20261101T100500Z-stale-summary` | Exit code 1; a `difference:` line with the generation list, 3 and 2; `run check: failed` |
| 8 | `python -m wixqa_rag run compare --runs-dir tests/data/runs --sets-dir tests/data/sets --first 20261101T100000Z-example-a --second 20261102T100000Z-example-b` | `compared: 6`, `left out: 2`, `gained: 2` with `hxa-002` and `hxa-003`, `lost: 1` with `hxb-003`, `run compare: done` |
| 9 | `python -m wixqa_rag run check` | `runs: 0`, `failed runs: 0`, `run check: passed`: the registry of the study holds no run yet |
| 10 | `pytest -m "not store and not provider and not real_data"` | Every test that needs neither a database nor a key passes, the 36 acceptance tests of this feature without a marker among them |

A reader can check one draw key of step 1 without the project:

```sh
printf 'sha256-order-v1:7:hxa-002' | sha256sum
# 3ab6dbb72b4a0c0ea6ac711d6dc1f5d74391faf706a742a5ba6f9392127e8bfc  (the smallest key of the five of hxa)
```

`data/` is outside version control and is not cleaned by the commands. A record left in `data/sets/` by an older state of the code makes `set build` refuse; remove the folder `data/sets/` and build again.

## B. The real question sets, on GitHub

### What is needed

- A pull request for the branch.
- The repository secret `OPENAI_API_KEY`, which exists since spec 1. No step of this part embeds anything for the real question sets; the key is used only by the tests on the example index.

### Steps and expected outcomes

| # | Step | Expected outcome |
|---|---|---|
| 1 | Open or update the pull request | The workflow "checks" starts by itself and ends green: lint, format, and every test that needs neither the provider nor the dataset host |
| 2 | Start "acceptance" with the scope `example`: the label `acceptance:example` on the pull request | Green. On top of step 1 it passes AC-010 and AC-011: the example index is audited with the question set `example`, and an audit with a set of another dataset is not carried out. The provider is called for a few hundred tokens at most |
| 3 | Start "acceptance" with the scope `full`, for the first time after User Story 1 is implemented | Green. The dataset is fetched; `golden-001` (100 + 100 questions), `held-out-001` (the other 100 + 100) and `synthetic-001` (300) are produced and checked; the held-out set shares no question with the golden set and leaves none out; the index `wixqa-001` is restored from its snapshot and audited with each of the three sets, with zero mismatches. The run then adds one commit to the branch with the three files under `evals/golden/`. A notice of the run gives, for each set, the numbers of single-article and multi-article questions |
| 4 | Start "acceptance" with the scope `full` again, at the end | Green. The three builds report `(already written)`, the three checks pass, the three audits pass. Nothing is added to the branch |

Before a story is implemented, the runs that include its tests end red: the tests exist and the commands do not.

## C. The real question sets, on a computer

### What is needed

As part B of spec 1's quickstart: uv, a PostgreSQL with pgvector that holds the index `wixqa-001` (restored from the release `index-wixqa-001`), and `DATABASE_URL`. No key of a provider.

### Steps

```sh
python -m wixqa_rag dataset fetch

python -m wixqa_rag set build --version golden-001 --role golden --take wixqa_expertwritten=100 --take wixqa_simulated=100 --seed 20261127
python -m wixqa_rag set build --version held-out-001 --role held-out --complement-of golden-001
python -m wixqa_rag set build --version synthetic-001 --role held-out --take wixqa_synthetic=300 --seed 20261127

python -m wixqa_rag set check --version golden-001
python -m wixqa_rag set check --version held-out-001
python -m wixqa_rag set check --version synthetic-001

python -m wixqa_rag index audit --index wixqa-001 --set golden-001
python -m wixqa_rag index audit --index wixqa-001 --set held-out-001
python -m wixqa_rag index audit --index wixqa-001 --set synthetic-001
```

On a checkout that already holds the three records, each build prints `(already written)`: the draw on this computer selected the same questions, byte for byte, as the draw that produced the records. That is FR-004, seen from outside.

A fingerprint can be compared without the project: `sha256sum evals/golden/golden-001.json`.
