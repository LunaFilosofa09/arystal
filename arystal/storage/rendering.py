"""Turns the simulated fields into a colour picture of the crystal.

COLOUR IS A RESULT, NOT AN INPUT: it is computed from the iron locked into the crystal.
The mapping from iron to colour is an ASSUMPTION (documented in docs/assumptions.md):

  intensity = 1 - exp( - (Fe/Si in the crystal) / scale )        (saturating, not linear)
  colour    = pale quartz  ->  deep amethyst, blended linearly with the intensity

Why saturating and not linear: iron alone does not make amethyst; natural irradiation is also
needed (Cohen & Hassan 1974), and measured colour does not follow iron content linearly. The
model assumes a uniform and sufficient irradiation dose everywhere. The two end colours are
purely aesthetic choices.
"""

import numpy as np

# Colour of quartz with (almost) no iron, and of fully saturated amethyst colour (RGB, 0-1).
PALE_QUARTZ_RGB = np.array([0.93, 0.92, 0.95])
DEEP_AMETHYST_RGB = np.array([0.40, 0.12, 0.60])

# Colour of the fluid around the crystal.
FLUID_RGB = np.array([1.0, 1.0, 1.0])

# The picture is meant for 8-bit displays and PNG files. Rounding to 8 bits ourselves avoids a faint halo that
# plotting libraries would otherwise create by truncating (not rounding) values such as 0.99999999999998 to 254.
EIGHT_BIT_LEVELS = 255.0

# Solid fractions below this are treated as empty when computing the iron ratio (avoids dividing by ~0).
MINIMUM_SOLID_FRACTION = 1e-3


def compute_crystal_iron_ratio(
    crystal_iron: np.ndarray, solid_fraction: np.ndarray, solid_capacity: float
) -> np.ndarray:
    """Return Fe/Si (mol per mol) of the crystal in every cell: iron locked in / silica held (Cs * solid fraction)."""
    safe_solid = np.maximum(solid_fraction, MINIMUM_SOLID_FRACTION)
    return np.maximum(crystal_iron, 0.0) / (solid_capacity * safe_solid)


def compute_color_intensity(iron_ratio: np.ndarray, color_scale: float) -> np.ndarray:
    """Return the colour intensity (0 = pale quartz, 1 = deep amethyst) for a Fe/Si ratio."""
    return 1.0 - np.exp(-iron_ratio / color_scale)


def blend_colors(intensity: np.ndarray) -> np.ndarray:
    """Return an (H, W, 3) picture going from pale quartz to deep amethyst with the intensity."""
    weight = intensity[..., None]
    return (1.0 - weight) * PALE_QUARTZ_RGB + weight * DEEP_AMETHYST_RGB


def render_crystal_rgb(
    phase_field: np.ndarray, crystal_iron: np.ndarray, solid_capacity: float, color_scale: float
) -> np.ndarray:
    """Return the (H, W, 3) colour picture of the crystal over a white fluid background.

    The border follows the phase field, so the surface looks as smooth as the simulation.
    """
    solid_fraction = phase_field**2 * (3.0 - 2.0 * phase_field)
    ratio = compute_crystal_iron_ratio(crystal_iron, solid_fraction, solid_capacity)
    crystal_rgb = blend_colors(compute_color_intensity(ratio, color_scale))
    weight = np.clip(phase_field, 0.0, 1.0)[..., None]
    picture = weight * crystal_rgb + (1.0 - weight) * FLUID_RGB
    return np.round(picture * EIGHT_BIT_LEVELS) / EIGHT_BIT_LEVELS


def render_plain_crystal_rgb(phase_field: np.ndarray) -> np.ndarray:
    """Return the (H, W, 3) picture of a crystal without iron: white fluid to deep amethyst colour following the phase field."""
    weight = np.clip(phase_field, 0.0, 1.0)[..., None]
    picture = weight * DEEP_AMETHYST_RGB + (1.0 - weight) * FLUID_RGB
    return np.round(picture * EIGHT_BIT_LEVELS) / EIGHT_BIT_LEVELS
