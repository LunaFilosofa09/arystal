"""Command-line entry point: a live window with controls. The run is saved when it ends.

Controls in the window: sliders for temperature and dissolved iron, buttons to pause/resume, extend the duration and
stop. Every change is recorded in the timeline (timeline.json) at the exact step it took effect, so the run can be
repeated exactly with:  python scripts/run_saved.py --replay results/<folder>

Examples:
    python scripts/run_live.py
    python scripts/run_live.py --temperature 30 --seed 4
    python scripts/run_live.py --mode research
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt  # noqa: E402

from arystal.simulation.controlled_run import ControlledRun  # noqa: E402
from arystal.simulation.cli_options import add_run_options, config_from_arguments  # noqa: E402
from arystal.simulation.material_loader import load_material  # noqa: E402
from arystal.simulation.run_config import RunConfig  # noqa: E402
from arystal.simulation.saved_run import RunSaver, advance_and_sample  # noqa: E402
from arystal.viewer.control_panel import create_control_panel, update_control_panel  # noqa: E402

# Steps computed between two looks at the controls, and minimum seconds between two redraws.
STEPS_PER_TURN = 20
SECONDS_BETWEEN_REDRAWS = 0.15
SECONDS_WAITING_WHEN_PAUSED = 0.05


def parse_arguments() -> argparse.Namespace:
    """Read the command-line options."""
    parser = argparse.ArgumentParser(description="Live simulation with controls.")
    add_run_options(parser)
    return parser.parse_args()


def run_live(config: RunConfig) -> Path:
    """Run with the live window until the run finishes or the window is closed; save and return the folder."""
    controller = ControlledRun(config, load_material())
    saver = RunSaver(controller)
    saver.sample(controller)
    panel = create_control_panel(controller)
    last_redraw = 0.0
    while not controller.is_finished():
        if not plt.fignum_exists(panel.figure.number):
            controller.request_stop()
        plt.pause(0.001)
        controller.process_commands()
        steps = advance_and_sample(controller, saver, STEPS_PER_TURN)
        if steps == 0 and not controller.is_finished():
            plt.pause(SECONDS_WAITING_WHEN_PAUSED)
        if time.perf_counter() - last_redraw > SECONDS_BETWEEN_REDRAWS and plt.fignum_exists(panel.figure.number):
            update_control_panel(panel, controller)
            last_redraw = time.perf_counter()
    folder = saver.finish(controller)
    if plt.fignum_exists(panel.figure.number):
        update_control_panel(panel, controller)
    return folder


def main() -> None:
    """Run the live session, then print where the results are and what was changed."""
    config = config_from_arguments(parse_arguments())
    folder = run_live(config)
    print(f"Results saved in {folder}")
    print(f"Repeat it exactly with: python scripts/run_saved.py --replay {folder}")
    if plt.get_fignums():
        plt.ioff()
        plt.show()


if __name__ == "__main__":
    main()
