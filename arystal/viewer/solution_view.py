"""Live matplotlib window for growth from solution: crystal on the left, supersaturation on the right."""

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.image import AxesImage

from arystal.engine.solution_params import SolutionParams
from arystal.simulation.solution_run import SolutionSnapshot
from arystal.storage.rendering import render_crystal_rgb

# Seconds matplotlib spends handling window events after each redraw.
REDRAW_PAUSE_SECONDS = 0.001

CRYSTAL_COLORMAP = "Purples"
SUPERSATURATION_COLORMAP = "RdBu_r"

# The supersaturation map is centred on S = 1 (saturated): blue = undersaturated, red = supersaturated.
SUPERSATURATION_MAP_HALF_RANGE = 0.8


def build_title(snapshot: SolutionSnapshot, params: SolutionParams) -> str:
    """Return the text above the pictures for a snapshot."""
    domain_area = params.grid_width * params.grid_height
    fraction = 100.0 * snapshot.crystal_area / domain_area
    return (
        f"T = {params.temperature_celsius:.0f} C   step {snapshot.step}   time {snapshot.time:.0f}   "
        f"crystal = {fraction:.2f}% of the container"
    )


def compute_supersaturation_map(snapshot: SolutionSnapshot, params: SolutionParams):
    """Return S - 1 = c / c_eq - 1 for every cell (0 = saturated)."""
    return snapshot.silica / params.equilibrium_silica - 1.0


def build_crystal_picture(snapshot: SolutionSnapshot, params: SolutionParams):
    """Return what the left panel shows: the coloured crystal if iron is simulated, else the phase field."""
    if params.sector_partition is None:
        return snapshot.phase_field
    return render_crystal_rgb(
        snapshot.phase_field, snapshot.crystal_iron, params.solid_capacity, params.color_iron_scale
    )


def create_window(snapshot: SolutionSnapshot, params: SolutionParams) -> tuple[Figure, AxesImage, AxesImage]:
    """Open the window with both panels and return the figure and the two images."""
    plt.ion()
    figure, (left, right) = plt.subplots(2, 1, figsize=(8, 8))
    crystal_image = left.imshow(
        build_crystal_picture(snapshot, params), origin="lower", cmap=CRYSTAL_COLORMAP, vmin=0, vmax=1
    )
    left.set_title("crystal (colour = incorporated iron; wall at the bottom)" if params.sector_partition else "crystal (wall at the bottom)")
    super_image = right.imshow(
        compute_supersaturation_map(snapshot, params),
        origin="lower",
        cmap=SUPERSATURATION_COLORMAP,
        vmin=-SUPERSATURATION_MAP_HALF_RANGE,
        vmax=SUPERSATURATION_MAP_HALF_RANGE,
    )
    right.set_title("supersaturation  S - 1  (red = growth, blue = dissolution)")
    figure.colorbar(super_image, ax=right, shrink=0.8)
    figure.suptitle(build_title(snapshot, params))
    return figure, crystal_image, super_image


def update_window(
    figure: Figure, crystal_image: AxesImage, super_image: AxesImage,
    snapshot: SolutionSnapshot, params: SolutionParams,
) -> None:
    """Replace both pictures with a new snapshot and let the window redraw."""
    crystal_image.set_data(build_crystal_picture(snapshot, params))
    super_image.set_data(compute_supersaturation_map(snapshot, params))
    figure.suptitle(build_title(snapshot, params))
    plt.pause(REDRAW_PAUSE_SECONDS)


def save_final_picture(snapshot: SolutionSnapshot, params: SolutionParams, path: str) -> None:
    """Save both panels of a snapshot as a PNG file (works without a window)."""
    figure, _, _ = create_window(snapshot, params)
    figure.savefig(path, dpi=110)
    plt.close(figure)
