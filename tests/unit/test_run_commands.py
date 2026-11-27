"""The three commands of the group `run` as commands (task T081): `run report`, `run check`
and `run compare` of `src/wixqa_rag/runs.py` and `src/wixqa_rag/cli.py`.

Covers:

- spec.md, FR-026: no command of this feature changes a run record, a question-set record
  that exists, or the dataset; FR-030; FR-031: a report, a check and a comparison need
  neither the vector store, nor a model provider, nor the dataset host, and no credential;
- contracts/cli.md, "General rules", and spec 1's contracts/cli.md, "Output", rule 7: wrong
  arguments of a named command end with a `reason:` line, the verdict `not carried out` of
  that command and exit code 2;
- contracts/cli.md, "`run report`": the whole report, the block of `--per-question`, the
  digits of each kind of number, `undefined` for a number over no question, and the table of
  the verdicts;
- contracts/harness.md, "Rules", 1: `runs` and `metrics` import neither `store`, nor
  `embedding`, nor `audit`.

`run compare` is implemented with User Story 4 (tasks.md, T096 and T097). tasks.md, T081,
names it here for three things, and this file tests exactly these of it: its wrong
arguments, that it runs without the two settings, and that it changes no file. Its output is
the subject of the tests of User Story 4.

The commands are typed in a temporary repository root with a copy of the example registries
(the fixture `registry_copy` of tests/conftest.py), except in the one test that reads the
files of `tests/data/` themselves. All documents named here are in
specs/002-evaluation-harness/ unless spec 1 is named.
"""

import json
import shutil
import subprocess
import sys

import pytest

RUN_A = "20261101T100000Z-example-a"
RUN_B = "20261102T100000Z-example-b"
RUN_C = "20261103T100000Z-example-c"
RUN_D = "20261104T100000Z-example-d"
STALE = "20261101T100500Z-stale-summary"
WRONG_HASH = "20261101T100400Z-wrong-hash"

RUNS = "data/runs"
RUNS_INVALID = "data/runs-invalid"
SETS = "data/sets"
DIRECTORIES = f"--runs-dir {RUNS} --sets-dir {SETS}"

# Invented values, long enough to be told apart from every other text; none is a credential.
INVENTED_SETTINGS = {
    "DATABASE_URL": "postgresql://store-user@store.invalid:5432/value-that-is-never-printed",
    "OPENAI_API_KEY": "invented-key-value-that-is-never-printed-7f3a91",
}

# contracts/cli.md, "`run report`", "Output for `tests/data/runs/20261101T100000Z-example-a`".
REPORT_A = [
    f"run: {RUN_A}",
    "question set: harness (golden)",
    "questions: 8",
    "status, all questions: 8 questions, answered 4, no_answer 1, error 1, timeout 1, call_limit 1",
    "status, single-article: 4 questions, answered 2, no_answer 0, error 1, timeout 0,"
    " call_limit 1",
    "status, multi-article: 4 questions, answered 2, no_answer 1, error 0, timeout 1, call_limit 0",
    "generation list, all questions: 6 questions, mean share_found 0.5278,"
    " all_found 2 of 6 (0.3333)",
    "generation list, single-article: 3 questions, mean share_found 0.3333,"
    " all_found 1 of 3 (0.3333)",
    "generation list, multi-article: 3 questions, mean share_found 0.7222,"
    " all_found 1 of 3 (0.3333)",
    "retrieved list, all questions: 7 questions, mean share_found 0.7857,"
    " all_found 5 of 7 (0.7143)",
    "retrieved list, single-article: 3 questions, mean share_found 0.6667,"
    " all_found 2 of 3 (0.6667)",
    "retrieved list, multi-article: 4 questions, mean share_found 0.8750,"
    " all_found 3 of 4 (0.7500)",
    "retrieval misses: 4",
    "  hxa-002",
    "  hxa-003",
    "  hxa-004",
    "  hxb-002",
    "questions without gold articles: 0",
    "cost_usd answering, all questions: 8 questions, total 0.01280000, per question 0.00160000",
    "cost_usd answering, single-article: 4 questions, total 0.00600000, per question 0.00150000",
    "cost_usd answering, multi-article: 4 questions, total 0.00680000, per question 0.00170000",
    "latency_seconds, all questions: 8 questions, median 4.500, p95 30.000",
    "latency_seconds, single-article: 4 questions, median 3.500, p95 7.000",
    "latency_seconds, multi-article: 4 questions, median 6.000, p95 30.000",
]
# The same section, the block of `--per-question`.
PER_QUESTION_A = [
    "per question: 8",
    "  hxa-001: answered; generation list 1 of 1, all_found 1; retrieved list 1 of 1, all_found 1",
    "  hxa-002: answered; generation list 0 of 1, all_found 0; retrieved list 1 of 1, all_found 1",
    "  hxa-003: answered; generation list 1 of 2, all_found 0; retrieved list 1 of 2, all_found 0",
    "  hxa-004: no_answer; generation list 2 of 3, all_found 0; retrieved list 3 of 3, all_found 1",
    "  hxa-005: error; generation list absent; retrieved list absent",
    "  hxb-001: timeout; generation list absent; retrieved list 2 of 2, all_found 1",
    "  hxb-002: call_limit; generation list 0 of 1, all_found 0; retrieved list 0 of 1,"
    " all_found 0",
    "  hxb-003: answered; generation list 2 of 2, all_found 1; retrieved list 2 of 2, all_found 1",
]
# The report of `example-c`, from the numbers of its summary (data-model.md, "The numbers of
# the four summaries") in the forms of contracts/cli.md: four digits for a mean and a share,
# eight for a cost, three for a latency, and `undefined` for a number that is `null`.
REPORT_C = [
    f"run: {RUN_C}",
    "question set: harness-hxc (held-out)",
    "questions: 2",
    "status, all questions: 2 questions, answered 2, no_answer 0, error 0, timeout 0, call_limit 0",
    "status, single-article: 2 questions, answered 2, no_answer 0, error 0, timeout 0,"
    " call_limit 0",
    "status, multi-article: 0 questions, answered 0, no_answer 0, error 0, timeout 0, call_limit 0",
    "generation list, all questions: 2 questions, mean share_found 0.5000,"
    " all_found 1 of 2 (0.5000)",
    "generation list, single-article: 2 questions, mean share_found 0.5000,"
    " all_found 1 of 2 (0.5000)",
    "generation list, multi-article: 0 questions, mean share_found undefined,"
    " all_found 0 of 0 (undefined)",
    "retrieved list, all questions: 2 questions, mean share_found 0.5000,"
    " all_found 1 of 2 (0.5000)",
    "retrieved list, single-article: 2 questions, mean share_found 0.5000,"
    " all_found 1 of 2 (0.5000)",
    "retrieved list, multi-article: 0 questions, mean share_found undefined,"
    " all_found 0 of 0 (undefined)",
    "retrieval misses: 1",
    "  hxc-002",
    "questions without gold articles: 0",
    "cost_usd answering, all questions: 2 questions, total 0.00240000, per question 0.00120000",
    "cost_usd answering, single-article: 2 questions, total 0.00240000, per question 0.00120000",
    "cost_usd answering, multi-article: 0 questions, total 0.00000000, per question undefined",
    "latency_seconds, all questions: 2 questions, median 1.500, p95 2.000",
    "latency_seconds, single-article: 2 questions, median 1.500, p95 2.000",
    "latency_seconds, multi-article: 0 questions, median undefined, p95 undefined",
]


@pytest.fixture
def typed(registry_copy, run_command):
    """Type a command of the program in the temporary repository root."""

    def command(arguments: str, **keywords):
        return run_command(f"python -m wixqa_rag {arguments}", cwd=registry_copy.root, **keywords)

    return command


def assert_wrong_arguments(result, name: str) -> None:
    """A `reason:` line, the verdict `not carried out` of the command and exit code 2."""
    assert result.exit_code == 2, result.stdout
    assert result.last_line == f"{name}: not carried out", (
        f"standard output:\n{result.stdout}\nstandard error:\n{result.stderr}"
    )
    assert result.reasons and all(result.reasons), "a `reason:` line gives the reason"
    assert not any(line.endswith((": done", ": passed", ": failed")) for line in result.lines)
    assert result.settings_printed == ()


# --- Wrong arguments (contracts/cli.md, "General rules") ----------------------------------------


@pytest.mark.parametrize(
    "arguments",
    [
        "",
        DIRECTORIES,
        "--run",
        f"--run {RUN_A} --no-such-option",
        f"--run {RUN_A} unexpected-argument",
        f"--run {RUN_A} --runs-dir",
        f"--run {RUN_A} --sets-dir",
        f"--run {RUN_A} --per-question yes",
        f"--run {RUN_A} --data-dir tests/data/harness",
        f"--first {RUN_A} --second {RUN_B}",
    ],
    ids=[
        "no argument",
        "the required --run left out",
        "--run without its value",
        "an unknown option",
        "an argument too many",
        "--runs-dir without its value",
        "--sets-dir without its value",
        "a value for --per-question",
        "--data-dir, which the command does not take",
        "the options of run compare",
    ],
)
def test_wrong_arguments_of_run_report_end_with_its_verdict(typed, arguments):
    """contracts/cli.md, "`run report`": `run report --run ID [--per-question] [--runs-dir
    DIR] [--sets-dir DIR]`; `--run` is required."""
    assert_wrong_arguments(typed(f"run report {arguments}"), "run report")


@pytest.mark.parametrize(
    "arguments",
    [
        "--run",
        "--no-such-option",
        "unexpected-argument",
        f"--run {RUN_A} unexpected-argument",
        "--runs-dir",
        "--sets-dir",
        f"--run {RUN_A} --per-question",
        "--data-dir tests/data/harness",
        f"--first {RUN_A} --second {RUN_B}",
    ],
    ids=[
        "--run without its value",
        "an unknown option",
        "an argument too many",
        "an argument too many after --run",
        "--runs-dir without its value",
        "--sets-dir without its value",
        "--per-question, which belongs to run report",
        "--data-dir, which the command does not take",
        "the options of run compare",
    ],
)
def test_wrong_arguments_of_run_check_end_with_its_verdict(typed, arguments):
    """contracts/cli.md, "`run check`": `run check [--run ID] [--runs-dir DIR] [--sets-dir
    DIR]`."""
    assert_wrong_arguments(typed(f"run check {arguments}"), "run check")


@pytest.mark.parametrize(
    "arguments",
    [
        "",
        f"--first {RUN_A}",
        f"--second {RUN_B}",
        f"--first --second {RUN_B}",
        f"--first {RUN_A} --second",
        f"--first {RUN_A} --second {RUN_B} --no-such-option",
        f"--first {RUN_A} --second {RUN_B} unexpected-argument",
        f"--first {RUN_A} --second {RUN_B} --runs-dir",
        f"--first {RUN_A} --second {RUN_B} --per-question",
        f"--run {RUN_A}",
    ],
    ids=[
        "no argument",
        "the required --second left out",
        "the required --first left out",
        "--first without its value",
        "--second without its value",
        "an unknown option",
        "an argument too many",
        "--runs-dir without its value",
        "--per-question, which belongs to run report",
        "the option of the two other commands",
    ],
)
def test_wrong_arguments_of_run_compare_end_with_its_verdict(typed, arguments):
    """contracts/cli.md, "`run compare`": `run compare --first ID --second ID [--runs-dir
    DIR] [--sets-dir DIR]`; both runs are required."""
    assert_wrong_arguments(typed(f"run compare {arguments}"), "run compare")


@pytest.mark.parametrize(
    ("command", "arguments"),
    [
        ("run report", f"--run {RUN_A} {DIRECTORIES}"),
        ("run check", DIRECTORIES),
        ("run compare", f"--first {RUN_A} --second {RUN_B} {DIRECTORIES}"),
    ],
)
def test_typed_where_no_dataset_json_exists_a_command_is_not_carried_out(
    tmp_path, run_command, command, arguments
):
    """contracts/cli.md, "General rules": "A command is typed at the repository root and
    reads `dataset.json` from the current directory; without it the command is not carried
    out." research.md, section 10: the three commands read it, as every command does."""
    result = run_command(f"python -m wixqa_rag {command} {arguments}", cwd=tmp_path)

    assert_wrong_arguments(result, command)
    assert any("dataset.json" in reason for reason in result.reasons)
    assert list(tmp_path.iterdir()) == []


# --- No store, no provider, no setting (FR-031) -------------------------------------------------


def test_runs_and_metrics_import_neither_store_nor_embedding_nor_audit():
    """contracts/harness.md, "Rules", 1: "Neither `metrics` nor `runs` imports `store`,
    `embedding` or `audit`, so the three `run` commands cannot reach the store or a provider"
    (FR-031). A new interpreter imports the two modules; none of the three is loaded, and
    neither the driver of the store nor the library of the provider."""
    script = (
        "import sys, json; import wixqa_rag.runs, wixqa_rag.metrics; "
        "print(json.dumps(sorted(name for name in sys.modules "
        "if name.split('.')[0] in ('wixqa_rag', 'psycopg', 'openai'))))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )

    assert completed.returncode == 0, completed.stderr
    loaded = json.loads(completed.stdout)
    assert "wixqa_rag.runs" in loaded and "wixqa_rag.metrics" in loaded
    for module in ("wixqa_rag.store", "wixqa_rag.embedding", "wixqa_rag.audit"):
        assert module not in loaded, f"`runs` or `metrics` imports {module}"
    assert not [name for name in loaded if name.split(".")[0] in ("psycopg", "openai")], loaded


@pytest.mark.parametrize(
    ("arguments", "verdict"),
    [
        (f"run report {DIRECTORIES} --run {RUN_A}", "run report: done"),
        (f"run report {DIRECTORIES} --run {RUN_A} --per-question", "run report: done"),
        (f"run check {DIRECTORIES} --run {RUN_A}", "run check: passed"),
        (f"run check {DIRECTORIES}", "run check: passed"),
        (f"run compare {DIRECTORIES} --first {RUN_A} --second {RUN_B}", "run compare: done"),
    ],
    ids=[
        "run report",
        "run report --per-question",
        "run check",
        "run check, registry",
        "run compare",
    ],
)
def test_the_three_commands_run_with_the_two_settings_removed(typed, arguments, verdict):
    """tasks.md, T081, and FR-031: the three commands run with `DATABASE_URL` and
    `OPENAI_API_KEY` removed from the environment. contracts/cli.md, "Settings": they "read
    no setting at all"."""
    result = typed(arguments, env={"DATABASE_URL": None, "OPENAI_API_KEY": None})

    assert result.exit_code == 0, f"{result.stdout}\n{result.stderr}"
    assert result.last_line == verdict
    assert not result.reasons


@pytest.mark.parametrize(
    ("arguments", "exit_code", "verdict"),
    [
        (f"run report {DIRECTORIES} --run {RUN_C}", 0, "run report: done"),
        (f"run check --runs-dir {RUNS_INVALID} --sets-dir {SETS}", 1, "run check: failed"),
        (
            f"run report --runs-dir {RUNS_INVALID} --sets-dir {SETS} --run {STALE}",
            2,
            "run report: refused",
        ),
        (
            f"run compare {DIRECTORIES} --first {RUN_C} --second {RUN_D}",
            0,
            "run compare: done",
        ),
        (
            f"run check {DIRECTORIES} --run 20261101T100000Z-no-such-run",
            2,
            "run check: not carried out",
        ),
    ],
    ids=["a report", "a failed check", "a refused report", "a comparison", "a run that is absent"],
)
def test_no_command_prints_the_value_of_a_setting_that_is_set(typed, arguments, exit_code, verdict):
    """Spec 1's contracts/cli.md, "Settings": a command never prints the value of a setting.
    The commands read no setting; with both set to invented values, neither value appears on
    either stream, whatever the outcome."""
    result = typed(arguments, env=INVENTED_SETTINGS)

    assert result.exit_code == exit_code, f"{result.stdout}\n{result.stderr}"
    assert result.last_line == verdict
    assert result.settings_printed == ()


# --- No command changes a file (FR-026) ---------------------------------------------------------

# Every command of this feature, on the files of `tests/data/` themselves: the command line
# typed at the repository root, and the exit code it ends with. A build of a version that is
# written reports it as already written, or is refused; neither writes.
ON_THE_EXAMPLE_DATA = [
    ("set check --data-dir tests/data/harness --sets-dir tests/data/sets --version harness", 0),
    (
        "set check --data-dir tests/data/harness --sets-dir tests/data/sets"
        " --version harness-half-rest",
        0,
    ),
    (
        "set check --data-dir tests/data/harness --sets-dir tests/data/sets"
        " --version harness-half-swapped",
        1,
    ),
    ("set check --data-dir tests/data/example --sets-dir tests/data/sets --version harness", 1),
    ("set check --data-dir tests/data/harness --sets-dir tests/data/sets --version absent", 2),
    (
        "set build --data-dir tests/data/harness --sets-dir tests/data/sets"
        " --version harness-half --role golden --take hxa=3 --take hxb=1 --seed 7",
        0,
    ),
    (
        "set build --data-dir tests/data/harness --sets-dir tests/data/sets"
        " --version harness-half --role golden --take hxa=3 --take hxb=1 --seed 8",
        2,
    ),
    (
        "set build --data-dir tests/data/harness --sets-dir tests/data/sets"
        " --version harness-half-rest --role held-out --complement-of harness-half",
        0,
    ),
    (
        "set build --data-dir tests/data/harness --sets-dir tests/data/sets"
        " --version not-written --role held-out --take hxc=3 --seed 1",
        2,
    ),
    (f"run report --runs-dir tests/data/runs --sets-dir tests/data/sets --run {RUN_A}", 0),
    (
        f"run report --runs-dir tests/data/runs --sets-dir tests/data/sets --run {RUN_B}"
        " --per-question",
        0,
    ),
    (f"run report --runs-dir tests/data/runs --sets-dir tests/data/sets --run {RUN_D}", 0),
    (
        f"run report --runs-dir tests/data/runs-invalid --sets-dir tests/data/sets --run {STALE}",
        2,
    ),
    (f"run check --runs-dir tests/data/runs --sets-dir tests/data/sets --run {RUN_B}", 0),
    ("run check --runs-dir tests/data/runs --sets-dir tests/data/sets", 0),
    (
        "run check --runs-dir tests/data/runs-invalid --sets-dir tests/data/sets"
        f" --run {WRONG_HASH}",
        1,
    ),
    ("run check --runs-dir tests/data/runs-invalid --sets-dir tests/data/sets", 1),
    ("run check --runs-dir tests/data/runs --sets-dir tests/data/sets --run absent", 2),
    (
        "run compare --runs-dir tests/data/runs --sets-dir tests/data/sets"
        f" --first {RUN_A} --second {RUN_B}",
        0,
    ),
    (
        "run compare --runs-dir tests/data/runs --sets-dir tests/data/sets"
        f" --first {RUN_A} --second {RUN_C}",
        2,
    ),
    (
        "run compare --runs-dir tests/data/runs-invalid --sets-dir tests/data/sets"
        f" --first {RUN_A} --second {WRONG_HASH}",
        2,
    ),
]


def example_files(repository_root) -> dict[str, bytes]:
    """Every file of the example data of this feature: its path -> its bytes."""
    data = repository_root / "tests" / "data"
    return {
        file.relative_to(data).as_posix(): file.read_bytes()
        for name in ("harness", "sets", "runs", "runs-invalid")
        for file in sorted((data / name).rglob("*"))
        if file.is_file()
    }


def test_the_example_data_has_the_same_bytes_after_every_command_of_this_feature(
    run_command, repository_root
):
    """tasks.md, T081, and FR-026: "the files of `tests/data/sets/`, `tests/data/runs/` and
    `tests/data/runs-invalid/` have the same bytes after every command of this feature as
    before", and no file is added: the commands that pass, fail, are refused and are not
    carried out, each ending with the exit code of its outcome."""
    before = example_files(repository_root)
    assert len(before) == 5 + 10 + 3 * (4 + 9)

    outcomes = {}
    for arguments, exit_code in ON_THE_EXAMPLE_DATA:
        result = run_command(f"python -m wixqa_rag {arguments}")
        outcomes[arguments] = (result.exit_code, exit_code)
        assert example_files(repository_root) == before, f"a file changed after: {arguments}"

    wrong = {arguments: found for arguments, found in outcomes.items() if found[0] != found[1]}
    assert not wrong, f"exit codes found and expected: {wrong}"


def test_a_report_and_a_check_change_no_file_of_the_registry(registry_copy, typed):
    """FR-026, on the temporary copy: after a report, a check of one run and of each
    registry, a refused report and a comparison, every file below the root is as it was,
    and none was added."""
    before = registry_copy.files()

    typed(f"run report {DIRECTORIES} --run {RUN_A} --per-question")
    typed(f"run check {DIRECTORIES} --run {RUN_B}")
    typed(f"run check {DIRECTORIES}")
    typed(f"run check --runs-dir {RUNS_INVALID} --sets-dir {SETS}")
    report = typed(f"run report --runs-dir {RUNS_INVALID} --sets-dir {SETS} --run {STALE}")
    typed(f"run compare {DIRECTORIES} --first {RUN_A} --second {RUN_B}")

    assert report.last_line == "run report: refused"
    assert registry_copy.files() == before


# --- The report (contracts/cli.md, "`run report`") ----------------------------------------------


def test_the_report_of_example_a_is_the_report_of_the_contract(typed):
    """contracts/cli.md, "`run report`", "Output for
    `tests/data/runs/20261101T100000Z-example-a`": every line, in its order (AC-012 to AC-016
    read parts of it)."""
    result = typed(f"run report {DIRECTORIES} --run {RUN_A}")

    assert result.exit_code == 0, result.stdout
    assert result.lines == [*REPORT_A, "run report: done"]
    assert result.settings_printed == ()


def test_the_report_with_per_question_adds_one_block_before_the_verdict(typed):
    """contracts/cli.md: "With `--per-question`, one more block stands before the verdict
    line: the line `per question: <n>` and one indented line per question, in the order of
    the set" (AC-017 reads three of the lines)."""
    result = typed(f"run report {DIRECTORIES} --run {RUN_A} --per-question")

    assert result.exit_code == 0, result.stdout
    assert result.lines == [*REPORT_A, *PER_QUESTION_A, "run report: done"]


def test_the_report_of_a_run_without_multi_article_questions_says_undefined(typed):
    """contracts/cli.md: "A breakdown without questions prints its lines with `0 questions`
    and `undefined` for every mean, share, cost per question and latency"; "Numbers in the
    output": "A number that is `null` in the record: `undefined`". spec.md, "Edge Cases":
    "reported as undefined, not as 0". The role stands in parentheses after the version
    (FR-034)."""
    result = typed(f"run report {DIRECTORIES} --run {RUN_C}")

    assert result.exit_code == 0, result.stdout
    assert result.lines == [*REPORT_C, "run report: done"]


def test_the_report_of_an_experiment_run_gives_its_own_numbers(typed):
    """data-model.md, "The numbers of the four summaries", the rows of `example-b`: the
    report is computed from the results of the run it names."""
    result = typed(f"run report {DIRECTORIES} --run {RUN_B}")

    assert result.exit_code == 0, result.stdout
    for line in (
        f"run: {RUN_B}",
        "question set: harness (golden)",
        "status, all questions: 8 questions, answered 6, no_answer 0, error 0, timeout 1,"
        " call_limit 1",
        "generation list, all questions: 7 questions, mean share_found 0.7381,"
        " all_found 4 of 7 (0.5714)",
        "retrieved list, all questions: 8 questions, mean share_found 0.8125,"
        " all_found 6 of 8 (0.7500)",
        "generation list, single-article: 4 questions, mean share_found 0.7500,"
        " all_found 3 of 4 (0.7500)",
        "retrieval misses: 3",
        "cost_usd answering, all questions: 8 questions, total 0.01400000, per question 0.00175000",
        "cost_usd answering, single-article: 4 questions, total 0.00720000,"
        " per question 0.00180000",
    ):
        assert line in result.lines, f"the report of example-b has the line `{line}`"
    start = result.lines.index("retrieval misses: 3")
    assert result.lines[start + 1 : start + 4] == ["  hxa-004", "  hxb-002", "  hxb-003"]


def test_the_report_is_computed_from_the_results_and_not_read_from_the_summary(
    registry_copy, typed
):
    """contracts/cli.md, "`run report`", step 3: "The numbers are computed from
    `results.jsonl` and the question-set record". A record whose summary states another
    number does not pass its check, so no report shows that number: it is refused
    (FR-025)."""
    registry_copy.change_summary(
        RUN_A,
        lambda document: document["breakdowns"]["all"]["retrieved_list"].update(all_found=7),
    )

    result = typed(f"run report {DIRECTORIES} --run {RUN_A}")

    assert result.exit_code == 2, result.stdout
    assert result.reasons == [f"the run check failed for {RUN_A}"]
    assert result.last_line == "run report: refused"
    assert not any(line.startswith("retrieved list") for line in result.lines)


@pytest.mark.parametrize(
    "run",
    [
        "20261101T100100Z-no-latency",
        "20261101T100200Z-missing-question",
        "20261101T100300Z-unknown-status",
        WRONG_HASH,
        STALE,
        "20261101T100600Z-two-changes",
        "20261103T100100Z-experiment-on-held-out",
    ],
)
def test_no_report_is_made_from_a_record_that_fails_its_check(typed, run):
    """FR-025 and contracts/cli.md, the table of `run report`: `reason: the run check failed
    for <ID>`, `run report: refused`, exit code 2, for each of the seven records with a
    defect (AC-029 reads one of them). No number is printed."""
    result = typed(f"run report --runs-dir {RUNS_INVALID} --sets-dir {SETS} --run {run}")

    assert result.exit_code == 2, result.stdout
    assert result.reasons == [f"the run check failed for {run}"]
    assert result.last_line == "run report: refused"
    assert not any(line.startswith(("status,", "generation list,")) for line in result.lines)


@pytest.mark.parametrize("run", ["20261101T100000Z-no-such-run", "no-such-run", "Not_A_Run"])
def test_no_report_is_made_of_a_run_that_does_not_exist(typed, run):
    """contracts/cli.md, the table of `run report`: "`ID` is not a run identifier, or the run
    does not exist": `reason: run <ID> does not exist in <runs directory>`, not carried out,
    exit code 2."""
    result = typed(f"run report {DIRECTORIES} --run {run}")

    assert result.exit_code == 2, result.stdout
    assert result.reasons == [f"run {run} does not exist in {RUNS}"]
    assert result.last_line == "run report: not carried out"


def test_the_run_is_looked_for_before_its_record_is_checked(typed):
    """contracts/cli.md, "`run report`": step 1, the run exists, comes before step 2: a run
    that does not exist is not carried out, and never refused."""
    result = typed(
        f"run report --runs-dir {RUNS_INVALID} --sets-dir data/no-such-sets --run {RUN_D}"
    )

    assert result.exit_code == 2, result.stdout
    assert result.reasons == [f"run {RUN_D} does not exist in {RUNS_INVALID}"]
    assert result.last_line == "run report: not carried out"


def test_the_default_directories_of_the_report_are_evals_runs_and_evals_golden(
    registry_copy, typed
):
    """contracts/cli.md, "Directories": the defaults of `--runs-dir` and `--sets-dir`."""
    missing = typed(f"run report --run {RUN_C}")
    assert missing.reasons == [f"run {RUN_C} does not exist in evals/runs"]

    shutil.copytree(registry_copy.runs_dir, registry_copy.root / "evals" / "runs")
    shutil.copytree(registry_copy.sets_dir, registry_copy.root / "evals" / "golden")

    found = typed(f"run report --run {RUN_C}")
    assert found.exit_code == 0, found.stdout
    assert found.lines == [*REPORT_C, "run report: done"]
