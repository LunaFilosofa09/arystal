"""Measurements of flat faces (facets) on the simulated crystal surface."""

import math

import numpy as np

from arystal.engine.anisotropic_phase_field import compute_gradient, compute_outward_normal_angle
from arystal.engine.grid import WALL_MIRROR_Y, compute_seed_center_x

# Interface cells are those where phi is within this distance of 1/2.
INTERFACE_BAND = 0.1

# Surface cells with |grad phi| below this are ignored (orientation undefined).
MINIMUM_GRADIENT = 1e-3


def collect_interface_cells(phase_field: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (x, y, normal angle) of every interface cell.

    x is measured from the seed centre, y from the wall's mirror plane, both in cells;
    the angle is the outward surface normal in radians from +x.
    """
    gradient_x, gradient_y = compute_gradient(phase_field)
    strength = np.hypot(gradient_x, gradient_y)
    band = (np.abs(phase_field - 0.5) < INTERFACE_BAND) & (strength > MINIMUM_GRADIENT)
    rows, columns = np.nonzero(band)
    x = columns - compute_seed_center_x(phase_field.shape[1])
    y = rows - WALL_MIRROR_Y
    angle = compute_outward_normal_angle(gradient_x[band], gradient_y[band])
    return x, y, angle


def compute_angle_difference(first: np.ndarray, second: float) -> np.ndarray:
    """Return the smallest absolute difference between angles (radians), handling wrap-around."""
    difference = np.abs(first - second) % (2.0 * math.pi)
    return np.minimum(difference, 2.0 * math.pi - difference)


def measure_facet_distance(
    phase_field: np.ndarray, normal_angle: float, tolerance_degrees: float
) -> tuple[float, int]:
    """Measure how far a flat face is from the seed centre, measured along its normal.

    Takes the interface cells whose normal is within `tolerance_degrees` of `normal_angle`
    and averages their distance along that normal. Returns (distance in cells, number of
    cells used); (nan, 0) if there are none, i.e. the face does not exist.
    """
    x, y, angle = collect_interface_cells(phase_field)
    chosen = compute_angle_difference(angle, normal_angle) < math.radians(tolerance_degrees)
    if not chosen.any():
        return float("nan"), 0
    distances = x[chosen] * math.cos(normal_angle) + y[chosen] * math.sin(normal_angle)
    return float(distances.mean()), int(chosen.sum())
