"""The well-mixed limit: dissolved silica and iron kept uniform in the fluid (very fast diffusion, Damkohler number Da -> 0).

WHEN IT IS VALID: when the attachment of silica to the surface is much slower than its diffusion through the fluid. Then the
concentration is the same everywhere (no depletion halo) and only changes slowly as the crystal uses silica up. The regime study
(docs/regime_study.md) shows that below Da of about 0.06 the measured supersaturation at the surface equals that of the bulk to
within 5% or better, and the evidence (docs/kinetic_regime.md) puts real geode crystals at Da of 1e-7 to 1e-3.

WHAT IT DOES: at each step the phase field advances with the (uniform) supersaturation, and the uniform concentration is then recomputed
so that the total silica (dissolved + held by the crystal) stays exactly what it was:
        c_new = (total silica - Cs * sum of the new solid fraction) / number of cells
and the same for iron. No diffusion equation is solved, so a step costs only the phase-field update, and the time step is chosen by how
far the interface moves (suggest_implicit_time_step), not by the diffusion.

It is NOT a simplification of the surface physics (the phase-field kinetics, the face anisotropy and the iron sectors are unchanged); it
only drops the transport of dissolved species, which in this regime has no visible effect. It cannot show a depletion halo or any effect of
a slow supply: use the explicit or implicit scheme for those.
"""

import dataclasses

import numpy as np

from arystal.engine.iron_incorporation import compute_iron_exchange
from arystal.engine.silica_transport import compute_solid_fraction


def advance_one_step_uniform(state, params, noise: np.ndarray | None = None, in_place: bool = False):
    """Advance one step with uniform dissolved silica and iron (see the module description) and return the new state.

    With the fast backend the iron bookkeeping uses the same Numba kernel as the other schemes with the diffusion switched off,
    and the uniform concentrations are set afterwards from the conserved totals.
    """
    from arystal.engine.solution_growth import compute_new_phase_field

    fast = params.backend == "numba"
    if fast:
        from arystal.engine.fast_step import advance_phase_field_fast, advance_transport_fast

        new_phase_field = advance_phase_field_fast(state, params, noise)
    else:
        new_phase_field = compute_new_phase_field(state, params, noise)
    old_solid, new_solid = compute_solid_fraction(state.phase_field), compute_solid_fraction(new_phase_field)
    cells = state.silica.size
    total_silica = state.silica.sum() + params.solid_capacity * old_solid.sum()
    new_silica = np.full_like(state.silica, (total_silica - params.solid_capacity * new_solid.sum()) / cells)
    if params.sector_partition is None:
        return dataclasses.replace(state, phase_field=new_phase_field, silica=new_silica)
    total_iron = state.iron.sum() + state.crystal_iron.sum()  # before the (possibly in-place) update of the crystal arrays
    if fast:
        _, _, crystal_iron, sector_iron, sector_silica = advance_transport_fast(state, new_phase_field, params, in_place, diffusion_scale=0.0)
    else:
        _, crystal_iron, sector_iron, sector_silica = compute_iron_exchange(
            state.iron, state.crystal_iron, state.sector_iron, state.sector_silica, state.silica, state.phase_field, new_phase_field, params
        )
    new_iron = np.full_like(state.iron, (total_iron - crystal_iron.sum()) / cells)
    return dataclasses.replace(
        state, phase_field=new_phase_field, silica=new_silica, iron=new_iron, crystal_iron=crystal_iron,
        sector_iron=sector_iron, sector_silica=sector_silica,
    )
