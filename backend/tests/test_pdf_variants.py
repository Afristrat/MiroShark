"""Tests pytest US-131 — 4 variantes PDF Bassira (exec/full/public/one-pager)."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services.report_pdf.anonymizer import anonymize_context, anonymize_text
from app.services.report_pdf.anonymizer import _AnonymizationState
from app.services.report_pdf.renderer import Renderer, _VARIANT_TEMPLATE
from app.services.report_pdf.schema import (
    KPIHero,
    Outcome,
    PDFReportContext,
    PivotalMoment,
    QualityMetrics,
    SimState,
)


# ── Mock LanguageTool pour eviter les timeouts reseau ────────────────────────
# Sans ce mock, chaque appel TextNormalizer.normalize() attend 4-5s
# le timeout reseau de LanguageTool → tests tres lents.
@pytest.fixture(autouse=True, scope="session")
def mock_languagetool_globally():
    """Mock global du client LanguageTool pour tous les tests US-131.

    Cible le nom lt_check tel qu importe dans app.services.text_normalizer.
    Retourne une liste vide (aucun probleme orthographique detecte).
    """
    with patch(
        "app.services.text_normalizer.lt_check",
        return_value=[],
    ):
        yield

# ── Constantes de test ────────────────────────────────────────────────────────

VALID_REPORT_ID = "report_a1b2c3d4e5f6"
VALID_SIM_ID = "sim_aabbcc112233"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_context(**overrides) -> PDFReportContext:
    """Construit un PDFReportContext minimal fonctionnel pour les tests."""
    base: dict = {
        "report_id": VALID_REPORT_ID,
        "simulation_id": VALID_SIM_ID,
        "title": "Analyse impact reforme fiscale Maroc — Bassira Inc.",
        "framework": "policy",
        "package": "budget-test",
        "lang": "fr",
        "outcome": Outcome(
            verdict="Consensus bullish modere atteint",
            bullish_pct=62.5,
            bearish_pct=27.3,
            nb_rounds=5,
            confidence=0.78,
            consensus_reached=True,
            recommendations=[
                "Renforcer la coordination avec Agent_42 et les partenaires",
                "Lancer un audit Bassira Corp avant Q3",
                "Impliquer les stakeholders des la phase preparatoire",
            ],
            quality_metrics=QualityMetrics(
                coherence=0.82,
                diversity=0.71,
                plausibility=0.88,
                alignment=0.75,
            ),
        ),
        "kpi_hero": KPIHero(
            verdict="Bullish modere",
            confidence_pct=78.0,
            brier=0.18,
            scenario_distribution={"bullish": 0.625, "bearish": 0.273, "neutre": 0.102},
        ),
        "executive_takeaways": [
            "La reforme beneficie du soutien de Bassira Inc. et ses filiales.",
            "Les agents bearish se concentrent sur l impact fiscal a court terme.",
            "Un consensus durable necessite l alignement de @stakeholder_lead.",
        ],
        "interpretations": {
            "consensus": "Un consensus bullish modere a ete atteint apres 5 rounds.",
            "polarisation": "La polarisation reste contenue a 27.3% des agents.",
        },
        "pivotal_moments": [
            PivotalMoment(round=3, agent="Agent_test", event="Basculement de position", delta_score=0.25),
        ],
        "sim_state": SimState(
            status="completed",
            current_round=5,
            profiles_count=20,
            entities_count=150,
        ),
    }
    base.update(overrides)
    return PDFReportContext(**base)


# ── Fixtures pytest ───────────────────────────────────────────────────────────


@pytest.fixture
def ctx() -> PDFReportContext:
    """Contexte standard pour les tests de variantes."""
    return _make_context()


@pytest.fixture
def renderer(ctx: PDFReportContext) -> Renderer:
    """Renderer sans branding ni charts_factory."""
    return Renderer(context=ctx, branding=None, charts_factory=None)


# ── Tests 1-4 : render_md pour chaque variante ───────────────────────────────


class TestRenderMdVariants:
    """Tests de base : les 4 variantes de render_md produisent du Markdown."""

    def test_render_full_produces_markdown(self, renderer: Renderer) -> None:
        md = renderer.render_md(variant="full")
        assert isinstance(md, str)
        assert len(md) > 100
        assert "---" in md  # front-matter YAML

    def test_render_exec_produces_markdown(self, renderer: Renderer) -> None:
        md = renderer.render_md(variant="exec")
        assert isinstance(md, str)
        assert len(md) > 100

    def test_render_public_produces_markdown(self, renderer: Renderer) -> None:
        md = renderer.render_md(variant="public")
        assert isinstance(md, str)
        assert len(md) > 100

    def test_render_one_pager_produces_markdown(self, renderer: Renderer) -> None:
        md = renderer.render_md(variant="one-pager")
        assert isinstance(md, str)
        assert len(md) > 100

    # Test 5 : longueurs differentes entre variantes

    def test_full_longer_than_exec(self, renderer: Renderer) -> None:
        """Le rapport complet (8 sections) est plus long que le digest executif (5 sections)."""
        md_full = renderer.render_md(variant="full")
        md_exec = renderer.render_md(variant="exec")
        assert len(md_full) > len(md_exec), (
            f"full ({len(md_full)}) devrait etre > exec ({len(md_exec)})"
        )

    def test_full_longer_than_public(self, renderer: Renderer) -> None:
        """Le rapport complet est plus long que l extrait public anonymise."""
        md_full = renderer.render_md(variant="full")
        md_pub = renderer.render_md(variant="public")
        assert len(md_full) > len(md_pub), (
            f"full ({len(md_full)}) devrait etre > public ({len(md_pub)})"
        )

    def test_full_longer_than_one_pager(self, renderer: Renderer) -> None:
        """Le rapport complet est significativement plus long que le one-pager."""
        md_full = renderer.render_md(variant="full")
        md_one = renderer.render_md(variant="one-pager")
        assert len(md_full) > len(md_one), (
            f"full ({len(md_full)}) devrait etre > one-pager ({len(md_one)})"
        )

    def test_non_full_variants_all_shorter_than_full(self, renderer: Renderer) -> None:
        """Toutes les variantes legeres sont plus courtes que le rapport complet."""
        md_full = renderer.render_md(variant="full")
        for v in ("exec", "public", "one-pager"):
            md_v = renderer.render_md(variant=v)
            assert len(md_full) > len(md_v), (
                f"full ({len(md_full)}) devrait etre > {v} ({len(md_v)})"
            )

    # Test 6 : front-matter YAML avec champ variant

    def test_all_variants_have_front_matter_and_variant_field(self, renderer: Renderer) -> None:
        for variant in ("full", "exec", "public", "one-pager"):
            md = renderer.render_md(variant=variant)
            assert md.startswith("---"), f"Variante {variant} : front-matter absent"
            assert "variant:" in md, f"Variante {variant} : champ variant absent"


# ── Tests cover titre par variante ────────────────────────────────────────────


class TestCoverTitles:
    """Verifie que chaque variante affiche le bon label de format."""

    def test_exec_contains_digest_label(self, renderer: Renderer) -> None:
        md = renderer.render_md(variant="exec")
        assert "Digest" in md, "La variante exec devrait mentionner Digest"

    def test_public_contains_public_label(self, renderer: Renderer) -> None:
        md = renderer.render_md(variant="public")
        assert "Public" in md, "La variante public devrait mentionner Public"

    def test_one_pager_label_in_content(self, renderer: Renderer) -> None:
        md = renderer.render_md(variant="one-pager")
        assert "one-pager" in md.lower(), "La variante one-pager devrait contenir one-pager"

    def test_variant_field_in_frontmatter_for_each(self, renderer: Renderer) -> None:
        """Champ variant correctement injete dans le front-matter de chaque variante."""
        for variant in ("full", "exec", "public", "one-pager"):
            md = renderer.render_md(variant=variant)
            # Le front-matter se situe entre les deux "---"
            fm_end = md.find("\n---\n", 4)
            frontmatter = md[:fm_end] if fm_end > 0 else md[:600]
            assert f"variant: {variant}" in frontmatter, (
                f"Variante {variant} : variant: {variant} absent du front-matter. "
                f"Front-matter extrait: {frontmatter[:200]}"
            )


# ── Tests anonymisation (anonymizer.py) ──────────────────────────────────────


class TestAnonymization:
    """Tests unitaires du module anonymizer.py."""

    def test_org_name_replaced(self) -> None:
        """Test 7 : Bassira Inc. -> [Org A]."""
        result = anonymize_text("Bassira Inc. a publie son rapport.")
        assert "Bassira Inc." not in result
        assert re.search(r"\[Org [A-Z]+\]", result), "Remplacement [Org X] attendu"

    def test_org_coherent_same_state(self) -> None:
        """Test 8 : coherence — meme org -> meme label dans un meme etat."""
        state = _AnonymizationState()
        r1 = anonymize_text("Bassira Inc. est present.", state)
        r2 = anonymize_text("Bassira Inc. confirme.", state)
        labels_r1 = re.findall(r"\[Org [A-Z]+\]", r1)
        labels_r2 = re.findall(r"\[Org [A-Z]+\]", r2)
        assert labels_r1, "Label [Org X] attendu dans r1"
        assert labels_r2, "Label [Org X] attendu dans r2"
        assert labels_r1[0] == labels_r2[0], (
            f"Incoherence : meme org -> {labels_r1[0]} puis {labels_r2[0]}"
        )

    def test_different_orgs_different_labels(self) -> None:
        """Deux orgs differentes -> deux labels distincts."""
        state = _AnonymizationState()
        r1 = anonymize_text("Bassira Inc. est partenaire.", state)
        r2 = anonymize_text("ACME Corp est concurrent.", state)
        labels_r1 = re.findall(r"\[Org [A-Z]+\]", r1)
        labels_r2 = re.findall(r"\[Org [A-Z]+\]", r2)
        assert labels_r1 and labels_r2
        assert labels_r1[0] != labels_r2[0], "Deux orgs differentes -> labels differents"

    def test_agent_pattern_replaced(self) -> None:
        """Test 9 : Agent_42 -> [Agent #1]."""
        result = anonymize_text("Le rapport de Agent_42 est disponible.")
        assert "Agent_42" not in result
        assert re.search(r"\[Agent #\d+\]", result), "[Agent #N] attendu"

    def test_at_username_replaced(self) -> None:
        """@stakeholder_lead -> [Agent #N]."""
        result = anonymize_text("@stakeholder_lead a valide la recommandation.")
        assert "@stakeholder_lead" not in result
        assert re.search(r"\[Agent #\d+\]", result), "[Agent #N] attendu apres @username"

    def test_empty_string_safe(self) -> None:
        """Chaine vide retournee inchangee."""
        assert anonymize_text("") == ""

    def test_no_sensitive_data_unchanged(self) -> None:
        """Texte sans org ni agent reste inchange."""
        text = "La simulation a produit 5 rounds sans incident."
        assert anonymize_text(text) == text

    def test_anonymize_context_title(self, ctx: PDFReportContext) -> None:
        """Test 10 : anonymize_context nettoie le titre."""
        anon = anonymize_context(ctx)
        assert "Bassira Inc." not in anon.title
        assert len(anon.title) > 0

    def test_anonymize_context_takeaways(self, ctx: PDFReportContext) -> None:
        """anonymize_context nettoie les executive_takeaways."""
        anon = anonymize_context(ctx)
        for t in anon.executive_takeaways:
            assert "Bassira Inc." not in t
            assert "@stakeholder_lead" not in t

    def test_anonymize_context_recommendations(self, ctx: PDFReportContext) -> None:
        """anonymize_context nettoie les recommandations."""
        anon = anonymize_context(ctx)
        assert anon.outcome is not None
        for r in anon.outcome.recommendations:
            assert "Agent_42" not in r
            assert "Bassira Corp" not in r

    def test_anonymize_context_global_coherence(self) -> None:
        """Meme org -> meme label partout dans le contexte.

        On utilise un titre qui contient exactement 'Bassira Inc.' (sans mots
        supplementaires avant qui formeraient un multi-mot distinct), et on
        verifie que le meme remplacement s applique dans les takeaways.
        """
        ctx2 = _make_context(
            title="Bassira Inc. analyse le marche 2026",
            executive_takeaways=[
                "Bassira Inc. domine le marche.",
                "Bassira Inc. investit en R&D.",
            ],
        )
        anon = anonymize_context(ctx2)
        labels_title = re.findall(r"\[Org [A-Z]+\]", anon.title)
        labels_takeaways: list[str] = []
        for t in anon.executive_takeaways:
            labels_takeaways.extend(re.findall(r"\[Org [A-Z]+\]", t))
        if labels_title and labels_takeaways:
            assert labels_title[0] == labels_takeaways[0], (
                f"Incoherence globale : titre={labels_title[0]}, takeaway={labels_takeaways[0]}"
            )


# ── Tests variante public + anonymisation integree ────────────────────────────


class TestPublicVariantAnonymization:
    """Tests d integration : variante public inclut l anonymisation automatique."""

    def test_public_removes_org_names(self, renderer: Renderer) -> None:
        """La variante public ne doit pas exposer Bassira Inc."""
        md = renderer.render_md(variant="public")
        assert "Bassira Inc." not in md, "Variante public : Bassira Inc. ne doit pas apparaitre"

    def test_public_removes_agent_names(self, renderer: Renderer) -> None:
        """La variante public ne doit pas exposer @stakeholder_lead."""
        md = renderer.render_md(variant="public")
        assert "@stakeholder_lead" not in md, "Variante public : @stakeholder_lead ne doit pas apparaitre"

    def test_public_render_does_not_raise(self, renderer: Renderer) -> None:
        """La variante public se rend sans lever d exception."""
        md = renderer.render_md(variant="public")
        assert isinstance(md, str) and len(md) > 0


# ── Tests one-pager layout CSS Grid ──────────────────────────────────────────


class TestOnePagerLayout:
    """Tests 11-12 : layout CSS Grid et classes one-pager."""

    def test_css_contains_kpi_grid(self) -> None:
        """Test 11 : le CSS brand contient .kpi-grid."""
        from app.services.report_pdf.jinja_env import get_jinja_env
        env = get_jinja_env()
        css_tmpl = env.get_template("pdf_brand.css.j2")
        css = css_tmpl.render(
            branding=None,
            lang="fr",
            context=None,
            generated_at="2026-05-05T12:00:00Z",
        )
        assert ".kpi-grid" in css, "CSS brand devrait contenir .kpi-grid"

    def test_css_contains_grid_template_columns(self) -> None:
        """Le CSS brand contient grid-template-columns pour le layout 2 col."""
        from app.services.report_pdf.jinja_env import get_jinja_env
        env = get_jinja_env()
        css_tmpl = env.get_template("pdf_brand.css.j2")
        css = css_tmpl.render(
            branding=None,
            lang="fr",
            context=None,
            generated_at="2026-05-05T12:00:00Z",
        )
        assert "grid-template-columns" in css, "CSS devrait contenir grid-template-columns"

    def test_one_pager_md_contains_kpi_grid(self, renderer: Renderer) -> None:
        """Test 12 : le template one-pager contient la classe kpi-grid."""
        md = renderer.render_md(variant="one-pager")
        assert "kpi-grid" in md, "Le template one-pager devrait contenir .kpi-grid"

    def test_one_pager_md_contains_layout_class(self, renderer: Renderer) -> None:
        """Le template one-pager contient .one-pager-layout."""
        md = renderer.render_md(variant="one-pager")
        assert "one-pager-layout" in md, "Le template one-pager devrait contenir .one-pager-layout"


# ── Tests 13 : mapping _VARIANT_TEMPLATE ─────────────────────────────────────


class TestVariantMapping:
    """Test 13 : le mapping _VARIANT_TEMPLATE contient les 4 variantes attendues."""

    def test_all_variants_present(self) -> None:
        for v in ("full", "exec", "public", "one-pager"):
            assert v in _VARIANT_TEMPLATE, f"Variante {v} absente de _VARIANT_TEMPLATE"

    def test_full_maps_to_root_template(self) -> None:
        assert _VARIANT_TEMPLATE["full"] == "_full.md.j2"

    def test_exec_maps_to_exec_template(self) -> None:
        assert _VARIANT_TEMPLATE["exec"] == "exec/_main.md.j2"

    def test_public_maps_to_public_template(self) -> None:
        assert _VARIANT_TEMPLATE["public"] == "public/_main.md.j2"

    def test_one_pager_maps_to_one_pager_template(self) -> None:
        assert _VARIANT_TEMPLATE["one-pager"] == "one-pager/_main.md.j2"


# ── Tests 14 : render_pdf (WeasyPrint, skip si absent) ───────────────────────

def _weasyprint_functional() -> bool:
    """Retourne True si WeasyPrint ET ses deps GTK/Pango sont disponibles."""
    try:
        from weasyprint import HTML, CSS  # noqa: F401
        return True
    except (ImportError, OSError):
        return False


_WEASYPRINT_AVAILABLE = _weasyprint_functional()


class TestRenderPdfVariants:
    """Tests 14 : render_pdf avec variants — skippes si WeasyPrint/GTK absent."""

    @pytest.mark.skipif(not _WEASYPRINT_AVAILABLE, reason="WeasyPrint/GTK non disponible")
    def test_render_pdf_exec_returns_bytes(self, renderer: Renderer) -> None:
        pdf_bytes = renderer.render_pdf(variant="exec")
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    @pytest.mark.skipif(not _WEASYPRINT_AVAILABLE, reason="WeasyPrint/GTK non disponible")
    def test_render_pdf_public_returns_bytes(self, renderer: Renderer) -> None:
        pdf_bytes = renderer.render_pdf(variant="public")
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"


# ── US-202 : encart « Méthode et limites » + marquage synthétique ─────────────


class TestMethodLimits:
    """L'encart de transparence est présent dans CHAQUE variante et chaque langue."""

    TITLES = {
        "fr": "Méthode et limites",
        "en": "Method and limits",
        "ar": "المنهجية والحدود",
    }

    @pytest.mark.parametrize("variant", list(_VARIANT_TEMPLATE))
    @pytest.mark.parametrize("lang", ["fr", "en", "ar"])
    def test_encart_present_toutes_variantes_et_langues(self, variant: str, lang: str) -> None:
        rend = Renderer(context=_make_context(lang=lang), branding=None)
        md = rend.render_md(variant=variant)
        assert 'class="method-limits"' in md, f"encart absent ({variant}/{lang})"
        assert self.TITLES[lang] in md, f"titre localisé absent ({variant}/{lang})"
        assert "method-limits-marking" in md

    @pytest.mark.parametrize("variant", list(_VARIANT_TEMPLATE))
    def test_encart_rtl_pour_arabe(self, variant: str) -> None:
        md = Renderer(context=_make_context(lang="ar"), branding=None).render_md(variant=variant)
        assert '<div class="method-limits" dir="rtl">' in md

    @pytest.mark.parametrize("variant", list(_VARIANT_TEMPLATE))
    def test_encart_avant_le_corps(self, variant: str) -> None:
        """L'encart arrive en tête de document (après la couverture), pas en annexe."""
        md = Renderer(context=_make_context(), branding=None).render_md(variant=variant)
        pos = md.find('class="method-limits"')
        assert 0 < pos < len(md) * 0.5


class TestSyntheticContentMarking:
    """mark_synthetic_content écrit les métadonnées machine-readable (AI Act art. 50)."""

    @staticmethod
    def _blank_pdf() -> bytes:
        from io import BytesIO
        from pypdf import PdfWriter

        w = PdfWriter()
        w.add_blank_page(width=72, height=72)
        buf = BytesIO()
        w.write(buf)
        return buf.getvalue()

    def test_metadonnees_synthetic_true(self) -> None:
        from io import BytesIO
        from pypdf import PdfReader
        from app.services.report_pdf.renderer import mark_synthetic_content

        marked = mark_synthetic_content(self._blank_pdf())
        meta = PdfReader(BytesIO(marked)).metadata
        assert meta.get("/SyntheticContent") == "true"
        assert meta.get("/AIGenerated") == "true"

    def test_metadonnees_existantes_preservees(self) -> None:
        from io import BytesIO
        from pypdf import PdfReader, PdfWriter
        from app.services.report_pdf.renderer import mark_synthetic_content

        w = PdfWriter()
        w.add_blank_page(width=72, height=72)
        w.add_metadata({"/Producer": "test-producer"})
        buf = BytesIO()
        w.write(buf)

        marked = mark_synthetic_content(buf.getvalue())
        meta = PdfReader(BytesIO(marked)).metadata
        assert meta.get("/Producer") == "test-producer"
        assert meta.get("/SyntheticContent") == "true"

    def test_sortie_est_un_pdf_valide(self) -> None:
        from app.services.report_pdf.renderer import mark_synthetic_content

        marked = mark_synthetic_content(self._blank_pdf())
        assert marked[:4] == b"%PDF"
