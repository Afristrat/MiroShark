"""Endpoints admin rapport workflow (US-126).

Blueprint ``admin_reports_bp`` monté sur ``/api/admin/reports``.

Routes :
  GET  /api/admin/reports/<report_id>/state      — état courant + audit log
  POST /api/admin/reports/<report_id>/transition — effectue une transition
  POST /api/admin/reports/<report_id>/lock       — acquiert le lock IN_REVIEW
  POST /api/admin/reports/<report_id>/unlock     — relâche le lock IN_REVIEW

Sécurité
────────
- Toutes les routes exigent @require_auth.
- Super-admin Bassira (is_super_admin_email) : accès à tous les reports.
- Org admin/owner : accès aux reports de son org uniquement.
- Service patterns : hérités de admin_branding.py (pattern _resolve_org_id).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from flask import Blueprint, g, jsonify, request

from ..auth.decorators import is_super_admin_email, require_auth
from ..auth.supabase_client import SupabaseConfigError, get_supabase_admin, get_user_orgs
from ..services import report_workflow as rw


logger = logging.getLogger("miroshark.api.admin_reports")

# Blueprint monté sur /api/admin/reports
admin_reports_bp = Blueprint("admin_reports", __name__)


# ─── Helpers ────────────────────────────────────────────────────────────────


def _err(code: str, message: str, status: int):
    return jsonify({
        "success": False,
        "error_code": code,
        "error": message,
    }), status


def _get_actor_info() -> tuple[str, str, str, str]:
    """Extrait actor_id, actor_email, ip et user_agent depuis la requête courante."""
    user = getattr(g, "current_user", None) or {}
    actor_id = user.get("id") or ""
    actor_email = user.get("email") or ""
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "") or ""
    ua = request.headers.get("User-Agent", "") or ""
    return actor_id, actor_email, ip, ua


def _check_report_access(report_id: str) -> tuple[Optional[Dict[str, Any]], Optional[Any]]:
    """Vérifie que l'utilisateur courant a accès au rapport.

    - Super-admin : accès universel.
    - Org admin/owner : doit appartenir à l'org du rapport.

    Returns:
        Tuple ``(state_row_or_None, error_response_or_None)``.
        Si error_response n'est pas None → retourner l'erreur.
    """
    user = getattr(g, "current_user", None) or {}
    email = user.get("email")
    user_id = user.get("id")

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return None, _err(
            "SUPABASE_NOT_CONFIGURED",
            "Backend Supabase admin client is not configured.",
            503,
        )

    state = rw.get_report_state(report_id, client=cli)

    # Super-admin : bypass, accès libre
    if is_super_admin_email(email):
        return state, None

    if not state:
        # Rapport introuvable → 404 générique (pas de leak d'existence)
        return None, _err("REPORT_NOT_FOUND", "Report not found or not accessible.", 404)

    # Org admin/owner : vérifier que le user appartient à l'org du rapport
    if not user_id:
        return None, _err("INVALID_TOKEN", "Token missing 'sub' claim.", 401)

    try:
        user_orgs = get_user_orgs(user_id)
    except SupabaseConfigError:
        return None, _err(
            "SUPABASE_NOT_CONFIGURED",
            "Backend Supabase admin client is not configured.",
            503,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("get_user_orgs failed: %s", exc.__class__.__name__)
        return None, _err("INTERNAL_AUTH_ERROR", "Could not resolve user organizations.", 500)

    report_org_id = str(state.get("org_id") or "")
    eligible = [
        o for o in user_orgs
        if o.get("role") in {"owner", "admin"} and str(o.get("id") or "") == report_org_id
    ]
    if not eligible:
        return None, _err(
            "ACCESS_DENIED",
            "You do not have admin access to this report's organization.",
            403,
        )

    return state, None


# ─── GET /api/admin/reports/<report_id>/state ────────────────────────────────


@admin_reports_bp.route("/<report_id>/state", methods=["GET"])
@require_auth
def get_report_state_endpoint(report_id: str):
    """Retourne l'état courant d'un rapport + les dernières entrées d'audit log.

    Query params :
        ``audit_limit`` — nombre de lignes d'audit log à inclure (défaut 20, max 50).

    Response :
        {
          "success": true,
          "data": {
            "state": "DRAFT",
            "current_version": 2,
            "locked_by": null,
            "last_transition_at": "...",
            "audit_log": [...]
          }
        }
    """
    state, err = _check_report_access(report_id)
    if err is not None:
        return err

    try:
        audit_limit = min(int(request.args.get("audit_limit", 20)), 50)
    except (TypeError, ValueError):
        audit_limit = 20

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase admin client is not configured.", 503)

    try:
        audit_log = rw.list_audit_log(report_id, limit=audit_limit, client=cli)
    except Exception as exc:  # noqa: BLE001
        logger.error("list_audit_log failed: %s", exc.__class__.__name__)
        audit_log = []

    return jsonify({
        "success": True,
        "data": {
            "report_id":          report_id,
            "state":              state.get("state") if state else None,
            "current_version":    state.get("current_version") if state else None,
            "locked_by":          state.get("locked_by") if state else None,
            "locked_at":          state.get("locked_at") if state else None,
            "last_transition_at": state.get("last_transition_at") if state else None,
            "org_id":             state.get("org_id") if state else None,
            "audit_log":          audit_log,
        },
    }), 200


# ─── POST /api/admin/reports/<report_id>/transition ──────────────────────────


@admin_reports_bp.route("/<report_id>/transition", methods=["POST"])
@require_auth
def transition_endpoint(report_id: str):
    """Effectue une transition d'état sur un rapport.

    Body JSON :
        { "to_state": "DRAFT", "comment": "..." }

    Response :
        { "success": true, "data": { "state": "DRAFT", ... } }

    Errors :
        - 400 INVALID_BODY
        - 409 ILLEGAL_TRANSITION
        - 423 REPORT_LOCKED
        - 403 ACCESS_DENIED
        - 404 REPORT_NOT_FOUND
    """
    body = request.get_json(silent=True) or {}
    to_state = body.get("to_state")
    if not isinstance(to_state, str) or not to_state.strip():
        return _err("INVALID_BODY", "Field `to_state` is required.", 400)
    to_state = to_state.strip().upper()

    comment = body.get("comment")

    state, err = _check_report_access(report_id)
    if err is not None:
        return err

    user = getattr(g, "current_user", None) or {}
    email = user.get("email")
    is_super = is_super_admin_email(email)

    actor_id, actor_email, ip, ua = _get_actor_info()

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase admin client is not configured.", 503)

    try:
        new_state = rw.transition(
            report_id,
            to_state=to_state,
            actor_id=actor_id,
            actor_email=actor_email,
            ip=ip,
            user_agent=ua,
            comment=comment,
            is_super_admin=is_super,
            client=cli,
        )
    except rw.IllegalTransitionError as exc:
        return _err("ILLEGAL_TRANSITION", str(exc), 409)
    except rw.LockedReportError as exc:
        return _err("REPORT_LOCKED", str(exc), 423)
    except rw.WorkflowError as exc:
        return _err("WORKFLOW_ERROR", str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        logger.error("transition failed: %s", exc.__class__.__name__)
        return _err("TRANSITION_FAILED", "Could not perform state transition.", 500)

    return jsonify({
        "success": True,
        "data": new_state,
    }), 200


# ─── POST /api/admin/reports/<report_id>/lock ────────────────────────────────


@admin_reports_bp.route("/<report_id>/lock", methods=["POST"])
@require_auth
def lock_endpoint(report_id: str):
    """Acquiert le lock IN_REVIEW sur un rapport.

    Permet à un reviewer d'indiquer qu'il travaille sur le rapport.
    Le lock est automatiquement relâché après LOCK_TIMEOUT_MIN minutes.

    Response :
        { "success": true, "data": { "locked": true, "locked_by": "uuid" } }

    Errors :
        - 423 LOCK_CONFLICT (déjà locké par un autre user)
    """
    state, err = _check_report_access(report_id)
    if err is not None:
        return err

    actor_id, _email, _ip, _ua = _get_actor_info()

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase admin client is not configured.", 503)

    acquired = rw.acquire_lock(report_id, actor_id, client=cli)
    if not acquired:
        locked_by = state.get("locked_by") if state else None
        return _err(
            "LOCK_CONFLICT",
            f"Report '{report_id}' is already locked by another user ('{locked_by}'). "
            f"The lock auto-expires after {rw.LOCK_TIMEOUT_MIN} minutes.",
            423,
        )

    return jsonify({
        "success": True,
        "data": {
            "report_id": report_id,
            "locked":    True,
            "locked_by": actor_id,
        },
    }), 200


# ─── POST /api/admin/reports/<report_id>/unlock ──────────────────────────────


@admin_reports_bp.route("/<report_id>/unlock", methods=["POST"])
@require_auth
def unlock_endpoint(report_id: str):
    """Relâche le lock IN_REVIEW d'un rapport.

    Seul le propriétaire du lock ou un super-admin peut relâcher.

    Response :
        { "success": true, "data": { "locked": false } }

    Errors :
        - 403 LOCK_RELEASE_DENIED
    """
    state, err = _check_report_access(report_id)
    if err is not None:
        return err

    user = getattr(g, "current_user", None) or {}
    email = user.get("email")
    is_super = is_super_admin_email(email)

    actor_id, _email, _ip, _ua = _get_actor_info()

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase admin client is not configured.", 503)

    try:
        rw.release_lock(report_id, actor_id, is_super_admin=is_super, client=cli)
    except rw.WorkflowError as exc:
        return _err("LOCK_RELEASE_DENIED", str(exc), 403)
    except Exception as exc:  # noqa: BLE001
        logger.error("unlock failed: %s", exc.__class__.__name__)
        return _err("UNLOCK_FAILED", "Could not release lock.", 500)

    return jsonify({
        "success": True,
        "data": {
            "report_id": report_id,
            "locked":    False,
        },
    }), 200


# ─── Approve & Sign (US-128) ────────────────────────────────────────────────
# Endpoint super-admin only : génère snapshot immuable + watermark + signature.

@admin_reports_bp.route("/<report_id>/approve", methods=["POST"])
@require_auth
def approve_report(report_id: str):
    """Approuve un rapport : génère snapshot immuable + watermark + signature (US-128).

    Body JSON :
        {"watermark_recipient": {"name": str, "company": str | null} | null, "sign": bool}

    Returns : {"success": true, "snapshot_path": str, "sha256": str, "version": int}
    """
    import hashlib

    user = getattr(g, "current_user", None) or {}
    if not is_super_admin_email(user.get("email")):
        return _err("FORBIDDEN", "Super-admin uniquement.", 403)

    body: Dict = {}
    if request.content_length and request.content_length > 0:
        body = request.get_json(silent=True) or {}

    watermark_recipient: Optional[Dict] = body.get("watermark_recipient")
    do_sign: bool = bool(body.get("sign", False))

    if watermark_recipient is not None:
        if not isinstance(watermark_recipient, dict) or not watermark_recipient.get("name"):
            return _err("INVALID_BODY", "'watermark_recipient.name' requis.", 400)

    try:
        from ..services.report_pdf.loader import PDFContextLoader
        context = PDFContextLoader.load(report_id=report_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("PDFContextLoader.load() echec %s : %s", report_id, exc)
        return _err("CONTEXT_LOAD_ERROR", str(exc), 500)

    branding = None
    try:
        from ..services.pdf_branding import get_active_branding
        org_id = getattr(context, "org_id", None) or getattr(context, "organisation_id", None)
        if org_id:
            branding = get_active_branding(org_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("branding lookup failed: %s", exc)

    try:
        from ..services.report_pdf.renderer import Renderer
        from ..services.report_pdf.charts import ChartFactory
        chart_factory = ChartFactory(context)
        renderer = Renderer(context, branding)
        markdown_str = renderer.render_md()
        pdf_bytes = renderer.render_pdf(charts_factory=chart_factory)
    except Exception as exc:  # noqa: BLE001
        logger.error("Renderer echec %s : %s", report_id, exc)
        return _err("RENDER_ERROR", str(exc), 500)

    chart_pngs: Dict[str, bytes] = {}
    try:
        from ..services.report_pdf.charts import ChartFactory as _CF
        _cf = _CF(context)
        for method_name in ("belief_drift", "polymarket_curves", "demographic_pyramid",
                            "influence_leaderboard", "interaction_network"):
            method = getattr(_cf, method_name, None)
            if callable(method):
                try:
                    png = method()
                    if png:
                        chart_pngs[method_name] = png
                except Exception:  # noqa: BLE001
                    pass
    except Exception:  # noqa: BLE001
        pass

    if watermark_recipient is not None:
        try:
            from ..services.report_pdf.watermark import apply_watermark_to_pdf
            pdf_bytes = apply_watermark_to_pdf(
                pdf_bytes,
                recipient_name=watermark_recipient["name"],
                recipient_company=watermark_recipient.get("company"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Watermark echec : %s", exc)
            return _err("WATERMARK_ERROR", str(exc), 500)

    if do_sign:
        try:
            from ..services.report_pdf.signer import sign_pdf_pades
            pdf_bytes = sign_pdf_pades(pdf_bytes)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Signature PAdES echec (ignored) : %s", exc)

    sha256_hex = hashlib.sha256(pdf_bytes).hexdigest()

    try:
        from ..services.report_pdf.snapshot import create_snapshot, list_snapshots
        existing = list_snapshots(report_id)
        version = (existing[-1]["version"] + 1) if existing else 1
        snapshot_result = create_snapshot(
            report_id=report_id,
            version=version,
            markdown=markdown_str,
            pdf_bytes=pdf_bytes,
            branding=branding,
            chart_pngs=chart_pngs,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("create_snapshot echec : %s", exc)
        return _err("SNAPSHOT_ERROR", str(exc), 500)

    # Workflow transition APPROVED (US-126)
    try:
        actor_id, _email, _ip, _ua = _get_actor_info()
        cli = get_supabase_admin()
        rw.transition(
            report_id,
            target_state="APPROVED",
            actor_id=actor_id,
            actor_email=user.get("email"),
            snapshot_hash=sha256_hex,
            client=cli,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Workflow transition APPROVED echec (ignored) : %s", exc)

    logger.info("Report approved %s version=%d sha256=%s",
                report_id, snapshot_result["version"], sha256_hex[:16])

    return jsonify({
        "success": True,
        "snapshot_path": snapshot_result["path"],
        "sha256": snapshot_result["sha256"],
        "version": snapshot_result["version"],
    }), 200
