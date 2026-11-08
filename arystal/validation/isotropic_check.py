"""Validation check 1: without anisotropy the crystal grows as a smooth half-disc.

Two tests, both reported in plain language:
  A. Shape: the distance from the seed centre to the surface is the same at every angle.
  B. Speed: the growth speed matches the exact theoretical prediction for this model.
"""

import numpy as np

from arystal.engine.isotropic_params import IsotropicParams
from arystal.engine.isotropic_theory import (
    compute_critical_radius,
    compute_front_speed_at_radius,
)
from arystal.metrics.shape import compute_roundness_error, measure_surface_radii
from arystal.simulation.isotropic_run import Snapshot, iterate_growth
from arystal.validation.check_result import CheckResult

# The surface radius may differ between angles by at most this fraction of the mean radius.
MAX_ROUNDNESS_ERROR = 0.05

# The measured growth speed may differ from the theory by at most this fraction.
MAX_SPEED_ERROR = 0.10

# Radius window (cells) in which the speed is measured: far from the seed's start-up
# and far from the domain boundaries.
SPEED_WINDOW_MIN_RADIUS = 30.0
SPEED_WINDOW_MAX_RADIUS = 60.0

STEPS_PER_SNAPSHOT = 100


def collect_snapshots(params: IsotropicParams) -> list[Snapshot]:
    """Run the growth to the end and keep every snapshot."""
    return list(iterate_growth(params, STEPS_PER_SNAPSHOT))


def select_speed_window(snapshots: list[Snapshot]) -> list[Snapshot]:
    """Keep only the snapshots whose radius lies in the speed-measurement window."""
    return [
        s for s in snapshots
        if SPEED_WINDOW_MIN_RADIUS <= s.equivalent_radius <= SPEED_WINDOW_MAX_RADIUS
    ]


def measure_growth_speed(window: list[Snapshot]) -> float:
    """Return the measured growth speed (cells per time unit): slope of radius vs time."""
    times = [s.time for s in window]
    radii = [s.equivalent_radius for s in window]
    slope, _ = np.polyfit(times, radii, 1)
    return float(slope)


def predict_growth_speed(params: IsotropicParams, window: list[Snapshot]) -> float:
    """Return the theoretical speed averaged over the radii seen in the window."""
    speeds = [compute_front_speed_at_radius(params, s.equivalent_radius) for s in window]
    return float(np.mean(speeds))


def check_shape(snapshot: Snapshot) -> CheckResult:
    """Test A: is the final crystal a half-circle?"""
    radii = measure_surface_radii(snapshot.phase_field)
    error = compute_roundness_error(radii)
    message = (
        f"Surface radius ranges from {np.nanmin(radii):.1f} to {np.nanmax(radii):.1f} cells "
        f"(mean {np.nanmean(radii):.1f}); spread = {100 * error:.2f}% of the mean "
        f"(limit {100 * MAX_ROUNDNESS_ERROR:.0f}%)."
    )
    return CheckResult("shape is a smooth half-disc", error <= MAX_ROUNDNESS_ERROR, message)


def check_speed(params: IsotropicParams, snapshots: list[Snapshot]) -> CheckResult:
    """Test B: does the crystal grow at the speed the theory predicts?"""
    window = select_speed_window(snapshots)
    measured = measure_growth_speed(window)
    predicted = predict_growth_speed(params, window)
    error = abs(measured - predicted) / predicted
    message = (
        f"Measured speed {measured:.4f} cells/time, theory {predicted:.4f}; "
        f"difference {100 * error:.2f}% (limit {100 * MAX_SPEED_ERROR:.0f}%)."
    )
    return CheckResult("growth speed matches theory", error <= MAX_SPEED_ERROR, message)


def check_seed_is_supercritical(params: IsotropicParams) -> CheckResult:
    """Sanity test: the seed must be larger than the critical radius, otherwise it would dissolve."""
    critical = compute_critical_radius(params)
    message = f"Seed radius {params.seed_radius:.1f} cells, critical radius {critical:.1f} cells."
    return CheckResult("seed is larger than critical radius", params.seed_radius > critical, message)


def run_isotropic_check(params: IsotropicParams) -> list[CheckResult]:
    """Run all tests of validation check 1 and return their results."""
    seed_result = check_seed_is_supercritical(params)
    if not seed_result.passed:
        return [seed_result]
    snapshots = collect_snapshots(params)
    return [seed_result, check_shape(snapshots[-1]), check_speed(params, snapshots)]
