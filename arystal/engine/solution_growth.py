"""Growth of the crystal from a silica solution: phase field coupled to silica diffusion.

Two main fields evolve together (plus the optional iron fields, see iron_incorporation.py):

  phi  (1 = crystal, 0 = fluid):
      tau(n) * d(phi)/dt = epsilon^2 * laplacian(phi) + phi*(1-phi)*(phi - 1/2 + m)
      tau(n) = tau / g(orientation)   (g = 1 when anisotropy is off, see anisotropy.py)
      m = lambda * ln(c / c_eq(T))        (clipped to +-max_driving_force)
      Supersaturated fluid (c > c_eq) gives m > 0 and the crystal grows;
      undersaturated fluid gives m < 0 and the crystal dissolves.

  c  (dissolved silica, mol/kg):
      d(c)/dt = (diffusion of c through the fluid) - Cs * d(h(phi))/dt
      Every bit of fluid that turns into crystal removes Cs of silica from the solution.
      Cs is the silica held by crystal beyond what the same volume of fluid holds.

Conservation: the total  sum( c + Cs * h(phi) )  does not change, because diffusion only moves
silica between cells and the growth term takes from c exactly what it adds to Cs*h.
"""

from dataclasses import dataclass

import numpy as np

from arystal.engine.grid import create_half_disc_seed
from arystal.engine.anisotropic_phase_field import advance_phase_field
from arystal.engine.iron_incorporation import compute_new_iron_fields
from arystal.engine.iron_partition import NUMBER_OF_FAMILIES
from arystal.engine.silica_transport import compute_diffusion_change, compute_solid_fraction
from arystal.engine.solution_params import MODEL_DIFFUSIVITY, SolutionParams

# Smallest concentration allowed inside the logarithm, so ln() never sees zero or negative values.
MINIMUM_CONCENTRATION_RATIO = 1e-6


@dataclass(frozen=True)
class SolutionState:
    """The two fields of the simulation at one moment."""

    phase_field: np.ndarray
    silica: np.ndarray
    iron: np.ndarray
    crystal_iron: np.ndarray
    sector_iron: np.ndarray
    sector_silica: np.ndarray


def draw_seed_variation(params: SolutionParams, seed_rng: np.random.Generator | None) -> tuple[float, float]:
    """Return (seed radius, horizontal offset in cells) of this run: the nominal values plus small random variations.

    With no random generator, or zero variation amplitudes, the nominal seed is returned and nothing is drawn.
    """
    if seed_rng is None:
        return params.seed_radius, 0.0
    radius_noise, offset_noise = seed_rng.standard_normal(2)
    radius = params.seed_radius * (1.0 + params.seed_radius_variation * radius_noise)
    return radius, params.seed_offset_std * offset_noise


def create_initial_state(params: SolutionParams, seed_rng: np.random.Generator | None = None) -> SolutionState:
    """Return the starting state: a seed on the wall in fluid with uniform silica.

    The fluid holds `initial_silica`; the small amount of dissolved silica inside the seed is
    set to the equilibrium value, so the seed does not start with trapped supersaturated fluid.
    If a random generator is given, the seed radius and position vary slightly (seed variation).
    """
    radius, offset = draw_seed_variation(params, seed_rng)
    phase_field = create_half_disc_seed(
        params.grid_width, params.grid_height, radius, params.interface_epsilon, offset
    )
    solid = compute_solid_fraction(phase_field)
    silica = params.initial_silica * (1.0 - solid) + params.equilibrium_silica * solid
    iron = np.full_like(silica, params.initial_iron)
    sector_shape = (NUMBER_OF_FAMILIES,) + silica.shape if params.sector_partition is not None else (NUMBER_OF_FAMILIES, 1, 1)
    return SolutionState(
        phase_field=phase_field, silica=silica, iron=iron, crystal_iron=np.zeros_like(silica),
        sector_iron=np.zeros(sector_shape), sector_silica=np.zeros(sector_shape),
    )


def compute_driving_force(silica: np.ndarray, params: SolutionParams) -> np.ndarray:
    """Return m = lambda * ln(c / c_eq) for every cell, limited to +-max_driving_force.

    Physically: the chemical driving force of growth (it is proportional to ln of the
    supersaturation ratio). Positive when the fluid holds more silica than it can at equilibrium.
    """
    ratio = np.maximum(silica / params.equilibrium_silica, MINIMUM_CONCENTRATION_RATIO)
    force = params.kinetic_coupling * np.log(ratio)
    return np.clip(force, -params.max_driving_force, params.max_driving_force)


def compute_noise_term(phase_field: np.ndarray, noise: np.ndarray, params: SolutionParams) -> np.ndarray:
    """Return the random change of phi in one step: sigma * sqrt(dt / tau) * 4 phi (1 - phi) * N(0,1).

    The factor 4 phi (1 - phi) is 1 at the interface and 0 in the bulk, so only the surface is disturbed.
    The factor 1 / sqrt(tau) keeps the noise in proportion to the deterministic dynamics, which are divided
    by tau (fluctuation-dissipation: a slower interface is also disturbed more slowly). Without it, a large tau
    would make the noise relatively huge and seed spurious crystals in the fluid.
    """
    interface_weight = 4.0 * phase_field * (1.0 - phase_field)
    return params.noise_amplitude * np.sqrt(params.time_step / params.relaxation_time) * interface_weight * noise


def compute_new_phase_field(state: SolutionState, params: SolutionParams, noise: np.ndarray | None = None) -> np.ndarray:
    """Return phi after one time step, with the driving force taken from the local silica.

    Growth speed depends on the surface orientation when params.anisotropy is set. If `noise` (an array of
    standard normal numbers) is given and params.noise_amplitude > 0, the random interface term is added.
    """
    driving_force = compute_driving_force(state.silica, params)
    new_phase_field = advance_phase_field(
        state.phase_field, driving_force, params.anisotropy,
        params.interface_epsilon, params.relaxation_time, params.time_step,
    )
    if noise is not None and params.noise_amplitude > 0.0:
        new_phase_field = new_phase_field + compute_noise_term(state.phase_field, noise, params)
    return new_phase_field


def compute_new_silica(
    state: SolutionState, new_phase_field: np.ndarray, params: SolutionParams
) -> np.ndarray:
    """Return the silica after one time step: diffusion minus what the new crystal absorbed."""
    old_solid = compute_solid_fraction(state.phase_field)
    new_solid = compute_solid_fraction(new_phase_field)
    diffusion = compute_diffusion_change(state.silica, old_solid, MODEL_DIFFUSIVITY)
    absorbed = params.solid_capacity * (new_solid - old_solid)
    return state.silica + params.time_step * diffusion - absorbed


def advance_iron(state: SolutionState, new_phase_field: np.ndarray, params: SolutionParams) -> tuple:
    """Return (fluid iron, crystal iron, iron by sector, silica by sector) after one step; unchanged when iron is off."""
    if params.sector_partition is None:
        return state.iron, state.crystal_iron, state.sector_iron, state.sector_silica
    return compute_new_iron_fields(
        state.iron, state.crystal_iron, state.sector_iron, state.sector_silica,
        state.silica, state.phase_field, new_phase_field, params,
    )


def advance_one_step(state: SolutionState, params: SolutionParams, noise: np.ndarray | None = None, in_place: bool = False) -> SolutionState:
    """Advance all fields by one time step and return the new state. `noise`: optional random numbers for the interface.

    With params.backend == "numba" the fast kernels do the work (same calculation, see fast_kernels.py); otherwise the
    readable NumPy code below, which is the definition of the physics. With `in_place` (fast backend only) the crystal arrays of
    `state` are updated directly, which is faster but means the old state must not be used afterwards.
    """
    if params.diffusion_scheme == "implicit":
        return advance_one_step_implicit(state, params, noise)
    if params.diffusion_scheme == "uniform":
        from arystal.engine.uniform_fluid import advance_one_step_uniform

        return advance_one_step_uniform(state, params, noise, in_place)
    if params.backend == "numba":
        from arystal.engine.fast_step import advance_one_step_fast

        return advance_one_step_fast(state, params, noise, in_place)
    new_phase_field = compute_new_phase_field(state, params, noise)
    new_silica = compute_new_silica(state, new_phase_field, params)
    iron, crystal_iron, sector_iron, sector_silica = advance_iron(state, new_phase_field, params)
    return SolutionState(
        phase_field=new_phase_field, silica=new_silica, iron=iron, crystal_iron=crystal_iron,
        sector_iron=sector_iron, sector_silica=sector_silica,
    )


def advance_one_step_implicit(state: SolutionState, params: SolutionParams, noise: np.ndarray | None = None) -> SolutionState:
    """Advance one time step with implicit diffusion of silica and iron (see implicit_diffusion.py); the phase field uses the chosen backend."""
    import dataclasses

    from arystal.engine.implicit_diffusion import advance_iron_implicit, advance_silica_implicit
    from arystal.engine.iron_incorporation import compute_iron_exchange

    if params.backend == "numba":
        from arystal.engine.fast_step import advance_phase_field_fast

        new_phase_field = advance_phase_field_fast(state, params, noise)
    else:
        new_phase_field = compute_new_phase_field(state, params, noise)
    old_solid, new_solid = compute_solid_fraction(state.phase_field), compute_solid_fraction(new_phase_field)
    new_silica = advance_silica_implicit(state.silica, old_solid, new_solid, params)
    if params.sector_partition is None:
        return dataclasses.replace(state, phase_field=new_phase_field, silica=new_silica)
    exchange, crystal_iron, sector_iron, sector_silica = compute_iron_exchange(
        state.iron, state.crystal_iron, state.sector_iron, state.sector_silica, state.silica, state.phase_field, new_phase_field, params
    )
    return dataclasses.replace(
        state, phase_field=new_phase_field, silica=new_silica, iron=advance_iron_implicit(state.iron, exchange, old_solid, params),
        crystal_iron=crystal_iron, sector_iron=sector_iron, sector_silica=sector_silica,
    )


def compute_total_silica(state: SolutionState, params: SolutionParams) -> float:
    """Return the total silica in the container: dissolved plus held by the crystal (model units).

    This is the quantity that must stay constant (validation check 3).
    """
    solid = compute_solid_fraction(state.phase_field)
    return float(np.sum(state.silica + params.solid_capacity * solid))


def compute_total_iron(state: SolutionState) -> float:
    """Return the total iron in the container: dissolved plus locked in the crystal (model units).

    This is the quantity that must stay constant (validation check 3, iron part).
    """
    return float(np.sum(state.iron + state.crystal_iron))
