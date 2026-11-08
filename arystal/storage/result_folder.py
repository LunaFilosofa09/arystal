"""Creates the folder of one run: results/<date>_<time>_<short id>/ with its sub-folders."""

import uuid
from datetime import datetime
from pathlib import Path

DEFAULT_RESULTS_ROOT = Path(__file__).resolve().parent.parent.parent / "results"
SHORT_ID_LENGTH = 6
SUBFOLDERS = ("snapshots", "plots")


def create_short_id() -> str:
    """Return a short random id (hexadecimal) that keeps two runs started in the same second apart."""
    return uuid.uuid4().hex[:SHORT_ID_LENGTH]


def create_timestamped_name(suffix: str = "") -> str:
    """Return a folder name made of the date, the time and a short random id (plus an optional suffix)."""
    return f"{datetime.now():%Y-%m-%d_%H%M%S}_{create_short_id()}{suffix}"


def create_result_folder(root: Path = DEFAULT_RESULTS_ROOT, name: str | None = None) -> Path:
    """Create and return a new folder for a run, with its snapshots/ and plots/ sub-folders.

    The folder is called `name` if given (used for the replicas of an ensemble), else date_time_id.
    """
    name = name or create_timestamped_name()
    folder = Path(root) / name
    for sub in SUBFOLDERS:
        (folder / sub).mkdir(parents=True)
    return folder


def create_ensemble_folder(root: Path = DEFAULT_RESULTS_ROOT) -> Path:
    """Create and return the folder of an ensemble: results/<date>_<time>_<id>_ensemble/ (the replicas go inside it)."""
    folder = Path(root) / create_timestamped_name("_ensemble")
    folder.mkdir(parents=True)
    return folder
