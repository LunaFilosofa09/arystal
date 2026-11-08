"""final_image.png: the rendered crystal at the end of a run."""

from pathlib import Path

from matplotlib.figure import Figure

from arystal.engine.solution_growth import SolutionState
from arystal.engine.solution_params import SolutionParams
from arystal.storage.rendering import render_crystal_rgb

PURPLE_COLORMAP = "Purples"


def save_final_image(folder: Path, state: SolutionState, params: SolutionParams, title: str) -> Path:
    """Render the final crystal (colour = incorporated iron when iron is simulated) and save it as PNG."""
    figure = Figure(figsize=(9, 5))
    axes = figure.subplots()
    if params.sector_partition is None:
        axes.imshow(state.phase_field, origin="lower", cmap=PURPLE_COLORMAP, vmin=0, vmax=1)
    else:
        axes.imshow(render_crystal_rgb(state.phase_field, state.crystal_iron, params.solid_capacity, params.color_iron_scale), origin="lower")
    axes.set_xlabel("x (cells)")
    axes.set_ylabel("y (cells), wall at y = 0")
    axes.set_title(title)
    path = Path(folder) / "final_image.png"
    figure.savefig(path, dpi=120)
    return path
