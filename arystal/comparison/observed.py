"""Reading a file of observed measurements of a real amethyst (YAML), as described in docs/observation_comparison.md."""

from dataclasses import dataclass
from pathlib import Path

import yaml

# How a measurement may be used. Only "check" and "prediction" can support a validation; "calibration" was used to tune the model.
VALID_ROLES = ("check", "calibration", "prediction")


@dataclass(frozen=True)
class ObservedMeasurement:
    """One measured quantity of a real crystal: value, uncertainty (one standard deviation, same units) and how it is used."""

    name: str
    value: float
    uncertainty: float
    units: str
    role: str
    how_measured: str


@dataclass(frozen=True)
class ObservedSample:
    """A real sample: where it comes from, whether the data are fictitious (code tests only), and its measurements."""

    sample_id: str
    source: str
    fictitious: bool
    approved_by_luna: bool
    measurements: list[ObservedMeasurement]


def check_role(role: str) -> None:
    """Raise ValueError if a measurement role is not one of the three allowed ones."""
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {VALID_ROLES}, got {role!r}")


def build_measurement(name: str, values: dict) -> ObservedMeasurement:
    """Return one measurement from its YAML entry; the uncertainty must be given and positive."""
    check_role(values["role"])
    if float(values["uncertainty"]) <= 0:
        raise ValueError(f"{name}: the uncertainty must be positive (a measurement without uncertainty cannot be compared).")
    return ObservedMeasurement(name, float(values["value"]), float(values["uncertainty"]), values.get("units", ""), values["role"], values.get("how_measured", ""))


def load_observed_sample(path: Path) -> ObservedSample:
    """Read an observation file and return the sample."""
    data = yaml.safe_load(Path(path).read_text())
    measurements = [build_measurement(name, values) for name, values in data["measurements"].items()]
    return ObservedSample(
        data["sample_id"], data.get("source", ""), bool(data.get("fictitious", False)), bool(data.get("approved_by_luna", False)), measurements,
    )
