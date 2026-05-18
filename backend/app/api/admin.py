"""Internal admin analytics endpoint (US-065).

Exposes ``GET /api/admin/analytics`` — a single aggregate read
that powers the founders/operators dashboard at ``/admin/analytics``
on the SPA. The dashboard's audience is the Bassira team itself
(Amine + co-operators), and the goal is "read the platform state in
30 seconds". So the endpoint computes everything in one pass:

  * **KPIs** — total simulations recorded in Supabase
    ``simulation_ownership``, completed (``outcome`` jsonb non-null),
    created in the last 30 days, and total quote requests recorded
    in ``quote_ownership``.
  * **Funnel** — coarse acquisition → activation → completion shape
    derived from the same Supabase aggregates (visits is reported as
    ``null`` until we wire a real analytics provider; the dashboard
    renders "—" rather than fabricating a number).
  * **30-day time series** — daily simulation count keyed by
    ``created_at``. Always 30 buckets; days without activity are 0.
  * **Top packages** — top 5 ``package_id`` values across every
    simulation row (filesystem ``template_id`` was deprecated in
    favour of the ``package_id`` column populated at create time).

Data source: **Supabase** (``simulation_ownership`` + ``quote_ownership``)
is the authoritative store since US-114. The previous filesystem
scan (``WONDERWALL_SIMULATION_DATA_DIR``) was decoupled from the
real platform state on ephemeral Coolify volumes and produced
stale numbers — replaced here by Supabase aggregation queries.

Auth: gated on ``BASSIRA_ADMIN_TOKEN`` via the shared
``require_admin_token`` decorator from ``app.api.simulation`` —
same fail-closed semantics as ``POST /publish`` / ``POST /resolve``
/ ``POST /outcome``. Internal-only by design; never expose to
unauthenticated clients.

Robustness contract: when Supabase is unreachable or unconfigured,
every counter/list resolves to ``0`` / ``[]`` rather than raising.
A 500 here would brick the ops dashboard, which is exactly when we
*most* want a signal.
"""

from __future__ import annotations

import re
import traceback
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flask import Blueprint, g, jsonify, request

from ..auth.decorators import (
    is_super_admin_email,
    require_auth,
    require_super_admin,
)
from ..auth.supabase_client import (
    SupabaseConfigError,
    get_supabase_admin,
    set_org_self_service_enabled,
)
from ..utils.logger import get_logger

from .simulation import require_admin_token


admin_bp = Blueprint("admin", __name__)
logger = get_logger("miroshark.api.admin")


# ─── Supabase fetch helpers (defensive — never raise) ────────────────────────


_SIM_FIELDS = "simulation_id, created_at, package_id, is_published, outcome, brier_score"


def _fetch_all_simulation_rows() -> List[Dict[str, Any]]:
    """Read every row from ``simulation_ownership`` for aggregation.

    Returns an empty list on any failure (Supabase unconfigured, network
    error, table missing). The dashboard is read-only ops UI — a hard
    500 here would brick the operator's view of the platform at exactly
    the moment a real signal is most useful.

    Volumes are still small enough (< 10k rows expected mid-term) that a
    full table read in one pass is the simplest correct implementation.
    When we cross that threshold we add pagination + a single materialised
    view; until then SQL aggregation is premature optimisation.
    """
    try:
        cli = get_supabase_admin()
    except SupabaseConfigError as exc:
        logger.warning("admin analytics: Supabase not configured (%s)", exc)
        return []
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "admin analytics: get_supabase_admin failed (%s)",
            exc.__class__.__name__,
        )
        return []

    try:
        resp = (
            cli.table("simulation_ownership")
            .select(_SIM_FIELDS)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        return [r for r in rows if isinstance(r, dict)]
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "admin analytics: simulation_ownership scan failed (%s)",
            exc.__class__.__name__,
        )
        return []


def _fetch_quote_count() -> int:
    """Return the total number of rows in ``quote_ownership``.

    Best-effort : 0 on any failure (Supabase unreachable, table missing).
    Mirrors the simulation fetch contract — never raise.
    """
    try:
        cli = get_supabase_admin()
    except SupabaseConfigError as exc:
        logger.warning("admin analytics quotes: Supabase not configured (%s)", exc)
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "admin analytics quotes: get_supabase_admin failed (%s)",
            exc.__class__.__name__,
        )
        return 0

    try:
        resp = (
            cli.table("quote_ownership")
            .select("quote_id", count="exact")
            .limit(1)
            .execute()
        )
        total = getattr(resp, "count", None)
        if isinstance(total, int) and total >= 0:
            return total
        rows = getattr(resp, "data", None) or []
        return len(rows)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "admin analytics quotes: quote_ownership count failed (%s)",
            exc.__class__.__name__,
        )
        return 0


# ─── Aggregation (pure functions, no I/O) ────────────────────────────────────


def _parse_iso_date(iso_str: Optional[str]) -> Optional[datetime]:
    """Parse a Supabase ``timestamptz`` ISO string into an aware datetime.

    Returns ``None`` for ``None`` / malformed input so a single bad row
    can't poison the aggregation.
    """
    if not iso_str or not isinstance(iso_str, str):
        return None
    s = iso_str.strip()
    if not s:
        return None
    # Supabase returns ``2026-05-18T14:30:00.123456+00:00`` — Python 3.11+
    # ``fromisoformat`` parses that natively; for older shapes (``Z`` suffix)
    # we normalise here defensively.
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def _build_time_series_30d(sim_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a 30-element list ``[{date: YYYY-MM-DD, completed: n}, …]``.

    The ``completed`` field name is historical — semantically this is the
    daily count of simulations *created* over the last 30 days (the most
    useful activity signal). The shape is preserved for frontend
    backward-compat.

    Always 30 entries (one per day, oldest → today) so the bar chart
    renders stable axes even on quiet days. Dates are in UTC to keep
    the series deterministic across operator timezones.
    """
    today = datetime.now(timezone.utc).date()
    cutoff = datetime.now(timezone.utc).timestamp() - 30 * 86400
    bucket: Dict[str, int] = {}
    for row in sim_rows:
        dt = _parse_iso_date(row.get("created_at"))
        if dt is None:
            continue
        if dt.timestamp() < cutoff:
            continue
        day = dt.astimezone(timezone.utc).date().isoformat()
        bucket[day] = bucket.get(day, 0) + 1
    series: List[Dict[str, Any]] = []
    for offset in range(29, -1, -1):
        day = (today.fromordinal(today.toordinal() - offset)).isoformat()
        series.append({"date": day, "completed": int(bucket.get(day, 0))})
    return series


def _build_top_packages(
    sim_rows: List[Dict[str, Any]],
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Aggregate the ``package_id`` column across every simulation row."""
    counter: Counter = Counter()
    for row in sim_rows:
        pid = row.get("package_id")
        if isinstance(pid, str) and pid.strip():
            counter[pid.strip()] += 1
    return [{"package": pkg, "n": n} for pkg, n in counter.most_common(limit)]


def _build_kpis(
    sim_rows: List[Dict[str, Any]],
    quotes_count: int,
) -> Dict[str, int]:
    """Compute the four headline numbers shown in the KPI row.

    * ``total``    — total simulation rows.
    * ``completed`` — simulations with a non-null ``outcome`` JSON.
    * ``last_30d`` — simulations created in the last 30 days (activity
      signal — the previous file-based "completed in 30d" rarely fired
      because outcome marking is async).
    * ``quotes``   — total quote_ownership rows.
    """
    cutoff = datetime.now(timezone.utc).timestamp() - 30 * 86400
    completed = 0
    last_30d = 0
    for row in sim_rows:
        outcome = row.get("outcome")
        if isinstance(outcome, dict) and outcome:
            completed += 1
        dt = _parse_iso_date(row.get("created_at"))
        if dt is not None and dt.timestamp() >= cutoff:
            last_30d += 1
    return {
        "total": len(sim_rows),
        "completed": completed,
        "last_30d": last_30d,
        "quotes": quotes_count,
    }


def _build_funnel(kpis: Dict[str, int]) -> List[Dict[str, Any]]:
    """Render the canonical 4-step funnel.

    ``visits`` is intentionally ``None`` until a real analytics provider
    is wired (we refuse to invent a number). The frontend renders
    ``null`` as "—" so the gap is visible to the operator.
    """
    return [
        {"step": "visits", "n": None},
        {"step": "simulations", "n": kpis["total"]},
        {"step": "completed", "n": kpis["completed"]},
        {"step": "quotes", "n": kpis["quotes"]},
    ]


# ─── Route ───────────────────────────────────────────────────────────────────


@admin_bp.route("/analytics", methods=["GET"])
@require_admin_token
def get_admin_analytics():
    """Return the aggregate analytics payload for the ops dashboard.

    Response shape (always ``data`` populated, never ``null``)::

        {
          "success": true,
          "data": {
            "kpis": {"total": N, "completed": N, "last_30d": N, "quotes": N},
            "funnel": [{"step": "visits", "n": null|N}, …],
            "time_series": [{"date": "YYYY-MM-DD", "completed": N}, … (30)],
            "top_packages": [{"package": "<id>", "n": N}, … (≤5)]
          }
        }

    Data source: Supabase ``simulation_ownership`` + ``quote_ownership``.
    Never raises 500 — Supabase outage degrades to zero values rather
    than bricking the ops view.
    """
    try:
        sim_rows = _fetch_all_simulation_rows()
        quotes_count = _fetch_quote_count()

        kpis = _build_kpis(sim_rows, quotes_count)
        funnel = _build_funnel(kpis)
        time_series = _build_time_series_30d(sim_rows)
        top_packages = _build_top_packages(sim_rows)

        return jsonify({
            "success": True,
            "data": {
                "kpis": kpis,
                "funnel": funnel,
                "time_series": time_series,
                "top_packages": top_packages,
            },
        }), 200
    except Exception as exc:  # noqa: BLE001 — last-resort safety net
        logger.error("admin analytics failed: %s\n%s", exc, traceback.format_exc())
        return jsonify({
            "success": False,
            "error_code": "ADMIN_ANALYTICS_FAILED",
            "error": "Could not compute analytics.",
        }), 500


# ─── Super-admin Bassira (US-095) ────────────────────────────────────────────
#
# Endpoints réservés aux founders Bassira (whitelist email via env var
# BASSIRA_SUPER_ADMIN_EMAILS). Permettent de voir TOUTES les organisations
# (cross-tenant) sans avoir à invoquer la console SQL Supabase.
#
# Sécurité :
#   - JWT Supabase valide obligatoire (require_super_admin compose require_auth).
#   - Email vérifié contre la whitelist côté backend uniquement.
#   - service_role bypass RLS — JAMAIS exposé au frontend.
#   - Aucun email logué en clair (hash sha256 court pour audit).


def _err_admin(code: str, message: str, status: int):
    """Réponse d'erreur API standard (cohérent avec le reste du backend)."""
    return jsonify({
        "success": False,
        "error_code": code,
        "error": message,
    }), status


def _aggregate_org_stats(client: Any, org_id: str) -> Dict[str, Any]:
    """Calcule les stats agrégées pour une organisation depuis simulation_ownership.

    Stats :
      - simulations_count : total des sims rattachées
      - published_count   : sims avec is_published = true
      - avg_brier         : moyenne des brier_score non-null (ou None)

    Robustesse : toute erreur Supabase → stats à None pour ne pas brique
    le tableau global (l'opérateur préfère voir « — » qu'un 500).
    """
    try:
        response = (
            client.table("simulation_ownership")
            .select("simulation_id, is_published, brier_score")
            .eq("org_id", org_id)
            .execute()
        )
        rows = getattr(response, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "_aggregate_org_stats failed for org_id=%s: %s",
            org_id, exc.__class__.__name__,
        )
        return {
            "simulations_count": None,
            "published_count": None,
            "avg_brier": None,
        }

    sims_count = len(rows)
    published = sum(1 for r in rows if r.get("is_published") is True)
    briers = [
        float(r["brier_score"])
        for r in rows
        if r.get("brier_score") is not None
    ]
    avg_brier = (sum(briers) / len(briers)) if briers else None
    return {
        "simulations_count": sims_count,
        "published_count": published,
        "avg_brier": round(avg_brier, 4) if avg_brier is not None else None,
    }


def _count_org_members(client: Any, org_id: str) -> Optional[int]:
    """Compte les membres d'une organisation (ou None si erreur Supabase)."""
    try:
        response = (
            client.table("org_members")
            .select("id", count="exact")
            .eq("org_id", org_id)
            .execute()
        )
        # Le SDK supabase-py expose `count` quand `count="exact"`.
        count = getattr(response, "count", None)
        if count is None:
            # Fallback : compter les lignes retournées si le SDK ne remonte
            # pas le `count` (variante de version).
            rows = getattr(response, "data", None) or []
            count = len(rows)
        return int(count)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "_count_org_members failed for org_id=%s: %s",
            org_id, exc.__class__.__name__,
        )
        return None


@admin_bp.route("/me/super-status", methods=["GET"])
@require_auth
def get_super_status():
    """Indique si l'utilisateur authentifié est super-admin Bassira.

    Endpoint léger appelé par le frontend (AppHeader.vue + AnalyticsView)
    pour conditionner l'affichage de l'entrée nav « Admin » et la section
    « Toutes les organisations ». Ne nécessite pas le rôle super-admin
    lui-même (un user normal reçoit `is_super_admin: false`).

    Response::

        { "success": true, "data": { "is_super_admin": bool, "email": str } }
    """
    user = getattr(g, "current_user", None) or {}
    email = user.get("email")
    is_super = is_super_admin_email(email)
    return jsonify({
        "success": True,
        "data": {
            "is_super_admin": bool(is_super),
            "email": email,
        },
    }), 200


@admin_bp.route("/organizations", methods=["GET"])
@require_super_admin
def list_all_organizations():
    """Liste TOUTES les organisations Bassira (super-admin only).

    Utilise `get_supabase_admin()` (service_role bypass RLS) pour lire
    `public.organizations` + agréger les stats par org.

    Response::

        {
          "success": true,
          "data": {
            "organizations": [
              {
                "id": "uuid",
                "slug": "...",
                "name": "...",
                "sector": "...",
                "country_code": "...",
                "status": "active|suspended|trial",
                "created_at": "...",
                "members_count": int|null,
                "simulations_count": int|null,
                "published_count": int|null,
                "avg_brier": float|null
              }
            ]
          }
        }
    """
    try:
        cli = get_supabase_admin()
    except SupabaseConfigError as exc:
        logger.error("Supabase admin config missing: %s", exc)
        return _err_admin(
            "SUPABASE_NOT_CONFIGURED",
            "Backend Supabase admin client is not configured.",
            503,
        )

    # US-098 — on tente de lire self_service_enabled. Si la colonne n'existe
    # pas (migration pas jouée), on retombe sur le SELECT historique.
    select_with_ss = (
        "id, slug, name, sector, country_code, status, created_at, "
        "self_service_enabled"
    )
    select_legacy = "id, slug, name, sector, country_code, status, created_at"
    try:
        response = (
            cli.table("organizations")
            .select(select_with_ss)
            .order("created_at", desc=True)
            .execute()
        )
        orgs = getattr(response, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "self_service_enabled" in msg or "column" in msg:
            logger.warning(
                "self_service_enabled column missing in list_all_organizations — "
                "fallback to legacy SELECT. Run migration 20260504_001."
            )
            try:
                response = (
                    cli.table("organizations")
                    .select(select_legacy)
                    .order("created_at", desc=True)
                    .execute()
                )
                orgs = getattr(response, "data", None) or []
            except Exception as exc2:  # noqa: BLE001
                logger.error(
                    "list_all_organizations legacy select failed: %s",
                    exc2.__class__.__name__,
                )
                return _err_admin(
                    "ADMIN_ORGS_FAILED",
                    "Could not list organizations.",
                    500,
                )
        else:
            logger.error(
                "list_all_organizations select failed: %s",
                exc.__class__.__name__,
            )
            return _err_admin(
                "ADMIN_ORGS_FAILED",
                "Could not list organizations.",
                500,
            )

    enriched: List[Dict[str, Any]] = []
    for org in orgs:
        org_id = org.get("id")
        if not org_id:
            continue
        stats = _aggregate_org_stats(cli, org_id)
        members_count = _count_org_members(cli, org_id)
        enriched.append({
            "id": org_id,
            "slug": org.get("slug"),
            "name": org.get("name"),
            "sector": org.get("sector"),
            "country_code": org.get("country_code"),
            "status": org.get("status"),
            "created_at": org.get("created_at"),
            "self_service_enabled": bool(org.get("self_service_enabled", False)),
            "members_count": members_count,
            **stats,
        })

    return jsonify({
        "success": True,
        "data": {
            "organizations": enriched,
        },
    }), 200


@admin_bp.route("/organizations/<org_id>", methods=["GET"])
@require_super_admin
def get_organization_detail(org_id: str):
    """Détail d'une organisation : metadata + members + simulations.

    Response::

        {
          "success": true,
          "data": {
            "organization": { id, slug, name, sector, country_code, status, created_at, metadata },
            "members": [{ user_id, email, role, created_at }, ...],
            "simulations": [{
              simulation_id, package_id, is_published, outcome, brier_score, created_at
            }, ...]
          }
        }
    """
    if not org_id or not isinstance(org_id, str):
        return _err_admin("INVALID_ORG_ID", "org_id is required.", 400)

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError as exc:
        logger.error("Supabase admin config missing: %s", exc)
        return _err_admin(
            "SUPABASE_NOT_CONFIGURED",
            "Backend Supabase admin client is not configured.",
            503,
        )

    # 1. Organisation
    try:
        org_resp = (
            cli.table("organizations")
            .select("id, slug, name, sector, country_code, status, created_at, metadata")
            .eq("id", org_id)
            .limit(1)
            .execute()
        )
        org_rows = getattr(org_resp, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "get_organization_detail org select failed: %s",
            exc.__class__.__name__,
        )
        return _err_admin("ADMIN_ORG_FAILED", "Could not load organization.", 500)

    if not org_rows:
        return _err_admin("ORG_NOT_FOUND", "Organization not found.", 404)
    organization = org_rows[0]

    # 2. Members — JOIN logique sur auth.users via user_id (l'email vit
    # dans auth.users, le SDK ne fait pas de JOIN cross-schema natif, on
    # le résout en deux étapes : lire org_members puis appeler
    # auth.admin.get_user_by_id si dispo, sinon retourner uniquement le
    # user_id. Pour rester fail-soft, on tente l'enrichissement et on
    # retombe gracieusement en `email: None` en cas d'erreur).
    members: List[Dict[str, Any]] = []
    try:
        members_resp = (
            cli.table("org_members")
            .select("user_id, role, created_at")
            .eq("org_id", org_id)
            .execute()
        )
        member_rows = getattr(members_resp, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "get_organization_detail members select failed: %s",
            exc.__class__.__name__,
        )
        member_rows = []

    for row in member_rows:
        user_id = row.get("user_id")
        email: Optional[str] = None
        if user_id:
            try:
                # supabase-py expose `auth.admin.get_user_by_id` quand le
                # client est initialisé avec service_role.
                admin_auth = getattr(cli, "auth", None)
                admin_api = getattr(admin_auth, "admin", None) if admin_auth else None
                if admin_api and hasattr(admin_api, "get_user_by_id"):
                    user_resp = admin_api.get_user_by_id(user_id)
                    user_obj = getattr(user_resp, "user", None) or user_resp
                    email = getattr(user_obj, "email", None) or (
                        user_obj.get("email") if isinstance(user_obj, dict) else None
                    )
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "get_user_by_id failed for member %s: %s",
                    user_id, exc.__class__.__name__,
                )
        members.append({
            "user_id": user_id,
            "email": email,
            "role": row.get("role"),
            "created_at": row.get("created_at"),
        })

    # 3. Simulations
    try:
        sims_resp = (
            cli.table("simulation_ownership")
            .select(
                "simulation_id, package_id, is_published, outcome, "
                "brier_score, created_at, created_by"
            )
            .eq("org_id", org_id)
            .order("created_at", desc=True)
            .execute()
        )
        sim_rows = getattr(sims_resp, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "get_organization_detail sims select failed: %s",
            exc.__class__.__name__,
        )
        sim_rows = []

    simulations = [
        {
            "simulation_id": s.get("simulation_id"),
            "package_id": s.get("package_id"),
            "is_published": bool(s.get("is_published")),
            "outcome": s.get("outcome"),
            "brier_score": s.get("brier_score"),
            "created_at": s.get("created_at"),
            "created_by": s.get("created_by"),
        }
        for s in sim_rows
    ]

    return jsonify({
        "success": True,
        "data": {
            "organization": organization,
            "members": members,
            "simulations": simulations,
        },
    }), 200


# ─── US-097 — Toutes les simulations cross-tenant ────────────────────────────
#
# Endpoint super-admin pour lister TOUTES les simulations Bassira, toutes
# orgs confondues. Permet à l'opérateur d'auditer la plateforme en
# identifiant rapidement les sims problématiques sans avoir à drill-down
# org par org.
#
# Filtres (query string) :
#   ?org_id=<uuid>            — filtre sur une org précise
#   ?package_id=<id>          — filtre sur un template_id (ex: 'fusion-bancaire-mena')
#   ?status=<state>           — filtre sur le statut filesystem (loose match)
#   ?published=true|false     — filtre sur is_published
#   ?limit=<n>                — pagination (default 50, max 200)
#   ?offset=<n>               — pagination (default 0)
#
# Pour la cohérence : on ne lit pas les statuts depuis simulation_ownership
# (la table ne stocke pas le status filesystem évolutif). À la place on
# filtre côté Python sur les sims retournées.

_ADMIN_SIMS_DEFAULT_LIMIT = 50
_ADMIN_SIMS_MAX_LIMIT = 200


def _parse_published_filter(raw: Optional[str]) -> Optional[bool]:
    """Parse le query param `published` en bool|None (None = pas de filtre)."""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if s in {"true", "1", "yes"}:
        return True
    if s in {"false", "0", "no"}:
        return False
    return None  # valeur invalide → pas de filtre (silent)


def _parse_int_param(raw: Optional[str], default: int, min_val: int, max_val: int) -> int:
    """Parse un query param numérique en bornant à [min_val, max_val]."""
    if raw is None:
        return default
    try:
        n = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return max(min_val, min(max_val, n))


def _enrich_sims_with_org_info(
    client: Any,
    sims: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Enrichit chaque sim avec org_name + org_slug en lookup batch.

    On lit toutes les org_id distinctes en une requête puis on indexe
    en mémoire pour éviter N+1 queries.
    """
    org_ids = {s.get("org_id") for s in sims if s.get("org_id")}
    org_index: Dict[str, Dict[str, Any]] = {}
    if org_ids:
        try:
            resp = (
                client.table("organizations")
                .select("id, slug, name")
                .in_("id", list(org_ids))
                .execute()
            )
            rows = getattr(resp, "data", None) or []
            for row in rows:
                org_index[row.get("id")] = row
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "_enrich_sims_with_org_info batch lookup failed: %s",
                exc.__class__.__name__,
            )

    out: List[Dict[str, Any]] = []
    for s in sims:
        org_id = s.get("org_id")
        org_meta = org_index.get(org_id, {}) if org_id else {}
        out.append({
            "simulation_id": s.get("simulation_id"),
            "org_id": org_id,
            "org_name": org_meta.get("name"),
            "org_slug": org_meta.get("slug"),
            "created_by": s.get("created_by"),
            "created_at": s.get("created_at"),
            "package_id": s.get("package_id"),
            "is_published": bool(s.get("is_published")),
            "outcome": s.get("outcome"),
            "brier_score": s.get("brier_score"),
        })
    return out


@admin_bp.route("/simulations", methods=["GET"])
@require_super_admin
def list_all_simulations():
    """Liste TOUTES les simulations cross-tenant (super-admin only).

    Query params : org_id, package_id, published (true|false), limit, offset.

    Response::

        {
          "success": true,
          "data": {
            "simulations": [
              {
                "simulation_id": "...",
                "org_id": "...", "org_name": "...", "org_slug": "...",
                "created_by": "...", "created_at": "...",
                "package_id": "...", "is_published": bool,
                "outcome": {...}|null, "brier_score": float|null
              }, ...
            ],
            "total": int,
            "limit": int,
            "offset": int
          }
        }
    """
    from flask import request as _req

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError as exc:
        logger.error("Supabase admin config missing: %s", exc)
        return _err_admin(
            "SUPABASE_NOT_CONFIGURED",
            "Backend Supabase admin client is not configured.",
            503,
        )

    org_id_filter = (_req.args.get("org_id") or "").strip() or None
    package_id_filter = (_req.args.get("package_id") or "").strip() or None
    published_filter = _parse_published_filter(_req.args.get("published"))
    limit = _parse_int_param(
        _req.args.get("limit"),
        _ADMIN_SIMS_DEFAULT_LIMIT, 1, _ADMIN_SIMS_MAX_LIMIT,
    )
    offset = _parse_int_param(_req.args.get("offset"), 0, 0, 1_000_000)

    try:
        query = (
            cli.table("simulation_ownership")
            .select(
                "simulation_id, org_id, created_by, created_at, package_id, "
                "is_published, outcome, brier_score",
                count="exact",
            )
        )
        if org_id_filter:
            query = query.eq("org_id", org_id_filter)
        if package_id_filter:
            query = query.eq("package_id", package_id_filter)
        if published_filter is not None:
            query = query.eq("is_published", published_filter)
        # Pagination + tri DESC
        query = query.order("created_at", desc=True).range(
            offset, offset + limit - 1
        )
        resp = query.execute()
        sims = getattr(resp, "data", None) or []
        total = getattr(resp, "count", None)
        if total is None:
            # Fallback : si le SDK ne remonte pas le count, estimation basée
            # sur la page courante (l'opérateur le saura via la doc UI).
            total = len(sims) + offset
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "list_all_simulations select failed: %s",
            exc.__class__.__name__,
        )
        return _err_admin(
            "ADMIN_SIMS_FAILED",
            "Could not list simulations.",
            500,
        )

    enriched = _enrich_sims_with_org_info(cli, sims)

    return jsonify({
        "success": True,
        "data": {
            "simulations": enriched,
            "total": int(total),
            "limit": limit,
            "offset": offset,
        },
    }), 200


# ─── US-098 — Toggle self_service_enabled par organisation ───────────────────


@admin_bp.route("/organizations/<org_id>/self-service", methods=["PATCH"])
@require_super_admin
def patch_org_self_service(org_id: str):
    """Active / désactive le self-service pour une organisation (super-admin only).

    Body JSON : ``{"enabled": true|false}``

    Response 200 :
        {"success": true, "data": {"org_id": "...", "self_service_enabled": bool}}

    Codes d'erreur :
        - 400 INVALID_BODY (body manquant ou mauvais type)
        - 404 ORG_NOT_FOUND (org_id inconnu)
        - 503 SUPABASE_NOT_CONFIGURED
        - 500 ADMIN_TOGGLE_FAILED
    """
    from flask import request as _req

    if not org_id or not isinstance(org_id, str):
        return _err_admin("INVALID_ORG_ID", "org_id is required.", 400)

    payload = _req.get_json(silent=True) or {}
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        return _err_admin(
            "INVALID_BODY",
            "Body must be JSON {'enabled': true|false}.",
            400,
        )

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError as exc:
        logger.error("Supabase admin config missing: %s", exc)
        return _err_admin(
            "SUPABASE_NOT_CONFIGURED",
            "Backend Supabase admin client is not configured.",
            503,
        )

    try:
        updated = set_org_self_service_enabled(org_id, enabled, client=cli)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "patch_org_self_service failed for org_id=%s: %s",
            org_id, exc.__class__.__name__,
        )
        return _err_admin(
            "ADMIN_TOGGLE_FAILED",
            "Could not update self_service_enabled.",
            500,
        )

    if not updated:
        return _err_admin("ORG_NOT_FOUND", "Organization not found.", 404)

    logger.info(
        "self_service_enabled set to %s for org_id=%s by super-admin",
        enabled, org_id,
    )
    return jsonify({
        "success": True,
        "data": {
            "org_id": org_id,
            "self_service_enabled": bool(enabled),
        },
    }), 200


# ─── POST /api/admin/organizations (US-138) ────────────────────────────────────


_ORG_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def _slugify(name: str) -> str:
    """Génère un slug minuscule kebab-case depuis un nom d'organisation."""
    s = (name or "").lower().strip()
    # Translittération basique des accents FR/AR vers ASCII
    replacements = {
        "à": "a", "â": "a", "ä": "a", "á": "a", "ã": "a",
        "ç": "c",
        "è": "e", "é": "e", "ê": "e", "ë": "e",
        "ì": "i", "í": "i", "î": "i", "ï": "i",
        "ò": "o", "ó": "o", "ô": "o", "ö": "o", "õ": "o",
        "ù": "u", "ú": "u", "û": "u", "ü": "u",
        "ñ": "n", "ý": "y", "ÿ": "y",
        "œ": "oe", "æ": "ae", "ß": "ss",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    s = s.replace(" ", "-").replace("_", "-")
    s = _ORG_SLUG_RE.sub("", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "org"


@admin_bp.route("/organizations", methods=["POST"])
@require_super_admin
def create_organization():
    """Crée une nouvelle organisation Bassira (super-admin only).

    Body JSON ::

        {
          "name": str (requis),
          "slug": str (optionnel — auto-généré depuis name si absent),
          "country_code": str (optionnel, ISO-2, ex "MA"),
          "sector": str (optionnel, ex "finance"),
          "self_service_enabled": bool (optionnel, défaut false)
        }

    Side effect : ajoute le caller comme `owner` dans `org_members`
    pour qu'il puisse gérer cette org tout de suite.

    Response : 201 ::
        { "success": true, "data": { "id", "slug", "name", ... } }
    """
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return _err_admin("MISSING_NAME", "name is required.", 400)
    if len(name) > 200:
        return _err_admin("NAME_TOO_LONG", "name must be 200 characters or less.", 400)

    slug = (body.get("slug") or "").strip().lower() or _slugify(name)
    if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", slug):
        return _err_admin(
            "INVALID_SLUG",
            "slug doit contenir uniquement [a-z0-9-] et commencer/finir par alphanum.",
            400,
        )

    country_code = (body.get("country_code") or "").strip().upper()
    if country_code and not re.match(r"^[A-Z]{2}$", country_code):
        return _err_admin("INVALID_COUNTRY_CODE", "country_code must be ISO-2 (e.g. MA, FR).", 400)
    sector = (body.get("sector") or "").strip() or None
    self_service_enabled = bool(body.get("self_service_enabled", False))

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err_admin(
            "SUPABASE_NOT_CONFIGURED",
            "Backend Supabase admin client is not configured.",
            503,
        )

    # Insérer l'organisation
    org_payload: Dict[str, Any] = {
        "name": name,
        "slug": slug,
        "status": "active",
    }
    if country_code:
        org_payload["country_code"] = country_code
    if sector:
        org_payload["sector"] = sector

    # self_service_enabled : essai avec, fallback sans (cf. pattern existant US-098)
    payload_with_ss = dict(org_payload, self_service_enabled=self_service_enabled)
    new_org: Dict[str, Any]
    try:
        resp = cli.table("organizations").insert(payload_with_ss).execute()
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise RuntimeError("INSERT returned no rows")
        new_org = rows[0]
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            return _err_admin(
                "SLUG_ALREADY_EXISTS",
                f"Une organisation existe déjà avec le slug '{slug}'.",
                409,
            )
        if "self_service_enabled" in msg or "column" in msg:
            try:
                resp = cli.table("organizations").insert(org_payload).execute()
                rows = getattr(resp, "data", None) or []
                if not rows:
                    raise RuntimeError("INSERT returned no rows (legacy)")
                new_org = rows[0]
            except Exception as exc2:  # noqa: BLE001
                logger.error("create_organization fallback insert failed: %s", exc2.__class__.__name__)
                return _err_admin(
                    "ADMIN_CREATE_ORG_FAILED",
                    "Could not create organization.",
                    500,
                )
        else:
            logger.error("create_organization insert failed: %s", exc.__class__.__name__)
            return _err_admin(
                "ADMIN_CREATE_ORG_FAILED",
                "Could not create organization.",
                500,
            )

    org_id = new_org.get("id")
    if not org_id:
        logger.error("create_organization: created row missing id field")
        return _err_admin("ADMIN_CREATE_ORG_FAILED", "Organization created but id missing.", 500)

    # Auto-add caller as owner — best-effort (la création réussit même
    # si l'ajout échoue ; le super-admin pourra se rajouter manuellement).
    user = getattr(g, "current_user", None) or {}
    caller_uid = user.get("id")
    if caller_uid:
        try:
            cli.table("org_members").upsert(
                {"user_id": caller_uid, "org_id": org_id, "role": "owner"},
                on_conflict="user_id,org_id",
            ).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "create_organization: could not auto-add caller %s as owner of %s : %s",
                caller_uid, org_id, exc.__class__.__name__,
            )

    logger.info("Organization created : id=%s slug=%s name=%r", org_id, slug, name)

    return jsonify({
        "success": True,
        "data": {
            "id": org_id,
            "slug": new_org.get("slug") or slug,
            "name": new_org.get("name") or name,
            "country_code": new_org.get("country_code") or country_code or None,
            "sector": new_org.get("sector") or sector,
            "status": new_org.get("status") or "active",
            "self_service_enabled": bool(new_org.get("self_service_enabled", self_service_enabled)),
            "created_at": new_org.get("created_at"),
        },
    }), 201
