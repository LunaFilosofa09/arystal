"""Command-line entry point: crystal growth from a silica solution.

The fluid starts saturated at --saturation-temperature and the run happens at --temperature.
If the run is colder, the fluid is supersaturated and the crystal grows.

Examples:
    python scripts/run_growth.py                                   # live window, 40 C
    python scripts/run_growth.py --temperature 20 --duration 8000
    python scripts/run_growth.py --no-window --png out.png --duration 3000
    python scripts/run_growth.py --iron-ppm 1.0                    # with iron and colour
    python scripts/run_growth.py --isotropic                       # no facets, for comparison
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt  # noqa: E402

from arystal.engine.anisotropy import create_facet_anisotropy_from_material  # noqa: E402
from arystal.engine.solution_params import create_solution_params  # noqa: E402
from arystal.engine.time_scaling import (  # noqa: E402
    compute_cell_size_mm,
    compute_density_scaling_factor,
    convert_model_time_to_diffusion_seconds,
)
from arystal.simulation.material_loader import load_material  # noqa: E402
from arystal.simulation.solution_run import iterate_solution_growth  # noqa: E402
from arystal.viewer.solution_view import create_window, save_final_picture, update_window  # noqa: E402

SECONDS_PER_HOUR = 3600.0


def parse_arguments() -> argparse.Namespace:
    """Read the command-line options."""
    parser = argparse.ArgumentParser(description="Crystal growth from a silica solution.")
    parser.add_argument("--temperature", type=float, default=40.0, help="run temperature in C (15-60)")
    parser.add_argument("--saturation-temperature", type=float, default=60.0,
                        help="temperature in C at which the fluid was saturated (sets the initial silica)")
    parser.add_argument("--duration", type=float, default=20000.0, help="model time units to simulate")
    parser.add_argument("--steps-per-frame", type=int, default=200)
    parser.add_argument("--relaxation-time", type=float, default=1.0,
                        help="tau: larger = slower attachment kinetics (surface-limited growth shows facets); default 1 is above the plateau (diffusion-limited), see docs/regime_study.md")
    parser.add_argument("--time-step", type=float, default=0.1)
    parser.add_argument("--grid-width", type=int, default=400)
    parser.add_argument("--grid-height", type=int, default=200)
    parser.add_argument("--iron-ppm", type=float, default=None,
                        help="dissolved iron in the fluid, ppm by mass (omit to leave iron out; 1.0 is the material default)")
    parser.add_argument("--isotropic", action="store_true", help="switch the facet anisotropy off (round growth)")
    parser.add_argument("--no-window", action="store_true", help="run without the live window")
    parser.add_argument("--png", default=None, help="save the final picture to this PNG file")
    return parser.parse_args()


def print_time_report(material, params, model_time: float) -> None:
    """Print what the simulated time means in physical units, with its caveat."""
    seconds = convert_model_time_to_diffusion_seconds(material, params, model_time)
    factor = compute_density_scaling_factor(material)
    if params.sector_partition is not None:
        print("Colour is computed from the incorporated iron with ASSUMED coefficients and an ASSUMED colour law; it is not a prediction of real amethyst colour.")
    print("Face growth speeds (m:r:z) are ASSUMED inputs: the habit shown is imposed by them, not predicted.")
    print(f"Cell size: {compute_cell_size_mm(params):.3f} mm.")
    print(f"Simulated {model_time:.0f} model time units = {seconds / SECONDS_PER_HOUR:.1f} h of diffusion time.")
    print(f"WARNING: the model crystal holds {factor:.0f}x less silica than a real one, so depositing a")
    print("real-density crystal at the same supply would take far longer. Order-of-magnitude only.")


def run(arguments: argparse.Namespace) -> None:
    """Run the growth, drawing live if requested, and optionally save the last frame."""
    material = load_material()
    anisotropy = None if arguments.isotropic else create_facet_anisotropy_from_material(material)
    params = create_solution_params(
        material, arguments.temperature, arguments.saturation_temperature, anisotropy=anisotropy,
        relaxation_time=arguments.relaxation_time, time_step=arguments.time_step, iron_ppm=arguments.iron_ppm,
        grid_width=arguments.grid_width, grid_height=arguments.grid_height,
    )
    window = None
    last = None
    for snapshot in iterate_solution_growth(params, arguments.steps_per_frame, arguments.duration):
        last = snapshot
        if arguments.no_window:
            continue
        if window is None:
            window = create_window(snapshot, params)
        else:
            update_window(*window, snapshot, params)
    print(f"Finished at step {last.step}: crystal fills {100 * last.crystal_area / (params.grid_width * params.grid_height):.2f}% of the container.")
    print_time_report(material, params, last.time)
    if arguments.png:
        save_final_picture(last, params, arguments.png)
        print(f"Saved {arguments.png}")
    if window is not None:
        plt.ioff()
        plt.show()


if __name__ == "__main__":
    run(parse_arguments())
