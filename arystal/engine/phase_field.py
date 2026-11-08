"""The isotropic phase-field equation, one time step at a time.

Equation (non-dimensional):

    tau * d(phi)/dt = epsilon^2 * laplacian(phi) + phi * (1 - phi) * (phi - 1/2 + m)

In words:
  - phi is 1 in the crystal and 0 in the fluid.
  - The laplacian term smooths the border (it is the "surface tension" of the interface).
  - phi*(1-phi)*(phi - 1/2) keeps phi close to 0 or 1 (a "double well").
  - m is the driving force: m > 0 makes crystal win over fluid, so the crystal grows.
    In the silica model it is computed from the supersaturation (solution_growth.py).
"""

import numpy as np

from arystal.engine.isotropic_params import IsotropicParams

# phi = 1/2 is where the two wells (crystal and fluid) are equally favourable.
EQUAL_WELLS_VALUE = 0.5


def compute_laplacian(field: np.ndarray) -> np.ndarray:
    """Return the discrete laplacian of a 2D field (cell size = 1).

    Meaning: how much each cell differs from the average of its four neighbours.
    Edges use a mirror (copy of the edge cell), so nothing flows through the walls.
    """
    padded = np.pad(field, 1, mode="edge")
    up = padded[2:, 1:-1]
    down = padded[:-2, 1:-1]
    right = padded[1:-1, 2:]
    left = padded[1:-1, :-2]
    return up + down + right + left - 4.0 * field


def compute_double_well_force(phase_field: np.ndarray, driving_force: float) -> np.ndarray:
    """Return phi*(1-phi)*(phi - 1/2 + m) for every cell.

    Physically: the push that drives each cell towards crystal (phi=1) or fluid (phi=0).
    """
    tilt = phase_field - EQUAL_WELLS_VALUE + driving_force
    return phase_field * (1.0 - phase_field) * tilt


def compute_phase_field_rate(phase_field: np.ndarray, params: IsotropicParams) -> np.ndarray:
    """Return d(phi)/dt for every cell, in 1/time units."""
    smoothing = params.interface_epsilon**2 * compute_laplacian(phase_field)
    push = compute_double_well_force(phase_field, params.driving_force)
    return (smoothing + push) / params.relaxation_time


def advance_one_step(phase_field: np.ndarray, params: IsotropicParams) -> np.ndarray:
    """Advance the phase field by one explicit Euler step and return the new field."""
    rate = compute_phase_field_rate(phase_field, params)
    return phase_field + params.time_step * rate
