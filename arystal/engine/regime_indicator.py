"""Rough indicator of the growth regime of a configured run (diffusion-limited or surface-limited).

Da_model = (speed set by surface attachment) / (speed set by silica diffusion), in model units, for the
initial supersaturation and a crystal of a given size. Da << 1: surface-limited (flat faces, uniform supersaturation);
Da >> 1: diffusion-limited (depletion halo, round shapes). The evidence (docs/kinetic_regime.md) says real growth has
Da between about 1e-7 and 1e-3.
"""

import math

from arystal.engine.solution_params import MODEL_DIFFUSIVITY, SolutionParams

# Model Da above this means attachment is fast compared with the silica supply.
DIFFUSION_LIMITED_THRESHOLD = 1.0


def compute_initial_driving_force(params: SolutionParams) -> float:
    """Return m = lambda * ln(S0), limited to the maximum allowed driving force, for the initial supersaturation."""
    force = params.kinetic_coupling * math.log(params.initial_silica / params.equilibrium_silica)
    return min(max(force, -params.max_driving_force), params.max_driving_force)


def compute_attachment_speed(params: SolutionParams) -> float:
    """Return the speed (cells per model time unit) of a flat front for the initial driving force: sqrt(2) eps m / tau."""
    return math.sqrt(2.0) * params.interface_epsilon * compute_initial_driving_force(params) / params.relaxation_time


def compute_diffusion_speed(params: SolutionParams, crystal_size_cells: float) -> float:
    """Return D * (c0 - c_eq) / (Cs * L): steady speed of a crystal of size L fed only by diffusion."""
    excess = params.initial_silica - params.equilibrium_silica
    return MODEL_DIFFUSIVITY * excess / (params.solid_capacity * crystal_size_cells)


def compute_model_damkohler(params: SolutionParams, crystal_size_cells: float) -> float:
    """Return Da_model = attachment speed / diffusion speed (nan if there is no supersaturation)."""
    diffusion = compute_diffusion_speed(params, crystal_size_cells)
    return compute_attachment_speed(params) / diffusion if diffusion > 0 else float("nan")
