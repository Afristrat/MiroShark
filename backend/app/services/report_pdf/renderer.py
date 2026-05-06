"""
renderer.py — Renderer pipeline PDF Bassira (US-125).

Assemble les modules report_pdf en un pipeline complet :
    1. Enrichissement du contexte via Enricher
    2. Rendu Markdown GFM via templates Jinja2 (_full.md.j2)
    3. Conversion Markdown → HTML via markdown-it-py
    4. Injection CSS brandé (pdf_brand.css.j2)
    5. Embed des charts PNG en base64
    6. Rendu PDF final via WeasyPrint

API publique :
    ``Renderer(context, branding).render_md() -> str``
    ``Renderer(context, branding).render_pdf(charts_factory=None) -> bytes``

Multilang :
    - fr : police Outfit/Manrope, LTR
    - en : police Outfit/Manrope, LTR
    - ar : police Tajawal, RTL (dir="rtl")

PDF metadata :
    - title, author (Bassira), keywords, lang, creator
"""

from __future__ import annotations

import base64
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from .schema import PDFReportContext


logger = logging.getLogger("miroshark.renderer")

# Version du template (incrémenter lors de changements majeurs)
_TEMPLATE_VERSION = "1.0.0"

# Regex pour extraire le front-matter YAML délimité par ---
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Noms des charts disponibles (ordre cohérent avec ChartFactory)
_CHART_METHODS = [
    "belief_drift",
    "polymarket_curves",
    "demographic_pyramid",
    "influence_leaderboard",
    "interaction_network",
]


class Renderer:
    """Pipeline de génération de rapports PDF Bassira.

    Args:
        context:       Contexte complet du rapport (PDFReportContext).
        branding:      Row de branding PDF actif (dict depuis pdf_branding).
                       Si None, les defaults Bassira sont utilisés dans le CSS.
        charts_factory: Instance de ChartFactory optionnelle. Si fournie,
                       les charts sont embarqués en data URI dans le Markdown
                       rendu par ``render_md()`` ET dans le HTML de ``render_pdf()``.
    """

    def __init__(
        self,
        context: PDFReportContext,
        branding: Optional[Any] = None,
        charts_factory: Optional[Any] = None,
    ) -> None:
        self.context = context
        self.branding = branding  # Dict ou None
        self.charts_factory = charts_factory  # ChartFactory ou None

    # ── Méthodes publiques ─────────────────────────────────────────────────────

    def render_md(self) -> str:
        """Assemble les templates Jinja2 → string Markdown GFM avec front-matter YAML.

        Étapes :
            1. Enrichissement du contexte (kpi_hero, pivotal_moments, interpretations,
               executive_takeaways) via Enricher si non déjà rempli.
            2. Rendu du template _full.md.j2 avec le contexte enrichi.

        Returns:
            String Markdown GFM avec front-matter YAML en tête.
        """
        # 1. Enrichir le contexte avant rendu
        enriched_context = self._enrich_context()

        # 2. Récupérer l'environnement Jinja2
        from .jinja_env import get_jinja_env

        env = get_jinja_env()
        template = env.get_template("_full.md.j2")

        generated_at = datetime.now(tz=timezone.utc).isoformat()
        branding_version = (
            str(self.branding.get("id", "default"))
            if isinstance(self.branding, dict) and self.branding
            else "default"
        )

        # 3. Rendre le template
        md_text = template.render(
            context=enriched_context,
            branding=self.branding,
            generated_at=generated_at,
            template_version=_TEMPLATE_VERSION,
            branding_version=branding_version,
        )

        # 4. Embed des charts en data URI dans le Markdown (standalone .md)
        #    Remplace ](belief_drift.png) → ](data:image/png;base64,XXXX)
        if self.charts_factory is not None:
            md_text = _embed_charts_md(md_text, self.charts_factory)

        return md_text

    def render_pdf(self, charts_factory: Optional[Any] = None) -> bytes:
        """Pipeline complet : MD → markdown-it → HTML → WeasyPrint → bytes PDF.

        Args:
            charts_factory: Instance de ChartFactory (optionnelle). Si fournie,
                            les charts sont générés et embarqués en base64.

        Returns:
            Bytes PDF valide (WeasyPrint).

        Raises:
            ImportError: Si WeasyPrint ou markdown-it-py ne sont pas installés.
        """
        # 1. Render Markdown complet
        md_text = self.render_md()

        # 2. Extraire le front-matter YAML avant markdown-it
        #    (markdown-it ne parse pas le YAML, il le traiterait comme du texte)
        md_clean = _strip_frontmatter(md_text)

        # 3. Conversion Markdown → HTML via markdown-it-py
        html_body = _md_to_html(md_clean)

        # 4. Embed des charts en base64
        if charts_factory is not None:
            html_body = _embed_charts(html_body, charts_factory)

        # 5. Récupérer l'environnement Jinja2 pour le CSS
        from .jinja_env import get_jinja_env

        env = get_jinja_env()
        css_template = env.get_template("pdf_brand.css.j2")

        # Reconstruire generated_at pour le CSS
        generated_at = datetime.now(tz=timezone.utc).isoformat()
        enriched_context = self._enrich_context()

        css_text = css_template.render(
            branding=self.branding,
            lang=self.context.lang,
            context=enriched_context,
            generated_at=generated_at,
        )

        # 6. Construire le document HTML5 complet
        lang = self.context.lang
        dir_attr = ' dir="rtl"' if lang == "ar" else ""
        title = self.context.title or "Rapport Bassira"

        full_html = f"""<!DOCTYPE html>
<html lang="{lang}"{dir_attr}>
  <head>
    <meta charset="utf-8">
    <title>{_escape_html(title)}</title>
  </head>
  <body>
{html_body}
  </body>
</html>"""

        # 7. Rendu WeasyPrint
        pdf_bytes = _render_weasyprint(full_html, css_text, self.context)

        return pdf_bytes

    # ── Méthodes privées ───────────────────────────────────────────────────────

    def _enrich_context(self) -> PDFReportContext:
        """Enrichit le contexte via Enricher si les champs dérivés sont vides."""
        ctx = self.context
        # Vérifier si l'enrichissement est nécessaire
        needs_enrichment = (
            ctx.kpi_hero is None
            or not ctx.pivotal_moments
            or not ctx.interpretations
            or not ctx.executive_takeaways
        )

        if needs_enrichment:
            try:
                from .enricher import Enricher

                enricher = Enricher(context=ctx)
                ctx = enricher.enrich()
            except Exception as exc:
                logger.warning(
                    "Enricher failed (non-bloquant) : %s — rendu sans enrichissement.",
                    exc,
                )

        return ctx


# ── Helpers module-level ───────────────────────────────────────────────────────


def _embed_charts_md(md_text: str, charts_factory: Any) -> str:
    """Remplace les références image Markdown ``](name.png)`` par des data URIs base64.

    Le template ``_macros.md.j2`` génère ``![alt](belief_drift.png)``.
    Dans un fichier .md standalone, ces chemins sont invalides (les PNG ne sont
    pas copiés à côté du fichier). Cette fonction les remplace par des data URIs
    ``data:image/png;base64,XXXX`` produits par ``charts_factory``.

    Args:
        md_text:        Markdown rendu par Jinja2 (avec les chemins ``.png`` bruts).
        charts_factory: Instance de ChartFactory avec les méthodes de génération.

    Returns:
        Markdown avec les references PNG remplacées par des data URIs base64.
    """
    for method_name in _CHART_METHODS:
        placeholder = f"]({method_name}.png)"
        if placeholder not in md_text:
            continue

        try:
            chart_method = getattr(charts_factory, method_name, None)
            if chart_method is None:
                logger.warning(
                    "ChartFactory.%s() non trouvé — placeholder PNG conservé dans MD.",
                    method_name,
                )
                continue

            png_bytes: bytes = chart_method()
            b64 = base64.b64encode(png_bytes).decode("ascii")
            data_uri = f"](data:image/png;base64,{b64})"
            md_text = md_text.replace(placeholder, data_uri)
            logger.debug("Chart %s embarqué en data URI dans le MD (%d bytes PNG).", method_name, len(png_bytes))
        except Exception as exc:
            logger.warning(
                "Génération chart %s échouée pour embed MD : %s — placeholder conservé.",
                method_name,
                exc,
            )

    return md_text


def _strip_frontmatter(md_text: str) -> str:
    """Retire le front-matter YAML (blocs délimités par ---) du Markdown.

    Returns:
        Markdown sans front-matter YAML.
    """
    match = _FRONTMATTER_RE.match(md_text)
    if match:
        return md_text[match.end():]
    return md_text


def extract_frontmatter(md_text: str) -> dict:
    """Extrait et parse le front-matter YAML d'un texte Markdown.

    Args:
        md_text: Markdown avec front-matter YAML éventuel.

    Returns:
        Dict YAML parsé ou dict vide si absent/invalide.
    """
    match = _FRONTMATTER_RE.match(md_text)
    if not match:
        return {}
    try:
        import yaml  # type: ignore[import-not-found]

        return yaml.safe_load(match.group(1)) or {}
    except Exception:
        return {}


def _md_to_html(md_text: str) -> str:
    """Convertit du Markdown GFM en HTML via markdown-it-py.

    Args:
        md_text: Markdown sans front-matter.

    Returns:
        HTML fragment (sans DOCTYPE ni <html>).

    Raises:
        ImportError: Si markdown-it-py n'est pas installé.
    """
    try:
        from markdown_it import MarkdownIt

        md = MarkdownIt("commonmark").enable(["table", "strikethrough"])
        return md.render(md_text)
    except ImportError as exc:
        raise ImportError(
            "markdown-it-py est requis pour render_pdf(). "
            "Installez-le via : pip install markdown-it-py>=3"
        ) from exc


def _embed_charts(html_body: str, charts_factory: Any) -> str:
    """Remplace les placeholders img charts par des data URIs base64.

    Cherche dans html_body les balises du type :
        <img alt="belief_drift" src="charts/belief_drift.png">
    et remplace src par un data URI base64 du PNG généré par charts_factory.

    Args:
        html_body:      HTML fragment après rendu markdown-it.
        charts_factory: Instance de ChartFactory avec les méthodes chart.

    Returns:
        HTML fragment avec les charts embarqués en base64.
    """
    for method_name in _CHART_METHODS:
        # Le placeholder src= peut être "charts/<name>.png"
        placeholder = f'src="charts/{method_name}.png"'
        if placeholder not in html_body:
            continue

        try:
            chart_method = getattr(charts_factory, method_name, None)
            if chart_method is None:
                logger.warning("ChartFactory.%s() non trouvé — placeholder conservé.", method_name)
                continue

            png_bytes: bytes = chart_method()
            b64 = base64.b64encode(png_bytes).decode("ascii")
            data_uri = f'src="data:image/png;base64,{b64}"'
            html_body = html_body.replace(placeholder, data_uri)
            logger.debug("Chart %s embarqué (%d bytes PNG).", method_name, len(png_bytes))
        except Exception as exc:
            logger.warning(
                "Génération chart %s échouée : %s — placeholder conservé.",
                method_name,
                exc,
            )

    return html_body


def _render_weasyprint(full_html: str, css_text: str, context: PDFReportContext) -> bytes:
    """Rend le HTML complet via WeasyPrint et retourne les bytes PDF.

    Injecte aussi les métadonnées PDF (title, author, keywords, lang).

    Args:
        full_html: Document HTML5 complet.
        css_text:  CSS text du branding.
        context:   Contexte du rapport pour les métadonnées.

    Returns:
        Bytes PDF WeasyPrint.

    Raises:
        ImportError: Si WeasyPrint n'est pas installé.
    """
    try:
        from weasyprint import CSS, HTML  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "WeasyPrint est requis pour render_pdf(). "
            "Installez-le via : pip install weasyprint>=60"
        ) from exc

    # Metadata du PDF via WeasyPrint (title, author, etc.)
    # WeasyPrint >= 60 supporte les métadonnées via HTML <meta> tags
    # On les injecte dans le <head> du HTML.
    title = _escape_html(context.title or "Rapport Bassira")
    keywords = f"{context.framework}, {context.package}, {context.simulation_id}"

    # Injecter les meta tags dans le head
    meta_tags = f"""
    <meta name="author" content="Bassira">
    <meta name="keywords" content="{_escape_html(keywords)}">
    <meta name="description" content="{title}">
    <meta name="generator" content="Bassira PDF Renderer {_TEMPLATE_VERSION}">
    <meta name="language" content="{context.lang}">
"""
    # Insertion dans <head> après <meta charset>
    full_html = full_html.replace(
        '<meta charset="utf-8">',
        f'<meta charset="utf-8">{meta_tags}',
        1,
    )

    # Rendu WeasyPrint
    pdf_bytes: bytes = HTML(string=full_html).write_pdf(
        stylesheets=[CSS(string=css_text)],
        presentational_hints=True,
    )

    return pdf_bytes


def _escape_html(text: str) -> str:
    """Échappe les caractères HTML spéciaux dans une chaîne."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
