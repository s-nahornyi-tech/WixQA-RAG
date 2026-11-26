# evals

Everything used to measure quality. The rules behind this folder are the measurement invariants in `PROJECT.md`.

| Folder | What it holds |
|---|---|
| `golden/` | The golden set: the fixed list of questions, with the seed and the selection rule |
| `labels/` | The owner's hand labels; each label is tied to one run and one answer |
| `runs/` | The run registry: one entry per run, with its config next to its results |
| `indexes/` | For each index built from the pinned dataset, one folder: the build record (`build.json`), the audit made right after the build (`audit.json`), and where the snapshot of the index is kept (`snapshot.json`). The folder appears with the first such index |

File formats are fixed by the specs, not here.
