"""Study of the kinetic regime (see docs/kinetic_regime.md, section 7).

For a range of the Damkohler number Da (attachment speed / diffusion speed; changed through the relaxation time tau, everything
else fixed) the same crystal is grown until it reaches the same size, and its properties are measured. If they stop changing
below some Da (a PLATEAU), then any Da on the plateau gives the same result, which is what the real, very small Da (1e-7 to 1e-3)
also gives. This is a STUDY, not a pass/fail check: it measures, and docs/regime_study.md reports what was found.

Runs use the fast kernels, the implicit diffusion for slow kinetics (an exact change of numerical scheme, validated against the
explicit one) or, on the plateau, the uniform-fluid limit (validated against the implicit solution), no noise and no iron (iron is a
passive trace and does not influence the shape).
"""

import dataclasses
import math
import time

import numpy as np

from arystal.engine.anisotropy import compute_face_normal_angles, create_facet_anisotropy_from_material
from arystal.engine.implicit_diffusion import suggest_implicit_time_step
from arystal.engine.material_constants import MaterialConstants
from arystal.engine.regime_indicator import compute_attachment_speed, compute_model_damkohler
from arystal.engine.solution_growth import advance_one_step, create_initial_state
from arystal.engine.solution_params import SolutionParams, create_solution_params
from arystal.metrics.facets import collect_interface_cells, compute_angle_difference
from arystal.metrics.growth_metrics import compute_face_distances, compute_height_and_width
from arystal.metrics.shape import compute_equivalent_radius

# The grid, the container and the seed of every run of the study.
GRID_WIDTH = 200
GRID_HEIGHT = 100
SEED_RADIUS = 12.0
RUN_CELSIUS = 20.0
SATURATION_CELSIUS = 60.0
TARGET_RADIUS = 30.0          # the crystals are compared when their equivalent radius reaches this (cells)
EXPLICIT_TIME_STEP = 0.1
EXPLICIT_UP_TO_TAU = 5.0      # larger tau: implicit diffusion
FASTEST_ORIENTATION_FACTOR = 1.6   # largest g of the speed polygon, to be safe when choosing the implicit time step
MAXIMUM_STEPS = 600_000
STEPS_BETWEEN_SIZE_CHECKS = 10
FACET_ANGLE_TOLERANCE_DEGREES = 3.0
FACE_KEYS = ("m_right", "r_upper_right", "z_upper_left", "m_left")
BASE_TAU = 10000.0         # relaxation time of the plateau runs at the reference resolution (200 cells across)
DEFAULT_TAUS = (1.0, 10.0, 100.0, 1000.0, 10000.0)
SMALLER_TARGET_RADIUS = 24.0


def build_study_params(
    material: MaterialConstants, tau: float, solid_capacity: float | None = None, grid: tuple[int, int] = (GRID_WIDTH, GRID_HEIGHT),
    run_celsius: float = RUN_CELSIUS, kinetic_coupling: float | None = None, seed_radius: float = SEED_RADIUS, uniform: bool = False,
) -> SolutionParams:
    """Return the parameters of one run of the study for a relaxation time tau (optionally another crystal capacity, temperature, kinetic coupling or seed)."""
    implicit = tau > EXPLICIT_UP_TO_TAU
    scheme = ("uniform" if uniform else "implicit") if implicit else "explicit"
    base = create_solution_params(
        material, run_celsius, SATURATION_CELSIUS, grid_width=grid[0], grid_height=grid[1], seed_radius=seed_radius,
        anisotropy=create_facet_anisotropy_from_material(material), relaxation_time=tau, time_step=EXPLICIT_TIME_STEP,
        backend="numba", diffusion_scheme=scheme,
    )
    if solid_capacity is not None:
        base = dataclasses.replace(base, solid_capacity=solid_capacity)
    if kinetic_coupling is not None:
        base = dataclasses.replace(base, kinetic_coupling=kinetic_coupling)
    if not implicit:
        return dataclasses.replace(base, time_step=min(0.2, 0.9 * tau / (4.0 * FASTEST_ORIENTATION_FACTOR)) if tau < 2.0 else 0.2) if tau != 1.0 else base
    speed = compute_attachment_speed(base) * FASTEST_ORIENTATION_FACTOR
    return dataclasses.replace(base, time_step=suggest_implicit_time_step(base, speed))


def compute_facet_fraction(phase_field: np.ndarray, r_pole_angle: float) -> float:
    """Return the share of the surface (interface cells) whose normal is within a few degrees of a face normal (m, r or z): how "faceted" it is."""
    _, _, angles = collect_interface_cells(phase_field)
    if len(angles) == 0:
        return float("nan")
    face_angles = compute_face_normal_angles(r_pole_angle)
    near = np.zeros(len(angles), dtype=bool)
    for key in FACE_KEYS:
        near |= compute_angle_difference(angles, face_angles[key]) < math.radians(FACET_ANGLE_TOLERANCE_DEGREES)
    return float(near.mean())


def measure_crystal(state, params: SolutionParams, r_pole_angle: float) -> dict:
    """Return the properties of the crystal that the study compares."""
    height, width = compute_height_and_width(state.phase_field)[0], compute_height_and_width(state.phase_field)[1]
    faces = compute_face_distances(state.phase_field, r_pole_angle)
    band = np.abs(state.phase_field - 0.5) < 0.1
    interface_s = float(state.silica[band].mean() / params.equilibrium_silica)
    bulk_s = float(state.silica[-1].mean() / params.equilibrium_silica)
    return {
        "radius": compute_equivalent_radius(state.phase_field), "aspect_ratio": height / width, "face_ratio_r_over_m": faces["r"] / faces["m"],
        "supersaturation_interface": interface_s, "supersaturation_bulk": bulk_s,
        "uniformity": (interface_s - 1.0) / (bulk_s - 1.0) if bulk_s > 1.0 else float("nan"),
        "facet_fraction": compute_facet_fraction(state.phase_field, r_pole_angle),
    }


def grow_to_radius(material: MaterialConstants, params: SolutionParams, target_radius: float = TARGET_RADIUS) -> dict:
    """Grow the crystal until its equivalent radius reaches `target_radius` and return its properties and the cost of the run."""
    state = create_initial_state(params)
    started, steps = time.perf_counter(), 0
    in_place = params.diffusion_scheme == "explicit"
    while compute_equivalent_radius(state.phase_field) < target_radius and steps < MAXIMUM_STEPS:
        for _ in range(STEPS_BETWEEN_SIZE_CHECKS):
            state = advance_one_step(state, params, None, in_place=in_place)
            steps += 1
    result = measure_crystal(state, params, material.r_pole_angle_to_c_degrees)
    result.update({
        "tau": params.relaxation_time, "damkohler": compute_model_damkohler(params, target_radius), "scheme": params.diffusion_scheme,
        "time_step": params.time_step, "steps": steps, "model_time": steps * params.time_step, "wall_seconds": time.perf_counter() - started,
        "reached_target": result["radius"] >= target_radius,
    })
    return result


def run_regime_map(material: MaterialConstants, taus: tuple = DEFAULT_TAUS, on_row=None) -> list[dict]:
    """Grow the same crystal for several relaxation times; return one row of properties per tau."""
    rows = []
    for tau in taus:
        rows.append(grow_to_radius(material, build_study_params(material, tau)))
        if on_row:
            on_row(rows[-1])
    return rows


def compute_plateau_changes(rows: list[dict], metrics: tuple = ("aspect_ratio", "face_ratio_r_over_m", "uniformity", "facet_fraction")) -> list[dict]:
    """Return, for each pair of consecutive rows (decreasing Da), the relative change of each metric."""
    changes = []
    for first, second in zip(rows, rows[1:]):
        change = {"from_tau": first["tau"], "to_tau": second["tau"]}
        for metric in metrics:
            change[metric] = abs(second[metric] / first[metric] - 1.0) if first[metric] not in (0, None) and not math.isnan(first[metric]) else float("nan")
        changes.append(change)
    return changes


def run_sensitivity(material: MaterialConstants, tau: float, on_row=None) -> list[dict]:
    """Grow the crystal on the plateau (large tau) while changing, one at a time, the crystal capacity, the kinetic coupling and the temperature.

    Each variation gets a label; the rows can be compared with the baseline ("baseline"). The temperature variation uses a smaller target
    radius because a closed container with less supersaturation can only grow a smaller crystal.
    """
    cases = [
        ("baseline", {}, TARGET_RADIUS),
        ("capacity x0.5", {"solid_capacity": 0.5 * material.solid_capacity_model}, TARGET_RADIUS),
        ("capacity x2", {"solid_capacity": 2.0 * material.solid_capacity_model}, TARGET_RADIUS),
        ("coupling x0.5", {"kinetic_coupling": 0.5 * material.kinetic_coupling}, TARGET_RADIUS),
        ("coupling x2", {"kinetic_coupling": 2.0 * material.kinetic_coupling}, TARGET_RADIUS),
        ("T = 40 C (lower supersaturation)", {"run_celsius": 40.0}, SMALLER_TARGET_RADIUS),
        ("baseline at the smaller radius", {}, SMALLER_TARGET_RADIUS),
    ]
    rows = []
    for label, options, target in cases:
        row = grow_to_radius(material, build_study_params(material, tau, **options), target)
        row["case"] = label
        rows.append(row)
        if on_row:
            on_row(row)
    return rows
