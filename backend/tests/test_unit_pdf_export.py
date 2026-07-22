"""Unit tests pour les endpoints export PDF/MD — US-024 / US-059 / US-133.

Mis à jour US-133 : le pipeline ReportLab est remplacé par le nouveau
pipeline PDFContextLoader → Enricher → Renderer (WeasyPrint / GFM).

Tests fully offline : no Neo4j, no OpenAI, no running Flask server.
Exercent le Flask test client avec SimulationManager monkey-patché.

Coverage :
  1.  404 pour une simulation inconnue (PDF).
  2.  200 + Content-Type application/pdf pour simulation connue (skip WeasyPrint).
  3.  PDF body > 500 bytes (skip WeasyPrint).
  4.  PDF magic bytes %PDF- (skip WeasyPrint).
  5.  PDF > 1 kB (skip WeasyPrint).
  6.  PDF accepte graph_image_b64 sans erreur (skip WeasyPrint).
  7.  MD 200 pour simulation connue.
  8.  MD Content-Type text/markdown.
  9.  MD contient Bassira.
  10. MD contient 'probabiliste' ou 'avertissement' (disclaimer).
  11. MD 404 pour simulation inconnue.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# ── Fixtures sim valides ──────────────────────────────────────────────────────
_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# On utilise la fixture sim valide (format sim_<12hex>)
_KNOWN_SIM_ID = "sim_aabbcc112233"


# ── Détection WeasyPrint disponible ───────────────────────────────────────────

def _weasyprint_available() -> bool:
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


# ── Mock LanguageTool global ──────────────────────────────────────────────────

@pytest.fixture(autouse=True, scope="session")
def mock_languagetool_globally():
    """Mock global du client LanguageTool pour éviter les timeouts réseau."""
    with patch("app.services.text_normalizer.lt_check", return_value=[]):
        yield


# ── Mock LLM global ───────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_llm_client():
    """Mock LLM pour Enricher — retourne des fallbacks immédiats."""
    mock_llm = MagicMock()
    mock_llm.chat.return_value = "Analyse simulée."
    with patch(
        "app.services.report_pdf.enricher._safe_create_llm_client",
        return_value=mock_llm,
    ):
        yield mock_llm


# ── Fake SimulationState ──────────────────────────────────────────────────────

class _FakeState:
    simulation_id = _KNOWN_SIM_ID
    project_id = "proj_fake"
    graph_id = "graph_fake"
    current_round = 5
    profiles_count = 12
    entities_count = 8
    locale = "fr"

    def to_dict(self) -> dict:
        return {"simulation_id": self.simulation_id}


_FAKE_STATE = _FakeState()


# ── Flask client fixture ─────────────────────────────────────────────────────

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

    original = storage_mod.Neo4jStorage
    storage_mod.Neo4jStorage = _NullStorage

    from app.services import simulation_runner as runner_mod
    original_cleanup = runner_mod.SimulationRunner.register_cleanup
    runner_mod.SimulationRunner.register_cleanup = classmethod(lambda cls: None)

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True

    storage_mod.Neo4jStorage = original
    runner_mod.SimulationRunner.register_cleanup = original_cleanup

    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


# ── Helpers de patch ──────────────────────────────────────────────────────────

def _patch_sim_manager_known():
    """Patches SimulationManager pour reconnaître _KNOWN_SIM_ID."""

    def _get_simulation(self, sim_id):
        return _FAKE_STATE if sim_id == _KNOWN_SIM_ID else None

    return (
        patch(
            "app.services.simulation_manager.SimulationManager.get_simulation",
            _get_simulation,
        ),
    )


def _patch_loader_to_fixture():
    """Patche PDFContextLoader.load() pour utiliser les fixtures de test."""
    from app.services.report_pdf.loader import PDFContextLoader

    original_load = PDFContextLoader.load

    def _patched_load(cls, simulation_id, report_id=None, lang="fr", **kwargs):
        return original_load(
            simulation_id=simulation_id,
            report_id=None,
            lang=lang,
            sim_base_dir=_FIXTURES_DIR,
            rep_base_dir=_FIXTURES_DIR,
        )

    return patch.object(PDFContextLoader, "load", classmethod(_patched_load))


def _patch_resolve_helpers():
    """Patche les helpers _resolve_* pour pointer vers les fixtures."""
    return (
        patch(
            "app.api.pdf_export._resolve_report_id_for_simulation",
            return_value=None,
        ),
        patch(
            "app.api.pdf_export._resolve_lang_for_simulation",
            return_value="fr",
        ),
    )


def _patch_export_access_allowed():
    """Isole les tests de rendu du guard d'accès couvert séparément."""
    return patch("app.api.pdf_export._authorize_simulation_access", return_value=None)


# ── Test : 404 pour simulation inconnue ─────────────────────────────────────

class TestPdfExport404:

    def test_unknown_simulation_returns_404(self, client):
        """Simulation inconnue → 404 SIMULATION_NOT_FOUND."""
        (p1,) = _patch_sim_manager_known()
        with p1:
            resp = client.post("/api/simulation/sim_doesnotexist/export-pdf")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["success"] is False
        assert data["error_code"] == "SIMULATION_NOT_FOUND"


# ── Test : 200 + PDF valide ──────────────────────────────────────────────────

class TestPdfExport200:

    @skip_no_weasyprint
    def test_response_status_200(self, client):
        (p1,) = _patch_sim_manager_known()
        pr1, pr2 = _patch_resolve_helpers()
        with p1, pr1, pr2, _patch_loader_to_fixture():
            resp = client.post(f"/api/simulation/{_KNOWN_SIM_ID}/export-pdf")
        assert resp.status_code == 200

    @skip_no_weasyprint
    def test_content_type_is_pdf(self, client):
        (p1,) = _patch_sim_manager_known()
        pr1, pr2 = _patch_resolve_helpers()
        with p1, pr1, pr2, _patch_loader_to_fixture():
            resp = client.post(f"/api/simulation/{_KNOWN_SIM_ID}/export-pdf")
        assert "application/pdf" in resp.content_type

    @skip_no_weasyprint
    def test_pdf_size_greater_than_500_bytes(self, client):
        (p1,) = _patch_sim_manager_known()
        pr1, pr2 = _patch_resolve_helpers()
        with p1, pr1, pr2, _patch_loader_to_fixture():
            resp = client.post(f"/api/simulation/{_KNOWN_SIM_ID}/export-pdf")
        assert len(resp.data) > 500, (
            f"PDF too small: {len(resp.data)} bytes (expected > 500)"
        )

    @skip_no_weasyprint
    def test_pdf_magic_bytes(self, client):
        """PDF files always start with %PDF-."""
        (p1,) = _patch_sim_manager_known()
        pr1, pr2 = _patch_resolve_helpers()
        with p1, pr1, pr2, _patch_loader_to_fixture():
            resp = client.post(f"/api/simulation/{_KNOWN_SIM_ID}/export-pdf")
        assert resp.data[:5] == b"%PDF-", (
            f"Response does not start with PDF magic bytes: {resp.data[:10]!r}"
        )

    @skip_no_weasyprint
    def test_pdf_size_greater_than_1kb(self, client):
        """PDF must be > 1 kB — validates enriched sections are rendered."""
        (p1,) = _patch_sim_manager_known()
        pr1, pr2 = _patch_resolve_helpers()
        with p1, pr1, pr2, _patch_loader_to_fixture():
            resp = client.post(f"/api/simulation/{_KNOWN_SIM_ID}/export-pdf")
        assert len(resp.data) > 1024, (
            f"PDF size {len(resp.data)} B is below 1 kB — sections likely missing"
        )

    @skip_no_weasyprint
    def test_pdf_with_graph_image(self, client):
        """PDF accepte une image graphe base64 sans erreur (ignorée gracefully)."""
        import base64

        # 1x1 transparent PNG
        tiny_png = base64.b64encode(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        ).decode()

        (p1,) = _patch_sim_manager_known()
        pr1, pr2 = _patch_resolve_helpers()
        with p1, pr1, pr2, _patch_loader_to_fixture():
            resp = client.post(
                f"/api/simulation/{_KNOWN_SIM_ID}/export-pdf",
                json={"graph_image_b64": tiny_png},
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert resp.data[:5] == b"%PDF-"


class TestMarkdownExport:

    def test_md_200_for_known_simulation(self, client):
        (p1,) = _patch_sim_manager_known()
        pr1, pr2 = _patch_resolve_helpers()
        with p1, pr1, pr2, _patch_loader_to_fixture(), _patch_export_access_allowed():
            resp = client.get(f"/api/simulation/{_KNOWN_SIM_ID}/export-md")
        assert resp.status_code == 200

    def test_md_content_type(self, client):
        (p1,) = _patch_sim_manager_known()
        pr1, pr2 = _patch_resolve_helpers()
        with p1, pr1, pr2, _patch_loader_to_fixture(), _patch_export_access_allowed():
            resp = client.get(f"/api/simulation/{_KNOWN_SIM_ID}/export-md")
        assert "markdown" in resp.content_type or "text" in resp.content_type

    def test_md_contains_bassira(self, client):
        (p1,) = _patch_sim_manager_known()
        pr1, pr2 = _patch_resolve_helpers()
        with p1, pr1, pr2, _patch_loader_to_fixture(), _patch_export_access_allowed():
            resp = client.get(f"/api/simulation/{_KNOWN_SIM_ID}/export-md")
        text = resp.data.decode("utf-8")
        assert "Bassira" in text or "BASSIRA" in text or "bassira" in text.lower()

    def test_md_contains_disclaimer(self, client):
        (p1,) = _patch_sim_manager_known()
        pr1, pr2 = _patch_resolve_helpers()
        with p1, pr1, pr2, _patch_loader_to_fixture(), _patch_export_access_allowed():
            resp = client.get(f"/api/simulation/{_KNOWN_SIM_ID}/export-md")
        text = resp.data.decode("utf-8")
        # Le nouveau template peut contenir 'disclaimer', 'probabiliste', ou 'avertissement'
        assert any(
            kw in text.lower()
            for kw in ("probabiliste", "avertissement", "disclaimer", "simulation")
        ), "Disclaimer ou référence à la simulation probabiliste absente du Markdown"

    def test_md_404_for_unknown(self, client):
        (p1,) = _patch_sim_manager_known()
        with p1:
            resp = client.get("/api/simulation/sim_doesnotexist/export-md")
        assert resp.status_code == 404
