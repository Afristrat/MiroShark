"""
PDF Export API — US-024 / US-059 / US-133 / US-138

Génère un rapport PDF ou Markdown enrichi pour une simulation terminée via
le pipeline Bassira (US-118 → US-125 + Enricher + ChartFactory + Renderer).

POST /api/simulation/<simulation_id>/export-pdf
  body (optionnel JSON) :
    {
      "graph_image_b64": "<base64 PNG>",     # ignoré, conservé compat
      "variant": "full" | "exec" | "public" | "one-pager"   # défaut "full"
    }
  → 200 application/pdf
  → 400 INVALID_SIMULATION_ID | INVALID_VARIANT
  → 404 SIMULATION_NOT_FOUND
  → 500 PDF_EXPORT_FAILED

GET  /api/simulation/<simulation_id>/export-md?variant=full|exec|public|one-pager
  → 200 text/markdown (charts en data URI base64 inlinés)
  → 400 INVALID_SIMULATION_ID | INVALID_VARIANT
  → 404 SIMULATION_NOT_FOUND
  → 500 MD_EXPORT_FAILED

US-138 — fixes critiques découverts en validation prod 2026-05-07 :
  • Bug 1 — paramètre `variant` n'était pas extrait du body et n'arrivait
    jamais à `Renderer.render_pdf()` → les 4 variantes produisaient un PDF
    identique de taille `full`.
  • Bug 2 — `_build_markdown()` instanciait Renderer SANS `charts_factory`,
    si bien que `_embed_charts_md()` ne s'appliquait jamais → 0 chart en
    data URI dans le `.md` exporté.
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

# Variantes PDF/MD supportées (US-131 + US-138). Doit rester en sync avec
# `Renderer._VARIANT_TEMPLATE` côté report_pdf/renderer.py.
_ALLOWED_VARIANTS = frozenset({"full", "exec", "public", "one-pager"})
_DEFAULT_VARIANT = "full"


def _parse_variant(raw: Optional[str]) -> str:
    """Valide et normalise un nom de variante PDF/MD.

    Retourne `_DEFAULT_VARIANT` si `raw` est None/vide. Lève `ValueError`
    sur une valeur inconnue (l'appelant transforme en 400 INVALID_VARIANT).
    """
    if not raw:
        return _DEFAULT_VARIANT
    candidate = str(raw).strip().lower()
    if candidate not in _ALLOWED_VARIANTS:
        raise ValueError(
            f"Variante inconnue : {raw!r}. "
            f"Variantes autorisées : {sorted(_ALLOWED_VARIANTS)}."
        )
    return candidate


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


def _build_pdf(
    simulation_id: str,
    graph_image_b64: str = "",
    variant: str = _DEFAULT_VARIANT,
) -> bytes:
    """Génère le PDF rapport via le pipeline (US-118 → 125 + Enricher + US-131).

    Args:
        simulation_id:  Identifiant de la simulation (format sim_<12hex>).
        graph_image_b64: PNG base64 du graphe (ignoré, conservé pour compat).
        variant:        Variante de rapport — "full" (~50p), "exec" (~5p),
                        "public" (~3p anonymisé), "one-pager" (~1p).
                        Doit être déjà validé via `_parse_variant`.

    Returns:
        Bytes PDF valides.

    Raises:
        PDFContextLoaderError: si simulation_config.json est absent.
        ImportError:           si WeasyPrint n'est pas installé.
    """
    from ..services.report_pdf.loader import PDFContextLoader, PDFContextLoaderError  # noqa: F401
    from ..services.report_pdf.enricher import Enricher
    from ..services.report_pdf.charts import ChartFactory
    from ..services.report_pdf.renderer import Renderer

    report_id = _resolve_report_id_for_simulation(simulation_id)
    lang = _resolve_lang_for_simulation(simulation_id)

    logger.debug(
        "_build_pdf : simulation_id=%s report_id=%s lang=%s variant=%s",
        simulation_id, report_id, lang, variant,
    )

    context = PDFContextLoader.load(
        simulation_id=simulation_id,
        report_id=report_id,
        lang=lang,
    )

    Enricher(context).enrich()

    chart_factory = ChartFactory(context)
    branding = None  # pas de branding PDF custom pour le self-service utilisateur
    renderer = Renderer(context, branding=branding)
    pdf_bytes = renderer.render_pdf(charts_factory=chart_factory, variant=variant)

    if graph_image_b64:
        logger.info(
            "graph_image_b64 reçu mais ignoré pour %s — "
            "interaction_network désormais généré par ChartFactory server-side.",
            simulation_id,
        )

    return pdf_bytes


def _build_markdown(
    simulation_id: str,
    variant: str = _DEFAULT_VARIANT,
) -> str:
    """Génère le rapport Markdown via Renderer.render_md() (Jinja2 GFM).

    US-138 : instancie maintenant un `ChartFactory(context)` et le passe au
    Renderer pour que `_embed_charts_md()` remplace les références
    `](belief_drift.png)` par des data URIs base64 (sinon le `.md` exporté
    contient des chemins relatifs cassés vers des PNG inexistants).

    Args:
        simulation_id: Identifiant de la simulation (format sim_<12hex>).
        variant:       Variante de rapport (cf. `_build_pdf`).

    Returns:
        String Markdown GFM avec front-matter YAML en tête, charts inlinés.
    """
    from ..services.report_pdf.loader import PDFContextLoader
    from ..services.report_pdf.enricher import Enricher
    from ..services.report_pdf.charts import ChartFactory
    from ..services.report_pdf.renderer import Renderer

    report_id = _resolve_report_id_for_simulation(simulation_id)
    lang = _resolve_lang_for_simulation(simulation_id)

    logger.debug(
        "_build_markdown : simulation_id=%s report_id=%s lang=%s variant=%s",
        simulation_id, report_id, lang, variant,
    )

    context = PDFContextLoader.load(
        simulation_id=simulation_id,
        report_id=report_id,
        lang=lang,
    )

    Enricher(context).enrich()

    chart_factory = ChartFactory(context)
    branding = None
    renderer = Renderer(context, branding=branding, charts_factory=chart_factory)
    return renderer.render_md(variant=variant)


# ── Flask endpoints ──────────────────────────────────────────────────────────


@simulation_bp.route("/<simulation_id>/export-pdf", methods=["POST"])
def export_simulation_pdf(simulation_id: str):
    """POST /api/simulation/<id>/export-pdf — PDF enrichi via le pipeline.

    Body JSON (tous optionnels) :
        - `variant` : "full" | "exec" | "public" | "one-pager" (défaut "full")
        - `graph_image_b64` : conservé pour compat, ignoré côté serveur
    """
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
        try:
            variant = _parse_variant(body.get("variant"))
        except ValueError as exc:
            return jsonify({"success": False, "error_code": "INVALID_VARIANT", "error": str(exc)}), 400

        pdf_bytes = _build_pdf(simulation_id, graph_image_b64=graph_b64, variant=variant)
        filename = f'bassira-{simulation_id}-{variant}.pdf' if variant != _DEFAULT_VARIANT else f'bassira-{simulation_id}.pdf'
        response = make_response(pdf_bytes)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.headers["Content-Length"] = str(len(pdf_bytes))
        return response

    except Exception as exc:
        logger.error("PDF export failed for %s: %s", simulation_id, exc)
        return jsonify({"success": False, "error_code": "PDF_EXPORT_FAILED",
                        "error": str(exc), "traceback": traceback.format_exc()}), 500


@simulation_bp.route("/<simulation_id>/export-md", methods=["GET"])
def export_simulation_markdown(simulation_id: str):
    """GET /api/simulation/<id>/export-md?variant=full|exec|public|one-pager."""
    try:
        try:
            validate_simulation_id(simulation_id)
        except ValueError as exc:
            return jsonify({"success": False, "error_code": "INVALID_SIMULATION_ID", "error": str(exc)}), 400

        manager = SimulationManager()
        if not manager.get_simulation(simulation_id):
            return jsonify({"success": False, "error_code": "SIMULATION_NOT_FOUND",
                            "error": f"Simulation introuvable : {simulation_id}"}), 404

        try:
            variant = _parse_variant(request.args.get("variant"))
        except ValueError as exc:
            return jsonify({"success": False, "error_code": "INVALID_VARIANT", "error": str(exc)}), 400

        md_content = _build_markdown(simulation_id, variant=variant)
        filename = f'bassira-{simulation_id}-{variant}.md' if variant != _DEFAULT_VARIANT else f'bassira-{simulation_id}.md'
        response = make_response(md_content)
        response.headers["Content-Type"] = "text/markdown; charset=utf-8"
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Exception as exc:
        logger.error("MD export failed for %s: %s", simulation_id, exc)
        return jsonify({"success": False, "error_code": "MD_EXPORT_FAILED",
                        "error": str(exc)}), 500
