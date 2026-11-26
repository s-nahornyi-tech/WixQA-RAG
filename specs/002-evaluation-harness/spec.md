# Feature Specification: Evaluation harness

**Feature Branch**: `002-evaluation-harness`

**Created**: 2026-11-26

**Status**: Draft

**Input**: User description: "Evaluation harness (spec 2 of the "Spec order" table in PROJECT.md): golden set, retrieval metrics, run registry. First the ruler, then what it measures. Fix the golden set as a record in the repository with its selection rule and its identity; by the owner's decision of 2026-11-26 it consists of all questions of the parts wixqa_expertwritten and wixqa_simulated (200 + 200 = 400 questions), and wixqa_synthetic is not in it. Compute the article-level retrieval metrics exactly as the constitution defines them: on the ordered list passed to generation and separately on the list before reranking, the share of gold articles found and the "all found" flag, the breakdown into single-article and multi-article questions, and failures as separate categories. Fix the run record format and the run registry as the constitution defines them, with a check of a run record. Compare two runs on the golden set pairwise: how many questions became correct and how many became incorrect. No retrieval, no generation, no judge and no real run is built here; acceptance is by tests on a small example with a known answer, and by checks on the real golden set that need no pipeline."

## Clarifications

### Session 2026-11-26

- Q: Does the golden-set record also hold, for each question, a copy of its gold article ids? → A: Yes. The record carries the gold article ids of each question, so the measurements of a run can be recomputed from the repository alone; the golden-set check compares them with the dataset (FR-003, FR-006). Owner's answer of 2026-11-26.
- Q: Once the golden set exists, which questions does an audit check when no question set is named? → A: Every question of the question parts, as today. The golden set is checked when it is named, which every run does (FR-008). Owner's answer of 2026-11-26.

## User Scenarios & Testing *(mandatory)*

The person who runs a command is called the *operator* in this spec: the owner, an agent, or a reader of the repository.

This feature builds the means of measuring and nothing that is measured. No pipeline exists in the repository today: nothing retrieves from the index and nothing generates an answer. So no run exists, the run registry is empty, and this spec contains no result number. Every number in it belongs to an example that was written by hand so that the right answer is known in advance.

### User Story 1 - Fix the golden set (Priority: P1)

The operator produces the golden set from the pinned dataset by one recorded rule and keeps it in the repository under a version. From then on every operator can check that the record in the repository is exactly what the rule selects from the dataset, and that every gold article of the golden set is in the index that will be searched.

**Why this priority**: Every later number of the study is a number "on the golden set". Until the set is fixed, two runs cannot be compared, and the audit of Principle I has no golden set to check.

**Independent Test**: Produce the golden set from a small example dataset and check it: the check passes and reports the number of questions per part. Check three altered golden sets, each with one known difference: the check fails each time and names exactly that difference.

**Acceptance Scenarios**:

1. **Given** the pinned dataset, **When** the operator produces the golden set by the decided rule, **Then** the record holds every question of `wixqa_expertwritten` and of `wixqa_simulated`, 400 in all, no question of `wixqa_synthetic`, the dataset revision, the rule and its version.
2. **Given** a golden set that was produced, **When** the operator produces it again from the same dataset by the same rule under the same version, **Then** nothing is written and the report says that this version already exists.
3. **Given** a golden set that was produced, **When** the operator asks for another selection under the same version, **Then** the request is refused and the record is unchanged.
4. **Given** a golden set and the dataset it was produced from, **When** the operator checks the golden set, **Then** the check passes and reports the number of questions per part, in total, with one gold article, with several gold articles, and without any.
5. **Given** a golden set that lacks a question the rule selects, holds a question the rule does not select, or differs from the dataset in another way, **When** the operator checks it, **Then** the check fails and names what differs.
6. **Given** a complete index and a golden set that passes its check, **When** the operator audits the index with the golden set as the question set, **Then** the audit reports for the questions of the golden set whether every gold article is in the index.

---

### User Story 2 - Read the measurements of a run (Priority: P2)

The operator takes a recorded run and gets its measurements: how many questions ended in each status, and, for the list passed to generation and for the list before reranking, the share of gold articles found and the share of questions with every gold article found. Every number comes for all questions, for single-article questions and for multi-article questions, with the number of questions behind it. Cost and latency stand next to them.

**Why this priority**: These are the numbers on which every later decision about retrieval rests (Principles II, VII, VIII and IX). They have to be shown right on an example where the right answer is known before any real run is measured with them.

**Independent Test**: Take the example run of "Acceptance Checks", whose lists were written by hand, and ask for its report. Every number of the report equals the number computed by hand from the table of that example.

**Acceptance Scenarios**:

1. **Given** a recorded run, **When** the operator asks for its report, **Then** the report gives the count of each of the five statuses, and the counts add up to the size of the golden set.
2. **Given** a question with several gold articles of which the generation list holds some, **When** the report is made, **Then** the question's share found is the number of its gold articles in the list divided by the number of its gold articles, and its "all found" flag is 0.
3. **Given** a question whose gold article is in the retrieved list and not in the generation list, **When** the report is made, **Then** the question counts as found on the retrieved list and as not found on the generation list.
4. **Given** a question that failed before a list existed, **When** the report is made, **Then** the question is counted under its status, is left out of the metrics of that list, and is not a retrieval miss.
5. **Given** a question whose list exists and is empty, **When** the report is made, **Then** the question is counted in the metrics of that list with a share found of 0.
6. **Given** a recorded run, **When** the report is made, **Then** every metric appears three times, for all questions, for single-article questions and for multi-article questions, each with its number of questions, and the cost and the latency of the run appear next to them.

---

### User Story 3 - Check a run record and the registry (Priority: P3)

The operator checks a run record against the format that the constitution requires, and checks the whole run registry. A record that lacks a required part, that contradicts itself, or whose summary cannot be recomputed from its own files is reported with the defect named.

**Why this priority**: A number is evidence only when the record behind it is complete and consistent (Principles VI, IX and X). Spec 3 writes the first real run record, and this check is what that record has to pass.

**Independent Test**: Check the example run: it passes. Check six altered records, each with one known defect: the check fails each time and names that defect.

**Acceptance Scenarios**:

1. **Given** a complete and consistent run record, **When** the operator checks it, **Then** the check passes.
2. **Given** a record in which a question of the golden set has no entry, an entry lacks its latency or its cost, a status is not one of the five, or the hash of an answer is not the hash of that answer, **When** the operator checks it, **Then** the check fails and names the question and the defect.
3. **Given** a record whose summary differs from what its other files give, **When** the operator checks it, **Then** the check fails and names the number that differs.
4. **Given** an experiment run whose config differs from the config of the run it names as its baseline in more than the one parameter it names, **When** the operator checks it, **Then** the check fails and names the other parameter.
5. **Given** a run registry, **When** the operator checks it as a whole, **Then** every run is checked, and the report gives the number of runs and the number of runs that failed.
6. **Given** a run that does not exist in the registry, **When** the operator checks it, **Then** the check ends as not carried out and states the reason.

---

### User Story 4 - Compare two runs pairwise (Priority: P4)

The operator names two runs on the same golden set and learns which questions changed: how many had not every gold article in the generation list in the first run and have every one in the second, how many went the other way, and which questions those are.

**Why this priority**: An average can stay flat while single questions flip in both directions (Principle III). It is last because it needs two records and the metrics.

**Independent Test**: Compare the two example runs of "Acceptance Checks": the comparison reports two questions gained and one lost and names them.

**Acceptance Scenarios**:

1. **Given** two runs on the same golden set, **When** the operator compares them, **Then** the report gives the number of questions gained and the number lost, with the identifiers of the questions behind both numbers.
2. **Given** a question that has no generation list in one of the two runs, **When** the operator compares them, **Then** the question is left out, and the number of questions left out is reported.
3. **Given** two runs on different versions of the golden set, **When** the operator compares them, **Then** the comparison is refused and names both versions.
4. **Given** a run whose record does not pass its check, **When** the operator compares it with another run, **Then** the comparison is refused.

---

### Edge Cases

- What happens when a question has no gold article? It has no share found and no "all found" flag. It is counted under its status and in the cost and the latency of all questions, and it belongs neither to the single-article nor to the multi-article questions. The golden-set check reports the number of such questions. The audit of the three question parts recorded in `evals/indexes/wixqa-001/audit.json` found none.
- What happens when a list holds the same article several times, because several passages of it were retrieved? The record keeps the list as it was, one article id per item. The metrics count the article once.
- What happens when a question names the same gold article twice? The article counts once, as in the audit of spec 1.
- What happens when a list is empty? An empty list exists: the question is counted with a share found of 0. A list that was never produced is recorded as absent, and the question is left out of that list's metrics.
- What happens when nothing reorders or cuts the list between retrieval and generation? The two lists are equal, both are recorded, and both sets of numbers are reported.
- What happens when no question of a breakdown has the list? The number of questions is 0, and the mean and the share are reported as undefined, not as 0.
- What happens when the same question text occurs more than once in the golden set? Every row stays a question of its own, as published. The golden-set check reports the number of repeated texts as a finding about the data.
- What happens when the local copy of the dataset is absent or fails the dataset check? The golden set is neither produced nor checked: the command ends as not carried out and states the reason.
- What happens when a run is compared with itself? Nothing is gained and nothing is lost.
- What happens when the run registry holds no run? The check of the registry passes and reports zero runs. This is the state of the repository today.

## Requirements *(mandatory)*

### Functional Requirements

**Golden set**

- **FR-001**: The golden set of the study MUST consist of every question of the parts `wixqa_expertwritten` and `wixqa_simulated` at the pinned revision: 200 + 200 = 400 questions. No question of `wixqa_synthetic` is in it. This is the owner's decision of 2026-11-26, recorded under "Decided" in `PROJECT.md`. How many of these questions are hand-labelled is not part of this feature (open decision 1 in `PROJECT.md`, spec 4).
- **FR-002**: A question identifier MUST have the form that spec 1 uses as the question reference: the name of the question's part, a hyphen, and the row number of the question in that part, counted from 1 in the order of the published file and written with at least three digits, for example `wixqa_expertwritten-017`. An identifier is valid together with the dataset revision it was made at.
- **FR-003**: The golden set MUST be kept in the repository as one record with: its version; the name and the pinned revision of the dataset; the fingerprint of every part it selects from; the selection rule; the seed, or the statement that the rule draws nothing at random; the question identifiers in a fixed order, each with the gold article ids of its question as the dataset gives them; and the number of questions. With the gold article ids in the record, the measurements of a run can be recomputed from the repository alone.
- **FR-004**: The golden set MUST be produced from the dataset by its rule and never typed by hand. Producing it twice from the same dataset by the same rule MUST give the same record: the record holds nothing that changes from one production to the next.
- **FR-005**: A version of the golden set MUST be written once. Producing an existing version again with the same dataset and the same rule writes nothing and reports that the version exists. A request for another selection under an existing version MUST be refused. Another selection is a new version, and the version that runs of the study use changes only by an amendment that the owner approves (Principle III).
- **FR-006**: The golden-set check MUST apply the recorded rule to the dataset again and compare. It MUST fail, and name every difference, when a question that the rule selects is not in the record, a question in the record is not selected by the rule, the gold articles of a question differ from the dataset, the number of questions differs, or the dataset is not the one recorded: another revision or another fingerprint of a part.
- **FR-007**: The golden-set check MUST report the number of questions per part and in total, the number of single-article questions, of multi-article questions and of questions without a gold article, and the number of question texts that occur more than once.
- **FR-008**: The audit of spec 1 MUST be able to take the golden set as its question set, so that it checks every gold article of every golden-set question against the index (Principle I). Its result MUST name the golden set by version. An audit that names a golden set which does not pass the golden-set check against the same dataset MUST end as not carried out. An audit that names no golden set MUST keep checking every question of every question part, as it does today; the golden set is a question set that is named on purpose.

**Retrieval metrics and the other numbers of a run**

- **FR-009**: The retrieval metrics MUST be computed as the constitution defines them under "Metric Definitions": on article ids, for the generation list and separately for the retrieved list, each exactly as recorded. No metric is computed on a cut-off or on any other list.
- **FR-010**: For every question that has a gold article, and for each of the two lists that exists for it, the harness MUST give `share_found`, the number of the question's gold articles among the distinct article ids of the list divided by the number of its gold articles, and `all_found`, 1 when every gold article is among them and 0 otherwise.
- **FR-011**: A list that was not produced MUST be told apart from an empty list. An empty list exists, and its question has `share_found` = 0. A question without the list is left out of that list's metrics.
- **FR-012**: For a run and for each of the two lists, the harness MUST give the mean of `share_found` and the share of questions with `all_found` = 1, over the questions that have a gold article and for which the list exists. The number of those questions and the number with `all_found` = 1 MUST be reported with them.
- **FR-013**: The harness MUST list the retrieval misses of a run: the questions whose generation list exists and has `all_found` = 0. A question without a generation list is never a retrieval miss, whatever its status.
- **FR-014**: Every question of a run MUST have exactly one of the five statuses of the constitution: `answered`, `no_answer`, `error`, `timeout`, `call_limit`. The count of each status MUST be reported, and the counts MUST add up to the size of the golden set.
- **FR-015**: Every number of FR-012, FR-014 and FR-016 MUST be reported three times: for all questions, for single-article questions (exactly one gold article) and for multi-article questions (two or more), each with the number of questions it is computed on.
- **FR-016**: The report of a run MUST carry, next to the retrieval metrics, the cost of answering in US dollars as a run total and per question, and the latency as the median and the 95th percentile over the questions. The cost of a question is its token counts multiplied by the prices recorded in the run config. The median of an even number of values is the mean of the two middle values. The 95th percentile of *n* values is the value at position ⌈0.95 × *n*⌉ when they are sorted in ascending order.
- **FR-017**: There MUST be one computation of these numbers. Later features use it when they record a run, and the check of a run record uses the same one, so that recomputing a summary gives the same numbers.

**Run record and run registry**

- **FR-018**: The run registry MUST hold one record per run, under the run's identifier. A run identifier MUST consist of the run's start time in UTC, to the second, a hyphen, and a short name of lower-case letters, digits and single hyphens, for example `20261201T093000Z-baseline`. It is unique in the registry and is never reused.
- **FR-019**: A run record MUST contain the four parts that the constitution lists under "Run Record Format": the identity (run identifier, start time in UTC, commit of the code); the config (everything needed to repeat the run, with the golden set named by its version and by the fingerprint of its record); the results, one entry per golden-set question; and the summary.
- **FR-020**: The entry of a question MUST hold the question identifier, the status, the retrieved list and the generation list, the context passed to the generator in a form from which its exact text can be restored, the answer and its hash, the token counts, the cost and the latency. Each list is recorded as ordered article ids, one per item, with repeated ids kept, or as absent. A question with the status `answered` or `no_answer` has both lists and an answer.
- **FR-021**: The summary MUST hold the audit result of Principle I, the count of each status, and the numbers of FR-012 and FR-016 in the three breakdowns with their numbers of questions. The audit result is the result that spec 1 defines, made with the run's golden set as the question set and with the outcome passed.
- **FR-022**: The check of a run record MUST fail, and name every defect, when: a part or a field that FR-019 to FR-021 require is absent; the run identifier does not have the form of FR-018 or does not agree with the recorded start time; the results do not hold exactly one entry for every question of the run's golden set and no other; a status is not one of the five; a list holds something that is not an article id; the hash of an answer is not the SHA-256 of that answer's text; the cost of an entry is not its token counts multiplied by the recorded prices; the audit result is absent, is not passed, or names another index, dataset revision or golden set than the config; or a number of the summary differs from the number that the one computation of FR-017 gives from the other files.
- **FR-023**: For an experiment run the check MUST also fail when the run it names as its baseline is not in the registry, when that run is on another golden set, or when the two configs differ in any parameter other than the one the experiment names, or do not differ in that one (Principle VI). The defect names the parameter.
- **FR-024**: The check of the registry MUST check every run in it and MUST report the number of runs and the number of runs that failed.
- **FR-025**: A report or a comparison MUST be made only from records that pass the check; otherwise it is refused, with the reason.
- **FR-026**: No command of this feature changes a run record, a golden-set record that exists, or the dataset. Recorded files are written once (constitution, "Run Record Format").

**Pairwise comparison**

- **FR-027**: For two runs on the same golden set, the comparison MUST report `gained`, the number of questions with `all_found` = 0 on the generation list in the first run and 1 in the second, and `lost`, the number with 1 in the first run and 0 in the second, together with the identifiers of the questions behind each number. The difference of the two numbers is never reported alone.
- **FR-028**: A question that lacks a generation list in either run MUST be left out of the comparison. The number of questions compared and the number left out MUST be reported, with the identifiers of the questions left out.
- **FR-029**: A comparison of two runs whose golden sets differ in version or in fingerprint MUST be refused, and the refusal names both.

**All commands**

- **FR-030**: Every check of this feature MUST end in exactly one of three outcomes that a program can tell apart: passed, failed with every difference named, or not carried out with the reason. Something that was not carried out is never reported as passed or as failed.
- **FR-031**: Making a report, checking a run record or the registry, and comparing two runs MUST need neither the vector store, nor a model provider, nor the dataset host, and no credential.

### Key Entities *(include if feature involves data)*

- **Question identifier**: the name of a question, made of its part and its row number; valid with the dataset revision.
- **Golden set**: the fixed list of questions on which every pipeline version is compared; it has a version, a rule, the dataset revision and a fingerprint.
- **Selection rule**: how the questions of a golden set are taken from the dataset. The rule of the study's golden set is "every question of the listed parts"; it draws nothing at random.
- **Retrieved list**: the ordered list of a question as it stood before reranking, as article ids.
- **Generation list**: the ordered list of a question that was passed to generation, exactly as passed, as article ids.
- **Status**: how a question of a run ended; one of five.
- **Run record**: the identity, the config, the results and the summary of one run.
- **Run registry**: where all run records are kept; today it holds none.
- **Summary**: the numbers of a run, derived from its other files and recomputable at any time.
- **Pairwise comparison**: for two runs on one golden set, the questions gained and the questions lost.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The golden set in the repository holds exactly 400 questions, 200 of `wixqa_expertwritten` and 200 of `wixqa_simulated`, and none of `wixqa_synthetic`; its check against the pinned dataset finds no difference.
- **SC-002**: Every gold article of every golden-set question is in the index `wixqa-001`: the audit with the golden set as the question set reports zero mismatches.
- **SC-003**: On the example run, every number of the report equals the number computed by hand from the example's table: the status counts, both retrieval metrics on both lists in the three breakdowns, the retrieval misses, the cost and the latency.
- **SC-004**: Each of the defects introduced on purpose in an example golden set or an example run record is caught: the check fails and names exactly that defect.
- **SC-005**: The comparison of the two example runs reports the questions gained and lost that were determined by hand, by number and by identifier; a comparison across two golden sets is refused.
- **SC-006**: Recomputing the summary of a recorded run gives the same numbers, and producing a golden set twice gives the same record.
- **SC-007**: The run registry of the repository passes its check.

No baseline run exists, so this spec states no numeric quality target (Principle X).

## Acceptance Checks *(mandatory)*

Each check is one command and the result a reader can observe. Every check fails before the feature is implemented and passes once it is implemented. The testing agent turns each check into an automated acceptance test before any implementation is written (constitution, "Development Workflow"). This section alone names commands; the sections above stay technology-agnostic.

Every command ends with one of three exit codes, as in spec 1: `0` when it passed or did its work, `1` when a check found a difference, `2` when it was refused or not carried out. The last line of the output is the verdict line. Before a verdict of `failed`, every difference is printed on a line that starts with `difference:`; before `refused` or `not carried out`, the reason is printed on a line that starts with `reason:`. The golden set of the study has the version `golden-001` and is kept in `evals/golden/`.

**The example data.** Everything below is written by hand for these checks and is not taken from `Wix/WixQA`. The numbers are illustrations with a known answer, not results.

`tests/data/harness/` is a data directory in the form of spec 1 that passes the dataset check: six articles, `hx-001` to `hx-006`, and three question parts, `hxa` with five questions, `hxb` with three and `hxc` with two. The gold articles of the questions of `hxa` and `hxb` are in the table below; the two questions of `hxc` name `hx-001` and `hx-002`.

`tests/data/golden/` holds golden-set records:

| Version | What it is |
|---|---|
| `harness` | Every question of `hxa` and `hxb` of `tests/data/harness`: eight questions, four single-article and four multi-article |
| `harness-hxa` | Every question of `hxa` of `tests/data/harness`: five questions |
| `harness-one-less` | As `harness`, without `hxb-003` |
| `harness-one-more` | As `harness`, with `hxc-001` added |
| `harness-other-gold` | As `harness`, with `hx-001` as the only gold article of `hxa-003` |
| `example` | Every question of `exq` of `tests/data/example`, the example dataset of spec 1: three questions |

`tests/data/runs/` is a run registry with three records that pass the check. The run `20261101T100000Z-example-a` is on the golden set `harness`; its one model costs 1.00 US dollar per million input tokens and 2.00 per million output tokens:

| Question | Gold articles | Status | Retrieved list | Generation list | Latency, s | Input tokens | Output tokens |
|---|---|---|---|---|---|---|---|
| `hxa-001` | `hx-001` | `answered` | `hx-001`, `hx-002`, `hx-003` | `hx-001`, `hx-002` | 1.0 | 1000 | 100 |
| `hxa-002` | `hx-002` | `answered` | `hx-003`, `hx-002`, `hx-001` | `hx-003`, `hx-001` | 2.0 | 1000 | 100 |
| `hxa-003` | `hx-001`, `hx-003` | `answered` | `hx-001`, `hx-004`, `hx-001` | `hx-001`, `hx-004` | 3.0 | 2000 | 200 |
| `hxa-004` | `hx-002`, `hx-003`, `hx-004` | `no_answer` | `hx-002`, `hx-003`, `hx-005`, `hx-004` | `hx-002`, `hx-003`, `hx-005` | 4.0 | 2000 | 50 |
| `hxa-005` | `hx-005` | `error` | absent | absent | 5.0 | 0 | 0 |
| `hxb-001` | `hx-004`, `hx-005` | `timeout` | `hx-004`, `hx-005` | absent | 30.0 | 500 | 0 |
| `hxb-002` | `hx-006` | `call_limit` | `hx-003` | empty | 7.0 | 3000 | 300 |
| `hxb-003` | `hx-001`, `hx-006` | `answered` | `hx-006`, `hx-001` | `hx-006`, `hx-001` | 8.0 | 1500 | 150 |

The run `20261102T100000Z-example-b` is on the same golden set, names `20261101T100000Z-example-a` as its baseline and differs from it in one config parameter. Its results are those of the table with five changes: the generation list of `hxa-002` is `hx-002`, `hx-003`; the retrieved list of `hxa-003` is `hx-001`, `hx-003`, `hx-004` and its generation list is `hx-003`, `hx-001`; `hxa-004` has the status `answered`; `hxa-005` has the status `answered` and both lists are `hx-005`; both lists of `hxb-003` are `hx-006`, `hx-002`. What the table and these changes leave open in that record, such as the answers and the token counts of the changed questions, is read by no check. The run `20261103T100000Z-example-c` is on the golden set `harness-hxa`; no check reads its results.

`tests/data/runs-invalid/` is a run registry with seven records: a copy of `20261101T100000Z-example-a`, which passes the check, and six records that each differ from it in their identifier and in one defect:

| Run | The one defect |
|---|---|
| `20261101T100100Z-no-latency` | The entry of `hxa-003` has no latency |
| `20261101T100200Z-missing-question` | The results have no entry for `hxb-003` |
| `20261101T100300Z-unknown-status` | The status of `hxa-004` is `skipped` |
| `20261101T100400Z-wrong-hash` | The hash recorded for the answer of `hxa-001` is not the hash of that answer |
| `20261101T100500Z-stale-summary` | The summary states 3 questions with every gold article in the generation list; the results give 2 |
| `20261101T100600Z-two-changes` | It names `20261101T100000Z-example-a` as its baseline and one config parameter as changed, and differs from the baseline in a second parameter as well |

**The golden set**

- **AC-001** (covers US1, FR-001, FR-002, FR-003, FR-004, FR-005, SC-001): `python -m wixqa_rag golden build --version golden-001 --part wixqa_expertwritten --part wixqa_simulated` → exit code 0; the output names the pinned revision and contains `wixqa_expertwritten: 200`, `wixqa_simulated: 200`, `questions: 400` and `golden build: done`, and no line for `wixqa_synthetic`; afterwards the file `evals/golden/golden-001.json` names the pinned revision, the two parts and the 400 question identifiers from `wixqa_expertwritten-001` to `wixqa_simulated-200`
- **AC-002** (covers US1, FR-006, FR-007, SC-001): `python -m wixqa_rag golden check --version golden-001` → exit code 0; the output contains `wixqa_expertwritten: 200`, `wixqa_simulated: 200`, `questions: 400`, `questions without gold articles: 0`, a line `single-article:` and a line `multi-article:` whose two numbers add up to 400, and `golden check: passed`
- **AC-003** (covers US1, FR-004, FR-005, SC-006): `python -m wixqa_rag golden build --data-dir tests/data/harness --golden-dir data/golden --version harness --part hxa --part hxb && python -m wixqa_rag golden build --data-dir tests/data/harness --golden-dir data/golden --version harness --part hxa --part hxb` → exit code 0; the output contains `hxa: 5`, `hxb: 3` and `questions: 8`; the second build prints `golden set: harness (already written)`
- **AC-004** (covers US1, FR-005): `python -m wixqa_rag golden build --data-dir tests/data/harness --golden-dir data/golden --version harness --part hxa --part hxb && python -m wixqa_rag golden build --data-dir tests/data/harness --golden-dir data/golden --version harness --part hxa` → exit code 2 and the line `golden build: refused`, with the reason that `harness` exists with another selection
- **AC-005** (covers US1, FR-003, FR-006, FR-007): `python -m wixqa_rag golden build --data-dir tests/data/harness --golden-dir data/golden --version harness --part hxa --part hxb && python -m wixqa_rag golden check --data-dir tests/data/harness --golden-dir data/golden --version harness && python -m wixqa_rag golden check --data-dir tests/data/harness --golden-dir tests/data/golden --version harness` → exit code 0; both checks print `questions: 8`, `single-article: 4`, `multi-article: 4`, `questions without gold articles: 0` and `golden check: passed`, and no line for `hxc`
- **AC-006** (covers US1, FR-006, SC-004): `python -m wixqa_rag golden check --data-dir tests/data/harness --golden-dir tests/data/golden --version harness-one-less` → exit code 1, the line `golden check: failed`, and a `difference:` line that names `hxb-003` as selected by the rule and not in the golden set
- **AC-007** (covers US1, FR-006, SC-004): `python -m wixqa_rag golden check --data-dir tests/data/harness --golden-dir tests/data/golden --version harness-one-more` → exit code 1, the line `golden check: failed`, and a `difference:` line that names `hxc-001` as in the golden set and not selected by the rule
- **AC-008** (covers US1, FR-006, SC-004): `python -m wixqa_rag golden check --data-dir tests/data/harness --golden-dir tests/data/golden --version harness-other-gold` → exit code 1, the line `golden check: failed`, and a `difference:` line that names `hxa-003` and the article `hx-003`
- **AC-009** (covers US1, FR-008, SC-002): `python -m wixqa_rag index audit --index wixqa-001 --golden golden-001` → exit code 0; the output contains `golden set: golden-001`, `questions: 400`, `missing from index: 0`, `not in corpus: 0`, `unknown question references: 0` and `audit: passed`
- **AC-010** (covers US1, FR-008): `python -m wixqa_rag index build --data-dir tests/data/example --index example && python -m wixqa_rag index audit --data-dir tests/data/example --index example --golden-dir tests/data/golden --golden example` → exit code 0; the output contains `golden set: example`, `questions: 3`, `unknown question references: 0` and `audit: passed`
- **AC-011** (covers US1, FR-008, FR-030): `python -m wixqa_rag index build --data-dir tests/data/example --index example && python -m wixqa_rag index audit --data-dir tests/data/example --index example --golden-dir tests/data/golden --golden harness` → exit code 2 and the line `audit: not carried out`, with the reason that the golden set `harness` does not match the dataset

**The report of a run**

- **AC-012** (covers US2, FR-014, FR-015, SC-003): `python -m wixqa_rag run report --runs-dir tests/data/runs --golden-dir tests/data/golden --run 20261101T100000Z-example-a` → exit code 0; the output contains the lines `status, all questions: 8 questions, answered 4, no_answer 1, error 1, timeout 1, call_limit 1`, `status, single-article: 4 questions, answered 2, no_answer 0, error 1, timeout 0, call_limit 1` and `status, multi-article: 4 questions, answered 2, no_answer 1, error 0, timeout 1, call_limit 0`, and ends with `run report: done`
- **AC-013** (covers US2, FR-009, FR-010, FR-011, FR-012, FR-015, SC-003): the command of AC-012 → the output contains the lines `generation list, all questions: 6 questions, mean share_found 0.5278, all_found 2 of 6 (0.3333)`, `generation list, single-article: 3 questions, mean share_found 0.3333, all_found 1 of 3 (0.3333)` and `generation list, multi-article: 3 questions, mean share_found 0.7222, all_found 1 of 3 (0.3333)`
- **AC-014** (covers US2, FR-009, FR-010, FR-011, FR-012, FR-015, SC-003): the command of AC-012 → the output contains the lines `retrieved list, all questions: 7 questions, mean share_found 0.7857, all_found 5 of 7 (0.7143)`, `retrieved list, single-article: 3 questions, mean share_found 0.6667, all_found 2 of 3 (0.6667)` and `retrieved list, multi-article: 4 questions, mean share_found 0.8750, all_found 3 of 4 (0.7500)`
- **AC-015** (covers US2, FR-013, SC-003): the command of AC-012 → the output contains the line `retrieval misses: 4`, followed by the four lines `  hxa-002`, `  hxa-003`, `  hxa-004` and `  hxb-002`; it names neither `hxa-005` nor `hxb-001` as a miss
- **AC-016** (covers US2, FR-015, FR-016, SC-003): the command of AC-012 → the output contains the lines `cost_usd answering, all questions: 8 questions, total 0.01280000, per question 0.00160000`, `cost_usd answering, single-article: 4 questions, total 0.00600000, per question 0.00150000`, `cost_usd answering, multi-article: 4 questions, total 0.00680000, per question 0.00170000`, `latency_seconds, all questions: 8 questions, median 4.500, p95 30.000`, `latency_seconds, single-article: 4 questions, median 3.500, p95 7.000` and `latency_seconds, multi-article: 4 questions, median 6.000, p95 30.000`
- **AC-017** (covers US2, FR-010, FR-011): `python -m wixqa_rag run report --runs-dir tests/data/runs --golden-dir tests/data/golden --run 20261101T100000Z-example-a --per-question` → exit code 0; the output contains the lines `  hxa-004: no_answer; generation list 2 of 3, all_found 0; retrieved list 3 of 3, all_found 1`, `  hxa-005: error; generation list absent; retrieved list absent` and `  hxb-002: call_limit; generation list 0 of 1, all_found 0; retrieved list 0 of 1, all_found 0`

**The run record and the registry**

- **AC-018** (covers US3, FR-017, FR-018, FR-019, FR-020, FR-021, FR-022, FR-031, SC-006): `env -u DATABASE_URL -u OPENAI_API_KEY python -m wixqa_rag run check --runs-dir tests/data/runs --golden-dir tests/data/golden --run 20261101T100000Z-example-a` → exit code 0; the output contains `run: 20261101T100000Z-example-a`, `golden set: harness`, `questions: 8` and `run check: passed`
- **AC-019** (covers US3, FR-023, FR-024): `python -m wixqa_rag run check --runs-dir tests/data/runs --golden-dir tests/data/golden` → exit code 0; the output contains `runs: 3`, `failed runs: 0` and `run check: passed`
- **AC-020** (covers US3, FR-024, FR-026, FR-030, SC-007): `python -m wixqa_rag run check && git status --porcelain evals/runs/` → exit code 0; the output contains `failed runs: 0` and `run check: passed`, and `git status` prints nothing: no file under `evals/runs/` is added or changed
- **AC-021** (covers US3, FR-022, SC-004): `python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --golden-dir tests/data/golden --run 20261101T100100Z-no-latency` → exit code 1, the line `run check: failed`, and a `difference:` line that names `hxa-003` and the latency
- **AC-022** (covers US3, FR-014, FR-022, SC-004): `python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --golden-dir tests/data/golden --run 20261101T100200Z-missing-question` → exit code 1, the line `run check: failed`, and a `difference:` line that names `hxb-003` as a question of the golden set without an entry
- **AC-023** (covers US3, FR-014, FR-022, SC-004): `python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --golden-dir tests/data/golden --run 20261101T100300Z-unknown-status` → exit code 1, the line `run check: failed`, and a `difference:` line that names `hxa-004` and the status `skipped`
- **AC-024** (covers US3, FR-022, SC-004): `python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --golden-dir tests/data/golden --run 20261101T100400Z-wrong-hash` → exit code 1, the line `run check: failed`, and a `difference:` line that names `hxa-001` and the hash of its answer
- **AC-025** (covers US3, FR-017, FR-022, SC-004, SC-006): `python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --golden-dir tests/data/golden --run 20261101T100500Z-stale-summary` → exit code 1, the line `run check: failed`, and a `difference:` line that names the generation list and both numbers, 3 and 2
- **AC-026** (covers US3, FR-023, SC-004): `python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --golden-dir tests/data/golden --run 20261101T100600Z-two-changes` → exit code 1, the line `run check: failed`, and a `difference:` line that names the second config parameter that differs from `20261101T100000Z-example-a`
- **AC-027** (covers US3, FR-024): `python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --golden-dir tests/data/golden` → exit code 1; the output contains `runs: 7`, `failed runs: 6` and `run check: failed`
- **AC-028** (covers US3, FR-030): `python -m wixqa_rag run check --runs-dir tests/data/runs --golden-dir tests/data/golden --run 20261101T100000Z-no-such-run` → exit code 2 and the line `run check: not carried out`, with the reason that the run `20261101T100000Z-no-such-run` does not exist
- **AC-029** (covers US3, FR-025): `python -m wixqa_rag run report --runs-dir tests/data/runs-invalid --golden-dir tests/data/golden --run 20261101T100500Z-stale-summary` → exit code 2 and the line `run report: refused`, with the reason that the run check failed

**The pairwise comparison**

- **AC-030** (covers US4, FR-027, FR-028, FR-031, SC-005): `env -u DATABASE_URL -u OPENAI_API_KEY python -m wixqa_rag run compare --runs-dir tests/data/runs --golden-dir tests/data/golden --first 20261101T100000Z-example-a --second 20261102T100000Z-example-b` → exit code 0; the output contains `compared: 6`; `left out: 2`, followed by `  hxa-005` and `  hxb-001`; `gained: 2`, followed by `  hxa-002` and `  hxa-003`; `lost: 1`, followed by `  hxb-003`; and `run compare: done`
- **AC-031** (covers US4, FR-029, SC-005): `python -m wixqa_rag run compare --runs-dir tests/data/runs --golden-dir tests/data/golden --first 20261101T100000Z-example-a --second 20261103T100000Z-example-c` → exit code 2 and the line `run compare: refused`, with a reason that names the golden sets `harness` and `harness-hxa`
- **AC-032** (covers US4, FR-025): `python -m wixqa_rag run compare --runs-dir tests/data/runs-invalid --golden-dir tests/data/golden --first 20261101T100000Z-example-a --second 20261101T100400Z-wrong-hash` → exit code 2 and the line `run compare: refused`, with the reason that the run check failed for `20261101T100400Z-wrong-hash`

## Evidence *(mandatory)*

This spec decides nothing about the pipeline and states no numeric quality target: it builds the means of measuring, and no run exists in `evals/runs/`. The composition of the golden set (FR-001) is the owner's decision of 2026-11-26 and rests on no run.

## Assumptions

- Commands are typed in a POSIX shell at the repository root, in the project's Python environment set up as the README describes.
- AC-001, AC-002 and AC-009 need the local copy of the pinned dataset, and AC-009, AC-010 and AC-011 need the vector store. By the owner's decision of 2026-11-24 they run on GitHub Actions, started by hand. AC-009 audits the index `wixqa-001` restored from its recorded snapshot, so nothing is embedded for it. AC-010 and AC-011 use the example index of spec 1, whose first build embeds a few hundred tokens. No other check of this spec calls a provider.
- The golden-set record `evals/golden/golden-001.json` is produced where the pinned dataset can be fetched and reaches `main` through the pull request of this spec. The plan fixes how.
- The constitution leaves to this spec "the file names, the field names, the form of a run id and the form of a question identifier". This spec fixes the two forms (FR-002, FR-018) and what every record holds. The contracts of this spec's plan fix the file names and the field names, as the plan of spec 1 did for its records.
- Principle III asks for "the selection rule and the seed". The decided rule takes every question of two parts and draws nothing at random, so the record states that no seed is used.
- The constitution names the 95th percentile and the median of the latency without a method. FR-016 fixes one for each. They are definitions of the ruler, not targets.
- The constitution lists answer quality and calibration among the metrics of a summary. They need the judge of spec 4, and a recorded file is never edited. This spec reads the two rules together as follows: the summary written with a run holds the numbers that the run's own files give (the audit result, the status counts, the retrieval metrics, the cost of answering and the latency), and spec 4 adds the judge's numbers and the cost of judging in files of its own. The pairwise comparison on the outcome `correct` arrives with spec 4 for the same reason; here it is made on `all_found` of the generation list.
- Principle VIII asks for every metric in three breakdowns. This spec applies it to the retrieval metrics, the status counts, the cost and the latency.
- Writing a run record is the task of the feature that makes runs (spec 3). This feature fixes the format, provides the one computation of the summary and the check that every record has to pass.
- Principle VI and the constitution's `TODO(REFERENCE_AFTER_ADOPTION)` leave open which run later experiments start from. FR-023 compares an experiment with the run that its record names as its baseline and takes no side in that decision.
- A config parameter, for FR-023, is one named setting of the config. The identity of a run (its identifier, its start time, the commit of the code) is not part of the config.
- The option that names a golden set for the audit is added to the command of spec 1 without changing what that command does when the option is absent. The plan of this spec records the addition to the contracts of spec 1.
- The example data under `tests/data/harness/`, `tests/data/golden/`, `tests/data/runs/` and `tests/data/runs-invalid/` is written for the acceptance checks and is not taken from `Wix/WixQA`. The example datasets of spec 1 stay as they are.
- A listing of the runs in the registry for readers, and any chart or page of results, are not part of this feature.
