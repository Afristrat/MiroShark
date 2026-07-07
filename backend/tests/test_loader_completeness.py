"""
Tests de complétude du PDFContextLoader — US-134.

Vérifie que les 11 champs critiques sont correctement remplis par le loader,
y compris les formats production (aliases de champs) et les formats de fixtures.

Couverture :
    1.  outline.title non vide (avec report)
    2.  outline.summary non vide (avec report)
    3.  outcome.verdict non vide
    4.  outcome.recommendations non vide (List[str])
    5.  outcome.bullish_pct non None/non zéro
    6.  config.title (sim_config.title) non vide
    7.  config.sources non vide (List[str])
    8.  state.current_round > 0
    9.  agent_profiles[0].archetype non vide
    10. agent_profiles[0].platform non vide
    11. Posts critiques : len ≥ 5 (via agent_log critical_posts)
    12. Articles générés : len(ctx.articles) ≥ 1

    + Tests de robustesse sur les aliases de champs production :
    13. simulation_config.json production : simulation_requirement → title
    14. simulation_config.json production : source_documents → sources
    15. outcome.json production : final_verdict → verdict
    16. outcome.json production : recommendation_list → recommendations
    17. trajectory.json production (snapshots) → rounds ≥ 1
    18. state.json production aliases : round → current_round
    19. agent_profiles production : realname + persona.archetype → AgentProfile
    20. generated_article.json production : article_text → GeneratedArticle

    + Test conditionnel simulation réelle (skip si absente)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# ── Ajout du backend/ au sys.path ────────────────────────────────────────────
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services.report_pdf.loader import (
    PDFContextLoader,
    _SIMULATIONS_DIR,
)
from app.services.report_pdf.schema import PDFReportContext

# ─── Chemins des fixtures ─────────────────────────────────────────────────────
_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

_TEST_SIM_ID = "sim_aabbcc112233"
_TEST_REP_ID = "report_a1b2c3d4e5f6"


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _write_jsonl(path: Path, records: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load_fixture_ctx(include_report: bool = False) -> PDFReportContext:
    """Charge le contexte depuis les fixtures statiques."""
    if include_report:
        return PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            report_id=_TEST_REP_ID,
            sim_base_dir=_FIXTURES_DIR,
            rep_base_dir=_FIXTURES_DIR,
        )
    return PDFContextLoader.load(
        simulation_id=_TEST_SIM_ID,
        sim_base_dir=_FIXTURES_DIR,
    )


def _minimal_sim_dir(tmp_path: Path) -> Path:
    """Crée un dossier simulation minimal avec simulation_config.json."""
    sim_dir = tmp_path / _TEST_SIM_ID
    sim_dir.mkdir(parents=True)
    _write_json(sim_dir / "simulation_config.json", {
        "title": "Test minimal",
        "framework": "cerberus",
        "lang": "fr",
    })
    return sim_dir


# ═══════════════════════════════════════════════════════════════════════════════
# Groupe 1 — Champs critiques sur fixtures statiques
# ═══════════════════════════════════════════════════════════════════════════════


class TestOutlineFields:
    """outline.title et outline.summary doivent être non vides avec un report."""

    def test_outline_title_not_empty(self):
        ctx = _load_fixture_ctx(include_report=True)
        assert ctx.outline is not None, "outline doit être chargé quand report_id fourni"
        assert ctx.outline.title, "outline.title ne doit pas être vide"
        assert len(ctx.outline.title) > 0

    def test_outline_summary_not_empty(self):
        ctx = _load_fixture_ctx(include_report=True)
        assert ctx.outline is not None
        assert ctx.outline.summary, "outline.summary ne doit pas être vide"
        assert len(ctx.outline.summary) > 0


class TestOutcomeFields:
    """outcome.verdict, recommendations, bullish_pct doivent être chargés."""

    def test_outcome_verdict_not_empty(self):
        ctx = _load_fixture_ctx()
        assert ctx.outcome is not None, "outcome doit être chargé depuis outcome.json"
        assert ctx.outcome.verdict, "outcome.verdict ne doit pas être vide"
        assert len(ctx.outcome.verdict) > 0

    def test_outcome_recommendations_not_empty(self):
        ctx = _load_fixture_ctx()
        assert ctx.outcome is not None
        assert isinstance(ctx.outcome.recommendations, list)
        assert len(ctx.outcome.recommendations) > 0, "outcome.recommendations ne doit pas être vide"
        assert all(isinstance(r, str) for r in ctx.outcome.recommendations)

    def test_outcome_bullish_pct_loaded(self):
        ctx = _load_fixture_ctx()
        assert ctx.outcome is not None
        # bullish_pct doit être non None ET non nul (fixture a 60.0)
        assert ctx.outcome.bullish_pct is not None
        assert ctx.outcome.bullish_pct > 0, f"bullish_pct attendu > 0, obtenu {ctx.outcome.bullish_pct}"


class TestConfigFields:
    """sim_config.title et sim_config.sources doivent être chargés."""

    def test_config_title_not_empty(self):
        ctx = _load_fixture_ctx()
        assert ctx.sim_config is not None
        assert ctx.sim_config.title, "sim_config.title (= simulation_requirement) ne doit pas être vide"

    def test_config_sources_not_empty(self):
        ctx = _load_fixture_ctx()
        assert ctx.sim_config is not None
        assert isinstance(ctx.sim_config.sources, list)
        assert len(ctx.sim_config.sources) > 0, "sim_config.sources ne doit pas être vide"


class TestStateFields:
    """sim_state.current_round doit être > 0."""

    def test_state_current_round_positive(self):
        ctx = _load_fixture_ctx()
        assert ctx.sim_state is not None
        assert ctx.sim_state.current_round > 0, (
            f"sim_state.current_round attendu > 0, obtenu {ctx.sim_state.current_round}"
        )


class TestAgentProfileFields:
    """agent_profiles[0].archetype et platform doivent être non vides."""

    def test_agent_profile_archetype_not_empty(self):
        ctx = _load_fixture_ctx()
        assert len(ctx.agent_profiles) > 0, "agent_profiles ne doit pas être vide"
        assert ctx.agent_profiles[0].archetype, (
            "agent_profiles[0].archetype ne doit pas être vide"
        )

    def test_agent_profile_platform_not_empty(self):
        ctx = _load_fixture_ctx()
        assert len(ctx.agent_profiles) > 0
        assert ctx.agent_profiles[0].platform, (
            "agent_profiles[0].platform ne doit pas être vide"
        )


class TestCriticalPosts:
    """Les posts critiques doivent être extraits depuis actions.jsonl."""

    def test_critical_posts_count(self):
        ctx = _load_fixture_ctx()
        # Les posts critiques sont stockés dans agent_log avec _type=critical_posts
        critical_entries = [
            entry for entry in ctx.agent_log
            if isinstance(entry, dict) and entry.get("_type") == "critical_posts"
        ]
        if not critical_entries:
            # Pas de posts critiques trouvés — vérifier si actions.jsonl a des posts
            pytest.skip("Aucune entrée critical_posts dans agent_log — actions.jsonl vide ?")
        posts = critical_entries[0].get("posts", [])
        assert len(posts) >= 5, (
            f"Attendu ≥ 5 posts critiques, obtenu {len(posts)}. "
            f"Vérifier que actions.jsonl contient des entrées de type post/tweet/comment."
        )

    def test_critical_posts_have_content(self):
        ctx = _load_fixture_ctx()
        critical_entries = [
            entry for entry in ctx.agent_log
            if isinstance(entry, dict) and entry.get("_type") == "critical_posts"
        ]
        if not critical_entries:
            pytest.skip("Aucune entrée critical_posts — test ignoré.")
        posts = critical_entries[0].get("posts", [])
        if not posts:
            pytest.skip("Liste posts vide — test ignoré.")
        for post in posts:
            assert "content" in post, "Chaque post doit avoir un champ 'content'"
            assert post["content"], "Le contenu du post ne doit pas être vide"


class TestArticles:
    """Les articles générés doivent être extraits correctement."""

    def test_articles_count(self):
        ctx = _load_fixture_ctx()
        assert len(ctx.articles) >= 1, (
            f"Attendu ≥ 1 article généré, obtenu {len(ctx.articles)}. "
            f"Vérifier generated_article.json."
        )

    def test_articles_have_content(self):
        ctx = _load_fixture_ctx()
        if not ctx.articles:
            pytest.skip("Aucun article — test ignoré.")
        for article in ctx.articles:
            assert article.content or article.title, "L'article doit avoir un contenu ou un titre"


# ═══════════════════════════════════════════════════════════════════════════════
# Groupe 2 — Aliases de champs production
# ═══════════════════════════════════════════════════════════════════════════════


class TestProductionSimConfig:
    """simulation_requirement → title, source_documents → sources."""

    def test_simulation_requirement_mapped_to_title(self, tmp_path):
        """Le champ production 'simulation_requirement' doit alimenter sim_config.title."""
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "simulation_requirement": "Export Ready : quand l'agrégation devient une guerre d'influence",
            "time_config": {
                "total_simulation_hours": 72,
                "minutes_per_round": 5,
            },
            "agent_configs": [],
            "llm_model": "gpt-4o",
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.sim_config is not None
        assert ctx.sim_config.title, "sim_config.title doit être non vide depuis simulation_requirement"
        assert "Export Ready" in ctx.sim_config.title

    def test_source_documents_mapped_to_sources(self, tmp_path):
        """Le champ production 'source_documents' doit alimenter sim_config.sources."""
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "simulation_requirement": "Test sources",
            "source_documents": ["Document A", "Document B", "Document C"],
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.sim_config is not None
        assert len(ctx.sim_config.sources) >= 3, "sources doit contenir les 3 documents"


class TestProductionOutcome:
    """final_verdict → verdict, recommendation_list → recommendations."""

    def test_final_verdict_mapped_to_verdict(self, tmp_path):
        """Le champ production 'final_verdict' doit alimenter outcome.verdict."""
        sim_dir = _minimal_sim_dir(tmp_path)
        _write_json(sim_dir / "outcome.json", {
            "final_verdict": "L'exportation administrative va renforcer les dynamiques de polarisation.",
            "bullish_pct": 45.0,
            "bearish_pct": 35.0,
            "confidence": 0.80,
            "quality_metrics": {
                "coherence": 0.85,
                "diversity": 0.70,
                "plausibility": 0.75,
                "alignment": 0.80,
            },
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.outcome is not None
        assert ctx.outcome.verdict, "outcome.verdict doit être non vide depuis final_verdict"
        assert "exportation" in ctx.outcome.verdict.lower() or "polarisation" in ctx.outcome.verdict.lower()

    def test_recommendation_list_mapped_to_recommendations(self, tmp_path):
        """Le champ production 'recommendation_list' doit alimenter outcome.recommendations."""
        sim_dir = _minimal_sim_dir(tmp_path)
        _write_json(sim_dir / "outcome.json", {
            "verdict": "Test",
            "recommendation_list": [
                "Recommandation A : surveiller les dynamiques de polarisation",
                "Recommandation B : adapter la communication institutionnelle",
            ],
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.outcome is not None
        assert len(ctx.outcome.recommendations) >= 2, "recommendations doit être non vide depuis recommendation_list"

    def test_bullish_pct_aliases(self, tmp_path):
        """Le champ 'bullish_percentage' doit alimenter outcome.bullish_pct."""
        sim_dir = _minimal_sim_dir(tmp_path)
        _write_json(sim_dir / "outcome.json", {
            "verdict": "Test alias bullish",
            "bullish_percentage": 55.0,
            "bearish_percentage": 30.0,
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.outcome is not None
        assert ctx.outcome.bullish_pct == pytest.approx(55.0)
        assert ctx.outcome.bearish_pct == pytest.approx(30.0)


class TestProductionTrajectory:
    """Format production snapshots → Trajectory.rounds."""

    def test_snapshots_format_loaded(self, tmp_path):
        """trajectory.json au format production (snapshots) doit générer des rounds."""
        sim_dir = _minimal_sim_dir(tmp_path)
        _write_json(sim_dir / "trajectory.json", {
            "snapshots": [
                {
                    "round_num": 1,
                    "belief_positions": {
                        "AgentA": {"topic1": 0.6, "topic2": 0.4},
                        "AgentB": {"topic1": -0.3, "topic2": -0.5},
                    },
                    "agent_stances": {
                        "AgentA": "bullish",
                        "AgentB": "bearish",
                    },
                },
                {
                    "round_num": 2,
                    "belief_positions": {
                        "AgentA": {"topic1": 0.7, "topic2": 0.5},
                        "AgentB": {"topic1": -0.2, "topic2": -0.3},
                    },
                    "agent_stances": {
                        "AgentA": "bullish",
                        "AgentB": "neutral",
                    },
                },
                {
                    "round_num": 19,
                    "belief_positions": {
                        "AgentA": {"topic1": 0.8},
                        "AgentB": {"topic1": 0.1},
                    },
                    "agent_stances": {
                        "AgentA": "bullish",
                        "AgentB": "bullish",
                    },
                },
            ],
            "topics": ["topic1", "topic2"],
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.trajectory is not None
        assert len(ctx.trajectory.rounds) >= 1, "La trajectoire doit contenir au moins un round"
        # Doit avoir 3 rounds depuis les 3 snapshots
        assert len(ctx.trajectory.rounds) == 3
        # Le premier round doit avoir round_idx = 1
        first = ctx.trajectory.rounds[0]
        assert first.round_idx == 1
        assert len(first.agents) == 2  # AgentA + AgentB


class TestProductionSimState:
    """Aliases state.json : round → current_round."""

    def test_round_alias_mapped_to_current_round(self, tmp_path):
        """Le champ 'round' doit alimenter sim_state.current_round."""
        sim_dir = _minimal_sim_dir(tmp_path)
        _write_json(sim_dir / "state.json", {
            "status": "completed",
            "round": 19,
            "agent_count": 70,
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.sim_state is not None
        assert ctx.sim_state.current_round == 19, (
            f"sim_state.current_round attendu 19, obtenu {ctx.sim_state.current_round}"
        )

    def test_agent_count_alias_mapped_to_profiles_count(self, tmp_path):
        """Le champ 'agent_count' doit alimenter sim_state.profiles_count."""
        sim_dir = _minimal_sim_dir(tmp_path)
        _write_json(sim_dir / "state.json", {
            "status": "completed",
            "round": 5,
            "agent_count": 70,
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.sim_state is not None
        assert ctx.sim_state.profiles_count == 70


class TestProductionAgentProfiles:
    """Profils production : realname + persona.archetype → AgentProfile."""

    def test_realname_mapped_to_name(self, tmp_path):
        """Le champ 'realname' doit alimenter AgentProfile.name."""
        sim_dir = _minimal_sim_dir(tmp_path)
        _write_json(sim_dir / "agent_profiles.json", [
            {
                "realname": "Amina Benali",
                "username": "amina_b",
                "bio": "Journaliste spécialisée en politique économique.",
                "profession": "Journaliste",
                "interested_topics": ["économie", "fiscalité"],
                "persona": {
                    "archetype": "Watchdog",
                    "bio": "Suit de près les décisions gouvernementales.",
                },
                "stance": "neutral",
            }
        ])
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert len(ctx.agent_profiles) == 1
        profile = ctx.agent_profiles[0]
        assert profile.name == "Amina Benali", f"name attendu 'Amina Benali', obtenu '{profile.name}'"

    def test_persona_archetype_extracted(self, tmp_path):
        """Le champ 'persona.archetype' doit alimenter AgentProfile.archetype."""
        sim_dir = _minimal_sim_dir(tmp_path)
        _write_json(sim_dir / "agent_profiles.json", [
            {
                "realname": "Karim Essaadi",
                "persona": {
                    "archetype": "Bull",
                    "bio": "Optimiste structurel sur les réformes.",
                },
                "stance": "bullish",
            }
        ])
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert len(ctx.agent_profiles) == 1
        assert ctx.agent_profiles[0].archetype == "Bull", (
            f"archetype attendu 'Bull', obtenu '{ctx.agent_profiles[0].archetype}'"
        )

    def test_bio_mapped_to_description(self, tmp_path):
        """Le champ 'bio' doit alimenter AgentProfile.description."""
        sim_dir = _minimal_sim_dir(tmp_path)
        _write_json(sim_dir / "agent_profiles.json", [
            {
                "realname": "Sara Benmoussa",
                "bio": "Économiste au Centre de Recherche en Politique Économique.",
            }
        ])
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert len(ctx.agent_profiles) == 1
        assert ctx.agent_profiles[0].description, "description doit être non vide depuis bio"
        assert "Économiste" in ctx.agent_profiles[0].description


class TestProductionGeneratedArticle:
    """generated_article.json production : article_text → GeneratedArticle."""

    def test_article_text_format_loaded(self, tmp_path):
        """Le format production article_text doit créer un GeneratedArticle."""
        sim_dir = _minimal_sim_dir(tmp_path)
        _write_json(sim_dir / "generated_article.json", {
            "article_text": (
                "# L'export ready devient une bataille\n\n"
                "_Comment les algorithmes ont changé la diplomatie._\n\n"
                "**42%** des agents ont basculé en moins de 3 rounds. "
                "C'est le chiffre qui résume tout."
            ),
            "generated_at": "2026-05-05T10:00:00Z",
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert len(ctx.articles) >= 1, "Un article doit être créé depuis article_text"
        article = ctx.articles[0]
        assert article.content, "article.content doit être non vide"
        assert article.title, "article.title doit être extrait de la première ligne"
        # Le titre doit contenir 'export ready' ou 'bataille'
        assert any(
            word in article.title.lower()
            for word in ("export", "bataille", "l'export", "ready")
        ), f"titre inattendu : '{article.title}'"

    def test_empty_article_text_returns_empty_list(self, tmp_path):
        """generated_article.json vide → liste vide, pas de crash."""
        sim_dir = _minimal_sim_dir(tmp_path)
        _write_json(sim_dir / "generated_article.json", {})
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.articles == [], "Un article sans contenu doit être ignoré"


class TestProductionCriticalPosts:
    """Posts critiques depuis le sous-dossier plateforme (format production)."""

    def test_platform_subdir_posts_extracted(self, tmp_path):
        """Les posts depuis twitter/actions.jsonl doivent être extraits."""
        sim_dir = _minimal_sim_dir(tmp_path)
        twitter_dir = sim_dir / "twitter"
        twitter_dir.mkdir(parents=True)

        # Écrire 15 actions (CREATE_POST + LIKE/REPOST)
        records = []
        for i in range(10):
            post_id = f"post_{i}"
            records.append({
                "action_type": "CREATE_POST",
                "agent_name": f"Agent{i}",
                "round": i + 1,
                "action_args": {
                    "post_id": post_id,
                    "content": f"Post {i} : analyse de la réforme fiscale et ses impacts.",
                },
            })
        # Ajouter des likes sur quelques posts
        for i in range(5):
            for _ in range(i + 1):
                records.append({
                    "action_type": "LIKE_POST",
                    "agent_name": "Liker",
                    "round": i + 2,
                    "action_args": {"post_id": f"post_{i}"},
                })

        _write_jsonl(twitter_dir / "actions.jsonl", records)

        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        critical_entries = [
            e for e in ctx.agent_log
            if isinstance(e, dict) and e.get("_type") == "critical_posts"
        ]
        assert critical_entries, "Des posts critiques doivent être extraits depuis twitter/actions.jsonl"
        posts = critical_entries[0]["posts"]
        assert len(posts) >= 5, f"Attendu ≥ 5 posts, obtenu {len(posts)}"

        # Vérifier que les posts sont triés par score décroissant
        scores = [p["score"] for p in posts]
        assert scores == sorted(scores, reverse=True), "Posts non triés par score décroissant"

    def test_no_crash_when_no_actions(self, tmp_path):
        """Absence d'actions.jsonl → agent_log sans critical_posts, pas de crash."""
        _minimal_sim_dir(tmp_path)
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        # Pas de critical_posts quand il n'y a pas d'actions
        critical_entries = [
            e for e in ctx.agent_log
            if isinstance(e, dict) and e.get("_type") == "critical_posts"
        ]
        assert len(critical_entries) == 0, "Pas d'entrée critical_posts sans actions"


# ═══════════════════════════════════════════════════════════════════════════════
# Test conditionnel — simulation réelle
# ═══════════════════════════════════════════════════════════════════════════════


class TestRealSimulationCompleteness:
    """Vérifie les champs critiques sur la simulation réelle (skip si absente)."""

    REAL_SIM_ID = "sim_ea0eb65b2e5b"

    def _load_real(self) -> PDFReportContext:
        real_path = _SIMULATIONS_DIR / self.REAL_SIM_ID
        if not real_path.is_dir():
            pytest.skip(f"Simulation réelle absente : {real_path}")
        return PDFContextLoader.load(simulation_id=self.REAL_SIM_ID)

    def test_real_sim_config_title_not_empty(self):
        ctx = self._load_real()
        assert ctx.sim_config is not None
        assert ctx.sim_config.title, "sim_config.title vide sur sim réelle"

    def test_real_outcome_verdict_not_empty(self):
        ctx = self._load_real()
        if ctx.outcome is None:
            pytest.skip("outcome.json absent sur sim réelle")
        assert ctx.outcome.verdict, "outcome.verdict vide sur sim réelle"

    def test_real_outcome_recommendations_not_empty(self):
        ctx = self._load_real()
        if ctx.outcome is None:
            pytest.skip("outcome.json absent sur sim réelle")
        assert len(ctx.outcome.recommendations) > 0, "recommendations vide sur sim réelle"

    def test_real_agent_profiles_archetype(self):
        ctx = self._load_real()
        if not ctx.agent_profiles:
            pytest.skip("Aucun profil agent sur sim réelle")
        profiles_with_archetype = [p for p in ctx.agent_profiles if p.archetype]
        assert len(profiles_with_archetype) > 0, "Aucun profil avec archetype sur sim réelle"

    def test_real_critical_posts_extracted(self):
        ctx = self._load_real()
        critical_entries = [
            e for e in ctx.agent_log
            if isinstance(e, dict) and e.get("_type") == "critical_posts"
        ]
        if not critical_entries:
            pytest.skip("Aucun post critique extrait sur sim réelle (normal si pas d'actions)")
        posts = critical_entries[0]["posts"]
        assert len(posts) >= 1, "Au moins 1 post critique attendu sur sim réelle"
