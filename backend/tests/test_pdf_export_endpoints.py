"""
Tests pytest pour US-133 — Câblage endpoints user export PDF/MD au nouveau Renderer.

Vérifie que les endpoints /export-pdf et /export-md délèguent bien au
pipeline PDFContextLoader → Enricher → Renderer (plus de code ReportLab).

Couverture (10 tests) :
    01. _build_pdf() retourne des bytes commençant par %PDF- (magic bytes PDF)
    02. _build_pdf() retourne > 1 kB (PDF non trivial)
    03. _build_markdown() retourne une string non vide
    04. _build_markdown() contient un front-matter YAML délimité par ---
    05. Endpoint POST /export-pdf → 200 + Content-Type application/pdf
    06. Endpoint GET /export-md → 200 + Content-Type text/markdown
    07. Endpoint POST /export-pdf avec simulation_id invalide → 400 INVALID_SIMULATION_ID
    08. Endpoint POST /export-pdf simulation absente → 404 SIMULATION_NOT_FOUND
    09. Fallback sans report_id : PDFContextLoader sans report ne crash pas
    10. graph_image_b64 ignoré gracefully (pas d'erreur, log info seulement)

Mocks :
    - LLM Enricher : MagicMock (évite appels réseau LLM)
    - LanguageTool : MagicMock (évite timeouts réseau 5 s)
    - WeasyPrint : contourné via skip si GTK absent (même pattern que test_renderer.py)
    - SimulationManager : patché pour éviter accès disque/Neo4j

Note : Les tests 01, 02, 05, 06, 09, 10 nécessitent WeasyPrint.
Ils sont skippés si GTK n'est pas disponible (Windows sans GTK).
Les tests 03, 04, 07, 08 ne nécessitent pas WeasyPrint.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Ajout backend/ au sys.path ────────────────────────────────────────────────
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# ── Fixtures sim valides ──────────────────────────────────────────────────────
_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_VALID_SIM_ID = "sim_aabbcc112233"
_VALID_REP_ID = "report_a1b2c3d4e5f6"
_FIXTURES_REP_DIR = _FIXTURES_DIR  # base dir pour les rapports


# ── Détection WeasyPrint disponible ───────────────────────────────────────────

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
    reason="WeasyPrint nécessite GTK/Pango non disponible dans cet environnement.",
)


# ── Mock LanguageTool global (évite timeouts réseau 5 s) ─────────────────────

@pytest.fixture(autouse=True, scope="session")
def mock_languagetool_globally():
    """Mock global du client LanguageTool pour éviter les timeouts réseau.

    Le patch cible lt_check tel qu'importé dans text_normalizer/__init__.py
    (même pattern que test_renderer.py).
    """
    with patch(
        "app.services.text_normalizer.lt_check",
        return_value=[],
    ):
        yield


# ── Mock LLM global (évite appels réseau LLM dans Enricher) ──────────────────

@pytest.fixture(autouse=True)
def mock_llm_client():
    """Mock du LLM client pour Enricher — retourne des fallbacks immédiats."""
    mock_llm = MagicMock()
    mock_llm.chat.return_value = "Analyse simulée pour les tests."
    with patch(
        "app.services.report_pdf.enricher._safe_create_llm_client",
        return_value=mock_llm,
    ):
        yield mock_llm


# ── Fake SimulationState ──────────────────────────────────────────────────────

class _FakeSimState:
    simulation_id = _VALID_SIM_ID
    project_id = "proj_test001"
    graph_id = "graph_test001"
    current_round = 5
    profiles_count = 10
    entities_count = 8
    locale = "fr"

    def to_dict(self) -> dict:
        return {"simulation_id": self.simulation_id}


_FAKE_STATE = _FakeSimState()


# ── Flask app fixture ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app(tmp_path_factory):
    """Construit une app Flask de test avec les dépendances stubées."""
    os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
    os.environ.setdefault("NEO4J_USER", "neo4j")
    os.environ.setdefault("NEO4J_PASSWORD", "test")
    os.environ.setdefault("OPENROUTER_API_KEY", "sk-test")

    import app.storage as storage_mod

    class _NullStorage:
        def __init__(self, *a, **kw):
            pass

    original_storage = storage_mod.Neo4jStorage
    storage_mod.Neo4jStorage = _NullStorage

    from app.services import simulation_runner as runner_mod
    original_cleanup = runner_mod.SimulationRunner.register_cleanup
    runner_mod.SimulationRunner.register_cleanup = classmethod(lambda cls: None)

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True

    storage_mod.Neo4jStorage = original_storage
    runner_mod.SimulationRunner.register_cleanup = original_cleanup

    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


# ── Helpers de patch ──────────────────────────────────────────────────────────

def _patch_sim_manager(sim_id: str = _VALID_SIM_ID, known: bool = True):
    """Retourne les patches SimulationManager pour les tests endpoint."""

    def _get_simulation(self, sid):
        return _FAKE_STATE if (known and sid == sim_id) else None

    def _get_sim_dir(self, sid, create=False):
        return str(_FIXTURES_DIR / sid)

    return (
        patch(
            "app.services.simulation_manager.SimulationManager.get_simulation",
            _get_simulation,
        ),
        patch(
            "app.services.simulation_manager.SimulationManager._get_simulation_dir",
            _get_sim_dir,
        ),
    )


# ── Tests _build_pdf() ────────────────────────────────────────────────────────

class TestBuildPdf:

    @skip_no_weasyprint
    def test_build_pdf_returns_bytes_starting_with_pdf_magic(self):
        """_build_pdf() doit retourner des bytes PDF valides (%PDF-)."""
        from app.api.pdf_export import _build_pdf

        with patch(
            "app.api.pdf_export._resolve_report_id_for_simulation",
            return_value=None,
        ), patch(
            "app.api.pdf_export._resolve_lang_for_simulation",
            return_value="fr",
        ), patch(
            "app.services.report_pdf.loader.PDFContextLoader.load",
            return_value=_make_minimal_context(),
        ):
            pdf_bytes = _build_pdf(_VALID_SIM_ID)

        assert isinstance(pdf_bytes, bytes), "Doit retourner des bytes"
        assert pdf_bytes[:5] == b"%PDF-", f"Magic bytes PDF attendus, reçu : {pdf_bytes[:10]!r}"

    @skip_no_weasyprint
    def test_build_pdf_size_greater_than_1kb(self):
        """_build_pdf() doit retourner un PDF > 1 KB (non trivial)."""
        from app.api.pdf_export import _build_pdf

        with patch(
            "app.api.pdf_export._resolve_report_id_for_simulation",
            return_value=None,
        ), patch(
            "app.api.pdf_export._resolve_lang_for_simulation",
            return_value="fr",
        ), patch(
            "app.services.report_pdf.loader.PDFContextLoader.load",
            return_value=_make_minimal_context(),
        ):
            pdf_bytes = _build_pdf(_VALID_SIM_ID)

        assert len(pdf_bytes) > 1024, (
            f"PDF trop petit : {len(pdf_bytes)} bytes (attendu > 1 kB)"
        )


# ── Tests _build_markdown() ───────────────────────────────────────────────────

class TestBuildMarkdown:

    def test_build_markdown_returns_non_empty_string(self):
        """_build_markdown() doit retourner une string non vide."""
        from app.api.pdf_export import _build_markdown

        with patch(
            "app.api.pdf_export._resolve_report_id_for_simulation",
            return_value=None,
        ), patch(
            "app.api.pdf_export._resolve_lang_for_simulation",
            return_value="fr",
        ), patch(
            "app.services.report_pdf.loader.PDFContextLoader.load",
            return_value=_make_minimal_context(),
        ):
            md = _build_markdown(_VALID_SIM_ID)

        assert isinstance(md, str), "Doit retourner une string"
        assert len(md) > 0, "String Markdown ne doit pas être vide"

    def test_build_markdown_contains_yaml_frontmatter(self):
        """_build_markdown() doit contenir un front-matter YAML délimité par ---."""
        from app.api.pdf_export import _build_markdown

        with patch(
            "app.api.pdf_export._resolve_report_id_for_simulation",
            return_value=None,
        ), patch(
            "app.api.pdf_export._resolve_lang_for_simulation",
            return_value="fr",
        ), patch(
            "app.services.report_pdf.loader.PDFContextLoader.load",
            return_value=_make_minimal_context(),
        ):
            md = _build_markdown(_VALID_SIM_ID)

        # Le front-matter YAML commence par --- et contient au moins une clé
        assert md.startswith("---"), (
            f"Le Markdown doit commencer par un front-matter YAML (---). "
            f"Début reçu : {md[:100]!r}"
        )
        # Vérifier que le bloc --- se ferme
        second_sep = md.find("\n---", 3)
        assert second_sep > 0, "Le front-matter YAML doit être fermé par ---"


# ── Tests endpoints Flask ─────────────────────────────────────────────────────

class TestEndpointExportPdf:

    @skip_no_weasyprint
    def test_export_pdf_200_application_pdf(self, client):
        """POST /export-pdf → 200 + Content-Type application/pdf."""
        p1, p2 = _patch_sim_manager()
        with p1, p2, _patch_loader_to_fixture():
            resp = client.post(f"/api/simulation/{_VALID_SIM_ID}/export-pdf")

        assert resp.status_code == 200, f"Attendu 200, reçu {resp.status_code}"
        assert "application/pdf" in resp.content_type, (
            f"Content-Type attendu application/pdf, reçu {resp.content_type}"
        )

    def test_export_pdf_invalid_sim_id_returns_400(self, client):
        """POST /export-pdf avec ID invalide (traversal ..) → 400 INVALID_SIMULATION_ID."""
        # Un ID contenant '..' déclenche ValueError dans validate_simulation_id → 400
        resp = client.post("/api/simulation/sim..escape/export-pdf")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert data["error_code"] == "INVALID_SIMULATION_ID"

    def test_export_pdf_unknown_sim_returns_404(self, client):
        """POST /export-pdf simulation absente → 404 SIMULATION_NOT_FOUND."""
        p1, p2 = _patch_sim_manager(known=False)
        with p1, p2:
            resp = client.post(f"/api/simulation/{_VALID_SIM_ID}/export-pdf")

        assert resp.status_code == 404
        data = resp.get_json()
        assert data["success"] is False
        assert data["error_code"] == "SIMULATION_NOT_FOUND"


class TestEndpointExportMd:

    def test_export_md_200_text_markdown(self, client):
        """GET /export-md → 200 + Content-Type text/markdown."""
        p1, p2 = _patch_sim_manager()
        with p1, p2, _patch_loader_to_fixture():
            resp = client.get(f"/api/simulation/{_VALID_SIM_ID}/export-md")

        assert resp.status_code == 200, f"Attendu 200, reçu {resp.status_code}"
        assert "markdown" in resp.content_type or "text" in resp.content_type, (
            f"Content-Type attendu text/markdown, reçu {resp.content_type}"
        )

    def test_export_md_invalid_sim_id_returns_400(self, client):
        """GET /export-md avec ID invalide (traversal ..) → 400 INVALID_SIMULATION_ID."""
        resp = client.get("/api/simulation/sim..escape/export-md")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert data["error_code"] == "INVALID_SIMULATION_ID"

    def test_export_md_unknown_sim_returns_404(self, client):
        """GET /export-md simulation absente → 404 SIMULATION_NOT_FOUND."""
        p1, p2 = _patch_sim_manager(known=False)
        with p1, p2:
            resp = client.get(f"/api/simulation/{_VALID_SIM_ID}/export-md")

        assert resp.status_code == 404
        data = resp.get_json()
        assert data["success"] is False
        assert data["error_code"] == "SIMULATION_NOT_FOUND"


# ── Tests fallback sans report_id ─────────────────────────────────────────────

class TestFallbackWithoutReportId:

    def test_build_markdown_without_report_id_does_not_crash(self):
        """PDFContextLoader sans report_id (mode dégradé) ne crash pas."""
        from app.api.pdf_export import _build_markdown

        with patch(
            "app.api.pdf_export._resolve_report_id_for_simulation",
            return_value=None,  # Pas de report_id
        ), patch(
            "app.api.pdf_export._resolve_lang_for_simulation",
            return_value="fr",
        ), patch(
            "app.services.report_pdf.loader.PDFContextLoader.load",
            return_value=_make_minimal_context(),
        ):
            # Ne doit pas lever d'exception
            md = _build_markdown(_VALID_SIM_ID)

        assert isinstance(md, str)
        assert len(md) > 0


# ── Tests graph_image_b64 ignoré gracefully ───────────────────────────────────

class TestGraphImageB64Ignored:

    @skip_no_weasyprint
    def test_graph_image_b64_ignored_gracefully(self, client, caplog):
        """graph_image_b64 dans la requête est ignoré sans erreur.

        Le PDF doit quand même être généré correctement.
        """
        import base64

        # PNG 1×1 transparent
        tiny_png = base64.b64encode(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        ).decode()

        p1, p2 = _patch_sim_manager()
        with p1, p2, _patch_loader_to_fixture():
            resp = client.post(
                f"/api/simulation/{_VALID_SIM_ID}/export-pdf",
                json={"graph_image_b64": tiny_png},
                content_type="application/json",
            )

        assert resp.status_code == 200, (
            f"PDF export avec graph_image_b64 doit réussir : {resp.status_code}"
        )
        assert resp.data[:5] == b"%PDF-"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_minimal_context():
    """Construit un PDFReportContext minimal valide pour les mocks."""
    from app.services.report_pdf.schema import PDFReportContext, Outcome

    ctx = PDFReportContext(
        report_id="report_aabbcc112233",
        simulation_id=_VALID_SIM_ID,
        lang="fr",
        title="Simulation test — US-133",
        framework="cerberus",
        package="crisis-drill-24h",
    )
    ctx.outcome = Outcome(
        verdict="Verdict simulé — test US-133.",
        bullish_pct=60.0,
        bearish_pct=30.0,
        confidence=0.72,
    )
    return ctx


def _patch_loader_to_fixture():
    """Patche PDFContextLoader.load() pour utiliser les fixtures de test.

    Charge le contexte réel depuis les fixtures en passant sim_base_dir
    et rep_base_dir explicites, sans toucher au disque de production.
    """
    from app.services.report_pdf.loader import PDFContextLoader

    original_load = PDFContextLoader.load

    def _patched_load(cls, simulation_id, report_id=None, lang="fr", **kwargs):
        return original_load(
            simulation_id=simulation_id,
            report_id=None,  # pas de report dans les fixtures
            lang=lang,
            sim_base_dir=_FIXTURES_DIR,
            rep_base_dir=_FIXTURES_DIR,
        )

    return patch.object(PDFContextLoader, "load", classmethod(_patched_load))


# ── Tests US-138 — variant + chart embedding ─────────────────────────────────


class TestVariantParameter:
    """US-138 — la valeur `variant` doit être lue, validée et propagée."""

    def test_invalid_variant_pdf_returns_400(self, client):
        """POST /export-pdf avec variant inconnu → 400 INVALID_VARIANT."""
        p1, p2 = _patch_sim_manager()
        with p1, p2:
            resp = client.post(
                f"/api/simulation/{_VALID_SIM_ID}/export-pdf",
                json={"variant": "executive-summary"},
                content_type="application/json",
            )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert data["error_code"] == "INVALID_VARIANT"

    def test_invalid_variant_md_returns_400(self, client):
        """GET /export-md?variant=foo → 400 INVALID_VARIANT."""
        p1, p2 = _patch_sim_manager()
        with p1, p2:
            resp = client.get(
                f"/api/simulation/{_VALID_SIM_ID}/export-md?variant=foo"
            )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error_code"] == "INVALID_VARIANT"

    def test_pdf_propagates_variant_to_renderer(self):
        """_build_pdf(variant='exec') doit passer `variant='exec'` à Renderer.render_pdf()."""
        from app.api.pdf_export import _build_pdf

        captured = {}

        class _FakeRenderer:
            def __init__(self, context, branding=None, charts_factory=None):
                captured["init_charts_factory"] = charts_factory

            def render_pdf(self, charts_factory=None, variant="full"):
                captured["render_variant"] = variant
                captured["render_charts_factory"] = charts_factory
                return b"%PDF-fake"

        with patch(
            "app.api.pdf_export._resolve_report_id_for_simulation",
            return_value=None,
        ), patch(
            "app.api.pdf_export._resolve_lang_for_simulation",
            return_value="fr",
        ), patch(
            "app.services.report_pdf.loader.PDFContextLoader.load",
            return_value=_make_minimal_context(),
        ), patch(
            "app.services.report_pdf.renderer.Renderer",
            _FakeRenderer,
        ):
            out = _build_pdf(_VALID_SIM_ID, variant="exec")

        assert out.startswith(b"%PDF-")
        assert captured["render_variant"] == "exec", (
            f"variant='exec' aurait dû arriver à render_pdf(), reçu {captured.get('render_variant')!r}"
        )
        assert captured["render_charts_factory"] is not None, (
            "ChartFactory aurait dû être instancié et passé à render_pdf()"
        )

    def test_md_propagates_variant_and_charts_factory(self):
        """_build_markdown(variant='public') doit instancier ChartFactory et propager variant."""
        from app.api.pdf_export import _build_markdown

        captured = {}

        class _FakeRenderer:
            def __init__(self, context, branding=None, charts_factory=None):
                captured["init_charts_factory"] = charts_factory

            def render_md(self, variant="full"):
                captured["render_variant"] = variant
                return "---\nfront: matter\n---\nfake md"

        with patch(
            "app.api.pdf_export._resolve_report_id_for_simulation",
            return_value=None,
        ), patch(
            "app.api.pdf_export._resolve_lang_for_simulation",
            return_value="fr",
        ), patch(
            "app.services.report_pdf.loader.PDFContextLoader.load",
            return_value=_make_minimal_context(),
        ), patch(
            "app.services.report_pdf.renderer.Renderer",
            _FakeRenderer,
        ):
            md = _build_markdown(_VALID_SIM_ID, variant="public")

        assert md.startswith("---")
        assert captured["render_variant"] == "public"
        # US-138 fix critique : ChartFactory doit être passé au constructeur,
        # sinon `_embed_charts_md` ne s'applique jamais → MD avec placeholders cassés.
        assert captured["init_charts_factory"] is not None, (
            "_build_markdown doit instancier un ChartFactory et le passer à Renderer"
        )

    def test_md_default_variant_is_full(self, client):
        """GET /export-md sans param → variant 'full' (rétro-compatible)."""
        from app.api.pdf_export import _parse_variant

        # Le test parametrique de _parse_variant suffit ici (test endpoint
        # déjà couvert par TestEndpointExportMd plus haut).
        assert _parse_variant(None) == "full"
        assert _parse_variant("") == "full"
        assert _parse_variant("FULL") == "full"  # Insensible à la casse
        assert _parse_variant("exec") == "exec"
        assert _parse_variant("one-pager") == "one-pager"

    def test_md_accepts_variant_query_param(self, client):
        """GET /export-md?variant=exec → 200 et content-disposition contient le suffix."""
        p1, p2 = _patch_sim_manager()
        with p1, p2, _patch_loader_to_fixture():
            resp = client.get(f"/api/simulation/{_VALID_SIM_ID}/export-md?variant=exec")
        assert resp.status_code == 200
        # Le filename doit refléter la variante non-default
        assert "exec" in resp.headers.get("Content-Disposition", "")
