"""Numerical and physical-like parameters of the isotropic phase-field model.

Everything here is NON-DIMENSIONAL: lengths are in grid cells and time is in
arbitrary model units. The link to millimetres and seconds is made by the silica model (time_scaling.py).
"""

from dataclasses import dataclass

# 10%-90% interface width in grid cells, for a tanh profile this is about 6.2 * epsilon.
# Value 6 comes from materials/amethyst.yaml (phase_field_model.interface_width_in_grid_cells).
INTERFACE_WIDTH_OVER_EPSILON = 6.2


@dataclass(frozen=True)
class IsotropicParams:
    """All settings of an isotropic growth run.

    grid_width, grid_height: size of the domain in cells. The bottom row is the wall.
    interface_epsilon: length scale of the interface in cells (about 1 gives a 6-cell border).
    driving_force: constant push towards crystal (m). Stands in for supersaturation in the isotropic model.
    relaxation_time: how fast the phase field responds (tau). Sets the time unit.
    time_step: explicit Euler step. Must stay below tau*dx^2 / (4*epsilon^2) = 0.25 for stability.
    seed_radius: radius in cells of the initial half-disc of crystal sitting on the wall.
    """

    grid_width: int = 400
    grid_height: int = 200
    interface_epsilon: float = 1.0
    driving_force: float = 0.1
    relaxation_time: float = 1.0
    time_step: float = 0.1
    seed_radius: float = 12.0
