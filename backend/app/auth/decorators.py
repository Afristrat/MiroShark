"""Décorateurs Flask pour l'authentification multitenant Bassira (US-092 + US-095).

Quatre décorateurs sont exposés :

* `@require_auth` — exige un JWT Supabase valide. Pose
  `g.current_user = {"id": uuid, "email": str, "claims": {...}}`. Sinon 401.
* `@require_org_membership(role_min="member")` — exige `@require_auth` puis
  vérifie que l'utilisateur appartient à au moins une organisation avec un
  rôle >= role_min. Si plusieurs orgs, l'org cible est résolue via le
  header `X-Org-Id` ou la query string `?org_id=`. Pose
  `g.current_org = {"id": uuid, "slug": str, "sector": str|None,
  "country_code": str|None, "role": str, "name": str}`.
* `@require_owner_or_admin` — alias de `@require_org_membership("admin")`.
* `@require_super_admin` — exige `@require_auth` puis vérifie que l'email
  de l'utilisateur figure dans la whitelist `BASSIRA_SUPER_ADMIN_EMAILS`
  (env var, liste séparée par virgules). Pose `g.is_super_admin = True`.
  Sinon 403 `NOT_SUPER_ADMIN`. Permet aux founders Bassira de voir
  TOUTES les organisations dans l'admin (cf. /api/admin/organizations).

Toutes les erreurs sont retournées au format API standard du backend
(`{"success": False, "error_code": "...", "error": "..."}`) avec un
status HTTP cohérent : 401 (auth manquante), 403 (membership / rôle
insuffisant / non super-admin), 404 (org_id explicite mais l'utilisateur
n'y appartient pas), 503 (config backend manquante).
"""

from __future__ import annotations

import os
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set

from flask import g, jsonify, request

from ..utils.logger import get_logger
from .jwt_verifier import InvalidTokenError, verify_supabase_jwt
from .supabase_client import (
    SupabaseConfigError,
    get_user_orgs,
    is_org_self_service_enabled,
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
    de configuration backend (SUPABASE_URL pour le mode JWKS asymétrique
    ou SUPABASE_JWT_SECRET pour le mode HS256 legacy), retourne 503.
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
            if (
                "SUPABASE_JWT_SECRET" in msg
                or "SUPABASE_URL is not configured" in msg
            ):
                return _err(
                    "AUTH_NOT_CONFIGURED",
                    "Backend authentication is not configured. "
                    "Set SUPABASE_URL in Coolify environment variables "
                    "(or SUPABASE_JWT_SECRET for legacy HS256 projects).",
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
                # US-098 — propagé pour permettre à
                # @require_self_service_enabled d'éviter un round-trip
                # Supabase si la donnée est déjà disponible.
                "self_service_enabled": bool(
                    selected.get("self_service_enabled", False)
                ),
            }
            return view_func(*args, **kwargs)

        return _wrapper

    return _decorator


def require_owner_or_admin(view_func: Callable) -> Callable:
    """Alias : exige role >= admin (admin ou owner)."""
    return require_org_membership(role_min="admin")(view_func)


# ─── Super-admin Bassira (US-095) ───────────────────────────────────────────

def _super_admin_emails() -> Set[str]:
    """Lit la whitelist `BASSIRA_SUPER_ADMIN_EMAILS` depuis l'environnement.

    Format : liste d'emails séparés par virgules (espaces tolérés).
    Comparaison case-insensitive (lowercase strip). Vide = personne n'est
    super-admin (le décorateur retournera 403 pour tout user).

    On lit l'env à chaque appel (et non au démarrage) pour permettre :
    1. Aux tests de monkeypatcher `BASSIRA_SUPER_ADMIN_EMAILS` à la volée.
    2. À l'opérateur de mettre à jour la liste sur Coolify sans redémarrer
       le process Flask (le prochain request prend la nouvelle valeur).
    """
    raw = os.getenv("BASSIRA_SUPER_ADMIN_EMAILS", "") or ""
    if not raw.strip():
        return set()
    return {
        item.strip().lower()
        for item in raw.split(",")
        if item.strip()
    }


def is_super_admin_email(email: Optional[str]) -> bool:
    """Retourne True si `email` figure dans la whitelist super-admin.

    Fonction libre (testable en isolation, réutilisable par
    `/api/admin/me/super-status` qui ne pose pas g.is_super_admin).
    """
    if not email or not isinstance(email, str):
        return False
    return email.strip().lower() in _super_admin_emails()


def require_super_admin(view_func: Callable) -> Callable:
    """Décorateur : exige un JWT valide ET un email super-admin whitelist.

    Compose `@require_auth` (pose `g.current_user`) puis vérifie que
    `g.current_user['email']` est listé dans la variable d'environnement
    `BASSIRA_SUPER_ADMIN_EMAILS`. Si match : pose `g.is_super_admin = True`.

    Codes d'erreur :
        - 401 MISSING_AUTH / INVALID_TOKEN (via require_auth)
        - 403 NOT_SUPER_ADMIN (email non whitelist)
        - 503 SUPER_ADMIN_NOT_CONFIGURED (env var vide ou absente)

    Ne JAMAIS logguer l'email rejeté en clair — on log seulement le hash
    court pour audit sans fuite de PII.
    """

    @wraps(view_func)
    @require_auth
    def _wrapper(*args, **kwargs):
        whitelist = _super_admin_emails()
        if not whitelist:
            # Pas de super-admin configuré côté serveur → 503 explicite
            # pour différencier d'un cas « email pas listé » (403).
            return _err(
                "SUPER_ADMIN_NOT_CONFIGURED",
                "Backend super-admin whitelist is empty. "
                "Set BASSIRA_SUPER_ADMIN_EMAILS in Coolify environment variables.",
                503,
            )

        user = getattr(g, "current_user", None) or {}
        email = user.get("email")
        if not email or not isinstance(email, str):
            return _err(
                "INVALID_TOKEN",
                "Token missing 'email' claim.",
                401,
            )

        if email.strip().lower() not in whitelist:
            # Log d'audit minimal (hash 8 char, pas l'email en clair).
            import hashlib
            digest = hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:8]
            logger.warning(
                "super-admin denied for email_hash=%s (not in whitelist)",
                digest,
            )
            return _err(
                "NOT_SUPER_ADMIN",
                "Authenticated user is not a Bassira super-admin.",
                403,
            )

        g.is_super_admin = True
        return view_func(*args, **kwargs)

    return _wrapper


# ─── Self-service activation per-org (US-098) ───────────────────────────────


def _user_is_super_admin_from_g() -> bool:
    """Helper interne : True si g.is_super_admin OU si l'email est whitelist.

    Permet à `@require_self_service_enabled` d'autoriser un super-admin
    Bassira à utiliser les endpoints self-service même sur une org dont
    le flag est désactivé. Ne nécessite pas que `@require_super_admin`
    ait préalablement décoré la route — le check est fait via l'email
    présent dans g.current_user.
    """
    if getattr(g, "is_super_admin", False) is True:
        return True
    user = getattr(g, "current_user", None) or {}
    email = user.get("email")
    return is_super_admin_email(email)


def require_self_service_enabled(view_func: Callable) -> Callable:
    """Décorateur : exige que l'org courante ait `self_service_enabled = true`.

    À appliquer APRÈS `@require_org_membership` (qui pose `g.current_org`).
    Le décorateur :
      1. Vérifie qu'un `g.current_org` est posé (sinon 500 — erreur dev).
      2. Vérifie le flag `self_service_enabled` côté Supabase.
      3. Bypass si l'utilisateur est super-admin Bassira (cf. US-099).

    Codes d'erreur :
        - 500 NO_CURRENT_ORG (décoration incorrecte côté dev — `@require_org_membership` manquant)
        - 403 SELF_SERVICE_DISABLED (org sans flag, user non super-admin)
        - 503 SUPABASE_NOT_CONFIGURED (héritée des helpers Supabase)
    """

    @wraps(view_func)
    def _wrapper(*args, **kwargs):
        # US-099 — bypass super-admin (ils peuvent toujours lancer des sims).
        if _user_is_super_admin_from_g():
            g.self_service_bypass = True
            return view_func(*args, **kwargs)

        org = getattr(g, "current_org", None) or {}
        org_id = org.get("id") if isinstance(org, dict) else None
        if not org_id:
            logger.error(
                "require_self_service_enabled used without g.current_org. "
                "Apply @require_org_membership first."
            )
            return _err(
                "NO_CURRENT_ORG",
                "Self-service decorator requires an authenticated org context.",
                500,
            )

        # Si la valeur est déjà connue dans g.current_org (US-098 — get_user_orgs
        # retourne self_service_enabled), on l'utilise pour éviter un round-trip.
        ss = org.get("self_service_enabled")
        if ss is None:
            try:
                ss = is_org_self_service_enabled(org_id)
            except SupabaseConfigError:
                return _err(
                    "SUPABASE_NOT_CONFIGURED",
                    "Backend Supabase admin client is not configured.",
                    503,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "self-service flag fetch failed for org_id=%s: %s",
                    org_id, exc.__class__.__name__,
                )
                return _err(
                    "INTERNAL_AUTH_ERROR",
                    "Could not verify self-service status.",
                    500,
                )

        if not ss:
            return _err(
                "SELF_SERVICE_DISABLED",
                "Self-service is disabled for this organization. "
                "Contact your Bassira analyst to order a simulation.",
                403,
            )

        return view_func(*args, **kwargs)

    return _wrapper


def soft_check_self_service(view_func: Callable) -> Callable:
    """Décorateur souple — applique le check self-service UNIQUEMENT si JWT présent.

    Logique :
      - Pas de JWT → laisse passer (mode legacy/public, pas de breaking change).
      - JWT + super-admin → laisse passer (US-099).
      - JWT + org membership → vérifie self_service_enabled.
      - JWT mais aucun JWT valide ne pose de g.current_user → laisse passer.

    Permet à US-098 d'être appliqué progressivement sur les endpoints existants
    (create / build / start) sans casser les flows publics legacy. Quand US-101+
    rendra l'auth obligatoire sur ces endpoints, on basculera sur la chaîne
    stricte `@require_org_membership + @require_self_service_enabled`.

    Codes d'erreur (uniquement quand JWT fourni) :
        - 403 SELF_SERVICE_DISABLED
        - 401 INVALID_TOKEN (si JWT fourni mais invalide)
    """

    @wraps(view_func)
    def _wrapper(*args, **kwargs):
        token = _extract_jwt_from_request()
        if not token:
            # Pas de JWT → laisse passer (legacy public mode).
            return view_func(*args, **kwargs)

        try:
            claims = verify_supabase_jwt(token)
        except InvalidTokenError as exc:
            msg = str(exc)
            if (
                "SUPABASE_JWT_SECRET" in msg
                or "SUPABASE_URL is not configured" in msg
            ):
                # Backend mal configuré — on log et on laisse passer pour ne
                # pas brique l'endpoint en dev local.
                logger.warning(
                    "soft_check_self_service: backend not configured, "
                    "letting request through legacy."
                )
                return view_func(*args, **kwargs)
            return _err("INVALID_TOKEN", "Invalid or expired token.", 401)

        # JWT valide → on pose g.current_user comme require_auth.
        g.current_user = {
            "id": claims.get("sub"),
            "email": claims.get("email"),
            "claims": claims,
        }

        # US-099 — super-admin bypass.
        if _user_is_super_admin_from_g():
            g.is_super_admin = True
            g.self_service_bypass = True
            return view_func(*args, **kwargs)

        # Sinon : on tente de résoudre l'org courante.
        user_id = (g.current_user or {}).get("id")
        if not user_id:
            return _err("INVALID_TOKEN", "Token missing 'sub' claim.", 401)

        requested_org_id = (
            request.headers.get("X-Org-Id")
            or request.args.get("org_id")
            or None
        )

        try:
            user_orgs = get_user_orgs(user_id)
        except SupabaseConfigError:
            # Backend mal configuré → fallback legacy.
            logger.warning(
                "soft_check_self_service: Supabase not configured, "
                "letting request through legacy."
            )
            return view_func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "soft_check_self_service get_user_orgs failed: %s",
                exc.__class__.__name__,
            )
            return view_func(*args, **kwargs)

        if not user_orgs:
            # User authentifié mais sans org → on ne peut pas vérifier le
            # flag. Si on est ici, c'est que le user veut explicitement
            # utiliser le mode self-service. Refus 403.
            return _err(
                "SELF_SERVICE_DISABLED",
                "Authenticated user is not a member of any organization. "
                "Self-service requires an active organization membership.",
                403,
            )

        # Sélection de l'org cible (X-Org-Id, ?org_id=, ou unique).
        if requested_org_id:
            match = next(
                (o for o in user_orgs if str(o.get("id")) == str(requested_org_id)),
                None,
            )
            if match is None:
                return _err(
                    "ORG_NOT_FOUND_FOR_USER",
                    "The requested org_id is not associated with this user.",
                    404,
                )
            selected = match
        elif len(user_orgs) == 1:
            selected = user_orgs[0]
        else:
            return _err(
                "ORG_ID_REQUIRED",
                "User belongs to multiple organizations — provide X-Org-Id "
                "header or ?org_id= query parameter.",
                400,
            )

        g.current_org = {
            "id": selected.get("id"),
            "slug": selected.get("slug"),
            "name": selected.get("name"),
            "sector": selected.get("sector"),
            "country_code": selected.get("country_code"),
            "role": selected.get("role"),
            "self_service_enabled": bool(
                selected.get("self_service_enabled", False)
            ),
        }

        if not g.current_org["self_service_enabled"]:
            return _err(
                "SELF_SERVICE_DISABLED",
                "Self-service is disabled for this organization. "
                "Contact your Bassira analyst to order a simulation.",
                403,
            )

        return view_func(*args, **kwargs)

    return _wrapper
