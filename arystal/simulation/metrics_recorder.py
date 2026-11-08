"""Collects the metrics over time of a run: one row per sampling moment, ready for metrics.csv."""

import math

from arystal.engine.silica_transport import compute_solid_fraction
from arystal.engine.solution_growth import SolutionState, compute_total_iron, compute_total_silica
from arystal.engine.solution_params import SolutionParams
from arystal.engine.material_constants import MaterialConstants
from arystal.engine.regime_indicator import compute_model_damkohler
from arystal.engine.time_scaling import compute_cell_size_mm, compute_kinetic_seconds_per_model_time, convert_model_time_to_diffusion_seconds
from arystal.metrics.growth_metrics import (
    FAMILY_NAMES,
    compute_aspect_ratio,
    compute_bulk_supersaturation,
    compute_estimated_mass_mg,
    compute_face_distances,
    compute_height_and_width,
    compute_interface_supersaturation,
    compute_iron_ratio_by_sector,
    compute_mean_iron_ratio,
)
from arystal.metrics.shape import compute_crystal_area

SECONDS_PER_HOUR = 3600.0
SECONDS_PER_YEAR = 3.156e7

# The kinetic conversion to real time is only meaningful when growth is surface-limited: Da at this crystal size below this value.
SURFACE_LIMITED_DAMKOHLER = 0.06
SIZE_FOR_DAMKOHLER_CELLS = 50.0
NAN = float("nan")


class MetricsRecorder:
    """Computes one metrics row from the state of a run, remembering what it needs for rates and drifts."""

    def __init__(self, params: SolutionParams, material: MaterialConstants, initial_state: SolutionState) -> None:
        """Remember the parameters and the initial totals (for the conservation check)."""
        self.params = params
        self.material = material
        self.initial_silica = compute_total_silica(initial_state, params)
        self.initial_iron = compute_total_iron(initial_state)
        self.previous_time = None
        self.previous_distances = None
        self.kinetic_seconds = 0.0
        self.last_row_time = 0.0

    def compute_growth_rates(self, time: float, distances: dict[str, float]) -> dict[str, float]:
        """Return the growth rate (cells per model time unit) of each family since the previous row (nan for the first row)."""
        if self.previous_time is None or time <= self.previous_time:
            return {family: NAN for family in FAMILY_NAMES}
        elapsed = time - self.previous_time
        return {family: (distances[family] - self.previous_distances[family]) / elapsed for family in FAMILY_NAMES}

    def compute_iron_metrics(self, state: SolutionState, solid: object) -> dict[str, float]:
        """Return the mean and per-sector Fe/Si of the crystal (all nan when iron is not simulated)."""
        if self.params.sector_partition is None:
            return {"mean_iron_ratio": NAN, **{f"iron_ratio_{f}": NAN for f in FAMILY_NAMES}}
        by_sector = compute_iron_ratio_by_sector(state.sector_iron, state.sector_silica)
        mean = compute_mean_iron_ratio(state.crystal_iron, state.phase_field, solid, self.params.solid_capacity)
        return {"mean_iron_ratio": mean, **{f"iron_ratio_{f}": by_sector[f] for f in FAMILY_NAMES}}

    def compute_drift(self, total: float, initial: float) -> float:
        """Return (total - initial) / initial, or 0 when the quantity is not simulated."""
        return (total - initial) / initial if initial > 0 else 0.0

    def update_kinetic_time(self, time: float, params: SolutionParams, supersaturation: float) -> float:
        """Add the real time (seconds) of the model time elapsed since the previous row, at the current rate, and return the total (nan if not surface-limited)."""
        if compute_model_damkohler(params, SIZE_FOR_DAMKOHLER_CELLS) > SURFACE_LIMITED_DAMKOHLER:
            return float("nan")
        seconds_per_unit = compute_kinetic_seconds_per_model_time(self.material, params, supersaturation)
        if seconds_per_unit == seconds_per_unit:  # not nan
            self.kinetic_seconds += (time - self.last_row_time) * seconds_per_unit
        self.last_row_time = time
        return self.kinetic_seconds

    def update_params(self, params: SolutionParams) -> None:
        """Use new parameters from now on (after a live change of temperature, for example)."""
        self.params = params

    def record(self, step: int, state: SolutionState, injected_iron: float = 0.0, injected_silica: float = 0.0) -> dict[str, float]:
        """Return the metrics row for the state at `step`.

        `injected_iron` is the iron added to the container by live changes of the fluid iron; the iron
        conservation drift is computed after discounting it. `injected_silica` is the same for silica (fluid renewals).
        """
        params = self.params
        time = step * params.time_step
        solid = compute_solid_fraction(state.phase_field)
        area_cells = compute_crystal_area(state.phase_field)
        cell_size = compute_cell_size_mm(params)
        height, width = compute_height_and_width(state.phase_field)
        distances = compute_face_distances(state.phase_field, self.material.r_pole_angle_to_c_degrees)
        rates = self.compute_growth_rates(time, distances)
        self.previous_time, self.previous_distances = time, distances
        row = {
            "step": step,
            "time_model": time,
            "temperature_celsius": params.temperature_celsius,
            "time_diffusion_hours": convert_model_time_to_diffusion_seconds(self.material, params, time) / SECONDS_PER_HOUR,
            "time_kinetic_years": self.update_kinetic_time(time, params, compute_bulk_supersaturation(state.silica, params.equilibrium_silica)) / SECONDS_PER_YEAR,
            "crystal_area_cells": area_cells,
            "crystal_area_mm2": area_cells * cell_size**2,
            "crystal_mass_mg_estimate": compute_estimated_mass_mg(
                area_cells, cell_size, self.material.assumed_thickness_mm, self.material.solid_density_real
            ),
            "height_cells": height,
            "width_cells": width,
            "aspect_ratio": compute_aspect_ratio(height, width),
        }
        row.update({f"face_distance_{f}_cells": distances[f] for f in FAMILY_NAMES})
        row.update({f"growth_rate_{f}_cells_per_time": rates[f] for f in FAMILY_NAMES})
        row.update(self.compute_iron_metrics(state, solid))
        total_silica = compute_total_silica(state, params)
        total_iron = compute_total_iron(state)
        row.update({
            "supersaturation_interface": compute_interface_supersaturation(state.silica, state.phase_field, params.equilibrium_silica),
            "supersaturation_bulk": compute_bulk_supersaturation(state.silica, params.equilibrium_silica),
            "total_silica": total_silica,
            "total_iron": total_iron,
            "silica_relative_drift": self.compute_drift(total_silica - injected_silica, self.initial_silica),
            "iron_relative_drift": self.compute_drift(total_iron - injected_iron, self.initial_iron),
        })
        return row
