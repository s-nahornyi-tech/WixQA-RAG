"""The fetch (tasks T025): what `dataset fetch` does, with a download double in place of the
dataset host.

Covers:

- contracts/cli.md, "`dataset fetch`": the three steps, the lines of a first fetch,
  `nothing downloaded` over a complete, matching copy, the verdicts and the exit codes;
- research.md, section 9: the address of a file, the temporary name, the manifest written last;
- contracts/records.md, "`manifest.json`", and data-model.md, "Data directory": what the
  manifest of the fetched copy records;
- spec.md, FR-001, FR-002, FR-003 and FR-005, User Story 1, scenario 2, and the edge cases
  "the dataset cannot be downloaded" and "a row count differs".

The command line always downloads from the dataset host, so these tests call the fetch
directly and pass the download function to it (tasks.md, T029). They need one name from
`src/wixqa_rag/dataset.py`:

    fetch(download: Callable[[str, Path], None]) -> int

`fetch` is the work of the command `dataset fetch`: it is called through `carry_out` of
`src/wixqa_rag/cli.py`, in the repository root as the current directory; it prints the lines of
contracts/cli.md and returns the exit code. An error that it does not handle itself is
reported by `carry_out` as not carried out.

`download(address, destination)` fetches one file: `address` is the text
`https://huggingface.co/datasets/<name>/resolve/<revision>/<path>`, with the values of
`dataset.json`, and `destination` is the path of a file that does not exist yet, in a folder
that exists; it is a temporary name, not the place of the part in the data directory. The
function writes the whole file there and returns nothing; when it cannot, it raises an
`OSError`. `fetch` calls it once for every part that is missing or differs, and never over a
complete, matching copy.

The tests work in a temporary repository root that pins example data (the fixture
`pinned_example` of tests/conftest.py). All documents named here are in
specs/001-corpus-and-audit/.
"""

import hashlib
import importlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[1] / "data"


def address_of(example, path: str) -> str:
    """research.md, section 9: where a file of the dataset is published at a revision."""
    return f"https://huggingface.co/datasets/{example.name}/resolve/{example.revision}/{path}"


class DatasetHost:
    """The download double: it stands for the dataset host and keeps what was asked of it."""

    def __init__(self, example, *, published=None, unreachable=()):
        self.example = example
        # Path inside the dataset -> the bytes that the host returns for it.
        self.published = {**example.sources, **(published or {})}
        # The paths for which the host cannot be reached.
        self.unreachable = set(unreachable)
        self.addresses: list[str] = []
        self.destinations: list[Path] = []
        # What the data directory looked like at the time of each call.
        self.manifest_existed: list[bool] = []
        self.part_was_in_place: list[bool] = []

    def __call__(self, address, destination) -> None:
        address = str(address)
        destination = Path(destination)
        self.addresses.append(address)
        self.destinations.append(destination)
        self.manifest_existed.append(self.example.manifest_file.exists())

        paths = [path for path in self.published if address == address_of(self.example, path)]
        if not paths:
            raise OSError(f"the stand-in host has no file at {address}")
        (path,) = paths
        self.part_was_in_place.append((self.example.data_dir / path).exists())
        if path in self.unreachable:
            raise OSError("the stand-in host cannot be reached")
        destination.write_bytes(self.published[path])


@dataclass(frozen=True)
class Fetched:
    exit_code: int
    lines: list[str]

    @property
    def last_line(self) -> str:
        return self.lines[-1] if self.lines else ""

    def starting_with(self, start: str) -> list[str]:
        return [line for line in self.lines if line.startswith(start)]


@pytest.fixture
def fetch(pinned_example, monkeypatch, capfd):
    """Call the fetch as the command `dataset fetch` does, with a download function.

    The current directory is the temporary repository root, and neither setting is set: the
    fetch needs neither the store nor the provider key (quickstart.md, "The published
    dataset").
    """
    monkeypatch.chdir(pinned_example.root)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def call(download) -> Fetched:
        # It fails while `src/wixqa_rag/dataset.py` does not exist (plan.md, source tree).
        dataset = importlib.import_module("wixqa_rag.dataset")
        cli = importlib.import_module("wixqa_rag.cli")
        capfd.readouterr()
        exit_code = cli.carry_out("dataset fetch", lambda: dataset.fetch(download))
        return Fetched(exit_code=exit_code, lines=capfd.readouterr().out.splitlines())

    return call


def names(line: str, word: str) -> bool:
    """Whether a line names a part as a word of its own: `ex` is not named by `exq`."""
    return re.search(rf"(?<![\w.-]){re.escape(word)}(?![\w-]|\.\w)", line) is not None


def has_number(line: str, number: int) -> bool:
    return re.search(rf"(?<!\d){number}(?!\d)", line) is not None


def assert_done(fetched: Fetched) -> None:
    assert fetched.exit_code == 0, (
        'contracts/cli.md, "`dataset fetch`": a fetch that did its work ends with exit code 0; '
        f"got {fetched.exit_code}. Standard output:\n" + "\n".join(fetched.lines)
    )
    assert fetched.last_line == "dataset fetch: done"


def assert_failed(fetched: Fetched) -> list[str]:
    assert fetched.exit_code == 1, (
        'contracts/cli.md, "`dataset fetch`": a differing row count ends with exit code 1; '
        f"got {fetched.exit_code}. Standard output:\n" + "\n".join(fetched.lines)
    )
    assert fetched.last_line == "dataset fetch: failed"
    differences = [line for line in fetched.lines[:-1] if line.startswith("difference: ")]
    assert differences, 'contracts/cli.md, "Output", rule 4: a `difference:` line comes first'
    return differences


def assert_not_carried_out(fetched: Fetched) -> None:
    assert fetched.exit_code == 2, (
        'contracts/cli.md, "`dataset fetch`": a file that cannot be downloaded ends with exit '
        f"code 2; got {fetched.exit_code}. Standard output:\n" + "\n".join(fetched.lines)
    )
    assert fetched.last_line == "dataset fetch: not carried out"
    assert [line for line in fetched.lines[:-1] if line.startswith("reason: ")], (
        'contracts/cli.md, "Output", rule 5: a `reason:` line comes before the verdict'
    )


PART_FIELDS = ("name", "role", "path", "rows", "bytes", "sha256")


def recorded_parts(manifest: dict) -> list[dict]:
    """The parts of a manifest with the six fields of contracts/records.md, sorted by name."""
    parts = [{field: part.get(field) for field in PART_FIELDS} for part in manifest["parts"]]
    return sorted(parts, key=lambda part: part["name"])


def expected_parts(example) -> list[dict]:
    return sorted(example.manifest_parts(), key=lambda part: part["name"])


def change_a_stored_file(example, path: str) -> None:
    """Change a file of the local copy after it was stored: same size, same rows, other bytes."""
    file = example.data_dir / path
    data = file.read_bytes()
    assert b"account" in data
    file.write_bytes(data.replace(b"account", b"ACCOUNT"))


# --- A first fetch ------------------------------------------------------------------------------


def test_a_first_fetch_downloads_every_part_at_the_pinned_revision(pinned_example, fetch):
    """FR-001 and research.md, section 9: every file is downloaded once, from
    `https://huggingface.co/datasets/Wix/WixQA/resolve/<revision>/<path>`, with the revision
    and the paths that `dataset.json` records."""
    host = DatasetHost(pinned_example)

    assert_done(fetch(host))

    assert sorted(host.addresses) == sorted(
        address_of(pinned_example, part["path"]) for part in pinned_example.parts
    )


def test_a_first_fetch_prints_the_lines_of_the_contract(pinned_example, fetch):
    """contracts/cli.md, "`dataset fetch`", output of a first fetch: the dataset, the pinned
    revision, the row count of each part, the number of files downloaded, the data directory
    and the verdict (FR-002)."""
    fetched = fetch(DatasetHost(pinned_example))

    assert_done(fetched)
    assert fetched.lines == [
        "dataset: Wix/WixQA",
        f"revision: {pinned_example.revision}",
        "ex: 5",
        "exq: 3",
        "exq_more: 3",
        "downloaded: 3 files",
        f"data directory: data/wixqa/{pinned_example.revision}",
        "dataset fetch: done",
    ]


def test_the_stored_files_have_the_bytes_that_were_downloaded(pinned_example, fetch):
    """FR-005 and research.md, section 9: the files stay exactly as published. Each part is
    stored at its path inside the data directory, byte for byte, also the two files of the
    same name and the file without a line feed after its last row. Nothing else is left in the
    data directory but the manifest."""
    assert_done(fetch(DatasetHost(pinned_example)))

    stored = pinned_example.stored_files()
    assert set(stored) == {*pinned_example.sources, "manifest.json"}
    for path, published in pinned_example.sources.items():
        assert stored[path] == published, f"{path} is stored with other bytes than downloaded"


def test_the_manifest_records_what_was_stored(pinned_example, fetch):
    """FR-003 and contracts/records.md, "`manifest.json`": the dataset name, the revision, the
    time the fetch finished in UTC, and for each part its name, role, path, row count, size
    and SHA-256."""
    before = datetime.now(UTC).replace(microsecond=0)
    assert_done(fetch(DatasetHost(pinned_example)))
    after = datetime.now(UTC)

    manifest = json.loads(pinned_example.manifest_file.read_text(encoding="utf-8"))
    assert manifest["name"] == "Wix/WixQA"
    assert manifest["revision"] == pinned_example.revision

    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", manifest["fetched_at"]), (
        "contracts/records.md: times are in UTC in the form 2026-11-24T10:15:00Z"
    )
    fetched_at = datetime.strptime(manifest["fetched_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    assert before - timedelta(seconds=1) <= fetched_at <= after + timedelta(seconds=1)

    assert recorded_parts(manifest) == expected_parts(pinned_example)
    for part in manifest["parts"]:
        stored = (pinned_example.data_dir / part["path"]).read_bytes()
        assert part["bytes"] == len(stored)
        assert part["sha256"] == hashlib.sha256(stored).hexdigest()


def test_after_a_fetch_the_dataset_check_passes(pinned_example, fetch, run_command):
    """contracts/cli.md, "`dataset fetch`", step 1, and User Story 1, "Independent Test": run
    the fetch and then the check; the check passes."""
    assert_done(fetch(DatasetHost(pinned_example)))

    result = run_command("python -m wixqa_rag dataset check", cwd=pinned_example.root)

    assert result.exit_code == 0, result.stdout
    assert result.last_line == "dataset check: passed"


# --- Temporary names, and the manifest last -----------------------------------------------------


def test_a_file_is_downloaded_under_a_temporary_name(pinned_example, fetch):
    """contracts/cli.md, "`dataset fetch`", steps 2 and 3: every part is downloaded under a
    temporary name, and the files are moved into place when every part matches."""
    host = DatasetHost(pinned_example)

    assert_done(fetch(host))

    places = {(pinned_example.data_dir / path).resolve() for path in pinned_example.sources}
    assert len(host.destinations) == 3
    for destination in host.destinations:
        assert destination.resolve() not in places, "a file was downloaded straight into its place"
        assert destination.resolve() != pinned_example.manifest_file.resolve()
        assert not destination.exists(), "a temporary name is left behind after the fetch"
    assert host.part_was_in_place == [False, False, False], (
        "a part was moved into place before every part was downloaded and counted"
    )


def test_the_manifest_is_written_last(pinned_example, fetch):
    """data-model.md, "Data directory": "The manifest is written last. A data directory without
    a manifest is not a local copy." While files are downloaded there is no manifest."""
    host = DatasetHost(pinned_example)

    assert_done(fetch(host))

    assert host.manifest_existed == [False, False, False]
    assert pinned_example.manifest_file.is_file()


# --- A fetch over a complete, matching copy -----------------------------------------------------


def test_a_fetch_over_a_complete_matching_copy_downloads_nothing(pinned_example, fetch):
    """FR-003 and User Story 1, scenario 2: given a complete local copy, nothing is downloaded,
    and the report gives the same counts. contracts/cli.md: the line `nothing downloaded`
    stands in place of the `downloaded:` line. The copy, its manifest included, is as it was."""
    pinned_example.store_copy()
    before = pinned_example.stored_files()
    host = DatasetHost(pinned_example)

    fetched = fetch(host)

    assert_done(fetched)
    assert host.addresses == [], "a fetch over a complete, matching copy asked the host for a file"
    assert fetched.lines == [
        "dataset: Wix/WixQA",
        f"revision: {pinned_example.revision}",
        "ex: 5",
        "exq: 3",
        "exq_more: 3",
        "nothing downloaded",
        f"data directory: data/wixqa/{pinned_example.revision}",
        "dataset fetch: done",
    ]
    assert pinned_example.stored_files() == before


def test_a_second_fetch_downloads_nothing(pinned_example, fetch):
    """AC-001 on example data: fetch twice; the second fetch prints `nothing downloaded` and
    asks the host for nothing."""
    host = DatasetHost(pinned_example)
    first = fetch(host)
    assert_done(first)
    after_the_first = pinned_example.stored_files()

    second = fetch(host)

    assert_done(second)
    assert len(host.addresses) == 3, "the second fetch asked the host for a file"
    assert "nothing downloaded" in second.lines
    assert not second.starting_with("downloaded:")
    for line in ("ex: 5", "exq: 3", "exq_more: 3"):
        assert line in first.lines and line in second.lines
    assert pinned_example.stored_files() == after_the_first


def test_only_the_parts_that_are_missing_or_differ_are_downloaded(pinned_example, fetch):
    """contracts/cli.md, "`dataset fetch`", step 2: every part that is missing or differs is
    downloaded. contracts/records.md: a fetch which replaces a missing or changed file writes
    the manifest again. Afterwards the copy is complete and matches."""
    pinned_example.store_copy()
    change_a_stored_file(pinned_example, "ex/ex.jsonl")
    (pinned_example.data_dir / "exq_more/test.jsonl").unlink()
    host = DatasetHost(pinned_example)

    fetched = fetch(host)

    assert_done(fetched)
    assert sorted(host.addresses) == sorted(
        address_of(pinned_example, path) for path in ("ex/ex.jsonl", "exq_more/test.jsonl")
    )
    assert fetched.starting_with("downloaded: 2 ")
    stored = pinned_example.stored_files()
    assert set(stored) == {*pinned_example.sources, "manifest.json"}
    assert {path: stored[path] for path in pinned_example.sources} == pinned_example.sources
    assert recorded_parts(json.loads(stored["manifest.json"])) == expected_parts(pinned_example)


# --- A row count differs from dataset.json (spec.md, "Edge Cases") ------------------------------


def test_a_differing_row_count_ends_as_failed_and_names_both_numbers(pinned_example, fetch):
    """FR-002 and the edge case "a row count at the pinned revision differs from the count
    recorded with it": the fetch fails and names both numbers. contracts/cli.md:
    `difference: <part> has <n> rows, dataset.json records <m>`, `dataset fetch: failed`,
    exit code 1. The host returns 4 articles where `dataset.json` records 5."""
    four_articles = (EXAMPLES / "example-one-less-article" / "ex.jsonl").read_bytes()
    host = DatasetHost(pinned_example, published={"ex/ex.jsonl": four_articles})

    differences = assert_failed(fetch(host))

    assert len(differences) == 1, "\n".join(differences)
    assert names(differences[0], "ex"), f"the line names the part ex: {differences[0]}"
    assert has_number(differences[0], 4), f"the line gives the 4 rows found: {differences[0]}"
    assert has_number(differences[0], 5), f"the line gives the 5 rows recorded: {differences[0]}"
    assert not pinned_example.manifest_file.exists(), (
        "a fetch that failed leaves no manifest: there is no local copy"
    )


def test_a_differing_row_count_leaves_the_local_copy_as_it_was(pinned_example, fetch):
    """contracts/cli.md, "`dataset fetch`": after a verdict other than `done`, an existing
    local copy is as it was before the command. One stored file has changed, so the fetch
    downloads that part; the host returns 2 questions where `dataset.json` records 3."""
    pinned_example.store_copy()
    change_a_stored_file(pinned_example, "exq/test.jsonl")
    before = pinned_example.stored_files()
    two_questions = b"".join(pinned_example.sources["exq/test.jsonl"].splitlines(keepends=True)[:2])
    host = DatasetHost(pinned_example, published={"exq/test.jsonl": two_questions})

    differences = assert_failed(fetch(host))

    assert host.addresses == [address_of(pinned_example, "exq/test.jsonl")]
    assert names(differences[0], "exq") and has_number(differences[0], 2)
    assert has_number(differences[0], 3)
    assert pinned_example.stored_files() == before, (
        "the local copy changed although the fetch failed"
    )


# --- A download that fails (spec.md, "Edge Cases") ----------------------------------------------


def test_a_download_that_fails_ends_as_not_carried_out(pinned_example, fetch):
    """The edge case "the dataset cannot be downloaded": the fetch is not carried out and
    states the reason. contracts/cli.md: `reason: …`, `dataset fetch: not carried out`, exit
    code 2, never exit code 1. Without a manifest there is no local copy afterwards."""
    host = DatasetHost(pinned_example, unreachable={"exq/test.jsonl"})

    assert_not_carried_out(fetch(host))

    assert not pinned_example.manifest_file.exists(), (
        "a fetch that was not carried out leaves no manifest: an interrupted fetch never looks "
        "complete (research.md, section 9)"
    )


def test_a_download_that_fails_leaves_the_local_copy_as_it_was(pinned_example, fetch):
    """The edge case "the dataset cannot be downloaded": an existing local copy stays as it
    was. One stored file has changed and one is missing, so the fetch downloads two parts; the
    second of them cannot be downloaded, and the first is not moved into place either."""
    pinned_example.store_copy()
    change_a_stored_file(pinned_example, "ex/ex.jsonl")
    (pinned_example.data_dir / "exq_more/test.jsonl").unlink()
    before = pinned_example.stored_files()
    host = DatasetHost(pinned_example, unreachable={"exq_more/test.jsonl"})

    assert_not_carried_out(fetch(host))

    assert pinned_example.stored_files() == before, (
        "the local copy changed although the fetch was not carried out"
    )
