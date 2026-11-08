"""Live matplotlib window that shows the crystal while it grows."""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.image import AxesImage

from arystal.simulation.isotropic_run import Snapshot

# Seconds matplotlib spends handling window events after each redraw.
REDRAW_PAUSE_SECONDS = 0.001

CRYSTAL_COLORMAP = "Purples"


def build_title(snapshot: Snapshot) -> str:
    """Return the text shown above the picture for a snapshot."""
    return f"step {snapshot.step}   time {snapshot.time:.1f}   radius {snapshot.equivalent_radius:.1f} cells"


def create_window(first_snapshot: Snapshot) -> tuple[Axes, AxesImage]:
    """Open the window and draw the first frame. Wall is at the bottom of the picture."""
    plt.ion()
    _, axes = plt.subplots(figsize=(9, 5))
    image = axes.imshow(
        first_snapshot.phase_field, origin="lower", cmap=CRYSTAL_COLORMAP, vmin=0.0, vmax=1.0
    )
    axes.set_xlabel("x (cells)")
    axes.set_ylabel("y (cells), wall at y = 0")
    axes.set_title(build_title(first_snapshot))
    return axes, image


def update_window(axes: Axes, image: AxesImage, snapshot: Snapshot) -> None:
    """Replace the picture with a new snapshot and let the window redraw."""
    image.set_data(snapshot.phase_field)
    axes.set_title(build_title(snapshot))
    plt.pause(REDRAW_PAUSE_SECONDS)


def save_final_picture(snapshot: Snapshot, path: str) -> None:
    """Save the crystal of a snapshot as a PNG file (works without a window)."""
    figure, axes = plt.subplots(figsize=(9, 5))
    axes.imshow(snapshot.phase_field, origin="lower", cmap=CRYSTAL_COLORMAP, vmin=0.0, vmax=1.0)
    axes.set_title(build_title(snapshot))
    figure.savefig(path, dpi=120)
    plt.close(figure)
