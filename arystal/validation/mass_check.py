"""Validation check 3: mass conservation.

The container is closed, so the total silica (dissolved + held by the crystal) must not change.
It is tested in two opposite situations: a supersaturated fluid (crystal grows) and an
undersaturated one (crystal dissolves). We also check that the concentration never becomes
negative, which would mean the model had invented silica somewhere to make the sums work.
"""

from arystal.engine.material_constants import MaterialConstants
from arystal.engine.solution_params import SolutionParams, create_solution_params
from arystal.simulation.solution_run import SolutionSnapshot, iterate_solution_growth
from arystal.validation.check_result import CheckResult

# Largest allowed relative change of the total silica over the whole run.
MAX_RELATIVE_DRIFT = 1e-9

# Small domain and short run so the check takes seconds.
CHECK_GRID_WIDTH = 200
CHECK_GRID_HEIGHT = 100
CHECK_DURATION = 2000.0
CHECK_STEPS_PER_SNAPSHOT = 500
CHECK_SEED_RADIUS = 12.0

# (name, run temperature C, temperature C at which the fluid was saturated)
SCENARIOS = [
    ("growth (supersaturated fluid)", 40.0, 60.0),
    ("dissolution (undersaturated fluid)", 60.0, 30.0),
]


def build_scenario_params(material: MaterialConstants, run_celsius: float, saturation_celsius: float) -> SolutionParams:
    """Return the parameters of one small test scenario."""
    return create_solution_params(
        material,
        temperature_celsius=run_celsius,
        saturation_temperature_celsius=saturation_celsius,
        grid_width=CHECK_GRID_WIDTH,
        grid_height=CHECK_GRID_HEIGHT,
        seed_radius=CHECK_SEED_RADIUS,
    )


def compute_max_relative_drift(snapshots: list[SolutionSnapshot]) -> float:
    """Return the largest |total silica - initial total silica| / initial total silica."""
    initial = snapshots[0].total_silica
    return max(abs(s.total_silica - initial) / initial for s in snapshots)


def compute_area_change_fraction(snapshots: list[SolutionSnapshot], params: SolutionParams) -> float:
    """Return (final crystal area - initial crystal area) / domain area."""
    domain_area = params.grid_width * params.grid_height
    return (snapshots[-1].crystal_area - snapshots[0].crystal_area) / domain_area


def check_scenario(material: MaterialConstants, name: str, run_celsius: float, saturation_celsius: float) -> CheckResult:
    """Run one scenario and test that silica is conserved and never negative."""
    params = build_scenario_params(material, run_celsius, saturation_celsius)
    snapshots = list(iterate_solution_growth(params, CHECK_STEPS_PER_SNAPSHOT, CHECK_DURATION))
    drift = compute_max_relative_drift(snapshots)
    lowest = min(s.minimum_silica for s in snapshots)
    area_change = compute_area_change_fraction(snapshots, params)
    passed = drift <= MAX_RELATIVE_DRIFT and lowest >= 0.0
    message = (
        f"Total silica changed by at most {drift:.1e} (relative; limit {MAX_RELATIVE_DRIFT:.0e}); "
        f"lowest concentration {lowest:.2e} mol/kg (must be >= 0); "
        f"crystal area changed by {100 * area_change:+.2f}% of the domain."
    )
    return CheckResult(f"mass conserved: {name}", passed, message)


def run_mass_check(material: MaterialConstants) -> list[CheckResult]:
    """Run all scenarios of validation check 3."""
    return [check_scenario(material, name, run, sat) for name, run, sat in SCENARIOS]
