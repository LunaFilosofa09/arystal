"""Run the face-speed study (docs/face_speed_study.md): shape and iron sectors for many m : r : z ratios at research resolution.

    python scripts/face_speed_study.py          # about 5-10 minutes; results in results/face_speed_study/
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from arystal.simulation.material_loader import load_material  # noqa: E402
from arystal.storage.rendering import render_crystal_rgb  # noqa: E402
from arystal.validation.face_speed_study import M_SPEEDS, list_cases, run_case  # noqa: E402

OUTPUT_FOLDER = Path(__file__).resolve().parent.parent / "results" / "face_speed_study"
PANEL_COLUMNS = 4
PANEL_SIZE_INCHES = 3.2


def print_row(row: dict) -> None:
    """Print the metrics of one case as soon as it is ready."""
    print(f"m {row['speed_m']:.1f} z {row['speed_z']:.1f} | aspect {row['aspect_ratio']:.3f} r/m {row['face_ratio_r_over_m']:.3f} z/m {row['face_ratio_z_over_m']:.3f} "
          f"| Fe/Si m {row['iron_ratio_m']:.2e} r {row['iron_ratio_r']:.2e} z {row['iron_ratio_z']:.2e} (r/m {row['iron_contrast_r_over_m']:.2f}) "
          f"| sectors m {row['sector_share_m']:.2f} r {row['sector_share_r']:.2f} z {row['sector_share_z']:.2f} | {row['steps']} steps {row['wall_seconds']:.0f} s", flush=True)


def plot_curves(rows: list[dict]) -> None:
    """Save the aspect ratio, the r/m face ratio and the m-sector share against m/r (r = z) as one PNG."""
    swept = [row for row in rows if row["speed_z"] == 1.0]
    speeds = [row["speed_m"] for row in swept]
    figure, axes = plt.subplots(1, 3, figsize=(12, 3.6))
    for axis, key, label in zip(axes, ("aspect_ratio", "face_ratio_r_over_m", "sector_share_m"), ("aspect ratio (length / width)", "r / m face distance", "share of crystal grown by m faces")):
        axis.plot(speeds, [row[key] for row in swept], marker="o")
        axis.set_xlabel("m / r speed (r = z = 1)")
        axis.set_ylabel(label)
        axis.grid(alpha=0.3)
    figure.suptitle("Face-speed study, research resolution 800 x 400 (ASSUMED speeds swept)")
    figure.tight_layout()
    figure.savefig(OUTPUT_FOLDER / "shape_vs_speed_ratio.png", dpi=120)
    plt.close(figure)


def plot_crystals(cases: list[dict], color_scale: float) -> None:
    """Save the final crystals of every case side by side, coloured by their iron."""
    rows_of_panels = (len(cases) + PANEL_COLUMNS - 1) // PANEL_COLUMNS
    figure, axes = plt.subplots(rows_of_panels, PANEL_COLUMNS, figsize=(PANEL_SIZE_INCHES * PANEL_COLUMNS, PANEL_SIZE_INCHES * rows_of_panels * 0.6))
    for axis in axes.flat:
        axis.axis("off")
    for axis, case in zip(axes.flat, cases):
        state, row = case["state"], case["row"]
        axis.imshow(render_crystal_rgb(state.phase_field, state.crystal_iron, case["solid_capacity"], color_scale), origin="lower")
        axis.set_title(f"m {row['speed_m']:.1f} : r 1 : z {row['speed_z']:.1f}", fontsize=9)
    figure.tight_layout()
    figure.savefig(OUTPUT_FOLDER / "crystals.png", dpi=110)
    plt.close(figure)


def main() -> None:
    """Run every case, print, save the table (JSON) and the two figures."""
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    material = load_material()
    cases = []
    for speed_m, speed_z in list_cases():
        case = run_case(material, speed_m, speed_z)
        case["solid_capacity"] = material.solid_capacity_model
        print_row(case["row"])
        cases.append(case)
    rows = [case["row"] for case in cases]
    (OUTPUT_FOLDER / "face_speed_study.json").write_text(json.dumps(rows, indent=2, default=float))
    plot_curves(rows)
    plot_crystals(cases, material.color_iron_scale)
    print(f"Saved in {OUTPUT_FOLDER} ({len(M_SPEEDS)} m values and the r != z cases).")


if __name__ == "__main__":
    main()
