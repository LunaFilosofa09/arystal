"""Speed measurements of the simulation on this computer."""

import dataclasses
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor

from arystal.simulation.controlled_run import ControlledRun
from arystal.simulation.material_loader import load_material
from arystal.simulation.run_config import RunConfig

# Minimum seconds of computing per measurement, so that timing noise is small.
MINIMUM_MEASUREMENT_SECONDS = 0.8
WARMUP_STEPS = 60
CHUNK = 20

# A run that has grown for a while (so that the interface is as large as in a typical run) is what gets timed.
GROWTH_STEPS_BEFORE_TIMING = 300


def make_benchmark_config(width: int, height: int, full_model: bool, backend: str, threads: int) -> RunConfig:
    """Return a configuration to time. "Full" model = iron, faceted growth and noise; otherwise no iron and no noise."""
    return RunConfig(
        temperature_celsius=20.0, saturation_temperature_celsius=60.0, iron_ppm=1.0 if full_model else None, duration=1e6,
        grid_width=width, grid_height=height, noise_on=full_model, backend=backend, threads=threads,
    )


def measure_milliseconds_per_step(config: RunConfig, minimum_seconds: float = MINIMUM_MEASUREMENT_SECONDS) -> float:
    """Run the configuration for at least `minimum_seconds` of computing and return the milliseconds per time step."""
    controller = ControlledRun(config, load_material())
    controller.advance(GROWTH_STEPS_BEFORE_TIMING + WARMUP_STEPS)  # also compiles the fast kernels
    steps = 0
    started = time.perf_counter()
    while time.perf_counter() - started < minimum_seconds:
        steps += controller.advance(CHUNK)
    return 1000.0 * (time.perf_counter() - started) / steps


def benchmark_single_process(grids: list[tuple[int, int]], thread_counts: list[int]) -> list[dict]:
    """Time the reference code and the fast code (several thread counts) on several grids; return one row per measurement."""
    rows = []
    for width, height in grids:
        for full_model in (True, False):
            variants = [("reference", 1)] + [("numba", threads) for threads in thread_counts]
            for backend, threads in variants:
                milliseconds = measure_milliseconds_per_step(make_benchmark_config(width, height, full_model, backend, threads), 0.4 if backend == "reference" else MINIMUM_MEASUREMENT_SECONDS)
                rows.append({
                    "grid": f"{width}x{height}", "model": "full" if full_model else "lean", "backend": backend, "threads": threads,
                    "ms_per_step": milliseconds, "steps_per_second": 1000.0 / milliseconds, "cell_updates_per_second": width * height * 1000.0 / milliseconds,
                })
    return rows


def run_scaling_worker(job: dict) -> dict:
    """Run one process of the scaling test: a fixed number of steps; return the seconds it took."""
    config = make_benchmark_config(job["width"], job["height"], True, "numba", 1)
    controller = ControlledRun(config, load_material())
    controller.advance(GROWTH_STEPS_BEFORE_TIMING)  # includes loading the compiled kernels
    started = time.perf_counter()
    controller.advance(job["steps"])
    return {"seconds": time.perf_counter() - started}


def benchmark_parallel_processes(width: int, height: int, steps: int, process_counts: list[int]) -> list[dict]:
    """Run N identical processes at the same time (as the replicas of an ensemble do) and measure how each one slows down."""
    rows = []
    for count in process_counts:
        job = {"width": width, "height": height, "steps": steps}
        started = time.perf_counter()
        with ProcessPoolExecutor(max_workers=count, mp_context=multiprocessing.get_context("spawn")) as pool:
            results = list(pool.map(run_scaling_worker, [job] * count))
        total_wall = time.perf_counter() - started
        seconds = [result["seconds"] for result in results]
        rows.append({
            "processes": count, "mean_seconds_per_process": sum(seconds) / count, "slowest_seconds": max(seconds),
            "aggregate_steps_per_second": count * steps / max(seconds), "total_wall_seconds_including_startup": total_wall,
        })
    one = rows[0]["mean_seconds_per_process"]
    for row in rows:
        row["slowdown_per_process"] = row["mean_seconds_per_process"] / one
        row["speedup_vs_one_process"] = row["aggregate_steps_per_second"] / rows[0]["aggregate_steps_per_second"]
    return rows
