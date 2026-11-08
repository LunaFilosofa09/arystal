"""Validation check 4b: the pH-dependent quartz rate law reproduces its source and changes only the real time.

Honest limits: the check compares the code with the numbers printed in Palandri & Kharaka (2004), Table 4 and eq. (6). It does not
show that the base term applies to growth (it was measured for dissolution), which of the two possible base constants is right, or what
the pH of geode fluids was (docs/kinetic_regime.md, section 10).
"""

import math

import numpy as np

from arystal.engine.material_constants import MaterialConstants
from arystal.engine.ph_rate_law import compute_base_rate_constant, compute_neutral_rate_constant
from arystal.engine.solution_growth import advance_one_step, create_initial_state
from arystal.engine.solution_params import create_solution_params
from arystal.engine.time_scaling import compute_kinetic_seconds_per_model_time, compute_quartz_rate_constant
from arystal.validation.check_result import CheckResult

LIMITS_NOTE = (
    "Limits: this shows the code equals the printed law and that pH only changes the real-time conversion; it does not show that the base term "
    "applies to quartz growth or which base constant (-16.29 or -17.98) is right."
)

# Numbers printed in Palandri & Kharaka (2004), Table 4 (read on the rendered page).
PRINTED_NEUTRAL_LOG10_K25 = -13.40
PRINTED_BASE_LOG10_K25 = -16.29
PRINTED_BASE_ORDER = -0.5
ROOM_TEMPERATURE_CELSIUS = 25.0

# Takeno et al. (2000), eq. (6), as printed: log10 k+ = -0.7324 - 3705.12 / T.
TAKENO_A = -0.7324
TAKENO_B = -3705.12
TEMPERATURES_CELSIUS = [15.0, 25.0, 40.0, 60.0]
PH_VALUES = [7.0, 8.0, 9.0, 10.0]
ALKALINE_PH = 10.0

TOLERANCE = 1e-12
SHAPE_TEST_STEPS = 200
SHAPE_TEST_GRID = (60, 40)
SHAPE_TEST_SEED_RADIUS = 8.0
SHAPE_TEST_RUN_CELSIUS = 20.0
SHAPE_TEST_SATURATION_CELSIUS = 60.0
SHAPE_TEST_SUPERSATURATION = 2.0


def check_neutral_term_at_25_celsius(material: MaterialConstants) -> CheckResult:
    """Does the neutral term give the printed log k = -13.40 at 25 C?"""
    value = math.log10(compute_neutral_rate_constant(material, ROOM_TEMPERATURE_CELSIUS))
    passed = abs(value - PRINTED_NEUTRAL_LOG10_K25) < TOLERANCE
    return CheckResult("neutral term equals Table 4 at 25 C", passed, f"log10 k = {value:.4f}; printed {PRINTED_NEUTRAL_LOG10_K25}.")


def check_base_term_at_25_celsius_ph_0(material: MaterialConstants) -> CheckResult:
    """Does the base term give the printed log k = -16.29 at 25 C and pH 0?"""
    value = math.log10(compute_base_rate_constant(material, ROOM_TEMPERATURE_CELSIUS, 0.0))
    passed = abs(value - PRINTED_BASE_LOG10_K25) < TOLERANCE
    return CheckResult("base term equals Table 4 at 25 C, pH 0", passed, f"log10 k = {value:.4f}; printed {PRINTED_BASE_LOG10_K25}.")


def check_base_term_slope(material: MaterialConstants) -> CheckResult:
    """Does the base term rise by 0.5 log units per pH unit (order -0.5 in H+)?"""
    logs = [math.log10(compute_base_rate_constant(material, ROOM_TEMPERATURE_CELSIUS, ph)) for ph in PH_VALUES]
    slopes = [later - earlier for earlier, later in zip(logs, logs[1:])]
    passed = all(abs(slope + PRINTED_BASE_ORDER) < TOLERANCE for slope in slopes)
    return CheckResult("base term: 0.5 log units per pH unit", passed, f"slopes between pH 7 and 10: {', '.join(f'{s:.4f}' for s in slopes)}.")


def check_no_ph_keeps_takeno_law(material: MaterialConstants) -> CheckResult:
    """Without a pH, is the rate constant still exactly the Takeno law (so old runs are unchanged)?"""
    worst = 0.0
    for temperature in TEMPERATURES_CELSIUS:
        printed = 10.0 ** (TAKENO_A + TAKENO_B / (temperature + 273.15))
        worst = max(worst, abs(compute_quartz_rate_constant(material, temperature) / printed - 1.0))
    return CheckResult("no pH: Takeno law unchanged", worst < TOLERANCE, f"largest relative difference at 15-60 C: {worst:.1e}.")


def grow_small_crystal(material: MaterialConstants, fluid_ph: float | None) -> tuple[np.ndarray, object]:
    """Grow a small crystal for a few steps and return (phase field, parameters)."""
    params = create_solution_params(
        material, SHAPE_TEST_RUN_CELSIUS, SHAPE_TEST_SATURATION_CELSIUS, grid_width=SHAPE_TEST_GRID[0], grid_height=SHAPE_TEST_GRID[1],
        seed_radius=SHAPE_TEST_SEED_RADIUS, fluid_ph=fluid_ph,
    )
    state = create_initial_state(params)
    for _ in range(SHAPE_TEST_STEPS):
        state = advance_one_step(state, params, None)
    return state.phase_field, params


def check_ph_changes_only_real_time(material: MaterialConstants) -> CheckResult:
    """Is the simulated crystal identical with and without pH, while the real time per model unit is shorter at pH 10?"""
    neutral_field, neutral_params = grow_small_crystal(material, None)
    alkaline_field, alkaline_params = grow_small_crystal(material, ALKALINE_PH)
    identical = bool(np.array_equal(neutral_field, alkaline_field))
    neutral_seconds = compute_kinetic_seconds_per_model_time(material, neutral_params, SHAPE_TEST_SUPERSATURATION)
    alkaline_seconds = compute_kinetic_seconds_per_model_time(material, alkaline_params, SHAPE_TEST_SUPERSATURATION)
    speed_up = neutral_seconds / alkaline_seconds
    message = f"phase fields identical: {identical}; at {SHAPE_TEST_RUN_CELSIUS:g} C, pH {ALKALINE_PH:g} makes real time {speed_up:.1f}x shorter than the Takeno law."
    return CheckResult("pH changes only the real time, not the crystal", identical and speed_up > 1.0, message)


def check_ph_out_of_range_is_refused(material: MaterialConstants) -> CheckResult:
    """Is a pH outside the range of the material file refused?"""
    try:
        create_solution_params(material, SHAPE_TEST_RUN_CELSIUS, SHAPE_TEST_SATURATION_CELSIUS, fluid_ph=material.fluid_ph_max + 1.0)
    except ValueError as error:
        return CheckResult("pH outside the allowed range is refused", True, str(error))
    return CheckResult("pH outside the allowed range is refused", False, "no error was raised")


def run_ph_rate_check(material: MaterialConstants) -> list[CheckResult]:
    """Run all tests of the pH-dependent rate law."""
    return [
        check_neutral_term_at_25_celsius(material), check_base_term_at_25_celsius_ph_0(material), check_base_term_slope(material),
        check_no_ph_keeps_takeno_law(material), check_ph_changes_only_real_time(material), check_ph_out_of_range_is_refused(material),
    ]
