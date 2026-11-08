"""Command-line entry point: run a simulation and save everything to results/<date>_<time>_<id>/.

Examples:
    python scripts/run_saved.py --seed 1                          # explore mode (200 x 100, a few seconds)
    python scripts/run_saved.py --mode research --seed 1          # research mode (800 x 400, converged, about 2 minutes)
    python scripts/run_saved.py --seed 1 --no-iron --no-noise
    python scripts/run_saved.py --replay results/2026-10-11_120000_ab12cd     # repeat a saved run exactly, including its timeline
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from arystal.simulation.cli_options import add_run_options, config_from_arguments  # noqa: E402
from arystal.simulation.saved_run import load_run_for_replay, run_and_save  # noqa: E402
from arystal.storage.serialization import read_json  # noqa: E402


def parse_arguments() -> argparse.Namespace:
    """Read the command-line options."""
    parser = argparse.ArgumentParser(description="Run a simulation and save all results.")
    add_run_options(parser)
    parser.add_argument("--replay", default=None, help="repeat the run saved in this results folder (uses its params.json and timeline.json)")
    return parser.parse_args()


def main() -> None:
    """Run, save, and print where the results are and the caveats that go with them."""
    arguments = parse_arguments()
    if arguments.replay:
        config, events = load_run_for_replay(Path(arguments.replay))
        folder = run_and_save(config, scheduled_events=events)
        print(f"Replayed {arguments.replay} with {len(events)} recorded timeline events")
    else:
        folder = run_and_save(config_from_arguments(arguments))
    summary = read_json(folder / "summary.json")
    print(f"Results saved in {folder}")
    print(f"Wall-clock time: {summary['compute_cost']['wall_clock_seconds']:.1f} s for {summary['compute_cost']['steps']} steps")
    print("Caveats stored in summary.json:")
    for name, text in summary["scientific_status"].items():
        print(f"  - {name}: {text}")


if __name__ == "__main__":
    main()
