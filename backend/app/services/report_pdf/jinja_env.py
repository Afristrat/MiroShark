"""
jinja_env.py — Environnement Jinja2 pour les templates PDF Bassira.

Fournit ``get_jinja_env()`` qui retourne un environnement Jinja2 configuré
pour lire les templates depuis ``backend/app/templates/pdf_report/``.

Filtres Jinja2 inclus :
    normalize    — applique TextNormalizer(lang) sur le texte (utilisé dans les templates)
    md_to_html   — convertit du Markdown en HTML via markdown-it-py (usage interne)

L'environnement est mis en cache par processus via un singleton module-level.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape


# Chemin vers le dossier templates/pdf_report/ relatif à ce fichier
_TEMPLATES_DIR: Path = (
    Path(__file__).resolve().parent.parent.parent  # → backend/app/
    / "templates"
    / "pdf_report"
)


@lru_cache(maxsize=1)
def get_jinja_env() -> Environment:
    """Retourne l'environnement Jinja2 pour les templates PDF Bassira.

    - FileSystemLoader pointant sur ``backend/app/templates/pdf_report/``
    - StrictUndefined : toute variable non définie lève une exception
    - Autoescape désactivé (les templates .md.j2 sont du Markdown, pas du HTML)
    - Filtre ``normalize`` : normalise un texte via TextNormalizer(lang)

    Returns:
        Environment Jinja2 configuré.
    """
    if not _TEMPLATES_DIR.exists():
        raise RuntimeError(
            f"Dossier templates PDF manquant : {_TEMPLATES_DIR}. "
            "Assurez-vous que les templates US-123 sont bien présents."
        )

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=StrictUndefined,
        autoescape=False,  # Markdown, pas HTML
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )

    # ── Filtre normalize ───────────────────────────────────────────────────────
    def _normalize_filter(text: str, lang: str = "fr") -> str:
        """Filtre Jinja2 : normalise typographiquement un texte selon la langue."""
        if not text:
            return text
        try:
            from app.services.text_normalizer import TextNormalizer

            result = TextNormalizer(lang=lang).normalize(text)  # type: ignore[arg-type]
            return result.normalized
        except Exception:
            # Si TextNormalizer n'est pas disponible, retourner le texte brut.
            return text

    env.filters["normalize"] = _normalize_filter

    # ── Filtre md_to_html ──────────────────────────────────────────────────────
    def _md_to_html_filter(text: str) -> str:
        """Filtre Jinja2 : convertit du Markdown en HTML via markdown-it-py."""
        if not text:
            return text
        try:
            from markdown_it import MarkdownIt

            md = MarkdownIt("commonmark").enable(["table", "strikethrough"])
            return md.render(text)
        except Exception:
            return text

    env.filters["md_to_html"] = _md_to_html_filter

    return env
