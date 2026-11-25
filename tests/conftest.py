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

import os
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
