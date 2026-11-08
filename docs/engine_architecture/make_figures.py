"""Figures for engine_architecture.tex. Data copied from docs/regime_study.md (sections 1 and 3)."""
import matplotlib.pyplot as plt
import figstyle
from matplotlib import font_manager
for _f in ("fonts/texgyrepagella-regular.otf", "fonts/texgyrepagella-italic.otf"):
    font_manager.fontManager.addfont(_f)

figstyle.apply()

# Regime map (docs/regime_study.md, section 1)
damkohler = [61, 6.1, 0.61, 0.061, 0.0061, 0.00061, 0.000061]
aspect = [0.517, 0.593, 0.804, 0.826, 0.826, 0.826, 0.826]
uniformity = [0.098, 0.189, 0.654, 0.952, 0.995, 1.000, 1.000]
fig, ax = plt.subplots(figsize=(3.4, 2.4))
ax.semilogx(damkohler, aspect, marker="o", ms=3, label="aspect ratio")
ax.semilogx(damkohler, uniformity, marker="s", ms=3, label=r"$S_\mathrm{surface}/S_\mathrm{bulk}$")
ax.axvline(0.06, color="0.6", lw=0.6)
ax.text(0.045, 0.35, "plateau onset", rotation=90, fontsize=7, color="0.35", ha="right")
ax.set_xlabel("model Damköhler number Da")
ax.set_ylabel("value at equal crystal size")
ax.set_ylim(0, 1.08)
ax.legend(loc="lower left")
fig.savefig("fig_regime.pdf")

# Resolution convergence (docs/regime_study.md, section 3)
cells = [100, 200, 400, 800, 1600]
aspect_res = [0.750, 0.826, 0.886, 0.930, 0.950]
ratio_rm = [1.227, 1.358, 1.405, 1.425, 1.431]
fig, ax = plt.subplots(figsize=(3.4, 2.4))
ax.semilogx(cells, [a / aspect_res[-1] for a in aspect_res], marker="o", ms=3, label="aspect ratio")
ax.semilogx(cells, [r / ratio_rm[-1] for r in ratio_rm], marker="s", ms=3, label=r"$r/m$ face ratio")
for x, name in [(200, "explore"), (800, "research")]:
    ax.axvline(x, color="0.6", lw=0.6)
    ax.text(x * 1.07, 0.775, name, rotation=90, fontsize=7, color="0.35")
ax.set_xticks(cells, [str(c) for c in cells])
ax.minorticks_off()
ax.set_xlabel("cells across the container")
ax.set_ylabel("value / value at 1600 cells")
ax.set_ylim(0.76, 1.02)
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2)
fig.savefig("fig_convergence.pdf")
