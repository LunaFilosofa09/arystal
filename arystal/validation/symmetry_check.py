"""Validation check 2 (symmetry) and a check that the faceted shape follows Frank's construction.

Tests:
  A. With equal r and z speeds and no noise, the crystal and the silica field are mirror
     symmetric about the c-axis (full model, with silica diffusion).
  B. With DIFFERENT r and z speeds the symmetry is broken. This proves test A is not trivially
     true: asymmetry appears when the physics says so (r and z are not equivalent in a trigonal
     crystal), and so a symmetric result is due to the equal inputs, not to a blind code.
  C. Frank construction: with a constant driving force each flat face ends up where the
     construction predicts, with the predicted orientation.

WHAT THESE TESTS DO NOT SHOW: that real amethyst has these face speeds, that the cap of a real
crystal is symmetric, or that the facets seen are free of numerical rounding. They check that
the code does what its equations say.
"""

import math

import numpy as np

from arystal.engine.anisotropic_phase_field import advance_phase_field
from arystal.engine.anisotropy import (
    FacetAnisotropy,
    compute_face_normal_angles,
    create_facet_anisotropy,
    create_facet_anisotropy_from_material,
)
from arystal.engine.grid import create_half_disc_seed
from arystal.engine.isotropic_params import IsotropicParams
from arystal.engine.isotropic_theory import compute_flat_front_speed
from arystal.engine.material_constants import MaterialConstants
from arystal.engine.solution_params import create_solution_params
from arystal.metrics.facets import measure_facet_distance
from arystal.metrics.symmetry import (
    compute_area_asymmetry_fraction,
    compute_crystal_mask,
    compute_mirror_asymmetry,
)
from arystal.simulation.solution_run import iterate_solution_growth
from arystal.validation.check_result import CheckResult

LIMITS_NOTE = (
    "Limits: these tests check the code against its own equations. They do not show that real amethyst "
    "has the assumed face speeds (ASSUMED in the material file), nor that facets are free of numerical rounding."
)

# Test A: full model, small and strongly supersaturated so the crystal grows visibly in a short run.
SYMMETRY_GRID_WIDTH = 240
SYMMETRY_GRID_HEIGHT = 120
SYMMETRY_RUN_CELSIUS = 15.0
SYMMETRY_SATURATION_CELSIUS = 60.0
SYMMETRY_DURATION = 800.0
SYMMETRY_STEPS_PER_SNAPSHOT = 400
SYMMETRY_SEED_RADIUS = 12.0
MAX_FIELD_ASYMMETRY = 1e-9
MINIMUM_GROWTH_FACTOR = 1.5  # the crystal must have grown to at least this times its starting area

# Tests B and C: constant driving force, no silica.
CONSTANT_FORCE = 0.3
FRANK_GRID_WIDTH = 400
FRANK_GRID_HEIGHT = 260
FRANK_STEPS = 3500
FRANK_SEED_RADIUS = 12.0
FRANK_TIME_STEP = 0.1
FRANK_EPSILON = 1.0
FRANK_TAU = 1.0
# Test C: a face position may differ from the prediction by this fraction. Early on, while the seed is
# still curved, interface curvature slows the faces; with the values used here that costs about
# (epsilon^2 / (v0 * tau)) * ln(R_final / R0) ~ 6 cells of ~160, i.e. ~4%.
MAX_FACE_POSITION_ERROR = 0.06
FACET_ANGLE_TOLERANCE_DEGREES = 3.0
MINIMUM_FACE_CELLS = 20

# Test B: z face slowed to this fraction of r.
ASYMMETRIC_Z_FRACTION = 0.7
MIN_BROKEN_SYMMETRY_FRACTION = 0.01


def check_symmetry_with_equal_faces(material: MaterialConstants) -> CheckResult:
    """Test A: equal r and z speeds give a mirror-symmetric crystal and silica field."""
    anisotropy = create_facet_anisotropy_from_material(material)
    params = create_solution_params(
        material, SYMMETRY_RUN_CELSIUS, SYMMETRY_SATURATION_CELSIUS,
        grid_width=SYMMETRY_GRID_WIDTH, grid_height=SYMMETRY_GRID_HEIGHT,
        seed_radius=SYMMETRY_SEED_RADIUS, anisotropy=anisotropy,
    )
    snapshots = list(iterate_solution_growth(params, SYMMETRY_STEPS_PER_SNAPSHOT, SYMMETRY_DURATION))
    last = snapshots[-1]
    phase_error = compute_mirror_asymmetry(last.phase_field)
    silica_error = compute_mirror_asymmetry(last.silica) / params.equilibrium_silica
    growth_factor = last.crystal_area / snapshots[0].crystal_area
    passed = max(phase_error, silica_error) <= MAX_FIELD_ASYMMETRY and growth_factor >= MINIMUM_GROWTH_FACTOR
    message = (
        f"Largest left-right difference: phase field {phase_error:.1e}, silica (relative) {silica_error:.1e} "
        f"(limit {MAX_FIELD_ASYMMETRY:.0e}); crystal grew to {growth_factor:.1f}x its starting area "
        f"(needs >= {MINIMUM_GROWTH_FACTOR}x, otherwise the test shows nothing)."
    )
    return CheckResult("symmetric about the c-axis when r = z (no noise)", passed, message)


def run_constant_force_growth(anisotropy: FacetAnisotropy) -> np.ndarray:
    """Grow a seed with a constant driving force (no silica) and return the final phase field."""
    phase_field = create_half_disc_seed(FRANK_GRID_WIDTH, FRANK_GRID_HEIGHT, FRANK_SEED_RADIUS, FRANK_EPSILON)
    for _ in range(FRANK_STEPS):
        phase_field = advance_phase_field(
            phase_field, CONSTANT_FORCE, anisotropy, FRANK_EPSILON, FRANK_TAU, FRANK_TIME_STEP
        )
    return phase_field


def check_symmetry_breaks_with_different_faces(material: MaterialConstants) -> CheckResult:
    """Test B: a slower z face makes the section asymmetric."""
    anisotropy = create_facet_anisotropy(
        material.facet_speed_m, material.facet_speed_r, ASYMMETRIC_Z_FRACTION * material.facet_speed_r,
        material.r_pole_angle_to_c_degrees, material.cusp_sharpness,
    )
    final = run_constant_force_growth(anisotropy)
    asymmetry = compute_area_asymmetry_fraction(final)
    message = (
        f"With z at {ASYMMETRIC_Z_FRACTION:.0%} of r, {100 * asymmetry:.1f}% of the crystal area has no mirror partner "
        f"(needs >= {100 * MIN_BROKEN_SYMMETRY_FRACTION:.0f}%)."
    )
    return CheckResult("symmetry is broken when r and z differ", asymmetry >= MIN_BROKEN_SYMMETRY_FRACTION, message)


def compute_predicted_face_distance(face_speed: float) -> float:
    """Return where Frank's construction puts a face: R0 + (relative speed) * (flat speed) * time.

    R0 is the radius of the starting seed, which touches every face; the flat speed is the
    exact speed of a flat front of the isotropic model (isotropic_theory.py).
    """
    flat_speed = compute_flat_front_speed(IsotropicParams(driving_force=CONSTANT_FORCE))
    return FRANK_SEED_RADIUS + face_speed * flat_speed * FRANK_STEPS * FRANK_TIME_STEP


def build_face_list(material: MaterialConstants) -> list[tuple[str, float, float]]:
    """Return (name, normal angle, relative speed) of the three upper faces that are checked."""
    angles = compute_face_normal_angles(material.r_pole_angle_to_c_degrees)
    return [
        ("m", angles["m_right"], material.facet_speed_m),
        ("r", angles["r_upper_right"], material.facet_speed_r),
        ("z", angles["z_upper_left"], material.facet_speed_z),
    ]


def measure_face_error(final: np.ndarray, angle: float, speed: float) -> tuple[float, int, float]:
    """Return (measured distance, cells on the face, relative error vs prediction) for one face."""
    measured, cells = measure_facet_distance(final, angle, FACET_ANGLE_TOLERANCE_DEGREES)
    predicted = compute_predicted_face_distance(speed)
    return measured, cells, abs(measured - predicted) / predicted


def compute_apex_deficit(final_mask: np.ndarray, material: MaterialConstants) -> tuple[int, float]:
    """Return how much lower the simulated apex is than the sharp polygon's apex, in cells and as a fraction.

    The sharp polygon's apex is where the r and z faces would meet: at height
    (distance of r face) / cos(angle between the r pole and the c-axis).
    """
    centre_column = final_mask.shape[1] // 2
    simulated = int(np.nonzero(final_mask[:, centre_column])[0].max())
    r_distance = compute_predicted_face_distance(material.facet_speed_r)
    sharp = r_distance / math.cos(math.radians(material.r_pole_angle_to_c_degrees))
    return int(sharp - simulated), float((sharp - simulated) / sharp)


def check_frank_construction(material: MaterialConstants) -> CheckResult:
    """Test C: each flat face sits where Frank's construction puts it, and has the right orientation."""
    anisotropy = create_facet_anisotropy_from_material(material)
    final = run_constant_force_growth(anisotropy)
    parts = []
    passed = True
    for name, angle, speed in build_face_list(material):
        measured, cells, error = measure_face_error(final, angle, speed)
        passed &= cells >= MINIMUM_FACE_CELLS and error <= MAX_FACE_POSITION_ERROR
        parts.append(f"{name}: {measured:.1f} vs {compute_predicted_face_distance(speed):.1f} cells ({100 * error:.1f}% off, {cells} surface cells)")
    deficit_cells, deficit_fraction = compute_apex_deficit(compute_crystal_mask(final), material)
    message = (
        "Face distance from the seed centre, measured vs predicted: " + "; ".join(parts)
        + f" (limit {100 * MAX_FACE_POSITION_ERROR:.0f}%). KNOWN LIMITATION, not gated: the apex is "
        f"{deficit_cells} cells ({100 * deficit_fraction:.0f}%) lower than the sharp polygon's, because orientations "
        "between r and z have almost no stiffness and interface curvature keeps the apex rounded."
    )
    return CheckResult("flat faces sit where Frank's construction puts them", passed, message)


def run_symmetry_check(material: MaterialConstants) -> list[CheckResult]:
    """Run all tests of validation check 2."""
    return [
        check_symmetry_with_equal_faces(material),
        check_symmetry_breaks_with_different_faces(material),
        check_frank_construction(material),
    ]
