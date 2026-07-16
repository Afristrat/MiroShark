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
from typing import Any, Dict, Optional, Tuple

from ..auth.supabase_client import SupabaseConfigError, get_supabase_admin
from ..utils.logger import get_logger

logger = get_logger("miroshark.services.prompt_registry")

_cache: Dict[Tuple[str, str], str] = {}
_cache_lock = threading.Lock()


def get(key: str, locale: str, client: Any = None) -> Optional[str]:
    """Retourne le contenu de la version active pour ``(key, locale)``.

    Args:
        key: identifiant technique stable du prompt (ex.
            ``arena.polymarket.system``).
        locale: locale du prompt (``fr`` | ``en`` | ``ar``).
        client: client Supabase injectable (tests).

    Returns:
        Le contenu de la version active, ou ``None`` si absente/injoignable
        (jamais d'exception — cf. docstring module).
    """
    cache_key = (key, locale)
    with _cache_lock:
        if cache_key in _cache:
            return _cache[cache_key]

    try:
        cli = client or get_supabase_admin()
        response = (
            cli.table("simulation_prompts")
            .select("content")
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
        if not isinstance(content, str) or not content:
            return None
    except SupabaseConfigError:
        logger.debug(
            "PromptRegistry.get(%s, %s): Supabase non configuré — fallback codé.",
            key, locale,
        )
        return None
    except Exception as exc:  # noqa: BLE001 — jamais casser le moteur pour le registre
        logger.warning(
            "PromptRegistry.get(%s, %s) failed: %s — fallback codé.",
            key, locale, exc.__class__.__name__,
        )
        return None

    with _cache_lock:
        _cache[cache_key] = content
    return content


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
