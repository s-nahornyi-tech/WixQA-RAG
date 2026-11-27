"""Helpers shared by every test.

The helper `run_command` runs a command line exactly as the spec writes it
(specs/001-corpus-and-audit/spec.md, "Acceptance Checks" and "Assumptions"): through a POSIX
shell, at the repository root, in the Python environment of the test run.

It also prints the command line and the standard output of the command to the standard output
of the test. pytest captures that output for each test, and the workflows read the verdict
lines of the commands from pytest's JUnit report (.github/scripts/junit_annotations.py).

The value of a setting (contracts/cli.md, "Settings") never leaves the helper: where a command
printed one, the helper replaces it before it prints or returns the text, and the result names
the setting in `settings_printed`.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

# The settings of contracts/cli.md, "Settings". A command never prints the value of one.
SETTING_NAMES = ("DATABASE_URL", "OPENAI_API_KEY")

# A shorter value is not looked for in the output: it would be found by chance.
SHORTEST_VALUE_LOOKED_FOR = 8

EXAMPLE_DATA = REPOSITORY_ROOT / "tests" / "data" / "example"

# The verdict lines of the commands of spec 1 and of spec 2 (their contracts/cli.md, "Verdict
# lines").
VERDICT_LINE = re.compile(
    r"(dataset fetch|dataset check|index build|audit|set build|set check"
    r"|run report|run check|run compare): (done|passed|failed|refused|not carried out)"
)

HARNESS_DATA = REPOSITORY_ROOT / "tests" / "data" / "harness"
EXAMPLE_SETS = REPOSITORY_ROOT / "tests" / "data" / "sets"

# Where an acceptance check of spec 2 writes the question sets that it builds from example
# data: `--sets-dir data/sets`, in the folder `data/` that Git ignores
# (specs/002-evaluation-harness/data-model.md, "Question set").
BUILT_SETS = REPOSITORY_ROOT / "data" / "sets"

# A full commit hash that is not the pinned revision of the repository, so that a place or an
# address in a test can only come from the `dataset.json` of the temporary repository root.
OTHER_REVISION = "0123456789abcdef0123456789abcdef01234567"


@dataclass(frozen=True)
class CommandResult:
    """What one command line left behind."""

    command: str
    exit_code: int
    # Standard output and standard error as text. Where the command printed the value of a
    # setting, the value is replaced by "<value of NAME>".
    stdout: str
    stderr: str
    # The names of the settings whose value the command printed, on either stream. A test of
    # FR-017 expects this to be empty.
    settings_printed: tuple[str, ...] = ()

    @property
    def lines(self) -> list[str]:
        """The lines of standard output, in order."""
        return self.stdout.splitlines()

    @property
    def last_line(self) -> str:
        """The last line of standard output: the verdict line (contracts/cli.md, "Output")."""
        lines = self.lines
        return lines[-1] if lines else ""

    def blocks(self) -> list[list[str]]:
        """The lines of standard output, one list for each command of a line that chains
        several commands with `&&`: a command prints its verdict line last, so a block ends
        with a verdict line. Lines after the last verdict line form a block of their own."""
        blocks: list[list[str]] = [[]]
        for line in self.lines:
            blocks[-1].append(line)
            if VERDICT_LINE.fullmatch(line):
                blocks.append([])
        return blocks if blocks[-1] else blocks[:-1]

    @property
    def reasons(self) -> list[str]:
        """The `reason:` lines of standard output, without the `reason: ` in front."""
        return [line[len("reason: ") :] for line in self.lines if line.startswith("reason: ")]

    @property
    def differences(self) -> list[str]:
        """The `difference:` lines of standard output, without the `difference: ` in front."""
        return [
            line[len("difference: ") :] for line in self.lines if line.startswith("difference: ")
        ]


def _environment(changes: Mapping[str, str | None] | None) -> dict[str, str]:
    """The environment of the test run, with the changes of one command applied."""
    environment = dict(os.environ)
    # "python" in a command line is the interpreter of the test run, also when the tests were
    # started without activating the project's environment.
    interpreter_folder = str(Path(sys.executable).parent)
    folders = environment.get("PATH", "").split(os.pathsep)
    if folders[0] != interpreter_folder:
        environment["PATH"] = os.pathsep.join([interpreter_folder, *filter(None, folders)])
    for name, value in (changes or {}).items():
        if value is None:
            environment.pop(name, None)
        else:
            environment[name] = value
    return environment


def _values_to_hide(environment: Mapping[str, str]) -> dict[str, set[str]]:
    """The values of the settings that a command could have received."""
    values: dict[str, set[str]] = {}
    for name in SETTING_NAMES:
        for source in (os.environ, environment):
            value = source.get(name, "")
            if len(value) >= SHORTEST_VALUE_LOOKED_FOR:
                values.setdefault(name, set()).add(value)
    return values


def _hide(text: str, values: Mapping[str, set[str]]) -> tuple[str, set[str]]:
    """Replace every value of a setting in the text; return the text and the settings found."""
    found: set[str] = set()
    for name, candidates in values.items():
        for value in sorted(candidates, key=len, reverse=True):
            if value in text:
                found.add(name)
                text = text.replace(value, f"<value of {name}>")
    return text, found


def _run_command(
    command: str,
    *,
    env: Mapping[str, str | None] | None = None,
    cwd: Path | None = None,
    timeout: float | None = None,
) -> CommandResult:
    environment = _environment(env)
    folder = REPOSITORY_ROOT if cwd is None else Path(cwd)
    completed = subprocess.run(
        ["/bin/sh", "-c", command],
        cwd=folder,
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=timeout,
        check=False,
    )

    values = _values_to_hide(environment)
    shown_command, _ = _hide(command, values)
    stdout, found_in_stdout = _hide(completed.stdout.decode("utf-8", errors="replace"), values)
    stderr, found_in_stderr = _hide(completed.stderr.decode("utf-8", errors="replace"), values)

    # The output of the test: the command line, then the standard output of the command as
    # the command printed it, so that a verdict line stays a line of its own.
    print(f"$ {shown_command}")
    if folder != REPOSITORY_ROOT:
        print(f"[typed in {folder}]")
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    print(f"[exit code {completed.returncode}]", flush=True)
    if stderr:
        print(stderr, end="" if stderr.endswith("\n") else "\n", file=sys.stderr, flush=True)

    return CommandResult(
        command=shown_command,
        exit_code=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        settings_printed=tuple(sorted(found_in_stdout | found_in_stderr)),
    )


@pytest.fixture
def run_command() -> Callable[..., CommandResult]:
    """Run one command line of the spec and return its exit code and its output.

        result = run_command("python -m wixqa_rag dataset check --data-dir tests/data/example")
        assert result.exit_code == 0
        assert result.last_line == "dataset check: passed"

    - `command` is passed unchanged to a POSIX shell (`/bin/sh -c`), so `&&` and `env -u NAME`
      work as they do when an operator types the line.
    - The command is typed at the repository root. `cwd` names another folder, for a command
      that is tried in a temporary repository root.
    - The environment is that of the test run, so `DATABASE_URL` and `OPENAI_API_KEY` reach
      the command when the run has them. `env` changes it for this one command: a string sets
      a variable, and `None` removes it, for example `env={"OPENAI_API_KEY": None}`.
    - `timeout` is in seconds. Without it the helper sets no time limit.
    """
    return _run_command


@pytest.fixture(scope="session")
def repository_root() -> Path:
    """The root of the checkout, where the commands of the spec are typed."""
    return REPOSITORY_ROOT


@pytest.fixture
def temporary_root(tmp_path: Path) -> Path:
    """A temporary folder that stands for the repository root.

    It holds a copy of the repository's `dataset.json` and nothing else. A test that tries code
    which reads or writes below the current directory works here, so that no file appears in
    the checkout (specs/001-corpus-and-audit/research.md, section 4; tasks.md, T039).
    """
    root = tmp_path / "repository-root"
    root.mkdir()
    shutil.copyfile(REPOSITORY_ROOT / "dataset.json", root / "dataset.json")
    return root


def count_rows(data: bytes) -> int:
    """The rows of a part file: its non-empty lines (data-model.md, "Part")."""
    return sum(1 for line in data.split(b"\n") if line.strip())


@dataclass(frozen=True)
class PinnedExample:
    """A temporary repository root whose `dataset.json` pins a small dataset of example data.

    It stands for the checkout with the published dataset: one corpus part and two question
    parts, in folders of their own and with two files of the same name, as `Wix/WixQA` has
    them (contracts/records.md, "`dataset.json`"). The second question part has no line feed
    after its last row. `sources` holds, for each path inside the dataset, the bytes that the
    dataset host would return. The default data directory does not exist until a test stores
    a copy or fetches one.
    """

    root: Path
    name: str
    revision: str
    # As `dataset.json` lists them: `name`, `role`, `path` and `rows`.
    parts: tuple[dict, ...]
    sources: dict[str, bytes]

    @property
    def data_dir(self) -> Path:
        """The default data directory (data-model.md, "Data directory")."""
        return self.root / "data" / "wixqa" / self.revision

    @property
    def manifest_file(self) -> Path:
        return self.data_dir / "manifest.json"

    def read_dataset_json(self) -> dict:
        return json.loads((self.root / "dataset.json").read_text(encoding="utf-8"))

    def write_dataset_json(self, document: object) -> None:
        text = json.dumps(document, indent=2) + "\n"
        (self.root / "dataset.json").write_text(text, encoding="utf-8")

    def manifest_parts(self) -> list[dict]:
        """The parts as the manifest of a complete, matching copy records them."""
        return [
            {
                **part,
                "bytes": len(self.sources[part["path"]]),
                "sha256": hashlib.sha256(self.sources[part["path"]]).hexdigest(),
            }
            for part in self.parts
        ]

    def write_manifest(self, document: object) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        text = json.dumps(document, indent=2) + "\n"
        self.manifest_file.write_text(text, encoding="utf-8")

    def store_copy(self) -> None:
        """Write a complete, matching local copy by hand: the part files, then the manifest."""
        for path, data in self.sources.items():
            file = self.data_dir / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
        self.write_manifest(
            {
                "name": self.name,
                "revision": self.revision,
                "fetched_at": "2026-11-24T10:15:00Z",
                "parts": self.manifest_parts(),
            }
        )

    def stored_files(self) -> dict[str, bytes]:
        """Every file below the default data directory: its path inside it -> its bytes."""
        if not self.data_dir.is_dir():
            return {}
        return {
            file.relative_to(self.data_dir).as_posix(): file.read_bytes()
            for file in sorted(self.data_dir.rglob("*"))
            if file.is_file()
        }


@pytest.fixture
def pinned_example(tmp_path: Path) -> PinnedExample:
    """A temporary repository root that pins example data; see `PinnedExample`.

    The root holds `dataset.json` and nothing else. A test that works here leaves no file in
    the checkout (specs/001-corpus-and-audit/research.md, section 4; tasks.md, T039).
    """
    root = tmp_path / "pinned-example-root"
    root.mkdir()
    articles = (EXAMPLE_DATA / "ex.jsonl").read_bytes()
    questions = (EXAMPLE_DATA / "exq.jsonl").read_bytes()
    sources = {
        "ex/ex.jsonl": articles,
        "exq/test.jsonl": questions,
        # The same questions, published without a line feed after the last row.
        "exq_more/test.jsonl": questions.removesuffix(b"\n"),
    }
    parts = tuple(
        {"name": name, "role": role, "path": path, "rows": count_rows(sources[path])}
        for name, role, path in (
            ("ex", "corpus", "ex/ex.jsonl"),
            ("exq", "questions", "exq/test.jsonl"),
            ("exq_more", "questions", "exq_more/test.jsonl"),
        )
    )
    example = PinnedExample(
        root=root, name="Wix/WixQA", revision=OTHER_REVISION, parts=parts, sources=sources
    )
    example.write_dataset_json(
        {"name": example.name, "revision": example.revision, "parts": list(parts)}
    )
    return example


# --- The example data of spec 2 (specs/002-evaluation-harness) --------------------------------


@pytest.fixture
def built_sets() -> Path:
    """`data/sets` of the checkout, empty of what an earlier test or an operator left there.

    Several acceptance checks of spec 2 build question sets with `--sets-dir data/sets`, typed
    at the repository root, and the command line of a check is not changed. A version is
    written once, so a record left by another test would change the outcome. The fixture
    removes the folder `data/sets` before the test and again after it. `data/` is ignored by
    Git, and nothing outside `data/sets` is touched: never `evals/`.
    """
    shutil.rmtree(BUILT_SETS, ignore_errors=True)
    yield BUILT_SETS
    shutil.rmtree(BUILT_SETS, ignore_errors=True)


def canonical_record(document: object) -> bytes:
    """The canonical form of a question-set record (specs/002-evaluation-harness/contracts/
    records.md, "The canonical form"), written here without code of the package."""
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


@dataclass(frozen=True)
class HarnessCopy:
    """A temporary repository root with a copy of the example data of spec 2.

    `root` holds `dataset.json`, the data directory `data/harness` (a copy of
    `tests/data/harness`) and the sets directory `data/sets` (a copy of `tests/data/sets`). A
    test changes the copies as it needs and never a file of the checkout. A command is typed
    in `root` with the relative paths `DATA_DIR` and `SETS_DIR`.
    """

    root: Path

    DATA_DIR = "data/harness"
    SETS_DIR = "data/sets"

    @property
    def data_dir(self) -> Path:
        return self.root / "data" / "harness"

    @property
    def sets_dir(self) -> Path:
        return self.root / "data" / "sets"

    def rows(self, part: str) -> list[dict]:
        text = (self.data_dir / f"{part}.jsonl").read_text(encoding="utf-8")
        return [json.loads(line) for line in text.split("\n") if line.strip()]

    def change_rows(self, part: str, change: Callable[[list[dict]], None]) -> None:
        """Change the rows of one part and write the manifest again from the file, so that
        the data directory still passes the dataset check."""
        rows = self.rows(part)
        change(rows)
        data = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode("utf-8")
        (self.data_dir / f"{part}.jsonl").write_bytes(data)
        manifest = json.loads((self.data_dir / "manifest.json").read_text(encoding="utf-8"))
        for entry in manifest["parts"]:
            if entry["name"] == part:
                entry.update(
                    rows=len(rows), bytes=len(data), sha256=hashlib.sha256(data).hexdigest()
                )
        text = json.dumps(manifest, indent=2) + "\n"
        (self.data_dir / "manifest.json").write_text(text, encoding="utf-8")

    def part_entry(self, part: str) -> dict:
        """A part as a question-set record names it: name, rows and SHA-256 of its file."""
        data = (self.data_dir / f"{part}.jsonl").read_bytes()
        return {"name": part, "rows": count_rows(data), "sha256": hashlib.sha256(data).hexdigest()}

    def gold(self) -> dict[str, list[str]]:
        """Question identifier -> the `article_ids` of its row, for the three question parts."""
        return {
            f"{part}-{number:03d}": row["article_ids"]
            for part in ("hxa", "hxb", "hxc")
            for number, row in enumerate(self.rows(part), 1)
        }

    def record(self, version: str) -> dict:
        """The document of a record of the sets directory."""
        return json.loads((self.sets_dir / f"{version}.json").read_text(encoding="utf-8"))

    def fingerprint(self, version: str) -> str:
        return hashlib.sha256((self.sets_dir / f"{version}.json").read_bytes()).hexdigest()

    def write_record(self, document: dict) -> Path:
        """Write a record by hand, in the canonical form, under its `version`."""
        file = self.sets_dir / f"{document['version']}.json"
        file.write_bytes(canonical_record(document))
        return file

    def change_record(self, version: str, change: Callable[[dict], None]) -> dict:
        """Change one record of the sets directory by hand and write it again."""
        document = self.record(version)
        change(document)
        (self.sets_dir / f"{version}.json").write_bytes(canonical_record(document))
        return document

    def rewrite_records(self) -> None:
        """Bring the records `harness`, `harness-hxc`, `harness-half` and `harness-half-rest`
        in line with the data directory after `change_rows`: the fingerprints of the parts,
        the gold article ids of every question, and `of_fingerprint` of the complement. The
        questions that each record holds stay as they are."""
        gold = self.gold()
        for version in ("harness", "harness-hxc", "harness-half", "harness-half-rest"):
            document = self.record(version)
            document["dataset"]["parts"] = [
                self.part_entry(part["name"]) for part in document["dataset"]["parts"]
            ]
            for question in document["questions"]:
                question["article_ids"] = gold[question["id"]]
            if document["rule"]["kind"] == "complement":
                document["rule"]["of_fingerprint"] = self.fingerprint(document["rule"]["of"])
            self.write_record(document)

    def sets(self) -> dict[str, bytes]:
        """Every file below the sets directory: its path inside it -> its bytes."""
        if not self.sets_dir.is_dir():
            return {}
        return {
            file.relative_to(self.sets_dir).as_posix(): file.read_bytes()
            for file in sorted(self.sets_dir.rglob("*"))
            if file.is_file()
        }


@pytest.fixture
def harness_copy(temporary_root: Path) -> HarnessCopy:
    """A temporary repository root with a copy of `tests/data/harness` and of
    `tests/data/sets`; see `HarnessCopy`. It is not the current directory of the test."""
    copy = HarnessCopy(root=temporary_root)
    shutil.copytree(HARNESS_DATA, copy.data_dir)
    shutil.copytree(EXAMPLE_SETS, copy.sets_dir)
    return copy
