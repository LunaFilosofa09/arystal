"""One time step of the model computed with the fast (Numba) kernels. Same inputs and outputs as the reference step.

`advance_one_step_fast(state, params, noise)` does what `solution_growth.advance_one_step` does, using fast_kernels.py.
The reference (NumPy) version stays the readable definition of the physics; validation check 6 compares the two.
"""

import numpy as np

from arystal.engine.fast_kernels import phase_field_step_kernel, transport_step_kernel
from arystal.engine.silica_transport import compute_solid_fraction
from arystal.engine.solution_params import MODEL_DIFFUSIVITY, SolutionParams

# Placeholder arrays for features that are switched off (the kernels need arrays of the right type anyway).
EMPTY_VECTOR = np.zeros(1)
EMPTY_INTEGERS = np.zeros(1, dtype=np.int64)
EMPTY_SECTOR_ARRAY = np.zeros((3, 1, 1))
EMPTY_NOISE = np.zeros((1, 1))


def set_thread_count(threads: int) -> int:
    """Use `threads` CPU threads for the fast kernels (limited to what Numba allows); returns the number in use."""
    import numba

    numba.set_num_threads(max(1, min(int(threads), numba.config.NUMBA_NUM_THREADS)))
    return numba.get_num_threads()


def get_anisotropy_arguments(params: SolutionParams) -> tuple:
    """Return the anisotropy arguments of the phase-field kernel: (use, corners x, corners y, sharpness, cusp correction)."""
    if params.anisotropy is None:
        return False, EMPTY_VECTOR, EMPTY_VECTOR, 1.0, 0.0
    anisotropy = params.anisotropy
    return (
        True, np.ascontiguousarray(anisotropy.vertices[:, 0]), np.ascontiguousarray(anisotropy.vertices[:, 1]),
        float(anisotropy.sharpness), float(anisotropy.cusp_correction),
    )


def get_sector_arguments(params: SolutionParams) -> tuple:
    """Return the iron-sector arguments of the transport kernel: (track iron, face angles, face families, coefficients per family, width)."""
    partition = params.sector_partition
    if partition is None:
        return False, EMPTY_VECTOR, EMPTY_INTEGERS, EMPTY_VECTOR, 1.0
    from arystal.engine.iron_partition import compute_family_coefficients

    return (
        True, np.ascontiguousarray(partition.face_angles, dtype=np.float64), np.ascontiguousarray(partition.face_families, dtype=np.int64),
        np.ascontiguousarray(compute_family_coefficients(partition), dtype=np.float64), float(partition.width),
    )


def advance_phase_field_fast(state, params: SolutionParams, noise: np.ndarray | None) -> np.ndarray:
    """Return the phase field after one step (fast kernel)."""
    use_anisotropy, vertices_x, vertices_y, sharpness, cusp_correction = get_anisotropy_arguments(params)
    use_noise = noise is not None and params.noise_amplitude > 0.0
    output = np.empty_like(state.phase_field)
    phase_field_step_kernel(
        state.phase_field, state.silica, noise if use_noise else EMPTY_NOISE, output,
        params.interface_epsilon**2, params.relaxation_time, params.time_step, params.kinetic_coupling, params.max_driving_force,
        params.equilibrium_silica, use_anisotropy, vertices_x, vertices_y, sharpness, cusp_correction, params.noise_amplitude, use_noise,
    )
    return output


def advance_transport_fast(state, new_phase_field: np.ndarray, params: SolutionParams, in_place: bool = False, diffusion_scale: float = 1.0):
    """Return (silica, iron, crystal iron, iron by sector, silica by sector) after one step (fast kernel).

    With `in_place` the crystal arrays (crystal iron and the by-sector arrays) of `state` are updated directly instead of
    copied: faster, but the arrays of the old state change too, so the old state must not be used afterwards.
    `diffusion_scale` multiplies the diffusivities (0 switches the diffusion off: used by the uniform-fluid scheme).
    """
    track_iron, face_angles, face_families, coefficients, width = get_sector_arguments(params)
    old_solid = compute_solid_fraction(state.phase_field)
    new_solid = compute_solid_fraction(new_phase_field)
    silica_output = np.empty_like(state.silica)
    if track_iron and in_place:
        iron_output, crystal_output = np.empty_like(state.iron), state.crystal_iron
        sector_iron_output, sector_silica_output = state.sector_iron, state.sector_silica
    elif track_iron:
        iron_output, crystal_output = np.empty_like(state.iron), np.empty_like(state.crystal_iron)
        sector_iron_output, sector_silica_output = np.empty_like(state.sector_iron), np.empty_like(state.sector_silica)
    else:
        iron_output, crystal_output = state.iron, state.crystal_iron
        sector_iron_output, sector_silica_output = state.sector_iron, state.sector_silica
    transport_step_kernel(
        state.phase_field, old_solid, new_solid, state.silica, state.iron, state.crystal_iron,
        state.sector_iron if track_iron else EMPTY_SECTOR_ARRAY, state.sector_silica if track_iron else EMPTY_SECTOR_ARRAY,
        silica_output, iron_output, crystal_output,
        sector_iron_output if track_iron else EMPTY_SECTOR_ARRAY, sector_silica_output if track_iron else EMPTY_SECTOR_ARRAY,
        params.time_step, params.solid_capacity, diffusion_scale * MODEL_DIFFUSIVITY, diffusion_scale * MODEL_DIFFUSIVITY * params.iron_diffusivity_ratio,
        params.equilibrium_silica, track_iron, not in_place, face_angles, face_families, coefficients, width,
    )
    return silica_output, iron_output, crystal_output, sector_iron_output, sector_silica_output


def advance_one_step_fast(state, params: SolutionParams, noise: np.ndarray | None = None, in_place: bool = False):
    """Advance all fields by one time step with the fast kernels and return the new state (see advance_transport_fast for `in_place`)."""
    import dataclasses

    new_phase_field = advance_phase_field_fast(state, params, noise)
    silica, iron, crystal_iron, sector_iron, sector_silica = advance_transport_fast(state, new_phase_field, params, in_place)
    return dataclasses.replace(
        state, phase_field=new_phase_field, silica=silica, iron=iron, crystal_iron=crystal_iron,
        sector_iron=sector_iron, sector_silica=sector_silica,
    )
