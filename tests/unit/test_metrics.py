"""The one computation of the numbers of a run (task T078): `src/wixqa_rag/metrics.py`.

Covers:

- spec.md, FR-009 to FR-017, and the edge cases on a question without a gold article, a list
  that holds an article several times, a gold article named twice, an empty list, a list
  that is absent, and a breakdown without questions;
- data-model.md, "The numbers, defined" and "Summary";
- research.md, section 7: exact numbers, turned into floating-point numbers once;
- contracts/harness.md, "`wixqa_rag.metrics`": the names below, and no other.

    STATUSES, BREAKDOWNS, LISTS
    share_found(gold, items)               # a fractions.Fraction, or None
    all_found(gold, items)                 # 1, 0, or None
    kind_of(gold)                          # "single_article", "multi_article", or None
    entry_cost(tokens, prices)             # a floating-point number; ValueError
    median(values), percentile_95(values)  # None for no value
    summarize(questions, entries, prices)  # the three keys of summary.json; ValueError
    per_question(questions, entries)       # one dictionary per question, in order

`questions` are the pairs of a question set, in its order: a question identifier and its list
of gold article ids. An entry is the document of one line of `results.jsonl`.

The tests are on plain values and on the example data of `tests/data/`, which is read here
with `json`; tests/unit/test_harness_example_data.py shows without code of the package that
the four summaries are what the definitions give. All documents named here are in
specs/002-evaluation-harness/.
"""

import builtins
import copy
import importlib
import io
import json
import os
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "data"
SETS = DATA / "sets"
RUNS = DATA / "runs"

RUN_A = "20261101T100000Z-example-a"
RUN_B = "20261102T100000Z-example-b"
RUN_C = "20261103T100000Z-example-c"
RUN_D = "20261104T100000Z-example-d"
SET_OF_RUN = {RUN_A: "harness", RUN_B: "harness", RUN_C: "harness-hxc", RUN_D: "harness-hxc"}

PRICES = [
    {
        "model": "example-model",
        "usd_per_million_input_tokens": 1.0,
        "usd_per_million_output_tokens": 2.0,
    }
]
NUMBERS_OF_A_LIST = {
    "questions": 0,
    "mean_share_found": None,
    "all_found": 0,
    "share_all_found": None,
}
NO_QUESTIONS = {
    "questions": 0,
    "status": {"answered": 0, "no_answer": 0, "error": 0, "timeout": 0, "call_limit": 0},
    "generation_list": NUMBERS_OF_A_LIST,
    "retrieved_list": NUMBERS_OF_A_LIST,
    "cost_usd": {"total": 0.0, "per_question": None},
    "latency_seconds": {"median": None, "p95": None},
}


def load_metrics():
    """Import the module; it fails while `src/wixqa_rag/metrics.py` does not exist (plan.md,
    "Project Structure")."""
    return importlib.import_module("wixqa_rag.metrics")


def pairs_of(version: str) -> list[tuple[str, list[str]]]:
    """The questions of an example set as pairs, read from its record."""
    record = json.loads((SETS / f"{version}.json").read_text(encoding="utf-8"))
    return [(question["id"], question["article_ids"]) for question in record["questions"]]


def entries_of(run: str) -> list[dict]:
    text = (RUNS / run / "results.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.split("\n") if line]


def summary_of(run: str) -> dict:
    return json.loads((RUNS / run / "summary.json").read_text(encoding="utf-8"))


def prices_of(run: str) -> list[dict]:
    document = json.loads((RUNS / run / "run.json").read_text(encoding="utf-8"))
    return document["config"]["prices"]


def entry(question: str, status: str = "answered", retrieved=(), generation=(), **fields) -> dict:
    """An entry on plain values; a list given as `None` is absent."""
    answered = status in ("answered", "no_answer")
    document = {
        "question_id": question,
        "status": status,
        "retrieved_list": None if retrieved is None else list(retrieved),
        "generation_list": None if generation is None else list(generation),
        "context": "The context." if answered else None,
        "answer": "The answer." if answered else None,
        "answer_sha256": None,
        "tokens": [{"model": "example-model", "input_tokens": 1000, "output_tokens": 100}],
        "cost_usd": 0.0012,
        "latency_seconds": 1.0,
    }
    return document | fields


# --- The three tuples --------------------------------------------------------------------------


def test_the_statuses_the_breakdowns_and_the_lists_are_named():
    """contracts/harness.md: `STATUSES`, `BREAKDOWNS` and `LISTS`, each in its order."""
    metrics = load_metrics()

    assert metrics.STATUSES == ("answered", "no_answer", "error", "timeout", "call_limit")
    assert metrics.BREAKDOWNS == ("all", "single_article", "multi_article")
    assert metrics.LISTS == ("generation_list", "retrieved_list")


# --- `share_found` and `all_found` (FR-010, FR-011) --------------------------------------------


@pytest.mark.parametrize(
    ("gold", "items", "share", "flag"),
    [
        # Some of the gold articles, all of them, and none.
        ({"hx-002", "hx-003", "hx-004"}, ["hx-002", "hx-003", "hx-005"], Fraction(2, 3), 0),
        ({"hx-001", "hx-003"}, ["hx-001", "hx-004"], Fraction(1, 2), 0),
        ({"hx-002", "hx-003", "hx-004"}, ["hx-002", "hx-003", "hx-005", "hx-004"], Fraction(1), 1),
        ({"hx-001"}, ["hx-001", "hx-002", "hx-003"], Fraction(1), 1),
        ({"hx-001", "hx-006"}, ["hx-006", "hx-001"], Fraction(1), 1),
        ({"hx-002"}, ["hx-003", "hx-001"], Fraction(0), 0),
        ({"hx-001", "hx-006"}, ["hx-002", "hx-003"], Fraction(0), 0),
        # The same article several times in the list: it counts once.
        ({"hx-001", "hx-003"}, ["hx-001", "hx-004", "hx-001"], Fraction(1, 2), 0),
        ({"hx-001"}, ["hx-001", "hx-001", "hx-001"], Fraction(1), 1),
        ({"hx-001", "hx-003"}, ["hx-003", "hx-003", "hx-001", "hx-003"], Fraction(1), 1),
        # An empty list exists: the share is 0.
        ({"hx-006"}, [], Fraction(0), 0),
        ({"hx-001", "hx-006"}, [], Fraction(0), 0),
    ],
)
def test_share_found_and_all_found_of_a_list(gold, items, share, flag):
    """FR-010: `share_found` is the number of the question's gold articles among the distinct
    article ids of the list divided by the number of its gold articles; `all_found` is 1 when
    every gold article is among them and 0 otherwise. FR-011: an empty list exists."""
    metrics = load_metrics()

    found = metrics.share_found(gold, items)

    assert isinstance(found, Fraction), "contracts/harness.md: a `fractions.Fraction`"
    assert found == share
    assert metrics.all_found(gold, items) == flag
    assert type(metrics.all_found(gold, items)) is int


def test_the_examples_of_the_contract():
    """contracts/harness.md, "`wixqa_rag.metrics`": the four calls shown there."""
    metrics = load_metrics()
    gold = {"hx-002", "hx-003", "hx-004"}

    assert metrics.share_found(gold, ["hx-002", "hx-003", "hx-005"]) == Fraction(2, 3)
    assert metrics.all_found(gold, ["hx-002", "hx-003", "hx-005"]) == 0
    assert metrics.share_found({"hx-005"}, None) is None
    assert metrics.share_found({"hx-006"}, []) == Fraction(0, 1)


@pytest.mark.parametrize("gold", [{"hx-005"}, {"hx-004", "hx-005"}])
def test_a_list_that_is_none_has_neither_number(gold):
    """FR-011: "A list that was not produced MUST be told apart from an empty list": `None`
    for both numbers, where the empty list gives 0."""
    metrics = load_metrics()

    assert metrics.share_found(gold, None) is None
    assert metrics.all_found(gold, None) is None
    assert metrics.share_found(gold, []) == 0
    assert metrics.all_found(gold, []) == 0


@pytest.mark.parametrize("items", [["hx-001", "hx-002"], [], None])
def test_a_question_without_a_gold_article_has_neither_number(items):
    """spec.md, "Edge Cases": a question without a gold article "has no share found and no
    'all found' flag", whatever the list."""
    metrics = load_metrics()

    assert metrics.share_found(set(), items) is None
    assert metrics.all_found(set(), items) is None


def test_the_order_of_a_list_does_not_change_its_numbers():
    """FR-009: the metrics are on article ids; the set of the distinct ids decides."""
    metrics = load_metrics()
    gold = {"hx-001", "hx-003"}

    assert metrics.share_found(gold, ["hx-004", "hx-001"]) == metrics.share_found(
        gold, ["hx-001", "hx-004"]
    )


def test_the_two_functions_do_not_change_their_arguments():
    """contracts/harness.md: every function is pure and does not change its arguments."""
    metrics = load_metrics()
    gold, items = {"hx-001", "hx-003"}, ["hx-001", "hx-004", "hx-001"]

    metrics.share_found(gold, items)
    metrics.all_found(gold, items)

    assert gold == {"hx-001", "hx-003"}
    assert items == ["hx-001", "hx-004", "hx-001"]


# --- `kind_of` (FR-015) ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("gold", "kind"),
    [
        ({"hx-001"}, "single_article"),
        ({"hx-001", "hx-003"}, "multi_article"),
        ({"hx-002", "hx-003", "hx-004"}, "multi_article"),
        (set(), None),
    ],
)
def test_kind_of_a_question(gold, kind):
    """data-model.md: single-article means exactly one gold article id, multi-article two or
    more; a question without a gold article is in `all` only."""
    assert load_metrics().kind_of(gold) == kind


# --- `entry_cost` (FR-016) ---------------------------------------------------------------------


def tokens(input_tokens: int, output_tokens: int, model: str = "example-model") -> dict:
    return {"model": model, "input_tokens": input_tokens, "output_tokens": output_tokens}


@pytest.mark.parametrize(
    ("counts", "cost"),
    [
        ([tokens(1000, 100)], 0.0012),
        ([tokens(2000, 200)], 0.0024),
        ([tokens(2000, 50)], 0.0021),
        ([tokens(500, 0)], 0.0005),
        ([tokens(3000, 300)], 0.0036),
        ([tokens(1500, 150)], 0.0018),
        ([tokens(0, 0)], 0.0),
        ([], 0.0),
    ],
)
def test_entry_cost_for_one_model(counts, cost):
    """data-model.md, `cost_usd`: input tokens x the input price / 1,000,000 plus output
    tokens x the output price / 1,000,000; the costs of the table of `example-a`. An entry
    for which no model was called costs 0.0."""
    found = load_metrics().entry_cost(counts, PRICES)

    assert type(found) is float, "contracts/harness.md: a floating-point number"
    assert found == cost


def test_entry_cost_for_two_models():
    """data-model.md: "The sum over `tokens`", each model at its own prices: 1000 and 100
    tokens at 1.00 and 2.00, and 400 and 50 tokens at 0.25 and 10.00."""
    prices = [
        *PRICES,
        {
            "model": "other-model",
            "usd_per_million_input_tokens": 0.25,
            "usd_per_million_output_tokens": 10.0,
        },
    ]

    cost = load_metrics().entry_cost([tokens(1000, 100), tokens(400, 50, "other-model")], prices)

    assert cost == float(Fraction(1200 + 100 + 500, 1_000_000))
    assert cost == 0.0018


def test_entry_cost_is_exact_for_a_price_such_as_0_02():
    """research.md, section 7: "A price is read as the decimal number that the JSON text
    states (`0.02` is 2/100)." Five tokens at 0.02 cost exactly 1e-07; the same product in
    floating-point numbers is 1.0000000000000001e-07."""
    prices = [
        {
            "model": "example-model",
            "usd_per_million_input_tokens": 0.02,
            "usd_per_million_output_tokens": 0.15,
        }
    ]
    metrics = load_metrics()

    assert 5 * 0.02 / 1_000_000 != 1e-07, "the case tells exact arithmetic from floating point"
    assert metrics.entry_cost([tokens(5, 0)], prices) == 1e-07
    assert 7 * 0.15 / 1_000_000 != 1.05e-06
    assert metrics.entry_cost([tokens(0, 7)], prices) == 1.05e-06
    assert metrics.entry_cost([tokens(5, 7)], prices) == float(Fraction(115, 100_000_000))


@pytest.mark.parametrize(
    "counts",
    [[tokens(10, 10, "model-without-a-price")], [tokens(1000, 100), tokens(1, 1, "unknown")]],
)
def test_entry_cost_raises_value_error_for_a_model_without_a_price(counts):
    """contracts/harness.md, `entry_cost`: "Raises `ValueError` for a model without a
    price"."""
    with pytest.raises(ValueError):
        load_metrics().entry_cost(counts, PRICES)


# --- `median` and `percentile_95` (FR-016) -----------------------------------------------------


@pytest.mark.parametrize(
    ("values", "median"),
    [
        ([7.0], 7.0),
        ([3.0, 1.0, 2.0], 2.0),
        ([8.0, 30.0, 4.0, 3.0, 1.0], 4.0),
        ([1.0, 2.0], 1.5),
        ([1.0, 2.0, 5.0, 7.0], 3.5),
        ([3.0, 4.0, 30.0, 8.0], 6.0),
        ([1.0, 2.0, 3.0, 4.0, 5.0, 30.0, 7.0, 8.0], 4.5),
        ([2.0, 2.0, 2.0, 2.0], 2.0),
    ],
)
def test_median_of_an_odd_and_of_an_even_number_of_values(values, median):
    """FR-016 and data-model.md: sorted ascending, the middle value when the number is odd,
    the mean of the two middle values when it is even. The values come in any order."""
    given = list(values)

    assert load_metrics().median(given) == median
    assert given == values, "the values are left as they were"


@pytest.mark.parametrize(
    ("values", "p95"),
    [
        ([7.0], 7.0),
        ([1.0, 2.0], 2.0),
        ([1.0, 2.0, 5.0, 7.0], 7.0),
        ([1.0, 2.0, 3.0, 4.0, 5.0, 30.0, 7.0, 8.0], 30.0),
        # 20 values: position 19. 21 values: position 20. 100 values: position 95.
        ([float(number) for number in range(20, 0, -1)], 19.0),
        ([float(number) for number in range(1, 22)], 20.0),
        ([float(number) for number in range(1, 101)], 95.0),
        ([float(number) for number in range(1, 102)], 96.0),
    ],
)
def test_percentile_95_is_the_value_at_position_ceil_of_0_95_n(values, p95):
    """FR-016: "The 95th percentile of n values is the value at position ceil(0.95 x n) when
    they are sorted in ascending order", counted from 1: one of the values, never a value
    between two."""
    given = list(values)

    assert load_metrics().percentile_95(given) == p95
    assert given == values, "the values are left as they were"


def test_median_and_percentile_95_are_none_for_no_value():
    """contracts/harness.md: "`None` for no value"; data-model.md: a latency of a breakdown
    without questions is `null`."""
    metrics = load_metrics()

    assert metrics.median([]) is None
    assert metrics.percentile_95([]) is None


# --- `summarize` on the four example runs (FR-012 to FR-017) -----------------------------------


@pytest.mark.parametrize("run", SET_OF_RUN)
def test_summarize_gives_the_dictionaries_of_the_summary_of_an_example_run(run):
    """tasks.md, T078: `summarize` gives, for the entries of the four example runs, exactly
    the dictionaries of their `summary.json`: the keys `breakdowns`, `retrieval_misses` and
    `questions_without_gold_articles`, "exactly as they stand in `summary.json`"."""
    summary = summary_of(run)

    numbers = load_metrics().summarize(pairs_of(SET_OF_RUN[run]), entries_of(run), prices_of(run))

    assert set(numbers) == {"breakdowns", "retrieval_misses", "questions_without_gold_articles"}
    for key in numbers:
        assert numbers[key] == summary[key], key
    assert json.dumps(numbers["breakdowns"]) == json.dumps(summary["breakdowns"]), (
        "the keys stand in the order of contracts/records.md, and every number has the same "
        "JSON text"
    )


def test_summarize_gives_the_numbers_of_example_a_as_the_data_model_states_them():
    """data-model.md, "The numbers of the four summaries", the three rows of `example-a`,
    typed here: a mean and a share are exact fractions turned into floating-point numbers
    once (19/36, 1/3, 11/14, 5/7, 13/18), and the total cost is 0.0128, where the sum of the
    eight costs in floating-point numbers is 0.012799999999999999."""
    numbers = load_metrics().summarize(pairs_of("harness"), entries_of(RUN_A), PRICES)
    everything = numbers["breakdowns"]["all"]

    assert sum(row["cost_usd"] for row in entries_of(RUN_A)) != 0.0128
    assert everything["cost_usd"] == {"total": 0.0128, "per_question": 0.0016}
    assert everything["generation_list"] == {
        "questions": 6,
        "mean_share_found": float(Fraction(19, 36)),
        "all_found": 2,
        "share_all_found": float(Fraction(1, 3)),
    }
    assert everything["retrieved_list"] == {
        "questions": 7,
        "mean_share_found": float(Fraction(11, 14)),
        "all_found": 5,
        "share_all_found": float(Fraction(5, 7)),
    }
    assert everything["latency_seconds"] == {"median": 4.5, "p95": 30.0}
    assert numbers["breakdowns"]["multi_article"]["generation_list"]["mean_share_found"] == float(
        Fraction(13, 18)
    )
    assert numbers["retrieval_misses"] == ["hxa-002", "hxa-003", "hxa-004", "hxb-002"]


def test_summarize_computes_the_cost_from_the_tokens_and_not_from_cost_usd():
    """contracts/harness.md: "`summarize` computes the cost of each entry from its `tokens`,
    not from its `cost_usd`." Every recorded cost is replaced by another number, and one is
    removed; the summary is the same."""
    entries = entries_of(RUN_A)
    for number, row in enumerate(entries):
        row["cost_usd"] = 100.0 + number
    del entries[2]["cost_usd"]

    numbers = load_metrics().summarize(pairs_of("harness"), entries, PRICES)

    assert numbers["breakdowns"] == summary_of(RUN_A)["breakdowns"]


def test_summarize_uses_the_prices_it_is_given():
    """FR-016: the cost of a question is its token counts multiplied by the prices recorded
    in the run config: at ten times the prices, ten times the cost."""
    prices = [
        {
            "model": "example-model",
            "usd_per_million_input_tokens": 10.0,
            "usd_per_million_output_tokens": 20.0,
        }
    ]

    numbers = load_metrics().summarize(pairs_of("harness"), entries_of(RUN_A), prices)

    assert numbers["breakdowns"]["all"]["cost_usd"] == {"total": 0.128, "per_question": 0.016}


def test_summarize_raises_value_error_for_a_model_without_a_price():
    """contracts/harness.md, `entry_cost`: a model without a price is a `ValueError`, also
    when the cost is computed inside `summarize`."""
    with pytest.raises(ValueError):
        load_metrics().summarize(pairs_of("harness"), entries_of(RUN_A), [])


@pytest.mark.parametrize("run", [RUN_C, RUN_D])
def test_summarize_gives_null_for_every_number_over_no_question(run):
    """data-model.md: "A number whose denominator is 0 is `null`: a mean or a share over no
    question, a cost per question and a latency of a breakdown without questions. A total
    cost over no question is `0.0`." The runs on `harness-hxc` have no multi-article
    question."""
    numbers = load_metrics().summarize(pairs_of("harness-hxc"), entries_of(run), PRICES)

    multi = numbers["breakdowns"]["multi_article"]
    assert multi == NO_QUESTIONS
    assert type(multi["cost_usd"]["total"]) is float


def test_summarize_of_no_question_is_three_breakdowns_without_questions():
    """The same for a question set without a question: every breakdown is empty."""
    numbers = load_metrics().summarize([], [], PRICES)

    assert numbers == {
        "breakdowns": {
            "all": NO_QUESTIONS,
            "single_article": NO_QUESTIONS,
            "multi_article": NO_QUESTIONS,
        },
        "retrieval_misses": [],
        "questions_without_gold_articles": 0,
    }


def test_no_question_of_a_breakdown_has_the_list():
    """spec.md, "Edge Cases": "What happens when no question of a breakdown has the list?
    The number of questions is 0, and the mean and the share are reported as undefined, not
    as 0." Two single-article questions, neither with a generation list."""
    questions = [("q-001", ["a-1"]), ("q-002", ["a-2"])]
    entries = [
        entry("q-001", "timeout", ["a-1"], None),
        entry("q-002", "error", None, None),
    ]

    numbers = load_metrics().summarize(questions, entries, PRICES)

    single = numbers["breakdowns"]["single_article"]
    assert single["questions"] == 2
    assert single["generation_list"] == NUMBERS_OF_A_LIST
    assert single["retrieved_list"] == {
        "questions": 1,
        "mean_share_found": 1.0,
        "all_found": 1,
        "share_all_found": 1.0,
    }
    assert numbers["retrieval_misses"] == []


def test_a_question_without_a_gold_article_is_counted_in_all_only():
    """spec.md, "Edge Cases": such a question "is counted under its status and in the cost
    and the latency of all questions, and it belongs neither to the single-article nor to
    the multi-article questions"; it has no share found, and it is never a retrieval miss."""
    questions = [("q-001", ["a-1"]), ("q-002", []), ("q-003", ["a-1", "a-2"])]
    entries = [
        entry("q-001", "answered", ["a-1"], ["a-1"], latency_seconds=1.0),
        entry("q-002", "no_answer", ["a-9"], ["a-9"], latency_seconds=9.0),
        entry("q-003", "answered", ["a-1", "a-2"], ["a-1"], latency_seconds=3.0),
    ]

    numbers = load_metrics().summarize(questions, entries, PRICES)

    everything = numbers["breakdowns"]["all"]
    assert numbers["questions_without_gold_articles"] == 1
    assert everything["questions"] == 3
    assert everything["status"]["no_answer"] == 1
    assert everything["cost_usd"] == {"total": 0.0036, "per_question": 0.0012}
    assert everything["latency_seconds"] == {"median": 3.0, "p95": 9.0}
    assert everything["generation_list"] == {
        "questions": 2,
        "mean_share_found": 0.75,
        "all_found": 1,
        "share_all_found": 0.5,
    }
    assert numbers["breakdowns"]["single_article"]["questions"] == 1
    assert numbers["breakdowns"]["multi_article"]["questions"] == 1
    assert numbers["breakdowns"]["single_article"]["status"]["no_answer"] == 0
    assert numbers["breakdowns"]["multi_article"]["status"]["no_answer"] == 0
    assert numbers["retrieval_misses"] == ["q-003"]


def test_a_gold_article_that_a_question_names_twice_counts_once():
    """spec.md, "Edge Cases": "What happens when a question names the same gold article
    twice? The article counts once": the question is single-article, and its share is 1."""
    questions = [("q-001", ["a-1", "a-1"]), ("q-002", ["a-1", "a-2", "a-1"])]
    entries = [
        entry("q-001", "answered", ["a-1"], ["a-1"]),
        entry("q-002", "answered", ["a-1", "a-2"], ["a-2"]),
    ]

    numbers = load_metrics().summarize(questions, entries, PRICES)

    assert numbers["breakdowns"]["single_article"]["questions"] == 1
    assert numbers["breakdowns"]["multi_article"]["questions"] == 1
    assert numbers["breakdowns"]["single_article"]["generation_list"]["mean_share_found"] == 1.0
    assert numbers["breakdowns"]["multi_article"]["generation_list"]["mean_share_found"] == 0.5
    assert numbers["retrieval_misses"] == ["q-002"]


def test_the_retrieval_misses_are_the_questions_whose_generation_list_lacks_a_gold_article():
    """FR-013: "the questions whose generation list exists and has `all_found` = 0. A
    question without a generation list is never a retrieval miss, whatever its status." In
    `example-a` the misses are in the order of the set, the empty list of `hxb-002` is a
    miss, and `hxa-005` and `hxb-001` are none."""
    numbers = load_metrics().summarize(pairs_of("harness"), entries_of(RUN_A), PRICES)

    assert numbers["retrieval_misses"] == ["hxa-002", "hxa-003", "hxa-004", "hxb-002"]
    assert "hxa-005" not in numbers["retrieval_misses"]
    assert "hxb-001" not in numbers["retrieval_misses"]


def test_the_status_counts_add_up_to_the_questions_of_each_breakdown():
    """FR-014: "The count of each status MUST be reported, and the counts MUST add up to the
    size of the run's question set", in each breakdown to its number of questions."""
    for run, version in SET_OF_RUN.items():
        numbers = load_metrics().summarize(pairs_of(version), entries_of(run), PRICES)
        for name, breakdown in numbers["breakdowns"].items():
            assert sum(breakdown["status"].values()) == breakdown["questions"], (run, name)
            assert list(breakdown["status"]) == [
                "answered",
                "no_answer",
                "error",
                "timeout",
                "call_limit",
            ]


@pytest.mark.parametrize(
    "change",
    [
        lambda entries: entries.pop(),
        lambda entries: entries.pop(0),
        lambda entries: entries.append(dict(entries[0])),
        lambda entries: entries.append(entry("hxc-001")),
        lambda entries: entries.__setitem__(3, entry("hxc-001")),
        lambda entries: entries.clear(),
    ],
    ids=[
        "the last question has no entry",
        "the first question has no entry",
        "a question has two entries",
        "an entry of a question outside the set",
        "an entry of another question in place of one",
        "no entry at all",
    ],
)
def test_summarize_raises_value_error_when_the_entries_are_not_one_per_question(change):
    """contracts/harness.md, `summarize`: "`entries`: the entries of the run, exactly one per
    question ... Raises `ValueError` when the entries are not one per question"."""
    entries = entries_of(RUN_A)
    change(entries)

    with pytest.raises(ValueError):
        load_metrics().summarize(pairs_of("harness"), entries, PRICES)


def test_summarize_does_not_change_its_arguments():
    """contracts/harness.md: every function is pure and does not change its arguments."""
    questions, entries, prices = pairs_of("harness"), entries_of(RUN_A), copy.deepcopy(PRICES)
    before = copy.deepcopy((questions, entries, prices))

    load_metrics().summarize(questions, entries, prices)

    assert (questions, entries, prices) == before


def test_summarize_gives_the_same_numbers_every_time():
    """FR-017 and SC-006: recomputing a summary gives the same numbers."""
    metrics = load_metrics()
    first = metrics.summarize(pairs_of("harness"), entries_of(RUN_B), PRICES)
    second = metrics.summarize(pairs_of("harness"), entries_of(RUN_B), PRICES)

    assert json.dumps(first) == json.dumps(second)


def test_summarize_ignores_a_further_field_of_an_entry():
    """data-model.md, "Results", rule 4: "An entry may hold further fields"."""
    entries = entries_of(RUN_A)
    for row in entries:
        row["trace"] = {"calls": 3}

    numbers = load_metrics().summarize(pairs_of("harness"), entries, PRICES)

    assert numbers["breakdowns"] == summary_of(RUN_A)["breakdowns"]


# --- `per_question` (FR-010, FR-011; AC-017) ---------------------------------------------------

# contracts/cli.md, "`run report`", the block of `--per-question` for `example-a`: for each
# question its status and, for each list, the gold articles found, the gold articles, and
# `all_found`; `None` for a list that is absent.
PER_QUESTION_A = [
    ("hxa-001", "answered", (1, 1, 1), (1, 1, 1)),
    ("hxa-002", "answered", (0, 1, 0), (1, 1, 1)),
    ("hxa-003", "answered", (1, 2, 0), (1, 2, 0)),
    ("hxa-004", "no_answer", (2, 3, 0), (3, 3, 1)),
    ("hxa-005", "error", None, None),
    ("hxb-001", "timeout", None, (2, 2, 1)),
    ("hxb-002", "call_limit", (0, 1, 0), (0, 1, 0)),
    ("hxb-003", "answered", (2, 2, 1), (2, 2, 1)),
]


def numbers_in(value) -> list[int]:
    """The whole numbers that `per_question` gives for one list of one question, whatever
    names it gives them: contracts/harness.md fixes that they are "the numbers found and to
    be found and `all_found`", and no name for each."""
    if isinstance(value, dict):
        value = list(value.values())
    assert isinstance(value, (list, tuple)), f"three numbers expected, got {value!r}"
    assert all(type(number) is int for number in value), value
    return sorted(value)


def test_per_question_gives_one_dictionary_for_every_question_in_order():
    """contracts/harness.md, `per_question`: "For every question, in order, a dictionary
    with `question_id`, `status`"."""
    rows = load_metrics().per_question(pairs_of("harness"), entries_of(RUN_A))

    assert [(row["question_id"], row["status"]) for row in rows] == [
        (question, status) for question, status, _, _ in PER_QUESTION_A
    ]


def test_per_question_gives_the_numbers_of_the_lines_of_ac_017():
    """tasks.md, T078: "`per_question` gives the lines of AC-017": for `hxa-004` two of three
    gold articles in the generation list and three of three in the retrieved list, for
    `hxa-005` both lists absent, for `hxb-002` none of one in either list; and so for every
    line of the block in contracts/cli.md. A list that is absent is `None`."""
    rows = load_metrics().per_question(pairs_of("harness"), entries_of(RUN_A))

    for row, (question, _, generation, retrieved) in zip(rows, PER_QUESTION_A, strict=True):
        for name, expected in (("generation_list", generation), ("retrieved_list", retrieved)):
            if expected is None:
                assert row[name] is None, f"{question}: the {name} is absent"
            else:
                assert row[name] is not None, f"{question}: the {name} exists"
                assert numbers_in(row[name]) == sorted(expected), (question, name)


def test_per_question_tells_an_empty_list_from_a_list_that_is_absent():
    """FR-011: `hxb-002` has an empty generation list, which gives numbers; `hxb-001` has no
    generation list, which gives `None`."""
    rows = {
        row["question_id"]: row
        for row in load_metrics().per_question(pairs_of("harness"), entries_of(RUN_A))
    }

    assert rows["hxb-002"]["generation_list"] is not None
    assert rows["hxb-001"]["generation_list"] is None
    assert rows["hxb-001"]["retrieved_list"] is not None


def test_per_question_gives_none_for_a_question_without_a_gold_article():
    """contracts/harness.md, `per_question`: "`None` for a list that is absent or a question
    without a gold article"."""
    questions = [("q-001", []), ("q-002", ["a-1"])]
    entries = [
        entry("q-001", "answered", ["a-1"], ["a-1"]),
        entry("q-002", "answered", ["a-1"], []),
    ]

    rows = load_metrics().per_question(questions, entries)

    assert rows[0]["question_id"] == "q-001"
    assert rows[0]["generation_list"] is None
    assert rows[0]["retrieved_list"] is None
    assert numbers_in(rows[1]["generation_list"]) == [0, 0, 1]
    assert numbers_in(rows[1]["retrieved_list"]) == [1, 1, 1]


# --- The module stands alone -------------------------------------------------------------------


def test_the_module_imports_nothing_of_the_project():
    """contracts/harness.md, "Rules", 1: "`metrics` imports nothing of the project." A new
    interpreter imports the module alone; of the project only the package itself and the
    module are loaded, and neither the store's driver nor the provider's library."""
    script = (
        "import sys, json; import wixqa_rag.metrics; "
        "print(json.dumps(sorted(name for name in sys.modules "
        "if name.split('.')[0] in ('wixqa_rag', 'psycopg', 'openai'))))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == ["wixqa_rag", "wixqa_rag.metrics"]


def test_the_computation_reads_no_file(monkeypatch):
    """contracts/harness.md: "Every function is pure: it reads no file, no clock and no
    setting". While the functions run, opening a file is an error."""
    metrics = load_metrics()
    questions, entries = pairs_of("harness"), entries_of(RUN_A)

    def refuse(*arguments, **keywords):
        raise AssertionError(f"the computation opened a file: {arguments[:1]}")

    monkeypatch.setattr(builtins, "open", refuse)
    monkeypatch.setattr(io, "open", refuse)
    monkeypatch.setattr(os, "open", refuse)
    try:
        numbers = metrics.summarize(questions, entries, PRICES)
        rows = metrics.per_question(questions, entries)
        cost = metrics.entry_cost(entries[0]["tokens"], PRICES)
    finally:
        monkeypatch.undo()

    assert numbers["questions_without_gold_articles"] == 0
    assert len(rows) == 8
    assert cost == 0.0012
