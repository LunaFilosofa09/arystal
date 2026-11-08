"""Validation check 6: the fast (Numba) kernels give the same results as the readable reference code.

For several scenarios (isotropic, faceted with iron and noise, dissolution with iron release, and a long run) both
implementations start from the same state, receive the same random numbers and advance step by step. Compared:
every field after ONE step (differences can only be rounding) and after MANY steps (rounding must not grow), the
conservation of silica and iron by the fast code, and that the number of CPU threads does not change the result.

WHAT THIS DOES NOT SHOW: that the physics is right (checks 1-4 and 7 address that); only that the fast code computes the
same thing as the reference.
"""

import dataclasses
import time

import numpy as np

from arystal.engine.anisotropy import create_facet_anisotropy_from_material
from arystal.engine.fast_step import set_thread_count
from arystal.engine.material_constants import MaterialConstants
from arystal.engine.solution_growth import advance_one_step, compute_total_iron, compute_total_silica, create_initial_state
from arystal.engine.solution_params import SolutionParams, create_solution_params
from arystal.validation.check_result import CheckResult

LIMITS_NOTE = "Limits: this only shows the fast code equals the reference code (to rounding); it does not validate the physics."

FIELDS = ("phase_field", "silica", "iron", "crystal_iron", "sector_iron", "sector_silica")
GRID_WIDTH = 120
GRID_HEIGHT = 60
ONE_STEP_TOLERANCE = 1e-13   # relative to the largest value of the field: only rounding is allowed after one step
MANY_STEPS = 3000
MANY_STEPS_TOLERANCE = 1e-9  # rounding differences must not grow
CONSERVATION_TOLERANCE = 1e-9
SPEED_TEST_GRID = (400, 200)
SPEED_TEST_STEPS = 30

# (name, run temperature, saturation temperature, anisotropy, iron, noise)
SCENARIOS = [
    ("isotropic growth, no iron", 40.0, 60.0, False, None, 0.0),
    ("faceted growth with iron and noise", 20.0, 60.0, True, 1.0, 0.02),
    ("dissolution with iron release", 60.0, 30.0, True, 1.0, 0.02),
]


def build_params(material: MaterialConstants, scenario: tuple, backend: str) -> SolutionParams:
    """Return the parameters of a scenario for one backend."""
    _, run, saturation, aniso, iron, noise = scenario
    return create_solution_params(
        material, run, saturation, grid_width=GRID_WIDTH, grid_height=GRID_HEIGHT, seed_radius=12.0,
        anisotropy=create_facet_anisotropy_from_material(material) if aniso else None, iron_ppm=iron,
        noise_amplitude=noise, backend=backend,
    )


def relative_difference(reference: np.ndarray, other: np.ndarray) -> float:
    """Return the largest |difference| divided by the largest |value| of the reference (0 if the field is all zero)."""
    scale = float(np.abs(reference).max())
    return float(np.abs(reference - other).max() / scale) if scale > 0 else float(np.abs(other).max())


def largest_field_difference(first, second) -> tuple[float, str]:
    """Return (largest relative difference over all fields, name of the field where it happens)."""
    worst = max(((relative_difference(getattr(first, name), getattr(second, name)), name) for name in FIELDS))
    return worst


def run_both(material: MaterialConstants, scenario: tuple, steps: int, in_place: bool = False) -> dict:
    """Advance both implementations `steps` steps with the same random numbers; return what is needed to compare them.

    With `in_place` the fast code updates the crystal arrays directly (as the run controller does); it then needs its own copy of the starting state.
    """
    reference_params = build_params(material, scenario, "reference")
    fast_params = dataclasses.replace(reference_params, backend="numba")
    rng = np.random.default_rng(7)
    reference, fast = create_initial_state(reference_params), create_initial_state(reference_params)
    initial_silica, initial_iron = compute_total_silica(reference, reference_params), compute_total_iron(reference)
    first_step_difference = (0.0, "")
    for step in range(steps):
        noise = rng.standard_normal(reference.silica.shape)
        reference = advance_one_step(reference, reference_params, noise)
        fast = advance_one_step(fast, fast_params, noise, in_place=in_place)
        if step == 0:
            first_step_difference = largest_field_difference(reference, fast)
    return {
        "one_step": first_step_difference, "many_steps": largest_field_difference(reference, fast),
        "silica_drift": abs(compute_total_silica(fast, fast_params) - initial_silica) / initial_silica,
        "iron_drift": abs(compute_total_iron(fast) - initial_iron) / initial_iron if initial_iron > 0 else 0.0,
        "area_change": float((fast.phase_field > 0.5).sum() - (create_initial_state(fast_params).phase_field > 0.5).sum()),
    }


def check_scenario(material: MaterialConstants, scenario: tuple, in_place: bool = False) -> CheckResult:
    """Compare the two implementations in one scenario."""
    result = run_both(material, scenario, MANY_STEPS, in_place)
    one, one_name = result["one_step"]
    many, many_name = result["many_steps"]
    passed = (
        one <= ONE_STEP_TOLERANCE and many <= MANY_STEPS_TOLERANCE
        and result["silica_drift"] <= CONSERVATION_TOLERANCE and result["iron_drift"] <= CONSERVATION_TOLERANCE
    )
    message = (
        f"After 1 step the largest relative difference is {one:.1e} ({one_name}; limit {ONE_STEP_TOLERANCE:.0e}); after {MANY_STEPS} steps {many:.1e} "
        f"({many_name}; limit {MANY_STEPS_TOLERANCE:.0e}); the fast code conserves silica to {result['silica_drift']:.1e} and iron to {result['iron_drift']:.1e} "
        f"(limit {CONSERVATION_TOLERANCE:.0e}); crystal area changed by {result['area_change']:+.0f} cells."
    )
    return CheckResult(f"fast = reference: {scenario[0]}{' (in-place update)' if in_place else ''}", passed, message)


def check_thread_independence(material: MaterialConstants) -> CheckResult:
    """The result must not depend on how many CPU threads are used."""
    scenario = SCENARIOS[1]
    params = build_params(material, scenario, "numba")
    finals = []
    for threads in (1, 4):
        set_thread_count(threads)
        rng = np.random.default_rng(3)
        state = create_initial_state(params)
        for _ in range(500):
            state = advance_one_step(state, params, rng.standard_normal(state.silica.shape))
        finals.append(state)
    set_thread_count(1)
    identical = all(np.array_equal(getattr(finals[0], name), getattr(finals[1], name)) for name in FIELDS)
    return CheckResult("the number of threads does not change the result", identical, f"500 steps with 1 thread and with 4 threads are identical bit for bit: {identical}.")


def measure_speed(material: MaterialConstants) -> CheckResult:
    """Report the speed of both implementations on a larger grid (informational: it passes unless the fast code is not faster)."""
    scenario = SCENARIOS[1]
    width, height = SPEED_TEST_GRID
    reference_params = dataclasses.replace(build_params(material, scenario, "reference"), grid_width=width, grid_height=height)
    fast_params = dataclasses.replace(reference_params, backend="numba")
    state = create_initial_state(reference_params)
    noise = np.random.default_rng(0).standard_normal(state.silica.shape)
    advance_one_step(state, fast_params, noise)  # compile outside the timing
    timings = {}
    for name, params in (("reference", reference_params), ("numba (1 thread)", fast_params)):
        started = time.perf_counter()
        current = state
        for _ in range(SPEED_TEST_STEPS):
            current = advance_one_step(current, params, noise)
        timings[name] = 1000 * (time.perf_counter() - started) / SPEED_TEST_STEPS
    speedup = timings["reference"] / timings["numba (1 thread)"]
    message = f"On a {width}x{height} grid with iron, anisotropy and noise: reference {timings['reference']:.1f} ms/step, fast {timings['numba (1 thread)']:.1f} ms/step: x{speedup:.1f} faster."
    return CheckResult("the fast code is faster", speedup > 1.0, message)


def run_fast_vs_reference_check(material: MaterialConstants) -> list[CheckResult]:
    """Run all tests of validation check 6."""
    set_thread_count(1)
    results = [check_scenario(material, scenario) for scenario in SCENARIOS]
    results.append(check_scenario(material, SCENARIOS[2], in_place=True))
    results.append(check_thread_independence(material))
    results.append(measure_speed(material))
    return results
