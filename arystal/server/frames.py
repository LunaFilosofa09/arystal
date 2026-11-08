"""The frames sent to the viewer: a picture of the crystal, a picture of the supersaturation, and the current metrics."""

import base64
import io
import math

import matplotlib
import numpy as np
from matplotlib.image import imsave

from arystal.simulation.controlled_run import ControlledRun
from arystal.simulation.metrics_recorder import MetricsRecorder
from arystal.storage.rendering import render_crystal_rgb, render_plain_crystal_rgb

# Pictures wider than this are shown at lower resolution (every n-th cell) to keep frames small.
MAXIMUM_FRAME_WIDTH = 400

# The supersaturation picture is centred on S = 1 (saturated); S - 1 from -0.8 to +0.8 spans the colour map.
SUPERSATURATION_HALF_RANGE = 0.8
SUPERSATURATION_COLORMAP = "RdBu_r"


def sanitize_value(value):
    """Return the value as JSON allows: nan and infinity become None."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def sanitize_row(row: dict) -> dict:
    """Return a metrics row with JSON-safe values."""
    return {key: sanitize_value(value) for key, value in row.items()}


def downsample(picture: np.ndarray) -> np.ndarray:
    """Keep every n-th cell so the picture is at most MAXIMUM_FRAME_WIDTH wide."""
    stride = max(1, math.ceil(picture.shape[1] / MAXIMUM_FRAME_WIDTH))
    return picture[::stride, ::stride]


def encode_png_base64(picture: np.ndarray) -> str:
    """Encode an (H, W, 3) picture (values 0-1, row 0 = bottom) as a PNG, in base64 text."""
    buffer = io.BytesIO()
    imsave(buffer, downsample(picture), format="png", origin="lower")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def build_crystal_picture(controller: ControlledRun) -> np.ndarray:
    """Return the colour picture of the crystal (colour = incorporated iron when iron is simulated)."""
    state, params = controller.state, controller.params
    if params.sector_partition is None:
        return render_plain_crystal_rgb(state.phase_field)
    return render_crystal_rgb(state.phase_field, state.crystal_iron, params.solid_capacity, params.color_iron_scale)


def build_supersaturation_picture(controller: ControlledRun) -> np.ndarray:
    """Return the picture of S - 1 = c / c_eq - 1 (red = growth, blue = dissolution)."""
    excess = controller.state.silica / controller.params.equilibrium_silica - 1.0
    scaled = np.clip(0.5 + 0.5 * excess / SUPERSATURATION_HALF_RANGE, 0.0, 1.0)
    return matplotlib.colormaps[SUPERSATURATION_COLORMAP](scaled)[..., :3]


def build_frame(sequence: int, controller: ControlledRun, recorder: MetricsRecorder) -> dict:
    """Return one frame: the pictures, the state of the run and the current metrics (all JSON-safe)."""
    recorder.update_params(controller.params)
    metrics = sanitize_row(recorder.record(controller.step, controller.state, controller.injected_iron, controller.injected_silica))
    return {
        "type": "frame",
        "sequence": sequence,
        "status": controller.status,
        "step": controller.step,
        "time": controller.time,
        "duration": controller.total_steps * controller.params.time_step,
        "temperature_celsius": controller.params.temperature_celsius,
        "iron_ppm": controller.current_iron_ppm,
        "metrics": metrics,
        "crystal_png": encode_png_base64(build_crystal_picture(controller)),
        "supersaturation_png": encode_png_base64(build_supersaturation_picture(controller)),
    }
