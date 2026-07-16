"""Endpoints génération PDF hybride sync/async (US-129).

Blueprint ``pdf_generation_bp`` monté sur ``/api/admin/reports``.

Routes :
  POST   /api/admin/reports/<report_id>/preview
         → Preview sync (≤ 5 s) — retourne PDF cover 1 page
  POST   /api/admin/reports/<report_id>/generate
         → Body {variant, lang, simulation_id, branding_id}
         → Enqueue async RQ, retourne {job_id, status_url}
  GET    /api/admin/reports/<report_id>/jobs/<job_id>
         → Polling status : queued|started|finished|failed + URL PDF

Queue :
  - RQ + Redis (REDIS_URL env).
  - Si Redis absent → mode synchrone fallback (génère immédiatement).

Sécurité :
  - Toutes les routes exigent @require_auth (JWT Supabase valide).
  - Super-admin only via @require_super_admin.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, Optional

from flask import Blueprint, Response, jsonify, request
from flask.typing import ResponseReturnValue

from ..auth.decorators import require_auth, require_super_admin

logger = logging.getLogger("miroshark.api.pdf_generation")

pdf_generation_bp = Blueprint("pdf_generation", __name__)

# ─── Helpers Redis / RQ ───────────────────────────────────────────────────────


def _get_redis_connection() -> Optional[Any]:
    """Retourne une connexion Redis si REDIS_URL est configuré, sinon None."""
    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        return None
    try:
        from redis import Redis  # type: ignore[import-not-found]

        return Redis.from_url(redis_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis non disponible (%s) — mode sync fallback.", exc)
        return None


def _get_queue(redis_conn: Any) -> Optional[Any]:
    """Retourne la Queue RQ 'pdf-generation', ou None si RQ absent."""
    try:
        from rq import Queue  # type: ignore[import-not-found]

        return Queue("pdf-generation", connection=redis_conn)
    except Exception as exc:  # noqa: BLE001
        logger.warning("RQ non disponible (%s) — mode sync fallback.", exc)
        return None


def _job_status(redis_conn: Any, job_id: str) -> Dict[str, Any]:
    """Retourne le statut d'un job RQ depuis Redis.

    Returns:
        Dict avec keys: job_id, status, pdf_path, error.
    """
    try:
        from rq.job import Job  # type: ignore[import-not-found]

        job = Job.fetch(job_id, connection=redis_conn)
        status = job.get_status()
        # RQ status: queued | started | finished | failed | stopped | canceled
        status_str = str(status.value) if hasattr(status, "value") else str(status)

        # job.return_value() est la API non-dépréciée (rq >= 1.15) ;
        # fallback sur job.result pour compatibilité versions antérieures.
        if status_str == "finished":
            try:
                result_data = job.return_value()
            except Exception:  # noqa: BLE001
                result_data = getattr(job, "result", None)
        else:
            result_data = None
        error = None
        if status_str == "failed":
            error = str(job.exc_info) if job.exc_info else "Erreur inconnue."

        pdf_path: Optional[str] = None
        if isinstance(result_data, dict):
            pdf_path = result_data.get("pdf_path")

        return {
            "job_id": job_id,
            "status": status_str,
            "pdf_path": pdf_path,
            "error": error,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "job_id": job_id,
            "status": "failed",
            "pdf_path": None,
            "error": str(exc),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoint : POST /api/admin/reports/<report_id>/preview  (sync ≤ 5 s)
# ═══════════════════════════════════════════════════════════════════════════════


@pdf_generation_bp.route("/<report_id>/preview", methods=["POST"])
@require_auth
@require_super_admin
def preview_report(report_id: str) -> ResponseReturnValue:
    """Génère et retourne la page de couverture du rapport PDF (1 page, sync).

    Body JSON (optionnel) :
      {
        "simulation_id": "sim_...",   // requis si pas dans les métadonnées du rapport
        "lang": "fr",                 // défaut : "fr"
        "branding_id": null           // défaut : null (Bassira defaults)
      }

    Returns:
      application/pdf — bytes de la cover page (1 page).
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    simulation_id: str = data.get("simulation_id", "")
    lang: str = data.get("lang", "fr")
    branding_id: Optional[str] = data.get("branding_id") or None

    if not simulation_id:
        return jsonify(
            {"success": False, "error_code": "MISSING_SIMULATION_ID",
             "error": "simulation_id est requis."}
        ), 400

    # Générer directement (sync) — variante one-pager = 1 page cover
    from app.workers.pdf_generation_worker import generate_pdf_job

    result = generate_pdf_job(
        report_id=report_id,
        simulation_id=simulation_id,
        variant="one-pager",
        lang=lang,
        branding_id=branding_id,
    )

    if result.get("status") != "finished" or not result.get("pdf_path"):
        return jsonify(
            {"success": False, "error_code": "PREVIEW_FAILED",
             "error": result.get("error", "Génération preview échouée.")}
        ), 500

    from pathlib import Path

    pdf_path = Path(result["pdf_path"])
    pdf_bytes = pdf_path.read_bytes()

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="preview_{report_id}.pdf"',
            "X-Report-Id": report_id,
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoint : POST /api/admin/reports/<report_id>/generate  (async)
# ═══════════════════════════════════════════════════════════════════════════════


@pdf_generation_bp.route("/<report_id>/generate", methods=["POST"])
@require_auth
@require_super_admin
def generate_report(report_id: str) -> ResponseReturnValue:
    """Enqueue une génération PDF async via RQ.

    Body JSON :
      {
        "simulation_id": "sim_...",   // requis
        "variant":        "full",     // défaut : "full" {full|exec|public|one-pager}
        "lang":           "fr",       // défaut : "fr"
        "branding_id":    null        // défaut : null
      }

    Returns (202 Accepted) :
      {
        "success":    true,
        "job_id":     "...",
        "status_url": "/api/admin/reports/<id>/jobs/<job_id>",
        "mode":       "async" | "sync"
      }
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    simulation_id: str = data.get("simulation_id", "")
    variant: str = data.get("variant", "full")
    lang: str = data.get("lang", "fr")
    branding_id: Optional[str] = data.get("branding_id") or None

    if not simulation_id:
        return jsonify(
            {"success": False, "error_code": "MISSING_SIMULATION_ID",
             "error": "simulation_id est requis."}
        ), 400

    _VALID_VARIANTS = {"full", "exec", "public", "one-pager"}
    if variant not in _VALID_VARIANTS:
        return jsonify(
            {"success": False, "error_code": "INVALID_VARIANT",
             "error": f"variant doit être l'un de : {', '.join(sorted(_VALID_VARIANTS))}."}
        ), 400

    # ── Tenter mode async (Redis + RQ) ────────────────────────────────────
    redis_conn = _get_redis_connection()
    if redis_conn is not None:
        queue = _get_queue(redis_conn)
        if queue is not None:
            from app.workers.pdf_generation_worker import generate_pdf_job

            job = queue.enqueue(
                generate_pdf_job,
                report_id,
                simulation_id,
                variant,
                lang,
                branding_id,
                job_timeout=300,  # 5 min max
            )
            status_url = f"/api/admin/reports/{report_id}/jobs/{job.id}"
            logger.info(
                "Job PDF enqueued : %s (report=%s, sim=%s, variant=%s, lang=%s).",
                job.id, report_id, simulation_id, variant, lang,
            )
            return jsonify(
                {
                    "success": True,
                    "job_id": job.id,
                    "status_url": status_url,
                    "mode": "async",
                }
            ), 202

    # ── Fallback sync si Redis absent ─────────────────────────────────────
    logger.info(
        "Mode sync fallback (Redis absent) — génération immédiate report=%s.",
        report_id,
    )
    from app.workers.pdf_generation_worker import generate_pdf_job

    job_id = f"sync-{uuid.uuid4().hex[:8]}"
    result = generate_pdf_job(
        report_id=report_id,
        simulation_id=simulation_id,
        variant=variant,
        lang=lang,
        branding_id=branding_id,
        job_id=job_id,
    )

    if result.get("status") == "finished":
        return jsonify(
            {
                "success": True,
                "job_id": job_id,
                "status": "finished",
                "pdf_path": result.get("pdf_path"),
                "mode": "sync",
            }
        ), 200
    else:
        return jsonify(
            {
                "success": False,
                "job_id": job_id,
                "status": "failed",
                "error": result.get("error"),
                "mode": "sync",
            }
        ), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoint : GET /api/admin/reports/<report_id>/jobs/<job_id>  (polling)
# ═══════════════════════════════════════════════════════════════════════════════


@pdf_generation_bp.route("/<report_id>/jobs/<job_id>", methods=["GET"])
@require_auth
@require_super_admin
def get_job_status(report_id: str, job_id: str) -> ResponseReturnValue:
    """Retourne le statut d'un job de génération PDF.

    Returns :
      {
        "job_id":     "...",
        "status":     "queued" | "started" | "finished" | "failed",
        "pdf_path":   "..." | null,        // renseigné si finished
        "download_url": "..." | null,      // URL relative si finished
        "error":      "..." | null
      }
    """
    # Mode sync : le job_id commence par "sync-" → pas de Redis à interroger
    if job_id.startswith("sync-"):
        return jsonify(
            {
                "job_id": job_id,
                "status": "finished",
                "pdf_path": None,
                "download_url": None,
                "error": "Mode sync — résultat retourné directement par /generate.",
            }
        ), 200

    redis_conn = _get_redis_connection()
    if redis_conn is None:
        return jsonify(
            {
                "success": False,
                "error_code": "REDIS_UNAVAILABLE",
                "error": "Redis non disponible — impossible de récupérer le statut du job.",
            }
        ), 503

    status_data = _job_status(redis_conn, job_id)

    # Construire l'URL de téléchargement si le job est terminé
    download_url: Optional[str] = None
    if status_data.get("status") == "finished" and status_data.get("pdf_path"):
        # On expose le path sous forme d'URL de téléchargement (à implémenter côté client)
        # Pour l'instant, le path disque absolu est exposé — le frontend peut
        # construire un lien vers /api/admin/reports/<id>/download ou similaire.
        download_url = f"/api/admin/reports/{report_id}/download/{job_id}"

    return jsonify(
        {
            "job_id": job_id,
            "status": status_data.get("status"),
            "pdf_path": status_data.get("pdf_path"),
            "download_url": download_url,
            "error": status_data.get("error"),
        }
    ), 200
