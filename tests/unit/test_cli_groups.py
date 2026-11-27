"""The two new groups of the command line (task T010): `set` and `run`.

Covers, for `python -m wixqa_rag` before any command of the two groups exists:

- specs/002-evaluation-harness/contracts/cli.md, "General rules", "Groups": two new groups
  stand next to `dataset` and `index`, `set` and `run`;
- the same file, "General rules", and spec 1's contracts/cli.md, "Output", rule 7: a command
  line that names no command prints the usage message to standard error, nothing to standard
  output, and ends with exit code 2. A group without a command names no command.

A command line that names something which is not a group ends in the same way: exit code 2,
a usage message on standard error and an empty standard output. So these tests tell a group
from a word that is not one by the usage message: the usage message of a group is the
group's own and names the group after the program, as that of `dataset` and `index` does
(`usage: python -m wixqa_rag dataset ...`), while the usage message for an unknown word is
that of the program. The groups are added in `build_parser` with the existing helpers
(contracts/harness.md, "`wixqa_rag.cli`: additions"), which give exactly this.

All documents named here are in specs/002-evaluation-harness/ unless spec 1 is named.
"""

import re

import pytest

NEW_GROUPS = ("set", "run")
GROUPS = ("dataset", "index", *NEW_GROUPS)


def usage_lines(stderr: str) -> list[str]:
    return [line for line in stderr.splitlines() if line.lower().startswith("usage:")]


def names_the_group(stderr: str, group: str) -> bool:
    """Whether the usage message on standard error is the group's own: its usage line names
    the group directly after the program."""
    return any(
        re.search(rf"wixqa_rag {re.escape(group)}(\s|$)", line) for line in usage_lines(stderr)
    )


def assert_names_no_command(result, command: str) -> None:
    """contracts/cli.md, "General rules": the usage message to standard error, nothing to
    standard output, exit code 2."""
    assert result.exit_code == 2, (
        f"`{command}` ended with {result.exit_code}. Standard error:\n{result.stderr}"
    )
    assert result.stdout == "", "standard output stays empty when no command is named"
    assert usage_lines(result.stderr), "the usage message goes to standard error"


@pytest.mark.parametrize("group", NEW_GROUPS)
def test_a_new_group_exists(run_command, group):
    """contracts/cli.md, "Groups": the groups `set` and `run` exist. The usage message for
    the group alone is the group's own, not the program's message for an unknown word."""
    unknown = run_command("python -m wixqa_rag no-such-group")
    assert not names_the_group(unknown.stderr, "no-such-group"), (
        "the usage message for a word that is not a group is that of the program"
    )

    command = f"python -m wixqa_rag {group}"
    result = run_command(command)

    assert names_the_group(result.stderr, group), (
        f"`{command}` must print the usage message of the group `{group}`; "
        f"standard error was:\n{result.stderr}"
    )


@pytest.mark.parametrize("group", NEW_GROUPS)
def test_a_new_group_without_a_command_prints_its_usage_and_ends_with_exit_code_2(
    run_command, group
):
    """contracts/cli.md, "General rules": a group without a command prints the usage message
    to standard error, nothing to standard output, and ends with exit code 2."""
    command = f"python -m wixqa_rag {group}"
    result = run_command(command)

    assert_names_no_command(result, command)
    assert names_the_group(result.stderr, group), (
        f"the usage message is that of the group `{group}`; standard error was:\n{result.stderr}"
    )
    assert "invalid choice" not in result.stderr, f"`{group}` is a group of the command line"


@pytest.mark.parametrize("group", NEW_GROUPS)
def test_a_new_group_without_a_command_has_no_verdict_line(run_command, group):
    """Spec 1's contracts/cli.md, "Output", rule 7: when the command line names no command,
    no verdict line exists. A group is not a command, so no line `set: ...`, `run: ...` or
    `... not carried out` is printed on either stream."""
    result = run_command(f"python -m wixqa_rag {group}")

    assert names_the_group(result.stderr, group), f"standard error was:\n{result.stderr}"
    assert result.stdout == ""
    assert "not carried out" not in result.stderr
    assert "reason:" not in result.stderr


@pytest.mark.parametrize(
    ("group", "arguments"),
    [
        (group, arguments)
        for group in NEW_GROUPS
        for arguments in ("no-such-command", "--no-such-option")
    ],
)
def test_a_new_group_with_something_that_is_no_command_names_no_command(
    run_command, group, arguments
):
    """Spec 1's contracts/cli.md, "Output", rule 7: an unknown command of a group names no
    command: the usage message of the group on standard error, an empty standard output,
    exit code 2. The same holds for `dataset` and `index` (tests/unit/test_cli_frame.py)."""
    command = f"python -m wixqa_rag {group} {arguments}"
    result = run_command(command)

    assert_names_no_command(result, command)
    assert names_the_group(result.stderr, group), (
        f"the usage message is that of the group `{group}`; standard error was:\n{result.stderr}"
    )


def test_the_new_groups_stand_next_to_dataset_and_index(run_command):
    """contracts/cli.md, "Groups": "Two new groups stand next to `dataset` and `index`". All
    four answer to their name with their own usage message, and the two groups of spec 1
    still do so with exit code 2 and an empty standard output."""
    missing = []
    for group in GROUPS:
        command = f"python -m wixqa_rag {group}"
        result = run_command(command)
        assert_names_no_command(result, command)
        if not names_the_group(result.stderr, group):
            missing.append(group)

    assert missing == [], f"not a group of the command line: {missing}"


@pytest.mark.parametrize("group", NEW_GROUPS)
def test_the_parser_of_the_command_line_knows_a_new_group(group, capsys):
    """contracts/harness.md, "`wixqa_rag.cli`: additions": the groups `set` and `run` are
    added in `build_parser`. The parser ends a command line of the group alone with exit
    code 2 and the usage message of the group on standard error."""
    from wixqa_rag import cli

    with pytest.raises(SystemExit) as stopped:
        cli.build_parser().parse_args([group])

    captured = capsys.readouterr()
    assert stopped.value.code == 2
    assert captured.out == ""
    assert names_the_group(captured.err, group), f"standard error was:\n{captured.err}"
