"""Diffusion of dissolved silica through the fluid, written as exchanges between neighbours.

Silica moves from each cell to its neighbours across the cell faces. Whatever leaves one
cell enters the next, so the total amount of silica cannot change by diffusion: that is what
makes mass conservation exact. Crystal blocks diffusion: the diffusivity of a face is
D * (fluid fraction on that face), so it is ~0 inside the crystal.
"""

import numpy as np


def compute_solid_fraction(phase_field: np.ndarray) -> np.ndarray:
    """Return h(phi) = phi^2 * (3 - 2*phi): the fraction of each cell that is solid.

    It is 0 in fluid and 1 in crystal, like phi, but flat at both ends, so the cells deep
    in the fluid or deep in the crystal take no silica from (or give none to) the solution.
    """
    return phase_field**2 * (3.0 - 2.0 * phase_field)


def compute_face_fluid_fraction(solid_fraction: np.ndarray, axis: int) -> np.ndarray:
    """Return the fluid fraction on every face between neighbouring cells along an axis.

    The face value is the average of the two cells it separates.
    """
    fluid = 1.0 - solid_fraction
    if axis == 0:
        return 0.5 * (fluid[1:, :] + fluid[:-1, :])
    return 0.5 * (fluid[:, 1:] + fluid[:, :-1])


def compute_flux_along_axis(
    silica: np.ndarray, solid_fraction: np.ndarray, axis: int, diffusivity: float
) -> np.ndarray:
    """Return the silica flux through every face along one axis (per unit time, cell size 1).

    Positive flux goes towards increasing index. Flux is proportional to the concentration
    difference between the two cells and to the fluid fraction on the face.
    """
    face_fluid = compute_face_fluid_fraction(solid_fraction, axis)
    difference = np.diff(silica, axis=axis)
    return diffusivity * face_fluid * difference


def compute_diffusion_change(
    silica: np.ndarray, solid_fraction: np.ndarray, diffusivity: float
) -> np.ndarray:
    """Return d(silica)/dt caused by diffusion alone, with closed (no-flux) boundaries.

    Each cell gains what flows in through its faces and loses what flows out.
    """
    change = np.zeros_like(silica)
    flux_vertical = compute_flux_along_axis(silica, solid_fraction, 0, diffusivity)
    change[:-1, :] += flux_vertical
    change[1:, :] -= flux_vertical
    flux_horizontal = compute_flux_along_axis(silica, solid_fraction, 1, diffusivity)
    change[:, :-1] += flux_horizontal
    change[:, 1:] -= flux_horizontal
    return change
