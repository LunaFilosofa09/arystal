"""Parameters of a growth run with dissolved silica.

Units: lengths in grid cells, time in "diffusion units" chosen so that the silica
diffusivity is exactly 1 cell^2 per time unit. Concentrations in mol/kg.
The conversion to millimetres and seconds is in time_scaling.py.
"""

from dataclasses import dataclass

from arystal.engine.anisotropy import FacetAnisotropy, compute_largest_speed_factor
from arystal.engine.iron_partition import SectorPartition, create_sector_partition
from arystal.engine.material_constants import MaterialConstants
from arystal.engine.ph_rate_law import check_ph_in_range
from arystal.engine.solubility import compute_equilibrium_concentration

# Diffusivity in model units: defines the model time unit (one time unit = dx^2 / D_real).
MODEL_DIFFUSIVITY = 1.0


@dataclass(frozen=True)
class SolutionParams:
    """All settings of a run with silica diffusion.

    grid_width, grid_height: domain size in cells (row 0 is the wall).
    container_width_mm: physical width of the domain; sets the cell size.
    interface_epsilon: interface length scale in cells (about 1 gives a 6-cell border).
    relaxation_time: tau of the phase-field equation (kinetics speed).
    time_step: explicit Euler step; must stay below 0.25 (diffusion) and tau/(4*eps^2).
    seed_radius: radius in cells of the initial half-disc.
    temperature_celsius: current fluid temperature.
    equilibrium_silica: c_eq at that temperature (mol/kg), computed from the solubility curve.
    initial_silica: starting dissolved silica everywhere (mol/kg).
    solid_capacity, kinetic_coupling, max_driving_force: copied from the material (model values).
    anisotropy: orientation-dependent growth speed (None = isotropic growth).
    initial_iron: dissolved iron everywhere at the start (mol/kg); 0 when iron is switched off.
    iron_diffusivity_ratio: D(iron) / D(silica).
    sector_partition: iron incorporation per sector (None = iron is not simulated).
    color_iron_scale: crystal Fe/Si ratio at which the rendered colour reaches 63% of its maximum.
    noise_amplitude: strength of the random term at the interface (0 = no noise).
    seed_radius_variation: relative random variation of the initial seed radius (0 = none).
    seed_offset_std: random horizontal offset of the initial seed in cells (0 = none).
    diffusion_scheme: "explicit" (default; time step limited by the diffusion), "implicit" (any time step; for slow growth, see implicit_diffusion.py)
        or "uniform" (dissolved silica and iron kept uniform: the limit of very fast diffusion, Da -> 0; see uniform_fluid.py).
    backend: "reference" (readable NumPy code, the definition of the physics) or "numba" (fast kernels, same results to rounding; see fast_kernels.py).
    fluid_ph: pH of the fluid for the pH-dependent rate law (None = Takeno law, no pH). Changes only the conversion to real time.
    """

    grid_width: int
    grid_height: int
    container_width_mm: float
    interface_epsilon: float
    relaxation_time: float
    time_step: float
    seed_radius: float
    temperature_celsius: float
    equilibrium_silica: float
    initial_silica: float
    solid_capacity: float
    kinetic_coupling: float
    max_driving_force: float
    anisotropy: FacetAnisotropy | None = None
    initial_iron: float = 0.0
    iron_diffusivity_ratio: float = 1.0
    sector_partition: SectorPartition | None = None
    color_iron_scale: float = 4e-4
    noise_amplitude: float = 0.0
    seed_radius_variation: float = 0.0
    seed_offset_std: float = 0.0
    backend: str = "reference"
    diffusion_scheme: str = "explicit"
    fluid_ph: float | None = None


# Safety factor of the explicit-Euler stability limit dt * 4 * epsilon^2 / tau_min < 1.
STABILITY_SAFETY_FACTOR = 0.9


def check_time_step_is_stable(params: "SolutionParams") -> None:
    """Raise ValueError if the time step is too large for the diffusion or the (fastest) phase-field kinetics."""
    fastest = 1.0 if params.anisotropy is None else max(1.0, compute_largest_speed_factor(params.anisotropy))
    smallest_tau = params.relaxation_time / fastest
    phase_limit = STABILITY_SAFETY_FACTOR * smallest_tau / (4.0 * params.interface_epsilon**2)
    diffusion_limit = STABILITY_SAFETY_FACTOR / (4.0 * MODEL_DIFFUSIVITY)
    limit = min(phase_limit, diffusion_limit) if params.diffusion_scheme == "explicit" else phase_limit
    if params.time_step > limit:
        raise ValueError(f"time_step {params.time_step} is too large for stability; use at most {limit:.3f}.")


def convert_iron_ppm_to_concentration(material: MaterialConstants, iron_ppm: float) -> float:
    """Convert dissolved iron from ppm by mass (mg per kg of water) into mol/kg."""
    return iron_ppm / (material.iron_molar_mass * 1000.0)


VALID_BACKENDS = ("reference", "numba")
VALID_DIFFUSION_SCHEMES = ("explicit", "implicit", "uniform")


def check_temperature_in_geode_range(material: MaterialConstants, temperature_celsius: float) -> None:
    """Raise ValueError if the temperature is outside the range allowed for geode growth."""
    low = material.geode_min_celsius
    high = material.geode_max_celsius
    if not low <= temperature_celsius <= high:
        raise ValueError(f"Temperature must be between {low} and {high} C, got {temperature_celsius} C.")


def create_solution_params(
    material: MaterialConstants,
    temperature_celsius: float,
    saturation_temperature_celsius: float,
    grid_width: int = 400,
    grid_height: int = 200,
    container_width_mm: float = 40.0,
    seed_radius: float = 15.0,
    time_step: float = 0.1,
    anisotropy: FacetAnisotropy | None = None,
    relaxation_time: float = 1.0,
    iron_ppm: float | None = None,
    noise_amplitude: float = 0.0,
    seed_radius_variation: float = 0.0,
    seed_offset_std: float = 0.0,
    backend: str = "reference",
    diffusion_scheme: str = "explicit",
    fluid_ph: float | None = None,
) -> SolutionParams:
    """Build the parameters of a run.

    If `iron_ppm` is given, iron is simulated as a trace solute with that concentration in the fluid.

    The fluid starts exactly saturated at `saturation_temperature_celsius` (it has been in
    equilibrium with quartz at that temperature) and the run happens at `temperature_celsius`.
    If the run temperature is lower, the fluid is supersaturated and the crystal grows.
    """
    check_temperature_in_geode_range(material, temperature_celsius)
    check_temperature_in_geode_range(material, saturation_temperature_celsius)
    if fluid_ph is not None:
        check_ph_in_range(material, fluid_ph)
    if diffusion_scheme not in VALID_DIFFUSION_SCHEMES:
        raise ValueError(f"diffusion_scheme must be one of {VALID_DIFFUSION_SCHEMES}, got {diffusion_scheme!r}")
    if backend not in VALID_BACKENDS:
        raise ValueError(f"backend must be one of {VALID_BACKENDS}, got {backend!r}")
    params = SolutionParams(
        grid_width=grid_width,
        grid_height=grid_height,
        container_width_mm=container_width_mm,
        interface_epsilon=1.0,
        relaxation_time=relaxation_time,
        time_step=time_step,
        seed_radius=seed_radius,
        temperature_celsius=temperature_celsius,
        equilibrium_silica=compute_equilibrium_concentration(material, temperature_celsius),
        initial_silica=compute_equilibrium_concentration(material, saturation_temperature_celsius),
        solid_capacity=material.solid_capacity_model,
        kinetic_coupling=material.kinetic_coupling,
        max_driving_force=material.max_driving_force,
        anisotropy=anisotropy,
        initial_iron=0.0 if iron_ppm is None else convert_iron_ppm_to_concentration(material, iron_ppm),
        iron_diffusivity_ratio=material.iron_diffusivity_ratio,
        sector_partition=None if iron_ppm is None else create_sector_partition(material),
        color_iron_scale=material.color_iron_scale,
        noise_amplitude=noise_amplitude,
        seed_radius_variation=seed_radius_variation,
        seed_offset_std=seed_offset_std,
        backend=backend,
        diffusion_scheme=diffusion_scheme,
        fluid_ph=fluid_ph,
    )
    check_time_step_is_stable(params)
    return params
