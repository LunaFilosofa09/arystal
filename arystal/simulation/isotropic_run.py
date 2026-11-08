"""The run loop of the isotropic model: grow the seed and hand out a snapshot every few steps."""

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np

from arystal.engine.grid import create_half_disc_seed
from arystal.engine.isotropic_params import IsotropicParams
from arystal.engine.phase_field import advance_one_step
from arystal.metrics.shape import compute_equivalent_radius

# Stop before the crystal touches the sides or the top of the domain.
STOP_MARGIN_CELLS = 10.0


@dataclass(frozen=True)
class Snapshot:
    """The state of the run at one moment."""

    step: int
    time: float
    phase_field: np.ndarray
    equivalent_radius: float


def compute_maximum_radius(params: IsotropicParams) -> float:
    """Return the largest crystal radius (cells) the domain allows before boundaries interfere."""
    limit = min(params.grid_height, params.grid_width / 2.0)
    return limit - STOP_MARGIN_CELLS


def create_initial_phase_field(params: IsotropicParams) -> np.ndarray:
    """Return the starting phase field (half-disc seed on the wall)."""
    return create_half_disc_seed(
        params.grid_width, params.grid_height, params.seed_radius, params.interface_epsilon
    )


def make_snapshot(step: int, phase_field: np.ndarray, params: IsotropicParams) -> Snapshot:
    """Bundle the current state into a Snapshot."""
    return Snapshot(
        step=step,
        time=step * params.time_step,
        phase_field=phase_field.copy(),
        equivalent_radius=compute_equivalent_radius(phase_field),
    )


def iterate_growth(params: IsotropicParams, steps_per_snapshot: int) -> Iterator[Snapshot]:
    """Grow the crystal, yielding a Snapshot every `steps_per_snapshot` steps.

    Stops by itself when the crystal gets close to the domain limits.
    """
    phase_field = create_initial_phase_field(params)
    step = 0
    yield make_snapshot(step, phase_field, params)
    while compute_equivalent_radius(phase_field) < compute_maximum_radius(params):
        for _ in range(steps_per_snapshot):
            phase_field = advance_one_step(phase_field, params)
            step += 1
        yield make_snapshot(step, phase_field, params)
