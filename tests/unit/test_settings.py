"""Settings and default places (tasks T016): `src/wixqa_rag/settings.py`.

Covers:

- contracts/cli.md, "Settings", and spec.md, FR-017 and the edge case of a missing credential:
  the two settings are read from the environment and from nowhere else; a missing setting is
  reported by its variable name; the value of a setting never appears in a message;
- data-model.md, "Data directory", "Build record" and "Audit result" (research.md, section
  15): the default places are derived from `dataset.json` and the index identifier.

No command exists yet that reads a setting or writes a record (tasks.md, T019), so these
tests call `settings.py` directly. They need these names from it and nothing else:

    class MissingSetting(Exception)        # its text names the variable that is not set
    database_url() -> str                  # the value of DATABASE_URL
    openai_api_key() -> str                # the value of OPENAI_API_KEY
    default_data_dir() -> Path             # data/wixqa/<revision>
    build_record_path(index: str, data_dir: Path | None = None) -> Path
    audit_result_path(index: str, audited_at: datetime) -> Path

Every function reads the environment or the current directory at the time of the call. The
current directory stands for the repository root (contracts/cli.md, "Where a command is
typed"). A place may be returned as an absolute path or as a path relative to the current
directory. The tests also use `carry_out` of `src/wixqa_rag/cli.py`, described in
tests/unit/test_cli_frame.py.

The values of the settings below are invented for these tests; none of them is a credential.
All documents named here are in specs/001-corpus-and-audit/.

Added for spec 2 (specs/002-evaluation-harness/tasks.md, T010), at the end of this file: the
two default directories of contracts/harness.md, "`wixqa_rag.settings`: additions":

    SETS_DIR: Path                         # evals/golden
    RUNS_DIR: Path                         # evals/runs
"""

import importlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

# Invented values, long enough to be told apart from every other text in a message.
INVENTED_VALUES = {
    "DATABASE_URL": "postgresql://store-user@store.invalid:5432/value-that-is-never-printed",
    "OPENAI_API_KEY": "invented-key-value-that-is-never-printed-7f3a91",
}
READERS = {"DATABASE_URL": "database_url", "OPENAI_API_KEY": "openai_api_key"}
SETTING_NAMES = tuple(READERS)

# A revision that differs from the pinned one, so that a place can only come from the
# `dataset.json` of the current directory.
OTHER_REVISION = "0123456789abcdef0123456789abcdef01234567"


def load_settings():
    """Import the module; it fails while `src/wixqa_rag/settings.py` does not exist (plan.md)."""
    return importlib.import_module("wixqa_rag.settings")


def load_cli():
    """Import the frame; it fails while `src/wixqa_rag/cli.py` does not exist (plan.md)."""
    return importlib.import_module("wixqa_rag.cli")


def other_setting(name: str) -> str:
    return next(other for other in SETTING_NAMES if other != name)


def place(path: Path) -> Path:
    """A returned place as an absolute path, whether it was returned absolute or relative."""
    return (Path.cwd() / path).resolve()


@pytest.fixture
def root_with_other_revision(temporary_root: Path, monkeypatch) -> Path:
    """A temporary repository root whose `dataset.json` pins another revision; the current
    directory of the test."""
    file = temporary_root / "dataset.json"
    pinned = json.loads(file.read_text(encoding="utf-8"))
    assert pinned["revision"] != OTHER_REVISION
    pinned["revision"] = OTHER_REVISION
    file.write_text(json.dumps(pinned, indent=2) + "\n", encoding="utf-8")
    monkeypatch.chdir(temporary_root)
    return temporary_root.resolve()


# --- The two settings are read from the environment (contracts/cli.md, "Settings") -----------


@pytest.mark.parametrize("name", SETTING_NAMES)
def test_a_setting_is_read_from_the_environment(name, monkeypatch):
    """contracts/cli.md, "Settings": `DATABASE_URL` and `OPENAI_API_KEY` are read from the
    environment, unchanged."""
    settings = load_settings()
    monkeypatch.setenv(name, INVENTED_VALUES[name])

    assert getattr(settings, READERS[name])() == INVENTED_VALUES[name]


@pytest.mark.parametrize("name", SETTING_NAMES)
def test_a_setting_is_read_at_the_time_of_the_call(name, monkeypatch):
    """contracts/cli.md, "Settings": the environment is the only source, so a value that
    changes or disappears there changes or disappears for the next call."""
    settings = load_settings()
    read = getattr(settings, READERS[name])

    monkeypatch.setenv(name, INVENTED_VALUES[name])
    assert read() == INVENTED_VALUES[name]
    monkeypatch.setenv(name, INVENTED_VALUES[name] + "-changed")
    assert read() == INVENTED_VALUES[name] + "-changed"
    monkeypatch.delenv(name)
    with pytest.raises(settings.MissingSetting):
        read()


@pytest.mark.parametrize("name", SETTING_NAMES)
def test_a_setting_is_read_from_nowhere_else(name, tmp_path, monkeypatch):
    """contracts/cli.md, "Settings", and FR-017: "read from the environment and from nowhere
    else". A `.env` file in the current directory does not supply a setting."""
    settings = load_settings()
    (tmp_path / ".env").write_text(f"{name}={INVENTED_VALUES[name]}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(name, raising=False)

    with pytest.raises(settings.MissingSetting):
        getattr(settings, READERS[name])()


# --- A missing setting is reported by its variable name ---------------------------------------


@pytest.mark.parametrize("name", SETTING_NAMES)
def test_a_missing_setting_is_reported_by_its_variable_name(name, monkeypatch):
    """contracts/cli.md, "Settings": a command names a setting by its variable name. spec.md,
    "Edge Cases": with a missing credential the command names the missing setting."""
    settings = load_settings()
    monkeypatch.delenv(name, raising=False)

    with pytest.raises(settings.MissingSetting) as caught:
        getattr(settings, READERS[name])()

    assert name in str(caught.value)
    assert other_setting(name) not in str(caught.value), "only the missing setting is named"


@pytest.mark.parametrize("name", SETTING_NAMES)
def test_an_empty_setting_is_a_missing_setting(name, monkeypatch):
    """spec.md, "Edge Cases": a missing credential. A variable that is set to an empty text
    carries no credential; a CI job passes a secret that does not exist in exactly this form
    (.github/workflows/acceptance.yml). It is reported like a variable that is not set."""
    settings = load_settings()
    monkeypatch.setenv(name, "")

    with pytest.raises(settings.MissingSetting) as caught:
        getattr(settings, READERS[name])()

    assert name in str(caught.value)


@pytest.mark.parametrize("name", SETTING_NAMES)
def test_a_missing_setting_reaches_the_output_as_a_reason_that_names_it(
    name, temporary_root, monkeypatch, capfd
):
    """contracts/cli.md, "`index build`" and "`index audit`": a missing setting ends as not
    carried out, with exit code 2 and a `reason:` line that names the variable (AC-014 reads
    that line for `OPENAI_API_KEY`)."""
    settings = load_settings()
    cli = load_cli()
    monkeypatch.chdir(temporary_root)
    monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(other_setting(name), INVENTED_VALUES[other_setting(name)])

    def action() -> int:
        getattr(settings, READERS[name])()
        print("index build: done")
        return 0

    exit_code = cli.carry_out("index build", action)

    lines = capfd.readouterr().out.splitlines()
    assert exit_code == 2
    assert lines[-1] == "index build: not carried out"
    reasons = [line for line in lines[:-1] if line.startswith("reason: ")]
    assert any(name in line for line in reasons), (
        'contracts/cli.md, "Output": the `reason:` line names the setting concerned'
    )


# --- The value of a setting never appears in a message ----------------------------------------


@pytest.mark.parametrize("name", SETTING_NAMES)
def test_the_report_of_a_missing_setting_holds_no_value_of_a_setting(name, monkeypatch):
    """contracts/cli.md, "Settings": a command never prints the value of a setting. The
    report of a missing setting does not hold the value of the setting that is present."""
    settings = load_settings()
    present = other_setting(name)
    monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(present, INVENTED_VALUES[present])

    with pytest.raises(settings.MissingSetting) as caught:
        getattr(settings, READERS[name])()

    for text in (str(caught.value), repr(caught.value)):
        assert INVENTED_VALUES[present] not in text


@pytest.mark.parametrize("name", SETTING_NAMES)
def test_the_value_of_a_setting_in_an_unexpected_error_is_not_printed(
    name, temporary_root, monkeypatch, capfd
):
    """contracts/cli.md, "Settings", and FR-017: a command never prints the value of a
    setting, "on either output stream". An error of a library can carry the value it was
    given, for example a connection string; the report of that error does not print it."""
    cli = load_cli()
    value = INVENTED_VALUES[name]
    monkeypatch.chdir(temporary_root)
    monkeypatch.setenv(name, value)

    def action() -> int:
        raise RuntimeError(f"the stand-in library refused {value!r}")

    exit_code = cli.carry_out("index build", action)

    captured = capfd.readouterr()
    assert exit_code == 2
    assert captured.out.splitlines()[-1] == "index build: not carried out"
    assert value not in captured.out, f"the value of {name} was printed to standard output"
    assert value not in captured.err, f"the value of {name} was printed to standard error"


# --- The default places (data-model.md; research.md, section 15) -----------------------------


def test_the_default_data_directory_is_derived_from_dataset_json(root_with_other_revision):
    """data-model.md, "Data directory": the default data directory is `data/wixqa/<revision>/`,
    with the revision that `dataset.json` in the current directory records."""
    settings = load_settings()

    assert place(settings.default_data_dir()) == (
        root_with_other_revision / "data" / "wixqa" / OTHER_REVISION
    )


def test_the_default_data_directory_follows_the_pinned_revision(temporary_root, monkeypatch):
    """data-model.md, "Pinned revision": every command reads the revision from `dataset.json`
    and from nowhere else. With the repository's own file the place is that of
    contracts/cli.md, "`dataset fetch`"."""
    settings = load_settings()
    monkeypatch.chdir(temporary_root)
    pinned = json.loads((temporary_root / "dataset.json").read_text(encoding="utf-8"))

    assert place(settings.default_data_dir()) == (
        temporary_root.resolve() / "data" / "wixqa" / pinned["revision"]
    )


@pytest.mark.parametrize("index", ["wixqa-001", "example"])
def test_the_build_record_of_the_pinned_dataset_is_kept_under_evals(
    index, root_with_other_revision
):
    """data-model.md, "Build record": for a build from the pinned dataset, which is a build
    without `--data-dir`, the file is `evals/indexes/<index>/build.json`."""
    settings = load_settings()

    assert place(settings.build_record_path(index)) == (
        root_with_other_revision / "evals" / "indexes" / index / "build.json"
    )


@pytest.mark.parametrize("index", ["example", "needs-key"])
def test_the_build_record_of_other_data_is_kept_under_data(index, root_with_other_revision):
    """data-model.md, "Build record": for a build with `--data-dir` the file is
    `data/indexes/<index>/build.json`, outside version control."""
    settings = load_settings()

    assert place(settings.build_record_path(index, Path("tests/data/example"))) == (
        root_with_other_revision / "data" / "indexes" / index / "build.json"
    )


def test_a_build_with_data_dir_never_records_under_evals(root_with_other_revision):
    """contracts/cli.md, "`index build`": "With `--data-dir` the build record goes to
    `data/indexes/ID/build.json`." A build that names the default data directory with
    `--data-dir` is a build with `--data-dir`, so its record goes under `data/` as well."""
    settings = load_settings()

    assert place(settings.build_record_path("wixqa-001", settings.default_data_dir())) == (
        root_with_other_revision / "data" / "indexes" / "wixqa-001" / "build.json"
    )


def test_the_audit_result_without_json_is_kept_under_data_audits(root_with_other_revision):
    """data-model.md, "Audit result": without `--json` the result goes to
    `data/audits/<index>/<time>.json`. contracts/records.md, "Audit result": `<time>` has the
    form `20261124T101500Z`, the time of the audit in UTC."""
    settings = load_settings()
    audited_at = datetime(2026, 11, 24, 10, 15, 0, tzinfo=UTC)

    assert place(settings.audit_result_path("example", audited_at)) == (
        root_with_other_revision / "data" / "audits" / "example" / "20261124T101500Z.json"
    )


def test_the_audit_results_of_two_indexes_are_kept_apart(root_with_other_revision):
    """data-model.md, "Audit result": the place is derived from the index identifier."""
    settings = load_settings()
    audited_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

    assert place(settings.audit_result_path("wixqa-001", audited_at)) == (
        root_with_other_revision / "data" / "audits" / "wixqa-001" / "20260102T030405Z.json"
    )


# --- The default directories of spec 2 (specs/002-evaluation-harness) -------------------------
#
# contracts/harness.md, "`wixqa_rag.settings`: additions"; contracts/cli.md, "Directories";
# data-model.md, "Question set" and "Run record".


def test_the_default_sets_directory_is_evals_golden():
    """contracts/harness.md: `SETS_DIR` is `Path("evals", "golden")`, the default sets
    directory. contracts/cli.md, "Directories": the default of `--sets-dir` is
    `evals/golden`."""
    settings = load_settings()

    assert isinstance(settings.SETS_DIR, Path)
    assert settings.SETS_DIR == Path("evals", "golden")


def test_the_default_runs_directory_is_evals_runs():
    """contracts/harness.md: `RUNS_DIR` is `Path("evals", "runs")`, the default runs
    directory. contracts/cli.md, "Directories": the default of `--runs-dir` is
    `evals/runs`."""
    settings = load_settings()

    assert isinstance(settings.RUNS_DIR, Path)
    assert settings.RUNS_DIR == Path("evals", "runs")


@pytest.mark.parametrize(
    ("name", "parts"), [("SETS_DIR", ("evals", "golden")), ("RUNS_DIR", ("evals", "runs"))]
)
def test_a_default_directory_of_spec_2_is_a_place_below_the_current_directory(
    name, parts, root_with_other_revision
):
    """contracts/cli.md, "General rules": a command is typed at the repository root, and the
    current directory stands for it. The two default directories are relative paths, so they
    lie below the directory where the command is typed, whatever `dataset.json` pins."""
    settings = load_settings()
    directory = getattr(settings, name)

    assert not directory.is_absolute()
    assert place(directory) == root_with_other_revision.joinpath(*parts)


def test_the_two_default_directories_of_spec_2_are_kept_apart():
    """data-model.md, "Question set" and "Run record": question sets are stored in
    `evals/golden/` and run records in `evals/runs/`; neither lies inside the other."""
    settings = load_settings()

    assert settings.SETS_DIR != settings.RUNS_DIR
    assert settings.SETS_DIR not in settings.RUNS_DIR.parents
    assert settings.RUNS_DIR not in settings.SETS_DIR.parents
