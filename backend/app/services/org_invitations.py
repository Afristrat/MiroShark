"""Service org_invitations Supabase (US-115).

Helpers métier autour de la table ``public.org_invitations`` :

  - ``create_invitation(org_id, email, role, invited_by, *, client)``
  - ``get_invitation(token, *, client)``
  - ``list_pending_invitations(org_id, *, client)``
  - ``revoke_invitation(token, *, client)``
  - ``redeem_invitation(token, user_id, *, client)`` — atomique (insert
    ``org_members`` + update ``accepted_at``).

Toutes les fonctions acceptent un client Supabase admin injecté
(``client=``) pour permettre l'injection de doublures pytest.
Toutes les écritures passent par le ``service_role`` (RLS bypass) — le
backend Flask est l'unique surface d'écriture autorisée.

Format du retour
────────────────

Les helpers retournent des dicts au format :

    {
      "token": "uuid",
      "org_id": "uuid",
      "email": "user@example.com",
      "role": "member",
      "expires_at": "2026-05-12T12:00:00Z",
      "accepted_at": null|"2026-05-06T...",
      "invited_by": "uuid|null",
      "created_at": "2026-05-05T...",
      "metadata": {...}
    }

Le helper ``get_invitation_with_org`` enrichit avec les meta de l'org
(``{org_name, org_slug, org_country_code}``) pour pré-remplir le signup.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ..auth.supabase_client import get_supabase_admin
from ..utils.logger import get_logger


logger = get_logger("miroshark.org_invitations")


_VALID_ROLES = {"admin", "member", "viewer"}
DEFAULT_EXPIRY_DAYS = 7


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def create_invitation(
    org_id: str,
    email: str,
    *,
    role: str = "member",
    invited_by: Optional[str] = None,
    expires_in_days: int = DEFAULT_EXPIRY_DAYS,
    client: Any = None,
) -> Dict[str, Any]:
    """Crée une nouvelle invitation org → email.

    Args:
        org_id : UUID de l'org cible.
        email : email du destinataire (sera lowercased pour comparaison RLS).
        role : ``admin`` | ``member`` | ``viewer`` (default ``member``).
        invited_by : UUID de l'admin qui invite (peut être None pour seed).
        expires_in_days : durée de validité (default 7).

    Returns:
        Le dict de l'invitation insérée (avec ``token``, ``expires_at``,
        ``created_at`` etc.).

    Raises:
        ValueError : args invalides.
        Exception : erreur Supabase propagée.
    """
    if not org_id or not isinstance(org_id, str):
        raise ValueError("org_id is required (str)")
    if not email or not isinstance(email, str) or "@" not in email:
        raise ValueError("email is required (must contain '@')")
    if role not in _VALID_ROLES:
        raise ValueError(
            f"Invalid role: {role!r}. Allowed: {sorted(_VALID_ROLES)}"
        )

    cli = client or get_supabase_admin()
    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(days=int(expires_in_days))
    ).replace(microsecond=0).isoformat()

    payload: Dict[str, Any] = {
        "org_id": org_id,
        "email": email.strip().lower(),
        "role": role,
        "expires_at": expires_at,
    }
    if invited_by:
        payload["invited_by"] = invited_by

    response = cli.table("org_invitations").insert(payload).execute()
    rows = getattr(response, "data", None) or []
    if not rows:
        raise RuntimeError("Insert returned no row — Supabase response empty")
    return rows[0]


def get_invitation(token: str, *, client: Any = None) -> Optional[Dict[str, Any]]:
    """Lit une invitation par token, ou ``None`` si absente.

    Ne filtre pas sur expires_at / accepted_at — c'est au caller de
    décider du contrat (un endpoint admin peut vouloir voir les
    invitations expirées pour audit).
    """
    if not token or not isinstance(token, str):
        return None
    cli = client or get_supabase_admin()
    try:
        response = (
            cli.table("org_invitations")
            .select(
                "token, org_id, email, role, expires_at, accepted_at, "
                "invited_by, created_at, metadata"
            )
            .eq("token", token)
            .limit(1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        if not rows:
            return None
        return rows[0]
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "get_invitation failed for token=%s***: %s",
            token[:8] if isinstance(token, str) else "?",
            exc.__class__.__name__,
        )
        return None


def get_invitation_with_org(
    token: str,
    *,
    client: Any = None,
) -> Optional[Dict[str, Any]]:
    """Lit une invitation + résout les meta de l'org en un appel.

    Returns un dict enrichi : ``{token, email, role, expires_at,
    accepted_at, org_id, org_name, org_slug, org_country_code}`` ou
    ``None`` si l'invitation est introuvable.
    """
    invitation = get_invitation(token, client=client)
    if not invitation:
        return None
    cli = client or get_supabase_admin()
    org_id = invitation.get("org_id")
    org_meta: Dict[str, Any] = {}
    if org_id:
        try:
            response = (
                cli.table("organizations")
                .select("id, name, slug, country_code")
                .eq("id", org_id)
                .limit(1)
                .execute()
            )
            rows = getattr(response, "data", None) or []
            if rows:
                org_meta = rows[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "get_invitation_with_org meta lookup failed: %s",
                exc.__class__.__name__,
            )
    return {
        "token": invitation.get("token"),
        "email": invitation.get("email"),
        "role": invitation.get("role"),
        "expires_at": invitation.get("expires_at"),
        "accepted_at": invitation.get("accepted_at"),
        "invited_by": invitation.get("invited_by"),
        "created_at": invitation.get("created_at"),
        "org_id": org_id,
        "org_name": org_meta.get("name"),
        "org_slug": org_meta.get("slug"),
        "org_country_code": org_meta.get("country_code"),
    }


def list_pending_invitations(
    org_id: str,
    *,
    client: Any = None,
) -> List[Dict[str, Any]]:
    """Liste les invitations pending (accepted_at NULL, non expirées) d'une org."""
    if not org_id or not isinstance(org_id, str):
        return []
    cli = client or get_supabase_admin()
    try:
        response = (
            cli.table("org_invitations")
            .select(
                "token, org_id, email, role, expires_at, accepted_at, "
                "invited_by, created_at"
            )
            .eq("org_id", org_id)
            .is_("accepted_at", "null")
            .order("created_at", desc=True)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        # Filtre côté Python pour les invitations expirées (sécurité
        # défensive si la base ne supporte pas la comparaison RFC).
        now_iso = _iso_now()
        return [
            r for r in rows
            if (r.get("expires_at") or "9999") > now_iso
        ]
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "list_pending_invitations failed for org_id=%s: %s",
            org_id, exc.__class__.__name__,
        )
        return []


def revoke_invitation(token: str, *, client: Any = None) -> bool:
    """Supprime une invitation pending (action admin).

    Returns ``True`` si la ligne a été supprimée, ``False`` sinon
    (token introuvable ou erreur Supabase).
    """
    if not token or not isinstance(token, str):
        return False
    cli = client or get_supabase_admin()
    try:
        response = (
            cli.table("org_invitations")
            .delete()
            .eq("token", token)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return len(rows) > 0
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "revoke_invitation failed for token=%s***: %s",
            token[:8] if isinstance(token, str) else "?",
            exc.__class__.__name__,
        )
        return False


def redeem_invitation(
    token: str,
    user_id: str,
    *,
    user_email: Optional[str] = None,
    client: Any = None,
) -> Dict[str, Any]:
    """Consomme une invitation : crée la row ``org_members`` + marque acceptée.

    Pré-conditions vérifiées en interne (retourne erreur sinon) :
      - L'invitation existe.
      - L'invitation n'est pas expirée.
      - L'invitation n'est pas déjà consommée.
      - Si ``user_email`` fourni, doit matcher (case-insensitive)
        l'email de l'invitation.

    Returns:
        Dict ``{ok: bool, error_code: str|None, org_id: str|None,
        role: str|None}``.

    Le user est ajouté avec le rôle de l'invitation. Si une row
    ``org_members`` existe déjà pour ce ``(org_id, user_id)``,
    l'idempotence est respectée (l'invitation est tout de même marquée
    consommée).
    """
    if not token or not isinstance(token, str):
        return {"ok": False, "error_code": "INVALID_TOKEN"}
    if not user_id or not isinstance(user_id, str):
        return {"ok": False, "error_code": "INVALID_USER"}

    cli = client or get_supabase_admin()
    invitation = get_invitation(token, client=cli)
    if not invitation:
        return {"ok": False, "error_code": "INVITATION_NOT_FOUND"}

    if invitation.get("accepted_at"):
        return {"ok": False, "error_code": "INVITATION_ALREADY_CONSUMED"}

    expires_at = invitation.get("expires_at")
    if expires_at and expires_at < _iso_now():
        return {"ok": False, "error_code": "INVITATION_EXPIRED"}

    invite_email = (invitation.get("email") or "").strip().lower()
    if user_email:
        ue = user_email.strip().lower()
        if ue and invite_email and ue != invite_email:
            return {"ok": False, "error_code": "EMAIL_MISMATCH"}

    org_id = invitation.get("org_id")
    role = invitation.get("role") or "member"

    # 1. Insert org_members (idempotent via unique (org_id, user_id))
    try:
        cli.table("org_members").insert({
            "org_id": org_id,
            "user_id": user_id,
            "role": role,
            "invited_by": invitation.get("invited_by"),
        }).execute()
    except Exception as exc:  # noqa: BLE001 — peut être duplicate
        msg = str(exc)
        if "duplicate" in msg.lower() or "23505" in msg:
            logger.info(
                "org_member already exists for org=%s user=%s — kept as is.",
                org_id, user_id,
            )
        else:
            logger.error(
                "redeem_invitation insert org_members failed: %s",
                exc.__class__.__name__,
            )
            return {"ok": False, "error_code": "INTERNAL_ERROR"}

    # 2. Marque l'invitation comme consommée.
    try:
        cli.table("org_invitations").update({
            "accepted_at": _iso_now(),
        }).eq("token", token).execute()
    except Exception as exc:  # noqa: BLE001
        # On a déjà créé le membership. Log mais pas de rollback — un
        # cron pourra cleaner les invitations obsolètes plus tard.
        logger.warning(
            "redeem_invitation update accepted_at failed: %s",
            exc.__class__.__name__,
        )

    return {
        "ok": True,
        "error_code": None,
        "org_id": org_id,
        "role": role,
    }
