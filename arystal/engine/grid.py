"""The grid and the initial crystal seed.

Array convention: phase_field[row, column], row 0 is the WALL (bottom of the picture),
column 0 is the left side. The wall behaves as a mirror (no flux through it), which is
what makes a seed centred on the wall a half-disc.
"""

import numpy as np

# The mirror plane of the wall lies half a cell below row 0, because the boundary
# condition copies row 0 into the "ghost" row below it (see compute_laplacian).
WALL_MIRROR_Y = -0.5

# Width of a tanh interface profile: phi = 0.5 * (1 - tanh(d / (2*sqrt(2)*epsilon))).
# This is the exact equilibrium profile of the double-well model used in phase_field.py.
TANH_SCALE_FACTOR = 2.0 * np.sqrt(2.0)


def compute_seed_center_x(grid_width: int) -> float:
    """Return the x position (in cells) of the middle of the grid, where the seed sits."""
    return (grid_width - 1) / 2.0


def compute_distance_to_seed_center(grid_width: int, grid_height: int, offset_x: float = 0.0) -> np.ndarray:
    """Return, for every cell, its distance in cells to the seed centre (on the wall).

    `offset_x` moves the seed centre sideways from the middle of the grid (cells).

    Output shape is (grid_height, grid_width).
    """
    rows, columns = np.mgrid[0:grid_height, 0:grid_width]
    delta_x = columns - (compute_seed_center_x(grid_width) + offset_x)
    delta_y = rows - WALL_MIRROR_Y
    return np.sqrt(delta_x**2 + delta_y**2)


def create_half_disc_seed(
    grid_width: int, grid_height: int, seed_radius: float, interface_epsilon: float, offset_x: float = 0.0
) -> np.ndarray:
    """Create the starting phase field: a small half-disc of crystal on the wall.

    Physically: the first nucleus of crystal stuck to the cavity wall.
    Inside the disc the field is 1 (crystal), outside it is 0 (fluid), with the
    smooth tanh border that the model itself would settle into.
    """
    distance = compute_distance_to_seed_center(grid_width, grid_height, offset_x)
    scaled_offset = (distance - seed_radius) / (TANH_SCALE_FACTOR * interface_epsilon)
    return 0.5 * (1.0 - np.tanh(scaled_offset))
