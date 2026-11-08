"""Reading past results from the results folder, safely (the server only serves files inside it)."""

import io
import re
from pathlib import Path

from matplotlib.image import imsave

from arystal.server.frames import sanitize_row
from arystal.storage.metrics_io import read_metrics_csv
from arystal.storage.rendering import render_crystal_rgb, render_plain_crystal_rgb
from arystal.storage.serialization import read_json
from arystal.storage.snapshots import list_snapshots, load_snapshot

# A result name is letters, digits, dots, underscores and hyphens only: no slashes, so it cannot leave the results folder.
RESULT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]+$")

# Only these kinds of files can be downloaded.
ALLOWED_FILE_SUFFIXES = (".png", ".json", ".csv")

RUN = "run"
ENSEMBLE = "ensemble"


def resolve_result_folder(results_root: Path, name: str) -> Path | None:
    """Return the folder of a result, or None if the name is invalid or the folder does not exist."""
    if not RESULT_NAME_PATTERN.match(name) or name in (".", ".."):
        return None
    folder = (Path(results_root) / name).resolve()
    if folder.parent != Path(results_root).resolve() or not folder.is_dir():
        return None
    return folder


def classify_result(folder: Path) -> str | None:
    """Return "run", "ensemble" or None for a folder of the results directory."""
    if (folder / "ensemble_summary.json").exists():
        return ENSEMBLE
    if (folder / "summary.json").exists():
        return RUN
    return None


def describe_run(folder: Path) -> dict:
    """Return the headline description of a saved run."""
    summary = read_json(folder / "summary.json")
    config = read_json(folder / "params.json")["config"]
    headline = summary["headline_results"]
    return {
        "name": folder.name, "kind": RUN, "seed": config["seed"], "temperature_celsius": config["temperature_celsius"],
        "mode": config["mode"], "final_model_time": headline["final_model_time"], "crystal_area_mm2": headline["crystal_area_mm2"],
        "aspect_ratio": headline["aspect_ratio"], "wall_clock_seconds": summary["compute_cost"]["wall_clock_seconds"],
    }


def describe_ensemble(folder: Path) -> dict:
    """Return the headline description of a saved ensemble."""
    summary = read_json(folder / "ensemble_summary.json")
    area = summary["statistics_of_final_metrics"]["crystal_area_mm2"]
    return {
        "name": folder.name, "kind": ENSEMBLE, "replicas": summary["ensemble"]["number_of_replicas"], "base_seed": summary["ensemble"]["base_seed"],
        "crystal_area_mm2_mean": area["mean"], "crystal_area_mm2_std": area["std"],
        "wall_clock_seconds": summary["compute_cost"]["ensemble_wall_clock_seconds"],
    }


def list_results(results_root: Path) -> list[dict]:
    """Return a description of every saved run and ensemble, newest first."""
    descriptions = []
    root = Path(results_root)
    for folder in sorted(root.iterdir(), reverse=True) if root.is_dir() else []:
        kind = classify_result(folder) if folder.is_dir() else None
        if kind == RUN:
            descriptions.append(describe_run(folder))
        elif kind == ENSEMBLE:
            descriptions.append(describe_ensemble(folder))
    return descriptions


def load_result(folder: Path) -> dict:
    """Return the summary, parameters and timeline (or the ensemble summary) of a saved result."""
    if classify_result(folder) == ENSEMBLE:
        return {"kind": ENSEMBLE, "ensemble_summary": read_json(folder / "ensemble_summary.json")}
    return {
        "kind": RUN, "summary": read_json(folder / "summary.json"),
        "timeline": read_json(folder / "timeline.json"), "params": read_json(folder / "params.json")["config"],
    }


def load_metrics(folder: Path) -> list[dict]:
    """Return the metrics rows of a saved run."""
    return [sanitize_row(row) for row in read_metrics_csv(folder / "metrics.csv")]


def resolve_result_file(folder: Path, relative: str) -> Path | None:
    """Return a file of a result folder if it is allowed to be served (inside the folder, right kind), else None."""
    path = (folder / relative).resolve()
    if folder not in path.parents or not path.is_file() or path.suffix not in ALLOWED_FILE_SUFFIXES:
        return None
    return path


def list_snapshot_steps(folder: Path) -> list[int]:
    """Return the steps of the saved snapshots of a run (to replay the animation without recalculating)."""
    return [int(path.stem.split("_")[1]) for path in list_snapshots(folder)]


def render_snapshot_png(folder: Path, step: int) -> bytes | None:
    """Return the PNG of the crystal at a saved snapshot, or None if that step was not saved."""
    path = folder / "snapshots" / f"snapshot_{step:09d}.npz"
    if not path.exists():
        return None
    snapshot = load_snapshot(path)
    params = read_json(folder / "params.json")["solution_params"]
    if params["sector_partition"] is None:
        picture = render_plain_crystal_rgb(snapshot["phase_field"].astype(float))
    else:
        picture = render_crystal_rgb(
            snapshot["phase_field"].astype(float), snapshot["crystal_iron"].astype(float), params["solid_capacity"], params["color_iron_scale"]
        )
    buffer = io.BytesIO()
    imsave(buffer, picture, format="png", origin="lower")
    return buffer.getvalue()
