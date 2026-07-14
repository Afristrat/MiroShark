"""Service ensure_client_account (Lot B — compte client multi-tenant).

Point d'entrée unique : ``ensure_client_account()``, appelée depuis deux
déclencheurs UNIQUEMENT — ``confirm_calcom_booking`` (réservation Cal.com)
et ``update_quote_status`` (devis payé, circuit admin manuel). Jamais
depuis le webhook Stripe self-service (``stripe_checkout.py``) — ce
circuit reste volontairement sans compte (ADR-007/US-205).

Idempotence : clé de dédup = email. Un email déjà rattaché à une org
retourne cette org sans rien recréer ni renvoyer de magic link.

Best-effort total : ne lève jamais d'exception — chaque étape est loggée,
toute erreur retourne ``{"org_id": None, "user_id": None, "created": False}``.
Pattern identique à ``_send_admin_notification`` (ADR-IQ-14).

Contrat SDK Supabase vérifié contre ``supabase_auth==2.29.0`` (installé
dans ``backend/.venv``, cf. plan d'implémentation) :
  - ``client.auth.admin.list_users()`` → ``List[User]`` (pas de wrapper).
  - ``client.auth.admin.create_user(attrs)`` → ``UserResponse(user: User)``.
  - ``client.auth.admin.generate_link(params)`` → ``GenerateLinkResponse``
    avec ``.properties.action_link: str`` (champ requis, jamais None).
"""

from __future__ import annotations

import re
import secrets
from typing import Any, Dict, Optional

from ..auth.supabase_client import get_supabase_admin
from ..utils.logger import get_logger
from .email_service import render_template, send_email

logger = get_logger("miroshark.client_account")

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    slug = _SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return slug or "org"


def _find_user_by_email(email: str, *, client: Any) -> Optional[Dict[str, Any]]:
    # list_users() retourne directement List[User] (pas de wrapper .users).
    # Pas d'équivalent "get by email" côté GoTrue admin API ; filtrage
    # client-side acceptable au volume actuel de ce produit (cf. commentaire
    # équivalent dans quote.py::list_quotes_admin).
    users = client.auth.admin.list_users()
    target = email.strip().lower()
    for u in users:
        if u.email and u.email.strip().lower() == target:
            return {"id": u.id, "email": u.email}
    return None


def _find_org_membership(user_id: str, *, client: Any) -> Optional[Dict[str, Any]]:
    resp = (
        client.table("org_members")
        .select("org_id, role")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = getattr(resp, "data", None) or []
    return rows[0] if rows else None


def _unique_slug(base_slug: str, *, client: Any) -> str:
    slug = base_slug
    for _ in range(3):
        resp = (
            client.table("organizations")
            .select("id")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )
        if not (getattr(resp, "data", None) or []):
            return slug
        slug = f"{base_slug}-{secrets.token_hex(2)}"
    return f"{base_slug}-{secrets.token_hex(4)}"


def _create_org_and_membership(
    email: str,
    full_name: str,
    org_name: Optional[str],
    *,
    client: Any,
) -> Dict[str, Any]:
    base_slug = _slugify(org_name or email.split("@")[0])
    slug = _unique_slug(base_slug, client=client)

    org_resp = (
        client.table("organizations")
        .insert({
            "name": org_name or full_name or email,
            "slug": slug,
            "status": "trial",
        })
        .execute()
    )
    org_rows = getattr(org_resp, "data", None) or []
    if not org_rows:
        raise RuntimeError("organizations insert returned no row")
    org_id = org_rows[0]["id"]

    # create_user() retourne UserResponse(user: User) — toujours un objet
    # Pydantic, jamais un dict (contrat vérifié supabase_auth==2.29.0).
    created_user = client.auth.admin.create_user({
        "email": email,
        "email_confirm": True,
        "user_metadata": {"full_name": full_name},
    })
    user_id = created_user.user.id

    client.table("org_members").insert({
        "org_id": org_id,
        "user_id": user_id,
        "role": "owner",
    }).execute()

    return {"org_id": org_id, "user_id": user_id}


def _reattach_quote_ownership(org_id: str, email: str, *, client: Any) -> None:
    try:
        client.table("quote_ownership").update({"org_id": org_id}).eq(
            "customer_email", email
        ).execute()
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.error(
            "_reattach_quote_ownership failed for org=%s: %s",
            org_id, exc.__class__.__name__,
        )


_SUBJECT_BY_LOCALE = {
    "fr": "Bassira — Votre espace client est prêt",
    "en": "Bassira — Your client portal is ready",
    "ar": "بصيرة — مساحتك الخاصة جاهزة",
}


def _send_magic_link(email: str, full_name: str, locale: str, *, client: Any) -> None:
    locale = locale if locale in _SUBJECT_BY_LOCALE else "fr"
    try:
        # generate_link() retourne GenerateLinkResponse(properties, user) —
        # properties.action_link est un champ Pydantic requis (jamais None).
        resp = client.auth.admin.generate_link({
            "type": "magiclink",
            "email": email,
        })
        action_link = resp.properties.action_link
        html_body = render_template(f"client_account_ready_{locale}", {
            "full_name": full_name or email,
            "magic_link": action_link,
        })
        send_email(
            to_email=email,
            subject=_SUBJECT_BY_LOCALE[locale],
            html_body=html_body,
            reply_to="contact@ai-mpower.com",
        )
    except Exception as exc:  # noqa: BLE001 — best-effort, ne bloque jamais l'appelant
        logger.error("_send_magic_link failed for %s: %s", email, exc.__class__.__name__)


def ensure_client_account(
    email: str,
    full_name: str,
    org_name: Optional[str],
    *,
    source: str,
    locale: str = "fr",
    client: Any = None,
) -> Dict[str, Any]:
    """Crée ou retrouve le compte client associé à ``email`` (idempotent).

    Args:
        email: email attesté du client (jamais un email non vérifié).
        full_name: nom complet, best-effort (peut être vide).
        org_name: nom d'organisation si connu (sinon dérivé de l'email).
        source: ``"calcom_booking"`` | ``"quote_paid"`` — traçabilité log
            uniquement, aucune branche logique différente.
        locale: ``"fr"`` | ``"en"`` | ``"ar"`` — langue du magic link envoyé
            (US-217, i18n polyglotte intégral). Défaut ``"fr"`` (pivot).
        client: client Supabase admin injecté (tests).

    Returns:
        ``{"org_id": str|None, "user_id": str|None, "created": bool}``.
        Ne lève jamais — toute erreur retourne des ``None``.
    """
    if not email or "@" not in email:
        logger.error("ensure_client_account: invalid email (source=%s)", source)
        return {"org_id": None, "user_id": None, "created": False}

    try:
        cli = client or get_supabase_admin()

        existing_user = _find_user_by_email(email, client=cli)
        if existing_user:
            membership = _find_org_membership(existing_user["id"], client=cli)
            if membership:
                return {
                    "org_id": membership["org_id"],
                    "user_id": existing_user["id"],
                    "created": False,
                }

        created = _create_org_and_membership(email, full_name, org_name, client=cli)
        _reattach_quote_ownership(created["org_id"], email, client=cli)
        _send_magic_link(email, full_name, locale, client=cli)

        logger.info(
            "ensure_client_account: created org=%s user=%s (source=%s)",
            created["org_id"], created["user_id"], source,
        )
        return {
            "org_id": created["org_id"],
            "user_id": created["user_id"],
            "created": True,
        }
    except Exception as exc:  # noqa: BLE001 — best-effort total, jamais propagé
        logger.error(
            "ensure_client_account failed (source=%s): %s",
            source, exc.__class__.__name__,
        )
        return {"org_id": None, "user_id": None, "created": False}
