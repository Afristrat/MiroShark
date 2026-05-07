"""US-043 + US-138.3 — locale_prompt helpers.

Couvre :
    01. `localize_system_prompt` injecte une instruction langue + sentinel
    02. Idempotence : second appel ne redouble pas l'instruction
    03. Locale invalide → fallback FR (DEFAULT_LOCALE)
    04. US-138.3 — clause traduction citations présente pour FR/EN/AR
    05. US-138.3 — liste explicite des exceptions (acronymes, noms propres)
    06. US-138.3 — étape de relecture (control qualité avant réponse)
    07. `get_request_locale` hors contexte Flask → default
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.utils.locale_prompt import (  # noqa: E402
    DEFAULT_LOCALE,
    LOCALE_FULL_NAMES,
    get_request_locale,
    localize_system_prompt,
)


# ── localize_system_prompt — base ────────────────────────────────────────────


def test_localize_appends_instruction_for_fr():
    out = localize_system_prompt("BASE PROMPT", locale="fr")
    assert "BASE PROMPT" in out
    assert "français" in out
    assert "[bassira-locale-instruction]" in out


def test_localize_idempotent():
    once = localize_system_prompt("X", locale="fr")
    twice = localize_system_prompt(once, locale="fr")
    assert once == twice, "Second appel doit être no-op (sentinel détecté)"


def test_localize_invalid_locale_fallback_to_default():
    out = localize_system_prompt("X", locale="zz")
    expected_full = LOCALE_FULL_NAMES[DEFAULT_LOCALE]
    assert expected_full in out


# ── US-138.3 — clause traduction citations ──────────────────────────────────


@pytest.mark.parametrize("locale", ["fr", "en", "ar"])
def test_us138_translation_clause_present(locale):
    """La clause US-138 doit être présente quelle que soit la locale cible."""
    out = localize_system_prompt("X", locale=locale)
    assert "US-138" in out, "Marqueur US-138 doit pointer la clause de traduction"
    full_name = LOCALE_FULL_NAMES[locale]
    assert "traduire" in out.lower() or "translate" in out.lower() or "ترجم" in out, (
        f"Le mot 'traduire' doit apparaître dans la clause US-138 (locale={locale})"
    )
    # La langue cible doit être explicitement nommée dans la clause
    assert full_name in out


def test_us138_proper_nouns_exceptions_listed():
    """Les exceptions (noms propres, acronymes) doivent être listées explicitement."""
    out = localize_system_prompt("X", locale="fr")
    # Au moins quelques acronymes typiques du contexte MENA
    assert "CGEM" in out or "OCP" in out or "FMI" in out, (
        "La clause US-138 doit nommer des exemples d'acronymes à conserver"
    )


def test_us138_quality_check_step_present():
    """L'étape « relecture qualité avant de répondre » doit être instruite."""
    out = localize_system_prompt("X", locale="fr")
    # Mots-clés du contrôle qualité — résistant à de petites refontes
    has_review = "Contrôle qualité" in out or "relis" in out.lower() or "relecture" in out.lower()
    assert has_review, (
        "La clause US-138 doit imposer une relecture finale pour éliminer "
        "les fragments anglais résiduels."
    )


# ── get_request_locale hors Flask ────────────────────────────────────────────


def test_get_request_locale_outside_flask_returns_default():
    """En dehors d'un contexte Flask, on retourne le default sans crash."""
    out = get_request_locale()
    assert out == DEFAULT_LOCALE


def test_get_request_locale_custom_default():
    out = get_request_locale(default="en")
    assert out == "en"
