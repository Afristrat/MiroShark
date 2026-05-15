"""US-B01 — Service proxy Bassira → Kairos pour la recherche dynamique.

Encapsule :
  * l'appel HTTP au pipeline Kairos (POST /research-from-seed,
    GET /research-from-seed?session_id=…) avec injection x-api-key et
    timeouts configurés ;
  * un cache TTL (Redis si REDIS_URL, sinon fallback in-process) pour
    éviter de re-trigger le pipeline 170s quand la même graine est
    soumise par un user qui re-clique trop vite ;
  * la traduction des erreurs HTTP/réseau en error_code lisibles côté
    Bassira (KAIROS_TIMEOUT, KAIROS_UNREACHABLE, KAIROS_INVALID_KEY…).

Le cache n'est utile QUE sur le POST from-seed (la même graine doit
réutiliser le même session_id pendant 1h). Le GET status n'est pas
cacheable côté Bassira car le statut change pendant le pipeline (running
→ completed). On peut en revanche cacher 24h le payload final quand le
status=completed pour éviter de re-hit Kairos après expiration de la
session côté Kairos (TTL 24h cron purge).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import requests

from ..config import Config


logger = logging.getLogger("miroshark.kairos_proxy")


# ─── Cache TTL ────────────────────────────────────────────────────────────────


class _TtlCache:
    """Cache TTL minimaliste : Redis si REDIS_URL défini, sinon dict en
    mémoire process. Le mode in-process n'a pas d'éviction LRU (juste TTL),
    mais l'API Kairos étant rate-limitée 60 RPM et chaque entrée pesant
    quelques KB, on tolère un footprint borné par l'usage réel.
    """

    PREFIX = "bassira:research:"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._memory: Dict[str, Tuple[float, str]] = {}
        self._client = None
        url = (Config.REDIS_URL or "").strip()
        if url:
            try:
                # `redis` est déjà tiré par `rq>=1.15` (US-129) donc pas
                # de nouvelle dépendance ajoutée au pyproject.
                import redis  # type: ignore

                self._client = redis.Redis.from_url(
                    url, decode_responses=True, socket_timeout=2.0
                )
                # `ping()` force la résolution + auth — si ça pète au
                # boot on bascule en in-process plutôt que de planter
                # tous les appels research.
                self._client.ping()
                logger.info("kairos_proxy cache backend: redis (%s)", url)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "kairos_proxy: REDIS_URL set mais ping a échoué (%s) "
                    "— fallback cache in-process.",
                    exc,
                )
                self._client = None
        if not self._client:
            logger.info("kairos_proxy cache backend: in-process dict")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        full = self.PREFIX + key
        if self._client is not None:
            try:
                raw = self._client.get(full)
                if raw:
                    return json.loads(raw)
                return None
            except Exception as exc:  # noqa: BLE001
                logger.warning("redis get(%s) failed: %s", full, exc)
                return None
        # In-process
        with self._lock:
            entry = self._memory.get(full)
            if not entry:
                return None
            expires_at, raw = entry
            if expires_at < time.time():
                self._memory.pop(full, None)
                return None
            return json.loads(raw)

    def set(self, key: str, value: Dict[str, Any], ttl_s: int) -> None:
        full = self.PREFIX + key
        raw = json.dumps(value, ensure_ascii=False)
        if self._client is not None:
            try:
                self._client.setex(full, int(ttl_s), raw)
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("redis setex(%s) failed: %s", full, exc)
                return
        # In-process
        with self._lock:
            self._memory[full] = (time.time() + ttl_s, raw)

    def delete(self, key: str) -> None:
        """F5 2026-05-15 — invalidation explicite d'une entrée.
        Best-effort : ne pète pas si la clé n'existe pas ou si Redis down."""
        full = self.PREFIX + key
        if self._client is not None:
            try:
                self._client.delete(full)
            except Exception as exc:  # noqa: BLE001
                logger.warning("redis delete(%s) failed: %s", full, exc)
        with self._lock:
            self._memory.pop(full, None)

    def purge_expired(self) -> int:
        """Nettoie les entrées expirées du cache in-process (no-op en Redis)."""
        if self._client is not None:
            return 0
        now = time.time()
        with self._lock:
            stale = [k for k, (exp, _) in self._memory.items() if exp < now]
            for k in stale:
                self._memory.pop(k, None)
            return len(stale)


# Singleton cache process-wide. Lazy : créé au 1er appel pour que les
# tests puissent monkeypatcher Config.REDIS_URL avant init.
_CACHE: Optional[_TtlCache] = None


def _cache() -> _TtlCache:
    global _CACHE
    if _CACHE is None:
        _CACHE = _TtlCache()
    return _CACHE


def _reset_cache_for_tests() -> None:
    """Re-init le cache (utilisé par la fixture pytest qui monkeypatch
    REDIS_URL pour exercer le path in-process)."""
    global _CACHE
    _CACHE = None


# ─── Hashing clé de cache ─────────────────────────────────────────────────────


def cache_key_from_seed(
    seed: str,
    lang: str,
    sector_hint: Optional[str] = None,
    depth_hint: Optional[int] = None,
) -> str:
    """Calcule sha256(seed|lang|sector_hint|depth_hint) — clé déterministe
    pour le cache POST from-seed."""
    norm = "|".join([
        (seed or "").strip(),
        (lang or "").strip().lower(),
        (sector_hint or "").strip(),
        "" if depth_hint is None else str(depth_hint),
    ])
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


# ─── Erreurs ──────────────────────────────────────────────────────────────────


@dataclass
class KairosError(Exception):
    """Erreur typée pour les pannes proxy. Le code finit dans le payload
    Bassira ; le status HTTP est utilisé pour la réponse Flask."""

    error_code: str
    message: str
    status: int = 502
    detail: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:  # pragma: no cover — display only
        return f"{self.error_code}: {self.message}"


class KairosNotConfigured(KairosError):
    def __init__(self) -> None:
        super().__init__(
            error_code="KAIROS_NOT_CONFIGURED",
            message=(
                "KAIROS_API_URL or KAIROS_API_KEY missing in environment. "
                "Set them on Coolify and redeploy."
            ),
            status=503,
        )


# ─── Appels HTTP ──────────────────────────────────────────────────────────────


def _require_config() -> Tuple[str, str]:
    url = (Config.KAIROS_API_URL or "").rstrip("/")
    key = Config.KAIROS_API_KEY or ""
    if not url or not key:
        raise KairosNotConfigured()
    return url, key


def post_from_seed(
    seed: str,
    lang: str,
    sector_hint: Optional[str] = None,
    depth_hint: Optional[int] = None,
) -> Dict[str, Any]:
    """POST {KAIROS_API_URL}/research-from-seed.

    Retourne le payload Kairos ``{ok, session_id, status, message}``.
    Lève ``KairosError`` sur erreur (timeout, 401, 429, 5xx).

    Cache : si la même (seed, lang, sector, depth) a été soumise depuis
    moins d'1h et que la session est toujours valide côté Kairos (TTL
    24h), on retourne la session_id cachée sans re-frapper Kairos.
    """
    url_base, api_key = _require_config()
    key = cache_key_from_seed(seed, lang, sector_hint, depth_hint)
    cached = _cache().get(f"seed:{key}")
    if cached:
        # Marqué pour que l'endpoint puisse indiquer cached:true au frontend.
        cached = {**cached, "cached": True}
        return cached

    body: Dict[str, Any] = {"seed": seed, "lang": lang}
    if sector_hint:
        body["sector_hint"] = sector_hint
    if depth_hint is not None:
        body["depth_hint"] = depth_hint

    try:
        resp = requests.post(
            f"{url_base}/research-from-seed",
            json=body,
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=Config.KAIROS_POST_TIMEOUT_S,
        )
    except requests.exceptions.Timeout as exc:
        raise KairosError(
            error_code="KAIROS_TIMEOUT",
            message=f"Kairos POST timed out after {Config.KAIROS_POST_TIMEOUT_S}s.",
            status=504,
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise KairosError(
            error_code="KAIROS_UNREACHABLE",
            message="Could not reach Kairos.",
            status=502,
            detail={"reason": str(exc)[:200]},
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise KairosError(
            error_code="KAIROS_REQUEST_FAILED",
            message="Unexpected requests error.",
            status=502,
            detail={"reason": str(exc)[:200]},
        ) from exc

    return _handle_kairos_response(resp, cache_key=key)


def _handle_kairos_response(
    resp: requests.Response, *, cache_key: Optional[str]
) -> Dict[str, Any]:
    """Parse + relaie les erreurs Kairos. Cache la session_id en cas de 202."""
    try:
        data = resp.json()
    except ValueError:
        data = {}
    status = resp.status_code

    if status == 401:
        raise KairosError(
            error_code="KAIROS_INVALID_KEY",
            message="x-api-key rejetée par Kairos.",
            status=502,
            detail=data,
        )
    if status == 429:
        raise KairosError(
            error_code="KAIROS_RATE_LIMITED",
            message="Kairos rate limit (60 RPM).",
            status=429,
            detail=data,
        )
    if status == 403:
        raise KairosError(
            error_code="KAIROS_FORBIDDEN",
            message="Kairos a refusé la requête (CORS ou scope).",
            status=502,
            detail=data,
        )
    if status >= 500:
        raise KairosError(
            error_code="KAIROS_SERVER_ERROR",
            message=f"Kairos a répondu {status}.",
            status=502,
            detail=data,
        )
    if status >= 400:
        # 400 = validation côté Kairos (seed_too_short, etc.) — on relaie
        # tel quel pour que le frontend puisse afficher la cause exacte.
        raise KairosError(
            error_code=str(data.get("error_code") or "KAIROS_BAD_REQUEST"),
            message=str(data.get("error") or data.get("message") or "Bad request"),
            status=400,
            detail=data,
        )

    # 200/202 — succès
    session_id = data.get("session_id")
    if cache_key and session_id:
        _cache().set(
            f"seed:{cache_key}",
            {
                "ok": True,
                "session_id": session_id,
                "status": data.get("status", "running"),
            },
            ttl_s=3600,  # 1h
        )
        # F5 2026-05-15 — index inverse session_id → cache_key pour
        # invalider la cache seed quand le poll status découvre que
        # la session a fini en failed/timeout. Sinon Bassira retourne
        # le même session_id mort pendant 1h.
        _cache().set(
            f"session:{session_id}",
            {"cache_key": cache_key},
            ttl_s=3600,
        )
    return data


def get_status(session_id: str) -> Dict[str, Any]:
    """GET {KAIROS_API_URL}/research-from-seed?session_id=<uuid>.

    Cache : si Kairos retourne status=completed, on cache le payload
    pendant 24h pour absorber l'expiration de research_sessions côté
    Kairos (cron purge horaire, TTL 24h). Si status=running/failed/timeout,
    pas de cache (le statut peut changer ou doit être re-traité).
    """
    url_base, api_key = _require_config()

    cached = _cache().get(f"status:{session_id}")
    if cached:
        return {**cached, "cached": True}

    try:
        resp = requests.get(
            f"{url_base}/research-from-seed",
            params={"session_id": session_id},
            headers={
                "x-api-key": api_key,
                "Accept": "application/json",
            },
            timeout=Config.KAIROS_GET_TIMEOUT_S,
        )
    except requests.exceptions.Timeout as exc:
        raise KairosError(
            error_code="KAIROS_TIMEOUT",
            message=f"Kairos GET timed out after {Config.KAIROS_GET_TIMEOUT_S}s.",
            status=504,
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise KairosError(
            error_code="KAIROS_UNREACHABLE",
            message="Could not reach Kairos.",
            status=502,
            detail={"reason": str(exc)[:200]},
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise KairosError(
            error_code="KAIROS_REQUEST_FAILED",
            message="Unexpected requests error.",
            status=502,
            detail={"reason": str(exc)[:200]},
        ) from exc

    if resp.status_code == 404:
        raise KairosError(
            error_code="SESSION_NOT_FOUND",
            message="session_id introuvable ou expirée (TTL 24h Kairos).",
            status=404,
        )
    if resp.status_code == 400:
        try:
            data = resp.json()
        except ValueError:
            data = {}
        raise KairosError(
            error_code=str(data.get("error_code") or "BAD_REQUEST"),
            message=str(data.get("error") or "Bad request"),
            status=400,
            detail=data,
        )

    # 200 OK — pipe-through, cache si terminé
    try:
        data = resp.json()
    except ValueError as exc:
        raise KairosError(
            error_code="KAIROS_INVALID_RESPONSE",
            message="Kairos a répondu sans JSON valide.",
            status=502,
        ) from exc

    status_lower = (data.get("status") or "").lower()
    if status_lower == "completed":
        _cache().set(f"status:{session_id}", data, ttl_s=24 * 3600)
    elif status_lower in ("failed", "timeout"):
        # F5 2026-05-15 — la session est morte : invalider la cache
        # seed:{cache_key} pour que le prochain POST avec la même graine
        # déclenche un VRAI nouveau pipeline au lieu de retourner le
        # session_id zombie pendant 1h. Couvre RC-6.
        reverse = _cache().get(f"session:{session_id}")
        if isinstance(reverse, dict):
            ck = reverse.get("cache_key")
            if isinstance(ck, str) and ck:
                _cache().delete(f"seed:{ck}")
                _cache().delete(f"session:{session_id}")
                logger.info(
                    "kairos_proxy: invalidated seed cache for session=%s status=%s",
                    session_id, status_lower,
                )
    return data
