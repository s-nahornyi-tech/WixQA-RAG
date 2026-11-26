"""The build of an index and its record: the work of the command `index build`.

The steps and their order are those of contracts/cli.md, "`index build`"; what the build does
when the identifier or a record file already exists is the table of research.md, section 15.
"""

import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from wixqa_rag import cli, dataset, embedding, settings, splitting, store

NAME = "index build"

# The order of the fields in a record file (contracts/records.md, "`build.json`").
_FIELDS = {
    "index": (),
    "dataset": ("name", "revision", "corpus_sha256"),
    "embedding": ("provider", "model_requested", "model_reported", "dimensions"),
    "splitting": ("rule", "max_chars"),
    "articles": (),
    "passages": (),
    "articles_without_passages": (),
    "tokens_embedded": (),
    "price_usd_per_million_tokens": (),
    "cost_usd": (),
    "started_at": (),
    "commit": (),
    "uncommitted_changes": (),
}


# U+0000, which PostgreSQL refuses in a text, and a surrogate, which cannot be sent as UTF-8.
# A character outside the basic plane is one character here, not a pair of surrogates.
_CANNOT_BE_TAKEN = re.compile("[\\x00\ud800-\udfff]")


def _first_text_that_cannot_be_taken(passages: list[tuple[str, int, str]]) -> str | None:
    """Why the store or the provider cannot take a passage, for the first such passage; None
    when every article id and every passage can be stored and sent."""
    for article_id, _, text in passages:
        if _CANNOT_BE_TAKEN.search(article_id):
            return (
                f"the article id {ascii(article_id)} holds a character "
                "that can be neither stored nor sent"
            )
        found = _CANNOT_BE_TAKEN.search(text)
        if found:
            return (
                f"the text of the article {article_id} holds the character "
                f"U+{ord(found.group()):04X}, which can be neither stored nor sent"
            )
    return None


def _in_order(document: dict, first: tuple | dict) -> dict:
    return {key: document[key] for key in [*(k for k in first if k in document), *document]}


def _write_record(file: Path, record: dict) -> None:
    ordered = _in_order(record, _FIELDS)
    for field, inner in _FIELDS.items():
        if inner and isinstance(ordered.get(field), dict):
            ordered[field] = _in_order(ordered[field], inner)
    file.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_record(file: Path) -> object:
    try:
        return json.loads(file.read_bytes())
    except ValueError:
        return None


def _code_commit() -> tuple[str, bool] | None:
    """The commit of the checkout in the current directory, and whether the working tree
    differs from it; None when the current directory is not in a Git checkout."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        ).stdout
    except OSError, subprocess.CalledProcessError:
        return None
    return commit, status.strip() != ""


def _articles(file: Path, part_name: str) -> list[tuple[str, str]]:
    """The id and the contents of every article of a corpus file that passed the check."""
    articles = []
    rows = [line for line in file.read_bytes().split(b"\n") if line.strip()]
    for number, line in enumerate(rows, start=1):
        row = json.loads(line)
        if not isinstance(row["contents"], str):
            raise dataset.DatasetError(
                f"{part_name} row {number} has the field contents with a wrong type"
            )
        articles.append((row["id"], row["contents"]))
    return articles


def _already_complete(index: str, record: dict, record_file: Path) -> int:
    cli.result("index", f"{index} (already complete)")
    cli.result("articles", record.get("articles"))
    cli.result("passages", record.get("passages"))
    cli.result("tokens embedded", 0)
    cli.result("build record", record_file.as_posix())
    return cli.verdict(NAME, "done")


def _stop(reason: str, outcome: str) -> int:
    cli.reason(reason)
    return cli.verdict(NAME, outcome)


def build(index: str, data_dir: Path | None, embedder) -> int:
    """Build the index `index` from the corpus of a data directory; `data_dir` is None for
    the default data directory. `embedder` has the attributes and the method `embed` of
    `embedding.Embedder`; `embed` is called only when passages have to be embedded.

    Prints the lines of contracts/cli.md and returns the exit code.
    """
    started_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Step 1: the identifier.
    if not store.is_valid_identifier(index):
        return _stop(f"{index} is not a valid index identifier", "not carried out")

    # Step 2: the data directory passes the dataset check.
    try:
        pinned = dataset.read_pinned()
        if data_dir is None:
            directory = settings.data_dir_of_revision(pinned.revision)
            examination = dataset.examine(directory, pinned)
        else:
            directory = data_dir
            examination = dataset.examine(directory)
    except dataset.DatasetError as error:
        return _stop(str(error), "not carried out")
    if examination.differences:
        dataset.print_examination(examination)
        return _stop(f"the dataset check failed for {directory.as_posix()}", "refused")
    manifest = examination.manifest
    corpus = next(part for part in manifest.parts if part.role == "corpus")
    record_file = settings.build_record_path(index, data_dir)
    of_this_build = {
        "dataset": {
            "name": manifest.name,
            "revision": manifest.revision,
            "corpus_sha256": corpus.sha256,
        },
        "embedding": {
            "provider": embedder.provider,
            "model_requested": embedder.model,
            "dimensions": embedder.dimensions,
        },
        "splitting": {"rule": splitting.RULE, "max_chars": splitting.MAX_CHARS},
    }

    # Step 3: the store.
    try:
        connection = store.connect()
    except store.Unreachable as error:
        return _stop(str(error), "not carried out")

    with connection:
        # Step 4: what the store and the record file allow (research.md, section 15).
        state, stored = store.state_of(connection, index)
        if state == store.NOT_COMPLETE:
            return _stop(f"index {index} exists and is not complete", "refused")
        if state == store.ABSENT and record_file.exists():
            return _stop(
                f"{record_file.as_posix()} records a build of {index}, "
                "and the store does not hold that index",
                "refused",
            )
        if state == store.COMPLETE:
            if record_file.exists() and _read_record(record_file) != stored:
                return _stop(
                    f"{record_file.as_posix()} does not match the index {index} in the store",
                    "refused",
                )
            built_from = stored.get("dataset") or {}
            if built_from.get("corpus_sha256") != corpus.sha256:
                return _stop(f"index {index} exists with another corpus", "refused")
            embedded_with = stored.get("embedding") or {}
            same_settings = stored.get("splitting") == of_this_build["splitting"] and all(
                embedded_with.get(key) == value for key, value in of_this_build["embedding"].items()
            )
            if not same_settings:
                return _stop(f"index {index} exists with other settings", "refused")
            if not record_file.exists():
                record_file.parent.mkdir(parents=True, exist_ok=True)
                _write_record(record_file, stored)
            return _already_complete(index, stored, record_file)

        # The record names the commit of the code; without it nothing is embedded.
        code = _code_commit()
        if code is None:
            return _stop("the commit of the code cannot be read", "not carried out")
        commit, uncommitted_changes = code

        # Steps 5 and 6: split, embed and store; the provider key is read at the first request.
        try:
            articles = _articles(directory / corpus.path, corpus.name)
        except dataset.DatasetError as error:
            return _stop(str(error), "not carried out")
        passages = []
        without_passages = []
        for article_id, contents in articles:
            texts = splitting.split(contents)
            if not texts:
                without_passages.append(article_id)
            passages.extend((article_id, number, text) for number, text in enumerate(texts))
        without_passages.sort()

        # Every passage is checked before the first request, so that nothing is paid for a
        # build that cannot end. The data stays as published; the article is only named.
        cannot_be_taken = _first_text_that_cannot_be_taken(passages)
        if cannot_be_taken is not None:
            return _stop(cannot_be_taken, "not carried out")

        store.create_index(connection, index, embedder.dimensions)
        tokens = 0
        reported = embedder.model
        for start in range(0, len(passages), embedding.MAX_TEXTS):
            batch = passages[start : start + embedding.MAX_TEXTS]
            embedded = embedder.embed([text for _, _, text in batch])
            if len(embedded.vectors) != len(batch):
                raise RuntimeError(
                    f"the embedder returned {len(embedded.vectors)} vectors "
                    f"for {len(batch)} passages"
                )
            store.insert_passages(
                connection,
                index,
                [
                    (*passage, vector)
                    for passage, vector in zip(batch, embedded.vectors, strict=True)
                ],
            )
            tokens += embedded.tokens
            reported = embedded.model
            cli.progress(f"embedded {start + len(batch)} of {len(passages)} passages")

        cost = embedding.cost_usd(tokens, embedder.price_usd_per_million_tokens)
        record = {
            "index": index,
            "dataset": of_this_build["dataset"],
            "embedding": {
                "provider": embedder.provider,
                "model_requested": embedder.model,
                "model_reported": reported,
                "dimensions": embedder.dimensions,
            },
            "splitting": of_this_build["splitting"],
            "articles": len(articles),
            "passages": len(passages),
            "articles_without_passages": without_passages,
            "tokens_embedded": tokens,
            "price_usd_per_million_tokens": embedder.price_usd_per_million_tokens,
            "cost_usd": cost,
            "started_at": started_at,
            "commit": commit,
            "uncommitted_changes": uncommitted_changes,
        }

        # The record file is written under a temporary name before the commit and gets its
        # final name after it: a failure before the commit leaves neither index nor record.
        folder_is_new = not record_file.parent.exists()
        record_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = record_file.with_name(record_file.name + ".tmp")
        try:
            _write_record(temporary, record)
            store.insert_build_row(connection, index, record)
            connection.commit()
            os.replace(temporary, record_file)
        finally:
            temporary.unlink(missing_ok=True)
            if folder_is_new and not record_file.exists():
                record_file.parent.rmdir()

    cli.result("index", index)
    cli.result("dataset", manifest.name)
    cli.result("revision", manifest.revision or "none")
    cli.result("embedding model", embedder.model)
    cli.result("splitting rule", f"{splitting.RULE} (max_chars={splitting.MAX_CHARS})")
    cli.result("articles", len(articles))
    cli.result("passages", len(passages))
    cli.result("articles without passages", len(without_passages))
    for article_id in without_passages:
        print(f"  {article_id}")
    cli.result("tokens embedded", tokens)
    cli.result("cost_usd", f"{cost:.8f}")
    cli.result("build record", record_file.as_posix())
    return cli.verdict(NAME, "done")
