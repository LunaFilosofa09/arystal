"""Validation of the iron model: conservation and sector zoning.

Tests:
  A. Iron conservation: dissolved + locked-in iron stays constant while the crystal grows and
     while it dissolves, and the dissolved iron never becomes negative.
  B. Sector zoning: with round (isotropic) growth the surface normal points like the polar angle
     from the seed, so the crystal records the iron coefficient of each direction as concentric
     sectors. The Fe/Si ratio measured in the m, r and z directions must follow the ratios of the
     coefficients set in the material file.

WHAT THESE TESTS DO NOT SHOW: that real amethyst has these coefficients (ASSUMED; only the order
r > z > m is supported, qualitatively, by Cohen & Hassan 1974 and Troilo et al. 2015), that the
colour law is right, or that iron is a passive trace in a real geode. They check that the code
does what its equations say.
"""

import dataclasses
import math

import numpy as np

from arystal.engine.iron_partition import compute_partition_from_angle
from arystal.engine.material_constants import MaterialConstants
from arystal.engine.solubility import compute_equilibrium_concentration
from arystal.engine.solution_growth import advance_one_step, compute_total_iron, create_initial_state
from arystal.engine.solution_params import SolutionParams, create_solution_params
from arystal.engine.silica_transport import compute_solid_fraction
from arystal.simulation.solution_run import SolutionSnapshot, iterate_solution_growth
from arystal.storage.rendering import compute_crystal_iron_ratio
from arystal.validation.check_result import CheckResult

LIMITS_NOTE = (
    "Limits: these tests check the code against its own equations. The incorporation coefficients are ASSUMED "
    "(only the order r > z > m is supported by literature, qualitatively); the colour law is an assumption."
)

TEST_IRON_PPM = 1.0

# Small grid and short runs so the checks take about a minute.
GRID_WIDTH = 240
GRID_HEIGHT = 120
SEED_RADIUS = 12.0
STEPS_PER_SNAPSHOT = 500

# Test A
CONSERVATION_DURATION = 2000.0
MAX_IRON_DRIFT = 1e-9
CONSERVATION_SCENARIOS = [
    ("growth (supersaturated fluid)", 40.0, 60.0),
    ("dissolution (undersaturated fluid)", 60.0, 30.0),
]

# Test A3: grow, then raise the temperature so the crystal dissolves and must give its iron back.
RELEASE_GROWTH_STEPS = 10000
RELEASE_DISSOLUTION_STEPS = 10000
RELEASE_HOT_CELSIUS = 60.0
MINIMUM_IRON_RELEASED_FRACTION = 0.05  # at least this share of the locked-in iron must be given back

# Test B: strongly supersaturated, isotropic growth, long enough for a crystal of ~40 cells radius.
SECTOR_RUN_CELSIUS = 15.0
SECTOR_SATURATION_CELSIUS = 60.0
SECTOR_DURATION = 3000.0
SECTOR_HALF_WIDTH_DEGREES = 5.0
M_SECTOR_HALF_WIDTH_DEGREES = 8.0
INNER_MARGIN_CELLS = 4.0   # ignore the seed itself, which holds no iron
OUTER_MARGIN_CELLS = 3.0   # ignore the surface layer, which is still changing
SOLID_THRESHOLD = 0.9      # only cells that are firmly crystal
MAX_R_OVER_Z_ERROR = 0.15
MAX_R_OVER_M_ERROR = 0.35


def build_params(
    material: MaterialConstants, run_celsius: float, saturation_celsius: float
) -> SolutionParams:
    """Return the parameters of a small run with iron and round (isotropic) growth."""
    return create_solution_params(
        material, run_celsius, saturation_celsius, grid_width=GRID_WIDTH, grid_height=GRID_HEIGHT,
        seed_radius=SEED_RADIUS, iron_ppm=TEST_IRON_PPM,
    )


def check_iron_conservation(material: MaterialConstants, name: str, run_celsius: float, saturation_celsius: float) -> CheckResult:
    """Test A for one scenario."""
    params = build_params(material, run_celsius, saturation_celsius)
    snapshots = list(iterate_solution_growth(params, STEPS_PER_SNAPSHOT, CONSERVATION_DURATION))
    initial = snapshots[0].total_iron
    drift = max(abs(s.total_iron - initial) / initial for s in snapshots)
    lowest = min(s.minimum_iron for s in snapshots)
    locked = snapshots[-1].crystal_iron.sum() / initial
    message = (
        f"Total iron changed by at most {drift:.1e} (relative; limit {MAX_IRON_DRIFT:.0e}); lowest dissolved iron "
        f"{lowest:.2e} mol/kg (must be >= 0); {100 * locked:.3f}% of all iron ends up locked in the crystal."
    )
    return CheckResult(f"iron conserved: {name}", drift <= MAX_IRON_DRIFT and lowest >= 0.0, message)


def check_iron_release_on_dissolution(material: MaterialConstants) -> CheckResult:
    """Test A3: iron locked into the crystal is returned to the fluid, and conserved, when the crystal dissolves."""
    params = build_params(material, 40.0, 60.0)
    state = create_initial_state(params)
    initial_total = compute_total_iron(state)
    for _ in range(RELEASE_GROWTH_STEPS):
        state = advance_one_step(state, params)
    locked_before = float(state.crystal_iron.sum())
    hot = dataclasses.replace(
        params, temperature_celsius=RELEASE_HOT_CELSIUS,
        equilibrium_silica=compute_equilibrium_concentration(material, RELEASE_HOT_CELSIUS),
    )
    for _ in range(RELEASE_DISSOLUTION_STEPS):
        state = advance_one_step(state, hot)
    locked_after = float(state.crystal_iron.sum())
    drift = abs(compute_total_iron(state) - initial_total) / initial_total
    released = (locked_before - locked_after) / locked_before
    passed = drift <= MAX_IRON_DRIFT and released >= MINIMUM_IRON_RELEASED_FRACTION and state.iron.min() >= 0.0
    message = (
        f"After growing, the crystal held {100 * locked_before / initial_total:.3f}% of all iron; after heating to {RELEASE_HOT_CELSIUS:.0f} C "
        f"it gave back {100 * released:.1f}% of it (needs >= {100 * MINIMUM_IRON_RELEASED_FRACTION:.0f}%); total iron changed by {drift:.1e} "
        f"(limit {MAX_IRON_DRIFT:.0e}). This exercises the release branch that the plain dissolution scenario does not."
    )
    return CheckResult("iron is returned to the fluid when the crystal dissolves", passed, message)


def compute_polar_angle_degrees(shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """Return (polar angle in degrees, distance in cells) of every cell as seen from the seed centre on the wall."""
    rows, columns = np.mgrid[0:shape[0], 0:shape[1]]
    x = columns - (shape[1] - 1) / 2.0
    y = rows + 0.5
    return np.degrees(np.arctan2(y, x)), np.hypot(x, y)


def collect_sector_ratios(snapshot: SolutionSnapshot, params: SolutionParams, r_angle: float) -> dict[str, float]:
    """Return the mean crystal Fe/Si ratio in the m, r and z directions (r_angle: direction of the r normal, degrees)."""
    angle, distance = compute_polar_angle_degrees(snapshot.phase_field.shape)
    solid = compute_solid_fraction(snapshot.phase_field)
    ratio = compute_crystal_iron_ratio(snapshot.crystal_iron, solid, params.solid_capacity)
    radius = float(np.sqrt(2.0 * snapshot.crystal_area / math.pi))
    usable = (solid > SOLID_THRESHOLD) & (distance > SEED_RADIUS + INNER_MARGIN_CELLS) & (distance < radius - OUTER_MARGIN_CELLS)
    return {
        "m": float(ratio[usable & ((angle < M_SECTOR_HALF_WIDTH_DEGREES) | (angle > 180 - M_SECTOR_HALF_WIDTH_DEGREES))].mean()),
        "r": float(ratio[usable & (np.abs(angle - r_angle) < SECTOR_HALF_WIDTH_DEGREES)].mean()),
        "z": float(ratio[usable & (np.abs(angle - (180.0 - r_angle)) < SECTOR_HALF_WIDTH_DEGREES)].mean()),
    }


def predict_coefficient(params: SolutionParams, centre_degrees: float, half_width_degrees: float) -> float:
    """Return the mean incorporation coefficient over a range of surface-normal angles."""
    angles = np.radians(np.linspace(centre_degrees - half_width_degrees, centre_degrees + half_width_degrees, 21))
    return float(compute_partition_from_angle(angles, params.sector_partition).mean())


def check_sector_zoning(material: MaterialConstants) -> CheckResult:
    """Test B: Fe/Si of the sectors follows the coefficient ratios."""
    params = build_params(material, SECTOR_RUN_CELSIUS, SECTOR_SATURATION_CELSIUS)
    snapshot = list(iterate_solution_growth(params, STEPS_PER_SNAPSHOT, SECTOR_DURATION))[-1]
    r_angle = 90.0 - material.r_pole_angle_to_c_degrees
    ratios = collect_sector_ratios(snapshot, params, r_angle)
    expected = {
        "m": 0.5 * (predict_coefficient(params, 4.0, M_SECTOR_HALF_WIDTH_DEGREES) + predict_coefficient(params, 176.0, M_SECTOR_HALF_WIDTH_DEGREES)),
        "r": predict_coefficient(params, r_angle, SECTOR_HALF_WIDTH_DEGREES),
        "z": predict_coefficient(params, 180.0 - r_angle, SECTOR_HALF_WIDTH_DEGREES),
    }
    r_over_z = ratios["r"] / ratios["z"]
    r_over_m = ratios["r"] / ratios["m"]
    r_over_z_error = abs(r_over_z / (expected["r"] / expected["z"]) - 1.0)
    r_over_m_error = abs(r_over_m / (expected["r"] / expected["m"]) - 1.0)
    passed = r_over_z_error <= MAX_R_OVER_Z_ERROR and r_over_m_error <= MAX_R_OVER_M_ERROR
    message = (
        f"Crystal Fe/Si (mol/mol): m {ratios['m']:.2e}, r {ratios['r']:.2e}, z {ratios['z']:.2e}. "
        f"r/z = {r_over_z:.2f} (coefficients say {expected['r'] / expected['z']:.2f}, {100 * r_over_z_error:.0f}% off, limit {100 * MAX_R_OVER_Z_ERROR:.0f}%); "
        f"r/m = {r_over_m:.2f} (coefficients say {expected['r'] / expected['m']:.2f}, {100 * r_over_m_error:.0f}% off, limit {100 * MAX_R_OVER_M_ERROR:.0f}%). "
        "The deviation comes from the local fluid Fe/Si at the surface, which is not exactly the same in every direction."
    )
    return CheckResult("iron sectors follow the incorporation coefficients", passed, message)


def run_iron_check(material: MaterialConstants) -> list[CheckResult]:
    """Run all tests of the iron check."""
    results = [check_iron_conservation(material, *scenario) for scenario in CONSERVATION_SCENARIOS]
    results.append(check_iron_release_on_dissolution(material))
    results.append(check_sector_zoning(material))
    return results
