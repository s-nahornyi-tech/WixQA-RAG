"""Acceptance test of check AC-020 (specs/002-evaluation-harness/spec.md, "Acceptance Checks").

    python -m wixqa_rag run check && git status --porcelain evals/runs/

→ exit code 0; the output contains `failed runs: 0` and `run check: passed`, and
`git status` prints nothing: no file under `evals/runs/` is added or changed.

Covers US3, FR-024, FR-026, FR-030 and SC-007.

The command checks the run registry of the study itself, `evals/runs/` of the checkout, with
the question sets of `evals/golden/`. Today the registry holds no run, and the check passes
with zero runs; when runs are recorded, each of them has to pass. The command writes
nothing: the test also compares every file under `evals/runs/` before and after. It needs
neither the store, the provider nor the dataset host and carries no marker.
"""

COMMAND = "python -m wixqa_rag run check && git status --porcelain evals/runs/"


def files_below(directory) -> dict[str, bytes]:
    return {
        file.relative_to(directory).as_posix(): file.read_bytes()
        for file in sorted(directory.rglob("*"))
        if file.is_file()
    }


def test_ac_020_the_registry_of_the_study_passes_its_check_and_is_left_untouched(
    run_command, repository_root
):
    """AC-020: every run of `evals/runs/` passes its check, and the check adds or changes no
    file there."""
    before = files_below(repository_root / "evals" / "runs")

    result = run_command(COMMAND)

    assert result.exit_code == 0, (
        f"AC-020: exit code 0 expected, got {result.exit_code}. Standard error:\n{result.stderr}"
    )
    for line in ("failed runs: 0", "run check: passed"):
        assert line in result.lines, f"AC-020: the output contains the line `{line}`"
    after_the_verdict = result.lines[result.lines.index("run check: passed") + 1 :]
    assert after_the_verdict == [], (
        "AC-020: `git status --porcelain evals/runs/` prints nothing; "
        f"it printed {after_the_verdict}"
    )
    assert files_below(repository_root / "evals" / "runs") == before, (
        "AC-020: no file under `evals/runs/` is added or changed"
    )
