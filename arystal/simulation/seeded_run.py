"""A run driven by one integer seed: builds the parameters, the random streams and the stepping loop.

Reproducibility: the seed is split into two independent random streams (one for the initial-seed variations,
one for the thermal noise) with numpy's SeedSequence. The same seed, settings and material file give the
identical result, bit for bit, on the same machine and library versions.
"""

import numpy as np

from arystal.engine.anisotropy import create_facet_anisotropy_from_material
from arystal.engine.material_constants import MaterialConstants
from arystal.engine.solution_growth import create_initial_state
from arystal.engine.solution_params import SolutionParams, check_temperature_in_geode_range, create_solution_params
from arystal.simulation.run_config import RunConfig

NUMBER_OF_STREAMS = 2


def create_rng_streams(seed: int) -> tuple[np.random.Generator, np.random.Generator]:
    """Return two independent random generators (seed variation, thermal noise) derived from one seed."""
    first, second = np.random.SeedSequence(seed).spawn(NUMBER_OF_STREAMS)
    return np.random.Generator(np.random.PCG64(first)), np.random.Generator(np.random.PCG64(second))


def build_params(config: RunConfig, material: MaterialConstants) -> SolutionParams:
    """Turn a run configuration and the material constants into the engine's parameters (refuses a renewal temperature outside the geode range)."""
    if config.renewal_interval is not None:
        check_temperature_in_geode_range(material, config.renewal_saturation_celsius)
    anisotropy = create_facet_anisotropy_from_material(material) if config.anisotropy_on else None
    return create_solution_params(
        material, config.temperature_celsius, config.saturation_temperature_celsius,
        grid_width=config.grid_width, grid_height=config.grid_height, container_width_mm=config.container_width_mm,
        seed_radius=config.seed_radius, time_step=config.time_step, anisotropy=anisotropy,
        relaxation_time=config.relaxation_time, iron_ppm=config.iron_ppm,
        noise_amplitude=material.thermal_noise_amplitude if config.noise_on else 0.0,
        seed_radius_variation=material.seed_radius_variation if config.noise_on else 0.0,
        seed_offset_std=material.seed_offset_std if config.noise_on else 0.0,
        backend=config.backend, diffusion_scheme=config.diffusion_scheme, fluid_ph=config.fluid_ph,
    )


def compute_total_steps(config: RunConfig) -> int:
    """Return the number of time steps of the run."""
    return int(round(config.duration / config.time_step))


def prepare_run(config: RunConfig, material: MaterialConstants):
    """Return (params, initial state, noise generator) for a run."""
    params = build_params(config, material)
    seed_rng, noise_rng = create_rng_streams(config.seed)
    return params, create_initial_state(params, seed_rng), noise_rng


def draw_noise(noise_rng: np.random.Generator, params: SolutionParams) -> np.ndarray | None:
    """Return one array of standard normal numbers for the interface noise, or None when noise is off.

    Single precision (float32) is plenty for a random term and takes half the time to generate; both backends use the same array.
    """
    if params.noise_amplitude <= 0.0:
        return None
    return noise_rng.standard_normal((params.grid_height, params.grid_width), dtype=np.float32)
