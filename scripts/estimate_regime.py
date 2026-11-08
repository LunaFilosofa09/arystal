"""Order-of-magnitude estimate of the growth regime: surface-reaction-limited or diffusion-limited?

Uses the quartz rate law and rate constant read in Takeno, Ishido & Pritchett (2000):
    net precipitation rate per unit surface = k+ * (S - 1),   log10 k+ = -0.7324 - 3705.12 / T
and compares the resulting growth speed with the speed a crystal could reach if limited only by
diffusion of silica to it. Da = v_kin / v_diff: Da << 1 means growth is limited by attachment at
the surface (uniform supersaturation, flat faces); Da >> 1 means limited by the silica supply.
See docs/kinetic_regime.md for the discussion and the uncertainties.

A second table repeats the estimate with the pH-dependent law of Palandri & Kharaka (2004) (neutral + base terms, section 10 of kinetic_regime.md).

    python scripts/estimate_regime.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from arystal.engine.solubility import compute_equilibrium_concentration  # noqa: E402
from arystal.engine.time_scaling import compute_quartz_rate_constant, compute_real_solid_capacity  # noqa: E402
from arystal.simulation.material_loader import get_value, load_material, read_material_file  # noqa: E402

KG_WATER_PER_M3 = 1000.0  # 1 m3 of water weighs about 1000 kg: converts mol/kg into mol/m3.
RUN_TEMPERATURES_CELSIUS = [15.0, 40.0, 60.0]
SUPERSATURATION_RATIOS = [2.0, 5.0, 10.0]
CRYSTAL_SIZES_METRES = [1e-3, 1e-2, 1e-1]
SECONDS_PER_YEAR = 3.156e7
FLUID_PH_VALUES = [None, 7.0, 8.0, 9.0, 10.0]   # None = Takeno law (no pH)
PH_TABLE_SUPERSATURATION = 2.0
PH_TABLE_SIZE_METRES = 0.1


def compute_rate_constant(data: dict, temperature_celsius: float) -> float:
    """Return k+ = 10^(A + B/T) in mol m-2 s-1 from the material file."""
    a = get_value(data, "kinetics", "quartz_rate_constant_log10_A")
    b = get_value(data, "kinetics", "quartz_rate_constant_log10_B")
    return 10.0 ** (a + b / (temperature_celsius + 273.15))


def compute_molar_volume_m3(material) -> float:
    """Return the molar volume of quartz in m3/mol (molar mass / density)."""
    return material.molar_mass * 1e-3 / (material.solid_density_real * 1e3)


def compute_diffusion_limited_speed(material, size: float, equilibrium: float, supersaturation: float) -> float:
    """Return v_D = D * (c - c_eq) / (Cs * L) in m/s: steady speed of a crystal of size L fed only by diffusion."""
    capacity = compute_real_solid_capacity(material) * KG_WATER_PER_M3
    excess = (supersaturation - 1.0) * equilibrium * KG_WATER_PER_M3
    return material.diffusivity_m2_per_s * excess / (capacity * size)


def describe_ph(fluid_ph: float | None) -> str:
    """Return the label of a rate-law case: 'Takeno' or 'pH 9'."""
    return "Takeno" if fluid_ph is None else f"pH {fluid_ph:g}"


def print_ph_table(material) -> None:
    """Print, for each temperature and fluid pH, the rate constant, the years to grow 10 cm and Da for a 10 cm crystal (S = 2)."""
    molar_volume = compute_molar_volume_m3(material)
    print(f"\npH-dependent law (Palandri & Kharaka 2004), S = {PH_TABLE_SUPERSATURATION:g}, crystal of {PH_TABLE_SIZE_METRES * 100:g} cm")
    print(f"{'T C':>4} {'law':>7} {'k mol/m2/s':>11} {'yr per 10cm':>12} {'Da 10 cm':>9}")
    for temperature in RUN_TEMPERATURES_CELSIUS:
        equilibrium = compute_equilibrium_concentration(material, temperature)
        diffusion_speed = compute_diffusion_limited_speed(material, PH_TABLE_SIZE_METRES, equilibrium, PH_TABLE_SUPERSATURATION)
        for fluid_ph in FLUID_PH_VALUES:
            rate_constant = compute_quartz_rate_constant(material, temperature, fluid_ph)
            speed = rate_constant * (PH_TABLE_SUPERSATURATION - 1.0) * molar_volume
            years = PH_TABLE_SIZE_METRES / speed / SECONDS_PER_YEAR
            print(f"{temperature:4.0f} {describe_ph(fluid_ph):>7} {rate_constant:11.1e} {years:12.1e} {speed / diffusion_speed:9.1e}")


def main() -> None:
    """Print the regime tables."""
    material = load_material()
    data = read_material_file("amethyst")
    molar_volume = compute_molar_volume_m3(material)
    print("Growth speed v_kin = k+ (S - 1) * Vm  (surface-reaction law, Takeno et al. 2000, eq. 1 and 6)")
    print("Da = v_kin / v_diff, v_diff = D (c - c_eq) / (Cs L), D = 1e-9 m2/s (ASSUMED), Cs = real quartz capacity\n")
    print(f"{'T C':>4} {'S':>4} {'k+ mol/m2/s':>12} {'v_kin m/s':>10} {'yr per 10cm':>12} | Da for L = 1 mm, 1 cm, 10 cm")
    for temperature in RUN_TEMPERATURES_CELSIUS:
        equilibrium = compute_equilibrium_concentration(material, temperature)
        rate_constant = compute_rate_constant(data, temperature)
        for supersaturation in SUPERSATURATION_RATIOS:
            speed = rate_constant * (supersaturation - 1.0) * molar_volume
            ratios = [speed / compute_diffusion_limited_speed(material, size, equilibrium, supersaturation) for size in CRYSTAL_SIZES_METRES]
            years = 0.1 / speed / SECONDS_PER_YEAR
            print(f"{temperature:4.0f} {supersaturation:4.0f} {rate_constant:12.1e} {speed:10.1e} {years:12.1e} | "
                  + "  ".join(f"{ratio:8.1e}" for ratio in ratios))
    print_ph_table(material)


if __name__ == "__main__":
    main()
