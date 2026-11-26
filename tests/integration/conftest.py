"""Fixtures of the integration tests (tasks T039): building and auditing against a real store,
with an embedder double (specs/001-corpus-and-audit/research.md, sections 3 and 17).

- `store`: a connection to the PostgreSQL that `DATABASE_URL` names. A test asks it for the
  identifiers of its indexes, so that every test works on indexes of its own; when the test
  ends, the schemas of exactly these identifiers are removed, and no other index is touched.
- `embedder_double`: the embedder that takes the place of the provider. It returns fixed
  vectors of 1536 numbers, reports the model name `embedder-double`, counts what it is asked
  for and can be told to fail.
- `build_root`: a temporary repository root with a `dataset.json` and a default data
  directory of its own (the fixture `pinned_example` of tests/conftest.py, with a complete
  local copy). It is the current directory of the test, so a build without `--data-dir`
  writes its record under `evals/` of this root and never under `evals/` of the checkout.
  The root is a Git checkout of its own with one commit, because a build reads the commit
  of the code from the checkout it runs in (contracts/cli.md, "`index build`").
- `build`: calls the build as the command `index build` does, with the embedder passed in.

Nothing here calls the embedding provider or the dataset host.
"""

import hashlib
import importlib
import json
import os
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest

EXAMPLES = Path(__file__).resolve().parents[1] / "data"

VECTOR_SIZE = 1536


# --- The store ---------------------------------------------------------------------------------


def schema_of(index: str) -> str:
    """data-model.md, "Index": `idx_` and the identifier with each hyphen as an underscore."""
    return "idx_" + index.replace("-", "_")


class Store:
    """What a test reads from the store, and the indexes it may create there."""

    def __init__(self, connection) -> None:
        self._connection = connection
        self._identifiers: list[str] = []

    def new_index(self, label: str = "") -> str:
        """A valid index identifier that no other test uses; its schema is removed afterwards."""
        identifier = "t" + uuid.uuid4().hex[:12] + (f"-{label}" if label else "")
        assert len(identifier) <= 40
        return self.register(identifier)

    def register(self, identifier: str) -> str:
        """Remember an identifier of this test, so that its schema is removed afterwards."""
        self._identifiers.append(identifier)
        return identifier

    def _rows(self, statement, parameters=()) -> list[tuple]:
        return self._connection.execute(statement, parameters).fetchall()

    def _table(self, index: str, table: str):
        from psycopg import sql

        return sql.Identifier(schema_of(index), table)

    def indexes(self) -> set[str]:
        """The names of all schemas of indexes that the store holds."""
        rows = self._rows(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE %s",
            ("idx\\_%",),
        )
        return {row[0] for row in rows}

    def holds(self, index: str) -> bool:
        """Whether the schema of the index exists, complete or not."""
        return schema_of(index) in self.indexes()

    def tables(self, index: str) -> set[str]:
        rows = self._rows(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
            (schema_of(index),),
        )
        return {row[0] for row in rows}

    def columns(self, index: str, table: str) -> dict[str, str]:
        """Column name -> its type as PostgreSQL writes it, for example `vector(1536)`."""
        rows = self._rows(
            "SELECT attribute.attname, format_type(attribute.atttypid, attribute.atttypmod) "
            "FROM pg_attribute AS attribute "
            "JOIN pg_class AS class ON class.oid = attribute.attrelid "
            "JOIN pg_namespace AS namespace ON namespace.oid = class.relnamespace "
            "WHERE namespace.nspname = %s AND class.relname = %s "
            "AND attribute.attnum > 0 AND NOT attribute.attisdropped",
            (schema_of(index), table),
        )
        return dict(rows)

    def passages(self, index: str) -> list[SimpleNamespace]:
        """The rows of `passages`, ordered by article and passage number."""
        from psycopg import sql

        rows = self._rows(
            sql.SQL(
                "SELECT article_id, passage_no, text, embedding::text FROM {} ORDER BY 1, 2"
            ).format(self._table(index, "passages"))
        )
        return [
            SimpleNamespace(
                article_id=row[0], passage_no=row[1], text=row[2], vector=json.loads(row[3])
            )
            for row in rows
        ]

    def article_ids(self, index: str) -> list[str]:
        """The article ids of the index: the distinct `article_id` values of `passages`."""
        return sorted({passage.article_id for passage in self.passages(index)})

    def build_rows(self, index: str) -> list[SimpleNamespace]:
        """The rows of `build`; a complete index has exactly one."""
        from psycopg import sql

        rows = self._rows(
            sql.SQL("SELECT only_row, record, completed_at FROM {}").format(
                self._table(index, "build")
            )
        )
        return [
            SimpleNamespace(only_row=row[0], record=row[1], completed_at=row[2]) for row in rows
        ]

    def make_schema_without_build_row(self, index: str) -> None:
        """Make by hand what no build leaves: the schema of an index without its `build` row
        (data-model.md, "Index": such an index is not complete)."""
        from psycopg import sql

        self._connection.execute(
            sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_of(index)))
        )

    def remove_created(self) -> None:
        from psycopg import sql

        for identifier in self._identifiers:
            self._connection.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    sql.Identifier(schema_of(identifier))
                )
            )


@pytest.fixture
def store():
    """A connection to the store that `DATABASE_URL` names; see `Store`.

    Only tests marked `store` use it. The value of `DATABASE_URL` and the text of a
    connection error are never shown.
    """
    import psycopg

    address = os.environ.get("DATABASE_URL", "")
    if not address:
        pytest.fail("a test marked `store` needs the environment variable DATABASE_URL")
    try:
        connection = psycopg.connect(address, autocommit=True, connect_timeout=15)
    except psycopg.Error as error:
        pytest.fail(
            f"the store cannot be reached through DATABASE_URL ({type(error).__name__})",
            pytrace=False,
        )
    with connection:
        helper = Store(connection)
        try:
            yield helper
        finally:
            helper.remove_created()


# --- The embedder double -----------------------------------------------------------------------


def vector_of(text: str) -> list[float]:
    """The fixed vector of a text: 1536 numbers that single precision stores exactly."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [digest[place % len(digest)] / 256 for place in range(VECTOR_SIZE)]


def tokens_of(text: str) -> int:
    """The tokens that the double reports for a text: the number of its words."""
    return len(text.split())


class EmbedderDouble:
    """Takes the place of `wixqa_rag.embedding.Embedder` (research.md, section 17).

    It has the attributes and the one method that the build uses of an embedder:
    `provider`, `model`, `dimensions`, `price_usd_per_million_tokens` and
    `embed(texts)`, which returns an object with `vectors`, `tokens` and `model`.
    """

    provider = "embedder-double"
    dimensions = VECTOR_SIZE
    price_usd_per_million_tokens = 0.5

    def __init__(
        self,
        *,
        model: str = "embedder-double",
        reported: str | None = None,
        fail_at_text: int | None = None,
        wrong_size_at_text: int | None = None,
        on_call=None,
    ) -> None:
        self.model = model
        # The model name that the double reports in its answers.
        self.reported = model if reported is None else reported
        # Counted from 1 over all texts the double is asked for: where it fails, and where it
        # returns a vector of 1535 numbers, which the store does not accept.
        self.fail_at_text = fail_at_text
        self.wrong_size_at_text = wrong_size_at_text
        self.on_call = on_call
        self.calls: list[list[str]] = []
        self.texts: list[str] = []
        self.tokens = 0

    def embed(self, texts):
        texts = list(texts)
        self.calls.append(texts)
        if self.on_call is not None:
            self.on_call()
        vectors = []
        for text in texts:
            self.texts.append(text)
            if len(self.texts) == self.fail_at_text:
                raise RuntimeError("the embedder double was told to fail")
            vector = vector_of(text)
            if len(self.texts) == self.wrong_size_at_text:
                vector = vector[:-1]
            vectors.append(vector)
        tokens = sum(tokens_of(text) for text in texts)
        self.tokens += tokens
        return SimpleNamespace(vectors=vectors, tokens=tokens, model=self.reported)


@pytest.fixture
def embedder_double():
    """The class `EmbedderDouble`; a test makes its own double: `embedder_double()`."""
    return EmbedderDouble


# --- The temporary repository root -------------------------------------------------------------


def _git(root: Path, *arguments: str) -> str:
    """Run Git in the temporary root, without the settings of the person or the machine."""
    environment = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    }
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        environment.pop(name, None)
    completed = subprocess.run(
        [
            "git",
            "-c",
            "user.name=Integration tests",
            "-c",
            "user.email=integration-tests@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *arguments,
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


@dataclass(frozen=True)
class BuildRoot:
    """A temporary repository root in which an index can be built without `--data-dir`."""

    root: Path
    # The fixture `pinned_example`: `dataset.json`, the default data directory, its sources.
    example: object
    # The commit of the temporary checkout, as a full hash.
    commit: str
    # A file of the commit; changing it makes the working tree differ from the commit.
    tracked_file: Path

    def record_file(self, index: str, *, with_data_dir: bool) -> Path:
        """data-model.md, "Build record": where the build record of an index is written."""
        folder = "data" if with_data_dir else "evals"
        return self.root / folder / "indexes" / index / "build.json"

    def files_below(self, folder: str) -> dict[str, bytes]:
        top = self.root / folder
        if not top.is_dir():
            return {}
        return {
            file.relative_to(self.root).as_posix(): file.read_bytes()
            for file in sorted(top.rglob("*"))
            if file.is_file()
        }


@pytest.fixture
def build_root(pinned_example, monkeypatch) -> BuildRoot:
    """A temporary repository root with a default data directory, as a Git checkout; the
    current directory of the test. `data/` is ignored there, as it is in the repository."""
    root = pinned_example.root
    pinned_example.store_copy()
    (root / ".gitignore").write_text("data/\n", encoding="utf-8")
    tracked_file = root / "NOTES.txt"
    tracked_file.write_text("A file of the temporary checkout.\n", encoding="utf-8")
    _git(root, "init", "--quiet", "--initial-branch=main")
    _git(root, "add", ".gitignore", "NOTES.txt", "dataset.json")
    _git(root, "commit", "--quiet", "--message", "The temporary repository root")
    commit = _git(root, "rev-parse", "HEAD")
    monkeypatch.chdir(root)
    return BuildRoot(root=root, example=pinned_example, commit=commit, tracked_file=tracked_file)


# --- Calling the build -------------------------------------------------------------------------


@dataclass(frozen=True)
class Built:
    """What one call of the build left on the two output streams."""

    exit_code: int
    lines: list[str]
    standard_error: str
    # The embedder that was passed to the build, and the texts it was asked to embed in this
    # call; none when nothing had to be embedded.
    embedder: object = None
    embedded: list = field(default_factory=list)
    # The names of the settings whose value the build printed, on either stream. The value
    # itself is replaced in `lines` and `standard_error`, so that no failure shows it.
    settings_printed: tuple[str, ...] = ()

    @property
    def last_line(self) -> str:
        return self.lines[-1] if self.lines else ""

    @property
    def reasons(self) -> list[str]:
        return [line for line in self.lines[:-1] if line.startswith("reason: ")]

    def value_of(self, name: str) -> str:
        """The value of the one result line `name: value`."""
        values = [line[len(name) + 2 :] for line in self.lines if line.startswith(f"{name}: ")]
        assert len(values) == 1, f"one line `{name}: ...` expected; got {values}"
        return values[0]


def _hide_settings(text: str) -> tuple[str, set[str]]:
    """Replace the value of each setting in a text; return the text and the settings found."""
    found = set()
    for name in ("DATABASE_URL", "OPENAI_API_KEY"):
        value = os.environ.get(name, "")
        if len(value) >= 8 and value in text:
            found.add(name)
            text = text.replace(value, f"<value of {name}>")
    return text, found


@pytest.fixture
def build(build_root, capfd):
    """Call the build as the command `index build` does, in the temporary repository root.

        built = build(index, data_dir, embedder)

    `data_dir` is None for a build without `--data-dir`. Without `embedder` the build gets a
    new `EmbedderDouble`.
    """

    def call(index: str, data_dir: Path | None = None, embedder=None) -> Built:
        # It fails while `src/wixqa_rag/index.py` does not exist (plan.md, source tree).
        index_module = importlib.import_module("wixqa_rag.index")
        cli = importlib.import_module("wixqa_rag.cli")
        given = EmbedderDouble() if embedder is None else embedder
        asked_before = len(getattr(given, "texts", []))

        capfd.readouterr()
        exit_code = cli.carry_out("index build", lambda: index_module.build(index, data_dir, given))
        captured = capfd.readouterr()
        output, in_output = _hide_settings(captured.out)
        error, in_error = _hide_settings(captured.err)
        return Built(
            exit_code=exit_code,
            lines=output.splitlines(),
            standard_error=error,
            embedder=given,
            embedded=list(getattr(given, "texts", []))[asked_before:],
            settings_printed=tuple(sorted(in_output | in_error)),
        )

    return call


# --- What an index built from an example directory holds ---------------------------------------


def articles_of(directory: Path) -> list[dict]:
    text = (directory / "ex.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.split("\n") if line.strip()]


def passage_of(contents: str) -> str | None:
    """The one passage of a short article under `line-pack-v1`: its non-empty lines, stripped
    and joined by a line feed (research.md, section 12). None for an article without text."""
    lines = [line.strip() for line in contents.replace("\r", "\n").split("\n") if line.strip()]
    text = "\n".join(lines)
    assert len(text) <= 2000, "the example articles are shorter than one passage"
    return text or None


@pytest.fixture
def expected_passages():
    """For an example directory: article id -> its one passage, for every article with text."""

    def of(directory: Path) -> dict[str, str]:
        passages = {row["id"]: passage_of(row["contents"]) for row in articles_of(directory)}
        return {article: text for article, text in passages.items() if text is not None}

    return of


@pytest.fixture
def examples() -> Path:
    """The folder `tests/data/` with the five example data directories."""
    return EXAMPLES


@pytest.fixture
def double_helpers():
    """`vector_of` and `tokens_of`: what the double returns and reports for a text."""
    return SimpleNamespace(vector_of=vector_of, tokens_of=tokens_of)
