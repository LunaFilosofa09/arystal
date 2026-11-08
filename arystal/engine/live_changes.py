"""Changes of the conditions during a run : temperature, dissolved iron, renewal of the fluid.

Both are interventions at one instant of the simulation:
  - A temperature change is a sudden change of the solubility c_eq(T). The silica in the container does not
    change, so cooling raises the supersaturation and heating lowers it (it can dissolve the crystal).
    ASSUMPTION: the change is instantaneous; real cooling is gradual (a sequence of small steps does that).
  - An iron change replaces the iron of the FLUID by a new concentration, like renewing the fluid. This adds
    or removes iron from the container, so it breaks the closed-container conservation of iron: the amount added
    is returned so that the conservation check can account for it.
  - A fluid renewal (open decision 5 of docs/kinetic_regime.md) replaces the fluid by new fluid saturated with quartz at a
    chosen temperature, carrying the current fluid iron: one pulse of the "episodic infiltration" reported for Uruguayan geodes
    (Arduin Rode et al. 2024, abstract only). The silica and iron added or removed are returned for the conservation checks.
    ASSUMPTION: the exchange is instantaneous and complete; the crystal is not touched.
"""

import dataclasses

import numpy as np

from arystal.engine.material_constants import MaterialConstants
from arystal.engine.silica_transport import compute_solid_fraction
from arystal.engine.solubility import compute_equilibrium_concentration
from arystal.engine.solution_growth import SolutionState
from arystal.engine.solution_params import SolutionParams, check_temperature_in_geode_range, convert_iron_ppm_to_concentration

UNIFORM_SCHEME = "uniform"


# A cell counts as containing fluid (and gets the new iron) if at least this fraction of it is fluid.
MINIMUM_FLUID_FRACTION = 0.01


def change_temperature(params: SolutionParams, material: MaterialConstants, temperature_celsius: float) -> SolutionParams:
    """Return the parameters with a new temperature (and the matching equilibrium silica). Refuses temperatures outside the geode range."""
    check_temperature_in_geode_range(material, temperature_celsius)
    return dataclasses.replace(
        params, temperature_celsius=temperature_celsius,
        equilibrium_silica=compute_equilibrium_concentration(material, temperature_celsius),
    )


def set_fluid_iron(
    state: SolutionState, params: SolutionParams, material: MaterialConstants, iron_ppm: float
) -> tuple[SolutionState, float]:
    """Return (state with the fluid iron set to `iron_ppm`, amount of iron added in model units).

    The fluid iron is set to the new value in every cell that has an appreciable fluid fraction, including the
    cells of the interface, which are the ones that feed the growing crystal; cells that are practically all crystal
    keep what they have, and the iron already locked into the crystal is not touched. Raises ValueError
    if iron is not simulated in this run or the value is negative.
    """
    if params.sector_partition is None:
        raise ValueError("Iron is not simulated in this run, so its concentration cannot be changed.")
    if iron_ppm < 0.0:
        raise ValueError("Iron concentration cannot be negative.")
    target = convert_iron_ppm_to_concentration(material, iron_ppm)
    has_fluid = (1.0 - compute_solid_fraction(state.phase_field)) > MINIMUM_FLUID_FRACTION
    new_iron = np.where(has_fluid, target, state.iron)
    return dataclasses.replace(state, iron=new_iron), float((new_iron - state.iron).sum())


def find_fluid_cells(state: SolutionState, params: SolutionParams) -> np.ndarray:
    """Return a boolean map of the cells whose fluid is exchanged by a renewal.

    With the uniform-fluid scheme the dissolved fields are one value everywhere (the fluid), so every cell is set; otherwise the cells
    with an appreciable fluid fraction (as for the iron change).
    """
    if params.diffusion_scheme == UNIFORM_SCHEME:
        return np.ones(state.silica.shape, dtype=bool)
    return (1.0 - compute_solid_fraction(state.phase_field)) > MINIMUM_FLUID_FRACTION


def renew_fluid(
    state: SolutionState, params: SolutionParams, material: MaterialConstants, saturation_celsius: float, iron_ppm: float | None
) -> tuple[SolutionState, float, float]:
    """Replace the fluid by new fluid saturated with quartz at `saturation_celsius` and carrying `iron_ppm` of iron.

    Returns (new state, silica added, iron added), both in model units (negative if removed). Physically: a pulse of fresh
    fluid enters the cavity and the old one leaves. Refuses temperatures outside the geode range.
    """
    check_temperature_in_geode_range(material, saturation_celsius)
    fluid = find_fluid_cells(state, params)
    new_silica = np.where(fluid, compute_equilibrium_concentration(material, saturation_celsius), state.silica)
    new_iron = state.iron
    if params.sector_partition is not None and iron_ppm is not None:
        new_iron = np.where(fluid, convert_iron_ppm_to_concentration(material, iron_ppm), state.iron)
    added_silica, added_iron = float((new_silica - state.silica).sum()), float((new_iron - state.iron).sum())
    return dataclasses.replace(state, silica=new_silica, iron=new_iron), added_silica, added_iron

