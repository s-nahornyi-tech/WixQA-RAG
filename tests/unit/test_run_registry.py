"""The check of a run registry, and the output of the check of one run (task T081): the
command `run check` and `run_ids` of `src/wixqa_rag/runs.py`.

Covers:

- spec.md, FR-024, FR-030 and FR-034, and the edge case "the run registry holds no run";
- data-model.md, "Check of the registry": every directory of the runs directory is a run
  and is checked; a directory whose name is not a run identifier is a failed run; files
  directly in the runs directory are not runs; the roles are counted by the
  `config.question_set.role` of every record in which that field can be read;
- contracts/cli.md, "`run check`": both outputs, the line `baseline:` of an experiment run,
  the differences of a failed run with the run in front, and the table of the verdicts;
- contracts/harness.md, "`wixqa_rag.runs`": `run_ids(runs_dir=None)`, "the names of the
  directories of a registry, sorted".

Every test works on a temporary copy of the example registries, the fixture `registry_copy`
of tests/conftest.py, and types the command in that temporary repository root. No file of
the checkout is written. All documents named here are in specs/002-evaluation-harness/.
"""

import importlib
import shutil

import pytest

RUN_A = "20261101T100000Z-example-a"
RUN_B = "20261102T100000Z-example-b"
RUN_C = "20261103T100000Z-example-c"
RUN_D = "20261104T100000Z-example-d"

RUNS = "data/runs"
RUNS_INVALID = "data/runs-invalid"
SETS = "data/sets"

# data-model.md, "`tests/data/runs-invalid/`": the seven records with one defect each, and
# the difference that the check names, in the wording of contracts/cli.md.
DEFECTS = {
    "20261101T100100Z-no-latency": "hxa-003 lacks the field latency_seconds",
    "20261101T100200Z-missing-question": (
        "hxb-003 is a question of the question set and has no entry"
    ),
    "20261101T100300Z-unknown-status": (
        "hxa-004 has the status skipped, which is not one of the five"
    ),
    "20261101T100400Z-wrong-hash": (
        "hxa-001 has an answer_sha256 that is not the hash of its answer"
    ),
    "20261101T100500Z-stale-summary": (
        "the summary states all_found 3 for the generation list, all questions; the results give 2"
    ),
    "20261101T100600Z-two-changes": (
        f"the config differs from the baseline {RUN_A} in retrieval.top_k, "
        "which is not the parameter the experiment names"
    ),
    "20261103T100100Z-experiment-on-held-out": (
        "the run is an experiment on the held-out set harness-hxc; "
        "an experiment run is made on a golden set"
    ),
}


def load_runs():
    """Import the module; it fails while `src/wixqa_rag/runs.py` does not exist (plan.md,
    "Project Structure")."""
    return importlib.import_module("wixqa_rag.runs")


@pytest.fixture
def run_check(registry_copy, run_command):
    """Type `run check` in the temporary repository root. Without `run` the registry is
    checked; a directory given as `None` is left to its default."""

    def of(run: str | None = None, runs_dir: str | None = RUNS, sets_dir: str | None = SETS):
        command = "python -m wixqa_rag run check"
        if runs_dir is not None:
            command += f" --runs-dir {runs_dir}"
        if sets_dir is not None:
            command += f" --sets-dir {sets_dir}"
        if run is not None:
            command += f" --run {run}"
        return run_command(command, cwd=registry_copy.root)

    return of


def counts(runs: int, failed: int, golden: int, held_out: int) -> list[str]:
    """The four lines of the output for a registry (contracts/cli.md, "`run check`")."""
    return [
        f"runs: {runs}",
        f"failed runs: {failed}",
        f"runs on golden sets: {golden}",
        f"runs on held-out sets: {held_out}",
    ]


def assert_not_carried_out(result) -> list[str]:
    """Exit code 2, `run check: not carried out` last, a reason before it, and neither
    `passed` nor `failed` (FR-030)."""
    assert result.exit_code == 2, result.stdout
    assert result.last_line == "run check: not carried out"
    assert "run check: passed" not in result.lines
    assert "run check: failed" not in result.lines
    assert result.reasons and all(result.reasons), "a `reason:` line gives the reason"
    assert result.settings_printed == ()
    return result.reasons


# --- The registry ------------------------------------------------------------------------------


def test_the_check_of_a_sound_registry_prints_the_four_counts_and_passes(run_check):
    """contracts/cli.md, "`run check`", "Output for the registry": every line (AC-019)."""
    result = run_check()

    assert result.exit_code == 0, result.stdout
    assert result.lines == [*counts(4, 0, 2, 2), "run check: passed"]
    assert result.settings_printed == ()


def test_the_check_of_the_invalid_registry_counts_the_roles_as_the_records_state_them(run_check):
    """tasks.md, T081, and data-model.md: the check of `runs-invalid` reports `runs: 9`,
    `failed runs: 7`, `runs on golden sets: 7` and `runs on held-out sets: 2`; it fails with
    exit code 1 (AC-027)."""
    result = run_check(runs_dir=RUNS_INVALID)

    assert result.exit_code == 1, result.stdout
    assert result.lines[:4] == counts(9, 7, 7, 2)
    assert result.last_line == "run check: failed"


def test_the_differences_of_a_failed_run_are_printed_with_the_run_in_front(run_check):
    """contracts/cli.md: "When runs failed, each of their differences is printed before the
    verdict with the run in front: `difference: <run id>: <the line for one run, without its
    "difference: ">`", after the four lines."""
    result = run_check(runs_dir=RUNS_INVALID)

    for run, text in DEFECTS.items():
        assert f"{run}: {text}" in result.differences, f"not printed for {run}"
    for text in result.differences:
        assert any(text.startswith(f"{run}: ") for run in DEFECTS), (
            f"a difference without a failed run in front: {text}"
        )
    assert not any(text.startswith((f"{RUN_A}: ", f"{RUN_C}: ")) for text in result.differences), (
        "a run that passes has no difference"
    )
    between = result.lines[4:-1]
    assert between and all(line.startswith("difference: ") for line in between), (
        "the four lines, then every difference, then the verdict"
    )


def test_every_failed_run_of_the_registry_has_a_difference(run_check):
    """FR-024: the check of the registry checks every run in it. Each of the seven failed
    runs has at least one line."""
    result = run_check(runs_dir=RUNS_INVALID)

    for run in DEFECTS:
        assert any(text.startswith(f"{run}: ") for text in result.differences), run


@pytest.mark.parametrize("name", ["not-a-run", "example-a", "20261101-example", "Runs"])
def test_a_directory_whose_name_is_not_a_run_identifier_is_a_failed_run(
    registry_copy, run_check, name
):
    """data-model.md, "Check of the registry": "A directory whose name is not a run
    identifier is a failed run", here a copy of a sound record under such a name. The record
    inside states the role `golden`, which can be read."""
    shutil.copytree(registry_copy.runs_dir / RUN_A, registry_copy.runs_dir / name)

    result = run_check()

    assert result.exit_code == 1, result.stdout
    assert result.lines[:2] == ["runs: 5", "failed runs: 1"]
    assert any(text.startswith(f"{name}: ") for text in result.differences), result.differences
    assert result.last_line == "run check: failed"


def test_an_empty_directory_in_the_registry_is_a_failed_run(registry_copy, run_check):
    """ "Every directory of the runs directory is a run and is checked": a directory with the
    name of a run and no file has none of the three files. Its role cannot be read, so it is
    counted under neither role."""
    (registry_copy.runs_dir / "20261105T100000Z-nothing-inside").mkdir()

    result = run_check()

    assert result.exit_code == 1, result.stdout
    assert result.lines[:4] == counts(5, 1, 2, 2)
    assert any(
        text.startswith("20261105T100000Z-nothing-inside: ") for text in result.differences
    ), result.differences


def test_a_run_whose_role_cannot_be_read_is_counted_under_neither_role(registry_copy, run_check):
    """data-model.md: the roles are "counted by the `config.question_set.role` of every
    record in which that field can be read". `run.json` of `example-d` is not JSON."""
    registry_copy.file(RUN_D, "run.json").write_text("not JSON\n", encoding="utf-8")

    result = run_check()

    assert result.exit_code == 1, result.stdout
    assert result.lines[:4] == counts(4, 1, 2, 1)


def test_a_failed_run_is_still_counted_under_the_role_that_its_record_states(
    registry_copy, run_check
):
    """The same rule from the other side: a run that fails for another reason states its
    role, and is counted. `example-c` gets a hash that is not the hash of its answer."""
    registry_copy.change_entries(RUN_C, lambda rows: rows[0].update(answer_sha256="0" * 64))

    result = run_check()

    assert result.exit_code == 1, result.stdout
    assert result.lines[:4] == counts(4, 1, 2, 2)
    assert result.differences == [
        f"{RUN_C}: hxc-001 has an answer_sha256 that is not the hash of its answer"
    ]


@pytest.mark.parametrize("name", [".gitkeep", "README.md", "20261105T100000Z-a-file"])
def test_a_file_in_the_runs_directory_is_not_a_run(registry_copy, run_check, name):
    """data-model.md: "Files directly in the runs directory, such as `.gitkeep`, are not
    runs", also a file with the name of a run."""
    (registry_copy.runs_dir / name).write_text("not a run\n", encoding="utf-8")

    result = run_check()

    assert result.exit_code == 0, result.stdout
    assert result.lines == [*counts(4, 0, 2, 2), "run check: passed"]


def test_a_registry_without_runs_passes_with_zero_runs(registry_copy, run_check):
    """spec.md, "Edge Cases": "What happens when the run registry holds no run? The check of
    the registry passes and reports zero runs." contracts/cli.md: "also a registry without
    runs (`runs: 0`)"."""
    empty = registry_copy.root / "data" / "no-runs-yet"
    empty.mkdir()
    (empty / ".gitkeep").write_bytes(b"")

    result = run_check(runs_dir="data/no-runs-yet")

    assert result.exit_code == 0, result.stdout
    assert result.lines == [*counts(0, 0, 0, 0), "run check: passed"]


def test_the_default_registry_is_evals_runs_with_the_sets_of_evals_golden(registry_copy, run_check):
    """contracts/cli.md, "Directories": the defaults of `--runs-dir` and `--sets-dir` are
    `evals/runs` and `evals/golden`, below the directory where the command is typed (AC-020
    reads the registry of the study in this way)."""
    shutil.copytree(registry_copy.runs_dir, registry_copy.root / "evals" / "runs")
    shutil.copytree(registry_copy.sets_dir, registry_copy.root / "evals" / "golden")

    result = run_check(runs_dir=None, sets_dir=None)

    assert result.exit_code == 0, result.stdout
    assert result.lines == [*counts(4, 0, 2, 2), "run check: passed"]


def test_a_runs_directory_that_does_not_exist_is_not_carried_out(run_check):
    """contracts/cli.md, the table of `run check`: "The runs directory does not exist":
    `reason: …`, `run check: not carried out`, exit code 2. It is not reported as a registry
    without runs."""
    result = run_check(runs_dir="data/no-such-directory")

    reasons = assert_not_carried_out(result)
    assert not any(line.startswith("runs:") for line in result.lines)
    assert any("data/no-such-directory" in reason for reason in reasons), reasons


def test_without_the_default_registry_the_check_is_not_carried_out(run_check):
    """The same for the default: the temporary root has no `evals/runs`."""
    assert_not_carried_out(run_check(runs_dir=None))


def test_the_check_of_a_registry_changes_no_file(registry_copy, run_check):
    """FR-026: no command of this feature changes a run record or a question-set record."""
    before = registry_copy.files()

    sound = run_check()
    invalid = run_check(runs_dir=RUNS_INVALID)

    assert (sound.last_line, invalid.last_line) == ("run check: passed", "run check: failed")
    assert registry_copy.files() == before


# --- `run_ids` ---------------------------------------------------------------------------------


def test_run_ids_gives_the_names_of_the_directories_sorted(registry_copy):
    """contracts/harness.md, `run_ids(runs_dir=None)`: "The names of the directories of a
    registry, sorted". A file is not a directory; a directory whose name is not a run
    identifier is one, and the check counts it as a failed run."""
    (registry_copy.runs_dir / ".gitkeep").write_bytes(b"")
    (registry_copy.runs_dir / "not-a-run").mkdir()

    found = load_runs().run_ids(registry_copy.runs_dir)

    assert list(found) == [RUN_A, RUN_B, RUN_C, RUN_D, "not-a-run"]


def test_run_ids_of_the_invalid_registry_are_its_nine_runs(registry_copy):
    """data-model.md: `tests/data/runs-invalid/` is a registry of nine records."""
    found = list(load_runs().run_ids(registry_copy.runs_invalid_dir))

    assert found == sorted([RUN_A, RUN_C, *DEFECTS])
    assert len(found) == 9


def test_run_ids_without_a_directory_reads_evals_runs(registry_copy, monkeypatch):
    """contracts/harness.md: `runs_dir=None` is the default runs directory, `evals/runs`,
    below the current directory."""
    shutil.copytree(registry_copy.runs_dir / RUN_C, registry_copy.root / "evals" / "runs" / RUN_C)
    monkeypatch.chdir(registry_copy.root)

    assert list(load_runs().run_ids()) == [RUN_C]


# --- One run -----------------------------------------------------------------------------------


def test_the_check_of_one_run_prints_the_run_its_question_set_and_its_questions(run_check):
    """contracts/cli.md, "`run check`", "Output for one run": every line (AC-018)."""
    result = run_check(RUN_A)

    assert result.exit_code == 0, result.stdout
    assert result.lines == [
        f"run: {RUN_A}",
        "question set: harness (golden)",
        "questions: 8",
        "run check: passed",
    ]


def test_the_check_of_a_run_on_a_held_out_set_states_the_role(run_check):
    """FR-034: the check of a run states the question set and its role (AC-042)."""
    result = run_check(RUN_D)

    assert result.exit_code == 0, result.stdout
    assert result.lines == [
        f"run: {RUN_D}",
        "question set: harness-hxc (held-out)",
        "questions: 2",
        "run check: passed",
    ]


def test_the_check_of_an_experiment_run_prints_its_baseline(run_check):
    """contracts/cli.md: "For an experiment run the line `baseline: <run id>` follows
    `questions:`"."""
    result = run_check(RUN_B)

    assert result.exit_code == 0, result.stdout
    assert result.lines == [
        f"run: {RUN_B}",
        "question set: harness (golden)",
        "questions: 8",
        f"baseline: {RUN_A}",
        "run check: passed",
    ]


@pytest.mark.parametrize("run", DEFECTS)
def test_the_check_of_a_failed_run_prints_its_lines_and_then_its_differences(run_check, run):
    """contracts/cli.md, the table of `run check`: "the lines above that can be printed, then
    every difference", `run check: failed`, exit code 1; the difference stands without the
    run in front when one run is checked."""
    result = run_check(run, runs_dir=RUNS_INVALID)

    assert result.exit_code == 1, result.stdout
    assert result.lines[0] == f"run: {run}"
    assert result.lines[1].startswith("question set: harness")
    assert DEFECTS[run] in result.differences
    first = result.lines.index(f"difference: {result.differences[0]}")
    assert all(line.startswith("difference: ") for line in result.lines[first:-1])
    assert result.last_line == "run check: failed"


def test_the_lines_of_the_question_set_are_left_out_when_run_json_cannot_be_read(
    registry_copy, run_check
):
    """contracts/cli.md: "The lines `question set:` and `questions:` are printed when
    `run.json` and the record of the set can be read; they are left out otherwise." Here
    `run.json` is not JSON."""
    registry_copy.file(RUN_A, "run.json").write_text("not JSON\n", encoding="utf-8")

    result = run_check(RUN_A)

    assert result.exit_code == 1, result.stdout
    assert not any(line.startswith(("question set:", "questions:")) for line in result.lines)
    assert result.differences
    assert result.last_line == "run check: failed"


def test_the_lines_of_the_question_set_are_left_out_when_the_set_cannot_be_read(
    registry_copy, run_check
):
    """The same when the record of the set is not in the sets directory; the difference is
    that of contracts/cli.md."""
    (registry_copy.sets_dir / "harness.json").unlink()

    result = run_check(RUN_A)

    assert result.exit_code == 1, result.stdout
    assert not any(line.startswith(("question set:", "questions:")) for line in result.lines)
    assert f"question set harness does not exist in {SETS}" in result.differences


@pytest.mark.parametrize(
    "run", ["20261101T100000Z-no-such-run", "no-such-run", "Not_A_Run", "example-a"]
)
def test_a_run_that_does_not_exist_is_not_checked(run_check, run):
    """contracts/cli.md, the table of `run check`: "`ID` is not a run identifier, or the run
    does not exist": `reason: run <ID> does not exist in <runs directory>`, not carried out,
    exit code 2 (AC-028)."""
    result = run_check(run)

    assert assert_not_carried_out(result) == [f"run {run} does not exist in {RUNS}"]


def test_a_directory_that_is_no_run_identifier_cannot_be_checked_by_name(registry_copy, run_check):
    """The same when a directory of that name exists: `--run` takes a run identifier."""
    shutil.copytree(registry_copy.runs_dir / RUN_A, registry_copy.runs_dir / "not-a-run")

    result = run_check("not-a-run")

    assert assert_not_carried_out(result) == [f"run not-a-run does not exist in {RUNS}"]


def test_a_sets_directory_that_does_not_exist_is_a_difference_of_the_run(run_check):
    """data-model.md, difference 4: the question set named in the config is not in the sets
    directory. The run exists and is checked; its set cannot be found."""
    result = run_check(RUN_A, sets_dir="data/no-such-sets")

    assert result.exit_code in (1, 2), result.stdout
    assert result.last_line in ("run check: failed", "run check: not carried out")
    assert "run check: passed" not in result.lines
