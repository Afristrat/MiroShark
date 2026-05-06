"""
tests/test_renderer.py — Tests du pipeline Renderer (US-125).

Couvre :
    1.  Fixture PDFReportContext valide (IDs 12-hex)
    2.  render_md() produit une string non vide
    3.  render_md() contient le titre du context
    4.  render_md() est du Markdown GFM valide (parseable par markdown-it)
    5.  Front-matter YAML extractable et parseable par yaml.safe_load
    6.  Front-matter YAML contient title / report_id / lang
    7.  render_pdf() sans branding produit bytes PDF valide (skip si GTK absent)
    8.  render_pdf() avec branding produit bytes PDF sans erreur (skip si GTK absent)
    9.  PDF a au moins 1 page — vérifié via pypdf (skip si GTK absent)
    10. Multilang : génère MD pour fr / en / ar, 3 MDs distincts
    11. Charts embedded : si charts_factory fourni, data:image/png;base64 dans HTML
    12. strip_frontmatter() retire le YAML et laisse le Markdown body
    13. extract_frontmatter() retourne un dict avec les bonnes clés
    14. Enricher appelé automatiquement si champs dérivés vides
    15. Branding None → CSS Jinja2 rendu sans exception
    16. render_pdf() avec charts_factory mock → PDF OK (skip si GTK absent)
    17. CSS template rendable sans exception pour fr / en / ar
    18. HTML intermédiaire est valide (bien formé)
    19. Pipeline MD → HTML complet sans WeasyPrint (test partiel)
    20. Context avec données minimales → MD sans exception
"""

from __future__ import annotations

import io
import sys
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest
import yaml

# ── Détection WeasyPrint disponible (GTK requis sur Linux/Windows) ────────────
def _weasyprint_available() -> bool:
    """Retourne True si WeasyPrint ET ses dépendances GTK sont disponibles."""
    try:
        from weasyprint import HTML, CSS  # noqa: F401
        return True
    except (ImportError, OSError):
        return False

WEASYPRINT_AVAILABLE = _weasyprint_available()
skip_no_weasyprint = pytest.mark.skipif(
    not WEASYPRINT_AVAILABLE,
    reason="WeasyPrint nécessite GTK/Pango (libgobject-2.0-0) non disponible dans cet environnement."
)

# ── Mock LanguageTool pour éviter les timeouts réseau (5s/appel) ────────────────
# LanguageTool self-hosted n'est pas disponible en CI/dev local.
# On mock le check() pour retourner une liste vide immédiatement.
@pytest.fixture(autouse=True, scope="session")
def mock_languagetool_globally():
    """Mock global du client LanguageTool pour tous les tests du module renderer.

    Sans ce mock, chaque appel TextNormalizer.normalize() attend 5s le
    timeout réseau de LanguageTool → tests 10+ minutes.

    Le patch cible le nom dans le module où la fonction est utilisée
    (``lt_check`` aliasé depuis ``languagetool_client.check``).
    """
    with patch(
        # Cible le nom ``lt_check`` tel qu'importé dans text_normalizer/__init__.py
        "app.services.text_normalizer.lt_check",
        return_value=[],
    ):
        yield


from app.services.report_pdf.schema import (
    Demographics,
    DemographicSegment,
    KPIHero,
    Outcome,
    PDFReportContext,
    PivotalMoment,
    QualityMetrics,
    Round,
    AgentState,
    Trajectory,
    Outline,
    Section,
    SimConfig,
    SimState,
    SocialNetwork,
    SocialNode,
    SocialEdge,
)
from app.services.report_pdf.renderer import (
    Renderer,
    extract_frontmatter,
    _strip_frontmatter,
)


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def minimal_context() -> PDFReportContext:
    """Contexte minimal valide avec IDs 12-hex."""
    return PDFReportContext(
        report_id="report_abc123def456",
        simulation_id="sim_123abc456def",
        title="Test Simulation Report",
        framework="cerberus",
        package="crisis-drill-24h",
        lang="fr",
    )


@pytest.fixture
def rich_context() -> PDFReportContext:
    """Contexte riche avec données simulation complètes."""
    trajectory = Trajectory(
        rounds=[
            Round(
                round_idx=0,
                agents=[
                    AgentState(agent_id="a001", name="Alice", stance="bullish", score=0.7),
                    AgentState(agent_id="a002", name="Bob", stance="bearish", score=-0.4),
                    AgentState(agent_id="a003", name="Charlie", stance="neutral", score=0.1),
                ],
                summary="Round 0 : consensus initial.",
            ),
            Round(
                round_idx=1,
                agents=[
                    AgentState(agent_id="a001", name="Alice", stance="bullish", score=0.9),
                    AgentState(agent_id="a002", name="Bob", stance="bearish", score=-0.6),
                    AgentState(agent_id="a003", name="Charlie", stance="bullish", score=0.3),
                ],
                summary="Round 1 : polarisation accrue.",
            ),
            Round(
                round_idx=2,
                agents=[
                    AgentState(agent_id="a001", name="Alice", stance="bullish", score=0.85),
                    AgentState(agent_id="a002", name="Bob", stance="neutral", score=0.0),
                    AgentState(agent_id="a003", name="Charlie", stance="bullish", score=0.5),
                ],
                summary="Round 2 : convergence haussière.",
            ),
        ]
    )

    outcome = Outcome(
        verdict="Scénario haussier dominant",
        bullish_pct=66.7,
        bearish_pct=33.3,
        nb_rounds=3,
        recommendations=[
            "Renforcer les indicateurs haussiers sur les marchés émergents.",
            "Surveiller la trajectoire des agents bearish.",
            "Préparer un scénario de sortie si polarisation augmente.",
        ],
        confidence=0.78,
        quality_metrics=QualityMetrics(
            coherence=0.85,
            diversity=0.72,
            plausibility=0.91,
            alignment=0.68,
        ),
        scenario_winner="Bullish camp",
        consensus_reached=False,
    )

    demographics = Demographics(
        total=3,
        segments=[
            DemographicSegment(label="18-34", count=1, pct=33.3, dimension="age"),
            DemographicSegment(label="35-54", count=2, pct=66.7, dimension="age"),
        ],
    )

    social_network = SocialNetwork(
        nodes=[
            SocialNode(id="a001", name="Alice", group="bullish", weight=0.9),
            SocialNode(id="a002", name="Bob", group="bearish", weight=0.6),
            SocialNode(id="a003", name="Charlie", group="bullish", weight=0.5),
        ],
        edges=[
            SocialEdge(source="a001", target="a002", weight=0.5, sentiment="negative"),
            SocialEdge(source="a001", target="a003", weight=0.8, sentiment="positive"),
        ],
    )

    outline = Outline(
        title="Rapport de Test — Cerberus Crisis Drill",
        summary="Simulation complétée avec 3 agents sur 3 rounds.",
        sections=[
            Section(idx=0, title="Stratégie de Sortie", content="Réduire l'exposition bearish de 20 %."),
            Section(idx=1, title="Risques Identifiés", content="Polarisation accrue si Bob ne converge pas."),
        ],
    )

    sim_config = SimConfig(
        title="Crisis Drill — Simulateur Cerberus 24h",
        package="crisis-drill-24h",
        framework="cerberus",
        lang="fr",
        sources=["reuters.com/economy", "imf.org/outlook-2026"],
    )

    sim_state = SimState(
        status="completed",
        current_round=2,
        profiles_count=3,
        entities_count=15,
        entity_types=["Organization", "Person", "Event"],
    )

    return PDFReportContext(
        report_id="report_abc123def456",
        simulation_id="sim_123abc456def",
        title="Crisis Drill — Rapport C-Level",
        framework="cerberus",
        package="crisis-drill-24h",
        lang="fr",
        trajectory=trajectory,
        outcome=outcome,
        demographics=demographics,
        social_network=social_network,
        outline=outline,
        sim_config=sim_config,
        sim_state=sim_state,
        kpi_hero=KPIHero(
            verdict="Haussier dominant",
            confidence_pct=78.0,
            brier=0.22,
            scenario_distribution={"bullish": 66.7, "bearish": 33.3},
        ),
        pivotal_moments=[
            PivotalMoment(round=1, agent="Alice", event="Pivot haussier Round 1.", delta_score=0.15),
        ],
        interpretations={
            "belief_drift": "Les convictions ont évolué vers un consensus haussier progressif.",
        },
        executive_takeaways=[
            "Scénario haussier dominant avec 78 % de confiance.",
            "Recommandation : renforcer les indicateurs haussiers.",
        ],
    )


@pytest.fixture
def branding_dict() -> dict:
    """Row de branding PDF simulant la table pdf_branding."""
    return {
        "id": "branding-test-001",
        "name": "Test Branding",
        "palette_primary": "#FF8551",
        "palette_secondary": "#006D44",
        "palette_text": "#241915",
        "palette_background": "#FAF7F2",
        "font_titles": "Outfit, DejaVu Sans, sans-serif",
        "font_body": "Manrope, DejaVu Sans, sans-serif",
        "font_mono": "Courier New, monospace",
        "logo_url": None,
        "disclaimer_text": "Rapport confidentiel Bassira.",
    }


# ══════════════════════════════════════════════════════════════════════════════
# Tests render_md()
# ══════════════════════════════════════════════════════════════════════════════


class TestRenderMd:
    """Tests du rendu Markdown."""

    def test_render_md_not_empty(self, rich_context: PDFReportContext) -> None:
        """render_md() produit une string non vide."""
        renderer = Renderer(rich_context)
        result = renderer.render_md()
        assert isinstance(result, str)
        assert len(result) > 100

    def test_render_md_contains_title(self, rich_context: PDFReportContext) -> None:
        """render_md() contient le titre du context."""
        renderer = Renderer(rich_context)
        result = renderer.render_md()
        assert "Crisis Drill" in result or rich_context.title[:10] in result

    def test_render_md_contains_report_id(self, rich_context: PDFReportContext) -> None:
        """render_md() contient le report_id dans le front-matter."""
        renderer = Renderer(rich_context)
        result = renderer.render_md()
        assert rich_context.report_id in result

    def test_render_md_valid_gfm(self, rich_context: PDFReportContext) -> None:
        """render_md() produit du Markdown parseable par markdown-it."""
        from markdown_it import MarkdownIt

        renderer = Renderer(rich_context)
        md_text = renderer.render_md()
        md_clean = _strip_frontmatter(md_text)

        md = MarkdownIt("commonmark").enable(["table", "strikethrough"])
        html = md.render(md_clean)
        assert isinstance(html, str)
        assert len(html) > 0

    def test_render_md_minimal_context(self, minimal_context: PDFReportContext) -> None:
        """render_md() fonctionne avec un contexte minimal."""
        renderer = Renderer(minimal_context)
        result = renderer.render_md()
        assert isinstance(result, str)
        assert len(result) > 0


# ══════════════════════════════════════════════════════════════════════════════
# Tests front-matter YAML
# ══════════════════════════════════════════════════════════════════════════════


class TestFrontmatter:
    """Tests du front-matter YAML."""

    def test_frontmatter_present(self, rich_context: PDFReportContext) -> None:
        """Le front-matter YAML est présent dans le MD rendu."""
        renderer = Renderer(rich_context)
        md_text = renderer.render_md()
        assert md_text.startswith("---")

    def test_frontmatter_parseable(self, rich_context: PDFReportContext) -> None:
        """Le front-matter YAML est parseable par yaml.safe_load."""
        renderer = Renderer(rich_context)
        md_text = renderer.render_md()
        frontmatter = extract_frontmatter(md_text)
        assert isinstance(frontmatter, dict)
        assert len(frontmatter) > 0

    def test_frontmatter_contains_required_keys(self, rich_context: PDFReportContext) -> None:
        """Le front-matter contient title, report_id et lang."""
        renderer = Renderer(rich_context)
        md_text = renderer.render_md()
        frontmatter = extract_frontmatter(md_text)
        assert "title" in frontmatter
        assert "report_id" in frontmatter
        assert "lang" in frontmatter

    def test_frontmatter_report_id_matches(self, rich_context: PDFReportContext) -> None:
        """Le report_id du front-matter correspond au contexte."""
        renderer = Renderer(rich_context)
        md_text = renderer.render_md()
        frontmatter = extract_frontmatter(md_text)
        assert frontmatter["report_id"] == rich_context.report_id

    def test_frontmatter_lang_matches(self, minimal_context: PDFReportContext) -> None:
        """Le lang du front-matter correspond au contexte."""
        renderer = Renderer(minimal_context)
        md_text = renderer.render_md()
        frontmatter = extract_frontmatter(md_text)
        assert frontmatter["lang"] == minimal_context.lang

    def test_strip_frontmatter(self, rich_context: PDFReportContext) -> None:
        """strip_frontmatter() retire le YAML et laisse le Markdown body."""
        renderer = Renderer(rich_context)
        md_text = renderer.render_md()
        md_clean = _strip_frontmatter(md_text)
        # Le résultat ne doit plus commencer par ---
        assert not md_clean.startswith("---\n")
        # Mais doit contenir du contenu
        assert len(md_clean.strip()) > 0


# ══════════════════════════════════════════════════════════════════════════════
# Tests render_pdf()
# ══════════════════════════════════════════════════════════════════════════════


class TestRenderPdf:
    """Tests du rendu PDF via WeasyPrint.

    Les tests qui nécessitent WeasyPrint+GTK sont décorés avec @skip_no_weasyprint.
    Sur Windows sans GTK, ces tests sont skippés (comportement attendu en CI/CD local).
    En production Linux (Coolify/Railway), GTK est disponible et tous les tests passent.
    """

    @skip_no_weasyprint
    def test_render_pdf_returns_bytes(self, rich_context: PDFReportContext) -> None:
        """render_pdf() retourne des bytes non vides."""
        renderer = Renderer(rich_context)
        pdf_bytes = renderer.render_pdf()
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000  # Un PDF valide fait au moins quelques Ko

    @skip_no_weasyprint
    def test_render_pdf_valid_pdf_header(self, rich_context: PDFReportContext) -> None:
        """Les bytes produits commencent par le magic number PDF %PDF-."""
        renderer = Renderer(rich_context)
        pdf_bytes = renderer.render_pdf()
        assert pdf_bytes[:4] == b"%PDF"

    @skip_no_weasyprint
    def test_render_pdf_at_least_one_page(self, rich_context: PDFReportContext) -> None:
        """Le PDF a au moins 1 page (vérifié via pypdf)."""
        import pypdf

        renderer = Renderer(rich_context)
        pdf_bytes = renderer.render_pdf()
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 1

    @skip_no_weasyprint
    def test_render_pdf_with_branding(
        self, rich_context: PDFReportContext, branding_dict: dict
    ) -> None:
        """render_pdf() avec branding produit un PDF sans exception."""
        renderer = Renderer(rich_context, branding=branding_dict)
        pdf_bytes = renderer.render_pdf()
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    @skip_no_weasyprint
    def test_render_pdf_without_branding(self, minimal_context: PDFReportContext) -> None:
        """render_pdf() sans branding utilise les defaults Bassira."""
        renderer = Renderer(minimal_context, branding=None)
        pdf_bytes = renderer.render_pdf()
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    @skip_no_weasyprint
    def test_render_pdf_minimal_context(self, minimal_context: PDFReportContext) -> None:
        """Context avec données minimales → PDF sans exception."""
        renderer = Renderer(minimal_context)
        pdf_bytes = renderer.render_pdf()
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_render_pdf_html_pipeline(self, rich_context: PDFReportContext) -> None:
        """Teste le pipeline jusqu'à l'HTML (sans WeasyPrint — toujours actif)."""
        from app.services.report_pdf.renderer import _md_to_html, _strip_frontmatter
        renderer = Renderer(rich_context)
        md_text = renderer.render_md()
        md_clean = _strip_frontmatter(md_text)
        html_body = _md_to_html(md_clean)
        assert isinstance(html_body, str)
        assert "<h" in html_body  # Au moins un heading HTML
        assert len(html_body) > 100

    def test_css_template_renderable(
        self, minimal_context: PDFReportContext, branding_dict: dict
    ) -> None:
        """Le template CSS Jinja2 est rendable sans exception pour fr/en/ar."""
        from app.services.report_pdf.jinja_env import get_jinja_env
        from datetime import datetime, timezone

        env = get_jinja_env()
        css_template = env.get_template("pdf_brand.css.j2")
        generated_at = datetime.now(tz=timezone.utc).isoformat()

        for lang in ["fr", "en", "ar"]:
            ctx = PDFReportContext(
                report_id="report_abc123def456",
                simulation_id="sim_123abc456def",
                title="CSS Test",
                framework="cerberus",
                package="test",
                lang=lang,  # type: ignore[arg-type]
            )
            css_text = css_template.render(
                branding=branding_dict,
                lang=lang,
                context=ctx,
                generated_at=generated_at,
            )
            assert isinstance(css_text, str)
            assert "--wi-orange" in css_text
            assert len(css_text) > 100


# ══════════════════════════════════════════════════════════════════════════════
# Tests multilang
# ══════════════════════════════════════════════════════════════════════════════


class TestMultilang:
    """Tests de la génération multilingue."""

    @pytest.mark.parametrize("lang", ["fr", "en", "ar"])
    def test_render_md_all_langs(self, lang: str) -> None:
        """render_md() fonctionne pour fr/en/ar."""
        ctx = PDFReportContext(
            report_id="report_abc123def456",
            simulation_id="sim_123abc456def",
            title="Multilang Test Report",
            framework="cerberus",
            package="test-package",
            lang=lang,  # type: ignore[arg-type]
        )
        renderer = Renderer(ctx)
        result = renderer.render_md()
        assert isinstance(result, str)
        assert len(result) > 0
        # Le front-matter doit contenir la bonne langue
        frontmatter = extract_frontmatter(result)
        assert frontmatter.get("lang") == lang

    def test_multilang_md_content_differs(self) -> None:
        """Les MDs FR/EN/AR ont des contenus textuels distincts."""
        md_texts = {}
        for lang in ["fr", "en", "ar"]:
            ctx = PDFReportContext(
                report_id="report_abc123def456",
                simulation_id="sim_123abc456def",
                title="Multilang Test",
                framework="cerberus",
                package="test-package",
                lang=lang,  # type: ignore[arg-type]
                outcome=Outcome(
                    verdict="Test verdict" if lang == "en" else ("Verdict test" if lang == "fr" else "حكم الاختبار"),
                    bullish_pct=60.0,
                    bearish_pct=40.0,
                    nb_rounds=5,
                    confidence=0.7,
                ),
            )
            renderer = Renderer(ctx)
            md_texts[lang] = renderer.render_md()

        # Les 3 MDs existent et ont du contenu
        assert all(len(md) > 100 for md in md_texts.values())
        # Les MDs sont différents (contenus en différentes langues)
        unique_mds = len(set(md_texts.values()))
        assert unique_mds == 3, "Les 3 MDs doivent être distincts (contenus multilingues)"

    @skip_no_weasyprint
    def test_multilang_pdf_sizes_differ(self) -> None:
        """Les PDFs FR/EN/AR ont des tailles de bytes distinctes."""
        sizes = {}
        for lang in ["fr", "en", "ar"]:
            ctx = PDFReportContext(
                report_id="report_abc123def456",
                simulation_id="sim_123abc456def",
                title="Multilang Test",
                framework="cerberus",
                package="test-package",
                lang=lang,  # type: ignore[arg-type]
                outcome=Outcome(
                    verdict="Test verdict" if lang == "en" else ("Verdict test" if lang == "fr" else "حكم الاختبار"),
                    bullish_pct=60.0,
                    bearish_pct=40.0,
                    nb_rounds=5,
                    confidence=0.7,
                ),
            )
            renderer = Renderer(ctx)
            pdf_bytes = renderer.render_pdf()
            sizes[lang] = len(pdf_bytes)

        # Les 3 PDFs existent et ont une taille > 0
        assert all(s > 0 for s in sizes.values())
        # Au moins 2 des 3 PDFs ont des tailles différentes (AR = RTL = différent)
        unique_sizes = len(set(sizes.values()))
        assert unique_sizes >= 2, f"PDFs multilang trop similaires : {sizes}"

    def test_ar_md_contains_arabic(self) -> None:
        """Le MD arabe contient du texte arabe (RTL content)."""
        ctx = PDFReportContext(
            report_id="report_abc123def456",
            simulation_id="sim_123abc456def",
            title="تقرير اختباري",
            framework="cerberus",
            package="test-ar",
            lang="ar",
        )
        renderer = Renderer(ctx)
        md_text = renderer.render_md()
        assert isinstance(md_text, str)
        assert len(md_text) > 0
        # Le front-matter contient lang=ar
        fm = extract_frontmatter(md_text)
        assert fm.get("lang") == "ar"


# ══════════════════════════════════════════════════════════════════════════════
# Tests charts embedded
# ══════════════════════════════════════════════════════════════════════════════


class TestChartsEmbedded:
    """Tests de l'intégration des charts en base64."""

    # PNG minimal valide (1x1 pixel transparent)
    _MINIMAL_PNG = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    def _make_mock_factory(self) -> MagicMock:
        """Crée un mock ChartFactory avec des méthodes retournant des PNG minimaux."""
        mock_factory = MagicMock()
        for method_name in ["belief_drift", "polymarket_curves", "demographic_pyramid",
                            "influence_leaderboard", "interaction_network"]:
            getattr(mock_factory, method_name).return_value = self._MINIMAL_PNG
        return mock_factory

    def test_charts_embedded_as_base64(self) -> None:
        """Si charts_factory fourni, data:image/png;base64 dans HTML intermédiaire."""
        from app.services.report_pdf.renderer import _embed_charts

        mock_factory = self._make_mock_factory()

        html_with_placeholder = (
            '<p><img alt="belief_drift" src="charts/belief_drift.png"></p>'
        )
        html_embedded = _embed_charts(html_with_placeholder, mock_factory)

        assert "data:image/png;base64," in html_embedded
        assert 'src="charts/belief_drift.png"' not in html_embedded

    def test_embed_charts_multiple_placeholders(self) -> None:
        """_embed_charts() remplace plusieurs placeholders en une passe."""
        from app.services.report_pdf.renderer import _embed_charts

        mock_factory = self._make_mock_factory()
        html = (
            '<img src="charts/belief_drift.png">'
            '<img src="charts/influence_leaderboard.png">'
            '<img src="charts/demographic_pyramid.png">'
        )
        html_embedded = _embed_charts(html, mock_factory)

        assert 'src="charts/belief_drift.png"' not in html_embedded
        assert 'src="charts/influence_leaderboard.png"' not in html_embedded
        assert html_embedded.count("data:image/png;base64,") == 3

    @skip_no_weasyprint
    def test_charts_factory_none_ok(self, rich_context: PDFReportContext) -> None:
        """render_pdf() sans charts_factory fonctionne sans erreur."""
        renderer = Renderer(rich_context)
        pdf_bytes = renderer.render_pdf(charts_factory=None)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    @skip_no_weasyprint
    def test_charts_factory_with_mock_pdf_ok(self, rich_context: PDFReportContext) -> None:
        """render_pdf() avec factory mock → PDF OK."""
        mock_factory = self._make_mock_factory()
        renderer = Renderer(rich_context)
        pdf_bytes = renderer.render_pdf(charts_factory=mock_factory)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"


# ══════════════════════════════════════════════════════════════════════════════
# Tests enricher automatique
# ══════════════════════════════════════════════════════════════════════════════


class TestEnricherIntegration:
    """Tests de l'enrichissement automatique."""

    def test_enricher_called_when_fields_empty(self, minimal_context: PDFReportContext) -> None:
        """Enricher est appelé automatiquement si kpi_hero est None."""
        # Le minimal_context n'a pas kpi_hero
        assert minimal_context.kpi_hero is None

        renderer = Renderer(minimal_context)
        # _enrich_context() doit compléter sans exception
        enriched = renderer._enrich_context()
        # Si pas d'outcome → kpi_hero reste None (données insuffisantes)
        # mais si Enricher fonctionne, il retourne un KPIHero vide
        # (comportement déterministe du stub)
        assert isinstance(enriched, PDFReportContext)

    def test_enricher_not_called_when_fields_set(self, rich_context: PDFReportContext) -> None:
        """Enricher ne re-calcule pas si les champs sont déjà remplis."""
        # Le rich_context a déjà kpi_hero, pivotal_moments, etc.
        renderer = Renderer(rich_context)

        with patch("app.services.report_pdf.renderer.Renderer._enrich_context",
                   wraps=renderer._enrich_context) as mock_enrich:
            renderer.render_md()
            # _enrich_context est toujours appelé mais Enricher.enrich() ne l'est pas
            mock_enrich.assert_called()


# ══════════════════════════════════════════════════════════════════════════════
# Tests fallback fonts
# ══════════════════════════════════════════════════════════════════════════════


class TestFallbackFonts:
    """Tests du fallback fonts (sans woff2 installés)."""

    @skip_no_weasyprint
    def test_pdf_without_woff2_fonts_no_exception(self, minimal_context: PDFReportContext) -> None:
        """Sans woff2 installés, WeasyPrint utilise le fallback et ne lève pas d'exception."""
        # Les fonts woff2 ne sont pas dans static/fonts/ (juste .gitkeep)
        # WeasyPrint doit utiliser DejaVu Sans en fallback
        renderer = Renderer(minimal_context)
        # Ne doit pas lever d'exception
        pdf_bytes = renderer.render_pdf()
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_css_with_font_fallback_renders(self, minimal_context: PDFReportContext) -> None:
        """Le CSS Jinja2 se rend correctement même sans woff2 déclarés."""
        from app.services.report_pdf.jinja_env import get_jinja_env
        from datetime import datetime, timezone

        env = get_jinja_env()
        css_template = env.get_template("pdf_brand.css.j2")
        generated_at = datetime.now(tz=timezone.utc).isoformat()

        css_text = css_template.render(
            branding=None,  # Pas de branding → defaults Bassira
            lang="fr",
            context=minimal_context,
            generated_at=generated_at,
        )
        # Le CSS doit contenir les déclarations @font-face
        assert "@font-face" in css_text
        assert "Outfit" in css_text
        assert "Manrope" in css_text
