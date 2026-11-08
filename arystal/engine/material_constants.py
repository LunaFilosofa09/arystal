"""The material constants the engine needs, as a plain container.

The engine never reads files. A loader (arystal/simulation/material_loader.py) fills this
from materials/<name>.yaml, so nothing about a specific material is hardcoded in the engine.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialConstants:
    """Constants of one material, already converted to the units used by the engine.

    solubility_a (K), solubility_b: equilibrium solubility log10(m) = a / T + b,
        m in mol per kg of water, T in kelvin.
    solubility_min_celsius, solubility_max_celsius: temperature range where that curve is valid.
    geode_min_celsius, geode_max_celsius: temperatures allowed for the growth environment.
    molar_mass: g/mol of the dissolved compound.
    solid_density_real: g/cm3 of the real crystal.
    diffusivity_m2_per_s: diffusion coefficient of the dissolved compound in the fluid (m2/s).
    solid_capacity_model: model value (mol/kg) of the extra silica held by crystal vs fluid.
    kinetic_coupling: lambda in m = lambda * ln(c / c_eq).
    max_driving_force: largest allowed |m| in the phase-field equation.
    r_pole_angle_to_c_degrees: angle between the pole of the r face and the c-axis.
    facet_speed_m, facet_speed_r, facet_speed_z: relative normal growth speeds of the face families.
    cusp_sharpness: beta of the smooth maximum that rounds the cusps (larger = sharper facets).
    iron_molar_mass: g/mol of iron.
    default_fluid_iron_ppm: default dissolved iron in the fluid, ppm by mass.
    iron_diffusivity_ratio: D(iron) / D(silica) in the fluid.
    partition_m, partition_r, partition_z: molar Fe/Si distribution coefficient per face family.
    sector_transition_width_degrees: smoothing width of the sector assignment, in surface-normal angle.
    color_iron_scale: crystal Fe/Si ratio at which the colour reaches 63% of its maximum.
    thermal_noise_amplitude: strength of the random term at the interface.
    seed_radius_variation: relative random variation of the initial seed radius.
    seed_offset_std: random horizontal offset (cells) of the initial seed.
    assumed_thickness_mm: thickness assumed to turn the 2D area into a mass.
    rate_constant_a, rate_constant_b: quartz dissolution rate constant log10(k+) = a + b / T (mol m-2 s-1, T in K); the net precipitation rate is k+ (S - 1).
    neutral_log10_k25, neutral_activation_energy_kj: neutral term of the pH-dependent quartz law (log10 mol m-2 s-1 at 25 C; kJ/mol).
    base_log10_k25, base_activation_energy_kj, base_order_in_h_plus: base (OH-catalysed) term: log10 rate constant at 25 C and pH 0, kJ/mol,
        and the order n in a_H+^n (Palandri & Kharaka 2004). Used only when a run gives a fluid pH.
    fluid_ph_min, fluid_ph_max: allowed range of that fluid pH.
    """

    solubility_a: float
    solubility_b: float
    solubility_min_celsius: float
    solubility_max_celsius: float
    geode_min_celsius: float
    geode_max_celsius: float
    molar_mass: float
    solid_density_real: float
    diffusivity_m2_per_s: float
    solid_capacity_model: float
    kinetic_coupling: float
    max_driving_force: float
    r_pole_angle_to_c_degrees: float
    facet_speed_m: float
    facet_speed_r: float
    facet_speed_z: float
    cusp_sharpness: float
    iron_molar_mass: float
    default_fluid_iron_ppm: float
    iron_diffusivity_ratio: float
    partition_m: float
    partition_r: float
    partition_z: float
    sector_transition_width_degrees: float
    color_iron_scale: float
    thermal_noise_amplitude: float
    seed_radius_variation: float
    seed_offset_std: float
    assumed_thickness_mm: float
    rate_constant_a: float
    rate_constant_b: float
    neutral_log10_k25: float
    neutral_activation_energy_kj: float
    base_log10_k25: float
    base_activation_energy_kj: float
    base_order_in_h_plus: float
    fluid_ph_min: float
    fluid_ph_max: float
