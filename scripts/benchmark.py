"""Measure the speed of the simulation on this computer.

    python scripts/benchmark.py                 # single-process speed (reference vs fast, threads, grids) and parallel scaling
    python scripts/benchmark.py --quick         # fewer measurements
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from arystal.simulation.benchmarking import benchmark_parallel_processes, benchmark_single_process  # noqa: E402

GRIDS = [(200, 100), (400, 200), (800, 400)]
QUICK_GRIDS = [(200, 100), (400, 200)]
THREADS = [1, 2, 4, 6]
PROCESS_COUNTS = [1, 2, 3, 5, 6]
SCALING_GRID = (400, 200)
SCALING_STEPS = 600


def print_single_process_table(rows: list[dict]) -> None:
    """Print the single-process results as a table."""
    print("\nSINGLE PROCESS (milliseconds per time step; lower is better)")
    print(f"{'grid':>9} {'model':>5} {'backend':>9} {'threads':>7} {'ms/step':>9} {'steps/s':>9} {'Mcell-updates/s':>16}")
    for row in rows:
        print(f"{row['grid']:>9} {row['model']:>5} {row['backend']:>9} {row['threads']:>7} {row['ms_per_step']:9.2f} {row['steps_per_second']:9.0f} {row['cell_updates_per_second'] / 1e6:16.1f}")


def print_scaling_table(rows: list[dict]) -> None:
    """Print the parallel-process results as a table."""
    print(f"\nPARALLEL PROCESSES (full model, {SCALING_GRID[0]}x{SCALING_GRID[1]}, 1 thread each, {SCALING_STEPS} steps per process)")
    print(f"{'processes':>9} {'s per process':>14} {'slowdown each':>14} {'aggregate steps/s':>18} {'speed-up':>9}")
    for row in rows:
        print(f"{row['processes']:>9} {row['mean_seconds_per_process']:14.2f} {row['slowdown_per_process']:14.2f} {row['aggregate_steps_per_second']:18.0f} {row['speedup_vs_one_process']:9.2f}")


def main() -> None:
    """Run the measurements, print the tables and save them as JSON."""
    parser = argparse.ArgumentParser(description="Benchmark of Arystal on this computer.")
    parser.add_argument("--quick", action="store_true")
    arguments = parser.parse_args()
    single = benchmark_single_process(QUICK_GRIDS if arguments.quick else GRIDS, THREADS)
    print_single_process_table(single)
    scaling = benchmark_parallel_processes(*SCALING_GRID, SCALING_STEPS, [1, 3, 6] if arguments.quick else PROCESS_COUNTS)
    print_scaling_table(scaling)
    output = Path(__file__).resolve().parent.parent / "results" / "benchmark.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps({"single_process": single, "parallel_processes": scaling}, indent=2))
    print(f"\nSaved {output}")


if __name__ == "__main__":
    main()
