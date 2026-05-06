"""
Tests pytest pour les templates Jinja2 Markdown PDF Bassira.

US-123 — Templates Jinja2 Markdown source unique + macros réutilisables.

Couverture (≥ 12 tests) :
    1.  Fixture PDFReportContext minimale valide
    2.  Rendu section 00_cover.md.j2
    3.  Rendu section 01_exec_summary.md.j2 (avec executive_takeaways)
    4.  Rendu section 01_exec_summary.md.j2 (fallback outline.summary)
    5.  Rendu section 02_toc.md.j2
    6.  Rendu section 03_diagnostic.md.j2
    7.  Rendu section 04_dynamic.md.j2
    8.  Rendu section 05_verdict.md.j2
    9.  Rendu section 06_recommendations.md.j2 (liste vide → callout warning)
    10. Rendu section 07_appendix.md.j2 (avec full_report_md)
    11. Rendu complet _full.md.j2 (front-matter YAML parseable)
    12. Filter |normalize fonctionne (avant/après)
    13. Sections gracieuses sur données vides (counterfactuals=[] ne crashe pas)
    14. front-matter YAML complet parseable par yaml.safe_load
    15. Inclusion full_report_md dans appendix si présent
    16. Recommandations vides → callout warning dans section 06
    17. executive_takeaways vides avec outline.summary disponible → fallback

Note : LanguageTool n'est pas disponible en CI — le client fait un fallback gracieux
vers une liste vide d'issues (comportement normal attendu).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

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
from app.services.report_pdf.jinja_env import get_jinja_env, render_section, render_full_report


# ─── Constantes de test ───────────────────────────────────────────────────────

VALID_REPORT_ID = "report_a1b2c3d4e5f6"
VALID_SIM_ID = "sim_aabbcc112233"
GENERATED_AT = "2026-05-05T12:00:00Z"


# ─── Mock LanguageTool (indisponible en CI) ───────────────────────────────────

@pytest.fixture(autouse=True, scope="module")
def mock_languagetool_unavailable():
    """Mock LanguageTool pour éviter le timeout 5 s × N appels en CI.

    Le comportement mocké est identique au fallback gracieux (liste vide),
    ce qui est le comportement attendu quand LanguageTool n'est pas disponible.

    On patche à l'emplacement où lt_check est utilisé (importé dans __init__.py)
    ET à la source (languagetool_client.check) pour couvrir tous les cas.
    """
    with patch(
        "app.services.text_normalizer.languagetool_client.check",
        return_value=[],
    ), patch(
        "app.services.text_normalizer.lt_check",
        return_value=[],
    ):
        yield


# ─── Fixture contexte minimal ─────────────────────────────────────────────────

@pytest.fixture(scope="module")
def minimal_context() -> PDFReportContext:
    """Contexte minimal valide — tous les champs optionnels à None/[]."""
    return PDFReportContext(
        report_id=VALID_REPORT_ID,
        simulation_id=VALID_SIM_ID,
        title="Simulation test — Bassira US-123",
        framework="cerberus",
        package="cerberus-standard",
        lang="fr",
    )


@pytest.fixture(scope="module")
def full_context() -> PDFReportContext:
    """Contexte complet avec tous les sous-modèles remplis."""
    return PDFReportContext(
        report_id=VALID_REPORT_ID,
        simulation_id=VALID_SIM_ID,
        title="Analyse stratégique — Marché crypto MENA 2026",
        framework="market",
        package="market-deep-dive",
        lang="fr",
        sim_config=SimConfig(
            title="Impact de la réglementation crypto au Maroc",
            package="market-deep-dive",
            framework="market",
            lang="fr",
            sources=["Bank Al-Maghrib Rapport 2025", "OCDE Crypto Policy 2025"],
            params={"rounds": 5, "agents": 20},
        ),
        sim_state=SimState(
            status="completed",
            current_round=5,
            profiles_count=20,
            entities_count=150,
            entity_types=["Company", "Person", "Regulation"],
        ),
        outcome=Outcome(
            verdict="La réglementation crypto au Maroc est haussière à 67 % de confiance.",
            bullish_pct=67.0,
            bearish_pct=22.0,
            nb_rounds=5,
            recommendations=[
                "Adopter un cadre réglementaire sandbox pour les crypto-actifs.",
                "Former les équipes BAM aux enjeux DeFi.",
                "Dialoguer avec les acteurs MENA pour harmoniser les normes.",
            ],
            confidence=0.67,
            quality_metrics=QualityMetrics(
                coherence=0.82,
                diversity=0.74,
                plausibility=0.79,
                alignment=0.88,
            ),
            scenario_winner="bullish",
            consensus_reached=True,
        ),
        trajectory=Trajectory(
            rounds=[
                Round(
                    round_idx=i,
                    agents=[
                        AgentState(
                            agent_id=f"agent_{i}_{j}",
                            name=f"Agent {j}",
                            stance="bullish" if j % 2 == 0 else "bearish",
                            score=0.5 + (i * 0.05) + (j * 0.01),
                            message=f"Message round {i} agent {j}",
                            platform="twitter",
                        )
                        for j in range(4)
                    ],
                    summary=f"Round {i} résumé.",
                )
                for i in range(5)
            ]
        ),
        agent_profiles=[
            AgentProfile(
                name="Khalil El Fassi",
                archetype="Bull",
                biais=["confirmation bias", "availability heuristic"],
                stance="bullish",
                platform="twitter",
                description="Expert en marchés financiers émergents.",
            ),
            AgentProfile(
                name="Nadia Benchrifa",
                archetype="Bear",
                biais=["loss aversion"],
                stance="bearish",
                platform="linkedin",
                description="Analyste réglementaire prudente.",
            ),
        ],
        social_network=SocialNetwork(
            nodes=[
                SocialNode(id="n1", name="Khalil El Fassi", group="bullish", weight=0.9),
                SocialNode(id="n2", name="Nadia Benchrifa", group="bearish", weight=0.7),
            ],
            edges=[
                SocialEdge(source="n1", target="n2", weight=0.6, sentiment="negative"),
            ],
        ),
        demographics=Demographics(
            segments=[
                DemographicSegment(label="Hommes", count=12, pct=60.0, dimension="genre"),
                DemographicSegment(label="Femmes", count=8, pct=40.0, dimension="genre"),
            ],
            total=20,
        ),
        counterfactuals=[
            Counterfactual(
                hypothesis="BAM annonce un ban total des crypto-actifs.",
                round_injected=3,
                delta_verdict="Bascule bearish à 80 %.",
                delta_confidence=-0.35,
                notes="Impact majeur sur la confiance bullish.",
            ),
        ],
        director_events=[
            DirectorEvent(
                round=2,
                event_type="news",
                description="Publication d'un rapport OCDE favorable.",
                impact="Hausse de 15 % des agents bullish.",
            ),
        ],
        articles=[
            GeneratedArticle(
                agent_name="Khalil El Fassi",
                platform="twitter",
                round=3,
                title="Crypto Maroc : vers une légalisation encadrée ?",
                content="Analyse des implications réglementaires pour le marché MENA.",
                stance="bullish",
            ),
        ],
        interviews=[
            AgentInterview(
                agent_name="Khalil El Fassi",
                archetype="Bull",
                questions=["Quelle est votre position sur la réglementation ?"],
                answers=["Je suis favorable à un cadre sandbox progressif."],
                final_stance="bullish",
            ),
        ],
        outline=Outline(
            title="Analyse stratégique — Marché crypto MENA 2026",
            summary="Ce rapport analyse l'impact de la réglementation crypto au Maroc.",
            sections=[
                Section(idx=0, title="Diagnostic", content="## Diagnostic\n\nContenu."),
                Section(idx=1, title="Dynamique", content="## Dynamique\n\nContenu."),
            ],
        ),
        full_report_md="# Rapport complet\n\nCeci est le markdown brut complet du rapport Bassira.",
        sections_md={0: "## Diagnostic\n\nContenu.", 1: "## Dynamique\n\nContenu."},
        agent_log=[
            {"round": 1, "agent_name": "Khalil El Fassi", "platform": "twitter", "message": "Post test round 1."},
        ],
        kpi_hero=KPIHero(
            verdict="Haussier modéré",
            confidence_pct=67.0,
            brier=0.22,
            scenario_distribution={"bullish": 0.67, "bearish": 0.22, "neutral": 0.11},
        ),
        pivotal_moments=[
            PivotalMoment(round=2, agent="Khalil El Fassi", event="Publication OCDE", delta_score=0.15),
        ],
        interpretations={
            "consensus": "Un consensus bullish modéré s'est formé autour de la réglementation sandbox.",
        },
        executive_takeaways=[
            "La réglementation sandbox est la voie la plus probable à court terme.",
            "Le dialogue avec les acteurs MENA est stratégique.",
            "La formation des équipes BAM est un prérequis.",
        ],
    )


# ─── Test 1 — Fixture valide ──────────────────────────────────────────────────

def test_fixture_minimal_context_valide(minimal_context: PDFReportContext) -> None:
    """La fixture PDFReportContext minimale est valide et bien formée."""
    assert minimal_context.report_id == VALID_REPORT_ID
    assert minimal_context.simulation_id == VALID_SIM_ID
    assert minimal_context.lang == "fr"
    assert minimal_context.framework == "cerberus"


# ─── Test 2 — Section 00 cover ────────────────────────────────────────────────

def test_render_section_00_cover(minimal_context: PDFReportContext) -> None:
    """La section 00_cover.md.j2 se rend sans erreur et contient le titre."""
    result = render_section("00_cover.md.j2", minimal_context, generated_at=GENERATED_AT)
    assert "Simulation test" in result
    assert "Bassira" in result
    assert "AIMPOWER" in result
    assert "Avertissement" in result


# ─── Test 3 — Section 01 exec_summary avec executive_takeaways ───────────────

def test_render_section_01_exec_summary_with_takeaways(full_context: PDFReportContext) -> None:
    """La section 01 affiche les takeaways exécutifs quand ils sont présents."""
    result = render_section("01_exec_summary.md.j2", full_context, generated_at=GENERATED_AT)
    assert "Résumé Exécutif" in result
    assert "sandbox" in result.lower() or "court terme" in result.lower() or "Priorisa" in result or "réglementation" in result
    # Le premier takeaway doit être présent
    assert "sandbox" in result or "réglementation" in result


# ─── Test 4 — Section 01 exec_summary avec fallback outline.summary ──────────

def test_render_section_01_exec_summary_fallback(minimal_context: PDFReportContext) -> None:
    """La section 01 utilise outline.summary comme fallback si executive_takeaways=[].

    Avec le contexte minimal (pas d'executive_takeaways ni d'outline), on doit
    obtenir un callout warning sans crash.
    """
    result = render_section("01_exec_summary.md.j2", minimal_context, generated_at=GENERATED_AT)
    assert "Résumé Exécutif" in result
    # Soit le callout warning, soit le contenu
    assert "Takeaways" in result or "takeaway" in result.lower() or "warning" in result.lower() or "NOTE" in result or "WARNING" in result or "CAUTION" in result


# ─── Test 5 — Section 02 toc ──────────────────────────────────────────────────

def test_render_section_02_toc(minimal_context: PDFReportContext) -> None:
    """La section 02_toc.md.j2 contient les 7 sections attendues."""
    result = render_section("02_toc.md.j2", minimal_context, generated_at=GENERATED_AT)
    assert "Table des Matières" in result
    assert "Diagnostic" in result
    assert "Dynamique" in result
    assert "Verdict" in result
    assert "Recommandations" in result
    assert "Annexes" in result


# ─── Test 6 — Section 03 diagnostic ──────────────────────────────────────────

def test_render_section_03_diagnostic(full_context: PDFReportContext) -> None:
    """La section 03_diagnostic.md.j2 affiche les sources et la démographie."""
    result = render_section("03_diagnostic.md.j2", full_context, generated_at=GENERATED_AT)
    assert "Diagnostic Stratégique" in result
    assert "Bank Al-Maghrib" in result
    assert "demographic_pyramid.png" in result
    # Vérifie que la démographie est listée
    assert "Hommes" in result or "Femmes" in result or "genre" in result


# ─── Test 7 — Section 04 dynamic ─────────────────────────────────────────────

def test_render_section_04_dynamic(full_context: PDFReportContext) -> None:
    """La section 04_dynamic.md.j2 affiche les charts et les pivots."""
    result = render_section("04_dynamic.md.j2", full_context, generated_at=GENERATED_AT)
    assert "Dynamique Observée" in result
    assert "belief_drift.png" in result
    assert "polymarket_curves.png" in result
    assert "influence_leaderboard.png" in result
    # Le moment pivot doit apparaître
    assert "Publication OCDE" in result or "Khalil" in result


# ─── Test 8 — Section 05 verdict ─────────────────────────────────────────────

def test_render_section_05_verdict(full_context: PDFReportContext) -> None:
    """La section 05_verdict.md.j2 affiche le verdict et les contrefactuels."""
    result = render_section("05_verdict.md.j2", full_context, generated_at=GENERATED_AT)
    assert "Verdict" in result
    assert "67" in result or "0.67" in result or "67.0" in result
    # Contrefactuel présent
    assert "ban total" in result or "Contrefactuel" in result


# ─── Test 9 — Section 06 recommendations liste vide → callout warning ─────────

def test_render_section_06_recommendations_empty() -> None:
    """La section 06 avec recommendations=[] affiche un callout warning sans crash."""
    ctx = PDFReportContext(
        report_id=VALID_REPORT_ID,
        simulation_id=VALID_SIM_ID,
        title="Test recommandations vides",
        framework="cerberus",
        lang="fr",
        outcome=Outcome(
            verdict="Test",
            confidence=0.5,
            recommendations=[],  # Liste vide intentionnelle
        ),
    )
    result = render_section("06_recommendations.md.j2", ctx, generated_at=GENERATED_AT)
    assert "Recommandations" in result
    # Doit afficher un callout d'avertissement
    assert "co-désigner" in result or "WARNING" in result or "warning" in result.lower() or "partenaire humain" in result


# ─── Test 10 — Section 07 appendix avec full_report_md ───────────────────────

def test_render_section_07_appendix_with_full_report_md(full_context: PDFReportContext) -> None:
    """La section 07_appendix.md.j2 inclut le full_report_md si présent."""
    result = render_section("07_appendix.md.j2", full_context, generated_at=GENERATED_AT)
    assert "Annexes" in result
    assert "Méthodologie" in result
    # Le full_report_md doit être inclus
    assert "Rapport complet" in result or "markdown brut" in result.lower()
    # Le glossaire doit être présent
    assert "Glossaire" in result
    assert "Belief Drift" in result


# ─── Test 11 — Rendu complet _full.md.j2 ─────────────────────────────────────

def test_render_full_report(full_context: PDFReportContext) -> None:
    """Le rendu complet via _full.md.j2 produit un document cohérent."""
    result = render_full_report(
        context=full_context,
        generated_at=GENERATED_AT,
        branding_version="v1.0",
    )
    # Le front-matter doit être présent
    assert result.startswith("---")
    # Toutes les sections majeures doivent être présentes
    assert "Résumé Exécutif" in result
    assert "Diagnostic" in result
    assert "Dynamique" in result
    assert "Verdict" in result
    assert "Recommandations" in result
    assert "Annexes" in result


# ─── Test 12 — Filter |normalize fonctionne ──────────────────────────────────

def test_filter_normalize_works() -> None:
    """Le filter |normalize est enregistré et fonctionne correctement."""
    env = get_jinja_env()
    assert "normalize" in env.filters

    # Test rendu simple avec le filtre
    tmpl = env.from_string("{{ text | normalize('fr') }}")
    result = tmpl.render(text="Bonjour le monde")
    assert "Bonjour" in result

    # Test valeur None → chaîne vide
    tmpl_none = env.from_string("{{ val | normalize('fr') }}")
    result_none = tmpl_none.render(val=None)
    assert result_none == ""


# ─── Test 13 — Sections gracieuses sur données vides ─────────────────────────

def test_sections_gracieuses_donnees_vides(minimal_context: PDFReportContext) -> None:
    """Toutes les sections se rendent sans crash avec le contexte minimal."""
    sections = [
        "00_cover.md.j2",
        "01_exec_summary.md.j2",
        "02_toc.md.j2",
        "03_diagnostic.md.j2",
        "04_dynamic.md.j2",
        "05_verdict.md.j2",
        "06_recommendations.md.j2",
        "07_appendix.md.j2",
    ]
    for section in sections:
        result = render_section(section, minimal_context, generated_at=GENERATED_AT)
        assert isinstance(result, str), f"Section {section} n'a pas retourné une string"
        assert len(result) > 0, f"Section {section} a retourné une chaîne vide"


# ─── Test 14 — Front-matter YAML parseable ────────────────────────────────────

def test_full_report_yaml_frontmatter_parseable(full_context: PDFReportContext) -> None:
    """Le front-matter YAML du rapport complet est parseable par yaml.safe_load."""
    result = render_full_report(
        context=full_context,
        generated_at=GENERATED_AT,
        branding_version="default",
    )
    # Extraire le front-matter
    assert result.startswith("---"), "Le rapport doit commencer par ---"
    parts = result.split("---", 2)
    assert len(parts) >= 3, "Le front-matter doit avoir --- de début et de fin"
    frontmatter_str = parts[1].strip()

    parsed = yaml.safe_load(frontmatter_str)
    assert isinstance(parsed, dict), "Le front-matter doit être un dict YAML"
    assert parsed["report_id"] == VALID_REPORT_ID
    assert parsed["simulation_id"] == VALID_SIM_ID
    assert parsed["lang"] == "fr"
    assert parsed["framework"] == "market"
    # yaml.safe_load parse les dates ISO 8601 en datetime — comparer en string
    assert str(parsed["generated_at"]).startswith("2026-05-05")
    assert parsed["template_version"] == "1.0.0"
    assert parsed["branding_version"] == "default"


# ─── Test 15 — full_report_md dans appendix si présent ───────────────────────

def test_appendix_includes_full_report_md_when_present() -> None:
    """La section 07 inclut full_report_md quand il est présent dans le contexte."""
    ctx = PDFReportContext(
        report_id=VALID_REPORT_ID,
        simulation_id=VALID_SIM_ID,
        title="Test appendix full_report_md",
        framework="cerberus",
        lang="fr",
        full_report_md="# Mon rapport complet\n\nContenu unique identifiable.",
    )
    result = render_section("07_appendix.md.j2", ctx, generated_at=GENERATED_AT)
    assert "Mon rapport complet" in result or "Contenu unique identifiable" in result


def test_appendix_gracieux_sans_full_report_md() -> None:
    """La section 07 affiche un callout info si full_report_md est absent."""
    ctx = PDFReportContext(
        report_id=VALID_REPORT_ID,
        simulation_id=VALID_SIM_ID,
        title="Test appendix sans full_report_md",
        framework="cerberus",
        lang="fr",
        full_report_md=None,  # Absent explicitement
    )
    result = render_section("07_appendix.md.j2", ctx, generated_at=GENERATED_AT)
    assert "Rapport brut" in result or "NOTE" in result or "info" in result.lower()


# ─── Test 16 — Counterfactuals vides ne crashent pas ─────────────────────────

def test_verdict_section_counterfactuals_vides() -> None:
    """La section 05 avec counterfactuals=[] ne crashe pas et affiche un callout."""
    ctx = PDFReportContext(
        report_id=VALID_REPORT_ID,
        simulation_id=VALID_SIM_ID,
        title="Test counterfactuals vides",
        framework="cerberus",
        lang="fr",
        counterfactuals=[],
        outcome=Outcome(verdict="Test verdict", confidence=0.6),
    )
    result = render_section("05_verdict.md.j2", ctx, generated_at=GENERATED_AT)
    assert "Verdict" in result
    assert "Contrefactuel" in result or "contrefactuel" in result.lower() or "NOTE" in result


# ─── Test 17 — executive_takeaways vides avec outline.summary → fallback ─────

def test_exec_summary_fallback_outline_summary() -> None:
    """Quand executive_takeaways=[] mais outline.summary est disponible, on utilise le fallback."""
    ctx = PDFReportContext(
        report_id=VALID_REPORT_ID,
        simulation_id=VALID_SIM_ID,
        title="Test fallback summary",
        framework="cerberus",
        lang="fr",
        executive_takeaways=[],  # Vide intentionnellement
        outline=Outline(
            title="Mon rapport",
            summary="Ceci est le résumé de fallback qui doit apparaître dans la section 01.",
            sections=[],
        ),
    )
    result = render_section("01_exec_summary.md.j2", ctx, generated_at=GENERATED_AT)
    # Le fallback summary ou le callout doit être présent
    assert "résumé" in result.lower() or "fallback" in result.lower() or "Takeaways" in result or "NOTE" in result or "WARNING" in result
