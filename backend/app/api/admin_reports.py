"""Endpoint admin Approve & Sign (US-128).

Blueprint ``admin_reports_bp`` monté sur ``/api/admin/reports``.

Routes :
  POST /api/admin/reports/<report_id>/approve — snapshot + watermark + signature

Sécurité :
  @require_super_admin — réservé aux fondateurs Bassira.

Dépendances US-126 :
  report_workflow.transition() est importé en best-effort : si le module
  n'est pas encore disponible (merge US-126 en attente), la transition
  est ignorée avec un log warning — pas de raise.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, Optional

from flask import Blueprint, g, jsonify, request

from ..auth.decorators import require_auth, require_super_admin


logger = logging.getLogger("miroshark.api.admin_reports")

admin_reports_bp = Blueprint("admin_reports", __name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _err(code: str, message: str, status: int):
    return jsonify({"success": False, "error_code": code, "error": message}), status


def _try_workflow_transition(report_id: str, target_status: str) -> None:
    """Appel best-effort à report_workflow.transition() (US-126).

    Si le module n'est pas disponible (merge en attente) ou si la
    transition échoue, on log un warning sans faire planter le endpoint.
    """
    try:
        from ..services.report_workflow import transition  # type: ignore[import]
        transition(report_id, target_status)
    except ImportError:
        logger.warning(
            "report_workflow non disponible (US-126 pas encore mergé) — "
            "transition %s ignorée pour report_id=%s",
            target_status,
            report_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Échec transition workflow %s pour report_id=%s : %s",
            target_status,
            report_id,
            exc,
        )


def _next_snapshot_version(report_id: str, base_dir: Optional[Any] = None) -> int:
    """Calcule le prochain numéro de version de snapshot (= nb existant + 1)."""
    from ..services.report_pdf.snapshot import list_snapshots

    existing = list_snapshots(report_id, base_dir=base_dir)
    return (existing[-1]["version"] + 1) if existing else 1


# ─── Route ───────────────────────────────────────────────────────────────────


@admin_reports_bp.route("/<report_id>/approve", methods=["POST"])
@require_super_admin
def approve_report(report_id: str):
    """Approuve un rapport : génère snapshot immuable + watermark + signature.

    Body JSON :
        {
            "watermark_recipient": {"name": str, "company": str | null} | null,
            "sign": bool
        }

    Returns :
        {
            "success": true,
            "snapshot_path": str,
            "sha256": str,
            "version": int
        }
    """
    # ── 1. Parse body ─────────────────────────────────────────────────────────
    body: Dict = {}
    if request.content_length and request.content_length > 0:
        body = request.get_json(silent=True) or {}

    watermark_recipient: Optional[Dict] = body.get("watermark_recipient")
    do_sign: bool = bool(body.get("sign", False))

    # Validation basique du watermark_recipient
    if watermark_recipient is not None:
        if not isinstance(watermark_recipient, dict):
            return _err("INVALID_BODY", "'watermark_recipient' doit être un objet ou null.", 400)
        if not watermark_recipient.get("name"):
            return _err("INVALID_BODY", "'watermark_recipient.name' est requis.", 400)

    # ── 2. Charger le contexte PDF via PDFContextLoader ───────────────────────
    try:
        from ..services.report_pdf.loader import PDFContextLoader, PDFContextLoaderError

        context = PDFContextLoader.load(
            report_id=report_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("PDFContextLoader.load() échoué pour report_id=%s : %s", report_id, exc)
        return _err("CONTEXT_LOAD_ERROR", f"Impossible de charger le contexte : {exc}", 500)

    # ── 3. Charger le branding actif ──────────────────────────────────────────
    branding: Optional[Dict] = None
    try:
        from ..services.pdf_branding import get_active_branding  # type: ignore[import]

        # get_active_branding attend org_id — on le récupère depuis le contexte si possible
        org_id = getattr(context, "org_id", None) or getattr(context, "organisation_id", None)
        if org_id:
            branding = get_active_branding(org_id)
    except ImportError:
        logger.warning("pdf_branding non disponible — branding None utilisé.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_active_branding() échoué : %s — branding None.", exc)

    # ── 4. Rendre le PDF via Renderer ─────────────────────────────────────────
    try:
        from ..services.report_pdf.renderer import Renderer
        from ..services.report_pdf.charts import ChartFactory

        chart_factory = ChartFactory(context)
        renderer = Renderer(context, branding)
        markdown_str = renderer.render_md()
        pdf_bytes = renderer.render_pdf(charts_factory=chart_factory)
    except Exception as exc:  # noqa: BLE001
        logger.error("Renderer échoué pour report_id=%s : %s", report_id, exc)
        return _err("RENDER_ERROR", f"Erreur rendu PDF : {exc}", 500)

    # ── 5. Collecter les charts PNG ───────────────────────────────────────────
    chart_pngs: Dict[str, bytes] = {}
    try:
        from ..services.report_pdf.charts import ChartFactory as _CF

        _cf = _CF(context)
        chart_methods = [
            "belief_drift",
            "polymarket_curves",
            "demographic_pyramid",
            "influence_leaderboard",
            "interaction_network",
        ]
        for method_name in chart_methods:
            method = getattr(_cf, method_name, None)
            if callable(method):
                try:
                    png = method()
                    if png:
                        chart_pngs[method_name] = png
                except Exception as chart_exc:  # noqa: BLE001
                    logger.warning("Chart %s échoué : %s", method_name, chart_exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Collecte charts échouée : %s — snapshot sans charts.", exc)

    # ── 6. Watermark optionnel ────────────────────────────────────────────────
    if watermark_recipient is not None:
        try:
            from ..services.report_pdf.watermark import apply_watermark_to_pdf

            pdf_bytes = apply_watermark_to_pdf(
                pdf_bytes,
                recipient_name=watermark_recipient["name"],
                recipient_company=watermark_recipient.get("company"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Watermark échoué : %s", exc)
            return _err("WATERMARK_ERROR", f"Erreur filigrane : {exc}", 500)

    # ── 7. Signature PAdES optionnelle ────────────────────────────────────────
    if do_sign:
        try:
            from ..services.report_pdf.signer import sign_pdf_pades

            pdf_bytes = sign_pdf_pades(pdf_bytes)
        except Exception as exc:  # noqa: BLE001
            logger.error("Signature PAdES échouée : %s", exc)
            # La signature est optionnelle — on continue sans.

    # ── 8. Calculer SHA256 du PDF final ───────────────────────────────────────
    sha256_hex = hashlib.sha256(pdf_bytes).hexdigest()

    # ── 9. Créer le snapshot immuable ─────────────────────────────────────────
    try:
        from ..services.report_pdf.snapshot import create_snapshot

        version = _next_snapshot_version(report_id)
        snapshot_result = create_snapshot(
            report_id=report_id,
            version=version,
            markdown=markdown_str,
            pdf_bytes=pdf_bytes,
            branding=branding,
            chart_pngs=chart_pngs,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("create_snapshot() échoué : %s", exc)
        return _err("SNAPSHOT_ERROR", f"Erreur snapshot : {exc}", 500)

    # ── 10. Transition workflow APPROVED (US-126, best-effort) ────────────────
    _try_workflow_transition(report_id, "APPROVED")

    logger.info(
        "Rapport approuvé : report_id=%s version=%d sha256=%s sign=%s watermark=%s",
        report_id,
        snapshot_result["version"],
        sha256_hex[:16] + "…",
        do_sign,
        watermark_recipient is not None,
    )

    return jsonify({
        "success": True,
        "snapshot_path": snapshot_result["path"],
        "sha256": snapshot_result["sha256"],
        "version": snapshot_result["version"],
    }), 200
