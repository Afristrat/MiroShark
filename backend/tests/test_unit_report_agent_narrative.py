"""Unit tests for ReportAgent narrative sections (US-041).

US-041 transforme le rapport final de Bassira d'un « résumé de logs » en un
rapport narratif orienté insight. Le system_prompt de planification est
customisé par `simulation_requirement` et 4 sections narratives obligatoires
sont forcées en plus des sections analytiques librement planifiées par le LLM :

1. « Le pari a-t-il été tenu ? »      — verdict prédiction vs résolution
2. « Qui a basculé ? »                — bascules de personas avec round + cause
3. « Qu'est-ce qui nous a surpris ? » — distributions observées vs attendues
4. « Qu'aurait-il fallu pour basculer le résultat ? » — counterfactual léger

Ces tests valident :

- La constante `_NARRATIVE_SECTIONS_REQUIRED` contient bien les 4 sections
  avec leurs titres canoniques en français.
- Le `PLAN_SYSTEM_PROMPT_BASE` contient le placeholder `{simulation_requirement}`.
- `_render_plan_system_prompt()` injecte le requirement dans le prompt rendu
  ET ajoute le bloc narratif des 4 sections obligatoires.
- Backward-compat : sans simulation_requirement, le prompt rendu n'inclut
  PAS le bloc narratif (legacy free-planning).
- L'helper `_build_narrative_section_directive()` retourne le bon bloc
  pour les 4 titres exacts et une chaîne vide pour les autres.
- L'application de `localize_system_prompt()` en bout de chaîne préserve
  l'instruction de locale (réutilisation du pattern test_unit_locale_prompt).

Conformément au pattern des autres `test_unit_*.py`, on ne touche pas au
LLMClient réel — on teste les transformations de prompts en pur Python.
"""

from app.services.report_agent import (
    PLAN_SYSTEM_PROMPT,
    PLAN_SYSTEM_PROMPT_BASE,
    _NARRATIVE_SECTIONS_PLAN_BLOCK,
    _NARRATIVE_SECTIONS_REQUIRED,
    _build_narrative_section_directive,
    _render_plan_system_prompt,
)
from app.utils.locale_prompt import localize_system_prompt


# ── Constants — _NARRATIVE_SECTIONS_REQUIRED ───────────────────────────────


def test_narrative_sections_required_has_exactly_four_sections():
    """4 sections narratives obligatoires, ni plus ni moins."""
    assert len(_NARRATIVE_SECTIONS_REQUIRED) == 4, (
        f"Expected 4 narrative sections, got {len(_NARRATIVE_SECTIONS_REQUIRED)}"
    )


def test_narrative_sections_required_titles_are_french_canonical():
    """Les 4 titres FR canoniques sont exactement ceux spécifiés dans US-041,
    dans l'ordre. Les majuscules accentuées et la ponctuation française
    (espace insécable avant ?) doivent être préservées au caractère près."""
    titles = [s["title"] for s in _NARRATIVE_SECTIONS_REQUIRED]
    expected = [
        "Le pari a-t-il été tenu ?",
        "Qui a basculé ?",
        "Qu'est-ce qui nous a surpris ?",
        "Qu'aurait-il fallu pour basculer le résultat ?",
    ]
    assert titles == expected, (
        "Narrative section titles diverged from US-041 spec.\n"
        f"got={titles}\nexpected={expected}"
    )


def test_narrative_sections_required_titles_first_letter_uppercase():
    """Chaque titre commence par une majuscule (vérification 1ʳᵉ lettre)."""
    for sec in _NARRATIVE_SECTIONS_REQUIRED:
        first = sec["title"][0]
        assert first.isupper(), (
            f"First letter of section title must be uppercase: '{sec['title']}'"
        )


def test_narrative_sections_required_each_has_description():
    """Chaque section narrative documente sa raison d'être pour traçabilité
    code (Amine relit le code, pas seulement les prompts)."""
    for sec in _NARRATIVE_SECTIONS_REQUIRED:
        assert "description" in sec
        assert len(sec["description"]) > 50, (
            f"Description too short for section '{sec['title']}'"
        )


# ── PLAN_SYSTEM_PROMPT — placeholder + injection ───────────────────────────


def test_plan_system_prompt_base_contains_simulation_requirement_placeholder():
    """Le template brut conserve `{simulation_requirement}` pour interpolation
    runtime dans `_render_plan_system_prompt()`."""
    assert "{simulation_requirement}" in PLAN_SYSTEM_PROMPT_BASE, (
        "PLAN_SYSTEM_PROMPT_BASE doit contenir le placeholder "
        "{simulation_requirement} pour injection runtime US-041."
    )


def test_plan_system_prompt_legacy_alias_still_exists():
    """Backward compat : l'ancien nom `PLAN_SYSTEM_PROMPT` reste exposé."""
    assert PLAN_SYSTEM_PROMPT is PLAN_SYSTEM_PROMPT_BASE


def test_render_plan_system_prompt_injects_requirement_text():
    """Le requirement passé à `_render_plan_system_prompt()` apparaît
    verbatim dans le prompt rendu."""
    requirement = "Test crisis 24h — bad-buzz Maroc fictif sur marque cosmétique."
    rendered = _render_plan_system_prompt(requirement)
    assert requirement in rendered
    # Le placeholder ne doit plus exister après interpolation.
    assert "{simulation_requirement}" not in rendered


def test_render_plan_system_prompt_includes_four_narrative_sections():
    """Quand un requirement est présent, les 4 titres FR canoniques
    apparaissent dans le bloc d'instructions au LLM."""
    rendered = _render_plan_system_prompt("Lancement produit B2B SaaS Maroc.")
    for narr in _NARRATIVE_SECTIONS_REQUIRED:
        assert narr["title"] in rendered, (
            f"Narrative section title missing from rendered prompt: '{narr['title']}'"
        )


def test_render_plan_system_prompt_mentions_us_041_marker():
    """Le marker US-041 est présent pour traçabilité de l'origine du bloc."""
    rendered = _render_plan_system_prompt("Some scenario.")
    assert "US-041" in rendered


def test_render_plan_system_prompt_legacy_no_requirement_drops_narrative_block():
    """Backward compat : un projet sans simulation_requirement (legacy)
    fait fonctionner le rapport SANS les 4 sections narratives forcées."""
    rendered_empty = _render_plan_system_prompt("")
    rendered_none = _render_plan_system_prompt(None)
    # Le bloc narratif (avec son marker exact) ne doit PAS être présent.
    block_marker = "[US-041 — Narrative Mandatory Sections]"
    assert block_marker not in rendered_empty
    assert block_marker not in rendered_none
    # Le prompt doit cependant rester utilisable (non vide, format ok).
    assert "Scenario Exploration Report" in rendered_empty
    assert "Scenario Exploration Report" in rendered_none


def test_narrative_plan_block_lists_all_four_titles():
    """Le bloc d'instructions narratif lui-même contient les 4 titres FR."""
    for narr in _NARRATIVE_SECTIONS_REQUIRED:
        assert narr["title"] in _NARRATIVE_SECTIONS_PLAN_BLOCK


# ── _build_narrative_section_directive — section-level directives ──────────


def test_build_narrative_directive_returns_block_for_each_required_title():
    """Chaque titre narratif obligatoire renvoie un bloc d'instructions
    non vide (injecté dans le SECTION_SYSTEM_PROMPT au runtime)."""
    for narr in _NARRATIVE_SECTIONS_REQUIRED:
        directive = _build_narrative_section_directive(narr["title"])
        assert directive, (
            f"Expected non-empty directive for '{narr['title']}'"
        )
        assert "US-041" in directive
        # La directive doit elle-même répéter le titre exact pour ancrage LLM.
        assert narr["title"] in directive


def test_build_narrative_directive_returns_empty_for_unknown_title():
    """Pour une section analytique standard (auto-planifiée), aucune
    directive narrative n'est appendée — le SECTION_SYSTEM_PROMPT reste
    inchangé pour ces sections."""
    assert _build_narrative_section_directive("Top influencers analysis") == ""
    assert _build_narrative_section_directive("Synthesis & Implications") == ""
    assert _build_narrative_section_directive("") == ""
    assert _build_narrative_section_directive(None) == ""


def test_build_narrative_directive_strips_whitespace_in_title_lookup():
    """Tolérance aux espaces accidentels en début/fin de titre."""
    directive = _build_narrative_section_directive("  Qui a basculé ?  ")
    assert directive
    assert "Qui a basculé ?" in directive


# ── Snapshot test minimal — system prompt généré pour un mock ──────────────


def test_snapshot_system_prompt_contains_requirement_and_four_sections():
    """Snapshot test minimal : avec un mock simulation_requirement,
    le system_prompt généré contient le requirement texte ET les 4 titres
    narratifs en consigne (validation end-to-end de l'interpolation)."""
    requirement = (
        "Cohorte synthétique 50 prospects PME Maroc/Sénégal/CI évaluant un "
        "outil SaaS B2B avec mobile money intégré. Cible : 30% d'intention "
        "d'achat ferme à S10."
    )
    rendered = _render_plan_system_prompt(requirement)

    # Requirement présent verbatim
    assert requirement in rendered

    # 4 titres narratifs présents
    assert "Le pari a-t-il été tenu ?" in rendered
    assert "Qui a basculé ?" in rendered
    assert "Qu'est-ce qui nous a surpris ?" in rendered
    assert "Qu'aurait-il fallu pour basculer le résultat ?" in rendered

    # Mots-clefs spécifiques aux directives narratives présents
    # (ces marqueurs sont propres à l'implémentation US-041, pas génériques).
    assert "narrative" in rendered.lower()
    assert "counterfactual" in rendered.lower()


# ── Integration with localize_system_prompt (US-043) ───────────────────────


def test_localize_system_prompt_applied_on_top_preserves_directive():
    """`localize_system_prompt()` est composé avec `_render_plan_system_prompt()`
    dans `plan_outline()`. On vérifie que la composition donne bien :
      requirement injecté + bloc narratif + directive de locale FR.
    Pattern réutilisé du test_unit_locale_prompt.py : on appelle le helper
    locale-aware sur la sortie du renderer narratif et on cherche les
    marqueurs des deux features (US-041 + US-043) dans le résultat final."""
    requirement = "Test scenario crisis 24h."
    rendered = _render_plan_system_prompt(requirement)
    final = localize_system_prompt(rendered, locale="fr")

    # US-041 : bloc narratif et requirement préservés
    assert requirement in final
    assert "Le pari a-t-il été tenu ?" in final
    assert "Qui a basculé ?" in final

    # US-043 : directive de locale appendée
    assert "français" in final
    assert "code `fr`" in final
    assert "[bassira-locale-instruction]" in final


def test_localize_system_prompt_applied_on_legacy_no_requirement():
    """Legacy mode + locale FR : la directive de locale s'applique même
    sans bloc narratif. Backward-compat preservée bout-en-bout."""
    rendered = _render_plan_system_prompt("")
    final = localize_system_prompt(rendered, locale="fr")
    # US-041 : bloc narratif ABSENT (legacy)
    assert "[US-041 — Narrative Mandatory Sections]" not in final
    # US-043 : directive de locale présente
    assert "français" in final
    assert "code `fr`" in final
