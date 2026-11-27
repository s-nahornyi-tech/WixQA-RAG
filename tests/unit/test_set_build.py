"""The command `set build` beyond the acceptance checks, and the wrong arguments of `set
build` and `set check` (task T040): `src/wixqa_rag/questionsets.py` and `src/wixqa_rag/cli.py`.

Covers:

- spec.md, FR-005 and FR-030; data-model.md, "Question set", rules 1, 2 and 5;
- contracts/cli.md, "`set build`": the six steps and their order, the report of a build, and
  the situations of the table that no acceptance check reads: a version that exists with
  another role, a part that is not a question part, a complement of a set whose rule is a
  complement, an empty complement, `--data-dir` with the sets directory `evals/golden`, an
  invalid version, a data directory that fails the dataset check, and a complemented record
  that does not exist or does not pass its check;
- the same section: "After a verdict of `refused` or `not carried out`, the sets directory
  holds exactly the files it held before", and step 6: "The record is written under a
  temporary name and then given its final name";
- contracts/cli.md, "General rules", and spec 1's contracts/cli.md, "Output", rule 7: wrong
  arguments of a named command end with a `reason:` line, the verdict `not carried out` of
  that command and exit code 2.

Every test works in a temporary repository root, the fixture `harness_copy` of
tests/conftest.py, with the data directory `data/harness` and a sets directory `data/built`
that is empty at first; the example records are in `data/sets`. No file of the checkout is
written. The commands are typed there as an operator types them; the one test that looks at
how the record reaches its place calls `questionsets.build` of contracts/harness.md
directly. All documents named here are in specs/002-evaluation-harness/ unless spec 1 is
named.
"""

import importlib
import json
import os
from pathlib import Path

import pytest

DATA_DIR = "data/harness"
BUILT = "data/built"
EXAMPLE_SETS = Path(__file__).resolve().parents[1] / "data" / "sets"

DRAW_HARNESS = "--take hxa=5 --take hxb=3 --seed 1"
DRAW_HALF = "--take hxa=3 --take hxb=1 --seed 7"


def example_bytes(version: str) -> bytes:
    return (EXAMPLE_SETS / f"{version}.json").read_bytes()


@pytest.fixture
def set_build(harness_copy, run_command):
    """Type `set build` in the temporary repository root. `arguments` is everything after
    `set build`; without `directories` the data directory and the sets directory of this
    file are added."""

    def of(arguments: str, directories: str | None = f"--data-dir {DATA_DIR} --sets-dir {BUILT}"):
        command = f"python -m wixqa_rag set build {arguments}"
        if directories:
            command += f" {directories}"
        return run_command(command, cwd=harness_copy.root)

    return of


@pytest.fixture
def built(harness_copy):
    """The files below the sets directory `data/built`: path inside it -> bytes."""

    def files() -> dict[str, bytes]:
        directory = harness_copy.root / BUILT
        if not directory.is_dir():
            return {}
        return {
            file.relative_to(directory).as_posix(): file.read_bytes()
            for file in sorted(directory.rglob("*"))
            if file.is_file()
        }

    return files


def assert_ends(result, verdict: str) -> list[str]:
    """Exit code 2, the verdict as the last line of standard output, a reason before it, and
    no value of a setting on either stream."""
    assert result.exit_code == 2, result.stdout
    assert result.last_line == f"set build: {verdict}", result.stdout
    assert "set build: done" not in result.lines
    assert result.reasons and all(result.reasons), "a `reason:` line gives the reason"
    assert result.settings_printed == ()
    return result.reasons


# --- A build that is carried out ----------------------------------------------------------------


def test_a_build_with_a_draw_prints_the_report_of_the_contract(set_build, built):
    """contracts/cli.md, "`set build`", "Output of a build with a draw": every line, and the
    record under the sets directory, with the bytes of the example record that was written
    by hand (quickstart.md, step 1)."""
    result = set_build(f"--version harness-half --role golden {DRAW_HALF}")

    assert result.exit_code == 0, result.stdout
    assert result.lines == [
        "question set: harness-half",
        "role: golden",
        "dataset: harness",
        "revision: none",
        "rule: draw sha256-order-v1",
        "seed: 7",
        "hxa: 3",
        "hxb: 1",
        "questions: 4",
        "single-article: 3",
        "multi-article: 1",
        "questions without gold articles: 0",
        f"record: {BUILT}/harness-half.json",
        "set build: done",
    ]
    assert built() == {"harness-half.json": example_bytes("harness-half")}
    assert result.settings_printed == ()


def test_a_build_with_a_complement_prints_the_rule_and_the_complemented_set(set_build, built):
    """contracts/cli.md: "A build with a complement prints `rule: complement` and, in place
    of the `seed:` line, `complement of: harness-half`"; the record has the bytes of the
    example record."""
    assert set_build(f"--version harness-half --role golden {DRAW_HALF}").exit_code == 0

    result = set_build("--version harness-half-rest --role held-out --complement-of harness-half")

    assert result.exit_code == 0, result.stdout
    assert result.lines == [
        "question set: harness-half-rest",
        "role: held-out",
        "dataset: harness",
        "revision: none",
        "rule: complement",
        "complement of: harness-half",
        "hxa: 2",
        "hxb: 2",
        "questions: 4",
        "single-article: 1",
        "multi-article: 3",
        "questions without gold articles: 0",
        f"record: {BUILT}/harness-half-rest.json",
        "set build: done",
    ]
    assert built() == {
        "harness-half.json": example_bytes("harness-half"),
        "harness-half-rest.json": example_bytes("harness-half-rest"),
    }


@pytest.mark.parametrize(
    ("version", "role", "rule"),
    [
        ("harness", "golden", DRAW_HARNESS),
        ("harness-hxc", "held-out", "--take hxc=2 --seed 1"),
    ],
)
def test_a_build_writes_the_bytes_of_the_example_record(set_build, built, version, role, rule):
    """FR-004: the record is produced by its rule; a rule that takes every question of its
    parts gives the example record that was written by hand."""
    result = set_build(f"--version {version} --role {role} {rule}")

    assert result.exit_code == 0, result.stdout
    assert built() == {f"{version}.json": example_bytes(version)}


def test_a_build_makes_the_sets_directory_when_it_does_not_exist(harness_copy, set_build):
    """data-model.md, "Question set": a set built from example data goes to `data/sets/`,
    outside version control, which a new checkout does not hold."""
    assert not (harness_copy.root / BUILT).exists()

    result = set_build(f"--version harness --role golden {DRAW_HARNESS}")

    assert result.exit_code == 0, result.stdout
    assert (harness_copy.root / BUILT / "harness.json").is_file()


def test_a_second_build_writes_nothing_and_reports_the_version_as_already_written(
    harness_copy, set_build, built
):
    """FR-005 and contracts/cli.md: "When the version is already written with the same
    bytes, the first line is `question set: harness-half (already written)` and the other
    lines are the same." The file is not written again."""
    first = set_build(f"--version harness-half --role golden {DRAW_HALF}")
    file = harness_copy.root / BUILT / "harness-half.json"
    os.utime(file, ns=(1_000_000_000, 1_000_000_000))

    second = set_build(f"--version harness-half --role golden {DRAW_HALF}")

    assert second.exit_code == 0, second.stdout
    assert second.lines == ["question set: harness-half (already written)", *first.lines[1:]]
    assert built() == {"harness-half.json": example_bytes("harness-half")}
    assert file.stat().st_mtime_ns == 1_000_000_000, "the record is written once"


def test_the_order_of_the_take_options_is_the_order_of_the_parts_in_the_record(set_build, built):
    """data-model.md, "Selection rule": `take` is "in the order given on the command line",
    and the questions stand with "the parts in the order of the rule"."""
    result = set_build("--version harness-turned --role golden --take hxb=3 --take hxa=5 --seed 1")

    assert result.exit_code == 0, result.stdout
    record = json.loads(built()["harness-turned.json"])
    assert [take["part"] for take in record["rule"]["take"]] == ["hxb", "hxa"]
    assert [part["name"] for part in record["dataset"]["parts"]] == ["hxb", "hxa"]
    assert [question["id"] for question in record["questions"]] == [
        "hxb-001",
        "hxb-002",
        "hxb-003",
        "hxa-001",
        "hxa-002",
        "hxa-003",
        "hxa-004",
        "hxa-005",
    ]
    assert result.lines.index("hxb: 3") < result.lines.index("hxa: 5")


def test_the_record_is_written_under_a_temporary_name_first(harness_copy, monkeypatch, capfd):
    """contracts/cli.md, "`set build`", step 6: "The record is written under a temporary
    name and then given its final name". The test watches the renames of the standard
    library while `questionsets.build` runs: the final name appears by a rename of another
    file that already holds the whole record, and no other file stays behind."""
    questionsets = importlib.import_module("wixqa_rag.questionsets")
    cli = importlib.import_module("wixqa_rag.cli")
    monkeypatch.chdir(harness_copy.root)
    final = (harness_copy.root / BUILT / "harness-half.json").resolve()
    renames = []

    def watched(original):
        def rename(source, target, *arguments, **keywords):
            source_file, target_file = Path(source).resolve(), Path(target).resolve()
            if target_file == final:
                renames.append((source_file, source_file.read_bytes(), final.exists()))
            return original(source, target, *arguments, **keywords)

        return rename

    monkeypatch.setattr(os, "replace", watched(os.replace))
    monkeypatch.setattr(os, "rename", watched(os.rename))

    exit_code = cli.carry_out(
        "set build",
        lambda: questionsets.build(
            "harness-half", "golden", [("hxa", 3), ("hxb", 1)], 7, None, Path(DATA_DIR), Path(BUILT)
        ),
    )

    assert exit_code == 0, capfd.readouterr().out
    assert len(renames) == 1, "the record gets its final name by one rename"
    source, content, existed_before = renames[0]
    assert source != final, "the record is first written under another name"
    assert content == example_bytes("harness-half"), "the whole record is written before the rename"
    assert not existed_before, "nothing stands under the final name before the rename"
    assert final.read_bytes() == example_bytes("harness-half")
    assert sorted(file.name for file in final.parent.iterdir()) == ["harness-half.json"], (
        "no file under a temporary name stays behind"
    )


# --- A version that exists (FR-005) --------------------------------------------------------------


def test_a_version_that_exists_with_another_role_is_refused(set_build, built):
    """contracts/cli.md: "The version exists and differs in another way (role, dataset)":
    `reason: question set <V> exists with other content`, refused, exit code 2."""
    assert set_build(f"--version harness --role golden {DRAW_HARNESS}").exit_code == 0
    before = built()

    result = set_build(f"--version harness --role held-out {DRAW_HARNESS}")

    assert assert_ends(result, "refused") == ["question set harness exists with other content"]
    assert built() == before


def test_a_version_that_exists_from_another_dataset_is_refused(harness_copy, set_build, built):
    """The same situation of the table, for the dataset: the data directory changed since
    the version was written, so the fingerprint of a part is another one."""
    assert set_build(f"--version harness --role golden {DRAW_HARNESS}").exit_code == 0
    before = built()
    harness_copy.change_rows("hxb", lambda rows: rows[0].update(answer="Another answer."))

    result = set_build(f"--version harness --role golden {DRAW_HARNESS}")

    assert assert_ends(result, "refused") == ["question set harness exists with other content"]
    assert built() == before


@pytest.mark.parametrize(
    ("rule", "reason"),
    [
        ("--take hxa=5 --take hxb=3 --seed 2", "question set harness exists with another seed"),
        ("--take hxa=5 --seed 1", "question set harness exists with another selection"),
        (
            "--take hxa=4 --take hxb=3 --seed 1",
            "question set harness exists with another selection",
        ),
        (
            "--take hxa=4 --take hxb=3 --seed 2",
            "question set harness exists with another selection",
        ),
        (
            "--take hxb=3 --take hxc=2 --seed 1",
            "question set harness exists with another selection",
        ),
        ("--complement-of harness-half", "question set harness exists with another selection"),
    ],
    ids=[
        "another seed",
        "fewer parts",
        "another number",
        "another number and another seed",
        "other parts",
        "another rule",
    ],
)
def test_a_version_that_exists_with_another_rule_is_refused_and_unchanged(
    harness_copy, set_build, built, rule, reason
):
    """contracts/cli.md, the table of `set build`: "another seed and the same parts and
    numbers" is another seed; "another rule, other parts or other numbers" is another
    selection. The record stays as it was (FR-005; User Story 1, scenario 6)."""
    assert set_build(f"--version harness --role golden {DRAW_HARNESS}").exit_code == 0
    assert set_build(f"--version harness-half --role golden {DRAW_HALF}").exit_code == 0
    before = built()

    result = set_build(f"--version harness --role golden {rule}")

    assert assert_ends(result, "refused") == [reason]
    assert built() == before


# --- A rule that cannot be applied ---------------------------------------------------------------


@pytest.mark.parametrize("part", ["hx", "no-such-part"])
def test_a_take_from_a_part_that_is_not_a_question_part_is_refused(set_build, built, part):
    """contracts/cli.md: `reason: <PART> is not a question part of <DIR>`, refused: the
    corpus part, and a part that the data directory does not have."""
    result = set_build(f"--version not-written --role golden --take {part}=2 --seed 1")

    assert assert_ends(result, "refused") == [f"{part} is not a question part of {DATA_DIR}"]
    assert built() == {}


def test_a_take_of_more_than_a_part_has_is_refused_with_both_numbers(set_build, built):
    """contracts/cli.md: `reason: the rule takes <N> questions of <PART>, which has <M>`
    (AC-045 reads the part and the numbers; this test reads the whole line)."""
    result = set_build("--version not-written --role golden --take hxa=5 --take hxb=4 --seed 1")

    assert assert_ends(result, "refused") == ["the rule takes 4 questions of hxb, which has 3"]
    assert built() == {}


def test_a_complement_of_a_set_whose_rule_is_a_complement_is_refused(set_build, built):
    """contracts/cli.md: "`--complement-of` names a set whose rule is not a draw": refused.
    data-model.md, "Selection rule": the rule of the complemented set has the kind `draw`."""
    assert set_build(f"--version harness-half --role golden {DRAW_HALF}").exit_code == 0
    rest = "--version harness-half-rest --role held-out --complement-of harness-half"
    assert set_build(rest).exit_code == 0
    before = built()

    result = set_build("--version not-written --role held-out --complement-of harness-half-rest")

    reasons = assert_ends(result, "refused")
    assert any("harness-half-rest" in reason for reason in reasons), reasons
    assert built() == before


def test_an_empty_complement_is_refused(set_build, built):
    """contracts/cli.md: "the complement is empty": refused. data-model.md, "Question set",
    rule 5: a set with no question is not produced. `harness` holds every question of its
    two parts."""
    assert set_build(f"--version harness --role golden {DRAW_HARNESS}").exit_code == 0
    before = built()

    result = set_build("--version not-written --role held-out --complement-of harness")

    reasons = assert_ends(result, "refused")
    assert any("harness" in reason for reason in reasons), reasons
    assert built() == before


def test_a_complement_of_a_set_that_does_not_exist_is_not_carried_out(set_build, built):
    """contracts/cli.md: `reason: question set <W> does not exist in <sets directory>`, not
    carried out (spec.md, "Edge Cases": the complemented set is absent)."""
    result = set_build("--version not-written --role held-out --complement-of harness-half")

    assert assert_ends(result, "not carried out") == [
        f"question set harness-half does not exist in {BUILT}"
    ]
    assert built() == {}


def test_a_complement_of_a_set_that_fails_its_check_is_not_carried_out(
    harness_copy, set_build, built
):
    """contracts/cli.md: "the `difference:` lines of its check and `reason: the check of
    question set <W> failed`", not carried out (spec.md, "Edge Cases": the complemented set
    does not pass its own check)."""
    directory = harness_copy.root / BUILT
    directory.mkdir(parents=True)
    (directory / "harness-half-swapped.json").write_bytes(example_bytes("harness-half-swapped"))
    before = built()

    result = set_build("--version not-written --role held-out --complement-of harness-half-swapped")

    assert assert_ends(result, "not carried out") == [
        "the check of question set harness-half-swapped failed"
    ]
    assert sorted(result.differences) == [
        "hxa-001 is in the question set and is not selected by the rule",
        "hxa-005 is selected by the rule and is not in the question set",
    ]
    assert built() == before


# --- `evals/golden` takes only sets of the pinned dataset ----------------------------------------


@pytest.mark.parametrize(
    "directories",
    [f"--data-dir {DATA_DIR}", f"--data-dir {DATA_DIR} --sets-dir evals/golden"],
    ids=["the default sets directory", "--sets-dir evals/golden"],
)
def test_a_data_dir_with_the_sets_directory_evals_golden_is_refused(
    harness_copy, set_build, directories
):
    """contracts/cli.md, step 2 and the table: `reason: evals/golden takes only question
    sets of the pinned dataset`, refused (research.md, section 5). Nothing is written under
    `evals/` of the temporary root."""
    result = set_build(f"--version harness --role golden {DRAW_HARNESS}", directories)

    assert assert_ends(result, "refused") == [
        "evals/golden takes only question sets of the pinned dataset"
    ]
    golden = harness_copy.root / "evals" / "golden"
    assert not golden.exists() or list(golden.iterdir()) == []


def test_the_sets_directory_is_looked_at_before_the_data_directory_is_checked(
    harness_copy, set_build
):
    """contracts/cli.md, "`set build`": step 2 comes before step 3, the dataset check."""
    result = set_build(
        f"--version harness --role golden {DRAW_HARNESS}", "--data-dir data/no-such-directory"
    )

    assert assert_ends(result, "refused") == [
        "evals/golden takes only question sets of the pinned dataset"
    ]


# --- A version of another form -------------------------------------------------------------------


@pytest.mark.parametrize("version", ["Harness", "two--hyphens", "with_underscore", "x" * 41])
def test_a_version_of_another_form_is_not_carried_out(set_build, built, version):
    """contracts/cli.md, step 1 and the table: `reason: <V> is not a valid version of a
    question set`, not carried out."""
    result = set_build(f"--version {version} --role golden {DRAW_HARNESS}")

    assert assert_ends(result, "not carried out") == [
        f"{version} is not a valid version of a question set"
    ]
    assert built() == {}


def test_a_complemented_version_of_another_form_is_not_carried_out(set_build, built):
    """contracts/cli.md, step 1: "`V` is a valid version, and so is `W`"."""
    result = set_build("--version harness-rest --role held-out --complement-of Not_A_Version")

    assert assert_ends(result, "not carried out") == [
        "Not_A_Version is not a valid version of a question set"
    ]
    assert built() == {}


def test_the_version_is_looked_at_before_the_sets_directory(set_build):
    """contracts/cli.md, "`set build`": step 1 comes before step 2."""
    result = set_build(f"--version Harness --role golden {DRAW_HARNESS}", f"--data-dir {DATA_DIR}")

    assert assert_ends(result, "not carried out") == [
        "Harness is not a valid version of a question set"
    ]


# --- A data directory that does not pass the dataset check ---------------------------------------


def test_a_data_directory_that_fails_the_dataset_check_is_not_built_from(
    harness_copy, set_build, built
):
    """contracts/cli.md: "the lines of the check, then `reason: the dataset check failed for
    <DIR>`", not carried out (spec.md, "Edge Cases")."""
    file = harness_copy.data_dir / "hxa.jsonl"
    file.write_bytes(file.read_bytes() + file.read_bytes().split(b"\n")[0] + b"\n")

    result = set_build(f"--version harness --role golden {DRAW_HARNESS}")

    assert assert_ends(result, "not carried out") == [f"the dataset check failed for {DATA_DIR}"]
    assert result.differences, "the lines of the dataset check stand before the reason"
    assert built() == {}


def test_a_data_directory_that_does_not_exist_is_not_built_from(set_build, built):
    """spec.md, "Edge Cases": "the local copy of the dataset is absent": a question set is
    not produced; the command ends as not carried out and states the reason."""
    result = set_build(
        f"--version harness --role golden {DRAW_HARNESS}",
        f"--data-dir data/no-such-directory --sets-dir {BUILT}",
    )

    assert_ends(result, "not carried out")
    assert built() == {}


def test_without_a_local_copy_of_the_pinned_dataset_nothing_is_built(harness_copy, set_build):
    """The same without `--data-dir`: the default data directory of the pinned dataset does
    not exist in the temporary root. Nothing is written under `evals/golden`."""
    result = set_build(
        "--version golden-001 --role golden"
        " --take wixqa_expertwritten=100 --take wixqa_simulated=100 --seed 20261127",
        None,
    )

    assert_ends(result, "not carried out")
    golden = harness_copy.root / "evals" / "golden"
    assert not golden.exists() or list(golden.iterdir()) == []


def test_the_dataset_check_comes_before_the_rule(harness_copy, set_build, built):
    """contracts/cli.md, "`set build`": step 3, the dataset check, comes before step 4: a
    rule that cannot be applied is not looked at for data that fails the check."""
    file = harness_copy.data_dir / "hxa.jsonl"
    file.write_bytes(file.read_bytes() + b"\n")

    result = set_build("--version harness --role golden --take hxc=3 --seed 1")

    assert assert_ends(result, "not carried out") == [f"the dataset check failed for {DATA_DIR}"]
    assert built() == {}


# --- Wrong arguments (contracts/cli.md, "General rules"; spec 1, "Output", rule 7) ---------------


def assert_wrong_arguments(result, name: str) -> None:
    """A `reason:` line, the verdict `not carried out` of the command and exit code 2."""
    assert result.exit_code == 2, result.stdout
    assert result.last_line == f"{name}: not carried out", result.stdout
    assert result.reasons and all(result.reasons), "a `reason:` line gives the reason"
    assert not any(line.endswith((": done", ": passed", ": failed")) for line in result.lines)
    assert result.settings_printed == ()


@pytest.mark.parametrize(
    "arguments",
    [
        # Both rules, and no rule.
        f"--version v --role golden {DRAW_HARNESS} --complement-of harness-half",
        "--version v --role golden --take hxa=5 --complement-of harness-half",
        "--version v --role golden --seed 1 --complement-of harness-half",
        "--version v --role golden",
        # One half of the draw without the other.
        "--version v --role golden --take hxa=5",
        "--version v --role golden --take hxa=5 --take hxb=3",
        "--version v --role golden --seed 1",
        # A `--take` that is not `PART=N` with a whole number N of 1 or more.
        "--version v --role golden --take hxa --seed 1",
        "--version v --role golden --take hxa= --seed 1",
        "--version v --role golden --take =5 --seed 1",
        "--version v --role golden --take hxa=five --seed 1",
        "--version v --role golden --take hxa=0 --seed 1",
        "--version v --role golden --take hxa=-2 --seed 1",
        "--version v --role golden --take hxa=2.5 --seed 1",
        "--version v --role golden --take hxa:5 --seed 1",
        "--version v --role golden --take hxa=5 --take hxb --seed 1",
        # A part given twice.
        "--version v --role golden --take hxa=3 --take hxa=2 --seed 1",
        "--version v --role golden --take hxa=3 --take hxb=3 --take hxa=3 --seed 1",
        # A seed that is not a whole number of 0 or more.
        "--version v --role golden --take hxa=5 --seed one",
        "--version v --role golden --take hxa=5 --seed 1.5",
        "--version v --role golden --take hxa=5 --seed=-1",
        # A role other than the two.
        f"--version v --role silver {DRAW_HARNESS}",
        f"--version v --role Golden {DRAW_HARNESS}",
        f"--version v --role held_out {DRAW_HARNESS}",
        # A required option or its value missing.
        f"--role golden {DRAW_HARNESS}",
        f"--version v {DRAW_HARNESS}",
        f"--version --role golden {DRAW_HARNESS}",
        "--version v --role golden --take hxa=5 --seed",
        "--version v --role held-out --complement-of",
        # An unknown option, and an argument too many.
        f"--version v --role golden {DRAW_HARNESS} --no-such-option",
        f"--version v --role golden {DRAW_HARNESS} unexpected-argument",
        f"--version v --role golden {DRAW_HARNESS} --json result.json",
    ],
)
def test_wrong_arguments_of_set_build_end_with_its_verdict(set_build, built, arguments):
    """contracts/cli.md, "`set build`": "Exactly one of the two rules is given ... Any other
    combination is a wrong argument, as are a `--take` that is not of the form `PART=N` with
    a whole number N of 1 or more, a part given twice, and a role other than the two"; a
    seed is "a whole number, 0 or greater". "General rules": a `reason:` line, the verdict
    `not carried out` of that command, exit code 2. Nothing is written."""
    result = set_build(arguments)

    assert_wrong_arguments(result, "set build")
    assert built() == {}


def test_wrong_arguments_of_set_build_are_found_before_anything_is_read(harness_copy, run_command):
    """Spec 1's contracts/cli.md, "Output", rule 7: wrong arguments are an outcome of their
    own. Typed where no data directory and no sets directory exist, the command still ends
    with the reason of its arguments."""
    result = run_command(
        "python -m wixqa_rag set build --version v --role golden --take hxa=5",
        cwd=harness_copy.root,
    )

    assert_wrong_arguments(result, "set build")


@pytest.mark.parametrize(
    "arguments",
    [
        "",
        "--version",
        f"--data-dir {DATA_DIR}",
        "--version harness --no-such-option",
        "--version harness unexpected-argument",
        "--version harness --data-dir",
        "--version harness --sets-dir",
        # The options of `set build` are not options of `set check`.
        "--version harness --role golden",
        "--version harness --take hxa=5 --seed 1",
        "--version harness --complement-of harness-half",
    ],
)
def test_wrong_arguments_of_set_check_end_with_its_verdict(harness_copy, run_command, arguments):
    """contracts/cli.md, "`set check`": the command takes `--version V`, which is required,
    `--data-dir DIR` and `--sets-dir DIR`. "General rules": wrong arguments give a `reason:`
    line, the verdict `not carried out` of that command and exit code 2."""
    result = run_command(f"python -m wixqa_rag set check {arguments}", cwd=harness_copy.root)

    assert_wrong_arguments(result, "set check")


@pytest.mark.parametrize("command", ["set build", "set check"])
def test_typed_where_no_dataset_json_exists_a_command_is_not_carried_out(
    tmp_path, run_command, command
):
    """contracts/cli.md, "General rules": "A command is typed at the repository root and
    reads `dataset.json` from the current directory; without it the command is not carried
    out." Nothing is written."""
    arguments = "--version harness"
    if command == "set build":
        arguments += f" --role golden {DRAW_HARNESS}"

    result = run_command(f"python -m wixqa_rag {command} {arguments}", cwd=tmp_path)

    assert_wrong_arguments(result, command)
    assert any("dataset.json" in reason for reason in result.reasons)
    assert list(tmp_path.iterdir()) == []
