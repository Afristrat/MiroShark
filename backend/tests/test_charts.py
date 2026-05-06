"""
Tests pytest pour US-122 — ChartFactory matplotlib palette Causse.

Couverture :
    01. Imports clean (matplotlib Agg backend, no display required)
    02. apply_causse_style() positionne les rcParams attendus
    03. belief_drift() retourne bytes PNG valides avec trajectoire remplie
    04. belief_drift() retourne placeholder quand trajectoire absente
    05. polymarket_curves() retourne bytes PNG valides
    06. polymarket_curves() retourne placeholder quand trajectoire absente
    07. demographic_pyramid() retourne bytes PNG (segments présents)
    08. demographic_pyramid() retourne placeholder quand Demographics absent
    09. demographic_pyramid() genre pyramid quand dimension 'genre'
    10. influence_leaderboard() retourne bytes PNG top-10
    11. influence_leaderboard() retourne placeholder quand trajectoire absente
    12. interaction_network() retourne bytes PNG avec réseau rempli
    13. interaction_network() retourne placeholder quand SocialNetwork absent
    14. Reproductibilité : deux appels successifs à belief_drift() → bytes identiques
    15. Reproductibilité : deux appels successifs à interaction_network() → bytes identiques
    16. Tous les PNG ont la magic bytes %PNG
    17. belief_drift() gère pivotal_moments (callouts sans crash)
    18. polymarket_curves() annote la valeur finale depuis outcome
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# ── Import du module sous test ────────────────────────────────────────────────
from app.services.report_pdf._style import (
    WI_CHARCOAL,
    WI_CREAM,
    WI_MINT,
    WI_ORANGE,
    WI_SAND,
    WI_TERRA,
    apply_causse_style,
)
from app.services.report_pdf.charts import ChartFactory, _placeholder_png
from app.services.report_pdf.schema import (
    AgentState,
    Demographics,
    DemographicSegment,
    Outcome,
    PDFReportContext,
    PivotalMoment,
    QualityMetrics,
    Round,
    SocialEdge,
    SocialNetwork,
    SocialNode,
    Trajectory,
)

# ─── IDs valides (format imposé par le schema) ────────────────────────────────
VALID_SIM_ID = "sim_aabbccddeeff"   # 12 hex chars
VALID_REPORT_ID = "report_aabbccddeeff"  # 12 hex chars


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _make_agents_round(round_idx: int, n_bull: int = 3, n_bear: int = 2) -> Round:
    """Fabrique un Round avec des agents bullish + bearish."""
    agents = []
    for i in range(n_bull):
        agents.append(
            AgentState(
                agent_id=f"bull-{round_idx}-{i}",
                name=f"BullAgent{i}",
                stance="bullish",
                score=0.6 + 0.05 * i + 0.01 * round_idx,
                message="Optimiste.",
                platform="twitter",
            )
        )
    for i in range(n_bear):
        agents.append(
            AgentState(
                agent_id=f"bear-{round_idx}-{i}",
                name=f"BearAgent{i}",
                stance="bearish",
                score=0.3 - 0.02 * i - 0.01 * round_idx,
                message="Pessimiste.",
                platform="reddit",
            )
        )
    return Round(round_idx=round_idx, agents=agents, summary=f"Round {round_idx} résumé")


def _make_trajectory(nb_rounds: int = 4) -> Trajectory:
    return Trajectory(rounds=[_make_agents_round(i) for i in range(nb_rounds)])


def _make_context_full() -> PDFReportContext:
    """Contexte complet avec tous les sous-modèles remplis."""
    return PDFReportContext(
        simulation_id=VALID_SIM_ID,
        report_id=VALID_REPORT_ID,
        title="Test rapport Bassira",
        trajectory=_make_trajectory(4),
        outcome=Outcome(
            verdict="Scénario haussier confirmé.",
            bullish_pct=62.0,
            bearish_pct=28.0,
            nb_rounds=4,
            confidence=0.78,
            quality_metrics=QualityMetrics(
                coherence=0.85, diversity=0.70, plausibility=0.80, alignment=0.75
            ),
            consensus_reached=False,
        ),
        pivotal_moments=[
            PivotalMoment(round=2, agent="BullAgent0", event="Annonce réglementaire", delta_score=0.12),
        ],
        demographics=Demographics(
            total=20,
            segments=[
                DemographicSegment(label="18-24 ans", count=4, pct=20.0, dimension="age"),
                DemographicSegment(label="25-34 ans", count=6, pct=30.0, dimension="age"),
                DemographicSegment(label="35-44 ans", count=5, pct=25.0, dimension="age"),
                DemographicSegment(label="45+ ans", count=5, pct=25.0, dimension="age"),
            ],
        ),
        social_network=SocialNetwork(
            nodes=[
                SocialNode(id="n1", name="BullAgent0", group="bullish", weight=2.0),
                SocialNode(id="n2", name="BullAgent1", group="bullish", weight=1.5),
                SocialNode(id="n3", name="BearAgent0", group="bearish", weight=1.8),
                SocialNode(id="n4", name="BearAgent1", group="bearish", weight=1.0),
            ],
            edges=[
                SocialEdge(source="n1", target="n3", weight=1.0, sentiment="negative"),
                SocialEdge(source="n2", target="n4", weight=0.5, sentiment="neutral"),
                SocialEdge(source="n1", target="n2", weight=1.5, sentiment="positive"),
            ],
        ),
    )


def _make_context_minimal() -> PDFReportContext:
    """Contexte minimal : seulement les IDs obligatoires."""
    return PDFReportContext(
        simulation_id=VALID_SIM_ID,
        report_id=VALID_REPORT_ID,
    )


def _make_context_genre() -> PDFReportContext:
    """Contexte avec segments de dimension 'genre' pour tester la pyramide."""
    return PDFReportContext(
        simulation_id=VALID_SIM_ID,
        report_id=VALID_REPORT_ID,
        demographics=Demographics(
            total=20,
            segments=[
                DemographicSegment(label="Femme", count=11, pct=55.0, dimension="genre"),
                DemographicSegment(label="Homme", count=9, pct=45.0, dimension="genre"),
            ],
        ),
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _is_png(data: bytes) -> bool:
    """Vérifie que les bytes commencent par la magic PNG."""
    return data[:8] == b"\x89PNG\r\n\x1a\n"


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestImportAndStyle:
    """Tests 01-02 : import propre et style rcParams."""

    def test_01_matplotlib_agg_backend(self):
        """matplotlib doit utiliser le backend Agg (non-interactif)."""
        import matplotlib
        assert matplotlib.get_backend().lower() == "agg"

    def test_02_causse_style_rcparams(self):
        """apply_causse_style() positionne les rcParams critiques."""
        import matplotlib.pyplot as plt

        apply_causse_style()
        assert plt.rcParams["figure.dpi"] == 300
        assert plt.rcParams["savefig.dpi"] == 300
        assert plt.rcParams["figure.facecolor"] == WI_CREAM
        assert plt.rcParams["axes.facecolor"] == WI_CREAM
        assert plt.rcParams["axes.spines.top"] is False
        assert plt.rcParams["axes.spines.right"] is False
        assert pytest.approx(plt.rcParams["grid.alpha"], abs=1e-3) == 0.4
        assert plt.rcParams["grid.color"] == WI_SAND


class TestPlaceholder:
    """Tests de base du placeholder PNG."""

    def test_placeholder_returns_valid_png(self):
        data = _placeholder_png("Test placeholder")
        assert _is_png(data)
        assert len(data) > 500  # non trivial

    def test_placeholder_custom_message(self):
        data = _placeholder_png("Données manquantes pour ce test")
        assert _is_png(data)


class TestBeliefDrift:
    """Tests 03-04 + 14 + 17 : belief_drift()."""

    def test_03_belief_drift_returns_png_with_trajectory(self):
        """Avec trajectoire, retourne un PNG valide."""
        ctx = _make_context_full()
        factory = ChartFactory(ctx)
        data = factory.belief_drift()
        assert _is_png(data)
        assert len(data) > 1000

    def test_04_belief_drift_placeholder_when_no_trajectory(self):
        """Sans trajectoire, retourne un placeholder PNG valide."""
        ctx = _make_context_minimal()
        factory = ChartFactory(ctx)
        data = factory.belief_drift()
        assert _is_png(data)

    def test_14_belief_drift_reproducible(self):
        """Deux appels successifs produisent des bytes identiques (reproducibilité)."""
        ctx = _make_context_full()
        f1 = ChartFactory(ctx)
        f2 = ChartFactory(ctx)
        data1 = f1.belief_drift()
        data2 = f2.belief_drift()
        assert data1 == data2

    def test_17_belief_drift_with_pivotal_moments(self):
        """belief_drift() gère les pivotal_moments sans crash."""
        ctx = PDFReportContext(
            simulation_id=VALID_SIM_ID,
            report_id=VALID_REPORT_ID,
            trajectory=_make_trajectory(5),
            pivotal_moments=[
                PivotalMoment(round=1, agent="Ag0", event="Event A", delta_score=0.1),
                PivotalMoment(round=3, agent="Ag1", event="Event B", delta_score=-0.05),
            ],
        )
        factory = ChartFactory(ctx)
        data = factory.belief_drift()
        assert _is_png(data)


class TestPolymarketCurves:
    """Tests 05-06 + 18 : polymarket_curves()."""

    def test_05_polymarket_curves_returns_png(self):
        """Avec trajectoire, retourne un PNG valide."""
        ctx = _make_context_full()
        factory = ChartFactory(ctx)
        data = factory.polymarket_curves()
        assert _is_png(data)
        assert len(data) > 1000

    def test_06_polymarket_curves_placeholder_no_trajectory(self):
        """Sans trajectoire, placeholder PNG valide."""
        ctx = _make_context_minimal()
        factory = ChartFactory(ctx)
        data = factory.polymarket_curves()
        assert _is_png(data)

    def test_18_polymarket_curves_with_outcome_annotation(self):
        """Avec outcome (bullish_pct/bearish_pct), génère le chart sans crash."""
        ctx = _make_context_full()
        assert ctx.outcome is not None
        factory = ChartFactory(ctx)
        data = factory.polymarket_curves()
        assert _is_png(data)


class TestDemographicPyramid:
    """Tests 07-09 : demographic_pyramid()."""

    def test_07_demographic_pyramid_returns_png_with_segments(self):
        """Avec segments, retourne un PNG valide."""
        ctx = _make_context_full()
        factory = ChartFactory(ctx)
        data = factory.demographic_pyramid()
        assert _is_png(data)
        assert len(data) > 500

    def test_08_demographic_pyramid_placeholder_no_demographics(self):
        """Sans données démographiques, placeholder PNG."""
        ctx = _make_context_minimal()
        factory = ChartFactory(ctx)
        data = factory.demographic_pyramid()
        assert _is_png(data)

    def test_09_demographic_pyramid_genre(self):
        """Avec dimension 'genre', génère la pyramide horizontale."""
        ctx = _make_context_genre()
        factory = ChartFactory(ctx)
        data = factory.demographic_pyramid()
        assert _is_png(data)


class TestInfluenceLeaderboard:
    """Tests 10-11 : influence_leaderboard()."""

    def test_10_influence_leaderboard_returns_png(self):
        """Avec trajectoire, retourne un PNG valide."""
        ctx = _make_context_full()
        factory = ChartFactory(ctx)
        data = factory.influence_leaderboard()
        assert _is_png(data)
        assert len(data) > 500

    def test_11_influence_leaderboard_placeholder_no_trajectory(self):
        """Sans trajectoire, placeholder PNG."""
        ctx = _make_context_minimal()
        factory = ChartFactory(ctx)
        data = factory.influence_leaderboard()
        assert _is_png(data)

    def test_influence_leaderboard_top10_limit(self):
        """Avec plus de 10 agents, seuls les 10 meilleurs sont tracés sans crash."""
        # 15 agents distincts, score croissant
        rounds = []
        agents = [
            AgentState(
                agent_id=f"a{i}",
                name=f"Agent{i:02d}",
                stance="bullish" if i % 2 == 0 else "bearish",
                score=float(i) / 10.0,
                message="",
                platform="twitter",
            )
            for i in range(15)
        ]
        rounds.append(Round(round_idx=0, agents=agents))
        ctx = PDFReportContext(
            simulation_id=VALID_SIM_ID,
            report_id=VALID_REPORT_ID,
            trajectory=Trajectory(rounds=rounds),
        )
        factory = ChartFactory(ctx)
        data = factory.influence_leaderboard()
        assert _is_png(data)


class TestInteractionNetwork:
    """Tests 12-13 + 15 : interaction_network()."""

    def test_12_interaction_network_returns_png(self):
        """Avec réseau social, retourne un PNG valide."""
        ctx = _make_context_full()
        factory = ChartFactory(ctx)
        data = factory.interaction_network()
        assert _is_png(data)
        assert len(data) > 1000

    def test_13_interaction_network_placeholder_no_network(self):
        """Sans réseau social, placeholder PNG."""
        ctx = _make_context_minimal()
        factory = ChartFactory(ctx)
        data = factory.interaction_network()
        assert _is_png(data)

    def test_15_interaction_network_reproducible(self):
        """Seed=42 → bytes identiques sur deux appels successifs."""
        ctx = _make_context_full()
        f1 = ChartFactory(ctx)
        f2 = ChartFactory(ctx)
        data1 = f1.interaction_network()
        data2 = f2.interaction_network()
        assert data1 == data2

    def test_interaction_network_isolated_nodes(self):
        """Réseau avec nœuds sans arêtes ne crash pas."""
        ctx = PDFReportContext(
            simulation_id=VALID_SIM_ID,
            report_id=VALID_REPORT_ID,
            social_network=SocialNetwork(
                nodes=[
                    SocialNode(id="x1", name="Solo1", group="g1", weight=1.0),
                    SocialNode(id="x2", name="Solo2", group="g2", weight=0.5),
                ],
                edges=[],
            ),
        )
        factory = ChartFactory(ctx)
        data = factory.interaction_network()
        assert _is_png(data)


class TestAllChartsPNGMagic:
    """Test 16 : toutes les méthodes retournent des PNG valides."""

    def test_16_all_charts_have_png_magic_bytes(self):
        """Chaque chart produit un PNG valide (magic bytes \\x89PNG...)."""
        ctx = _make_context_full()
        factory = ChartFactory(ctx)
        for method_name in ("belief_drift", "polymarket_curves", "demographic_pyramid",
                            "influence_leaderboard", "interaction_network"):
            method = getattr(factory, method_name)
            data = method()
            assert _is_png(data), f"{method_name}() ne retourne pas un PNG valide"
            assert len(data) > 100, f"{method_name}() retourne des données trop courtes"
