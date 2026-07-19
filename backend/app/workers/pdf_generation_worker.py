"""Tâche RQ durable de génération PDF (US-208)."""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Optional, cast

logger = logging.getLogger("miroshark.pdf_worker")

_PDF_CACHE: dict[tuple[str, ...], tuple[str, float]] = {}
_CACHE_TTL_SECONDS = 24 * 3600
_TEMPLATE_VERSION = "1.0.0"


def _cache_key(
    simulation_id: str,
    report_id: str,
    branding_id: Optional[str],
    variant: str,
    lang: str,
    job_id: str,
) -> tuple[str, ...]:
    return (
        simulation_id,
        report_id,
        branding_id or "default",
        _TEMPLATE_VERSION,
        variant,
        lang,
        job_id,
    )


def _cache_get(key: tuple[str, ...]) -> Optional[str]:
    entry = _PDF_CACHE.get(key)
    if entry is None:
        return None
    pdf_path, created_at = entry
    if time.time() - created_at > _CACHE_TTL_SECONDS or not Path(pdf_path).is_file():
        del _PDF_CACHE[key]
        return None
    return pdf_path


def _cache_set(key: tuple[str, ...], pdf_path: str) -> None:
    _PDF_CACHE[key] = (pdf_path, time.time())


def _artifact_path(job_id: str, base_dir: Optional[Path]) -> Path:
    root = base_dir or (Path(__file__).resolve().parents[2] / "uploads" / "pdf_jobs")
    return root / f"{job_id}.pdf"


def _local_job_id(
    report_id: str,
    simulation_id: str,
    branding_id: Optional[str],
    variant: str,
    lang: str,
) -> str:
    payload = "\x1f".join(
        (report_id, simulation_id, branding_id or "default", _TEMPLATE_VERSION, variant, lang)
    ).encode("utf-8")
    return f"sync-{hashlib.sha256(payload).hexdigest()[:32]}"


def _write_artifact(path: Path, pdf_bytes: bytes) -> None:
    """Écrit l'artefact du job atomiquement : un retry ne lit jamais un PDF partiel."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(pdf_bytes)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _gs_compress(pdf_path: Path) -> None:
    """Conserve la compression Ghostscript historique sans rendre le job fragile."""
    try:
        if subprocess.run(["gs", "--version"], capture_output=True, timeout=5).returncode:
            return
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return
    compressed = pdf_path.with_suffix(".tmp.pdf")
    try:
        subprocess.run(
            ["gs", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite", f"-sOutputFile={compressed}", str(pdf_path)],
            capture_output=True,
            check=True,
            timeout=60,
        )
        if compressed.is_file() and compressed.stat().st_size < pdf_path.stat().st_size:
            compressed.replace(pdf_path)
        else:
            compressed.unlink(missing_ok=True)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        compressed.unlink(missing_ok=True)
        logger.warning("Compression Ghostscript ignorée", exc_info=True)


def _fire_webhook(
    webhook_url: str,
    job_id: str,
    status: str,
    error_code: Optional[str] = None,
) -> None:
    try:
        import requests  # type: ignore[import-not-found]

        requests.post(
            webhook_url,
            json={"job_id": job_id, "status": status, "error_code": error_code},
            timeout=10,
        )
    except Exception:  # noqa: BLE001 - callback best-effort
        logger.warning("Webhook PDF ignoré", exc_info=True)


def _load_branding(branding_id: str) -> Optional[dict[str, Any]]:
    """Charge explicitement le branding demandé ; l'endpoint est super-admin only."""
    from app.auth.supabase_client import get_supabase_admin

    response = get_supabase_admin().table("pdf_branding").select("*").eq("id", branding_id).limit(1).execute()
    rows = getattr(response, "data", None) or []
    return rows[0] if rows and isinstance(rows[0], dict) else None


def generate_pdf_job(
    report_id: str,
    simulation_id: str,
    variant: str = "full",
    lang: str = "fr",
    branding_id: Optional[str] = None,
    *,
    job_id: Optional[str] = None,
    _rep_base_dir: Optional[str] = None,
    _sim_base_dir: Optional[str] = None,
    _artifact_base_dir: Optional[str] = None,
) -> dict[str, Any]:
    """Rend un PDF de travail ; les échecs remontent à RQ pour retry/failed."""
    if job_id is None:
        try:
            from rq import get_current_job  # type: ignore[import-not-found]

            current_job = get_current_job()
            job_id = current_job.id if current_job else _local_job_id(
                report_id, simulation_id, branding_id, variant, lang
            )
        except Exception:  # noqa: BLE001 - exécution locale sans RQ
            job_id = _local_job_id(report_id, simulation_id, branding_id, variant, lang)

    key = _cache_key(simulation_id, report_id, branding_id, variant, lang, job_id)
    cached_path = _cache_get(key)
    if cached_path:
        return {"job_id": job_id, "status": "finished", "pdf_path": cached_path, "from_cache": True}

    artifact_base_dir = Path(_artifact_base_dir) if _artifact_base_dir else None
    pdf_path = _artifact_path(job_id, artifact_base_dir)
    if pdf_path.is_file():
        _cache_set(key, str(pdf_path))
        return {"job_id": job_id, "status": "finished", "pdf_path": str(pdf_path), "from_cache": True}

    webhook_url = os.environ.get("PDF_GENERATION_WEBHOOK_URL", "")
    try:
        from app.services.report_pdf.charts import ChartFactory
        from app.services.report_pdf.loader import PDFContextLoader
        from app.services.report_pdf.renderer import Renderer

        loader_kwargs: dict[str, Any] = {
            "simulation_id": simulation_id,
            "report_id": report_id,
            "lang": lang,
        }
        if _sim_base_dir:
            loader_kwargs["sim_base_dir"] = Path(_sim_base_dir)
        if _rep_base_dir:
            loader_kwargs["rep_base_dir"] = Path(_rep_base_dir)
        context = PDFContextLoader.load(**loader_kwargs)

        branding: Optional[dict[str, Any]] = None
        if branding_id:
            try:
                branding = _load_branding(branding_id)
            except Exception:  # noqa: BLE001 - comportement historique : branding default
                logger.warning("Branding PDF indisponible ; défaut utilisé", exc_info=True)

        charts_factory = ChartFactory(context)
        renderer = Renderer(context, branding=branding, charts_factory=charts_factory)
        pdf_bytes = renderer.render_pdf(charts_factory=charts_factory, variant=cast(Any, variant))
        _write_artifact(pdf_path, pdf_bytes)
        _gs_compress(pdf_path)
        _cache_set(key, str(pdf_path))
    except Exception:
        logger.exception("Échec PDF job=%s report=%s", job_id, report_id)
        if webhook_url:
            _fire_webhook(webhook_url, job_id, "failed", "PDF_GENERATION_FAILED")
        raise

    if webhook_url:
        _fire_webhook(webhook_url, job_id, "finished")
    return {"job_id": job_id, "status": "finished", "pdf_path": str(pdf_path), "from_cache": False}
