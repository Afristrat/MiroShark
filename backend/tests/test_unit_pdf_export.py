"""Unit tests for US-024 — Génération PDF brandé AIMPOWER.

Tests are fully offline: no Neo4j, no OpenAI, no running Flask server.
They exercise the Flask test client (app factory) with monkey-patched
SimulationManager so we never touch the filesystem.

Coverage:
  1. 404 for an unknown simulation ID.
  2. 200 with Content-Type application/pdf for a known simulation.
  3. PDF body size > 500 bytes.
  4. PDF body starts with the PDF magic bytes (%PDF-).
  5. AIMPOWER brand string appears in the PDF byte stream.
  6. PDF size > 1 kB (résumé exécutif section is present and non-trivial).
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


# ── Fake SimulationState ─────────────────────────────────────────────────────

class _FakeState:
    simulation_id  = "sim_faketest001"
    project_id     = "proj_fake"
    graph_id       = "graph_fake"
    current_round  = 5
    profiles_count = 12
    entities_count = 8
    locale         = "fr"

    def to_dict(self) -> dict:
        return {"simulation_id": self.simulation_id}


_FAKE_STATE = _FakeState()

_KNOWN_SIM_ID = "sim_faketest001"


# ── Flask client fixture ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app(tmp_path_factory):
    """Build a test Flask app with Neo4jStorage stubbed out."""
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

    # SimulationRunner.register_cleanup accesses subprocesses — stub it out
    from app.services import simulation_runner as runner_mod
    original_cleanup = runner_mod.SimulationRunner.register_cleanup
    runner_mod.SimulationRunner.register_cleanup = classmethod(lambda cls: None)

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True

    # Restore originals after the app is built (no further impact on tests)
    storage_mod.Neo4jStorage = original
    runner_mod.SimulationRunner.register_cleanup = original_cleanup

    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


# ── Shared patch helper ───────────────────────────────────────────────────────

def _patch_manager(tmp_path):
    """Return a context-manager stack that patches SimulationManager."""
    def _get_simulation(self, sim_id):
        return _FAKE_STATE if sim_id == _KNOWN_SIM_ID else None

    def _get_sim_dir(self, sim_id, create=False):
        return str(tmp_path)

    get_patch = patch(
        "app.services.simulation_manager.SimulationManager.get_simulation",
        _get_simulation,
    )
    dir_patch = patch(
        "app.services.simulation_manager.SimulationManager._get_simulation_dir",
        _get_sim_dir,
    )
    project_patch = patch(
        "app.models.project.ProjectManager.get_project",
        return_value=MagicMock(
            simulation_requirement=(
                "Analyse de l'impact d'une hausse des taux de la BCE "
                "sur les marchés émergents."
            ),
        ),
    )
    return get_patch, dir_patch, project_patch


# ── Test: 404 for unknown simulation ─────────────────────────────────────────

class TestPdfExport404:

    def test_unknown_simulation_returns_404(self, client, tmp_path):
        p1, p2, p3 = _patch_manager(tmp_path)
        with p1, p2, p3:
            resp = client.post("/api/simulation/sim_doesnotexist/export-pdf")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["success"] is False
        assert data["error_code"] == "SIMULATION_NOT_FOUND"


# ── Test: 200 + valid PDF for known simulation ────────────────────────────────

class TestPdfExport200:

    def test_response_status_200(self, client, tmp_path):
        p1, p2, p3 = _patch_manager(tmp_path)
        with p1, p2, p3:
            resp = client.post(f"/api/simulation/{_KNOWN_SIM_ID}/export-pdf")
        assert resp.status_code == 200

    def test_content_type_is_pdf(self, client, tmp_path):
        p1, p2, p3 = _patch_manager(tmp_path)
        with p1, p2, p3:
            resp = client.post(f"/api/simulation/{_KNOWN_SIM_ID}/export-pdf")
        assert "application/pdf" in resp.content_type

    def test_pdf_size_greater_than_500_bytes(self, client, tmp_path):
        p1, p2, p3 = _patch_manager(tmp_path)
        with p1, p2, p3:
            resp = client.post(f"/api/simulation/{_KNOWN_SIM_ID}/export-pdf")
        assert len(resp.data) > 500, (
            f"PDF too small: {len(resp.data)} bytes (expected > 500)"
        )

    def test_pdf_magic_bytes(self, client, tmp_path):
        """PDF files always start with %PDF-."""
        p1, p2, p3 = _patch_manager(tmp_path)
        with p1, p2, p3:
            resp = client.post(f"/api/simulation/{_KNOWN_SIM_ID}/export-pdf")
        assert resp.data[:5] == b"%PDF-", (
            f"Response does not start with PDF magic bytes: {resp.data[:10]!r}"
        )

    def test_pdf_contains_bassira_brand(self, client, tmp_path):
        """Le mot BASSIRA doit apparaître dans le texte extrait du PDF."""
        import fitz  # PyMuPDF

        p1, p2, p3 = _patch_manager(tmp_path)
        with p1, p2, p3:
            resp = client.post(f"/api/simulation/{_KNOWN_SIM_ID}/export-pdf")

        doc = fitz.open(stream=resp.data, filetype="pdf")
        all_text = "\n".join(page.get_text() for page in doc)
        doc.close()
        assert "BASSIRA" in all_text, (
            f"BASSIRA brand not found in PDF text. First 500 chars: {all_text[:500]!r}"
        )

    def test_pdf_contains_disclaimer(self, client, tmp_path):
        """Le disclaimer légal doit être présent dans le PDF."""
        import fitz

        p1, p2, p3 = _patch_manager(tmp_path)
        with p1, p2, p3:
            resp = client.post(f"/api/simulation/{_KNOWN_SIM_ID}/export-pdf")

        doc = fitz.open(stream=resp.data, filetype="pdf")
        all_text = "\n".join(page.get_text() for page in doc)
        doc.close()
        assert "probabiliste" in all_text.lower() or "avertissement" in all_text.lower(), (
            "Disclaimer légal absent du PDF"
        )

    def test_pdf_size_greater_than_1kb(self, client, tmp_path):
        """PDF must be > 1 kB — validates enriched sections are rendered."""
        p1, p2, p3 = _patch_manager(tmp_path)
        with p1, p2, p3:
            resp = client.post(f"/api/simulation/{_KNOWN_SIM_ID}/export-pdf")
        assert len(resp.data) > 1024, (
            f"PDF size {len(resp.data)} B is below 1 kB — sections likely missing"
        )

    def test_pdf_with_graph_image(self, client, tmp_path):
        """PDF accepte une image graphe base64 sans erreur."""
        import base64

        # 1x1 transparent PNG
        tiny_png = base64.b64encode(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        ).decode()

        p1, p2, p3 = _patch_manager(tmp_path)
        with p1, p2, p3:
            resp = client.post(
                f"/api/simulation/{_KNOWN_SIM_ID}/export-pdf",
                json={"graph_image_b64": tiny_png},
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert resp.data[:5] == b"%PDF-"


class TestMarkdownExport:

    def test_md_200_for_known_simulation(self, client, tmp_path):
        p1, p2, p3 = _patch_manager(tmp_path)
        with p1, p2, p3:
            resp = client.get(f"/api/simulation/{_KNOWN_SIM_ID}/export-md")
        assert resp.status_code == 200

    def test_md_content_type(self, client, tmp_path):
        p1, p2, p3 = _patch_manager(tmp_path)
        with p1, p2, p3:
            resp = client.get(f"/api/simulation/{_KNOWN_SIM_ID}/export-md")
        assert "markdown" in resp.content_type or "text" in resp.content_type

    def test_md_contains_bassira(self, client, tmp_path):
        p1, p2, p3 = _patch_manager(tmp_path)
        with p1, p2, p3:
            resp = client.get(f"/api/simulation/{_KNOWN_SIM_ID}/export-md")
        text = resp.data.decode("utf-8")
        assert "Bassira" in text or "BASSIRA" in text

    def test_md_contains_disclaimer(self, client, tmp_path):
        p1, p2, p3 = _patch_manager(tmp_path)
        with p1, p2, p3:
            resp = client.get(f"/api/simulation/{_KNOWN_SIM_ID}/export-md")
        text = resp.data.decode("utf-8")
        assert "probabiliste" in text.lower() or "avertissement" in text.lower()

    def test_md_contains_sections(self, client, tmp_path):
        """Les sections clés doivent être présentes dans le Markdown."""
        p1, p2, p3 = _patch_manager(tmp_path)
        with p1, p2, p3:
            resp = client.get(f"/api/simulation/{_KNOWN_SIM_ID}/export-md")
        text = resp.data.decode("utf-8")
        for section in ("Résumé exécutif", "Résultats", "Méthodologie", "Recommandations"):
            assert section in text, f"Section '{section}' absente du Markdown"

    def test_md_404_for_unknown(self, client, tmp_path):
        p1, p2, p3 = _patch_manager(tmp_path)
        with p1, p2, p3:
            resp = client.get("/api/simulation/sim_doesnotexist/export-md")
        assert resp.status_code == 404
