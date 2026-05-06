"""
jinja_env.py — Environnement Jinja2 configuré pour les templates PDF Bassira.

Fournit :
    get_jinja_env()  → Environment Jinja2 avec :
        - FileSystemLoader sur backend/app/templates/pdf_report/
        - autoescape=False (markdown brut)
        - trim_blocks=True / lstrip_blocks=True
        - filter |normalize → TextNormalizer(lang).normalize(text).normalized

Usage ::

    from app.services.report_pdf.jinja_env import get_jinja_env

    env = get_jinja_env()
    template = env.get_template('_full.md.j2')
    rendered = template.render(
        context=pdf_context,
        generated_at='2026-05-05T12:00:00Z',
        branding_version='default',
    )
"""

from __future__ import annotations

import pathlib

from jinja2 import Environment, FileSystemLoader

from app.services.text_normalizer import TextNormalizer

# Chemin absolu vers les templates PDF
_TEMPLATES_DIR = pathlib.Path(__file__).parent.parent.parent / "templates" / "pdf_report"


def get_jinja_env() -> Environment:
    """
    Construit et retourne l'Environment Jinja2 configuré pour les templates PDF Bassira.

    Caractéristiques :
    - FileSystemLoader sur ``backend/app/templates/pdf_report/``
    - ``autoescape=False`` : les templates génèrent du Markdown brut (pas du HTML).
    - ``trim_blocks=True`` : supprime la newline après un bloc de tag ``{% %}``.
    - ``lstrip_blocks=True`` : supprime les espaces en début de ligne avant un bloc.
    - Filter ``|normalize`` : normalise typographiquement un texte via TextNormalizer.

    Returns
    -------
    Environment
        Instance Jinja2 prête à charger les templates ``*.md.j2``.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=False,  # Markdown brut — pas d'échappement HTML
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # ── Filter |normalize ──────────────────────────────────────────────────────
    # Appelé depuis les templates via {{ text | normalize(lang) }} ou
    # {{ text | normalize }} (lang='fr' par défaut).
    # Le lang est passé explicitement dans les templates via context.lang.
    def _normalize_filter(value: object, lang: str = "fr") -> str:
        """Normalise typographiquement *value* selon la langue *lang*.

        Gestion défensive :
        - Si *value* est None → retourne ''.
        - Si *lang* n'est pas dans {'fr', 'en', 'ar'} → fallback sur 'fr'.
        - En cas d'erreur inattendue → retourne str(value) sans planter le rendu.
        """
        if value is None:
            return ""
        text = str(value)
        if not text:
            return ""
        # Validation défensive de la langue
        if lang not in {"fr", "en", "ar"}:
            lang = "fr"
        try:
            return TextNormalizer(lang).normalize(text).normalized
        except Exception:
            # Ne jamais crasher le rendu de template pour une normalisation
            return text

    env.filters["normalize"] = _normalize_filter

    return env


def render_section(section_name: str, context: object, **extra_vars: object) -> str:
    """
    Raccourci pour rendre un template de section individuel.

    Parameters
    ----------
    section_name :
        Nom du fichier template (ex. ``'00_cover.md.j2'``).
    context :
        Instance ``PDFReportContext`` à exposer dans le template.
    **extra_vars :
        Variables supplémentaires passées au template (ex. ``generated_at``).

    Returns
    -------
    str
        Contenu Markdown rendu.
    """
    env = get_jinja_env()
    template = env.get_template(section_name)
    return template.render(context=context, **extra_vars)


def render_full_report(context: object, generated_at: str, branding_version: str = "default") -> str:
    """
    Rend le rapport complet via ``_full.md.j2``.

    Parameters
    ----------
    context :
        Instance ``PDFReportContext``.
    generated_at :
        Horodatage ISO 8601 de génération (ex. ``'2026-05-05T12:00:00Z'``).
    branding_version :
        Version du branding à inscrire dans le front-matter YAML.

    Returns
    -------
    str
        Markdown complet du rapport avec front-matter YAML.
    """
    env = get_jinja_env()
    template = env.get_template("_full.md.j2")
    return template.render(
        context=context,
        generated_at=generated_at,
        branding_version=branding_version,
    )
