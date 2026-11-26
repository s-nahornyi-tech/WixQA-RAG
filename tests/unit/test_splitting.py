"""The splitting rule `line-pack-v1` (tasks T037): `src/wixqa_rag/splitting.py`.

Covers research.md, section 12, step by step, and data-model.md, "Passage" (`text` is not
empty and has at most `max_chars` characters; `passage_no` counts from 0, which is the place
of a passage in the returned list). FR-007: one rule, the same for every article.

The rule is a function of a text, so these tests call it directly. They need one name:

    split(contents: str, max_chars: int = 2000) -> list[str]

It returns the passages of one article in order; the passage at place `n` of the list has
`passage_no` `n`. An article without a non-empty line gives an empty list.

The expected passages below are worked out by hand from the five steps of the rule. A small
`max_chars` keeps them short enough to check by eye. All documents named here are in
specs/001-corpus-and-audit/.
"""

import importlib
import json
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[1] / "data" / "example"


def split(contents: str, *arguments, **options) -> list[str]:
    """Call the rule; it fails while `src/wixqa_rag/splitting.py` does not exist (plan.md)."""
    return importlib.import_module("wixqa_rag.splitting").split(contents, *arguments, **options)


# --- Step 1: line breaks are normalised -------------------------------------------------------


@pytest.mark.parametrize(
    "contents",
    ["first\nsecond", "first\r\nsecond", "first\rsecond", "first\r\n\r\nsecond", "first\n\rsecond"],
    ids=["LF", "CR LF", "CR", "CR LF twice", "LF CR"],
)
def test_step_1_every_kind_of_line_break_ends_a_line(contents):
    """research.md, section 12, step 1: `\\r\\n` and `\\r` become `\\n`."""
    assert split(contents, 20) == ["first\nsecond"]


# --- Step 2: lines are stripped, and empty lines are dropped ----------------------------------


def test_step_2_lines_are_stripped_and_empty_lines_are_dropped():
    """research.md, section 12, step 2: each line is stripped of leading and trailing
    whitespace, and empty lines are dropped."""
    contents = "  Title  \n\n\t\n   first step\t\n\n\nsecond step   \n"

    assert split(contents, 50) == ["Title\nfirst step\nsecond step"]


def test_step_2_whitespace_inside_a_line_is_kept():
    """research.md, section 12: the text of a passage is what is stored, with nothing added;
    only the ends of a line are stripped."""
    assert split("one  two\tthree", 50) == ["one  two\tthree"]


def test_step_2_only_a_line_feed_ends_a_line():
    """research.md, section 12, step 2: the contents are cut "at every `\\n`", and at nothing
    else. A form feed and the Unicode line separator are whitespace inside a line."""
    assert split("one\x0ctwo", 50) == ["one\x0ctwo"]
    assert split("one two", 50) == ["one two"]


def test_step_2_whitespace_is_what_str_isspace_accepts():
    """research.md, section 12: "whitespace is every character that Python's `str.isspace`
    accepts". A no-break space at the end of a line is stripped; a zero-width space is not
    whitespace and stays."""
    assert " ".isspace() and not "​".isspace()

    assert split(" padded \n \nnext", 50) == ["padded\nnext"]
    assert split("kept​", 50) == ["kept​"]


# --- Step 5: an article without a non-empty line produces no passage --------------------------


@pytest.mark.parametrize(
    "contents",
    ["", "\n", "   ", " \n\t\n\r\n  \r ", " \n　"],
    ids=["empty", "one line feed", "spaces", "blank lines", "Unicode spaces"],
)
def test_step_5_a_text_without_a_non_empty_line_gives_no_passage(contents):
    """research.md, section 12, step 5; data-model.md, "Passage": an article whose `contents`
    has no non-empty line produces no passage."""
    assert split(contents) == []
    assert split(contents, 10) == []


# --- Step 3: a line longer than max_chars is cut ----------------------------------------------


def test_step_3_a_long_line_is_cut_at_the_last_whitespace_within_the_limit():
    """research.md, section 12, step 3: a line longer than `max_chars` is cut at the last
    whitespace within its first `max_chars` characters; each piece is stripped, and the
    cutting repeats on the rest.

    `max_chars` = 10. "alpha beta gamma delta": the first 10 characters are "alpha beta";
    their last whitespace follows "alpha". The rest, "beta gamma delta", is cut after "beta",
    and its rest, "gamma delta", after "gamma". Step 4 then packs "alpha" and "beta" into one
    passage of 10 characters; "gamma" and "delta" would need 11.
    """
    assert split("alpha beta gamma delta", 10) == ["alpha\nbeta", "gamma", "delta"]


def test_step_3_the_cut_uses_as_much_of_the_limit_as_whole_words_allow():
    """research.md, section 12, step 3: "the last whitespace within its first `max_chars`
    characters". `max_chars` = 12: "aa bb cc dd ee ff" → the first 12 characters are
    "aa bb cc dd "; their last whitespace follows "dd"."""
    assert split("aa bb cc dd ee ff", 12) == ["aa bb cc dd", "ee ff"]


def test_step_3_a_line_without_whitespace_is_cut_after_exactly_max_chars():
    """research.md, section 12, step 3: "or after exactly `max_chars` characters when it has
    no whitespace there"."""
    assert split("abcdefghijklmnopqrstuvwxy", 10) == ["abcdefghij", "klmnopqrst", "uvwxy"]


def test_step_3_both_kinds_of_cut_in_one_line():
    """research.md, section 12, step 3, on one line: `max_chars` = 5.
    "abc defghijk lm": "abc d" is cut at its whitespace → "abc"; the rest "defghijk lm" has no
    whitespace in "defgh" → "defgh"; the rest "ijk lm" is cut at its whitespace → "ijk"; "lm"
    fits. "ijk" and "lm" would need 6 characters together, so each is a passage."""
    assert split("abc defghijk lm", 5) == ["abc", "defgh", "ijk", "lm"]


def test_step_3_a_line_of_exactly_max_chars_is_not_cut():
    """research.md, section 12, step 3: only "a line longer than `max_chars`" is cut."""
    assert split("abcde fghi", 10) == ["abcde fghi"]


def test_step_3_a_cut_is_made_at_any_whitespace():
    """research.md, section 12: whitespace is what `str.isspace` accepts; a tab and a no-break
    space are places to cut."""
    assert split("abc\tdefgh", 5) == ["abc", "defgh"]
    assert split("abc defgh", 5) == ["abc", "defgh"]


def test_step_3_several_whitespace_characters_at_a_cut_are_stripped():
    """research.md, section 12, step 3: "Each piece is stripped"."""
    assert split("abc   defgh", 6) == ["abc", "defgh"]


# --- Step 4: lines and pieces are packed in order ---------------------------------------------


def test_step_4_lines_join_a_passage_while_it_stays_within_the_limit():
    """research.md, section 12, step 4: the next line joins the current passage, after a
    `\\n`, when the passage stays within `max_chars` characters; otherwise it starts a new
    passage. `max_chars` = 10: "aaaa\\nbbbb" has 9 characters; with "\\ncc" it would have 12."""
    assert split("aaaa\nbbbb\ncc\ndd", 10) == ["aaaa\nbbbb", "cc\ndd"]


def test_step_4_the_line_feed_between_lines_counts():
    """research.md, section 12, step 4: the passage with its `\\n` stays within `max_chars`.
    Two lines of 5 characters need 11."""
    assert split("aaaaa\nbbbbb", 10) == ["aaaaa", "bbbbb"]
    assert split("aaaaa\nbbbb", 10) == ["aaaaa\nbbbb"]


def test_step_4_the_pieces_of_a_cut_line_are_packed_with_their_neighbours():
    """research.md, section 12, step 4: "The lines and pieces are packed in order."
    `max_chars` = 10: the lines are "ab", "cdefg hijkl mn" and "op". The long line gives the
    pieces "cdefg" and "hijkl mn", which fits and is not cut again. Packed: "ab\\ncdefg" (8);
    "hijkl mn" (8) would make 17, so it starts a passage; with "\\nop" it would have 11."""
    assert split("ab\ncdefg hijkl mn\nop", 10) == ["ab\ncdefg", "hijkl mn", "op"]


def test_step_4_the_order_of_the_text_is_kept():
    """research.md, section 12, step 4: packed "in order"; a short line is not moved ahead to
    fill an earlier passage, although "aaaaaa\\ncc" would fit."""
    assert split("aaaaaa\nbbbbbbbb\ncc", 10) == ["aaaaaa", "bbbbbbbb", "cc"]


# --- Length is counted in characters ----------------------------------------------------------


def test_length_is_counted_in_characters_not_in_bytes():
    """research.md, section 12: "Length is counted in Unicode characters." Five characters of
    three bytes each fit into a passage of five characters."""
    assert split("€€€€€", 5) == ["€€€€€"]
    assert split("€€€\n€", 5) == ["€€€\n€"]
    assert split("€€€€€€€", 5) == ["€€€€€", "€€"]


# --- The limits of data-model.md, "Passage" ---------------------------------------------------

AWKWARD_TEXTS = [
    "word " * 900,
    "x" * 4500,
    "\n".join(f"line {number} " + "y" * (number * 37 % 300) for number in range(120)),
    ("tab\tseparated words and a very long run " + "z" * 2500 + " end\r\n") * 3,
    " \n".join(["€uro sign " * 70, "", "short", "q" * 2000, "r" * 2001]),
]


@pytest.mark.parametrize("contents", AWKWARD_TEXTS, ids=range(len(AWKWARD_TEXTS)))
@pytest.mark.parametrize("max_chars", [2000, 64, 7])
def test_every_passage_is_within_the_limits(contents, max_chars):
    """data-model.md, "Passage": `text` is not empty and has at most `max_chars` characters.
    research.md, section 12: nothing is added and nothing but whitespace is left out, so the
    passages hold every other character of the text, in order."""
    passages = split(contents, max_chars)

    assert passages, "a text with a non-empty line gives at least one passage"
    for passage in passages:
        assert passage, "a passage is not empty"
        assert len(passage) <= max_chars
        assert passage == passage.strip(), "a passage starts and ends with a line that is stripped"
    kept = "".join("".join(passage.split()) for passage in passages)
    assert kept == "".join(contents.split())


def test_the_default_limit_is_2000_characters():
    """data-model.md, "Passage": the rule `line-pack-v1` with `max_chars = 2000`."""
    assert split("x" * 2000) == ["x" * 2000]
    assert split("x" * 2001) == ["x" * 2000, "x"]
    assert split("x" * 4500, 2000) == split("x" * 4500)


@pytest.mark.parametrize("contents", AWKWARD_TEXTS, ids=range(len(AWKWARD_TEXTS)))
def test_the_same_text_always_gives_the_same_passages(contents):
    """FR-007 and research.md, section 12: the rule uses characters and lines only, so the
    same text gives the same passages every time."""
    first = split(contents)

    assert split(contents) == first
    assert split(str(contents)) == first
    assert first == list(first), "the passages come as a list, in order"


# --- The example articles ---------------------------------------------------------------------


def test_each_example_article_gives_one_passage_of_its_non_empty_lines():
    """data-model.md, "Example datasets", read with research.md, section 12: every example
    article is shorter than 2,000 characters, so it gives one passage: its non-empty lines,
    stripped and joined by `\\n`. An index built from `example` holds 5 passages."""
    rows = [
        json.loads(line)
        for line in (EXAMPLE / "ex.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 5

    for row in rows:
        lines = [line.strip() for line in row["contents"].split("\n") if line.strip()]
        assert split(row["contents"]) == ["\n".join(lines)], row["id"]
