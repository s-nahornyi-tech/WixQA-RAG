# evals

Everything used to measure quality. The rules behind this folder are the measurement invariants in `PROJECT.md`.

| Folder | What it holds |
|---|---|
| `golden/` | The golden set: the fixed list of questions, with the seed and the selection rule |
| `labels/` | The owner's hand labels; each label is tied to one run and one answer |
| `runs/` | The run registry: one entry per run, with its config next to its results |

File formats are fixed by the specs, not here.
