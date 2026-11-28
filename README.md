# WixQA-RAG

What actually makes a support knowledge-base assistant answer better? An open, reproducible study on the [WixQA](https://huggingface.co/datasets/Wix/WixQA) dataset: every design decision is backed by a measurement you can re-run.

**Status:** early. The dataset is pinned, and the retrieval index of the corpus is built and audited: 6,221 articles in 11,656 passages, with zero mismatches against the dataset (records in [`evals/indexes/wixqa-001/`](evals/indexes/wixqa-001/)). The three question sets are fixed and recorded in [`evals/golden/`](evals/golden/): the golden set `golden-001` with 200 questions (100 of `wixqa_expertwritten` and 100 of `wixqa_simulated`, drawn with a recorded seed; 159 single-article and 41 multi-article), the held-out set `held-out-001` with the other 200 questions of the same two parts (162 single-article and 38 multi-article), and the synthetic held-out set `synthetic-001` with 300 questions of `wixqa_synthetic`, all single-article. Each record can be produced again and checked against the dataset (`set build`, `set check`), and the audit of the index passed with each of the three sets on 2026-11-27 (workflow run 46016911377). The form of a run record is fixed, and a record can be checked against its own results, reported and compared with another run on the same question set (`run check`, `run report`, `run compare`); so far these commands have run on example data only. Nothing retrieves from the index or generates answers yet. No evaluation run and no results yet.

## Approach

Measurement comes first, the pipeline second:

- a fixed set of questions on which every version is compared;
- one change per run, with the run's settings stored next to its results;
- an automatic judge whose verdicts are checked against human labels;
- a registry of runs, so each decision points to the evidence behind it.

The rules and their reasons are in `PROJECT.md` under "Measurement invariants"; their exact definitions are in the constitution.

## Where things are

| Path | What it holds |
|---|---|
| `PROJECT.md` | Project facts and decisions; the single source of truth for agents |
| `.specify/memory/constitution.md` | The constitution: binding rules, exact metric definitions, and the workflow |
| `.specify/templates/overrides/` | The project's spec and tasks templates: acceptance checks, evidence, and tests first |
| `.claude/agents/` | The role files of the five agents: testing, coding, code review, DevOps and spec |
| `specs/` | One folder per feature: its spec, plan, contracts and task list |
| `dataset.json` | The pinned revision of the dataset, with the path and the row count of each part |
| `evals/` | Everything used to measure quality: the golden set and the two held-out sets, hand labels, the run registry, and the records of indexes. Three question sets are recorded; there are no labels and no runs yet |
| `evals/golden/` | The records of the question sets: the golden set `golden-001` and the two held-out sets `held-out-001` and `synthetic-001`, each with its selection rule, its seed and the list of its questions |
| `evals/runs/` | The run registry: one folder per run, holding its config (`run.json`), one entry per question (`results.jsonl`) and its summary (`summary.json`). It holds no run yet |
| `evals/indexes/` | For each index built from the pinned dataset: its build record, the audit made right after the build, and where its snapshot is kept |
| `src/` | The system's code |
| `tests/` | Tests, and the small example datasets they use |
| `data/` | Downloaded datasets, and the records of indexes built from example data; kept out of Git |
| `.github/workflows/` | The two CI workflows: `checks.yml` runs for every pull request; `acceptance.yml` runs when a person starts it |

`.specify/` and `.claude/skills/` hold GitHub Spec Kit (version 1.4.2).

## Setting up

The commands of the specs are typed at the repository root, in the project's Python environment. It needs [uv](https://docs.astral.sh/uv/), version 0.11.32 or a later 0.11 release; uv installs Python 3.14 and the locked dependencies:

```sh
uv sync --locked
source .venv/bin/activate
```

A few things can then be tried with nothing else installed:

```sh
python -m wixqa_rag dataset check --data-dir tests/data/example
python -m wixqa_rag set check --version harness-half --data-dir tests/data/harness --sets-dir tests/data/sets
python -m wixqa_rag run check --runs-dir tests/data/runs --sets-dir tests/data/sets
python -m wixqa_rag run check
pytest -m "not store and not provider and not real_data"
```

The first checks one of the example datasets and ends with `dataset check: passed`. The second checks an example question set against its example dataset, and the third checks four example run records; both end with `passed`. The fourth checks the run registry of the study and reports `runs: 0`, because no run exists yet. The last runs the tests that need neither a database nor a key. More steps on example data, with the outcome to expect from each, are in [`specs/002-evaluation-harness/quickstart.md`](specs/002-evaluation-harness/quickstart.md). Without activating the environment, put `uv run` in front of a command.

Building and auditing an index needs a PostgreSQL with pgvector, and building also needs a key of the embedding provider. The steps, on GitHub Actions and on a computer, are in [`specs/001-corpus-and-audit/quickstart.md`](specs/001-corpus-and-audit/quickstart.md); the names of the two settings are in `.env.example`.

## How we work

Spec-driven development with GitHub Spec Kit, plus seven additions of our own. They are listed in `PROJECT.md` under "Process".
