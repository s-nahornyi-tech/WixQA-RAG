"""The question identifier, the form of a version and the draw (task T037):
`src/wixqa_rag/questionsets.py`.

Covers:

- spec.md, FR-002, and data-model.md, "Question identifier": the name of the part, a hyphen,
  and the row number counted from 1, written with at least three digits;
- data-model.md, "Version of a question set": lower-case letters, digits and single hyphens;
  it starts and ends with a letter or a digit; at most 40 characters;
- spec.md, FR-004, data-model.md, "Selection rule", and research.md, section 2: the draw key
  and the draw by the method `sha256-order-v1`, which depend on nothing but the identifiers,
  the number and the seed.

The names are those of contracts/harness.md, "`wixqa_rag.questionsets`", and no other:

    DRAW_METHOD                            # "sha256-order-v1"
    ROLES                                  # ("golden", "held-out")
    question_id(part, row) -> str
    is_valid_version(version) -> bool
    draw_key(seed, identifier) -> str
    draw(identifiers, number, seed) -> the selected identifiers, in the order given

The expected keys and selections are copied from data-model.md, "Example data", and computed
here with `hashlib`; no test derives one from the code it tests. All documents named here
are in specs/002-evaluation-harness/.
"""

import hashlib
import importlib

import pytest

# data-model.md, the table of the eight draw keys with the seed 7.
DRAW_KEYS = {
    "hxa-001": "b007c1a99f194f36e77ddff1287444edf952051575fc10e8920235c10574b35a",
    "hxa-002": "3ab6dbb72b4a0c0ea6ac711d6dc1f5d74391faf706a742a5ba6f9392127e8bfc",
    "hxa-003": "3d153221a5af0c19cabea03edc0c7911e80dc59e4665e9d71f3bcb5d5e22e1e3",
    "hxa-004": "ddd57ba1f0b3ac63038adda3109582537c275bde1cd1d957e296569a1c668f3b",
    "hxa-005": "ac565ec9fabc07a8cbfe8cbb64efaf1d716272217ecb623cb8954a8f0b035bd9",
    "hxb-001": "bdeb5dbf30b3cda7003e44daaa672c50e9ef7f6796a1f5b4fa61e5e88563be62",
    "hxb-002": "25dedc6ec7bacbd106c0818e47ab1288ccfc0f93a2a1f357497e3d1797a190fa",
    "hxb-003": "e63b12a2e3a527e027c2b151bdff7ee0728d36c6e9417885d6fe85d70c8db68a",
}
HXA = ["hxa-001", "hxa-002", "hxa-003", "hxa-004", "hxa-005"]
HXB = ["hxb-001", "hxb-002", "hxb-003"]


def load_questionsets():
    """Import the module; it fails while `src/wixqa_rag/questionsets.py` does not exist
    (plan.md, "Project Structure")."""
    return importlib.import_module("wixqa_rag.questionsets")


def key_of(seed: int, identifier: str) -> str:
    """The draw key as data-model.md defines it, computed without the package."""
    return hashlib.sha256(f"sha256-order-v1:{seed}:{identifier}".encode()).hexdigest()


def selection_of(identifiers: list[str], number: int, seed: int) -> list[str]:
    """The draw as research.md, section 2, defines it, computed without the package: the
    identifiers with the smallest keys, returned in the order in which they were given."""
    ordered = sorted(identifiers, key=lambda identifier: (key_of(seed, identifier), identifier))
    selected = set(ordered[:number])
    return [identifier for identifier in identifiers if identifier in selected]


# --- The two constants -------------------------------------------------------------------------


def test_the_method_of_the_draw_is_named_sha256_order_v1():
    """contracts/harness.md: `DRAW_METHOD` is `"sha256-order-v1"`, the name that every record
    which draws states (FR-003)."""
    assert load_questionsets().DRAW_METHOD == "sha256-order-v1"


def test_the_roles_are_golden_and_held_out():
    """contracts/harness.md: `ROLES` is `("golden", "held-out")`."""
    assert load_questionsets().ROLES == ("golden", "held-out")


# --- The question identifier (FR-002) ----------------------------------------------------------


@pytest.mark.parametrize(
    ("part", "row", "identifier"),
    [
        ("hxa", 3, "hxa-003"),
        ("hxa", 1, "hxa-001"),
        ("exq", 12, "exq-012"),
        ("wixqa_expertwritten", 17, "wixqa_expertwritten-017"),
        ("wixqa_simulated", 200, "wixqa_simulated-200"),
        ("wixqa_synthetic", 999, "wixqa_synthetic-999"),
        ("wixqa_synthetic", 1000, "wixqa_synthetic-1000"),
        ("wixqa_synthetic", 6221, "wixqa_synthetic-6221"),
    ],
)
def test_question_id_is_the_part_a_hyphen_and_the_row_with_at_least_three_digits(
    part, row, identifier
):
    """FR-002 and data-model.md, "Question identifier": the examples of the documents, and a
    row number of four digits, which is written in full."""
    assert load_questionsets().question_id(part, row) == identifier


@pytest.mark.parametrize(("part", "row"), [("hxa", 3), ("wixqa_synthetic", 6221), ("exq", 1)])
def test_question_id_is_the_question_reference_of_spec_1(part, row):
    """FR-002: "the form that spec 1 uses as the question reference". contracts/harness.md:
    `audit.question_reference` of spec 1 stays and returns the same text."""
    audit = importlib.import_module("wixqa_rag.audit")

    assert load_questionsets().question_id(part, row) == audit.question_reference(part, row)


# --- The form of a version (data-model.md, "Version of a question set") -----------------------


@pytest.mark.parametrize(
    "version",
    [
        "harness",
        "golden-001",
        "held-out-001",
        "synthetic-001",
        "harness-half-rest-overlap",
        "a",
        "7",
        "001",
        "a-b-c-d",
        "x" * 40,
    ],
)
def test_is_valid_version_accepts_the_form(version):
    """Lower-case letters, digits and single hyphens; it starts and ends with a letter or a
    digit; at most 40 characters."""
    assert load_questionsets().is_valid_version(version) is True


@pytest.mark.parametrize(
    "version",
    [
        "",
        "Harness",
        "GOLDEN-001",
        "golden_001",
        "two--hyphens",
        "-golden",
        "golden-",
        "-",
        "golden 001",
        " golden",
        "golden\n",
        "golden.json",
        "sets/golden",
        "../golden",
        "gölden",
        "x" * 41,
    ],
)
def test_is_valid_version_rejects_every_other_text(version):
    """An upper-case letter, an underscore, two hyphens in a row, a hyphen at either end, a
    space, a line feed, a dot, a path, a letter outside a to z, and 41 characters."""
    assert load_questionsets().is_valid_version(version) is False


# --- The draw key (data-model.md, "The draw key") ---------------------------------------------


@pytest.mark.parametrize("identifier", DRAW_KEYS)
def test_draw_key_gives_the_eight_keys_of_the_data_model(identifier):
    """data-model.md, the table of the eight draw keys: the key with the seed 7."""
    assert load_questionsets().draw_key(7, identifier) == DRAW_KEYS[identifier]


@pytest.mark.parametrize(
    ("seed", "identifier"),
    [(0, "hxa-001"), (1, "hxa-001"), (20261127, "wixqa_expertwritten-017"), (7, "exq-003")],
)
def test_draw_key_is_the_sha256_of_method_seed_and_identifier(seed, identifier):
    """data-model.md: the SHA-256, as 64 lower-case hexadecimal characters, of the UTF-8
    bytes of `sha256-order-v1:<seed>:<identifier>`; the seed in decimal digits (research.md,
    section 2)."""
    key = load_questionsets().draw_key(seed, identifier)

    assert key == key_of(seed, identifier)
    assert len(key) == 64 and key == key.lower()


def test_draw_key_differs_with_the_seed_and_with_the_identifier():
    """research.md, section 3: the keys of two draws differ in the seed or in the identifier."""
    questionsets = load_questionsets()

    assert questionsets.draw_key(7, "hxa-001") != questionsets.draw_key(8, "hxa-001")
    assert questionsets.draw_key(7, "hxa-001") != questionsets.draw_key(7, "hxa-002")


# --- The draw (research.md, section 2) ---------------------------------------------------------


def test_draw_selects_three_of_hxa_with_the_seed_7():
    """data-model.md, "The draw behind `harness-half`": `hxa-002`, `hxa-003` and `hxa-005`."""
    assert list(load_questionsets().draw(HXA, 3, 7)) == ["hxa-002", "hxa-003", "hxa-005"]


def test_draw_selects_one_of_hxb_with_the_seed_7():
    """data-model.md, "The draw behind `harness-half`": `hxb-002`."""
    assert list(load_questionsets().draw(HXB, 1, 7)) == ["hxb-002"]


@pytest.mark.parametrize("number", [1, 2, 3, 4, 5])
def test_draw_selects_the_identifiers_with_the_smallest_keys(number):
    """data-model.md: "The draw of N questions from a part selects the N identifiers with
    the smallest keys". By the table the order of the keys of `hxa` with the seed 7 is
    `hxa-002`, `hxa-003`, `hxa-005`, `hxa-001`, `hxa-004`."""
    by_key = ["hxa-002", "hxa-003", "hxa-005", "hxa-001", "hxa-004"]

    selected = list(load_questionsets().draw(HXA, number, 7))

    assert set(selected) == set(by_key[:number])
    assert selected == [identifier for identifier in HXA if identifier in by_key[:number]]


def test_draw_returns_the_selection_in_the_order_in_which_the_identifiers_were_given():
    """contracts/harness.md, `draw`: "in the order in which they were given", not in the
    order of the keys. `hxa-001` has a larger key than `hxa-005` and stands before it."""
    selected = list(load_questionsets().draw(HXA, 4, 7))

    assert selected == ["hxa-001", "hxa-002", "hxa-003", "hxa-005"]
    assert DRAW_KEYS["hxa-001"] > DRAW_KEYS["hxa-005"]


@pytest.mark.parametrize("seed", [0, 1, 7, 42, 20261127])
@pytest.mark.parametrize("identifiers", [HXA, HXB, ["hxc-001", "hxc-002"], ["exq-001"]])
def test_draw_of_every_identifier_selects_all_of_them_whatever_the_seed(identifiers, seed):
    """research.md, section 2: "A draw of every question of a part selects all of them
    whatever the seed", which gives `harness`, `harness-hxc` and `example` a known content."""
    selected = load_questionsets().draw(identifiers, len(identifiers), seed)

    assert list(selected) == identifiers


@pytest.mark.parametrize(
    "given",
    [
        ["hxa-005", "hxa-004", "hxa-003", "hxa-002", "hxa-001"],
        ["hxa-003", "hxa-001", "hxa-005", "hxa-002", "hxa-004"],
        ["hxa-004", "hxa-005", "hxa-001", "hxa-003", "hxa-002"],
    ],
)
def test_draw_gives_the_same_selection_when_the_identifiers_come_in_another_order(given):
    """FR-004: the questions that a draw selects depend only on the questions of the part,
    the number, the seed and the method. Given in another order, the same three identifiers
    are selected, and they are returned in the order given."""
    selected = list(load_questionsets().draw(given, 3, 7))

    assert set(selected) == {"hxa-002", "hxa-003", "hxa-005"}
    assert selected == [identifier for identifier in given if identifier in set(selected)]


@pytest.mark.parametrize(("number", "seed"), [(1, 0), (2, 1), (3, 20261127), (4, 3), (2, 99)])
def test_draw_agrees_with_the_definition_for_other_seeds(number, seed):
    """research.md, section 2, steps 2 to 4, computed here with `hashlib` for seeds whose
    selection no document lists."""
    assert list(load_questionsets().draw(HXA, number, seed)) == selection_of(HXA, number, seed)


def test_draw_gives_the_same_selection_every_time():
    """FR-004: the same identifiers, number and seed give the same selection."""
    questionsets = load_questionsets()

    assert list(questionsets.draw(HXA, 2, 20261127)) == list(questionsets.draw(HXA, 2, 20261127))


def test_draw_does_not_change_the_identifiers_it_is_given():
    """The list of identifiers is read and left as it was."""
    given = list(HXA)

    load_questionsets().draw(given, 3, 7)

    assert given == HXA


def test_equal_keys_are_ordered_by_identifier(monkeypatch):
    """data-model.md, "The draw key": "equal keys are ordered by identifier" (research.md,
    section 2, step 3). Two different texts with the same SHA-256 are not known, so the test
    replaces `questionsets.draw_key` by a function that gives every identifier the same key;
    `draw` is expected to obtain its keys from the function of that name in its module. The
    two smallest identifiers are then selected, whatever the order in which they are given."""
    questionsets = load_questionsets()
    monkeypatch.setattr(questionsets, "draw_key", lambda seed, identifier: "0" * 64)
    given = ["hxa-004", "hxa-002", "hxa-005", "hxa-001", "hxa-003"]

    assert list(questionsets.draw(given, 2, 7)) == ["hxa-002", "hxa-001"]
    assert list(questionsets.draw(given, 3, 7)) == ["hxa-002", "hxa-001", "hxa-003"]


def test_keys_that_are_equal_in_part_are_ordered_by_identifier(monkeypatch):
    """The same rule when only two identifiers share a key: the key decides first, and the
    identifier decides between `hxa-005` and `hxa-002`, which share the smallest key."""
    questionsets = load_questionsets()
    keys = {
        "hxa-001": "b" * 64,
        "hxa-002": "a" * 64,
        "hxa-003": "c" * 64,
        "hxa-004": "d" * 64,
        "hxa-005": "a" * 64,
    }
    monkeypatch.setattr(questionsets, "draw_key", lambda seed, identifier: keys[identifier])

    assert list(questionsets.draw(HXA, 1, 7)) == ["hxa-002"]
    assert list(questionsets.draw(HXA, 2, 7)) == ["hxa-002", "hxa-005"]
    assert list(questionsets.draw(HXA, 3, 7)) == ["hxa-001", "hxa-002", "hxa-005"]


# --- What the draw refuses (contracts/harness.md, `draw`) --------------------------------------


@pytest.mark.parametrize("number", [0, -1, -5])
def test_draw_raises_value_error_for_a_number_below_1(number):
    """contracts/harness.md: `ValueError` when `number` is below 1. A set with no question
    is not produced (data-model.md, "Question set", rule 5)."""
    with pytest.raises(ValueError):
        load_questionsets().draw(HXA, number, 7)


@pytest.mark.parametrize(("identifiers", "number"), [(HXA, 6), (HXB, 4), (HXA, 100), ([], 1)])
def test_draw_raises_value_error_for_a_number_above_the_number_of_identifiers(identifiers, number):
    """contracts/harness.md: `ValueError` when `number` is above the number of identifiers.
    spec.md, "Edge Cases": a rule that asks for more questions than a part has."""
    with pytest.raises(ValueError):
        load_questionsets().draw(identifiers, number, 7)


@pytest.mark.parametrize("seed", [-1, -20261127])
def test_draw_raises_value_error_for_a_seed_below_0(seed):
    """contracts/harness.md: `ValueError` when `seed` is below 0. data-model.md, "Selection
    rule": the seed is zero or greater."""
    with pytest.raises(ValueError):
        load_questionsets().draw(HXA, 3, seed)


def test_draw_accepts_the_seed_0():
    """data-model.md, "Selection rule": "Zero or greater"."""
    assert list(load_questionsets().draw(HXA, 2, 0)) == selection_of(HXA, 2, 0)
