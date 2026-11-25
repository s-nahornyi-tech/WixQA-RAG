"""The command line, `python -m wixqa_rag` (contracts/cli.md, "General rules").

This is the frame: the two groups `dataset` and `index`, the kinds of output line, and the
mapping of every outcome to an exit code. The groups have no commands yet.

A command is added to its group in `build_parser`: a parser with the arguments of the command
and the two defaults `verdict_name`, the start of its verdict line, and `run`, a function that
takes the parsed arguments. `run` prints the result lines, ends with `verdict(...)` and returns
its exit code. `main` calls it through `carry_out`.
"""

import argparse
import sys
import traceback
from collections.abc import Callable, Sequence

from wixqa_rag import settings

# The exit code of each verdict (contracts/cli.md, "Exit codes" and "Verdict lines"). Code 1
# means only that a check or an audit ran to the end and found a difference.
EXIT_CODES = {"done": 0, "passed": 0, "failed": 1, "refused": 2, "not carried out": 2}


def result(name: str, value: object) -> None:
    """Print a result line, `name: value`, to standard output."""
    print(f"{name}: {value}")


def difference(text: str) -> None:
    """Print one difference; every difference comes before a verdict of `failed`."""
    print(f"difference: {text}")


def reason(text: str) -> None:
    """Print the reason; it comes before a verdict of `refused` or `not carried out`."""
    print(f"reason: {text}")


def progress(text: str) -> None:
    """Print a progress message to standard error."""
    print(text, file=sys.stderr)


def verdict(name: str, outcome: str) -> int:
    """Print the verdict line, the last line of standard output, and return its exit code."""
    exit_code = EXIT_CODES[outcome]
    print(f"{name}: {outcome}")
    return exit_code


def carry_out(name: str, action: Callable[[], int]) -> int:
    """Do the work of one command and return its exit code.

    `name` is the start of the verdict line of the command. `action` prints the result lines
    and the verdict line and returns the exit code, which is passed on unchanged. Without
    `dataset.json` in the current directory the action does not start. An error that the
    action raises ends as `not carried out` with exit code 2, never with exit code 1.
    """
    if not settings.DATASET_JSON.is_file():
        reason(f"{settings.DATASET_JSON} is not in the current directory")
        return verdict(name, "not carried out")
    try:
        return action()
    except settings.MissingSetting as error:
        reason(str(error))
    except Exception as error:
        progress(settings.hide_values(traceback.format_exc()).rstrip())
        text = settings.hide_values(f"unexpected error ({type(error).__name__}): {error}")
        reason(" ".join(text.split()))
    return verdict(name, "not carried out")


def _add_group(groups, name: str, description: str):
    """Add a group to the command line and return the place where its commands are added."""
    group = groups.add_parser(name, help=description, description=description)
    return group.add_subparsers(dest="command", metavar="COMMAND", required=True)


def build_parser() -> argparse.ArgumentParser:
    """The arguments of the command line. Wrong arguments end the program with exit code 2."""
    parser = argparse.ArgumentParser(
        prog="python -m wixqa_rag",
        description="The dataset, the index and the audit of the WixQA study.",
    )
    groups = parser.add_subparsers(dest="group", metavar="GROUP", required=True)
    _add_group(groups, "dataset", "The local copy of the dataset at the pinned revision.")
    _add_group(groups, "index", "The retrieval index built from the corpus.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Read the command line, carry out the command and return its exit code."""
    arguments = build_parser().parse_args(argv)
    return carry_out(arguments.verdict_name, lambda: arguments.run(arguments))
