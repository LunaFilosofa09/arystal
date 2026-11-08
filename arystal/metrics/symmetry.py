"""Measurements of mirror symmetry about the c-axis (the vertical line through the middle of the grid)."""

import numpy as np

# phi = 0.5 is where we say the crystal surface is.
CRYSTAL_LEVEL = 0.5


def mirror_field_about_c_axis(field: np.ndarray) -> np.ndarray:
    """Return the field flipped left-right (the grid is symmetric about its middle column)."""
    return field[:, ::-1]


def compute_mirror_asymmetry(field: np.ndarray) -> float:
    """Return the largest absolute difference between a field and its left-right mirror image.

    0 means perfectly symmetric about the c-axis.
    """
    return float(np.abs(field - mirror_field_about_c_axis(field)).max())


def compute_crystal_mask(phase_field: np.ndarray) -> np.ndarray:
    """Return a True/False map of the cells that belong to the crystal (phi > 1/2)."""
    return phase_field > CRYSTAL_LEVEL


def compute_area_asymmetry_fraction(phase_field: np.ndarray) -> float:
    """Return the share of the crystal area that has no mirror partner.

    Counts the cells that are crystal on one side but not on the mirrored side, divided by
    the crystal area. Unlike the pointwise difference it is easy to interpret: 0.02 = 2%.
    """
    mask = compute_crystal_mask(phase_field)
    mismatch = mask != mirror_field_about_c_axis(mask)
    return float(mismatch.sum() / max(mask.sum(), 1))
