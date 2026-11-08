"""Study of the shape as a function of the face speeds m : r : z (docs/face_speed_study.md).

The relative growth speeds of the prism (m) and the rhombohedra (r, z) are ASSUMED (no measured values for geode conditions were found).
This study grows the same crystal at research resolution (800 x 400) for many speed ratios and measures what changes, so that:
1. it is clear which features of the result are set by the assumed speeds and which are not;
2. a measured shape (aspect ratio, face ratio) of a real crystal could later be turned back into speed ratios (an inverse problem).

Setup (the regime study crystal scaled to 800 cells, like convergence check 5): 40 mm container, fluid saturated at 60 C, run at 20 C, uniform fluid
(valid on the plateau), tau on the plateau, no noise, iron on (material default). Each crystal is grown until its equivalent radius is 120 cells (6 mm).
"""

import dataclasses
import time

from arystal.engine.anisotropy import create_facet_anisotropy_from_material
from arystal.engine.implicit_diffusion import suggest_implicit_time_step
from arystal.engine.material_constants import MaterialConstants
from arystal.engine.regime_indicator import compute_attachment_speed
from arystal.engine.solution_growth import advance_one_step, create_initial_state
from arystal.engine.solution_params import SolutionParams, create_solution_params
from arystal.metrics.growth_metrics import compute_face_distances, compute_height_and_width, compute_iron_ratio_by_sector
from arystal.metrics.shape import compute_equivalent_radius
from arystal.validation.regime_study import BASE_TAU, FASTEST_ORIENTATION_FACTOR, GRID_WIDTH, RUN_CELSIUS, SATURATION_CELSIUS, SEED_RADIUS, TARGET_RADIUS

RESEARCH_GRID = (800, 400)                      # research mode (simulation/modes.py)
SCALE = RESEARCH_GRID[0] / GRID_WIDTH           # 4: cell-based quantities of the regime study are scaled by this
STEPS_BETWEEN_SIZE_CHECKS = 10
MAXIMUM_STEPS = 200_000
M_SPEEDS = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)   # m / r, with r = z = 1
Z_SPEEDS = (0.6, 0.8)                                       # z / r, with m = 0.5 and r = 1
FAMILIES = ("m", "r", "z")


def build_material_with_speeds(material: MaterialConstants, speed_m: float, speed_z: float) -> MaterialConstants:
    """Return a copy of the material with other relative face speeds (r stays 1, the fastest face)."""
    return dataclasses.replace(material, facet_speed_m=speed_m, facet_speed_z=speed_z)


def build_research_params(material: MaterialConstants) -> SolutionParams:
    """Return research-resolution parameters on the plateau, uniform fluid, iron on, no noise, with a time step limited by the interface motion."""
    params = create_solution_params(
        material, RUN_CELSIUS, SATURATION_CELSIUS, grid_width=RESEARCH_GRID[0], grid_height=RESEARCH_GRID[1], seed_radius=SEED_RADIUS * SCALE,
        anisotropy=create_facet_anisotropy_from_material(material), relaxation_time=BASE_TAU * SCALE, iron_ppm=material.default_fluid_iron_ppm,
        backend="numba", diffusion_scheme="uniform",
    )
    speed = compute_attachment_speed(params) * FASTEST_ORIENTATION_FACTOR
    return dataclasses.replace(params, time_step=suggest_implicit_time_step(params, speed))


def grow_until_size(params: SolutionParams, target_radius: float):
    """Grow until the equivalent radius reaches `target_radius` cells; return (state, steps)."""
    state, steps = create_initial_state(params), 0
    while compute_equivalent_radius(state.phase_field) < target_radius and steps < MAXIMUM_STEPS:
        for _ in range(STEPS_BETWEEN_SIZE_CHECKS):
            state = advance_one_step(state, params, None)
            steps += 1
    return state, steps


def compute_sector_shares(state) -> dict[str, float]:
    """Return the share of the deposited silica that each face family (m, r, z) laid down: how big each growth sector is."""
    totals = {family: float(state.sector_silica[index].sum()) for index, family in enumerate(FAMILIES)}
    grand_total = sum(totals.values())
    return {family: totals[family] / grand_total for family in FAMILIES}


def measure_shape_and_iron(state, material: MaterialConstants) -> dict:
    """Return the shape metrics (aspect ratio, r/m and z/m face distances) and the iron of each sector."""
    height, width = compute_height_and_width(state.phase_field)
    faces = compute_face_distances(state.phase_field, material.r_pole_angle_to_c_degrees)
    iron = compute_iron_ratio_by_sector(state.sector_iron, state.sector_silica)
    shares = compute_sector_shares(state)
    return {
        "aspect_ratio": height / width, "face_ratio_r_over_m": faces["r"] / faces["m"], "face_ratio_z_over_m": faces["z"] / faces["m"],
        **{f"iron_ratio_{family}": iron[family] for family in FAMILIES}, **{f"sector_share_{family}": shares[family] for family in FAMILIES},
        "iron_contrast_r_over_m": iron["r"] / iron["m"], "radius": compute_equivalent_radius(state.phase_field),
    }


def run_case(material: MaterialConstants, speed_m: float, speed_z: float) -> dict:
    """Grow one crystal with the given speeds; return its metrics, the final state and the cost."""
    case_material = build_material_with_speeds(material, speed_m, speed_z)
    started = time.perf_counter()
    state, steps = grow_until_size(build_research_params(case_material), TARGET_RADIUS * SCALE)
    row = {"speed_m": speed_m, "speed_r": case_material.facet_speed_r, "speed_z": speed_z, **measure_shape_and_iron(state, case_material)}
    row.update({"steps": steps, "wall_seconds": time.perf_counter() - started})
    return {"row": row, "state": state}


def list_cases() -> list[tuple[float, float]]:
    """Return the (m, z) speed pairs of the study: m swept with r = z, then z swept with m = 0.5."""
    return [(speed_m, 1.0) for speed_m in M_SPEEDS] + [(0.5, speed_z) for speed_z in Z_SPEEDS]
