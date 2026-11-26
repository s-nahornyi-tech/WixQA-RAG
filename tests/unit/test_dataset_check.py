"""The dataset check (tasks T024): `python -m wixqa_rag dataset check [--data-dir DIR]`.

Covers:

- data-model.md, "Data directory": one test for each of the differences 1 to 8, each made on
  a temporary copy of `tests/data/example/`; a directory without `manifest.json` is not a
  local copy; an empty `contents` and an empty `article_ids` list are not differences;
- data-model.md, "Pinned revision" and "Part": a `dataset.json` or a manifest that breaks a
  rule is not used, and a row is a non-empty line;
- contracts/cli.md, "`dataset check`" and "Output": the lines of a passed check, a
  `difference:` line for every difference before the verdict `failed`, a `reason:` line
  before the verdict `not carried out`, and the exit codes 0, 1 and 2;
- spec.md, FR-004, FR-005 and User Story 1, scenario 3.

Every test types the command line itself. A `difference:` line is read as far as
contracts/cli.md fixes it: it names what the table of "`dataset check`" writes in angle
brackets (the part, the path, the row, the field, the id, the numbers), in any wording.

Except for the tests of difference 8, a temporary copy differs from `example` in one way
only: after a part file was changed on purpose, the manifest of the copy is written again
from its files, as the manifests under `tests/data/` are. The check then finds one difference.

All documents named here are in specs/001-corpus-and-audit/.
"""

import hashlib
import json
import re
import shlex
import shutil
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[1] / "data" / "example"

# Neither setting is needed by the dataset commands (quickstart.md, "The published dataset").
NO_SETTINGS = {"DATABASE_URL": None, "OPENAI_API_KEY": None}

ARTICLE_FIELDS = ("id", "url", "contents", "article_type")
QUESTION_FIELDS = ("question", "answer", "article_ids")


# --- Making a copy and changing it -----------------------------------------------------------


@pytest.fixture
def copy(tmp_path: Path) -> Path:
    """A temporary copy of `tests/data/example/`."""
    directory = tmp_path / "example-copy"
    shutil.copytree(EXAMPLE, directory)
    return directory


def read_rows(directory: Path, file: str) -> list[dict]:
    text = (directory / file).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.split("\n") if line.strip()]


def write_lines(directory: Path, file: str, lines: list[str]) -> None:
    """Write a part file from its lines and write the manifest again from the files."""
    (directory / file).write_bytes("".join(line + "\n" for line in lines).encode("utf-8"))
    refresh_manifest(directory)


def write_rows(directory: Path, file: str, rows: list[dict]) -> None:
    write_lines(directory, file, [json.dumps(row, ensure_ascii=False) for row in rows])


def read_manifest(directory: Path) -> dict:
    return json.loads((directory / "manifest.json").read_text(encoding="utf-8"))


def write_manifest(directory: Path, manifest: object) -> None:
    text = json.dumps(manifest, indent=2) + "\n"
    (directory / "manifest.json").write_text(text, encoding="utf-8")


def refresh_manifest(directory: Path) -> None:
    """Record again, for every part whose file exists, its rows, its size and its SHA-256."""
    manifest = read_manifest(directory)
    for part in manifest["parts"]:
        file = directory / part["path"]
        if file.is_file():
            data = file.read_bytes()
            part["rows"] = sum(1 for line in data.split(b"\n") if line.strip())
            part["bytes"] = len(data)
            part["sha256"] = hashlib.sha256(data).hexdigest()
    write_manifest(directory, manifest)


def manifest_part(manifest: dict, name: str) -> dict:
    return next(part for part in manifest["parts"] if part["name"] == name)


def files_of(directory: Path) -> dict[str, bytes]:
    return {
        file.relative_to(directory).as_posix(): file.read_bytes()
        for file in sorted(directory.rglob("*"))
        if file.is_file()
    }


# --- Typing the command and reading its output -----------------------------------------------


def check(run_command, directory: Path | None = None, *, cwd: Path | None = None):
    """Type `dataset check`, with `--data-dir` when a directory is given."""
    command = "python -m wixqa_rag dataset check"
    if directory is not None:
        command += f" --data-dir {shlex.quote(str(directory))}"
    return run_command(command, env=NO_SETTINGS, cwd=cwd)


def names(line: str, word: str) -> bool:
    """Whether a line names a part, a field, a file or an id as a word of its own.

    `ex` is not named by `exq`, `ex.jsonl` or `ex-002`.
    """
    return re.search(rf"(?<![\w.-]){re.escape(word)}(?![\w-]|\.\w)", line) is not None


def has_number(line: str, number: int) -> bool:
    return re.search(rf"(?<!\d){number}(?!\d)", line) is not None


def assert_passed(result) -> None:
    assert result.exit_code == 0, (
        'contracts/cli.md, "`dataset check`": no difference ends with exit code 0; got '
        f"{result.exit_code}.\nStandard output:\n{result.stdout}\nStandard error:\n{result.stderr}"
    )
    assert result.last_line == "dataset check: passed"
    assert not [line for line in result.lines if line.startswith(("difference:", "reason:"))]


def differences_of_a_failed_check(result) -> list[str]:
    """Exit code 1, the verdict `failed` last, and the `difference:` lines before it."""
    assert result.exit_code == 1, (
        'contracts/cli.md, "`dataset check`": a difference ends with exit code 1; got '
        f"{result.exit_code}.\nStandard output:\n{result.stdout}\nStandard error:\n{result.stderr}"
    )
    assert result.last_line == "dataset check: failed", (
        'contracts/cli.md, "Output", rule 3: the verdict line is the last line of standard output'
    )
    differences = [line for line in result.lines[:-1] if line.startswith("difference: ")]
    assert differences, (
        'contracts/cli.md, "Output", rule 4: before a verdict of `failed`, every difference is '
        "printed on a line that starts with `difference:`"
    )
    return differences


def the_one_difference(result) -> str:
    """The `difference:` line of a check that found exactly one difference."""
    differences = differences_of_a_failed_check(result)
    assert len(differences) == 1, (
        "the copy differs in one way, so one difference is printed; got:\n" + "\n".join(differences)
    )
    return differences[0]


def assert_not_carried_out(result) -> None:
    assert result.exit_code == 2, (
        'contracts/cli.md, "`dataset check`": a check that is not carried out ends with exit '
        f"code 2; got {result.exit_code}.\nStandard output:\n{result.stdout}\n"
        f"Standard error:\n{result.stderr}"
    )
    assert result.last_line == "dataset check: not carried out"
    assert [line for line in result.lines[:-1] if line.startswith("reason: ")], (
        'contracts/cli.md, "Output", rule 5: the reason is printed on a line that starts with '
        "`reason:`"
    )
    assert not [line for line in result.lines if line.startswith("difference:")], (
        "a check that is not carried out reports no difference: it is neither passed nor failed"
    )


# --- A check that passes (contracts/cli.md, "`dataset check`") --------------------------------


def test_the_example_dataset_passes_with_the_lines_of_the_contract(run_command):
    """contracts/cli.md, "`dataset check`": the output when the check passes, for
    `tests/data/example`: the dataset, `revision: none` for a dataset that is not published,
    one line per part with the number of rows found, and the verdict."""
    result = run_command(
        "python -m wixqa_rag dataset check --data-dir tests/data/example", env=NO_SETTINGS
    )

    assert_passed(result)
    assert result.lines == [
        "dataset: example",
        "revision: none",
        "ex: 5",
        "exq: 3",
        "dataset check: passed",
    ]


def test_a_copy_of_the_example_passes(run_command, copy):
    """The counterpart of every test below: the unchanged copy has no difference."""
    assert_passed(check(run_command, copy))


@pytest.mark.parametrize(
    "directory",
    ["example-one-more-article", "example-one-less-article", "example-unknown-reference"],
)
def test_the_altered_examples_pass_the_dataset_check(run_command, directory):
    """data-model.md, "Example datasets": only `example-damaged` fails the dataset check. The
    three other altered directories differ from `example` in a way that the audit finds, and
    the dataset check does not compare question references with the corpus."""
    result = run_command(
        f"python -m wixqa_rag dataset check --data-dir tests/data/{directory}", env=NO_SETTINGS
    )

    assert_passed(result)


def test_the_check_changes_no_file(run_command, copy):
    """FR-005: no command changes a question, an answer or an article; the check only reads."""
    before = files_of(copy)

    assert_passed(check(run_command, copy))
    (copy / "exq.jsonl").unlink()
    differences_of_a_failed_check(check(run_command, copy))

    after = files_of(copy)
    assert after == {name: data for name, data in before.items() if name != "exq.jsonl"}


# --- A row is a non-empty line (data-model.md, "Part") ----------------------------------------


def test_a_last_row_without_a_line_feed_is_a_row(run_command, copy):
    """data-model.md, "Part": a row is a non-empty line. A file that does not end with a line
    feed has as many rows as it has non-empty lines."""
    file = copy / "ex.jsonl"
    file.write_bytes(file.read_bytes().removesuffix(b"\n"))
    refresh_manifest(copy)
    assert manifest_part(read_manifest(copy), "ex")["rows"] == 5

    result = check(run_command, copy)

    assert_passed(result)
    assert "ex: 5" in result.lines


def test_an_empty_line_is_not_a_row(run_command, copy):
    """data-model.md, "Part": a row is a non-empty line, so an empty line is neither counted
    nor reported as a row that is not a JSON object."""
    lines = (copy / "exq.jsonl").read_text(encoding="utf-8").splitlines()
    write_lines(copy, "exq.jsonl", [lines[0], "", lines[1], lines[2], ""])
    assert manifest_part(read_manifest(copy), "exq")["rows"] == 3

    result = check(run_command, copy)

    assert_passed(result)
    assert "exq: 3" in result.lines


# --- Difference 1: the file of a part is missing ----------------------------------------------


@pytest.mark.parametrize(("part", "file"), [("ex", "ex.jsonl"), ("exq", "exq.jsonl")])
def test_difference_1_the_file_of_a_part_is_missing(run_command, copy, part, file):
    """data-model.md, "Data directory", difference 1; contracts/cli.md:
    `difference: <part> is missing (<path>)`."""
    (copy / file).unlink()

    line = the_one_difference(check(run_command, copy))

    assert names(line, part), f"the line names the part {part}: {line}"
    assert file in line, f"the line names the path {file}: {line}"


# --- Difference 2: the row count of a part differs --------------------------------------------


@pytest.mark.parametrize(("part", "found", "recorded"), [("ex", 5, 6), ("exq", 3, 2)])
def test_difference_2_the_row_count_differs_from_the_manifest(
    run_command, copy, part, found, recorded
):
    """data-model.md, "Data directory", difference 2; contracts/cli.md:
    `difference: <part> has <n> rows, the manifest records <m>`. The files are unchanged and
    the manifest records another number, so the fingerprints still match."""
    manifest = read_manifest(copy)
    manifest_part(manifest, part)["rows"] = recorded
    write_manifest(copy, manifest)

    line = the_one_difference(check(run_command, copy))

    assert names(line, part), f"the line names the part {part}: {line}"
    assert has_number(line, found), f"the line gives the {found} rows found: {line}"
    assert has_number(line, recorded), f"the line gives the {recorded} rows recorded: {line}"


# --- Difference 3: the SHA-256 of a part differs ----------------------------------------------


@pytest.mark.parametrize(
    ("part", "file", "old", "new"),
    [("ex", "ex.jsonl", b"30 minutes", b"45 minutes"), ("exq", "exq.jsonl", b"UTC", b"utc")],
)
def test_difference_3_a_file_has_changed_since_its_fingerprint_was_recorded(
    run_command, copy, part, file, old, new
):
    """data-model.md, "Data directory", difference 3; contracts/cli.md:
    `difference: <part> has changed since its fingerprint was recorded`. The changed file has
    the same number of rows and the same size, so only its fingerprint tells (User Story 1,
    scenario 3: "a file has changed since it was fetched")."""
    data = (copy / file).read_bytes()
    assert old in data and len(old) == len(new)
    (copy / file).write_bytes(data.replace(old, new))

    line = the_one_difference(check(run_command, copy))

    assert names(line, part), f"the line names the part {part}: {line}"


# --- Difference 4: a row is not a JSON object -------------------------------------------------


@pytest.mark.parametrize(
    ("part", "file", "row", "text"),
    [
        ("ex", "ex.jsonl", 3, '["ex-003", "a list, not an object"]'),
        ("ex", "ex.jsonl", 5, '{"id": "ex-005", "url": '),
        ("exq", "exq.jsonl", 2, '"a text, not an object"'),
        ("exq", "exq.jsonl", 1, "not JSON at all"),
    ],
    ids=["a list in ex", "cut-off JSON in ex", "a text in exq", "no JSON in exq"],
)
def test_difference_4_a_row_is_not_a_json_object(run_command, copy, part, file, row, text):
    """data-model.md, "Data directory", difference 4; contracts/cli.md:
    `difference: <part> row <n> is not a JSON object`. Rows are counted from 1."""
    lines = (copy / file).read_text(encoding="utf-8").splitlines()
    lines[row - 1] = text
    write_lines(copy, file, lines)

    line = the_one_difference(check(run_command, copy))

    assert names(line, part), f"the line names the part {part}: {line}"
    assert has_number(line, row), f"the line names row {row}: {line}"


# --- Difference 5: a required field is absent -------------------------------------------------

ABSENT_FIELDS = [("ex", "ex.jsonl", field) for field in ARTICLE_FIELDS] + [
    ("exq", "exq.jsonl", field) for field in QUESTION_FIELDS
]


@pytest.mark.parametrize(("part", "file", "field"), ABSENT_FIELDS)
@pytest.mark.parametrize("absent_as", ["no such key", "null"])
def test_difference_5_a_required_field_is_absent(run_command, copy, part, file, field, absent_as):
    """data-model.md, "Data directory", difference 5; contracts/cli.md:
    `difference: <part> row <n> lacks the field <field>`. FR-004: the required fields are
    those listed under "Data" in PROJECT.md. A field is absent when the row has no such key
    or the value is null."""
    rows = read_rows(copy, file)
    row = 2
    if absent_as == "null":
        rows[row - 1][field] = None
    else:
        del rows[row - 1][field]
    write_rows(copy, file, rows)

    line = the_one_difference(check(run_command, copy))

    assert names(line, part), f"the line names the part {part}: {line}"
    assert has_number(line, row), f"the line names row {row}: {line}"
    assert names(line, field), f"the line names the field {field}: {line}"


# --- Difference 6: a field has the wrong type -------------------------------------------------


@pytest.mark.parametrize(
    ("part", "file", "row", "field", "value"),
    [
        ("ex", "ex.jsonl", 3, "id", 3),
        ("ex", "ex.jsonl", 4, "id", ["ex-004"]),
        ("exq", "exq.jsonl", 1, "article_ids", "ex-001"),
        ("exq", "exq.jsonl", 2, "article_ids", ["ex-002", 3]),
        ("exq", "exq.jsonl", 3, "article_ids", {"ex-004": True}),
    ],
    ids=[
        "id is a number",
        "id is a list",
        "article_ids is a text",
        "article_ids holds a number",
        "article_ids is an object",
    ],
)
def test_difference_6_an_id_or_article_ids_has_the_wrong_type(
    run_command, copy, part, file, row, field, value
):
    """data-model.md, "Data directory", difference 6: an `id` is not a string, or
    `article_ids` is not a list of strings; contracts/cli.md:
    `difference: <part> row <n> has the field <field> with a wrong type`."""
    rows = read_rows(copy, file)
    rows[row - 1][field] = value
    write_rows(copy, file, rows)

    line = the_one_difference(check(run_command, copy))

    assert names(line, part), f"the line names the part {part}: {line}"
    assert has_number(line, row), f"the line names row {row}: {line}"
    assert names(line, field), f"the line names the field {field}: {line}"


# --- Difference 7: an article id occurs more than once ----------------------------------------


@pytest.mark.parametrize(("repeated", "times"), [("ex-002", 2), ("ex-004", 3)])
def test_difference_7_an_article_id_occurs_more_than_once(run_command, copy, repeated, times):
    """data-model.md, "Data directory", difference 7; contracts/cli.md:
    `difference: article id <id> occurs <n> times in <part>`. One line for an id, however
    often it occurs."""
    rows = read_rows(copy, "ex.jsonl")
    again = next(row for row in rows if row["id"] == repeated)
    write_rows(copy, "ex.jsonl", rows + [again] * (times - 1))

    line = the_one_difference(check(run_command, copy))

    assert names(line, repeated), f"the line names the article id {repeated}: {line}"
    assert has_number(line, times), f"the line gives the {times} occurrences: {line}"
    assert names(line, "ex"), f"the line names the part ex: {line}"


def test_two_questions_that_name_the_same_article_are_no_difference(run_command, copy):
    """data-model.md, "Data directory", difference 7, is about the `id` of an article in the
    corpus part. Two questions may name the same article."""
    rows = read_rows(copy, "exq.jsonl")
    rows[2]["article_ids"] = ["ex-001", "ex-004"]
    write_rows(copy, "exq.jsonl", rows)

    assert_passed(check(run_command, copy))


# --- Every difference is printed --------------------------------------------------------------


def test_every_difference_found_is_printed_on_its_own_line(run_command, copy):
    """contracts/cli.md, "`dataset check`": "Every difference found is printed, each on its
    own line." The copy has a repeated article id, a row without `url` and a missing file."""
    rows = read_rows(copy, "ex.jsonl")
    del rows[3]["url"]
    write_rows(copy, "ex.jsonl", [*rows, rows[0]])
    (copy / "exq.jsonl").unlink()

    differences = differences_of_a_failed_check(check(run_command, copy))

    assert len(differences) == 3, "three differences, three lines; got:\n" + "\n".join(differences)
    assert any(names(line, "ex-001") for line in differences)
    assert any(names(line, "url") and has_number(line, 4) for line in differences)
    assert any(names(line, "exq") and "exq.jsonl" in line for line in differences)


# --- What is not a difference (data-model.md, "Data directory") -------------------------------


def test_an_empty_contents_is_not_a_difference(run_command, copy):
    """data-model.md, "Data directory": an empty `contents` is not a difference; the build
    reports the article (`Article.contents`)."""
    rows = read_rows(copy, "ex.jsonl")
    rows[4]["contents"] = ""
    write_rows(copy, "ex.jsonl", rows)

    assert_passed(check(run_command, copy))


def test_an_empty_article_ids_list_is_not_a_difference(run_command, copy):
    """data-model.md, "Data directory": an empty `article_ids` list is not a difference; the
    audit counts the question (`Question.article_ids`)."""
    rows = read_rows(copy, "exq.jsonl")
    rows[0]["article_ids"] = []
    write_rows(copy, "exq.jsonl", rows)

    assert_passed(check(run_command, copy))


# --- Difference 8: default directory only, the manifest differs from dataset.json -------------


def test_the_default_data_directory_is_checked_without_data_dir(run_command, pinned_example):
    """contracts/cli.md, "`dataset check`": without `--data-dir` the command checks the default
    data directory, `data/wixqa/<revision>/`, with the revision of `dataset.json` in the
    current directory. The parts are those of the manifest, whatever their names and folders
    (research.md, section 11). The counterpart of the tests of difference 8."""
    pinned_example.store_copy()

    result = check(run_command, cwd=pinned_example.root)

    assert_passed(result)
    assert result.lines == [
        "dataset: Wix/WixQA",
        f"revision: {pinned_example.revision}",
        "ex: 5",
        "exq: 3",
        "exq_more: 3",
        "dataset check: passed",
    ]


def the_one_difference_from_dataset_json(result) -> str:
    line = the_one_difference(result)
    assert "dataset.json" in line, (
        'contracts/cli.md, "`dataset check`": `difference: the manifest differs from '
        f"dataset.json: <what>`; got: {line}"
    )
    return line


def test_difference_8_the_dataset_name_differs_from_dataset_json(run_command, pinned_example):
    """data-model.md, "Data directory", difference 8: the dataset name of the manifest differs
    from `dataset.json`."""
    pinned_example.store_copy()
    manifest = json.loads(pinned_example.manifest_file.read_text(encoding="utf-8"))
    manifest["name"] = "Wix/Another-Dataset"
    pinned_example.write_manifest(manifest)

    the_one_difference_from_dataset_json(check(run_command, cwd=pinned_example.root))


def test_difference_8_the_revision_differs_from_dataset_json(run_command, pinned_example):
    """data-model.md, "Data directory", difference 8: the revision of the manifest differs
    from `dataset.json`. The files lie in the folder of the pinned revision, and their
    manifest says that they were fetched at another one."""
    pinned_example.store_copy()
    manifest = json.loads(pinned_example.manifest_file.read_text(encoding="utf-8"))
    manifest["revision"] = "f" * 40
    pinned_example.write_manifest(manifest)

    the_one_difference_from_dataset_json(check(run_command, cwd=pinned_example.root))


def test_difference_8_a_part_differs_from_dataset_json(run_command, pinned_example):
    """data-model.md, "Data directory", difference 8: a part of the manifest differs from
    `dataset.json`. Here the manifest does not list a part that `dataset.json` lists."""
    pinned_example.store_copy()
    manifest = json.loads(pinned_example.manifest_file.read_text(encoding="utf-8"))
    manifest["parts"] = [part for part in manifest["parts"] if part["name"] != "exq_more"]
    pinned_example.write_manifest(manifest)

    the_one_difference_from_dataset_json(check(run_command, cwd=pinned_example.root))


def test_difference_8_a_row_count_differs_from_dataset_json(run_command, pinned_example):
    """data-model.md, "Data directory", difference 8: a row count of the manifest differs
    from `dataset.json`. The files and the manifest agree on 5 articles, and `dataset.json`
    records 6."""
    pinned_example.store_copy()
    pinned = pinned_example.read_dataset_json()
    assert pinned["parts"][0]["name"] == "ex"
    pinned["parts"][0]["rows"] = 6
    pinned_example.write_dataset_json(pinned)

    the_one_difference_from_dataset_json(check(run_command, cwd=pinned_example.root))


def test_difference_8_holds_for_the_default_directory_only(run_command, pinned_example, copy):
    """data-model.md, "Data directory", difference 8: "default directory only". A directory
    named with `--data-dir` is compared with its own manifest and not with `dataset.json`:
    the copy of the example has another name, no revision and other parts."""
    pinned_example.store_copy()

    result = check(run_command, copy, cwd=pinned_example.root)

    assert_passed(result)
    assert result.lines[:2] == ["dataset: example", "revision: none"]


# --- Not carried out: no local copy -----------------------------------------------------------


def test_a_directory_without_manifest_is_not_carried_out(run_command, copy):
    """contracts/cli.md, "`dataset check`": the directory has no `manifest.json` → `reason:`,
    `dataset check: not carried out`, exit code 2. A data directory without a manifest is not
    a local copy (data-model.md, "Data directory")."""
    (copy / "manifest.json").unlink()

    assert_not_carried_out(check(run_command, copy))


def test_a_directory_that_does_not_exist_is_not_carried_out(run_command, tmp_path):
    """contracts/cli.md, "`dataset check`": no `manifest.json`, or any other error → not
    carried out. A directory that does not exist has no manifest."""
    assert_not_carried_out(check(run_command, tmp_path / "no-such-directory"))


def test_without_a_local_copy_the_default_check_is_not_carried_out(run_command, pinned_example):
    """plan.md, "Points the spec leaves open", point 8: a dataset check without a local copy
    is not carried out; it is not reported as failed."""
    assert not pinned_example.data_dir.exists()

    assert_not_carried_out(check(run_command, cwd=pinned_example.root))
    assert not pinned_example.data_dir.exists(), "the check creates no data directory"


def test_part_files_without_a_manifest_are_not_a_local_copy(run_command, pinned_example):
    """data-model.md, "Data directory": the manifest is written last, and a data directory
    without a manifest is not a local copy, also when every part file is there."""
    pinned_example.store_copy()
    pinned_example.manifest_file.unlink()

    assert_not_carried_out(check(run_command, cwd=pinned_example.root))


def test_a_manifest_that_is_not_json_is_not_carried_out(run_command, copy):
    """contracts/cli.md, "`dataset check`": any other error → not carried out, exit code 2,
    never exit code 1 (research.md, section 16)."""
    (copy / "manifest.json").write_text("not JSON at all\n", encoding="utf-8")

    assert_not_carried_out(check(run_command, copy))


# --- Not carried out: a manifest that breaks a rule (data-model.md, "Data directory") --------


def manifest_without_a_corpus_part(manifest: dict) -> None:
    manifest_part(manifest, "ex")["role"] = "questions"


def manifest_with_two_corpus_parts(manifest: dict) -> None:
    manifest_part(manifest, "exq")["role"] = "corpus"


def manifest_with_a_part_name_used_twice(manifest: dict) -> None:
    manifest_part(manifest, "exq")["name"] = "ex"


@pytest.mark.parametrize(
    "break_the_rule",
    [
        manifest_without_a_corpus_part,
        manifest_with_two_corpus_parts,
        manifest_with_a_part_name_used_twice,
    ],
    ids=["no corpus part", "two corpus parts", "a part name used twice"],
)
def test_a_manifest_that_breaks_a_rule_is_not_carried_out(run_command, copy, break_the_rule):
    """contracts/cli.md, "Where a command is typed": a command is not carried out when the
    manifest of the data directory breaks a rule of data-model.md: no part or several parts
    have the role `corpus`, or a part name is used twice."""
    manifest = read_manifest(copy)
    break_the_rule(manifest)
    write_manifest(copy, manifest)

    assert_not_carried_out(check(run_command, copy))


# --- Not carried out: a dataset.json that breaks a rule (data-model.md, "Pinned revision") ----


def revision_is_a_branch_name(pinned: dict) -> None:
    pinned["revision"] = "main"


def revision_is_a_short_hash(pinned: dict) -> None:
    pinned["revision"] = pinned["revision"][:7]


def no_corpus_part(pinned: dict) -> None:
    pinned["parts"][0]["role"] = "questions"


def two_corpus_parts(pinned: dict) -> None:
    pinned["parts"][1]["role"] = "corpus"


def a_part_name_used_twice(pinned: dict) -> None:
    pinned["parts"][2]["name"] = pinned["parts"][1]["name"]


@pytest.mark.parametrize(
    "break_the_rule",
    [
        revision_is_a_branch_name,
        revision_is_a_short_hash,
        no_corpus_part,
        two_corpus_parts,
        a_part_name_used_twice,
    ],
    ids=[
        "revision is a branch name",
        "revision is a short hash",
        "no corpus part",
        "two corpus parts",
        "a part name used twice",
    ],
)
@pytest.mark.parametrize(
    "directory", ["the default directory", "a directory named with --data-dir"]
)
def test_a_dataset_json_that_breaks_a_rule_is_not_carried_out(
    run_command, pinned_example, copy, break_the_rule, directory
):
    """data-model.md, "Pinned revision": `revision` is a full commit hash, never a branch name;
    exactly one part has the role `corpus`; part names are unique. "A file that breaks one of
    these rules is not used: the command is not carried out." contracts/cli.md, "Where a
    command is typed": this holds for every command, also with `--data-dir`.

    With the unbroken `dataset.json` the same two checks pass; see
    `test_the_default_data_directory_is_checked_without_data_dir` and
    `test_difference_8_holds_for_the_default_directory_only`."""
    pinned_example.store_copy()
    pinned = pinned_example.read_dataset_json()
    break_the_rule(pinned)
    pinned_example.write_dataset_json(pinned)

    named = copy if directory == "a directory named with --data-dir" else None
    assert_not_carried_out(check(run_command, named, cwd=pinned_example.root))


def test_a_dataset_json_that_is_not_json_is_not_carried_out(run_command, pinned_example, copy):
    """contracts/cli.md, "Exit codes": every error ends with exit code 2 and never with 1."""
    (pinned_example.root / "dataset.json").write_text("not JSON at all\n", encoding="utf-8")

    assert_not_carried_out(check(run_command, copy, cwd=pinned_example.root))
