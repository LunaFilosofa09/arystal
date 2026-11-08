"""Estilo de figuras a juego con la plantilla (Palatino, sobrio, vectorial).
Uso: import figstyle; figstyle.apply(); ... ; fig.savefig('fig.pdf')"""
import matplotlib as mpl

def apply():
    mpl.rcParams.update({
        "font.family": "serif",
        "font.serif": ["TeX Gyre Pagella", "Palatino", "DejaVu Serif"],
        "mathtext.fontset": "custom",
        "mathtext.rm": "TeX Gyre Pagella",
        "mathtext.it": "TeX Gyre Pagella:italic",
        "font.size": 9, "axes.labelsize": 9, "legend.fontsize": 8,
        "xtick.labelsize": 8, "ytick.labelsize": 8,
        "axes.linewidth": 0.6, "lines.linewidth": 1.2,
        "xtick.direction": "in", "ytick.direction": "in",
        "xtick.top": True, "ytick.right": True,
        "axes.spines.top": True, "axes.spines.right": True,
        "legend.frameon": False,
        "axes.prop_cycle": mpl.cycler(color=["#000000", "#6b6b6b", "#3b5b8c"],
                                      linestyle=["-", "--", ":"]),
        "figure.figsize": (3.4, 2.4), "savefig.bbox": "tight",
        "pdf.fonttype": 42,
    })
