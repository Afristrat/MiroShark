"""
PDF Export API — US-024 / US-059 / US-133
Génère un rapport PDF ou Markdown enrichi pour une simulation terminée
via le nouveau pipeline Bassira (US-118 → US-125 + Enricher + ChartFactory).

POST /api/simulation/<simulation_id>/export-pdf
  body (optionnel JSON) : { "graph_image_b64": "<base64 PNG>" }
  → 200 application/pdf   (stream binaire PDF)
  → 400 INVALID_SIMULATION_ID
  → 404 SIMULATION_NOT_FOUND
  → 500 PDF_EXPORT_FAILED

GET /api/simulation/<simulation_id>/export-md
  → 200 text/markdown
  → 400 INVALID_SIMULATION_ID
  → 404 SIMULATION_NOT_FOUND
  → 500 MD_EXPORT_FAILED

US-133 : tout le code reportlab obsolète (sections plates, _build_* v1) a été
retiré (Option B clean code). Les deux fonctions _build_pdf / _build_markdown
délèguent désormais au pipeline :
    PDFContextLoader.load() → Enricher.enrich() → Renderer.render_pdf/md()
"""

from __future__ import annotations

import json
import os
import traceback
from typing import Optional

from flask import jsonify, make_response, request

from . import simulation_bp
from ..services.simulation_manager import SimulationManager
from ..utils.logger import get_logger
from ..utils.validation import validate_simulation_id

logger = get_logger("miroshark.api.pdf_export")


# ── Helpers de résolution ────────────────────────────────────────────────────


def _resolve_report_id_for_simulation(simulation_id: str) -> Optional[str]:
    """Tente de trouver un report_id associé à simulation_id.

    Stratégie :
      1. Répertoire reports/ — cherche le premier rapport dont meta.json
         contient un champ simulation_id correspondant.
      2. Sinon retourne None (mode dégradé sans outline).
    """
    from ..services.report_pdf.loader import _REPORTS_DIR

    if not _REPORTS_DIR.is_dir():
        return None

    try:
        for entry in sorted(_REPORTS_DIR.iterdir()):
            if not entry.is_dir():
                continue
            meta_path = entry / "meta.json"
            if not meta_path.is_file():
                # Essayer aussi outline.json pour le champ simulation_id
                outline_path = entry / "outline.json"
                if not outline_path.is_file():
                    continue
                try:
                    with open(outline_path, encoding="utf-8") as fh:
                        data = json.load(fh)
                    if data.get("simulation_id") == simulation_id:
                        return entry.name
                except Exception:
                    continue
            else:
                try:
                    with open(meta_path, encoding="utf-8") as fh:
                        data = json.load(fh)
                    if data.get("simulation_id") == simulation_id:
                        return entry.name
                except Exception:
                    continue
    except Exception as exc:
        logger.debug("_resolve_report_id_for_simulation error (non-bloquant) : %s", exc)

    return None


def _resolve_lang_for_simulation(simulation_id: str) -> str:
    """Lit simulation_config.json::lang ou retourne 'fr' par défaut.

    Consulte aussi SimulationState.locale si la config est absente.
    """
    # 1. Tenter via SimulationManager (rapide, en mémoire / fichier)
    try:
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if state is not None:
            locale = getattr(state, "locale", None)
            if locale and locale in ("fr", "en", "ar"):
                return locale
    except Exception:
        pass

    # 2. Tenter via simulation_config.json directement
    try:
        from ..services.report_pdf.loader import _SIMULATIONS_DIR
        config_path = _SIMULATIONS_DIR / simulation_id / "simulation_config.json"
        if config_path.is_file():
            with open(config_path, encoding="utf-8") as fh:
                config = json.load(fh)
            lang = config.get("lang") or config.get("locale") or config.get("language")
            if lang and lang in ("fr", "en", "ar"):
                return lang
    except Exception:
        pass

    return "fr"


# ── Builders via nouveau pipeline ────────────────────────────────────────────


def _build_pdf(simulation_id: str, graph_image_b64: str = "") -> bytes:
    """Génère le PDF rapport via le nouveau pipeline (US-118 → 125 + Enricher).

    US-133 : remplace la génération ReportLab à plat par le pipeline complet :
        PDFContextLoader → Enricher → ChartFactory → Renderer.render_pdf()

    Args:
        simulation_id:  Identifiant de la simulation (format sim_<12hex>).
        graph_image_b64: Image PNG base64 du graphe fournie par le frontend.
                         Ignorée (le ChartFactory génère interaction_network
                         server-side). Conservée dans la signature pour ne pas
                         casser l'API frontend existante.

    Returns:
        Bytes PDF valides.

    Raises:
        PDFContextLoaderError: si simulation_config.json est absent.
        ImportError: si WeasyPrint n'est pas installé.
    """
    from ..services.report_pdf.loader import PDFContextLoader, PDFContextLoaderError
    from ..services.report_pdf.enricher import Enricher
    from ..services.report_pdf.charts import ChartFactory
    from ..services.report_pdf.renderer import Renderer

    # 1. Résoudre report_id et lang
    report_id = _resolve_report_id_for_simulation(simulation_id)
    lang = _resolve_lang_for_simulation(simulation_id)

    logger.debug(
        "_build_pdf : simulation_id=%s report_id=%s lang=%s",
        simulation_id, report_id, lang,
    )

    # 2. Charger le contexte
    context = PDFContextLoader.load(
        simulation_id=simulation_id,
        report_id=report_id,
        lang=lang,
    )

    # 3. Enrichir (kpi_hero, pivotal_moments, narratives, takeaways)
    Enricher(context).enrich()

    # 4. Render via Renderer + ChartFactory (WeasyPrint)
    chart_factory = ChartFactory(context)
    branding = None  # pas de branding PDF custom pour le self-service utilisateur
    renderer = Renderer(context, branding=branding)
    pdf_bytes = renderer.render_pdf(charts_factory=chart_factory)

    # NOTE US-133 : graph_image_b64 du frontend est ignoré — le ChartFactory
    # génère l'interaction_network server-side. On logue pour traçabilité.
    if graph_image_b64:
        logger.info(
            "graph_image_b64 reçu mais ignoré pour %s — "
            "interaction_network désormais généré par ChartFactory server-side.",
            simulation_id,
        )

    return pdf_bytes


def _build_markdown(simulation_id: str) -> str:
    """Génère le rapport Markdown via le nouveau pipeline.

    US-133 : remplace le builder manuel par Renderer.render_md() (Jinja2 GFM).

    Returns:
        String Markdown GFM avec front-matter YAML en tête.
    """
    from ..services.report_pdf.loader import PDFContextLoader
    from ..services.report_pdf.enricher import Enricher
    from ..services.report_pdf.renderer import Renderer

    # 1. Résoudre report_id et lang
    report_id = _resolve_report_id_for_simulation(simulation_id)
    lang = _resolve_lang_for_simulation(simulation_id)

    logger.debug(
        "_build_markdown : simulation_id=%s report_id=%s lang=%s",
        simulation_id, report_id, lang,
    )

    # 2. Charger le contexte
    context = PDFContextLoader.load(
        simulation_id=simulation_id,
        report_id=report_id,
        lang=lang,
    )

    # 3. Enrichir
    Enricher(context).enrich()

    # 4. Render Markdown
    branding = None
    renderer = Renderer(context, branding=branding)
    return renderer.render_md()


# ── Flask endpoints ──────────────────────────────────────────────────────────


@simulation_bp.route("/<simulation_id>/export-pdf", methods=["POST"])
def export_simulation_pdf(simulation_id: str):
    """POST /api/simulation/<id>/export-pdf — PDF enrichi via le nouveau pipeline."""
    try:
        try:
            validate_simulation_id(simulation_id)
        except ValueError as exc:
            return jsonify({"success": False, "error_code": "INVALID_SIMULATION_ID", "error": str(exc)}), 400

        manager = SimulationManager()
        if not manager.get_simulation(simulation_id):
            return jsonify({"success": False, "error_code": "SIMULATION_NOT_FOUND",
                            "error": f"Simulation introuvable : {simulation_id}"}), 404

        body = request.get_json(silent=True) or {}
        graph_b64 = body.get("graph_image_b64") or ""

        pdf_bytes = _build_pdf(simulation_id, graph_image_b64=graph_b64)
        response = make_response(pdf_bytes)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f'attachment; filename="bassira-{simulation_id}.pdf"'
        response.headers["Content-Length"] = str(len(pdf_bytes))
        return response

    except Exception as exc:
        logger.error("PDF export failed for %s: %s", simulation_id, exc)
        return jsonify({"success": False, "error_code": "PDF_EXPORT_FAILED",
                        "error": str(exc), "traceback": traceback.format_exc()}), 500


@simulation_bp.route("/<simulation_id>/export-md", methods=["GET"])
def export_simulation_markdown(simulation_id: str):
    """GET /api/simulation/<id>/export-md — rapport Markdown via le nouveau pipeline."""
    try:
        try:
            validate_simulation_id(simulation_id)
        except ValueError as exc:
            return jsonify({"success": False, "error_code": "INVALID_SIMULATION_ID", "error": str(exc)}), 400

        manager = SimulationManager()
        if not manager.get_simulation(simulation_id):
            return jsonify({"success": False, "error_code": "SIMULATION_NOT_FOUND",
                            "error": f"Simulation introuvable : {simulation_id}"}), 404

        md_content = _build_markdown(simulation_id)
        response = make_response(md_content)
        response.headers["Content-Type"] = "text/markdown; charset=utf-8"
        response.headers["Content-Disposition"] = f'attachment; filename="bassira-{simulation_id}.md"'
        return response

    except Exception as exc:
        logger.error("MD export failed for %s: %s", simulation_id, exc)
        return jsonify({"success": False, "error_code": "MD_EXPORT_FAILED",
                        "error": str(exc)}), 500
