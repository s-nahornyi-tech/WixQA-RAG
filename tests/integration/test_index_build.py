"""The build of an index against a real store, with the embedder double (tasks T040).

Covers:

- FR-006 to FR-009 and User Story 2, scenarios 1, 3, 4 and 5;
- data-model.md, "Index" (identifier, schema, the two tables, one transaction, the `build`
  row as the mark of completion) and "Passage";
- research.md, section 15: every row of the table of what `index build` decides;
- contracts/cli.md, "`index build`": the order of the steps, the lines of a build and of an
  index that is already complete, the reasons, the verdicts and exit code 2;
- the edge cases "an article has no text" and "a credential is missing"; FR-005.

The command line always calls the provider (research.md, section 17), so these tests call the
build directly and pass the embedder to it. They need one name from `src/wixqa_rag/index.py`:

    build(index: str, data_dir: Path | None, embedder) -> int

`build` is the work of the command `index build`: it is called through `carry_out` of
`src/wixqa_rag/cli.py`, in the repository root as the current directory; it prints the lines
of contracts/cli.md and returns the exit code. `data_dir` is None for a build without
`--data-dir`. `embedder` is an embedder as tests/unit/test_embedding.py describes it: the
build reads its `provider`, `model`, `dimensions` and `price_usd_per_million_tokens`, and it
calls `embed` only when passages have to be embedded (step 5).

Every test is marked `store`: it needs the PostgreSQL that `DATABASE_URL` names. Each test
builds under identifiers of its own and works in a temporary repository root (the fixtures
of tests/integration/conftest.py). All documents named here are in
specs/001-corpus-and-audit/.
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.store

EXAMPLE_ARTICLE_IDS = ["ex-001", "ex-002", "ex-003", "ex-004", "ex-005"]


def files_of(directory: Path) -> dict[str, bytes]:
    return {
        file.relative_to(directory).as_posix(): file.read_bytes()
        for file in sorted(directory.rglob("*"))
        if file.is_file()
    }


def copy_with_articles(source: Path, target: Path, change) -> Path:
    """A copy of an example directory whose articles were changed; its manifest is written
    again from its files, so the copy passes the dataset check."""
    shutil.copytree(source, target)
    lines = (target / "ex.jsonl").read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    change(rows)
    data = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode("utf-8")
    (target / "ex.jsonl").write_bytes(data)
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    for part in manifest["parts"]:
        if part["name"] == "ex":
            part.update(rows=len(rows), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return target


def assert_done(built) -> None:
    assert built.exit_code == 0, (
        'contracts/cli.md, "`index build`": a build that did its work ends with exit code 0; '
        f"got {built.exit_code}. Standard output:\n" + "\n".join(built.lines)
    )
    assert built.last_line == "index build: done"


def assert_stopped(built, verdict: str) -> str:
    """Exit code 2, the verdict `refused` or `not carried out` last, and the reason before it."""
    assert built.exit_code == 2, (
        f'contracts/cli.md, "`index build`": `{verdict}` ends with exit code 2; got '
        f"{built.exit_code}. Standard output:\n" + "\n".join(built.lines)
    )
    assert built.last_line == f"index build: {verdict}", "\n".join(built.lines)
    assert len(built.reasons) == 1, (
        'contracts/cli.md, "Output", rule 5: the reason is printed on a line that starts with '
        "`reason:`; got:\n" + "\n".join(built.lines)
    )
    return built.reasons[0]


# --- A build (research.md, section 15, last row: no index, no record file) -------------------


def test_a_build_stores_a_passage_for_every_article_with_the_id_of_its_article(
    store, build, examples, expected_passages, double_helpers
):
    """FR-007 and User Story 2, scenario 1: every article of the corpus has at least one
    passage in the index, and every passage carries the `id` of its article. data-model.md,
    "Passage": `passage_no` counts from 0, `text` is not empty, and `embedding` is what the
    embedder returned for `text`."""
    index = store.new_index()
    expected = expected_passages(examples / "example")

    assert_done(build(index, examples / "example"))

    passages = store.passages(index)
    assert store.article_ids(index) == EXAMPLE_ARTICLE_IDS
    assert [(passage.article_id, passage.passage_no) for passage in passages] == [
        (article, 0) for article in EXAMPLE_ARTICLE_IDS
    ]
    for passage in passages:
        assert passage.text == expected[passage.article_id], passage.article_id
        assert passage.vector == double_helpers.vector_of(passage.text), (
            f"the vector stored for {passage.article_id} is not the one the embedder returned"
        )


def test_a_build_prints_the_lines_of_the_contract(
    store, build, examples, expected_passages, double_helpers, embedder_double
):
    """contracts/cli.md, "`index build`", output of a build. `cost_usd` is printed with eight
    digits after the decimal point; the double reports one token for each word at 0.5 US
    dollars per million tokens."""
    index = store.new_index()
    passages = expected_passages(examples / "example").values()
    tokens = sum(double_helpers.tokens_of(text) for text in passages)
    double = embedder_double()

    built = build(index, examples / "example", double)

    assert_done(built)
    assert double.tokens == tokens
    assert built.lines == [
        f"index: {index}",
        "dataset: example",
        "revision: none",
        "embedding model: embedder-double",
        "splitting rule: line-pack-v1 (max_chars=2000)",
        "articles: 5",
        "passages: 5",
        "articles without passages: 0",
        f"tokens embedded: {tokens}",
        f"cost_usd: {tokens * 0.5 / 1_000_000:.8f}",
        f"build record: data/indexes/{index}/build.json",
        "index build: done",
    ]


def test_the_passages_are_embedded_as_the_splitting_rule_gives_them(
    store, build, examples, expected_passages, embedder_double
):
    """research.md, section 12: "The text of a passage is what is embedded and what is stored,
    with nothing added." The embedder is asked for exactly the passages, each once."""
    index = store.new_index()
    double = embedder_double()

    assert_done(build(index, examples / "example", double))

    assert sorted(double.texts) == sorted(expected_passages(examples / "example").values())
    assert sorted(passage.text for passage in store.passages(index)) == sorted(double.texts)


def test_a_long_article_is_stored_as_several_passages_numbered_from_0(
    store, build, examples, tmp_path
):
    """data-model.md, "Passage": `passage_no` is the position within the article, counted
    from 0, and `text` has at most 2,000 characters. An article of three lines of 1,500
    characters gives three passages (research.md, section 12, step 4)."""

    def lengthen(rows):
        rows[1]["contents"] = "\n".join(letter * 1500 for letter in "abc")

    directory = copy_with_articles(examples / "example", tmp_path / "long-article", lengthen)
    index = store.new_index()

    built = build(index, directory)

    assert_done(built)
    assert built.value_of("articles") == "5"
    assert built.value_of("passages") == "7"
    of_the_article = [p for p in store.passages(index) if p.article_id == "ex-002"]
    assert [passage.passage_no for passage in of_the_article] == [0, 1, 2]
    assert [passage.text for passage in of_the_article] == ["a" * 1500, "b" * 1500, "c" * 1500]


def test_an_index_has_the_two_tables_of_the_data_model(store, build, examples):
    """data-model.md, "Index", "In the store": one schema per index, named `idx_` and the
    identifier with each hyphen replaced by an underscore, with the tables `passages` and
    `build`. The embedding is a `vector(1536)` of the pgvector extension, which the build
    enables."""
    index = store.new_index("with-hyphens")
    assert "-" in index

    assert_done(build(index, examples / "example"))

    assert store.holds(index)
    assert store.tables(index) == {"passages", "build"}
    assert store.columns(index, "passages") == {
        "article_id": "text",
        "passage_no": "integer",
        "text": "text",
        "embedding": "vector(1536)",
    }
    assert store.columns(index, "build") == {
        "only_row": "boolean",
        "record": "jsonb",
        "completed_at": "timestamp with time zone",
    }


def test_a_complete_index_has_exactly_one_build_row(store, build, examples):
    """FR-009 and data-model.md, "Index": the `build` table holds at most one row; the row is
    the mark of completion, and `record` is the build record."""
    index = store.new_index()

    assert_done(build(index, examples / "example"))

    rows = store.build_rows(index)
    assert len(rows) == 1
    assert rows[0].only_row is True
    assert rows[0].completed_at is not None
    assert rows[0].record["index"] == index
    assert rows[0].record["articles"] == 5


def test_nothing_of_a_build_is_visible_before_its_end(store, build, examples, embedder_double):
    """data-model.md, "Index": a build is one transaction; the `build` row is inserted last,
    and "until the commit, no other connection sees any of it". While the embedder is asked,
    the connection of the test sees no schema of the index."""
    index = store.new_index()
    seen_during_the_build = []
    double = embedder_double(on_call=lambda: seen_during_the_build.append(store.holds(index)))

    assert_done(build(index, examples / "example", double))

    assert seen_during_the_build, "the embedder was asked at least once"
    assert not any(seen_during_the_build), "another connection saw the index before the commit"
    assert store.holds(index)


# --- A build that stops in the middle ---------------------------------------------------------


def test_a_build_that_stops_at_the_embedder_leaves_no_schema(
    store, build, build_root, examples, embedder_double
):
    """FR-009 and data-model.md, "Index": a build that stops for any reason is rolled back,
    and the identifier stays absent. contracts/cli.md: an error of the provider ends as
    `index build: not carried out`; afterwards the store holds exactly the indexes it held
    before, and no build record file was written. The double fails at the fourth passage."""
    index = store.new_index()
    before = store.indexes()

    built = build(index, examples / "example", embedder_double(fail_at_text=4))

    assert_stopped(built, "not carried out")
    assert not store.holds(index)
    assert store.indexes() == before
    assert build_root.files_below("data/indexes") == {}
    assert build_root.files_below("evals") == {}


def test_a_build_that_stops_at_the_store_leaves_no_schema(
    store, build, build_root, examples, embedder_double
):
    """FR-009: a build that stops part-way leaves nothing. The double returns a vector of
    1535 numbers for the last passage; the store refuses it after it accepted the passages
    before it, and the whole transaction is rolled back."""
    index = store.new_index()
    before = store.indexes()
    double = embedder_double(wrong_size_at_text=5)

    built = build(index, examples / "example", double)

    assert len(double.texts) == 5, "every passage was embedded before the store refused one"
    assert_stopped(built, "not carried out")
    assert not store.holds(index)
    assert store.indexes() == before
    assert build_root.files_below("data/indexes") == {}


def test_after_a_build_that_stopped_the_identifier_can_be_built(
    store, build, examples, embedder_double
):
    """data-model.md, "Index", "Life of an identifier": a build that stops is rolled back,
    and the identifier stays absent; a later build under it builds."""
    index = store.new_index()
    assert_stopped(
        build(index, examples / "example", embedder_double(fail_at_text=2)), "not carried out"
    )

    assert_done(build(index, examples / "example"))

    assert store.article_ids(index) == EXAMPLE_ARTICLE_IDS


# --- The decision table of research.md, section 15 --------------------------------------------


def test_row_1_complete_index_and_equal_record_file_is_reported_as_already_complete(
    store, build, build_root, examples, embedder_double
):
    """research.md, section 15, row 1 (FR-008; User Story 2, scenario 3): the index is
    complete, the record file equals the record in the store, corpus and settings are the
    same → the build reports the index as already complete and embeds nothing. The lines
    are those of contracts/cli.md; the record file is not written again (FR-010)."""
    index = store.new_index()
    assert_done(build(index, examples / "example"))
    record_file = build_root.record_file(index, with_data_dir=True)
    record_before = record_file.read_bytes()
    modified_before = record_file.stat().st_mtime_ns
    passages_before = store.passages(index)
    second = embedder_double()

    built = build(index, examples / "example", second)

    assert_done(built)
    assert built.lines == [
        f"index: {index} (already complete)",
        "articles: 5",
        "passages: 5",
        "tokens embedded: 0",
        f"build record: data/indexes/{index}/build.json",
        "index build: done",
    ]
    assert built.embedded == [], "an index that is already complete embeds nothing"
    assert second.texts == []
    assert record_file.read_bytes() == record_before
    assert record_file.stat().st_mtime_ns == modified_before, "a record is written once"
    assert store.passages(index) == passages_before
    assert len(store.build_rows(index)) == 1


def test_row_2_complete_index_without_record_file_gets_the_file_from_the_store(
    store, build, build_root, examples
):
    """research.md, section 15, row 2: the index is complete and the record file is absent →
    the build writes the file from the record in the store and reports the index as already
    complete."""
    index = store.new_index()
    assert_done(build(index, examples / "example"))
    record_file = build_root.record_file(index, with_data_dir=True)
    record_before = json.loads(record_file.read_text(encoding="utf-8"))
    record_file.unlink()

    built = build(index, examples / "example")

    assert_done(built)
    assert built.lines[0] == f"index: {index} (already complete)"
    assert built.value_of("tokens embedded") == "0"
    assert built.embedded == []
    assert json.loads(record_file.read_text(encoding="utf-8")) == record_before
    assert json.loads(record_file.read_text(encoding="utf-8")) == store.build_rows(index)[0].record


def test_row_3_record_file_that_differs_from_the_store_is_refused(
    store, build, build_root, examples
):
    """research.md, section 15, row 3: the index is complete and the record file differs from
    the record in the store → refused: the file and the index do not belong together.
    contracts/cli.md: `reason: <file> does not match the index <ID> in the store`."""
    index = store.new_index()
    assert_done(build(index, examples / "example"))
    record_file = build_root.record_file(index, with_data_dir=True)
    record = json.loads(record_file.read_text(encoding="utf-8"))
    record["tokens_embedded"] += 1
    record_file.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    changed_file = record_file.read_bytes()
    row_before = store.build_rows(index)

    built = build(index, examples / "example")

    reason = assert_stopped(built, "refused")
    assert index in reason, f"the reason names the index: {reason}"
    assert "build.json" in reason, f"the reason names the record file: {reason}"
    assert built.embedded == []
    assert record_file.read_bytes() == changed_file, "a refused build writes no record file"
    assert store.build_rows(index) == row_before


def test_row_4_another_corpus_under_an_existing_identifier_is_refused(
    store, build, build_root, examples
):
    """research.md, section 15, row 4 (FR-008; User Story 2, scenario 4; AC-006 with the
    double): the index is complete and the corpus differs → refused, and the existing index is
    unchanged. contracts/cli.md: `reason: index <ID> exists with another corpus`."""
    index = store.new_index()
    assert_done(build(index, examples / "example"))
    record_before = build_root.files_below("data/indexes")
    passages_before = store.passages(index)

    built = build(index, examples / "example-one-more-article")

    reason = assert_stopped(built, "refused")
    assert index in reason and "another corpus" in reason, reason
    assert built.embedded == []
    assert store.passages(index) == passages_before
    assert store.article_ids(index) == EXAMPLE_ARTICLE_IDS
    assert build_root.files_below("data/indexes") == record_before


def test_row_4_other_settings_under_an_existing_identifier_are_refused(
    store, build, build_root, examples, embedder_double
):
    """research.md, section 15, row 4: the index is complete and the settings differ →
    refused. "Same corpus and settings" includes the embedding model; here the same corpus
    is built with an embedder of another model name. contracts/cli.md:
    `reason: index <ID> exists with other settings`."""
    index = store.new_index()
    assert_done(build(index, examples / "example"))
    record_before = build_root.files_below("data/indexes")
    passages_before = store.passages(index)
    other = embedder_double(model="embedder-double-of-another-model")

    built = build(index, examples / "example", other)

    reason = assert_stopped(built, "refused")
    assert index in reason and "other settings" in reason, reason
    assert other.texts == [], "a refused build embeds nothing"
    assert store.passages(index) == passages_before
    assert build_root.files_below("data/indexes") == record_before


def test_row_4_the_command_line_refuses_an_index_of_the_double_without_the_provider_key(
    store, build, build_root, examples, run_command
):
    """research.md, section 15, row 4, through the command line; contracts/cli.md,
    "`index build`", steps 4 and 5: the store decides before the key is asked for. The index
    was built with the double, the command line builds with `text-embedding-3-small`: other
    settings, refused, and `OPENAI_API_KEY` is not needed for that answer."""
    index = store.new_index()
    assert_done(build(index, examples / "example"))
    passages_before = store.passages(index)

    result = run_command(
        f"python -m wixqa_rag index build --index {index} --data-dir {examples / 'example'}",
        env={"OPENAI_API_KEY": None},
        cwd=build_root.root,
    )

    assert result.exit_code == 2
    assert result.last_line == "index build: refused"
    reasons = [line for line in result.lines if line.startswith("reason: ")]
    assert len(reasons) == 1 and index in reasons[0] and "other settings" in reasons[0]
    assert result.settings_printed == ()
    assert store.passages(index) == passages_before


def test_row_5_a_schema_without_its_build_row_is_refused(store, build, build_root, examples):
    """research.md, section 15, row 5 (FR-009; data-model.md, "Index"): a schema without its
    `build` row is not complete, and a build under its identifier is refused.
    contracts/cli.md: `reason: index <ID> exists and is not complete`."""
    index = store.new_index()
    store.make_schema_without_build_row(index)

    built = build(index, examples / "example")

    reason = assert_stopped(built, "refused")
    assert index in reason and "not complete" in reason, reason
    assert built.embedded == []
    assert store.tables(index) == set(), "the schema that was made by hand is as it was"
    assert build_root.files_below("data/indexes") == {}


def test_row_6_a_record_file_without_its_index_is_refused(store, build, build_root, examples):
    """research.md, section 15, row 6: the store does not hold the index and a record file
    exists → refused; a build never overwrites a build record (FR-010). contracts/cli.md:
    `reason: <file> records a build of <ID>, and the store does not hold that index`."""
    index = store.new_index()
    record_file = build_root.record_file(index, with_data_dir=True)
    record_file.parent.mkdir(parents=True)
    record_file.write_text(json.dumps({"index": index}) + "\n", encoding="utf-8")
    left_behind = record_file.read_bytes()

    built = build(index, examples / "example")

    reason = assert_stopped(built, "refused")
    assert index in reason, f"the reason names the index: {reason}"
    assert "build.json" in reason, f"the reason names the record file: {reason}"
    assert built.embedded == []
    assert not store.holds(index)
    assert record_file.read_bytes() == left_behind


def test_row_6_holds_for_the_record_of_the_pinned_dataset(store, build, build_root):
    """research.md, section 15, row 6, for a build without `--data-dir`: the record file is
    `evals/indexes/<index>/build.json`. This row protects a paid job: when a restore failed
    without notice, the build must not embed the whole corpus again."""
    index = store.new_index()
    record_file = build_root.record_file(index, with_data_dir=False)
    record_file.parent.mkdir(parents=True)
    record_file.write_text(json.dumps({"index": index}) + "\n", encoding="utf-8")
    left_behind = record_file.read_bytes()

    built = build(index)

    assert_stopped(built, "refused")
    assert built.embedded == []
    assert not store.holds(index)
    assert record_file.read_bytes() == left_behind


def test_two_identifiers_are_two_indexes(store, build, examples):
    """research.md, section 8: nothing is shared between indexes. The same corpus built
    under a second identifier is a build of its own, and the first index is unchanged."""
    first = store.new_index("first")
    second = store.new_index("second")
    assert_done(build(first, examples / "example"))
    passages_before = store.passages(first)

    built = build(second, examples / "example-one-less-article")

    assert_done(built)
    assert built.embedded
    assert store.article_ids(second) == EXAMPLE_ARTICLE_IDS[:4]
    assert store.passages(first) == passages_before


# --- Step 1: the identifier (data-model.md, "Index") ------------------------------------------


@pytest.mark.parametrize(
    "identifier",
    [
        "Example",
        "with_underscore",
        "-starts-with-a-hyphen",
        "ends-with-a-hyphen-",
        "two--hyphens",
        "with space",
        "dot.inside",
        "x" * 41,
        "",
        "ünïcode",
    ],
)
def test_an_identifier_that_breaks_the_rule_is_not_carried_out(
    store, build, build_root, examples, identifier
):
    """data-model.md, "Index", "Identifier": lower-case letters, digits and single hyphens;
    it starts and ends with a letter or a digit; at most 40 characters. "A command given any
    other identifier is not carried out." contracts/cli.md:
    `reason: <ID> is not a valid index identifier`, `index build: not carried out`."""
    before = store.indexes()

    built = build(identifier, examples / "example")

    assert_stopped(built, "not carried out")
    assert built.embedded == []
    assert store.indexes() == before
    assert build_root.files_below("data/indexes") == {}


def test_an_identifier_of_40_characters_is_valid(store, build, examples):
    """data-model.md, "Index", "Identifier": at most 40 characters; digits and single hyphens
    are allowed, and an identifier may start with a digit."""
    index = store.new_index()
    index = store.register("0" + index + "-" + "9" * (40 - len(index) - 2))
    assert len(index) == 40

    assert_done(build(index, examples / "example"))

    assert store.article_ids(index) == EXAMPLE_ARTICLE_IDS


# --- Step 2: the data directory passes the dataset check (FR-006) -----------------------------


def test_a_data_directory_that_fails_the_dataset_check_is_refused(
    store, build, build_root, examples
):
    """FR-006 (AC-007 with a store at hand): an index is built only from a corpus that passes
    the dataset check. contracts/cli.md: the lines of the check, then
    `reason: the dataset check failed for <DIR>`, `index build: refused`."""
    index = store.new_index()

    built = build(index, examples / "example-damaged")

    reason = assert_stopped(built, "refused")
    assert "dataset check failed" in reason, reason
    assert any(line.startswith("difference: ") and "ex-002" in line for line in built.lines), (
        "the lines of the check come before the reason"
    )
    assert built.embedded == []
    assert not store.holds(index)
    assert build_root.files_below("data/indexes") == {}


# --- An article without text (spec.md, "Edge Cases") ------------------------------------------


def test_an_article_without_text_is_listed_and_is_not_in_the_index(
    store, build, build_root, examples, tmp_path
):
    """The edge case "an article has no text": the build reports every article that produced
    no passage, and such an article is not in the index. contracts/cli.md: the ids follow the
    line `articles without passages:`, one per line, indented by two spaces and sorted.
    data-model.md, "Build record": `articles` is the number of rows of the corpus part."""

    def empty_two(rows):
        rows[4]["contents"] = ""
        rows[2]["contents"] = "  \n\t\n \r\n"

    directory = copy_with_articles(examples / "example", tmp_path / "without-text", empty_two)
    index = store.new_index()

    built = build(index, directory)

    assert_done(built)
    assert built.value_of("articles") == "5"
    assert built.value_of("passages") == "3"
    place = built.lines.index("articles without passages: 2")
    assert built.lines[place + 1 : place + 3] == ["  ex-003", "  ex-005"]
    assert store.article_ids(index) == ["ex-001", "ex-002", "ex-004"]
    record = json.loads(build_root.record_file(index, with_data_dir=True).read_text("utf-8"))
    assert record["articles"] == 5
    assert record["passages"] == 3
    assert record["articles_without_passages"] == ["ex-003", "ex-005"]


# --- Step 3: the store (contracts/cli.md, "Settings") -----------------------------------------


def test_without_database_url_the_build_is_not_carried_out_and_names_the_variable(
    store, build, build_root, examples, monkeypatch
):
    """The edge case "a credential for the vector store is missing" and FR-017: the command
    is not carried out and names the missing setting. contracts/cli.md:
    `reason: the environment variable DATABASE_URL is not set`."""
    index = store.new_index()
    monkeypatch.delenv("DATABASE_URL")

    built = build(index, examples / "example")

    reason = assert_stopped(built, "not carried out")
    assert "DATABASE_URL" in reason
    assert built.embedded == []
    assert not store.holds(index)
    assert build_root.files_below("data/indexes") == {}


def test_a_store_that_cannot_be_reached_is_not_carried_out(
    store, build, build_root, examples, monkeypatch
):
    """contracts/cli.md, "`index build`": `reason: the vector store cannot be reached`,
    `index build: not carried out`. The value of `DATABASE_URL` appears on neither stream
    (FR-017). Nothing listens on port 1 of this machine."""
    index = store.new_index()
    unreachable = "postgresql://nobody@127.0.0.1:1/no-such-store-for-this-test?connect_timeout=5"
    monkeypatch.setenv("DATABASE_URL", unreachable)

    built = build(index, examples / "example")

    assert_stopped(built, "not carried out")
    assert built.settings_printed == (), "the value of DATABASE_URL was printed"
    assert built.embedded == []
    assert build_root.files_below("data/indexes") == {}


# --- The commit of the code -------------------------------------------------------------------


def test_outside_a_git_checkout_the_build_is_not_carried_out(
    store, build, build_root, examples, tmp_path, monkeypatch
):
    """contracts/cli.md, "`index build`": the commit of the code cannot be read, because the
    command does not run in a Git checkout → `reason: the commit of the code cannot be read`,
    `index build: not carried out`. Nothing is embedded for a record that could not name its
    commit. The folder has a `dataset.json` and is no checkout."""
    outside = tmp_path / "no-checkout"
    outside.mkdir()
    shutil.copyfile(build_root.root / "dataset.json", outside / "dataset.json")
    monkeypatch.chdir(outside)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    index = store.new_index()

    built = build(index, examples / "example")

    assert_stopped(built, "not carried out")
    assert built.embedded == [], "passages were embedded although the commit cannot be read"
    assert not store.holds(index)
    assert not list(outside.rglob("build.json"))


# --- FR-005: the data stays as it is ----------------------------------------------------------


def test_the_data_files_are_the_same_after_a_build(store, build, build_root, examples):
    """FR-005: no command changes a question, an answer or an article. The files of the
    example directory and of the default data directory have the same bytes after a build,
    after a second build and after a refused build."""
    example_before = files_of(examples / "example")
    default_before = build_root.example.stored_files()
    with_data_dir = store.new_index()
    without_data_dir = store.new_index()

    assert_done(build(with_data_dir, examples / "example"))
    assert_done(build(with_data_dir, examples / "example"))
    assert_stopped(build(with_data_dir, examples / "example-one-more-article"), "refused")
    assert_done(build(without_data_dir))

    assert files_of(examples / "example") == example_before
    assert build_root.example.stored_files() == default_before


# --- A passage that the store or the provider cannot take ------------------------------------

# U+0000, which PostgreSQL refuses in a text, and an unpaired surrogate, which cannot be sent
# as UTF-8. A JSON file carries them as `\u0000` and `\ud800`.
NUL = "\x00"
UNPAIRED_SURROGATE = "\ud800"


def copy_with_escaped_articles(source: Path, target: Path, articles: list[dict]) -> Path:
    """A copy of an example directory with the given articles. Every character outside ASCII
    is written as a JSON escape, so the file can carry U+0000 and an unpaired surrogate. The
    manifest is written again from the file, so the copy passes the dataset check."""
    shutil.copytree(source, target)
    data = "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in articles).encode("ascii")
    (target / "ex.jsonl").write_bytes(data)
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    for part in manifest["parts"]:
        if part["name"] == "ex":
            part.update(
                rows=len(articles), bytes=len(data), sha256=hashlib.sha256(data).hexdigest()
            )
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return target


def example_articles(examples: Path) -> list[dict]:
    lines = (examples / "example" / "ex.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def assert_nothing_was_embedded_or_left(built, double, store, build_root, index, before) -> None:
    assert double.calls == [], (
        f"the embedder was called {len(double.calls)} time(s) before the build stopped; every "
        "passage is checked before the first request"
    )
    assert not store.holds(index), "no schema is left"
    assert store.indexes() == before, "the store holds exactly the indexes it held before"
    assert build_root.files_below("data/indexes") == {}, "no record file is left"
    assert build_root.files_below("evals") == {}
    assert built.settings_printed == ()


@pytest.mark.parametrize(
    ("character", "bad_article"),
    [
        (NUL, "ex-004"),
        (UNPAIRED_SURROGATE, "ex-005"),
        (NUL, "ex-002"),
        (UNPAIRED_SURROGATE, "ex-003"),
    ],
    ids=["NUL in ex-004", "surrogate in ex-005", "NUL in ex-002", "surrogate in ex-003"],
)
def test_a_passage_the_store_or_the_provider_cannot_take_stops_the_build_before_any_request(
    store, build, build_root, examples, embedder_double, tmp_path, character, bad_article
):
    """FR-009 and contracts/cli.md, "`index build`": a passage with U+0000, or with an
    unpaired surrogate, cannot be stored or sent. The build splits every article and checks
    every passage before the first request to the embedder, so that nothing is paid for a
    build that cannot end: `reason:` names the article id, `index build: not carried out`,
    exit code 2; the embedder was never called; no schema and no record file are left. The
    character sits in the middle of a line of a late article, and the copy passes the dataset
    check."""
    articles = example_articles(examples)
    row = next(row for row in articles if row["id"] == bad_article)
    row["contents"] = row["contents"][:30] + character + row["contents"][30:]
    directory = copy_with_escaped_articles(examples / "example", tmp_path / "bad", articles)
    index = store.new_index()
    before = store.indexes()
    double = embedder_double()

    built = build(index, directory, double)

    reason = assert_stopped(built, "not carried out")
    assert bad_article in reason, f"the reason names the article id {bad_article}: {reason}"
    assert_nothing_was_embedded_or_left(built, double, store, build_root, index, before)


@pytest.mark.parametrize("character", [NUL, UNPAIRED_SURROGATE], ids=["NUL", "surrogate"])
def test_a_bad_character_in_the_last_of_many_articles_stops_the_build_before_any_request(
    store, build, build_root, examples, embedder_double, tmp_path, character
):
    """FR-009: the check comes before the first request, however many passages come before
    the one that cannot be taken. The corpus has 250 articles, more than one request carries
    (research.md, section 13: at most 96 passages); only the last one holds the character."""
    first = example_articles(examples)[0]
    articles = [
        {**first, "id": f"ex-{number:03d}", "contents": f"Article {number}\n{first['contents']}"}
        for number in range(1, 251)
    ]
    articles[-1]["contents"] += f"\nA last line with {character} inside."
    directory = copy_with_escaped_articles(examples / "example", tmp_path / "many", articles)
    index = store.new_index()
    before = store.indexes()
    double = embedder_double()

    built = build(index, directory, double)

    reason = assert_stopped(built, "not carried out")
    assert "ex-250" in reason, f"the reason names the article id ex-250: {reason}"
    assert_nothing_was_embedded_or_left(built, double, store, build_root, index, before)


def test_a_build_that_was_stopped_by_a_bad_character_changes_no_data_file(
    store, build, examples, embedder_double, tmp_path
):
    """FR-005 and the constitution, "Scope and Non-Goals": the dataset is never edited. The
    build reports the article and leaves the file as it is; it does not clean the text."""
    articles = example_articles(examples)
    articles[3]["contents"] += f"\nA line with {NUL} inside."
    directory = copy_with_escaped_articles(examples / "example", tmp_path / "bad", articles)
    files_before = files_of(directory)

    built = build(store.new_index(), directory, embedder_double())

    assert_stopped(built, "not carried out")
    assert files_of(directory) == files_before


def test_a_character_outside_the_basic_plane_is_no_reason_to_stop(
    store, build, examples, embedder_double, tmp_path
):
    """The counterpart of the tests above: only an unpaired surrogate cannot be sent. A
    character outside the Basic Multilingual Plane, which a JSON file writes as a pair of
    surrogates, is an ordinary character, and the build stores it unchanged."""
    articles = example_articles(examples)
    articles[3]["contents"] += "\nA line with \U0001f600 inside."
    directory = copy_with_escaped_articles(examples / "example", tmp_path / "pair", articles)
    assert b"\\ud83d\\ude00" in (directory / "ex.jsonl").read_bytes()
    index = store.new_index()

    assert_done(build(index, directory, embedder_double()))

    of_the_article = [p for p in store.passages(index) if p.article_id == "ex-004"]
    assert len(of_the_article) == 1
    assert of_the_article[0].text.endswith("A line with \U0001f600 inside.")
