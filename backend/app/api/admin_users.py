"""Endpoints admin gestion utilisateurs cross-tenant (US-137).

Blueprint ``admin_users_bp`` monté sur ``/api/admin/users``.

Routes :
  GET  /api/admin/users                    — liste paginée des inscriptions
  GET  /api/admin/users/stats              — statistiques globales
  GET  /api/admin/users/<user_id>/simulations — simulations d'un utilisateur

Sécurité
────────
- Super-admin Bassira : accès cross-tenant à tous les utilisateurs.
- Org admin/owner : accès restreint aux users de ses organisations.
- Simple membre : 403.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from flask import Blueprint, g, jsonify, request

from ..auth.decorators import is_super_admin_email, require_auth
from ..auth.supabase_client import SupabaseConfigError, get_supabase_admin, get_user_orgs


logger = logging.getLogger("miroshark.api.admin_users")

# Blueprint monté sur /api/admin/users
admin_users_bp = Blueprint("admin_users", __name__)


# ─── Helpers ────────────────────────────────────────────────────────────────


def _err(code: str, message: str, status: int):
    return jsonify({
        "success": False,
        "error_code": code,
        "error": message,
    }), status


def _check_admin_access() -> tuple[bool, Optional[List[str]], Optional[Any]]:
    """Vérifie que l'utilisateur courant est super-admin OU org admin/owner.

    Returns:
        Tuple ``(is_super, org_ids_or_None, error_response_or_None)``.
        - ``is_super`` = True si super-admin Bassira.
        - ``org_ids`` = liste des org_id auxquels l'user est admin/owner (None si super-admin).
        - ``error_response`` = réponse d'erreur Flask ou None si ok.
    """
    user = getattr(g, "current_user", None) or {}
    email = user.get("email")
    user_id = user.get("id")

    is_super = is_super_admin_email(email)
    if is_super:
        return True, None, None

    if not user_id:
        return False, None, _err("INVALID_TOKEN", "Token missing 'sub' claim.", 401)

    try:
        user_orgs = get_user_orgs(user_id)
    except SupabaseConfigError:
        return False, None, _err(
            "SUPABASE_NOT_CONFIGURED",
            "Backend Supabase admin client is not configured.",
            503,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("get_user_orgs failed: %s", exc.__class__.__name__)
        return False, None, _err("INTERNAL_AUTH_ERROR", "Could not resolve user organizations.", 500)

    admin_orgs = [
        str(o.get("id") or "")
        for o in user_orgs
        if o.get("role") in {"owner", "admin"}
    ]
    if not admin_orgs:
        return False, None, _err(
            "INSUFFICIENT_ROLE",
            "Only org admin/owner or super-admin can access this endpoint.",
            403,
        )

    return False, admin_orgs, None


# ─── GET /api/admin/users ──────────────────────────────────────────────────────


@admin_users_bp.route("", methods=["GET"])
@require_auth
def list_users_endpoint():
    """Liste paginée des inscriptions Supabase (cross-tenant ou scoped org).

    Query params :
        ``org_id``  — filtre sur une organisation spécifique (optionnel).
        ``search``  — sous-chaîne email (ILIKE, optionnel).
        ``limit``   — défaut 50, max 200.
        ``offset``  — défaut 0.

    Response :
        {
          "success": true,
          "data": {
            "users": [
              {
                "id": "uuid",
                "email": "...",
                "created_at": "ISO",
                "last_sign_in_at": "ISO|null",
                "orgs": [{"id": "...", "name": "...", "slug": "...", "role": "..."}],
                "meta_data": {...}
              }
            ],
            "total": N,
            "limit": N,
            "offset": N
          }
        }
    """
    is_super, admin_org_ids, err = _check_admin_access()
    if err is not None:
        return err

    try:
        limit = min(int(request.args.get("limit", 50)), 200)
        offset = max(int(request.args.get("offset", 0)), 0)
    except (TypeError, ValueError):
        return _err("INVALID_PARAMS", "limit et offset doivent être des entiers.", 400)

    search = (request.args.get("search") or "").strip()
    filter_org_id = (request.args.get("org_id") or "").strip() or None

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase admin client is not configured.", 503)

    # ── Résoudre les org_ids de restriction ─────────────────────────────────
    # Super-admin : tous les users (ou filtrés par org_id si fourni).
    # Org admin : uniquement les users de ses orgs (filtré par filter_org_id si fourni).
    restriction_org_ids: Optional[List[str]] = None
    if not is_super:
        # Org admin : restriction aux orgs dont il est admin
        if filter_org_id:
            # Vérifier que cet org_id fait partie de ses orgs admin
            if filter_org_id not in admin_org_ids:
                return _err(
                    "ORG_NOT_FOUND_FOR_USER",
                    "Vous n'êtes pas admin/owner de cette organisation.",
                    404,
                )
            restriction_org_ids = [filter_org_id]
        else:
            restriction_org_ids = admin_org_ids
    else:
        if filter_org_id:
            restriction_org_ids = [filter_org_id]

    # ── Récupérer les org_members pour construire la liste des user_ids ─────
    try:
        if restriction_org_ids is not None:
            # On filtre par org_ids — récupérer les user_ids de ces orgs
            members_query = (
                cli.table("org_members")
                .select("user_id, role, org_id, organizations(id, name, slug)")
                .in_("org_id", restriction_org_ids)
                .execute()
            )
            members_rows = getattr(members_query, "data", None) or []
        else:
            # Super-admin sans filtre org : récupérer tous les membres
            members_query = (
                cli.table("org_members")
                .select("user_id, role, org_id, organizations(id, name, slug)")
                .execute()
            )
            members_rows = getattr(members_query, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        logger.error("org_members fetch failed: %s", exc.__class__.__name__)
        return _err("FETCH_FAILED", "Could not fetch organization members.", 500)

    # Construire un index user_id → [{org info + role}]
    user_orgs_map: Dict[str, List[Dict[str, Any]]] = {}
    for row in members_rows:
        uid = row.get("user_id") or ""
        if not uid:
            continue
        org_data = row.get("organizations") or {}
        org_entry = {
            "id": org_data.get("id") or row.get("org_id"),
            "name": org_data.get("name") or "",
            "slug": org_data.get("slug") or "",
            "role": row.get("role") or "",
        }
        user_orgs_map.setdefault(uid, []).append(org_entry)

    all_user_ids = list(user_orgs_map.keys())

    # Si aucun user associé dans les orgs, retourner liste vide
    if not all_user_ids and restriction_org_ids is not None:
        return jsonify({
            "success": True,
            "data": {
                "users": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
            },
        }), 200

    # ── Récupérer les profils auth.users via Supabase Auth Admin API ─────────
    try:
        # Récupérer les users depuis auth.users via la table users accessible
        # avec la clé service_role.
        # On utilise l'API admin du SDK Supabase pour lister les users.
        # Le SDK Python expose list_users() sur le client admin auth.
        auth_admin = cli.auth.admin

        # Si on a une liste restreinte d'user_ids, on les filtre après fetch.
        # L'API Supabase Admin ne permet pas de filtrer par IDs multiples directement.
        # On récupère par pages et on filtre.

        if restriction_org_ids is not None and all_user_ids:
            # Fetch paginé avec filtrage email
            # On doit construire la liste à partir des IDs connus
            fetched_users = []
            page_num = 1
            per_page = 1000

            while True:
                resp = auth_admin.list_users(page=page_num, per_page=per_page)
                batch = resp if isinstance(resp, list) else (resp.users if hasattr(resp, 'users') else [])
                if not batch:
                    break
                for u in batch:
                    uid = str(getattr(u, 'id', '') or '')
                    if uid in user_orgs_map:
                        fetched_users.append(u)
                if len(batch) < per_page:
                    break
                page_num += 1
        else:
            # Super-admin sans restriction : list_users paginé
            resp = auth_admin.list_users(page=1, per_page=1000)
            fetched_users = resp if isinstance(resp, list) else (resp.users if hasattr(resp, 'users') else [])

    except Exception as exc:  # noqa: BLE001
        logger.error("auth.admin.list_users failed: %s", exc.__class__.__name__)
        return _err("FETCH_FAILED", "Could not fetch users from auth.", 500)

    # Filtrer par search email (ILIKE)
    if search:
        search_lower = search.lower()
        fetched_users = [
            u for u in fetched_users
            if search_lower in (getattr(u, 'email', '') or '').lower()
        ]

    # Tri par created_at DESC
    def _get_created(u: Any) -> str:
        v = getattr(u, 'created_at', None)
        return str(v) if v else ''

    fetched_users.sort(key=_get_created, reverse=True)

    total = len(fetched_users)
    page_users = fetched_users[offset: offset + limit]

    # ── Sérialiser ──────────────────────────────────────────────────────────
    def _serialize_user(u: Any) -> Dict[str, Any]:
        uid = str(getattr(u, 'id', '') or '')
        email = getattr(u, 'email', '') or ''
        created_at = str(getattr(u, 'created_at', '') or '')
        last_sign_in_at_raw = getattr(u, 'last_sign_in_at', None)
        last_sign_in_at = str(last_sign_in_at_raw) if last_sign_in_at_raw else None
        meta_data = getattr(u, 'user_metadata', None) or {}
        if hasattr(meta_data, '__dict__'):
            meta_data = {k: v for k, v in vars(meta_data).items() if not k.startswith('_')}

        orgs = user_orgs_map.get(uid, [])

        return {
            "id": uid,
            "email": email,
            "created_at": created_at,
            "last_sign_in_at": last_sign_in_at,
            "orgs": orgs,
            "meta_data": meta_data,
        }

    users_serialized = [_serialize_user(u) for u in page_users]

    return jsonify({
        "success": True,
        "data": {
            "users": users_serialized,
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }), 200


# ─── GET /api/admin/users/stats ──────────────────────────────────────────────


@admin_users_bp.route("/stats", methods=["GET"])
@require_auth
def users_stats_endpoint():
    """Statistiques globales des inscriptions.

    Response :
        {
          "success": true,
          "data": {
            "total_users": N,
            "active_7d": N,
            "new_30d": N,
            "by_org": {"org_id": count, ...}
          }
        }
    """
    is_super, admin_org_ids, err = _check_admin_access()
    if err is not None:
        return err

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase admin client is not configured.", 503)

    # Statistiques org_members pour by_org et totaux
    try:
        if is_super:
            members_resp = (
                cli.table("org_members")
                .select("user_id, org_id")
                .execute()
            )
        else:
            members_resp = (
                cli.table("org_members")
                .select("user_id, org_id")
                .in_("org_id", admin_org_ids)
                .execute()
            )
        members_rows = getattr(members_resp, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        logger.error("stats members fetch failed: %s", exc.__class__.__name__)
        return _err("FETCH_FAILED", "Could not fetch stats.", 500)

    unique_user_ids = {str(r.get("user_id") or "") for r in members_rows if r.get("user_id")}
    total_users = len(unique_user_ids)

    # Comptage par org
    by_org: Dict[str, int] = {}
    for row in members_rows:
        oid = str(row.get("org_id") or "")
        uid = str(row.get("user_id") or "")
        if oid and uid:
            by_org[oid] = by_org.get(oid, 0) + 1

    # Active 7 jours + new 30 jours via auth.admin.list_users
    active_7d = 0
    new_30d = 0
    try:
        from datetime import datetime, timedelta, timezone as tz
        now_dt = datetime.now(tz.utc)
        cutoff_7d = now_dt - timedelta(days=7)
        cutoff_30d = now_dt - timedelta(days=30)

        auth_admin = cli.auth.admin
        resp = auth_admin.list_users(page=1, per_page=1000)
        all_auth_users = resp if isinstance(resp, list) else (resp.users if hasattr(resp, 'users') else [])

        # Si org admin : filtrer aux user_ids connus
        if not is_super and unique_user_ids:
            all_auth_users = [
                u for u in all_auth_users
                if str(getattr(u, 'id', '') or '') in unique_user_ids
            ]

        for u in all_auth_users:
            last_sign = getattr(u, 'last_sign_in_at', None)
            created = getattr(u, 'created_at', None)

            if last_sign:
                try:
                    if isinstance(last_sign, str):
                        last_sign_dt = datetime.fromisoformat(
                            last_sign.replace('Z', '+00:00')
                        )
                    else:
                        last_sign_dt = last_sign
                        if last_sign_dt.tzinfo is None:
                            last_sign_dt = last_sign_dt.replace(tzinfo=tz.utc)
                    if last_sign_dt >= cutoff_7d:
                        active_7d += 1
                except (ValueError, TypeError):
                    pass

            if created:
                try:
                    if isinstance(created, str):
                        created_dt = datetime.fromisoformat(
                            created.replace('Z', '+00:00')
                        )
                    else:
                        created_dt = created
                        if created_dt.tzinfo is None:
                            created_dt = created_dt.replace(tzinfo=tz.utc)
                    if created_dt >= cutoff_30d:
                        new_30d += 1
                except (ValueError, TypeError):
                    pass

    except Exception as exc:  # noqa: BLE001
        logger.warning("stats active/new computation failed: %s", exc.__class__.__name__)
        # Non bloquant — on retourne 0 pour ces métriques

    return jsonify({
        "success": True,
        "data": {
            "total_users": total_users,
            "active_7d": active_7d,
            "new_30d": new_30d,
            "by_org": by_org,
        },
    }), 200


# ─── GET /api/admin/users/<user_id>/simulations ───────────────────────────────


@admin_users_bp.route("/<user_id>/simulations", methods=["GET"])
@require_auth
def user_simulations_endpoint(user_id: str):
    """Liste les simulations d'un utilisateur.

    Query params :
        ``limit``  — défaut 20, max 100.
        ``offset`` — défaut 0.

    Response :
        {
          "success": true,
          "data": {
            "simulations": [...],
            "total": N,
            "user_id": "uuid"
          }
        }
    """
    is_super, admin_org_ids, err = _check_admin_access()
    if err is not None:
        return err

    try:
        limit = min(int(request.args.get("limit", 20)), 100)
        offset = max(int(request.args.get("offset", 0)), 0)
    except (TypeError, ValueError):
        return _err("INVALID_PARAMS", "limit et offset doivent être des entiers.", 400)

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase admin client is not configured.", 503)

    # Vérifier que l'user_id demandé est accessible pour l'appelant
    if not is_super:
        # Vérifier que cet user est dans une des orgs de l'admin
        try:
            membership_resp = (
                cli.table("org_members")
                .select("user_id")
                .eq("user_id", user_id)
                .in_("org_id", admin_org_ids)
                .limit(1)
                .execute()
            )
            membership_rows = getattr(membership_resp, "data", None) or []
            if not membership_rows:
                return _err(
                    "ACCESS_DENIED",
                    "Cet utilisateur n'appartient pas à vos organisations.",
                    403,
                )
        except Exception as exc:  # noqa: BLE001
            logger.error("membership check failed: %s", exc.__class__.__name__)
            return _err("INTERNAL_AUTH_ERROR", "Could not verify user membership.", 500)

    try:
        sims_query = (
            cli.table("simulation_ownership")
            .select(
                "simulation_id, org_id, created_by, package_id, is_published, "
                "outcome, brier_score, created_at, "
                "organizations(id, name, slug)"
            )
            .eq("created_by", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        sims_rows = getattr(sims_query, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        logger.error("simulations fetch failed for user %s: %s", user_id, exc.__class__.__name__)
        return _err("FETCH_FAILED", "Could not fetch user simulations.", 500)

    # Filtrer par orgs si org admin
    if not is_super:
        sims_rows = [
            r for r in sims_rows
            if str(r.get("org_id") or "") in admin_org_ids
        ]

    total = len(sims_rows)
    page_sims = sims_rows[offset: offset + limit]

    def _serialize_sim(row: Dict[str, Any]) -> Dict[str, Any]:
        org_data = row.get("organizations") or {}
        return {
            "simulation_id": row.get("simulation_id"),
            "org_id": row.get("org_id"),
            "org_name": org_data.get("name") if isinstance(org_data, dict) else None,
            "org_slug": org_data.get("slug") if isinstance(org_data, dict) else None,
            "package_id": row.get("package_id"),
            "is_published": bool(row.get("is_published", False)),
            "outcome": row.get("outcome"),
            "brier_score": row.get("brier_score"),
            "created_at": row.get("created_at"),
        }

    return jsonify({
        "success": True,
        "data": {
            "simulations": [_serialize_sim(r) for r in page_sims],
            "total": total,
            "user_id": user_id,
            "limit": limit,
            "offset": offset,
        },
    }), 200
