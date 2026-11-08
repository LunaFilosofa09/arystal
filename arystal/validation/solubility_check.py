"""Validation check 4: the implemented solubility curve reproduces its source.

Honest limits: the original paper of Rimstidt (1997) was not read. The equation was read in
Takeno et al. (2000), eq. (3), which quotes it, and Verma's paper quotes its value at 25 C. This
check tests the implementation against those verified statements, plus physical sanity tests.
"""

from arystal.engine.material_constants import MaterialConstants
from arystal.engine.solubility import (
    compute_dissolution_enthalpy_kj_per_mol,
    compute_equilibrium_concentration,
    convert_concentration_to_ppm,
)
from arystal.validation.check_result import CheckResult

# Rimstidt (1997) value at 25 C as quoted by Verma (read in full): 11.0 +/- 1.1 ppm SiO2.
ROOM_TEMPERATURE_CELSIUS = 25.0
ROOM_TEMPERATURE_PPM = 11.0
ROOM_TEMPERATURE_PPM_UNCERTAINTY = 1.1

# Range of 25 C values that Verma lists as acceptable within analytical errors (6.6 to 12 ppm).
LITERATURE_PPM_LOW = 6.6
LITERATURE_PPM_HIGH = 12.0

# Dissolution enthalpy implied by the thermodynamic data in the same Rimstidt paper
# (dHf of H4SiO4(aq) = -1460.913 kJ/mol, as seen in a search summary) combined with textbook
# values dHf quartz = -910.7 and dHf water(l) = -285.83 kJ/mol, for SiO2 + 2 H2O = H4SiO4.
EXPECTED_ENTHALPY_KJ_PER_MOL = -1460.913 + 910.7 + 2 * 285.83
ENTHALPY_TOLERANCE_FRACTION = 0.03

TEMPERATURES_FOR_MONOTONIC_TEST = [0.0, 15.0, 25.0, 40.0, 60.0, 100.0, 200.0, 300.0]


# Equation exactly as printed in Takeno et al. (2000), eq. (3): log K = -0.0254 - 1107.12 / T (T in kelvin).
PRINTED_A = -1107.12
PRINTED_B = -0.0254
TEMPERATURES_FOR_PRINTED_EQUATION = [0.0, 15.0, 25.0, 60.0, 150.0, 300.0]
MAX_PRINTED_EQUATION_DIFFERENCE = 1e-12


def check_matches_printed_equation(material: MaterialConstants) -> CheckResult:
    """Does the implementation reproduce the equation as printed in the source (no transcription error)?"""
    worst = 0.0
    for temperature in TEMPERATURES_FOR_PRINTED_EQUATION:
        printed = 10.0 ** (PRINTED_A / (temperature + 273.15) + PRINTED_B)
        implemented = compute_equilibrium_concentration(material, temperature)
        worst = max(worst, abs(implemented - printed) / printed)
    message = f"Largest relative difference from the printed equation over {len(TEMPERATURES_FOR_PRINTED_EQUATION)} temperatures: {worst:.1e}."
    return CheckResult("matches the equation printed in Takeno et al. (2000), eq. 3", worst <= MAX_PRINTED_EQUATION_DIFFERENCE, message)


def check_value_at_room_temperature(material: MaterialConstants) -> CheckResult:
    """Does the curve give 11.0 +/- 1.1 ppm at 25 C, the verified value from the source?"""
    concentration = compute_equilibrium_concentration(material, ROOM_TEMPERATURE_CELSIUS)
    ppm = convert_concentration_to_ppm(material, concentration)
    error = abs(ppm - ROOM_TEMPERATURE_PPM)
    message = f"Curve gives {ppm:.2f} ppm at 25 C; source says {ROOM_TEMPERATURE_PPM} +/- {ROOM_TEMPERATURE_PPM_UNCERTAINTY} ppm."
    return CheckResult("matches the source value at 25 C", error <= ROOM_TEMPERATURE_PPM_UNCERTAINTY, message)


def check_inside_literature_spread(material: MaterialConstants) -> CheckResult:
    """Is the 25 C value inside the range (6.6-12 ppm) that different authors report?"""
    concentration = compute_equilibrium_concentration(material, ROOM_TEMPERATURE_CELSIUS)
    ppm = convert_concentration_to_ppm(material, concentration)
    passed = LITERATURE_PPM_LOW <= ppm <= LITERATURE_PPM_HIGH
    message = (
        f"{ppm:.2f} ppm; literature spread at 25 C is {LITERATURE_PPM_LOW}-{LITERATURE_PPM_HIGH} ppm "
        "(Fournier & Potter 6.6, older work 12, Rimstidt 11.0). The model is therefore uncertain by up to ~40% in c_eq."
    )
    return CheckResult("inside the literature spread at 25 C", passed, message)


def check_increases_with_temperature(material: MaterialConstants) -> CheckResult:
    """Does solubility rise with temperature (so that cooling creates supersaturation)?"""
    values = [compute_equilibrium_concentration(material, t) for t in TEMPERATURES_FOR_MONOTONIC_TEST]
    passed = all(later > earlier for earlier, later in zip(values, values[1:]))
    message = f"Solubility from 0 to 300 C rises from {values[0]:.2e} to {values[-1]:.2e} mol/kg, strictly increasing: {passed}."
    return CheckResult("solubility increases with temperature", passed, message)


def check_enthalpy_consistency(material: MaterialConstants) -> CheckResult:
    """Does the slope of the curve agree with the thermodynamic data of the same paper?"""
    enthalpy = compute_dissolution_enthalpy_kj_per_mol(material)
    error = abs(enthalpy - EXPECTED_ENTHALPY_KJ_PER_MOL) / abs(EXPECTED_ENTHALPY_KJ_PER_MOL)
    message = (
        f"Curve slope implies {enthalpy:.1f} kJ/mol; enthalpies of formation give "
        f"{EXPECTED_ENTHALPY_KJ_PER_MOL:.1f} kJ/mol; difference {100 * error:.1f}% "
        f"(limit {100 * ENTHALPY_TOLERANCE_FRACTION:.0f}%)."
    )
    return CheckResult("curve slope matches thermodynamic data", error <= ENTHALPY_TOLERANCE_FRACTION, message)


def check_range_is_enforced(material: MaterialConstants) -> CheckResult:
    """Does the code refuse temperatures where the curve is not valid?"""
    refused = 0
    for outside in (material.solubility_min_celsius - 1.0, material.solubility_max_celsius + 1.0):
        try:
            compute_equilibrium_concentration(material, outside)
        except ValueError:
            refused += 1
    return CheckResult("refuses temperatures outside the valid range", refused == 2, f"{refused} of 2 out-of-range temperatures refused.")


def run_solubility_check(material: MaterialConstants) -> list[CheckResult]:
    """Run all tests of validation check 4."""
    return [
        check_matches_printed_equation(material),
        check_value_at_room_temperature(material),
        check_inside_literature_spread(material),
        check_increases_with_temperature(material),
        check_enthalpy_consistency(material),
        check_range_is_enforced(material),
    ]
