"""Implicit (backward Euler) diffusion of silica and iron, for long runs where the growth is slow compared with the diffusion.

WHY: with the explicit scheme the time step is limited by the diffusion (dt < 0.225 cell^2 / D), so a run whose crystal grows
slowly (surface-limited growth, small Damkohler number Da) needs about 1/Da steps, although the dissolved silica hardly changes.
The implicit scheme is stable for any time step, so the step can be chosen by how far the interface moves (a fraction of a cell).
It is a change of numerical scheme only: the equations are the same (docs/kinetic_regime.md, section 8, optimisation 2).

WHAT IT SOLVES: the same face-by-face diffusion as silica_transport.py, written as a matrix A, with
        (I - dt * A) c_new = c_old - Cs * (change of the solid fraction)
The conductivity of every face uses the fluid fraction at the START of the step (as in the explicit scheme). A has zero column sums
(what leaves a cell enters its neighbour), so the total silica is conserved exactly, up to rounding, by the direct solver.
The coupling between the fields is still explicit (the driving force uses the silica at the start of the step), so the time step
must keep the change of the solid fraction per step small: see suggest_implicit_time_step.
"""

import numpy as np
from scipy.sparse import coo_matrix, identity
from scipy.sparse.linalg import splu

from arystal.engine.silica_transport import compute_solid_fraction
from arystal.engine.solution_params import MODEL_DIFFUSIVITY, SolutionParams

# The interface should move at most this many cells per step for the explicit coupling to stay accurate.
TARGET_FRONT_DISPLACEMENT_CELLS = 0.3


def build_diffusion_operator(solid_fraction: np.ndarray, diffusivity: float) -> coo_matrix:
    """Return the matrix A such that (A c) is d(c)/dt by diffusion through the fluid (closed boundaries), cells numbered row by row.

    Each face between two neighbouring cells has conductivity diffusivity * (average fluid fraction of the two cells); the cell
    on one side gains what the cell on the other side loses.
    """
    rows, columns = solid_fraction.shape
    fluid = 1.0 - solid_fraction
    index = np.arange(rows * columns).reshape(rows, columns)
    vertical = diffusivity * 0.5 * (fluid[:-1, :] + fluid[1:, :])      # faces between a cell and the one above it
    horizontal = diffusivity * 0.5 * (fluid[:, :-1] + fluid[:, 1:])    # faces between a cell and the one to its right
    first = np.concatenate([index[:-1, :].ravel(), index[:, :-1].ravel()])   # one side of every face
    second = np.concatenate([index[1:, :].ravel(), index[:, 1:].ravel()])    # the other side
    conductivity = np.concatenate([vertical.ravel(), horizontal.ravel()])
    row_index = np.concatenate([first, second, first, second])
    column_index = np.concatenate([second, first, first, second])
    values = np.concatenate([conductivity, conductivity, -conductivity, -conductivity])
    size = rows * columns
    return coo_matrix((values, (row_index, column_index)), shape=(size, size))


def solve_implicit_diffusion(
    field: np.ndarray, source: np.ndarray, solid_fraction: np.ndarray, diffusivity: float, time_step: float
) -> np.ndarray:
    """Return the field after one implicit step: solve (I - dt A) new = field + source (the source is already multiplied by nothing: it is the amount added)."""
    operator = build_diffusion_operator(solid_fraction, diffusivity).tocsc()
    system = (identity(operator.shape[0], format="csc") - time_step * operator).tocsc()
    solution = splu(system).solve((field + source).ravel())
    return solution.reshape(field.shape)


def advance_silica_implicit(silica: np.ndarray, old_solid: np.ndarray, new_solid: np.ndarray, params: SolutionParams) -> np.ndarray:
    """Return the silica after one implicit step: diffusion minus what the new crystal absorbed."""
    absorbed = params.solid_capacity * (new_solid - old_solid)
    return solve_implicit_diffusion(silica, -absorbed, old_solid, MODEL_DIFFUSIVITY, params.time_step)


def advance_iron_implicit(iron: np.ndarray, exchange: np.ndarray, old_solid: np.ndarray, params: SolutionParams) -> np.ndarray:
    """Return the fluid iron after one implicit step: diffusion minus the iron exchanged with the crystal."""
    return solve_implicit_diffusion(iron, -exchange, old_solid, MODEL_DIFFUSIVITY * params.iron_diffusivity_ratio, params.time_step)


def suggest_implicit_time_step(params: SolutionParams, front_speed_cells_per_time: float) -> float:
    """Return a time step that moves the fastest interface by TARGET_FRONT_DISPLACEMENT_CELLS per step (never above the phase-field limit)."""
    wanted = TARGET_FRONT_DISPLACEMENT_CELLS / front_speed_cells_per_time
    return min(wanted, params.relaxation_time / (4.0 * params.interface_epsilon**2) * 0.5)
