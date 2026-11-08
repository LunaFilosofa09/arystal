"""Validation of seed reproducibility and of the saved results.

Tests:
  A. Same seed, same settings: the final fields are identical, bit for bit.
  B. Different seeds: the results differ (the noise works) but only slightly (replicas of one experiment).
  C. Saved run: all files of the results folder exist, and final_state.npz is identical to the in-memory result.
  D. Replay: rebuilding the run from the saved params.json and running again reproduces the saved result exactly.
  E. With noise and seed variations off, the seed has no effect.
  F. Noise does not roughen the surface, even with slow attachment kinetics (large tau): the random term must
     scale like the deterministic dynamics (fluctuation-dissipation). Found during development: without the 1/sqrt(tau) factor the
     surface of a slow-kinetics run was visibly ragged (roughness 0.083 vs 0.015 with the factor).

WHAT THESE TESTS DO NOT SHOW: that the noise amplitude gives the right spread between real crystals (it is
ASSUMED), or that results are identical on another computer or with other library versions (floating-point results
can differ in the last bits between platforms).
"""

import dataclasses
import tempfile
from pathlib import Path

import numpy as np

from arystal.engine.material_constants import MaterialConstants
from arystal.engine.solution_growth import SolutionState
from arystal.metrics.shape import compute_surface_roughness
from arystal.simulation.run_config import RunConfig, create_config_from_dict
from arystal.simulation.saved_run import run_and_save
from arystal.simulation.controlled_run import run_to_end
from arystal.storage.serialization import read_json
from arystal.storage.snapshots import FINAL_FIELDS, list_snapshots, load_final_state
from arystal.validation.check_result import CheckResult

LIMITS_NOTE = (
    "Limits: the noise amplitude is ASSUMED, so the spread between seeds is not calibrated against real crystals. "
    "Bit-for-bit identity holds on the same machine and library versions; other platforms may differ in the last bits."
)

# Small and short: a few seconds per run.
BASE_CONFIG = RunConfig(
    temperature_celsius=15.0, saturation_temperature_celsius=60.0, duration=400.0, grid_width=120, grid_height=60,
    seed=11, metrics_every_steps=500, snapshot_every_steps=2000,
)
OTHER_SEED = 12
MAX_AREA_DIFFERENCE_BETWEEN_SEEDS = 0.10
MAX_CONSERVATION_DRIFT = 1e-9

# Test F: slow kinetics (large tau) with noise on, compared with the noise-free run. Roughness is measured on the
# contour phi = 0.1 (see metrics/shape.py). Measured when the test was written: 0.011 without noise, 0.015 with the
# correct noise scaling, 0.083 with the defective one; the limit lies between them.
SLOW_RELAXATION_TIME = 40.0
SLOW_TIME_STEP = 0.2
SLOW_DURATION = 1500.0
SLOW_GRID_WIDTH = 160
SLOW_GRID_HEIGHT = 80
ROUGHNESS_LEVEL = 0.1
MAX_SURFACE_ROUGHNESS = 0.04

EXPECTED_FILES = ("params.json", "timeline.json", "metrics.csv", "final_state.npz", "final_image.png", "summary.json")


def find_differing_fields(first: SolutionState, second: SolutionState) -> list[str]:
    """Return the names of the fields in which two states are not exactly equal."""
    return [name for name in FINAL_FIELDS if not np.array_equal(getattr(first, name), getattr(second, name))]


def find_differing_saved_fields(saved: dict, state: SolutionState) -> list[str]:
    """Return the names of the saved fields that are not exactly equal to the state's."""
    return [name for name in FINAL_FIELDS if not np.array_equal(saved[name], getattr(state, name))]


def check_same_seed_identical(material: MaterialConstants) -> CheckResult:
    """Test A."""
    first, _ = run_to_end(BASE_CONFIG, material)
    second, _ = run_to_end(BASE_CONFIG, material)
    differing = find_differing_fields(first, second)
    message = f"Fields that differ between two runs with seed {BASE_CONFIG.seed}: {differing if differing else 'none (identical bit for bit)'}."
    return CheckResult("same seed gives an identical result", not differing, message)


def check_different_seeds_differ_slightly(material: MaterialConstants) -> CheckResult:
    """Test B."""
    first, _ = run_to_end(BASE_CONFIG, material)
    second, _ = run_to_end(dataclasses.replace(BASE_CONFIG, seed=OTHER_SEED), material)
    largest_difference = float(np.abs(first.phase_field - second.phase_field).max())
    area_first, area_second = first.phase_field.sum(), second.phase_field.sum()
    area_difference = abs(area_first - area_second) / area_first
    passed = largest_difference > 0.0 and area_difference <= MAX_AREA_DIFFERENCE_BETWEEN_SEEDS
    message = (
        f"Seeds {BASE_CONFIG.seed} and {OTHER_SEED}: largest difference in the phase field {largest_difference:.2e} (must be > 0), "
        f"crystal area differs by {100 * area_difference:.2f}% (limit {100 * MAX_AREA_DIFFERENCE_BETWEEN_SEEDS:.0f}%)."
    )
    return CheckResult("different seeds give slightly different crystals", passed, message)


def check_saved_run(material: MaterialConstants, root: Path) -> tuple[CheckResult, CheckResult]:
    """Tests C and D, which share one saved run."""
    folder = run_and_save(BASE_CONFIG, root, material)
    missing = [name for name in EXPECTED_FILES if not (folder / name).exists()]
    plots = sorted(path.name for path in (folder / "plots").glob("*.png"))
    snapshots = len(list_snapshots(folder))
    expected, _ = run_to_end(BASE_CONFIG, material)
    saved = load_final_state(folder)
    differing_saved = find_differing_saved_fields(saved, expected)
    drift = read_json(folder / "summary.json")["conservation"]
    worst_drift = max(drift.values())
    passed_c = not missing and not differing_saved and snapshots >= 1 and bool(plots) and worst_drift <= MAX_CONSERVATION_DRIFT
    message_c = (
        f"Missing files: {missing if missing else 'none'}; {snapshots} snapshots, {len(plots)} plots; final_state.npz identical to the "
        f"in-memory result: {not differing_saved}; conservation drift in summary.json {worst_drift:.1e} (limit {MAX_CONSERVATION_DRIFT:.0e})."
    )
    replayed_config = create_config_from_dict(read_json(folder / "params.json")["config"])
    replayed, _ = run_to_end(replayed_config, material)
    differing_replay = find_differing_saved_fields(saved, replayed)
    message_d = f"Run rebuilt from params.json differs from the saved result in: {differing_replay if differing_replay else 'nothing (identical bit for bit)'}."
    return (
        CheckResult("results folder is complete and exact", passed_c, message_c),
        CheckResult("replaying params.json reproduces the saved result", not differing_replay, message_d),
    )


def check_noise_off_ignores_seed(material: MaterialConstants) -> CheckResult:
    """Test E."""
    quiet = dataclasses.replace(BASE_CONFIG, noise_on=False)
    first, _ = run_to_end(quiet, material)
    second, _ = run_to_end(dataclasses.replace(quiet, seed=OTHER_SEED), material)
    differing = find_differing_fields(first, second)
    message = f"With noise off, seeds {quiet.seed} and {OTHER_SEED} differ in: {differing if differing else 'nothing (the seed only acts through the noise)'}."
    return CheckResult("with noise off the seed has no effect", not differing, message)


def check_noise_does_not_roughen_surface(material: MaterialConstants) -> CheckResult:
    """Test F."""
    config = dataclasses.replace(
        BASE_CONFIG, relaxation_time=SLOW_RELAXATION_TIME, time_step=SLOW_TIME_STEP, duration=SLOW_DURATION,
        grid_width=SLOW_GRID_WIDTH, grid_height=SLOW_GRID_HEIGHT, seed=7,
    )
    noisy, _ = run_to_end(config, material)
    quiet, _ = run_to_end(dataclasses.replace(config, noise_on=False), material)
    rough = compute_surface_roughness(noisy.phase_field, ROUGHNESS_LEVEL)
    baseline = compute_surface_roughness(quiet.phase_field, ROUGHNESS_LEVEL)
    message = (
        f"With tau = {SLOW_RELAXATION_TIME:.0f} the surface roughness (contour phi = {ROUGHNESS_LEVEL}) is {rough:.3f} with noise and "
        f"{baseline:.3f} without (limit {MAX_SURFACE_ROUGHNESS}; a noise term that does not scale with tau gave about 0.083)."
    )
    return CheckResult("noise does not roughen the surface with slow kinetics", rough <= MAX_SURFACE_ROUGHNESS, message)


def run_reproducibility_check(material: MaterialConstants) -> list[CheckResult]:
    """Run all tests of the reproducibility check."""
    with tempfile.TemporaryDirectory() as folder:
        saved_results = check_saved_run(material, Path(folder))
    return [
        check_same_seed_identical(material),
        check_different_seeds_differ_slightly(material),
        *saved_results,
        check_noise_off_ignores_seed(material),
        check_noise_does_not_roughen_surface(material),
    ]
