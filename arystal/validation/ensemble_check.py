"""Validation of the ensemble.

Tests:
  A. A replica is identical, bit for bit, to running its seed alone with the same settings and timeline.
  B. The replica seeds are derived reproducibly from the base seed, are distinct, and the replicas really differ.
  C. The same recorded timeline is applied in every replica.
  D. The output files exist and the statistics (mean, standard deviation, min, max) equal an independent computation.
  E. The result does not depend on the number of parallel processes (serial = parallel).
  F. The statistics function handles known values, missing values and a single replica.

WHAT THESE TESTS DO NOT SHOW: that the spread between replicas resembles the natural variability of crystals. It is set by
the noise amplitudes, which are ASSUMED and uncalibrated. They check that the ensemble machinery is correct and reproducible.
"""

import dataclasses
import math
import tempfile
from pathlib import Path

import numpy as np

from arystal.engine.material_constants import MaterialConstants
from arystal.metrics.ensemble_statistics import compute_statistics
from arystal.simulation.controlled_run import run_to_end
from arystal.simulation.ensemble import EnsembleSettings, derive_replica_seeds, run_ensemble
from arystal.simulation.run_config import RunConfig
from arystal.simulation.timeline import TEMPERATURE, TimelineEvent, event_to_dict
from arystal.storage.serialization import read_json
from arystal.storage.snapshots import FINAL_FIELDS, load_final_state
from arystal.validation.check_result import CheckResult

LIMITS_NOTE = (
    "Limits: the spread between replicas is set by the ASSUMED noise amplitudes; these tests show the machinery is correct and "
    "reproducible, not that the spread resembles the natural variability of crystals."
)

BASE_CONFIG = RunConfig(
    temperature_celsius=40.0, saturation_temperature_celsius=60.0, iron_ppm=1.0, duration=200.0, grid_width=100, grid_height=50,
    seed=3, metrics_every_steps=500, snapshot_every_steps=1000,
)
TIMELINE = [TimelineEvent(1000, 100.0, TEMPERATURE, 20.0)]
REPLICAS = 3
PARALLEL_WORKERS = 2
MAX_STATISTIC_DIFFERENCE = 1e-12


def load_replica_states(ensemble_folder: Path) -> list[dict]:
    """Return the final states of the replicas of an ensemble folder, in replica order."""
    return [load_final_state(folder) for folder in sorted(ensemble_folder.glob("replica_*"))]


def states_equal(first: dict, second: dict) -> bool:
    """True if two saved final states are identical in all fields."""
    return all(np.array_equal(first[name], second[name]) for name in FINAL_FIELDS)


def read_seeds(ensemble_folder: Path) -> list[int]:
    """Return the replica seeds recorded in ensemble_summary.json."""
    return read_json(ensemble_folder / "ensemble_summary.json")["ensemble"]["replica_seeds"]


def check_replica_equals_standalone(material: MaterialConstants, parallel_folder: Path) -> CheckResult:
    """Test A."""
    seeds = read_seeds(parallel_folder)
    states = load_replica_states(parallel_folder)
    differing = []
    for seed, saved in zip(seeds, states):
        alone, _ = run_to_end(dataclasses.replace(BASE_CONFIG, seed=seed), material, TIMELINE)
        if not all(np.array_equal(saved[name], getattr(alone, name)) for name in FINAL_FIELDS):
            differing.append(seed)
    message = f"Replicas that differ from the same seed run alone: {differing if differing else 'none'} (of {len(seeds)}, run in {PARALLEL_WORKERS} parallel processes)."
    return CheckResult("each replica is identical to its seed run alone", not differing, message)


def check_seeds(parallel_folder: Path) -> CheckResult:
    """Test B."""
    seeds = read_seeds(parallel_folder)
    reproducible = derive_replica_seeds(BASE_CONFIG.seed, REPLICAS) == seeds
    distinct = len(set(seeds)) == len(seeds)
    states = load_replica_states(parallel_folder)
    differ = all(not np.array_equal(states[i]["phase_field"], states[j]["phase_field"]) for i in range(len(states)) for j in range(i + 1, len(states)))
    message = f"Seeds {seeds}: derived reproducibly from base seed {BASE_CONFIG.seed}: {reproducible}; all distinct: {distinct}; every pair of replicas differs: {differ}."
    return CheckResult("seeds are reproducible and distinct, and replicas differ", reproducible and distinct and differ, message)


def check_timeline_in_every_replica(parallel_folder: Path) -> CheckResult:
    """Test C."""
    expected = [event_to_dict(event) for event in TIMELINE]
    wrong = []
    for folder in sorted(parallel_folder.glob("replica_*")):
        record = read_json(folder / "timeline.json")
        applied = [{key: event[key] for key in ("step", "time", "parameter", "value")} for event in record["events"]]
        if applied != expected or record["final_step"] != int(round(BASE_CONFIG.duration / BASE_CONFIG.time_step)):
            wrong.append(folder.name)
    message = f"Replicas whose timeline differs from the base timeline {[(e.step, e.parameter, e.value) for e in TIMELINE]}: {wrong if wrong else 'none'}."
    return CheckResult("the same timeline is applied in every replica", not wrong, message)


def check_outputs_and_statistics(parallel_folder: Path) -> CheckResult:
    """Test D."""
    required = ("ensemble_summary.json", "ensemble_params.json", "ensemble_metrics.csv", "comparison.png")
    missing = [name for name in required if not (parallel_folder / name).exists()]
    summary = read_json(parallel_folder / "ensemble_summary.json")
    areas = [read_json(folder / "summary.json")["headline_results"]["crystal_area_mm2"] for folder in sorted(parallel_folder.glob("replica_*"))]
    reported = summary["statistics_of_final_metrics"]["crystal_area_mm2"]
    expected = {"mean": float(np.mean(areas)), "std": float(np.std(areas, ddof=1)), "min": float(np.min(areas)), "max": float(np.max(areas))}
    worst = max(abs(reported[key] - expected[key]) / abs(expected[key]) for key in expected)
    folders = len(list(parallel_folder.glob("replica_*")))
    passed = not missing and folders == REPLICAS and worst <= MAX_STATISTIC_DIFFERENCE
    message = (
        f"Missing files: {missing if missing else 'none'}; replica folders: {folders}; mean/std/min/max of the final area differ from an independent "
        f"computation by at most {worst:.1e} (limit {MAX_STATISTIC_DIFFERENCE:.0e}); area mean {reported['mean']:.2f} mm2, std {reported['std']:.2f}."
    )
    return CheckResult("output files are complete and statistics are right", passed, message)


def check_serial_equals_parallel(material: MaterialConstants, parallel_folder: Path, root: Path) -> CheckResult:
    """Test E."""
    serial_folder = run_ensemble(BASE_CONFIG, TIMELINE, EnsembleSettings(REPLICAS, 1, BASE_CONFIG.seed), root)
    parallel_states = load_replica_states(parallel_folder)
    serial_states = load_replica_states(serial_folder)
    same = len(parallel_states) == len(serial_states) and all(states_equal(a, b) for a, b in zip(parallel_states, serial_states))
    message = f"Serial ensemble (1 process) and parallel ensemble ({PARALLEL_WORKERS} processes) give identical replicas: {same}."
    return CheckResult("the number of parallel processes does not change the result", same, message)


def check_statistics_function() -> CheckResult:
    """Test F."""
    known = compute_statistics([1.0, 2.0, 3.0, 4.0])
    with_missing = compute_statistics([1.0, float("nan"), 3.0])
    only_missing = compute_statistics([float("nan")])
    single = compute_statistics([5.0])
    passed = (
        math.isclose(known["mean"], 2.5) and math.isclose(known["std"], math.sqrt(5.0 / 3.0)) and known["min"] == 1.0 and known["max"] == 4.0
        and with_missing["n"] == 2 and math.isclose(with_missing["mean"], 2.0)
        and only_missing["mean"] is None and only_missing["n"] == 0
        and single["std"] is None and single["mean"] == 5.0
    )
    message = f"[1,2,3,4] -> mean {known['mean']}, std {known['std']:.4f} (sample, n-1); missing values ignored; all-missing and single-value cases give None where undefined."
    return CheckResult("statistics handle known values, missing values and one replica", passed, message)


def run_ensemble_check(material: MaterialConstants) -> list[CheckResult]:
    """Run all tests of the ensemble check."""
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        parallel_folder = run_ensemble(BASE_CONFIG, TIMELINE, EnsembleSettings(REPLICAS, PARALLEL_WORKERS, BASE_CONFIG.seed), root)
        return [
            check_replica_equals_standalone(material, parallel_folder),
            check_seeds(parallel_folder),
            check_timeline_in_every_replica(parallel_folder),
            check_outputs_and_statistics(parallel_folder),
            check_serial_equals_parallel(material, parallel_folder, root),
            check_statistics_function(),
        ]
