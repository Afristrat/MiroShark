"""
_style.py — Palette Causse Warm Intelligence pour matplotlib.

Expose ``apply_causse_style()`` qui configure les rcParams matplotlib de
sorte que tous les charts produits par ChartFactory respectent la charte
graphique Bassira / Causse Warm Intelligence.

Palette de référence (design-tokens.css, namespace --wi-*) :
    WI_ORANGE   = '#FF8551'   (--wi-primary-container)
    WI_MINT     = '#006D44'   (--wi-secondary)
    WI_CREAM    = '#FAF7F2'   (fond de page rapport)
    WI_CHARCOAL = '#241915'   (--wi-on-bg / texte principal)
    WI_TERRA    = '#A13F0F'   (--wi-primary)
    WI_SAND     = '#E8DDC9'   (fond léger, grid)
    WI_INK      = '#1A0F0A'   (variante très sombre du charcoal)

Polices :
    - Titres  : Outfit  (fallback DejaVu Sans si non installée)
    - Axes    : Manrope (fallback DejaVu Sans si non installée)

DPI : 300
"""

from __future__ import annotations

import matplotlib

# Backend non-interactif DOIT être sélectionné avant tout import pyplot.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

# ─── Palette Causse Warm Intelligence ─────────────────────────────────────────
WI_ORANGE: str = "#FF8551"
WI_MINT: str = "#006D44"
WI_CREAM: str = "#FAF7F2"
WI_CHARCOAL: str = "#241915"
WI_TERRA: str = "#A13F0F"
WI_SAND: str = "#E8DDC9"
WI_INK: str = "#1A0F0A"

# Palette séquentielle pour les multi-séries (stances / groupes d'agents)
CAUSSE_PALETTE: list[str] = [
    WI_ORANGE,
    WI_MINT,
    WI_TERRA,
    "#57423A",  # on-surface-variant
    "#006971",  # tertiary
    "#98F2BE",  # secondary-container
    "#FFCDB2",  # accent clair
    "#8A7269",  # outline
]


def _font_family(preferred: str, fallback: str = "DejaVu Sans") -> str:
    """Retourne *preferred* si la police est disponible, sinon *fallback*."""
    from matplotlib import font_manager

    available = {f.name for f in font_manager.fontManager.ttflist}
    return preferred if preferred in available else fallback


def apply_causse_style() -> None:
    """
    Configure matplotlib rcParams avec la palette Causse Warm Intelligence.

    Appeler cette fonction UNE FOIS avant toute création de figure.
    Elle est idempotente (réentrant sans effet de bord).
    """
    font_title = _font_family("Outfit")
    font_axes = _font_family("Manrope")

    plt.rcParams.update(
        {
            # ── Résolution ──────────────────────────────────────────────────
            "figure.dpi": 300,
            "savefig.dpi": 300,
            # ── Fond & couleurs de figure ────────────────────────────────────
            "figure.facecolor": WI_CREAM,
            "axes.facecolor": WI_CREAM,
            "savefig.facecolor": WI_CREAM,
            # ── Palette de couleurs par défaut ───────────────────────────────
            "axes.prop_cycle": plt.cycler(color=CAUSSE_PALETTE),
            # ── Texte & polices ──────────────────────────────────────────────
            "font.family": "sans-serif",
            "font.sans-serif": [font_axes, "DejaVu Sans"],
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "figure.titlesize": 13,
            "axes.titleweight": "bold",
            # ── Couleurs du texte ────────────────────────────────────────────
            "text.color": WI_CHARCOAL,
            "axes.labelcolor": WI_CHARCOAL,
            "xtick.color": WI_CHARCOAL,
            "ytick.color": WI_CHARCOAL,
            "axes.titlecolor": WI_INK,
            # ── Spines ──────────────────────────────────────────────────────
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": WI_SAND,
            # ── Grille ──────────────────────────────────────────────────────
            "axes.grid": True,
            "grid.color": WI_SAND,
            "grid.alpha": 0.4,
            "grid.linewidth": 0.6,
            "axes.axisbelow": True,
            # ── Lignes & markers ────────────────────────────────────────────
            "lines.linewidth": 2.0,
            "lines.markersize": 5,
            # ── Légende ─────────────────────────────────────────────────────
            "legend.fontsize": 7,
            "legend.framealpha": 0.85,
            "legend.facecolor": WI_CREAM,
            "legend.edgecolor": WI_SAND,
            # ── Tight layout ────────────────────────────────────────────────
            "figure.autolayout": False,
        }
    )

    # Polices titre (figure.titlefontproperties n'est pas un rcParam standard ;
    # on passe la police titre via axes.title.fontfamily quand possible)
    try:
        plt.rcParams["axes.titlefamily"] = font_title
    except KeyError:
        # rcParam non reconnu sur certaines versions anciennes, ignoré.
        pass
