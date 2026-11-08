"""The run loop of growth from a silica solution: grow the crystal in a silica solution, yielding snapshots."""

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np

from arystal.engine.solution_growth import (
    SolutionState,
    advance_one_step,
    compute_total_iron,
    compute_total_silica,
    create_initial_state,
)
from arystal.engine.solution_params import SolutionParams
from arystal.metrics.shape import compute_crystal_area


@dataclass(frozen=True)
class SolutionSnapshot:
    """The state of the run at one moment, plus a few headline numbers."""

    step: int
    time: float
    phase_field: np.ndarray
    silica: np.ndarray
    iron: np.ndarray
    crystal_iron: np.ndarray
    crystal_area: float
    total_silica: float
    total_iron: float
    minimum_silica: float
    minimum_iron: float


def make_snapshot(step: int, state: SolutionState, params: SolutionParams) -> SolutionSnapshot:
    """Bundle the current state and its headline numbers into a snapshot."""
    return SolutionSnapshot(
        step=step,
        time=step * params.time_step,
        phase_field=state.phase_field.copy(),
        silica=state.silica.copy(),
        iron=state.iron.copy(),
        crystal_iron=state.crystal_iron.copy(),
        crystal_area=compute_crystal_area(state.phase_field),
        total_silica=compute_total_silica(state, params),
        total_iron=compute_total_iron(state),
        minimum_silica=float(state.silica.min()),
        minimum_iron=float(state.iron.min()),
    )


def iterate_solution_growth(
    params: SolutionParams, steps_per_snapshot: int, duration: float
) -> Iterator[SolutionSnapshot]:
    """Grow the crystal until `duration` model time units, yielding a snapshot every few steps."""
    state = create_initial_state(params)
    step = 0
    yield make_snapshot(step, state, params)
    while step * params.time_step < duration:
        for _ in range(steps_per_snapshot):
            state = advance_one_step(state, params)
            step += 1
        yield make_snapshot(step, state, params)
