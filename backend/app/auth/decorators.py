"""Décorateurs Flask pour l'authentification multitenant Bassira (US-092).

Trois décorateurs sont exposés :

* `@require_auth` — exige un JWT Supabase valide. Pose
  `g.current_user = {"id": uuid, "email": str, "claims": {...}}`. Sinon 401.
* `@require_org_membership(role_min="member")` — exige `@require_auth` puis
  vérifie que l'utilisateur appartient à au moins une organisation avec un
  rôle >= role_min. Si plusieurs orgs, l'org cible est résolue via le
  header `X-Org-Id` ou la query string `?org_id=`. Pose
  `g.current_org = {"id": uuid, "slug": str, "sector": str|None,
  "country_code": str|None, "role": str, "name": str}`.
* `@require_owner_or_admin` — alias de `@require_org_membership("admin")`.

Toutes les erreurs sont retournées au format API standard du backend
(`{"success": False, "error_code": "...", "error": "..."}`) avec un
status HTTP cohérent : 401 (auth manquante), 403 (membership / rôle
insuffisant), 404 (org_id explicite mais l'utilisateur n'y appartient
pas), 503 (config backend manquante).
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from flask import g, jsonify, request

from ..utils.logger import get_logger
from .jwt_verifier import InvalidTokenError, verify_supabase_jwt
from .supabase_client import (
    SupabaseConfigError,
    get_user_orgs,
    role_meets_minimum,
)


logger = get_logger("miroshark.auth.decorators")


# ─── Helpers privés ─────────────────────────────────────────────────────────

def _extract_jwt_from_request() -> Optional[str]:
    """Extrait le JWT depuis `Authorization: Bearer …` ou cookie Supabase.

    Le frontend Bassira utilisera `@supabase/supabase-js` qui pose le
    cookie `sb-access-token` lors d'une session SSR-friendly. En mode
    SPA pur, c'est l'header `Authorization` qui est utilisé. On accepte
    les deux : header en priorité (canonique), cookie en fallback.
    """
    # 1. Header `Authorization: Bearer <token>`
    auth_header = request.headers.get("Authorization", "") or ""
    if auth_header:
        parts = auth_header.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()
            if token:
                return token

    # 2. Cookie `sb-access-token`
    cookie_token = request.cookies.get("sb-access-token", "") or ""
    cookie_token = cookie_token.strip()
    if cookie_token:
        return cookie_token

    return None


def _err(code: str, message: str, status: int):
    """Construit une réponse d'erreur API cohérente avec le reste du backend."""
    return jsonify({
        "success": False,
        "error_code": code,
        "error": message,
    }), status


def _resolve_target_org(
    requested_org_id: Optional[str],
    user_orgs: List[Dict[str, Any]],
):
    """Sélectionne l'org cible selon l'header `X-Org-Id` / `?org_id=`.

    Returns:
        Tuple ``(selected_org_dict, error_response)``.
        - ``selected_org_dict`` est un membre de `user_orgs` ou ``None``
          si une erreur a été produite.
        - ``error_response`` est un tuple Flask `(jsonify, status)` ou
          ``None`` si tout va bien.
    """
    if not user_orgs:
        return None, _err(
            "NOT_A_MEMBER",
            "Authenticated user is not a member of any organization.",
            403,
        )

    if requested_org_id:
        match = next(
            (o for o in user_orgs if str(o.get("id")) == str(requested_org_id)),
            None,
        )
        if match is None:
            return None, _err(
                "ORG_NOT_FOUND_FOR_USER",
                "The requested org_id is not associated with this user.",
                404,
            )
        return match, None

    if len(user_orgs) == 1:
        return user_orgs[0], None

    # Plusieurs orgs et aucune sélection explicite — on refuse plutôt que
    # de deviner. Le frontend doit imposer un org_id à ce stade.
    return None, _err(
        "ORG_ID_REQUIRED",
        "User belongs to multiple organizations — provide X-Org-Id header "
        "or ?org_id= query parameter.",
        400,
    )


# ─── Décorateurs publics ────────────────────────────────────────────────────

def require_auth(view_func: Callable) -> Callable:
    """Décorateur : exige un JWT Supabase valide.

    Pose `g.current_user` pour la suite du traitement. En cas d'absence
    de configuration `SUPABASE_JWT_SECRET`, retourne 503 explicite.
    """

    @wraps(view_func)
    def _wrapper(*args, **kwargs):
        token = _extract_jwt_from_request()
        if not token:
            return _err(
                "MISSING_AUTH",
                "Authentication required: missing Authorization header or sb-access-token cookie.",
                401,
            )
        try:
            claims = verify_supabase_jwt(token)
        except InvalidTokenError as exc:
            # Distinction config-manquante vs token-invalide pour faciliter
            # le diagnostic opérateur sans fuiter d'info au client.
            msg = str(exc)
            if "SUPABASE_JWT_SECRET" in msg:
                return _err(
                    "AUTH_NOT_CONFIGURED",
                    "Backend authentication is not configured. "
                    "Set SUPABASE_JWT_SECRET in Coolify environment variables.",
                    503,
                )
            return _err("INVALID_TOKEN", "Invalid or expired token.", 401)

        g.current_user = {
            "id": claims.get("sub"),
            "email": claims.get("email"),
            "claims": claims,
        }
        return view_func(*args, **kwargs)

    return _wrapper


def require_org_membership(role_min: str = "member") -> Callable:
    """Décorateur factory : exige une appartenance à une org avec un rôle minimal.

    Args:
        role_min : un parmi `viewer`, `member`, `admin`, `owner`.

    Effets :
        - Pose `g.current_user` (via `require_auth` interne).
        - Pose `g.current_org` = ``{id, slug, name, sector, country_code, role}``.

    Codes d'erreur :
        - 401 MISSING_AUTH / INVALID_TOKEN
        - 403 NOT_A_MEMBER / ROLE_TOO_LOW
        - 404 ORG_NOT_FOUND_FOR_USER (org_id explicite invalide)
        - 400 ORG_ID_REQUIRED (multi-org sans hint)
        - 503 SUPABASE_NOT_CONFIGURED
    """

    if role_min not in {"viewer", "member", "admin", "owner"}:
        raise ValueError(f"Invalid role_min: {role_min!r}")

    def _decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        @require_auth
        def _wrapper(*args, **kwargs):
            user = getattr(g, "current_user", None) or {}
            user_id = user.get("id")
            if not user_id:
                # Ne devrait jamais arriver après require_auth, mais on
                # se protège : un sub claim absent = 401.
                return _err("INVALID_TOKEN", "Token missing 'sub' claim.", 401)

            requested_org_id = (
                request.headers.get("X-Org-Id")
                or request.args.get("org_id")
                or None
            )

            try:
                user_orgs = get_user_orgs(user_id)
            except SupabaseConfigError as exc:
                logger.error("Supabase admin config missing: %s", exc)
                return _err(
                    "SUPABASE_NOT_CONFIGURED",
                    "Backend Supabase admin client is not configured.",
                    503,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "get_user_orgs failed for user_id=%s: %s",
                    user_id, exc.__class__.__name__,
                )
                return _err(
                    "INTERNAL_AUTH_ERROR",
                    "Could not resolve user organizations.",
                    500,
                )

            selected, error = _resolve_target_org(requested_org_id, user_orgs)
            if error is not None:
                return error
            assert selected is not None  # _resolve_target_org garantit ce contrat

            actual_role = selected.get("role")
            if not role_meets_minimum(actual_role, role_min):
                return _err(
                    "ROLE_TOO_LOW",
                    f"Role '{actual_role}' is insufficient (requires '{role_min}' or higher).",
                    403,
                )

            g.current_org = {
                "id": selected.get("id"),
                "slug": selected.get("slug"),
                "name": selected.get("name"),
                "sector": selected.get("sector"),
                "country_code": selected.get("country_code"),
                "role": actual_role,
            }
            return view_func(*args, **kwargs)

        return _wrapper

    return _decorator


def require_owner_or_admin(view_func: Callable) -> Callable:
    """Alias : exige role >= admin (admin ou owner)."""
    return require_org_membership(role_min="admin")(view_func)
