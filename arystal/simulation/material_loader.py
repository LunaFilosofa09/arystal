"""Reads a material file (materials/<name>.yaml) into the engine's MaterialConstants."""

from pathlib import Path

import yaml

from arystal.engine.material_constants import MaterialConstants

MATERIALS_FOLDER = Path(__file__).resolve().parent.parent.parent / "materials"


def read_material_file(material_name: str) -> dict:
    """Return the raw contents of materials/<material_name>.yaml."""
    with open(MATERIALS_FOLDER / f"{material_name}.yaml") as file:
        return yaml.safe_load(file)


def get_value(data: dict, section: str, key: str):
    """Return the 'value' entry of data[section][key] (every constant has value/units/source/status)."""
    return data[section][key]["value"]


def load_material(material_name: str = "amethyst") -> MaterialConstants:
    """Load a material file and return the constants the engine needs."""
    data = read_material_file(material_name)
    curve_range = get_value(data, "thermodynamics", "quartz_solubility_valid_range")
    return MaterialConstants(
        solubility_a=get_value(data, "thermodynamics", "quartz_solubility_log10_molal_A"),
        solubility_b=get_value(data, "thermodynamics", "quartz_solubility_log10_molal_B"),
        solubility_min_celsius=curve_range[0],
        solubility_max_celsius=curve_range[1],
        geode_min_celsius=get_value(data, "environment", "geode_temperature_min"),
        geode_max_celsius=get_value(data, "environment", "geode_temperature_max"),
        molar_mass=get_value(data, "thermodynamics", "molar_mass_SiO2"),
        solid_density_real=get_value(data, "thermodynamics", "density_quartz"),
        diffusivity_m2_per_s=get_value(data, "transport", "silica_diffusivity_in_water"),
        solid_capacity_model=get_value(data, "model_scaling", "solid_silica_capacity_model"),
        kinetic_coupling=get_value(data, "model_scaling", "kinetic_coupling"),
        max_driving_force=get_value(data, "model_scaling", "max_driving_force"),
        r_pole_angle_to_c_degrees=get_value(data, "crystallography", "angle_r_pole_to_c_axis"),
        facet_speed_m=get_value(data, "anisotropy", "facet_speed_m"),
        facet_speed_r=get_value(data, "anisotropy", "facet_speed_r"),
        facet_speed_z=get_value(data, "anisotropy", "facet_speed_z"),
        cusp_sharpness=get_value(data, "anisotropy", "cusp_sharpness"),
        iron_molar_mass=get_value(data, "iron_model", "iron_molar_mass"),
        default_fluid_iron_ppm=get_value(data, "iron_model", "default_fluid_iron"),
        iron_diffusivity_ratio=get_value(data, "iron_model", "iron_diffusivity_ratio"),
        partition_m=get_value(data, "iron", "partition_coefficient_m"),
        partition_r=get_value(data, "iron", "partition_coefficient_r"),
        partition_z=get_value(data, "iron", "partition_coefficient_z"),
        sector_transition_width_degrees=get_value(data, "iron_model", "sector_transition_width"),
        color_iron_scale=get_value(data, "iron_model", "color_iron_to_silicon_scale"),
        thermal_noise_amplitude=get_value(data, "stochastic", "thermal_noise_amplitude"),
        seed_radius_variation=get_value(data, "stochastic", "seed_radius_variation"),
        seed_offset_std=get_value(data, "stochastic", "seed_offset_std"),
        assumed_thickness_mm=get_value(data, "mass_estimate", "assumed_thickness"),
        rate_constant_a=get_value(data, "kinetics", "quartz_rate_constant_log10_A"),
        rate_constant_b=get_value(data, "kinetics", "quartz_rate_constant_log10_B"),
        neutral_log10_k25=get_value(data, "kinetics", "quartz_rate_neutral_log10_k25"),
        neutral_activation_energy_kj=get_value(data, "kinetics", "quartz_rate_neutral_activation_energy"),
        base_log10_k25=get_value(data, "kinetics", "quartz_rate_base_log10_k25"),
        base_activation_energy_kj=get_value(data, "kinetics", "quartz_rate_base_activation_energy"),
        base_order_in_h_plus=get_value(data, "kinetics", "quartz_rate_base_order_in_h_plus"),
        fluid_ph_min=get_value(data, "environment", "fluid_ph_min"),
        fluid_ph_max=get_value(data, "environment", "fluid_ph_max"),
    )
