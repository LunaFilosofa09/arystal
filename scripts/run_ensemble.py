"""Command-line entry point: an ensemble of replicas (same settings and timeline, different seeds).

The ensemble is built from a saved run: its configuration and its recorded timeline (live changes included) are used for every replica.

Examples:
    python scripts/run_ensemble.py --from results/2026-10-11_120000_ab12cd
    python scripts/run_ensemble.py --from results/<folder> --replicas 10 --workers 5
    python scripts/run_ensemble.py --mode research --temperature 20       # no saved run: use these settings, no timeline
"""

import argparse
import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from arystal.simulation.ensemble import DEFAULT_NUMBER_OF_REPLICAS, DEFAULT_WORKERS, EnsembleSettings, run_ensemble  # noqa: E402
from arystal.simulation.cli_options import add_run_options, config_from_arguments  # noqa: E402
from arystal.simulation.saved_run import load_run_for_replay  # noqa: E402
from arystal.storage.serialization import read_json  # noqa: E402


def parse_arguments() -> argparse.Namespace:
    """Read the command-line options."""
    parser = argparse.ArgumentParser(description="Run an ensemble of replicas.")
    parser.add_argument("--from", dest="source", default=None, help="results folder of a saved run: its settings and timeline are used")
    parser.add_argument("--replicas", type=int, default=DEFAULT_NUMBER_OF_REPLICAS)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="parallel processes (default 5; one core stays free)")
    parser.add_argument("--base-seed", type=int, default=None, help="the replica seeds are derived from it (default: the seed of the saved run)")
    add_run_options(parser)
    return parser.parse_args()


def build_base(arguments: argparse.Namespace):
    """Return (config, timeline events, base seed) from a saved run (--from) or from the options (threads: 1 per replica)."""
    if arguments.source:
        config, events = load_run_for_replay(Path(arguments.source))
        return config, events, config.seed
    config = dataclasses.replace(config_from_arguments(arguments), threads=1)
    return config, [], config.seed


def main() -> None:
    """Run the ensemble, printing each replica as it finishes, and report where the results are."""
    arguments = parse_arguments()
    config, events, base_seed = build_base(arguments)
    if arguments.base_seed is not None:
        base_seed = arguments.base_seed
    settings = EnsembleSettings(number_of_replicas=arguments.replicas, workers=arguments.workers, base_seed=base_seed)
    print(f"Ensemble of {settings.number_of_replicas} replicas, {settings.workers} workers, {len(events)} timeline events replayed in each")
    folder = run_ensemble(config, events, settings, on_replica_done=lambda result: print(f"  replica {result['index'] + 1} (seed {result['seed']}) done in {result['wall_seconds']:.0f} s"))
    summary = read_json(folder / "ensemble_summary.json")
    area = summary["statistics_of_final_metrics"]["crystal_area_mm2"]
    cost = summary["compute_cost"]
    print(f"Results saved in {folder}")
    print(f"Final crystal area: mean {area['mean']:.1f} mm2, std {area['std']:.2f}, min {area['min']:.1f}, max {area['max']:.1f}")
    print(f"Wall-clock time {cost['ensemble_wall_clock_seconds']:.0f} s; on average {cost['average_concurrency']:.1f} replicas ran at once (this is not the speed-up: each replica is slower when several share the machine)")
    print("Caveats stored in ensemble_summary.json (scientific_status): the spread between replicas depends on ASSUMED noise amplitudes.")


if __name__ == "__main__":
    main()
