"""Solubility of the crystal material in the fluid, as a function of temperature.

Physically: the maximum amount of dissolved silica the fluid can hold at equilibrium with
quartz. Above that amount the fluid is supersaturated and crystal grows. Cooling lowers the
maximum, so cooling creates supersaturation.

Curve used (Rimstidt 1997): log10(m) = a / T + b, with m in mol/kg of water and T in kelvin.
The constants a and b come from the material file.
"""

import math

from arystal.engine.material_constants import MaterialConstants

KELVIN_OFFSET = 273.15  # 0 degrees Celsius in kelvin.
GRAMS_PER_KILOGRAM_TO_PPM = 1000.0  # 1 g per kg of water = 1000 mg per kg = 1000 ppm.


def convert_celsius_to_kelvin(temperature_celsius: float) -> float:
    """Return the temperature in kelvin."""
    return temperature_celsius + KELVIN_OFFSET


def check_temperature_in_curve_range(material: MaterialConstants, temperature_celsius: float) -> None:
    """Raise ValueError if the solubility curve is not valid at this temperature."""
    low = material.solubility_min_celsius
    high = material.solubility_max_celsius
    if not low <= temperature_celsius <= high:
        raise ValueError(
            f"Solubility curve is only valid from {low} to {high} C, got {temperature_celsius} C."
        )


def compute_equilibrium_concentration(material: MaterialConstants, temperature_celsius: float) -> float:
    """Return the equilibrium (saturation) silica concentration in mol/kg at a temperature in C."""
    check_temperature_in_curve_range(material, temperature_celsius)
    kelvin = convert_celsius_to_kelvin(temperature_celsius)
    return 10.0 ** (material.solubility_a / kelvin + material.solubility_b)


def convert_concentration_to_ppm(material: MaterialConstants, concentration_mol_per_kg: float) -> float:
    """Convert mol/kg of dissolved compound into ppm (mg per kg of water)."""
    return concentration_mol_per_kg * material.molar_mass * GRAMS_PER_KILOGRAM_TO_PPM


def compute_supersaturation_ratio(concentration: float, equilibrium_concentration: float) -> float:
    """Return S = c / c_eq. S = 1 is exactly saturated, S > 1 supersaturated (growth)."""
    return concentration / equilibrium_concentration


def compute_dissolution_enthalpy_kj_per_mol(material: MaterialConstants) -> float:
    """Return the enthalpy (kJ/mol) of dissolving the crystal implied by the curve's slope.

    Van 't Hoff: d(ln K)/d(1/T) = -dH/R, and log10(m) = a / T + b gives dH = -a * R * ln(10).
    Used in validation check 4 to compare against thermodynamic data.
    """
    gas_constant_kj = 8.314462618e-3  # kJ / (mol K), CODATA 2018.
    return -material.solubility_a * gas_constant_kj * math.log(10.0)
