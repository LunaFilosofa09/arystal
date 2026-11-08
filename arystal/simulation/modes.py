"""The two modes of a run, "explore" and "research", with the settings chosen from the regime and convergence studies.

Both use the regime that the evidence supports: surface-limited growth (Damkohler number Da between about 1e-7 and 1e-3), which the regime study
(docs/regime_study.md) showed to be a PLATEAU for Da below about 0.06. On that plateau the dissolved silica and iron are uniform, so the "uniform"
diffusion scheme is used (validated against the full solution) and the relaxation time is on the plateau (1e4 at 200 cells across, scaled with the
resolution so that the physical attachment speed stays the same).

  explore : 200 x 100 cells (0.2 mm per cell in a 40 mm container). Fast, for live control. Shapes are QUALITATIVE: the aspect ratio is about 13% below its
            converged value (docs/validation_report.md, check 5).
  research: 800 x 400 cells (0.05 mm per cell). The aspect ratio is within about 2% of its value at 1600 cells and the r/m face ratio within 0.5%.
            A run takes seconds to minutes.

The time step is 0.1 tau: the largest step that keeps the explicit phase-field update stable (limit about 0.14 tau for the fastest orientation), with
a margin. With uniform fluid nothing else limits it, and the interface moves only about 0.03 cells per step.
"""

import dataclasses
from dataclasses import dataclass

from arystal.simulation.run_config import RunConfig

REFERENCE_RESOLUTION = 200          # cells across the container at which BASE_TAU was found on the plateau
BASE_TAU = 10000.0
TIME_STEP_FRACTION_OF_TAU = 0.1


@dataclass(frozen=True)
class ModeSettings:
    """What a mode fixes: grid, how long a default run is (in steps), sampling and threads."""

    grid_width: int
    grid_height: int
    default_steps: int
    metrics_every_steps: int
    snapshot_every_steps: int
    threads: int
    description: str


MODE_SETTINGS = {
    "explore": ModeSettings(200, 100, 800, 10, 100, 4, "fast; shapes are qualitative (aspect ratio ~13% below its converged value)"),
    "research": ModeSettings(800, 400, 4000, 50, 500, 6, "converged to ~2% (aspect ratio) / 0.5% (face ratio); slower"),
}


def compute_relaxation_time(grid_width: int) -> float:
    """Return the relaxation time that keeps the physical attachment speed (and Da) fixed at this resolution."""
    return BASE_TAU * grid_width / REFERENCE_RESOLUTION


def build_mode_config(mode: str, **overrides) -> RunConfig:
    """Return the configuration of a mode. Any RunConfig field can be overridden by keyword (grid, duration, temperature, seed...).

    Unless overridden, tau follows the grid width, the time step is 0.1 tau and the duration is the mode's default number of steps.
    """
    if mode not in MODE_SETTINGS:
        raise ValueError(f"mode must be one of {tuple(MODE_SETTINGS)}, got {mode!r}")
    settings = MODE_SETTINGS[mode]
    grid_width = overrides.get("grid_width", settings.grid_width)
    relaxation_time = overrides.get("relaxation_time", compute_relaxation_time(grid_width))
    time_step = overrides.get("time_step", TIME_STEP_FRACTION_OF_TAU * relaxation_time)
    values = {
        "mode": mode, "grid_width": grid_width, "grid_height": overrides.get("grid_height", settings.grid_height * grid_width // settings.grid_width),
        "relaxation_time": relaxation_time, "time_step": time_step, "diffusion_scheme": "uniform",
        "duration": settings.default_steps * time_step, "metrics_every_steps": settings.metrics_every_steps,
        "snapshot_every_steps": settings.snapshot_every_steps, "threads": settings.threads, "seed_radius": 15.0 * grid_width / settings.grid_width,
    }
    values.update(overrides)
    return RunConfig(**values)


def describe_mode(mode: str) -> str:
    """Return a one-line description of a mode."""
    settings = MODE_SETTINGS[mode]
    return f"{mode}: {settings.grid_width}x{settings.grid_height} cells, {settings.description}"
