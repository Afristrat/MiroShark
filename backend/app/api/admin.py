"""Internal admin analytics endpoint (US-065).

Exposes ``GET /api/admin/analytics`` — a single aggregate read
that powers the founders/operators dashboard at ``/admin/analytics``
on the SPA. The dashboard's audience is the Bassira team itself
(Amine + co-operators), and the goal is "read the platform state in
30 seconds". So the endpoint computes everything in one pass:

  * **KPIs** — total simulations on disk, completed (``outcome.json``
    present), completed in the last 30 days, and total persisted
    quote requests (``WONDERWALL_DATA_DIR/quotes/quote_*.json``).
  * **Funnel** — coarse acquisition → activation → completion shape
    derived from the same disk inputs (visits is reported as ``null``
    until we wire a real analytics provider; the dashboard renders
    "—" rather than fabricating a number).
  * **30-day time series** — daily ``completed`` count keyed by the
    ``mtime`` of each ``outcome.json``. Sparse on a fresh deploy,
    which is the desired behaviour (the chart should be honest).
  * **Top packages** — top 5 ``template_id`` values across every
    simulation that carries one in ``simulation_config.json``.

Auth: gated on ``BASSIRA_ADMIN_TOKEN`` via the shared
``require_admin_token`` decorator from ``app.api.simulation`` —
same fail-closed semantics as ``POST /publish`` / ``POST /resolve``
/ ``POST /outcome``. Internal-only by design; never expose to
unauthenticated clients.

Robustness contract: when the data dirs are missing (fresh install,
test env without ``uploads/``), every counter/list resolves to
``0`` / ``[]`` rather than raising. A 500 here would brick the
ops dashboard, which is exactly when we *most* want a signal.
"""

from __future__ import annotations

import json
import os
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, g, jsonify

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
from ..config import Config
from ..utils.logger import get_logger

from .simulation import require_admin_token


admin_bp = Blueprint("admin", __name__)
logger = get_logger("miroshark.api.admin")


# ─── Path helpers ────────────────────────────────────────────────────────────


def _simulations_dir() -> str:
    """Return the directory containing per-simulation subfolders.

    Resolved per-call so a test that monkeypatches ``Config`` after
    module import still sees the override.
    """
    return getattr(Config, "WONDERWALL_SIMULATION_DATA_DIR", "") or ""


def _quotes_dir() -> str:
    """Return the directory where quote payloads are persisted.

    Mirrors the resolution logic in ``app.services.quote_service`` so
    a deployment that sets ``WONDERWALL_DATA_DIR`` (sibling
    ``quotes/``) and one that only sets the simulation dir both work
    out of the box.
    """
    base_dir = getattr(Config, "WONDERWALL_DATA_DIR", None)
    if not base_dir:
        sim_dir = _simulations_dir()
        if sim_dir:
            base_dir = os.path.dirname(sim_dir)
    if not base_dir:
        return ""
    return os.path.join(base_dir, "quotes")


# ─── Disk scans (defensive — never raise) ────────────────────────────────────


def _list_simulation_dirs() -> List[str]:
    """Return absolute paths to every simulation subdirectory.

    A simulation is any direct subdir of
    ``WONDERWALL_SIMULATION_DATA_DIR``. Hidden / dotfile entries are
    skipped so a stray ``.DS_Store`` does not inflate the count.
    """
    sims_root = _simulations_dir()
    if not sims_root or not os.path.isdir(sims_root):
        return []
    out: List[str] = []
    try:
        for name in os.listdir(sims_root):
            if name.startswith("."):
                continue
            path = os.path.join(sims_root, name)
            if os.path.isdir(path):
                out.append(path)
    except OSError as exc:
        logger.warning("Could not scan simulations dir %s: %s", sims_root, exc)
    return out


def _outcome_mtime(sim_dir: str) -> Optional[float]:
    """Return the ``mtime`` of ``<sim_dir>/outcome.json`` or ``None``."""
    path = os.path.join(sim_dir, "outcome.json")
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def _read_template_id(sim_dir: str) -> Optional[str]:
    """Return the ``template_id`` from ``simulation_config.json``.

    Defensive: parse failures or missing keys resolve to ``None`` so a
    single corrupt file does not poison the aggregation.
    """
    cfg_path = os.path.join(sim_dir, "simulation_config.json")
    if not os.path.isfile(cfg_path):
        return None
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f) or {}
    except (OSError, json.JSONDecodeError):
        return None
    tid = cfg.get("template_id")
    if not isinstance(tid, str):
        return None
    tid = tid.strip()
    return tid or None


def _count_quotes() -> int:
    """Count ``quote_*.json`` files persisted under the quotes dir."""
    qdir = _quotes_dir()
    if not qdir or not os.path.isdir(qdir):
        return 0
    n = 0
    try:
        for name in os.listdir(qdir):
            if name.startswith("quote_") and name.endswith(".json"):
                n += 1
    except OSError as exc:
        logger.warning("Could not scan quotes dir %s: %s", qdir, exc)
    return n


# ─── Aggregation ─────────────────────────────────────────────────────────────


def _build_time_series_30d(completed_mtimes: List[float]) -> List[Dict[str, Any]]:
    """Return a 30-element list ``[{date: YYYY-MM-DD, completed: n}, …]``.

    Always 30 entries (one per day, oldest → today) so the frontend can
    render a stable bar chart even when no completions exist that day.
    Dates are computed in UTC to keep the series deterministic across
    operator timezones.
    """
    today = datetime.now(timezone.utc).date()
    bucket: Dict[str, int] = {}
    cutoff = time.time() - 30 * 86400
    for mtime in completed_mtimes:
        if mtime < cutoff:
            continue
        day = datetime.fromtimestamp(mtime, tz=timezone.utc).date().isoformat()
        bucket[day] = bucket.get(day, 0) + 1
    series: List[Dict[str, Any]] = []
    for offset in range(29, -1, -1):
        day = (today.fromordinal(today.toordinal() - offset)).isoformat()
        series.append({"date": day, "completed": int(bucket.get(day, 0))})
    return series


def _build_top_packages(sim_dirs: List[str], limit: int = 5) -> List[Dict[str, Any]]:
    """Aggregate ``template_id`` across every simulation, top ``limit``."""
    counter: Counter = Counter()
    for sd in sim_dirs:
        tid = _read_template_id(sd)
        if tid:
            counter[tid] += 1
    return [{"package": pkg, "n": n} for pkg, n in counter.most_common(limit)]


def _build_kpis(
    sim_dirs: List[str],
    completed_mtimes: List[float],
    quotes_count: int,
) -> Dict[str, int]:
    """Compute the four headline numbers shown in the KPI row."""
    cutoff = time.time() - 30 * 86400
    last_30d = sum(1 for m in completed_mtimes if m >= cutoff)
    return {
        "total": len(sim_dirs),
        "completed": len(completed_mtimes),
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

    Never raises 500 from a missing dir — fresh installs render zero,
    and that is a valid (and correct) state.
    """
    try:
        sim_dirs = _list_simulation_dirs()
        completed_mtimes: List[float] = []
        for sd in sim_dirs:
            mtime = _outcome_mtime(sd)
            if mtime is not None:
                completed_mtimes.append(mtime)

        quotes_count = _count_quotes()
        kpis = _build_kpis(sim_dirs, completed_mtimes, quotes_count)
        funnel = _build_funnel(kpis)
        time_series = _build_time_series_30d(completed_mtimes)
        top_packages = _build_top_packages(sim_dirs)

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
