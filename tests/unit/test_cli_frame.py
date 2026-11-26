"""The frame of the command line (tasks T015): contracts/cli.md, "General rules".

Covers, for `python -m wixqa_rag` before any command of a story exists:

- "Exit codes": wrong arguments end with exit code 2, never with 0 or 1;
- "Output", rule 7: wrong arguments of the two dataset commands end with a `reason:` line and
  the verdict `not carried out` of that command; a command line that names no command has no
  verdict line, and its usage message goes to standard error;
- "Exit codes" and "Output", rules 3 and 5: an error that the program did not expect ends
  with exit code 2, a `reason:` line and the verdict `not carried out` as the last line of
  standard output, and never with exit code 1 (research.md, section 16);
- "Where a command is typed": a command typed where no `dataset.json` exists is not
  carried out.

The first group runs the command line itself. The two other rules cannot be reached from the
command line while the groups `dataset` and `index` have no commands (tasks.md, T019), so
these tests call the frame directly, through the one function they need from
`src/wixqa_rag/cli.py`:

    carry_out(name: str, action: Callable[[], int]) -> int

`name` is the start of the verdict line of a command (contracts/cli.md, "Verdict lines":
`dataset fetch`, `dataset check`, `index build`, `audit`). `action` does the work of the
command, prints its result lines and its verdict line, and returns the exit code. `carry_out`
returns what `action` returns and prints nothing after it. When the current directory has no
`dataset.json`, or when `action` raises an exception, `carry_out` prints a `reason:` line and
then `<name>: not carried out` to standard output and returns 2.

All documents named here are in specs/001-corpus-and-audit/.
"""

import importlib

import pytest

# The start of the verdict line of each command (contracts/cli.md, "Verdict lines").
VERDICT_NAMES = ("dataset fetch", "dataset check", "index build", "audit")


def load_cli():
    """Import the frame; it fails while `src/wixqa_rag/cli.py` does not exist (plan.md)."""
    return importlib.import_module("wixqa_rag.cli")


def assert_not_carried_out(name: str, exit_code: int, stdout: str) -> None:
    """Exit code 2, a `reason:` line, and the verdict `not carried out` as the last line."""
    lines = stdout.splitlines()
    assert exit_code == 2, (
        'contracts/cli.md, "Exit codes": a command that was not carried out ends with exit '
        f"code 2; got {exit_code}"
    )
    assert lines, 'contracts/cli.md, "Output": the verdict line goes to standard output'
    assert lines[-1] == f"{name}: not carried out", (
        'contracts/cli.md, "Output", rule 3: the last line of standard output is the verdict line'
    )
    reasons = [line for line in lines[:-1] if line.startswith("reason: ")]
    assert reasons, (
        'contracts/cli.md, "Output", rule 5: before a verdict of `not carried out`, the reason '
        "is printed on a line that starts with `reason:`"
    )
    assert all(len(line) > len("reason: ") for line in reasons), "a `reason:` line gives a reason"


# --- Wrong arguments end with exit code 2 -----------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        # Neither a group nor an option of the program.
        "python -m wixqa_rag no-such-group",
        "python -m wixqa_rag --no-such-option",
        # A group without a command, and no group at all: nothing to carry out.
        "python -m wixqa_rag",
        "python -m wixqa_rag dataset",
        "python -m wixqa_rag index",
        # Not a command of its group.
        "python -m wixqa_rag dataset no-such-command",
        "python -m wixqa_rag index no-such-command",
        # Wrong arguments of the commands that contracts/cli.md names: an unknown option, the
        # required `--index` left out, and `--index` without its value.
        "python -m wixqa_rag dataset check --no-such-option",
        "python -m wixqa_rag dataset fetch unexpected-argument",
        "python -m wixqa_rag index build --data-dir tests/data/example",
        "python -m wixqa_rag index audit --index",
    ],
)
def test_wrong_arguments_end_with_exit_code_2(run_command, command):
    """contracts/cli.md, "Exit codes": code 2 includes wrong arguments.

    Exit code 1 means only "a check or an audit found a difference", and exit code 0 means
    that the command did its work; wrong arguments are neither.
    """
    result = run_command(command)
    assert result.exit_code == 2, (
        'contracts/cli.md, "Exit codes": wrong arguments end with exit code 2; '
        f"`{command}` ended with {result.exit_code}. Standard error:\n{result.stderr}"
    )


def test_wrong_arguments_report_no_result_of_a_check(run_command):
    """contracts/cli.md, "Verdict lines": a command with wrong arguments did no work and found
    no difference, so its standard output ends with none of `passed`, `done` and `failed`."""
    result = run_command("python -m wixqa_rag dataset check --no-such-option")
    assert result.exit_code == 2, (
        'contracts/cli.md, "Exit codes": wrong arguments end with exit code 2; got '
        f"{result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert not result.last_line.endswith((": passed", ": done", ": failed"))


# --- Wrong arguments: with or without a verdict line (contracts/cli.md, "Output", rule 7) ----


@pytest.mark.parametrize(
    ("command", "name"),
    [
        # An unknown option, an argument too many, and an option without its value.
        ("python -m wixqa_rag dataset check --no-such-option", "dataset check"),
        ("python -m wixqa_rag dataset check unexpected-argument", "dataset check"),
        ("python -m wixqa_rag dataset check --data-dir", "dataset check"),
        ("python -m wixqa_rag dataset check --data-dir tests/data/example again", "dataset check"),
        ("python -m wixqa_rag dataset fetch --no-such-option", "dataset fetch"),
        ("python -m wixqa_rag dataset fetch unexpected-argument", "dataset fetch"),
        # `dataset fetch` takes no data directory: it fetches into the default one.
        ("python -m wixqa_rag dataset fetch --data-dir tests/data/example", "dataset fetch"),
    ],
)
def test_wrong_arguments_of_a_dataset_command_end_with_its_verdict(run_command, command, name):
    """contracts/cli.md, "Output", rule 7: when the command line names a command and its
    arguments are wrong, standard output gets a `reason:` line and the verdict
    `not carried out` of that command, and the exit code is 2."""
    result = run_command(command)

    assert_not_carried_out(name, result.exit_code, result.stdout)


@pytest.mark.parametrize(
    "command",
    [
        # The required `--index` left out, `--index` or `--data-dir` without its value, an
        # unknown option, and an argument too many.
        "python -m wixqa_rag index build",
        "python -m wixqa_rag index build --data-dir tests/data/example",
        "python -m wixqa_rag index build --index",
        "python -m wixqa_rag index build --index example --data-dir",
        "python -m wixqa_rag index build --index example --no-such-option",
        "python -m wixqa_rag index build --index example unexpected-argument",
        # `index build` writes no result file: `--json` belongs to `index audit`.
        "python -m wixqa_rag index build --index example --json result.json",
    ],
)
def test_wrong_arguments_of_index_build_end_with_its_verdict(run_command, command):
    """contracts/cli.md, "Output", rule 7: when the command line names a command and its
    arguments are wrong, standard output gets a `reason:` line and the verdict
    `not carried out` of that command, and the exit code is 2."""
    result = run_command(command, env={"DATABASE_URL": None, "OPENAI_API_KEY": None})

    assert_not_carried_out("index build", result.exit_code, result.stdout)


@pytest.mark.parametrize(
    "command",
    [
        "python -m wixqa_rag",
        "python -m wixqa_rag --no-such-option",
        "python -m wixqa_rag no-such-group",
        "python -m wixqa_rag dataset",
        "python -m wixqa_rag dataset no-such-command",
        "python -m wixqa_rag dataset --no-such-option",
        "python -m wixqa_rag index",
        "python -m wixqa_rag index no-such-command",
    ],
)
def test_a_command_line_that_names_no_command_has_no_verdict_line(run_command, command):
    """contracts/cli.md, "Output", rule 7: when the command line names no command (no
    arguments, an unknown group or command, a group without a command), no verdict line
    exists: the usage message goes to standard error, standard output stays empty, and the
    exit code is 2."""
    result = run_command(command)

    assert result.exit_code == 2, (
        f"`{command}` ended with {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert result.stdout == "", "standard output stays empty when no command is named"
    assert "usage" in result.stderr.lower(), "the usage message goes to standard error"


# --- An error that the program did not expect -------------------------------------------------


@pytest.mark.parametrize("name", VERDICT_NAMES)
def test_an_unexpected_error_ends_as_not_carried_out(name, temporary_root, monkeypatch, capfd):
    """contracts/cli.md, "Exit codes" and "Output": an error that the program did not expect
    ends with exit code 2, a `reason:` line and `<name>: not carried out` as the last line."""
    cli = load_cli()
    monkeypatch.chdir(temporary_root)

    def action() -> int:
        print("dataset: example")
        raise RuntimeError("the stand-in command broke")

    exit_code = cli.carry_out(name, action)

    assert_not_carried_out(name, exit_code, capfd.readouterr().out)


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("the stand-in command broke"),
        KeyError("no-such-key"),
        OSError("the stand-in device is full"),
        ZeroDivisionError("division by zero"),
        AssertionError("the stand-in command expected something else"),
    ],
    ids=lambda error: type(error).__name__,
)
def test_an_unexpected_error_never_ends_with_exit_code_1(error, temporary_root, monkeypatch, capfd):
    """research.md, section 16: an uncaught Python error would end with exit code 1 and look
    like "a difference was found"; whatever the error is, the exit code is 2."""
    cli = load_cli()
    monkeypatch.chdir(temporary_root)

    def action() -> int:
        raise error

    exit_code = cli.carry_out("dataset check", action)

    assert exit_code != 1, (
        'contracts/cli.md, "Exit codes": code 1 means that a check or an audit found a difference'
    )
    assert_not_carried_out("dataset check", exit_code, capfd.readouterr().out)


@pytest.mark.parametrize(
    ("name", "verdict", "exit_code_of_the_action"),
    [
        ("dataset check", "passed", 0),
        ("dataset check", "failed", 1),
        ("index build", "refused", 2),
        ("audit", "passed", 0),
        ("audit", "failed", 1),
    ],
)
def test_a_command_that_ends_by_itself_keeps_its_verdict_and_its_exit_code(
    name, verdict, exit_code_of_the_action, temporary_root, monkeypatch, capfd
):
    """contracts/cli.md, "Exit codes" and "Output", rule 3: the frame turns only an error into
    `not carried out`. A command that ran to its end keeps its exit code, 0, 1 or 2, and its
    verdict line stays the last line of standard output."""
    cli = load_cli()
    monkeypatch.chdir(temporary_root)

    def action() -> int:
        print(f"{name}: {verdict}")
        return exit_code_of_the_action

    exit_code = cli.carry_out(name, action)

    assert exit_code == exit_code_of_the_action
    assert capfd.readouterr().out.splitlines()[-1] == f"{name}: {verdict}"


# --- A command typed where no `dataset.json` exists -------------------------------------------


@pytest.mark.parametrize("name", VERDICT_NAMES)
def test_without_dataset_json_a_command_is_not_carried_out(name, tmp_path, monkeypatch, capfd):
    """contracts/cli.md, "Where a command is typed": a command reads `dataset.json` from the
    current directory; without it the command is not carried out."""
    cli = load_cli()
    monkeypatch.chdir(tmp_path)
    assert not (tmp_path / "dataset.json").exists()
    carried_out = []

    def action() -> int:
        carried_out.append(name)
        print(f"{name}: passed")
        return 0

    exit_code = cli.carry_out(name, action)

    assert carried_out == [], (
        'contracts/cli.md, "Where a command is typed": without `dataset.json` in the current '
        "directory the work of the command does not start"
    )
    assert_not_carried_out(name, exit_code, capfd.readouterr().out)


def test_with_dataset_json_the_command_is_carried_out(temporary_root, monkeypatch, capfd):
    """The counterpart of the test above: the same stand-in command, typed where a
    `dataset.json` exists, does its work. The two tests differ in that file only."""
    cli = load_cli()
    monkeypatch.chdir(temporary_root)
    assert (temporary_root / "dataset.json").is_file()
    carried_out = []

    def action() -> int:
        carried_out.append("dataset check")
        print("dataset check: passed")
        return 0

    exit_code = cli.carry_out("dataset check", action)

    assert carried_out == ["dataset check"]
    assert exit_code == 0
    assert capfd.readouterr().out.splitlines()[-1] == "dataset check: passed"
