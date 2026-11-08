"""Validation check: fluid renewal pulses (open decisions 4 and 5 of docs/kinetic_regime.md).

A renewal replaces the fluid by fluid saturated with quartz at a chosen temperature, with the current fluid iron. Tests:
A. one renewal sets the fluid to the target silica, and silica and iron balances close after discounting what the renewal added;
B. periodic renewals keep the supersaturation higher than in the closed container, grow a larger crystal, and are reproducible;
C. the same holds with the uniform-fluid scheme of the modes;
D. a renewal temperature outside the geode range is refused.

Honest limits: this checks that the code does what it says. Whether real geodes were renewed in instantaneous, complete pulses, how often, and with
what fluid, is not known (Arduin Rode et al. 2024, abstract only: "episodic infiltration of meteoric water").
"""

import dataclasses

import numpy as np

from arystal.engine.material_constants import MaterialConstants
from arystal.engine.silica_transport import compute_solid_fraction
from arystal.engine.solubility import compute_equilibrium_concentration
from arystal.metrics.shape import compute_crystal_area
from arystal.simulation.controlled_run import ControlledRun, run_to_end
from arystal.simulation.run_config import RunConfig
from arystal.simulation.timeline import RENEWAL
from arystal.validation.check_result import CheckResult

LIMITS_NOTE = (
    "Limits: renewals are instantaneous and complete by assumption; their frequency and fluid are not known for real geodes. "
    "These tests check the bookkeeping and the behaviour, not the geology."
)

BASE_CONFIG = RunConfig(
    temperature_celsius=20.0, saturation_temperature_celsius=60.0, iron_ppm=1.0, duration=600.0, grid_width=100, grid_height=50,
    seed=3, noise_on=False, metrics_every_steps=500, snapshot_every_steps=2000,
)
RENEWAL_STEP = 3000
RENEWAL_CELSIUS = 50.0
PERIODIC_INTERVAL = 100.0          # model time between periodic renewals (6 renewals in the run)
MAX_BALANCE_ERROR = 1e-12
MAX_TARGET_ERROR = 1e-12
UNIFORM_TAU = 10000.0              # on the plateau, as in the modes
UNIFORM_TIME_STEP = 1000.0
UNIFORM_DURATION = 3.0e6
UNIFORM_INTERVAL = 5.0e5


def compute_total_silica(controller: ControlledRun) -> float:
    """Return dissolved + held silica in the container (model units)."""
    solid = compute_solid_fraction(controller.state.phase_field)
    return float(controller.state.silica.sum() + controller.params.solid_capacity * solid.sum())


def compute_total_iron(controller: ControlledRun) -> float:
    """Return dissolved + locked-in iron in the container (model units)."""
    return float(controller.state.iron.sum() + controller.state.crystal_iron.sum())


def check_single_renewal(material: MaterialConstants) -> CheckResult:
    """Test A."""
    controller = ControlledRun(BASE_CONFIG, material)
    start_silica, start_iron = compute_total_silica(controller), compute_total_iron(controller)
    controller.advance(RENEWAL_STEP)
    controller.request_change(RENEWAL, RENEWAL_CELSIUS)
    controller.process_commands()
    target = compute_equilibrium_concentration(material, RENEWAL_CELSIUS)
    fluid = (1.0 - compute_solid_fraction(controller.state.phase_field)) > 0.5
    target_error = float(np.abs(controller.state.silica[fluid] / target - 1.0).max())
    while not controller.is_finished():
        controller.advance(10**9)
    silica_error = abs(compute_total_silica(controller) - controller.injected_silica - start_silica) / start_silica
    iron_error = abs(compute_total_iron(controller) - controller.injected_iron - start_iron) / start_iron
    passed = target_error <= MAX_TARGET_ERROR and silica_error <= MAX_BALANCE_ERROR and iron_error <= MAX_BALANCE_ERROR
    message = (
        f"After the renewal the fluid silica equals c_eq({RENEWAL_CELSIUS:g} C) to {target_error:.1e}; at the end, silica balance {silica_error:.1e} and iron balance "
        f"{iron_error:.1e} after discounting what the renewal added (limit {MAX_BALANCE_ERROR:.0e}). Silica added {controller.injected_silica:.3g} model units."
    )
    return CheckResult("one renewal: fluid reset to the target, balances close", passed, message)


def grow_closed_and_renewed(config: RunConfig, material: MaterialConstants, interval: float) -> tuple[float, float, float]:
    """Return (crystal area closed, area with periodic renewals, area of a repeated renewed run)."""
    closed_state, _ = run_to_end(config, material)
    renewed_config = dataclasses.replace(config, renewal_interval=interval, renewal_saturation_celsius=config.saturation_temperature_celsius)
    renewed_state, _ = run_to_end(renewed_config, material)
    repeated_state, _ = run_to_end(renewed_config, material)
    identical = np.array_equal(renewed_state.phase_field, repeated_state.phase_field)
    return compute_crystal_area(closed_state.phase_field), compute_crystal_area(renewed_state.phase_field), 1.0 if identical else 0.0


def check_periodic_renewal(material: MaterialConstants, config: RunConfig, interval: float, label: str) -> CheckResult:
    """Tests B and C: periodic renewals grow more crystal than the closed container, and the run is reproducible."""
    closed_area, renewed_area, identical = grow_closed_and_renewed(config, material, interval)
    passed = renewed_area > closed_area and identical == 1.0
    message = (
        f"[{label}] crystal area closed {closed_area:.0f} cells, with a renewal every {interval:g} model time units {renewed_area:.0f} cells "
        f"(x{renewed_area / closed_area:.2f}); repeated run identical bit for bit: {identical == 1.0}."
    )
    return CheckResult(f"periodic renewals feed more growth and are reproducible ({label})", passed, message)


def check_out_of_range_refused(material: MaterialConstants) -> CheckResult:
    """Test D."""
    controller = ControlledRun(BASE_CONFIG, material)
    controller.request_change(RENEWAL, material.geode_max_celsius + 20.0)
    controller.process_commands()
    refused = bool(controller.rejected) and controller.injected_silica == 0.0
    return CheckResult("renewal outside the geode temperature range is refused", refused, controller.rejected[-1] if controller.rejected else "no rejection")


def build_uniform_config() -> RunConfig:
    """Return a small run with the uniform-fluid scheme on the plateau, like the modes."""
    return dataclasses.replace(
        BASE_CONFIG, diffusion_scheme="uniform", relaxation_time=UNIFORM_TAU, time_step=UNIFORM_TIME_STEP, duration=UNIFORM_DURATION,
    )


def run_renewal_check(material: MaterialConstants) -> list[CheckResult]:
    """Run all tests of the renewal check."""
    return [
        check_single_renewal(material),
        check_periodic_renewal(material, BASE_CONFIG, PERIODIC_INTERVAL, "explicit diffusion"),
        check_periodic_renewal(material, build_uniform_config(), UNIFORM_INTERVAL, "uniform fluid"),
        check_out_of_range_refused(material),
    ]
