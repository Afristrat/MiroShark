"""Génération PDF asynchrone via Redis/RQ (US-208)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from typing import Any, Optional

from flask import Blueprint, Response, jsonify, request
from flask.typing import ResponseReturnValue

from ..auth.decorators import require_auth, require_super_admin

logger = logging.getLogger("miroshark.api.pdf_generation")

pdf_generation_bp = Blueprint("pdf_generation", __name__)

_VALID_VARIANTS = frozenset({"full", "exec", "public", "one-pager"})
_REPORT_ID_RE = re.compile(r"^report_[a-f0-9]{12}$")
_SIMULATION_ID_RE = re.compile(r"^sim_[a-f0-9]{12}$")
_JOB_VERSION = "2"
_JOB_TTL_SECONDS = 7 * 24 * 60 * 60
_ENQUEUE_LOCK_TTL_SECONDS = 60


class RedisUnavailable(RuntimeError):
    """Redis ou RQ est configuré mais ne peut pas accepter de travail."""


def _redis_url() -> str:
    return os.environ.get("REDIS_URL", "").strip()


def _get_redis_connection() -> Any:
    """Retourne une connexion Redis vérifiée, ou lève si elle est indisponible."""
    redis_url = _redis_url()
    if not redis_url:
        return None
    try:
        from redis import Redis  # type: ignore[import-not-found]

        connection = Redis.from_url(redis_url)
        connection.ping()
        return connection
    except Exception as exc:  # noqa: BLE001 - frontière d'infrastructure
        raise RedisUnavailable("Redis configuré mais indisponible") from exc


def _get_queue(redis_conn: Any) -> Any:
    """Construit la queue RQ dédiée ou lève, sans basculer silencieusement en sync."""
    try:
        from rq import Queue  # type: ignore[import-not-found]

        return Queue("pdf-generation", connection=redis_conn)
    except Exception as exc:  # noqa: BLE001 - frontière d'infrastructure
        raise RedisUnavailable("RQ indisponible") from exc


def _job_metadata(
    report_id: str,
    simulation_id: str,
    variant: str,
    lang: str,
    branding_id: Optional[str],
    input_digest: str,
) -> dict[str, str]:
    return {
        "report_id": report_id,
        "simulation_id": simulation_id,
        "variant": variant,
        "lang": lang,
        "branding_id": branding_id or "",
        "input_digest": input_digest,
        "job_version": _JOB_VERSION,
    }


def _job_id(metadata: dict[str, str]) -> str:
    payload = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"pdf-{hashlib.sha256(payload).hexdigest()[:32]}"


def _render_input_digest(
    report_id: str,
    simulation_id: str,
    variant: str,
    lang: str,
    branding_id: Optional[str],
) -> str:
    """Empreinte le contexte durable et le branding effectivement rendus."""
    from app.services.report_pdf.loader import PDFContextLoader

    context = PDFContextLoader.load(
        report_id=report_id,
        simulation_id=simulation_id,
        lang=lang,
    )
    branding: Optional[dict[str, Any]] = None
    if branding_id:
        try:
            from app.workers.pdf_generation_worker import _load_branding

            branding = _load_branding(branding_id)
        except Exception:  # noqa: BLE001 - identique au fallback du worker
            logger.warning("Branding PDF indisponible pour l'empreinte ; défaut utilisé", exc_info=True)

    canonical = json.dumps(
        {
            "context": context.model_dump(mode="json"),
            "branding": branding or {},
            "variant": variant,
            "template_version": _JOB_VERSION,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _validated_ids(report_id: str, simulation_id: str) -> bool:
    return bool(_REPORT_ID_RE.fullmatch(report_id) and _SIMULATION_ID_RE.fullmatch(simulation_id))


def _get_existing_job(redis_conn: Any, job_id: str, metadata: dict[str, str]) -> Any:
    """Retourne uniquement le job identique ; un ID connu ne suffit jamais seul."""
    try:
        from rq.job import Job  # type: ignore[import-not-found]

        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:  # noqa: BLE001 - absence normale après expiration TTL
        return None
    return job if getattr(job, "meta", {}) == metadata else None


def _lock_key(job_id: str) -> str:
    return f"pdf-generation:enqueue:{job_id}"


def _claim_enqueue_lock(redis_conn: Any, job_id: str) -> bool:
    """Acquiert le verrou Redis court qui sérialise les enqueue concurrents."""
    return bool(redis_conn.set(_lock_key(job_id), job_id, nx=True, ex=_ENQUEUE_LOCK_TTL_SECONDS))


def _release_enqueue_lock(redis_conn: Any, job_id: str) -> None:
    """Libère seulement le verrou qui porte encore la valeur de ce processus."""
    key = _lock_key(job_id)
    try:
        with redis_conn.pipeline() as pipeline:
            while True:
                try:
                    pipeline.watch(key)
                    value = pipeline.get(key)
                    if value == job_id or value == job_id.encode("utf-8"):
                        pipeline.multi()
                        pipeline.delete(key)
                        pipeline.execute()
                    pipeline.unwatch()
                    return
                except Exception as exc:  # WatchError uniquement, sans dépendance de type Redis
                    if exc.__class__.__name__ != "WatchError":
                        raise
    except Exception:  # noqa: BLE001 - le TTL nettoie le verrou si Redis devient indisponible
        logger.warning("Libération du verrou PDF différée job=%s", job_id, exc_info=True)


def _job_status(redis_conn: Any, job_id: str, report_id: str) -> dict[str, Optional[str]]:
    """Retourne un statut sûr, lié au rapport demandé et sans détail interne."""
    try:
        from rq.job import Job  # type: ignore[import-not-found]

        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:  # noqa: BLE001 - ne pas divulguer le backend Redis/RQ
        return {"status": "missing", "error_code": "JOB_NOT_FOUND"}

    if getattr(job, "meta", {}).get("report_id") != report_id:
        return {"status": "missing", "error_code": "JOB_NOT_FOUND"}

    status = job.get_status()
    status_str = str(status.value) if hasattr(status, "value") else str(status)
    if status_str == "failed":
        return {"status": status_str, "error_code": "PDF_GENERATION_FAILED"}
    return {"status": status_str, "error_code": None}


def _error(error_code: str, message: str, status: int) -> ResponseReturnValue:
    return jsonify({"success": False, "error_code": error_code, "error": message}), status


@pdf_generation_bp.route("/<report_id>/preview", methods=["POST"])
@require_auth
@require_super_admin
def preview_report(report_id: str) -> ResponseReturnValue:
    """Génère la couverture immédiatement ; une preview n'est jamais mise en queue."""
    data: dict[str, Any] = request.get_json(silent=True) or {}
    simulation_id = str(data.get("simulation_id", ""))
    if not simulation_id:
        return _error("MISSING_SIMULATION_ID", "simulation_id est requis.", 400)
    if not _validated_ids(report_id, simulation_id):
        return _error("INVALID_REPORT_INPUT", "Identifiants de rapport invalides.", 400)

    lang = str(data.get("lang", "fr"))
    branding_id = data.get("branding_id") or None
    try:
        input_digest = _render_input_digest(
            report_id, simulation_id, "one-pager", lang, branding_id
        )
    except Exception:  # noqa: BLE001 - contexte durable indisponible
        logger.exception("Contexte de preview PDF indisponible report=%s", report_id)
        return _error("PDF_INPUT_UNAVAILABLE", "Les données du rapport sont indisponibles.", 503)

    from app.workers.pdf_generation_worker import generate_pdf_job

    try:
        metadata = _job_metadata(
            report_id, simulation_id, "one-pager", lang, branding_id, input_digest
        )
        result = generate_pdf_job(
            report_id=report_id,
            simulation_id=simulation_id,
            variant="one-pager",
            lang=lang,
            branding_id=branding_id,
            job_id=_job_id(metadata),
        )
        from pathlib import Path

        pdf_bytes = Path(result["pdf_path"]).read_bytes()
    except Exception:  # noqa: BLE001 - le détail ne doit pas sortir de l'API admin
        logger.exception("Échec de la preview PDF report=%s", report_id)
        return _error("PREVIEW_FAILED", "La preview PDF n'a pas pu être générée.", 500)

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="preview_{report_id}.pdf"',
            "X-Report-Id": report_id,
        },
    )


@pdf_generation_bp.route("/<report_id>/generate", methods=["POST"])
@require_auth
@require_super_admin
def generate_report(report_id: str) -> ResponseReturnValue:
    """Enqueue une génération durable ; le sync n'est autorisé que sans REDIS_URL."""
    data: dict[str, Any] = request.get_json(silent=True) or {}
    simulation_id = str(data.get("simulation_id", ""))
    variant = str(data.get("variant", "full"))
    lang = str(data.get("lang", "fr"))
    branding_id = data.get("branding_id") or None

    if not simulation_id:
        return _error("MISSING_SIMULATION_ID", "simulation_id est requis.", 400)
    if variant not in _VALID_VARIANTS:
        return _error("INVALID_VARIANT", "variant est invalide.", 400)
    if not _validated_ids(report_id, simulation_id):
        return _error("INVALID_REPORT_INPUT", "Identifiants de rapport invalides.", 400)

    try:
        input_digest = _render_input_digest(
            report_id, simulation_id, variant, lang, branding_id
        )
    except Exception:  # noqa: BLE001 - contexte durable indisponible
        logger.exception("Contexte de génération PDF indisponible report=%s", report_id)
        return _error("PDF_INPUT_UNAVAILABLE", "Les données du rapport sont indisponibles.", 503)

    metadata = _job_metadata(
        report_id, simulation_id, variant, lang, branding_id, input_digest
    )
    job_id = _job_id(metadata)

    if not _redis_url():
        logger.warning("REDIS_URL absente : fallback PDF synchrone report=%s", report_id)
        from app.workers.pdf_generation_worker import generate_pdf_job

        try:
            generate_pdf_job(
                report_id=report_id,
                simulation_id=simulation_id,
                variant=variant,
                lang=lang,
                branding_id=branding_id,
                job_id=job_id,
            )
        except Exception:  # noqa: BLE001 - le détail est journalisé, pas exposé
            logger.exception("Échec PDF synchrone report=%s job=%s", report_id, job_id)
            return _error("PDF_GENERATION_FAILED", "La génération PDF a échoué.", 500)
        return jsonify({"success": True, "job_id": job_id, "status": "finished", "mode": "sync"}), 200

    try:
        redis_conn = _get_redis_connection()
        existing_job = _get_existing_job(redis_conn, job_id, metadata)
        if existing_job is None:
            if not _claim_enqueue_lock(redis_conn, job_id):
                existing_job = _get_existing_job(redis_conn, job_id, metadata)
                if existing_job is not None:
                    job = existing_job
                else:
                    # Un autre processus vient d'acquérir le verrou : même ID, aucun double render.
                    return jsonify(
                        {
                            "success": True,
                            "job_id": job_id,
                            "status_url": f"/api/admin/reports/{report_id}/jobs/{job_id}",
                            "mode": "async",
                        }
                    ), 202
            else:
                try:
                    existing_job = _get_existing_job(redis_conn, job_id, metadata)
                    if existing_job is not None:
                        job = existing_job
                    else:
                        queue = _get_queue(redis_conn)
                        from rq import Retry  # type: ignore[import-not-found]
                        from app.workers.pdf_generation_worker import generate_pdf_job

                        job = queue.enqueue_call(
                            generate_pdf_job,
                            kwargs={
                                "report_id": report_id,
                                "simulation_id": simulation_id,
                                "variant": variant,
                                "lang": lang,
                                "branding_id": branding_id,
                            },
                            timeout=300,
                            result_ttl=_JOB_TTL_SECONDS,
                            failure_ttl=_JOB_TTL_SECONDS,
                            job_id=job_id,
                            meta=metadata,
                            retry=Retry(max=2, interval=[30, 120]),
                        )
                except Exception:
                    existing_job = _get_existing_job(redis_conn, job_id, metadata)
                    if existing_job is not None:
                        job = existing_job
                    else:
                        raise
                finally:
                    _release_enqueue_lock(redis_conn, job_id)
        else:
            job = existing_job
    except RedisUnavailable:
        logger.warning("Redis/RQ indisponible pour report=%s", report_id, exc_info=True)
        return _error("REDIS_UNAVAILABLE", "Le service de génération asynchrone est indisponible.", 503)
    except Exception:  # noqa: BLE001 - enqueue peut échouer après le ping
        logger.exception("Échec enqueue PDF report=%s", report_id)
        return _error("PDF_QUEUE_UNAVAILABLE", "Le service de génération asynchrone est indisponible.", 503)

    return jsonify(
        {
            "success": True,
            "job_id": job.id,
            "status_url": f"/api/admin/reports/{report_id}/jobs/{job.id}",
            "mode": "async",
        }
    ), 202


@pdf_generation_bp.route("/<report_id>/jobs/<job_id>", methods=["GET"])
@require_auth
@require_super_admin
def get_job_status(report_id: str, job_id: str) -> ResponseReturnValue:
    """Expose le seul statut sûr du job, jamais ses chemins ou traces internes."""
    if not _redis_url():
        return _error("REDIS_UNAVAILABLE", "Le statut synchrone n'est pas conservé.", 503)
    try:
        status_data = _job_status(_get_redis_connection(), job_id, report_id)
    except RedisUnavailable:
        return _error("REDIS_UNAVAILABLE", "Le service de génération asynchrone est indisponible.", 503)

    if status_data["status"] == "missing":
        return _error("JOB_NOT_FOUND", "Job introuvable.", 404)
    return jsonify({"job_id": job_id, **status_data}), 200
