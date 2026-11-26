"""The places of the files and the two settings of the commands.

The current directory stands for the repository root (contracts/cli.md, "Where a command is
typed"), so every place is a path relative to it. Nothing is kept between calls: each function
reads the environment or `dataset.json` when it is called.

The functions that derive a place from an index identifier expect a valid identifier
(data-model.md, "Index"); a command checks the identifier before it asks for a place.
"""

import os
from datetime import UTC, datetime
from pathlib import Path

# The pinned revision of the dataset (data-model.md, "Pinned revision").
DATASET_JSON = Path("dataset.json")

# The settings (contracts/cli.md, "Settings"): read from the environment and from nowhere else.
SETTING_NAMES = ("DATABASE_URL", "OPENAI_API_KEY")


class MissingSetting(Exception):
    """A setting is not set, or is set to an empty text. The message names the variable."""

    def __init__(self, name: str) -> None:
        super().__init__(f"the environment variable {name} is not set")
        self.name = name


def _setting(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise MissingSetting(name)
    return value


def database_url() -> str:
    """The connection string of the vector store."""
    return _setting("DATABASE_URL")


def openai_api_key() -> str:
    """The key of the embedding provider."""
    return _setting("OPENAI_API_KEY")


def hide_values(text: str) -> str:
    """The text with every value of a setting replaced by the name of the setting.

    A message never shows the value of a setting, also when the error of a library carries it.
    """
    values = [(os.environ.get(name, ""), name) for name in SETTING_NAMES]
    for value, name in sorted(values, key=lambda pair: len(pair[0]), reverse=True):
        if value:
            text = text.replace(value, f"<{name}>")
    return text


def data_dir_of_revision(revision: str) -> Path:
    """`data/wixqa/<revision>`: where the dataset fetched at a revision is kept."""
    return Path("data", "wixqa", revision)


def default_data_dir() -> Path:
    """`data/wixqa/<revision>`, with the revision that `dataset.json` records.

    `dataset.json` is read, and its rules are checked, by `dataset.read_pinned`.
    """
    from wixqa_rag import dataset

    return data_dir_of_revision(dataset.read_pinned().revision)


def build_record_path(index: str, data_dir: Path | None = None) -> Path:
    """The file of the build record of an index (data-model.md, "Build record").

    A build without `--data-dir` (`data_dir` is None) is a build from the pinned dataset: its
    record is kept under `evals/`, in version control. Every build with `--data-dir` records
    under `data/`, whichever directory it names.
    """
    folder = Path("evals") if data_dir is None else Path("data")
    return folder / "indexes" / index / "build.json"


def audit_result_path(index: str, audited_at: datetime) -> Path:
    """The file of an audit result written without `--json` (data-model.md, "Audit result").

    The name is the time of the audit in UTC, in the form `20261124T101500Z`.
    """
    if audited_at.tzinfo is None:
        raise ValueError("the time of the audit has no time zone")
    time = audited_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return Path("data", "audits", index, f"{time}.json")
