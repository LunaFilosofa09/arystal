"""Kinetic anisotropy of the amethyst section: growth speed as a function of surface orientation.

Geometry of the 2D section (see docs/physics_model.md):
  The section plane contains the c-axis (pointing up, +y) and the pole of one prism face m.
  Seen in that plane:
    - the two m faces are vertical; their outward normals point along +x and -x,
    - the r face {10-11} has its pole tilted by `r_pole_angle_to_c` from +y, towards +x (right side),
    - the z face {01-11} has its pole tilted by the same angle towards -x (left side).
  r and z sit on opposite sides because of the 3-fold axis: going around the c-axis the
  terminations alternate r, z, r, z, ... every 60 degrees, and the plane cuts opposite sides.
  The same faces are mirrored below (their normals pointing down) only so that the speed
  function is defined for every direction; the crystal is attached to the wall there.

Model (Frank's kinetic Wulff construction, smoothed):
  Each face family has a normal growth speed v_face. The speed of a surface with outward
  normal angle theta is
        g(theta) = max over polygon vertices k of ( V_k . n(theta) )      (a "support function")
  where the polygon is the shape bounded by half-planes  n_face . x <= v_face.
  g equals v_face exactly at each face normal, where it has a CUSP (a V-shaped minimum):
  slow orientations are the ones that survive as flat faces, fast orientations grow out and
  vanish. The cusp is rounded with a smooth maximum (log-sum-exp) of sharpness beta so the
  phase-field equation stays smooth.

IMPORTANT: the face speeds are INPUTS (assumed, see materials/amethyst.yaml). This model
reproduces the habit those speeds imply; it does not predict the speeds themselves.
"""

import math
from dataclasses import dataclass

import numpy as np
from scipy.spatial import HalfspaceIntersection

from arystal.engine.material_constants import MaterialConstants

# A face counts as present only if its edge on the polygon is longer than this
# (relative to the polygon size); otherwise a faster face has "grown out" and vanished.
MINIMUM_FACE_EDGE_LENGTH = 1e-6

# Where |grad phi| is below this the surface orientation is undefined (bulk fluid or crystal);
# the speed factor there is set to 1 because the phase field does not move there anyway.
GRADIENT_THRESHOLD = 1e-4


@dataclass(frozen=True)
class FacetAnisotropy:
    """Everything needed to evaluate the speed factor g(theta).

    vertices: (K, 2) array of the corners of the speed polygon (relative speed units).
    sharpness: beta of the smooth maximum.
    cusp_correction: constant subtracted from g so that g equals the face speed exactly at
        face normals (where two corners tie and the smooth maximum overshoots by ln(2)/beta).
    """

    vertices: np.ndarray
    sharpness: float
    cusp_correction: float


def compute_face_normal_angles(r_pole_angle_to_c_degrees: float) -> dict[str, float]:
    """Return the outward normal angle (radians, measured from +x) of each face in the section.

    The pole of r is `r_pole_angle_to_c` away from +y (the c-axis), i.e. at
    (90 - r_pole_angle_to_c) degrees from +x. z is its mirror image across the c-axis.
    """
    tilt = math.radians(90.0 - r_pole_angle_to_c_degrees)
    return {
        "m_right": 0.0,
        "r_upper_right": tilt,
        "z_upper_left": math.pi - tilt,
        "m_left": math.pi,
        "z_lower_left": math.pi + tilt,
        "r_lower_right": 2.0 * math.pi - tilt,
    }


def get_face_speed(face_name: str, speed_m: float, speed_r: float, speed_z: float) -> float:
    """Return the speed of a face, chosen by its family (m, r or z) from its name."""
    if face_name.startswith("m"):
        return speed_m
    if face_name.startswith("r"):
        return speed_r
    return speed_z


def build_half_planes(angles: dict[str, float], speed_m: float, speed_r: float, speed_z: float) -> np.ndarray:
    """Return half-planes as rows [nx, ny, -speed] meaning nx*x + ny*y - speed <= 0 (scipy format)."""
    rows = []
    for name, angle in angles.items():
        speed = get_face_speed(name, speed_m, speed_r, speed_z)
        rows.append([math.cos(angle), math.sin(angle), -speed])
    return np.array(rows)


def compute_polygon_vertices(half_planes: np.ndarray) -> np.ndarray:
    """Return the corners of the polygon bounded by the half-planes, ordered counter-clockwise."""
    corners = HalfspaceIntersection(half_planes, np.zeros(2)).intersections
    angles = np.arctan2(corners[:, 1], corners[:, 0])
    return corners[np.argsort(angles)]


def find_missing_faces(vertices: np.ndarray, half_planes: np.ndarray) -> list[int]:
    """Return the indices of half-planes whose face does not appear on the polygon (edge length ~ 0)."""
    missing = []
    for index, (nx, ny, minus_speed) in enumerate(half_planes):
        distances = vertices @ np.array([nx, ny]) + minus_speed
        corners_on_face = np.sum(np.abs(distances) < MINIMUM_FACE_EDGE_LENGTH)
        if corners_on_face < 2:
            missing.append(index)
    return missing


def create_facet_anisotropy(
    speed_m: float, speed_r: float, speed_z: float, r_pole_angle_to_c_degrees: float, sharpness: float
) -> FacetAnisotropy:
    """Build the anisotropy from the three face speeds.

    Raises ValueError if some face is so fast, relative to the others, that it would not
    appear on the crystal at all (Frank: fast faces grow out), because then the requested
    face speeds cannot be honoured.
    """
    angles = compute_face_normal_angles(r_pole_angle_to_c_degrees)
    half_planes = build_half_planes(angles, speed_m, speed_r, speed_z)
    vertices = compute_polygon_vertices(half_planes)
    missing = find_missing_faces(vertices, half_planes)
    if missing:
        names = [list(angles)[i] for i in missing]
        raise ValueError(f"These faces would grow out and vanish with the given speeds: {names}")
    return FacetAnisotropy(vertices=vertices, sharpness=sharpness, cusp_correction=math.log(2.0) / sharpness)


def create_facet_anisotropy_from_material(material: MaterialConstants) -> FacetAnisotropy:
    """Build the anisotropy from the material constants."""
    return create_facet_anisotropy(
        material.facet_speed_m, material.facet_speed_r, material.facet_speed_z,
        material.r_pole_angle_to_c_degrees, material.cusp_sharpness,
    )


def compute_speed_factor_from_angle(angle: np.ndarray, anisotropy: FacetAnisotropy) -> np.ndarray:
    """Return g(theta): the relative growth speed of a surface whose outward normal is at `angle`.

    Smooth maximum of the projections of the polygon corners on the normal direction.
    """
    normal = np.stack([np.cos(angle), np.sin(angle)])
    projections = np.tensordot(anisotropy.vertices, normal, axes=([1], [0]))
    scaled = anisotropy.sharpness * projections
    peak = scaled.max(axis=0)
    log_sum = peak + np.log(np.exp(scaled - peak).sum(axis=0))
    return log_sum / anisotropy.sharpness - anisotropy.cusp_correction


def compute_largest_speed_factor(anisotropy: FacetAnisotropy) -> float:
    """Return the maximum of g over all directions (used to check the time step is stable)."""
    angles = np.linspace(0.0, 2.0 * math.pi, 3600, endpoint=False)
    return float(compute_speed_factor_from_angle(angles, anisotropy).max())


def compute_smallest_speed_factor(anisotropy: FacetAnisotropy) -> float:
    """Return the minimum of g over all directions."""
    angles = np.linspace(0.0, 2.0 * math.pi, 3600, endpoint=False)
    return float(compute_speed_factor_from_angle(angles, anisotropy).min())
