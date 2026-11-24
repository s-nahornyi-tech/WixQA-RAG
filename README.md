# WixQA-RAG

What actually makes a support knowledge-base assistant answer better? An open, reproducible study on the [WixQA](https://huggingface.co/datasets/Wix/WixQA) dataset: every design decision is backed by a measurement you can re-run.

**Status:** early setup. No code or results yet.

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
| `evals/` | Everything used to measure quality: the golden set, hand labels, and the run registry |
| `src/` | The system's code |
| `tests/` | Tests |
| `data/` | Downloaded datasets; kept out of Git |

`.specify/` and `.claude/skills/` hold GitHub Spec Kit (version 1.4.2). `specs/` appears when the first feature is specified.

## How we work

Spec-driven development with GitHub Spec Kit, plus seven additions of our own. They are listed in `PROJECT.md` under "Process".
