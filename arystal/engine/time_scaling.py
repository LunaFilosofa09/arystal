"""Conversion between model units and physical units (millimetres, seconds).

Model length unit = one grid cell = container_width / grid_width.
Model time unit   = dx^2 / D_real  (so the model diffusivity is exactly 1).

IMPORTANT: this gives the *diffusion time scale* of the model. Because the model uses a
silica capacity for the crystal much smaller than the real one (see
materials/amethyst.yaml, model_scaling), the time to deposit a REAL-density crystal at the
same silica supply is longer by the factor returned by compute_density_scaling_factor.
Both numbers are order-of-magnitude only (the real diffusivity is ASSUMED).

SURFACE-LIMITED GROWTH (the regime the evidence supports, docs/kinetic_regime.md): the time a crystal takes to grow is set by how fast silica attaches to
its surface, not by diffusion. Then the model time can be tied to real time through the speed of the fastest face:
        real time per model time unit = (model speed [cells per unit] * cell size) / (real speed)
with the real speed Vm * k+(T) * (S - 1) from the verified quartz rate law (Takeno et al. 2000; or, if the run gives a fluid pH, the neutral + base law of Palandri & Kharaka 2004) and the model speed sqrt(2) * epsilon * m / tau, m = lambda ln S.
ASSUMPTIONS: the rate constant (measured for quartz in general, for neutral dilute solutions) applies to the fastest face family; surface area is the geometric area.
UNCERTAINTY: at least two orders of magnitude (pH, extrapolation to 15-60 C, face-specific rates, a secondary source for the constant); see docs/kinetic_regime.md.
"""

import math

from arystal.engine.material_constants import MaterialConstants
from arystal.engine.ph_rate_law import compute_ph_rate_constant
from arystal.engine.solution_params import SolutionParams

KELVIN_OFFSET = 273.15
MILLIMETRES_PER_METRE = 1000.0
GRAMS_PER_CM3_TO_G_PER_KG_WATER = 1000.0  # 1 g/cm3 = 1000 g per litre ~ 1000 g per kg of water.


def compute_cell_size_mm(params: SolutionParams) -> float:
    """Return the physical size of one grid cell in millimetres."""
    return params.container_width_mm / params.grid_width


def compute_model_time_unit_seconds(material: MaterialConstants, params: SolutionParams) -> float:
    """Return how many real seconds one model time unit lasts (dx^2 / D)."""
    cell_size_m = compute_cell_size_mm(params) / MILLIMETRES_PER_METRE
    return cell_size_m**2 / material.diffusivity_m2_per_s


def compute_real_solid_capacity(material: MaterialConstants) -> float:
    """Return the real silica capacity of the crystal in mol per kg of water (density / molar mass)."""
    return material.solid_density_real * GRAMS_PER_CM3_TO_G_PER_KG_WATER / material.molar_mass


def compute_density_scaling_factor(material: MaterialConstants) -> float:
    """Return (real capacity) / (model capacity): how much longer real-density growth would take."""
    return compute_real_solid_capacity(material) / material.solid_capacity_model


def convert_model_time_to_diffusion_seconds(
    material: MaterialConstants, params: SolutionParams, model_time: float
) -> float:
    """Return the diffusion time scale in seconds for a model time."""
    return model_time * compute_model_time_unit_seconds(material, params)


def compute_quartz_rate_constant(material: MaterialConstants, temperature_celsius: float, fluid_ph: float | None = None) -> float:
    """Return the quartz rate constant (mol m-2 s-1) at a temperature (C).

    Without a pH: Takeno et al. (2000), log10(k+) = a + b / T (neutral dilute solution). With a pH: the neutral + base law of
    Palandri & Kharaka (2004), see ph_rate_law.py.
    """
    if fluid_ph is not None:
        return compute_ph_rate_constant(material, temperature_celsius, fluid_ph)
    return 10.0 ** (material.rate_constant_a + material.rate_constant_b / (temperature_celsius + KELVIN_OFFSET))


def compute_real_front_speed(material: MaterialConstants, temperature_celsius: float, supersaturation: float, fluid_ph: float | None = None) -> float:
    """Return the real speed (m/s) of a quartz surface from the rate law: molar volume * k * (S - 1). Zero if S <= 1. pH optional (None = Takeno law)."""
    molar_volume = material.molar_mass * 1e-3 / (material.solid_density_real * 1e3)  # m3 per mol
    return molar_volume * compute_quartz_rate_constant(material, temperature_celsius, fluid_ph) * max(supersaturation - 1.0, 0.0)


def compute_kinetic_seconds_per_model_time(material: MaterialConstants, params: SolutionParams, supersaturation: float) -> float:
    """Return how many real seconds one model time unit lasts, if growth is surface-limited (nan if S <= 1: nothing grows).

    Matches the model speed of the fastest face with the real speed from the rate law (see the module description).
    """
    real_speed = compute_real_front_speed(material, params.temperature_celsius, supersaturation, params.fluid_ph)
    force = params.kinetic_coupling * math.log(supersaturation) if supersaturation > 0 else 0.0
    force = min(max(force, -params.max_driving_force), params.max_driving_force)
    model_speed = math.sqrt(2.0) * params.interface_epsilon * force / params.relaxation_time  # cells per model time unit
    if real_speed <= 0.0 or model_speed <= 0.0:
        return float("nan")
    return model_speed * compute_cell_size_mm(params) / MILLIMETRES_PER_METRE / real_speed
