"""The quartz growth rate constant with a dependence on the fluid pH (optional).

Physics: quartz reacts with water through two parallel mechanisms (Palandri & Kharaka 2004, USGS OFR 2004-1068, eq. 6 and Table 4):
    k(T, pH) = k_neutral(T) + k_base(T) * a_H+^n,    each term k(T) = k(25 C) * exp(-E / R * (1/T - 1/298.15))
The neutral term does not depend on pH. The base term is catalysed by hydroxide: with n = -0.5 it grows 10^0.5 = 3.16 times
per pH unit, so it matters only in alkaline fluids. The net growth rate per unit surface is k * (S - 1), as in the Takeno law
(p = q = 1, as assumed by the source). a_H+ is taken as 10^-pH (activity coefficient 1).

What this changes in a run: only the conversion of model time to real time (time_kinetic_years). On the plateau of the regime study
the simulated shape does not depend on the absolute rate. Without a pH the engine keeps the Takeno law (time_scaling.py).

Caveats (docs/kinetic_regime.md, section 10): the base term was measured for dissolution; its printed constant is inconsistent in the
source (log k = -16.29 used, -17.98 possible); sodium catalysis is not included; the pH of geode fluids is unknown.
"""

import math

from arystal.engine.material_constants import MaterialConstants

GAS_CONSTANT_J_PER_MOL_K = 8.314462618  # J mol-1 K-1, CODATA value (standard constant).
REFERENCE_KELVIN = 298.15  # 25 C: the temperature at which Palandri & Kharaka give their rate constants.
KELVIN_OFFSET = 273.15
JOULES_PER_KILOJOULE = 1000.0


def compute_arrhenius_factor(activation_energy_kj: float, temperature_celsius: float) -> float:
    """Return exp(-E/R (1/T - 1/298.15)): how much faster (> 1) or slower (< 1) a reaction is at T than at 25 C.

    activation_energy_kj in kJ/mol, temperature in C; dimensionless result.
    """
    kelvin = temperature_celsius + KELVIN_OFFSET
    exponent = -activation_energy_kj * JOULES_PER_KILOJOULE / GAS_CONSTANT_J_PER_MOL_K * (1.0 / kelvin - 1.0 / REFERENCE_KELVIN)
    return math.exp(exponent)


def compute_neutral_rate_constant(material: MaterialConstants, temperature_celsius: float) -> float:
    """Return the neutral-mechanism rate constant of quartz (mol m-2 s-1) at a temperature (C). Independent of pH."""
    at_25_celsius = 10.0 ** material.neutral_log10_k25
    return at_25_celsius * compute_arrhenius_factor(material.neutral_activation_energy_kj, temperature_celsius)


def compute_base_rate_constant(material: MaterialConstants, temperature_celsius: float, fluid_ph: float) -> float:
    """Return the base (hydroxide-catalysed) rate constant of quartz (mol m-2 s-1) at a temperature (C) and pH.

    Physically: in alkaline water OH- ions help break Si-O bonds; the term is k_base(T) * a_H+^n with a_H+ = 10^-pH.
    """
    at_25_celsius_ph_0 = 10.0 ** material.base_log10_k25
    hydrogen_activity = 10.0 ** (-fluid_ph)
    temperature_factor = compute_arrhenius_factor(material.base_activation_energy_kj, temperature_celsius)
    return at_25_celsius_ph_0 * temperature_factor * hydrogen_activity ** material.base_order_in_h_plus


def compute_ph_rate_constant(material: MaterialConstants, temperature_celsius: float, fluid_ph: float) -> float:
    """Return the total quartz rate constant k (mol m-2 s-1): neutral term + base term, at a temperature (C) and pH."""
    neutral = compute_neutral_rate_constant(material, temperature_celsius)
    return neutral + compute_base_rate_constant(material, temperature_celsius, fluid_ph)


def check_ph_in_range(material: MaterialConstants, fluid_ph: float) -> None:
    """Raise ValueError if the fluid pH is outside the range allowed by the material file."""
    if not material.fluid_ph_min <= fluid_ph <= material.fluid_ph_max:
        raise ValueError(f"Fluid pH must be between {material.fluid_ph_min} and {material.fluid_ph_max}, got {fluid_ph}.")
