"""Observed vs simulated: one row per measurement, with a tolerance and the role of the measurement (check / calibration / prediction)."""

import math
from dataclasses import dataclass

from arystal.comparison.observed import ObservedSample

COVERAGE_FACTOR = 2.0   # "within tolerance" = difference smaller than 2 combined standard deviations (about 95% if errors are normal)

ROLE_MEANING = {
    "check": "(a) check of a feature that was NOT tuned to this sample",
    "calibration": "(b) CALIBRATION: a parameter was tuned to this value, agreement is expected and validates nothing",
    "prediction": "(c) prediction for an independent sample (not used for calibration)",
}


@dataclass(frozen=True)
class ComparisonRow:
    """The comparison of one quantity."""

    name: str
    observed: float
    observed_uncertainty: float
    simulated: float
    simulated_uncertainty: float
    difference: float
    tolerance: float
    within_tolerance: bool
    role: str
    units: str


def compute_tolerance(observed_uncertainty: float, simulated_uncertainty: float) -> float:
    """Return the tolerance: coverage factor times the combined uncertainty sqrt(u_obs^2 + u_sim^2)."""
    return COVERAGE_FACTOR * math.sqrt(observed_uncertainty**2 + simulated_uncertainty**2)


def compare_one(measurement, simulated: float, simulated_uncertainty: float) -> ComparisonRow:
    """Return the comparison row for one observed measurement."""
    difference = simulated - measurement.value
    tolerance = compute_tolerance(measurement.uncertainty, simulated_uncertainty)
    return ComparisonRow(
        measurement.name, measurement.value, measurement.uncertainty, simulated, simulated_uncertainty, difference, tolerance,
        abs(difference) <= tolerance, measurement.role, measurement.units,
    )


def compare_sample(sample: ObservedSample, simulated: dict[str, float], uncertainty_of) -> list[ComparisonRow]:
    """Return one row per observed measurement that the model also produces; `uncertainty_of(name, value)` gives the model's numerical uncertainty."""
    rows = []
    for measurement in sample.measurements:
        if measurement.name not in simulated:
            raise ValueError(f"The model does not produce {measurement.name!r}; produced: {sorted(simulated)}")
        value = simulated[measurement.name]
        rows.append(compare_one(measurement, value, uncertainty_of(measurement.name, value)))
    return rows


def summarise_by_role(rows: list[ComparisonRow]) -> dict[str, str]:
    """Return, for each role present, how many rows are within tolerance and what that means."""
    summary = {}
    for role, meaning in ROLE_MEANING.items():
        selected = [row for row in rows if row.role == role]
        if selected:
            summary[role] = f"{sum(row.within_tolerance for row in selected)}/{len(selected)} within tolerance: {meaning}"
    return summary


def describe_validation_status(sample: ObservedSample, rows: list[ComparisonRow]) -> str:
    """Return one honest sentence on what this comparison can claim."""
    if sample.fictitious:
        return "FICTITIOUS DATA: this only tests the code. Nothing can be concluded about the model."
    if not sample.approved_by_luna:
        return "Data source NOT yet approved by Luna: do not use these results."
    if all(row.role == "calibration" for row in rows):
        return "Calibration only: agreement is by construction. A second, independent sample is needed to validate."
    return "Checks and predictions above are evidence about the model; calibration rows are not. Validation needs a second independent sample."
