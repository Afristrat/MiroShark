"""
Tests de qualité de rendu — US-136 Templates fixes.

Couvre :
    1.  Numérotation TOC : 8 sections → | 1 |, | 2 |, ..., | 8 |
    2.  Date FR : ISO → "6 mai 2026" ou "6 May 2026" (Babel)
    3.  Date EN : ISO → "May" et "2026"
    4.  Date AR : ISO → non vide et contient "2026"
    5.  Date sur valeur None → chaîne vide
    6.  Charts data URI dans render_md si charts_factory fourni
    7.  Pas de data URI si pas de charts_factory
    8.  Articles fallback (aucun article) → callout "Aucun article" dans le MD
    9.  Articles présents → titre et contenu présents
    10. Posts critiques fallback (agent_log vide) → callout, pas de table "—"
    11. Posts critiques vides (messages vides) → fallback callout
    12. Profils sans archétype → colonne "Archétype" absente
    13. Profils avec archétype → colonne "Archétype" présente
    14. Profils sans plateforme → colonne "Plateforme" absente
    15. filter |format_date enregistré dans l'env Jinja2
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services.report_pdf.schema import (
    AgentProfile,
    AgentState,
    GeneratedArticle,
    Outline,
    PDFReportContext,
    Round,
    Section,
    Trajectory,
)
from app.services.report_pdf.jinja_env import get_jinja_env, render_section, render_full_report
from app.services.report_pdf.renderer import Renderer


# ─── Constantes ───────────────────────────────────────────────────────────────

VALID_REPORT_ID = "report_aabbccddeeff"
VALID_SIM_ID = "sim_aabbcc112233"
GENERATED_AT_ISO = "2026-05-06T15:07:07.946532+00:00"


# ─── Mock LanguageTool (indisponible en CI) ───────────────────────────────────

@pytest.fixture(autouse=True, scope="module")
def mock_languagetool_unavailable():
    with patch(
        "app.services.text_normalizer.languagetool_client.check",
        return_value=[],
    ), patch(
        "app.services.text_normalizer.lt_check",
        return_value=[],
    ):
        yield


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_ctx(**kwargs) -> PDFReportContext:
    """Fabrique un contexte minimal valide avec surcharge par kwargs."""
    defaults = dict(
        report_id=VALID_REPORT_ID,
        simulation_id=VALID_SIM_ID,
        title="Test US-136",
        framework="cerberus",
        lang="fr",
    )
    defaults.update(kwargs)
    return PDFReportContext(**defaults)


# ─── Test 1 — Numérotation TOC ────────────────────────────────────────────────

def test_toc_numerotation_8_sections() -> None:
    """8 sections doivent être numérotées 1 à 8 dans la table des matières."""
    ctx = _make_ctx(
        outline=Outline(
            title="Test numérotation",
            summary="",
            sections=[
                Section(idx=0, title=f"Section {i}", content="")
                for i in range(8)
            ],
        )
    )
    result = render_section("02_toc.md.j2", ctx, generated_at=GENERATED_AT_ISO)

    # Chaque numéro de 1 à 8 doit apparaître dans une cellule de table
    for expected_num in range(1, 9):
        assert f"| {expected_num} |" in result, (
            f"Numéro {expected_num} absent du TOC. "
            f"Résultat partiel : {result[:500]}"
        )

    # Ne doit pas avoir de | 0 | (index 0-based non corrigé)
    assert "| 0 |" not in result, "Index 0 présent dans le TOC — la numérotation n'est pas corrigée."


def test_toc_sections_idx_all_zero() -> None:
    """Même si tous les idx=0, loop.index doit produire 1,2,3,4."""
    ctx = _make_ctx(
        outline=Outline(
            title="Test idx=0",
            summary="",
            sections=[
                Section(idx=0, title=f"Section {letter}", content="")
                for letter in ["Alpha", "Beta", "Gamma", "Delta"]
            ],
        )
    )
    result = render_section("02_toc.md.j2", ctx, generated_at=GENERATED_AT_ISO)

    # Tous les idx sont 0 mais loop.index doit donner 1,2,3,4
    for expected_num in range(1, 5):
        assert f"| {expected_num} |" in result, (
            f"Numéro {expected_num} absent alors que tous les idx=0. "
            f"Vérifier que loop.index est utilisé à la place de section.idx + 1."
        )


# ─── Test 2 — Filter format_date ──────────────────────────────────────────────

def test_filter_format_date_enregistre() -> None:
    """Le filter |format_date est enregistré dans l'env Jinja2."""
    env = get_jinja_env()
    assert "format_date" in env.filters, "Le filter |format_date n'est pas enregistré dans l'env Jinja2."


def test_format_date_fr_contient_mai_2026() -> None:
    """filter |format_date en langue fr retourne une date avec le mois de mai 2026."""
    from app.services.report_pdf.jinja_env import _format_date_filter

    result = _format_date_filter("2026-05-06T15:07:07.946532+00:00", lang="fr")
    assert result != "", "Le résultat ne doit pas être vide."
    assert "2026" in result, f"'2026' absent dans '{result}'"
    # Babel retourne "6 mai 2026" ; fallback retourne "6 mai 2026"
    assert "mai" in result.lower() or "May" in result, (
        f"Mois de mai absent dans '{result}'"
    )
    assert "6" in result, f"Jour '6' absent dans '{result}'"


def test_format_date_en_contient_may_2026() -> None:
    """filter |format_date en langue en retourne une date avec May et 2026."""
    from app.services.report_pdf.jinja_env import _format_date_filter

    result = _format_date_filter("2026-05-06T15:07:07.946532+00:00", lang="en")
    assert result != "", "Le résultat ne doit pas être vide."
    assert "2026" in result, f"'2026' absent dans '{result}'"
    assert "May" in result or "may" in result.lower(), f"'May' absent dans '{result}'"


def test_format_date_ar_non_vide_avec_2026() -> None:
    """filter |format_date en langue ar retourne une date non vide contenant 2026."""
    from app.services.report_pdf.jinja_env import _format_date_filter

    result = _format_date_filter("2026-05-06T15:07:07.946532+00:00", lang="ar")
    assert result != "", "Le résultat ne doit pas être vide pour lang=ar."
    assert "2026" in result, f"'2026' absent dans '{result}'"


def test_format_date_none_retourne_chaine_vide() -> None:
    """filter |format_date avec valeur None retourne une chaîne vide."""
    from app.services.report_pdf.jinja_env import _format_date_filter

    result = _format_date_filter(None, lang="fr")
    assert result == "", f"Attendu chaîne vide, obtenu : '{result}'"


def test_format_date_dans_template_cover() -> None:
    """La section 00_cover.md.j2 affiche une date lisible (pas l'ISO brut)."""
    ctx = _make_ctx()
    result = render_section("00_cover.md.j2", ctx, generated_at=GENERATED_AT_ISO)
    # La date ISO brute ne doit pas apparaître telle quelle
    assert "2026-05-06T15:07:07.946532+00:00" not in result, (
        "La date ISO brute est encore présente dans le rendu — le filter format_date n'est pas appliqué."
    )
    # La date doit contenir 2026
    assert "2026" in result, "L'année 2026 devrait être présente dans la date formatée."


# ─── Test 3 — Charts data URI ─────────────────────────────────────────────────

def test_render_md_charts_data_uri_si_factory_fourni() -> None:
    """render_md() embarque les charts en data URI si charts_factory est fourni."""
    ctx = _make_ctx(
        trajectory=Trajectory(
            rounds=[
                Round(
                    round_idx=0,
                    agents=[
                        AgentState(agent_id="a0", name="Agent A", stance="bullish", score=0.6),
                    ],
                )
            ]
        )
    )

    # Mock de ChartFactory : chaque méthode retourne 3 bytes PNG fictifs
    _FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50  # PNG magic + padding
    mock_factory = MagicMock()
    for method in ["belief_drift", "polymarket_curves", "demographic_pyramid",
                   "influence_leaderboard", "interaction_network"]:
        getattr(mock_factory, method).return_value = _FAKE_PNG

    renderer = Renderer(context=ctx, charts_factory=mock_factory)
    md = renderer.render_md()

    # Au moins un chart doit être embarqué (belief_drift est dans 04_dynamic.md.j2)
    assert "data:image/png;base64," in md, (
        "Aucun chart embarqué en data URI dans le MD. "
        "Vérifier _embed_charts_md() dans renderer.py."
    )


def test_render_md_pas_de_data_uri_sans_factory() -> None:
    """render_md() sans charts_factory conserve les références .png (non embarquées)."""
    ctx = _make_ctx()
    renderer = Renderer(context=ctx)
    md = renderer.render_md()

    # Sans factory, pas de data URI — les .png restent en placeholder
    assert "data:image/png;base64," not in md, (
        "Des data URIs ont été générés sans charts_factory — comportement inattendu."
    )


# ─── Test 4 — Articles fallback ───────────────────────────────────────────────

def test_articles_fallback_aucun_article() -> None:
    """Section 05 sans articles → callout 'Aucun article' dans le MD."""
    ctx = _make_ctx(articles=[])
    result = render_section("05_verdict.md.j2", ctx, generated_at=GENERATED_AT_ISO)

    assert "Aucun article" in result, (
        "Le callout 'Aucun article' est absent. "
        "Vérifier le bloc {% else %} dans 05_verdict.md.j2."
    )


def test_articles_presents_contenu_visible() -> None:
    """Section 05 avec articles → titre et body présents dans le MD."""
    ctx = _make_ctx(
        articles=[
            GeneratedArticle(
                agent_name="Khalil",
                platform="twitter",
                round=3,
                title="Crypto : vers une légalisation ?",
                content="Analyse des implications réglementaires.",
                stance="bullish",
            )
        ]
    )
    result = render_section("05_verdict.md.j2", ctx, generated_at=GENERATED_AT_ISO)

    assert "Crypto" in result, "Le titre de l'article n'est pas visible."
    assert "Analyse des implications" in result, "Le contenu de l'article n'est pas visible."
    assert "Aucun article" not in result, "Le callout 'Aucun article' ne doit pas apparaître quand des articles existent."


# ─── Test 5 — Posts critiques fallback ────────────────────────────────────────

def test_posts_critiques_fallback_agent_log_vide() -> None:
    """Section 04 avec agent_log=[] → callout posts critiques, pas de table avec '—'."""
    ctx = _make_ctx(agent_log=[])
    result = render_section("04_dynamic.md.j2", ctx, generated_at=GENERATED_AT_ISO)

    # Le callout de fallback doit être présent
    assert "posts publiés" in result.lower() or "NOTE" in result or "actions.jsonl" in result, (
        "Le callout fallback pour posts critiques est absent quand agent_log=[]."
    )


def test_posts_critiques_fallback_messages_vides() -> None:
    """Section 04 avec agent_log contenant uniquement des messages vides → fallback."""
    ctx = _make_ctx(
        agent_log=[
            {"round": 1, "agent_name": "Agent A", "platform": "twitter", "message": ""},
            {"round": 2, "agent_name": "Agent B", "platform": "reddit", "content": ""},
        ]
    )
    result = render_section("04_dynamic.md.j2", ctx, generated_at=GENERATED_AT_ISO)

    # Les lignes "—" dans la table des posts ne doivent pas apparaître
    # Si tous les messages sont vides, on doit tomber sur le fallback
    assert "posts publiés" in result.lower() or "NOTE" in result or "actions.jsonl" in result, (
        "Des messages vides ne doivent pas produire une table de posts — fallback attendu."
    )


# ─── Test 6 — Profils agents colonnes conditionnelles ─────────────────────────

def test_profils_sans_archetype_colonne_absente() -> None:
    """Section 07 avec profils sans archétype → colonne 'Archétype' absente."""
    ctx = _make_ctx(
        agent_profiles=[
            AgentProfile(name="Agent A", archetype="", stance="bullish", platform="twitter"),
            AgentProfile(name="Agent B", archetype="", stance="bearish", platform="reddit"),
        ]
    )
    result = render_section("07_appendix.md.j2", ctx, generated_at=GENERATED_AT_ISO)

    # La colonne Archétype ne doit pas être présente si tous les archétypes sont vides
    assert "Archétype" not in result, (
        "La colonne 'Archétype' est présente alors que tous les archétypes sont vides."
    )


def test_profils_avec_archetype_colonne_presente() -> None:
    """Section 07 avec profils avec archétype → colonne 'Archétype' présente."""
    ctx = _make_ctx(
        agent_profiles=[
            AgentProfile(name="Agent A", archetype="Bull", stance="bullish", platform="twitter"),
            AgentProfile(name="Agent B", archetype="Bear", stance="bearish", platform="reddit"),
        ]
    )
    result = render_section("07_appendix.md.j2", ctx, generated_at=GENERATED_AT_ISO)

    assert "Archétype" in result, (
        "La colonne 'Archétype' est absente alors que des archétypes sont renseignés."
    )
    assert "Bull" in result, "La valeur 'Bull' de l'archétype est absente du rendu."


def test_profils_sans_plateforme_colonne_absente() -> None:
    """Section 07 avec profils sans plateforme → colonne 'Plateforme' absente."""
    ctx = _make_ctx(
        agent_profiles=[
            AgentProfile(name="Agent X", archetype="", stance="bullish", platform=""),
            AgentProfile(name="Agent Y", archetype="", stance="bearish", platform=""),
        ]
    )
    result = render_section("07_appendix.md.j2", ctx, generated_at=GENERATED_AT_ISO)

    assert "Plateforme" not in result, (
        "La colonne 'Plateforme' est présente alors que toutes les plateformes sont vides."
    )
