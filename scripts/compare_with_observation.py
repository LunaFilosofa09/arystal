"""Compare a saved run with measurements of a real amethyst (docs/observation_comparison.md).

    python scripts/compare_with_observation.py examples/observation_example_FICTITIOUS.yaml results/<run folder>

Writes comparison.csv and comparison.png into results/<run folder>/comparison_<sample id>/ and prints the table.
"""

import argparse
import csv
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import yaml  # noqa: E402

from arystal.comparison.compare import ROLE_MEANING, compare_sample, describe_validation_status, summarise_by_role  # noqa: E402
from arystal.comparison.observed import load_observed_sample  # noqa: E402
from arystal.comparison.simulated import get_numerical_uncertainty, measure_simulated_quantities, read_params  # noqa: E402


def parse_arguments() -> argparse.Namespace:
    """Read the observation file and the run folder."""
    parser = argparse.ArgumentParser(description="Compare a saved run with observed measurements.")
    parser.add_argument("observations", type=Path, help="YAML file of observed measurements")
    parser.add_argument("run_folder", type=Path, help="a saved run in results/")
    return parser.parse_args()


def format_row(row) -> str:
    """Return one printed line of the table."""
    mark = "yes" if row.within_tolerance else "NO"
    return (f"{row.name:28s} {row.observed:9.3f} +/- {row.observed_uncertainty:<7.3f} {row.simulated:9.3f} +/- {row.simulated_uncertainty:<7.3f} "
            f"{row.difference:+9.3f} {row.tolerance:8.3f}  {mark:4s} {row.role}")


def print_table(sample, rows) -> None:
    """Print the comparison with its honest status and the meaning of each role."""
    print(f"Sample {sample.sample_id} ({sample.source}){' -- FICTITIOUS DATA' if sample.fictitious else ''}")
    print(f"{'quantity':28s} {'observed':>20s} {'simulated':>20s} {'diff':>9s} {'tolerance':>8s}  in?  role")
    for row in rows:
        print(format_row(row))
    for role, text in summarise_by_role(rows).items():
        print(f"  {role}: {text}")
    print("STATUS: " + describe_validation_status(sample, rows))


def write_csv(rows, path: Path) -> None:
    """Save the table as CSV."""
    with open(path, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(asdict(rows[0])))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def find_observed_image(observation_file: Path) -> Path | None:
    """Return the photo named in the observation file (key `image`, relative to the file), if any and if it exists."""
    image = yaml.safe_load(observation_file.read_text()).get("image")
    path = observation_file.parent / image if image else None
    return path if path and path.exists() else None


def plot_bars(axis, rows) -> None:
    """Draw observed and simulated values with their tolerances, normalised by the observed value."""
    names = [row.name for row in rows]
    positions = range(len(rows))
    axis.errorbar(positions, [1.0] * len(rows), yerr=[2 * r.observed_uncertainty / abs(r.observed) for r in rows], fmt="o", label="observed (2 sigma)")
    axis.errorbar([p + 0.15 for p in positions], [r.simulated / r.observed for r in rows], yerr=[r.tolerance / abs(r.observed) for r in rows], fmt="s", label="simulated (tolerance)")
    axis.set_xticks(list(positions), names, rotation=40, ha="right", fontsize=7)
    axis.set_ylabel("value / observed")
    axis.legend(fontsize=7)
    axis.grid(alpha=0.3)


def plot_comparison(sample, rows, run_folder: Path, observed_image: Path | None, path: Path) -> None:
    """Save a figure: observed photo (if any), simulated crystal, and the values side by side."""
    panels = 3 if observed_image else 2
    figure, axes = plt.subplots(1, panels, figsize=(5 * panels, 4))
    index = 0
    if observed_image:
        axes[0].imshow(mpimg.imread(observed_image))
        axes[0].set_title(f"observed: {sample.sample_id}", fontsize=9)
        axes[0].axis("off")
        index = 1
    axes[index].imshow(mpimg.imread(run_folder / "final_image.png"))
    axes[index].set_title(f"simulated: {run_folder.name}", fontsize=9)
    axes[index].axis("off")
    plot_bars(axes[index + 1], rows)
    title = "FICTITIOUS DATA - code test only" if sample.fictitious else describe_validation_status(sample, rows)
    figure.suptitle(title, fontsize=10, color="red" if sample.fictitious else "black")
    figure.tight_layout()
    figure.savefig(path, dpi=110)
    plt.close(figure)


def main() -> None:
    """Load, compare, print and save."""
    arguments = parse_arguments()
    sample = load_observed_sample(arguments.observations)
    mode = read_params(arguments.run_folder)["mode"]
    rows = compare_sample(sample, measure_simulated_quantities(arguments.run_folder), lambda name, value: get_numerical_uncertainty(name, value, mode))
    print_table(sample, rows)
    output = arguments.run_folder / f"comparison_{sample.sample_id}"
    output.mkdir(exist_ok=True)
    write_csv(rows, output / "comparison.csv")
    plot_comparison(sample, rows, arguments.run_folder, find_observed_image(arguments.observations), output / "comparison.png")
    print(f"Saved in {output}. Roles: " + "; ".join(f"{role} = {text}" for role, text in ROLE_MEANING.items()))


if __name__ == "__main__":
    main()
