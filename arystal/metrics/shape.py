"""Simple shape measurements of a half-disc-like crystal sitting on the wall."""

import numpy as np
from scipy.ndimage import map_coordinates

from arystal.engine.grid import WALL_MIRROR_Y, compute_seed_center_x

# phi = 0.5 is where we say the crystal surface is.
INTERFACE_LEVEL = 0.5

# How finely we walk along each ray when looking for the surface (cells).
RAY_STEP = 0.25


def compute_crystal_area(phase_field: np.ndarray) -> float:
    """Return the crystal area in cells (sum of phi over the grid)."""
    return float(phase_field.sum())


def compute_equivalent_radius(phase_field: np.ndarray) -> float:
    """Return the radius (cells) of the half-disc that has the same area as the crystal."""
    return float(np.sqrt(2.0 * compute_crystal_area(phase_field) / np.pi))


def sample_ray(phase_field: np.ndarray, angle: float, max_distance: float) -> np.ndarray:
    """Return phi sampled along a ray from the seed centre at the given angle (radians).

    Angle 0 points right along the wall, pi/2 straight up, pi left along the wall.
    """
    distances = np.arange(0.0, max_distance, RAY_STEP)
    xs = compute_seed_center_x(phase_field.shape[1]) + distances * np.cos(angle)
    ys = WALL_MIRROR_Y + distances * np.sin(angle)
    return map_coordinates(phase_field, [ys, xs], order=1, mode="nearest")


def find_surface_distance(phase_field: np.ndarray, angle: float, max_distance: float) -> float:
    """Return the distance (cells) from the seed centre to the crystal surface along a ray.

    Walks outward until phi drops below 1/2 and interpolates linearly between the two samples.
    Returns nan if the surface is not found inside max_distance.
    """
    values = sample_ray(phase_field, angle, max_distance)
    below = np.nonzero(values < INTERFACE_LEVEL)[0]
    if len(below) == 0 or below[0] == 0:
        return float("nan")
    index = below[0]
    fraction = (values[index - 1] - INTERFACE_LEVEL) / (values[index - 1] - values[index])
    return float((index - 1 + fraction) * RAY_STEP)


def measure_surface_radii(phase_field: np.ndarray, number_of_angles: int = 91) -> np.ndarray:
    """Return the surface distance for angles spread from 0 to 180 degrees (along the wall, up, along the wall)."""
    max_distance = float(min(phase_field.shape[0], phase_field.shape[1] / 2.0)) - 1.0
    angles = np.linspace(0.0, np.pi, number_of_angles)
    return np.array([find_surface_distance(phase_field, a, max_distance) for a in angles])


def compute_roundness_error(radii: np.ndarray) -> float:
    """Return (max radius - min radius) / mean radius. 0 means a perfect half-circle."""
    return float((np.nanmax(radii) - np.nanmin(radii)) / np.nanmean(radii))


def find_level_distance(phase_field: np.ndarray, angle: float, max_distance: float, level: float) -> float:
    """Return the distance (cells) from the seed centre at which phi first drops below `level` along a ray (nan if never)."""
    values = sample_ray(phase_field, angle, max_distance)
    below = np.nonzero(values < level)[0]
    if len(below) == 0 or below[0] == 0:
        return float("nan")
    index = below[0]
    fraction = (values[index - 1] - level) / (values[index - 1] - values[index])
    return float((index - 1 + fraction) * RAY_STEP)


def compute_surface_roughness(phase_field: np.ndarray, level: float, number_of_angles: int = 181) -> float:
    """Return the roughness of the contour phi = `level`: root-mean-square second difference of its radius along the angle.

    A smooth shape (even a faceted one) has a small value; random jitter of the surface makes it grow.
    It is independent of the overall size, and 0 for a perfect circle.
    """
    max_distance = float(min(phase_field.shape[0], phase_field.shape[1] / 2.0)) - 1.0
    angles = np.linspace(0.0, np.pi, number_of_angles)
    radii = np.array([find_level_distance(phase_field, a, max_distance, level) for a in angles])
    second_difference = radii[1:-1] - 0.5 * (radii[:-2] + radii[2:])
    return float(np.sqrt(np.nanmean(second_difference**2)))
