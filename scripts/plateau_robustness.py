"""Run the plateau-robustness study (docs/regime_study.md, section 7): the Da sweep repeated under other conditions.

    python scripts/plateau_robustness.py                  # every case, 5 parallel processes (about 30-40 minutes)
    python scripts/plateau_robustness.py --time-only      # time one fast and one slow job first

Results: results/plateau_robustness/plateau_robustness.json and plateau_vs_da.png.
"""

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from arystal.simulation.material_loader import load_material  # noqa: E402
from arystal.validation.plateau_robustness import (  # noqa: E402
    CASES, STUDY_TAUS, check_aspect_within_one_cell, compute_mode_damkohler, find_plateau_onset, list_jobs, run_case_at_tau,
)

OUTPUT_FOLDER = Path(__file__).resolve().parent.parent / "results" / "plateau_robustness"
DEFAULT_WORKERS = 5          # leave one core free on a 6-core machine
THREADS_PER_WORKER = 1


def start_worker() -> None:
    """Give each worker process one Numba thread, so 5 workers use 5 cores."""
    import numba
    numba.set_num_threads(THREADS_PER_WORKER)


def run_job(job: tuple[int, float]) -> dict:
    """Run one (case, tau) job in a worker process and return its row."""
    import warnings
    warnings.simplefilter("ignore", RuntimeWarning)
    return run_case_at_tau(load_material(), job[0], job[1])


def run_jobs(jobs: list[tuple[int, float]], workers: int) -> list[dict]:
    """Run the jobs in parallel and return their rows, printing each one when it finishes."""
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=start_worker) as pool:
        futures = [pool.submit(run_job, job) for job in jobs]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(f"{row['case']:60s} tau {row['tau']:9.0f} Da {row['damkohler']:8.1e} aspect {row['aspect_ratio']:.4f} r/m {row['face_ratio_r_over_m']:.4f} "
                  f"reached {row['reached_target']} {row['wall_seconds']:6.0f} s", flush=True)
    return rows


def summarise(rows: list[dict]) -> list[dict]:
    """Return one summary per case: plateau onset (Da at the target size), the Da of the modes, and whether the modes are on the plateau."""
    material = load_material()
    summaries = []
    for case_index, case in enumerate(CASES):
        case_rows = [row for row in rows if row["case_index"] == case_index]
        onset = find_plateau_onset(case_rows)
        modes = compute_mode_damkohler(material, case_index)
        ratio = case_rows[0]["damkohler_at_warning_size"] / case_rows[0]["damkohler"]
        summaries.append({"case": case[0], "group": case[1], "plateau_onset_da": onset, "plateau_onset_da_at_warning_size": onset * ratio,
                          "aspect_within_one_cell_on_plateau": check_aspect_within_one_cell(case_rows, onset),
                          "modes_da": modes["at_target"], "modes_on_plateau": onset == onset and modes["at_target"] <= onset})
    return summaries


def plot_rows(rows: list[dict]) -> None:
    """Save aspect ratio against Da (log scale) for every case, one panel per group."""
    groups = sorted({row["group"] for row in rows})
    figure, axes = plt.subplots(1, len(groups), figsize=(4 * len(groups), 3.6), sharey=False)
    for axis, group in zip(axes, groups):
        for case_index, case in enumerate(CASES):
            if case[1] not in (group, "baseline"):
                continue
            case_rows = sorted([row for row in rows if row["case_index"] == case_index], key=lambda row: row["damkohler"])
            axis.plot([row["damkohler"] for row in case_rows], [row["aspect_ratio"] for row in case_rows], marker="o", label=case[0][:28])
        axis.set_xscale("log")
        axis.set_xlabel("model Da (at the target size)")
        axis.set_title(group)
        axis.grid(alpha=0.3)
        axis.legend(fontsize=6)
    axes[0].set_ylabel("aspect ratio at equal size")
    figure.tight_layout()
    figure.savefig(OUTPUT_FOLDER / "plateau_vs_da.png", dpi=120)
    plt.close(figure)


def main() -> None:
    """Time, or run everything, save and print the summary."""
    parser = argparse.ArgumentParser(description="Plateau robustness study.")
    parser.add_argument("--time-only", action="store_true")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--summary-only", action="store_true", help="recompute the summary and figure from the saved rows")
    arguments = parser.parse_args()
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    if arguments.time_only:
        started = time.perf_counter()
        run_jobs([(0, STUDY_TAUS[0]), (0, STUDY_TAUS[-3])], 2)
        print(f"wall time for the two jobs in parallel: {time.perf_counter() - started:.0f} s")
        return
    saved = OUTPUT_FOLDER / "plateau_robustness.json"
    rows = json.loads(saved.read_text())["rows"] if arguments.summary_only else run_jobs(list_jobs(), min(arguments.workers, DEFAULT_WORKERS))
    summaries = summarise(rows)
    (OUTPUT_FOLDER / "plateau_robustness.json").write_text(json.dumps({"rows": rows, "summaries": summaries}, indent=2, default=float))
    plot_rows(rows)
    for summary in summaries:
        print(f"{summary['case']:60s} onset Da {summary['plateau_onset_da']:8.1e} (at 50 cells {summary['plateau_onset_da_at_warning_size']:8.1e}) "
              f"modes Da {summary['modes_da']:8.1e} on plateau: {summary['modes_on_plateau']} aspect within one cell: {summary['aspect_within_one_cell_on_plateau']}")


if __name__ == "__main__":
    main()
