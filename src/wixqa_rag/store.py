"""The vector store: PostgreSQL with pgvector, one schema per index (data-model.md, "Index").

Every SQL statement of the project lives in this file. A build uses one connection and one
transaction: until the commit no other connection sees any of it, and a build that stops is
rolled back.
"""

import re
from collections.abc import Iterable, Sequence

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from wixqa_rag import settings

# Lower-case letters, digits and single hyphens; at most 40 characters.
_IDENTIFIER = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
_LONGEST_IDENTIFIER = 40

ABSENT = "absent"
NOT_COMPLETE = "not complete"
COMPLETE = "complete"


class Unreachable(Exception):
    """The store cannot be reached. The message never holds the text of the library's error,
    which could carry a part of the connection string."""

    def __init__(self) -> None:
        super().__init__("the vector store cannot be reached")


def is_valid_identifier(index: str) -> bool:
    """Whether a text is an index identifier (data-model.md, "Index", "Identifier")."""
    return len(index) <= _LONGEST_IDENTIFIER and _IDENTIFIER.fullmatch(index) is not None


def schema_name(index: str) -> str:
    """`idx_` and the identifier with each hyphen replaced by an underscore."""
    if not is_valid_identifier(index):
        raise ValueError("not a valid index identifier")
    return "idx_" + index.replace("-", "_")


def connect() -> psycopg.Connection:
    """Connect to the store that `DATABASE_URL` names. Nothing is committed until `commit`."""
    address = settings.database_url()
    try:
        return psycopg.connect(address)
    except psycopg.Error:
        raise Unreachable() from None


def state_of(connection: psycopg.Connection, index: str) -> tuple[str, dict | None]:
    """Whether the index is absent, not complete or complete, and the build record of a
    complete index. The `build` row is the mark of completion."""
    schema = schema_name(index)
    exists = connection.execute(
        "SELECT 1 FROM pg_namespace WHERE nspname = %s", (schema,)
    ).fetchone()
    if exists is None:
        return ABSENT, None
    has_table = connection.execute("SELECT to_regclass(%s) IS NOT NULL", (f"{schema}.build",))
    if not has_table.fetchone()[0]:
        return NOT_COMPLETE, None
    row = connection.execute(
        sql.SQL("SELECT record FROM {}").format(sql.Identifier(schema, "build"))
    ).fetchone()
    if row is None:
        return NOT_COMPLETE, None
    return COMPLETE, row[0]


def create_index(connection: psycopg.Connection, index: str, dimensions: int) -> None:
    """Enable pgvector and create the schema of an index with its two tables."""
    schema = schema_name(index)
    connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
    connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    connection.execute(
        sql.SQL(
            "CREATE TABLE {} ("
            " article_id text NOT NULL,"
            " passage_no integer NOT NULL CHECK (passage_no >= 0),"
            " text text NOT NULL CHECK (text <> ''),"
            " embedding vector({}) NOT NULL,"
            " PRIMARY KEY (article_id, passage_no))"
        ).format(sql.Identifier(schema, "passages"), sql.SQL(str(int(dimensions))))
    )
    connection.execute(
        sql.SQL(
            "CREATE TABLE {} ("
            " only_row boolean PRIMARY KEY DEFAULT true CHECK (only_row),"
            " record jsonb NOT NULL,"
            " completed_at timestamptz NOT NULL)"
        ).format(sql.Identifier(schema, "build"))
    )


def insert_passages(
    connection: psycopg.Connection,
    index: str,
    passages: Iterable[tuple[str, int, str, Sequence[float]]],
) -> None:
    """Insert passages: article id, passage number, text and vector. A vector is sent in
    pgvector's text form."""
    rows = [
        (article_id, passage_no, text, "[" + ",".join(repr(float(x)) for x in vector) + "]")
        for article_id, passage_no, text, vector in passages
    ]
    with connection.cursor() as cursor:
        cursor.executemany(
            sql.SQL(
                "INSERT INTO {} (article_id, passage_no, text, embedding)"
                " VALUES (%s, %s, %s, %s::vector)"
            ).format(sql.Identifier(schema_name(index), "passages")),
            rows,
        )


def insert_build_row(connection: psycopg.Connection, index: str, record: dict) -> None:
    """Insert the build record, the mark of completion; it is the last statement of a build."""
    connection.execute(
        sql.SQL("INSERT INTO {} (record, completed_at) VALUES (%s, now())").format(
            sql.Identifier(schema_name(index), "build")
        ),
        (Jsonb(record),),
    )


def article_ids(connection: psycopg.Connection, index: str) -> set[str]:
    """The article ids of an index: the distinct `article_id` values of its `passages` table,
    the table that retrieval queries."""
    rows = connection.execute(
        sql.SQL("SELECT DISTINCT article_id FROM {}").format(
            sql.Identifier(schema_name(index), "passages")
        )
    ).fetchall()
    return {row[0] for row in rows}
