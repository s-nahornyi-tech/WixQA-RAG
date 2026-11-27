"""The example data of spec 2 under tests/data/ is what the documents say it is (task T009).

Covers, for the data of tasks T005 to T008:

- data-model.md, "Example data", "`tests/data/harness/`: a data directory", and spec 1's
  contracts/records.md, "`manifest.json`": the manifest matches its files; the six articles
  and the ten questions with their gold article ids; ten different question texts;
- data-model.md, "Selection rule" and the table of the eight draw keys: each key is the
  SHA-256 of `sha256-order-v1:7:<identifier>`, and the three smallest of `hxa` and the
  smallest of `hxb` are the questions of `harness-half`;
- contracts/records.md, "Question-set record": every record of `tests/data/sets/` has the
  bytes of its own canonical form, the fields in the order of the contract, and the content
  that the table of data-model.md states; `of_fingerprint` of the two complements is the
  SHA-256 of `harness-half.json`;
- contracts/records.md, "Run record", and data-model.md, "`tests/data/runs/`": in every run
  record the fingerprint of the question set is the SHA-256 of the set's file, every
  `answer_sha256` is the hash of its answer, every `cost_usd` follows from the tokens and the
  prices, `run_id` is the name of the directory, and the entries and every number of the four
  summaries are those of the tables;
- data-model.md, "`tests/data/runs-invalid/`": the two sound records have the bytes of those
  of `tests/data/runs/`, and each of the seven others is the record it is made from with its
  own `run_id` and `started_at` and the one change of the table.

These tests read the files themselves, compute every fingerprint, hash, cost and number on
their own, and use no code of the package, so they pass before any implementation exists.
The documents named here are in specs/002-evaluation-harness/ unless spec 1 is named.
"""

import copy
import hashlib
import json
import re
from fractions import Fraction
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "data"
HARNESS = DATA / "harness"
SETS = DATA / "sets"
RUNS = DATA / "runs"
RUNS_INVALID = DATA / "runs-invalid"

SHA256 = re.compile(r"[0-9a-f]{64}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint(file: Path) -> str:
    """The SHA-256 of the bytes of a file (data-model.md, "Question set": "Fingerprint")."""
    return sha256(file.read_bytes())


def read_json(file: Path):
    return json.loads(file.read_text(encoding="utf-8"))


def read_rows(file: Path) -> list[dict]:
    """One JSON object for each non-empty line of a JSON Lines file."""
    return [json.loads(line) for line in file.read_text(encoding="utf-8").split("\n") if line]


def canonical(document) -> bytes:
    """contracts/records.md, "The canonical form": an indentation of two spaces, the
    separators of `json.dumps`, non-ASCII characters as they are, one line feed at the end."""
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


# =============================================================================================
# tests/data/harness/ (T005)
# =============================================================================================

# data-model.md, "`tests/data/harness/`: a data directory": part -> role, file, rows.
PARTS = {
    "hx": ("corpus", "hx.jsonl", 6),
    "hxa": ("questions", "hxa.jsonl", 5),
    "hxb": ("questions", "hxb.jsonl", 3),
    "hxc": ("questions", "hxc.jsonl", 2),
}
QUESTION_PARTS = ("hxa", "hxb", "hxc")

# The table of the ten questions, copied from data-model.md.
GOLD = {
    "hxa-001": ["hx-001"],
    "hxa-002": ["hx-002"],
    "hxa-003": ["hx-001", "hx-003"],
    "hxa-004": ["hx-002", "hx-003", "hx-004"],
    "hxa-005": ["hx-005"],
    "hxb-001": ["hx-004", "hx-005"],
    "hxb-002": ["hx-006"],
    "hxb-003": ["hx-001", "hx-006"],
    "hxc-001": ["hx-001"],
    "hxc-002": ["hx-002"],
}
SINGLE_ARTICLE = {"hxa-001", "hxa-002", "hxa-005", "hxb-002", "hxc-001", "hxc-002"}
ARTICLE_TYPES = {"article", "feature_request", "known_issue"}


def harness_manifest() -> dict:
    return read_json(HARNESS / "manifest.json")


def harness_questions() -> dict[str, dict]:
    """Question identifier -> row, for the three question parts (data-model.md, "Question
    identifier": the part, a hyphen, the row number from 1 with at least three digits)."""
    return {
        f"{part}-{number:03d}": row
        for part in QUESTION_PARTS
        for number, row in enumerate(read_rows(HARNESS / PARTS[part][1]), 1)
    }


def test_the_harness_directory_holds_its_four_parts_and_its_manifest():
    """tasks.md, T005: `hx.jsonl`, `hxa.jsonl`, `hxb.jsonl`, `hxc.jsonl` and `manifest.json`."""
    names = sorted(entry.name for entry in HARNESS.iterdir())
    assert names == ["hx.jsonl", "hxa.jsonl", "hxb.jsonl", "hxc.jsonl", "manifest.json"]


def test_the_harness_manifest_has_the_name_harness_and_no_revision():
    """data-model.md, "Example data": the name `harness`, the revision `null`. Spec 1's
    contracts/records.md, "`manifest.json`": `fetched_at` is `null` for a dataset that was
    not fetched."""
    manifest = harness_manifest()
    assert list(manifest) == ["name", "revision", "fetched_at", "parts"]
    assert manifest["name"] == "harness"
    assert manifest["revision"] is None
    assert manifest["fetched_at"] is None


def test_the_harness_manifest_lists_one_corpus_part_and_three_question_parts():
    """data-model.md, the table of the parts: name, role, file and rows of each."""
    listed = {
        entry["name"]: (entry["role"], entry["path"], entry["rows"])
        for entry in harness_manifest()["parts"]
    }
    assert len(harness_manifest()["parts"]) == 4
    assert listed == PARTS
    for entry in harness_manifest()["parts"]:
        assert set(entry) == {"name", "role", "path", "rows", "bytes", "sha256"}


@pytest.mark.parametrize("part", PARTS)
def test_the_harness_manifest_matches_the_file_of_a_part(part):
    """Spec 1's contracts/records.md, "`manifest.json`": the row count, the size in bytes and
    the SHA-256 that the manifest records are those of the file."""
    data = (HARNESS / PARTS[part][1]).read_bytes()
    (entry,) = [entry for entry in harness_manifest()["parts"] if entry["name"] == part]

    assert entry["rows"] == sum(1 for line in data.split(b"\n") if line.strip())
    assert entry["bytes"] == len(data)
    assert entry["sha256"] == sha256(data)


def test_the_harness_articles_are_hx_001_to_hx_006():
    """data-model.md: six articles, `hx-001` to `hx-006`, in the form of spec 1's article:
    `id`, `url`, `contents` and `article_type` as text, and every article has text."""
    rows = read_rows(HARNESS / "hx.jsonl")
    assert [row["id"] for row in rows] == [f"hx-{number:03d}" for number in range(1, 7)]
    for row in rows:
        assert list(row) == ["id", "url", "contents", "article_type"]
        assert all(type(value) is str for value in row.values())
        assert row["contents"].strip()
        assert row["article_type"] in ARTICLE_TYPES


def test_the_harness_questions_name_the_gold_articles_of_the_table():
    """data-model.md, the table of the ten questions: the `article_ids` of each, in order."""
    questions = harness_questions()
    assert {identifier: row["article_ids"] for identifier, row in questions.items()} == GOLD
    for row in questions.values():
        assert list(row) == ["question", "answer", "article_ids"]
        assert type(row["question"]) is str and row["question"]
        assert type(row["answer"]) is str and row["answer"]


def test_the_harness_questions_are_single_article_and_multi_article_as_the_table_says():
    """data-model.md, the column "Kind"; spec.md: `harness` has four single-article and four
    multi-article questions, and both questions of `hxc` are single-article."""
    single = {identifier for identifier, ids in GOLD.items() if len(set(ids)) == 1}
    assert single == SINGLE_ARTICLE
    of_harness = [identifier for identifier in GOLD if not identifier.startswith("hxc")]
    assert sum(1 for identifier in of_harness if identifier in single) == 4
    assert sum(1 for identifier in of_harness if identifier not in single) == 4


def test_the_ten_question_texts_are_all_different():
    """data-model.md: "The ten question texts are all different, so every check reports
    `repeated question texts: 0` and `question texts in both sets: 0`." Texts are compared as
    they are."""
    texts = [row["question"] for row in harness_questions().values()]
    assert len(texts) == 10
    assert len(set(texts)) == 10


def test_the_harness_corpus_is_not_plain_ascii():
    """A size is counted in bytes and a hash is taken of UTF-8 bytes; one article holds a
    character of several bytes, so that bytes and characters differ."""
    data = (HARNESS / "hx.jsonl").read_bytes()
    assert len(data.decode("utf-8")) < len(data)


# =============================================================================================
# Every file of the example data: UTF-8, LF line endings, a final line feed
# =============================================================================================

EXAMPLE_FILES = sorted(
    file.relative_to(DATA).as_posix()
    for directory in (HARNESS, SETS, RUNS, RUNS_INVALID)
    for file in directory.rglob("*")
    if file.is_file()
)


def test_the_example_data_of_spec_2_exists():
    """tasks.md, T005 to T008: 5 files of the data directory, 10 question-set records, and
    three files for each of the 4 + 9 run records."""
    assert len(EXAMPLE_FILES) == 5 + 10 + 3 * (4 + 9)


@pytest.mark.parametrize("name", EXAMPLE_FILES)
def test_a_file_of_the_example_data_is_utf8_with_lf_line_endings(name):
    """contracts/records.md: "Every file is UTF-8 text." research.md, section 14: a
    fingerprint is taken of bytes, so the files have LF line endings and no carriage return."""
    data = (DATA / name).read_bytes()
    data.decode("utf-8")
    assert b"\r" not in data, "a carriage return would change the fingerprint"
    assert data.endswith(b"\n") and not data.endswith(b"\n\n"), "exactly one final line feed"
    assert not data.startswith(b"\xef\xbb\xbf"), "no byte order mark"


# =============================================================================================
# The draw behind `harness-half` (data-model.md, "Selection rule" and the table of the keys)
# =============================================================================================

# The table of the eight draw keys with the seed 7, copied from data-model.md:
# identifier -> key, position in its part, selected.
DRAW_KEYS = {
    "hxa-001": ("b007c1a99f194f36e77ddff1287444edf952051575fc10e8920235c10574b35a", 4, False),
    "hxa-002": ("3ab6dbb72b4a0c0ea6ac711d6dc1f5d74391faf706a742a5ba6f9392127e8bfc", 1, True),
    "hxa-003": ("3d153221a5af0c19cabea03edc0c7911e80dc59e4665e9d71f3bcb5d5e22e1e3", 2, True),
    "hxa-004": ("ddd57ba1f0b3ac63038adda3109582537c275bde1cd1d957e296569a1c668f3b", 5, False),
    "hxa-005": ("ac565ec9fabc07a8cbfe8cbb64efaf1d716272217ecb623cb8954a8f0b035bd9", 3, True),
    "hxb-001": ("bdeb5dbf30b3cda7003e44daaa672c50e9ef7f6796a1f5b4fa61e5e88563be62", 2, False),
    "hxb-002": ("25dedc6ec7bacbd106c0818e47ab1288ccfc0f93a2a1f357497e3d1797a190fa", 1, True),
    "hxb-003": ("e63b12a2e3a527e027c2b151bdff7ee0728d36c6e9417885d6fe85d70c8db68a", 3, False),
}
HALF = ["hxa-002", "hxa-003", "hxa-005", "hxb-002"]
HALF_REST = ["hxa-001", "hxa-004", "hxb-001", "hxb-003"]


def draw_key(seed: int, identifier: str) -> str:
    """data-model.md, "The draw key": the SHA-256 of the UTF-8 bytes of
    `sha256-order-v1:<seed>:<identifier>`."""
    return sha256(f"sha256-order-v1:{seed}:{identifier}".encode())


@pytest.mark.parametrize("identifier", DRAW_KEYS)
def test_a_draw_key_of_the_table_is_the_sha256_of_its_text(identifier):
    """data-model.md, the table of the eight draw keys: each key, computed here."""
    assert draw_key(7, identifier) == DRAW_KEYS[identifier][0]


@pytest.mark.parametrize("part", ["hxa", "hxb"])
def test_the_positions_of_the_table_are_the_order_of_the_keys(part):
    """data-model.md, the column "Position in its part": the identifiers of a part in
    ascending order of their keys, compared as text."""
    identifiers = [identifier for identifier in DRAW_KEYS if identifier.startswith(part)]
    ordered = sorted(identifiers, key=lambda identifier: (draw_key(7, identifier), identifier))
    positions = {identifier: number for number, identifier in enumerate(ordered, 1)}

    assert positions == {identifier: DRAW_KEYS[identifier][1] for identifier in identifiers}


def test_the_smallest_keys_are_the_questions_of_harness_half():
    """data-model.md: the draw of N questions selects the N identifiers with the smallest
    keys. Three of `hxa` and one of `hxb` with the seed 7 are the questions of the record
    `harness-half`, which stand in the order of the dataset."""
    selected = []
    for part, number in (("hxa", 3), ("hxb", 1)):
        identifiers = [identifier for identifier in GOLD if identifier.startswith(part)]
        smallest = sorted(identifiers, key=lambda identifier: draw_key(7, identifier))[:number]
        selected.extend(sorted(smallest))

    assert selected == HALF
    assert selected == [identifier for identifier, row in DRAW_KEYS.items() if row[2]]
    recorded = read_json(SETS / "harness-half.json")
    assert [question["id"] for question in recorded["questions"]] == selected


# =============================================================================================
# tests/data/sets/ (T006)
# =============================================================================================

ALL_OF_HARNESS = [
    "hxa-001",
    "hxa-002",
    "hxa-003",
    "hxa-004",
    "hxa-005",
    "hxb-001",
    "hxb-002",
    "hxb-003",
]
DRAW_ALL = {
    "kind": "draw",
    "method": "sha256-order-v1",
    "seed": 1,
    "take": [{"part": "hxa", "questions": 5}, {"part": "hxb", "questions": 3}],
}
DRAW_HALF = {
    "kind": "draw",
    "method": "sha256-order-v1",
    "seed": 7,
    "take": [{"part": "hxa", "questions": 3}, {"part": "hxb", "questions": 1}],
}
COMPLEMENT_OF_HALF = "the complement of harness-half"

# The table of the ten records, copied from data-model.md:
# version -> role, rule, the question identifiers in order.
SET_TABLE = {
    "harness": ("golden", DRAW_ALL, ALL_OF_HARNESS),
    "harness-hxc": (
        "held-out",
        {
            "kind": "draw",
            "method": "sha256-order-v1",
            "seed": 1,
            "take": [{"part": "hxc", "questions": 2}],
        },
        ["hxc-001", "hxc-002"],
    ),
    "harness-one-less": ("golden", DRAW_ALL, ALL_OF_HARNESS[:-1]),
    "harness-one-more": ("golden", DRAW_ALL, [*ALL_OF_HARNESS, "hxc-001"]),
    "harness-other-gold": ("golden", DRAW_ALL, ALL_OF_HARNESS),
    "harness-half": ("golden", DRAW_HALF, HALF),
    "harness-half-rest": ("held-out", COMPLEMENT_OF_HALF, HALF_REST),
    "harness-half-swapped": ("golden", DRAW_HALF, ["hxa-001", "hxa-002", "hxa-003", "hxb-002"]),
    "harness-half-rest-overlap": (
        "held-out",
        COMPLEMENT_OF_HALF,
        ["hxa-001", "hxa-002", "hxb-001", "hxb-003"],
    ),
    "example": (
        "golden",
        {
            "kind": "draw",
            "method": "sha256-order-v1",
            "seed": 1,
            "take": [{"part": "exq", "questions": 3}],
        },
        ["exq-001", "exq-002", "exq-003"],
    ),
}
VERSIONS = tuple(SET_TABLE)
# The parts a record takes questions from; "`dataset.parts` as `harness`" for `one-more`.
PARTS_OF_SET = {version: ["hxa", "hxb"] for version in VERSIONS} | {
    "harness-hxc": ["hxc"],
    "example": ["exq"],
}


def read_set(version: str) -> dict:
    return read_json(SETS / f"{version}.json")


def data_directory_of(version: str) -> Path:
    return DATA / "example" if version == "example" else HARNESS


def gold_of_the_dataset(version: str) -> dict[str, list[str]]:
    """Question identifier -> `article_ids` of its row, for the data directory of a set."""
    if version != "example":
        return GOLD
    rows = read_rows(DATA / "example" / "exq.jsonl")
    return {f"exq-{number:03d}": row["article_ids"] for number, row in enumerate(rows, 1)}


def expected_rule(version: str) -> dict:
    rule = SET_TABLE[version][1]
    if rule == COMPLEMENT_OF_HALF:
        return {
            "kind": "complement",
            "of": "harness-half",
            "of_fingerprint": fingerprint(SETS / "harness-half.json"),
        }
    return rule


def test_the_sets_directory_holds_the_ten_records():
    """tasks.md, T006: the ten question-set records, one file `<version>.json` each."""
    names = sorted(entry.name for entry in SETS.iterdir())
    assert names == sorted(f"{version}.json" for version in VERSIONS)


@pytest.mark.parametrize("version", VERSIONS)
def test_a_set_record_has_the_bytes_of_its_canonical_form(version):
    """contracts/records.md, "The canonical form": writing the document of the record again
    in that form gives the bytes of the file."""
    data = (SETS / f"{version}.json").read_bytes()
    assert data == canonical(json.loads(data))


@pytest.mark.parametrize("version", VERSIONS)
def test_a_set_record_has_its_fields_in_the_order_of_the_contract(version):
    """contracts/records.md, "The canonical form": the keys in the order of the tables."""
    record = read_set(version)
    assert list(record) == ["version", "role", "dataset", "rule", "questions", "count"]
    assert list(record["dataset"]) == ["name", "revision", "parts"]
    for part in record["dataset"]["parts"]:
        assert list(part) == ["name", "rows", "sha256"]
    if record["rule"]["kind"] == "draw":
        assert list(record["rule"]) == ["kind", "method", "seed", "take"]
        for take in record["rule"]["take"]:
            assert list(take) == ["part", "questions"]
    else:
        assert list(record["rule"]) == ["kind", "of", "of_fingerprint"]
    for question in record["questions"]:
        assert list(question) == ["id", "article_ids"]


@pytest.mark.parametrize("version", VERSIONS)
def test_a_set_record_has_its_own_version_and_the_role_of_the_table(version):
    """data-model.md: "Every record has its own `version`", equal to the name of the file
    without `.json`; the role as the table gives it."""
    record = read_set(version)
    assert record["version"] == version
    assert record["role"] == SET_TABLE[version][0]


@pytest.mark.parametrize("version", VERSIONS)
def test_a_set_record_names_the_dataset_and_the_fingerprints_of_its_parts(version):
    """contracts/records.md: `dataset.name` and `dataset.revision` from the manifest of the
    data directory, and for each part its row count and its SHA-256. Computed here from the
    part files, and compared with the manifest as well."""
    record = read_set(version)
    directory = data_directory_of(version)
    manifest = read_json(directory / "manifest.json")
    listed = {entry["name"]: entry for entry in manifest["parts"]}

    assert record["dataset"]["name"] == manifest["name"]
    assert record["dataset"]["revision"] is None
    assert [part["name"] for part in record["dataset"]["parts"]] == PARTS_OF_SET[version]
    for part in record["dataset"]["parts"]:
        data = (directory / listed[part["name"]]["path"]).read_bytes()
        assert listed[part["name"]]["role"] == "questions"
        assert part["rows"] == sum(1 for line in data.split(b"\n") if line.strip())
        assert part["rows"] == listed[part["name"]]["rows"]
        assert part["sha256"] == sha256(data)
        assert part["sha256"] == listed[part["name"]]["sha256"]


@pytest.mark.parametrize("version", VERSIONS)
def test_a_set_record_has_the_rule_of_the_table(version):
    """data-model.md, the column "Rule". For the two complements `of_fingerprint` is the
    SHA-256 of the bytes of `harness-half.json`, computed here."""
    assert read_set(version)["rule"] == expected_rule(version)


@pytest.mark.parametrize("version", VERSIONS)
def test_a_set_record_lists_the_questions_of_the_table(version):
    """data-model.md, the column "`questions`, in order"; `count` is their number."""
    record = read_set(version)
    identifiers = [question["id"] for question in record["questions"]]
    assert identifiers == SET_TABLE[version][2]
    assert len(set(identifiers)) == len(identifiers)
    assert record["count"] == len(identifiers)


@pytest.mark.parametrize("version", VERSIONS)
def test_a_set_record_gives_the_gold_articles_as_the_dataset_does(version):
    """contracts/records.md, `questions[].article_ids`: exactly as the row of the dataset
    gives them. The one exception is the defect of `harness-other-gold`: there the
    `article_ids` of `hxa-003` are `hx-001` only."""
    expected = dict(gold_of_the_dataset(version))
    if version == "harness-other-gold":
        assert expected["hxa-003"] == ["hx-001", "hx-003"]
        expected["hxa-003"] = ["hx-001"]

    for question in read_set(version)["questions"]:
        assert question["article_ids"] == expected[question["id"]], question["id"]


def test_the_example_set_takes_all_three_questions_of_the_example_dataset():
    """spec.md: `example` is 3 of `exq` of `tests/data/example`, all three questions."""
    assert len(read_rows(DATA / "example" / "exq.jsonl")) == 3
    assert read_set("example")["dataset"]["name"] == "example"


def test_harness_half_has_the_bytes_of_the_example_of_the_contract():
    """contracts/records.md, "A set whose rule draws": the document of the contract, with the
    two fingerprints of the part files computed here, written in the canonical form."""
    expected = {
        "version": "harness-half",
        "role": "golden",
        "dataset": {
            "name": "harness",
            "revision": None,
            "parts": [
                {"name": "hxa", "rows": 5, "sha256": fingerprint(HARNESS / "hxa.jsonl")},
                {"name": "hxb", "rows": 3, "sha256": fingerprint(HARNESS / "hxb.jsonl")},
            ],
        },
        "rule": {
            "kind": "draw",
            "method": "sha256-order-v1",
            "seed": 7,
            "take": [{"part": "hxa", "questions": 3}, {"part": "hxb", "questions": 1}],
        },
        "questions": [
            {"id": "hxa-002", "article_ids": ["hx-002"]},
            {"id": "hxa-003", "article_ids": ["hx-001", "hx-003"]},
            {"id": "hxa-005", "article_ids": ["hx-005"]},
            {"id": "hxb-002", "article_ids": ["hx-006"]},
        ],
        "count": 4,
    }
    assert (SETS / "harness-half.json").read_bytes() == canonical(expected)


def test_harness_half_rest_has_the_bytes_of_the_example_of_the_contract():
    """contracts/records.md, "A set whose rule is a complement": the document of the
    contract, with the three fingerprints computed here, written in the canonical form."""
    expected = {
        "version": "harness-half-rest",
        "role": "held-out",
        "dataset": {
            "name": "harness",
            "revision": None,
            "parts": [
                {"name": "hxa", "rows": 5, "sha256": fingerprint(HARNESS / "hxa.jsonl")},
                {"name": "hxb", "rows": 3, "sha256": fingerprint(HARNESS / "hxb.jsonl")},
            ],
        },
        "rule": {
            "kind": "complement",
            "of": "harness-half",
            "of_fingerprint": fingerprint(SETS / "harness-half.json"),
        },
        "questions": [
            {"id": "hxa-001", "article_ids": ["hx-001"]},
            {"id": "hxa-004", "article_ids": ["hx-002", "hx-003", "hx-004"]},
            {"id": "hxb-001", "article_ids": ["hx-004", "hx-005"]},
            {"id": "hxb-003", "article_ids": ["hx-001", "hx-006"]},
        ],
        "count": 4,
    }
    assert (SETS / "harness-half-rest.json").read_bytes() == canonical(expected)


@pytest.mark.parametrize("version", ["harness-half-rest", "harness-half-rest-overlap"])
def test_of_fingerprint_of_a_complement_is_the_sha256_of_harness_half(version):
    """tasks.md, T009: `of_fingerprint` of the two complements is the SHA-256 of
    `harness-half.json`."""
    rule = read_set(version)["rule"]
    assert rule["of"] == "harness-half"
    assert rule["of_fingerprint"] == sha256((SETS / "harness-half.json").read_bytes())


def test_harness_half_and_its_rest_share_no_question_and_are_all_questions_of_their_parts():
    """data-model.md: `harness-half-rest` passes with `in both sets: 0` and
    `in neither set: 0`."""
    half = {question["id"] for question in read_set("harness-half")["questions"]}
    rest = {question["id"] for question in read_set("harness-half-rest")["questions"]}
    assert not half & rest
    assert half | rest == set(ALL_OF_HARNESS)


def test_the_swapped_record_differs_from_the_draw_in_exactly_two_questions():
    """data-model.md, "What the checks of the four records around the draw find":
    `hxa-005` is selected by the rule and is not in the set; `hxa-001` is in the set and is
    not selected by the rule."""
    swapped = {question["id"] for question in read_set("harness-half-swapped")["questions"]}
    assert set(HALF) - swapped == {"hxa-005"}
    assert swapped - set(HALF) == {"hxa-001"}


def test_the_overlap_record_has_one_question_in_both_sets_and_one_in_neither():
    """data-model.md, the same table: `hxa-002` is in both sets; `hxa-004` is in neither."""
    overlap = {question["id"] for question in read_set("harness-half-rest-overlap")["questions"]}
    assert overlap & set(HALF) == {"hxa-002"}
    assert set(ALL_OF_HARNESS) - set(HALF) - overlap == {"hxa-004"}


@pytest.mark.parametrize(
    ("version", "sound"),
    [
        ("harness-one-less", "harness"),
        ("harness-one-more", "harness"),
        ("harness-other-gold", "harness"),
        ("harness-half-swapped", "harness-half"),
        ("harness-half-rest-overlap", "harness-half-rest"),
    ],
)
def test_a_defective_set_record_is_otherwise_its_sound_counterpart(version, sound):
    """data-model.md: "Apart from what the table states, a defective record is its sound
    counterpart": the role, the dataset and the rule are the same."""
    defective, counterpart = read_set(version), read_set(sound)
    for field in ("role", "dataset", "rule"):
        assert defective[field] == counterpart[field], field
    assert defective["questions"] != counterpart["questions"]


# =============================================================================================
# tests/data/runs/ (T007)
# =============================================================================================

RUN_A = "20261101T100000Z-example-a"
RUN_B = "20261102T100000Z-example-b"
RUN_C = "20261103T100000Z-example-c"
RUN_D = "20261104T100000Z-example-d"
SOUND_RUNS = (RUN_A, RUN_B, RUN_C, RUN_D)
SET_OF_RUN = {RUN_A: "harness", RUN_B: "harness", RUN_C: "harness-hxc", RUN_D: "harness-hxc"}
RUN_FILES = ["results.jsonl", "run.json", "summary.json"]

MODEL = "example-model"
STATUSES = ("answered", "no_answer", "error", "timeout", "call_limit")
ENTRY_FIELDS = [
    "question_id",
    "status",
    "retrieved_list",
    "generation_list",
    "context",
    "answer",
    "answer_sha256",
    "tokens",
    "cost_usd",
    "latency_seconds",
]

# data-model.md, "**`example-a`**: the table of the spec": question -> status, retrieved
# list, generation list, latency, (input tokens, output tokens) or None, cost.
ENTRIES_A = {
    "hxa-001": (
        "answered",
        ["hx-001", "hx-002", "hx-003"],
        ["hx-001", "hx-002"],
        1.0,
        (1000, 100),
        0.0012,
    ),
    "hxa-002": (
        "answered",
        ["hx-003", "hx-002", "hx-001"],
        ["hx-003", "hx-001"],
        2.0,
        (1000, 100),
        0.0012,
    ),
    "hxa-003": (
        "answered",
        ["hx-001", "hx-004", "hx-001"],
        ["hx-001", "hx-004"],
        3.0,
        (2000, 200),
        0.0024,
    ),
    "hxa-004": (
        "no_answer",
        ["hx-002", "hx-003", "hx-005", "hx-004"],
        ["hx-002", "hx-003", "hx-005"],
        4.0,
        (2000, 50),
        0.0021,
    ),
    "hxa-005": ("error", None, None, 5.0, None, 0.0),
    "hxb-001": ("timeout", ["hx-004", "hx-005"], None, 30.0, (500, 0), 0.0005),
    "hxb-002": ("call_limit", ["hx-003"], [], 7.0, (3000, 300), 0.0036),
    "hxb-003": (
        "answered",
        ["hx-006", "hx-001"],
        ["hx-006", "hx-001"],
        8.0,
        (1500, 150),
        0.0018,
    ),
}
# data-model.md, "**`example-b`**: as `example-a`, with ... these five entries changed".
ENTRIES_B = ENTRIES_A | {
    "hxa-002": (
        "answered",
        ["hx-003", "hx-002", "hx-001"],
        ["hx-002", "hx-003"],
        2.0,
        (1000, 100),
        0.0012,
    ),
    "hxa-003": (
        "answered",
        ["hx-001", "hx-003", "hx-004"],
        ["hx-003", "hx-001"],
        3.0,
        (2000, 200),
        0.0024,
    ),
    "hxa-004": (
        "answered",
        ["hx-002", "hx-003", "hx-005", "hx-004"],
        ["hx-002", "hx-003", "hx-005"],
        4.0,
        (2000, 50),
        0.0021,
    ),
    "hxa-005": ("answered", ["hx-005"], ["hx-005"], 5.0, (1000, 100), 0.0012),
    "hxb-003": (
        "answered",
        ["hx-006", "hx-002"],
        ["hx-006", "hx-002"],
        8.0,
        (1500, 150),
        0.0018,
    ),
}
# data-model.md, "**`example-c` and `example-d`**".
ENTRIES_C = {
    "hxc-001": ("answered", ["hx-001"], ["hx-001"], 1.0, (1000, 100), 0.0012),
    "hxc-002": ("answered", ["hx-003"], ["hx-003"], 2.0, (1000, 100), 0.0012),
}
ENTRIES_D = {
    "hxc-001": ("answered", ["hx-001"], ["hx-001"], 1.0, (1000, 100), 0.0012),
    "hxc-002": ("answered", ["hx-002"], ["hx-002"], 2.0, (1000, 100), 0.0012),
}
ENTRY_TABLES = {RUN_A: ENTRIES_A, RUN_B: ENTRIES_B, RUN_C: ENTRIES_C, RUN_D: ENTRIES_D}

EXPERIMENT_OF_B = {
    "baseline": RUN_A,
    "parameter": "reranking.enabled",
    "baseline_value": False,
    "value": True,
}

# data-model.md, "The numbers of the four summaries", copied. One breakdown: questions; the
# five status counts; the generation list and the retrieved list, each as questions,
# mean_share_found, all_found, share_all_found; the cost as total, per question; the latency
# as median, p95.
NO_QUESTIONS = (
    0,
    (0, 0, 0, 0, 0),
    (0, None, 0, None),
    (0, None, 0, None),
    (0.0, None),
    (None,) * 2,
)
SUMMARY_TABLE = {
    RUN_A: {
        "all": (
            8,
            (4, 1, 1, 1, 1),
            (6, 0.5277777777777778, 2, 0.3333333333333333),
            (7, 0.7857142857142857, 5, 0.7142857142857143),
            (0.0128, 0.0016),
            (4.5, 30.0),
        ),
        "single_article": (
            4,
            (2, 0, 1, 0, 1),
            (3, 0.3333333333333333, 1, 0.3333333333333333),
            (3, 0.6666666666666666, 2, 0.6666666666666666),
            (0.006, 0.0015),
            (3.5, 7.0),
        ),
        "multi_article": (
            4,
            (2, 1, 0, 1, 0),
            (3, 0.7222222222222222, 1, 0.3333333333333333),
            (4, 0.875, 3, 0.75),
            (0.0068, 0.0017),
            (6.0, 30.0),
        ),
    },
    RUN_B: {
        "all": (
            8,
            (6, 0, 0, 1, 1),
            (7, 0.7380952380952381, 4, 0.5714285714285714),
            (8, 0.8125, 6, 0.75),
            (0.014, 0.00175),
            (4.5, 30.0),
        ),
        "single_article": (
            4,
            (3, 0, 0, 0, 1),
            (4, 0.75, 3, 0.75),
            (4, 0.75, 3, 0.75),
            (0.0072, 0.0018),
            (3.5, 7.0),
        ),
        "multi_article": (
            4,
            (3, 0, 0, 1, 0),
            (3, 0.7222222222222222, 1, 0.3333333333333333),
            (4, 0.875, 3, 0.75),
            (0.0068, 0.0017),
            (6.0, 30.0),
        ),
    },
    RUN_C: {
        "all": (
            2,
            (2, 0, 0, 0, 0),
            (2, 0.5, 1, 0.5),
            (2, 0.5, 1, 0.5),
            (0.0024, 0.0012),
            (1.5, 2.0),
        ),
        "single_article": (
            2,
            (2, 0, 0, 0, 0),
            (2, 0.5, 1, 0.5),
            (2, 0.5, 1, 0.5),
            (0.0024, 0.0012),
            (1.5, 2.0),
        ),
        "multi_article": NO_QUESTIONS,
    },
    RUN_D: {
        "all": (
            2,
            (2, 0, 0, 0, 0),
            (2, 1.0, 2, 1.0),
            (2, 1.0, 2, 1.0),
            (0.0024, 0.0012),
            (1.5, 2.0),
        ),
        "single_article": (
            2,
            (2, 0, 0, 0, 0),
            (2, 1.0, 2, 1.0),
            (2, 1.0, 2, 1.0),
            (0.0024, 0.0012),
            (1.5, 2.0),
        ),
        "multi_article": NO_QUESTIONS,
    },
}
RETRIEVAL_MISSES = {
    RUN_A: ["hxa-002", "hxa-003", "hxa-004", "hxb-002"],
    RUN_B: ["hxa-004", "hxb-002", "hxb-003"],
    RUN_C: ["hxc-002"],
    RUN_D: [],
}


def run_directories(registry: Path) -> list[str]:
    return sorted(entry.name for entry in registry.iterdir())


def read_run(registry: Path, run: str) -> tuple[dict, list[dict], dict]:
    """The three documents of a run record: `run.json`, the entries, `summary.json`."""
    folder = registry / run
    return (
        read_json(folder / "run.json"),
        read_rows(folder / "results.jsonl"),
        read_json(folder / "summary.json"),
    )


def started_at_of(run: str) -> str:
    """data-model.md, "Run identifier": the time part `20261101T100000Z` of an identifier,
    in the form of `started_at`, `2026-11-01T10:00:00Z`."""
    time = re.fullmatch(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z-[a-z0-9-]+", run)
    assert time, f"{run} does not have the form of a run identifier"
    year, month, day, hour, minute, second = time.groups()
    return f"{year}-{month}-{day}T{hour}:{minute}:{second}Z"


def set_reference(version: str) -> dict:
    """`version`, `role` and `fingerprint` of a question set, from the record's file."""
    return {
        "version": version,
        "role": read_set(version)["role"],
        "fingerprint": fingerprint(SETS / f"{version}.json"),
    }


def expected_run_document(run: str, version: str) -> dict:
    """contracts/records.md, the `run.json` of `example-a`, for a run and a question set."""
    return {
        "run_id": run,
        "started_at": started_at_of(run),
        "commit": "0123456789abcdef0123456789abcdef01234567",
        "uncommitted_changes": False,
        "config": {
            "dataset": {"name": "harness", "revision": None},
            "question_set": set_reference(version),
            "index": "harness",
            "models": {"generation": "example-model"},
            "prompts": {"generation": "Answer from the context only."},
            "retrieval": {"top_k": 3},
            "reranking": {"enabled": False},
            "context": {"max_articles": 2},
            "limits": {"timeout_seconds": 20, "max_calls": 4},
            "seeds": {},
            "concurrency": 1,
            "prices": [
                {
                    "model": "example-model",
                    "usd_per_million_input_tokens": 1.0,
                    "usd_per_million_output_tokens": 2.0,
                }
            ],
            "experiment": None,
        },
    }


def exact(number) -> Fraction:
    """A number of a record as the decimal number that its JSON text states (research.md,
    section 7): `0.02` is 2/100."""
    return Fraction(str(number))


def entry_cost(tokens: list[dict], prices: list[dict]) -> Fraction:
    """data-model.md, `cost_usd`: the sum over `tokens` of input tokens x the input price /
    1,000,000 plus output tokens x the output price / 1,000,000, computed exactly."""
    price = {entry["model"]: entry for entry in prices}
    total = Fraction(0)
    for count in tokens:
        of_model = price[count["model"]]
        total += count["input_tokens"] * exact(of_model["usd_per_million_input_tokens"]) / 10**6
        total += count["output_tokens"] * exact(of_model["usd_per_million_output_tokens"]) / 10**6
    return total


def as_number(value: Fraction | None) -> float | None:
    """research.md, section 7: turned into a floating-point number once, at the end."""
    return None if value is None else float(value)


def list_numbers(pairs: list[tuple[list[str], dict]], name: str) -> dict:
    """data-model.md, "The four numbers of a list in a breakdown": over the questions that
    have a gold article and for which the list exists."""
    shares = []
    for article_ids, entry in pairs:
        gold = set(article_ids)
        if gold and entry[name] is not None:
            shares.append(Fraction(len(gold & set(entry[name])), len(gold)))
    all_found = sum(1 for share in shares if share == 1)
    return {
        "questions": len(shares),
        "mean_share_found": as_number(sum(shares) / len(shares)) if shares else None,
        "all_found": all_found,
        "share_all_found": as_number(Fraction(all_found, len(shares))) if shares else None,
    }


def breakdown(pairs: list[tuple[list[str], dict]], prices: list[dict]) -> dict:
    """data-model.md, "One breakdown" and "The numbers, defined", computed with exact
    fractions from the entries: the cost from the tokens, the median, and the 95th
    percentile as the value at position ceil(0.95 x n), counted from 1."""
    count = len(pairs)
    total = sum((entry_cost(entry["tokens"], prices) for _, entry in pairs), Fraction(0))
    latencies = sorted(exact(entry["latency_seconds"]) for _, entry in pairs)
    median = p95 = None
    if count:
        middle = count // 2
        median = latencies[middle]
        if count % 2 == 0:
            median = (latencies[middle - 1] + latencies[middle]) / 2
        p95 = latencies[-(-95 * count // 100) - 1]
    return {
        "questions": count,
        "status": {
            status: sum(1 for _, entry in pairs if entry["status"] == status) for status in STATUSES
        },
        "generation_list": list_numbers(pairs, "generation_list"),
        "retrieved_list": list_numbers(pairs, "retrieved_list"),
        "cost_usd": {
            "total": float(total),
            "per_question": as_number(total / count if count else None),
        },
        "latency_seconds": {"median": as_number(median), "p95": as_number(p95)},
    }


def recomputed_numbers(version: str, entries: list[dict], prices: list[dict]) -> dict:
    """The three derived keys of `summary.json`, from the question-set record and the
    entries (data-model.md, "Summary")."""
    questions = read_set(version)["questions"]
    assert [entry["question_id"] for entry in entries] == [question["id"] for question in questions]
    pairs = [
        (question["article_ids"], entry) for question, entry in zip(questions, entries, strict=True)
    ]
    misses = [
        entry["question_id"]
        for article_ids, entry in pairs
        if article_ids
        and entry["generation_list"] is not None
        and not set(article_ids) <= set(entry["generation_list"])
    ]
    return {
        "breakdowns": {
            "all": breakdown(pairs, prices),
            "single_article": breakdown([pair for pair in pairs if len(set(pair[0])) == 1], prices),
            "multi_article": breakdown([pair for pair in pairs if len(set(pair[0])) >= 2], prices),
        },
        "retrieval_misses": misses,
        "questions_without_gold_articles": sum(1 for article_ids, _ in pairs if not article_ids),
    }


def breakdown_of_the_table(row: tuple) -> dict:
    """One row of the table of the summaries as the object of `summary.json`."""
    questions, status, generation, retrieved, cost, latency = row
    names = ("questions", "mean_share_found", "all_found", "share_all_found")
    return {
        "questions": questions,
        "status": dict(zip(STATUSES, status, strict=True)),
        "generation_list": dict(zip(names, generation, strict=True)),
        "retrieved_list": dict(zip(names, retrieved, strict=True)),
        "cost_usd": {"total": cost[0], "per_question": cost[1]},
        "latency_seconds": {"median": latency[0], "p95": latency[1]},
    }


def expected_audit(version: str, audited_at: str) -> dict:
    """contracts/records.md, the `audit` of the `summary.json` of `example-a`: the audit
    result of spec 1 with the three fields of an audit with `--set`, written by hand with
    the outcome `passed`, for the index `harness` and the run's question set."""
    record = read_set(version)
    return {
        "index": "harness",
        "dataset": {"name": "harness", "revision": None},
        "question_set": {
            "description": f"question set {version} ({record['role']})",
            "parts": [part["name"] for part in record["dataset"]["parts"]],
            "questions": record["count"],
            **set_reference(version),
        },
        "articles_in_corpus": 6,
        "articles_in_index": 6,
        "missing_from_index": [],
        "not_in_corpus": [],
        "unknown_references": [],
        "questions_without_article_ids": 0,
        "outcome": "passed",
        "audited_at": audited_at,
    }


def test_the_registry_holds_the_four_sound_records():
    """tasks.md, T007: four records, each with `run.json`, `results.jsonl`, `summary.json`."""
    assert run_directories(RUNS) == sorted(SOUND_RUNS)
    for run in SOUND_RUNS:
        assert sorted(entry.name for entry in (RUNS / run).iterdir()) == RUN_FILES


@pytest.mark.parametrize("run", SOUND_RUNS)
def test_run_id_is_the_name_of_the_directory_and_agrees_with_started_at(run):
    """data-model.md, `run.json`: `run_id` equals the name of the directory, and
    `started_at` agrees with its time part. The summary names the same run."""
    document, _, summary = read_run(RUNS, run)
    assert document["run_id"] == run
    assert document["started_at"] == started_at_of(run)
    assert summary["run_id"] == run


@pytest.mark.parametrize("run", SOUND_RUNS)
def test_the_fingerprint_of_the_question_set_is_the_sha256_of_the_file_of_the_set(run):
    """tasks.md, T009: in every run record the fingerprint of the question set is the SHA-256
    of the set's file. It stands in the config, in the summary and in the audit result; the
    role is that of the set's record."""
    document, _, summary = read_run(RUNS, run)
    expected = {
        "version": SET_OF_RUN[run],
        "role": read_set(SET_OF_RUN[run])["role"],
        "fingerprint": sha256((SETS / f"{SET_OF_RUN[run]}.json").read_bytes()),
    }
    assert document["config"]["question_set"] == expected
    assert summary["question_set"] == expected
    for field, value in expected.items():
        assert summary["audit"]["question_set"][field] == value


def test_run_json_of_example_a_is_the_document_of_the_contract():
    """contracts/records.md, "`run.json`: identity and config": the document shown there,
    with the fingerprint of `harness.json` computed here; the keys in the same order."""
    document = read_json(RUNS / RUN_A / "run.json")
    expected = expected_run_document(RUN_A, "harness")
    assert document == expected
    assert canonical(document) == canonical(expected), "the keys stand in the order of the contract"


def test_run_json_of_example_b_differs_from_example_a_in_one_parameter():
    """data-model.md: `example-b` names `example-a` as its baseline and the parameter
    `reranking.enabled`, `false` -> `true`. contracts/records.md gives its
    `config.experiment`. Nothing else of the config differs."""
    expected = expected_run_document(RUN_B, "harness")
    expected["config"]["reranking"]["enabled"] = True
    expected["config"]["experiment"] = EXPERIMENT_OF_B

    assert read_json(RUNS / RUN_B / "run.json") == expected


@pytest.mark.parametrize("run", [RUN_C, RUN_D])
def test_run_json_of_a_run_on_the_held_out_set_names_no_baseline(run):
    """data-model.md: `example-c` and `example-d` are on `harness-hxc` and are not
    experiments; what the four runs share is as in `example-a`."""
    document = read_json(RUNS / run / "run.json")
    assert document == expected_run_document(run, "harness-hxc")
    assert document["config"]["question_set"]["role"] == "held-out"
    assert document["config"]["experiment"] is None


@pytest.mark.parametrize("run", SOUND_RUNS)
def test_the_config_has_the_thirteen_fields_and_one_price_for_the_model(run):
    """data-model.md, "Identity and config": all thirteen fields are required. "Shared by the
    four runs": the index `harness`, the dataset `harness` without a revision, and one model
    at 1.00 and 2.00 US dollars per million input and output tokens."""
    config = read_json(RUNS / run / "run.json")["config"]
    assert list(config) == [
        "dataset",
        "question_set",
        "index",
        "models",
        "prompts",
        "retrieval",
        "reranking",
        "context",
        "limits",
        "seeds",
        "concurrency",
        "prices",
        "experiment",
    ]
    assert config["index"] == "harness"
    assert config["dataset"] == {"name": "harness", "revision": None}
    assert config["prices"] == [
        {
            "model": MODEL,
            "usd_per_million_input_tokens": 1.0,
            "usd_per_million_output_tokens": 2.0,
        }
    ]


@pytest.mark.parametrize("run", SOUND_RUNS)
def test_the_results_have_one_entry_per_question_in_the_order_of_the_set(run):
    """contracts/records.md, "`results.jsonl`": one JSON object per line, one line per
    question of the run's question set, in the order of the set, with the ten fields."""
    lines = (RUNS / run / "results.jsonl").read_text(encoding="utf-8").split("\n")
    assert lines[-1] == "" and all(lines[:-1]), "every line is an entry, each ended by a line feed"
    entries = [json.loads(line) for line in lines[:-1]]

    questions = [question["id"] for question in read_set(SET_OF_RUN[run])["questions"]]
    assert [entry["question_id"] for entry in entries] == questions
    for entry in entries:
        assert list(entry) == ENTRY_FIELDS


@pytest.mark.parametrize("run", SOUND_RUNS)
def test_the_entries_are_those_of_the_tables(run):
    """data-model.md, the tables of the entries of the four runs: status, both lists,
    latency, token counts and cost of every question."""
    _, entries, _ = read_run(RUNS, run)
    table = ENTRY_TABLES[run]
    assert [entry["question_id"] for entry in entries] == list(table)

    for entry in entries:
        status, retrieved, generation, latency, tokens, cost = table[entry["question_id"]]
        expected_tokens = (
            []
            if tokens is None
            else [{"model": MODEL, "input_tokens": tokens[0], "output_tokens": tokens[1]}]
        )
        assert entry["status"] == status, entry["question_id"]
        assert entry["retrieved_list"] == retrieved, entry["question_id"]
        assert entry["generation_list"] == generation, entry["question_id"]
        assert entry["latency_seconds"] == latency, entry["question_id"]
        assert entry["tokens"] == expected_tokens, entry["question_id"]
        assert entry["cost_usd"] == cost, entry["question_id"]


@pytest.mark.parametrize("run", SOUND_RUNS)
def test_every_answer_sha256_is_the_hash_of_its_answer(run):
    """data-model.md, `answer_sha256`: the SHA-256 of the UTF-8 bytes of `answer`; `null`
    exactly when `answer` is `null`."""
    _, entries, _ = read_run(RUNS, run)
    for entry in entries:
        if entry["answer"] is None:
            assert entry["answer_sha256"] is None, entry["question_id"]
        else:
            assert type(entry["answer"]) is str and entry["answer"]
            assert entry["answer_sha256"] == sha256(entry["answer"].encode("utf-8")), entry[
                "question_id"
            ]


@pytest.mark.parametrize("run", SOUND_RUNS)
def test_every_cost_usd_follows_from_the_tokens_and_the_prices(run):
    """data-model.md, `cost_usd`, and research.md, section 7: the exact cost of the tokens at
    the prices of the config, turned into a floating-point number once."""
    document, entries, _ = read_run(RUNS, run)
    prices = document["config"]["prices"]
    for entry in entries:
        assert type(entry["cost_usd"]) is float, entry["question_id"]
        assert entry["cost_usd"] == float(entry_cost(entry["tokens"], prices)), entry["question_id"]


@pytest.mark.parametrize("run", SOUND_RUNS)
def test_the_entries_keep_the_rules_across_fields(run):
    """data-model.md, "Rules across fields": a question with the status `answered` or
    `no_answer` has both lists and an answer; a question with a generation list has a
    retrieved list. data-model.md, `example-a`: the entries of `hxa-005`, `hxb-001` and
    `hxb-002` have no context, no answer and no hash; the others have a context and an
    answer."""
    _, entries, _ = read_run(RUNS, run)
    for entry in entries:
        if entry["status"] in ("answered", "no_answer"):
            assert entry["retrieved_list"] is not None, entry["question_id"]
            assert entry["generation_list"] is not None, entry["question_id"]
            assert type(entry["context"]) is str and entry["context"], entry["question_id"]
            assert type(entry["answer"]) is str and entry["answer"], entry["question_id"]
        else:
            assert entry["context"] is None, entry["question_id"]
            assert entry["answer"] is None, entry["question_id"]
            assert entry["answer_sha256"] is None, entry["question_id"]
        if entry["generation_list"] is not None:
            assert entry["retrieved_list"] is not None, entry["question_id"]


def test_the_untouched_entries_of_example_b_are_those_of_example_a():
    """data-model.md, `example-b`: "as `example-a`, with ... these five entries changed"."""
    lines_a = (RUNS / RUN_A / "results.jsonl").read_bytes().split(b"\n")
    lines_b = (RUNS / RUN_B / "results.jsonl").read_bytes().split(b"\n")
    changed = [
        json.loads(first)["question_id"]
        for first, second in zip(lines_a[:-1], lines_b[:-1], strict=True)
        if first != second
    ]
    assert changed == ["hxa-002", "hxa-003", "hxa-004", "hxa-005", "hxb-003"]


def test_an_answer_of_the_example_is_not_plain_ascii():
    """A hash is taken of the UTF-8 bytes of an answer, and a record writes non-ASCII
    characters as they are: one answer of `example-a` holds a character of several bytes."""
    data = (RUNS / RUN_A / "results.jsonl").read_bytes()
    answers = [entry["answer"] for entry in read_rows(RUNS / RUN_A / "results.jsonl")]
    assert any(answer and not answer.isascii() for answer in answers)
    assert b"\\u" not in data


@pytest.mark.parametrize("run", SOUND_RUNS)
def test_the_summary_has_the_numbers_that_the_results_give(run):
    """data-model.md, "Summary": derived from the two other files and the question-set
    record. The breakdowns, the retrieval misses and the number of questions without gold
    articles are computed here from the entries, with exact fractions, and compared for
    equality (research.md, section 7)."""
    document, entries, summary = read_run(RUNS, run)
    recomputed = recomputed_numbers(SET_OF_RUN[run], entries, document["config"]["prices"])

    for key, value in recomputed.items():
        assert summary[key] == value, key
    assert summary["questions"] == len(entries)


@pytest.mark.parametrize("run", SOUND_RUNS)
@pytest.mark.parametrize("name", ["all", "single_article", "multi_article"])
def test_a_breakdown_of_the_summary_has_the_numbers_of_the_table(run, name):
    """data-model.md, "The numbers of the four summaries": every number of the table. A
    number over no question is `null`, except a total cost, which is `0.0`."""
    summary = read_json(RUNS / run / "summary.json")
    assert summary["breakdowns"][name] == breakdown_of_the_table(SUMMARY_TABLE[run][name])


@pytest.mark.parametrize("run", SOUND_RUNS)
def test_the_summary_lists_the_retrieval_misses_of_the_table(run):
    """data-model.md, the table of `retrieval_misses`; `questions_without_gold_articles` is 0
    in all four."""
    summary = read_json(RUNS / run / "summary.json")
    assert summary["retrieval_misses"] == RETRIEVAL_MISSES[run]
    assert summary["questions_without_gold_articles"] == 0


@pytest.mark.parametrize("run", SOUND_RUNS)
def test_the_summary_is_the_whole_document_of_the_contract(run):
    """contracts/records.md, "`summary.json`": the fields in the order of the document shown
    for `example-a`, written with an indentation of two spaces and a final line feed; the
    audit result has the form of spec 1 with the three fields of an audit with `--set`, the
    outcome `passed`, the index `harness` and the run's question set."""
    data = (RUNS / run / "summary.json").read_bytes()
    summary = json.loads(data)
    version = SET_OF_RUN[run]
    expected = {
        "run_id": run,
        "question_set": set_reference(version),
        "questions": read_set(version)["count"],
        "audit": expected_audit(version, summary["audit"]["audited_at"]),
        "breakdowns": {
            name: breakdown_of_the_table(row) for name, row in SUMMARY_TABLE[run].items()
        },
        "retrieval_misses": RETRIEVAL_MISSES[run],
        "questions_without_gold_articles": 0,
    }

    assert summary == expected
    assert data == canonical(expected), "the keys in the order of the contract, canonical form"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", summary["audit"]["audited_at"])
    assert summary["audit"]["audited_at"] < read_json(RUNS / run / "run.json")["started_at"], (
        "the audit is the gate before the run"
    )


def test_the_audit_of_example_a_is_the_one_of_the_contract():
    """contracts/records.md, the `summary.json` of `example-a`: audited at
    `2026-11-01T09:59:00Z`, the parts `hxa` and `hxb`, eight questions."""
    audit = read_json(RUNS / RUN_A / "summary.json")["audit"]
    assert audit["audited_at"] == "2026-11-01T09:59:00Z"
    assert audit["question_set"]["description"] == "question set harness (golden)"
    assert audit["question_set"]["parts"] == ["hxa", "hxb"]
    assert audit["question_set"]["questions"] == 8


@pytest.mark.parametrize(
    ("first", "second", "compared", "left_out", "gained", "lost"),
    [
        (RUN_A, RUN_B, 6, ["hxa-005", "hxb-001"], ["hxa-002", "hxa-003"], ["hxb-003"]),
        (RUN_C, RUN_D, 2, [], ["hxc-002"], []),
    ],
)
def test_the_comparisons_of_the_table_follow_from_the_records(
    first, second, compared, left_out, gained, lost
):
    """data-model.md, "The comparisons" and "Pairwise comparison": the outcome of a question
    is `all_found` on the generation list; a question without a generation list in either
    run is left out."""
    questions = read_set(SET_OF_RUN[first])["questions"]
    _, first_entries, _ = read_run(RUNS, first)
    _, second_entries, _ = read_run(RUNS, second)
    found = {"left out": [], "gained": [], "lost": [], "compared": 0}
    for question, one, two in zip(questions, first_entries, second_entries, strict=True):
        gold = set(question["article_ids"])
        if not gold or one["generation_list"] is None or two["generation_list"] is None:
            found["left out"].append(question["id"])
            continue
        found["compared"] += 1
        before = gold <= set(one["generation_list"])
        after = gold <= set(two["generation_list"])
        if after and not before:
            found["gained"].append(question["id"])
        if before and not after:
            found["lost"].append(question["id"])

    assert found == {"left out": left_out, "gained": gained, "lost": lost, "compared": compared}


# =============================================================================================
# tests/data/runs-invalid/ (T008)
# =============================================================================================

NO_LATENCY = "20261101T100100Z-no-latency"
MISSING_QUESTION = "20261101T100200Z-missing-question"
UNKNOWN_STATUS = "20261101T100300Z-unknown-status"
WRONG_HASH = "20261101T100400Z-wrong-hash"
STALE_SUMMARY = "20261101T100500Z-stale-summary"
TWO_CHANGES = "20261101T100600Z-two-changes"
EXPERIMENT_ON_HELD_OUT = "20261103T100100Z-experiment-on-held-out"

# data-model.md, the table of the seven records: run -> the record it is made from.
MADE_FROM = {
    NO_LATENCY: RUN_A,
    MISSING_QUESTION: RUN_A,
    UNKNOWN_STATUS: RUN_A,
    WRONG_HASH: RUN_A,
    STALE_SUMMARY: RUN_A,
    TWO_CHANGES: RUN_A,
    EXPERIMENT_ON_HELD_OUT: RUN_C,
}
DEFECTIVE_RUNS = tuple(MADE_FROM)
COPIED_RUNS = (RUN_A, RUN_C)


def with_identity(document: dict, run: str) -> dict:
    """The `run.json` of the source with the `run_id` and the `started_at` of another run."""
    changed = copy.deepcopy(document)
    changed["run_id"] = run
    changed["started_at"] = started_at_of(run)
    return changed


def test_the_invalid_registry_holds_nine_records():
    """tasks.md, T008: the two sound records and the seven records with one defect each,
    every one with its three files."""
    assert run_directories(RUNS_INVALID) == sorted([*COPIED_RUNS, *DEFECTIVE_RUNS])
    for run in run_directories(RUNS_INVALID):
        assert sorted(entry.name for entry in (RUNS_INVALID / run).iterdir()) == RUN_FILES


@pytest.mark.parametrize("run", COPIED_RUNS)
@pytest.mark.parametrize("file", RUN_FILES)
def test_a_sound_record_of_the_invalid_registry_has_the_bytes_of_the_registry(run, file):
    """data-model.md: "Two sound records, byte for byte the records of `tests/data/runs/`"."""
    assert (RUNS_INVALID / run / file).read_bytes() == (RUNS / run / file).read_bytes()


@pytest.mark.parametrize("run", DEFECTIVE_RUNS)
def test_a_defective_record_has_its_own_run_id_and_started_at(run):
    """data-model.md: "A defective record has its own `run_id` and `started_at`, in all three
    files where they occur": `run.json` and `summary.json`. The identifier is the name of
    the directory, and no two records of the registry start at the same time."""
    document, _, summary = read_run(RUNS_INVALID, run)
    assert document["run_id"] == run
    assert document["started_at"] == started_at_of(run)
    assert summary["run_id"] == run

    started = [
        read_json(RUNS_INVALID / other / "run.json")["started_at"]
        for other in run_directories(RUNS_INVALID)
    ]
    assert len(set(started)) == 9


@pytest.mark.parametrize("run", [NO_LATENCY, MISSING_QUESTION, UNKNOWN_STATUS, WRONG_HASH])
def test_a_record_with_a_defect_in_its_results_keeps_run_json_and_the_summary(run):
    """data-model.md: such a record "is otherwise the record it is made from", and its
    summary is left as the summary of that record, with the new `run_id`."""
    source_document, _, source_summary = read_run(RUNS, MADE_FROM[run])
    document, _, summary = read_run(RUNS_INVALID, run)

    assert document == with_identity(source_document, run)
    assert summary == source_summary | {"run_id": run}


@pytest.mark.parametrize("run", [STALE_SUMMARY, TWO_CHANGES, EXPERIMENT_ON_HELD_OUT])
def test_a_record_with_a_defect_outside_its_results_keeps_the_results(run):
    """data-model.md: the results of `stale-summary`, `two-changes` and
    `experiment-on-held-out` are those of the record each is made from, byte for byte."""
    assert (RUNS_INVALID / run / "results.jsonl").read_bytes() == (
        RUNS / MADE_FROM[run] / "results.jsonl"
    ).read_bytes()


def result_lines(registry: Path, run: str) -> list[bytes]:
    return (registry / run / "results.jsonl").read_bytes().split(b"\n")[:-1]


def the_one_changed_line(run: str) -> tuple[dict, dict]:
    """The entry of the source and the entry of the defective record, for the one line of
    `results.jsonl` in which the two differ."""
    source, defective = result_lines(RUNS, MADE_FROM[run]), result_lines(RUNS_INVALID, run)
    assert len(source) == len(defective)
    changed = [
        (json.loads(a), json.loads(b)) for a, b in zip(source, defective, strict=True) if a != b
    ]
    assert len(changed) == 1, "exactly one entry differs"
    return changed[0]


def test_no_latency_lacks_the_latency_of_hxa_003_and_nothing_else():
    """data-model.md: "The entry of `hxa-003` has no field `latency_seconds`"."""
    source, defective = the_one_changed_line(NO_LATENCY)
    assert defective["question_id"] == "hxa-003"
    assert "latency_seconds" not in defective
    assert defective | {"latency_seconds": source["latency_seconds"]} == source


def test_missing_question_has_no_line_for_hxb_003_and_nothing_else():
    """data-model.md: "`results.jsonl` has no line for `hxb-003`"; it is the last question
    of the set, and the seven other lines are those of `example-a`."""
    source, defective = result_lines(RUNS, RUN_A), result_lines(RUNS_INVALID, MISSING_QUESTION)
    assert json.loads(source[-1])["question_id"] == "hxb-003"
    assert defective == source[:-1]


def test_unknown_status_has_the_status_skipped_for_hxa_004_and_nothing_else():
    """data-model.md: "The status of `hxa-004` is `skipped`"."""
    source, defective = the_one_changed_line(UNKNOWN_STATUS)
    assert defective["question_id"] == "hxa-004"
    assert defective == source | {"status": "skipped"}
    assert "skipped" not in STATUSES


def test_wrong_hash_has_64_zeros_for_hxa_001_and_nothing_else():
    """data-model.md: "`answer_sha256` of `hxa-001` is 64 zeros"; this is the one entry of
    the example data whose hash is not the hash of its answer."""
    source, defective = the_one_changed_line(WRONG_HASH)
    assert defective["question_id"] == "hxa-001"
    assert defective == source | {"answer_sha256": "0" * 64}
    assert defective["answer_sha256"] != sha256(defective["answer"].encode("utf-8"))


@pytest.mark.parametrize("run", [run for run in DEFECTIVE_RUNS if run != WRONG_HASH])
def test_every_other_answer_sha256_of_the_invalid_registry_is_the_hash_of_its_answer(run):
    """tasks.md, T009: every `answer_sha256` is the hash of its answer except in
    `wrong-hash`."""
    for entry in read_rows(RUNS_INVALID / run / "results.jsonl"):
        expected = None if entry["answer"] is None else sha256(entry["answer"].encode("utf-8"))
        assert entry["answer_sha256"] == expected, entry["question_id"]


@pytest.mark.parametrize("run", DEFECTIVE_RUNS)
def test_every_cost_usd_of_the_invalid_registry_follows_from_the_tokens_and_the_prices(run):
    """tasks.md, T009: every `cost_usd` follows from the tokens and the prices. No defect of
    the table touches a cost."""
    document, entries, _ = read_run(RUNS_INVALID, run)
    for entry in entries:
        expected = float(entry_cost(entry["tokens"], document["config"]["prices"]))
        assert entry["cost_usd"] == expected, entry["question_id"]


@pytest.mark.parametrize("run", DEFECTIVE_RUNS)
def test_the_fingerprint_of_the_question_set_holds_in_the_invalid_registry(run):
    """tasks.md, T009: in every run record the fingerprint of the question set is the SHA-256
    of the set's file. No defect of the table touches the question set of a record."""
    document, _, summary = read_run(RUNS_INVALID, run)
    version = SET_OF_RUN[MADE_FROM[run]]
    assert document["config"]["question_set"] == set_reference(version)
    assert summary["question_set"] == set_reference(version)
    assert summary["audit"] == read_json(RUNS / MADE_FROM[run] / "summary.json")["audit"]


def test_stale_summary_states_3_where_the_results_give_2_and_nothing_else():
    """data-model.md: "`breakdowns.all.generation_list.all_found` is 3"; the results give 2."""
    source_document, _, source_summary = read_run(RUNS, RUN_A)
    document, entries, summary = read_run(RUNS_INVALID, STALE_SUMMARY)

    expected = copy.deepcopy(source_summary) | {"run_id": STALE_SUMMARY}
    assert expected["breakdowns"]["all"]["generation_list"]["all_found"] == 2
    expected["breakdowns"]["all"]["generation_list"]["all_found"] = 3
    assert summary == expected
    assert document == with_identity(source_document, STALE_SUMMARY)

    recomputed = recomputed_numbers("harness", entries, document["config"]["prices"])
    assert recomputed["breakdowns"]["all"]["generation_list"]["all_found"] == 2


def test_two_changes_differs_from_its_baseline_in_two_parameters():
    """data-model.md: `config.experiment` names the baseline `example-a` and the parameter
    `reranking.enabled`, `false` -> `true`; `config.reranking.enabled` is `true`, and
    `config.retrieval.top_k` is 4 where the baseline has 3. The baseline is in the same
    registry."""
    source_document, _, source_summary = read_run(RUNS, RUN_A)
    document, _, summary = read_run(RUNS_INVALID, TWO_CHANGES)

    expected = with_identity(source_document, TWO_CHANGES)
    assert expected["config"]["retrieval"]["top_k"] == 3
    expected["config"]["retrieval"]["top_k"] = 4
    expected["config"]["reranking"]["enabled"] = True
    expected["config"]["experiment"] = EXPERIMENT_OF_B
    assert document == expected
    assert summary == source_summary | {"run_id": TWO_CHANGES}
    assert (RUNS_INVALID / RUN_A).is_dir()


def test_experiment_on_held_out_is_an_experiment_on_harness_hxc():
    """data-model.md: `config.experiment` names the baseline `example-c` and the parameter
    `reranking.enabled`, `false` -> `true`; `config.reranking.enabled` is `true`. The run is
    on the held-out set `harness-hxc`, and the baseline is in the same registry."""
    source_document, _, source_summary = read_run(RUNS, RUN_C)
    document, _, summary = read_run(RUNS_INVALID, EXPERIMENT_ON_HELD_OUT)

    expected = with_identity(source_document, EXPERIMENT_ON_HELD_OUT)
    expected["config"]["reranking"]["enabled"] = True
    expected["config"]["experiment"] = EXPERIMENT_OF_B | {"baseline": RUN_C}
    assert document == expected
    assert document["config"]["question_set"]["version"] == "harness-hxc"
    assert document["config"]["question_set"]["role"] == "held-out"
    assert summary == source_summary | {"run_id": EXPERIMENT_ON_HELD_OUT}
    assert (RUNS_INVALID / RUN_C).is_dir()


def test_the_invalid_registry_has_seven_runs_on_golden_sets_and_two_on_held_out_sets():
    """data-model.md: the check of this registry reports `runs: 9`, `failed runs: 7`,
    `runs on golden sets: 7` and `runs on held-out sets: 2`, counted by the
    `config.question_set.role` of every record."""
    roles = [
        read_json(RUNS_INVALID / run / "run.json")["config"]["question_set"]["role"]
        for run in run_directories(RUNS_INVALID)
    ]
    assert len(roles) == 9
    assert roles.count("golden") == 7
    assert roles.count("held-out") == 2


def test_the_registry_has_two_runs_on_golden_sets_and_two_on_held_out_sets():
    """contracts/cli.md, "`run check`", the output for the registry: `runs: 4`,
    `runs on golden sets: 2`, `runs on held-out sets: 2`."""
    roles = [
        read_json(RUNS / run / "run.json")["config"]["question_set"]["role"]
        for run in run_directories(RUNS)
    ]
    assert roles.count("golden") == 2
    assert roles.count("held-out") == 2
