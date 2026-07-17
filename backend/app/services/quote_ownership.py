"""Quote ownership helper Supabase (US-114).

Module dédié au mapping ``quote_id (text) → org_id (uuid)`` matérialisé
par la table ``public.quote_ownership`` (cf. migration
``supabase/migrations/20260505_001_quote_ownership.sql``).

Le payload riche d'un devis (full_name, message, geo_focus, …) reste
sur le filesystem (``backend/uploads/quotes/quote_*.json``) — cette
table sert uniquement d'index requêtable :

  * **Membres d'une org** voient leurs propres devis via le helper RLS
    ``user_orgs()`` (migration ``20260503_001``).
  * **Super-admin Bassira** voit tout via ``service_role`` (RLS bypass).

Helpers exposés
───────────────

* ``link_quote_to_org(quote_id, org_id, *, customer_email, package_id,
  status, client)`` — INSERT idempotent. Si la ligne existe déjà
  (clé primaire ``quote_id``), elle est conservée — pas d'écrasement
  silencieux.
* ``get_org_for_quote(quote_id, *, client)`` → ``org_id (str) | None``.
* ``list_quotes_for_org(org_id, *, limit, offset, client)`` →
  ``[{quote_id, customer_email, package_id, status, created_at}, …]``.
* ``update_quote_status_in_supabase(quote_id, status, *, client)`` —
  miroir best-effort du workflow filesystem (US-103). Échec silencieux
  si la ligne n'existe pas (devis pré-US-114 non encore migré).

Toutes les fonctions acceptent un client injecté en paramètre
``client=`` pour permettre l'injection de doublures pytest sans
dépendance live à Supabase.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..auth.supabase_client import get_supabase_admin
from ..utils.logger import get_logger


logger = get_logger("miroshark.quote_ownership")


_VALID_STATUSES = {
    "received",
    "reviewing",
    "quoted",
    "declined",
    "paid",
    "in_progress",
    "delivered",
}


def link_quote_to_org(
    quote_id: str,
    org_id: str,
    *,
    customer_email: Optional[str] = None,
    package_id: Optional[str] = None,
    status: str = "received",
    payload: Optional[Dict[str, Any]] = None,
    client: Any = None,
) -> bool:
    """INSERT idempotent dans ``public.quote_ownership``.

    Args:
        quote_id : identifiant du devis (format ``q_<hex8>``).
        org_id : UUID de l'org propriétaire.
        customer_email : email saisi à la soumission (peut être None).
        package_id : valeur de ``payload.package`` à la soumission.
        status : statut courant (default ``'received'``).
        payload : payload complet du devis (US-203 — source de vérité
                  Supabase ; le filesystem n'est plus qu'un cache).
        client : client Supabase injecté (pour tests).

    Returns:
        ``True`` si la ligne a été insérée, ``False`` si elle existait
        déjà (idempotence garantie — pas d'erreur remontée).

    Raises:
        ``Exception`` propagée pour toute erreur autre qu'un duplicate.
    """
    if not quote_id or not isinstance(quote_id, str):
        raise ValueError("quote_id is required (str)")
    if not org_id or not isinstance(org_id, str):
        raise ValueError("org_id is required (str)")
    if status not in _VALID_STATUSES:
        raise ValueError(f"Invalid status: {status!r}")

    cli = client or get_supabase_admin()
    row: Dict[str, Any] = {
        "quote_id": quote_id,
        "org_id": org_id,
        "status": status,
    }
    if customer_email:
        row["customer_email"] = customer_email
    if package_id:
        row["package_id"] = package_id
    if payload:
        row["payload"] = payload

    try:
        cli.table("quote_ownership").insert(row).execute()
        return True
    except Exception as exc:  # noqa: BLE001 — duplicate key, etc.
        msg = str(exc)
        if "duplicate" in msg.lower() or "23505" in msg:
            logger.info(
                "quote_ownership already exists for %s — kept as is.",
                quote_id,
            )
            return False
        logger.error(
            "link_quote_to_org failed for %s: %s",
            quote_id, exc.__class__.__name__,
        )
        raise


def get_org_for_quote(quote_id: str, *, client: Any = None) -> Optional[str]:
    """Retourne l'``org_id`` propriétaire du devis, ou ``None`` si absent.

    Returns ``None`` aussi sur erreur Supabase (fail-soft : le caller
    bascule sur le mode legacy filesystem-only).
    """
    if not quote_id or not isinstance(quote_id, str):
        return None
    cli = client or get_supabase_admin()
    try:
        response = (
            cli.table("quote_ownership")
            .select("org_id")
            .eq("quote_id", quote_id)
            .limit(1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        if not rows:
            return None
        org_id = rows[0].get("org_id")
        return org_id if isinstance(org_id, str) and org_id else None
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "get_org_for_quote failed for %s: %s",
            quote_id, exc.__class__.__name__,
        )
        return None


def list_quotes_for_org(
    org_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
    client: Any = None,
) -> List[Dict[str, Any]]:
    """Liste les devis d'une org (du plus récent au plus ancien).

    Returns une liste de dicts au format ``{quote_id, customer_email,
    package_id, status, created_at, org_id}``. Retourne ``[]`` si
    aucun devis ou en cas d'erreur Supabase (fail-soft).
    """
    if not org_id or not isinstance(org_id, str):
        return []
    # Bornes de pagination défensives.
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))

    cli = client or get_supabase_admin()
    try:
        response = (
            cli.table("quote_ownership")
            .select(
                "quote_id, org_id, customer_email, package_id, status, created_at, payload"
            )
            .eq("org_id", org_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return list(rows)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "list_quotes_for_org failed for org_id=%s: %s",
            org_id, exc.__class__.__name__,
        )
        return []


def update_quote_status_in_supabase(
    quote_id: str,
    status: str,
    *,
    client: Any = None,
) -> bool:
    """Miroir best-effort du workflow filesystem (US-103) vers Supabase.

    Mise à jour du champ ``status`` pour le ``quote_id`` donné.
    Idempotent. Retourne ``True`` si la ligne a été mise à jour,
    ``False`` si la ligne n'existait pas (cas devis pré-US-114 non
    encore migré).

    Échec silencieux (logged, pas d'exception remontée) sur erreur
    Supabase — le filesystem reste source de vérité pour le statut.
    """
    if not quote_id or not isinstance(quote_id, str):
        return False
    if status not in _VALID_STATUSES:
        logger.warning("Invalid status %r — skip Supabase mirror", status)
        return False

    cli = client or get_supabase_admin()
    try:
        response = (
            cli.table("quote_ownership")
            .update({"status": status})
            .eq("quote_id", quote_id)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return len(rows) > 0
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "update_quote_status_in_supabase failed for %s: %s",
            quote_id, exc.__class__.__name__,
        )
        return False


def get_quote_payload_from_supabase(
    quote_id: str,
    *,
    client: Any = None,
) -> Optional[Dict[str, Any]]:
    """Retourne le payload complet du devis depuis Supabase (US-203).

    Returns ``None`` si la ligne n'existe pas, si le payload est vide
    (``{}`` — devis pré-US-203 jamais backfillé) ou sur erreur Supabase
    (fail-soft : le caller bascule sur le cache filesystem).
    """
    if not quote_id or not isinstance(quote_id, str):
        return None
    try:
        cli = client or get_supabase_admin()
        response = (
            cli.table("quote_ownership")
            .select("payload")
            .eq("quote_id", quote_id)
            .limit(1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        if not rows:
            return None
        payload = rows[0].get("payload")
        if isinstance(payload, dict) and payload:
            return payload
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "get_quote_payload_from_supabase failed for %s: %s",
            quote_id, exc.__class__.__name__,
        )
        return None


def list_quotes_with_payload(
    *,
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    client: Any = None,
) -> Optional[Dict[str, Any]]:
    """Liste paginée des devis AVEC payload, pour la console admin (US-203).

    Vue super-admin (service_role — voit toutes les orgs). Retourne
    ``{"items": [rows], "total": int}`` où chaque row contient
    ``quote_id, org_id, customer_email, package_id, status, created_at,
    payload``. Retourne ``None`` sur erreur/non-configuré (fail-soft :
    le caller bascule sur le listing filesystem legacy).
    """
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    try:
        cli = client or get_supabase_admin()
        query = (
            cli.table("quote_ownership")
            .select(
                "quote_id, org_id, customer_email, package_id, status, "
                "created_at, payload",
                count="exact",
            )
        )
        if status_filter and status_filter in _VALID_STATUSES:
            query = query.eq("status", status_filter)
        response = (
            query
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        total = getattr(response, "count", None)
        if total is None:
            total = offset + len(rows)
        return {"items": list(rows), "total": int(total)}
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "list_quotes_with_payload failed: %s",
            exc.__class__.__name__,
        )
        return None


def list_quotes_for_orgs(
    org_ids: List[str],
    *,
    limit: int = 200,
    client: Any = None,
) -> List[Dict[str, Any]]:
    """Liste les devis appartenant à un set d'orgs (utilisée par le
    endpoint étendu ``/api/admin/quotes`` quand l'utilisateur est
    membre — pas super-admin).

    Returns ``[]`` si la liste d'orgs est vide ou sur erreur Supabase.
    """
    if not org_ids:
        return []
    cli = client or get_supabase_admin()
    try:
        response = (
            cli.table("quote_ownership")
            .select(
                "quote_id, org_id, customer_email, package_id, status, created_at"
            )
            .in_("org_id", list(org_ids))
            .order("created_at", desc=True)
            .limit(max(1, min(int(limit), 1000)))
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return list(rows)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "list_quotes_for_orgs failed: %s",
            exc.__class__.__name__,
        )
        return []
