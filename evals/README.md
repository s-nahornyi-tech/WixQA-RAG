# evals

Everything used to measure quality. The rules behind this folder are the measurement invariants in `PROJECT.md`.

| Folder | What it holds |
|---|---|
| `golden/` | The question sets, one record each, with the selection rule and the seed: the golden set `golden-001` (200 questions: 100 of `wixqa_expertwritten` and 100 of `wixqa_simulated`, drawn by the method `sha256-order-v1` with the seed 20261127), the held-out set `held-out-001` (the other 200 questions of the same two parts: the complement of `golden-001`), and the synthetic held-out set `synthetic-001` (300 questions of `wixqa_synthetic`, drawn by the same method with the seed 20261127). Each record is one file, `<version>.json`: `golden-001.json`, `held-out-001.json` and `synthetic-001.json`. A record is written once by `set build` and never edited by hand; `set check --version <version>` compares it with the dataset |
| `labels/` | The owner's hand labels; each label is tied to one run and one answer |
| `runs/` | The run registry: one folder per run, named by the run identifier, with the config (`run.json`), one entry per question (`results.jsonl`) and the summary (`summary.json`). `run check` checks every record of the registry, and `run check --run <run id>` checks one. There is no run yet |
| `indexes/` | For each index built from the pinned dataset, one folder: the build record (`build.json`), the audit made right after the build (`audit.json`), and where the snapshot of the index is kept (`snapshot.json`). The folder appears with the first such index |

File formats are fixed by the specs, not here: the records of indexes in `specs/001-corpus-and-audit/contracts/records.md`, and the records of question sets and of runs in `specs/002-evaluation-harness/contracts/records.md`.
