"""The one computation of the numbers of a run (specs/002-evaluation-harness: spec.md, FR-009
to FR-017, FR-027 and FR-028; data-model.md, "The numbers, defined" and "Pairwise
comparison"; contracts/harness.md, "`wixqa_rag.metrics`").

It is used when a run is recorded, when its record is checked and when it is reported. Every
function is pure: it reads no file, no clock and no setting, and it does not change its
arguments. The module imports nothing of the project.

Numbers are computed with exact fractions and turned into floating-point numbers once, at the
end (research.md, section 7). A number in a document is read as the decimal number that its
shortest text states: `0.02` is 2/100.

`questions` are the pairs of a question set, in its order: a question identifier and its list
of gold article ids. An *entry* is the document of one line of `results.jsonl`.
"""

import math
from collections.abc import Collection, Iterable, Sequence
from fractions import Fraction

STATUSES = ("answered", "no_answer", "error", "timeout", "call_limit")
BREAKDOWNS = ("all", "single_article", "multi_article")
LISTS = ("generation_list", "retrieved_list")

_MILLION = 1_000_000


def _exact(number: int | float) -> Fraction:
    """The decimal number that the shortest text of a number states."""
    return Fraction(number) if isinstance(number, int) else Fraction(repr(number))


def _number(value: Fraction | None) -> float | None:
    return None if value is None else float(value)


# --- One question and one list ------------------------------------------------------------------


def share_found(gold: Collection[str], items: Iterable[str] | None) -> Fraction | None:
    """The gold article ids among the distinct items, divided by the number of gold article
    ids. `None` when `gold` is empty or `items` is `None`."""
    wanted = set(gold)
    if not wanted or items is None:
        return None
    return Fraction(len(wanted & set(items)), len(wanted))


def all_found(gold: Collection[str], items: Iterable[str] | None) -> int | None:
    """1 when every gold article id is among the items, otherwise 0; `None` when `gold` is
    empty or `items` is `None`."""
    wanted = set(gold)
    if not wanted or items is None:
        return None
    return 1 if wanted <= set(items) else 0


def kind_of(gold: Collection[str]) -> str | None:
    """`"single_article"`, `"multi_article"`, or `None` for a question without a gold
    article."""
    distinct = len(set(gold))
    if distinct == 0:
        return None
    return "single_article" if distinct == 1 else "multi_article"


# --- Cost and latency ---------------------------------------------------------------------------


def _exact_cost(tokens: Sequence[dict], prices: Sequence[dict]) -> Fraction:
    by_model = {price["model"]: price for price in prices}
    cost = Fraction(0)
    for count in tokens:
        if count["model"] not in by_model:
            raise ValueError(f"the model {count['model']} has no price")
        price = by_model[count["model"]]
        cost += count["input_tokens"] * _exact(price["usd_per_million_input_tokens"]) / _MILLION
        cost += count["output_tokens"] * _exact(price["usd_per_million_output_tokens"]) / _MILLION
    return cost


def entry_cost(tokens: Sequence[dict], prices: Sequence[dict]) -> float:
    """The cost of one entry: `tokens` and `prices` as the documents of `tokens` and of
    `config.prices`. Raises `ValueError` for a model without a price."""
    return float(_exact_cost(tokens, prices))


def _exact_median(values: Sequence[Fraction]) -> Fraction | None:
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def median(values: Iterable[int | float]) -> float | None:
    """The median: sorted ascending, the middle value of an odd number of values and the mean
    of the two middle values of an even number; `None` for no value."""
    return _number(_exact_median([_exact(value) for value in values]))


def percentile_95(values: Iterable[int | float]) -> float | None:
    """The 95th percentile: the value at position ceil(0.95 x n), counted from 1, of the n
    values sorted ascending; `None` for no value."""
    ordered = sorted(values)
    if not ordered:
        return None
    position = math.ceil(Fraction(95, 100) * len(ordered))
    return float(ordered[position - 1])


# --- The numbers of a run -----------------------------------------------------------------------


def _one_per_question(questions: Sequence[tuple[str, Sequence[str]]], entries: Sequence[dict]):
    """The entry of every question, in the order of the questions. Raises `ValueError` when
    the entries are not exactly one per question."""
    by_question = {}
    for entry in entries:
        question = entry["question_id"]
        if question in by_question:
            raise ValueError(f"{question} has two entries")
        by_question[question] = entry
    identifiers = [question for question, _ in questions]
    for question in identifiers:
        if question not in by_question:
            raise ValueError(f"{question} has no entry")
    outside = [question for question in by_question if question not in set(identifiers)]
    if outside or len(identifiers) != len(by_question):
        raise ValueError("the entries are not one per question of the question set")
    return [by_question[question] for question in identifiers]


def _list_numbers(rows: Sequence[tuple[set[str], dict]], name: str) -> dict:
    """The four numbers of one list in one breakdown: over the questions that have a gold
    article and for which the list exists."""
    shares = [
        share_found(gold, entry[name]) for gold, entry in rows if gold and entry[name] is not None
    ]
    found = sum(
        all_found(gold, entry[name]) for gold, entry in rows if gold and entry[name] is not None
    )
    number = len(shares)
    return {
        "questions": number,
        "mean_share_found": _number(sum(shares, Fraction(0)) / number) if number else None,
        "all_found": found,
        "share_all_found": _number(Fraction(found, number)) if number else None,
    }


def _breakdown(rows: Sequence[tuple[set[str], dict]], prices: Sequence[dict]) -> dict:
    number = len(rows)
    total = sum((_exact_cost(entry["tokens"], prices) for _, entry in rows), Fraction(0))
    latencies = [entry["latency_seconds"] for _, entry in rows]
    return {
        "questions": number,
        "status": {
            status: sum(1 for _, entry in rows if entry["status"] == status) for status in STATUSES
        },
        **{name: _list_numbers(rows, name) for name in LISTS},
        "cost_usd": {
            "total": float(total),
            "per_question": _number(total / number) if number else None,
        },
        "latency_seconds": {"median": median(latencies), "p95": percentile_95(latencies)},
    }


def summarize(
    questions: Sequence[tuple[str, Sequence[str]]], entries: Sequence[dict], prices: Sequence[dict]
) -> dict:
    """The numbers of a run: the keys `breakdowns`, `retrieval_misses` and
    `questions_without_gold_articles`, exactly as they stand in `summary.json`. The cost of
    an entry is computed from its `tokens`, not from its `cost_usd`. Raises `ValueError`
    when the entries are not one per question, or for a model without a price."""
    ordered = _one_per_question(questions, entries)
    rows = [(set(gold), entry) for (_, gold), entry in zip(questions, ordered, strict=True)]
    of_breakdown = {
        "all": rows,
        "single_article": [row for row in rows if kind_of(row[0]) == "single_article"],
        "multi_article": [row for row in rows if kind_of(row[0]) == "multi_article"],
    }
    return {
        "breakdowns": {name: _breakdown(of_breakdown[name], prices) for name in BREAKDOWNS},
        "retrieval_misses": [
            entry["question_id"]
            for gold, entry in rows
            if all_found(gold, entry["generation_list"]) == 0
        ],
        "questions_without_gold_articles": sum(1 for gold, _ in rows if not gold),
    }


def per_question(
    questions: Sequence[tuple[str, Sequence[str]]], entries: Sequence[dict]
) -> list[dict]:
    """For every question, in order, a dictionary with `question_id`, `status` and, under the
    name of each of the two lists, `found` (the gold articles in the list), `gold` (the gold
    articles of the question) and `all_found`; `None` in place of the three for a list that
    is absent or a question without a gold article."""
    rows = []
    for (question, gold), entry in zip(
        questions, _one_per_question(questions, entries), strict=True
    ):
        row = {"question_id": question, "status": entry["status"]}
        wanted = set(gold)
        for name in LISTS:
            items = entry[name]
            if not wanted or items is None:
                row[name] = None
            else:
                row[name] = {
                    "found": len(wanted & set(items)),
                    "gold": len(wanted),
                    "all_found": all_found(wanted, items),
                }
        rows.append(row)
    return rows


# --- The pairwise comparison --------------------------------------------------------------------


def compare(
    questions: Sequence[tuple[str, Sequence[str]]],
    first_entries: Sequence[dict],
    second_entries: Sequence[dict],
) -> dict:
    """The pairwise comparison of two runs on one question set, on `all_found` of the
    generation list: `compared` (a number) and `left_out`, `gained` and `lost` (lists of
    question identifiers in the order of the set). A question without a gold article, or
    without a generation list in either run, is left out."""
    first = _one_per_question(questions, first_entries)
    second = _one_per_question(questions, second_entries)
    compared = 0
    left_out, gained, lost = [], [], []
    for (question, gold), before, after in zip(questions, first, second, strict=True):
        outcomes = (
            all_found(gold, before["generation_list"]),
            all_found(gold, after["generation_list"]),
        )
        if None in outcomes:
            left_out.append(question)
            continue
        compared += 1
        if outcomes == (0, 1):
            gained.append(question)
        elif outcomes == (1, 0):
            lost.append(question)
    return {"compared": compared, "left_out": left_out, "gained": gained, "lost": lost}
