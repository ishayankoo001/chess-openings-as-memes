"""
plot_theme.py — single styling source for every figure in this project.

Five professional themes, each a distinct design language. Switch with ONE line:
    DEFAULT_THEME = "editorial"          # edit this constant, OR
    plot_theme.use_theme("editorial")    # call at runtime

Every theme exposes the SAME role keys, so your plotting code never changes when
you swap themes — only the hexes behind the roles move:
    PALETTE['trap']     # the eye-catching emphasis colour (Stafford / viral)
    PALETTE['control']  # muted, recedes (Queen's Gambit / baseline)
    PALETTE['primary']  # neutral default series
    colors_for(k)       # k distinct categorical colours (k-means clusters)

USAGE in a plotting cell:
    import plot_theme
    from plot_theme import PALETTE, save_fig, annotate_point, colors_for
    fig, ax = plt.subplots()
    ax.plot(m, stafford, color=PALETTE['trap'],    label='Stafford (viral)')
    ax.plot(m, qg,       color=PALETTE['control'], label="Queen's Gambit (control)")
    save_fig('h1_stafford_vs_qg')

Keep the SAME opening the SAME colour across H1/H2/H4 — that visual through-line is
most of what makes the deck read as designed.
"""

from pathlib import Path
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from cycler import cycler

# ============================================================================
# THEMES — each defines identical role keys + a CATEGORICAL cycle.
# ============================================================================
THEMES = {

    # 1. STUDIO — warm, balanced flat-UI. Friendly-professional. (the original)
    "studio": {
        "ink": "#22223B", "primary": "#3D5A80", "trap": "#E76F51",
        "control": "#8D99AE", "accent": "#2A9D8F", "highlight": "#E9C46A",
        "muted": "#ADB5BD", "grid": "#E9ECEF", "bg": "#FFFFFF",
        "categorical": ["#3D5A80", "#E76F51", "#2A9D8F", "#E9C46A", "#6D597A", "#8D99AE"],
    },

    # 2. EDITORIAL — Economist / FT / FiveThirtyEight quantitative-journalism look.
    #    Vermilion emphasis + confident blue + cyan. Best fit for an academic stats talk.
    "editorial": {
        "ink": "#121317", "primary": "#1A6CA8", "trap": "#D6442B",
        "control": "#8A9BA8", "accent": "#2FA4C0", "highlight": "#E0A52E",
        "muted": "#A9B4BC", "grid": "#E4E9ED", "bg": "#FFFFFF",
        "categorical": ["#1A6CA8", "#D6442B", "#2FA4C0", "#E0A52E", "#5C6F7E", "#8A9BA8"],
    },

    # 3. MONO — Apple / Linear minimalism. Grayscale + ONE accent that carries all
    #    meaning. Stunning for line charts & scatter; weak for 3-way k-means (3 grays).
    "mono": {
        "ink": "#0F1115", "primary": "#6B7280", "trap": "#F43F5E",
        "control": "#C4CAD2", "accent": "#374151", "highlight": "#F43F5E",
        "muted": "#9AA1AB", "grid": "#EDEFF2", "bg": "#FFFFFF",
        "categorical": ["#F43F5E", "#374151", "#9AA1AB", "#C4CAD2", "#1F2937", "#6B7280"],
    },

    # 4. PULSE — Spotify-energy vibrant. Hot-pink emphasis, green, violet. High-impact,
    #    slightly playful; great if you present with confidence. Strong k-means colours.
    "pulse": {
        "ink": "#191414", "primary": "#1DB954", "trap": "#EC4899",
        "control": "#9AA0A6", "accent": "#7C3AED", "highlight": "#FACC15",
        "muted": "#B7BCC2", "grid": "#ECECEC", "bg": "#FFFFFF",
        "categorical": ["#1DB954", "#EC4899", "#7C3AED", "#FACC15", "#06B6D4", "#FB7185"],
    },

    # 5. SLATE — Stripe / fintech premium. Cool indigo-forward with one warm rose pop.
    #    Sophisticated, techy, "product-launch" polish.
    "slate": {
        "ink": "#1E1B2E", "primary": "#5B5BD6", "trap": "#FB7185",
        "control": "#94A3B8", "accent": "#06B6D4", "highlight": "#14B8A6",
        "muted": "#A8B2C0", "grid": "#ECEDF5", "bg": "#FFFFFF",
        "categorical": ["#5B5BD6", "#FB7185", "#06B6D4", "#14B8A6", "#8B5CF6", "#94A3B8"],
    },
}

# ---- pick your theme here (or call use_theme at runtime) -------------------
DEFAULT_THEME = "studio"

# Active palette — rebound by use_theme(). Always reference PALETTE[...] in code.
PALETTE = dict(THEMES[DEFAULT_THEME])
CATEGORICAL = list(THEMES[DEFAULT_THEME]["categorical"])

# Where figures are written (./figures relative to where you run).
FIG_DIR = Path("figures")


def _font_stack():
    """Prefer a modern sans if installed; always fall back to DejaVu Sans so no
    machine errors or spams findfont warnings."""
    installed = {f.name for f in font_manager.fontManager.ttflist}
    preferred = ["Inter", "SF Pro Display", "Helvetica Neue", "Helvetica",
                 "Arial", "Segoe UI", "Roboto", "Lato"]
    return [f for f in preferred if f in installed] + ["DejaVu Sans"]


def apply_theme():
    """Apply rcParams from the ACTIVE palette. Called by use_theme(); call again if
    a library clobbers rcParams mid-notebook."""
    p = PALETTE
    mpl.rcParams.update({
        "figure.figsize": (9, 5.5), "figure.dpi": 110,
        "figure.facecolor": p["bg"], "axes.facecolor": p["bg"],
        "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.3,
        "savefig.facecolor": p["bg"],

        "font.family": "sans-serif", "font.sans-serif": _font_stack(), "font.size": 12.5,

        "axes.titlesize": 16, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "axes.titlepad": 12, "axes.titlecolor": p["ink"],

        "axes.labelsize": 12.5, "axes.labelcolor": p["ink"], "axes.labelpad": 8,

        "axes.edgecolor": p["ink"], "axes.linewidth": 1.0,
        "axes.spines.top": False, "axes.spines.right": False,

        "axes.grid": True, "axes.grid.axis": "y",
        "grid.color": p["grid"], "grid.linewidth": 0.9, "axes.axisbelow": True,

        "xtick.color": p["ink"], "ytick.color": p["ink"],
        "xtick.labelsize": 11, "ytick.labelsize": 11,
        "xtick.major.size": 0, "ytick.major.size": 0,
        "xtick.minor.size": 0, "ytick.minor.size": 0,

        "lines.linewidth": 2.2, "lines.markersize": 6, "lines.solid_capstyle": "round",

        "legend.frameon": False, "legend.fontsize": 11,
        "legend.handlelength": 1.6, "legend.labelspacing": 0.4,

        "axes.prop_cycle": cycler(color=CATEGORICAL),

        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    })


def use_theme(name):
    """Switch the active theme by name and re-apply. Rebinds PALETTE/CATEGORICAL and
    the convenience constants so everything downstream stays correct."""
    if name not in THEMES:
        raise ValueError(f"unknown theme {name!r}; choose from {list(THEMES)}")
    global PALETTE, CATEGORICAL, INK, PRIMARY, TRAP, CONTROL, ACCENT
    PALETTE = dict(THEMES[name])
    CATEGORICAL = list(THEMES[name]["categorical"])
    INK, PRIMARY, TRAP = PALETTE["ink"], PALETTE["primary"], PALETTE["trap"]
    CONTROL, ACCENT = PALETTE["control"], PALETTE["accent"]
    apply_theme()
    return name


def colors_for(n):
    """Return n categorical colours (cycles if n > len(CATEGORICAL))."""
    return [CATEGORICAL[i % len(CATEGORICAL)] for i in range(n)]


def despine(ax=None):
    ax = ax or plt.gca()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return ax


def annotate_point(ax, x, y, text, dx=8, dy=8, color=None):
    """Label a single point (e.g. Stafford on the PCA scatter) with a clean offset
    annotation and a faint connector. Offsets in points."""
    ax.annotate(
        text, xy=(x, y), xytext=(dx, dy), textcoords="offset points",
        fontsize=10.5, color=color or PALETTE["ink"], fontweight="bold",
        ha="left", va="bottom",
        arrowprops=dict(arrowstyle="-", color=PALETTE["muted"], lw=0.8),
    )


def save_fig(name, fig=None, dpi=300, transparent=False, subdir=None):
    target = FIG_DIR / subdir if subdir else FIG_DIR
    target.mkdir(parents=True, exist_ok=True)
    path = target / (name if name.endswith(".png") else f"{name}.png")
    (fig or plt.gcf()).savefig(path, dpi=dpi, transparent=transparent)
    print(f"saved {path}")
    return path


def preview_all(filename="_theme_preview"):
    """Render all five themes side by side so you can choose. Each row: a trap-vs-
    control line pair (left) and the categorical bars (right)."""
    import numpy as np
    names = list(THEMES)
    fig, axes = plt.subplots(len(names), 2, figsize=(11, 2.3 * len(names)),
                             gridspec_kw={"width_ratios": [1.6, 1]})
    fig.patch.set_facecolor("#FFFFFF")
    x = np.arange(1, 13)
    ctrl = 0.041 + 0.0015 * np.sin(x / 2.2)
    trap = 0.0004 * np.where(x < 6, 1, 7) + 0.00005 * np.cos(x)
    for row, name in enumerate(names):
        t = THEMES[name]
        la, ra = axes[row][0], axes[row][1]
        for ax in (la, ra):
            ax.set_facecolor(t["bg"])
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
            for s in ("left", "bottom"):
                ax.spines[s].set_color(t["ink"])
            ax.tick_params(length=0, colors=t["ink"], labelsize=8)
        la.grid(axis="y", color=t["grid"], linewidth=0.9)
        la.set_axisbelow(True)
        la.plot(x, ctrl, color=t["control"], lw=2.4)
        la.plot(x, trap, color=t["trap"], lw=2.4)
        la.set_title(f"  {name}", loc="left", fontsize=13, fontweight="bold",
                     color=t["ink"], pad=8)
        la.set_yticks([])
        cats = t["categorical"]
        ra.bar(range(len(cats)), [1, 1.4, 0.8, 1.2, 0.95, 1.1][:len(cats)],
               color=cats, width=0.74)
        ra.set_yticks([]); ra.set_xticks([])
    fig.suptitle("Theme options — trap vs control (left), categorical set (right)",
                 x=0.06, ha="left", fontsize=15, fontweight="bold", color="#111")
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(FIG_DIR / f"{filename}.png", dpi=200, bbox_inches="tight",
                facecolor="#FFFFFF")
    print(f"saved {FIG_DIR / filename}.png")
    return fig


# convenience constants (kept correct across switches by use_theme)
INK, PRIMARY, TRAP = PALETTE["ink"], PALETTE["primary"], PALETTE["trap"]
CONTROL, ACCENT = PALETTE["control"], PALETTE["accent"]

# auto-apply DEFAULT_THEME on import
use_theme(DEFAULT_THEME)


if __name__ == "__main__":
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    preview_all()
