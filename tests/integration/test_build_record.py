"""The build record (tasks T041): the file `build.json` and the record inside the index.

Covers:

- FR-010 and User Story 2, scenario 2; SC-005: the cost can be read from the record;
- contracts/records.md, "`build.json`": every field;
- data-model.md, "Build record": the place of the file with and without `--data-dir`, the
  rules of `cost_usd` and `articles`, written once, the same document in the `build` table;
- FR-017: neither the record nor the output of a build contains the value of a setting.

The tests call the build with the embedder double, as tests/integration/test_index_build.py
describes it, in a temporary repository root that is a Git checkout of its own; no record is
written under `evals/` of the repository. Every test is marked `store`. All documents named
here are in specs/001-corpus-and-audit/.
"""

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta

import pytest

pytestmark = pytest.mark.store

# contracts/records.md, "`build.json`": the fields of a build record.
RECORD_FIELDS = {
    "index",
    "dataset",
    "embedding",
    "splitting",
    "articles",
    "passages",
    "articles_without_passages",
    "tokens_embedded",
    "price_usd_per_million_tokens",
    "cost_usd",
    "started_at",
    "commit",
    "uncommitted_changes",
}

# An invented value, to see that the key of the provider reaches no record and no output.
INVENTED_KEY = "invented-key-value-that-is-never-recorded-3d91b7"


def read_record(file) -> dict:
    return json.loads(file.read_text(encoding="utf-8"))


def built_from_the_example(store, build, build_root, examples, embedder=None):
    """Build an index from `tests/data/example` and return its identifier and its record."""
    index = store.new_index()
    built = build(index, examples / "example", embedder)
    assert built.exit_code == 0, "\n".join(built.lines)
    return index, read_record(build_root.record_file(index, with_data_dir=True)), built


# --- Every field (contracts/records.md, "`build.json`") ---------------------------------------


def test_the_record_has_the_fields_of_the_contract(store, build, build_root, examples):
    """contracts/records.md, "`build.json`": one JSON document with the fields of the table,
    and the nested fields of `dataset`, `embedding` and `splitting`."""
    _, record, _ = built_from_the_example(store, build, build_root, examples)

    assert set(record) == RECORD_FIELDS
    assert set(record["dataset"]) == {"name", "revision", "corpus_sha256"}
    assert set(record["embedding"]) == {
        "provider",
        "model_requested",
        "model_reported",
        "dimensions",
    }
    assert set(record["splitting"]) == {"rule", "max_chars"}


def test_the_record_names_the_index_and_the_dataset(store, build, build_root, examples):
    """contracts/records.md: `index`; `dataset.name` and `dataset.revision` from the manifest
    (null for a dataset that is not published); `dataset.corpus_sha256`, the fingerprint of
    the corpus file the index was built from."""
    index, record, _ = built_from_the_example(store, build, build_root, examples)
    corpus = (examples / "example" / "ex.jsonl").read_bytes()

    assert record["index"] == index
    assert record["dataset"] == {
        "name": "example",
        "revision": None,
        "corpus_sha256": hashlib.sha256(corpus).hexdigest(),
    }


def test_the_record_names_the_model_as_requested_and_as_reported(
    store, build, build_root, examples, embedder_double
):
    """FR-010 and contracts/records.md: `embedding.model_requested` is the model name sent to
    the provider, and `embedding.model_reported` the name in the provider's responses, the
    most specific identifier the provider offers; `provider` and `dimensions` are those of
    the embedder."""
    double = embedder_double(reported="embedder-double-as-reported")

    _, record, _ = built_from_the_example(store, build, build_root, examples, double)

    assert record["embedding"] == {
        "provider": "embedder-double",
        "model_requested": "embedder-double",
        "model_reported": "embedder-double-as-reported",
        "dimensions": 1536,
    }


def test_the_record_names_the_splitting_rule_and_its_parameters(store, build, build_root, examples):
    """FR-010 and contracts/records.md: `splitting.rule` and every parameter of the rule; for
    `line-pack-v1` this is `max_chars` (data-model.md, "Passage": 2000)."""
    _, record, _ = built_from_the_example(store, build, build_root, examples)

    assert record["splitting"] == {"rule": "line-pack-v1", "max_chars": 2000}


def test_the_record_counts_articles_and_passages(store, build, build_root, examples):
    """contracts/records.md: `articles` is the number of rows of the corpus part, `passages`
    the number of passages in the index, and `articles_without_passages` the sorted ids of
    the articles that produced no passage: none in the example."""
    index, record, _ = built_from_the_example(store, build, build_root, examples)

    assert record["articles"] == 5
    assert record["passages"] == len(store.passages(index)) == 5
    assert record["articles_without_passages"] == []


def test_the_record_states_tokens_price_and_cost(
    store, build, build_root, examples, embedder_double
):
    """FR-010, SC-005 and data-model.md, "Build record": `tokens_embedded` is the sum of the
    token counts that the embedder reported, `price_usd_per_million_tokens` the price used,
    and `cost_usd` = `tokens_embedded` × `price_usd_per_million_tokens` ÷ 1,000,000. The
    printed cost is that of the record."""
    double = embedder_double()

    _, record, built = built_from_the_example(store, build, build_root, examples, double)

    assert double.tokens > 0
    assert record["tokens_embedded"] == double.tokens
    assert type(record["tokens_embedded"]) is int
    assert record["price_usd_per_million_tokens"] == 0.5
    assert record["cost_usd"] == pytest.approx(double.tokens * 0.5 / 1_000_000, rel=1e-9)
    assert built.value_of("tokens embedded") == str(double.tokens)
    assert built.value_of("cost_usd") == f"{record['cost_usd']:.8f}"


def test_the_record_states_the_start_time_in_utc(store, build, build_root, examples):
    """FR-010 and contracts/records.md: `started_at`, the time the build started, in UTC in
    the form `2026-11-24T10:15:00Z`."""
    before = datetime.now(UTC).replace(microsecond=0)
    _, record, _ = built_from_the_example(store, build, build_root, examples)
    after = datetime.now(UTC)

    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", record["started_at"])
    started = datetime.strptime(record["started_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    assert before - timedelta(seconds=1) <= started <= after + timedelta(seconds=1)


def test_the_record_names_the_commit_of_the_code(store, build, build_root, examples):
    """FR-010 and contracts/records.md: `commit`, the commit of the code as a full hash, and
    `uncommitted_changes`, false when the working tree is that commit. The commit is that of
    the checkout the command runs in: here the temporary repository root."""
    _, record, _ = built_from_the_example(store, build, build_root, examples)

    assert re.fullmatch(r"[0-9a-f]{40}", record["commit"])
    assert record["commit"] == build_root.commit
    assert record["uncommitted_changes"] is False


def test_the_record_says_when_the_working_tree_differed_from_the_commit(
    store, build, build_root, examples
):
    """contracts/records.md: `uncommitted_changes` is true when the working tree differed
    from the commit. A file of the commit was changed and not committed."""
    build_root.tracked_file.write_text("Changed after the commit.\n", encoding="utf-8")

    _, record, _ = built_from_the_example(store, build, build_root, examples)

    assert record["commit"] == build_root.commit
    assert record["uncommitted_changes"] is True


# --- The place of the file (data-model.md, "Build record") ------------------------------------


def test_with_data_dir_the_record_is_kept_under_data(store, build, build_root, examples):
    """data-model.md, "Build record": for a build with `--data-dir` the file is
    `data/indexes/<index>/build.json`, outside version control; nothing is written under
    `evals/`. The folder of the index holds the record and nothing else: the temporary name
    under which the record was written is gone."""
    index = store.new_index()

    built = build(index, examples / "example")

    assert built.exit_code == 0, "\n".join(built.lines)
    assert built.value_of("build record") == f"data/indexes/{index}/build.json"
    assert list(build_root.files_below("data/indexes")) == [f"data/indexes/{index}/build.json"]
    assert build_root.files_below("evals") == {}


def test_without_data_dir_the_record_is_kept_under_evals(store, build, build_root):
    """data-model.md, "Build record": for a build from the pinned dataset, which is a build
    without `--data-dir`, the file is `evals/indexes/<index>/build.json`. The dataset of the
    record is the pinned one: its name, its revision and the fingerprint of its corpus file.
    The build reads the default data directory of the temporary repository root."""
    index = store.new_index()
    example = build_root.example

    built = build(index)

    assert built.exit_code == 0, "\n".join(built.lines)
    assert built.value_of("build record") == f"evals/indexes/{index}/build.json"
    assert built.value_of("dataset") == "Wix/WixQA"
    assert built.value_of("revision") == example.revision
    assert list(build_root.files_below("evals")) == [f"evals/indexes/{index}/build.json"]
    assert build_root.files_below("data/indexes") == {}
    record = read_record(build_root.record_file(index, with_data_dir=False))
    assert record["index"] == index
    assert record["dataset"] == {
        "name": "Wix/WixQA",
        "revision": example.revision,
        "corpus_sha256": hashlib.sha256(example.sources["ex/ex.jsonl"]).hexdigest(),
    }
    assert record["articles"] == 5


def test_the_default_data_directory_named_with_data_dir_records_under_data(
    store, build, build_root
):
    """contracts/cli.md, "`index build`": "With `--data-dir` the build record goes to
    `data/indexes/ID/build.json`", also when the directory named is the default one."""
    index = store.new_index()

    built = build(index, build_root.example.data_dir)

    assert built.exit_code == 0, "\n".join(built.lines)
    assert list(build_root.files_below("data/indexes")) == [f"data/indexes/{index}/build.json"]
    assert build_root.files_below("evals") == {}


# --- The record in the store equals the file --------------------------------------------------


@pytest.mark.parametrize("with_data_dir", [True, False], ids=["with --data-dir", "without"])
def test_the_record_in_the_store_equals_the_file(store, build, build_root, examples, with_data_dir):
    """contracts/records.md, "`build.json`": "The same document is stored in the `build` table
    of the index." data-model.md, "Index": `record` of the one `build` row."""
    index = store.new_index()

    built = build(index, examples / "example" if with_data_dir else None)

    assert built.exit_code == 0, "\n".join(built.lines)
    rows = store.build_rows(index)
    assert len(rows) == 1
    record = read_record(build_root.record_file(index, with_data_dir=with_data_dir))
    assert rows[0].record == record
    assert set(rows[0].record) == RECORD_FIELDS


def test_the_record_is_one_json_document_in_utf8(store, build, build_root, examples):
    """contracts/records.md: every file is UTF-8 text and holds one JSON document."""
    index = store.new_index()

    assert build(index, examples / "example").exit_code == 0

    data = build_root.record_file(index, with_data_dir=True).read_bytes()
    assert isinstance(json.loads(data.decode("utf-8")), dict)


# --- No value of a setting (FR-017) -----------------------------------------------------------


def test_neither_the_record_nor_the_output_contains_the_value_of_a_setting(
    store, build, build_root, examples, monkeypatch
):
    """FR-017 and contracts/cli.md, "Settings": no value of a setting is written to a record,
    and a command never prints one, on either output stream. The build has both settings in
    its environment: the address of the store, and an invented key."""
    import os

    monkeypatch.setenv("OPENAI_API_KEY", INVENTED_KEY)
    values = {name: os.environ[name] for name in ("DATABASE_URL", "OPENAI_API_KEY")}
    index = store.new_index()

    built = build(index, examples / "example")

    assert built.exit_code == 0, "\n".join(built.lines)
    assert built.settings_printed == (), "the build printed the value of a setting"
    texts = {
        "the record file": build_root.record_file(index, with_data_dir=True).read_text("utf-8"),
        "the record in the store": json.dumps(store.build_rows(index)[0].record),
    }
    # Only names are reported, so that a failure of this test shows no value either.
    found = sorted(
        f"the value of {name} in {place}"
        for place, text in texts.items()
        for name, value in values.items()
        if value in text
    )
    assert found == []
