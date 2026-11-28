# Contract: command line

**Feature**: `002-evaluation-harness` | **Date**: 2026-11-27 | **Plan**: [../plan.md](../plan.md)

The five commands of this feature and the two options it adds to `index audit`: what they take, what they print and how they end. The acceptance checks of the spec are written against this contract. The numbers in the example outputs are those of the example data in [../data-model.md](../data-model.md); they are illustrations, not results.

## General rules

The general rules of spec 1's [contracts/cli.md](../../001-corpus-and-audit/contracts/cli.md) hold for every command here without change: where a command is typed, the exit codes 0, 1 and 2, the seven rules of the output, and rule 7 for wrong arguments. In short:

- A command is typed at the repository root and reads `dataset.json` from the current directory; without it the command is not carried out.
- Result lines have the form `name: value` and go to standard output. A line that lists an identifier is indented by two spaces. The last line of standard output is the verdict line.
- Before `failed`, every difference is on a line that starts with `difference:`. Before `refused` or `not carried out`, the reason is on a line that starts with `reason:`.
- Wrong arguments of a named command (an unknown option, an argument too many, a required option or its value missing, a value of the wrong form) give a `reason:` line and the verdict `not carried out` of that command, with exit code 2. A command line that names no command prints the usage message to standard error, nothing to standard output, and ends with exit code 2.

**Groups.** Two new groups stand next to `dataset` and `index`: `set` with the commands `build` and `check`, and `run` with the commands `report`, `check` and `compare`.

**Settings.** No command of this feature reads `OPENAI_API_KEY`. `set build`, `set check`, `run report`, `run check` and `run compare` read no setting at all (FR-031). `index audit` reads `DATABASE_URL` as before.

**Directories.**

| Option | Default | Meaning |
|---|---|---|
| `--data-dir DIR` | The default data directory of the pinned dataset | The data directory, as in spec 1 |
| `--sets-dir DIR` | `evals/golden` | Where question-set records are read and written |
| `--runs-dir DIR` | `evals/runs` | The run registry |

**Verdict lines.**

| Command | Exit code 0 | Exit code 1 | Exit code 2 |
|---|---|---|---|
| `set build` | `set build: done` | never | `set build: refused` or `set build: not carried out` |
| `set check` | `set check: passed` | `set check: failed` | `set check: not carried out` |
| `run report` | `run report: done` | never | `run report: refused` or `run report: not carried out` |
| `run check` | `run check: passed` | `run check: failed` | `run check: not carried out` |
| `run compare` | `run compare: done` | never | `run compare: refused` or `run compare: not carried out` |

`refused` means that the request conflicts with what already exists or with a condition the spec sets. `not carried out` means that something outside the request stopped the command.

The verdict lines and the names of the result lines in this file are fixed. The wording after `difference:` and `reason:` is fixed as far as this file states it; a line always names the question, the part, the version, the run or the parameter concerned.

**Numbers in the output.** A mean and a share: four digits after the decimal point. A cost: eight. A latency: three. A number that is `null` in the record: `undefined`.

## `set build`

```sh
python -m wixqa_rag set build --version V --role ROLE --take PART=N [--take PART=N ...] --seed S [--data-dir DIR] [--sets-dir DIR]
python -m wixqa_rag set build --version V --role ROLE --complement-of W [--data-dir DIR] [--sets-dir DIR]
```

Produces the question set `V` from a data directory by a rule and writes its record to `<sets directory>/V.json` (FR-001 to FR-005, FR-032).

| Option | Meaning |
|---|---|
| `--version V` | The version of the set; required |
| `--role ROLE` | `golden` or `held-out`; required |
| `--take PART=N` | Draw N questions from the question part PART; may be given several times, each time with another part; needs `--seed` |
| `--seed S` | The seed of the draw: a whole number, 0 or greater |
| `--complement-of W` | The set is the complement of the set `W` of the same sets directory |

Exactly one of the two rules is given: one or more `--take` with `--seed`, or `--complement-of`. Any other combination is a wrong argument, as are a `--take` that is not of the form `PART=N` with a whole number N of 1 or more, a part given twice, and a role other than the two.

The command works in this order, and it stops at the first step that does not hold:

1. `V` is a valid version, and so is `W`.
2. A `--data-dir` is not combined with the sets directory `evals/golden`.
3. The data directory passes the dataset check.
4. The rule can be applied. Draw: every part is a question part of the data directory, and no `--take` asks for more questions than its part has. Complement: the record `W` exists, its rule is a draw, it passes the check of `set check` against the same data directory, and the complement is not empty.
5. The record is computed. If `<sets directory>/V.json` exists and has the same bytes, the set is reported as already written. If it exists with other bytes, the build is refused.
6. The record is written under a temporary name and then given its final name, and the report is printed.

In step 6 the final name is given with a hard link, and the temporary name is then removed. The sets directory must therefore be on a file system that supports hard links. On one that does not, the command ends as `set build: not carried out` with a `reason:` line, and no record is left behind.

Output of a build with a draw:

```text
question set: harness-half
role: golden
dataset: harness
revision: none
rule: draw sha256-order-v1
seed: 7
hxa: 3
hxb: 1
questions: 4
single-article: 3
multi-article: 1
questions without gold articles: 0
record: data/sets/harness-half.json
set build: done
```

One line per part of the rule gives the number of questions taken from it. A build with a complement prints `rule: complement` and, in place of the `seed:` line, `complement of: harness-half`. When the version is already written with the same bytes, the first line is `question set: harness-half (already written)` and the other lines are the same.

| Situation | Lines before the verdict | Verdict | Exit code |
|---|---|---|---|
| The record was written | as above | `set build: done` | 0 |
| The version exists with the same bytes | as above, with `(already written)` | `set build: done` | 0 |
| The version exists with another seed and the same parts and numbers | `reason: question set <V> exists with another seed` | `set build: refused` | 2 |
| The version exists with another rule, other parts or other numbers | `reason: question set <V> exists with another selection` | `set build: refused` | 2 |
| The version exists and differs in another way (role, dataset) | `reason: question set <V> exists with other content` | `set build: refused` | 2 |
| A `--take` asks for more than the part has | `reason: the rule takes <N> questions of <PART>, which has <M>` | `set build: refused` | 2 |
| A `--take` names a part that is not a question part | `reason: <PART> is not a question part of <DIR>` | `set build: refused` | 2 |
| `--complement-of` names a set whose rule is not a draw, or the complement is empty | `reason: …` | `set build: refused` | 2 |
| `--data-dir` with the sets directory `evals/golden` | `reason: evals/golden takes only question sets of the pinned dataset` | `set build: refused` | 2 |
| `V` or `W` is not a valid version | `reason: <V> is not a valid version of a question set` | `set build: not carried out` | 2 |
| The data directory does not pass the dataset check | the lines of the check, then `reason: the dataset check failed for <DIR>` | `set build: not carried out` | 2 |
| The record `W` does not exist, or does not pass its check | `reason: question set <W> does not exist in <sets directory>`, or the `difference:` lines of its check and `reason: the check of question set <W> failed` | `set build: not carried out` | 2 |
| Any other error | `reason: …` | `set build: not carried out` | 2 |

After a verdict of `refused` or `not carried out`, the sets directory holds exactly the files it held before.

## `set check`

```sh
python -m wixqa_rag set check --version V [--data-dir DIR] [--sets-dir DIR]
```

Checks the record `<sets directory>/V.json` against a data directory (FR-006, FR-007, FR-032). The differences and the reported numbers are defined in [../data-model.md](../data-model.md), "Check of a question set".

The command works in this order:

1. `V` is a valid version, and the record exists and can be read as a question-set record.
2. The data directory passes the dataset check.
3. For a complement: the complemented record exists and passes this same check.
4. The record is compared, and the report is printed.

Output for a set whose rule draws:

```text
question set: harness-half
role: golden
dataset: harness
revision: none
rule: draw sha256-order-v1
seed: 7
hxa: 3
hxb: 1
questions: 4
single-article: 3
multi-article: 1
questions without gold articles: 0
repeated question texts: 0
set check: passed
```

Output for a complement:

```text
question set: harness-half-rest
role: held-out
dataset: harness
revision: none
rule: complement
complement of: harness-half
hxa: 2
hxb: 2
questions: 4
single-article: 1
multi-article: 3
questions without gold articles: 0
repeated question texts: 0
in both sets: 0
in neither set: 0
question texts in both sets: 0
set check: passed
```

The lines of the parts give the number of questions that the record holds of each part of `dataset.parts`. A question of the record that belongs to no such part appears only in a `difference:` line, so the check of `harness-one-more` prints no line for `hxc`. The numbers describe the record as it is, also when the check fails. The `difference:` lines follow the report and stand before the verdict.

| Difference | Line |
|---|---|
| A question the rule selects is not in the record | `difference: <question> is selected by the rule and is not in the question set` |
| A question in the record is not selected by the rule | `difference: <question> is in the question set and is not selected by the rule` |
| The gold articles of a question differ | `difference: <question> has the gold articles <ids> in the question set and <ids> in the dataset` |
| The number of questions of a part differs from the rule | `difference: the question set holds <n> questions of <part>, the rule takes <m>` |
| `count` is not the number of questions | `difference: count is <n>, the question set holds <m> questions` |
| The dataset is not the one recorded | `difference: the question set records <what>, the data directory has <what>` |
| Complement: a question is in both sets | `difference: <question> is in both <V> and <W>` |
| Complement: a question is in neither set | `difference: <question> is in neither <V> nor <W>` |
| Complement: the fingerprint of the complemented record differs | `difference: <W> has changed since <V> was produced` |
| Any other difference of data-model.md | `difference: …` |

Ids in a line are separated by a comma and a space; an empty list is written `none`.

| Situation | Lines before the verdict | Verdict | Exit code |
|---|---|---|---|
| No difference | the report | `set check: passed` | 0 |
| At least one difference | the report, then every difference | `set check: failed` | 1 |
| `V` is not a valid version, or the record does not exist | `reason: question set <V> does not exist in <sets directory>` | `set check: not carried out` | 2 |
| The record cannot be read as a question-set record | `reason: <file> is not a question-set record: <what>` | `set check: not carried out` | 2 |
| The data directory does not pass the dataset check | the lines of the check, then `reason: the dataset check failed for <DIR>` | `set check: not carried out` | 2 |
| The complemented record does not exist or does not pass its check | `reason: …` | `set check: not carried out` | 2 |
| Any other error | `reason: …` | `set check: not carried out` | 2 |

## `index audit`: the options `--set` and `--sets-dir`

```sh
python -m wixqa_rag index audit --index ID [--data-dir DIR] [--json FILE] [--set V] [--sets-dir DIR]
```

With `--set V` the audit takes the question set `V` as its question set (FR-008). Without it the command is exactly the command of spec 1. `--sets-dir` without `--set` is a wrong argument.

The order of spec 1's five steps stays; one step is added after the dataset check:

- 4a. The record `V` exists in the sets directory and passes the check of `set check` against the same data directory.

The report gains one line, after `revision:` and before `questions:`:

```text
index: wixqa-001
dataset: Wix/WixQA
revision: d662dc42479c14e202eccd832f8c4b66a035c4cc
question set: golden-001 (golden)
questions: 200
articles in corpus: 6221
articles in index: 6221
missing from index: 0
not in corpus: 0
unknown question references: 0
questions without article ids: 0
audit result: data/audits/wixqa-001/20261127T101500Z.json
audit: passed
```

`questions:` is then the number of questions of the set, and the question references checked are those of the set. The result file names the set (spec 1's contracts/records.md, "Audit result").

| Situation | Lines before the verdict | Verdict | Exit code |
|---|---|---|---|
| The record `V` does not exist, or `V` is not a valid version | `reason: question set <V> does not exist in <sets directory>` | `audit: not carried out` | 2 |
| The record `V` does not pass its check against the data directory | the `difference:` lines of that check, then `reason: question set <V> does not match the dataset of <DIR>` | `audit: not carried out` | 2 |

Every other situation is as in spec 1.

## `run report`

```sh
python -m wixqa_rag run report --run ID [--per-question] [--runs-dir DIR] [--sets-dir DIR]
```

Prints the numbers of one run, computed from its results (FR-009 to FR-016, FR-034). It writes nothing.

The command works in this order:

1. The run `ID` exists in the runs directory.
2. Its record passes the check of `run check`.
3. The numbers are computed from `results.jsonl` and the question-set record, and the report is printed.

When step 2 does not hold, the command prints the `reason:` line and the verdict and nothing else: no result line and no `difference:` line. The differences are those that `run check --run ID` prints.

Output for `tests/data/runs/20261101T100000Z-example-a`:

```text
run: 20261101T100000Z-example-a
question set: harness (golden)
questions: 8
status, all questions: 8 questions, answered 4, no_answer 1, error 1, timeout 1, call_limit 1
status, single-article: 4 questions, answered 2, no_answer 0, error 1, timeout 0, call_limit 1
status, multi-article: 4 questions, answered 2, no_answer 1, error 0, timeout 1, call_limit 0
generation list, all questions: 6 questions, mean share_found 0.5278, all_found 2 of 6 (0.3333)
generation list, single-article: 3 questions, mean share_found 0.3333, all_found 1 of 3 (0.3333)
generation list, multi-article: 3 questions, mean share_found 0.7222, all_found 1 of 3 (0.3333)
retrieved list, all questions: 7 questions, mean share_found 0.7857, all_found 5 of 7 (0.7143)
retrieved list, single-article: 3 questions, mean share_found 0.6667, all_found 2 of 3 (0.6667)
retrieved list, multi-article: 4 questions, mean share_found 0.8750, all_found 3 of 4 (0.7500)
retrieval misses: 4
  hxa-002
  hxa-003
  hxa-004
  hxb-002
questions without gold articles: 0
cost_usd answering, all questions: 8 questions, total 0.01280000, per question 0.00160000
cost_usd answering, single-article: 4 questions, total 0.00600000, per question 0.00150000
cost_usd answering, multi-article: 4 questions, total 0.00680000, per question 0.00170000
latency_seconds, all questions: 8 questions, median 4.500, p95 30.000
latency_seconds, single-article: 4 questions, median 3.500, p95 7.000
latency_seconds, multi-article: 4 questions, median 6.000, p95 30.000
run report: done
```

- The role stands in parentheses after the version: `question set: harness-hxc (held-out)` for a run on a held-out set.
- A breakdown without questions prints its lines with `0 questions` and `undefined` for every mean, share, cost per question and latency: `generation list, multi-article: 0 questions, mean share_found undefined, all_found 0 of 0 (undefined)`.

With `--per-question`, one more block stands before the verdict line: the line `per question: <n>` and one indented line per question, in the order of the set:

```text
per question: 8
  hxa-001: answered; generation list 1 of 1, all_found 1; retrieved list 1 of 1, all_found 1
  hxa-002: answered; generation list 0 of 1, all_found 0; retrieved list 1 of 1, all_found 1
  hxa-003: answered; generation list 1 of 2, all_found 0; retrieved list 1 of 2, all_found 0
  hxa-004: no_answer; generation list 2 of 3, all_found 0; retrieved list 3 of 3, all_found 1
  hxa-005: error; generation list absent; retrieved list absent
  hxb-001: timeout; generation list absent; retrieved list 2 of 2, all_found 1
  hxb-002: call_limit; generation list 0 of 1, all_found 0; retrieved list 0 of 1, all_found 0
  hxb-003: answered; generation list 2 of 2, all_found 1; retrieved list 2 of 2, all_found 1
```

`2 of 3` is the number of gold articles found and the number of gold articles: the share found, unreduced. A list that was not produced is `absent`. For a question without a gold article both parts read `no gold articles`.

| Situation | Lines before the verdict | Verdict | Exit code |
|---|---|---|---|
| The report was made | as above | `run report: done` | 0 |
| The record does not pass its check | `reason: the run check failed for <ID>` | `run report: refused` | 2 |
| `ID` is not a run identifier, or the run does not exist | `reason: run <ID> does not exist in <runs directory>` | `run report: not carried out` | 2 |
| Any other error | `reason: …` | `run report: not carried out` | 2 |

## `run check`

```sh
python -m wixqa_rag run check [--run ID] [--runs-dir DIR] [--sets-dir DIR]
```

With `--run`, checks one run record (FR-022, FR-023, FR-035). Without it, checks every run of the registry (FR-024, FR-034). The differences are defined in [../data-model.md](../data-model.md), "Check of a run record". The command writes nothing.

Output for one run:

```text
run: 20261101T100000Z-example-a
question set: harness (golden)
questions: 8
run check: passed
```

For an experiment run the line `baseline: <run id>` follows `questions:`. The lines `question set:` and `questions:` are printed when `run.json` and the record of the set can be read; they are left out otherwise.

| Difference | Line |
|---|---|
| A required field of an entry is absent | `difference: <question> lacks the field <field>` |
| A question of the set has no entry | `difference: <question> is a question of the question set and has no entry` |
| An entry names a question outside the set | `difference: <question> has an entry and is not a question of the question set` |
| A status is not one of the five | `difference: <question> has the status <status>, which is not one of the five` |
| The hash of an answer differs | `difference: <question> has an answer_sha256 that is not the hash of its answer` |
| The cost of an entry differs | `difference: <question> has cost_usd <n>, its tokens and the prices give <m>` |
| A number of the summary differs | `difference: the summary states <field> <n> for the <generation list or retrieved list>, <breakdown>; the results give <m>`; for a number that belongs to no list: `difference: the summary states <field> <n> for <breakdown>; the results give <m>` |
| The question set of the config is absent, or differs | `difference: question set <V> does not exist in <sets directory>`, or `difference: the config records the <role or fingerprint> <x> for question set <V>, its record has <y>` |
| Experiment: on a held-out set | `difference: the run is an experiment on the held-out set <V>; an experiment run is made on a golden set` |
| Experiment: a second parameter differs | `difference: the config differs from the baseline <run id> in <parameter>, which is not the parameter the experiment names` |
| Experiment: the named parameter does not differ | `difference: the config does not differ from the baseline <run id> in <parameter>` |
| Experiment: the baseline is absent, or on another set | `difference: the baseline <run id> …` |
| Experiment: the run names itself as its baseline | `difference: the baseline <run id> is the run itself` |
| Any other difference of data-model.md | `difference: …` |

In the line for a number of the summary, the breakdown is written `all questions`, `single-article` or `multi-article`, and a field of a list as in the record: `the summary states all_found 3 for the generation list, all questions; the results give 2`.

Output for the registry:

```text
runs: 4
failed runs: 0
runs on golden sets: 2
runs on held-out sets: 2
run check: passed
```

When runs failed, each of their differences is printed before the verdict with the run in front: `difference: <run id>: <the line for one run, without its "difference: ">`.

| Situation | Lines before the verdict | Verdict | Exit code |
|---|---|---|---|
| One run, no difference | as above | `run check: passed` | 0 |
| One run, at least one difference | the lines above that can be printed, then every difference | `run check: failed` | 1 |
| The registry, no run failed; also a registry without runs (`runs: 0`) | the four lines | `run check: passed` | 0 |
| The registry, at least one run failed | the four lines, then every difference | `run check: failed` | 1 |
| `ID` is not a run identifier, or the run does not exist | `reason: run <ID> does not exist in <runs directory>` | `run check: not carried out` | 2 |
| The runs directory does not exist, or any other error | `reason: …` | `run check: not carried out` | 2 |

## `run compare`

```sh
python -m wixqa_rag run compare --first ID --second ID [--runs-dir DIR] [--sets-dir DIR]
```

Compares two runs on the same question set, question by question, on `all_found` of the generation list (FR-027 to FR-029, FR-036). It writes nothing.

The command works in this order:

1. Both runs exist in the runs directory.
2. Both records pass the check of `run check`; the first run is checked first.
3. Both runs are on the same question set: the same version and the same fingerprint.
4. The comparison is made and printed.

Output:

```text
first run: 20261101T100000Z-example-a
second run: 20261102T100000Z-example-b
question set: harness (golden)
outcome: all_found on the generation list
compared: 6
left out: 2
  hxa-005
  hxb-001
gained: 2
  hxa-002
  hxa-003
lost: 1
  hxb-003
run compare: done
```

For two runs on a held-out set, one line follows the `question set:` line:

```text
question set: harness-hxc (held-out)
held-out set: its questions are not used to choose a setting
```

The identifiers under `left out:`, `gained:` and `lost:` are in the order of the question set. The command prints no difference of the two numbers and no statement on whether a difference is more than chance.

| Situation | Lines before the verdict | Verdict | Exit code |
|---|---|---|---|
| The comparison was made | as above | `run compare: done` | 0 |
| A record does not pass its check | `reason: the run check failed for <ID>` | `run compare: refused` | 2 |
| The runs are on different question sets | `reason: the runs are on different question sets: <V> and <W>` | `run compare: refused` | 2 |
| The runs are on one version with different fingerprints | `reason: the runs are on different records of the question set <V>: <fingerprint> and <fingerprint>` | `run compare: refused` | 2 |
| A run does not exist, or `ID` is not a run identifier | `reason: run <ID> does not exist in <runs directory>` | `run compare: not carried out` | 2 |
| Any other error | `reason: …` | `run compare: not carried out` | 2 |
