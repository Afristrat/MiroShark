"""Vérification des JWT émis par Supabase Auth (US-092 + refactor ECC).

Supabase Auth a migré (2026) vers des **JWT Signing Keys asymétriques**
(ECC P-256 = ES256, ou RS256). Les anciens projets utilisent encore le
**Legacy JWT Secret** HS256. Ce module supporte les deux modes de
manière transparente :

  1. **Asymétrique (ES256/RS256, par défaut)** — récupère les clés
     publiques depuis le JWKS endpoint Supabase :
     ``${SUPABASE_URL}/auth/v1/.well-known/jwks.json``
     Aucun secret partagé n'est requis côté backend ; seule l'URL du
     projet (publique) suffit. Géré via ``PyJWKClient`` qui gère le
     cache des clés et la rotation automatique.

  2. **HS256 legacy (fallback)** — si ``SUPABASE_JWT_SECRET`` est défini
     dans l'environnement, le module l'utilise pour valider les tokens
     signés en HS256. Permet de coexister avec d'anciens projets.

Le mode est **détecté automatiquement** depuis le header ``alg`` du JWT
décodé sans vérification. Aucune configuration manuelle n'est requise.

Cache : on cache la dernière vérification valide d'un jeton pendant
5 minutes (TTL borné par ``exp``) pour limiter la charge CPU et les
appels JWKS répétés. PyJWKClient gère lui-même le cache des clés
publiques (par défaut 16 clés × lifespan).

Aucune fuite de PII : ni le JWT brut ni le header ``Authorization`` ne
sont jamais loggés (cf. rule supabase.md).
"""

from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from typing import Any, Dict

import jwt  # PyJWT — résolu via le pyproject.toml (extra `crypto`).
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError as _PyJWTInvalidTokenError

from ..utils.logger import get_logger


logger = get_logger("miroshark.auth.jwt")


# ─── Exception publique ─────────────────────────────────────────────────────

class InvalidTokenError(Exception):
    """Erreur levée quand un JWT est absent, malformé, expiré ou mal signé.

    On expose une exception spécifique au module afin que les décorateurs
    puissent attraper *cette* erreur sans capturer accidentellement les
    erreurs internes de PyJWT (qui peuvent évoluer entre versions). Le
    message reste générique côté API (le décorateur traduit en 401) mais
    on conserve le détail dans les logs serveur pour le debug.
    """


# ─── Cache LRU + TTL pour les claims décodés ────────────────────────────────

_CACHE_MAX_SIZE = 256
_CACHE_TTL_SECONDS = 5 * 60  # 5 minutes — voir docstring du module.

# OrderedDict[token_str, (expires_at_epoch, claims_dict)]
_cache: "OrderedDict[str, tuple[float, Dict[str, Any]]]" = OrderedDict()
_cache_lock = threading.Lock()


def _cache_get(token: str) -> Dict[str, Any] | None:
    """Récupère un payload mis en cache si encore valide, sinon `None`."""
    now = time.time()
    with _cache_lock:
        entry = _cache.get(token)
        if entry is None:
            return None
        expires_at, claims = entry
        if expires_at <= now:
            _cache.pop(token, None)
            return None
        _cache.move_to_end(token)
        return claims


def _cache_set(token: str, claims: Dict[str, Any]) -> None:
    """Insère un payload validé avec un TTL borné par exp et 5 min."""
    now = time.time()
    exp = claims.get("exp")
    ttl_deadline = now + _CACHE_TTL_SECONDS
    if isinstance(exp, (int, float)):
        ttl_deadline = min(ttl_deadline, float(exp) - 5.0)
    if ttl_deadline <= now:
        return
    with _cache_lock:
        _cache[token] = (ttl_deadline, claims)
        _cache.move_to_end(token)
        while len(_cache) > _CACHE_MAX_SIZE:
            _cache.popitem(last=False)


def _cache_clear() -> None:
    """Vide entièrement le cache (utilisé par les tests)."""
    with _cache_lock:
        _cache.clear()


# ─── PyJWKClient (JWKS Supabase) ────────────────────────────────────────────

# Singleton thread-safe. Reconstruit si l'URL change (ex: tests).
_jwks_client_lock = threading.Lock()
_jwks_client: PyJWKClient | None = None
_jwks_client_url: str | None = None


def _get_jwks_client() -> PyJWKClient:
    """Retourne un PyJWKClient pour le projet Supabase courant.

    L'URL JWKS est ``${SUPABASE_URL}/auth/v1/.well-known/jwks.json``.
    PyJWKClient gère son propre cache (lifespan 5 min, 16 clés max).
    """
    global _jwks_client, _jwks_client_url
    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if not supabase_url:
        raise InvalidTokenError(
            "SUPABASE_URL is not configured on the backend "
            "(required to fetch JWKS for asymmetric JWT verification)."
        )
    jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    with _jwks_client_lock:
        if _jwks_client is None or _jwks_client_url != jwks_url:
            _jwks_client = PyJWKClient(
                jwks_url,
                cache_keys=True,
                lifespan=300,  # 5 min — cohérent avec _CACHE_TTL_SECONDS
                max_cached_keys=16,
            )
            _jwks_client_url = jwks_url
        return _jwks_client


def _reset_jwks_client() -> None:
    """Réinitialise le PyJWKClient (utilisé par les tests)."""
    global _jwks_client, _jwks_client_url
    with _jwks_client_lock:
        _jwks_client = None
        _jwks_client_url = None


# ─── API publique ───────────────────────────────────────────────────────────

def _load_legacy_secret() -> str | None:
    """Lit ``SUPABASE_JWT_SECRET`` à chaque appel (legacy HS256)."""
    secret = os.getenv("SUPABASE_JWT_SECRET", "").strip()
    return secret or None


def _peek_alg(token: str) -> str:
    """Lit l'algorithme déclaré dans le header JWT sans vérifier signature."""
    try:
        header = jwt.get_unverified_header(token)
    except _PyJWTInvalidTokenError as exc:
        raise InvalidTokenError("Invalid token header.") from exc
    alg = header.get("alg")
    if not isinstance(alg, str) or not alg:
        raise InvalidTokenError("Token header missing 'alg'.")
    return alg


def verify_supabase_jwt(token: str) -> Dict[str, Any]:
    """Décode et vérifie un JWT Supabase, retourne les claims.

    Détecte l'algorithme automatiquement :
      - ``HS256`` → utilise ``SUPABASE_JWT_SECRET`` (legacy)
      - ``ES256`` / ``RS256`` / ``EdDSA`` → utilise le JWKS asymétrique
        à ``${SUPABASE_URL}/auth/v1/.well-known/jwks.json``

    Args:
        token : la valeur brute du JWT (sans le préfixe ``Bearer``).

    Returns:
        Le dictionnaire des claims décodés (au minimum `sub`, `email`,
        `aud`, `role`, `exp`, `iat`).

    Raises:
        InvalidTokenError : token vide, malformé, expiré, signature
            invalide ou backend non configuré.
    """
    if not token or not token.strip():
        raise InvalidTokenError("Empty bearer token.")

    token = token.strip()
    cached = _cache_get(token)
    if cached is not None:
        return cached

    alg = _peek_alg(token)

    decode_options = {
        "require": ["exp", "sub"],
        "verify_aud": False,
    }

    try:
        if alg == "HS256":
            # Mode legacy : exige SUPABASE_JWT_SECRET.
            secret = _load_legacy_secret()
            if not secret:
                raise InvalidTokenError(
                    "Token uses HS256 but SUPABASE_JWT_SECRET is not "
                    "configured on the backend."
                )
            claims: Dict[str, Any] = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options=decode_options,
            )
        elif alg in ("ES256", "RS256", "EdDSA"):
            # Mode asymétrique : récupère la public key via JWKS.
            jwks_client = _get_jwks_client()
            try:
                signing_key = jwks_client.get_signing_key_from_jwt(token)
            except _PyJWTInvalidTokenError:
                raise
            except Exception as exc:  # noqa: BLE001 — JWKS HTTP/parse error
                logger.error(
                    "JWKS fetch/parse error: %s", exc.__class__.__name__
                )
                raise InvalidTokenError(
                    "Could not fetch JWKS for token verification."
                ) from exc
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                options=decode_options,
            )
        else:
            raise InvalidTokenError(f"Unsupported JWT algorithm: {alg}.")
    except InvalidTokenError:
        raise
    except _PyJWTInvalidTokenError as exc:
        # Politique : on ne loggue jamais un JWT ni un header Authorization.
        logger.info("JWT rejected by PyJWT: %s", exc.__class__.__name__)
        raise InvalidTokenError("Invalid or expired token.") from exc
    except Exception as exc:  # noqa: BLE001 — défense en profondeur
        logger.error(
            "Unexpected JWT verification error: %s", exc.__class__.__name__
        )
        raise InvalidTokenError("Token verification failed.") from exc

    # Sanity check minimal : sub doit être un uuid string non vide.
    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise InvalidTokenError("Token missing valid 'sub' claim.")

    _cache_set(token, claims)
    return claims
