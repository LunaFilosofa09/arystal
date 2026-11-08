"""Iron as a second dissolved species: transport in the fluid and incorporation into the crystal.

Two iron fields (amounts per unit volume, in mol/kg-equivalent units like silica):
  iron          iron dissolved in the fluid (diffuses, like silica but with its own diffusivity)
  crystal_iron  iron locked into the crystal (does not move)
  sector_iron, sector_silica  the same crystal iron and the silica deposited, split by face family (m, r, z)

When the solid fraction of a cell increases by dh, silica Cs*dh is deposited, and iron is
deposited together with it in the proportion
        Fe/Si (crystal) = coefficient(sector) * Fe/Si (fluid)
When the crystal dissolves (dh < 0) it gives back iron in the proportion in which it holds it.

Conservation: sum(iron + crystal_iron) is constant, because what the fluid loses the crystal
gains and diffusion only moves iron between cells.

Assumption (documented): iron is a TRACE. It does not change growth, silica supply or solubility.
"""

import numpy as np

from arystal.engine.iron_partition import compute_family_coefficients, compute_family_weight_field
from arystal.engine.silica_transport import compute_diffusion_change, compute_solid_fraction
from arystal.engine.solution_params import MODEL_DIFFUSIVITY, SolutionParams

# Smallest silica concentration used in the Fe/Si ratio, to avoid dividing by zero.
MINIMUM_SILICA_RATIO = 1e-6

# Smallest solid fraction used when giving iron back from a dissolving cell.
MINIMUM_SOLID_FRACTION = 1e-6


def compute_fluid_iron_to_silica_ratio(iron: np.ndarray, silica: np.ndarray, params: SolutionParams) -> np.ndarray:
    """Return Fe/Si (mol per mol) of the fluid in every cell."""
    safe_silica = np.maximum(silica, MINIMUM_SILICA_RATIO * params.equilibrium_silica)
    return np.maximum(iron, 0.0) / safe_silica


def compute_family_deposits(
    iron: np.ndarray, silica: np.ndarray, phase_field: np.ndarray, solid_change: np.ndarray, params: SolutionParams
) -> tuple[np.ndarray, np.ndarray]:
    """Return what the crystal deposits in this step, split by face family (m, r, z): (iron, silica), each (3, H, W).

    Silica deposited = Cs * (increase of solid fraction), shared among the families by their weights.
    Iron deposited = coefficient(family) * (Fe/Si of the fluid) * that silica. The total iron is capped by the
    iron available in the cell, so the fluid can never go negative.
    """
    weights = compute_family_weight_field(phase_field, params.sector_partition)
    coefficients = compute_family_coefficients(params.sector_partition)[:, None, None]
    ratio = compute_fluid_iron_to_silica_ratio(iron, silica, params)
    silica_total = params.solid_capacity * np.maximum(solid_change, 0.0)
    silica_by_family = weights * silica_total
    iron_wanted = coefficients * ratio * silica_by_family
    wanted_total = iron_wanted.sum(axis=0)
    available = np.maximum(iron, 0.0)
    scale = np.where(wanted_total > 0.0, np.minimum(wanted_total, available) / np.where(wanted_total > 0.0, wanted_total, 1.0), 0.0)
    return iron_wanted * scale, silica_by_family


def compute_fraction_dissolved(old_solid: np.ndarray, solid_change: np.ndarray) -> np.ndarray:
    """Return the fraction (0-1) of the crystal in each cell that dissolves in this step."""
    return np.minimum(np.maximum(-solid_change, 0.0) / np.maximum(old_solid, MINIMUM_SOLID_FRACTION), 1.0)


def compute_iron_exchange(
    iron: np.ndarray, crystal_iron: np.ndarray, sector_iron: np.ndarray, sector_silica: np.ndarray,
    silica: np.ndarray, old_phase_field: np.ndarray, new_phase_field: np.ndarray, params: SolutionParams,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return (iron exchanged with the crystal, crystal iron, iron by sector, silica by sector) after one step.

    The exchange is positive where the crystal takes iron up and negative where it gives iron back. The by-sector arrays
    record, for every cell, how much iron and silica were deposited by each face family (exact iron per growth sector).
    """
    old_solid = compute_solid_fraction(old_phase_field)
    solid_change = compute_solid_fraction(new_phase_field) - old_solid
    iron_by_family, silica_by_family = compute_family_deposits(iron, silica, old_phase_field, solid_change, params)
    kept = 1.0 - compute_fraction_dissolved(old_solid, solid_change)
    new_sector_iron = sector_iron * kept + iron_by_family
    new_sector_silica = sector_silica * kept + silica_by_family
    new_crystal_iron = crystal_iron * kept + iron_by_family.sum(axis=0)
    return new_crystal_iron - crystal_iron, new_crystal_iron, new_sector_iron, new_sector_silica


def compute_new_iron_fields(
    iron: np.ndarray, crystal_iron: np.ndarray, sector_iron: np.ndarray, sector_silica: np.ndarray,
    silica: np.ndarray, old_phase_field: np.ndarray, new_phase_field: np.ndarray, params: SolutionParams,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return (fluid iron, crystal iron, iron by sector, silica by sector) after one time step (explicit diffusion)."""
    exchange, new_crystal_iron, new_sector_iron, new_sector_silica = compute_iron_exchange(
        iron, crystal_iron, sector_iron, sector_silica, silica, old_phase_field, new_phase_field, params
    )
    old_solid = compute_solid_fraction(old_phase_field)
    diffusion = compute_diffusion_change(iron, old_solid, MODEL_DIFFUSIVITY * params.iron_diffusivity_ratio)
    new_iron = iron + params.time_step * diffusion - exchange
    return new_iron, new_crystal_iron, new_sector_iron, new_sector_silica
