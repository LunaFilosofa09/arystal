"""Sector zoning: how much iron a growing surface takes up, depending on which face it belongs to.

Different crystal faces incorporate different amounts of impurity (sector zoning). Here the
"sector" of a piece of surface is decided by the direction its normal points to: a surface
pointing like an r face takes up iron like an r face, and so on. The coefficient passes smoothly
from one face family to the next (Gaussian weights in angle) so the model stays symmetric and smooth.

The coefficient is a molar distribution coefficient:
    (Fe / Si in the crystal) = coefficient * (Fe / Si in the fluid)
It is defined per unit of silica deposited, so it does not depend on the scaled crystal capacity.

IMPORTANT: the coefficients are ASSUMED (no measured values found). Only the order r > z > m is
supported by the literature, qualitatively.
"""

import math
from dataclasses import dataclass

import numpy as np

from arystal.engine.anisotropic_phase_field import compute_gradient, compute_outward_normal_angle
from arystal.engine.anisotropy import GRADIENT_THRESHOLD, compute_face_normal_angles, get_face_speed
from arystal.engine.material_constants import MaterialConstants


# Index of each face family in the per-sector arrays: m, r, z (the first letter of the face name).
FAMILY_INDEX = {"m": 0, "r": 1, "z": 2}
NUMBER_OF_FAMILIES = 3


@dataclass(frozen=True)
class SectorPartition:
    """Incorporation coefficient of every face of the section.

    face_angles: outward normal angle (radians from +x) of each face.
    face_families: family of each face: 0 = m, 1 = r, 2 = z.
    coefficients: distribution coefficient of each face.
    width: Gaussian width (radians) of the transition between faces.
    mean_coefficient: used where the surface orientation is undefined.
    """

    face_angles: np.ndarray
    face_families: np.ndarray
    coefficients: np.ndarray
    width: float
    mean_coefficient: float


def create_sector_partition(material: MaterialConstants) -> SectorPartition:
    """Build the sector partition of the section from the material constants."""
    angles = compute_face_normal_angles(material.r_pole_angle_to_c_degrees)
    names = list(angles)
    coefficients = [
        get_face_speed(name, material.partition_m, material.partition_r, material.partition_z) for name in names
    ]
    return SectorPartition(
        face_angles=np.array([angles[name] for name in names]),
        face_families=np.array([FAMILY_INDEX[name[0]] for name in names]),
        coefficients=np.array(coefficients),
        width=math.radians(material.sector_transition_width_degrees),
        mean_coefficient=float(np.mean(coefficients)),
    )


def compute_angle_distance(angle: np.ndarray, reference: float) -> np.ndarray:
    """Return the smallest difference between angles (radians), handling the wrap-around at 2*pi."""
    difference = np.abs(angle - reference) % (2.0 * math.pi)
    return np.minimum(difference, 2.0 * math.pi - difference)


def compute_face_weights(angle: np.ndarray, partition: SectorPartition) -> np.ndarray:
    """Return the weight of every face for surfaces whose outward normal is at `angle`: shape (faces, N).

    Weight exp(-(angle distance / width)^2), not yet normalised.
    """
    return np.stack([
        np.exp(-((compute_angle_distance(angle, face) / partition.width) ** 2)) for face in partition.face_angles
    ])


def compute_partition_from_angle(angle: np.ndarray, partition: SectorPartition) -> np.ndarray:
    """Return the incorporation coefficient for surfaces whose outward normal is at `angle`.

    Weighted average of the face coefficients.
    """
    weights = compute_face_weights(angle, partition)
    return (weights * partition.coefficients[:, None]).sum(axis=0) / weights.sum(axis=0)


def compute_family_weights_from_angle(angle: np.ndarray, partition: SectorPartition) -> np.ndarray:
    """Return the share (m, r, z) of each face family for surfaces at `angle`: shape (3, N), columns sum to 1."""
    weights = compute_face_weights(angle, partition)
    shares = np.zeros((NUMBER_OF_FAMILIES, weights.shape[1]))
    for face_index, family in enumerate(partition.face_families):
        shares[family] += weights[face_index]
    return shares / shares.sum(axis=0)


def compute_family_weight_field(phase_field: np.ndarray, partition: SectorPartition) -> np.ndarray:
    """Return the (3, H, W) share of each face family in every cell (equal shares where the orientation is undefined)."""
    gradient_x, gradient_y = compute_gradient(phase_field)
    on_interface = gradient_x**2 + gradient_y**2 > GRADIENT_THRESHOLD**2
    field = np.full((NUMBER_OF_FAMILIES,) + phase_field.shape, 1.0 / NUMBER_OF_FAMILIES)
    angle = compute_outward_normal_angle(gradient_x[on_interface], gradient_y[on_interface])
    field[:, on_interface] = compute_family_weights_from_angle(angle, partition)
    return field


def compute_family_coefficients(partition: SectorPartition) -> np.ndarray:
    """Return the incorporation coefficient of each face family (m, r, z), shape (3,)."""
    coefficients = np.zeros(NUMBER_OF_FAMILIES)
    for face_index, family in enumerate(partition.face_families):
        coefficients[family] = partition.coefficients[face_index]
    return coefficients


def compute_partition_field(phase_field: np.ndarray, partition: SectorPartition) -> np.ndarray:
    """Return the incorporation coefficient for every cell (mean coefficient where the orientation is undefined)."""
    gradient_x, gradient_y = compute_gradient(phase_field)
    on_interface = gradient_x**2 + gradient_y**2 > GRADIENT_THRESHOLD**2
    field = np.full_like(phase_field, partition.mean_coefficient)
    angle = compute_outward_normal_angle(gradient_x[on_interface], gradient_y[on_interface])
    field[on_interface] = compute_partition_from_angle(angle, partition)
    return field
