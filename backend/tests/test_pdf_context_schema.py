"""
Tests pytest exhaustifs pour PDFReportContext et ses sub-models.

US-118 — Schema PDFReportContext exhaustif (Pydantic v2).

Couverture :
    1. Construction valid depuis dict réaliste (minimal, complet, optionnels None)
    2. Construction invalid raise ValidationError (lang, framework, IDs mal formés)
    3. Roundtrip JSON (model_dump_json → model_validate_json)
    4. Default values respectés sur tous les champs optionnels
    5. Sub-models isolés (SimConfig, Outcome, QualityMetrics, Trajectory, …)
    6. Validators ciblés (report_id regex, simulation_id regex, lang, framework)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services.report_pdf.schema import (
    AgentInterview,
    AgentProfile,
    AgentState,
    Counterfactual,
    Demographics,
    DemographicSegment,
    DirectorEvent,
    GeneratedArticle,
    KPIHero,
    Outline,
    Outcome,
    PDFReportContext,
    PivotalMoment,
    QualityMetrics,
    Round,
    Section,
    SimConfig,
    SimState,
    SocialEdge,
    SocialNetwork,
    SocialNode,
    Trajectory,
)


# ─── Fixtures dict réalistes ─────────────────────────────────────────────────

VALID_REPORT_ID = "report_a1b2c3d4e5f6"
VALID_SIM_ID = "sim_aabbcc112233"


def _minimal_context() -> dict:
    """Contexte minimal : seuls les champs obligatoires renseignés."""
    return {
        "report_id": VALID_REPORT_ID,
        "simulation_id": VALID_SIM_ID,
    }


def _full_context() -> dict:
    """Contexte complet avec tous les sub-models renseignés."""
    return {
        "report_id": VALID_REPORT_ID,
        "simulation_id": VALID_SIM_ID,
        "title": "Analyse de l'impact de la réforme fiscale sur l'investissement MENA",
        "framework": "policy",
        "package": "budget-loi-finances",
        "lang": "fr",
        "sim_config": {
            "title": "Réforme fiscale Maroc 2027",
            "package": "budget-loi-finances",
            "framework": "policy",
            "lang": "fr",
            "sources": ["Projet de loi de finances 2027", "Note BAM Q3-2026"],
            "params": {"rounds": 10, "agents_count": 15},
        },
        "sim_state": {
            "status": "completed",
            "current_round": 10,
            "profiles_count": 15,
            "entities_count": 87,
            "entity_types": ["Person", "Organisation", "Concept"],
        },
        "outcome": {
            "verdict": "Consensus progressif autour d'une adoption partielle de la réforme",
            "bullish_pct": 62.5,
            "bearish_pct": 25.0,
            "nb_rounds": 10,
            "recommendations": [
                "Accompagner la réforme d'un plan de communication ciblé PME",
                "Prévoir une phase pilote 6 mois avant généralisation",
            ],
            "confidence": 0.74,
            "quality_metrics": {
                "coherence": 0.82,
                "diversity": 0.71,
                "plausibility": 0.79,
                "alignment": 0.85,
            },
            "scenario_winner": "Progressive",
            "consensus_reached": True,
        },
        "quality_metrics": {
            "coherence": 0.82,
            "diversity": 0.71,
            "plausibility": 0.79,
            "alignment": 0.85,
        },
        "trajectory": {
            "rounds": [
                {
                    "round_idx": 0,
                    "summary": "Réaction initiale polarisée",
                    "agents": [
                        {
                            "agent_id": "agent_001",
                            "name": "Karim Benali",
                            "stance": "bullish",
                            "score": 0.65,
                            "message": "La réforme favorisera l'investissement à long terme.",
                            "platform": "twitter",
                        },
                        {
                            "agent_id": "agent_002",
                            "name": "Nadia Oukili",
                            "stance": "bearish",
                            "score": 0.30,
                            "message": "L'impact à court terme sur les PME sera brutal.",
                            "platform": "reddit",
                        },
                    ],
                },
                {
                    "round_idx": 1,
                    "summary": "Convergence progressive",
                    "agents": [
                        {
                            "agent_id": "agent_001",
                            "name": "Karim Benali",
                            "stance": "bullish",
                            "score": 0.70,
                            "message": "Les chiffres confirment l'effet positif sur l'IDE.",
                            "platform": "twitter",
                        }
                    ],
                },
            ]
        },
        "agent_profiles": [
            {
                "name": "Karim Benali",
                "archetype": "Progressive",
                "biais": ["confirmation_bias", "optimism_bias"],
                "stance": "bullish",
                "platform": "twitter",
                "description": "Économiste bullish sur les réformes structurelles.",
            },
            {
                "name": "Nadia Oukili",
                "archetype": "Conservative",
                "biais": ["loss_aversion"],
                "stance": "bearish",
                "platform": "reddit",
                "description": "Représentante syndicale, prudente sur l'impact social.",
            },
        ],
        "social_network": {
            "nodes": [
                {"id": "agent_001", "name": "Karim Benali", "group": "Progressive", "weight": 1.5},
                {"id": "agent_002", "name": "Nadia Oukili", "group": "Conservative", "weight": 1.2},
            ],
            "edges": [
                {
                    "source": "agent_001",
                    "target": "agent_002",
                    "weight": 0.8,
                    "sentiment": "negative",
                }
            ],
        },
        "demographics": {
            "total": 15,
            "segments": [
                {"label": "Hommes", "count": 9, "pct": 60.0, "dimension": "genre"},
                {"label": "Femmes", "count": 6, "pct": 40.0, "dimension": "genre"},
                {"label": "25-34 ans", "count": 5, "pct": 33.3, "dimension": "age"},
                {"label": "Casablanca", "count": 7, "pct": 46.7, "dimension": "geo"},
            ],
        },
        "counterfactuals": [
            {
                "hypothesis": "Et si le taux d'IS baissait de 5 pts de plus ?",
                "round_injected": 5,
                "delta_verdict": "Adoption totale au lieu de partielle",
                "delta_confidence": 0.12,
                "notes": "L'effet d'entraînement sur l'investissement privé serait significatif.",
            }
        ],
        "director_events": [
            {
                "round": 3,
                "event_type": "news",
                "description": "Publication du rapport FMI favorable à la réforme",
                "impact": "Renforcement de la position bullish",
            }
        ],
        "articles": [
            {
                "agent_name": "Karim Benali",
                "platform": "twitter",
                "round": 2,
                "title": "La réforme fiscale, un levier pour l'IDE",
                "content": "Après analyse des projections, la réforme devrait attirer 2 Mds USD.",
                "stance": "bullish",
            }
        ],
        "interviews": [
            {
                "agent_name": "Nadia Oukili",
                "archetype": "Conservative",
                "questions": ["Quelle est votre position finale ?", "Avez-vous changé d'avis ?"],
                "answers": [
                    "Ma position reste prudente, mais j'admets un impact positif à long terme.",
                    "Partiellement. Les garanties PME annoncées m'ont convaincue.",
                ],
                "final_stance": "neutral",
            }
        ],
        "outline": {
            "title": "Rapport d'analyse — Réforme fiscale Maroc 2027",
            "summary": "Cette simulation multi-agents révèle une convergence vers l'adoption de la réforme.",
            "sections": [
                {"idx": 0, "title": "Contexte et objectifs", "content": "## Contexte\n\nLa réforme..."},
                {"idx": 1, "title": "Dynamiques observées", "content": "## Dynamiques\n\nRound 1..."},
                {"idx": 2, "title": "Recommandations", "content": "## Recommandations\n\n1. ..."},
            ],
        },
        "full_report_md": "# Rapport complet\n\n## Contexte\n\nTexte...",
        "sections_md": {0: "## Contexte\n\nTexte section 0.", 1: "## Dynamiques\n\nTexte section 1."},
        "agent_log": [
            {
                "timestamp": "2026-05-05T10:00:00",
                "action": "report_start",
                "stage": "pending",
                "details": {"message": "Démarrage"},
            }
        ],
        "kpi_hero": {
            "verdict": "Adoption progressive",
            "confidence_pct": 74.0,
            "brier": 0.18,
            "scenario_distribution": {"Progressive": 0.625, "Conservative": 0.25, "Technocrat": 0.125},
        },
        "pivotal_moments": [
            {
                "round": 3,
                "agent": "Karim Benali",
                "event": "Rapport FMI favorable publié",
                "delta_score": 0.15,
            }
        ],
        "interpretations": {
            "consensus": "Convergence vers l'adoption partielle dès le round 7.",
            "polarisation": "Clivage initial forte entre Pro et Anti-réforme.",
        },
        "executive_takeaways": [
            "La réforme obtient un consensus au round 7 sur 10.",
            "L'agent déclencheur principal est la publication du rapport FMI.",
            "Un accompagnement PME est indispensable pour réduire la résistance.",
        ],
    }


def _optional_none_context() -> dict:
    """Contexte avec tous les champs optionnels explicitement à None."""
    return {
        "report_id": VALID_REPORT_ID,
        "simulation_id": VALID_SIM_ID,
        "title": "Test champs optionnels",
        "framework": "market",
        "lang": "en",
        "sim_config": None,
        "sim_state": None,
        "outcome": None,
        "quality_metrics": None,
        "trajectory": None,
        "social_network": None,
        "demographics": None,
        "outline": None,
        "full_report_md": None,
        "kpi_hero": None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Construction valid — 3 cas
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidConstruction:
    def test_minimal_context_valid(self):
        """Construction minimale : seuls report_id et simulation_id requis."""
        ctx = PDFReportContext(**_minimal_context())
        assert ctx.report_id == VALID_REPORT_ID
        assert ctx.simulation_id == VALID_SIM_ID
        # Vérification defaults
        assert ctx.title == ""
        assert ctx.framework == "cerberus"
        assert ctx.lang == "fr"
        assert ctx.package == ""
        assert ctx.sim_config is None
        assert ctx.sim_state is None
        assert ctx.outcome is None
        assert ctx.trajectory is None
        assert ctx.agent_profiles == []
        assert ctx.counterfactuals == []
        assert ctx.director_events == []
        assert ctx.articles == []
        assert ctx.interviews == []
        assert ctx.sections_md == {}
        assert ctx.agent_log == []
        assert ctx.pivotal_moments == []
        assert ctx.interpretations == {}
        assert ctx.executive_takeaways == []

    def test_full_context_valid(self):
        """Construction complète avec tous les sub-models renseignés."""
        ctx = PDFReportContext(**_full_context())
        assert ctx.report_id == VALID_REPORT_ID
        assert ctx.simulation_id == VALID_SIM_ID
        assert ctx.framework == "policy"
        assert ctx.lang == "fr"
        assert ctx.package == "budget-loi-finances"

        # sim_config
        assert ctx.sim_config is not None
        assert ctx.sim_config.title == "Réforme fiscale Maroc 2027"
        assert ctx.sim_config.framework == "policy"
        assert len(ctx.sim_config.sources) == 2

        # sim_state
        assert ctx.sim_state is not None
        assert ctx.sim_state.status == "completed"
        assert ctx.sim_state.current_round == 10
        assert ctx.sim_state.profiles_count == 15

        # outcome
        assert ctx.outcome is not None
        assert ctx.outcome.bullish_pct == 62.5
        assert ctx.outcome.consensus_reached is True
        assert ctx.outcome.quality_metrics.coherence == 0.82

        # trajectory
        assert ctx.trajectory is not None
        assert len(ctx.trajectory.rounds) == 2
        assert ctx.trajectory.rounds[0].round_idx == 0
        assert len(ctx.trajectory.rounds[0].agents) == 2

        # agent_profiles
        assert len(ctx.agent_profiles) == 2
        assert ctx.agent_profiles[0].name == "Karim Benali"

        # social_network
        assert ctx.social_network is not None
        assert len(ctx.social_network.nodes) == 2
        assert len(ctx.social_network.edges) == 1

        # demographics
        assert ctx.demographics is not None
        assert ctx.demographics.total == 15
        assert len(ctx.demographics.segments) == 4

        # contrefactuels, events, articles, interviews
        assert len(ctx.counterfactuals) == 1
        assert len(ctx.director_events) == 1
        assert len(ctx.articles) == 1
        assert len(ctx.interviews) == 1
        assert ctx.interviews[0].final_stance == "neutral"

        # outline
        assert ctx.outline is not None
        assert ctx.outline.title.startswith("Rapport")
        assert len(ctx.outline.sections) == 3

        # sections_md (keys are ints)
        assert ctx.sections_md[0].startswith("## Contexte")

        # kpi_hero
        assert ctx.kpi_hero is not None
        assert ctx.kpi_hero.confidence_pct == 74.0
        assert ctx.kpi_hero.brier == 0.18

        # pivotal_moments
        assert len(ctx.pivotal_moments) == 1
        assert ctx.pivotal_moments[0].round == 3
        assert ctx.pivotal_moments[0].delta_score == 0.15

        # interpretations & takeaways
        assert "consensus" in ctx.interpretations
        assert len(ctx.executive_takeaways) == 3

    def test_optional_fields_none(self):
        """Construction avec tous les champs optionnels explicitement None."""
        ctx = PDFReportContext(**_optional_none_context())
        assert ctx.sim_config is None
        assert ctx.sim_state is None
        assert ctx.outcome is None
        assert ctx.quality_metrics is None
        assert ctx.trajectory is None
        assert ctx.social_network is None
        assert ctx.demographics is None
        assert ctx.outline is None
        assert ctx.full_report_md is None
        assert ctx.kpi_hero is None
        # Listes vides par défaut
        assert ctx.agent_profiles == []
        assert ctx.counterfactuals == []

    def test_arabic_lang_valid(self):
        """Construction avec lang='ar' (arabe)."""
        ctx = PDFReportContext(
            report_id=VALID_REPORT_ID,
            simulation_id=VALID_SIM_ID,
            lang="ar",
            framework="market",
        )
        assert ctx.lang == "ar"

    def test_english_lang_valid(self):
        """Construction avec lang='en' (anglais)."""
        ctx = PDFReportContext(
            report_id=VALID_REPORT_ID,
            simulation_id=VALID_SIM_ID,
            lang="en",
        )
        assert ctx.lang == "en"

    def test_all_frameworks_valid(self):
        """Tous les frameworks acceptés sont valides."""
        for fw in ("cerberus", "market", "crisis", "policy", "decision"):
            ctx = PDFReportContext(
                report_id=VALID_REPORT_ID,
                simulation_id=VALID_SIM_ID,
                framework=fw,
            )
            assert ctx.framework == fw


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Construction invalid — raise ValidationError
# ═══════════════════════════════════════════════════════════════════════════════


class TestInvalidConstruction:
    def test_invalid_lang_raises(self):
        """lang hors {fr, en, ar} → ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PDFReportContext(
                report_id=VALID_REPORT_ID,
                simulation_id=VALID_SIM_ID,
                lang="de",  # type: ignore[arg-type]
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("lang",) for e in errors)

    def test_invalid_framework_raises(self):
        """framework hors {cerberus, market, crisis, policy, decision} → ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PDFReportContext(
                report_id=VALID_REPORT_ID,
                simulation_id=VALID_SIM_ID,
                framework="unknown",  # type: ignore[arg-type]
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("framework",) for e in errors)

    def test_invalid_report_id_raises(self):
        """report_id au format incorrect → ValidationError."""
        bad_ids = [
            "rpt_a1b2c3d4e5f6",   # préfixe incorrect
            "report_SHORT",        # trop court
            "report_g1b2c3d4e5f6", # 'g' n'est pas un hex valide
            "report_a1b2c3d4e5f67", # trop long (13 chars hex)
            "report_A1B2C3D4E5F6",  # majuscules non acceptées
            "",                     # vide
            "sim_a1b2c3d4e5f6",    # mauvais préfixe
        ]
        for bad_id in bad_ids:
            with pytest.raises(ValidationError, match="report_id") as exc_info:
                PDFReportContext(
                    report_id=bad_id,
                    simulation_id=VALID_SIM_ID,
                )
            errors = exc_info.value.errors()
            assert any(e["loc"] == ("report_id",) for e in errors), (
                f"Attendu une erreur sur report_id pour '{bad_id}'"
            )

    def test_invalid_simulation_id_raises(self):
        """simulation_id au format incorrect → ValidationError."""
        bad_ids = [
            "simulation_a1b2c3d4e5f6",  # préfixe incorrect
            "sim_SHORT",                 # trop court
            "sim_g1b2c3d4e5f6",         # 'g' non hex
            "sim_A1B2C3D4E5F6",         # majuscules non acceptées
            "",                          # vide
            "report_a1b2c3d4e5f6",       # mauvais préfixe
        ]
        for bad_id in bad_ids:
            with pytest.raises(ValidationError, match="simulation_id") as exc_info:
                PDFReportContext(
                    report_id=VALID_REPORT_ID,
                    simulation_id=bad_id,
                )
            errors = exc_info.value.errors()
            assert any(e["loc"] == ("simulation_id",) for e in errors), (
                f"Attendu une erreur sur simulation_id pour '{bad_id}'"
            )

    def test_missing_report_id_raises(self):
        """Absence de report_id → ValidationError."""
        with pytest.raises(ValidationError):
            PDFReportContext(simulation_id=VALID_SIM_ID)  # type: ignore[call-arg]

    def test_missing_simulation_id_raises(self):
        """Absence de simulation_id → ValidationError."""
        with pytest.raises(ValidationError):
            PDFReportContext(report_id=VALID_REPORT_ID)  # type: ignore[call-arg]

    def test_quality_metrics_out_of_range_raises(self):
        """QualityMetrics avec valeur hors [0,1] → ValidationError."""
        with pytest.raises(ValidationError):
            QualityMetrics(coherence=1.5, diversity=0.5, plausibility=0.5, alignment=0.5)

    def test_outcome_bullish_out_of_range_raises(self):
        """Outcome avec bullish_pct > 100 → ValidationError."""
        with pytest.raises(ValidationError):
            Outcome(bullish_pct=110.0)

    def test_kpi_hero_brier_out_of_range_raises(self):
        """KPIHero avec brier > 1.0 → ValidationError."""
        with pytest.raises(ValidationError):
            KPIHero(brier=1.5)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Roundtrip JSON
# ═══════════════════════════════════════════════════════════════════════════════


class TestJsonRoundtrip:
    def test_minimal_roundtrip(self):
        """Roundtrip JSON sur contexte minimal."""
        ctx = PDFReportContext(**_minimal_context())
        json_str = ctx.model_dump_json()
        ctx2 = PDFReportContext.model_validate_json(json_str)
        assert ctx2.report_id == ctx.report_id
        assert ctx2.simulation_id == ctx.simulation_id
        assert ctx2.framework == ctx.framework
        assert ctx2.lang == ctx.lang

    def test_full_roundtrip(self):
        """Roundtrip JSON sur contexte complet."""
        ctx = PDFReportContext(**_full_context())
        json_str = ctx.model_dump_json()

        # Vérification que le JSON est parsable
        parsed = json.loads(json_str)
        assert parsed["report_id"] == VALID_REPORT_ID
        assert parsed["simulation_id"] == VALID_SIM_ID

        # Reconstruction depuis JSON
        ctx2 = PDFReportContext.model_validate_json(json_str)
        assert ctx2.framework == ctx.framework
        assert ctx2.lang == ctx.lang
        assert ctx2.outcome is not None
        assert ctx2.outcome.bullish_pct == ctx.outcome.bullish_pct
        assert ctx2.trajectory is not None
        assert len(ctx2.trajectory.rounds) == len(ctx.trajectory.rounds)
        assert len(ctx2.agent_profiles) == len(ctx.agent_profiles)
        assert ctx2.kpi_hero is not None
        assert ctx2.kpi_hero.confidence_pct == ctx.kpi_hero.confidence_pct

    def test_roundtrip_preserves_sections_md_int_keys(self):
        """Roundtrip JSON préserve les clés int de sections_md."""
        ctx = PDFReportContext(
            report_id=VALID_REPORT_ID,
            simulation_id=VALID_SIM_ID,
            sections_md={0: "Section 0", 1: "Section 1", 5: "Section 5"},
        )
        json_str = ctx.model_dump_json()
        ctx2 = PDFReportContext.model_validate_json(json_str)
        assert ctx2.sections_md[0] == "Section 0"
        assert ctx2.sections_md[1] == "Section 1"
        assert ctx2.sections_md[5] == "Section 5"

    def test_roundtrip_none_optionals_preserved(self):
        """Roundtrip JSON préserve les None des optionnels."""
        ctx = PDFReportContext(**_optional_none_context())
        json_str = ctx.model_dump_json()
        ctx2 = PDFReportContext.model_validate_json(json_str)
        assert ctx2.sim_config is None
        assert ctx2.outcome is None
        assert ctx2.trajectory is None
        assert ctx2.kpi_hero is None


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Default values
# ═══════════════════════════════════════════════════════════════════════════════


class TestDefaults:
    def test_sim_config_defaults(self):
        sc = SimConfig()
        assert sc.title == ""
        assert sc.package == ""
        assert sc.framework == "cerberus"
        assert sc.lang == "fr"
        assert sc.sources == []
        assert sc.params == {}

    def test_sim_state_defaults(self):
        ss = SimState()
        assert ss.status == "completed"
        assert ss.current_round == 0
        assert ss.profiles_count == 0
        assert ss.entities_count == 0
        assert ss.entity_types == []

    def test_outcome_defaults(self):
        o = Outcome()
        assert o.verdict == ""
        assert o.bullish_pct == 0.0
        assert o.bearish_pct == 0.0
        assert o.nb_rounds == 0
        assert o.recommendations == []
        assert o.confidence == 0.0
        assert isinstance(o.quality_metrics, QualityMetrics)
        assert o.scenario_winner is None
        assert o.consensus_reached is False

    def test_quality_metrics_defaults(self):
        qm = QualityMetrics()
        assert qm.coherence == 0.0
        assert qm.diversity == 0.0
        assert qm.plausibility == 0.0
        assert qm.alignment == 0.0

    def test_trajectory_defaults(self):
        t = Trajectory()
        assert t.rounds == []

    def test_round_defaults(self):
        r = Round()
        assert r.round_idx == 0
        assert r.agents == []
        assert r.summary == ""

    def test_agent_state_defaults(self):
        a = AgentState()
        assert a.agent_id == ""
        assert a.name == ""
        assert a.stance == "neutral"
        assert a.score == 0.0
        assert a.message == ""
        assert a.platform == ""

    def test_agent_profile_defaults(self):
        ap = AgentProfile()
        assert ap.name == ""
        assert ap.archetype == ""
        assert ap.biais == []
        assert ap.stance == "neutral"
        assert ap.platform == ""
        assert ap.description == ""

    def test_social_network_defaults(self):
        sn = SocialNetwork()
        assert sn.nodes == []
        assert sn.edges == []

    def test_demographics_defaults(self):
        d = Demographics()
        assert d.segments == []
        assert d.total == 0

    def test_counterfactual_defaults(self):
        c = Counterfactual()
        assert c.hypothesis == ""
        assert c.round_injected == 0
        assert c.delta_verdict == ""
        assert c.delta_confidence == 0.0
        assert c.notes == ""

    def test_director_event_defaults(self):
        de = DirectorEvent()
        assert de.round == 0
        assert de.event_type == ""
        assert de.description == ""
        assert de.impact == ""

    def test_generated_article_defaults(self):
        ga = GeneratedArticle()
        assert ga.agent_name == ""
        assert ga.platform == ""
        assert ga.round == 0
        assert ga.title == ""
        assert ga.content == ""
        assert ga.stance == ""

    def test_agent_interview_defaults(self):
        ai = AgentInterview()
        assert ai.agent_name == ""
        assert ai.archetype == ""
        assert ai.questions == []
        assert ai.answers == []
        assert ai.final_stance == ""

    def test_outline_defaults(self):
        o = Outline()
        assert o.title == ""
        assert o.summary == ""
        assert o.sections == []

    def test_section_defaults(self):
        s = Section()
        assert s.idx == 0
        assert s.title == ""
        assert s.content == ""

    def test_kpi_hero_defaults(self):
        k = KPIHero()
        assert k.verdict == ""
        assert k.confidence_pct == 0.0
        assert k.brier == 0.0
        assert k.scenario_distribution == {}

    def test_pivotal_moment_defaults(self):
        pm = PivotalMoment()
        assert pm.round == 0
        assert pm.agent == ""
        assert pm.event == ""
        assert pm.delta_score == 0.0

    def test_pdf_report_context_list_defaults_are_independent(self):
        """Vérifie que les default_factory créent des objets indépendants."""
        ctx1 = PDFReportContext(report_id=VALID_REPORT_ID, simulation_id=VALID_SIM_ID)
        ctx2 = PDFReportContext(
            report_id="report_000000000001",
            simulation_id="sim_000000000001",
        )
        ctx1.agent_profiles.append(AgentProfile(name="Test"))
        assert len(ctx2.agent_profiles) == 0  # isolation garantie


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Tests sub-models isolés
# ═══════════════════════════════════════════════════════════════════════════════


class TestSubModels:
    def test_social_node_weight_ge_zero(self):
        """SocialNode.weight ne peut pas être négatif."""
        with pytest.raises(ValidationError):
            SocialNode(id="n1", weight=-0.1)

    def test_social_edge_weight_ge_zero(self):
        """SocialEdge.weight ne peut pas être négatif."""
        with pytest.raises(ValidationError):
            SocialEdge(source="a", target="b", weight=-1.0)

    def test_demographic_segment_pct_range(self):
        """DemographicSegment.pct doit être dans [0, 100]."""
        with pytest.raises(ValidationError):
            DemographicSegment(label="X", count=5, pct=105.0, dimension="geo")

    def test_round_idx_non_negative(self):
        """Round.round_idx ne peut pas être négatif."""
        with pytest.raises(ValidationError):
            Round(round_idx=-1)

    def test_section_idx_non_negative(self):
        """Section.idx ne peut pas être négatif."""
        with pytest.raises(ValidationError):
            Section(idx=-1)

    def test_outline_with_sections(self):
        """Outline avec sections construites depuis dict."""
        outline = Outline(
            title="Mon rapport",
            summary="Résumé exécutif.",
            sections=[
                {"idx": 0, "title": "Introduction", "content": "..."},
                {"idx": 1, "title": "Analyse", "content": "..."},
            ],
        )
        assert len(outline.sections) == 2
        assert outline.sections[1].title == "Analyse"

    def test_kpi_hero_scenario_distribution(self):
        """KPIHero.scenario_distribution accepte un dict str → float."""
        kpi = KPIHero(
            verdict="Consensus atteint",
            confidence_pct=82.0,
            brier=0.12,
            scenario_distribution={"Bull": 0.7, "Bear": 0.3},
        )
        assert kpi.scenario_distribution["Bull"] == 0.7

    def test_trajectory_nested_roundtrip(self):
        """Trajectory avec rounds imbriqués → roundtrip JSON stable."""
        traj = Trajectory(
            rounds=[
                Round(
                    round_idx=0,
                    agents=[AgentState(agent_id="a1", name="Agent 1", stance="bullish")],
                )
            ]
        )
        json_str = traj.model_dump_json()
        traj2 = Trajectory.model_validate_json(json_str)
        assert len(traj2.rounds) == 1
        assert traj2.rounds[0].agents[0].agent_id == "a1"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Validators ciblés
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidators:
    def test_report_id_valid_formats(self):
        """Formes valides de report_id."""
        valid_ids = [
            "report_a1b2c3d4e5f6",
            "report_000000000000",
            "report_abcdef012345",
            "report_fedcba987654",
        ]
        for rid in valid_ids:
            ctx = PDFReportContext(report_id=rid, simulation_id=VALID_SIM_ID)
            assert ctx.report_id == rid

    def test_simulation_id_valid_formats(self):
        """Formes valides de simulation_id."""
        valid_ids = [
            "sim_a1b2c3d4e5f6",
            "sim_000000000000",
            "sim_abcdef012345",
        ]
        for sid in valid_ids:
            ctx = PDFReportContext(report_id=VALID_REPORT_ID, simulation_id=sid)
            assert ctx.simulation_id == sid

    def test_validate_assignment_lang(self):
        """validate_assignment=True : modification post-construction validée."""
        ctx = PDFReportContext(report_id=VALID_REPORT_ID, simulation_id=VALID_SIM_ID)
        ctx.lang = "ar"
        assert ctx.lang == "ar"
        with pytest.raises(ValidationError):
            ctx.lang = "es"  # type: ignore[assignment]

    def test_validate_assignment_framework(self):
        """validate_assignment=True : modification post-construction de framework."""
        ctx = PDFReportContext(report_id=VALID_REPORT_ID, simulation_id=VALID_SIM_ID)
        ctx.framework = "crisis"
        assert ctx.framework == "crisis"
        with pytest.raises(ValidationError):
            ctx.framework = "invalid"  # type: ignore[assignment]

    def test_extra_fields_ignored(self):
        """extra='ignore' : champs inconnus absorbés silencieusement."""
        ctx = PDFReportContext(
            report_id=VALID_REPORT_ID,
            simulation_id=VALID_SIM_ID,
            unknown_field_from_future_artifact="should_be_ignored",  # type: ignore[call-arg]
        )
        assert not hasattr(ctx, "unknown_field_from_future_artifact")

    def test_counterfactual_delta_confidence_range(self):
        """Counterfactual.delta_confidence doit être dans [-1.0, 1.0]."""
        with pytest.raises(ValidationError):
            Counterfactual(delta_confidence=1.5)
        with pytest.raises(ValidationError):
            Counterfactual(delta_confidence=-1.5)
        # Bornes valides
        c1 = Counterfactual(delta_confidence=1.0)
        assert c1.delta_confidence == 1.0
        c2 = Counterfactual(delta_confidence=-1.0)
        assert c2.delta_confidence == -1.0
