"""Command-line entry point: grow an isotropic half-disc on the wall.

Examples:
    python scripts/run_isotropic.py                 # live window
    python scripts/run_isotropic.py --no-window --png final.png
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt  # noqa: E402

from arystal.engine.isotropic_params import IsotropicParams  # noqa: E402
from arystal.simulation.isotropic_run import iterate_growth  # noqa: E402
from arystal.viewer.live_view import create_window, save_final_picture, update_window  # noqa: E402

DEFAULT_STEPS_PER_FRAME = 40


def parse_arguments() -> argparse.Namespace:
    """Read the command-line options."""
    parser = argparse.ArgumentParser(description="Isotropic crystal growth on a wall.")
    parser.add_argument("--no-window", action="store_true", help="run without the live window")
    parser.add_argument("--png", default=None, help="save the final picture to this PNG file")
    parser.add_argument("--driving-force", type=float, default=IsotropicParams.driving_force)
    parser.add_argument("--steps-per-frame", type=int, default=DEFAULT_STEPS_PER_FRAME)
    return parser.parse_args()


def run(arguments: argparse.Namespace) -> None:
    """Run the growth, drawing live if requested, and optionally save the last frame."""
    params = IsotropicParams(driving_force=arguments.driving_force)
    axes = image = last_snapshot = None
    for snapshot in iterate_growth(params, arguments.steps_per_frame):
        last_snapshot = snapshot
        if arguments.no_window:
            continue
        if image is None:
            axes, image = create_window(snapshot)
        update_window(axes, image, snapshot)
    print(f"Finished at step {last_snapshot.step}, radius {last_snapshot.equivalent_radius:.1f} cells")
    if arguments.png:
        save_final_picture(last_snapshot, arguments.png)
        print(f"Saved {arguments.png}")
    if not arguments.no_window:
        plt.ioff()
        plt.show()


if __name__ == "__main__":
    run(parse_arguments())
