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
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

from app.services.text_normalizer import TextNormalizer

# ── Babel (optionnel — fallback intégré si absent) ────────────────────────────
try:
    from babel.dates import format_datetime as _babel_format_datetime

    _HAS_BABEL = True
except ImportError:  # pragma: no cover — babel présent en prod, absent en CI minimal
    _HAS_BABEL = False

# Chemin absolu vers les templates PDF
_TEMPLATES_DIR = pathlib.Path(__file__).parent.parent.parent / "templates" / "pdf_report"


def _format_date_filter(value: object, lang: str = "fr", format_style: str = "long") -> str:
    """Formate un horodatage ISO 8601 en date lisible selon la langue.

    Utilise Babel si disponible (fr_FR, en_US, ar_MA) ; sinon fallback
    manuel sans dépendance externe.

    Parameters
    ----------
    value :
        Chaîne ISO 8601 (ex. ``'2026-05-06T15:07:07+00:00'``) ou objet datetime.
    lang :
        Langue cible : ``'fr'``, ``'en'`` ou ``'ar'``. Défaut : ``'fr'``.
    format_style :
        Style Babel (``'long'``, ``'medium'``, ``'short'``). Défaut : ``'long'``.

    Returns
    -------
    str
        Date formatée, ou chaîne vide si value est None/vide.
    """
    if not value:
        return ""

    # Normalisation de la valeur en datetime
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return str(value)
    elif isinstance(value, datetime):
        dt = value
    else:
        return str(value)

    # Validation de la langue
    if lang not in {"fr", "en", "ar"}:
        lang = "fr"

    if _HAS_BABEL:
        locale_map = {"fr": "fr_FR", "en": "en_US", "ar": "ar_MA"}
        locale = locale_map.get(lang, "fr_FR")
        try:
            return _babel_format_datetime(dt, format=format_style, locale=locale)
        except Exception:
            pass  # Fallback ci-dessous

    # Fallback sans Babel
    _FR_MONTHS = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ]
    _EN_MONTHS = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    if lang == "fr":
        return (
            f"{dt.day} {_FR_MONTHS[dt.month - 1]} {dt.year}"
            f" à {dt.hour:02d}h{dt.minute:02d} UTC"
        )
    if lang == "ar":
        return (
            f"{dt.day} {_EN_MONTHS[dt.month - 1]} {dt.year}"
            f" — {dt.hour:02d}:{dt.minute:02d} UTC"
        )
    # Anglais par défaut
    return f"{_EN_MONTHS[dt.month - 1]} {dt.day}, {dt.year} at {dt.hour:02d}:{dt.minute:02d} UTC"


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

    # ── Filter |humanize_agent ─────────────────────────────────────────────────
    # Transforme un identifiant snake_case_NNN en libellé lisible :
    #   "whisperx_largev3_841"      → "WhisperX large-v3 (#841)"
    #   "amine_mansouri_idrissi_441" → "Amine Mansouri Idrissi (#441)"
    #   "Restic_289"                 → "Restic (#289)"
    # Si l'input est déjà un nom propre (espaces, capitales), retourne tel quel.
    import re as _re

    _SUFFIX_NUM_RE = _re.compile(r"_(\d{2,5})$")
    _LARGE_V_RE = _re.compile(r"\blargev(\d+)\b", _re.IGNORECASE)

    def _humanize_agent_filter(value: object) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        # Si déjà un nom propre (espaces ou majuscules + min mélangées sans _)
        if " " in text and "_" not in text:
            return text
        # Suffixe numérique → on l'extrait pour l'afficher en ID
        m = _SUFFIX_NUM_RE.search(text)
        suffix = ""
        if m:
            suffix = f" (#{m.group(1)})"
            text = text[: m.start()]
        # _ → espaces
        text = text.replace("_", " ").strip()
        # largev3 → large-v3
        text = _LARGE_V_RE.sub(lambda mm: f"large-v{mm.group(1)}", text)
        # capitalize premier mot, garde les acronymes (mots > 2 chars en lowercase
        # avec mix de chiffres seulement)
        parts = text.split(" ")
        capitalized = []
        for p in parts:
            if not p:
                continue
            if any(c.isdigit() for c in p) or p.isupper():
                capitalized.append(p)
            else:
                capitalized.append(p[0].upper() + p[1:])
        return " ".join(capitalized) + suffix

    env.filters["humanize_agent"] = _humanize_agent_filter

    # ── Filter |position_label ─────────────────────────────────────────────────
    # Mappe les stances internes (bullish/bearish/neutral, héritées du framework
    # Cerberus inspiré des marchés prédictifs) vers un vocabulaire lisible par
    # un C-level TPE/PME/GE Maroc-Afrique :
    #   bullish  → "Adhésion"
    #   bearish  → "Résistance"
    #   neutral  → "En observation"
    # Pour un dirigeant qui pilote un déploiement, "Bullish 95 %" n'a pas de
    # sens — "Adhésion 95 %" est immédiatement actionnable.
    _POSITION_LABEL_FR = {
        "bullish":  "Adhésion",
        "bearish":  "Résistance",
        "neutral":  "En observation",
        "neutre":   "En observation",
        "adoption": "Adhésion",
        "support":  "Adhésion",
        "oppose":   "Résistance",
        "opposed":  "Résistance",
        "watch":    "En observation",
    }

    def _position_label_filter(value: object) -> str:
        if value is None:
            return ""
        key = str(value).strip().lower()
        return _POSITION_LABEL_FR.get(key, key.capitalize() if key else "")

    env.filters["position_label"] = _position_label_filter

    # ── Filter |reliability_pct ────────────────────────────────────────────────
    # Convertit un Brier score [0, 1] en "Indice de fiabilité" % lisible.
    # Brier 0 = parfait → 100 %. Brier 1 = totalement faux → 0 %.
    def _reliability_pct_filter(brier: object) -> float:
        try:
            b = float(brier)
        except (TypeError, ValueError):
            return 0.0
        return round(max(0.0, min(1.0, 1.0 - b)) * 100.0, 1)

    env.filters["reliability_pct"] = _reliability_pct_filter

    # ── Filter |format_date ────────────────────────────────────────────────────
    # Appelé depuis les templates via {{ generated_at | format_date(lang=context.lang) }}
    env.filters["format_date"] = _format_date_filter

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
