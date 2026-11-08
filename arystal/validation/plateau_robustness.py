"""Does the plateau of the regime study hold outside the conditions where it was measured? (validation_report.md, section 5, point 9)

The regime study (regime_study.py, docs/regime_study.md) found that, for one crystal (run at 20 C, fluid saturated at 60 C, m:r:z 0.5:1:1, grown to
an equivalent radius of 30 cells on a 200 x 100 grid), the shape no longer depends on the Damkohler number Da below about 0.06. Here the same Da sweep
(relaxation time tau from 30 to 1e6, implicit diffusion, so the silica transport is solved in full) is repeated changing ONE thing at a time:
temperature, final size, face speeds, initial supersaturation and the scaled crystal capacity Cs_model.

For each case: the aspect ratio and r/m face ratio at equal size for every tau; the plateau onset = the largest Da below which every further
step down in Da changes the r/m ratio by at most 0.5% AND the aspect ratio by at most about one cell. The aspect ratio is height / width of the bounding
box in WHOLE cells, so at radius 20-40 one cell is 1.5-3% and a 0.5% test cannot be applied to it; and the Da the explore and research modes would have in that case.
"""

import dataclasses

from arystal.engine.material_constants import MaterialConstants
from arystal.engine.regime_indicator import compute_model_damkohler
from arystal.engine.solubility import compute_equilibrium_concentration
from arystal.validation.regime_study import BASE_TAU, TARGET_RADIUS, build_study_params, grow_to_radius

STUDY_TAUS = (30.0, 100.0, 300.0, 1000.0, 3000.0, 10000.0, 100000.0, 1000000.0)
PLATEAU_TOLERANCE = 0.005                 # 0.5%: a change at most this big counts as "no change"
PLATEAU_METRICS = ("face_ratio_r_over_m",)   # continuous (support distances); the aspect ratio is counted in whole cells, see below
WARNING_SIZE_CELLS = 50.0                 # crystal size used by the run warning (saved_run.py, metrics_recorder.py)
SMALL_TARGET_RADIUS = 20.0
LARGE_TARGET_RADIUS = 40.0
LOW_SUPERSATURATION_SATURATION_CELSIUS = 40.0
HIGH_SUPERSATURATION_FACTOR = 1.5         # initial silica 1.5 times the 60 C saturation value (a fluid supersaturated by another silica source)

# Each case: label, group, options of build_study_params, material changes, extra changes of the parameters, target radius (cells).
CASES = [
    ("baseline (20 C, sat. 60 C, m 0.5, radius 30)", "baseline", {}, {}, {}, TARGET_RADIUS),
    ("T = 15 C", "temperature", {"run_celsius": 15.0}, {}, {}, TARGET_RADIUS),
    ("T = 37 C", "temperature", {"run_celsius": 37.0}, {}, {}, 24.0),
    ("T = 45 C (55-60 C: the seed dissolves, too little supersaturation)", "temperature", {"run_celsius": 45.0}, {}, {}, 16.0),
    ("small crystal (radius 20)", "size", {}, {}, {}, SMALL_TARGET_RADIUS),
    ("large crystal (radius 40)", "size", {}, {}, {}, LARGE_TARGET_RADIUS),
    ("m/r = 0.3", "face speeds", {}, {"facet_speed_m": 0.3}, {}, TARGET_RADIUS),
    ("m/r = 0.8", "face speeds", {}, {"facet_speed_m": 0.8}, {}, TARGET_RADIUS),
    ("low S (saturated at 40 C)", "supersaturation", {}, {}, {"saturation_celsius": LOW_SUPERSATURATION_SATURATION_CELSIUS}, 20.0),
    ("high S (silica x1.5)", "supersaturation", {}, {}, {"silica_factor": HIGH_SUPERSATURATION_FACTOR}, TARGET_RADIUS),
    ("Cs_model x0.5", "capacity", {"solid_capacity_factor": 0.5}, {}, {}, TARGET_RADIUS),
    ("Cs_model x2", "capacity", {"solid_capacity_factor": 2.0}, {}, {}, TARGET_RADIUS),
]


def build_case_params(material: MaterialConstants, case: tuple, tau: float):
    """Return (material of the case, parameters of the case at relaxation time tau), on the 200 x 100 grid of the regime study."""
    _, _, options, material_changes, extra, _ = case
    case_material = dataclasses.replace(material, **material_changes)
    options = dict(options)
    capacity_factor = options.pop("solid_capacity_factor", None)
    if capacity_factor is not None:
        options["solid_capacity"] = capacity_factor * material.solid_capacity_model
    params = build_study_params(case_material, tau, **options)
    if "saturation_celsius" in extra:
        params = dataclasses.replace(params, initial_silica=compute_equilibrium_concentration(case_material, extra["saturation_celsius"]))
    if "silica_factor" in extra:
        params = dataclasses.replace(params, initial_silica=params.initial_silica * extra["silica_factor"])
    return case_material, params


def run_case_at_tau(material: MaterialConstants, case_index: int, tau: float) -> dict:
    """Grow the crystal of one case at one tau until its target size; return the row with the case label, group and Da values."""
    case = CASES[case_index]
    case_material, params = build_case_params(material, case, tau)
    row = grow_to_radius(case_material, params, case[5])
    row.update({"case": case[0], "group": case[1], "case_index": case_index, "target_radius": case[5],
                "damkohler_at_warning_size": compute_model_damkohler(params, WARNING_SIZE_CELLS)})
    return row


def compute_mode_damkohler(material: MaterialConstants, case_index: int) -> dict:
    """Return the Da (at the target size and at the warning size) the modes would have in this case (tau of the modes at 200 cells across).

    The modes scale tau with the resolution, and Da with it, so explore (200) and research (800) have the same Da for the same physical crystal.
    """
    _, params = build_case_params(material, CASES[case_index], BASE_TAU)
    return {"at_target": compute_model_damkohler(params, CASES[case_index][5]), "at_warning_size": compute_model_damkohler(params, WARNING_SIZE_CELLS)}


def compute_relative_change(first: float, second: float) -> float:
    """Return |second / first - 1|."""
    return abs(second / first - 1.0)


def compute_one_cell_aspect_change(row: dict) -> float:
    """Return the relative change of the aspect ratio caused by one cell of height: 1 / height (height = aspect x width, about 2 x radius)."""
    return 1.0 / (2.0 * row["target_radius"] * max(row["aspect_ratio"], 1.0))


def is_step_unchanged(upper: dict, lower: dict) -> bool:
    """Return True if going from one Da to the next lower one changes r/m by at most 0.5% and the aspect ratio by at most about one cell."""
    face_change = max(compute_relative_change(upper[metric], lower[metric]) for metric in PLATEAU_METRICS)
    aspect_tolerance = 1.5 * compute_one_cell_aspect_change(lower)   # 1.5: a one-cell step plus rounding of the width
    return face_change <= PLATEAU_TOLERANCE and compute_relative_change(upper["aspect_ratio"], lower["aspect_ratio"]) <= aspect_tolerance


def find_plateau_onset(rows: list[dict]) -> float:
    """Return the largest Da (at the target size) such that every step to a lower Da leaves the shape unchanged (is_step_unchanged).

    rows: one case, any order. Returns nan if even the last two rows differ (no plateau seen).
    """
    ordered = sorted(rows, key=lambda row: -row["damkohler"])
    onset = float("nan")
    for index in range(len(ordered) - 1, 0, -1):
        if not is_step_unchanged(ordered[index - 1], ordered[index]):
            break
        onset = ordered[index - 1]["damkohler"]
    return onset


def check_aspect_within_one_cell(rows: list[dict], onset: float) -> bool:
    """Return True if, at and below the onset, the aspect ratio never differs from its lowest-Da value by more than about one cell."""
    on_plateau = [row for row in rows if row["damkohler"] <= onset * (1.0 + 1e-9)]
    if not on_plateau:
        return False
    reference = min(on_plateau, key=lambda row: row["damkohler"])
    tolerance = 1.5 * compute_one_cell_aspect_change(reference)   # 1.5: a one-cell step plus rounding of the width
    return all(compute_relative_change(reference["aspect_ratio"], row["aspect_ratio"]) <= tolerance for row in on_plateau)


def list_jobs() -> list[tuple[int, float]]:
    """Return every (case index, tau) pair of the study."""
    return [(case_index, tau) for case_index in range(len(CASES)) for tau in STUDY_TAUS]
