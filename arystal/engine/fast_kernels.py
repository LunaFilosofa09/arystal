"""Fast (Numba) versions of the time step of the silica-and-iron phase-field model.

These do the SAME calculation as the readable NumPy code of the engine (the REFERENCE):
    phase-field step      <->  anisotropic_phase_field.advance_phase_field + solution_growth.compute_new_phase_field
    transport step        <->  silica_transport + solution_growth.compute_new_silica + iron_incorporation
They exist only for speed: explicit loops over the cells, spread over the CPU cores. Validation check 6 compares them
with the reference step by step. If you want to understand the physics, read the reference; if you want to know what
the fast code does, every line below is commented.

Conventions: arrays are (rows, columns) = (y, x), row 0 is the wall. Neighbour indices past the edge are clamped to the
edge cell, which is the same as the mirror (no-flux) boundary of the reference code.
Floating-point operations are kept in IEEE order (no "fastmath"), so results are reproducible; they can differ from the
reference only in the last bits, because the order of some additions is different.
"""

import math

import numpy as np
from numba import njit, prange

# Where |grad phi|^2 is below this the surface orientation is undefined (same as anisotropy.GRADIENT_THRESHOLD ** 2).
GRADIENT_THRESHOLD_SQUARED = 1e-4 ** 2

# Smallest value of c / c_eq inside the logarithm (same as solution_growth.MINIMUM_CONCENTRATION_RATIO).
MINIMUM_CONCENTRATION_RATIO = 1e-6

# Same constants as iron_incorporation.py.
MINIMUM_SILICA_RATIO = 1e-6
MINIMUM_SOLID_FRACTION = 1e-6

# Cells whose solid fraction changes by less than this in a step neither take up nor give back iron (the amounts would be
# below 1e-18 of the silica scale, under rounding), so the iron incorporation is skipped there: it is the expensive part and
# only the thin interface band changes noticeably.
NEGLIGIBLE_SOLID_CHANGE = 1e-18

NUMBER_OF_FAMILIES = 3
TWO_PI = 2.0 * math.pi


@njit(cache=True, inline="always")
def compute_speed_factor(gradient_x, gradient_y, vertices_x, vertices_y, sharpness, cusp_correction):
    """Return g, the relative growth speed of the surface whose gradient is (gradient_x, gradient_y).

    Smooth maximum (log-sum-exp) of the projections of the speed-polygon corners on the outward normal,
    exactly as anisotropy.compute_speed_factor_from_angle (using cos and sin of the angle directly).
    """
    norm = math.sqrt(gradient_x * gradient_x + gradient_y * gradient_y)  # length of the gradient
    normal_x = -gradient_x / norm  # outward normal = minus the gradient (phi grows towards the crystal)
    normal_y = -gradient_y / norm
    peak = -1.0e300  # largest scaled projection, subtracted to keep exp() from overflowing
    for corner in range(vertices_x.shape[0]):
        scaled = sharpness * (vertices_x[corner] * normal_x + vertices_y[corner] * normal_y)
        if scaled > peak:
            peak = scaled
    total = 0.0
    for corner in range(vertices_x.shape[0]):
        scaled = sharpness * (vertices_x[corner] * normal_x + vertices_y[corner] * normal_y)
        total += math.exp(scaled - peak)
    return (peak + math.log(total)) / sharpness - cusp_correction


@njit(cache=True, parallel=True)
def phase_field_step_kernel(
    phase_field, silica, noise, output,
    interface_epsilon_squared, relaxation_time, time_step, kinetic_coupling, max_driving_force, equilibrium_silica,
    use_anisotropy, vertices_x, vertices_y, sharpness, cusp_correction, noise_amplitude, use_noise,
):
    """Advance the phase field by one time step; write the new field into `output`."""
    rows, columns = phase_field.shape
    noise_scale = noise_amplitude * math.sqrt(time_step / relaxation_time)  # sigma * sqrt(dt / tau)
    for row in prange(rows):  # each row is handled by one thread; rows are independent (they only READ phase_field)
        below = max(row - 1, 0)  # row below, clamped at the wall
        above = min(row + 1, rows - 1)  # row above, clamped at the top
        for column in range(columns):
            left = max(column - 1, 0)
            right = min(column + 1, columns - 1)
            phi = phase_field[row, column]
            # Laplacian: sum of the four neighbours minus four times the cell.
            laplacian = (
                phase_field[above, column] + phase_field[below, column]
                + phase_field[row, right] + phase_field[row, left] - 4.0 * phi
            )
            # Driving force m = lambda * ln(c / c_eq), limited to +-max_driving_force.
            ratio = max(silica[row, column] / equilibrium_silica, MINIMUM_CONCENTRATION_RATIO)
            force = kinetic_coupling * math.log(ratio)
            force = min(max(force, -max_driving_force), max_driving_force)
            push = phi * (1.0 - phi) * (phi - 0.5 + force)  # double-well push towards crystal or fluid
            speed_factor = 1.0  # g = 1 means isotropic growth
            if use_anisotropy:
                gradient_x = 0.5 * (phase_field[row, right] - phase_field[row, left])  # central differences
                gradient_y = 0.5 * (phase_field[above, column] - phase_field[below, column])
                if gradient_x * gradient_x + gradient_y * gradient_y > GRADIENT_THRESHOLD_SQUARED:  # on the interface
                    speed_factor = compute_speed_factor(gradient_x, gradient_y, vertices_x, vertices_y, sharpness, cusp_correction)
            rate = speed_factor * (interface_epsilon_squared * laplacian + push) / relaxation_time
            new_value = phi + time_step * rate
            if use_noise:  # random term, only at the interface (4 phi (1 - phi) is 0 in bulk)
                new_value = new_value + noise_scale * (4.0 * phi * (1.0 - phi)) * noise[row, column]
            output[row, column] = new_value


@njit(cache=True, inline="always")
def compute_family_shares(gradient_x, gradient_y, face_angles, face_families, width, shares):
    """Fill `shares` (3 numbers: m, r, z) with the share of each face family for a surface with this gradient.

    Gaussian weights exp(-(angle distance / width)^2) over all faces, added per family and normalised to 1,
    as iron_partition.compute_family_weights_from_angle. Equal shares where the orientation is undefined.
    """
    for family in range(NUMBER_OF_FAMILIES):
        shares[family] = 0.0
    if gradient_x * gradient_x + gradient_y * gradient_y <= GRADIENT_THRESHOLD_SQUARED:
        for family in range(NUMBER_OF_FAMILIES):
            shares[family] = 1.0 / NUMBER_OF_FAMILIES
        return
    angle = math.atan2(-gradient_y, -gradient_x)  # direction of the outward normal
    total = 0.0
    for face in range(face_angles.shape[0]):
        difference = abs(angle - face_angles[face]) % TWO_PI
        difference = min(difference, TWO_PI - difference)  # smallest angle between the two directions
        weight = math.exp(-((difference / width) ** 2))
        shares[face_families[face]] += weight
        total += weight
    for family in range(NUMBER_OF_FAMILIES):
        shares[family] = shares[family] / total


@njit(cache=True, inline="always")
def compute_diffusion_change(field, solid, row, column, diffusivity):
    """Return d(field)/dt of one cell caused by diffusion through the fluid (closed boundaries).

    Each face between two cells carries diffusivity * (average fluid fraction of the two cells) * (difference of the field).
    What leaves one cell enters the neighbour (the same number with the opposite sign), so nothing is created or lost.
    """
    rows, columns = field.shape
    centre = field[row, column]
    fluid_centre = 1.0 - solid[row, column]
    change = 0.0
    if row + 1 < rows:  # face towards the row above (no face at the top edge)
        change += diffusivity * (0.5 * (fluid_centre + (1.0 - solid[row + 1, column]))) * (field[row + 1, column] - centre)
    if row - 1 >= 0:  # face towards the row below (no face at the wall)
        change += diffusivity * (0.5 * (fluid_centre + (1.0 - solid[row - 1, column]))) * (field[row - 1, column] - centre)
    if column + 1 < columns:  # face towards the right
        change += diffusivity * (0.5 * (fluid_centre + (1.0 - solid[row, column + 1]))) * (field[row, column + 1] - centre)
    if column - 1 >= 0:  # face towards the left
        change += diffusivity * (0.5 * (fluid_centre + (1.0 - solid[row, column - 1]))) * (field[row, column - 1] - centre)
    return change


@njit(cache=True, parallel=True)
def transport_step_kernel(
    old_phase_field, old_solid, new_solid, silica, iron, crystal_iron, sector_iron, sector_silica,
    silica_output, iron_output, crystal_iron_output, sector_iron_output, sector_silica_output,
    time_step, solid_capacity, silica_diffusivity, iron_diffusivity, equilibrium_silica, track_iron, copy_unchanged,
    face_angles, face_families, family_coefficients, sector_width,
):
    """Advance silica (and, if `track_iron`, iron) by one step; write the results into the output arrays.

    old_solid / new_solid are h(phi) before and after the phase-field step. Silica: diffusion minus what the new crystal
    absorbed (Cs * change of the solid fraction). Iron: diffusion, minus what the crystal takes up (by face family),
    plus what dissolving crystal gives back.

    The crystal arrays (crystal_iron, sector_iron, sector_silica) of a cell depend only on that cell, so the output arrays may be
    the very same arrays as the inputs (in-place update). Then `copy_unchanged` is False and the cells that do not change are not
    touched at all, which saves most of the memory traffic of the step.
    """
    rows, columns = silica.shape
    for row in prange(rows):  # rows are independent: they only READ the old fields and WRITE their own outputs
        below = max(row - 1, 0)
        above = min(row + 1, rows - 1)
        shares = np.zeros(NUMBER_OF_FAMILIES)  # per-thread scratch space for the family shares of one cell
        for column in range(columns):
            solid_change = new_solid[row, column] - old_solid[row, column]
            diffusion = compute_diffusion_change(silica, old_solid, row, column, silica_diffusivity)
            silica_output[row, column] = silica[row, column] + time_step * diffusion - solid_capacity * solid_change
            if not track_iron:
                continue
            if abs(solid_change) <= NEGLIGIBLE_SOLID_CHANGE:  # nothing grows or dissolves here: only the iron diffusion matters
                if copy_unchanged:  # separate output arrays: carry the old values over
                    for family in range(NUMBER_OF_FAMILIES):
                        sector_iron_output[family, row, column] = sector_iron[family, row, column]
                        sector_silica_output[family, row, column] = sector_silica[family, row, column]
                    crystal_iron_output[row, column] = crystal_iron[row, column]
                iron_diffusion = compute_diffusion_change(iron, old_solid, row, column, iron_diffusivity)
                iron_output[row, column] = iron[row, column] + time_step * iron_diffusion
                continue
            left = max(column - 1, 0)
            right = min(column + 1, columns - 1)
            gradient_x = 0.5 * (old_phase_field[row, right] - old_phase_field[row, left])
            gradient_y = 0.5 * (old_phase_field[above, column] - old_phase_field[below, column])
            compute_family_shares(gradient_x, gradient_y, face_angles, face_families, sector_width, shares)
            fluid_iron = max(iron[row, column], 0.0)  # iron available in the fluid of this cell
            safe_silica = max(silica[row, column], MINIMUM_SILICA_RATIO * equilibrium_silica)
            iron_to_silica = fluid_iron / safe_silica  # Fe/Si of the fluid
            silica_deposited = solid_capacity * max(solid_change, 0.0)  # silica that becomes crystal in this step
            wanted_total = 0.0
            for family in range(NUMBER_OF_FAMILIES):  # iron the crystal would like to take, per family
                wanted_total += family_coefficients[family] * iron_to_silica * (shares[family] * silica_deposited)
            scale = 0.0  # cannot take more iron than the cell has
            if wanted_total > 0.0:
                scale = min(wanted_total, fluid_iron) / wanted_total
            fraction_dissolved = min(max(-solid_change, 0.0) / max(old_solid[row, column], MINIMUM_SOLID_FRACTION), 1.0)
            kept = 1.0 - fraction_dissolved  # share of the crystal that stays
            taken_total = 0.0
            for family in range(NUMBER_OF_FAMILIES):
                taken = family_coefficients[family] * iron_to_silica * (shares[family] * silica_deposited) * scale
                sector_iron_output[family, row, column] = sector_iron[family, row, column] * kept + taken
                sector_silica_output[family, row, column] = sector_silica[family, row, column] * kept + shares[family] * silica_deposited
                taken_total += taken
            crystal_iron_output[row, column] = crystal_iron[row, column] * kept + taken_total
            exchange = crystal_iron_output[row, column] - crystal_iron[row, column]  # what the crystal gained (negative if it gave back)
            iron_diffusion = compute_diffusion_change(iron, old_solid, row, column, iron_diffusivity)
            iron_output[row, column] = iron[row, column] + time_step * iron_diffusion - exchange
