"""Validation check 7: qualitative behaviour.

Two expectations of the Phase 1 specification (an unpublished planning document) are compared with the model:
  A. Higher supersaturation gives faster growth (JUDGED: this is basic physics: the driving force of growth grows with supersaturation).
  B. Very high supersaturation destabilises the facets: the faces stop being flat and the crystal becomes hopper-like or branched (REPORTED,
     NOT JUDGED). This statement comes from the general crystal-growth literature as the spec states it; it has not been verified against a
     source in this project, so the result is reported as a measurement ("observed" or "not observed") and does not decide pass or fail.

Measure used for B: SOLIDITY = crystal area / area of its convex hull. A compact faceted crystal is close to 1; faces that cave in, and branches,
lower it. The facet share (surface within a few degrees of a face normal) is also reported.

WHAT THIS DOES NOT SHOW: that the model reproduces real hopper growth; only whether it shows any loss of compactness within the range tried.
"""

import dataclasses
import math

import numpy as np
from scipy.spatial import ConvexHull

from arystal.engine.material_constants import MaterialConstants
from arystal.engine.solution_growth import advance_one_step, create_initial_state
from arystal.engine.solution_params import SolutionParams
from arystal.metrics.shape import compute_equivalent_radius
from arystal.validation.check_result import CheckResult
from arystal.validation.regime_study import BASE_TAU, MAXIMUM_STEPS, STEPS_BETWEEN_SIZE_CHECKS, build_study_params, compute_facet_fraction

LIMITS_NOTE = (
    "Limits: A is basic physics, judged. B compares with a literature statement that is not verified here and is only reported. "
    "Both are for one geometry, without noise or iron, and the supersaturations of the closed model container."
)

# Test A: surface-limited regime (the one the evidence supports), several run temperatures with the fluid saturated at 60 C.
TEMPERATURES_CELSIUS = (40.0, 30.0, 20.0, 15.0)
SIZE_FOR_TIMING = 22.0              # equivalent radius (cells) at which the growth time is read
MINIMUM_SPEEDUP_LOWEST_TO_HIGHEST = 2.0

# Test B: diffusion-limited regime (tau = 1) where the supply of silica can make corners outrun the middle of the faces, and the plateau regime.
SUPERSATURATIONS = (1.6, 3.3, 10.0, 30.0)   # S = c0 / c_eq at the start
HIGH_SUPERSATURATION_TAUS = (1.0, BASE_TAU)
SIZE_FOR_SHAPE = 24.0
MIN_SOLIDITY_LOSS_TO_CALL_IT_OBSERVED = 0.03   # absolute loss of solidity between the lowest and highest S


def time_to_reach_radius(params: SolutionParams, target_radius: float) -> float:
    """Grow a crystal and return the model time at which its equivalent radius reaches `target_radius` (linear interpolation between steps)."""
    state = create_initial_state(params)
    previous_radius, previous_time, steps = compute_equivalent_radius(state.phase_field), 0.0, 0
    in_place = params.diffusion_scheme == "explicit"
    while steps < MAXIMUM_STEPS:
        for _ in range(STEPS_BETWEEN_SIZE_CHECKS):
            state = advance_one_step(state, params, None, in_place=in_place)
            steps += 1
        radius, time = compute_equivalent_radius(state.phase_field), steps * params.time_step
        if radius >= target_radius:
            return previous_time + (time - previous_time) * (target_radius - previous_radius) / (radius - previous_radius)
        previous_radius, previous_time = radius, time
    return float("nan")


def check_growth_speed_rises_with_supersaturation(material: MaterialConstants) -> CheckResult:
    """Test A."""
    times, supersaturations = [], []
    for celsius in TEMPERATURES_CELSIUS:
        params = build_study_params(material, BASE_TAU, run_celsius=celsius, uniform=True)
        supersaturations.append(params.initial_silica / params.equilibrium_silica)
        times.append(time_to_reach_radius(params, SIZE_FOR_TIMING))
    decreasing = all(later < earlier for earlier, later in zip(times, times[1:]))
    speedup = times[0] / times[-1]
    passed = decreasing and speedup >= MINIMUM_SPEEDUP_LOWEST_TO_HIGHEST
    parts = ", ".join(f"T {t:.0f} C (S = {s:.2f}): {time:.0f}" for t, s, time in zip(TEMPERATURES_CELSIUS, supersaturations, times))
    message = (
        f"Model time to grow to radius {SIZE_FOR_TIMING:.0f} cells (surface-limited regime): {parts}. Each higher supersaturation is faster: {decreasing}; "
        f"the highest is {speedup:.1f}x faster than the lowest (needs >= {MINIMUM_SPEEDUP_LOWEST_TO_HIGHEST})."
    )
    return CheckResult("higher supersaturation gives faster growth", passed, message)


def compute_solidity(phase_field: np.ndarray) -> float:
    """Return crystal area / area of its convex hull (1 = compact; lower = faces caving in or branches)."""
    rows, columns = np.nonzero(phase_field > 0.5)
    if len(rows) < 4:
        return float("nan")
    centres = np.column_stack([columns, rows]).astype(float)
    corners = np.concatenate([centres + np.array([dx, dy]) for dx in (-0.5, 0.5) for dy in (-0.5, 0.5)])  # every cell as a unit square
    return float(len(centres) / ConvexHull(corners).volume)


def shape_at_supersaturation(material: MaterialConstants, tau: float, supersaturation: float) -> dict:
    """Grow a crystal in a fluid that starts at `supersaturation` (times the equilibrium) and return its solidity and facet share."""
    base = build_study_params(material, tau, solid_capacity=None, uniform=tau > 5.0)
    params = dataclasses.replace(base, initial_silica=supersaturation * base.equilibrium_silica)
    state = create_initial_state(params)
    steps, in_place = 0, params.diffusion_scheme == "explicit"
    while compute_equivalent_radius(state.phase_field) < SIZE_FOR_SHAPE and steps < MAXIMUM_STEPS:
        for _ in range(STEPS_BETWEEN_SIZE_CHECKS):
            state = advance_one_step(state, params, None, in_place=in_place)
            steps += 1
    return {"solidity": compute_solidity(state.phase_field), "facet_fraction": compute_facet_fraction(state.phase_field, material.r_pole_angle_to_c_degrees), "steps": steps}


def report_facet_destabilisation(material: MaterialConstants) -> list[CheckResult]:
    """Test B (reported, not judged): solidity against supersaturation, in the diffusion-limited and the surface-limited regime."""
    results = []
    for tau in HIGH_SUPERSATURATION_TAUS:
        rows = [shape_at_supersaturation(material, tau, s) for s in SUPERSATURATIONS]
        solidities = [row["solidity"] for row in rows]
        loss = solidities[0] - min(solidities)
        observed = loss >= MIN_SOLIDITY_LOSS_TO_CALL_IT_OBSERVED
        regime = "diffusion-limited (tau 1)" if tau == 1.0 else f"surface-limited (tau {tau:.0f})"
        parts = ", ".join(f"S {s:g}: solidity {row['solidity']:.3f} / facets {row['facet_fraction']:.2f}" for s, row in zip(SUPERSATURATIONS, rows))
        message = (
            f"[{regime}] {parts}. Loss of solidity from the lowest S to the worst: {loss:.3f}; "
            f"facet destabilisation {'OBSERVED' if observed else 'NOT observed'} in this range (threshold {MIN_SOLIDITY_LOSS_TO_CALL_IT_OBSERVED}). Reported only."
        )
        results.append(CheckResult(f"[reported] facet destabilisation at very high supersaturation, {regime}", True, message, informational=True))
    return results


def run_qualitative_check(material: MaterialConstants) -> list[CheckResult]:
    """Run all tests of validation check 7."""
    return [check_growth_speed_rises_with_supersaturation(material), *report_facet_destabilisation(material)]
