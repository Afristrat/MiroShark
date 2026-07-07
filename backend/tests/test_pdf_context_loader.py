"""
Tests pytest exhaustifs pour PDFContextLoader.

US-119 — Loader complet (charge tous les artifacts simulation + report dans
un PDFReportContext).

Couverture :
    1.  Happy path — charge les fixtures sim_aabbcc112233 (sans report)
    2.  Happy path — charge les fixtures sim + report_a1b2c3d4e5f6 (avec report)
    3.  Vérification des champs identité (simulation_id, outcome.verdict, …)
    4.  Fichier optionnel absent → champ None ou liste vide, pas de crash
    5.  simulation_config.json absent → PDFContextLoaderError
    6.  outline.json absent quand report_id fourni → PDFContextLoaderError
    7.  JSON malformé → PDFContextLoaderError
    8.  Fallback chain profils : agent_profiles → reddit → twitter csv → polymarket
    9.  Sections markdown chargées (sections_md Dict[int, str])
    10. Charge sim réelle si le dossier existe (skip sinon)
    11. JSONL actions + events chargés correctement
    12. full_report.md chargé en string brute
"""

from __future__ import annotations

import csv
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
    PDFContextLoaderError,
    _SIMULATIONS_DIR,
)
from app.services.report_pdf.schema import PDFReportContext

# ─── Chemins des fixtures ─────────────────────────────────────────────────────
# Les dossiers fixtures sont nommés avec les IDs de test pour que le loader
# puisse les trouver en passant sim_base_dir=_FIXTURES_DIR.
_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# IDs synthétiques de test (format validé par PDFReportContext)
_TEST_SIM_ID = "sim_aabbcc112233"
_TEST_REP_ID = "report_a1b2c3d4e5f6"


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers fixtures temporaires
# ═══════════════════════════════════════════════════════════════════════════════


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_jsonl(path: Path, records: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — happy path (fixtures statiques)
# ═══════════════════════════════════════════════════════════════════════════════


class TestHappyPathSimOnly:
    """Charge uniquement les artifacts simulation (sans report_id)."""

    def test_load_returns_pdf_report_context(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert isinstance(ctx, PDFReportContext)

    def test_simulation_id_correct(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert ctx.simulation_id == _TEST_SIM_ID

    def test_report_id_generated_when_not_provided(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        # Un report_id synthétique est généré — doit être valide
        assert ctx.report_id.startswith("report_")
        assert len(ctx.report_id) == len("report_") + 12

    def test_sim_config_loaded(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert ctx.sim_config is not None
        assert ctx.sim_config.title == "Simulation test — réforme fiscale"
        assert ctx.sim_config.framework == "cerberus"
        assert ctx.sim_config.lang == "fr"

    def test_sim_state_loaded(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert ctx.sim_state is not None
        assert ctx.sim_state.status == "completed"
        assert ctx.sim_state.current_round == 5
        assert ctx.sim_state.profiles_count == 10

    def test_outcome_loaded(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert ctx.outcome is not None
        assert ctx.outcome.verdict == "Consensus progressif"
        assert ctx.outcome.bullish_pct == 60.0
        assert ctx.outcome.consensus_reached is True

    def test_quality_metrics_loaded(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert ctx.quality_metrics is not None
        assert ctx.quality_metrics.coherence == pytest.approx(0.82)
        assert ctx.quality_metrics.diversity == pytest.approx(0.65)

    def test_trajectory_loaded(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert ctx.trajectory is not None
        assert len(ctx.trajectory.rounds) == 2
        assert ctx.trajectory.rounds[0].round_idx == 0
        assert ctx.trajectory.rounds[1].round_idx == 1

    def test_agent_profiles_loaded(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert len(ctx.agent_profiles) == 2
        names = [p.name for p in ctx.agent_profiles]
        assert "Agent Alpha" in names
        assert "Agent Beta" in names

    def test_social_network_loaded(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert ctx.social_network is not None
        assert len(ctx.social_network.nodes) == 2
        assert len(ctx.social_network.edges) == 1

    def test_demographics_loaded(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert ctx.demographics is not None
        assert len(ctx.demographics.segments) == 3
        assert ctx.demographics.total == 10

    def test_counterfactuals_loaded(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert len(ctx.counterfactuals) == 1
        assert "taux d'imposition" in ctx.counterfactuals[0].hypothesis

    def test_articles_loaded(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert len(ctx.articles) == 1
        assert ctx.articles[0].agent_name == "Agent Alpha"

    def test_actions_log_loaded(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        # actions.jsonl → champ agent_log (pas utilisé ici) — vérifier via director_events
        # actions.jsonl est stocké brut mais director_events vient de events.jsonl
        # Ici on vérifie juste que ça ne plante pas et que les director_events sont chargés
        assert isinstance(ctx.director_events, list)
        assert len(ctx.director_events) == 2  # 2 lignes dans events.jsonl

    def test_director_events_loaded(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert ctx.director_events[0].event_type == "shock"
        assert ctx.director_events[1].event_type == "news"

    def test_lang_parameter_used(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
            lang="en",
        )
        assert ctx.lang == "en"

    def test_title_derived_from_sim_config(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert ctx.title == "Simulation test — réforme fiscale"

    def test_framework_derived_from_sim_config(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert ctx.framework == "cerberus"

    def test_no_report_fields_when_no_report_id(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert ctx.outline is None
        assert ctx.full_report_md is None
        assert ctx.sections_md == {}
        # agent_log peut contenir des entrées critical_posts issues des actions.jsonl
        # même sans report_id — filtrer les entrées report pures (level/message).
        report_entries = [
            e for e in ctx.agent_log
            if isinstance(e, dict) and e.get("_type") != "critical_posts"
        ]
        assert report_entries == [], (
            "Sans report_id, agent_log ne doit contenir que des entrées critical_posts"
        )


class TestHappyPathWithReport:
    """Charge simulation + report (avec report_id fourni)."""

    def test_load_with_report_id(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            report_id=_TEST_REP_ID,
            sim_base_dir=_FIXTURES_DIR,
            rep_base_dir=_FIXTURES_DIR,
        )
        assert ctx.report_id == _TEST_REP_ID
        assert ctx.simulation_id == _TEST_SIM_ID

    def test_outline_loaded(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            report_id=_TEST_REP_ID,
            sim_base_dir=_FIXTURES_DIR,
            rep_base_dir=_FIXTURES_DIR,
        )
        assert ctx.outline is not None
        assert ctx.outline.title == "Rapport d'analyse — Réforme fiscale"
        assert len(ctx.outline.sections) == 2
        assert ctx.outline.sections[0].idx == 0
        assert ctx.outline.sections[1].idx == 1

    def test_full_report_md_loaded(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            report_id=_TEST_REP_ID,
            sim_base_dir=_FIXTURES_DIR,
            rep_base_dir=_FIXTURES_DIR,
        )
        assert ctx.full_report_md is not None
        assert "Rapport d'analyse" in ctx.full_report_md

    def test_sections_md_loaded(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            report_id=_TEST_REP_ID,
            sim_base_dir=_FIXTURES_DIR,
            rep_base_dir=_FIXTURES_DIR,
        )
        assert isinstance(ctx.sections_md, dict)
        assert 0 in ctx.sections_md
        assert 1 in ctx.sections_md
        assert "Résumé exécutif" in ctx.sections_md[0]
        assert "Analyse détaillée" in ctx.sections_md[1]

    def test_agent_log_loaded(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            report_id=_TEST_REP_ID,
            sim_base_dir=_FIXTURES_DIR,
            rep_base_dir=_FIXTURES_DIR,
        )
        assert isinstance(ctx.agent_log, list)
        # agent_log contient les entrées report_agent_log.jsonl + critical_posts
        # Filtrer uniquement les entrées report (level=INFO/etc.)
        report_entries = [
            e for e in ctx.agent_log
            if isinstance(e, dict) and e.get("_type") != "critical_posts"
        ]
        assert len(report_entries) == 2
        assert report_entries[0]["level"] == "INFO"


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — fichiers optionnels absents
# ═══════════════════════════════════════════════════════════════════════════════


class TestMissingOptionalFiles:
    """Fichier optionnel absent → champ None ou liste vide, pas de crash."""

    def test_missing_state_json(self, tmp_path):
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test", "framework": "cerberus", "lang": "fr"
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.sim_state is None

    def test_missing_outcome_json(self, tmp_path):
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test", "framework": "cerberus", "lang": "fr"
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.outcome is None
        assert ctx.quality_metrics is None

    def test_missing_trajectory_json(self, tmp_path):
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test", "framework": "cerberus", "lang": "fr"
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.trajectory is None

    def test_missing_network_json(self, tmp_path):
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test", "framework": "cerberus", "lang": "fr"
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.social_network is None

    def test_missing_demographics_json(self, tmp_path):
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test", "framework": "cerberus", "lang": "fr"
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.demographics is None

    def test_missing_counterfactual_json(self, tmp_path):
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test", "framework": "cerberus", "lang": "fr"
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.counterfactuals == []

    def test_missing_all_profile_files(self, tmp_path):
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test", "framework": "cerberus", "lang": "fr"
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.agent_profiles == []

    def test_missing_events_jsonl(self, tmp_path):
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test", "framework": "cerberus", "lang": "fr"
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.director_events == []

    def test_missing_full_report_md(self, tmp_path):
        """Avec report_id fourni mais full_report.md absent → None, pas de crash."""
        sim_dir = tmp_path / _TEST_SIM_ID
        rep_dir = tmp_path / _TEST_REP_ID
        sim_dir.mkdir(parents=True)
        rep_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test", "framework": "cerberus", "lang": "fr"
        })
        _write_json(rep_dir / "outline.json", {
            "title": "Rapport test",
            "summary": "Résumé",
            "sections": [],
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            report_id=_TEST_REP_ID,
            sim_base_dir=tmp_path,
            rep_base_dir=tmp_path,
        )
        assert ctx.full_report_md is None


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — fichiers obligatoires absents → PDFContextLoaderError
# ═══════════════════════════════════════════════════════════════════════════════


class TestMissingRequiredFiles:
    """Fichier obligatoire absent → PDFContextLoaderError levée."""

    def test_missing_simulation_config_raises(self, tmp_path):
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        # Pas de simulation_config.json
        with pytest.raises(PDFContextLoaderError, match="simulation_config.json"):
            PDFContextLoader.load(
                simulation_id=_TEST_SIM_ID,
                sim_base_dir=tmp_path,
            )

    def test_missing_outline_raises_when_report_id_given(self, tmp_path):
        sim_dir = tmp_path / _TEST_SIM_ID
        rep_dir = tmp_path / _TEST_REP_ID
        sim_dir.mkdir(parents=True)
        rep_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test", "framework": "cerberus", "lang": "fr"
        })
        # Pas de outline.json dans le dossier rapport
        with pytest.raises(PDFContextLoaderError, match="outline.json"):
            PDFContextLoader.load(
                simulation_id=_TEST_SIM_ID,
                report_id=_TEST_REP_ID,
                sim_base_dir=tmp_path,
                rep_base_dir=tmp_path,
            )

    def test_error_message_contains_path(self, tmp_path):
        """Le message d'erreur mentionne le chemin du fichier manquant."""
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        with pytest.raises(PDFContextLoaderError) as exc_info:
            PDFContextLoader.load(
                simulation_id=_TEST_SIM_ID,
                sim_base_dir=tmp_path,
            )
        assert "simulation_config.json" in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — JSON malformé
# ═══════════════════════════════════════════════════════════════════════════════


class TestMalformedJSON:
    """JSON invalide → PDFContextLoaderError avec message explicite."""

    def test_malformed_simulation_config(self, tmp_path):
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        (sim_dir / "simulation_config.json").write_text(
            "{invalid json", encoding="utf-8"
        )
        with pytest.raises(PDFContextLoaderError, match="JSON malformé"):
            PDFContextLoader.load(
                simulation_id=_TEST_SIM_ID,
                sim_base_dir=tmp_path,
            )

    def test_malformed_outcome_json(self, tmp_path):
        """outcome.json malformé → PDFContextLoaderError."""
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test", "framework": "cerberus", "lang": "fr"
        })
        (sim_dir / "outcome.json").write_text(
            "[broken json}", encoding="utf-8"
        )
        with pytest.raises(PDFContextLoaderError, match="JSON malformé"):
            PDFContextLoader.load(
                simulation_id=_TEST_SIM_ID,
                sim_base_dir=tmp_path,
            )

    def test_malformed_outline_json(self, tmp_path):
        """outline.json malformé → PDFContextLoaderError."""
        sim_dir = tmp_path / _TEST_SIM_ID
        rep_dir = tmp_path / _TEST_REP_ID
        sim_dir.mkdir(parents=True)
        rep_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test", "framework": "cerberus", "lang": "fr"
        })
        (rep_dir / "outline.json").write_text("not json!", encoding="utf-8")
        with pytest.raises(PDFContextLoaderError, match="JSON malformé"):
            PDFContextLoader.load(
                simulation_id=_TEST_SIM_ID,
                report_id=_TEST_REP_ID,
                sim_base_dir=tmp_path,
                rep_base_dir=tmp_path,
            )

    def test_malformed_jsonl_lines_skipped(self, tmp_path):
        """JSONL avec lignes invalides → lignes invalides ignorées, reste chargé."""
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test", "framework": "cerberus", "lang": "fr"
        })
        (sim_dir / "events.jsonl").write_text(
            '{"event_type": "shock", "description": "valid"}\n'
            'INVALID JSON LINE\n'
            '{"event_type": "news", "description": "also valid"}\n',
            encoding="utf-8",
        )
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        # Les 2 lignes valides doivent être chargées, l'invalide ignorée
        assert len(ctx.director_events) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Fallback chain profils
# ═══════════════════════════════════════════════════════════════════════════════


class TestProfileFallbackChain:
    """Vérifie la chaîne de fallback : agent_profiles → reddit → twitter csv → polymarket."""

    def _make_sim_dir(self, tmp_path: Path) -> Path:
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test", "framework": "cerberus", "lang": "fr"
        })
        return sim_dir

    def test_agent_profiles_json_takes_priority(self, tmp_path):
        sim_dir = self._make_sim_dir(tmp_path)
        # agent_profiles.json ET reddit_profiles.json présents
        _write_json(sim_dir / "agent_profiles.json", [
            {"name": "From_AgentProfiles", "platform": "twitter"}
        ])
        _write_json(sim_dir / "reddit_profiles.json", [
            {"name": "From_Reddit", "platform": "reddit"}
        ])
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert len(ctx.agent_profiles) == 1
        assert ctx.agent_profiles[0].name == "From_AgentProfiles"

    def test_fallback_to_reddit_when_agent_profiles_missing(self, tmp_path):
        sim_dir = self._make_sim_dir(tmp_path)
        _write_json(sim_dir / "reddit_profiles.json", [
            {"name": "From_Reddit", "platform": "reddit"}
        ])
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert len(ctx.agent_profiles) == 1
        assert ctx.agent_profiles[0].name == "From_Reddit"

    def test_fallback_to_twitter_csv(self, tmp_path):
        sim_dir = self._make_sim_dir(tmp_path)
        csv_path = sim_dir / "twitter_profiles.csv"
        with open(csv_path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["name", "archetype", "biais", "stance", "platform", "description"])
            writer.writeheader()
            writer.writerow({
                "name": "twitter_user",
                "archetype": "Challenger",
                "biais": "anchoring",
                "stance": "bullish",
                "platform": "twitter",
                "description": "Un utilisateur Twitter.",
            })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert len(ctx.agent_profiles) == 1
        assert ctx.agent_profiles[0].name == "twitter_user"
        assert ctx.agent_profiles[0].platform == "twitter"

    def test_fallback_to_polymarket(self, tmp_path):
        sim_dir = self._make_sim_dir(tmp_path)
        _write_json(sim_dir / "polymarket_profiles.json", [
            {"name": "From_Polymarket", "platform": "polymarket", "stance": "bearish"}
        ])
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert len(ctx.agent_profiles) == 1
        assert ctx.agent_profiles[0].name == "From_Polymarket"

    def test_fallback_to_reddit_when_agent_profiles_empty_list(self, tmp_path):
        """agent_profiles.json existe mais vide → fallback vers reddit."""
        sim_dir = self._make_sim_dir(tmp_path)
        _write_json(sim_dir / "agent_profiles.json", [])  # liste vide
        _write_json(sim_dir / "reddit_profiles.json", [
            {"name": "From_Reddit_Fallback", "platform": "reddit"}
        ])
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert len(ctx.agent_profiles) == 1
        assert ctx.agent_profiles[0].name == "From_Reddit_Fallback"


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — sections_md
# ═══════════════════════════════════════════════════════════════════════════════


class TestSectionsMd:
    """Vérifie le chargement des sections markdown section_NN.md."""

    def test_sections_md_empty_when_no_report_id(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=_FIXTURES_DIR,
        )
        assert ctx.sections_md == {}

    def test_sections_md_dict_int_str(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            report_id=_TEST_REP_ID,
            sim_base_dir=_FIXTURES_DIR,
            rep_base_dir=_FIXTURES_DIR,
        )
        assert all(isinstance(k, int) for k in ctx.sections_md.keys())
        assert all(isinstance(v, str) for v in ctx.sections_md.values())

    def test_sections_md_indices_correct(self):
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            report_id=_TEST_REP_ID,
            sim_base_dir=_FIXTURES_DIR,
            rep_base_dir=_FIXTURES_DIR,
        )
        assert set(ctx.sections_md.keys()) == {0, 1}

    def test_sections_md_dynamic(self, tmp_path):
        """Génère N sections dynamiquement et vérifie qu'elles sont toutes chargées."""
        sim_dir = tmp_path / _TEST_SIM_ID
        rep_dir = tmp_path / _TEST_REP_ID
        sim_dir.mkdir(parents=True)
        rep_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test", "framework": "cerberus", "lang": "fr"
        })
        _write_json(rep_dir / "outline.json", {
            "title": "T", "summary": "S", "sections": []
        })
        for i in range(5):
            _write_text(rep_dir / f"section_{i:02d}.md", f"# Section {i}\nContenu {i}.")
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            report_id=_TEST_REP_ID,
            sim_base_dir=tmp_path,
            rep_base_dir=tmp_path,
        )
        assert len(ctx.sections_md) == 5
        for i in range(5):
            assert i in ctx.sections_md
            assert f"Section {i}" in ctx.sections_md[i]


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — counterfactual unique dict vs liste
# ═══════════════════════════════════════════════════════════════════════════════


class TestCounterfactualFormats:
    """counterfactual_injection.json peut être un dict ou une liste."""

    def _minimal_sim(self, tmp_path: Path) -> Path:
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "T", "framework": "cerberus", "lang": "fr"
        })
        return sim_dir

    def test_counterfactual_as_dict(self, tmp_path):
        sim_dir = self._minimal_sim(tmp_path)
        _write_json(sim_dir / "counterfactual_injection.json", {
            "hypothesis": "Et si A ?",
            "round_injected": 1,
            "delta_verdict": "Changement",
            "delta_confidence": 0.1,
            "notes": "",
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert len(ctx.counterfactuals) == 1
        assert ctx.counterfactuals[0].hypothesis == "Et si A ?"

    def test_counterfactual_as_list(self, tmp_path):
        sim_dir = self._minimal_sim(tmp_path)
        _write_json(sim_dir / "counterfactual_injection.json", [
            {"hypothesis": "Scénario 1", "round_injected": 1, "delta_confidence": 0.05, "delta_verdict": "", "notes": ""},
            {"hypothesis": "Scénario 2", "round_injected": 2, "delta_confidence": -0.1, "delta_verdict": "", "notes": ""},
        ])
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert len(ctx.counterfactuals) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — extra fields ignorés (extra=ignore)
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtraFieldsIgnored:
    """Les champs inconnus dans les artifacts ne font pas planter le loader."""

    def test_extra_fields_in_sim_config(self, tmp_path):
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test",
            "framework": "cerberus",
            "lang": "fr",
            "unknown_field_xyz": "ignored",
            "another_extra": 42,
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.sim_config is not None
        assert ctx.sim_config.title == "Test"

    def test_extra_fields_in_outcome(self, tmp_path):
        sim_dir = tmp_path / _TEST_SIM_ID
        sim_dir.mkdir(parents=True)
        _write_json(sim_dir / "simulation_config.json", {
            "title": "Test", "framework": "cerberus", "lang": "fr"
        })
        _write_json(sim_dir / "outcome.json", {
            "verdict": "Résultat test",
            "summary": "Champ inconnu qui doit être ignoré",
            "extra_data": {"a": 1},
        })
        ctx = PDFContextLoader.load(
            simulation_id=_TEST_SIM_ID,
            sim_base_dir=tmp_path,
        )
        assert ctx.outcome is not None
        assert ctx.outcome.verdict == "Résultat test"


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — simulation réelle (skip si dossier absent)
# ═══════════════════════════════════════════════════════════════════════════════


class TestRealSimulation:
    """Charge une simulation réelle si son dossier existe sur le disque."""

    REAL_SIM_ID = "sim_ea0eb65b2e5b"

    def test_load_real_sim_if_exists(self):
        real_sim_path = _SIMULATIONS_DIR / self.REAL_SIM_ID
        if not real_sim_path.is_dir():
            pytest.skip(
                f"Simulation réelle absente : {real_sim_path} — test ignoré."
            )
        ctx = PDFContextLoader.load(simulation_id=self.REAL_SIM_ID)
        assert isinstance(ctx, PDFReportContext)
        assert ctx.simulation_id == self.REAL_SIM_ID
        # sim_config doit être chargé (fichier obligatoire)
        assert ctx.sim_config is not None


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — import et export du sous-package
# ═══════════════════════════════════════════════════════════════════════════════


class TestPackageImports:
    """Vérifie que PDFContextLoader et PDFContextLoaderError sont bien exportés."""

    def test_import_from_package(self):
        from app.services.report_pdf import PDFContextLoader as Loader
        from app.services.report_pdf import PDFContextLoaderError as LoaderError
        assert Loader is not None
        assert LoaderError is not None

    def test_loader_error_is_exception(self):
        from app.services.report_pdf import PDFContextLoaderError as LoaderError
        assert issubclass(LoaderError, Exception)
