"""
Tests pytest pour US-124 — Enricher LLM (insights + pivotal_moments + narratives).

Couverture (≥ 10 tests) :
    01. _compute_kpi_hero : KPIHero rempli avec champs corrects depuis outcome
    02. _compute_kpi_hero : verdict vide quand outcome est None
    03. _compute_kpi_hero : brier dérivé de quality_metrics.coherence
    04. _detect_pivotal_moments : détecte bascule artificielle > 0.20
    05. _detect_pivotal_moments : aucun moment pivot si variation < 0.20
    06. _detect_pivotal_moments : moments triés par round ascendant
    07. _generate_chart_narratives : 5 entrées dans interpretations après enrich
    08. Cache LRU narrative : 2 appels successifs → 1 seul appel LLM
    09. Fallback LLM down : raise géré, texte fallback présent dans interpretations
    10. _extract_executive_takeaways : 3 takeaways après enrich
    11. Cache LRU takeaways : 2 appels → 1 seul appel LLM
    12. _pass_through_normalizer : texte FR avec 'Etat' → 'État' après enrich
    13. enrich() retourne bien le contexte (chaînage)
    14. Fallback LLM None (client non configuré) → texte générique, pas de crash
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock

import pytest

# ── Ajout backend/ au sys.path ────────────────────────────────────────────────
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# ── Imports sous test ─────────────────────────────────────────────────────────
from app.services.report_pdf.enricher import (
    Enricher,
    _LLM_FALLBACK,
    _narrative_cache,
    _takeaway_cache,
)
from app.services.report_pdf.schema import (
    AgentState,
    KPIHero,
    Outcome,
    Outline,
    PDFReportContext,
    QualityMetrics,
    Round,
    Trajectory,
)

# ─── IDs valides (format regex schema.py) ─────────────────────────────────────
VALID_REPORT_ID = "report_aabbcc112233"
VALID_SIM_ID = "sim_112233aabbcc"


# ─── Fixture PDFReportContext minimale ────────────────────────────────────────


def _make_context(
    *,
    lang: str = "fr",
    with_outcome: bool = True,
    with_trajectory: bool = False,
) -> PDFReportContext:
    """Construit un PDFReportContext minimal valide pour les tests."""
    ctx = PDFReportContext(
        report_id=VALID_REPORT_ID,
        simulation_id=VALID_SIM_ID,
        lang=lang,  # type: ignore[arg-type]
    )

    if with_outcome:
        ctx.outcome = Outcome(
            verdict="Le marché demeure haussier malgré la pression réglementaire.",
            bullish_pct=62.5,
            bearish_pct=30.0,
            nb_rounds=5,
            confidence=0.78,
            quality_metrics=QualityMetrics(
                coherence=0.85,
                diversity=0.70,
                plausibility=0.80,
                alignment=0.75,
            ),
        )

    if with_trajectory:
        ctx.trajectory = _make_trajectory()

    ctx.outline = Outline(
        title="Rapport de simulation",
        summary="Synthèse exécutive de la simulation.",
    )
    return ctx


def _make_trajectory(
    *,
    agents: List[Dict] | None = None,
    n_rounds: int = 3,
) -> Trajectory:
    """Construit une Trajectory de test avec n rounds.

    Si agents est None, crée 2 agents avec des scores stables.
    """
    if agents is None:
        agents = [
            {"agent_id": "ag1", "name": "Alice", "stance": "bullish", "score": 0.5},
            {"agent_id": "ag2", "name": "Bob", "stance": "bearish", "score": -0.3},
        ]

    rounds = []
    for i in range(n_rounds):
        rnd = Round(
            round_idx=i,
            agents=[AgentState(**a) for a in agents],
        )
        rounds.append(rnd)
    return Trajectory(rounds=rounds)


def _make_mock_llm(response: str = "Insight test : stabilité dominante.") -> MagicMock:
    """Crée un LLM mock qui retourne toujours la même réponse."""
    mock = MagicMock()
    mock.chat.return_value = response
    return mock


# ─── Nettoyage cache entre tests ──────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_enricher_caches():
    """Vide les caches LRU avant chaque test pour éviter la pollution entre tests."""
    _narrative_cache.clear()
    _takeaway_cache.clear()
    yield
    _narrative_cache.clear()
    _takeaway_cache.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — _compute_kpi_hero
# ═══════════════════════════════════════════════════════════════════════════════


def test_compute_kpi_hero_champs_corrects():
    """Test 01 — KPIHero rempli avec champs corrects depuis outcome.

    Sémantique L99 v2 (corrigée vs US-135 originale) :
        confidence_pct = outcome.confidence × 100 SI confidence > 0,
        sinon fallback sur bullish_pct.
    Ici outcome.confidence = 0.78 (explicite) → confidence_pct = 78.0.
    """
    ctx = _make_context(with_outcome=True)
    enricher = Enricher(ctx, llm_client=_make_mock_llm())
    enricher._compute_kpi_hero()

    hero = ctx.kpi_hero
    assert hero is not None
    assert isinstance(hero, KPIHero)
    assert hero.verdict == "Le marché demeure haussier malgré la pression réglementaire."
    # outcome.confidence = 0.78 est explicite et prime sur bullish_pct
    assert abs(hero.confidence_pct - 78.0) < 0.1
    assert 0.0 <= hero.brier <= 1.0
    assert "bullish" in hero.scenario_distribution
    assert "bearish" in hero.scenario_distribution
    assert abs(hero.scenario_distribution["bullish"] - 62.5) < 0.01
    assert abs(hero.scenario_distribution["bearish"] - 30.0) < 0.01


def test_compute_kpi_hero_outcome_none():
    """Test 02 — Verdict vide quand outcome est None."""
    ctx = _make_context(with_outcome=False)
    enricher = Enricher(ctx, llm_client=_make_mock_llm())
    enricher._compute_kpi_hero()

    hero = ctx.kpi_hero
    assert hero is not None
    assert hero.verdict == ""
    assert hero.confidence_pct == 0.0
    assert hero.brier == 0.0
    assert hero.scenario_distribution == {}


def test_compute_kpi_hero_brier_from_coherence():
    """Test 03 — Brier dérivé de quality_metrics.coherence (brier = 1 - coherence)."""
    ctx = _make_context(with_outcome=True)
    assert ctx.outcome is not None
    ctx.outcome.quality_metrics = QualityMetrics(coherence=0.75)

    enricher = Enricher(ctx, llm_client=_make_mock_llm())
    enricher._compute_kpi_hero()

    hero = ctx.kpi_hero
    assert hero is not None
    assert abs(hero.brier - 0.25) < 0.001


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — _detect_pivotal_moments
# ═══════════════════════════════════════════════════════════════════════════════


def test_detect_pivotal_moments_bascule_detectee():
    """Test 04 — Détecte une bascule artificielle > 0.20 entre round 0 et round 1.

    L99 v2 — Le libellé d'événement est désormais contextualisé selon l'ampleur
    et le signe de la bascule ("bascule forte ⟶ adhésion", "bascule positive",
    "bascule négative", "bascule forte ⟶ retrait") via _pivot_event_label.
    Ici delta=+0.40 → bascule forte vers adhésion.
    """
    ctx = _make_context()
    # Round 0 : Alice score 0.10 ; Round 1 : Alice score 0.50 (delta = +0.40 > seuil)
    ctx.trajectory = Trajectory(
        rounds=[
            Round(
                round_idx=0,
                agents=[AgentState(agent_id="ag1", name="Alice", score=0.10)],
            ),
            Round(
                round_idx=1,
                agents=[AgentState(agent_id="ag1", name="Alice", score=0.50)],
            ),
        ]
    )

    enricher = Enricher(ctx, llm_client=_make_mock_llm())
    enricher._detect_pivotal_moments()

    assert len(ctx.pivotal_moments) == 1
    pm = ctx.pivotal_moments[0]
    assert pm.round == 1
    assert pm.agent == "Alice"
    # L99 v2 : le label commence par "bascule" et peut être étoffé (positive/forte/⟶ adhésion)
    assert pm.event.startswith("bascule")
    assert abs(pm.delta_score - 0.40) < 0.001


def test_detect_pivotal_moments_pas_de_bascule_sous_seuil():
    """Test 05 — Aucun moment pivot si variation < 0.20."""
    ctx = _make_context()
    # Delta = 0.10 → sous le seuil
    ctx.trajectory = Trajectory(
        rounds=[
            Round(round_idx=0, agents=[AgentState(agent_id="ag1", name="Alice", score=0.10)]),
            Round(round_idx=1, agents=[AgentState(agent_id="ag1", name="Alice", score=0.20)]),
        ]
    )

    enricher = Enricher(ctx, llm_client=_make_mock_llm())
    enricher._detect_pivotal_moments()

    assert ctx.pivotal_moments == []


def test_detect_pivotal_moments_tris_par_round():
    """Test 06 — Moments pivots triés par round ascendant."""
    ctx = _make_context()
    # Alice bascule au round 1, Bob bascule au round 2
    ctx.trajectory = Trajectory(
        rounds=[
            Round(
                round_idx=0,
                agents=[
                    AgentState(agent_id="ag1", name="Alice", score=0.0),
                    AgentState(agent_id="ag2", name="Bob", score=0.0),
                ],
            ),
            Round(
                round_idx=1,
                agents=[
                    AgentState(agent_id="ag1", name="Alice", score=0.50),  # +0.50
                    AgentState(agent_id="ag2", name="Bob", score=0.05),     # +0.05 (sous seuil)
                ],
            ),
            Round(
                round_idx=2,
                agents=[
                    AgentState(agent_id="ag1", name="Alice", score=0.52),   # +0.02 (sous seuil)
                    AgentState(agent_id="ag2", name="Bob", score=-0.30),    # -0.35 (au-dessus)
                ],
            ),
        ]
    )

    enricher = Enricher(ctx, llm_client=_make_mock_llm())
    enricher._detect_pivotal_moments()

    assert len(ctx.pivotal_moments) == 2
    assert ctx.pivotal_moments[0].round == 1  # Alice
    assert ctx.pivotal_moments[1].round == 2  # Bob
    assert ctx.pivotal_moments[0].round <= ctx.pivotal_moments[1].round


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — _generate_chart_narratives
# ═══════════════════════════════════════════════════════════════════════════════


def test_generate_chart_narratives_cinq_entrees():
    """Test 07 — Toutes les entrées chart sont produites après _generate_chart_narratives.

    L99 v2 — Le pipeline a été étendu à 8 charts (5 historiques + 3 nouveaux outils
    de viz C-Level : influence_posture_matrix, stance_flow_sankey,
    agent_engagement_heatmap). Le test vérifie que TOUS les charts présents dans
    _CHART_IDS reçoivent une narrative, peu importe leur nombre exact.
    """
    from app.services.report_pdf.enricher import _CHART_IDS

    ctx = _make_context(with_outcome=True, with_trajectory=True)
    enricher = Enricher(ctx, llm_client=_make_mock_llm("Marché stable, haussiers en avance."))
    enricher._generate_chart_narratives()

    assert len(ctx.interpretations) == len(_CHART_IDS)
    assert set(ctx.interpretations.keys()) == set(_CHART_IDS)
    # Les 5 charts historiques doivent être présents (garde non-régression)
    historical_keys = {
        "belief_drift",
        "polymarket_curves",
        "demographic_pyramid",
        "influence_leaderboard",
        "interaction_network",
    }
    assert historical_keys.issubset(set(ctx.interpretations.keys()))
    for narrative in ctx.interpretations.values():
        assert isinstance(narrative, str)
        assert len(narrative) > 0


def test_generate_chart_narratives_cache_lru_un_seul_appel():
    """Test 08 — Cache LRU narrative : 2 appels successifs → 1 seul appel LLM par chart."""
    ctx = _make_context(with_outcome=True)
    mock_llm = _make_mock_llm("Insight stable.")
    enricher = Enricher(ctx, llm_client=mock_llm)

    # Premier appel
    enricher._generate_chart_narratives()
    first_call_count = mock_llm.chat.call_count

    # Deuxième appel avec le MÊME context (même data → même cache key)
    enricher._generate_chart_narratives()
    second_call_count = mock_llm.chat.call_count

    # Le cache doit avoir évité les appels LLM lors du second passage
    assert second_call_count == first_call_count, (
        f"Le cache n'a pas fonctionné : {first_call_count} appels au 1er passage, "
        f"{second_call_count} au 2ème (attendu : même nombre)"
    )


def test_fallback_llm_down_texte_generique():
    """Test 09 — Fallback LLM down : raise géré, texte fallback présent dans interpretations.

    L99 v2 — 8 charts au lieu de 5 (cf. _CHART_IDS).
    """
    from app.services.report_pdf.enricher import _CHART_IDS

    ctx = _make_context(with_outcome=True)

    mock_llm = MagicMock()
    mock_llm.chat.side_effect = Exception("Connection refused")

    enricher = Enricher(ctx, llm_client=mock_llm)
    enricher._generate_chart_narratives()

    # Pas de crash, toutes les entrées avec fallback
    assert len(ctx.interpretations) == len(_CHART_IDS)
    for narrative in ctx.interpretations.values():
        assert narrative == _LLM_FALLBACK


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — _extract_executive_takeaways
# ═══════════════════════════════════════════════════════════════════════════════


def test_extract_executive_takeaways_trois_takeaways():
    """Test 10 — 3 takeaways C-level après _extract_executive_takeaways."""
    ctx = _make_context(with_outcome=True)
    llm_response = (
        "1. Les haussiers consolident leur avance malgré la volatilité réglementaire.\n"
        "2. Le consensus reste fragile : un choc exogène pourrait inverser la tendance.\n"
        "3. La diversité des opinions protège la robustesse de la simulation."
    )
    enricher = Enricher(ctx, llm_client=_make_mock_llm(llm_response))
    enricher._extract_executive_takeaways()

    assert len(ctx.executive_takeaways) == 3
    for t in ctx.executive_takeaways:
        assert isinstance(t, str)
        assert len(t) > 10


def test_extract_executive_takeaways_cache_lru():
    """Test 11 — Cache LRU takeaways : 2 appels successifs → 1 seul appel LLM."""
    ctx = _make_context(with_outcome=True)
    llm_response = "1. Insight A.\n2. Insight B.\n3. Insight C."
    mock_llm = _make_mock_llm(llm_response)
    enricher = Enricher(ctx, llm_client=mock_llm)

    enricher._extract_executive_takeaways()
    first_count = mock_llm.chat.call_count

    enricher._extract_executive_takeaways()
    second_count = mock_llm.chat.call_count

    assert second_count == first_count, (
        "Le cache LRU takeaways doit éviter un second appel LLM."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — _pass_through_normalizer
# ═══════════════════════════════════════════════════════════════════════════════


def test_pass_through_normalizer_etat_accent():
    """Test 12 — Texte FR avec 'ETAT' (tout-caps) → 'ÉTAT' après _pass_through_normalizer.

    Le TextNormalizer FR applique la règle DEFCON-1 accents majuscules sur les mots
    entièrement en majuscules (regex [A-Z]{2,}). « ETAT » → « ÉTAT » est garanti
    par le dictionnaire ACCENT_DICT dans text_normalizer/fr.py.
    """
    ctx = _make_context(lang="fr", with_outcome=True)

    # Simule des textes non normalisés dans interpretations et takeaways.
    # On utilise ETAT (tout-caps) car c'est ce que le normalizer FR corrige.
    ctx.interpretations = {
        "belief_drift": "ETAT des marchés : tendance haussière confirmée.",
        "polymarket_curves": "Analyse stable.",
        "demographic_pyramid": "Distribution uniforme.",
        "influence_leaderboard": "Leaders identifiés.",
        "interaction_network": "Réseau dense.",
    }
    ctx.executive_takeaways = [
        "ETAT du système : robuste.",
        "Croissance continue.",
        "Risques maîtrisés.",
    ]

    enricher = Enricher(ctx, llm_client=_make_mock_llm())
    enricher._pass_through_normalizer()

    # "ETAT" (tout-caps sans accent) → "ÉTAT" via ACCENT_DICT du normalizer FR
    assert "ÉTAT" in ctx.interpretations["belief_drift"], (
        f"Attendu 'ÉTAT' dans '{ctx.interpretations['belief_drift']}'"
    )
    assert "ÉTAT" in ctx.executive_takeaways[0], (
        f"Attendu 'ÉTAT' dans '{ctx.executive_takeaways[0]}'"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — enrich() (pipeline complet)
# ═══════════════════════════════════════════════════════════════════════════════


def test_enrich_retourne_le_contexte():
    """Test 13 — enrich() retourne bien le contexte (chaînage)."""
    from app.services.report_pdf.enricher import _CHART_IDS

    ctx = _make_context(with_outcome=True, with_trajectory=True)
    llm_response = "1. Takeaway A.\n2. Takeaway B.\n3. Takeaway C."
    enricher = Enricher(ctx, llm_client=_make_mock_llm(llm_response))

    result = enricher.enrich()

    assert result is ctx
    assert result.kpi_hero is not None
    assert isinstance(result.pivotal_moments, list)
    assert len(result.interpretations) == len(_CHART_IDS)
    assert len(result.executive_takeaways) == 3
    # Aucune option n'est créée sans recommandation issue de la simulation.
    assert result.scored_recommendations == []
    assert result.strategic_options == []


def test_enrich_llm_none_pas_de_crash():
    """Test 14 — Fallback LLM=None (client non configuré) → texte générique, pas de crash.

    US-135 + L99 v2 : les chart narratives retournent _LLM_FALLBACK pour les
    8 charts. Les executive takeaways utilisent le fallback summary (outline.summary
    découpé en phrases) plutôt que 3× _LLM_FALLBACK — ce qui garantit un livrable
    client lisible même quand le LLM est indisponible. Les scored_recommendations
    sont déterministes (aucun LLM nécessaire).
    """
    from app.services.report_pdf.enricher import _CHART_IDS

    ctx = _make_context(with_outcome=True, with_trajectory=True)
    enricher = Enricher(ctx, llm_client=None)

    # Ne doit pas lever d'exception
    result = enricher.enrich()

    assert result.kpi_hero is not None
    assert len(result.interpretations) == len(_CHART_IDS)
    for narrative in result.interpretations.values():
        assert narrative == _LLM_FALLBACK
    # Takeaways : au moins 3 éléments (fallback summary ou _LLM_FALLBACK)
    assert len(result.executive_takeaways) == 3
    for t in result.executive_takeaways:
        assert isinstance(t, str)
        assert len(t) > 0
    assert result.scored_recommendations == []
    assert result.strategic_options == []
