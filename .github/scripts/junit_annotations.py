"""Publish one pytest JUnit report as GitHub Actions annotations.

A reader of a workflow run, a person or an agent, sees its result through annotations, without
opening a log. This script reads the JUnit report that pytest wrote and prints workflow commands:

- one notice with the number of tests that passed, failed, ended in an error or were skipped;
- when a test failed: one error that lists every failed test, then one error for each failed
  test with the reason. GitHub shows only the first ten errors of a step, which is why the
  complete list comes first;
- with --verdicts: one notice with the verdict lines that the commands under test printed, for
  example "audit: passed". They are read from the output that pytest captured for each test,
  so the report has to be written with "-o junit_logging=all", and a test has to pass the
  output of its command on to its own standard output. When a "set build" ended as done, a
  second notice gives its line "question set: <version>", which ends with "(already written)"
  when the record was there before and had the same bytes. A last notice states how long each
  test took, which for the test that builds an index is the time of the build.

The same facts are added to the summary page of the job.

The script uses the Python standard library only and is started at the repository root:

    python .github/scripts/junit_annotations.py [--name NAME] [--verdicts] REPORT

It ends with exit code 0 when the report was read, whatever the tests did: the step that ran
pytest already carries their result. It ends with exit code 1 when the report is missing or
cannot be read.
"""

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

# The most characters of a failure text that go into one annotation; the end of the text is kept,
# because pytest prints the reason and the place of a failure last.
DETAIL_LIMIT = 3000
SUMMARY_LIMIT = 500
LIST_LIMIT = 20000

# The verdict lines of specs/001-corpus-and-audit/contracts/cli.md and of
# specs/002-evaluation-harness/contracts/cli.md, as whole lines.
VERDICT_LINE = re.compile(
    r"(?:dataset fetch|dataset check|index build|audit"
    r"|set build|set check|run report|run check|run compare): "
    r"(?:done|passed|failed|refused|not carried out)"
)
# The first line of the report of "set build" (spec 2's contracts/cli.md, "set build"). It ends
# with "(already written)" when the record existed with the same bytes.
BUILT_SET_LINE = re.compile(r"question set: \S+(?: \(already written\))?")
BUILD_DONE = "set build: done"
BUILT_SETS_HEADING = (
    'Question sets that "set build" reported as done; "(already written)" marks a record that '
    "was there before with the same bytes:"
)
# A place in a pytest failure text, for example "tests/unit/test_cli.py:12: AssertionError".
LOCATION_LINE = re.compile(r"^(?P<path>[^\s:]+\.py):(?P<line>\d+): ", re.MULTILINE)


@dataclass
class Case:
    """One test of the report."""

    test_id: str
    file: str | None
    status: str  # "passed", "failed", "error" or "skipped"
    reason: str = ""
    line: int | None = None
    verdicts: list[str] = field(default_factory=list)
    built_sets: list[str] = field(default_factory=list)
    seconds: float = 0.0


def escape_data(text: str) -> str:
    """Escape the message of a workflow command."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def escape_property(text: str) -> str:
    """Escape the value of a property of a workflow command."""
    return escape_data(text).replace(":", "%3A").replace(",", "%2C")


def emit(level: str, message: str, **properties: str | int | None) -> None:
    """Print one workflow command: an annotation of the given level."""
    listed = ",".join(
        f"{key}={escape_property(str(value))}"
        for key, value in properties.items()
        if value is not None
    )
    head = f"::{level} {listed}" if listed else f"::{level}"
    print(f"{head}::{escape_data(message)}", flush=True)


def keep_start(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit].rstrip() + " ..."


def keep_end(text: str, limit: int) -> str:
    """Keep the last lines of a text, cut at a line break where one exists."""
    if len(text) <= limit:
        return text
    kept = text[-limit:]
    _, line_break, rest = kept.partition("\n")
    return "...\n" + (rest if line_break and rest else kept)


def module_file(parts: list[str], root: Path) -> tuple[str | None, list[str]]:
    """Find the test file that a dotted name starts with.

    pytest writes "tests.unit.test_cli.TestFrame" for a class in tests/unit/test_cli.py. The
    longest start of the name that is a Python file under the root is the test file; what
    follows it is returned as the rest.
    """
    if not parts or any(not part or "/" in part or part.startswith(".") for part in parts):
        return None, parts
    for end in range(len(parts), 0, -1):
        relative = "/".join(parts[:end]) + ".py"
        if (root / relative).is_file():
            return relative, parts[end:]
    return None, parts


def identify(classname: str, name: str, root: Path) -> tuple[str, str | None]:
    """Return the identifier of a test in the form pytest prints, and its file."""
    file, rest = module_file(classname.split(".") if classname else [], root)
    if file is not None:
        return "::".join([file, *rest, name]), file
    if not classname:
        # A file that could not be collected is reported with its dotted name only.
        file, rest = module_file(name.split("."), root)
        if file is not None and not rest:
            return file, file
    return (f"{classname}::{name}" if classname else name), None


def line_of_failure(text: str, file: str | None) -> int | None:
    """Return the last line of the test file that the failure text names."""
    if file is None:
        return None
    lines = [int(match["line"]) for match in LOCATION_LINE.finditer(text) if match["path"] == file]
    return lines[-1] if lines else None


def seconds_of(testcase: ET.Element) -> float:
    try:
        return float(testcase.get("time") or 0)
    except ValueError:
        return 0.0


def duration(seconds: float) -> str:
    whole = round(seconds)
    return f"{whole // 60} min {whole % 60} s"


def read_case(testcase: ET.Element, root: Path) -> Case:
    test_id, file = identify(testcase.get("classname") or "", testcase.get("name") or "", root)
    problems = [child for child in testcase if child.tag in ("failure", "error")]
    if any(child.tag == "failure" for child in problems):
        status = "failed"
    elif problems:
        status = "error"
    elif testcase.find("skipped") is not None:
        status = "skipped"
    else:
        status = "passed"

    reasons = []
    line = None
    for child in problems:
        summary = keep_start((child.get("message") or "").strip(), SUMMARY_LIMIT)
        details = (child.text or "").strip()
        reasons.append("\n\n".join(part for part in (summary, details) if part))
        line = line_of_failure(details, file) or line

    # A command prints its verdict line last, so the line "question set: ..." that belongs to a
    # "set build: done" is the last one printed since the verdict line before it. "set check"
    # and "run check" print such a line too; theirs is dropped at their own verdict line.
    verdicts = []
    built_sets = []
    for child in testcase:
        if child.tag in ("system-out", "system-err"):
            named_set = None
            for captured in (child.text or "").splitlines():
                printed = captured.strip()
                if VERDICT_LINE.fullmatch(printed):
                    verdicts.append(printed)
                    if printed == BUILD_DONE and named_set is not None:
                        built_sets.append(named_set)
                    named_set = None
                elif BUILT_SET_LINE.fullmatch(printed):
                    named_set = printed

    return Case(
        test_id=test_id,
        file=file,
        status=status,
        reason=keep_end("\n\n".join(reasons), DETAIL_LIMIT),
        line=line,
        verdicts=verdicts,
        built_sets=built_sets,
        seconds=seconds_of(testcase),
    )


def listing(lines: list[str], limit: int) -> str:
    """Join lines; when they exceed the limit, say how many were left out."""
    kept: list[str] = []
    used = 0
    for line in lines:
        if used + len(line) + 1 > limit:
            kept.append(f"... and {len(lines) - len(kept)} more")
            break
        kept.append(line)
        used += len(line) + 1
    return "\n".join(kept)


def write_job_summary(
    name: str, counts: str, failed: list[Case], verdicts: list[str], built_sets: list[str]
) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    lines = [f"### {name}", "", counts, ""]
    if failed:
        lines += ["Failed:", ""]
        lines += [f"- `{case.test_id}` ({case.status})" for case in failed]
        lines.append("")
    if verdicts:
        lines += ["Verdict lines of the commands:", ""]
        lines += [f"- {verdict}" for verdict in verdicts]
        lines.append("")
    if built_sets:
        lines += [BUILT_SETS_HEADING, ""]
        lines += [f"- {built_set}" for built_set in built_sets]
        lines.append("")
    with open(path, "a", encoding="utf-8") as summary:
        summary.write("\n".join(lines) + "\n")


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Publish a pytest JUnit report as annotations.")
    parser.add_argument("report", type=Path, help="the JUnit report that pytest wrote")
    parser.add_argument("--name", default="tests", help="what the report covers; used as a title")
    parser.add_argument(
        "--verdicts",
        action="store_true",
        help="also publish the verdict lines found in the captured output of the tests",
    )
    options = parser.parse_args(arguments)
    name: str = options.name

    if not options.report.is_file():
        emit(
            "error",
            "pytest left no report: it stopped before it ran a test. "
            "The step that ran pytest shows why.",
            title=name,
        )
        return 1
    try:
        tree = ET.parse(options.report)
    except ET.ParseError as problem:
        emit("error", f"The report of pytest cannot be read: {problem}", title=name)
        return 1

    root = Path.cwd()
    cases = [read_case(testcase, root) for testcase in tree.getroot().iter("testcase")]
    number = {
        status: sum(1 for case in cases if case.status == status)
        for status in ("passed", "failed", "error", "skipped")
    }
    counts = (
        f"{len(cases)} {'test' if len(cases) == 1 else 'tests'}: "
        f"{number['passed']} passed, {number['failed']} failed, "
        f"{number['error']} ended in an error, {number['skipped']} skipped"
    )
    emit("notice", counts, title=name)

    failed = [case for case in cases if case.status in ("failed", "error")]
    if failed:
        emit(
            "error",
            listing([f"{case.test_id} ({case.status})" for case in failed], LIST_LIMIT),
            title=f"{name}: {len(failed)} not passed",
        )
        for case in failed:
            emit(
                "error",
                case.reason or "pytest recorded no reason.",
                file=case.file,
                line=case.line,
                title=f"{case.test_id} ({case.status})",
            )

    verdicts: list[str] = []
    built_sets: list[str] = []
    if options.verdicts:
        verdicts = [
            f"{verdict}  [{case.test_id}, {case.status}]"
            for case in cases
            for verdict in case.verdicts
        ]
        if verdicts:
            emit("notice", listing(verdicts, LIST_LIMIT), title=f"{name}: verdict lines")
        else:
            emit(
                "notice",
                "No verdict line of a command was found in the output captured for these tests.",
                title=f"{name}: verdict lines",
            )

        built_sets = [
            f"{built_set}  [{case.test_id}, {case.status}]"
            for case in cases
            for built_set in case.built_sets
        ]
        if built_sets:
            emit(
                "notice",
                listing([BUILT_SETS_HEADING, *built_sets], LIST_LIMIT),
                title=f"{name}: question sets built",
            )

        emit(
            "notice",
            listing(
                [f"{duration(case.seconds)}  [{case.test_id}, {case.status}]" for case in cases],
                LIST_LIMIT,
            )
            or "The report holds no test.",
            title=f"{name}: how long each test took",
        )

    write_job_summary(name, counts, failed, verdicts, built_sets)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
