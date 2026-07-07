"""Endpoints invitations org → user (US-115).

Trois groupes de routes :

  ``/api/admin/invitations``     (org admin OU super-admin Bassira)
    POST    — crée une invitation + envoie l'email magic link
    GET     — liste les invitations pending de l'org courante
    DELETE /<token>  — révoque une invitation pending

  ``/api/invitations/<token>``   (public, no auth requise)
    GET /accept   — résout les metadata pour pré-remplir le signup
                    (org name, role, expires_at) sans exiger d'auth.
                    Permet au front de matcher les bons UX states.

  ``/api/invitations/<token>/redeem``   (auth requise)
    POST          — appelé après signup auth, crée la row org_members.
                    Vérifie que ``auth.email() == invitation.email``.

Sécurité
────────
- Tokens UUID opaques. Pas d'énumération possible (16 caractères hex
  cryptographiques, 122 bits d'entropie via gen_random_uuid).
- L'email ``invitation.email`` est comparé case-insensitive à
  ``g.current_user.email`` au moment du redeem — pas d'usurpation
  possible même si quelqu'un a obtenu le token.
- Email leakage : on ne logue jamais le token complet, seulement les
  8 premiers caractères pour le tracing.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from flask import Blueprint, g, jsonify, request

from ..auth.decorators import (
    is_super_admin_email,
    require_auth,
)
from ..auth.supabase_client import (
    SupabaseConfigError,
    get_supabase_admin,
    get_user_orgs,
)
from ..services import org_invitations as oi


logger = logging.getLogger("miroshark.api.invitations")


# Blueprint admin (POST/GET/DELETE) — préfixé /api/admin/invitations
admin_invitations_bp = Blueprint("admin_invitations", __name__)

# Blueprint public + redeem — préfixé /api/invitations
invitations_bp = Blueprint("invitations", __name__)


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_VALID_ROLES = {"admin", "member", "viewer"}


def _err(code: str, message: str, status: int):
    return jsonify({
        "success": False,
        "error_code": code,
        "error": message,
    }), status


# ─── Helpers privés ────────────────────────────────────────────────────────


def _resolve_target_org_for_invite(
    user: Dict[str, Any],
    requested_org_id: Optional[str],
) -> tuple[Optional[str], Optional[Any]]:
    """Sélectionne l'org sur laquelle créer l'invitation.

    - Super-admin Bassira : doit fournir ``org_id`` explicitement (pas
      d'org "courante" légitime — il agit pour le compte d'une org).
    - Admin/owner d'une org : peut omettre org_id si une seule org, ou
      doit fournir org_id si plusieurs.

    Returns ``(org_id, error_response_tuple_or_None)``.
    """
    email = user.get("email") if isinstance(user, dict) else None
    is_super = is_super_admin_email(email)

    if is_super:
        if not requested_org_id:
            return None, _err(
                "ORG_ID_REQUIRED",
                "Super-admin must provide org_id explicitly to invite.",
                400,
            )
        return requested_org_id, None

    # Org admin path : on lit ses orgs et on vérifie qu'il est admin/owner.
    user_id = user.get("id") if isinstance(user, dict) else None
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
        logger.error("user_orgs failed: %s", exc.__class__.__name__)
        return None, _err("INTERNAL_AUTH_ERROR", "Could not resolve orgs.", 500)

    eligible = [
        o for o in user_orgs
        if o.get("role") in {"owner", "admin"}
    ]
    if not eligible:
        return None, _err(
            "INSUFFICIENT_ROLE",
            "Only org owner/admin can invite members.",
            403,
        )

    if requested_org_id:
        match = next(
            (o for o in eligible if str(o.get("id")) == str(requested_org_id)),
            None,
        )
        if match is None:
            return None, _err(
                "ORG_NOT_FOUND_FOR_USER",
                "You are not an admin/owner of this organization.",
                404,
            )
        return requested_org_id, None

    if len(eligible) == 1:
        return eligible[0].get("id"), None

    return None, _err(
        "ORG_ID_REQUIRED",
        "User is admin/owner of multiple orgs — provide org_id in the body.",
        400,
    )


def _send_invitation_email(
    invitation: Dict[str, Any],
    org_meta: Dict[str, Any],
) -> bool:
    """Best-effort envoi de l'email d'invitation via le service unifié."""
    try:
        from ..services.email_service import render_template, send_email

        token = invitation.get("token") or ""
        # Le frontend SPA route /signup et lit ?invite=<token>.
        invite_url = (
            f"https://prospectives.ai-mpower.com/signup?invite={token}"
        )

        ctx = {
            "org_name": org_meta.get("name") or "Bassira",
            "org_slug": org_meta.get("slug") or "",
            "role": invitation.get("role") or "member",
            "invite_url": invite_url,
            "expires_at": invitation.get("expires_at") or "",
            "email": invitation.get("email") or "",
        }
        html_body = render_template("org_invitation", ctx)
        return bool(send_email(
            to_email=invitation.get("email") or "",
            subject=f"Bassira — Invitation à rejoindre {ctx['org_name']}",
            html_body=html_body,
            reply_to="contact@ai-mpower.com",
        ))
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "invitation email failed for token=%s***: %s",
            (invitation.get("token") or "")[:8],
            exc.__class__.__name__,
        )
        return False


# ─── POST /api/admin/invitations ────────────────────────────────────────────


@admin_invitations_bp.route("", methods=["POST"])
@require_auth
def create_invitation_endpoint():
    """Crée une invitation org → user + envoie l'email magic link.

    Body JSON :
        {
          "email": "user@example.com",
          "role": "member" | "admin" | "viewer"  (default "member"),
          "org_id": "uuid"  (requis si super-admin OR multi-org admin)
        }

    Retourne 201 + l'invitation créée. Email envoyé best-effort.
    """
    body = request.get_json(silent=True) or {}
    email = body.get("email")
    role = body.get("role") or "member"
    requested_org_id = body.get("org_id")

    if not isinstance(email, str) or not _EMAIL_RE.match(email.strip()):
        return _err("INVALID_EMAIL", "Field `email` is required and must be valid.", 400)
    if role not in _VALID_ROLES:
        return _err(
            "INVALID_ROLE",
            f"Invalid role: {role}. Allowed: {sorted(_VALID_ROLES)}.",
            400,
        )

    user = getattr(g, "current_user", None) or {}
    org_id, err = _resolve_target_org_for_invite(user, requested_org_id)
    if err is not None:
        return err
    assert org_id is not None  # contract de _resolve_target_org_for_invite

    invited_by = user.get("id") if isinstance(user, dict) else None

    # Création + email
    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err(
            "SUPABASE_NOT_CONFIGURED",
            "Backend Supabase admin client is not configured.",
            503,
        )

    try:
        invitation = oi.create_invitation(
            org_id,
            email,
            role=role,
            invited_by=invited_by,
            client=cli,
        )
    except ValueError as exc:
        return _err("INVALID_BODY", str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        logger.error("create_invitation failed: %s", exc.__class__.__name__)
        return _err("INVITATION_CREATE_FAILED", "Could not create invitation.", 500)

    # Lookup org meta pour l'email (best-effort)
    org_meta: Dict[str, Any] = {}
    try:
        resp = (
            cli.table("organizations")
            .select("id, name, slug")
            .eq("id", org_id)
            .limit(1)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if rows:
            org_meta = rows[0]
    except Exception:  # noqa: BLE001
        pass

    email_sent = _send_invitation_email(invitation, org_meta)

    return jsonify({
        "success": True,
        "data": {
            "invitation": {
                "token": invitation.get("token"),
                "org_id": invitation.get("org_id"),
                "email": invitation.get("email"),
                "role": invitation.get("role"),
                "expires_at": invitation.get("expires_at"),
                "created_at": invitation.get("created_at"),
            },
            "email_sent": email_sent,
        },
    }), 201


# ─── GET /api/admin/invitations ─────────────────────────────────────────────


@admin_invitations_bp.route("", methods=["GET"])
@require_auth
def list_invitations_endpoint():
    """Liste les invitations pending pour l'org courante.

    Query : ``org_id`` (requis si super-admin OR multi-org admin).
    """
    user = getattr(g, "current_user", None) or {}
    requested_org_id = request.args.get("org_id")
    org_id, err = _resolve_target_org_for_invite(user, requested_org_id)
    if err is not None:
        return err
    assert org_id is not None

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err(
            "SUPABASE_NOT_CONFIGURED",
            "Backend Supabase admin client is not configured.",
            503,
        )

    invitations = oi.list_pending_invitations(org_id, client=cli)
    return jsonify({
        "success": True,
        "data": {
            "invitations": invitations,
            "org_id": org_id,
        },
    }), 200


# ─── DELETE /api/admin/invitations/<token> ──────────────────────────────────


@admin_invitations_bp.route("/<token>", methods=["DELETE"])
@require_auth
def revoke_invitation_endpoint(token: str):
    """Révoque (supprime) une invitation pending."""
    if not token:
        return _err("INVALID_TOKEN", "token is required.", 400)

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err(
            "SUPABASE_NOT_CONFIGURED",
            "Backend Supabase admin client is not configured.",
            503,
        )

    invitation = oi.get_invitation(token, client=cli)
    if not invitation:
        return _err("INVITATION_NOT_FOUND", "Invitation not found.", 404)

    # Vérifie que le caller a le droit de révoquer (admin de l'org OU super-admin).
    user = getattr(g, "current_user", None) or {}
    org_id, err = _resolve_target_org_for_invite(user, invitation.get("org_id"))
    if err is not None:
        return err

    if oi.revoke_invitation(token, client=cli):
        return jsonify({"success": True, "data": {"revoked": True}}), 200
    return _err("INVITATION_REVOKE_FAILED", "Could not revoke invitation.", 500)


# ─── GET /api/invitations/<token>/accept (public) ───────────────────────────


@invitations_bp.route("/<token>/accept", methods=["GET"])
def accept_invitation_metadata(token: str):
    """Public : renvoie les metadata d'invitation pour pré-remplir le signup.

    Aucun cookie / JWT requis. Vérifie expires_at et accepted_at avant de
    renvoyer les meta : si expirée ou consommée, renvoie 410 Gone.
    """
    if not token or not isinstance(token, str):
        return _err("INVALID_TOKEN", "token is required.", 400)

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err(
            "SUPABASE_NOT_CONFIGURED",
            "Backend Supabase admin client is not configured.",
            503,
        )

    enriched = oi.get_invitation_with_org(token, client=cli)
    if not enriched:
        return _err("INVITATION_NOT_FOUND", "Invitation not found.", 404)

    from datetime import datetime, timezone
    if enriched.get("accepted_at"):
        return _err("INVITATION_ALREADY_CONSUMED", "Invitation already consumed.", 410)

    expires_at = enriched.get("expires_at") or ""
    if expires_at and expires_at < datetime.now(timezone.utc).isoformat():
        return _err("INVITATION_EXPIRED", "Invitation has expired.", 410)

    return jsonify({
        "success": True,
        "data": {
            "token": enriched.get("token"),
            "email": enriched.get("email"),
            "role": enriched.get("role"),
            "expires_at": enriched.get("expires_at"),
            "org_name": enriched.get("org_name"),
            "org_slug": enriched.get("org_slug"),
            "org_country_code": enriched.get("org_country_code"),
        },
    }), 200


# ─── POST /api/invitations/<token>/redeem (auth requise) ────────────────────


@invitations_bp.route("/<token>/redeem", methods=["POST"])
@require_auth
def redeem_invitation_endpoint(token: str):
    """Consomme l'invitation : crée la row ``org_members`` pour l'user courant.

    Pré-condition : l'utilisateur doit être authentifié (JWT Supabase).
    L'email du JWT doit matcher l'email de l'invitation (case-insensitive).
    """
    if not token or not isinstance(token, str):
        return _err("INVALID_TOKEN", "token is required.", 400)

    user = getattr(g, "current_user", None) or {}
    user_id = user.get("id") if isinstance(user, dict) else None
    user_email = user.get("email") if isinstance(user, dict) else None
    if not user_id:
        return _err("INVALID_TOKEN", "Token missing 'sub' claim.", 401)

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err(
            "SUPABASE_NOT_CONFIGURED",
            "Backend Supabase admin client is not configured.",
            503,
        )

    result = oi.redeem_invitation(
        token, user_id, user_email=user_email, client=cli
    )
    if not result.get("ok"):
        code = result.get("error_code") or "REDEEM_FAILED"
        if code == "INVITATION_NOT_FOUND":
            return _err(code, "Invitation not found.", 404)
        if code == "INVITATION_EXPIRED":
            return _err(code, "Invitation has expired.", 410)
        if code == "INVITATION_ALREADY_CONSUMED":
            return _err(code, "Invitation already consumed.", 409)
        if code == "EMAIL_MISMATCH":
            return _err(code, "Token email does not match authenticated user.", 403)
        return _err(code, "Could not redeem invitation.", 500)

    return jsonify({
        "success": True,
        "data": {
            "org_id": result.get("org_id"),
            "role": result.get("role"),
        },
    }), 200
