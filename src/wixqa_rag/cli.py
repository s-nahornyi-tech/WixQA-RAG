"""The command line, `python -m wixqa_rag` (contracts/cli.md, "General rules").

The frame: the four groups `dataset`, `index`, `set` and `run`, the kinds of output line, and
the mapping of every outcome to an exit code.

A command is added to its group in `build_parser` with `_add_command`: the start of its
verdict line and `run`, a function that takes the parsed arguments, prints the result lines,
ends with `verdict(...)` and returns its exit code. `main` calls it through `carry_out`. A
command whose arguments have a rule that holds between them sets `wrong`, a function that
takes the parsed arguments and returns the reason for which they are wrong, or None.
"""

import argparse
import re
import sys
import traceback
from collections.abc import Callable, Sequence
from pathlib import Path

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


class _CommandParser(argparse.ArgumentParser):
    """The arguments of one command. Wrong arguments end with the verdict of the command."""

    verdict_name = ""

    def error(self, message: str):
        self.print_usage(sys.stderr)
        sys.exit(_wrong_arguments(self.verdict_name, message))


def _wrong_arguments(name: str, message: str) -> int:
    """contracts/cli.md, "Output", rule 7: a named command with wrong arguments."""
    reason(" ".join(settings.hide_values(message).split()))
    return verdict(name, "not carried out")


def _add_group(groups, name: str, description: str):
    """Add a group to the command line and return the place where its commands are added."""
    group = groups.add_parser(name, help=description, description=description)
    return group.add_subparsers(
        dest="command", metavar="COMMAND", required=True, parser_class=_CommandParser
    )


def _add_command(commands, name: str, verdict_name: str, run, description: str):
    """Add a command to its group and return its parser, for the arguments of the command."""
    command = commands.add_parser(
        name, help=description, description=description, allow_abbrev=False
    )
    command.verdict_name = verdict_name
    command.set_defaults(verdict_name=verdict_name, run=run)
    return command


def _dataset_fetch(arguments: argparse.Namespace) -> int:
    from wixqa_rag import dataset

    return dataset.fetch(dataset.download)


def _dataset_check(arguments: argparse.Namespace) -> int:
    from wixqa_rag import dataset

    return dataset.check(arguments.data_dir)


def _index_build(arguments: argparse.Namespace) -> int:
    from wixqa_rag import embedding, index

    # The embedder makes its client, and reads the provider key, at its first request.
    return index.build(arguments.index, arguments.data_dir, embedding.Embedder())


def _index_audit(arguments: argparse.Namespace) -> int:
    from wixqa_rag import audit

    return audit.command(
        arguments.index, arguments.data_dir, arguments.json, arguments.set, arguments.sets_dir
    )


def _wrong_index_audit(arguments: argparse.Namespace) -> str | None:
    if arguments.sets_dir is not None and arguments.set is None:
        return "--sets-dir is given without --set"
    return None


def _set_build(arguments: argparse.Namespace) -> int:
    from wixqa_rag import questionsets

    return questionsets.build(
        arguments.version,
        arguments.role,
        arguments.take,
        arguments.seed,
        arguments.complement_of,
        arguments.data_dir,
        arguments.sets_dir,
    )


def _wrong_set_build(arguments: argparse.Namespace) -> str | None:
    """contracts/cli.md, "`set build`": exactly one of the two rules is given, and no part
    is given twice."""
    draws = arguments.take is not None or arguments.seed is not None
    if draws and arguments.complement_of is not None:
        return "--complement-of is given together with --take or --seed: a set has one rule"
    if arguments.complement_of is None:
        if not draws:
            return "no rule is given: --take with --seed, or --complement-of"
        if arguments.take is None:
            return "--seed is given without --take"
        if arguments.seed is None:
            return "--take is given without --seed"
        parts = [part for part, _ in arguments.take]
        for part in parts:
            if parts.count(part) > 1:
                return f"--take names the part {part} more than once"
    return None


def _set_check(arguments: argparse.Namespace) -> int:
    from wixqa_rag import questionsets

    return questionsets.check(arguments.version, arguments.data_dir, arguments.sets_dir)


def _run_report(arguments: argparse.Namespace) -> int:
    from wixqa_rag import runs

    return runs.report(
        arguments.run_id, arguments.per_question, arguments.runs_dir, arguments.sets_dir
    )


def _run_check(arguments: argparse.Namespace) -> int:
    from wixqa_rag import runs

    return runs.check(arguments.run_id, arguments.runs_dir, arguments.sets_dir)


def _run_compare(arguments: argparse.Namespace) -> int:
    from wixqa_rag import runs

    return runs.compare(arguments.first, arguments.second, arguments.runs_dir, arguments.sets_dir)


def _add_registry(command) -> None:
    """The options `--runs-dir` and `--sets-dir` of the commands of the group `run`."""
    command.add_argument(
        "--runs-dir",
        type=Path,
        metavar="DIR",
        help=f"the run registry; without it, {settings.RUNS_DIR.as_posix()}",
    )
    command.add_argument(
        "--sets-dir",
        type=Path,
        metavar="DIR",
        help=f"where question-set records are kept; without it, {settings.SETS_DIR.as_posix()}",
    )


def _take(text: str) -> tuple[str, int]:
    """The value of `--take`: `PART=N` with a whole number N of 1 or more."""
    found = re.fullmatch(r"([^=]+)=([0-9]+)", text)
    if found is None or int(found.group(2)) < 1:
        raise argparse.ArgumentTypeError(
            f"{text} is not of the form PART=N with a whole number N of 1 or more"
        )
    return found.group(1), int(found.group(2))


def _seed(text: str) -> int:
    """The value of `--seed`: a whole number, 0 or greater."""
    if re.fullmatch(r"[0-9]+", text) is None:
        raise argparse.ArgumentTypeError(f"{text} is not a whole number of 0 or more")
    return int(text)


def _add_directories(command) -> None:
    """The options `--data-dir` and `--sets-dir` of the commands of the group `set`."""
    command.add_argument(
        "--data-dir",
        type=Path,
        metavar="DIR",
        help="the data directory; without it, the default data directory",
    )
    command.add_argument(
        "--sets-dir",
        type=Path,
        metavar="DIR",
        help=f"where question-set records are kept; without it, {settings.SETS_DIR.as_posix()}",
    )


def build_parser() -> argparse.ArgumentParser:
    """The arguments of the command line. Wrong arguments end the program with exit code 2."""
    parser = argparse.ArgumentParser(
        prog="python -m wixqa_rag",
        description="The dataset, the index and the audit of the WixQA study.",
    )
    groups = parser.add_subparsers(dest="group", metavar="GROUP", required=True)

    dataset = _add_group(groups, "dataset", "The local copy of the dataset at the pinned revision.")
    _add_command(
        dataset,
        "fetch",
        "dataset fetch",
        _dataset_fetch,
        "Fetch the dataset at the pinned revision into the default data directory.",
    )
    check = _add_command(
        dataset,
        "check",
        "dataset check",
        _dataset_check,
        "Check a data directory against its manifest.",
    )
    check.add_argument(
        "--data-dir",
        type=Path,
        metavar="DIR",
        help="the data directory to check; without it, the default data directory",
    )

    index = _add_group(groups, "index", "The retrieval index built from the corpus.")
    build = _add_command(
        index,
        "build",
        "index build",
        _index_build,
        "Build an index from the corpus of a data directory.",
    )
    build.add_argument("--index", required=True, metavar="ID", help="the index identifier")
    build.add_argument(
        "--data-dir",
        type=Path,
        metavar="DIR",
        help="the data directory to build from; without it, the default data directory",
    )
    audit = _add_command(
        index,
        "audit",
        "audit",
        _index_audit,
        "Audit an index against a data directory.",
    )
    audit.add_argument("--index", required=True, metavar="ID", help="the index identifier")
    audit.add_argument(
        "--data-dir",
        type=Path,
        metavar="DIR",
        help="the data directory to audit against; without it, the default data directory",
    )
    audit.add_argument(
        "--json",
        type=Path,
        metavar="FILE",
        help="where the result is written; without it, data/audits/ID/<time>.json",
    )
    audit.add_argument("--set", metavar="V", help="the version of the question set to audit with")
    audit.add_argument(
        "--sets-dir",
        type=Path,
        metavar="DIR",
        help=f"where the record of --set is read; without it, {settings.SETS_DIR.as_posix()}",
    )
    audit.set_defaults(wrong=_wrong_index_audit)

    sets = _add_group(groups, "set", "The question sets: the golden set and the held-out sets.")
    build = _add_command(
        sets,
        "build",
        "set build",
        _set_build,
        "Produce a question set from a data directory by a rule and write its record.",
    )
    build.add_argument("--version", required=True, metavar="V", help="the version of the set")
    build.add_argument(
        "--role", required=True, choices=("golden", "held-out"), help="the role of the set"
    )
    build.add_argument(
        "--take",
        action="append",
        type=_take,
        metavar="PART=N",
        help="draw N questions from the question part PART; needs --seed",
    )
    build.add_argument("--seed", type=_seed, metavar="S", help="the seed of the draw")
    build.add_argument(
        "--complement-of",
        metavar="W",
        help="the set is the complement of the set W of the same sets directory",
    )
    _add_directories(build)
    build.set_defaults(wrong=_wrong_set_build)
    check = _add_command(
        sets,
        "check",
        "set check",
        _set_check,
        "Check the record of a question set against a data directory.",
    )
    check.add_argument("--version", required=True, metavar="V", help="the version of the set")
    _add_directories(check)

    # The parsed arguments hold the function of a command as `run`, so the option `--run`
    # is kept as `run_id`.
    runs = _add_group(groups, "run", "The records of the run registry.")
    report = _add_command(
        runs, "report", "run report", _run_report, "Print the numbers of one run."
    )
    report.add_argument("--run", dest="run_id", required=True, metavar="ID", help="the run")
    report.add_argument(
        "--per-question", action="store_true", help="also print one line for every question"
    )
    _add_registry(report)
    check_run = _add_command(
        runs,
        "check",
        "run check",
        _run_check,
        "Check one run record, or every run of the registry.",
    )
    check_run.add_argument(
        "--run", dest="run_id", metavar="ID", help="the run; without it, every run of the registry"
    )
    _add_registry(check_run)
    compare = _add_command(
        runs, "compare", "run compare", _run_compare, "Compare two runs on one question set."
    )
    compare.add_argument("--first", required=True, metavar="ID", help="the first run")
    compare.add_argument("--second", required=True, metavar="ID", help="the second run")
    _add_registry(compare)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Read the command line, carry out the command and return its exit code."""
    parser = build_parser()
    arguments, unrecognized = parser.parse_known_args(argv)
    if unrecognized:
        message = "unrecognized arguments: " + " ".join(unrecognized)
        name = getattr(arguments, "verdict_name", None)
        if name is None:
            parser.error(message)
        return _wrong_arguments(name, message)
    # A command may look at its arguments together: `wrong` gives the reason, or None.
    wrong = getattr(arguments, "wrong", None)
    message = None if wrong is None else wrong(arguments)
    if message is not None:
        return _wrong_arguments(arguments.verdict_name, message)
    return carry_out(arguments.verdict_name, lambda: arguments.run(arguments))
