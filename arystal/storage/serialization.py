"""Writing and reading JSON files, including numpy arrays and dataclasses. Values that are not numbers (nan) are stored as null."""

import dataclasses
import json
import math
from pathlib import Path

import numpy as np


def to_jsonable(value):
    """Convert dataclasses, numpy arrays and numpy numbers (recursively) into plain Python values for JSON."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {field.name: to_jsonable(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return to_jsonable(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None  # standard JSON has no NaN or infinity; "not available" is written as null
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def write_json(path: Path, value) -> None:
    """Write a value as indented JSON."""
    with open(path, "w") as file:
        json.dump(to_jsonable(value), file, indent=2, allow_nan=False)


def read_json(path: Path):
    """Read a JSON file. NaN and infinity (written by older versions of the program, not valid JSON) are read as None."""
    with open(path) as file:
        return json.load(file, parse_constant=lambda name: None)
