"""The live viewer with controls: crystal, supersaturation, sliders and buttons.

The controls only send requests to the ControlledRun (arystal/simulation/controlled_run.py); they never touch the
simulation directly. The handlers are plain functions so they can be tested without a screen.
"""

from dataclasses import dataclass

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.image import AxesImage
from matplotlib.text import Text
from matplotlib.widgets import Button, Slider

from arystal.metrics.shape import compute_crystal_area
from arystal.simulation.controlled_run import PAUSED, ControlledRun
from arystal.simulation.timeline import DURATION, IRON, TEMPERATURE
from arystal.viewer.solution_view import (
    CRYSTAL_COLORMAP,
    SUPERSATURATION_COLORMAP,
    SUPERSATURATION_MAP_HALF_RANGE,
    build_crystal_picture,
    compute_supersaturation_map,
)

# Seconds matplotlib spends handling window events after each redraw.
REDRAW_PAUSE_SECONDS = 0.001

# The "extend" button adds this fraction of the current total duration.
EXTEND_FRACTION = 0.5

# Largest dissolved iron (ppm) the slider offers. ASSUMED upper limit of the slider only.
MAXIMUM_IRON_PPM = 5.0

# Slider steps.
TEMPERATURE_STEP = 0.5
IRON_STEP = 0.1


@dataclass
class ControlPanel:
    """All the pieces of the window."""

    figure: Figure
    crystal_image: AxesImage
    supersaturation_image: AxesImage
    temperature_slider: Slider
    iron_slider: Slider | None
    pause_button: Button
    stop_button: Button
    extend_button: Button
    status_text: Text


def handle_temperature_change(controller: ControlledRun, value: float) -> None:
    """The temperature slider moved: ask the run to change the temperature."""
    controller.request_change(TEMPERATURE, float(value))


def handle_iron_change(controller: ControlledRun, value: float) -> None:
    """The iron slider moved: ask the run to change the dissolved iron."""
    controller.request_change(IRON, float(value))


def handle_pause_click(controller: ControlledRun) -> None:
    """The pause/resume button was clicked: pause if running, resume if paused."""
    if controller.status == PAUSED:
        controller.request_resume()
    else:
        controller.request_pause()


def handle_stop_click(controller: ControlledRun) -> None:
    """The stop button was clicked: end the run now (it will be saved)."""
    controller.request_stop()


def handle_extend_click(controller: ControlledRun) -> None:
    """The extend button was clicked: lengthen the total duration by a fraction of itself."""
    current = controller.total_steps * controller.params.time_step
    controller.request_change(DURATION, current * (1.0 + EXTEND_FRACTION))


def build_status_line(controller: ControlledRun) -> str:
    """Return the text above the pictures: state of the run and the key numbers."""
    area = compute_crystal_area(controller.state.phase_field)
    domain = controller.params.grid_width * controller.params.grid_height
    duration = controller.total_steps * controller.params.time_step
    return (
        f"[{controller.status.upper()}]  T = {controller.params.temperature_celsius:.1f} C   step {controller.step}   "
        f"time {controller.time:.0f} / {duration:.0f}   crystal = {100 * area / domain:.2f}% of the container"
    )


def create_slider(figure: Figure, position: list[float], label: str, low: float, high: float, value: float, step: float) -> Slider:
    """Add a slider to the figure at `position` (left, bottom, width, height in figure fractions)."""
    return Slider(figure.add_axes(position), label, low, high, valinit=value, valstep=step)


def create_button(figure: Figure, position: list[float], label: str) -> Button:
    """Add a button to the figure."""
    return Button(figure.add_axes(position), label)


def draw_pictures(controller: ControlledRun, left: Axes, right: Axes, figure: Figure) -> tuple[AxesImage, AxesImage]:
    """Draw the crystal (left) and the supersaturation map (right); return their images."""
    crystal = left.imshow(build_crystal_picture(controller.state, controller.params), origin="lower", cmap=CRYSTAL_COLORMAP, vmin=0, vmax=1)
    left.set_title("crystal (wall at the bottom)" if controller.params.sector_partition is None else "crystal (colour = incorporated iron)")
    supersaturation = right.imshow(
        compute_supersaturation_map(controller.state, controller.params), origin="lower", cmap=SUPERSATURATION_COLORMAP,
        vmin=-SUPERSATURATION_MAP_HALF_RANGE, vmax=SUPERSATURATION_MAP_HALF_RANGE,
    )
    right.set_title("supersaturation  S - 1  (red = growth, blue = dissolution)")
    figure.colorbar(supersaturation, ax=right, shrink=0.8)
    return crystal, supersaturation


def create_control_panel(controller: ControlledRun) -> ControlPanel:
    """Open the window with pictures, sliders and buttons, and connect the controls to the run."""
    plt.ion()
    figure = plt.figure(figsize=(9, 10))
    left = figure.add_axes([0.08, 0.60, 0.80, 0.30])
    right = figure.add_axes([0.08, 0.27, 0.80, 0.28])
    crystal, supersaturation = draw_pictures(controller, left, right, figure)
    material = controller.material
    temperature = create_slider(figure, [0.15, 0.17, 0.70, 0.03], "T (C)", material.geode_min_celsius, material.geode_max_celsius, controller.params.temperature_celsius, TEMPERATURE_STEP)
    temperature.on_changed(lambda value: handle_temperature_change(controller, value))
    iron = None
    if controller.current_iron_ppm is not None:
        iron = create_slider(figure, [0.15, 0.12, 0.70, 0.03], "Fe (ppm)", 0.0, MAXIMUM_IRON_PPM, controller.current_iron_ppm, IRON_STEP)
        iron.on_changed(lambda value: handle_iron_change(controller, value))
    pause = create_button(figure, [0.15, 0.04, 0.20, 0.05], "Pause / Resume")
    pause.on_clicked(lambda _: handle_pause_click(controller))
    extend = create_button(figure, [0.40, 0.04, 0.20, 0.05], "Extend +50%")
    extend.on_clicked(lambda _: handle_extend_click(controller))
    stop = create_button(figure, [0.65, 0.04, 0.20, 0.05], "Stop and save")
    stop.on_clicked(lambda _: handle_stop_click(controller))
    status = figure.text(0.5, 0.95, build_status_line(controller), ha="center")
    return ControlPanel(figure, crystal, supersaturation, temperature, iron, pause, stop, extend, status)


def update_control_panel(panel: ControlPanel, controller: ControlledRun) -> None:
    """Redraw the pictures and the status line with the current state of the run."""
    panel.crystal_image.set_data(build_crystal_picture(controller.state, controller.params))
    panel.supersaturation_image.set_data(compute_supersaturation_map(controller.state, controller.params))
    panel.status_text.set_text(build_status_line(controller))
    plt.pause(REDRAW_PAUSE_SECONDS)
