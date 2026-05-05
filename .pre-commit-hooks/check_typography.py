#!/usr/bin/env python3
"""Hook pre-commit — vérification typographique des templates Jinja2 (*.md.j2).

Scanne tous les fichiers ``*.md.j2`` dans ``backend/app/templates/``
et échoue (exit 1) si des erreurs typographiques françaises sont détectées.

Règles vérifiées :
- Mots entièrement en majuscules sans accent (ex: ETAT → doit être ÉTAT)
- Ponctuation directe sans espace insécable (ex: `text:` sans NNBSP avant `:`)

Usage manuel ::

    python .pre-commit-hooks/check_typography.py
    python .pre-commit-hooks/check_typography.py --path backend/app/templates/

Exit codes :
    0 — aucun problème détecté
    1 — au moins un problème détecté (détails sur stderr)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, NamedTuple

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

NNBSP = " "  # espace insécable fine

# Mots entièrement en majuscules qui DOIVENT avoir un accent
# (sous-ensemble représentatif du dictionnaire fr.py)
_ACCENT_REQUIRED: dict[str, str] = {
    "ETAT": "ÉTAT",
    "ETATS": "ÉTATS",
    "ECOLE": "ÉCOLE",
    "ECOLES": "ÉCOLES",
    "ETRE": "ÊTRE",
    "EVENEMENT": "ÉVÉNEMENT",
    "EVENEMENTS": "ÉVÉNEMENTS",
    "REUSSITE": "RÉUSSITE",
    "PROBLEME": "PROBLÈME",
    "PROBLEMES": "PROBLÈMES",
    "STRATEGIE": "STRATÉGIE",
    "STRATEGIES": "STRATÉGIES",
    "REALITE": "RÉALITÉ",
    "OPERATIONNEL": "OPÉRATIONNEL",
    "OPERATIONNELS": "OPÉRATIONNELS",
    "EVALUATION": "ÉVALUATION",
    "EVALUATIONS": "ÉVALUATIONS",
    "DEVELOPPEMENT": "DÉVELOPPEMENT",
    "SYSTEME": "SYSTÈME",
    "SYSTEMES": "SYSTÈMES",
    "SANTE": "SANTÉ",
    "SECURITE": "SÉCURITÉ",
    "SOCIETE": "SOCIÉTÉ",
    "ECONOMIE": "ÉCONOMIE",
    "EDUCATION": "ÉDUCATION",
    "ENERGIE": "ÉNERGIE",
}

# Pattern mot entièrement en majuscules
_CAPS_RE = re.compile(r'\b([A-Z]{3,})\b')

# Pattern : ponctuation `; : ! ?` précédée d'un caractère non-espace-insécable
# (l'espace normale ou aucune espace = erreur)
_PUNCT_NO_NNBSP_RE = re.compile(r'(?<!' + NNBSP + r')([;:!?])')


# ---------------------------------------------------------------------------
# Structures
# ---------------------------------------------------------------------------

class TypoError(NamedTuple):
    file: Path
    line: int
    col: int
    message: str
    suggestion: str


# ---------------------------------------------------------------------------
# Logique de détection
# ---------------------------------------------------------------------------

def _check_file(path: Path) -> List[TypoError]:
    errors: List[TypoError] = []
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="latin-1")

    for lineno, line in enumerate(content.splitlines(), start=1):
        # 1. Mots en majuscules sans accent
        for m in _CAPS_RE.finditer(line):
            word = m.group(1)
            if word in _ACCENT_REQUIRED:
                errors.append(
                    TypoError(
                        file=path,
                        line=lineno,
                        col=m.start() + 1,
                        message=f"Mot sans accent obligatoire : '{word}'",
                        suggestion=f"Remplacer par '{_ACCENT_REQUIRED[word]}'",
                    )
                )

        # 2. Ponctuation directe sans espace insécable fine
        for m in _PUNCT_NO_NNBSP_RE.finditer(line):
            # Ignorer si c'est en début de ligne ou après une autre ponctuation
            col = m.start()
            if col == 0:
                continue
            preceding_char = line[col - 1]
            # Ignorer si déjà précédé d'une espace insécable fine
            if preceding_char == NNBSP:
                continue
            # Ignorer si c'est dans une URL (simpliste mais utile)
            if "://" in line[max(0, col - 10):col]:
                continue
            # Ignorer les séquences Jinja2 ({{ ... }})
            if "{{" in line[max(0, col - 20):col]:
                continue
            errors.append(
                TypoError(
                    file=path,
                    line=lineno,
                    col=col + 1,
                    message=f"Ponctuation '{m.group(1)}' sans espace insécable fine (U+202F) avant",
                    suggestion=f"Insérer \\u202f avant '{m.group(1)}'",
                )
            )

    return errors


def _find_templates(root: Path) -> List[Path]:
    return sorted(root.rglob("*.md.j2"))


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vérifie la typographie française dans les templates *.md.j2"
    )
    parser.add_argument(
        "--path",
        default="backend/app/templates",
        help="Répertoire racine à scanner (défaut : backend/app/templates)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Affiche les fichiers sans erreur également",
    )
    args = parser.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"[WARN] Répertoire '{root}' introuvable — hook ignoré.", file=sys.stderr)
        return 0

    templates = _find_templates(root)
    if not templates:
        print(f"[INFO] Aucun fichier *.md.j2 trouvé dans '{root}'.", file=sys.stderr)
        return 0

    all_errors: List[TypoError] = []
    for template in templates:
        file_errors = _check_file(template)
        all_errors.extend(file_errors)
        if args.verbose and not file_errors:
            print(f"  OK  {template}", file=sys.stderr)

    if not all_errors:
        print(
            f"[OK] {len(templates)} template(s) vérifié(s) — aucune erreur typographique.",
            file=sys.stderr,
        )
        return 0

    print(
        f"\n[ÉCHEC TYPOGRAPHIE] {len(all_errors)} erreur(s) dans {len(templates)} template(s)\n",
        file=sys.stderr,
    )
    for err in all_errors:
        print(
            f"  {err.file}:{err.line}:{err.col}  {err.message}",
            file=sys.stderr,
        )
        print(f"    → {err.suggestion}", file=sys.stderr)

    print(
        "\nCorrigez les erreurs ci-dessus avant de commiter.\n"
        "Référence : .pre-commit-hooks/check_typography.py",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
