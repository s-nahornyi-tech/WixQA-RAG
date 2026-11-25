"""The helper `run_command` of tests/conftest.py does what the acceptance tests rely on (T014).

Covers:

- spec.md, "Assumptions": a command line is typed in a POSIX shell at the repository root, in
  the project's Python environment; the helper passes the line on unchanged;
- research.md, section 4: the workflows read the verdict lines of the commands from the
  output that pytest captured for each test, so the helper prints the command line and the
  standard output of the command to the standard output of the test;
- contracts/cli.md, "Settings", and FR-017: the settings reach a command from the
  environment, a test can change or remove one for a single command, and the helper never
  prints the value of one.

These tests run shell commands only and use no code of the package, so they pass before any
implementation exists. The values of the settings below are invented; none is a credential.
All documents named here are in specs/001-corpus-and-audit/.
"""

import sys
from pathlib import Path

INVENTED_KEY = "invented-key-value-that-is-never-printed-52c8e0"
INVENTED_STORE = "postgresql://store-user@store.invalid:5432/value-that-is-never-printed"

# Prints whether the command received the key, without printing the key.
KEY_IS_SET = 'test -n "${OPENAI_API_KEY:-}" && echo "key: set" || echo "key: not set"'


def test_a_command_is_typed_at_the_repository_root(run_command, repository_root):
    """spec.md, "Assumptions": commands are typed at the repository root."""
    result = run_command("pwd -P && test -f dataset.json && test -f pyproject.toml")

    assert result.exit_code == 0
    assert Path(result.last_line) == repository_root.resolve()


def test_a_command_line_goes_unchanged_through_a_posix_shell(run_command):
    """spec.md, "Acceptance Checks": the checks chain commands with `&&`; the chain stops at
    the first command that fails, and its exit code is the exit code of the line."""
    result = run_command("echo first && sh -c 'exit 2' && echo never")

    assert result.exit_code == 2
    assert result.lines == ["first"]


def test_standard_output_and_standard_error_are_returned_apart(run_command):
    """contracts/cli.md, "Output", rule 1: result lines go to standard output and progress
    messages to standard error; the checks read standard output."""
    result = run_command("echo 'articles: 5' && echo 'reading the corpus' >&2")

    assert result.stdout == "articles: 5\n"
    assert result.stderr == "reading the corpus\n"


def test_the_last_line_of_standard_output_is_at_hand(run_command):
    """contracts/cli.md, "Output", rule 3: the last line of standard output is the verdict."""
    result = run_command("echo 'dataset: example' && echo 'dataset check: passed'")

    assert result.last_line == "dataset check: passed"
    assert run_command("true").last_line == ""


def test_python_in_a_command_line_is_the_interpreter_of_the_test_run(run_command):
    """spec.md, "Assumptions": commands run in the project's Python environment, the one that
    runs the tests and has the package installed."""
    result = run_command('python -c "import sys, wixqa_rag; print(sys.prefix)"')

    assert result.exit_code == 0, result.stderr
    assert result.last_line == sys.prefix


def test_the_command_line_and_its_output_are_printed_for_the_report(run_command, capsys):
    """research.md, section 4: a workflow step reads the verdict lines from the output that
    pytest captured for a test. A verdict line stays a whole line of that output."""
    run_command("echo 'missing from index: 0' && echo 'audit: passed'")

    printed = capsys.readouterr().out.splitlines()
    assert printed[0] == "$ echo 'missing from index: 0' && echo 'audit: passed'"
    assert "missing from index: 0" in printed
    assert "audit: passed" in printed
    assert printed[-1] == "[exit code 0]"


def test_the_standard_error_of_a_command_is_printed_apart(run_command, capsys):
    """A message on standard error, such as the reason why Python could not start the
    program, is shown with the test, apart from the standard output of the command."""
    run_command("echo 'audit: not carried out' && echo 'no such module' >&2 && exit 2")

    captured = capsys.readouterr()
    assert "audit: not carried out" in captured.out.splitlines()
    assert "[exit code 2]" in captured.out.splitlines()
    assert "no such module" not in captured.out.splitlines()
    assert captured.err.splitlines() == ["no such module"]


def test_the_environment_of_the_test_run_reaches_the_command(run_command, monkeypatch):
    """contracts/cli.md, "Settings": a command reads its settings from the environment; the
    helper passes the environment of the test run on."""
    monkeypatch.setenv("OPENAI_API_KEY", INVENTED_KEY)
    monkeypatch.setenv("WIXQA_HELPER_MARK", "passed on")

    assert run_command(KEY_IS_SET).last_line == "key: set"
    assert run_command('echo "$WIXQA_HELPER_MARK"').last_line == "passed on"


def test_a_setting_can_be_removed_for_a_single_command(run_command, monkeypatch):
    """A test of a missing setting removes it for one command; the next command has it again."""
    monkeypatch.setenv("OPENAI_API_KEY", INVENTED_KEY)

    assert run_command(KEY_IS_SET, env={"OPENAI_API_KEY": None}).last_line == "key: not set"
    assert run_command(KEY_IS_SET).last_line == "key: set"


def test_a_setting_can_be_set_for_a_single_command(run_command, monkeypatch):
    """A test sets or replaces a setting for one command; the next command does not see it."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert run_command(KEY_IS_SET, env={"OPENAI_API_KEY": INVENTED_KEY}).last_line == "key: set"
    assert run_command(KEY_IS_SET).last_line == "key: not set"


def test_a_command_line_can_remove_a_setting_itself(run_command, monkeypatch):
    """spec.md, AC-014: the check writes `env -u OPENAI_API_KEY ...`; the line works as written."""
    monkeypatch.setenv("OPENAI_API_KEY", INVENTED_KEY)

    result = run_command(f"env -u OPENAI_API_KEY sh -c '{KEY_IS_SET}'")

    assert result.exit_code == 0
    assert result.last_line == "key: not set"


def test_the_value_of_the_provider_key_is_never_printed_or_returned(
    run_command, monkeypatch, capsys
):
    """FR-017: no credential appears in the output of a command. When a command prints the
    key all the same, the helper keeps the value out of the output of the test and out of the
    text it returns, and names the setting in `settings_printed`."""
    monkeypatch.setenv("OPENAI_API_KEY", INVENTED_KEY)

    result = run_command('echo "key=$OPENAI_API_KEY" && echo "$OPENAI_API_KEY" >&2')

    captured = capsys.readouterr()
    for text in (captured.out, captured.err, result.stdout, result.stderr, result.command):
        assert INVENTED_KEY not in text
    assert result.stdout == "key=<value of OPENAI_API_KEY>\n"
    assert result.settings_printed == ("OPENAI_API_KEY",)


def test_a_value_set_for_a_single_command_is_hidden_as_well(run_command, monkeypatch, capsys):
    """contracts/cli.md, "Settings": no command prints the value of a setting. The helper
    hides `DATABASE_URL` like the key, also when the value was set for one command only."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    result = run_command('echo "store: $DATABASE_URL"', env={"DATABASE_URL": INVENTED_STORE})

    assert INVENTED_STORE not in capsys.readouterr().out
    assert result.stdout == "store: <value of DATABASE_URL>\n"
    assert result.settings_printed == ("DATABASE_URL",)


def test_a_command_that_prints_no_setting_names_none(run_command, monkeypatch):
    """The counterpart of the two tests above: `settings_printed` is empty for a command that
    keeps the values to itself, which is what a test of FR-017 expects."""
    monkeypatch.setenv("OPENAI_API_KEY", INVENTED_KEY)
    monkeypatch.setenv("DATABASE_URL", INVENTED_STORE)

    result = run_command(KEY_IS_SET)

    assert result.stdout == "key: set\n"
    assert result.settings_printed == ()


def test_a_command_can_be_typed_in_a_temporary_repository_root(run_command, temporary_root):
    """research.md, section 4: a test never leaves a file in the checkout. A command that
    writes below the current directory is typed in a temporary repository root."""
    result = run_command(
        "pwd -P && test -f dataset.json && echo written > note.txt", cwd=temporary_root
    )

    assert result.exit_code == 0
    assert Path(result.lines[0]) == temporary_root.resolve()
    assert (temporary_root / "note.txt").read_text(encoding="utf-8") == "written\n"
