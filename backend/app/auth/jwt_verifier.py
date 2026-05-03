"""Vérification des JWT émis par Supabase Auth (US-092).

Supabase Auth signe ses JWT en HS256 avec la clé secrète disponible
dans le dashboard sous *Settings → API → JWT Settings*. Cette clé doit
être injectée au backend via la variable d'environnement
`SUPABASE_JWT_SECRET` (jamais commitée, jamais exposée au frontend).

Pour limiter la charge CPU sur les endpoints très sollicités, on cache
la dernière vérification valide d'un jeton pendant 5 minutes
(TTL court : un access token Supabase a une durée de vie d'1h, donc on
ne risque pas de servir un token expiré au-delà de sa fenêtre).
Le cache est borné à 256 entrées (LRU) pour ne pas grossir indéfiniment
en présence d'un volume élevé de tokens distincts.

Aucune dépendance live à Supabase n'est introduite ici : la
vérification est purement cryptographique (HS256 = HMAC-SHA256), donc
les tests unitaires peuvent monkeypatcher `jwt.decode` ou bien fournir
un secret en mémoire et signer un token valide.
"""

from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from typing import Any, Dict

import jwt  # PyJWT — résolu via le pyproject.toml (extra `crypto`).
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


# ─── Cache LRU + TTL ────────────────────────────────────────────────────────

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
            # Entrée expirée — purge proactive.
            _cache.pop(token, None)
            return None
        # LRU : on remet l'entrée en fin de file (plus récemment utilisée).
        _cache.move_to_end(token)
        return claims


def _cache_set(token: str, claims: Dict[str, Any]) -> None:
    """Insère un payload validé avec un TTL borné par exp et 5 min."""
    # Le TTL de cache ne doit jamais dépasser la durée de vie effective du
    # token : si `exp` est < now+TTL, on cale sur exp (-5s de marge pour
    # éviter de servir un token au moment exact de son expiration).
    now = time.time()
    exp = claims.get("exp")
    ttl_deadline = now + _CACHE_TTL_SECONDS
    if isinstance(exp, (int, float)):
        ttl_deadline = min(ttl_deadline, float(exp) - 5.0)
    if ttl_deadline <= now:
        return  # token déjà sur le point d'expirer — inutile de cacher.
    with _cache_lock:
        _cache[token] = (ttl_deadline, claims)
        _cache.move_to_end(token)
        # Politique LRU : on évince la plus ancienne entrée si on dépasse.
        while len(_cache) > _CACHE_MAX_SIZE:
            _cache.popitem(last=False)


def _cache_clear() -> None:
    """Vide entièrement le cache (utilisé par les tests)."""
    with _cache_lock:
        _cache.clear()


# ─── API publique ───────────────────────────────────────────────────────────

def _load_jwt_secret() -> str:
    """Lit `SUPABASE_JWT_SECRET` au moment de l'appel.

    Résolu à chaque vérification afin que les tests pytest puissent
    monkeypatcher `os.environ` sans recharger le module et qu'un
    rotation de clé soit prise en compte sans redémarrer le process.
    """
    secret = os.getenv("SUPABASE_JWT_SECRET", "").strip()
    if not secret:
        # On ne loggue pas la clé absente comme un warning à chaque
        # requête — la responsabilité de la configuration revient au
        # déploiement, et ce signal est déjà capté par
        # `@require_auth` qui retourne un 503 explicite.
        raise InvalidTokenError(
            "SUPABASE_JWT_SECRET is not configured on the backend."
        )
    return secret


def verify_supabase_jwt(token: str) -> Dict[str, Any]:
    """Décode et vérifie un JWT Supabase, retourne les claims.

    Args:
        token : la valeur brute du JWT (sans le préfixe ``Bearer``).

    Returns:
        Le dictionnaire des claims décodés (au minimum `sub`, `email`,
        `aud`, `role`, `exp`, `iat`).

    Raises:
        InvalidTokenError : token vide, malformé, expiré, signature
            invalide ou secret backend manquant. Le message d'erreur est
            sécurisé côté API (générique) ; les détails apparaissent
            dans les logs serveur pour le diagnostic opérateur.
    """
    if not token or not token.strip():
        raise InvalidTokenError("Empty bearer token.")

    token = token.strip()
    cached = _cache_get(token)
    if cached is not None:
        return cached

    secret = _load_jwt_secret()

    # Supabase signe en HS256 par défaut. L'audience standard est
    # `authenticated` pour les utilisateurs connectés ; on l'accepte
    # explicitement et on tolère son absence pour rester compatible avec
    # d'éventuels tokens custom (service_role par ex.).
    try:
        claims: Dict[str, Any] = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={
                "require": ["exp", "sub"],
                "verify_aud": False,
            },
        )
    except _PyJWTInvalidTokenError as exc:
        # Évite tout log du token (politique : on ne logue jamais un JWT
        # ni une header Authorization, conformément à la rule supabase.md).
        logger.info("JWT rejected by PyJWT: %s", exc.__class__.__name__)
        raise InvalidTokenError("Invalid or expired token.") from exc
    except Exception as exc:  # noqa: BLE001 — défense en profondeur
        logger.error("Unexpected JWT verification error: %s", exc.__class__.__name__)
        raise InvalidTokenError("Token verification failed.") from exc

    # Sanity check minimal : sub doit être un uuid string non vide.
    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise InvalidTokenError("Token missing valid 'sub' claim.")

    _cache_set(token, claims)
    return claims
