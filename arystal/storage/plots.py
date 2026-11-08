"""PNG graphs of the metrics over time (written into the run's plots/ folder)."""

from pathlib import Path

import numpy as np
from matplotlib.figure import Figure

# (file name, title, [(column, label)], y label)
PLOT_DEFINITIONS = [
    ("growth.png", "Crystal size", [("crystal_area_mm2", "area (mm2)")], "area (mm2) - see also mass in metrics.csv"),
    ("shape.png", "Shape", [("aspect_ratio", "length along c / width")], "aspect ratio"),
    ("face_growth.png", "Growth of each face family (support distance)",
     [("face_distance_m_cells", "m"), ("face_distance_r_cells", "r"), ("face_distance_z_cells", "z")], "distance from seed (cells)"),
    ("face_rates.png", "Growth rate of each face family",
     [("growth_rate_m_cells_per_time", "m"), ("growth_rate_r_cells_per_time", "r"), ("growth_rate_z_cells_per_time", "z")], "cells per model time unit"),
    ("iron.png", "Iron incorporated in the crystal (Fe/Si, mol/mol)",
     [("mean_iron_ratio", "mean"), ("iron_ratio_m", "m sector"), ("iron_ratio_r", "r sector"), ("iron_ratio_z", "z sector")], "Fe / Si"),
    ("supersaturation.png", "Supersaturation S = c / c_eq",
     [("supersaturation_interface", "at the interface"), ("supersaturation_bulk", "in the bulk fluid")], "S"),
    ("conservation.png", "Conservation check (relative change of the totals)",
     [("silica_relative_drift", "silica"), ("iron_relative_drift", "iron")], "relative change"),
]


def has_data(rows: list[dict], columns: list[tuple[str, str]]) -> bool:
    """Return True if at least one of the columns has a real (non-nan) value."""
    return any(not np.isnan(row[column]) for row in rows for column, _ in columns)


def save_one_plot(folder: Path, rows: list[dict], definition: tuple) -> None:
    """Draw one metric graph against model time and save it as PNG."""
    file_name, title, columns, y_label = definition
    figure = Figure(figsize=(7, 4))
    axes = figure.subplots()
    times = [row["time_model"] for row in rows]
    for column, label in columns:
        axes.plot(times, [row[column] for row in rows], label=label)
    axes.set_xlabel("model time (not physical time)")
    axes.set_ylabel(y_label)
    axes.set_title(title)
    axes.grid(alpha=0.3)
    if len(columns) > 1:
        axes.legend()
    figure.tight_layout()
    figure.savefig(Path(folder) / "plots" / file_name, dpi=110)


def save_metric_plots(folder: Path, rows: list[dict]) -> list[str]:
    """Save all metric graphs that have data and return their file names."""
    saved = []
    for definition in PLOT_DEFINITIONS:
        if has_data(rows, definition[2]):
            save_one_plot(folder, rows, definition)
            saved.append(definition[0])
    return saved
