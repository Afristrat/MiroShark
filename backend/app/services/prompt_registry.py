"""Registre versionné des prompts de simulation (ADR-017, US-223).

Résout ``key + locale`` → contenu de la version active dans la table
Supabase ``simulation_prompts``. Cache in-process (process-wide, threads
Flask partagés) avec invalidation manuelle — pas de TTL, la fraîcheur est
garantie par ``invalidate()`` appelé après toute activation de version
(US-233).

Contrat de résilience : ``get()`` ne lève JAMAIS. Table vide, Supabase non
configuré, ou toute erreur réseau → ``None``, et l'appelant retombe sur son
prompt codé en dur. Le moteur de simulation ne doit jamais casser à cause
du registre.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from ..auth.supabase_client import SupabaseConfigError, get_supabase_admin
from ..utils.logger import get_logger

logger = get_logger("miroshark.services.prompt_registry")


@dataclass(frozen=True)
class ActivePrompt:
    """Contenu et version immuable de la version active."""

    content: str
    version: int


_cache: Dict[Tuple[str, str], ActivePrompt] = {}
_cache_lock = threading.Lock()


def get(key: str, locale: str, client: Any = None) -> Optional[str]:
    """Retourne le contenu de la version active pour ``(key, locale)``.

    La signature et le retour restent rétrocompatibles. Utiliser
    :func:`get_active` lorsqu'un service doit également persister la version.
    """
    active = get_active(key, locale, client=client)
    return active.content if active is not None else None


def get_active(key: str, locale: str, client: Any = None) -> Optional[ActivePrompt]:
    """Retourne contenu et version active, ou ``None`` sans jamais lever."""
    cache_key = (key, locale)
    with _cache_lock:
        cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        cli = client or get_supabase_admin()
        response = (
            cli.table("simulation_prompts")
            .select("content,version")
            .eq("key", key)
            .eq("locale", locale)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        if not rows:
            return None
        content = rows[0].get("content")
        # simulation_prompts.version est NOT NULL. Le défaut maintient les
        # doubles legacy injectables de get() compatibles.
        version = rows[0].get("version", 1)
        if (
            not isinstance(content, str)
            or not content
            or not isinstance(version, int)
            or isinstance(version, bool)
            or version < 1
        ):
            return None
    except SupabaseConfigError:
        logger.debug(
            "PromptRegistry.get_active(%s, %s): Supabase non configuré.",
            key, locale,
        )
        return None
    except Exception as exc:  # noqa: BLE001 — jamais casser le moteur pour le registre
        logger.warning(
            "PromptRegistry.get_active(%s, %s) failed: %s.",
            key, locale, exc.__class__.__name__,
        )
        return None

    active = ActivePrompt(content=content, version=version)
    with _cache_lock:
        _cache[cache_key] = active
    return active


def invalidate(key: Optional[str] = None, locale: Optional[str] = None) -> None:
    """Vide le cache — entrée précise si (key, locale) fournis, sinon tout.

    Appelé après toute activation de version (US-233) pour que le prochain
    ``get()`` relise Supabase au lieu de servir l'ancienne version en cache.
    """
    with _cache_lock:
        if key is not None and locale is not None:
            _cache.pop((key, locale), None)
        else:
            _cache.clear()
