"""Validation check 5: resolution convergence.

The same physical crystal is grown on grids of 200, 400, 800 and 1600 cells across the same container (so the cell is 0.2, 0.1, 0.05 and 0.025 mm). To keep the
physical problem the same, everything given in cells is scaled with the resolution: seed radius, target size and the relaxation time tau (so that
the physical attachment speed and the Damkohler number do not change). What changes is the physical thickness of the interface, which shrinks as the
grid is refined: the sharp-interface limit that the model approaches. The properties of the crystal at the same size must stop changing.

The runs use the uniform-fluid scheme (valid on the plateau, where growth is surface-limited), which is what makes 1600 cells affordable; it was validated
against the full implicit solution (check 6b) and, at 100 to 400 cells, gave the same aspect ratio to four digits (docs/regime_study.md).

Properties compared: aspect ratio, ratio of the r and m face distances, and the uniformity of the supersaturation (surface-limited regime). The share of the
surface lying on flat faces is reported but not judged: it grows as facets get sharper with refinement (known from the anisotropy model), and depends on how it is counted.

WHAT THIS DOES NOT SHOW: convergence for other conditions or for the full model with noise; it is one representative case, on the plateau of the regime study.
"""

from arystal.engine.material_constants import MaterialConstants
from arystal.validation.check_result import CheckResult
from arystal.validation.regime_study import BASE_TAU, GRID_HEIGHT, GRID_WIDTH, SEED_RADIUS, TARGET_RADIUS, build_study_params, grow_to_radius

LIMITS_NOTE = "Limits: one representative case on the plateau, no noise, no iron; other conditions may converge differently. The explore resolution (200) is NOT converged for the aspect ratio."

RESOLUTIONS = (200, 400, 800, 1600)   # cells across the container
REFERENCE_RESOLUTION = 200
JUDGED_METRICS = ("aspect_ratio", "face_ratio_r_over_m", "uniformity")
MAX_CHANGE_AT_FINEST = 0.05      # fraction: the change from the second finest to the finest grid must be below this
REPORTED_METRIC = "facet_fraction"


def run_resolution(material: MaterialConstants, resolution: int) -> dict:
    """Grow the reference crystal on a grid of `resolution` cells across the container, with the cell-based quantities scaled."""
    scale = resolution / REFERENCE_RESOLUTION
    params = build_study_params(
        material, BASE_TAU * scale, grid=(resolution, resolution * GRID_HEIGHT // GRID_WIDTH), seed_radius=SEED_RADIUS * scale, uniform=True,
    )
    row = grow_to_radius(material, params, TARGET_RADIUS * scale)
    row["resolution"] = resolution
    return row


def compute_changes(rows: list[dict], metric: str) -> list[float]:
    """Return the relative changes of a metric between consecutive resolutions."""
    return [abs(second[metric] / first[metric] - 1.0) for first, second in zip(rows, rows[1:])]


def run_convergence_check(material: MaterialConstants, resolutions: tuple = RESOLUTIONS, on_row=None) -> list[CheckResult]:
    """Run the convergence check and return its results."""
    rows = []
    for resolution in resolutions:
        rows.append(run_resolution(material, resolution))
        if on_row:
            on_row(rows[-1])
    results = []
    for metric in JUDGED_METRICS:
        changes = compute_changes(rows, metric)
        values = ", ".join(f"{row[metric]:.3f}" for row in rows)
        converging = len(changes) < 2 or changes[-1] <= changes[-2]
        passed = changes[-1] <= MAX_CHANGE_AT_FINEST and converging
        message = (
            f"{metric} at {', '.join(str(r) for r in resolutions)} cells: {values}; relative changes between consecutive resolutions "
            f"{', '.join(f'{100 * c:.2f}%' for c in changes)} (finest change must be <= {100 * MAX_CHANGE_AT_FINEST:.0f}% and not larger than the one before)."
        )
        results.append(CheckResult(f"{metric} converges with the resolution", passed, message))
    facets = ", ".join(f"{row[REPORTED_METRIC]:.3f}" for row in rows)
    cost = ", ".join(f"{row['wall_seconds']:.0f} s" for row in rows)
    results.append(CheckResult("[reported] share of the surface on flat faces", True, f"{REPORTED_METRIC} at {', '.join(str(r) for r in resolutions)} cells: {facets}; cost of each run {cost}.", informational=True))
    return results
