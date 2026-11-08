"""Run the regime study: the same crystal grown at many Damkohler numbers. Results go to results/regime_study.json.

    python scripts/regime_study.py                       # taus 1 ... 1e4
    python scripts/regime_study.py --taus 1 100 1000
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from arystal.simulation.material_loader import load_material  # noqa: E402
from arystal.validation.regime_study import DEFAULT_TAUS, compute_plateau_changes, run_regime_map, run_sensitivity  # noqa: E402


def print_row(row: dict) -> None:
    """Print one row of the map as soon as it is ready."""
    print(f"tau {row['tau']:8.0f} Da {row['damkohler']:9.2e} {row['scheme']:8s} dt {row['time_step']:7.3f} steps {row['steps']:7d} wall {row['wall_seconds']:7.1f}s | "
          f"aspect {row['aspect_ratio']:.3f} r/m {row['face_ratio_r_over_m']:.3f} S_int {row['supersaturation_interface']:.3f} S_bulk {row['supersaturation_bulk']:.3f} "
          f"uniformity {row['uniformity']:.3f} facets {row['facet_fraction']:.3f} reached {row['reached_target']}", flush=True)


def main() -> None:
    """Run, print and save."""
    parser = argparse.ArgumentParser(description="Regime study.")
    parser.add_argument("--taus", type=float, nargs="+", default=list(DEFAULT_TAUS))
    parser.add_argument("--sensitivity", type=float, default=None, help="instead of the map, vary capacity, coupling and temperature at this tau (on the plateau)")
    arguments = parser.parse_args()
    if arguments.sensitivity:
        rows = run_sensitivity(load_material(), arguments.sensitivity, lambda row: print(f"{row['case']:34s} " , end="") or print_row(row))
        Path(__file__).resolve().parent.parent.joinpath("results").mkdir(exist_ok=True)
        Path(__file__).resolve().parent.parent.joinpath("results", "regime_sensitivity.json").write_text(json.dumps(rows, indent=2, default=float))
        return
    rows = run_regime_map(load_material(), tuple(arguments.taus), print_row)
    changes = compute_plateau_changes(rows)
    print("\nRelative change between consecutive Da values (plateau = small and stable):")
    for change in changes:
        print("  tau %g -> %g: " % (change["from_tau"], change["to_tau"]) + "  ".join(f"{key} {100 * value:.1f}%" for key, value in change.items() if key not in ("from_tau", "to_tau")))
    output = Path(__file__).resolve().parent.parent / "results" / "regime_study.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps({"rows": rows, "changes": changes}, indent=2, default=float))
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
