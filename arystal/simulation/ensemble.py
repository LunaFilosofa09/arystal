"""An ensemble: several replicas of the same run, each with a different seed.

Every replica has the same configuration and replays the same recorded timeline, so the replicas differ only through the
random numbers (interface noise and seed variation). Replicas run in parallel in separate processes, 5 at a time by default
(one core is left free on the 6-core MacBook). Each replica is a complete saved run in its own folder inside the ensemble folder.

The seeds are derived from one base seed, so the whole ensemble is reproducible, and a replica is identical to running
its seed alone.
"""

import dataclasses
import multiprocessing
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from arystal.metrics.ensemble_statistics import compute_final_statistics, compute_timeseries_statistics, rows_are_aligned
from arystal.simulation.material_loader import load_material
from arystal.simulation.run_config import RunConfig
from arystal.simulation.saved_run import build_scientific_status, run_and_save
from arystal.simulation.seeded_run import build_params
from arystal.simulation.timeline import TimelineEvent, event_from_dict, event_to_dict
from arystal.storage.ensemble_outputs import save_comparison_image, save_ensemble_plots, write_timeseries_csv
from arystal.storage.metrics_io import read_metrics_csv
from arystal.storage.result_folder import DEFAULT_RESULTS_ROOT, create_ensemble_folder
from arystal.storage.serialization import read_json, write_json

DEFAULT_NUMBER_OF_REPLICAS = 10
DEFAULT_WORKERS = 5  # 6-core machine: leave one core free
STATISTIC_NOTE = "std is the sample standard deviation (n - 1) over the replicas."
CONCURRENCY_NOTE = (
    "average_concurrency is the sum of the replica times divided by the ensemble time: how many replicas ran at once on average. It is NOT the speed-up: "
    "replicas run slower when several share the machine (measured with the NumPy code: 2.3x slower each with 5 workers, real speed-up about 2.2x). Compare with a serial run to get the speed-up."
)
SPREAD_NOTE = (
    "The spread between replicas comes from the interface noise and the seed variations, whose amplitudes are ASSUMED and not calibrated "
    "against real crystals: it shows that the model reacts to randomness, not how variable real crystals are."
)


@dataclasses.dataclass(frozen=True)
class EnsembleSettings:
    """How to build the ensemble: number of replicas, parallel workers and the seed the replica seeds are derived from."""

    number_of_replicas: int = DEFAULT_NUMBER_OF_REPLICAS
    workers: int = DEFAULT_WORKERS
    base_seed: int = 0


def derive_replica_seeds(base_seed: int, number_of_replicas: int) -> list[int]:
    """Return distinct integer seeds derived from the base seed (the same base seed always gives the same list)."""
    seeds = []
    for value in np.random.SeedSequence(base_seed).generate_state(number_of_replicas * 2):
        if int(value) not in seeds:
            seeds.append(int(value))
        if len(seeds) == number_of_replicas:
            break
    return seeds


def build_replica_name(index: int, seed: int) -> str:
    """Return the folder name of a replica."""
    return f"replica_{index + 1:02d}_seed{seed}"


def run_replica(job: dict) -> dict:
    """Run one replica and return its seed, folder, compute time and metrics. (Top-level function so it can run in another process.)"""
    config = RunConfig(**job["config"])
    events = [event_from_dict(values) for values in job["events"]]
    started = time.perf_counter()
    folder = run_and_save(config, Path(job["root"]), None, events, folder_name=job["name"])
    return {
        "index": job["index"], "seed": config.seed, "folder": str(folder),
        "wall_seconds": time.perf_counter() - started, "rows": read_metrics_csv(folder / "metrics.csv"),
    }


def build_jobs(config: RunConfig, events: list[TimelineEvent], seeds: list[int], root: Path) -> list[dict]:
    """Return one job description (plain data, easy to send to another process) per replica."""
    return [
        {"index": index, "name": build_replica_name(index, seed), "root": str(root),
         "config": dataclasses.asdict(dataclasses.replace(config, seed=seed)), "events": [event_to_dict(event) for event in events]}
        for index, seed in enumerate(seeds)
    ]


def run_jobs(jobs: list[dict], workers: int, on_replica_done: Callable[[dict], None] | None) -> list[dict]:
    """Run the jobs, in parallel in separate processes when workers > 1 (serially in this process otherwise). Returns results ordered by replica."""
    results = []
    if workers <= 1:
        for job in jobs:
            results.append(run_replica(job))
            if on_replica_done:
                on_replica_done(results[-1])
    else:
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=min(workers, len(jobs)), mp_context=context) as pool:
            futures = [pool.submit(run_replica, job) for job in jobs]
            for future in as_completed(futures):
                results.append(future.result())
                if on_replica_done:
                    on_replica_done(results[-1])
    return sorted(results, key=lambda result: result["index"])


def build_replica_records(results: list[dict], ensemble_folder: Path) -> list[dict]:
    """Return the per-replica part of ensemble_summary.json: seed, folder name, compute time and final metrics."""
    return [
        {"index": result["index"], "seed": result["seed"], "folder": Path(result["folder"]).name,
         "wall_clock_seconds": result["wall_seconds"], "final_metrics": result["rows"][-1]}
        for result in results
    ]


def build_ensemble_summary(
    config: RunConfig, events: list[TimelineEvent], settings: EnsembleSettings, seeds: list[int],
    results: list[dict], ensemble_wall_seconds: float, ensemble_folder: Path,
) -> dict:
    """Return the content of ensemble_summary.json."""
    material = load_material()
    replica_walls = [result["wall_seconds"] for result in results]
    final_rows = [result["rows"][-1] for result in results]
    return {
        "ensemble": {
            "number_of_replicas": len(results), "base_seed": settings.base_seed, "replica_seeds": seeds,
            "workers": settings.workers, "statistics_note": STATISTIC_NOTE,
        },
        "base_config": dataclasses.asdict(config),
        "timeline_applied_to_every_replica": [event_to_dict(event) for event in events],
        "replicas": build_replica_records(results, ensemble_folder),
        "statistics_of_final_metrics": compute_final_statistics(final_rows),
        "compute_cost": {
            "ensemble_wall_clock_seconds": ensemble_wall_seconds,
            "sum_of_replica_wall_clock_seconds": float(sum(replica_walls)),
            "average_concurrency": float(sum(replica_walls)) / ensemble_wall_seconds if ensemble_wall_seconds > 0 else None,
            "concurrency_note": CONCURRENCY_NOTE,
        },
        "scientific_status": {**build_scientific_status(config, build_params(config, material), material), "spread": SPREAD_NOTE},
    }


def run_ensemble(
    config: RunConfig, events: list[TimelineEvent] | None = None, settings: EnsembleSettings = EnsembleSettings(),
    results_root: Path = DEFAULT_RESULTS_ROOT, on_replica_done: Callable[[dict], None] | None = None,
) -> Path:
    """Run the ensemble of `config` replaying `events` and save everything in a new ensemble folder, which is returned."""
    events = events or []
    folder = create_ensemble_folder(results_root)
    seeds = derive_replica_seeds(settings.base_seed, settings.number_of_replicas)
    write_json(folder / "ensemble_params.json", {"settings": settings, "config": config, "replica_seeds": seeds, "timeline": [event_to_dict(e) for e in events]})
    started = time.perf_counter()
    results = run_jobs(build_jobs(config, events, seeds, folder), settings.workers, on_replica_done)
    wall = time.perf_counter() - started
    all_rows = [result["rows"] for result in results]
    if rows_are_aligned(all_rows):
        timeseries = compute_timeseries_statistics(all_rows)
        write_timeseries_csv(folder / "ensemble_metrics.csv", timeseries)
        save_ensemble_plots(folder, timeseries)
    save_comparison_image(folder, [Path(result["folder"]) for result in results], seeds)
    write_json(folder / "ensemble_summary.json", build_ensemble_summary(config, events, settings, seeds, results, wall, folder))
    return folder
