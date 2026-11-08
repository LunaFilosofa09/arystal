"""Measurements of the crystal at one moment.

All lengths are in grid cells unless the name says otherwise. The seed sits at the middle of the
grid on the wall; "m", "r" and "z" are the face families of the amethyst section (see anisotropy.py).
"""

import math

import numpy as np

from arystal.engine.anisotropic_phase_field import compute_gradient
from arystal.engine.anisotropy import compute_face_normal_angles
from arystal.engine.grid import WALL_MIRROR_Y, compute_seed_center_x
from arystal.engine.iron_partition import NUMBER_OF_FAMILIES
from arystal.metrics.symmetry import compute_crystal_mask

FAMILY_NAMES = ("m", "r", "z")

# The face used to measure each family's growth: the upper right m face, the upper right r face, the upper left z face.
FACE_KEYS = {"m": "m_right", "r": "r_upper_right", "z": "z_upper_left"}

# Interface cells are those where phi is within this distance of 1/2.
INTERFACE_BAND = 0.1

# Cells used to locate the surface with sub-cell accuracy: phi within this distance of 1/2, and a usable gradient.
SURFACE_BAND = 0.25
MINIMUM_GRADIENT = 1e-3

# Silica sums smaller than this are treated as "nothing deposited" (avoids dividing by zero).
MINIMUM_DEPOSITED_SILICA = 1e-30


def collect_surface_points(phase_field: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (x, y) positions of points on the crystal surface, with better-than-one-cell accuracy.

    Every cell near the surface (phi between 0.25 and 0.75) estimates where the surface is by moving
    along the outward normal by (phi - 1/2) / |grad phi|, which is the distance to phi = 1/2 for a
    locally linear profile. x is measured from the seed centre, y from the wall's mirror plane.
    """
    gradient_x, gradient_y = compute_gradient(phase_field)
    strength = np.hypot(gradient_x, gradient_y)
    band = (np.abs(phase_field - 0.5) < SURFACE_BAND) & (strength > MINIMUM_GRADIENT)
    rows, columns = np.nonzero(band)
    along = (phase_field[band] - 0.5) / strength[band]
    outward_x = -gradient_x[band] / strength[band]
    outward_y = -gradient_y[band] / strength[band]
    x = columns - compute_seed_center_x(phase_field.shape[1]) + along * outward_x
    y = rows - WALL_MIRROR_Y + along * outward_y
    return x, y


def compute_support_distance(phase_field: np.ndarray, normal_angle: float) -> float:
    """Return how far the crystal extends from the seed centre in the direction `normal_angle` (cells).

    The "support distance": the largest value of (surface position . direction). For a flat face with that
    normal it is the distance of the face from the seed centre; for a round shape it is the radius.
    """
    x, y = collect_surface_points(phase_field)
    if len(x) == 0:
        return float("nan")
    return float((x * math.cos(normal_angle) + y * math.sin(normal_angle)).max())


def compute_face_distances(phase_field: np.ndarray, r_pole_angle_to_c_degrees: float) -> dict[str, float]:
    """Return the support distance (cells) in the directions of the m, r and z faces."""
    angles = compute_face_normal_angles(r_pole_angle_to_c_degrees)
    return {family: compute_support_distance(phase_field, angles[key]) for family, key in FACE_KEYS.items()}


def compute_height_and_width(phase_field: np.ndarray) -> tuple[float, float]:
    """Return (height along the c-axis, width) of the crystal's bounding box, in cells."""
    mask = compute_crystal_mask(phase_field)
    rows, columns = np.nonzero(mask)
    if len(rows) == 0:
        return 0.0, 0.0
    return float(rows.max() + 1), float(columns.max() - columns.min() + 1)


def compute_aspect_ratio(height: float, width: float) -> float:
    """Return length along c divided by width (nan for an empty crystal)."""
    return height / width if width > 0 else float("nan")


def compute_estimated_mass_mg(area_cells: float, cell_size_mm: float, thickness_mm: float, density_g_per_cm3: float) -> float:
    """Return the estimated mass in mg: area x assumed thickness x real density of quartz.

    ASSUMPTION (see materials/amethyst.yaml, mass_estimate): the 2D section is extruded to an arbitrary thickness.
    1 g/cm3 = 1 mg/mm3.
    """
    return area_cells * cell_size_mm**2 * thickness_mm * density_g_per_cm3


def compute_interface_supersaturation(silica: np.ndarray, phase_field: np.ndarray, equilibrium: float) -> float:
    """Return the mean S = c / c_eq over the interface cells (nan if there are none)."""
    band = np.abs(phase_field - 0.5) < INTERFACE_BAND
    return float(silica[band].mean() / equilibrium) if band.any() else float("nan")


def compute_bulk_supersaturation(silica: np.ndarray, equilibrium: float) -> float:
    """Return the mean S over the top row of the container, the part farthest from the crystal on the wall."""
    return float(silica[-1].mean() / equilibrium)


def compute_mean_iron_ratio(
    crystal_iron: np.ndarray, phase_field: np.ndarray, solid_fraction: np.ndarray, solid_capacity: float
) -> float:
    """Return the Fe/Si (mol/mol) of the whole crystal: iron locked in / silica held, over the crystal cells."""
    mask = compute_crystal_mask(phase_field)
    silica_held = solid_capacity * solid_fraction[mask].sum()
    return float(crystal_iron[mask].sum() / silica_held) if silica_held > 0 else float("nan")


def compute_iron_ratio_by_sector(sector_iron: np.ndarray, sector_silica: np.ndarray) -> dict[str, float]:
    """Return the Fe/Si (mol/mol) of the material deposited by each face family (m, r, z).

    Exact: it uses the iron and silica recorded by family at the moment of deposition.
    """
    ratios = {}
    for index in range(NUMBER_OF_FAMILIES):
        silica = sector_silica[index].sum()
        ratios[FAMILY_NAMES[index]] = float(sector_iron[index].sum() / silica) if silica > MINIMUM_DEPOSITED_SILICA else float("nan")
    return ratios
