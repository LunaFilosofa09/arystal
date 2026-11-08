"""Probe: can the model show facet destabilisation at all? (docs/regime_study.md section 8; validation_report.md section 5 point 5)

Larger crystals than check 7 (equivalent radius 80 cells on a 400 x 200 grid, 0.1 mm cells), explicit diffusion, noise ON, at Da far ABOVE the
plateau (tau 1 and 100: diffusion-limited, NOT the realistic regime for geodes), compared with a plateau run (uniform fluid). Two initial
supersaturations: fluid saturated at 60 C run at 15 C (S0 3.3), and silica x1.4 on top (S0 4.6, just above where the driving force is clipped).

    python scripts/facet_stability_probe.py      # a few minutes; results/facet_stability_probe/
"""

import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from arystal.engine.regime_indicator import compute_model_damkohler  # noqa: E402
from arystal.engine.solution_growth import advance_one_step, create_initial_state  # noqa: E402
from arystal.metrics.shape import compute_equivalent_radius  # noqa: E402
from arystal.simulation.material_loader import load_material  # noqa: E402
from arystal.validation.qualitative_check import compute_solidity  # noqa: E402
from arystal.validation.regime_study import build_study_params, compute_facet_fraction  # noqa: E402

OUTPUT_FOLDER = Path(__file__).resolve().parent.parent / "results" / "facet_stability_probe"
GRID = (400, 200)
SEED_RADIUS = 24.0
TARGET_RADIUS = 80.0
RUN_CELSIUS = 15.0
EXTRA_SILICA_FACTORS = (1.0, 1.4)
TAUS = (1.0, 100.0, 40000.0)      # 1 and 100: diffusion-limited (unrealistic for geodes); 40000: on the plateau (uniform fluid)
NOISE_SEED = 7
MAXIMUM_STEPS = 2_000_000
STEPS_BETWEEN_SIZE_CHECKS = 20


def build_probe_params(material, tau: float, silica_factor: float):
    """Return the parameters of one probe run, with noise on."""
    params = build_study_params(material, tau, grid=GRID, seed_radius=SEED_RADIUS, run_celsius=RUN_CELSIUS, uniform=tau > 1000.0)
    return dataclasses.replace(params, initial_silica=params.initial_silica * silica_factor, noise_amplitude=material.thermal_noise_amplitude)


def grow_with_noise(params):
    """Grow until the target radius, with the interface noise drawn from a fixed seed; return the final state."""
    rng = np.random.default_rng(NOISE_SEED)
    state, steps = create_initial_state(params), 0
    while compute_equivalent_radius(state.phase_field) < TARGET_RADIUS and steps < MAXIMUM_STEPS:
        for _ in range(STEPS_BETWEEN_SIZE_CHECKS):
            state = advance_one_step(state, params, rng.standard_normal(params.grid_height * params.grid_width).reshape(params.grid_height, params.grid_width))
            steps += 1
    return state, steps


def main() -> None:
    """Run every case, print, and save the table and a picture of the crystals."""
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    material = load_material()
    rows, fields = [], []
    for silica_factor in EXTRA_SILICA_FACTORS:
        for tau in TAUS:
            params = build_probe_params(material, tau, silica_factor)
            state, steps = grow_with_noise(params)
            row = {"tau": tau, "silica_factor": silica_factor, "initial_supersaturation": params.initial_silica / params.equilibrium_silica,
                   "damkohler_at_target": compute_model_damkohler(params, TARGET_RADIUS), "radius": compute_equivalent_radius(state.phase_field),
                   "solidity": compute_solidity(state.phase_field), "facet_fraction": compute_facet_fraction(state.phase_field, material.r_pole_angle_to_c_degrees), "steps": steps}
            print(json.dumps(row), flush=True)
            rows.append(row)
            fields.append(state.phase_field)
    (OUTPUT_FOLDER / "probe.json").write_text(json.dumps(rows, indent=2))
    figure, axes = plt.subplots(len(EXTRA_SILICA_FACTORS), len(TAUS), figsize=(4 * len(TAUS), 2.4 * len(EXTRA_SILICA_FACTORS)))
    for axis, row, field in zip(axes.flat, rows, fields):
        axis.imshow(field, origin="lower", cmap="Purples", vmin=0, vmax=1.3)
        axis.set_title(f"S0 {row['initial_supersaturation']:.1f}, Da {row['damkohler_at_target']:.1e}, solidity {row['solidity']:.3f}", fontsize=8)
        axis.axis("off")
    figure.tight_layout()
    figure.savefig(OUTPUT_FOLDER / "probe.png", dpi=110)
    plt.close(figure)


if __name__ == "__main__":
    main()
