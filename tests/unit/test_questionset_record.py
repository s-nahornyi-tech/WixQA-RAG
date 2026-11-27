"""The record of a question set (task T038): `src/wixqa_rag/questionsets.py`.

Covers:

- spec.md, FR-003 and FR-004, and data-model.md, "Question set" and "Selection rule": the
  record that a rule gives from a data directory, the same on every call, with nothing that
  changes from one production to the next;
- contracts/records.md, "Question-set record": the canonical form and the fingerprint;
- contracts/harness.md, "`wixqa_rag.questionsets`": the names below, and no other.

    record(version, role, rule, data_dir, sets_dir=None) -> dict
        # the document of the record that `set build` would write; it writes nothing
    canonical(document) -> bytes
    read(version, sets_dir=None) -> QuestionSet
    QuestionSet                            # version, role, dataset_name, dataset_revision,
                                           # rule, questions, fingerprint, document
    QuestionSet.pairs()
    QuestionSet.gold(question)
    SetError

`rule` is passed as the document of the rule, exactly as it stands in the record
(`QuestionSet.rule`, "the document of the rule"): for a draw `kind`, `method`, `seed` and
`take`; for a complement `kind`, `of` and `of_fingerprint`.

The expected bytes are the four records of `tests/data/sets/` that pass their check; they
were written by hand, and tests/unit/test_harness_example_data.py shows without code of the
package that they are what the documents state. All documents named here are in
specs/002-evaluation-harness/.
"""

import hashlib
import importlib
import json
import shutil
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "data"
HARNESS = DATA / "harness"
SETS = DATA / "sets"

# The four sound records of the harness data: version -> role (data-model.md, "Example data").
SOUND = {
    "harness": "golden",
    "harness-hxc": "held-out",
    "harness-half": "golden",
    "harness-half-rest": "held-out",
}


def load_questionsets():
    """Import the module; it fails while `src/wixqa_rag/questionsets.py` does not exist
    (plan.md, "Project Structure")."""
    return importlib.import_module("wixqa_rag.questionsets")


def recorded_bytes(version: str) -> bytes:
    return (SETS / f"{version}.json").read_bytes()


def recorded(version: str) -> dict:
    return json.loads(recorded_bytes(version))


def record_of(version: str) -> dict:
    """`record` for the rule of an example record, on the harness data."""
    return load_questionsets().record(
        version, SOUND[version], recorded(version)["rule"], HARNESS, SETS
    )


def files_below(directory: Path) -> dict[str, bytes]:
    return {
        file.relative_to(directory).as_posix(): file.read_bytes()
        for file in sorted(directory.rglob("*"))
        if file.is_file()
    }


def write_set(sets_dir: Path, version: str, content: bytes) -> Path:
    sets_dir.mkdir(parents=True, exist_ok=True)
    file = sets_dir / f"{version}.json"
    file.write_bytes(content)
    return file


# --- `record` and `canonical` -----------------------------------------------------------------


@pytest.mark.parametrize("version", SOUND)
def test_record_in_the_canonical_form_gives_the_bytes_of_the_example_record(version):
    """tasks.md, T038: `record` for the rules of `harness`, `harness-hxc`, `harness-half` and
    `harness-half-rest` on `tests/data/harness/`, turned into bytes with `canonical`, gives
    the bytes of the four example records (FR-003; contracts/records.md)."""
    questionsets = load_questionsets()

    assert questionsets.canonical(record_of(version)) == recorded_bytes(version)


@pytest.mark.parametrize("version", SOUND)
def test_record_gives_the_same_bytes_on_a_second_call(version):
    """FR-004: the same dataset, rule and seed give the same record."""
    questionsets = load_questionsets()

    first = questionsets.canonical(record_of(version))
    second = questionsets.canonical(record_of(version))

    assert first == second == recorded_bytes(version)


@pytest.mark.parametrize("version", SOUND)
def test_record_is_the_document_of_the_example_record(version):
    """contracts/harness.md, `record`: "The document of the record": the parsed JSON of the
    file, with the keys in the order of contracts/records.md."""
    document = record_of(version)

    assert document == recorded(version)
    assert list(document) == ["version", "role", "dataset", "rule", "questions", "count"]


def test_record_of_a_draw_selects_by_the_keys_of_the_data_model():
    """data-model.md, the table of the eight draw keys: three of `hxa` and one of `hxb` with
    the seed 7 are `hxa-002`, `hxa-003`, `hxa-005` and `hxb-002`, in the order of the
    dataset, each with its gold article ids as the dataset gives them."""
    document = record_of("harness-half")

    assert document["questions"] == [
        {"id": "hxa-002", "article_ids": ["hx-002"]},
        {"id": "hxa-003", "article_ids": ["hx-001", "hx-003"]},
        {"id": "hxa-005", "article_ids": ["hx-005"]},
        {"id": "hxb-002", "article_ids": ["hx-006"]},
    ]
    assert document["count"] == 4


def test_record_of_a_complement_holds_the_other_questions_of_the_parts():
    """FR-032 and data-model.md, "Selection rule": every question, of the parts that the
    other set draws from, which that set does not hold; `dataset.parts` are those of the
    complemented set, and `of_fingerprint` is the fingerprint of its record."""
    document = record_of("harness-half-rest")

    assert [question["id"] for question in document["questions"]] == [
        "hxa-001",
        "hxa-004",
        "hxb-001",
        "hxb-003",
    ]
    assert document["dataset"]["parts"] == recorded("harness-half")["dataset"]["parts"]
    assert document["rule"] == {
        "kind": "complement",
        "of": "harness-half",
        "of_fingerprint": hashlib.sha256(recorded_bytes("harness-half")).hexdigest(),
    }


@pytest.mark.parametrize("version", SOUND)
def test_record_holds_no_time_no_commit_and_no_path_of_a_machine(version):
    """data-model.md, "Question set", rule 3, and FR-004: the record holds nothing that
    changes from one production to the next. Its fields are exactly those of
    contracts/records.md, and no value names the place of the data or of the sets."""
    document = record_of(version)
    text = load_questionsets().canonical(document).decode("utf-8")

    assert set(document) == {"version", "role", "dataset", "rule", "questions", "count"}
    assert set(document["dataset"]) == {"name", "revision", "parts"}
    for part in document["dataset"]["parts"]:
        assert set(part) == {"name", "rows", "sha256"}
    for question in document["questions"]:
        assert set(question) == {"id", "article_ids"}
    for place in (str(HARNESS), str(SETS), str(DATA), "tests/data"):
        assert place not in text, f"the record names a path: {place}"


def test_record_is_the_same_from_a_copy_of_the_data_in_another_place(tmp_path):
    """FR-004: the record does not depend on the machine: the same files in another
    directory give the same bytes."""
    questionsets = load_questionsets()
    data_dir = tmp_path / "elsewhere" / "the-data"
    sets_dir = tmp_path / "other" / "the-sets"
    shutil.copytree(HARNESS, data_dir)
    shutil.copytree(SETS, sets_dir)

    for version, role in SOUND.items():
        document = questionsets.record(version, role, recorded(version)["rule"], data_dir, sets_dir)
        assert questionsets.canonical(document) == recorded_bytes(version), version


def test_record_writes_nothing(tmp_path):
    """contracts/harness.md, `record`: "It writes nothing"; rule 2: no function changes a
    file that exists."""
    questionsets = load_questionsets()
    data_dir = tmp_path / "harness"
    sets_dir = tmp_path / "sets"
    shutil.copytree(HARNESS, data_dir)
    shutil.copytree(SETS, sets_dir)
    before = files_below(tmp_path)

    for version, role in SOUND.items():
        questionsets.record(version, role, recorded(version)["rule"], data_dir, sets_dir)
    questionsets.record(
        "not-yet-written", "golden", recorded("harness")["rule"], data_dir, sets_dir
    )

    assert files_below(tmp_path) == before


def test_record_under_another_version_and_role_differs_in_these_two_fields_only():
    """data-model.md, "Question set": the version and the role are fields of the record; the
    selection depends on the rule and the dataset alone."""
    document = load_questionsets().record(
        "another-name", "held-out", recorded("harness-half")["rule"], HARNESS, SETS
    )

    assert document == recorded("harness-half") | {"version": "another-name", "role": "held-out"}


@pytest.mark.parametrize("version", SOUND)
def test_canonical_gives_the_bytes_of_the_canonical_form(version):
    """contracts/records.md, "The canonical form": two spaces of indentation, the separators
    of `json.dumps`, one line feed after the closing brace."""
    document = recorded(version)

    data = load_questionsets().canonical(document)

    assert isinstance(data, bytes)
    assert data == recorded_bytes(version)
    assert data == (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def test_canonical_writes_non_ascii_characters_as_they_are():
    """contracts/records.md: "non-ASCII characters written as they are", in UTF-8."""
    document = recorded("harness")
    document["questions"][0]["article_ids"] = ["hx-€"]

    data = load_questionsets().canonical(document)

    assert "hx-€".encode() in data
    assert b"\\u" not in data


def test_canonical_does_not_change_the_document():
    """The document is read and left as it was."""
    document = recorded("harness-half")

    load_questionsets().canonical(document)

    assert document == recorded("harness-half")


# --- `read` and `QuestionSet` -----------------------------------------------------------------


@pytest.mark.parametrize("version", ["harness", "harness-hxc", "harness-half", "example"])
def test_read_returns_the_fields_of_a_question_set(version):
    """contracts/harness.md, `QuestionSet`: `version`, `role`, `dataset_name`,
    `dataset_revision`, `rule` (the document of the rule), `questions` (a tuple of pairs of a
    question identifier and a tuple of its gold article ids, in the order of the record) and
    `document` (the whole record)."""
    document = recorded(version)

    question_set = load_questionsets().read(version, SETS)

    assert isinstance(question_set, load_questionsets().QuestionSet)
    assert question_set.version == version
    assert question_set.role == document["role"]
    assert question_set.dataset_name == document["dataset"]["name"]
    assert question_set.dataset_revision is None
    assert question_set.rule == document["rule"]
    assert question_set.questions == tuple(
        (question["id"], tuple(question["article_ids"])) for question in document["questions"]
    )
    assert question_set.document == document


def test_read_returns_the_rule_of_a_complement():
    """contracts/harness.md, `QuestionSet.rule`: the document of the rule, also for a set
    whose rule is a complement."""
    question_set = load_questionsets().read("harness-half-rest", SETS)

    assert question_set.role == "held-out"
    assert question_set.rule == {
        "kind": "complement",
        "of": "harness-half",
        "of_fingerprint": hashlib.sha256(recorded_bytes("harness-half")).hexdigest(),
    }


@pytest.mark.parametrize("version", ["harness", "harness-half", "harness-half-rest", "example"])
def test_the_fingerprint_is_the_sha256_of_the_bytes_of_the_file(version):
    """data-model.md, "Question set": "Fingerprint: the SHA-256 of the bytes of the file"."""
    question_set = load_questionsets().read(version, SETS)

    assert question_set.fingerprint == hashlib.sha256(recorded_bytes(version)).hexdigest()


def test_the_fingerprint_is_taken_of_the_file_as_it_is(tmp_path):
    """The fingerprint is that of the bytes of the file, not of a form that the record is
    brought into: a record that is not in the canonical form has the fingerprint of its own
    bytes."""
    compact = json.dumps(recorded("harness"), ensure_ascii=False).encode("utf-8")
    write_set(tmp_path, "harness", compact)

    question_set = load_questionsets().read("harness", tmp_path)

    assert compact != recorded_bytes("harness")
    assert question_set.fingerprint == hashlib.sha256(compact).hexdigest()


def test_read_reads_the_record_as_it_is_and_does_not_check_it():
    """contracts/harness.md, `read`: "It reads the record as it is and does not check it
    against a dataset." The defective records of the example data are read without an error,
    each with the questions it holds."""
    questionsets = load_questionsets()

    one_more = questionsets.read("harness-one-more", SETS)
    other_gold = questionsets.read("harness-other-gold", SETS)

    assert one_more.questions[-1] == ("hxc-001", ("hx-001",))
    assert len(one_more.questions) == 9
    assert dict(other_gold.questions)["hxa-003"] == ("hx-001",)


def test_pairs_gives_the_questions_as_the_audit_takes_them():
    """contracts/harness.md, `QuestionSet.pairs()`: pairs of an identifier and its list of
    article ids, in the order of the record: the form that `audit_index` takes as
    `questions`."""
    pairs = load_questionsets().read("harness-half", SETS).pairs()

    assert [(question, list(article_ids)) for question, article_ids in pairs] == [
        ("hxa-002", ["hx-002"]),
        ("hxa-003", ["hx-001", "hx-003"]),
        ("hxa-005", ["hx-005"]),
        ("hxb-002", ["hx-006"]),
    ]


def test_pairs_keeps_the_article_ids_as_the_record_gives_them(tmp_path):
    """contracts/records.md, `questions[].article_ids`: "same order, repeats kept"."""
    document = recorded("harness")
    document["questions"][3]["article_ids"] = ["hx-004", "hx-002", "hx-004"]
    write_set(tmp_path, "harness", json.dumps(document).encode("utf-8"))

    pairs = load_questionsets().read("harness", tmp_path).pairs()

    assert list(dict(pairs)["hxa-004"]) == ["hx-004", "hx-002", "hx-004"]


@pytest.mark.parametrize(
    ("question", "gold"),
    [
        ("hxa-001", {"hx-001"}),
        ("hxa-003", {"hx-001", "hx-003"}),
        ("hxa-004", {"hx-002", "hx-003", "hx-004"}),
        ("hxb-003", {"hx-001", "hx-006"}),
    ],
)
def test_gold_gives_the_set_of_the_gold_article_ids_of_a_question(question, gold):
    """contracts/harness.md, `QuestionSet.gold(question)`: the set of distinct gold article
    ids of a question."""
    assert load_questionsets().read("harness", SETS).gold(question) == gold


def test_a_gold_article_that_a_question_names_twice_counts_once(tmp_path):
    """spec.md, "Edge Cases": "What happens when a question names the same gold article
    twice? The article counts once". The record keeps the list as the dataset gives it."""
    document = recorded("harness")
    document["questions"][0]["article_ids"] = ["hx-001", "hx-001"]
    document["questions"][2]["article_ids"] = ["hx-003", "hx-001", "hx-003"]
    write_set(tmp_path, "harness", json.dumps(document, indent=2).encode("utf-8"))

    question_set = load_questionsets().read("harness", tmp_path)

    assert question_set.gold("hxa-001") == {"hx-001"}
    assert len(question_set.gold("hxa-001")) == 1
    assert question_set.gold("hxa-003") == {"hx-001", "hx-003"}
    assert dict(question_set.questions)["hxa-001"] == ("hx-001", "hx-001")


def test_gold_of_a_question_without_gold_articles_is_empty(tmp_path):
    """data-model.md, "The numbers, defined": a question may have an empty set of gold
    article ids."""
    document = recorded("harness")
    document["questions"][1]["article_ids"] = []
    write_set(tmp_path, "harness", json.dumps(document, indent=2).encode("utf-8"))

    assert load_questionsets().read("harness", tmp_path).gold("hxa-002") == set()


def test_read_without_a_sets_directory_reads_from_evals_golden(temporary_root, monkeypatch):
    """contracts/harness.md, `read`: "without `sets_dir`, from `evals/golden`", below the
    current directory, which stands for the repository root."""
    write_set(temporary_root / "evals" / "golden", "harness-half", recorded_bytes("harness-half"))
    monkeypatch.chdir(temporary_root)

    question_set = load_questionsets().read("harness-half")

    assert question_set.version == "harness-half"
    assert question_set.fingerprint == hashlib.sha256(recorded_bytes("harness-half")).hexdigest()


def test_read_changes_no_file(tmp_path):
    """contracts/harness.md, "Rules", 2: no function changes a file that exists."""
    shutil.copytree(SETS, tmp_path / "sets")
    before = files_below(tmp_path)

    load_questionsets().read("harness", tmp_path / "sets")

    assert files_below(tmp_path) == before


# --- `SetError` --------------------------------------------------------------------------------


def test_set_error_for_a_record_that_does_not_exist(tmp_path):
    """contracts/harness.md, `SetError`: "A record does not exist ... The message names the
    file"."""
    questionsets = load_questionsets()
    shutil.copytree(SETS, tmp_path / "sets")

    with pytest.raises(questionsets.SetError) as caught:
        questionsets.read("no-such-set", tmp_path / "sets")

    assert "no-such-set.json" in str(caught.value)


def test_set_error_for_a_sets_directory_that_does_not_exist(tmp_path):
    """The same when the sets directory itself does not exist."""
    questionsets = load_questionsets()

    with pytest.raises(questionsets.SetError) as caught:
        questionsets.read("harness", tmp_path / "no-such-directory")

    assert "harness.json" in str(caught.value)


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"this is not JSON\n",
        b'{"version": "broken", "role": "golden"',
        b"\xff\xfe\x00 not UTF-8",
        b'["hxa-001", "hxa-002"]\n',
        b'"harness"\n',
        b"{}\n",
        b'{"version": "broken"}\n',
    ],
    ids=[
        "an empty file",
        "a text that is not JSON",
        "JSON that is cut off",
        "bytes that are not UTF-8",
        "a JSON list",
        "a JSON text",
        "an object without fields",
        "an object with the version only",
    ],
)
def test_set_error_for_a_file_that_is_not_a_question_set_record(tmp_path, content):
    """contracts/harness.md, `SetError`: a record "cannot be read as a question-set record.
    The message names the file"."""
    questionsets = load_questionsets()
    write_set(tmp_path, "broken", content)

    with pytest.raises(questionsets.SetError) as caught:
        questionsets.read("broken", tmp_path)

    assert "broken.json" in str(caught.value)


@pytest.mark.parametrize("field", ["version", "role", "dataset", "rule", "questions"])
def test_set_error_for_a_record_that_lacks_a_field(tmp_path, field):
    """contracts/harness.md, `QuestionSet`: `version`, `role`, `dataset_name`,
    `dataset_revision`, `rule` and `questions` are read from the record. A file without the
    field that one of them is read from cannot be read as a question-set record."""
    questionsets = load_questionsets()
    document = recorded("harness")
    del document[field]
    write_set(tmp_path, "harness", json.dumps(document, indent=2).encode("utf-8"))

    with pytest.raises(questionsets.SetError) as caught:
        questionsets.read("harness", tmp_path)

    assert "harness.json" in str(caught.value)


@pytest.mark.parametrize(
    "questions",
    [
        "hxa-001",
        [["hxa-001", ["hx-001"]]],
        [{"id": "hxa-001"}],
        [{"id": "hxa-001", "article_ids": "hx-001"}],
        [{"id": 1, "article_ids": ["hx-001"]}],
        [{"id": "hxa-001", "article_ids": [1]}],
    ],
    ids=[
        "a text",
        "pairs in place of objects",
        "a question without article ids",
        "article ids as one text",
        "an identifier that is a number",
        "an article id that is a number",
    ],
)
def test_set_error_for_questions_of_another_form(tmp_path, questions):
    """contracts/records.md: `questions[]` is a list of objects, each with the text `id` and
    the list of texts `article_ids`."""
    questionsets = load_questionsets()
    document = recorded("harness")
    document["questions"] = questions
    document["count"] = len(questions)
    write_set(tmp_path, "harness", json.dumps(document, indent=2).encode("utf-8"))

    with pytest.raises(questionsets.SetError) as caught:
        questionsets.read("harness", tmp_path)

    assert "harness.json" in str(caught.value)


def test_set_error_is_an_exception_of_its_own():
    """contracts/harness.md: `SetError` is an exception, raised with a message."""
    questionsets = load_questionsets()

    assert issubclass(questionsets.SetError, Exception)
    with pytest.raises(questionsets.SetError):
        raise questionsets.SetError("tests/data/sets/broken.json is not a question-set record")
