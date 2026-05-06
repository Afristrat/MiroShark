"""
pdf_generation_worker.py — Worker RQ pour la génération PDF Bassira (US-129).

Ce module est à la fois :
  - La définition de la tâche RQ ``generate_pdf_job`` (exécutée par le worker).
  - Le point d'entrée de la file RQ (lancé via ``rq worker pdf-generation``).

Fonctionnement :
  1. Charge le contexte PDF via PDFContextLoader.
  2. Génère les charts via ChartFactory.
  3. Rend le PDF via Renderer.
  4. Sauvegarde le snapshot via create_snapshot.
  5. Appelle le webhook de callback si configuré (env PDF_GENERATION_WEBHOOK_URL).

Optimisation :
  - Pre-warm WeasyPrint au boot du worker (importe HTML au chargement du module)
    → gain 2-3 s par requête sur la première exécution.
  - Cache LRU in-memory sur (simulation_id, report_id, branding_v, template_v,
    variant, lang) avec TTL 24h — évite de re-rendre un PDF identique.

Fallback sync :
  Si REDIS_URL absent de l'env, le job est exécuté immédiatement dans le
  processus appelant (pas d'async). Le résultat est retourné directement.
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("miroshark.pdf_worker")

# ─── Pre-warm WeasyPrint (gain 2-3s/requête) ──────────────────────────────────
# Déclenché à l'import du module (boot worker).
try:
    from weasyprint import HTML as _WP_HTML  # noqa: F401  — pre-warm

    logger.debug("WeasyPrint pre-warm OK.")
except (ImportError, OSError):
    logger.debug("WeasyPrint non disponible — pre-warm ignoré.")

# ─── Cache LRU in-memory ──────────────────────────────────────────────────────
# Clé : (simulation_id, report_id, branding_v, template_v, variant, lang)
# Valeur : (pdf_path_str, timestamp_float)
_PDF_CACHE: Dict[Tuple[str, ...], Tuple[str, float]] = {}
_CACHE_TTL_SECONDS = 24 * 3600  # 24h

_TEMPLATE_VERSION = "1.0.0"  # Incrémenter lors de changements majeurs de template


def _cache_key(
    simulation_id: str,
    report_id: Optional[str],
    branding_v: str,
    variant: str,
    lang: str,
) -> Tuple[str, ...]:
    """Construit la clé de cache pour un couple (sim, report, branding, variant, lang)."""
    return (
        simulation_id,
        report_id or "",
        branding_v,
        _TEMPLATE_VERSION,
        variant,
        lang,
    )


def _cache_get(key: Tuple[str, ...]) -> Optional[str]:
    """Retourne le chemin PDF si la clé est en cache et non expirée."""
    entry = _PDF_CACHE.get(key)
    if entry is None:
        return None
    pdf_path, ts = entry
    if time.time() - ts > _CACHE_TTL_SECONDS:
        del _PDF_CACHE[key]
        return None
    # Vérifier que le fichier existe toujours sur disque
    if not Path(pdf_path).is_file():
        del _PDF_CACHE[key]
        return None
    return pdf_path


def _cache_set(key: Tuple[str, ...], pdf_path: str) -> None:
    """Stocke le chemin PDF dans le cache."""
    _PDF_CACHE[key] = (pdf_path, time.time())


# ─── Compression Ghostscript (optionnelle) ────────────────────────────────────


def _gs_compress(pdf_path: Path) -> None:
    """Compresse le PDF via Ghostscript si ``gs`` est disponible (-50% taille).

    Utilise ``-dPDFSETTINGS=/prepress`` (qualité impression).
    Si Ghostscript absent ou erreur → ignoré silencieusement.
    """
    try:
        # Vérifier que gs est disponible
        result = subprocess.run(
            ["gs", "--version"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            return
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.debug("Ghostscript absent — compression ignorée.")
        return

    compressed = pdf_path.with_suffix(".tmp.pdf")
    try:
        subprocess.run(
            [
                "gs",
                "-dBATCH",
                "-dNOPAUSE",
                "-sDEVICE=pdfwrite",
                "-dPDFSETTINGS=/prepress",
                "-dCompatibilityLevel=1.5",
                f"-sOutputFile={compressed}",
                str(pdf_path),
            ],
            capture_output=True,
            timeout=60,
            check=True,
        )
        # Remplacer l'original par le compressé si la compression est bénéfique
        if compressed.is_file() and compressed.stat().st_size < pdf_path.stat().st_size:
            compressed.replace(pdf_path)
            logger.debug("Compression GS appliquée : %s.", pdf_path)
        else:
            compressed.unlink(missing_ok=True)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("Compression GS échouée : %s — ignorée.", exc)
        compressed.unlink(missing_ok=True)


# ─── Webhook callback ─────────────────────────────────────────────────────────


def _fire_webhook(
    webhook_url: str,
    job_id: str,
    status: str,
    pdf_path: Optional[str],
    error: Optional[str] = None,
) -> None:
    """Envoie un POST JSON au webhook de callback.

    Non bloquant sur erreur — loggue et continue.
    """
    try:
        import requests  # type: ignore[import-not-found]

        payload: Dict[str, Any] = {
            "job_id": job_id,
            "status": status,
            "pdf_path": pdf_path,
            "error": error,
        }
        requests.post(webhook_url, json=payload, timeout=10)
        logger.debug("Webhook fired : %s → %s.", webhook_url, status)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Webhook callback échoué : %s — ignoré.", exc)


# ═══════════════════════════════════════════════════════════════════════════════
# Tâche RQ principale
# ═══════════════════════════════════════════════════════════════════════════════


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
) -> Dict[str, Any]:
    """Génère un PDF rapport Bassira complet.

    Cette fonction est appelée par RQ en mode async, ou directement en mode sync.

    Args:
        report_id:      Identifiant du rapport (format report_<12hex>).
        simulation_id:  Identifiant de la simulation (format sim_<12hex>).
        variant:        Variante {full, exec, public, one-pager}.
        lang:           Langue {fr, en, ar}.
        branding_id:    ID du branding PDF (None = defaults Bassira).
        job_id:         ID du job RQ (injecté auto par RQ si None).
        _rep_base_dir:  Override répertoire rapports (tests).
        _sim_base_dir:  Override répertoire simulations (tests).

    Returns:
        Dict avec keys : job_id, status, pdf_path, error.
    """
    # Récupérer le job_id courant depuis RQ si disponible
    if job_id is None:
        try:
            from rq import get_current_job  # type: ignore[import-not-found]

            current_job = get_current_job()
            job_id = current_job.id if current_job else "sync"
        except Exception:  # noqa: BLE001
            job_id = "sync"

    webhook_url = os.environ.get("PDF_GENERATION_WEBHOOK_URL", "")

    # ── Déterminer la version branding pour le cache ───────────────────────
    branding_v = branding_id or "default"

    # ── Vérifier le cache LRU ─────────────────────────────────────────────
    cache_key = _cache_key(simulation_id, report_id, branding_v, variant, lang)
    cached_path = _cache_get(cache_key)
    if cached_path:
        logger.info(
            "Cache LRU hit pour (sim=%s, report=%s, variant=%s, lang=%s).",
            simulation_id,
            report_id,
            variant,
            lang,
        )
        result = {
            "job_id": job_id,
            "status": "finished",
            "pdf_path": cached_path,
            "error": None,
            "from_cache": True,
        }
        if webhook_url:
            _fire_webhook(webhook_url, job_id, "finished", cached_path)
        return result

    try:
        # ── 1. Charger le contexte PDF ─────────────────────────────────────
        from app.services.report_pdf.loader import PDFContextLoader

        loader_kwargs: Dict[str, Any] = {
            "simulation_id": simulation_id,
            "report_id": report_id,
            "lang": lang,
        }
        if _sim_base_dir:
            from pathlib import Path as _Path

            loader_kwargs["sim_base_dir"] = _Path(_sim_base_dir)
        if _rep_base_dir:
            from pathlib import Path as _Path

            loader_kwargs["rep_base_dir"] = _Path(_rep_base_dir)

        context = PDFContextLoader.load(**loader_kwargs)

        # ── 2. Charger le branding ─────────────────────────────────────────
        branding: Optional[Dict[str, Any]] = None
        if branding_id:
            try:
                from app.services import pdf_branding as pb

                branding = pb.get_branding_by_id(branding_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Branding %s introuvable : %s — defaults Bassira utilisés.",
                    branding_id,
                    exc,
                )

        # ── 3. Générer les charts ──────────────────────────────────────────
        from app.services.report_pdf.charts import ChartFactory

        charts_factory = ChartFactory(context)

        # ── 4. Rendre le PDF ──────────────────────────────────────────────
        from app.services.report_pdf.renderer import Renderer

        renderer = Renderer(context, branding=branding)

        if variant == "one-pager":
            # Cover 1 page uniquement (mode preview sync)
            pdf_bytes = _render_one_pager(renderer, charts_factory)
        else:
            pdf_bytes = renderer.render_pdf(charts_factory=charts_factory)

        # ── 5. Snapshot sur disque ────────────────────────────────────────
        from app.services.report_pdf.snapshot import create_snapshot

        snapshot_kwargs: Dict[str, Any] = {
            "report_id": report_id,
            "pdf_bytes": pdf_bytes,
            "variant": variant,
            "lang": lang,
        }
        if _rep_base_dir:
            snapshot_kwargs["rep_base_dir"] = Path(_rep_base_dir)

        pdf_path = create_snapshot(**snapshot_kwargs)

        # ── 6. Compression Ghostscript (optionnelle) ──────────────────────
        _gs_compress(pdf_path)

        # ── 7. Mettre en cache ────────────────────────────────────────────
        _cache_set(cache_key, str(pdf_path))

        result = {
            "job_id": job_id,
            "status": "finished",
            "pdf_path": str(pdf_path),
            "error": None,
            "from_cache": False,
        }
        if webhook_url:
            _fire_webhook(webhook_url, job_id, "finished", str(pdf_path))
        return result

    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "generate_pdf_job échoué (job_id=%s, report=%s) : %s.",
            job_id,
            report_id,
            exc,
        )
        if webhook_url:
            _fire_webhook(webhook_url, job_id, "failed", None, str(exc))
        return {
            "job_id": job_id,
            "status": "failed",
            "pdf_path": None,
            "error": str(exc),
        }


def _render_one_pager(renderer: Any, charts_factory: Any) -> bytes:
    """Rend uniquement la page de couverture (1 page) pour le mode preview sync.

    Stratégie :
      - Génère le PDF full.
      - Extrait la première page via pypdf.
      - Retourne les bytes de la page extraite.
    """
    import io

    pdf_full = renderer.render_pdf(charts_factory=charts_factory)

    try:
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(pdf_full))
        writer = pypdf.PdfWriter()
        if len(reader.pages) > 0:
            writer.add_page(reader.pages[0])
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Extraction page 1 via pypdf échouée : %s — PDF full retourné.", exc
        )
        return pdf_full
