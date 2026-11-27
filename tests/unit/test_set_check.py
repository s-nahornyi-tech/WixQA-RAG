"""The check of a question set (task T039): `examine` and the command `set check` of
`src/wixqa_rag/questionsets.py`.

Covers:

- spec.md, FR-006, FR-007 and FR-032, and data-model.md, "Check of a question set": one
  test, or more, for each of the differences 1 to 11; every difference is reported; the
  reported numbers; the cases in which the check is not carried out;
- spec.md, "Edge Cases": a question without a gold article, a question text that occurs more
  than once, a question text in both sets, a complemented set that is absent or fails its
  own check, and a local copy of the dataset that is absent or fails the dataset check;
- data-model.md, "What the checks of the four records around the draw find";
- contracts/cli.md, "`set check`": the report, the wording of the `difference:` lines as far
  as the contract fixes it, the verdicts and the exit codes (FR-030).

Every test works on a temporary copy of the example data, the fixture `harness_copy` of
tests/conftest.py: a temporary repository root with the data directory `data/harness` and
the sets directory `data/sets`. A test changes the copies by hand, without code of the
package, and no file of the checkout.

The differences and the numbers are read through the names of contracts/harness.md,
"`wixqa_rag.questionsets`", and no other:

    examine(version, data_dir=None, sets_dir=None) -> SetExamination
    SetExamination                         # question_set, differences, counts
    SetError

The cases in which the check is not carried out are read from the command line, typed in the
temporary root. All documents named here are in specs/002-evaluation-harness/.
"""

import hashlib
import importlib
import json
import re

import pytest

DATA_DIR = "data/harness"
SETS_DIR = "data/sets"

DRAW_REPORT = [
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
    "repeated question texts: 0",
]
COMPLEMENT_REPORT = [
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
    "repeated question texts: 0",
    "in both sets: 0",
    "in neither set: 0",
    "question texts in both sets: 0",
]


def load_questionsets():
    """Import the module; it fails while `src/wixqa_rag/questionsets.py` does not exist
    (plan.md, "Project Structure")."""
    return importlib.import_module("wixqa_rag.questionsets")


@pytest.fixture
def examine(harness_copy, monkeypatch):
    """`examine` for a record of the temporary copy; the current directory is the temporary
    repository root."""
    monkeypatch.chdir(harness_copy.root)

    def of(version: str):
        return load_questionsets().examine(version, harness_copy.data_dir, harness_copy.sets_dir)

    return of


@pytest.fixture
def set_check(harness_copy, run_command):
    """Type `set check` in the temporary repository root, for the copied directories."""

    def of(version: str, data_dir: str | None = DATA_DIR, sets_dir: str | None = SETS_DIR):
        command = f"python -m wixqa_rag set check --version {version}"
        if data_dir is not None:
            command += f" --data-dir {data_dir}"
        if sets_dir is not None:
            command += f" --sets-dir {sets_dir}"
        return run_command(command, cwd=harness_copy.root)

    return of


def names(text: str, word: str) -> bool:
    """Whether a text holds a word as a word of its own: `hx` is not named by `hxa`."""
    return re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", text) is not None


def assert_not_carried_out(result) -> list[str]:
    """Exit code 2, `set check: not carried out` as the last line, a reason before it, and
    neither `passed` nor `failed` (FR-030)."""
    assert result.exit_code == 2, result.stdout
    assert result.last_line == "set check: not carried out"
    assert "set check: passed" not in result.lines
    assert "set check: failed" not in result.lines
    assert result.reasons and all(result.reasons), "a `reason:` line gives the reason"
    assert result.settings_printed == ()
    return result.reasons


# --- Records that pass --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("version", "counts"),
    [
        (
            "harness",
            {"hxa": 5, "hxb": 3, "questions": 8, "single-article": 4, "multi-article": 4},
        ),
        ("harness-hxc", {"hxc": 2, "questions": 2, "single-article": 2, "multi-article": 0}),
        (
            "harness-half",
            {"hxa": 3, "hxb": 1, "questions": 4, "single-article": 3, "multi-article": 1},
        ),
    ],
)
def test_a_sound_record_with_a_draw_has_no_difference_and_the_numbers_of_its_report(
    examine, version, counts
):
    """FR-006 and FR-007: the rule applied again selects exactly the record. contracts/
    harness.md, `SetExamination.counts`: "a dictionary with the keys of the report"."""
    examination = examine(version)

    assert list(examination.differences) == []
    assert examination.counts == counts | {
        "questions without gold articles": 0,
        "repeated question texts": 0,
    }
    assert examination.question_set.version == version


def test_a_sound_complement_has_no_difference_and_the_numbers_of_its_report(examine):
    """FR-032 and data-model.md: `harness-half-rest` passes with `in both sets: 0` and
    `in neither set: 0`; a complement also reports the question texts in both sets."""
    examination = examine("harness-half-rest")

    assert list(examination.differences) == []
    assert examination.counts == {
        "hxa": 2,
        "hxb": 2,
        "questions": 4,
        "single-article": 1,
        "multi-article": 3,
        "questions without gold articles": 0,
        "repeated question texts": 0,
        "in both sets": 0,
        "in neither set": 0,
        "question texts in both sets": 0,
    }
    assert examination.question_set.role == "held-out"


def test_the_counts_of_a_draw_have_no_key_of_a_complement(examine):
    """contracts/harness.md, `counts`: "and for a complement `in both sets`, `in neither
    set`, `question texts in both sets`": a set whose rule draws does not report them."""
    counts = examine("harness-half").counts

    for key in ("in both sets", "in neither set", "question texts in both sets"):
        assert key not in counts


def test_the_command_prints_the_report_of_a_draw(set_check):
    """contracts/cli.md, "`set check`", "Output for a set whose rule draws": every line."""
    result = set_check("harness-half")

    assert result.exit_code == 0, result.stdout
    assert result.lines == [*DRAW_REPORT, "set check: passed"]
    assert result.settings_printed == ()


def test_the_command_prints_the_report_of_a_complement(set_check):
    """contracts/cli.md, "`set check`", "Output for a complement": every line."""
    result = set_check("harness-half-rest")

    assert result.exit_code == 0, result.stdout
    assert result.lines == [*COMPLEMENT_REPORT, "set check: passed"]


def test_the_command_writes_nothing(harness_copy, set_check):
    """contracts/harness.md, "Rules", 2: no function changes a file that exists; a check
    that passes and a check that fails leave the two directories as they were."""
    before = {
        file.relative_to(harness_copy.root).as_posix(): file.read_bytes()
        for file in sorted(harness_copy.root.rglob("*"))
        if file.is_file()
    }

    assert set_check("harness-half-rest").exit_code == 0
    assert set_check("harness-half-swapped").exit_code == 1

    after = {
        file.relative_to(harness_copy.root).as_posix(): file.read_bytes()
        for file in sorted(harness_copy.root.rglob("*"))
        if file.is_file()
    }
    assert after == before


# --- Difference 1: the dataset name or the revision --------------------------------------------


def test_difference_1_another_dataset_name(harness_copy, examine):
    """data-model.md, difference 1: the dataset name of the record differs from the manifest.
    contracts/cli.md: `the question set records <what>, the data directory has <what>`."""
    harness_copy.change_record("harness", lambda d: d["dataset"].update(name="another-dataset"))

    differences = list(examine("harness").differences)

    found = [text for text in differences if "another-dataset" in text]
    assert len(found) == 1, differences
    assert found[0].startswith("the question set records ")
    assert ", the data directory has " in found[0]
    assert names(found[0], "harness")
    assert differences == found, "the name is the one difference of this record"


def test_difference_1_another_revision(harness_copy, examine):
    """data-model.md, difference 1: the revision of the record differs from the manifest,
    which has none (FR-006: "another revision")."""
    revision = "0123456789abcdef0123456789abcdef01234567"
    harness_copy.change_record("harness", lambda d: d["dataset"].update(revision=revision))

    differences = list(examine("harness").differences)

    found = [text for text in differences if revision in text]
    assert len(found) == 1, differences
    assert found[0].startswith("the question set records ")
    assert ", the data directory has " in found[0]
    assert differences == found


def test_difference_1_the_set_of_another_dataset(harness_copy, examine):
    """AC-011 rests on this: the record `example` was produced from another dataset and does
    not pass its check against the harness data."""
    differences = list(examine("example").differences)

    assert any(
        text.startswith("the question set records ") and names(text, "example")
        for text in differences
    ), differences


# --- Difference 2: the parts of the record ------------------------------------------------------


def test_difference_2_another_fingerprint_of_a_part(harness_copy, examine):
    """data-model.md, difference 2: the SHA-256 of a part differs (FR-006: "another
    fingerprint of a part"). The record is as it was; a row of the part has changed."""
    harness_copy.change_rows("hxb", lambda rows: rows[0].update(answer="Another answer."))

    differences = list(examine("harness").differences)

    found = [text for text in differences if names(text, "hxb")]
    assert len(found) == 1, differences
    assert found[0].startswith("the question set records ")
    assert ", the data directory has " in found[0]
    assert differences == found, "the gold articles and the rows did not change"


def test_difference_2_another_row_count_of_a_part(harness_copy, examine):
    """data-model.md, difference 2: the row count of a part differs from the manifest."""

    def change(document):
        document["dataset"]["parts"][0]["rows"] = 4

    harness_copy.change_record("harness", change)

    differences = list(examine("harness").differences)

    assert any(
        text.startswith("the question set records ") and names(text, "hxa") for text in differences
    ), differences


@pytest.mark.parametrize("part", ["hx", "no-such-part"])
def test_difference_2_a_part_that_is_not_a_question_part(harness_copy, examine, part):
    """data-model.md, difference 2: "A part of the record is not a question part of the data
    directory": the corpus part, and a part that the data directory does not have."""

    def change(document):
        document["dataset"]["parts"].append({"name": part, "rows": 6, "sha256": "0" * 64})

    harness_copy.change_record("harness", change)

    differences = list(examine("harness").differences)

    assert any(names(text, part) for text in differences), differences


# --- Differences 3 and 4: the rule applied again ------------------------------------------------


def test_difference_3_a_question_that_the_rule_selects_is_not_in_the_record(examine):
    """data-model.md, difference 3; contracts/cli.md: the wording of the line."""
    differences = list(examine("harness-one-less").differences)

    assert "hxb-003 is selected by the rule and is not in the question set" in differences


def test_difference_4_a_question_in_the_record_is_not_selected_by_the_rule(examine):
    """data-model.md, difference 4; contracts/cli.md: the wording of the line."""
    differences = list(examine("harness-one-more").differences)

    assert "hxc-001 is in the question set and is not selected by the rule" in differences


def test_differences_3_and_4_of_a_draw_with_the_recorded_seed(harness_copy, examine):
    """FR-006: the rule is applied "with the recorded seed". The record `harness-half` under
    the seed 8 is no longer what its rule selects, unless the draw with the seed 8 happens
    to select the same four questions, which the keys computed here exclude."""

    def key(identifier: str) -> str:
        return hashlib.sha256(f"sha256-order-v1:8:{identifier}".encode()).hexdigest()

    hxa = sorted((f"hxa-{number:03d}" for number in range(1, 6)), key=key)[:3]
    hxb = sorted((f"hxb-{number:03d}" for number in range(1, 4)), key=key)[:1]
    selected = set(hxa) | set(hxb)
    recorded = {"hxa-002", "hxa-003", "hxa-005", "hxb-002"}
    assert selected != recorded, "the seed 8 selects other questions than the seed 7"
    harness_copy.change_record("harness-half", lambda d: d["rule"].update(seed=8))

    differences = sorted(examine("harness-half").differences)

    assert differences == sorted(
        [
            f"{question} is selected by the rule and is not in the question set"
            for question in selected - recorded
        ]
        + [
            f"{question} is in the question set and is not selected by the rule"
            for question in recorded - selected
        ]
    )


# --- Difference 5: the gold article ids ---------------------------------------------------------


def test_difference_5_gold_articles_that_differ_from_the_dataset(examine):
    """data-model.md, difference 5; contracts/cli.md: the wording, with the ids separated by
    a comma and a space."""
    differences = list(examine("harness-other-gold").differences)

    assert differences == [
        "hxa-003 has the gold articles hx-001 in the question set and hx-001, hx-003 in the dataset"
    ]


def test_difference_5_an_empty_list_is_written_none(harness_copy, examine):
    """contracts/cli.md: "an empty list is written `none`"."""

    def change(document):
        document["questions"][0]["article_ids"] = []

    harness_copy.change_record("harness", change)

    differences = list(examine("harness").differences)

    assert differences == [
        "hxa-001 has the gold articles none in the question set and hx-001 in the dataset"
    ]


def test_difference_5_gold_articles_in_another_order(harness_copy, examine):
    """contracts/records.md, `questions[].article_ids`: "exactly as the row of the dataset
    gives them: same order, repeats kept". The same ids in another order differ."""

    def change(document):
        document["questions"][2]["article_ids"] = ["hx-003", "hx-001"]

    harness_copy.change_record("harness", change)

    differences = list(examine("harness").differences)

    assert differences == [
        "hxa-003 has the gold articles hx-003, hx-001 in the question set"
        " and hx-001, hx-003 in the dataset"
    ]


def test_difference_5_gold_articles_that_the_dataset_changed(harness_copy, examine):
    """FR-006: the gold articles are compared with the row of the question in the dataset.
    Here the row changed and the record stayed; the fingerprint of the part differs too."""
    harness_copy.change_rows("hxb", lambda rows: rows[1].update(article_ids=["hx-006", "hx-002"]))

    differences = list(examine("harness").differences)

    assert (
        "hxb-002 has the gold articles hx-006 in the question set and hx-006, hx-002 in the dataset"
        in differences
    )
    assert any(text.startswith("the question set records ") for text in differences)


# --- Difference 6: the numbers -------------------------------------------------------------------


def test_difference_6_the_number_of_questions_of_a_part(examine):
    """data-model.md, difference 6; contracts/cli.md: the wording of the line. The record
    `harness-one-less` holds two questions of `hxb`, and its rule takes three."""
    differences = list(examine("harness-one-less").differences)

    assert "the question set holds 2 questions of hxb, the rule takes 3" in differences


def test_difference_6_a_count_that_is_not_the_number_of_questions(harness_copy, examine):
    """data-model.md, difference 6, and "Question set", rule 4: `count` is the length of
    `questions`; contracts/cli.md: the wording of the line."""
    harness_copy.change_record("harness", lambda document: document.update(count=9))

    differences = list(examine("harness").differences)

    assert differences == ["count is 9, the question set holds 8 questions"]


# --- Difference 7: repeats and order -------------------------------------------------------------


def test_difference_7_an_identifier_that_occurs_twice(harness_copy, examine):
    """data-model.md, difference 7, and "Question set", rule 4: no identifier occurs twice."""

    def change(document):
        document["questions"].insert(2, dict(document["questions"][1]))
        document["count"] = 9

    harness_copy.change_record("harness", change)

    differences = list(examine("harness").differences)

    assert any(names(text, "hxa-002") for text in differences), differences


def test_difference_7_questions_that_are_not_in_the_order_of_the_dataset(harness_copy, examine):
    """data-model.md, difference 7, and "Question set", "Order of `questions`": within a
    part by ascending row number. Two questions of `hxa` stand in the other order; the
    record holds the questions that its rule selects, so no question is missing or added."""

    def change(document):
        questions = document["questions"]
        questions[0], questions[1] = questions[1], questions[0]

    harness_copy.change_record("harness", change)

    differences = list(examine("harness").differences)

    assert differences, "the order of the questions is a difference"
    assert not any("selected by the rule" in text for text in differences), differences
    assert not any("has the gold articles" in text for text in differences), differences


def test_difference_7_parts_that_are_not_in_the_order_of_the_rule(harness_copy, examine):
    """data-model.md, "Order of `questions`": "the parts in the order of the rule". The
    questions of `hxb` stand before those of `hxa`."""

    def change(document):
        questions = document["questions"]
        document["questions"] = questions[5:] + questions[:5]

    harness_copy.change_record("harness", change)

    differences = list(examine("harness").differences)

    assert differences, "the order of the parts is a difference"
    assert not any("selected by the rule" in text for text in differences), differences


# --- Difference 8: the rule itself ---------------------------------------------------------------


def test_difference_8_another_method_of_the_draw(harness_copy, examine):
    """data-model.md, difference 8: "The method of a draw is not `sha256-order-v1`"."""
    harness_copy.change_record("harness", lambda d: d["rule"].update(method="shuffle-v0"))

    differences = list(examine("harness").differences)

    assert any("shuffle-v0" in text or "sha256-order-v1" in text for text in differences), (
        differences
    )


def test_difference_8_a_take_that_names_a_part_twice(harness_copy, examine):
    """data-model.md, difference 8: "a `take` names a part twice"; "Selection rule": no part
    occurs twice."""

    def change(document):
        document["rule"]["take"] = [
            {"part": "hxa", "questions": 3},
            {"part": "hxb", "questions": 3},
            {"part": "hxa", "questions": 2},
        ]

    harness_copy.change_record("harness", change)

    differences = list(examine("harness").differences)

    assert any(names(text, "hxa") for text in differences), differences


def test_difference_8_a_take_that_asks_for_more_than_the_part_has(harness_copy, examine):
    """data-model.md, difference 8: a `take` "asks for more questions than the part has".
    The check reports it; it does not end with an error."""

    def change(document):
        document["rule"]["take"][1]["questions"] = 4

    harness_copy.change_record("harness", change)

    differences = list(examine("harness").differences)

    assert any(names(text, "hxb") for text in differences), differences


# --- Differences 9 to 11: a complement -----------------------------------------------------------


def test_difference_9_the_complemented_record_has_another_fingerprint(harness_copy, examine):
    """data-model.md, difference 9; contracts/cli.md: `<W> has changed since <V> was
    produced`."""
    harness_copy.change_record(
        "harness-half-rest", lambda document: document["rule"].update(of_fingerprint="0" * 64)
    )

    differences = list(examine("harness-half-rest").differences)

    assert differences == ["harness-half has changed since harness-half-rest was produced"]


def test_difference_10_a_question_that_is_in_both_sets(harness_copy, examine):
    """data-model.md, difference 10; contracts/cli.md: `<question> is in both <V> and <W>`.
    The complement holds one question more, which the complemented set holds as well."""

    def change(document):
        document["questions"].insert(1, {"id": "hxa-002", "article_ids": ["hx-002"]})
        document["count"] = 5

    harness_copy.change_record("harness-half-rest", change)

    examination = examine("harness-half-rest")

    assert "hxa-002 is in both harness-half-rest and harness-half" in examination.differences
    assert examination.counts["in both sets"] == 1
    assert examination.counts["in neither set"] == 0


def test_difference_11_a_question_that_is_in_neither_set(harness_copy, examine):
    """data-model.md, difference 11; contracts/cli.md: `<question> is in neither <V> nor
    <W>`. The complement lacks one question of the parts."""

    def change(document):
        del document["questions"][-1]
        document["count"] = 3

    harness_copy.change_record("harness-half-rest", change)

    examination = examine("harness-half-rest")

    assert "hxb-003 is in neither harness-half-rest nor harness-half" in examination.differences
    assert examination.counts["in both sets"] == 0
    assert examination.counts["in neither set"] == 1


def test_a_complement_states_differences_3_and_4_as_differences_11_and_10(examine):
    """data-model.md: "For a complement, differences 3 and 4 are stated as differences 11
    and 10". The check of `harness-half-rest-overlap` names no question as selected or not
    selected by the rule."""
    differences = list(examine("harness-half-rest-overlap").differences)

    assert not any("selected by the rule" in text for text in differences), differences


# --- Every difference is reported ----------------------------------------------------------------


def test_every_difference_of_a_record_is_reported(harness_copy, examine):
    """FR-006: the check "MUST fail, and name every difference". One record lacks a question
    that its rule selects, holds a question that its rule does not select, gives other gold
    articles for a third, and states a wrong count."""

    def change(document):
        questions = document["questions"]
        del questions[7]
        questions.append({"id": "hxc-002", "article_ids": ["hx-002"]})
        questions[2]["article_ids"] = ["hx-001"]
        document["count"] = 12

    harness_copy.change_record("harness", change)

    differences = list(examine("harness").differences)

    for expected in (
        "hxb-003 is selected by the rule and is not in the question set",
        "hxc-002 is in the question set and is not selected by the rule",
        "hxa-003 has the gold articles hx-001 in the question set"
        " and hx-001, hx-003 in the dataset",
        "the question set holds 2 questions of hxb, the rule takes 3",
        "count is 12, the question set holds 8 questions",
    ):
        assert expected in differences, f"not reported: {expected}\nreported: {differences}"
    assert len(differences) == len(set(differences)), "no difference is reported twice"


def test_every_question_of_a_complement_that_differs_is_named(harness_copy, examine):
    """FR-032: the check of a complement "MUST fail and name every such question": two
    questions in both sets and two in neither."""

    def change(document):
        document["questions"] = [
            {"id": "hxa-002", "article_ids": ["hx-002"]},
            {"id": "hxa-004", "article_ids": ["hx-002", "hx-003", "hx-004"]},
            {"id": "hxb-002", "article_ids": ["hx-006"]},
            {"id": "hxb-003", "article_ids": ["hx-001", "hx-006"]},
        ]

    harness_copy.change_record("harness-half-rest", change)

    examination = examine("harness-half-rest")

    assert sorted(examination.differences) == [
        "hxa-001 is in neither harness-half-rest nor harness-half",
        "hxa-002 is in both harness-half-rest and harness-half",
        "hxb-001 is in neither harness-half-rest nor harness-half",
        "hxb-002 is in both harness-half-rest and harness-half",
    ]
    assert examination.counts["in both sets"] == 2
    assert examination.counts["in neither set"] == 2


# --- The four records around the draw (data-model.md, "Example data") ---------------------------


@pytest.mark.parametrize(
    ("version", "differences"),
    [
        ("harness-half", []),
        ("harness-half-rest", []),
        (
            "harness-half-swapped",
            [
                "hxa-001 is in the question set and is not selected by the rule",
                "hxa-005 is selected by the rule and is not in the question set",
            ],
        ),
        (
            "harness-half-rest-overlap",
            [
                "hxa-002 is in both harness-half-rest-overlap and harness-half",
                "hxa-004 is in neither harness-half-rest-overlap nor harness-half",
            ],
        ),
    ],
)
def test_the_four_records_around_the_draw_give_the_differences_of_the_table(
    examine, version, differences
):
    """data-model.md, "What the checks of the four records around the draw find": the
    outcome and the differences of each, `harness-half-swapped` with "exactly two"."""
    assert sorted(examine(version).differences) == differences


def test_the_overlap_record_reports_one_question_in_both_sets_and_one_in_neither(examine):
    """data-model.md, the same table: `in both sets: 1`, `in neither set: 1` (AC-036)."""
    counts = examine("harness-half-rest-overlap").counts

    assert counts["in both sets"] == 1
    assert counts["in neither set"] == 1


def test_the_command_prints_the_report_and_then_the_differences_of_a_failed_check(set_check):
    """contracts/cli.md, "`set check`": "The `difference:` lines follow the report and stand
    before the verdict"; exit code 1."""
    result = set_check("harness-half-swapped")

    assert result.exit_code == 1, result.stdout
    report = ["question set: harness-half-swapped", *DRAW_REPORT[1:]]
    assert result.lines[: len(report)] == report
    assert sorted(result.lines[len(report) : -1]) == [
        "difference: hxa-001 is in the question set and is not selected by the rule",
        "difference: hxa-005 is selected by the rule and is not in the question set",
    ]
    assert result.last_line == "set check: failed"


# --- The reported numbers (FR-007) ---------------------------------------------------------------


def test_the_numbers_describe_the_record_as_it_is_also_when_the_check_fails(examine):
    """contracts/cli.md: "The numbers describe the record as it is, also when the check
    fails." `harness-one-less` holds two questions of `hxb` and seven in all."""
    counts = examine("harness-one-less").counts

    assert counts == {
        "hxa": 5,
        "hxb": 2,
        "questions": 7,
        "single-article": 4,
        "multi-article": 3,
        "questions without gold articles": 0,
        "repeated question texts": 0,
    }


def test_a_question_of_no_part_of_the_record_has_no_line_of_its_own(examine, set_check):
    """contracts/cli.md: "A question of the record that belongs to no such part appears only
    in a `difference:` line, so the check of `harness-one-more` prints no line for `hxc`."
    The record holds nine questions."""
    counts = examine("harness-one-more").counts
    result = set_check("harness-one-more")

    assert "hxc" not in counts
    assert (counts["hxa"], counts["hxb"], counts["questions"]) == (5, 3, 9)
    assert not any(line.startswith("hxc:") for line in result.lines)
    assert "questions: 9" in result.lines
    assert result.exit_code == 1


def test_a_question_without_a_gold_article_is_counted(harness_copy, examine):
    """spec.md, "Edge Cases", and FR-007: the check reports the number of questions without
    a gold article. Such a question is neither single-article nor multi-article, and it is
    no difference: the record gives what the dataset gives."""
    harness_copy.change_rows("hxa", lambda rows: rows[0].update(article_ids=[]))
    harness_copy.rewrite_records()

    examination = examine("harness")

    assert list(examination.differences) == []
    assert examination.counts["questions without gold articles"] == 1
    assert examination.counts["single-article"] == 3
    assert examination.counts["multi-article"] == 4
    assert examination.counts["questions"] == 8


def test_a_gold_article_that_a_question_names_twice_counts_once(harness_copy, examine):
    """spec.md, "Edge Cases": "What happens when a question names the same gold article
    twice? The article counts once". data-model.md: single-article means exactly one
    distinct gold article id. The record keeps the list as the dataset gives it."""
    harness_copy.change_rows("hxa", lambda rows: rows[0].update(article_ids=["hx-001", "hx-001"]))
    harness_copy.rewrite_records()

    examination = examine("harness")

    assert list(examination.differences) == []
    assert examination.counts["single-article"] == 4
    assert examination.counts["multi-article"] == 4
    assert dict(examination.question_set.questions)["hxa-001"] == ("hx-001", "hx-001")


def test_a_question_text_that_occurs_twice_is_reported_and_is_no_difference(harness_copy, examine):
    """spec.md, "Edge Cases": "Every row stays a question of its own, as published. The
    check of the set reports the number of repeated texts as a finding about the data."""
    text = harness_copy.rows("hxa")[0]["question"]
    harness_copy.change_rows("hxb", lambda rows: rows[2].update(question=text))
    harness_copy.rewrite_records()

    examination = examine("harness")

    assert list(examination.differences) == []
    assert examination.counts["repeated question texts"] == 1
    assert examination.counts["questions"] == 8


def test_repeated_question_texts_are_counted_as_distinct_texts(harness_copy, examine):
    """data-model.md: "Distinct values of the field `question` that occur in two or more
    questions of the set": one text in three questions and another in two are two texts."""
    rows = harness_copy.rows("hxa")
    first, second = rows[0]["question"], rows[1]["question"]

    def change_hxa(rows):
        rows[2]["question"] = first
        rows[3]["question"] = second

    harness_copy.change_rows("hxa", change_hxa)
    harness_copy.change_rows("hxb", lambda rows: rows[0].update(question=first))
    harness_copy.rewrite_records()

    assert examine("harness").counts["repeated question texts"] == 2


def test_question_texts_are_compared_as_they_are(harness_copy, examine):
    """data-model.md: "Texts are compared as they are, without changing case or spaces"."""
    text = harness_copy.rows("hxa")[0]["question"]

    def change(rows):
        rows[1]["question"] = text.upper()
        rows[2]["question"] = text + " "
        rows[3]["question"] = " " + text

    harness_copy.change_rows("hxa", change)
    harness_copy.rewrite_records()

    assert examine("harness").counts["repeated question texts"] == 0


def test_a_repeated_text_is_counted_only_among_the_questions_of_the_set(harness_copy, examine):
    """data-model.md: "in two or more questions of the set". `hxa-001` is not a question of
    `harness-half`, so its text, repeated in `hxa-002`, is not a repeated text of that set."""
    text = harness_copy.rows("hxa")[0]["question"]
    harness_copy.change_rows("hxa", lambda rows: rows[1].update(question=text))
    harness_copy.rewrite_records()

    assert examine("harness-half").counts["repeated question texts"] == 0
    assert examine("harness").counts["repeated question texts"] == 1


def test_a_question_text_in_both_sets_is_reported_for_the_complement(harness_copy, examine):
    """spec.md, "Edge Cases", and FR-032: the check of a held-out set that complements a
    golden set "also reports the number of question texts that occur in both". `hxa-001` of
    the complement gets the text of `hxa-002` of the complemented set. It is a finding, not
    a difference."""
    text = harness_copy.rows("hxa")[1]["question"]
    harness_copy.change_rows("hxa", lambda rows: rows[0].update(question=text))
    harness_copy.rewrite_records()

    examination = examine("harness-half-rest")

    assert list(examination.differences) == []
    assert examination.counts["question texts in both sets"] == 1
    assert examination.counts["repeated question texts"] == 0
    assert examination.counts["in both sets"] == 0
    assert examination.counts["in neither set"] == 0


def test_the_command_prints_the_findings_and_passes(harness_copy, set_check):
    """FR-007 and contracts/cli.md: the numbers of the report for a dataset with a question
    without a gold article and a question text that occurs in both sets; the check passes."""
    text = harness_copy.rows("hxa")[1]["question"]

    def change(rows):
        rows[0]["question"] = text
        rows[3]["article_ids"] = []

    harness_copy.change_rows("hxa", change)
    harness_copy.rewrite_records()

    result = set_check("harness-half-rest")

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
        "multi-article: 2",
        "questions without gold articles: 1",
        "repeated question texts: 0",
        "in both sets: 0",
        "in neither set: 0",
        "question texts in both sets: 1",
        "set check: passed",
    ]


# --- The check is not carried out (FR-030, FR-032) ----------------------------------------------


def test_examine_raises_set_error_for_a_record_that_does_not_exist(harness_copy, examine):
    """contracts/harness.md, `examine`: "Raises `SetError` when the record ... cannot be
    read"."""
    with pytest.raises(load_questionsets().SetError) as caught:
        examine("no-such-set")

    assert "no-such-set.json" in str(caught.value)


def test_examine_raises_set_error_when_the_complemented_record_cannot_be_read(
    harness_copy, examine
):
    """contracts/harness.md, `examine`: "Raises `SetError` when the record, or the record it
    complements, cannot be read"."""
    (harness_copy.sets_dir / "harness-half.json").unlink()

    with pytest.raises(load_questionsets().SetError) as caught:
        examine("harness-half-rest")

    assert "harness-half.json" in str(caught.value)


def test_a_record_that_does_not_exist_is_not_checked(set_check):
    """contracts/cli.md, "`set check`": `reason: question set <V> does not exist in <sets
    directory>`, the verdict `not carried out` and exit code 2."""
    result = set_check("no-such-set")

    assert assert_not_carried_out(result) == [
        f"question set no-such-set does not exist in {SETS_DIR}"
    ]


@pytest.mark.parametrize("version", ["Harness", "two--hyphens", "x" * 41])
def test_a_version_of_another_form_is_not_checked(set_check, version):
    """contracts/cli.md, "`set check`", step 1: "`V` is a valid version"; the same reason
    line as for a record that does not exist."""
    result = set_check(version)

    assert assert_not_carried_out(result) == [
        f"question set {version} does not exist in {SETS_DIR}"
    ]


@pytest.mark.parametrize(
    "content",
    [b"this is not JSON\n", b'["hxa-001"]\n', b"{}\n"],
    ids=["a text that is not JSON", "a JSON list", "an object without fields"],
)
def test_a_file_that_is_not_a_question_set_record_is_not_checked(harness_copy, set_check, content):
    """contracts/cli.md, "`set check`": `reason: <file> is not a question-set record:
    <what>`."""
    (harness_copy.sets_dir / "broken.json").write_bytes(content)

    reasons = assert_not_carried_out(set_check("broken"))

    assert len(reasons) == 1
    assert "broken.json is not a question-set record: " in reasons[0]
    assert len(reasons[0].split(": ", 1)[1]) > 0


def test_a_data_directory_that_fails_the_dataset_check_is_not_checked_against(
    harness_copy, set_check
):
    """spec.md, "Edge Cases": when the local copy fails the dataset check, a question set is
    not checked. contracts/cli.md: "the lines of the check, then `reason: the dataset check
    failed for <DIR>`". Here a part file changed after its fingerprint was recorded."""
    file = harness_copy.data_dir / "hxb.jsonl"
    file.write_bytes(file.read_bytes() + file.read_bytes().split(b"\n")[0] + b"\n")

    result = set_check("harness")

    reasons = assert_not_carried_out(result)
    assert reasons == [f"the dataset check failed for {DATA_DIR}"]
    assert any(names(text, "hxb") for text in result.differences), (
        "the lines of the dataset check stand before the reason"
    )
    assert result.lines.index(f"reason: {reasons[0]}") == len(result.lines) - 2


def test_a_data_directory_that_does_not_exist_is_not_checked_against(set_check):
    """spec.md, "Edge Cases": "the local copy of the dataset is absent": not carried out,
    with the reason."""
    result = set_check("harness", data_dir="data/no-such-directory")

    assert_not_carried_out(result)


def test_without_a_local_copy_of_the_pinned_dataset_the_check_is_not_carried_out(set_check):
    """spec.md, "Edge Cases": without `--data-dir` the check reads the default data
    directory of the pinned dataset, which the temporary root does not have."""
    result = set_check("harness", data_dir=None)

    assert_not_carried_out(result)


def test_the_record_is_looked_for_before_the_data_directory_is_checked(set_check):
    """contracts/cli.md, "`set check`": step 1, the record, comes before step 2, the dataset
    check."""
    result = set_check("no-such-set", data_dir="data/no-such-directory")

    assert assert_not_carried_out(result) == [
        f"question set no-such-set does not exist in {SETS_DIR}"
    ]


def test_a_complement_whose_complemented_record_is_missing_is_not_checked(harness_copy, set_check):
    """FR-032 and spec.md, "Edge Cases": the check of a complement "is not carried out when
    the golden set it names is absent"."""
    (harness_copy.sets_dir / "harness-half.json").unlink()

    result = set_check("harness-half-rest")

    reasons = assert_not_carried_out(result)
    assert any(names(text, "harness-half") for text in reasons), reasons


def test_a_complement_whose_complemented_record_fails_its_check_is_not_checked(
    harness_copy, set_check
):
    """FR-032 and spec.md, "Edge Cases": the check of a complement is not carried out when
    the set it names "does not pass its own check". The record `harness-half` holds
    `hxa-001` in place of `hxa-005`, which its rule selects."""
    swapped = harness_copy.record("harness-half-swapped") | {"version": "harness-half"}
    harness_copy.write_record(swapped)

    result = set_check("harness-half-rest")

    reasons = assert_not_carried_out(result)
    assert any(names(text, "harness-half") for text in reasons), reasons


def test_a_complement_of_a_set_that_is_not_a_record_is_not_checked(harness_copy, set_check):
    """The same when the complemented record cannot be read as a question-set record."""
    (harness_copy.sets_dir / "harness-half.json").write_text("not a record\n", encoding="utf-8")

    assert_not_carried_out(set_check("harness-half-rest"))


def test_the_default_sets_directory_is_evals_golden(harness_copy, set_check):
    """contracts/cli.md, "Directories": the default of `--sets-dir` is `evals/golden`, below
    the directory where the command is typed. The reason names it; a record that is copied
    there is found."""
    missing = set_check("harness-half", sets_dir=None)
    assert assert_not_carried_out(missing) == [
        "question set harness-half does not exist in evals/golden"
    ]

    golden = harness_copy.root / "evals" / "golden"
    golden.mkdir(parents=True)
    content = (harness_copy.sets_dir / "harness-half.json").read_bytes()
    (golden / "harness-half.json").write_bytes(content)

    found = set_check("harness-half", sets_dir=None)
    assert found.exit_code == 0, found.stdout
    assert found.lines == [*DRAW_REPORT, "set check: passed"]
    assert json.loads(content)["version"] == "harness-half"
