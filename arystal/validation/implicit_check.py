"""Validation of the implicit diffusion scheme (part of validation check 6, "fast vs reference").

The implicit scheme is a change of numerical scheme only, so it must give the same results as the explicit one wherever both are
feasible, conserve silica and iron exactly, and converge as the time step shrinks. Tests:
  A. Same results as the explicit scheme at the same (small) time step.
  B. Silica and iron are conserved to rounding.
  C. Time-step convergence: results hardly change between a small and a large implicit time step in a slow-kinetics run.
  D. A very large time step stays stable (no overshoot, no NaN) and keeps conserving.
  E. Dissolution with iron release works with the implicit scheme.
  F. The UNIFORM-fluid scheme (Da -> 0) gives the same crystal as the full implicit solution when growth is surface-limited, conserves exactly,
     and its fast kernel equals its reference implementation.

WHAT THIS DOES NOT SHOW: that the physics is right; only that the implicit scheme solves the same equations as the explicit one.
"""

import dataclasses

import numpy as np

from arystal.engine.anisotropy import create_facet_anisotropy_from_material
from arystal.engine.material_constants import MaterialConstants
from arystal.engine.solution_growth import advance_one_step, compute_total_iron, compute_total_silica, create_initial_state
from arystal.engine.solution_params import SolutionParams, create_solution_params
from arystal.metrics.growth_metrics import compute_face_distances
from arystal.validation.check_result import CheckResult

LIMITS_NOTE = "Limits: this only shows the implicit scheme equals the explicit one (and converges); it does not validate the physics."

GRID = (120, 60)
SMALL_STEP = 0.1
SAME_STEP_TIME = 40.0
MAX_AREA_DIFFERENCE = 0.005         # fraction, implicit vs explicit at the same step
MAX_FACE_DIFFERENCE_CELLS = 0.3
CONSERVATION_TOLERANCE = 1e-11
SLOW_TAU = 50.0
SLOW_TIME = 1500.0
SLOW_STEPS_TO_COMPARE = (1.0, 5.0)  # implicit steps compared with the explicit reference at SMALL_STEP
MAX_SLOW_AREA_DIFFERENCE = 0.01
HUGE_TAU = 500.0
HUGE_STEP = 50.0
HUGE_TIME = 5000.0


def build_params(material: MaterialConstants, scheme: str, time_step: float, tau: float, run: float = 20.0, saturation: float = 60.0, iron: float | None = 1.0) -> SolutionParams:
    """Return the parameters of a small test run."""
    return create_solution_params(
        material, run, saturation, grid_width=GRID[0], grid_height=GRID[1], seed_radius=12.0, iron_ppm=iron,
        anisotropy=create_facet_anisotropy_from_material(material), relaxation_time=tau, time_step=time_step, backend="numba", diffusion_scheme=scheme,
    )


def run_for(params: SolutionParams, model_time: float):
    """Advance a run for `model_time` and return (final state, relative silica drift, relative iron drift)."""
    state = create_initial_state(params)
    silica, iron = compute_total_silica(state, params), compute_total_iron(state)
    for _ in range(int(round(model_time / params.time_step))):
        state = advance_one_step(state, params)
    iron_drift = abs(compute_total_iron(state) - iron) / iron if iron > 0 else 0.0
    return state, abs(compute_total_silica(state, params) - silica) / silica, iron_drift


def area_of(state) -> float:
    """Crystal area in cells."""
    return float((state.phase_field > 0.5).sum())


def check_same_as_explicit(material: MaterialConstants) -> CheckResult:
    """Tests A and B."""
    explicit, _, _ = run_for(build_params(material, "explicit", SMALL_STEP, 1.0), SAME_STEP_TIME)
    implicit, silica_drift, iron_drift = run_for(build_params(material, "implicit", SMALL_STEP, 1.0), SAME_STEP_TIME)
    area_difference = abs(area_of(implicit) / area_of(explicit) - 1.0)
    faces = [compute_face_distances(state.phase_field, material.r_pole_angle_to_c_degrees) for state in (explicit, implicit)]
    face_difference = max(abs(faces[0][key] - faces[1][key]) for key in faces[0])
    field_difference = float(np.abs(explicit.phase_field - implicit.phase_field).max())
    passed = area_difference <= MAX_AREA_DIFFERENCE and face_difference <= MAX_FACE_DIFFERENCE_CELLS and silica_drift <= CONSERVATION_TOLERANCE and iron_drift <= CONSERVATION_TOLERANCE
    message = (
        f"Same time step {SMALL_STEP}: crystal area differs by {100 * area_difference:.3f}% (limit {100 * MAX_AREA_DIFFERENCE:.1f}%), face distances by {face_difference:.3f} cells "
        f"(limit {MAX_FACE_DIFFERENCE_CELLS}), largest difference of the phase field {field_difference:.1e}; implicit conserves silica to {silica_drift:.1e} and iron to {iron_drift:.1e} (limit {CONSERVATION_TOLERANCE:.0e})."
    )
    return CheckResult("implicit diffusion equals explicit diffusion at the same time step, and conserves", passed, message)


def check_time_step_convergence(material: MaterialConstants) -> CheckResult:
    """Test C."""
    reference, _, _ = run_for(build_params(material, "explicit", SMALL_STEP, SLOW_TAU, iron=None), SLOW_TIME)
    parts, worst = [], 0.0
    for step in SLOW_STEPS_TO_COMPARE:
        state, _, _ = run_for(build_params(material, "implicit", step, SLOW_TAU, iron=None), SLOW_TIME)
        difference = abs(area_of(state) / area_of(reference) - 1.0)
        worst = max(worst, difference)
        parts.append(f"dt {step}: {100 * difference:.3f}%")
    message = f"Slow kinetics (tau {SLOW_TAU:.0f}): crystal area of the implicit scheme vs the explicit reference ({SMALL_STEP}): " + "; ".join(parts) + f" (limit {100 * MAX_SLOW_AREA_DIFFERENCE:.0f}%)."
    return CheckResult("implicit results hardly depend on the time step", worst <= MAX_SLOW_AREA_DIFFERENCE, message)


def check_huge_step(material: MaterialConstants) -> CheckResult:
    """Test D."""
    state, silica_drift, iron_drift = run_for(build_params(material, "implicit", HUGE_STEP, HUGE_TAU), HUGE_TIME)
    phase = state.phase_field
    bounded = bool(np.isfinite(phase).all() and phase.min() > -0.05 and phase.max() < 1.05 and np.isfinite(state.silica).all() and state.silica.min() > 0)
    passed = bounded and silica_drift <= CONSERVATION_TOLERANCE and iron_drift <= CONSERVATION_TOLERANCE
    message = f"Time step {HUGE_STEP} (tau {HUGE_TAU:.0f}): fields finite and bounded: {bounded} (phase field {phase.min():.3f} to {phase.max():.3f}); silica drift {silica_drift:.1e}, iron drift {iron_drift:.1e}."
    return CheckResult("a very large implicit time step stays stable and conserving", passed, message)


def check_dissolution(material: MaterialConstants) -> CheckResult:
    """Test E."""
    params = build_params(material, "implicit", 0.1, 1.0, run=60.0, saturation=30.0)
    start = create_initial_state(params)
    state, silica_drift, iron_drift = run_for(params, 40.0)
    shrank = area_of(state) < area_of(start)
    passed = shrank and silica_drift <= CONSERVATION_TOLERANCE and iron_drift <= CONSERVATION_TOLERANCE
    message = f"Undersaturated fluid: crystal area {area_of(start):.0f} -> {area_of(state):.0f} cells (must shrink: {shrank}); silica drift {silica_drift:.1e}, iron drift {iron_drift:.1e}."
    return CheckResult("implicit scheme dissolves and conserves too", passed, message)


UNIFORM_TAU = 10000.0
UNIFORM_STEP_FRACTION = 0.1
UNIFORM_STEPS = 500
MAX_UNIFORM_AREA_DIFFERENCE = 0.01
MAX_UNIFORM_FACE_DIFFERENCE_CELLS = 0.5
MAX_BACKEND_DIFFERENCE = 1e-12


def check_uniform_scheme(material: MaterialConstants) -> CheckResult:
    """Test F."""
    step = UNIFORM_STEP_FRACTION * UNIFORM_TAU
    full, _, _ = run_for(build_params(material, "implicit", step, UNIFORM_TAU), UNIFORM_STEPS * step)
    uniform_params = build_params(material, "uniform", step, UNIFORM_TAU)
    uniform, silica_drift, iron_drift = run_for(uniform_params, UNIFORM_STEPS * step)
    reference, _, _ = run_for(dataclasses.replace(uniform_params, backend="reference"), UNIFORM_STEPS * step)
    area_difference = abs(area_of(uniform) / area_of(full) - 1.0)
    faces = [compute_face_distances(state.phase_field, material.r_pole_angle_to_c_degrees) for state in (full, uniform)]
    face_difference = max(abs(faces[0][key] - faces[1][key]) for key in faces[0])
    backend_difference = max(float(np.abs(getattr(uniform, name) - getattr(reference, name)).max() / max(np.abs(getattr(reference, name)).max(), 1e-300)) for name in ("phase_field", "silica", "iron", "crystal_iron", "sector_iron"))
    passed = (
        area_difference <= MAX_UNIFORM_AREA_DIFFERENCE and face_difference <= MAX_UNIFORM_FACE_DIFFERENCE_CELLS
        and silica_drift <= CONSERVATION_TOLERANCE and iron_drift <= CONSERVATION_TOLERANCE and backend_difference <= MAX_BACKEND_DIFFERENCE
    )
    message = (
        f"Surface-limited run (tau {UNIFORM_TAU:.0f}, {UNIFORM_STEPS} steps): the uniform-fluid crystal differs from the full implicit solution by {100 * area_difference:.3f}% in area "
        f"(limit {100 * MAX_UNIFORM_AREA_DIFFERENCE:.0f}%) and {face_difference:.3f} cells in the faces (limit {MAX_UNIFORM_FACE_DIFFERENCE_CELLS}); it conserves silica to {silica_drift:.1e} and iron to {iron_drift:.1e}; "
        f"fast kernel vs reference implementation of the uniform scheme: {backend_difference:.1e} (limit {MAX_BACKEND_DIFFERENCE:.0e})."
    )
    return CheckResult("uniform-fluid scheme equals the full solution when growth is surface-limited", passed, message)


def run_implicit_check(material: MaterialConstants) -> list[CheckResult]:
    """Run all tests of the implicit-scheme check."""
    return [check_same_as_explicit(material), check_time_step_convergence(material), check_huge_step(material), check_dissolution(material), check_uniform_scheme(material)]
