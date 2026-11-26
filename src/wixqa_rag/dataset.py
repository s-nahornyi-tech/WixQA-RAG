"""The dataset: the pinned revision, a data directory with its manifest, the check and the fetch.

- `read_pinned` and `read_manifest` read `dataset.json` and a `manifest.json`; the rules of
  data-model.md, "Pinned revision", are checked when a file is read, here and nowhere else.
- `examine` is the dataset check (data-model.md, "Data directory", differences 1 to 8).
- `check` and `fetch` are the work of the commands `dataset check` and `dataset fetch`
  (contracts/cli.md): they print the lines of the contract and return the exit code.

No function writes to a part file after it has been stored (FR-005).
"""

import hashlib
import http.client
import json
import os
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from wixqa_rag import cli, settings

MANIFEST = "manifest.json"
ROLES = ("corpus", "questions")

# The fields that a row must have (PROJECT.md, "Data").
REQUIRED_FIELDS = {
    "corpus": ("id", "url", "contents", "article_type"),
    "questions": ("question", "answer", "article_ids"),
}

_FULL_COMMIT_HASH = re.compile(r"[0-9a-f]{40}")

# The real download: seconds without an answer from the host, and the size of one piece.
_TIME_LIMIT = 60
_PIECE = 1024 * 1024


class DatasetError(Exception):
    """A file of the dataset cannot be used; the message is the reason, ready to be printed."""


@dataclass(frozen=True)
class Part:
    """One file of a dataset. `bytes` and `sha256` are recorded by a manifest only."""

    name: str
    role: str
    path: str
    rows: int
    bytes: int | None = None
    sha256: str | None = None


@dataclass(frozen=True)
class Pinned:
    """What `dataset.json` records."""

    name: str
    revision: str
    parts: tuple[Part, ...]


@dataclass(frozen=True)
class Manifest:
    """What the `manifest.json` of a data directory records."""

    name: str
    revision: str | None
    fetched_at: str | None
    parts: tuple[Part, ...]


@dataclass(frozen=True)
class Examination:
    """The outcome of the dataset check of one data directory."""

    manifest: Manifest
    # Part name -> the number of rows found; a part whose file is missing has no entry.
    rows: dict[str, int]
    differences: list[str]


# --- Reading dataset.json and a manifest -------------------------------------------------------


def _document(file: Path) -> dict:
    try:
        document = json.loads(file.read_bytes())
    except ValueError:
        document = None
    if not isinstance(document, dict):
        raise DatasetError(f"{file} is not a JSON object")
    return document


def _is_count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _stays_inside(path: str) -> bool:
    """Whether the path of a part names a file below the folder it is stored in."""
    pure = PurePosixPath(path)
    return bool(pure.parts) and not pure.is_absolute() and ".." not in pure.parts


def _parts(document: dict, file: Path, *, with_fingerprints: bool) -> tuple[Part, ...]:
    entries = document.get("parts")
    if not isinstance(entries, list):
        raise DatasetError(f"{file}: parts is not a list")
    parts = []
    for entry in entries:
        usable = (
            isinstance(entry, dict)
            and isinstance(entry.get("name"), str)
            and entry["name"] != ""
            and entry.get("role") in ROLES
            and isinstance(entry.get("path"), str)
            and _stays_inside(entry["path"])
            and _is_count(entry.get("rows"))
        )
        if usable and with_fingerprints:
            usable = _is_count(entry.get("bytes")) and isinstance(entry.get("sha256"), str)
        if not usable:
            raise DatasetError(f"{file}: a part lacks a field or has a field that cannot be used")
        parts.append(
            Part(
                name=entry["name"],
                role=entry["role"],
                path=entry["path"],
                rows=entry["rows"],
                bytes=entry["bytes"] if with_fingerprints else None,
                sha256=entry["sha256"] if with_fingerprints else None,
            )
        )
    corpus_parts = sum(1 for part in parts if part.role == "corpus")
    if corpus_parts != 1:
        raise DatasetError(
            f"{file}: exactly one part has the role corpus, and {corpus_parts} parts have it here"
        )
    for name, times in sorted(Counter(part.name for part in parts).items()):
        if times > 1:
            raise DatasetError(f"{file}: the part name {name} is used {times} times")
    return tuple(parts)


def _name(document: dict, file: Path) -> str:
    name = document.get("name")
    if not isinstance(name, str) or name == "":
        raise DatasetError(f"{file}: name is not a text")
    return name


def _is_full_commit_hash(value: object) -> bool:
    return isinstance(value, str) and _FULL_COMMIT_HASH.fullmatch(value) is not None


def read_pinned() -> Pinned:
    """Read `dataset.json` from the current directory (data-model.md, "Pinned revision")."""
    file = settings.DATASET_JSON
    document = _document(file)
    if not _is_full_commit_hash(document.get("revision")):
        raise DatasetError(f"{file}: revision is not a full commit hash")
    return Pinned(
        name=_name(document, file),
        revision=document["revision"],
        parts=_parts(document, file, with_fingerprints=False),
    )


def read_manifest(data_dir: Path) -> Manifest:
    """Read the manifest of a data directory; without one the directory is not a local copy."""
    file = data_dir / MANIFEST
    if not file.is_file():
        raise DatasetError(f"{data_dir} has no {MANIFEST}: it is not a local copy of a dataset")
    document = _document(file)
    revision = document.get("revision")
    if revision is not None and not _is_full_commit_hash(revision):
        raise DatasetError(f"{file}: revision is neither a full commit hash nor null")
    fetched_at = document.get("fetched_at")
    return Manifest(
        name=_name(document, file),
        revision=revision,
        fetched_at=fetched_at if isinstance(fetched_at, str) else None,
        parts=_parts(document, file, with_fingerprints=True),
    )


# --- The dataset check -------------------------------------------------------------------------


def _rows_of(data: bytes) -> list[bytes]:
    """The rows of a part file: its non-empty lines (data-model.md, "Part")."""
    return [line for line in data.split(b"\n") if line.strip()]


def _measure(file: Path) -> tuple[int, int, str]:
    """The row count, the size and the SHA-256 of a file."""
    data = file.read_bytes()
    return len(_rows_of(data)), len(data), hashlib.sha256(data).hexdigest()


def _differences_from_pinned(manifest: Manifest, pinned: Pinned) -> list[str]:
    """Difference 8: where the manifest of the default data directory differs from dataset.json."""
    found = []
    if manifest.name != pinned.name:
        found.append(f"the dataset name is {manifest.name}, dataset.json records {pinned.name}")
    if manifest.revision != pinned.revision:
        found.append(
            f"the revision is {manifest.revision or 'none'}, dataset.json records {pinned.revision}"
        )
    in_manifest = {part.name: part for part in manifest.parts}
    for part in pinned.parts:
        stored = in_manifest.pop(part.name, None)
        if stored is None:
            found.append(f"the part {part.name} is not in the manifest")
            continue
        if stored.role != part.role:
            found.append(
                f"{part.name} has the role {stored.role}, dataset.json records {part.role}"
            )
        if stored.path != part.path:
            found.append(
                f"{part.name} has the path {stored.path}, dataset.json records {part.path}"
            )
        if stored.rows != part.rows:
            found.append(
                f"{part.name} has {stored.rows} rows in the manifest, "
                f"dataset.json records {part.rows}"
            )
    found.extend(f"the part {name} is not in dataset.json" for name in in_manifest)
    return [f"the manifest differs from dataset.json: {what}" for what in found]


def _differences_of_the_rows(part: Part, rows: list[bytes]) -> list[str]:
    """Differences 4 to 7 of one part."""
    found = []
    ids: Counter[str] = Counter()
    for number, line in enumerate(rows, start=1):
        try:
            row = json.loads(line)
        except ValueError:
            row = None
        if not isinstance(row, dict):
            found.append(f"{part.name} row {number} is not a JSON object")
            continue
        for field in REQUIRED_FIELDS[part.role]:
            value = row.get(field)
            if value is None:
                found.append(f"{part.name} row {number} lacks the field {field}")
            elif field == "id" and not isinstance(value, str):
                found.append(f"{part.name} row {number} has the field {field} with a wrong type")
            elif field == "article_ids" and not (
                isinstance(value, list) and all(isinstance(item, str) for item in value)
            ):
                found.append(f"{part.name} row {number} has the field {field} with a wrong type")
            elif field == "id":
                ids[value] += 1
    for article_id, times in sorted(ids.items()):
        if times > 1:
            found.append(f"article id {article_id} occurs {times} times in {part.name}")
    return found


def examine(data_dir: Path, pinned: Pinned | None = None) -> Examination:
    """Check a data directory against its manifest and, when `pinned` is given, against
    `dataset.json`. Every difference is listed. A directory without a usable manifest raises
    `DatasetError`: the check is not carried out."""
    manifest = read_manifest(data_dir)
    differences = [] if pinned is None else _differences_from_pinned(manifest, pinned)
    rows_found = {}
    for part in manifest.parts:
        file = data_dir / part.path
        if not file.is_file():
            differences.append(f"{part.name} is missing ({part.path})")
            continue
        data = file.read_bytes()
        rows = _rows_of(data)
        rows_found[part.name] = len(rows)
        if len(rows) != part.rows:
            differences.append(
                f"{part.name} has {len(rows)} rows, the manifest records {part.rows}"
            )
        if hashlib.sha256(data).hexdigest() != part.sha256:
            differences.append(f"{part.name} has changed since its fingerprint was recorded")
        differences.extend(_differences_of_the_rows(part, rows))
    return Examination(manifest=manifest, rows=rows_found, differences=differences)


def print_examination(examination: Examination) -> None:
    """Print the lines of the check before its verdict: the dataset, the revision, the rows
    found in each part, and every difference."""
    cli.result("dataset", examination.manifest.name)
    cli.result("revision", examination.manifest.revision or "none")
    for part in examination.manifest.parts:
        if part.name in examination.rows:
            cli.result(part.name, examination.rows[part.name])
    for text in examination.differences:
        cli.difference(text)


def check(data_dir: Path | None = None) -> int:
    """The command `dataset check`. Without a directory it checks the default data directory,
    and only then is the manifest compared with `dataset.json`."""
    name = "dataset check"
    try:
        pinned = read_pinned()
        if data_dir is None:
            default = settings.data_dir_of_revision(pinned.revision)
            if not (default / MANIFEST).is_file():
                raise DatasetError(
                    f"{default.as_posix()} has no {MANIFEST}: fetch the dataset first, "
                    "with `python -m wixqa_rag dataset fetch`"
                )
            examination = examine(default, pinned)
        else:
            examination = examine(data_dir)
    except DatasetError as error:
        cli.reason(str(error))
        return cli.verdict(name, "not carried out")
    print_examination(examination)
    return cli.verdict(name, "failed" if examination.differences else "passed")


# --- The fetch ---------------------------------------------------------------------------------


def address_of(pinned: Pinned, part: Part) -> str:
    """Where a file of the dataset is published at the pinned revision."""
    return f"https://huggingface.co/datasets/{pinned.name}/resolve/{pinned.revision}/{part.path}"


def download(address: str, destination: Path) -> None:
    """Download one file over HTTPS to a destination that does not exist yet.

    Redirects are followed, and no token is sent. A file that cannot be downloaded whole
    raises `OSError`.
    """
    request = urllib.request.Request(
        urllib.parse.quote(address, safe=":/"), headers={"User-Agent": "wixqa-rag"}
    )
    try:
        with (
            urllib.request.urlopen(request, timeout=_TIME_LIMIT) as response,
            destination.open("xb") as file,
        ):
            shutil.copyfileobj(response, file, _PIECE)
            announced = response.headers.get("Content-Length")
            received = file.tell()
    except http.client.HTTPException as error:
        raise OSError(f"the download broke off: {error!r}") from error
    if announced is not None and announced.isdigit() and int(announced) != received:
        raise OSError(f"the download broke off after {received} of {announced} bytes")


def _stored_parts(pinned: Pinned, data_dir: Path) -> dict[str, Part]:
    """The parts of the local copy that are complete and match: listed by the manifest as
    `dataset.json` lists them, with a file that has the recorded rows, size and SHA-256."""
    try:
        manifest = read_manifest(data_dir)
    except DatasetError:
        return {}
    if (manifest.name, manifest.revision) != (pinned.name, pinned.revision):
        return {}
    in_manifest = {part.name: part for part in manifest.parts}
    stored = {}
    for part in pinned.parts:
        recorded = in_manifest.get(part.name)
        file = data_dir / part.path
        if recorded is None or replace(recorded, bytes=None, sha256=None) != part:
            continue
        if file.is_file() and _measure(file) == (recorded.rows, recorded.bytes, recorded.sha256):
            stored[part.name] = recorded
    return stored


def _write_manifest(file: Path, pinned: Pinned, parts: list[Part]) -> None:
    document = {
        "name": pinned.name,
        "revision": pinned.revision,
        "fetched_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "parts": [asdict(part) for part in parts],
    }
    file.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def fetch(download: Callable[[str, Path], None]) -> int:
    """The command `dataset fetch`: fetch the dataset at the pinned revision into the default
    data directory. `download(address, destination)` fetches one file.

    Every part that is missing or differs is downloaded under a temporary name, counted and
    fingerprinted. Only when every part has the rows that `dataset.json` records are the files
    moved into place, and the manifest is written last. After any other verdict than `done`
    the local copy is as it was.
    """
    name = "dataset fetch"
    try:
        pinned = read_pinned()
    except DatasetError as error:
        cli.reason(str(error))
        return cli.verdict(name, "not carried out")
    data_dir = settings.data_dir_of_revision(pinned.revision)
    cli.result("dataset", pinned.name)
    cli.result("revision", pinned.revision)

    parts = _stored_parts(pinned, data_dir)
    wanted = [part for part in pinned.parts if part.name not in parts]
    if wanted:
        data_dir.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".fetch-", dir=data_dir.parent))
        try:
            differences = []
            for number, part in enumerate(wanted):
                address = address_of(pinned, part)
                cli.progress(f"downloading {part.name} from {address}")
                try:
                    download(address, temporary / f"part-{number}")
                    rows, size, sha256 = _measure(temporary / f"part-{number}")
                except OSError as error:
                    text = " ".join(str(error).split())
                    cli.reason(f"{part.name} cannot be downloaded from {address}: {text}")
                    return cli.verdict(name, "not carried out")
                if rows != part.rows:
                    differences.append(
                        f"{part.name} has {rows} rows, dataset.json records {part.rows}"
                    )
                parts[part.name] = replace(part, bytes=size, sha256=sha256)
            if differences:
                for text in differences:
                    cli.difference(text)
                return cli.verdict(name, "failed")
            _write_manifest(temporary / MANIFEST, pinned, [parts[p.name] for p in pinned.parts])
            # A data directory without a manifest is not a local copy: the old manifest goes
            # first, and the new one comes last.
            (data_dir / MANIFEST).unlink(missing_ok=True)
            for number, part in enumerate(wanted):
                place = data_dir / part.path
                place.parent.mkdir(parents=True, exist_ok=True)
                os.replace(temporary / f"part-{number}", place)
            os.replace(temporary / MANIFEST, data_dir / MANIFEST)
        finally:
            shutil.rmtree(temporary, ignore_errors=True)

    for part in pinned.parts:
        cli.result(part.name, part.rows)
    if wanted:
        cli.result("downloaded", f"{len(wanted)} file" + ("" if len(wanted) == 1 else "s"))
    else:
        print("nothing downloaded")
    cli.result("data directory", data_dir.as_posix())
    return cli.verdict(name, "done")
