"""The example datasets under tests/data/ are what the documents say they are (tasks T012, T013).

Covers:

- contracts/records.md, "`manifest.json`": the row count, the size and the SHA-256 that each
  manifest records equal those of the files next to it;
- data-model.md, "Example datasets", "Article" and "Question": the five directories, their
  articles and questions, and the one difference of each directory from `example`;
- spec.md, "Acceptance Checks": the known answers that AC-003, AC-005 to AC-007 and AC-009 to
  AC-014 name (`ex-002` twice, `ex-006`, `ex-005`, `exq-003` and `ex-999`) are true of the files.

These tests read the files themselves and use no code of the package, so they pass before any
implementation exists. All documents named here are in specs/001-corpus-and-audit/.
"""

import hashlib
import json
import re
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "data"

DIRECTORIES = (
    "example",
    "example-damaged",
    "example-one-more-article",
    "example-one-less-article",
    "example-unknown-reference",
)
# The parts of every example directory: name, role and file (research.md, section 11).
PARTS = {"ex": ("corpus", "ex.jsonl"), "exq": ("questions", "exq.jsonl")}
FILES = [(directory, part) for directory in DIRECTORIES for part in PARTS]

ARTICLE_FIELDS = ("id", "url", "contents", "article_type")
QUESTION_FIELDS = ("question", "answer", "article_ids")
ARTICLE_TYPES = {"article", "feature_request", "known_issue"}

EXAMPLE_ARTICLE_IDS = ["ex-001", "ex-002", "ex-003", "ex-004", "ex-005"]


def read_bytes(directory: str, part: str) -> bytes:
    return (DATA / directory / PARTS[part][1]).read_bytes()


def read_rows(directory: str, part: str) -> list[dict]:
    """The rows of a part: one JSON object for each non-empty line (data-model.md, "Part")."""
    text = read_bytes(directory, part).decode("utf-8")
    return [json.loads(line) for line in text.split("\n") if line.strip()]


def read_lines(directory: str, part: str) -> list[bytes]:
    """The non-empty lines of a part as bytes, to compare rows byte for byte."""
    return [line for line in read_bytes(directory, part).split(b"\n") if line.strip()]


def read_manifest(directory: str) -> dict:
    return json.loads((DATA / directory / "manifest.json").read_text(encoding="utf-8"))


def manifest_part(directory: str, part: str) -> dict:
    found = [entry for entry in read_manifest(directory)["parts"] if entry["name"] == part]
    assert len(found) == 1, f"{directory}/manifest.json must list the part {part} exactly once"
    return found[0]


def article_ids(directory: str) -> list[str]:
    return [row["id"] for row in read_rows(directory, "ex")]


def question_reference(row_number: int) -> str:
    """The question reference of a row of `exq` (data-model.md, "Question")."""
    return f"exq-{row_number:03d}"


def references(directory: str) -> dict[str, list[str]]:
    """Question reference -> the article ids that the question names."""
    rows = read_rows(directory, "exq")
    return {question_reference(number): row["article_ids"] for number, row in enumerate(rows, 1)}


# --- The directories and their files (data-model.md, "Example datasets") ---------------------


def test_the_five_example_directories_exist():
    """data-model.md, "Example datasets": five data directories under tests/data/."""
    missing = [name for name in DIRECTORIES if not (DATA / name).is_dir()]
    assert not missing, f"missing under tests/data/: {missing}"


@pytest.mark.parametrize("directory", DIRECTORIES)
def test_a_directory_holds_its_two_parts_and_its_manifest(directory):
    """tasks.md, T012: each directory holds `ex.jsonl`, `exq.jsonl` and `manifest.json` only."""
    names = sorted(entry.name for entry in (DATA / directory).iterdir())
    assert names == ["ex.jsonl", "exq.jsonl", "manifest.json"]


# --- The manifest (contracts/records.md, "`manifest.json`") ----------------------------------


@pytest.mark.parametrize("directory", DIRECTORIES)
def test_manifest_has_the_fields_of_the_records_contract(directory):
    """contracts/records.md, "`manifest.json`": the fields of a manifest and of its parts.

    An example dataset is not published and was not fetched, so `revision` and `fetched_at`
    are null. The dataset name is `example`, as contracts/cli.md prints it (`dataset: example`).
    """
    manifest = read_manifest(directory)
    assert set(manifest) == {"name", "revision", "fetched_at", "parts"}
    assert manifest["name"] == "example"
    assert manifest["revision"] is None
    assert manifest["fetched_at"] is None

    for entry in manifest["parts"]:
        assert set(entry) == {"name", "role", "path", "rows", "bytes", "sha256"}
        assert type(entry["rows"]) is int
        assert type(entry["bytes"]) is int
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), (
            "a SHA-256 is written as 64 lower-case hexadecimal characters"
        )


@pytest.mark.parametrize("directory", DIRECTORIES)
def test_manifest_lists_one_corpus_part_and_one_question_part(directory):
    """data-model.md, "Example datasets" and "Data directory": a corpus part `ex` and a question
    part `exq`; exactly one part has the role `corpus`, and part names are unique."""
    listed = {
        entry["name"]: (entry["role"], entry["path"]) for entry in read_manifest(directory)["parts"]
    }
    assert len(read_manifest(directory)["parts"]) == 2
    assert listed == PARTS


@pytest.mark.parametrize(("directory", "part"), FILES)
def test_manifest_row_count_equals_the_rows_of_the_file(directory, part):
    """contracts/records.md, `parts[].rows`; a row is a non-empty line (data-model.md, "Part")."""
    lines = read_bytes(directory, part).split(b"\n")
    rows = sum(1 for line in lines if line.strip())
    assert manifest_part(directory, part)["rows"] == rows


@pytest.mark.parametrize(("directory", "part"), FILES)
def test_manifest_size_equals_the_bytes_of_the_file(directory, part):
    """contracts/records.md, `parts[].bytes`: the size of the file."""
    assert manifest_part(directory, part)["bytes"] == len(read_bytes(directory, part))


@pytest.mark.parametrize(("directory", "part"), FILES)
def test_manifest_sha256_equals_the_fingerprint_of_the_file(directory, part):
    """contracts/records.md, `parts[].sha256`: the fingerprint of the file."""
    fingerprint = hashlib.sha256(read_bytes(directory, part)).hexdigest()
    assert manifest_part(directory, part)["sha256"] == fingerprint


# --- The form of the part files (data-model.md, "Part", "Article", "Question") ---------------


@pytest.mark.parametrize(("directory", "part"), FILES)
def test_a_part_file_is_utf8_json_lines_with_lf_line_endings(directory, part):
    """data-model.md, "Part": one JSON object per line. research.md, section 11: a fingerprint
    is taken of bytes, so the files have LF line endings on every platform."""
    data = read_bytes(directory, part)
    assert b"\r" not in data, "a carriage return would change the fingerprint"
    assert data.endswith(b"\n"), "the last row ends with a line feed"
    lines = data.decode("utf-8").split("\n")[:-1]
    assert all(line.strip() for line in lines), "no empty line: every line is a row"
    assert all(type(json.loads(line)) is dict for line in lines)


@pytest.mark.parametrize("directory", DIRECTORIES)
def test_an_article_row_has_the_four_fields_as_text(directory):
    """data-model.md, "Article": `id`, `url`, `contents` and `article_type` are strings.

    Every example article has text, so every one produces a passage and no audit of these
    directories names an article without passages (data-model.md, "Example datasets").
    """
    for row in read_rows(directory, "ex"):
        assert tuple(row) == ARTICLE_FIELDS
        assert all(type(row[field]) is str for field in ARTICLE_FIELDS)
        assert row["contents"].strip()
        assert row["article_type"] in ARTICLE_TYPES
        assert re.fullmatch(r"ex-\d{3}", row["id"])


@pytest.mark.parametrize("directory", DIRECTORIES)
def test_a_question_row_has_the_three_fields(directory):
    """data-model.md, "Question": `question` and `answer` are strings, and `article_ids` is a
    list of strings. No example question has an empty list or names an article twice."""
    for row in read_rows(directory, "exq"):
        assert tuple(row) == QUESTION_FIELDS
        assert type(row["question"]) is str and row["question"]
        assert type(row["answer"]) is str and row["answer"]
        assert type(row["article_ids"]) is list and row["article_ids"]
        assert all(type(value) is str for value in row["article_ids"])
        assert len(set(row["article_ids"])) == len(row["article_ids"])


def test_the_example_corpus_is_not_plain_ascii():
    """contracts/records.md, `parts[].bytes`: the size is counted in bytes, not in characters.
    One article holds a character of several bytes, so the two numbers differ."""
    data = read_bytes("example", "ex")
    assert len(data.decode("utf-8")) < len(data)


# --- `example` (data-model.md, "Example datasets"; spec.md, "Acceptance Checks") -------------


def test_example_has_the_articles_ex_001_to_ex_005():
    """spec.md, "Acceptance Checks": five articles, `ex-001` to `ex-005`."""
    assert article_ids("example") == EXAMPLE_ARTICLE_IDS


def test_example_has_the_questions_exq_001_to_exq_003():
    """spec.md, "Acceptance Checks": three questions, `exq-001` to `exq-003`. A question is
    named by its part and its row number (data-model.md, "Question")."""
    assert list(references("example")) == ["exq-001", "exq-002", "exq-003"]


def test_example_questions_name_only_ex_001_to_ex_004_and_one_names_two():
    """data-model.md, "Example datasets": the questions name only the articles `ex-001` to
    `ex-004`, and one question names two articles."""
    named = references("example")
    assert {value for ids in named.values() for value in ids} == {
        "ex-001",
        "ex-002",
        "ex-003",
        "ex-004",
    }
    assert sorted(len(ids) for ids in named.values()) == [1, 1, 2]


# --- `example-damaged` (AC-003, AC-007) -------------------------------------------------------


def test_damaged_repeats_the_row_of_ex_002_and_nothing_else():
    """data-model.md, "Example datasets": as `example`, with the row of `ex-002` twice.
    AC-003 expects the dataset check to name the repeated article id `ex-002`."""
    original = read_lines("example", "ex")
    damaged = read_lines("example-damaged", "ex")
    row_of_ex_002 = original[1]

    assert article_ids("example-damaged") == [*EXAMPLE_ARTICLE_IDS, "ex-002"]
    assert damaged == [*original, row_of_ex_002]
    assert read_bytes("example-damaged", "exq") == read_bytes("example", "exq")


def test_damaged_manifest_matches_its_own_files():
    """data-model.md, "Example datasets": the manifest of each directory matches its own files,
    so the repeated id is the only difference that the dataset check finds in AC-003."""
    assert manifest_part("example-damaged", "ex")["rows"] == 6


# --- `example-one-more-article` (AC-006, AC-009) ----------------------------------------------


def test_one_more_article_adds_ex_006_and_nothing_else():
    """data-model.md, "Example datasets": `ex-001` to `ex-006`, questions as `example`.
    AC-009 expects `missing from index: 1` and the id `ex-006`; AC-006 expects another corpus."""
    original = read_lines("example", "ex")
    larger = read_lines("example-one-more-article", "ex")

    assert article_ids("example-one-more-article") == [*EXAMPLE_ARTICLE_IDS, "ex-006"]
    assert larger[:5] == original
    assert read_bytes("example-one-more-article", "exq") == read_bytes("example", "exq")
    assert (
        manifest_part("example-one-more-article", "ex")["sha256"]
        != manifest_part("example", "ex")["sha256"]
    )


# --- `example-one-less-article` (AC-010) ------------------------------------------------------


def test_one_less_article_lacks_ex_005_and_nothing_else():
    """data-model.md, "Example datasets": `ex-001` to `ex-004`, questions as `example`.
    AC-010 expects `not in corpus: 1` and the id `ex-005`."""
    original = read_lines("example", "ex")
    smaller = read_lines("example-one-less-article", "ex")

    assert article_ids("example-one-less-article") == EXAMPLE_ARTICLE_IDS[:4]
    assert smaller == original[:4]
    assert read_bytes("example-one-less-article", "exq") == read_bytes("example", "exq")


# --- `example-unknown-reference` (AC-011) -----------------------------------------------------


def test_unknown_reference_adds_ex_999_to_exq_003_and_nothing_else():
    """data-model.md, "Example datasets": articles as `example`; `exq-003` also names `ex-999`.
    AC-011 expects `unknown question references: 1`, the question `exq-003` and the id `ex-999`.
    """
    original = read_rows("example", "exq")
    altered = read_rows("example-unknown-reference", "exq")

    assert read_bytes("example-unknown-reference", "ex") == read_bytes("example", "ex")
    assert read_lines("example-unknown-reference", "exq")[:2] == read_lines("example", "exq")[:2]
    assert altered[2] == {
        **original[2],
        "article_ids": [*original[2]["article_ids"], "ex-999"],
    }


def test_unknown_reference_is_the_only_reference_outside_the_example_corpus():
    """AC-011 expects exactly one unknown question reference: the pair `exq-003` -> `ex-999`."""
    held_by_the_index = set(article_ids("example"))
    unknown = [
        (question, value)
        for question, ids in references("example-unknown-reference").items()
        for value in ids
        if value not in held_by_the_index
    ]
    assert unknown == [("exq-003", "ex-999")]


# --- The known answers of the audits (AC-009 to AC-013) --------------------------------------


@pytest.mark.parametrize(
    ("directory", "missing_from_index", "not_in_corpus", "unknown_references"),
    [
        ("example", [], [], []),
        ("example-one-more-article", ["ex-006"], [], []),
        ("example-one-less-article", [], ["ex-005"], []),
        ("example-unknown-reference", [], [], [("exq-003", "ex-999")]),
    ],
)
def test_an_audit_against_a_directory_has_one_known_answer(
    directory, missing_from_index, not_in_corpus, unknown_references
):
    """data-model.md, "Audit result" and "Example datasets": for an index built from `example`,
    the audit against each directory shows exactly the difference of the table and nothing else
    (AC-009, AC-010, AC-011; AC-013 for `example` itself). The three lists are worked out here
    from the files alone, with the definitions of "Audit result"."""
    in_index = set(article_ids("example"))
    in_corpus = set(article_ids(directory))

    assert sorted(in_corpus - in_index) == missing_from_index
    assert sorted(in_index - in_corpus) == not_in_corpus
    assert (
        sorted(
            (question, value)
            for question, ids in references(directory).items()
            for value in set(ids)
            if value not in in_index
        )
        == unknown_references
    )
