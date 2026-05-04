"""Client Supabase admin (service_role) + helpers ownership (US-092).

Ce module fournit un singleton `get_supabase_admin()` initialisé avec la
clé `SUPABASE_SERVICE_ROLE_KEY`. Cette clé contourne RLS et n'est donc
JAMAIS exposée hors du backend (cf. rules/supabase.md). Toutes les
écritures / lectures cross-org effectuées par le backend Flask passent
par ce client (création d'orgs, attribution de simulations, marquage
d'outcomes, publication, lecture des aggregates).

Helpers exposés :
    - get_user_orgs(user_id)
    - get_user_role_in_org(user_id, org_id)
    - record_simulation_ownership(simulation_id, org_id, user_id, package_id?)
    - get_simulation_owner(simulation_id)
    - mark_outcome(simulation_id, label, observed_at, source_url, brier_score, marker_user_id)
    - publish_simulation(simulation_id, marker_user_id)
    - get_public_calibration_aggregates()

Tests : `get_supabase_admin()` est conçu pour être monkeypatché. Les
helpers prennent le client en paramètre optionnel (`client=`) pour
permettre l'injection de doublures en pytest sans dépendance live.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger


logger = get_logger("miroshark.auth.supabase")


# ─── Singleton client admin ─────────────────────────────────────────────────

_client_singleton = None
_client_lock = threading.Lock()


class SupabaseConfigError(RuntimeError):
    """Erreur levée quand la configuration Supabase est manquante.

    Exposée au niveau API par les décorateurs sous forme de 503
    (`SUPABASE_NOT_CONFIGURED`) afin que l'opérateur voie immédiatement
    qu'une variable d'environnement Coolify est manquante.
    """


def _build_admin_client():
    """Instancie un nouveau client Supabase admin.

    Doit être appelé **une fois** (cf. `get_supabase_admin`). On lazy-
    importe `create_client` afin de ne pas alourdir le démarrage du
    backend quand le module est seulement importé pour les décorateurs
    ou les helpers (qui peuvent prendre un client injecté en test).
    """
    url = os.getenv("SUPABASE_URL", "").strip()
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not service_key:
        raise SupabaseConfigError(
            "SUPABASE_URL and/or SUPABASE_SERVICE_ROLE_KEY are not set. "
            "Configure them in Coolify environment variables."
        )

    try:
        from supabase import create_client  # type: ignore
    except ImportError as exc:  # pragma: no cover — pyproject pin l'install
        raise SupabaseConfigError(
            "supabase Python SDK is not installed (pyproject.toml)."
        ) from exc

    logger.info("Supabase admin client initialized (service_role).")
    return create_client(url, service_key)


def get_supabase_admin():
    """Retourne le client Supabase admin (singleton process-wide).

    Le client est initialisé paresseusement et partagé par tous les
    threads (Flask request workers). Pas de risque de fuite de la clé :
    elle reste dans le process backend et n'est jamais sérialisée vers
    le frontend.
    """
    global _client_singleton
    if _client_singleton is not None:
        return _client_singleton
    with _client_lock:
        if _client_singleton is None:
            _client_singleton = _build_admin_client()
    return _client_singleton


def reset_supabase_admin() -> None:
    """Vide le singleton (utilisé par les tests pour réinitialiser)."""
    global _client_singleton
    with _client_lock:
        _client_singleton = None


# ─── Helpers métier ─────────────────────────────────────────────────────────

def get_user_orgs(user_id: str, client: Any = None) -> List[Dict[str, Any]]:
    """Liste des organisations auxquelles l'utilisateur appartient.

    Effectue un JOIN logique côté Supabase :
      `org_members.role` + `organizations.{id, slug, name, sector,
      country_code, status, self_service_enabled}`.

    Returns:
        Une liste de dicts au format :
        ``[{"id": uuid, "slug": str, "name": str, "sector": str|None,
            "country_code": str|None, "status": str, "role": str,
            "self_service_enabled": bool}, ...]``
        — vide si l'utilisateur n'est rattaché à aucune org.

    Note US-098 : `self_service_enabled` peut être absent si la migration
    003 n'a pas encore été jouée côté DB. Dans ce cas, on retombe à
    `False` (sécurité par défaut).
    """
    cli = client or get_supabase_admin()
    # Le SDK Python supporte l'embed Postgrest : `organizations(...)`.
    # On tente avec self_service_enabled (US-098). Si la colonne n'existe
    # pas encore (migration 003 non jouée), on retombe sans cette colonne.
    select_with_ss = (
        "role, org_id, "
        "organizations(id, slug, name, sector, country_code, status, self_service_enabled)"
    )
    select_legacy = (
        "role, org_id, "
        "organizations(id, slug, name, sector, country_code, status)"
    )
    try:
        response = (
            cli.table("org_members")
            .select(select_with_ss)
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001 — colonne absente ?
        msg = str(exc).lower()
        if "self_service_enabled" in msg or "column" in msg:
            logger.warning(
                "self_service_enabled column missing — falling back. "
                "Run migration 20260504_001_org_self_service.sql in SQL Editor."
            )
            response = (
                cli.table("org_members")
                .select(select_legacy)
                .eq("user_id", user_id)
                .execute()
            )
        else:
            raise

    rows = getattr(response, "data", None) or []
    out: List[Dict[str, Any]] = []
    for row in rows:
        org = row.get("organizations") or {}
        if not org:
            continue
        out.append(
            {
                "id": org.get("id"),
                "slug": org.get("slug"),
                "name": org.get("name"),
                "sector": org.get("sector"),
                "country_code": org.get("country_code"),
                "status": org.get("status"),
                "self_service_enabled": bool(org.get("self_service_enabled", False)),
                "role": row.get("role"),
            }
        )
    return out


def is_org_self_service_enabled(org_id: str, client: Any = None) -> bool:
    """Retourne True si l'org a `self_service_enabled = true` (US-098).

    Sécurité par défaut : toute erreur Supabase / colonne manquante / org
    introuvable → False. L'opérateur active explicitement le flag via
    l'UI super-admin ou par SQL direct ; pas d'auto-activation.
    """
    cli = client or get_supabase_admin()
    try:
        response = (
            cli.table("organizations")
            .select("self_service_enabled")
            .eq("id", org_id)
            .limit(1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        if not rows:
            return False
        return bool(rows[0].get("self_service_enabled", False))
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "is_org_self_service_enabled failed for org_id=%s: %s",
            org_id, exc.__class__.__name__,
        )
        return False


def set_org_self_service_enabled(
    org_id: str,
    enabled: bool,
    client: Any = None,
) -> bool:
    """Met à jour `self_service_enabled` pour une org (US-098).

    Pré-condition : appelé uniquement depuis un endpoint @require_super_admin.

    Returns:
        True si la mise à jour a affecté >=1 ligne, False sinon
        (org introuvable, erreur Supabase).
    """
    cli = client or get_supabase_admin()
    try:
        response = (
            cli.table("organizations")
            .update({"self_service_enabled": bool(enabled)})
            .eq("id", org_id)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return len(rows) > 0
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "set_org_self_service_enabled failed for org_id=%s: %s",
            org_id, exc.__class__.__name__,
        )
        raise


def get_user_role_in_org(user_id: str, org_id: str, client: Any = None) -> Optional[str]:
    """Retourne le rôle de l'utilisateur dans l'org donnée, ou `None`."""
    cli = client or get_supabase_admin()
    response = (
        cli.table("org_members")
        .select("role")
        .eq("user_id", user_id)
        .eq("org_id", org_id)
        .limit(1)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    if not rows:
        return None
    role = rows[0].get("role")
    return role if isinstance(role, str) and role else None


def record_simulation_ownership(
    simulation_id: str,
    org_id: str,
    user_id: Optional[str] = None,
    package_id: Optional[str] = None,
    client: Any = None,
) -> None:
    """Enregistre une simulation comme appartenant à une org.

    Idempotent : un INSERT...ON CONFLICT côté Supabase (la clé primaire
    est `simulation_id`). Si la sim est déjà tracée, la ligne existante
    n'est pas écrasée — on log un warning et on retourne sans erreur.
    """
    cli = client or get_supabase_admin()
    payload: Dict[str, Any] = {
        "simulation_id": simulation_id,
        "org_id": org_id,
    }
    if user_id:
        payload["created_by"] = user_id
    if package_id:
        payload["package_id"] = package_id
    try:
        cli.table("simulation_ownership").insert(payload).execute()
    except Exception as exc:  # noqa: BLE001 — duplicate key, etc.
        # On garde l'idempotence : si la ligne existe déjà, on ne
        # remonte pas l'erreur au caller. Tout autre problème est
        # logué (sans token ni JWT) avant d'être ré-émis.
        msg = str(exc)
        if "duplicate" in msg.lower() or "23505" in msg:
            logger.info(
                "simulation_ownership already exists for %s — kept as is.",
                simulation_id,
            )
            return
        logger.error(
            "record_simulation_ownership failed for %s: %s",
            simulation_id, exc.__class__.__name__,
        )
        raise


def get_simulation_owner(simulation_id: str, client: Any = None) -> Optional[Dict[str, Any]]:
    """Retourne la ligne ownership pour une sim, ou `None` si absente."""
    cli = client or get_supabase_admin()
    response = (
        cli.table("simulation_ownership")
        .select(
            "simulation_id, org_id, created_by, package_id, is_published, "
            "outcome, brier_score, created_at"
        )
        .eq("simulation_id", simulation_id)
        .limit(1)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    if not rows:
        return None
    return rows[0]


def mark_outcome(
    simulation_id: str,
    label: str,
    observed_at: str,
    source_url: Optional[str],
    brier_score: Optional[float],
    marker_user_id: Optional[str],
    client: Any = None,
) -> None:
    """Marque l'outcome d'une simulation.

    Args:
        label : `called_it` | `partial` | `wrong`.
        observed_at : ISO 8601.
        source_url : URL publique du fait observé (peut être None).
        brier_score : float dans [0, 1] (peut être None).
        marker_user_id : utilisateur ayant marqué l'outcome.

    Pré-condition : l'autorisation `role >= admin` doit avoir été
    vérifiée par le décorateur en amont.
    """
    if label not in {"called_it", "partial", "wrong"}:
        raise ValueError(f"Invalid outcome label: {label!r}")
    cli = client or get_supabase_admin()
    outcome_payload: Dict[str, Any] = {
        "label": label,
        "observed_at": observed_at,
        "marked_by": marker_user_id,
        "marked_at": datetime.now(timezone.utc).isoformat(),
    }
    if source_url:
        outcome_payload["source_url"] = source_url

    update: Dict[str, Any] = {"outcome": outcome_payload}
    if brier_score is not None:
        update["brier_score"] = float(brier_score)

    cli.table("simulation_ownership").update(update).eq(
        "simulation_id", simulation_id
    ).execute()


def publish_simulation(
    simulation_id: str,
    marker_user_id: Optional[str],
    client: Any = None,
) -> None:
    """Bascule `is_published = true` pour exposer la sim dans la VIEW agrégée.

    L'identité du marker est conservée dans `metadata.published_by`
    pour audit (sans modifier le schéma).
    """
    cli = client or get_supabase_admin()
    metadata_patch = {
        "published_by": marker_user_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    # On utilise l'opérateur `set` du SDK pour mettre à jour les deux
    # colonnes en une seule requête. Postgres mergera le jsonb metadata
    # côté serveur via une expression jsonb_concat — ici on remplace
    # simplement le metadata complet (taille négligeable, pas de besoin
    # d'une opération atomique multi-clés sur ce champ).
    cli.table("simulation_ownership").update(
        {"is_published": True, "metadata": metadata_patch}
    ).eq("simulation_id", simulation_id).execute()


def get_public_calibration_aggregates(client: Any = None) -> List[Dict[str, Any]]:
    """Lit la VIEW publique `public_calibration_aggregates` (k-anonymity n>=5).

    La VIEW est définie en migration 002 et expose uniquement des lignes
    où `n_published >= 5`. Aucune donnée individuelle ne fuit.
    """
    cli = client or get_supabase_admin()
    response = (
        cli.table("public_calibration_aggregates")
        .select("*")
        .execute()
    )
    rows = getattr(response, "data", None) or []
    return list(rows)


# ─── Hiérarchie des rôles ───────────────────────────────────────────────────
#
# Utilisée par `decorators.require_org_membership` pour comparer le rôle
# effectif de l'utilisateur au rôle minimal exigé par la route. La
# hiérarchie suit le contrat documenté en migration 001 :
#     owner > admin > member > viewer
#
# Une fonction libre est fournie ici pour pouvoir être testée en
# isolation et réutilisée par `simulation_manager.is_user_authorized_to_read`.

ROLE_RANK: Dict[str, int] = {
    "viewer": 1,
    "member": 2,
    "admin": 3,
    "owner": 4,
}


def role_meets_minimum(actual_role: Optional[str], min_role: str) -> bool:
    """Retourne True si `actual_role` est >= `min_role` dans la hiérarchie."""
    if not actual_role:
        return False
    actual_rank = ROLE_RANK.get(actual_role, 0)
    min_rank = ROLE_RANK.get(min_role, 0)
    if actual_rank == 0 or min_rank == 0:
        return False
    return actual_rank >= min_rank
