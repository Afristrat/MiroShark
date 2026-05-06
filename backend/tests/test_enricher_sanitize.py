"""
Tests pytest pour US-135 — Enricher fixes : sanitize LLM tool_call + KPI Hero réel.

Couverture (≥ 10 tests) :

Sanitize :
    01. sanitize_llm_output : supprime <tool_call>...</tool_call> simple
    02. sanitize_llm_output : supprime <tool_call> multiline
    03. sanitize_llm_output : supprime <function_call>...</function_call>
    04. sanitize_llm_output : supprime <thinking>...</thinking>
    05. sanitize_llm_output : supprime <scratchpad>...</scratchpad>
    06. sanitize_llm_output : supprime versions échappées \\<tool_call\\>
    07. sanitize_llm_output : supprime [function_calls]...[/function_calls]
    08. sanitize_llm_output : texte sans balises inchangé
    09. sanitize_llm_output : texte vide/None retourné tel quel

KPI Hero (US-135) :
    10. confidence_pct depuis bullish_pct (pas outcome.confidence)
    11. confidence_pct depuis bearish_pct en fallback si bullish=0
    12. brier depuis 1-coherence (proxy QualityMetrics)
    13. confidence_pct=0.0 si bullish=0 et bearish=0

Pivotal moments :
    14. bascule > 0.20 détectée
    15. pas de bascule si delta < 0.20 (fixture flat)

Takeaways :
    16. outline.takeaways existant → utilisé directement sans LLM
    17. outline.executive_summary existant → utilisé directement sans LLM
    18. fallback summary → 3 phrases depuis outline.summary quand LLM=None

Sanitize appliqué en bout de pipeline :
    19. <tool_call> dans sortie LLM chart → supprimé avant injection dans interpretations
    20. <tool_call> dans sortie LLM takeaway → supprimé avant injection
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List
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
    sanitize_llm_output,
)
from app.services.report_pdf.schema import (
    AgentState,
    KPIHero,
    Outcome,
    Outline,
    PDFReportContext,
    PivotalMoment,
    QualityMetrics,
    Round,
    Trajectory,
)

# ─── IDs valides (format regex schema.py) ─────────────────────────────────────
VALID_REPORT_ID = "report_aabbcc112233"
VALID_SIM_ID = "sim_112233aabbcc"


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_enricher_caches():
    """Vide les caches LRU avant chaque test."""
    _narrative_cache.clear()
    _takeaway_cache.clear()
    yield
    _narrative_cache.clear()
    _takeaway_cache.clear()


def _make_context(
    *,
    lang: str = "fr",
    bullish_pct: float = 65.7,
    bearish_pct: float = 20.0,
    confidence: float = 0.0,
    coherence: float = 0.82,
    with_outcome: bool = True,
    with_outline: bool = True,
    summary: str = "La simulation révèle une tendance haussière. Les agents convergent. La polarisation diminue.",
) -> PDFReportContext:
    """Construit un PDFReportContext minimal valide pour les tests US-135."""
    ctx = PDFReportContext(
        report_id=VALID_REPORT_ID,
        simulation_id=VALID_SIM_ID,
        lang=lang,  # type: ignore[arg-type]
    )

    if with_outcome:
        ctx.outcome = Outcome(
            verdict="Tendance haussière confirmée malgré la pression réglementaire.",
            bullish_pct=bullish_pct,
            bearish_pct=bearish_pct,
            nb_rounds=5,
            confidence=confidence,
            quality_metrics=QualityMetrics(
                coherence=coherence,
                diversity=0.70,
                plausibility=0.80,
                alignment=0.75,
            ),
        )

    if with_outline:
        ctx.outline = Outline(
            title="Rapport de simulation",
            summary=summary,
        )

    return ctx


def _make_mock_llm(response: str = "Analyse stable.") -> MagicMock:
    """Crée un LLM mock qui retourne toujours la même réponse."""
    mock = MagicMock()
    mock.chat.return_value = response
    return mock


def _make_trajectory_with_bascule(delta: float = 0.40, n_rounds: int = 2) -> Trajectory:
    """Construit une trajectoire avec une bascule de score ``delta`` au round 1."""
    return Trajectory(
        rounds=[
            Round(
                round_idx=0,
                agents=[AgentState(agent_id="ag1", name="Alice", score=0.10)],
            ),
            Round(
                round_idx=1,
                agents=[AgentState(agent_id="ag1", name="Alice", score=0.10 + delta)],
            ),
        ]
    )


def _make_trajectory_flat() -> Trajectory:
    """Construit une trajectoire sans bascule significative (delta=0.05 < seuil 0.20)."""
    return Trajectory(
        rounds=[
            Round(round_idx=0, agents=[AgentState(agent_id="ag1", name="Alice", score=0.50)]),
            Round(round_idx=1, agents=[AgentState(agent_id="ag1", name="Alice", score=0.55)]),
            Round(round_idx=2, agents=[AgentState(agent_id="ag1", name="Alice", score=0.52)]),
        ]
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Tests 01–09 — sanitize_llm_output
# ═══════════════════════════════════════════════════════════════════════════════


def test_sanitize_supprime_tool_call_simple():
    """Test 01 — <tool_call>...</tool_call> supprimé, texte avant/après conservé."""
    raw = "Avant <tool_call>insight_forge</tool_call> Après"
    result = sanitize_llm_output(raw)
    assert "<tool_call>" not in result
    assert "insight_forge" not in result
    assert "Avant" in result
    assert "Après" in result
    # Vérifie que le strip fonctionne bien
    assert result == "Avant  Après".strip() or result.startswith("Avant")


def test_sanitize_supprime_tool_call_multiline():
    """Test 02 — <tool_call> multiline supprimé intégralement."""
    raw = (
        "Analyse : Le marché est haussier.\n"
        "<tool_call>\n"
        '{"name": "insight_forge", "arguments": {"query": "bullish trend"}}\n'
        "</tool_call>\n"
        "Conclusion : stabilité confirmée."
    )
    result = sanitize_llm_output(raw)
    assert "<tool_call>" not in result
    assert "insight_forge" not in result
    assert "Analyse" in result
    assert "Conclusion" in result


def test_sanitize_supprime_function_call():
    """Test 03 — <function_call>...</function_call> supprimé."""
    raw = "Résultat : <function_call>search_web</function_call> ok."
    result = sanitize_llm_output(raw)
    assert "<function_call>" not in result
    assert "search_web" not in result
    assert "Résultat" in result
    assert "ok" in result


def test_sanitize_supprime_thinking():
    """Test 04 — <thinking>...</thinking> supprimé."""
    raw = "<thinking>Je dois analyser ce graphe en détail...</thinking>Voici mon analyse."
    result = sanitize_llm_output(raw)
    assert "<thinking>" not in result
    assert "Je dois analyser" not in result
    assert "Voici mon analyse" in result


def test_sanitize_supprime_scratchpad():
    """Test 05 — <scratchpad>...</scratchpad> supprimé."""
    raw = "Texte utile.<scratchpad>notes internes</scratchpad>Suite."
    result = sanitize_llm_output(raw)
    assert "<scratchpad>" not in result
    assert "notes internes" not in result
    assert "Texte utile" in result
    assert "Suite" in result


def test_sanitize_supprime_versions_echappees():
    """Test 06 — Versions échappées \\<tool_call\\>...\\</tool_call\\> supprimées."""
    raw = r"Analyse \<tool_call\>foo\</tool_call\> fin."
    result = sanitize_llm_output(raw)
    assert r"\<tool_call\>" not in result
    assert "foo" not in result
    assert "Analyse" in result
    assert "fin" in result


def test_sanitize_supprime_function_calls_brackets():
    """Test 07 — [function_calls]...[/function_calls] supprimé."""
    raw = "Début [function_calls]appel interne[/function_calls] Fin."
    result = sanitize_llm_output(raw)
    assert "[function_calls]" not in result
    assert "appel interne" not in result
    assert "Début" in result
    assert "Fin" in result


def test_sanitize_texte_sans_balise_inchange():
    """Test 08 — Texte sans balise retourné intact (strip seulement)."""
    raw = "Le marché est haussier avec 65 % de confiance. La volatilité reste modérée."
    result = sanitize_llm_output(raw)
    assert result == raw.strip()


def test_sanitize_texte_vide_retourne_tel_quel():
    """Test 09 — Texte vide ou None retourné tel quel sans erreur."""
    assert sanitize_llm_output("") == ""
    assert sanitize_llm_output(None) is None  # type: ignore[arg-type]


# ═══════════════════════════════════════════════════════════════════════════════
# Tests 10–13 — KPI Hero (US-135 : confidence depuis bullish_pct)
# ═══════════════════════════════════════════════════════════════════════════════


def test_kpi_hero_confidence_depuis_bullish_pct():
    """Test 10 — confidence_pct = bullish_pct (65.7), pas outcome.confidence (0.0)."""
    ctx = _make_context(bullish_pct=65.7, confidence=0.0)
    enricher = Enricher(ctx, llm_client=_make_mock_llm())
    enricher._compute_kpi_hero()

    hero = ctx.kpi_hero
    assert hero is not None
    assert abs(hero.confidence_pct - 65.7) < 0.01, (
        f"confidence_pct attendu 65.7, obtenu {hero.confidence_pct}"
    )


def test_kpi_hero_confidence_fallback_bearish():
    """Test 11 — confidence_pct = 100 - bearish_pct si bullish_pct=0."""
    ctx = _make_context(bullish_pct=0.0, bearish_pct=30.0, confidence=0.0)
    enricher = Enricher(ctx, llm_client=_make_mock_llm())
    enricher._compute_kpi_hero()

    hero = ctx.kpi_hero
    assert hero is not None
    assert abs(hero.confidence_pct - 70.0) < 0.01, (
        f"confidence_pct attendu 70.0 (100-30), obtenu {hero.confidence_pct}"
    )


def test_kpi_hero_brier_depuis_coherence():
    """Test 12 — brier = 1 - coherence quand brier_score absent de QualityMetrics."""
    ctx = _make_context(bullish_pct=65.7, coherence=0.82)
    enricher = Enricher(ctx, llm_client=_make_mock_llm())
    enricher._compute_kpi_hero()

    hero = ctx.kpi_hero
    assert hero is not None
    expected_brier = round(1.0 - 0.82, 4)
    assert abs(hero.brier - expected_brier) < 0.001, (
        f"brier attendu {expected_brier}, obtenu {hero.brier}"
    )


def test_kpi_hero_confidence_zero_si_bullish_et_bearish_nuls():
    """Test 13 — confidence_pct=0.0 si bullish=0 et bearish=0."""
    ctx = _make_context(bullish_pct=0.0, bearish_pct=0.0, confidence=0.0)
    enricher = Enricher(ctx, llm_client=_make_mock_llm())
    enricher._compute_kpi_hero()

    hero = ctx.kpi_hero
    assert hero is not None
    assert hero.confidence_pct == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Tests 14–15 — Pivotal moments
# ═══════════════════════════════════════════════════════════════════════════════


def test_pivotal_moments_bascule_detectee():
    """Test 14 — bascule > 0.20 détectée sur fixture trajectory."""
    ctx = _make_context()
    ctx.trajectory = _make_trajectory_with_bascule(delta=0.40)

    enricher = Enricher(ctx, llm_client=_make_mock_llm())
    enricher._detect_pivotal_moments()

    assert len(ctx.pivotal_moments) >= 1
    pm = ctx.pivotal_moments[0]
    assert pm.round == 1
    assert pm.agent == "Alice"
    assert abs(pm.delta_score - 0.40) < 0.01


def test_pivotal_moments_flat_liste_vide():
    """Test 15 — aucun moment pivot si delta < 0.20 (fixture flat)."""
    ctx = _make_context()
    ctx.trajectory = _make_trajectory_flat()

    enricher = Enricher(ctx, llm_client=_make_mock_llm())
    enricher._detect_pivotal_moments()

    assert ctx.pivotal_moments == [], (
        f"Aucun pivot attendu, obtenu : {ctx.pivotal_moments}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Tests 16–18 — Executive takeaways
# ═══════════════════════════════════════════════════════════════════════════════


def test_takeaways_depuis_outline_takeaways():
    """Test 16 — outline.takeaways List[str] → utilisé directement sans appel LLM."""
    ctx = _make_context()
    # Injecte une liste takeaways dans l'outline (monkey-patch, schéma intouchable)
    outline = ctx.outline
    object.__setattr__(outline, "takeaways", ["Takeaway A.", "Takeaway B.", "Takeaway C."])

    mock_llm = _make_mock_llm("LLM ne doit pas être appelé.")
    enricher = Enricher(ctx, llm_client=mock_llm)
    enricher._extract_executive_takeaways()

    assert ctx.executive_takeaways == ["Takeaway A.", "Takeaway B.", "Takeaway C."]
    mock_llm.chat.assert_not_called()


def test_takeaways_depuis_outline_executive_summary():
    """Test 17 — outline.executive_summary List[str] → utilisé si takeaways absent."""
    ctx = _make_context()
    outline = ctx.outline
    # Pas de 'takeaways', mais 'executive_summary' présent
    object.__setattr__(
        outline,
        "executive_summary",
        ["Insight A.", "Insight B.", "Insight C."],
    )

    mock_llm = _make_mock_llm("LLM ne doit pas être appelé.")
    enricher = Enricher(ctx, llm_client=mock_llm)
    enricher._extract_executive_takeaways()

    assert ctx.executive_takeaways == ["Insight A.", "Insight B.", "Insight C."]
    mock_llm.chat.assert_not_called()


def test_takeaways_fallback_summary_quand_llm_none():
    """Test 18 — fallback : outline.summary découpé en phrases quand LLM=None."""
    ctx = _make_context(
        summary="La simulation révèle une tendance haussière. Les agents convergent. La polarisation diminue.",
    )

    enricher = Enricher(ctx, llm_client=None)
    enricher._extract_executive_takeaways()

    # Doit produire exactement 3 takeaways non vides
    assert len(ctx.executive_takeaways) == 3
    for t in ctx.executive_takeaways:
        assert isinstance(t, str)
        assert len(t) > 0

    # Le premier takeaway doit provenir du summary (pas _LLM_FALLBACK)
    assert ctx.executive_takeaways[0] != _LLM_FALLBACK
    assert "tendance" in ctx.executive_takeaways[0].lower() or len(ctx.executive_takeaways[0]) > 5


# ═══════════════════════════════════════════════════════════════════════════════
# Tests 19–20 — Sanitize appliqué en bout de pipeline
# ═══════════════════════════════════════════════════════════════════════════════


def test_sanitize_applique_sur_chart_narrative():
    """Test 19 — <tool_call> dans sortie LLM chart → supprimé avant injection dans interpretations."""
    ctx = _make_context(with_outcome=True)
    # Le LLM retourne une narrative avec une balise tool_call parasite
    llm_response = "Le marché est haussier.<tool_call>insight_forge</tool_call> Volatilité modérée."
    mock_llm = _make_mock_llm(llm_response)

    enricher = Enricher(ctx, llm_client=mock_llm)
    enricher._generate_chart_narratives()

    for chart_id, narrative in ctx.interpretations.items():
        assert "<tool_call>" not in narrative, (
            f"Chart {chart_id!r} contient encore <tool_call> : {narrative!r}"
        )
        assert "insight_forge" not in narrative, (
            f"Chart {chart_id!r} contient encore 'insight_forge' : {narrative!r}"
        )


def test_sanitize_applique_sur_takeaway():
    """Test 20 — <tool_call> dans sortie LLM takeaway → supprimé avant injection."""
    ctx = _make_context(with_outcome=True)
    # Le LLM retourne des takeaways avec des balises parasites
    llm_response = (
        "1. <tool_call>foo</tool_call>La tendance haussière persiste.\n"
        "2. Le consensus reste fragile.\n"
        "3. La diversité protège la robustesse."
    )
    mock_llm = _make_mock_llm(llm_response)

    enricher = Enricher(ctx, llm_client=mock_llm)
    enricher._extract_executive_takeaways()

    for takeaway in ctx.executive_takeaways:
        assert "<tool_call>" not in takeaway, (
            f"Takeaway contient encore <tool_call> : {takeaway!r}"
        )
        assert "foo" not in takeaway, (
            f"Takeaway contient encore le contenu de la balise : {takeaway!r}"
        )
