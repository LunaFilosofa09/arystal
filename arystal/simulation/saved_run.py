"""Runs a simulation and saves everything to its own results folder."""

import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path

import numpy as np

from arystal.engine.material_constants import MaterialConstants
from arystal.engine.regime_indicator import compute_model_damkohler
from arystal.engine.solution_params import SolutionParams
from arystal.engine.time_scaling import compute_cell_size_mm, compute_density_scaling_factor
from arystal.simulation.material_loader import load_material
from arystal.simulation.controlled_run import ControlledRun
from arystal.simulation.metrics_recorder import MetricsRecorder
from arystal.simulation.run_config import RunConfig
from arystal.simulation.timeline import TimelineEvent, event_to_dict, read_scheduled_events
from arystal.storage.images import save_final_image
from arystal.storage.metrics_io import write_metrics_csv
from arystal.storage.plots import save_metric_plots
from arystal.storage.result_folder import DEFAULT_RESULTS_ROOT, create_result_folder
from arystal.storage.serialization import write_json
from arystal.storage.snapshots import save_final_state, save_snapshot

PROJECT_FOLDER = Path(__file__).resolve().parent.parent.parent
SOFTWARE_VERSION = "arystal engine v1 (phase 1)"

# Da below this is on the plateau of the regime study (docs/regime_study.md).
PLATEAU_DAMKOHLER = 0.06

# Crystal size (cells) at which the regime indicator is evaluated for the summary.
INDICATOR_CRYSTAL_SIZE_CELLS = 50.0


def read_git_revision() -> str:
    """Return the short git revision of the project (and '+uncommitted' if there are local changes), or 'unknown'."""
    try:
        revision = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_FOLDER, capture_output=True, text=True, check=True).stdout.strip()
        changed = subprocess.run(["git", "status", "--porcelain"], cwd=PROJECT_FOLDER, capture_output=True, text=True, check=True).stdout.strip()
        return revision + ("+uncommitted" if changed else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build_params_record(config: RunConfig, params: SolutionParams, material: MaterialConstants, scheduled_events: list[TimelineEvent]) -> dict:
    """Return the content of params.json: everything needed to repeat the run."""
    return {
        "created": datetime.now().isoformat(timespec="seconds"),
        "software": {
            "version": SOFTWARE_VERSION, "git_revision": read_git_revision(),
            "python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform(),
        },
        "config": config,
        "seed": config.seed,
        "mode": config.mode,
        "solution_params": params,
        "material_constants": material,
        "events_scheduled_at_start": [event_to_dict(event) for event in scheduled_events],
    }


def describe_rate_law(params: SolutionParams) -> str:
    """Return one sentence saying which quartz rate law converts model time to real time in this run."""
    if params.fluid_ph is None:
        return "Rate law: Takeno et al. (2000), neutral dilute solution, no pH."
    return (
        f"Rate law: neutral + base terms of Palandri & Kharaka (2004) at pH {params.fluid_ph:g} (base term measured for dissolution; "
        "its printed constant is inconsistent in the source; pH of geode fluids unknown; docs/kinetic_regime.md section 10)."
    )


def build_scientific_status(config: RunConfig, params: SolutionParams, material: MaterialConstants) -> dict:
    """Return the caveats that must travel with every result: what is assumed and what is provisional."""
    damkohler = compute_model_damkohler(params, INDICATOR_CRYSTAL_SIZE_CELLS)
    if damkohler <= PLATEAU_DAMKOHLER:
        regime = (
            f"Model Da = {damkohler:.2g} (crystal of {INDICATOR_CRYSTAL_SIZE_CELLS:.0f} cells): surface-limited, on the plateau of the regime study (Da below about {PLATEAU_DAMKOHLER}), "
            "where the shape no longer depends on Da. This is the regime the evidence supports (real Da about 1e-7 to 1e-3; docs/kinetic_regime.md, docs/regime_study.md)."
        )
    else:
        regime = (
            f"WARNING: model Da = {damkohler:.2g} (crystal of {INDICATOR_CRYSTAL_SIZE_CELLS:.0f} cells) is ABOVE the plateau: growth is partly or fully diffusion-limited, which the evidence "
            "does not support for geode crystals (real Da about 1e-7 to 1e-3). Shapes from such a run are not predictions of amethyst habit."
        )
    return {
        "kinetic_regime": regime,
        "resolution": f"Grid {params.grid_width} x {params.grid_height}: aspect ratio converges slowly with resolution (about 13% below its converged value at 200 cells across, 2% at 800; docs/validation_report.md, check 5).",
        "time": (
            "time_model is model time. time_kinetic_years (metrics.csv) converts it with the verified quartz rate law, valid only in the surface-limited regime, assuming the rate constant applies to the "
            f"fastest face family; uncertain by at least two orders of magnitude. The model crystal holds {compute_density_scaling_factor(material):.0f}x less silica than a real one."
            f" {describe_rate_law(params)}"
        ),
        "face_speeds": "IMPOSED: relative growth speeds of the m, r, z faces are ASSUMED (no data found); the habit is a consequence of them.",
        "iron": "IMPOSED: incorporation coefficients, fluid iron and colour law are ASSUMED; only the order r > z > m is supported (qualitatively).",
        "noise": "Noise and seed variations are a modelling device with ASSUMED amplitudes; the spread between seeds is not calibrated.",
        "mass": "Mass is the 2D area times an ASSUMED thickness at real density: an order of magnitude only.",
    }


def build_summary(
    config: RunConfig, params: SolutionParams, material: MaterialConstants, rows: list[dict],
    wall_seconds: float, cpu_seconds: float, total_steps: int, saved_snapshots: int, plots: list[str],
) -> dict:
    """Return the content of summary.json: headline results, conservation, compute cost and caveats."""
    final = rows[-1]
    domain_area = params.grid_width * params.grid_height
    return {
        "headline_results": {
            "final_model_time": final["time_model"],
            "crystal_fraction_of_container": final["crystal_area_cells"] / domain_area,
            "crystal_area_mm2": final["crystal_area_mm2"],
            "crystal_mass_mg_estimate": final["crystal_mass_mg_estimate"],
            "aspect_ratio": final["aspect_ratio"],
            "mean_iron_ratio": final["mean_iron_ratio"],
            "iron_ratio_by_sector": {family: final[f"iron_ratio_{family}"] for family in ("m", "r", "z")},
            "supersaturation_interface": final["supersaturation_interface"],
            "supersaturation_bulk": final["supersaturation_bulk"],
            "cell_size_mm": compute_cell_size_mm(params),
        },
        "conservation": {
            "max_abs_silica_relative_drift": max(abs(row["silica_relative_drift"]) for row in rows),
            "max_abs_iron_relative_drift": max(abs(row["iron_relative_drift"]) for row in rows),
        },
        "compute_cost": {
            "wall_clock_seconds": wall_seconds, "cpu_seconds": cpu_seconds, "steps": total_steps,
            "steps_per_second": total_steps / wall_seconds if wall_seconds > 0 else float("nan"),
            "grid_cells": domain_area,
        },
        "outputs": {"metric_rows": len(rows), "snapshots_saved": saved_snapshots, "plots": plots},
        "scientific_status": build_scientific_status(config, params, material),
    }


class RunSaver:
    """Writes the files of a run folder while the run advances and when it ends."""

    def __init__(
        self, controller: ControlledRun, results_root: Path = DEFAULT_RESULTS_ROOT,
        scheduled_events: list[TimelineEvent] | None = None, folder_name: str | None = None,
    ) -> None:
        """Create the run folder and write params.json."""
        self.config = controller.config
        self.material = controller.material
        self.folder = create_result_folder(results_root, folder_name)
        self.recorder = MetricsRecorder(controller.params, controller.material, controller.state)
        self.rows: list[dict] = []
        self.snapshots_saved = 0
        self.wall_seconds = 0.0
        self.cpu_seconds = 0.0
        write_json(self.folder / "params.json", build_params_record(controller.config, controller.params, controller.material, scheduled_events or []))

    def steps_to_next_sample(self, step: int) -> int:
        """Return how many steps remain until the next moment at which metrics are recorded."""
        return self.config.metrics_every_steps - step % self.config.metrics_every_steps

    def is_sample_step(self, step: int) -> bool:
        """True if metrics are recorded at this step."""
        return step % self.config.metrics_every_steps == 0

    def sample(self, controller: ControlledRun) -> None:
        """Record a metrics row, and a snapshot when it is due."""
        self.recorder.update_params(controller.params)
        self.rows.append(self.recorder.record(controller.step, controller.state, controller.injected_iron, controller.injected_silica))
        if controller.step % self.config.snapshot_every_steps == 0:
            save_snapshot(self.folder, controller.step, controller.time, controller.state)
            self.snapshots_saved += 1

    def add_compute_cost(self, wall_seconds: float, cpu_seconds: float) -> None:
        """Add time spent computing steps (waiting, pauses and drawing are not counted)."""
        self.wall_seconds += wall_seconds
        self.cpu_seconds += cpu_seconds

    def finish(self, controller: ControlledRun) -> Path:
        """Write the end-of-run files and return the run folder."""
        if self.rows[-1]["step"] != controller.step:
            self.sample(controller)
        write_json(self.folder / "timeline.json", controller.build_timeline_record())
        save_final_state(self.folder, controller.state)
        write_metrics_csv(self.folder / "metrics.csv", self.rows)
        plots = save_metric_plots(self.folder, self.rows)
        title = f"T = {controller.params.temperature_celsius:.0f} C, seed {self.config.seed}, model time {controller.time:.0f}"
        save_final_image(self.folder, controller.state, controller.params, title)
        summary = build_summary(
            self.config, controller.params, self.material, self.rows, self.wall_seconds, self.cpu_seconds,
            controller.step, self.snapshots_saved, plots,
        )
        summary["timeline"] = {"events": len(controller.timeline), "iron_injected_model_units": controller.injected_iron, "silica_injected_model_units": controller.injected_silica}
        summary["conservation_note"] = "Iron drift discounts the iron added by live changes of the fluid iron."
        write_json(self.folder / "summary.json", summary)
        return self.folder


def advance_and_sample(controller: ControlledRun, saver: RunSaver, chunk: int) -> int:
    """Advance up to `chunk` steps (never past a sampling moment), recording metrics when one is reached. Returns the steps taken."""
    started, cpu_started = time.perf_counter(), time.process_time()
    steps = controller.advance(min(chunk, saver.steps_to_next_sample(controller.step)))
    saver.add_compute_cost(time.perf_counter() - started, time.process_time() - cpu_started)
    if steps and saver.is_sample_step(controller.step):
        saver.sample(controller)
    return steps


def run_and_save(
    config: RunConfig, results_root: Path = DEFAULT_RESULTS_ROOT, material: MaterialConstants | None = None,
    scheduled_events: list[TimelineEvent] | None = None, folder_name: str | None = None,
) -> Path:
    """Run the simulation described by `config` (replaying `scheduled_events`, if any) and save all its results. Returns the run folder."""
    material = material or load_material()
    controller = ControlledRun(config, material, scheduled_events or [])
    saver = RunSaver(controller, results_root, scheduled_events, folder_name)
    saver.sample(controller)
    while not controller.is_finished():
        advance_and_sample(controller, saver, config.metrics_every_steps)
    return saver.finish(controller)


def load_run_for_replay(folder: Path) -> tuple[RunConfig, list[TimelineEvent]]:
    """Return (configuration, recorded timeline events) of a saved run, ready to be run again exactly."""
    from arystal.simulation.run_config import create_config_from_dict
    from arystal.storage.serialization import read_json

    config = create_config_from_dict(read_json(Path(folder) / "params.json")["config"])
    return config, read_scheduled_events(read_json(Path(folder) / "timeline.json"))
