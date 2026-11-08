"""The same quantities as the observations, measured on a saved run (results/<run>/).

Every quantity is read from what the run saved: metrics.csv (last row), final_state.npz (sector arrays) and params.json (material angles).
"""

import csv
import json
import math
from pathlib import Path

import numpy as np

# Numerical uncertainty of the aspect ratio by mode, from the resolution convergence (validation check 5): explore about 13% low, research about 2%.
ASPECT_RATIO_NUMERICAL_UNCERTAINTY = {"explore": 0.13, "research": 0.02}
FACE_RATIO_NUMERICAL_UNCERTAINTY = {"explore": 0.05, "research": 0.005}
FAMILIES = ("m", "r", "z")
COLOR_SATURATION_FRACTION = 1.0 - math.exp(-1.0)   # the colour law reaches 63% of full colour at the colour scale


def read_last_metrics_row(folder: Path) -> dict[str, float]:
    """Return the last row of metrics.csv as numbers (nan for empty or null cells)."""
    with open(Path(folder) / "metrics.csv") as file:
        rows = list(csv.DictReader(file))
    return {key: float(value) if value not in ("", "null", "None") else float("nan") for key, value in rows[-1].items()}


def read_params(folder: Path) -> dict:
    """Return params.json of the run."""
    return json.loads((Path(folder) / "params.json").read_text())


def compute_section_angles(r_pole_angle_to_c_degrees: float) -> dict[str, float]:
    """Return the interior angles of the longitudinal section, in degrees.

    Prism m to rhombohedron r: 180 - (90 - rho); apex between r and z: 180 - 2 rho, where rho is the angle of the r pole from the c-axis.
    These follow from the crystallography (material file), not from the growth: they test the cut and the face identification.
    """
    return {"angle_m_to_r_degrees": 180.0 - (90.0 - r_pole_angle_to_c_degrees), "apex_angle_r_to_z_degrees": 180.0 - 2.0 * r_pole_angle_to_c_degrees}


def compute_sector_area_shares(folder: Path) -> dict[str, float]:
    """Return the share of the crystal laid down by each face family (m, r, z), from the silica deposited per sector."""
    sector_silica = np.load(Path(folder) / "final_state.npz")["sector_silica"]
    totals = [float(sector_silica[index].sum()) for index in range(len(FAMILIES))]
    return {f"sector_share_{family}": totals[index] / sum(totals) for index, family in enumerate(FAMILIES)}


def compute_color_intensity(iron_ratio: float, color_scale: float) -> float:
    """Return the rendered colour intensity (0-1) of a sector with this Fe/Si ratio: 1 - exp(-ratio / scale), the ASSUMED colour law."""
    return 1.0 - math.exp(-iron_ratio / color_scale)


def measure_simulated_quantities(folder: Path) -> dict[str, float]:
    """Return every comparable quantity of a saved run (names as in the observation files)."""
    row, params = read_last_metrics_row(folder), read_params(folder)
    material = params["material_constants"]
    scale = material["color_iron_scale"]
    values = {"aspect_ratio": row["aspect_ratio"], "face_ratio_r_over_m": row["face_distance_r_cells"] / row["face_distance_m_cells"]}
    values.update(compute_section_angles(material["r_pole_angle_to_c_degrees"]))
    values.update(compute_sector_area_shares(folder))
    intensities = {family: compute_color_intensity(row[f"iron_ratio_{family}"], scale) for family in FAMILIES}
    values.update({"color_contrast_r_over_m": intensities["r"] / intensities["m"], "color_contrast_r_over_z": intensities["r"] / intensities["z"]})
    return values


def get_numerical_uncertainty(name: str, value: float, mode: str) -> float:
    """Return the model's own numerical uncertainty of a quantity (absolute), from the convergence check; 0 when it is exact."""
    if name == "aspect_ratio":
        return ASPECT_RATIO_NUMERICAL_UNCERTAINTY.get(mode, 0.13) * value
    if name == "face_ratio_r_over_m":
        return FACE_RATIO_NUMERICAL_UNCERTAINTY.get(mode, 0.05) * value
    return 0.0
