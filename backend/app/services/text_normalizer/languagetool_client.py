"""Client HTTP léger vers une instance LanguageTool self-hosted.

Endpoint attendu : POST /v2/check
Env : LANGUAGETOOL_URL (défaut http://localhost:8010)

En cas d'indisponibilité, le client retourne une liste vide et loggue
un avertissement — il ne lève JAMAIS d'exception vers l'appelant.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List

import requests

logger = logging.getLogger("miroshark.text_normalizer.languagetool")

_DEFAULT_URL = "http://localhost:8010"
_TIMEOUT_S = 5


@dataclass
class Issue:
    """Problème détecté par LanguageTool (ou pyspellchecker en fallback)."""

    offset: int
    length: int
    message: str
    replacements: List[str] = field(default_factory=list)
    severity: str = "info"  # "info" | "warning" | "error"
    rule_id: str = ""


_LANG_MAP = {
    "fr": "fr-FR",
    "en": "en-US",
    "ar": "ar",
}


def check(text: str, lang: str) -> List[Issue]:
    """Envoie *text* à LanguageTool et retourne la liste d'issues parsées.

    Parameters
    ----------
    text:
        Texte brut à vérifier.
    lang:
        Code langue court (``'fr'``, ``'en'``, ``'ar'``).

    Returns
    -------
    List[Issue]
        Liste potentiellement vide si LanguageTool est down ou si aucun
        problème n'est détecté.
    """
    if not text or not text.strip():
        return []

    base_url = os.environ.get("LANGUAGETOOL_URL", _DEFAULT_URL).rstrip("/")
    lt_lang = _LANG_MAP.get(lang, lang)

    try:
        resp = requests.post(
            f"{base_url}/v2/check",
            data={"text": text, "language": lt_lang},
            timeout=_TIMEOUT_S,
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.exceptions.ConnectionError:
        logger.warning(
            "LanguageTool inaccessible sur %s — fallback liste vide.", base_url
        )
        return []
    except requests.exceptions.Timeout:
        logger.warning(
            "LanguageTool timeout (%ds) sur %s — fallback liste vide.",
            _TIMEOUT_S,
            base_url,
        )
        return []
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "LanguageTool erreur inattendue (%s) — fallback liste vide.", exc
        )
        return []

    issues: List[Issue] = []
    for match in payload.get("matches", []):
        context = match.get("context", {})
        offset = context.get("offset", match.get("offset", 0))
        length = context.get("length", match.get("length", 0))

        rule = match.get("rule", {})
        rule_id = rule.get("id", "")
        issue_type = match.get("type", {}).get("typeName", "Other")

        # Mapper le type LanguageTool sur notre sémantique de sévérité
        severity_map = {
            "misspelling": "error",
            "grammar": "warning",
            "style": "info",
            "Other": "info",
        }
        severity = severity_map.get(issue_type, "info")

        replacements = [r.get("value", "") for r in match.get("replacements", [])]

        issues.append(
            Issue(
                offset=offset,
                length=length,
                message=match.get("message", ""),
                replacements=replacements[:5],  # limiter à 5 suggestions
                severity=severity,
                rule_id=rule_id,
            )
        )

    return issues
