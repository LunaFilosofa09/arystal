"""Saving and loading the grids of a run: snapshots every N steps and the final state.

Snapshots are stored compressed and in single precision (float32) to save space: they are for replaying the
animation, not for restarting the simulation. final_state.npz keeps full precision (float64) so a result can be
compared exactly with a re-run.
"""

from pathlib import Path

import numpy as np

from arystal.engine.solution_growth import SolutionState

SNAPSHOT_FIELDS = ("phase_field", "silica", "iron", "crystal_iron")
FINAL_FIELDS = SNAPSHOT_FIELDS + ("sector_iron", "sector_silica")


def build_snapshot_path(folder: Path, step: int) -> Path:
    """Return the file of the snapshot at `step`."""
    return Path(folder) / "snapshots" / f"snapshot_{step:09d}.npz"


def save_snapshot(folder: Path, step: int, time: float, state: SolutionState) -> Path:
    """Save the main grids of a state, compressed, in float32. Returns the file path."""
    path = build_snapshot_path(folder, step)
    arrays = {name: getattr(state, name).astype(np.float32) for name in SNAPSHOT_FIELDS}
    np.savez_compressed(path, step=step, time=time, **arrays)
    return path


def load_snapshot(path: Path) -> dict:
    """Load a snapshot file into a dictionary of arrays (plus 'step' and 'time')."""
    with np.load(path) as data:
        return {name: data[name] for name in data.files}


def list_snapshots(folder: Path) -> list[Path]:
    """Return the snapshot files of a run folder, in time order."""
    return sorted((Path(folder) / "snapshots").glob("snapshot_*.npz"))


def save_final_state(folder: Path, state: SolutionState) -> Path:
    """Save the final grids at full precision."""
    path = Path(folder) / "final_state.npz"
    np.savez_compressed(path, **{name: getattr(state, name) for name in FINAL_FIELDS})
    return path


def load_final_state(folder: Path) -> dict:
    """Load final_state.npz of a run folder into a dictionary of arrays."""
    with np.load(Path(folder) / "final_state.npz") as data:
        return {name: data[name] for name in data.files}
