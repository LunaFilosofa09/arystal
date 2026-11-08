"""Pictures and tables of an ensemble: the replicas side by side, and the metrics as mean +/- standard deviation."""

import csv
import math
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure

from arystal.storage.rendering import render_crystal_rgb
from arystal.storage.serialization import read_json
from arystal.storage.snapshots import load_final_state

# Free space (cells) kept around the crystals in the comparison picture.
CROP_MARGIN_CELLS = 6

# Phase-field values above this count as "crystal" when deciding the common crop.
CROP_THRESHOLD = 0.05

COLUMNS_IN_COMPARISON = 5

# (file, title, [(column prefix, label)], y label)
ENSEMBLE_PLOTS = [
    ("ensemble_size.png", "Crystal area (mean +/- standard deviation over the replicas)", [("crystal_area_mm2", "area (mm2)")], "area (mm2)"),
    ("ensemble_shape.png", "Aspect ratio (length along c / width)", [("aspect_ratio", "aspect ratio")], "aspect ratio"),
    ("ensemble_faces.png", "Growth of each face family (support distance)",
     [("face_distance_m_cells", "m"), ("face_distance_r_cells", "r"), ("face_distance_z_cells", "z")], "cells"),
    ("ensemble_iron.png", "Iron incorporated (Fe/Si)", [("mean_iron_ratio", "mean"), ("iron_ratio_m", "m"), ("iron_ratio_r", "r"), ("iron_ratio_z", "z")], "Fe / Si"),
]


def write_timeseries_csv(path: Path, rows: list[dict]) -> None:
    """Write the mean and standard deviation over the replicas at every sampling moment."""
    with open(path, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def has_data(rows: list[dict], columns: list[tuple[str, str]]) -> bool:
    """True if at least one of the columns has a real value."""
    return any(not math.isnan(row[f"{column}_mean"]) for row in rows for column, _ in columns)


def save_one_ensemble_plot(folder: Path, rows: list[dict], definition: tuple) -> None:
    """Draw one mean +/- standard deviation graph against model time."""
    file_name, title, columns, y_label = definition
    figure = Figure(figsize=(7, 4))
    axes = figure.subplots()
    times = np.array([row["time_model"] for row in rows])
    for column, label in columns:
        mean = np.array([row[f"{column}_mean"] for row in rows])
        std = np.nan_to_num(np.array([row[f"{column}_std"] for row in rows]))
        axes.plot(times, mean, label=label)
        axes.fill_between(times, mean - std, mean + std, alpha=0.25)
    axes.set_xlabel("model time (not physical time)")
    axes.set_ylabel(y_label)
    axes.set_title(title, fontsize=9)
    axes.grid(alpha=0.3)
    if len(columns) > 1:
        axes.legend()
    figure.tight_layout()
    figure.savefig(Path(folder) / file_name, dpi=110)


def save_ensemble_plots(folder: Path, rows: list[dict]) -> list[str]:
    """Save the ensemble graphs that have data and return their file names."""
    saved = []
    for definition in ENSEMBLE_PLOTS:
        if has_data(rows, definition[2]):
            save_one_ensemble_plot(folder, rows, definition)
            saved.append(definition[0])
    return saved


def compute_common_crop(phase_fields: list[np.ndarray]) -> tuple[slice, slice]:
    """Return (rows, columns) slices that contain every crystal, plus a margin, so replicas are drawn at the same scale."""
    height, width = phase_fields[0].shape
    rows = np.concatenate([np.nonzero((field > CROP_THRESHOLD).any(axis=1))[0] for field in phase_fields])
    columns = np.concatenate([np.nonzero((field > CROP_THRESHOLD).any(axis=0))[0] for field in phase_fields])
    return (
        slice(0, min(height, int(rows.max()) + CROP_MARGIN_CELLS)),
        slice(max(0, int(columns.min()) - CROP_MARGIN_CELLS), min(width, int(columns.max()) + CROP_MARGIN_CELLS)),
    )


def save_comparison_image(folder: Path, replica_folders: list[Path], seeds: list[int]) -> Path:
    """Draw the final crystals of all replicas side by side (comparison.png)."""
    states = [load_final_state(replica) for replica in replica_folders]
    params = read_json(replica_folders[0] / "params.json")["solution_params"]
    iron_on = params["sector_partition"] is not None
    crop = compute_common_crop([state["phase_field"] for state in states])
    count = len(replica_folders)
    rows_of_plots = math.ceil(count / COLUMNS_IN_COMPARISON)
    figure = Figure(figsize=(3.0 * COLUMNS_IN_COMPARISON, 2.6 * rows_of_plots + 0.6))
    axes = figure.subplots(rows_of_plots, COLUMNS_IN_COMPARISON, squeeze=False)
    for slot, axis in enumerate(axes.flat):
        axis.axis("off")
        if slot >= count:
            continue
        phase_field, crystal_iron = states[slot]["phase_field"][crop], states[slot]["crystal_iron"][crop]
        if iron_on:
            axis.imshow(render_crystal_rgb(phase_field, crystal_iron, params["solid_capacity"], params["color_iron_scale"]), origin="lower")
        else:
            axis.imshow(phase_field, origin="lower", cmap="Purples", vmin=0, vmax=1)
        axis.set_title(f"replica {slot + 1}  (seed {seeds[slot]})", fontsize=8)
    figure.suptitle("Final crystals of the ensemble (same settings and timeline, different seeds; common scale)", fontsize=10)
    figure.tight_layout()
    path = Path(folder) / "comparison.png"
    figure.savefig(path, dpi=110)
    return path
