"""The parameters in which two configs differ (task T079): `config_differences` of
`src/wixqa_rag/runs.py`.

Covers:

- spec.md, FR-023, and Principle VI of the constitution: an experiment run differs from its
  baseline in exactly one parameter;
- research.md, section 9, and data-model.md, "Identity and config": a parameter is a leaf of
  the config, named by the path of keys to it joined with dots; objects are descended into;
  a list, a text, a number, a truth value and `null` are leaves; `experiment` is not
  compared; two configs differ in a parameter when its value differs or when only one of
  them has it;
- contracts/harness.md, "`wixqa_rag.runs`": `config_differences(first_config,
  second_config)` gives "the parameters in which two configs differ, as a sorted list of
  dotted paths".

The configs are those of the example registries under `tests/data/`, read here with `json`,
and changed copies of them. All documents named here are in specs/002-evaluation-harness/.
"""

import copy
import importlib
import json
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "data"

RUN_A = "20261101T100000Z-example-a"
RUN_B = "20261102T100000Z-example-b"
RUN_C = "20261103T100000Z-example-c"


def load_runs():
    """Import the module; it fails while `src/wixqa_rag/runs.py` does not exist (plan.md,
    "Project Structure")."""
    return importlib.import_module("wixqa_rag.runs")


def config_of(run: str, registry: str = "runs") -> dict:
    document = json.loads((DATA / registry / run / "run.json").read_text(encoding="utf-8"))
    return document["config"]


def differences(first: dict, second: dict) -> list[str]:
    found = load_runs().config_differences(first, second)
    assert isinstance(found, list), "contracts/harness.md: a sorted list of dotted paths"
    return found


def changed(config: dict, change) -> dict:
    other = copy.deepcopy(config)
    change(other)
    return other


# --- The configs of the example registries -----------------------------------------------------


def test_a_config_does_not_differ_from_itself():
    """Two equal configs differ in no parameter."""
    config = config_of(RUN_A)

    assert differences(config, copy.deepcopy(config)) == []


def test_the_experiment_of_the_example_differs_in_the_one_parameter_it_names():
    """data-model.md, "Example data": `example-b` differs from `example-a` in
    `reranking.enabled`. Its `experiment` object differs too and is not compared."""
    assert config_of(RUN_A)["experiment"] != config_of(RUN_B)["experiment"]

    assert differences(config_of(RUN_A), config_of(RUN_B)) == ["reranking.enabled"]
    assert differences(config_of(RUN_B), config_of(RUN_A)) == ["reranking.enabled"]


def test_the_record_with_two_changes_differs_in_two_parameters():
    """data-model.md, `two-changes`: `reranking.enabled` and `retrieval.top_k` (AC-026)."""
    two_changes = config_of("20261101T100600Z-two-changes", "runs-invalid")

    assert differences(config_of(RUN_A), two_changes) == ["reranking.enabled", "retrieval.top_k"]


def test_two_runs_on_different_sets_differ_in_the_leaves_of_the_question_set():
    """research.md, section 9: objects are descended into. `example-a` and `example-c` are
    on different question sets: the version, the role and the fingerprint are three leaves."""
    assert differences(config_of(RUN_A), config_of(RUN_C)) == [
        "question_set.fingerprint",
        "question_set.role",
        "question_set.version",
    ]


# --- A leaf whose value differs ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("change", "path"),
    [
        (lambda config: config.update(index="harness-2"), "index"),
        (lambda config: config.update(concurrency=4), "concurrency"),
        (lambda config: config["retrieval"].update(top_k=5), "retrieval.top_k"),
        (lambda config: config["context"].update(max_articles=3), "context.max_articles"),
        (lambda config: config["limits"].update(timeout_seconds=30), "limits.timeout_seconds"),
        (lambda config: config["models"].update(generation="other-model"), "models.generation"),
        (lambda config: config["prompts"].update(generation="Answer."), "prompts.generation"),
        (lambda config: config["dataset"].update(revision="0" * 40), "dataset.revision"),
        (lambda config: config["reranking"].update(enabled=None), "reranking.enabled"),
    ],
)
def test_a_leaf_whose_value_differs_is_named_by_its_dotted_path(change, path):
    """research.md, section 9: a text, a number, a truth value and `null` are leaves, named
    by the path of keys joined with dots: `retrieval.top_k`."""
    config = config_of(RUN_A)

    assert differences(config, changed(config, change)) == [path]
    assert differences(changed(config, change), config) == [path]


def test_a_leaf_deep_inside_objects_is_named_by_its_whole_path():
    """ "Objects are descended into", however deep they are."""
    config = config_of(RUN_A)
    config["retrieval"]["hybrid"] = {"weights": {"dense": 0.5, "keyword": 0.5}}

    def change(other):
        other["retrieval"]["hybrid"]["weights"]["dense"] = 0.7

    assert differences(config, changed(config, change)) == ["retrieval.hybrid.weights.dense"]


# --- A list is one leaf -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "change",
    [
        lambda config: config["prices"][0].update(usd_per_million_input_tokens=3.0),
        lambda config: config["prices"].append(
            {
                "model": "other-model",
                "usd_per_million_input_tokens": 0.5,
                "usd_per_million_output_tokens": 1.5,
            }
        ),
        lambda config: config["prices"].clear(),
    ],
    ids=["a price inside the list", "an entry more", "an empty list"],
)
def test_a_list_is_one_leaf(change):
    """research.md, section 9: "a list ... [is a leaf]", so "a change of the price list ...
    is one parameter": `prices`, and never `prices.0.usd_per_million_input_tokens`."""
    config = config_of(RUN_A)

    assert differences(config, changed(config, change)) == ["prices"]


def test_a_list_inside_an_object_is_one_leaf():
    """The same for a list below an object: its path, and nothing beyond it."""
    config = config_of(RUN_A)
    config["retrieval"]["article_types"] = ["article", "known_issue"]

    def change(other):
        other["retrieval"]["article_types"] = ["known_issue", "article"]

    assert differences(config, changed(config, change)) == ["retrieval.article_types"]


# --- A leaf that only one config has ------------------------------------------------------------


@pytest.mark.parametrize(
    ("change", "path"),
    [
        (lambda config: config["retrieval"].update(method="hybrid"), "retrieval.method"),
        (lambda config: config["seeds"].update(generation=7), "seeds.generation"),
        (lambda config: config["retrieval"].pop("top_k"), "retrieval.top_k"),
        (lambda config: config.pop("index"), "index"),
        (lambda config: config["reranking"].update(model=None), "reranking.model"),
    ],
)
def test_a_leaf_that_only_one_config_has_is_a_difference(change, path):
    """research.md, section 9: "Two configs differ in a parameter when its value differs or
    when only one of them has it", in whichever of the two it is, also when its value is
    `null`."""
    config = config_of(RUN_A)

    assert differences(config, changed(config, change)) == [path]
    assert differences(changed(config, change), config) == [path]


def test_an_object_that_only_one_config_has_is_named_by_its_leaves():
    """Objects are descended into: the leaves of an object that one config lacks are the
    parameters that only the other has."""
    config = config_of(RUN_A)

    def change(other):
        other["retrieval"]["hybrid"] = {"dense": 0.5, "keyword": 0.5}

    assert differences(config, changed(config, change)) == [
        "retrieval.hybrid.dense",
        "retrieval.hybrid.keyword",
    ]


# --- `experiment` is not compared ---------------------------------------------------------------


@pytest.mark.parametrize(
    "experiment",
    [
        None,
        {"baseline": RUN_A, "parameter": "retrieval.top_k", "baseline_value": 3, "value": 5},
        {"baseline": RUN_C, "parameter": "index", "baseline_value": "a", "value": "b"},
    ],
)
def test_experiment_is_not_compared(experiment):
    """data-model.md: "`config.experiment` is not part of the comparison": whatever the two
    objects hold, no path starts with `experiment`."""
    first, second = config_of(RUN_A), config_of(RUN_B)
    second["experiment"] = experiment

    assert differences(first, second) == ["reranking.enabled"]


def test_a_config_without_the_key_experiment_does_not_differ_in_it():
    """The same when one config does not have the key at all."""
    config = config_of(RUN_B)

    assert differences(config, changed(config, lambda other: other.pop("experiment"))) == []


# --- Several differences ------------------------------------------------------------------------


def test_several_differences_are_given_as_a_sorted_list():
    """contracts/harness.md: "as a sorted list of dotted paths"."""
    config = config_of(RUN_A)

    def change(other):
        other["retrieval"]["top_k"] = 9
        other["concurrency"] = 2
        other["reranking"]["enabled"] = True
        other["seeds"]["generation"] = 1
        other["prices"][0]["usd_per_million_output_tokens"] = 4.0
        other["limits"]["max_calls"] = 8

    found = differences(config, changed(config, change))

    assert found == [
        "concurrency",
        "limits.max_calls",
        "prices",
        "reranking.enabled",
        "retrieval.top_k",
        "seeds.generation",
    ]
    assert found == sorted(found)


def test_the_two_configs_are_left_as_they_were():
    """The function reads its arguments and does not change them."""
    first, second = config_of(RUN_A), config_of(RUN_B)

    differences(first, second)

    assert first == config_of(RUN_A)
    assert second == config_of(RUN_B)
