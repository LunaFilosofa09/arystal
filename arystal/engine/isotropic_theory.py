"""Exact predictions of the isotropic model, used to check the simulation (validation check 1).

For the equation in phase_field.py, a flat front moves at speed
    v_flat = sqrt(2) * epsilon * m / tau
and a curved front of radius R is slowed down by its curvature (surface tension):
    v(R) = v_flat - epsilon^2 / (tau * R)
Below the critical radius R_c = epsilon / (sqrt(2) * m) the seed shrinks instead of growing.
Speeds are in cells per model time unit.
"""

import math

from arystal.engine.isotropic_params import IsotropicParams


def compute_flat_front_speed(params: IsotropicParams) -> float:
    """Return the speed of a perfectly flat front (cells per time unit)."""
    return math.sqrt(2.0) * params.interface_epsilon * params.driving_force / params.relaxation_time


def compute_critical_radius(params: IsotropicParams) -> float:
    """Return the radius (cells) below which a seed dissolves instead of growing."""
    return params.interface_epsilon / (math.sqrt(2.0) * params.driving_force)


def compute_front_speed_at_radius(params: IsotropicParams, radius: float) -> float:
    """Return the predicted speed of a circular front of the given radius (cells per time unit)."""
    curvature_slowdown = params.interface_epsilon**2 / (params.relaxation_time * radius)
    return compute_flat_front_speed(params) - curvature_slowdown
