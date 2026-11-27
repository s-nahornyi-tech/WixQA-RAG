# Feature Specification: Evaluation harness

**Feature Branch**: `002-evaluation-harness`

**Created**: 2026-11-26

**Status**: Approved by the owner on 2026-11-27

**Input**: User description: "Evaluation harness (spec 2 of the "Spec order" table in PROJECT.md): golden set, retrieval metrics, run registry. First the ruler, then what it measures. Fix the golden set as a record in the repository with its selection rule and its identity; by the owner's decision of 2026-11-26 it consists of all questions of the parts wixqa_expertwritten and wixqa_simulated (200 + 200 = 400 questions), and wixqa_synthetic is not in it. Compute the article-level retrieval metrics exactly as the constitution defines them: on the ordered list passed to generation and separately on the list before reranking, the share of gold articles found and the "all found" flag, the breakdown into single-article and multi-article questions, and failures as separate categories. Fix the run record format and the run registry as the constitution defines them, with a check of a run record. Compare two runs on the golden set pairwise: how many questions became correct and how many became incorrect. No retrieval, no generation, no judge and no real run is built here; acceptance is by tests on a small example with a known answer, and by checks on the real golden set that need no pipeline."

## Clarifications

### Session 2026-11-26

- Q: Does the golden-set record also hold, for each question, a copy of its gold article ids? → A: Yes. The record carries the gold article ids of each question, so the measurements of a run can be recomputed from the repository alone; the golden-set check compares them with the dataset (FR-003, FR-006). Owner's answer of 2026-11-26.
- Q: Once the golden set exists, which questions does an audit check when no question set is named? → A: Every question of the question parts, as today. The golden set is checked when it is named, which every run does (FR-008). Owner's answer of 2026-11-26.

### Session 2026-11-27

- Q: Which questions make up the golden set, and is a part of the questions held back? → A: The owner's answer of 2026-11-27 replaces the composition decided on 2026-11-26 (every question of the two parts, 400 questions). There are three question sets. The golden set, the working set on which decisions are taken, has 100 questions of `wixqa_expertwritten` and 100 of `wixqa_simulated`, drawn at random with a recorded seed. The held-out set has the other 100 + 100 questions of the same two parts. The synthetic held-out set has 300 questions of `wixqa_synthetic`, drawn at random with a recorded seed; its numbers are reported on their own and never mixed with the others. A held-out set is used rarely, at the baseline and at milestones the owner names, and is never used to choose a setting. The owner's reason: when every decision is taken on the same questions, the system can become fitted to them; a part is held back to show that it works on questions it was not tuned on. The owner accepts the cost: with 200 working questions instead of 400, a small difference is harder to tell from chance (FR-001, FR-032 to FR-036).
- Q: Are single-article and multi-article questions balanced between the golden set and the held-out set? → A: No. The draw is a plain random draw of 100 questions per part, with no balancing by question type. The check of each set prints the number of questions of each kind. If the balance looks lopsided, the remedy is a new version with a balanced rule, never another seed (FR-005, FR-007). Owner's answer of 2026-11-27.
- The owner also decided on 2026-11-27 that no golden set of synthetic questions is added now; the question may be raised again after the baseline.
- The two answers of the session 2026-11-26 stand. They now hold for every question-set record, and the audit takes any question set that is named.

## User Scenarios & Testing *(mandatory)*

The person who runs a command is called the *operator* in this spec: the owner, an agent, or a reader of the repository.

This feature builds the means of measuring and nothing that is measured. No pipeline exists in the repository today: nothing retrieves from the index and nothing generates an answer. So no run exists, the run registry is empty, and this spec contains no result number. Every number in it belongs to an example that was written by hand so that the right answer is known in advance.

A *question set* is a fixed list of questions with a version and a role. The *golden set* is the question set with the role golden: the working set of the glossary in `PROJECT.md`, on which decisions are taken. A *held-out set* is a question set with the role held-out: it is used rarely and never to choose a setting.

### User Story 1 - Fix the golden set and the held-out sets (Priority: P1)

The operator produces the three question sets of the study from the pinned dataset, each by a recorded rule, and keeps each in the repository under a version: the golden set, drawn at random with a recorded seed from the two parts of real questions; the held-out set, which is every other question of those two parts; and the synthetic held-out set, drawn at random with a recorded seed from the synthetic part. From then on every operator, on any machine, gets the same three records from the same dataset, can check that each record is exactly what its rule selects, that the golden set and the held-out set share no question and together are all questions of the two parts, and that every gold article of each set is in the index that will be searched.

**Why this priority**: Every later number of the study is a number on one of these sets. Until the golden set is fixed, two runs cannot be compared, and the audit of Principle I has no set to check. Until the held-out questions are set apart, before any run, nothing can later show that the pipeline works on questions it was not tuned on.

**Independent Test**: Produce question sets from a small example dataset and check them. A set that takes every question of its parts has a known content, and its check reports the number of questions per part. A set drawn at random with a seed passes the check against a record that was written beforehand from the definition of the draw, and it and its complement share no question and together are all questions of their parts. Altered records, each with one known difference, fail the check, which names the difference.

**Acceptance Scenarios**:

1. **Given** the pinned dataset, **When** the operator produces the golden set by the decided rule and seed, **Then** the record holds 100 questions of `wixqa_expertwritten` and 100 of `wixqa_simulated`, no question of `wixqa_synthetic`, the dataset revision, the rule, the seed, the role and the version.
2. **Given** the golden set, **When** the operator produces the held-out set as its complement, **Then** the record holds the other 100 questions of each of the two parts: no question is in both sets, and no question of the two parts is in neither.
3. **Given** the pinned dataset, **When** the operator produces the synthetic held-out set by its rule and seed, **Then** the record holds 300 questions of `wixqa_synthetic` and no other question.
4. **Given** the same dataset, the same rule and the same seed, **When** a question set is produced on another machine or at another time, **Then** the record is the same.
5. **Given** a question set that was produced, **When** the operator produces it again from the same dataset by the same rule and seed under the same version, **Then** nothing is written and the report says that this version already exists.
6. **Given** a question set that was produced, **When** the operator asks for another selection or another seed under the same version, **Then** the request is refused and the record is unchanged.
7. **Given** a question set and the dataset it was produced from, **When** the operator checks the set, **Then** the check passes and reports the role, the seed, and the number of questions per part, in total, with one gold article, with several gold articles, and without any.
8. **Given** a question set that lacks a question its rule selects, holds a question its rule does not select, or differs from the dataset in another way, **When** the operator checks it, **Then** the check fails and names what differs.
9. **Given** a held-out set that shares a question with the golden set it complements, or leaves out a question of their parts, **When** the operator checks it, **Then** the check fails and names the question.
10. **Given** a complete index and a question set that passes its check, **When** the operator audits the index with that set as the question set, **Then** the audit reports for the questions of the set whether every gold article is in the index.

---

### User Story 2 - Read the measurements of a run (Priority: P2)

The operator takes a recorded run and gets its measurements: how many questions ended in each status, and, for the list passed to generation and for the list before reranking, the share of gold articles found and the share of questions with every gold article found. Every number comes for all questions, for single-article questions and for multi-article questions, with the number of questions behind it. Cost and latency stand next to them.

**Why this priority**: These are the numbers on which every later decision about retrieval rests (Principles II, VII, VIII and IX). They have to be shown right on an example where the right answer is known before any real run is measured with them.

**Independent Test**: Take the example run of "Acceptance Checks", whose lists were written by hand, and ask for its report. Every number of the report equals the number computed by hand from the table of that example.

**Acceptance Scenarios**:

1. **Given** a recorded run, **When** the operator asks for its report, **Then** the report gives the count of each of the five statuses, and the counts add up to the size of the run's question set.
2. **Given** a question with several gold articles of which the generation list holds some, **When** the report is made, **Then** the question's share found is the number of its gold articles in the list divided by the number of its gold articles, and its "all found" flag is 0.
3. **Given** a question whose gold article is in the retrieved list and not in the generation list, **When** the report is made, **Then** the question counts as found on the retrieved list and as not found on the generation list.
4. **Given** a question that failed before a list existed, **When** the report is made, **Then** the question is counted under its status, is left out of the metrics of that list, and is not a retrieval miss.
5. **Given** a question whose list exists and is empty, **When** the report is made, **Then** the question is counted in the metrics of that list with a share found of 0.
6. **Given** a recorded run, **When** the report is made, **Then** every metric appears three times, for all questions, for single-article questions and for multi-article questions, each with its number of questions, and the cost and the latency of the run appear next to them.
7. **Given** a run that was made on a held-out set, **When** the report is made, **Then** the report names the set and states that it is a held-out set.

---

### User Story 3 - Check a run record and the registry (Priority: P3)

The operator checks a run record against the format that the constitution requires, and checks the whole run registry. A record that lacks a required part, that contradicts itself, or whose summary cannot be recomputed from its own files is reported with the defect named.

**Why this priority**: A number is evidence only when the record behind it is complete and consistent (Principles VI, IX and X). Spec 3 writes the first real run record, and this check is what that record has to pass.

**Independent Test**: Check the example run: it passes. Check seven altered records, each with one known defect: the check fails each time and names that defect.

**Acceptance Scenarios**:

1. **Given** a complete and consistent run record, **When** the operator checks it, **Then** the check passes.
2. **Given** a record in which a question of the run's question set has no entry, an entry lacks its latency or its cost, a status is not one of the five, or the hash of an answer is not the hash of that answer, **When** the operator checks it, **Then** the check fails and names the question and the defect.
3. **Given** a record whose summary differs from what its other files give, **When** the operator checks it, **Then** the check fails and names the number that differs.
4. **Given** an experiment run whose config differs from the config of the run it names as its baseline in more than the one parameter it names, **When** the operator checks it, **Then** the check fails and names the other parameter.
5. **Given** a run registry, **When** the operator checks it as a whole, **Then** every run is checked, and the report gives the number of runs, the number of runs that failed, and the number of runs on golden sets and on held-out sets.
6. **Given** a run that does not exist in the registry, **When** the operator checks it, **Then** the check ends as not carried out and states the reason.
7. **Given** an experiment run that was made on a held-out set, **When** the operator checks it, **Then** the check fails and states that an experiment is made on the golden set.

---

### User Story 4 - Compare two runs pairwise (Priority: P4)

The operator names two runs on the same question set and learns which questions changed: how many had not every gold article in the generation list in the first run and have every one in the second, how many went the other way, and which questions those are.

**Why this priority**: An average can stay flat while single questions flip in both directions (Principle III). It is last because it needs two records and the metrics. The golden set has 200 questions, not the 400 of the two parts: the owner holds the other half back and knows the cost, which is that a small difference between two runs is harder to tell from chance. This spec sets no statistical threshold. The comparison gives the counts and the questions behind them; how large a difference has to be before it supports a decision is stated by the specs that take decisions, after the baseline run exists.

**Independent Test**: Compare the two example runs of "Acceptance Checks": the comparison reports two questions gained and one lost and names them.

**Acceptance Scenarios**:

1. **Given** two runs on the same question set, **When** the operator compares them, **Then** the report gives the number of questions gained and the number lost, with the identifiers of the questions behind both numbers.
2. **Given** a question that has no generation list in one of the two runs, **When** the operator compares them, **Then** the question is left out, and the number of questions left out is reported.
3. **Given** two runs on different question sets, or on different versions of one, **When** the operator compares them, **Then** the comparison is refused and names both.
4. **Given** a run whose record does not pass its check, **When** the operator compares it with another run, **Then** the comparison is refused.

---

### Edge Cases

- What happens when a question has no gold article? It has no share found and no "all found" flag. It is counted under its status and in the cost and the latency of all questions, and it belongs neither to the single-article nor to the multi-article questions. The check of a question set reports the number of such questions. The audit of the three question parts recorded in `evals/indexes/wixqa-001/audit.json` found none.
- What happens when a list holds the same article several times, because several passages of it were retrieved? The record keeps the list as it was, one article id per item. The metrics count the article once.
- What happens when a question names the same gold article twice? The article counts once, as in the audit of spec 1.
- What happens when a list is empty? An empty list exists: the question is counted with a share found of 0. A list that was never produced is recorded as absent, and the question is left out of that list's metrics.
- What happens when nothing reorders or cuts the list between retrieval and generation? The two lists are equal, both are recorded, and both sets of numbers are reported.
- What happens when no question of a breakdown has the list? The number of questions is 0, and the mean and the share are reported as undefined, not as 0.
- What happens when the same question text occurs more than once in a question set? Every row stays a question of its own, as published. The check of the set reports the number of repeated texts as a finding about the data. The same text in the golden set and in the held-out set would weaken the held-out set, so the check of a held-out set that complements a golden set also reports the number of question texts that occur in both.
- What happens when a rule asks for more questions than a part has? The set is not produced: the request is refused and names the part and both numbers. A rule that asks for every question of a part selects all of them, whatever the seed.
- What happens when the golden set that a held-out set complements is absent or does not pass its own check? The held-out set is neither produced nor checked: the command ends as not carried out and states the reason.
- What happens when a draw is repeated with another seed? It is another selection and needs another version. Nothing in a record can show how many seeds were tried before one was recorded; see "What a program cannot check".
- What happens when the local copy of the dataset is absent or fails the dataset check? A question set is neither produced nor checked: the command ends as not carried out and states the reason.
- What happens when a run is compared with itself? Nothing is gained and nothing is lost.
- What happens when the run registry holds no run? The check of the registry passes and reports zero runs. This is the state of the repository today.

## Requirements *(mandatory)*

### Functional Requirements

**Question sets: the golden set and the held-out sets**

- **FR-001**: The study MUST have three question sets, taken from the dataset at the pinned revision. This is the owner's decision of 2026-11-27, recorded under "Decided" in `PROJECT.md`; it replaces the composition decided on 2026-11-26.

  | Set | Role | Composition | Use |
  |---|---|---|---|
  | Golden set | golden | 100 questions of `wixqa_expertwritten` and 100 of `wixqa_simulated`, drawn at random with a recorded seed: 200 questions | Every run; decisions are taken on it |
  | Held-out set | held-out | The other 100 + 100 questions of the same two parts: 200 questions | Rarely: at the baseline and at milestones the owner names; no decision about the pipeline is taken on it |
  | Synthetic held-out set | held-out | 300 questions of `wixqa_synthetic`, drawn at random with a recorded seed | As the held-out set; its numbers are reported on their own |

  How many questions are hand-labelled is not part of this feature (open decision 1 in `PROJECT.md`, spec 4).
- **FR-002**: A question identifier MUST have the form that spec 1 uses as the question reference: the name of the question's part, a hyphen, and the row number of the question in that part, counted from 1 in the order of the published file and written with at least three digits, for example `wixqa_expertwritten-017`. An identifier is valid together with the dataset revision it was made at.
- **FR-003**: Every question set MUST be kept in the repository as one record with: its version; its role, golden or held-out; the name and the pinned revision of the dataset; the fingerprint of every part it selects from; the selection rule with every parameter, which is either the parts and the number of questions drawn from each, with the seed and the name of the method of the draw, or the question set that it complements; the question identifiers in a fixed order, each with the gold article ids of its question as the dataset gives them; and the number of questions. With the gold article ids in the record, the measurements of a run can be recomputed from the repository alone.
- **FR-004**: A question set MUST be produced from the dataset by its rule and never typed by hand. The same dataset, the same rule and the same seed MUST give the same record everywhere: the questions that a draw selects depend only on the questions of the part, the number to draw, the seed and the named method of the draw, and not on the machine, the operating system, the time, or the version of any tool. The record holds nothing that changes from one production to the next.
- **FR-005**: A version of a question set MUST be written once. Producing an existing version again with the same dataset, the same rule and the same seed writes nothing and reports that the version exists. A request for another selection or another seed under an existing version MUST be refused. Another selection is a new version, and the versions that runs of the study use change only by an amendment that the owner approves (Principle III). A draw whose result is not wanted, for example because single-article and multi-article questions fell unevenly, is remedied by a new version with another rule, never by another seed.
- **FR-006**: The check of a question set MUST apply the recorded rule to the dataset again, with the recorded seed, and compare. It MUST fail, and name every difference, when a question that the rule selects is not in the record, a question in the record is not selected by the rule, the gold articles of a question differ from the dataset, the number of questions of a part or in total differs from the rule, or the dataset is not the one recorded: another revision or another fingerprint of a part.
- **FR-007**: The check of a question set MUST report its role, its seed or the set it complements, the number of questions per part and in total, the number of single-article questions, of multi-article questions and of questions without a gold article, and the number of question texts that occur more than once.
- **FR-008**: The audit of spec 1 MUST be able to take a question set as its question set, so that it checks every gold article of every question of that set against the index (Principle I). Its result MUST name the question set by version. An audit that names a question set which does not pass its check against the same dataset MUST end as not carried out. An audit that names no question set MUST keep checking every question of every question part, as it does today; a question set is named on purpose.
- **FR-032**: The held-out set of FR-001 MUST be produced as the complement of the golden set: every question of the parts that the golden set draws from which the golden set does not hold. The check of a set made by this rule MUST verify that no question is in both sets and that no question of those parts is in neither, MUST report both numbers, and MUST fail and name every such question. It MUST also report the number of question texts that occur in both sets. It is not carried out when the golden set it names is absent or does not pass its own check.
- **FR-033**: A run MUST be made on exactly one question set. No report and no comparison of this feature puts questions of different sets into one number, so the numbers of the synthetic held-out set are never mixed with those of another set.

**Retrieval metrics and the other numbers of a run**

- **FR-009**: The retrieval metrics MUST be computed as the constitution defines them under "Metric Definitions": on article ids, for the generation list and separately for the retrieved list, each exactly as recorded. No metric is computed on a cut-off or on any other list.
- **FR-010**: For every question that has a gold article, and for each of the two lists that exists for it, the harness MUST give `share_found`, the number of the question's gold articles among the distinct article ids of the list divided by the number of its gold articles, and `all_found`, 1 when every gold article is among them and 0 otherwise.
- **FR-011**: A list that was not produced MUST be told apart from an empty list. An empty list exists, and its question has `share_found` = 0. A question without the list is left out of that list's metrics.
- **FR-012**: For a run and for each of the two lists, the harness MUST give the mean of `share_found` and the share of questions with `all_found` = 1, over the questions that have a gold article and for which the list exists. The number of those questions and the number with `all_found` = 1 MUST be reported with them.
- **FR-013**: The harness MUST list the retrieval misses of a run: the questions whose generation list exists and has `all_found` = 0. A question without a generation list is never a retrieval miss, whatever its status.
- **FR-014**: Every question of a run MUST have exactly one of the five statuses of the constitution: `answered`, `no_answer`, `error`, `timeout`, `call_limit`. The count of each status MUST be reported, and the counts MUST add up to the size of the run's question set.
- **FR-015**: Every number of FR-012, FR-014 and FR-016 MUST be reported three times: for all questions, for single-article questions (exactly one gold article) and for multi-article questions (two or more), each with the number of questions it is computed on.
- **FR-016**: The report of a run MUST carry, next to the retrieval metrics, the cost of answering in US dollars as a run total and per question, and the latency as the median and the 95th percentile over the questions. The cost of a question is its token counts multiplied by the prices recorded in the run config. The median of an even number of values is the mean of the two middle values. The 95th percentile of *n* values is the value at position ⌈0.95 × *n*⌉ when they are sorted in ascending order.
- **FR-017**: There MUST be one computation of these numbers. Later features use it when they record a run, and the check of a run record uses the same one, so that recomputing a summary gives the same numbers.

**Run record and run registry**

- **FR-018**: The run registry MUST hold one record per run, under the run's identifier. A run identifier MUST consist of the run's start time in UTC, to the second, a hyphen, and a short name of lower-case letters, digits and single hyphens, for example `20261201T093000Z-baseline`. It is unique in the registry and is never reused.
- **FR-019**: A run record MUST contain the four parts that the constitution lists under "Run Record Format": the identity (run identifier, start time in UTC, commit of the code); the config (everything needed to repeat the run, with the run's question set named by its version, by its role and by the fingerprint of its record); the results, one entry per question of that set; and the summary.
- **FR-020**: The entry of a question MUST hold the question identifier, the status, the retrieved list and the generation list, the context passed to the generator in a form from which its exact text can be restored, the answer and its hash, the token counts, the cost and the latency. Each list is recorded as ordered article ids, one per item, with repeated ids kept, or as absent. A question with the status `answered` or `no_answer` has both lists and an answer.
- **FR-021**: The summary MUST hold the audit result of Principle I, the count of each status, and the numbers of FR-012 and FR-016 in the three breakdowns with their numbers of questions. The audit result is the result that spec 1 defines, made with the run's question set as the question set and with the outcome passed.
- **FR-022**: The check of a run record MUST fail, and name every defect, when: a part or a field that FR-019 to FR-021 require is absent; the run identifier does not have the form of FR-018 or does not agree with the recorded start time; the config names a question set that is absent, or a role or a fingerprint other than that of the set's record; the results do not hold exactly one entry for every question of the run's question set and no other; a status is not one of the five; a list holds something that is not an article id; the hash of an answer is not the SHA-256 of that answer's text; the cost of an entry is not its token counts multiplied by the recorded prices; the audit result is absent, is not passed, or names another index, dataset revision or question set than the config; or a number of the summary differs from the number that the one computation of FR-017 gives from the other files.
- **FR-023**: For an experiment run the check MUST also fail when the run it names as its baseline is not in the registry, when that run is on another question set, or when the two configs differ in any parameter other than the one the experiment names, or do not differ in that one (Principle VI). The defect names the parameter.
- **FR-024**: The check of the registry MUST check every run in it and MUST report the number of runs and the number of runs that failed.
- **FR-034**: A run on a held-out set MUST be recognisable as such: the report of a run, the check of a run and a comparison MUST state the question set and its role, and the check of the registry MUST report the number of runs on golden sets and the number of runs on held-out sets, so that every use of a held-out set can be seen.
- **FR-035**: An experiment run, which is a run that names a baseline, MUST be on a question set with the role golden. The check of a run record MUST fail for an experiment run on a held-out set and state that an experiment is made on the golden set.
- **FR-025**: A report or a comparison MUST be made only from records that pass the check; otherwise it is refused, with the reason.
- **FR-026**: No command of this feature changes a run record, a question-set record that exists, or the dataset. Recorded files are written once (constitution, "Run Record Format").

**Pairwise comparison**

- **FR-027**: For two runs on the same question set, the comparison MUST report `gained`, the number of questions with `all_found` = 0 on the generation list in the first run and 1 in the second, and `lost`, the number with 1 in the first run and 0 in the second, together with the identifiers of the questions behind each number. The difference of the two numbers is never reported alone.
- **FR-028**: A question that lacks a generation list in either run MUST be left out of the comparison. The number of questions compared and the number left out MUST be reported, with the identifiers of the questions left out.
- **FR-029**: A comparison of two runs whose question sets differ in version or in fingerprint MUST be refused, and the refusal names both. This holds between two versions of the golden set and between the golden set and a held-out set.
- **FR-036**: A comparison of two runs on a held-out set MUST state, next to its numbers, that the set is a held-out set and that its questions are not used to choose a setting.

The golden set has 200 questions. With 200 questions instead of the 400 of the two parts, a small difference between two runs is harder to tell from chance; the owner accepted this cost on 2026-11-27 in exchange for the held-out set. This spec states no statistical threshold. The comparison reports counts and question identifiers and no verdict on whether a difference is real.

**What a program cannot check**

The rule that gives a held-out set its meaning is: a held-out set is never used to choose a setting. The harness checks the part of it that can be read from records: every run names its question set and the role of that set (FR-019, FR-034), an experiment run is on the golden set (FR-035), numbers of different sets are never combined or compared (FR-029, FR-033), and every run on a held-out set is counted in the registry (FR-034). The following only discipline can keep, and no check of this feature claims it:

- that nobody changed a setting after looking at the results of a held-out run. A record does not show why a setting was chosen. What can be reviewed is that every decision cites runs on the golden set (Principle X), and the code review agent and the owner review that;
- that a held-out set is used only at the baseline and at the milestones the owner names. The registry shows how often it was used, not whether each use was named by the owner;
- that the seed was fixed before the draw and the draw was made once. A record shows the seed that was used, not how many were tried. The seeds of the study's sets are stated in this spec, before any draw is made.

**All commands**

- **FR-030**: Every check of this feature MUST end in exactly one of three outcomes that a program can tell apart: passed, failed with every difference named, or not carried out with the reason. Something that was not carried out is never reported as passed or as failed.
- **FR-031**: Making a report, checking a run record or the registry, and comparing two runs MUST need neither the vector store, nor a model provider, nor the dataset host, and no credential.

### Key Entities *(include if feature involves data)*

- **Question identifier**: the name of a question, made of its part and its row number; valid with the dataset revision.
- **Question set**: a fixed list of questions with a version, a role, a rule, the dataset revision and a fingerprint.
- **Role**: golden or held-out. It says what a set may be used for.
- **Golden set**: the question set with the role golden: the working set on which every pipeline version is compared and decisions are taken.
- **Held-out set**: a question set with the role held-out: used rarely and never to choose a setting. The study has two: the complement of the golden set, and the synthetic one.
- **Selection rule**: how the questions of a set are taken from the dataset: a number of questions drawn at random from each listed part, or the complement of another set.
- **Seed**: the number that fixes a random draw, so that the draw can be repeated.
- **Retrieved list**: the ordered list of a question as it stood before reranking, as article ids.
- **Generation list**: the ordered list of a question that was passed to generation, exactly as passed, as article ids.
- **Status**: how a question of a run ended; one of five.
- **Run record**: the identity, the config, the results and the summary of one run.
- **Run registry**: where all run records are kept; today it holds none.
- **Summary**: the numbers of a run, derived from its other files and recomputable at any time.
- **Pairwise comparison**: for two runs on one question set, the questions gained and the questions lost.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The golden set in the repository holds exactly 200 questions, 100 of `wixqa_expertwritten` and 100 of `wixqa_simulated`. The held-out set holds exactly the other 200 questions of those two parts: no question is in both, and none of the 400 is in neither. The synthetic held-out set holds exactly 300 questions of `wixqa_synthetic`. The check of each set against the pinned dataset finds no difference.
- **SC-002**: Every gold article of every question of the three sets is in the index `wixqa-001`: the audit with each set as the question set reports zero mismatches.
- **SC-003**: On the example run, every number of the report equals the number computed by hand from the example's table: the status counts, both retrieval metrics on both lists in the three breakdowns, the retrieval misses, the cost and the latency.
- **SC-004**: Each of the defects introduced on purpose in an example question set or an example run record is caught: the check fails and names exactly that defect.
- **SC-005**: The comparison of the two example runs reports the questions gained and lost that were determined by hand, by number and by identifier; a comparison across two question sets is refused.
- **SC-006**: Recomputing the summary of a recorded run gives the same numbers, and producing a question set twice from the same dataset, rule and seed gives the same record, also where the record to compare with was written beforehand from the definition of the draw.
- **SC-007**: The run registry of the repository passes its check.
- **SC-008**: A run on a held-out set is named as such in its report, in its check and in the count of the registry, and an experiment run on a held-out set is caught by the check.

No baseline run exists, so this spec states no numeric quality target (Principle X).

## Acceptance Checks *(mandatory)*

Each check is one command and the result a reader can observe. Every check fails before the feature is implemented and passes once it is implemented. The testing agent turns each check into an automated acceptance test before any implementation is written (constitution, "Development Workflow"). This section alone names commands; the sections above stay technology-agnostic.

Every command ends with one of three exit codes, as in spec 1: `0` when it passed or did its work, `1` when a check found a difference, `2` when it was refused or not carried out. The last line of the output is the verdict line. Before a verdict of `failed`, every difference is printed on a line that starts with `difference:`; before `refused` or `not carried out`, the reason is printed on a line that starts with `reason:`.

The question sets of the study are kept in `evals/golden/`, the place that Principle III names for the golden set: `golden-001` (the golden set), `held-out-001` (the held-out set) and `synthetic-001` (the synthetic held-out set). The seed of both draws is `20261127`. `--take PART=N` draws N questions from the part PART.

**The example data.** Everything below is written by hand for these checks and is not taken from `Wix/WixQA`. The numbers are illustrations with a known answer, not results.

`tests/data/harness/` is a data directory in the form of spec 1 that passes the dataset check: six articles, `hx-001` to `hx-006`, and three question parts, `hxa` with five questions, `hxb` with three and `hxc` with two. The gold articles of the questions of `hxa` and `hxb` are in the table of the run below; `hxc-001` names `hx-001` and `hxc-002` names `hx-002`.

`tests/data/sets/` holds question-set records. A rule that takes every question of its parts has a content that is known whatever the seed; the two records marked "drawn" are written beforehand from the plan's definition of the draw, without running the implementation.

| Version | Role | What it is |
|---|---|---|
| `harness` | golden | 5 of `hxa` and 3 of `hxb`, seed 1: every question of the two parts, eight questions, four single-article and four multi-article |
| `harness-hxc` | held-out | 2 of `hxc`, seed 1: both questions of `hxc` |
| `harness-one-less` | golden | As `harness`, without `hxb-003` |
| `harness-one-more` | golden | As `harness`, with `hxc-001` added |
| `harness-other-gold` | golden | As `harness`, with `hx-001` as the only gold article of `hxa-003` |
| `harness-half` | golden | Drawn: 3 of `hxa` and 1 of `hxb`, seed 7: four questions |
| `harness-half-rest` | held-out | The complement of `harness-half`: the other two questions of `hxa` and the other two of `hxb` |
| `harness-half-swapped` | golden | As `harness-half`, with one of its questions of `hxa` replaced by a question of `hxa` that the draw does not select |
| `harness-half-rest-overlap` | held-out | As `harness-half-rest`, with one of its questions of `hxa` replaced by a question of `hxa` that is in `harness-half` |
| `example` | golden | 3 of `exq` of `tests/data/example`, the example dataset of spec 1, seed 1: all three questions |

`tests/data/runs/` is a run registry with four records that pass the check. The run `20261101T100000Z-example-a` is on the golden set `harness`; its one model costs 1.00 US dollar per million input tokens and 2.00 per million output tokens:

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

The run `20261102T100000Z-example-b` is on the same question set, names `20261101T100000Z-example-a` as its baseline and differs from it in one config parameter. Its results are those of the table with five changes: the generation list of `hxa-002` is `hx-002`, `hx-003`; the retrieved list of `hxa-003` is `hx-001`, `hx-003`, `hx-004` and its generation list is `hx-003`, `hx-001`; `hxa-004` has the status `answered`; `hxa-005` has the status `answered` and both lists are `hx-005`; both lists of `hxb-003` are `hx-006`, `hx-002`. What the table and these changes leave open in that record, such as the answers and the token counts of the changed questions, is read by no check.

The runs `20261103T100000Z-example-c` and `20261104T100000Z-example-d` are on the held-out set `harness-hxc`, and neither names a baseline. In both, the two questions have the status `answered`, and the retrieved list equals the generation list. In `example-c` the list of `hxc-001` is `hx-001` and the list of `hxc-002` is `hx-003`; in `example-d` the list of `hxc-001` is `hx-001` and the list of `hxc-002` is `hx-002`.

`tests/data/runs-invalid/` is a run registry with nine records: copies of `20261101T100000Z-example-a` and of `20261103T100000Z-example-c`, which pass the check, and seven records that each have one defect. The first six differ from `example-a` in their identifier and in the defect; the seventh differs from `example-c` in the same way.

| Run | The one defect |
|---|---|
| `20261101T100100Z-no-latency` | The entry of `hxa-003` has no latency |
| `20261101T100200Z-missing-question` | The results have no entry for `hxb-003` |
| `20261101T100300Z-unknown-status` | The status of `hxa-004` is `skipped` |
| `20261101T100400Z-wrong-hash` | The hash recorded for the answer of `hxa-001` is not the hash of that answer |
| `20261101T100500Z-stale-summary` | The summary states 3 questions with every gold article in the generation list; the results give 2 |
| `20261101T100600Z-two-changes` | It names `20261101T100000Z-example-a` as its baseline and one config parameter as changed, and differs from the baseline in a second parameter as well |
| `20261103T100100Z-experiment-on-held-out` | It names `20261103T100000Z-example-c` as its baseline and differs from it in the one config parameter it names: an experiment run on the held-out set `harness-hxc` |

**The question sets**

- **AC-001** (covers US1, FR-001, FR-002, FR-003, FR-004, FR-005, SC-001): `python -m wixqa_rag set build --version golden-001 --role golden --take wixqa_expertwritten=100 --take wixqa_simulated=100 --seed 20261127` → exit code 0; the output names the pinned revision and contains `wixqa_expertwritten: 100`, `wixqa_simulated: 100`, `questions: 200` and `set build: done`, and no line for `wixqa_synthetic`; afterwards the file `evals/golden/golden-001.json` names the pinned revision, the role `golden`, the rule, the seed `20261127` and 200 question identifiers, 100 that start with `wixqa_expertwritten-` and 100 that start with `wixqa_simulated-`
- **AC-002** (covers US1, FR-006, FR-007, SC-001): `python -m wixqa_rag set check --version golden-001` → exit code 0; the output contains `role: golden`, `seed: 20261127`, `wixqa_expertwritten: 100`, `wixqa_simulated: 100`, `questions: 200`, `questions without gold articles: 0`, a line `single-article:` and a line `multi-article:` whose two numbers add up to 200, and `set check: passed`
- **AC-003** (covers US1, FR-004, FR-005, SC-006): `python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets --version harness --role golden --take hxa=5 --take hxb=3 --seed 1 && python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets --version harness --role golden --take hxa=5 --take hxb=3 --seed 1` → exit code 0; the output contains `hxa: 5`, `hxb: 3` and `questions: 8`; the second build prints `question set: harness (already written)`
- **AC-004** (covers US1, FR-005): `python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets --version harness --role golden --take hxa=5 --take hxb=3 --seed 1 && python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets --version harness --role golden --take hxa=5 --seed 1` → exit code 2 and the line `set build: refused`, with the reason that `harness` exists with another selection
- **AC-005** (covers US1, FR-003, FR-006, FR-007): `python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets --version harness --role golden --take hxa=5 --take hxb=3 --seed 1 && python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir data/sets --version harness && python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets --version harness` → exit code 0; both checks print `role: golden`, `seed: 1`, `questions: 8`, `single-article: 4`, `multi-article: 4`, `questions without gold articles: 0` and `set check: passed`, and no line for `hxc`
- **AC-006** (covers US1, FR-006, SC-004): `python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets --version harness-one-less` → exit code 1, the line `set check: failed`, and a `difference:` line that names `hxb-003` as selected by the rule and not in the question set
- **AC-007** (covers US1, FR-006, SC-004): `python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets --version harness-one-more` → exit code 1, the line `set check: failed`, and a `difference:` line that names `hxc-001` as in the question set and not selected by the rule
- **AC-008** (covers US1, FR-006, SC-004): `python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets --version harness-other-gold` → exit code 1, the line `set check: failed`, and a `difference:` line that names `hxa-003` and the article `hx-003`
- **AC-009** (covers US1, FR-008, SC-002): `python -m wixqa_rag index audit --index wixqa-001 --set golden-001` → exit code 0; the output contains `question set: golden-001 (golden)`, `questions: 200`, `missing from index: 0`, `not in corpus: 0`, `unknown question references: 0` and `audit: passed`
- **AC-010** (covers US1, FR-008): `python -m wixqa_rag index build --data-dir tests/data/example --index example && python -m wixqa_rag index audit --data-dir tests/data/example --index example --sets-dir tests/data/sets --set example` → exit code 0; the output contains `question set: example (golden)`, `questions: 3`, `unknown question references: 0` and `audit: passed`
- **AC-011** (covers US1, FR-008, FR-030): `python -m wixqa_rag index build --data-dir tests/data/example --index example && python -m wixqa_rag index audit --data-dir tests/data/example --index example --sets-dir tests/data/sets --set harness` → exit code 2 and the line `audit: not carried out`, with the reason that the question set `harness` does not match the dataset
- **AC-033** (covers US1, FR-004, FR-032, SC-006): `python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets --version harness-half --role golden --take hxa=3 --take hxb=1 --seed 7 && python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets --version harness-half-rest --role held-out --complement-of harness-half && python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir data/sets --version harness-half && python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir data/sets --version harness-half-rest` → exit code 0; the first check prints `role: golden`, `seed: 7`, `hxa: 3`, `hxb: 1` and `questions: 4`; the second prints `role: held-out`, `complement of: harness-half`, `hxa: 2`, `hxb: 2`, `questions: 4`, `in both sets: 0` and `in neither set: 0`; both end with `set check: passed`
- **AC-034** (covers US1, FR-004, FR-006, FR-032, SC-006): `python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets --version harness-half && python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets --version harness-half-rest` → exit code 0; both checks end with `set check: passed`: the draw that the command makes with the seed 7 selects exactly the questions of the record that was written beforehand
- **AC-035** (covers US1, FR-006, SC-004): `python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets --version harness-half-swapped` → exit code 1, the line `set check: failed`, and exactly two `difference:` lines, each naming a question of `hxa`: one selected by the rule and not in the question set, one in the question set and not selected by the rule
- **AC-036** (covers US1, FR-032, SC-004): `python -m wixqa_rag set check --data-dir tests/data/harness --sets-dir tests/data/sets --version harness-half-rest-overlap` → exit code 1; the output contains `in both sets: 1`, `in neither set: 1` and `set check: failed`
- **AC-037** (covers US1, FR-001, FR-032, SC-001): `python -m wixqa_rag set build --version golden-001 --role golden --take wixqa_expertwritten=100 --take wixqa_simulated=100 --seed 20261127 && python -m wixqa_rag set build --version held-out-001 --role held-out --complement-of golden-001` → exit code 0; the output of the second build contains `wixqa_expertwritten: 100`, `wixqa_simulated: 100`, `questions: 200` and `set build: done`; afterwards the file `evals/golden/held-out-001.json` names the pinned revision, the role `held-out`, the set `golden-001` that it complements and 200 question identifiers
- **AC-038** (covers US1, FR-001, FR-033, SC-001): `python -m wixqa_rag set build --version synthetic-001 --role held-out --take wixqa_synthetic=300 --seed 20261127` → exit code 0; the output contains `wixqa_synthetic: 300`, `questions: 300` and `set build: done`, and no line for another part; afterwards the file `evals/golden/synthetic-001.json` names the pinned revision, the role `held-out`, the seed `20261127` and 300 question identifiers that all start with `wixqa_synthetic-`
- **AC-039** (covers US1, FR-006, FR-007, FR-032, SC-001): `python -m wixqa_rag set check --version held-out-001` → exit code 0; the output contains `role: held-out`, `complement of: golden-001`, `wixqa_expertwritten: 100`, `wixqa_simulated: 100`, `questions: 200`, `in both sets: 0`, `in neither set: 0`, a line `question texts in both sets:`, `questions without gold articles: 0` and `set check: passed`
- **AC-040** (covers US1, FR-006, FR-007, SC-001): `python -m wixqa_rag set check --version synthetic-001` → exit code 0; the output contains `role: held-out`, `seed: 20261127`, `wixqa_synthetic: 300`, `questions: 300`, `questions without gold articles: 0` and `set check: passed`
- **AC-041** (covers US1, FR-008, SC-002): `python -m wixqa_rag index audit --index wixqa-001 --set held-out-001 && python -m wixqa_rag index audit --index wixqa-001 --set synthetic-001` → exit code 0; the output contains `question set: held-out-001 (held-out)` with `questions: 200`, `question set: synthetic-001 (held-out)` with `questions: 300`, and for both audits `unknown question references: 0` and `audit: passed`
- **AC-044** (covers US1, FR-005): `python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets --version harness --role golden --take hxa=5 --take hxb=3 --seed 1 && python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets --version harness --role golden --take hxa=5 --take hxb=3 --seed 2` → exit code 2 and the line `set build: refused`, with the reason that `harness` exists with another seed
- **AC-045** (covers US1, FR-006, FR-030): `python -m wixqa_rag set build --data-dir tests/data/harness --sets-dir data/sets --version harness-too-many --role held-out --take hxc=3 --seed 1` → exit code 2 and the line `set build: refused`, with a reason that names `hxc` and the numbers 3 and 2; no record `harness-too-many` is written

**The report of a run**

- **AC-012** (covers US2, FR-014, FR-015, SC-003): `python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets --run 20261101T100000Z-example-a` → exit code 0; the output contains the lines `status, all questions: 8 questions, answered 4, no_answer 1, error 1, timeout 1, call_limit 1`, `status, single-article: 4 questions, answered 2, no_answer 0, error 1, timeout 0, call_limit 1` and `status, multi-article: 4 questions, answered 2, no_answer 1, error 0, timeout 1, call_limit 0`, and ends with `run report: done`
- **AC-013** (covers US2, FR-009, FR-010, FR-011, FR-012, FR-015, SC-003): the command of AC-012 → the output contains the lines `generation list, all questions: 6 questions, mean share_found 0.5278, all_found 2 of 6 (0.3333)`, `generation list, single-article: 3 questions, mean share_found 0.3333, all_found 1 of 3 (0.3333)` and `generation list, multi-article: 3 questions, mean share_found 0.7222, all_found 1 of 3 (0.3333)`
- **AC-014** (covers US2, FR-009, FR-010, FR-011, FR-012, FR-015, SC-003): the command of AC-012 → the output contains the lines `retrieved list, all questions: 7 questions, mean share_found 0.7857, all_found 5 of 7 (0.7143)`, `retrieved list, single-article: 3 questions, mean share_found 0.6667, all_found 2 of 3 (0.6667)` and `retrieved list, multi-article: 4 questions, mean share_found 0.8750, all_found 3 of 4 (0.7500)`
- **AC-015** (covers US2, FR-013, SC-003): the command of AC-012 → the output contains the line `retrieval misses: 4`, followed by the four lines `  hxa-002`, `  hxa-003`, `  hxa-004` and `  hxb-002`; it names neither `hxa-005` nor `hxb-001` as a miss
- **AC-016** (covers US2, FR-015, FR-016, SC-003): the command of AC-012 → the output contains the lines `cost_usd answering, all questions: 8 questions, total 0.01280000, per question 0.00160000`, `cost_usd answering, single-article: 4 questions, total 0.00600000, per question 0.00150000`, `cost_usd answering, multi-article: 4 questions, total 0.00680000, per question 0.00170000`, `latency_seconds, all questions: 8 questions, median 4.500, p95 30.000`, `latency_seconds, single-article: 4 questions, median 3.500, p95 7.000` and `latency_seconds, multi-article: 4 questions, median 6.000, p95 30.000`
- **AC-017** (covers US2, FR-010, FR-011): `python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets --run 20261101T100000Z-example-a --per-question` → exit code 0; the output contains the lines `  hxa-004: no_answer; generation list 2 of 3, all_found 0; retrieved list 3 of 3, all_found 1`, `  hxa-005: error; generation list absent; retrieved list absent` and `  hxb-002: call_limit; generation list 0 of 1, all_found 0; retrieved list 0 of 1, all_found 0`

**The run record and the registry**

- **AC-018** (covers US3, FR-017, FR-018, FR-019, FR-020, FR-021, FR-022, FR-031, SC-006): `env -u DATABASE_URL -u OPENAI_API_KEY python -m wixqa_rag run check --runs-dir tests/data/runs --sets-dir tests/data/sets --run 20261101T100000Z-example-a` → exit code 0; the output contains `run: 20261101T100000Z-example-a`, `question set: harness (golden)`, `questions: 8` and `run check: passed`
- **AC-019** (covers US3, FR-023, FR-024, FR-034, SC-008): `python -m wixqa_rag run check --runs-dir tests/data/runs --sets-dir tests/data/sets` → exit code 0; the output contains `runs: 4`, `failed runs: 0`, `runs on golden sets: 2`, `runs on held-out sets: 2` and `run check: passed`
- **AC-020** (covers US3, FR-024, FR-026, FR-030, SC-007): `python -m wixqa_rag run check && git status --porcelain evals/runs/` → exit code 0; the output contains `failed runs: 0` and `run check: passed`, and `git status` prints nothing: no file under `evals/runs/` is added or changed
- **AC-021** (covers US3, FR-022, SC-004): `python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir tests/data/sets --run 20261101T100100Z-no-latency` → exit code 1, the line `run check: failed`, and a `difference:` line that names `hxa-003` and the latency
- **AC-022** (covers US3, FR-014, FR-022, SC-004): `python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir tests/data/sets --run 20261101T100200Z-missing-question` → exit code 1, the line `run check: failed`, and a `difference:` line that names `hxb-003` as a question of the run's question set without an entry
- **AC-023** (covers US3, FR-014, FR-022, SC-004): `python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir tests/data/sets --run 20261101T100300Z-unknown-status` → exit code 1, the line `run check: failed`, and a `difference:` line that names `hxa-004` and the status `skipped`
- **AC-024** (covers US3, FR-022, SC-004): `python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir tests/data/sets --run 20261101T100400Z-wrong-hash` → exit code 1, the line `run check: failed`, and a `difference:` line that names `hxa-001` and the hash of its answer
- **AC-025** (covers US3, FR-017, FR-022, SC-004, SC-006): `python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir tests/data/sets --run 20261101T100500Z-stale-summary` → exit code 1, the line `run check: failed`, and a `difference:` line that names the generation list and both numbers, 3 and 2
- **AC-026** (covers US3, FR-023, SC-004): `python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir tests/data/sets --run 20261101T100600Z-two-changes` → exit code 1, the line `run check: failed`, and a `difference:` line that names the second config parameter that differs from `20261101T100000Z-example-a`
- **AC-027** (covers US3, FR-024): `python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir tests/data/sets` → exit code 1; the output contains `runs: 9`, `failed runs: 7` and `run check: failed`
- **AC-028** (covers US3, FR-030): `python -m wixqa_rag run check --runs-dir tests/data/runs --sets-dir tests/data/sets --run 20261101T100000Z-no-such-run` → exit code 2 and the line `run check: not carried out`, with the reason that the run `20261101T100000Z-no-such-run` does not exist
- **AC-042** (covers US2, US3, FR-034, SC-008): `python -m wixqa_rag run report --runs-dir tests/data/runs --sets-dir tests/data/sets --run 20261103T100000Z-example-c && python -m wixqa_rag run check --runs-dir tests/data/runs --sets-dir tests/data/sets --run 20261103T100000Z-example-c` → exit code 0; the output of both commands contains `question set: harness-hxc (held-out)`; the report contains `generation list, all questions: 2 questions, mean share_found 0.5000, all_found 1 of 2 (0.5000)`
- **AC-043** (covers US3, FR-035, SC-004, SC-008): `python -m wixqa_rag run check --runs-dir tests/data/runs-invalid --sets-dir tests/data/sets --run 20261103T100100Z-experiment-on-held-out` → exit code 1, the line `run check: failed`, and a `difference:` line that names the held-out set `harness-hxc` and states that an experiment run is made on a golden set
- **AC-029** (covers US3, FR-025): `python -m wixqa_rag run report --runs-dir tests/data/runs-invalid --sets-dir tests/data/sets --run 20261101T100500Z-stale-summary` → exit code 2 and the line `run report: refused`, with the reason that the run check failed

**The pairwise comparison**

- **AC-030** (covers US4, FR-027, FR-028, FR-031, SC-005): `env -u DATABASE_URL -u OPENAI_API_KEY python -m wixqa_rag run compare --runs-dir tests/data/runs --sets-dir tests/data/sets --first 20261101T100000Z-example-a --second 20261102T100000Z-example-b` → exit code 0; the output contains `question set: harness (golden)`; `compared: 6`; `left out: 2`, followed by `  hxa-005` and `  hxb-001`; `gained: 2`, followed by `  hxa-002` and `  hxa-003`; `lost: 1`, followed by `  hxb-003`; and `run compare: done`
- **AC-031** (covers US4, FR-029, FR-033, SC-005): `python -m wixqa_rag run compare --runs-dir tests/data/runs --sets-dir tests/data/sets --first 20261101T100000Z-example-a --second 20261103T100000Z-example-c` → exit code 2 and the line `run compare: refused`, with a reason that names the question sets `harness` and `harness-hxc`
- **AC-032** (covers US4, FR-025): `python -m wixqa_rag run compare --runs-dir tests/data/runs-invalid --sets-dir tests/data/sets --first 20261101T100000Z-example-a --second 20261101T100400Z-wrong-hash` → exit code 2 and the line `run compare: refused`, with the reason that the run check failed for `20261101T100400Z-wrong-hash`
- **AC-046** (covers US4, FR-034, FR-036): `python -m wixqa_rag run compare --runs-dir tests/data/runs --sets-dir tests/data/sets --first 20261103T100000Z-example-c --second 20261104T100000Z-example-d` → exit code 0; the output contains `question set: harness-hxc (held-out)`, the line `held-out set: its questions are not used to choose a setting`, `compared: 2`, `left out: 0`, `gained: 1`, followed by `  hxc-002`, `lost: 0` and `run compare: done`

## Evidence *(mandatory)*

This spec decides nothing about the pipeline and states no numeric quality target: it builds the means of measuring, and no run exists in `evals/runs/`. The composition of the three question sets (FR-001) is the owner's decision of 2026-11-27 and rests on no run. The seed `20261127` of the two draws is chosen before any draw is made and rests on no run either.

## Assumptions

- Commands are typed in a POSIX shell at the repository root, in the project's Python environment set up as the README describes.
- AC-001, AC-002, AC-009 and AC-037 to AC-041 need the local copy of the pinned dataset, and AC-009, AC-010, AC-011 and AC-041 need the vector store. By the owner's decision of 2026-11-24 they run on GitHub Actions, started by hand. AC-009 and AC-041 audit the index `wixqa-001` restored from its recorded snapshot, so nothing is embedded for them. AC-010 and AC-011 use the example index of spec 1, whose first build embeds a few hundred tokens. No other check of this spec calls a provider.
- The three records `evals/golden/golden-001.json`, `evals/golden/held-out-001.json` and `evals/golden/synthetic-001.json` are produced where the pinned dataset can be fetched and reach `main` through the pull request of this spec. The plan fixes how.
- The constitution leaves to this spec "the file names, the field names, the form of a run id and the form of a question identifier". This spec fixes the two forms (FR-002, FR-018) and what every record holds. The contracts of this spec's plan fix the file names and the field names, as the plan of spec 1 did for its records.
- Principle III asks for the selection rule and, where the rule draws at random, the seed. The golden set and the synthetic held-out set record their seed. The held-out set records the golden set it complements and draws nothing itself. The seed of both draws is `20261127`, the day of the owner's decision; it is stated here before any draw is made.
- The spec says what a draw has to guarantee (FR-004). The plan defines the method of the draw completely, so that the two example records marked "drawn" can be written from that definition before the implementation exists.
- The draw takes a fixed number of questions from each part and balances nothing else. How many single-article and multi-article questions fall into the golden set and into the held-out set is left to the draw, and the check of each set reports both numbers (owner's answer of 2026-11-27). If they fall unevenly, the remedy is a new version with a balanced rule, never another seed (FR-005).
- This spec is written against the constitution in version 1.2.0, which gives held-out sets their rules (Principles I, III and X, "Metric Definitions", "Run Record Format"). Principle III places the golden set in `evals/golden/` and asks only that a held-out set is recorded in the repository in the same form; this spec keeps the held-out records in `evals/golden/` next to the golden set.
- The constitution names the 95th percentile and the median of the latency without a method. FR-016 fixes one for each. They are definitions of the ruler, not targets.
- The constitution lists answer quality and calibration among the metrics of a summary. They need the judge of spec 4, and a recorded file is never edited. This spec reads the two rules together as follows: the summary written with a run holds the numbers that the run's own files give (the audit result, the status counts, the retrieval metrics, the cost of answering and the latency), and spec 4 adds the judge's numbers and the cost of judging in files of its own. The pairwise comparison on the outcome `correct` arrives with spec 4 for the same reason; here it is made on `all_found` of the generation list.
- Principle VIII asks for every metric in three breakdowns. This spec applies it to the retrieval metrics, the status counts, the cost and the latency.
- Writing a run record is the task of the feature that makes runs (spec 3). This feature fixes the format, provides the one computation of the summary and the check that every record has to pass.
- Principle VI and the constitution's `TODO(REFERENCE_AFTER_ADOPTION)` leave open which run later experiments start from. FR-023 compares an experiment with the run that its record names as its baseline and takes no side in that decision.
- A config parameter, for FR-023, is one named setting of the config. The identity of a run (its identifier, its start time, the commit of the code) is not part of the config.
- The option that names a question set for the audit is added to the command of spec 1 without changing what that command does when the option is absent. The plan of this spec records the addition to the contracts of spec 1.
- The example data under `tests/data/harness/`, `tests/data/sets/`, `tests/data/runs/` and `tests/data/runs-invalid/` is written for the acceptance checks and is not taken from `Wix/WixQA`. The example datasets of spec 1 stay as they are.
- A listing of the runs in the registry for readers, and any chart or page of results, are not part of this feature.
