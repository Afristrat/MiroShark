"""Endpoints admin — versionning + commentaires rapport (US-127).

Blueprint ``admin_report_versions_bp`` monté sur ``/api/admin/reports``.

Routes :
  GET  /api/admin/reports/<id>/versions                            — liste versions
  POST /api/admin/reports/<id>/versions                           — snapshot nouvelle version
  GET  /api/admin/reports/<id>/versions/<vid>/diff/<other_id>     — diff JSON
  GET  /api/admin/reports/<id>/comments                           — liste commentaires
  POST /api/admin/reports/<id>/comments                           — crée commentaire
  PATCH /api/admin/reports/<id>/comments/<cid>                    — résout commentaire

Sécurité
────────
- Toutes les routes exigent @require_auth.
- Super-admin : accès universel.
- Org admin/owner : accès aux reports de son org uniquement.
  (même logique que admin_reports.py via _check_report_access importé)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from flask import Blueprint, g, jsonify, request

from ..auth.decorators import is_super_admin_email, require_auth
from ..auth.supabase_client import SupabaseConfigError, get_supabase_admin, get_user_orgs
from ..services import report_workflow as rw


logger = logging.getLogger("miroshark.api.admin_report_versions")

# Blueprint partagé avec admin_reports (même préfixe /api/admin/reports)
admin_report_versions_bp = Blueprint("admin_report_versions", __name__)

_TABLE_VERSIONS = "report_versions"
_TABLE_COMMENTS = "report_comments"


# ─── Helpers ────────────────────────────────────────────────────────────────────


def _err(code: str, message: str, status: int):
    return jsonify({
        "success": False,
        "error_code": code,
        "error": message,
    }), status


def _check_report_access(report_id: str):
    """Vérifie que l'utilisateur courant a accès au rapport.

    Returns:
        Tuple ``(state_row_or_None, error_response_or_None)``.
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
        return None, _err("REPORT_NOT_FOUND", "Report not found or not accessible.", 404)

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


# ─── Diff utilitaire (côté Python, évite une dépendance NPM supplémentaire)
# Utilise difflib standard pour générer un diff JSON line-by-line.


def _compute_diff(old_text: str, new_text: str) -> List[Dict[str, Any]]:
    """Retourne une liste d'opérations de diff [{op, text}] utilisable par le front.

    op values: 'equal' | 'insert' | 'delete'
    """
    import difflib

    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    result: List[Dict[str, Any]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in old_lines[i1:i2]:
                result.append({"op": "equal", "text": line})
        elif tag == "replace":
            for line in old_lines[i1:i2]:
                result.append({"op": "delete", "text": line})
            for line in new_lines[j1:j2]:
                result.append({"op": "insert", "text": line})
        elif tag == "delete":
            for line in old_lines[i1:i2]:
                result.append({"op": "delete", "text": line})
        elif tag == "insert":
            for line in new_lines[j1:j2]:
                result.append({"op": "insert", "text": line})

    return result


# ─── GET /api/admin/reports/<report_id>/versions ────────────────────────────────


@admin_report_versions_bp.route("/<report_id>/versions", methods=["GET"])
@require_auth
def list_versions(report_id: str):
    """Liste les versions d'un rapport par ordre décroissant.

    Query params :
        ``limit`` — max résultats (défaut 20, max 50).
        ``offset`` — pagination (défaut 0).

    Response :
        { "success": true, "data": { "versions": [...], "total": n } }
    """
    _state, err = _check_report_access(report_id)
    if err is not None:
        return err

    try:
        limit = min(int(request.args.get("limit", 20)), 50)
        offset = max(int(request.args.get("offset", 0)), 0)
    except (TypeError, ValueError):
        limit, offset = 20, 0

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend not configured.", 503)

    try:
        resp = (
            cli.table(_TABLE_VERSIONS)
            .select("version_id,report_id,version_number,created_by,created_at,comment")
            .eq("report_id", report_id)
            .order("version_number", desc=True)
            .limit(limit)
            .offset(offset)
            .execute()
        )
        versions = resp.data or []
    except Exception as exc:  # noqa: BLE001
        logger.error("list_versions failed: %s", exc.__class__.__name__)
        return _err("DB_ERROR", "Could not fetch versions.", 500)

    return jsonify({
        "success": True,
        "data": {
            "report_id": report_id,
            "versions": versions,
            "count": len(versions),
        },
    }), 200


# ─── POST /api/admin/reports/<report_id>/versions ────────────────────────────────


@admin_report_versions_bp.route("/<report_id>/versions", methods=["POST"])
@require_auth
def create_version(report_id: str):
    """Crée un snapshot de version pour un rapport.

    Body JSON :
        { "markdown_content": "...", "comment": "..." }

    Response :
        { "success": true, "data": { "version": {...} } }
    """
    _state, err = _check_report_access(report_id)
    if err is not None:
        return err

    body = request.get_json(silent=True) or {}
    markdown_content = body.get("markdown_content")
    if not isinstance(markdown_content, str):
        return _err("INVALID_BODY", "Field `markdown_content` (string) is required.", 400)

    comment = body.get("comment")

    user = getattr(g, "current_user", None) or {}
    user_id = user.get("id")

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend not configured.", 503)

    # Calcule le prochain numéro de version
    try:
        count_resp = (
            cli.table(_TABLE_VERSIONS)
            .select("version_number")
            .eq("report_id", report_id)
            .order("version_number", desc=True)
            .limit(1)
            .execute()
        )
        existing = count_resp.data or []
        next_version = (existing[0]["version_number"] + 1) if existing else 1
    except Exception as exc:  # noqa: BLE001
        logger.error("version_number fetch failed: %s", exc.__class__.__name__)
        return _err("DB_ERROR", "Could not determine version number.", 500)

    row: Dict[str, Any] = {
        "version_id":       str(uuid.uuid4()),
        "report_id":        report_id,
        "version_number":   next_version,
        "markdown_content": markdown_content,
        "created_by":       user_id,
        "comment":          comment,
    }

    try:
        ins_resp = cli.table(_TABLE_VERSIONS).insert(row).execute()
        version = (ins_resp.data or [row])[0]
    except Exception as exc:  # noqa: BLE001
        logger.error("create_version insert failed: %s", exc.__class__.__name__)
        return _err("DB_ERROR", "Could not save version.", 500)

    return jsonify({
        "success": True,
        "data": {"version": version},
    }), 201


# ─── GET /api/admin/reports/<report_id>/versions/<version_id>/diff/<other_version_id>


@admin_report_versions_bp.route(
    "/<report_id>/versions/<version_id>/diff/<other_version_id>",
    methods=["GET"],
)
@require_auth
def diff_versions(report_id: str, version_id: str, other_version_id: str):
    """Retourne le diff JSON entre deux versions d'un rapport.

    Response :
        {
          "success": true,
          "data": {
            "from_version": { version_id, version_number },
            "to_version":   { version_id, version_number },
            "diff": [ { "op": "equal"|"insert"|"delete", "text": "..." }, ... ]
          }
        }
    """
    _state, err = _check_report_access(report_id)
    if err is not None:
        return err

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend not configured.", 503)

    def _fetch_version(vid: str) -> Optional[Dict[str, Any]]:
        try:
            resp = (
                cli.table(_TABLE_VERSIONS)
                .select("version_id,report_id,version_number,markdown_content")
                .eq("report_id", report_id)
                .eq("version_id", vid)
                .limit(1)
                .execute()
            )
            rows = resp.data or []
            return rows[0] if rows else None
        except Exception:  # noqa: BLE001
            return None

    from_v = _fetch_version(version_id)
    to_v = _fetch_version(other_version_id)

    if from_v is None or to_v is None:
        return _err("VERSION_NOT_FOUND", "One or both versions not found.", 404)

    diff_ops = _compute_diff(
        from_v.get("markdown_content", ""),
        to_v.get("markdown_content", ""),
    )

    return jsonify({
        "success": True,
        "data": {
            "from_version": {
                "version_id":     from_v["version_id"],
                "version_number": from_v["version_number"],
            },
            "to_version": {
                "version_id":     to_v["version_id"],
                "version_number": to_v["version_number"],
            },
            "diff": diff_ops,
        },
    }), 200


# ─── GET /api/admin/reports/<report_id>/comments ────────────────────────────────


@admin_report_versions_bp.route("/<report_id>/comments", methods=["GET"])
@require_auth
def list_comments(report_id: str):
    """Liste les commentaires d'un rapport.

    Query params :
        ``resolved`` — true|false pour filtrer (défaut : tous).
        ``limit``    — max résultats (défaut 50, max 100).

    Response :
        { "success": true, "data": { "comments": [...] } }
    """
    _state, err = _check_report_access(report_id)
    if err is not None:
        return err

    try:
        limit = min(int(request.args.get("limit", 50)), 100)
    except (TypeError, ValueError):
        limit = 50

    resolved_filter = request.args.get("resolved")

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend not configured.", 503)

    try:
        q = (
            cli.table(_TABLE_COMMENTS)
            .select("comment_id,report_id,version_id,paragraph_anchor,author_id,body,resolved,created_at")
            .eq("report_id", report_id)
            .order("created_at", desc=False)
            .limit(limit)
        )
        if resolved_filter is not None:
            q = q.eq("resolved", resolved_filter.lower() == "true")

        resp = q.execute()
        comments = resp.data or []
    except Exception as exc:  # noqa: BLE001
        logger.error("list_comments failed: %s", exc.__class__.__name__)
        return _err("DB_ERROR", "Could not fetch comments.", 500)

    return jsonify({
        "success": True,
        "data": {
            "report_id": report_id,
            "comments": comments,
            "count": len(comments),
        },
    }), 200


# ─── POST /api/admin/reports/<report_id>/comments ────────────────────────────────


@admin_report_versions_bp.route("/<report_id>/comments", methods=["POST"])
@require_auth
def create_comment(report_id: str):
    """Crée un commentaire sur un paragraphe du rapport.

    Body JSON :
        { "paragraph_anchor": "...", "body": "...", "version_id": "..." (optionnel) }

    Response :
        { "success": true, "data": { "comment": {...} } }
    """
    _state, err = _check_report_access(report_id)
    if err is not None:
        return err

    body = request.get_json(silent=True) or {}
    paragraph_anchor = body.get("paragraph_anchor", "")
    comment_body = body.get("body", "")
    version_id = body.get("version_id")

    if not isinstance(comment_body, str) or not comment_body.strip():
        return _err("INVALID_BODY", "Field `body` (string) is required.", 400)

    user = getattr(g, "current_user", None) or {}
    user_id = user.get("id")

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend not configured.", 503)

    row: Dict[str, Any] = {
        "comment_id":       str(uuid.uuid4()),
        "report_id":        report_id,
        "version_id":       version_id,
        "paragraph_anchor": paragraph_anchor,
        "author_id":        user_id,
        "body":             comment_body,
        "resolved":         False,
    }

    try:
        ins_resp = cli.table(_TABLE_COMMENTS).insert(row).execute()
        comment = (ins_resp.data or [row])[0]
    except Exception as exc:  # noqa: BLE001
        logger.error("create_comment insert failed: %s", exc.__class__.__name__)
        return _err("DB_ERROR", "Could not save comment.", 500)

    return jsonify({
        "success": True,
        "data": {"comment": comment},
    }), 201


# ─── PATCH /api/admin/reports/<report_id>/comments/<comment_id> ───────────────


@admin_report_versions_bp.route("/<report_id>/comments/<comment_id>", methods=["PATCH"])
@require_auth
def patch_comment(report_id: str, comment_id: str):
    """Met à jour un commentaire (résolution).

    Body JSON :
        { "resolved": true|false }

    Response :
        { "success": true, "data": { "comment": {...} } }
    """
    _state, err = _check_report_access(report_id)
    if err is not None:
        return err

    body = request.get_json(silent=True) or {}
    if "resolved" not in body:
        return _err("INVALID_BODY", "Field `resolved` (bool) is required.", 400)

    resolved = bool(body.get("resolved"))

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend not configured.", 503)

    try:
        upd_resp = (
            cli.table(_TABLE_COMMENTS)
            .update({"resolved": resolved})
            .eq("report_id", report_id)
            .eq("comment_id", comment_id)
            .execute()
        )
        rows = upd_resp.data or []
        if not rows:
            return _err("COMMENT_NOT_FOUND", "Comment not found.", 404)
        comment = rows[0]
    except Exception as exc:  # noqa: BLE001
        logger.error("patch_comment failed: %s", exc.__class__.__name__)
        return _err("DB_ERROR", "Could not update comment.", 500)

    return jsonify({
        "success": True,
        "data": {"comment": comment},
    }), 200
