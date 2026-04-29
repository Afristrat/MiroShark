"""Unit tests for WonderwallProfileGenerator._build_agent_system_prompt (US-038).

US-038 added a deterministic, locale-aware narrative `system_prompt` for each
synthetic Wonderwall agent. The system_prompt anchors the agent on the
simulation scenario, role, values, and authority sources — fixing the
"free-floating agent" issue where posts didn't match the persona's role.

These tests cover:

- Scenario truncation + presence in the rendered prompt.
- Persona field interpolation (realname / profession).
- Locale routing (`fr` / `en` / `ar`) using the LOCALE_FULL_NAMES helper.
- Length sanity (200-1000 chars window relaxed from the 200-400 narrative
  ideal — this builder is programmatic, not literary).
- Determinism + uniqueness across distinct personas.
- Robustness with missing fields (no city, no bio, no profession).
- Invalid-locale fallback handling.
"""

from app.services.wonderwall_profile_generator import (
    WonderwallProfileGenerator,
)


# ── Helpers ───────────────────────────────────────────────────────────────


def _build(profile, requirement="Lancement produit B2B SaaS au Maroc.", locale="fr"):
    """Convenience wrapper around the staticmethod under test."""
    return WonderwallProfileGenerator._build_agent_system_prompt(
        profile=profile,
        simulation_requirement=requirement,
        locale=locale,
    )


_KARIM = {
    "realname": "Karim Bennani",
    "profession": "CTO et co-fondateur",
    "city": "Casablanca",
    "bio": "32 ans, 6 développeurs sous sa responsabilité.",
    "stance": "supportive",
    "interested_topics": ["fintech", "mobile money", "DevOps"],
}


_AICHA = {
    "realname": "Aïcha Ndiaye",
    "profession": "Head of Growth e-commerce",
    "city": "Dakar",
    "bio": "Pilote l'acquisition d'un retailer 200 employés.",
    "stance": "neutral",
    "interested_topics": ["growth", "BCEAO", "mobile money"],
}


# ── Scenario interpolation ────────────────────────────────────────────────


def test_system_prompt_contains_simulation_requirement_first_chars():
    requirement = (
        "Cohorte synthétique de 50 prospects PME africains évaluant un nouvel "
        "outil SaaS B2B avec paiement mobile money intégré et conformité "
        "fiscale Maroc/Sénégal/Côte d'Ivoire/Nigeria."
    )
    out = _build(_KARIM, requirement=requirement)
    # First 100 chars of the requirement must appear verbatim in the prompt.
    assert requirement[:100] in out


def test_system_prompt_truncates_long_simulation_requirement():
    requirement = "Scénario verbeux. " * 200  # ~3400 chars, well over 600
    out = _build(_KARIM, requirement=requirement)
    # The 600-char cap guarantees the rendered prompt cannot embed the
    # full bloated requirement; an ellipsis sentinel "..." marks the cut.
    assert "..." in out
    assert requirement not in out


# ── Persona field interpolation ───────────────────────────────────────────


def test_system_prompt_contains_realname_and_profession():
    out = _build(_KARIM)
    assert "Karim Bennani" in out
    assert "CTO et co-fondateur" in out


def test_system_prompt_contains_city_when_present():
    out = _build(_KARIM)
    assert "Casablanca" in out


# ── Locale routing ────────────────────────────────────────────────────────


def test_system_prompt_locale_fr_uses_french_label():
    out = _build(_KARIM, locale="fr")
    assert "français" in out
    assert "(fr)" in out


def test_system_prompt_locale_en_uses_english_label():
    out = _build(_KARIM, locale="en")
    assert "English" in out
    assert "(en)" in out


def test_system_prompt_locale_ar_uses_arabic_label():
    out = _build(_KARIM, locale="ar")
    assert "العربية" in out
    assert "(ar)" in out


def test_system_prompt_invalid_locale_falls_back_to_french():
    # 'zz' is not in LOCALE_FULL_NAMES — helper must silently fall back to
    # the default ('fr'), matching the contract from US-043.
    out = _build(_KARIM, locale="zz")
    assert "français" in out
    assert "(fr)" in out


# ── Length sanity ─────────────────────────────────────────────────────────


def test_system_prompt_length_within_relaxed_bounds():
    out = _build(_KARIM)
    # The narrative ideal is 200-400 words but this is a programmatic
    # builder. Relax to a 200-1000 character window — generous enough to
    # cover all 5 supported templates without being a no-op.
    assert 200 <= len(out) <= 1000, (
        f"system_prompt length out of bounds: {len(out)}"
    )


# ── Uniqueness across distinct personas ───────────────────────────────────


def test_five_distinct_personas_yield_five_distinct_system_prompts():
    personas = [
        _KARIM,
        _AICHA,
        {
            "realname": "Ousmane Koné",
            "profession": "DSI banque tier-2",
            "city": "Abidjan",
            "stance": "opposing",
            "interested_topics": ["compliance", "BCEAO", "souveraineté"],
        },
        {
            "realname": "Fatou Diallo",
            "profession": "Co-founder edtech B2B2C",
            "city": "Dakar",
            "stance": "supportive",
            "interested_topics": ["edtech", "founders", "transparence"],
        },
        {
            "realname": "Amadou Diop",
            "profession": "Ops manager logistique",
            "city": "Lagos",
            "stance": "observer",
            "interested_topics": ["logistics", "TCO", "uptime"],
        },
    ]
    prompts = [_build(p) for p in personas]
    assert len(set(prompts)) == len(prompts), "system_prompts collide across distinct personas"


# ── Robustness with missing fields ────────────────────────────────────────


def test_system_prompt_handles_missing_city_and_bio():
    profile = {
        "realname": "Anonymous Trader",
        "profession": "Day Trader",
        # No city, no bio, no stance, no topics — all optional fields
        # must fall back gracefully without crashing.
    }
    out = _build(profile)
    assert "Anonymous Trader" in out
    assert "Day Trader" in out
    # Fallback marker for unknown city must appear instead of an empty
    # string mangling the prompt structure.
    assert "localisation non précisée" in out


def test_system_prompt_handles_completely_empty_profile():
    # Only requirement: realname has a fallback. Even a profile with only
    # an empty dict should not raise — it should produce a legible prompt
    # using the safe defaults.
    out = _build({})
    # No exception, non-empty output, default placeholders present.
    assert len(out) > 0
    assert "cet agent" in out  # default realname fallback
    assert "profession non précisée" in out  # default profession fallback
