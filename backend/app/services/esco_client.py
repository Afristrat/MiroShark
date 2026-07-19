"""Client ESCO cache-first pour les fiches métiers (US-228, ADR-016).

Stratégie : cache Supabase (``occupation_profiles``) d'abord, API ESCO
publique sinon, échec réseau → ``None`` journalisé (jamais d'exception —
même contrat de résilience que ``prompt_registry``, US-223 : le moteur de
simulation ne doit jamais casser à cause d'une indisponibilité ESCO).

Requête API en 2 temps, schéma vérifié le 2026-07-05 (script de référence
``~/.claude/skills/prompt-engineer-pro/scripts/esco-role.py``, testé OK
FR/AR) :
    1. GET /search?text=...&language=...&type=occupation
       -> ``_embedded.results[]`` {title, uri}
    2. GET /resource/occupation?uri=...&language=...
       -> ``description.<lang>.literal`` + ``_links.hasEssentialSkill[]``/
          ``hasOptionalSkill[]`` {title}

urllib stdlib exclusivement (Ponytail — zéro dépendance nouvelle, ADR-016 §3.2).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

from ..auth.supabase_client import SupabaseConfigError, get_supabase_admin
from ..utils.logger import get_logger

logger = get_logger("miroshark.services.esco_client")

ESCO_API_BASE = "https://ec.europa.eu/esco/api"
_REQUEST_TIMEOUT_SECONDS = 20


def _normalize(label: str) -> str:
    return label.strip().lower()


def _title_matches_query(query: str, title: Any) -> bool:
    """Accept only an exact ESCO title or one exact slash-separated variant."""
    if not isinstance(title, str):
        return False
    normalized_query = _normalize(query)
    return any(normalized_query == _normalize(variant) for variant in title.split("/"))


def _esco_get(url: str) -> Optional[Dict[str, Any]]:
    """GET JSON sur l'API ESCO — ne lève jamais, retourne None sur échec."""
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict):
                return payload
            logger.warning("ESCO API : objet JSON attendu sur %s", url)
    except urllib.error.HTTPError as exc:
        logger.warning("ESCO API HTTP %s sur %s", exc.code, url)
    except urllib.error.URLError as exc:
        logger.warning("ESCO API injoignable (%s) sur %s", exc.reason, url)
    except json.JSONDecodeError:
        logger.warning("ESCO API : réponse JSON invalide sur %s", url)
    except Exception as exc:  # noqa: BLE001 — jamais casser la génération de personas
        logger.warning("ESCO API erreur inattendue (%s) sur %s", exc.__class__.__name__, url)
    return None


def _extract_description(resource: Dict[str, Any], lang: str) -> str:
    descriptions = resource.get("description") or {}
    entry = descriptions.get(lang) or next(iter(descriptions.values()), None)
    if isinstance(entry, dict):
        return entry.get("literal", "")
    return ""


def _fetch_from_esco_api(query: str, lang: str) -> Tuple[Optional[Dict[str, Any]], bool]:
    """Return ``(profile, definitive_miss)`` after the ESCO lookup."""
    search_url = (
        f"{ESCO_API_BASE}/search?"
        f"text={quote(query)}&language={lang}&type=occupation&limit=5"
    )
    data = _esco_get(search_url)
    if not data:
        return None, False
    embedded = data.get("_embedded")
    if not isinstance(embedded, dict):
        return None, False
    results = embedded.get("results")
    if not isinstance(results, list):
        return None, False
    if not results:
        return None, True
    best = next(
        (
            result
            for result in results
            if isinstance(result, dict) and _title_matches_query(query, result.get("title"))
        ),
        None,
    )
    if best is None:
        logger.info("ESCO search result rejected as non-exact match for '%s'.", query)
        return None, True
    occupation_uri = best.get("uri")
    if not occupation_uri:
        return None, False

    detail_url = (
        f"{ESCO_API_BASE}/resource/occupation?"
        f"uri={quote(occupation_uri, safe='')}&language={lang}"
    )
    detail = _esco_get(detail_url)
    if not detail:
        return None, False
    links = detail.get("_links")
    if not isinstance(links, dict):
        links = {}
    essential = links.get("hasEssentialSkill")
    optional = links.get("hasOptionalSkill")
    if not isinstance(essential, list):
        essential = []
    if not isinstance(optional, list):
        optional = []
    return (
        {
            "occupation_uri": occupation_uri,
            "definition": _extract_description(detail, lang),
            "essential_skills": [
                skill.get("title", "")
                for skill in essential
                if isinstance(skill, dict) and skill.get("title")
            ],
            "optional_skills": [
                skill.get("title", "")
                for skill in optional
                if isinstance(skill, dict) and skill.get("title")
            ],
        },
        False,
    )


def _record_unresolved_occupation(label: str, lang: str, client: Any = None) -> None:
    """Persist an absent ESCO term for US-230 without affecting persona generation."""
    try:
        (client or get_supabase_admin()).table("occupation_profile_unresolved").insert(
            {"label": label, "lang": lang}
        ).execute()
    except SupabaseConfigError:
        pass
    except Exception as exc:  # noqa: BLE001 — duplicate and unavailable storage are best-effort
        logger.debug("ESCO unresolved trace unavailable (%s) for '%s'.", exc.__class__.__name__, label)


def get_occupation_profile(
    query: str, lang: str = "fr", client: Any = None,
) -> Optional[Dict[str, Any]]:
    """Retourne la fiche métier pour ``query`` (cache d'abord, API sinon).

    Args:
        query: libellé du métier recherché (ex. "analyste financier").
        lang: langue ESCO (fr | en | ar | ...).
        client: client Supabase injectable (tests).

    Returns:
        ``{"occupation_uri", "label", "lang", "definition",
        "essential_skills", "optional_skills", "source"}`` ou ``None`` si
        introuvable/injoignable ET cache vide (jamais d'exception — le
        caller retombe sur un persona sans bloc expertise, US-229).
    """
    normalized = _normalize(query)
    if not normalized:
        return None

    try:
        cli = client or get_supabase_admin()
        response = (
            cli.table("occupation_profiles")
            .select("occupation_uri, label, lang, definition, essential_skills, optional_skills, source")
            .eq("label", normalized)
            .eq("lang", lang)
            .limit(1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        if rows:
            return rows[0]
    except SupabaseConfigError:
        logger.debug("ESCO cache: Supabase non configuré — appel API direct.")
    except Exception as exc:  # noqa: BLE001 — cache indisponible != échec fatal
        logger.warning("ESCO cache lookup failed (%s) — appel API direct.", exc.__class__.__name__)

    # Cache miss (ou cache injoignable) — appel API.
    fetched, definitive_miss = _fetch_from_esco_api(query, lang)
    if fetched is None:
        logger.warning(
            "ESCO: profil introuvable pour '%s' (%s) — persona sans bloc expertise.",
            query, lang,
        )
        if definitive_miss:
            _record_unresolved_occupation(normalized, lang, client=client)
        return None

    profile: Dict[str, Any] = {
        "occupation_uri": fetched["occupation_uri"],
        "label": normalized,
        "lang": lang,
        "definition": fetched["definition"],
        "essential_skills": fetched["essential_skills"],
        "optional_skills": fetched["optional_skills"],
        "source": "esco",
    }

    try:
        cli = client or get_supabase_admin()
        cli.table("occupation_profiles").insert(profile).execute()
    except SupabaseConfigError:
        pass  # Pas de cache disponible — le profil reste utilisable ce round.
    except Exception as exc:  # noqa: BLE001 — écriture cache best-effort
        msg = str(exc)
        if "duplicate" not in msg.lower() and "23505" not in msg:
            logger.warning("ESCO cache write failed (%s) pour '%s'.", exc.__class__.__name__, query)

    return profile
