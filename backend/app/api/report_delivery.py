"""Endpoints livraison de rapports (US-130).

Blueprint ``report_delivery_bp`` — routes :

  POST /api/admin/reports/<id>/deliver
    - super-admin only
    - Body : {recipient_email, recipient_name, expiry_days=7, language='fr'}
    - Crée une delivery + envoie l'email

  GET  /r/<token>
    - Public, sans auth
    - Valide le token, journalise le téléchargement (CF-IPCountry), stream PDF

  GET  /api/admin/reports/<id>/deliveries
    - super-admin OR org admin
    - Liste les deliveries

  GET  /api/admin/reports/<id>/deliveries/<delivery_id>/downloads
    - tracking des téléchargements

  POST /api/admin/reports/<id>/deliveries/<delivery_id>/resend
    - Invalide ancien token + envoie nouveau email

Les routes /api/admin/… sont montées via admin_reports_bp dans __init__.py.
La route /r/<token> est un blueprint séparé (public) monté sans préfixe.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Blueprint, Response, g, jsonify, request, stream_with_context

from ..auth.decorators import is_super_admin_email, require_auth
from ..auth.supabase_client import SupabaseConfigError, get_supabase_admin, get_user_orgs
from ..services import report_delivery as rd


logger = logging.getLogger("miroshark.api.report_delivery")


# ─── Blueprint admin (monté sur /api/admin/reports via admin_reports_bp) ─────

report_delivery_admin_bp = Blueprint("report_delivery_admin", __name__)

# ─── Blueprint public (monté sur / pour les liens /r/<token>) ─────────────

report_delivery_public_bp = Blueprint("report_delivery_public", __name__)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _err(code: str, message: str, status: int):
    return jsonify({"success": False, "error_code": code, "error": message}), status


def _get_current_user() -> Dict[str, Any]:
    return getattr(g, "current_user", None) or {}


def _check_report_access_delivery(report_id: str):
    """Vérifie accès admin (super-admin ou org admin) au rapport.

    Returns (None, error_response) ou (user_info, None).
    """
    user = _get_current_user()
    email = user.get("email")
    user_id = user.get("id")

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return None, _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase not configured.", 503)

    # Super-admin : accès libre
    if is_super_admin_email(email):
        return user, None

    # Org admin : vérifier appartenance à l'org du rapport
    if not user_id:
        return None, _err("INVALID_TOKEN", "Token missing 'sub' claim.", 401)

    # Récupérer l'org_id du rapport
    try:
        resp = cli.table("report_states").select("org_id").eq("report_id", report_id).execute()
        rows = resp.data or []
    except Exception as exc:  # noqa: BLE001
        logger.error("report_states query failed: %s", exc.__class__.__name__)
        return None, _err("INTERNAL_ERROR", "Could not resolve report organization.", 500)

    if not rows:
        return None, _err("REPORT_NOT_FOUND", "Report not found or not accessible.", 404)

    report_org_id = str(rows[0].get("org_id") or "")

    try:
        user_orgs = get_user_orgs(user_id)
    except SupabaseConfigError:
        return None, _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase not configured.", 503)
    except Exception as exc:  # noqa: BLE001
        logger.error("get_user_orgs failed: %s", exc.__class__.__name__)
        return None, _err("INTERNAL_AUTH_ERROR", "Could not resolve user organizations.", 500)

    eligible = [
        o for o in user_orgs
        if o.get("role") in {"owner", "admin"} and str(o.get("id") or "") == report_org_id
    ]
    if not eligible:
        return None, _err("ACCESS_DENIED", "You do not have admin access to this report.", 403)

    return user, None


def _snapshot_pdf_path(report_id: str, version: int) -> Optional[Path]:
    """Retourne le chemin vers full.pdf du snapshot, ou None si introuvable."""
    base = Path(os.environ.get("BASSIRA_SNAPSHOTS_DIR", "uploads/report_snapshots"))
    pdf = base / report_id / f"v{version}" / "full.pdf"
    if pdf.exists():
        return pdf
    # Essai depuis backend/
    alt_base = Path(__file__).resolve().parent.parent.parent / "uploads" / "report_snapshots"
    alt_pdf = alt_base / report_id / f"v{version}" / "full.pdf"
    return alt_pdf if alt_pdf.exists() else None


# ─── POST /api/admin/reports/<report_id>/deliver ─────────────────────────────


@report_delivery_admin_bp.route("/<report_id>/deliver", methods=["POST"])
@require_auth
def create_delivery_endpoint(report_id: str):
    """Crée une livraison et envoie l'email Resend (super-admin uniquement).

    Body JSON :
        {
          "recipient_email": "client@example.com",
          "recipient_name":  "Jean Dupont",
          "expiry_days":     7,
          "language":        "fr",
          "report_title":    "Rapport Stratégique Q1 2026"
        }

    Response :
        { "success": true, "data": { ... delivery row ... } }
    """
    user = _get_current_user()
    email = user.get("email")
    if not is_super_admin_email(email):
        return _err("FORBIDDEN", "Super-admin access required.", 403)

    body = request.get_json(silent=True) or {}
    recipient_email = (body.get("recipient_email") or "").strip()
    recipient_name  = (body.get("recipient_name") or "").strip()
    expiry_days     = int(body.get("expiry_days", 7))
    language        = (body.get("language") or "fr").strip().lower()
    report_title    = body.get("report_title")

    if not recipient_email:
        return _err("INVALID_BODY", "Field `recipient_email` is required.", 400)
    if language not in {"fr", "en", "ar"}:
        language = "fr"
    expiry_days = max(1, min(expiry_days, 90))

    # Déterminer la version courante du rapport depuis report_states
    try:
        cli = get_supabase_admin()
        resp = cli.table("report_states").select("current_version").eq("report_id", report_id).execute()
        rows = resp.data or []
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase not configured.", 503)
    except Exception as exc:  # noqa: BLE001
        logger.error("report_states query: %s", exc.__class__.__name__)
        return _err("INTERNAL_ERROR", "Could not resolve report version.", 500)

    if not rows:
        return _err("REPORT_NOT_FOUND", "Report not found.", 404)

    version = int(rows[0].get("current_version") or 1)
    sent_by = user.get("id")

    try:
        delivery = rd.create_delivery(
            report_id,
            version,
            recipient_email,
            recipient_name,
            expiry_days=expiry_days,
            language=language,
            sent_by=sent_by,
            report_title=report_title,
            client=cli,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("create_delivery failed: %s — %s", exc.__class__.__name__, exc)
        return _err("DELIVERY_FAILED", "Could not create delivery.", 500)

    return jsonify({"success": True, "data": delivery}), 201


# ─── GET /api/admin/reports/<report_id>/deliveries ───────────────────────────


@report_delivery_admin_bp.route("/<report_id>/deliveries", methods=["GET"])
@require_auth
def list_deliveries_endpoint(report_id: str):
    """Liste toutes les livraisons d'un rapport (super-admin ou org admin)."""
    _user, err = _check_report_access_delivery(report_id)
    if err is not None:
        return err

    try:
        cli = get_supabase_admin()
        deliveries = rd.list_deliveries(report_id, client=cli)
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase not configured.", 503)
    except Exception as exc:  # noqa: BLE001
        logger.error("list_deliveries failed: %s", exc.__class__.__name__)
        return _err("INTERNAL_ERROR", "Could not list deliveries.", 500)

    return jsonify({"success": True, "data": {"deliveries": deliveries}}), 200


# ─── GET /api/admin/reports/<report_id>/deliveries/<delivery_id>/downloads ────


@report_delivery_admin_bp.route("/<report_id>/deliveries/<delivery_id>/downloads", methods=["GET"])
@require_auth
def list_downloads_endpoint(report_id: str, delivery_id: str):
    """Retourne le tracking téléchargements d'une livraison."""
    _user, err = _check_report_access_delivery(report_id)
    if err is not None:
        return err

    try:
        cli = get_supabase_admin()
        downloads = rd.list_downloads(delivery_id, client=cli)
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase not configured.", 503)
    except Exception as exc:  # noqa: BLE001
        logger.error("list_downloads failed: %s", exc.__class__.__name__)
        return _err("INTERNAL_ERROR", "Could not list downloads.", 500)

    return jsonify({"success": True, "data": {"downloads": downloads}}), 200


# ─── POST /api/admin/reports/<report_id>/deliveries/<delivery_id>/resend ─────


@report_delivery_admin_bp.route("/<report_id>/deliveries/<delivery_id>/resend", methods=["POST"])
@require_auth
def resend_delivery_endpoint(report_id: str, delivery_id: str):
    """Invalide l'ancien token et envoie un nouveau lien (super-admin uniquement)."""
    user = _get_current_user()
    email = user.get("email")
    if not is_super_admin_email(email):
        return _err("FORBIDDEN", "Super-admin access required.", 403)

    body = request.get_json(silent=True) or {}
    expiry_days  = int(body.get("expiry_days", 7))
    report_title = body.get("report_title")
    expiry_days  = max(1, min(expiry_days, 90))

    try:
        cli = get_supabase_admin()
        delivery = rd.re_send_link(delivery_id, expiry_days=expiry_days, report_title=report_title, client=cli)
    except ValueError as exc:
        return _err("NOT_FOUND", str(exc), 404)
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase not configured.", 503)
    except Exception as exc:  # noqa: BLE001
        logger.error("re_send_link failed: %s — %s", exc.__class__.__name__, exc)
        return _err("RESEND_FAILED", "Could not re-send delivery.", 500)

    return jsonify({"success": True, "data": delivery}), 200


# ─── GET /r/<token> — route publique ─────────────────────────────────────────


@report_delivery_public_bp.route("/r/<token>", methods=["GET"])
def download_report(token: str):
    """Valide le token signé et stream le PDF du rapport.

    Headers lus :
        CF-IPCountry   : code pays ISO 3166-1 alpha-2 (Cloudflare)
        X-Forwarded-For: IP réelle du client
        User-Agent     : navigateur/OS du client
        Referer        : page source du lien

    Response :
        - 200 : application/pdf avec Content-Disposition: attachment
        - 404 : token invalide ou expiré
        - 404 : snapshot PDF introuvable
    """
    payload = rd.verify_signing_token(token)
    if payload is None:
        return jsonify({
            "success": False,
            "error_code": "TOKEN_INVALID_OR_EXPIRED",
            "error": "Ce lien de téléchargement est invalide ou a expiré.",
        }), 404

    report_id = payload["rid"]
    version   = payload["ver"]

    # Retrouver la livraison par token pour logger le download
    delivery_id: Optional[str] = None
    try:
        cli = get_supabase_admin()
        resp = cli.table("report_deliveries").select("id").eq("signing_token", token).execute()
        rows = resp.data or []
        if rows:
            delivery_id = rows[0]["id"]
    except Exception:  # noqa: BLE001
        pass  # Ne pas bloquer le téléchargement pour un échec de lookup

    # IP + géo
    ip          = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    # CF-IPCountry est injecté par Cloudflare (2 lettres ISO ou "XX")
    country     = request.headers.get("CF-IPCountry", "")
    ua          = request.headers.get("User-Agent", "")
    referer     = request.headers.get("Referer", "")

    # Journaliser le download (best-effort)
    if delivery_id:
        try:
            rd.log_download(
                delivery_id,
                ip       or None,
                ua       or None,
                country  or None,
                referer  = referer or None,
            )
        except Exception:  # noqa: BLE001
            pass

    # Charger le PDF depuis le snapshot
    pdf_path = _snapshot_pdf_path(report_id, version)
    if pdf_path is None:
        logger.warning("PDF introuvable pour report_id=%s version=%d", report_id, version)
        return jsonify({
            "success": False,
            "error_code": "PDF_NOT_FOUND",
            "error": "Le fichier PDF de ce rapport est introuvable.",
        }), 404

    # Stream du fichier PDF
    def _stream_pdf():
        with open(pdf_path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                yield chunk

    safe_name = f"rapport-bassira-{report_id[:8]}-v{version}.pdf"
    return Response(
        stream_with_context(_stream_pdf()),
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Content-Length":      str(pdf_path.stat().st_size),
            "Cache-Control":       "no-store, no-cache",
            "X-Robots-Tag":        "noindex",
        },
    )
