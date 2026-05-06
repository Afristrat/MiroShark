#!/usr/bin/env python3
"""
lint_palette_contrast.py — Linter WCAG AA de la palette Causse Warm Intelligence.

Usage :
    python scripts/lint_palette_contrast.py [--verbose]

Vérifie que les couleurs de la palette Bassira respectent les ratios de contraste
WCAG AA :
    - Texte normal  : ratio ≥ 4.5:1
    - Texte large   : ratio ≥ 3.0:1  (≥ 18pt ou 14pt bold)

Paires testées :
    - WI_CHARCOAL sur WI_CREAM  (texte principal sur fond)
    - WI_INK sur WI_CREAM       (texte très sombre sur fond)
    - WI_ORANGE sur WI_CREAM    (couleur primaire sur fond) — texte large seulement
    - WI_MINT sur WI_CREAM      (couleur secondaire sur fond) — texte normal

Exit codes :
    0 — Toutes les paires respectent WCAG AA
    1 — Au moins une paire échoue + rapport détaillé en sortie

Source :
    - Constantes WI_* depuis app/services/report_pdf/_style.py
    - Algorithme WCAG 2.1 Section 1.4.3 (relative luminance)

Référence WCAG :
    https://www.w3.org/TR/WCAG21/#contrast-minimum
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ── Ajout du backend/ au sys.path pour import app ────────────────────────────
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ═══════════════════════════════════════════════════════════════════════════════
# Algorithme WCAG 2.1 — Luminance relative et ratio de contraste
# ═══════════════════════════════════════════════════════════════════════════════


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convertit une couleur hex (#RRGGBB) en triplet RGB [0, 255]."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(f"Format hex invalide : #{hex_color} (attendu #RRGGBB)")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return float(r), float(g), float(b)


def _linearize(channel: float) -> float:
    """Linéarisation d'un canal RGB (sRGB → linéaire) selon WCAG 2.1."""
    c = channel / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    """Calcule la luminance relative WCAG 2.1 d'une couleur hex.

    Formule :
        L = 0.2126 × R_lin + 0.7152 × G_lin + 0.0722 × B_lin

    Returns:
        Flottant dans [0, 1]. 0 = noir absolu, 1 = blanc absolu.
    """
    r, g, b = _hex_to_rgb(hex_color)
    r_lin = _linearize(r)
    g_lin = _linearize(g)
    b_lin = _linearize(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(color_fg: str, color_bg: str) -> float:
    """Calcule le ratio de contraste WCAG 2.1 entre deux couleurs.

    Formule :
        ratio = (L1 + 0.05) / (L2 + 0.05)
        où L1 = luminance la plus élevée, L2 = luminance la plus basse.

    Returns:
        Ratio dans [1, 21]. 1 = aucun contraste, 21 = contraste maximal.
    """
    l_fg = relative_luminance(color_fg)
    l_bg = relative_luminance(color_bg)
    l_light = max(l_fg, l_bg)
    l_dark = min(l_fg, l_bg)
    return (l_light + 0.05) / (l_dark + 0.05)


# ═══════════════════════════════════════════════════════════════════════════════
# Chargement des constantes de palette
# ═══════════════════════════════════════════════════════════════════════════════


def _load_palette() -> dict[str, str]:
    """Charge les constantes WI_* depuis _style.py.

    Retourne un dict {nom_constante: hex_color}.
    Fallback sur les valeurs hardcodées si l'import échoue.
    """
    try:
        from app.services.report_pdf._style import (
            WI_ORANGE,
            WI_MINT,
            WI_CREAM,
            WI_CHARCOAL,
            WI_TERRA,
            WI_SAND,
            WI_INK,
        )
        return {
            "WI_ORANGE": WI_ORANGE,
            "WI_MINT": WI_MINT,
            "WI_CREAM": WI_CREAM,
            "WI_CHARCOAL": WI_CHARCOAL,
            "WI_TERRA": WI_TERRA,
            "WI_SAND": WI_SAND,
            "WI_INK": WI_INK,
        }
    except ImportError as exc:
        print(f"[WARN] Import _style.py échoué : {exc} — utilisation des fallbacks hardcodés.", file=sys.stderr)
        return {
            "WI_ORANGE": "#FF8551",
            "WI_MINT": "#006D44",
            "WI_CREAM": "#FAF7F2",
            "WI_CHARCOAL": "#241915",
            "WI_TERRA": "#A13F0F",
            "WI_SAND": "#E8DDC9",
            "WI_INK": "#1A0F0A",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Définition des paires à tester
# ═══════════════════════════════════════════════════════════════════════════════

# Format : (nom_fg, nom_bg, type_texte, ratio_minimum)
# type_texte : "normal" (≥ 4.5) ou "large" (≥ 3.0)
_PAIRS_TO_CHECK: list[tuple[str, str, str, float]] = [
    # Texte principal charcoal sur fond crème — texte normal
    ("WI_CHARCOAL", "WI_CREAM", "normal", 4.5),
    # Texte très sombre ink sur fond crème — texte normal
    ("WI_INK", "WI_CREAM", "normal", 4.5),
    # Orange primaire sur fond crème — seulement pour texte large (titres, CTA)
    ("WI_ORANGE", "WI_CREAM", "large", 3.0),
    # Vert secondaire sur fond crème — texte normal (badges, indicateurs)
    ("WI_MINT", "WI_CREAM", "normal", 4.5),
    # Terra sur fond crème — texte large (couleur d'accentuation)
    ("WI_TERRA", "WI_CREAM", "large", 3.0),
]


# ═══════════════════════════════════════════════════════════════════════════════
# Fonction principale
# ═══════════════════════════════════════════════════════════════════════════════


def run_checks(palette: dict[str, str], verbose: bool = False) -> list[dict]:
    """Effectue tous les checks de contraste WCAG AA.

    Returns:
        Liste de résultats par paire :
            {fg, bg, type, ratio, threshold, passes, ratio_str}
    """
    results = []
    for fg_name, bg_name, text_type, threshold in _PAIRS_TO_CHECK:
        fg_hex = palette.get(fg_name, "#000000")
        bg_hex = palette.get(bg_name, "#FFFFFF")
        ratio = contrast_ratio(fg_hex, bg_hex)
        passes = ratio >= threshold

        results.append({
            "fg": fg_name,
            "bg": bg_name,
            "fg_hex": fg_hex,
            "bg_hex": bg_hex,
            "type": text_type,
            "ratio": ratio,
            "threshold": threshold,
            "passes": passes,
            "ratio_str": f"{ratio:.2f}:1",
        })

        if verbose:
            status = "✓ OK " if passes else "✗ FAIL"
            print(
                f"  {status}  {fg_name} ({fg_hex}) / {bg_name} ({bg_hex}) "
                f"[{text_type}] → {ratio:.2f}:1 (seuil ≥ {threshold}:1)"
            )

    return results


def main() -> int:
    """Point d'entrée principal. Retourne 0 si OK, 1 si échec."""
    parser = argparse.ArgumentParser(
        description="Linter WCAG AA — palette Causse Warm Intelligence Bassira",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Affiche le détail de chaque paire testée.",
    )
    args = parser.parse_args()

    palette = _load_palette()

    print("=" * 60)
    print("lint_palette_contrast — WCAG AA Contrast Check")
    print(f"Palette source : app/services/report_pdf/_style.py")
    print("=" * 60)

    if args.verbose:
        print("\nPalette chargée :")
        for name, hex_val in palette.items():
            lum = relative_luminance(hex_val)
            print(f"  {name:15s} {hex_val}  (luminance: {lum:.4f})")
        print()
        print("Résultats par paire :")

    results = run_checks(palette, verbose=args.verbose)

    failures = [r for r in results if not r["passes"]]

    print()
    if failures:
        print(f"✗ ÉCHEC — {len(failures)} paire(s) ne respectent pas WCAG AA :")
        for r in failures:
            print(
                f"  - {r['fg']} ({r['fg_hex']}) / {r['bg']} ({r['bg_hex']}) "
                f"[{r['type']}] : {r['ratio_str']} < {r['threshold']}:1"
            )
        print()
        print("Correction requise : ajuster les couleurs dans _style.py et pdf_brand.css.j2")
        print("Référence WCAG AA : https://www.w3.org/TR/WCAG21/#contrast-minimum")
        return 1
    else:
        print(f"✓ OK — Toutes les {len(results)} paires respectent WCAG AA")
        for r in results:
            print(
                f"  {r['fg']:15s} / {r['bg']:15s} [{r['type']:6s}] → {r['ratio_str']}"
            )
        return 0


if __name__ == "__main__":
    sys.exit(main())
