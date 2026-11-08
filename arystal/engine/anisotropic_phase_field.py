"""Phase-field step with orientation-dependent growth speed (kinetic anisotropy).

    tau(n) * d(phi)/dt = epsilon^2 * laplacian(phi) + phi*(1-phi)*(phi - 1/2 + m)
    tau(n) = tau0 / g(theta)

where theta is the angle of the outward surface normal and g the speed factor of
anisotropy.py. A surface with orientation theta therefore moves g(theta) times as fast as
in the isotropic model. With anisotropy switched off (None), g = 1 everywhere and this is
exactly the isotropic equation.
"""

import numpy as np

from arystal.engine.anisotropy import GRADIENT_THRESHOLD, FacetAnisotropy, compute_speed_factor_from_angle
from arystal.engine.phase_field import compute_double_well_force, compute_laplacian


def compute_gradient(field: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (d/dx, d/dy) of a field by central differences (cell size 1, mirror at the edges)."""
    padded = np.pad(field, 1, mode="edge")
    gradient_x = 0.5 * (padded[1:-1, 2:] - padded[1:-1, :-2])
    gradient_y = 0.5 * (padded[2:, 1:-1] - padded[:-2, 1:-1])
    return gradient_x, gradient_y


def compute_outward_normal_angle(gradient_x: np.ndarray, gradient_y: np.ndarray) -> np.ndarray:
    """Return the angle (radians from +x) of the surface normal pointing out of the crystal.

    phi grows towards the crystal, so the outward normal is minus its gradient.
    """
    return np.arctan2(-gradient_y, -gradient_x)


def compute_speed_factor_field(phase_field: np.ndarray, anisotropy: FacetAnisotropy | None) -> np.ndarray:
    """Return g for every cell (1 where the surface orientation is undefined or anisotropy is off)."""
    factor = np.ones_like(phase_field)
    if anisotropy is None:
        return factor
    gradient_x, gradient_y = compute_gradient(phase_field)
    on_interface = gradient_x**2 + gradient_y**2 > GRADIENT_THRESHOLD**2
    angle = compute_outward_normal_angle(gradient_x[on_interface], gradient_y[on_interface])
    factor[on_interface] = compute_speed_factor_from_angle(angle, anisotropy)
    return factor


def advance_phase_field(
    phase_field: np.ndarray,
    driving_force: np.ndarray,
    anisotropy: FacetAnisotropy | None,
    interface_epsilon: float,
    relaxation_time: float,
    time_step: float,
) -> np.ndarray:
    """Return phi after one explicit time step, for a given driving force m (array or scalar)."""
    speed_factor = compute_speed_factor_field(phase_field, anisotropy)
    smoothing = interface_epsilon**2 * compute_laplacian(phase_field)
    push = compute_double_well_force(phase_field, driving_force)
    rate = speed_factor * (smoothing + push) / relaxation_time
    return phase_field + time_step * rate
