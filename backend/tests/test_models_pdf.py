"""Unit tests for US-088 — Endpoint /api/models/<slug>/pdf-brief.

Tests are fully offline: no Neo4j, no LLM, no filesystem write.
They exercise the Flask test client (app factory) and verify that the
5 published models render as valid A4 PDFs in fr / en / ar.

Coverage:
  1. 200 + application/pdf for the 5 supported slugs × 3 languages
  2. 404 MODEL_NOT_FOUND for an unknown slug
  3. 400 INVALID_LANG for an unsupported lang
  4. PDF body > 5 kB (the 4-6 page brief is non-trivial)
  5. Content-Type + Content-Disposition headers correct
  6. PDF magic bytes (%PDF-)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ── Flask app fixture ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
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


# ── Constants ────────────────────────────────────────────────────────────────

_SLUGS = (
    "fusion-bancaire-mena",
    "crisis-drill-24h",
    "allocation-fonds-strategique",
    "stress-test-politique",
    "lancement-diaspora-eu",
)
_LANGS = ("fr", "en", "ar")


# ── Test 1: 200 OK for the 5 × 3 matrix ──────────────────────────────────────

class TestPdfBriefMatrix:

    @pytest.mark.parametrize("slug", _SLUGS)
    @pytest.mark.parametrize("lang", _LANGS)
    def test_status_200(self, client, slug, lang):
        resp = client.get(f"/api/models/{slug}/pdf-brief?lang={lang}")
        assert resp.status_code == 200, (
            f"Slug {slug}/{lang} returned {resp.status_code}: {resp.data[:200]!r}"
        )

    @pytest.mark.parametrize("slug", _SLUGS)
    @pytest.mark.parametrize("lang", _LANGS)
    def test_content_type_pdf(self, client, slug, lang):
        resp = client.get(f"/api/models/{slug}/pdf-brief?lang={lang}")
        assert "application/pdf" in resp.content_type, (
            f"Slug {slug}/{lang} content type = {resp.content_type!r}"
        )

    @pytest.mark.parametrize("slug", _SLUGS)
    @pytest.mark.parametrize("lang", _LANGS)
    def test_content_disposition_attachment(self, client, slug, lang):
        resp = client.get(f"/api/models/{slug}/pdf-brief?lang={lang}")
        cd = resp.headers.get("Content-Disposition", "")
        assert "attachment" in cd
        assert f"bassira-modele-{slug}-{lang}.pdf" in cd

    @pytest.mark.parametrize("slug", _SLUGS)
    @pytest.mark.parametrize("lang", _LANGS)
    def test_pdf_magic_bytes(self, client, slug, lang):
        resp = client.get(f"/api/models/{slug}/pdf-brief?lang={lang}")
        assert resp.data[:5] == b"%PDF-", (
            f"Slug {slug}/{lang} did not return a PDF stream: {resp.data[:20]!r}"
        )

    @pytest.mark.parametrize("slug", _SLUGS)
    @pytest.mark.parametrize("lang", _LANGS)
    def test_pdf_size_above_5kb(self, client, slug, lang):
        resp = client.get(f"/api/models/{slug}/pdf-brief?lang={lang}")
        assert len(resp.data) > 5000, (
            f"Slug {slug}/{lang} PDF too small: {len(resp.data)} bytes"
        )


# ── Test 2: 404 for unknown slug ─────────────────────────────────────────────

class TestPdfBriefNotFound:

    def test_unknown_slug_returns_404(self, client):
        resp = client.get("/api/models/this-slug-does-not-exist/pdf-brief")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data is not None
        assert data["success"] is False
        assert data["error_code"] == "MODEL_NOT_FOUND"

    def test_invalid_slug_format_returns_400(self, client):
        resp = client.get("/api/models/Invalid_Slug_Capital/pdf-brief")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data is not None
        assert data["error_code"] == "INVALID_SLUG"


# ── Test 3: 400 for invalid lang ─────────────────────────────────────────────

class TestPdfBriefInvalidLang:

    def test_unsupported_lang_returns_400(self, client):
        resp = client.get("/api/models/fusion-bancaire-mena/pdf-brief?lang=de")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data is not None
        assert data["success"] is False
        assert data["error_code"] == "INVALID_LANG"

    def test_no_lang_param_defaults_to_fr(self, client):
        """Calling without ?lang should default to fr and return 200."""
        resp = client.get("/api/models/fusion-bancaire-mena/pdf-brief")
        assert resp.status_code == 200
        assert "application/pdf" in resp.content_type


# ── Test 4: PDF brand string + content sanity ────────────────────────────────

class TestPdfBriefContent:

    def test_pdf_contains_bassira_brand(self, client):
        """The BASSIRA brand string must appear in extracted text (FR PDF)."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            pytest.skip("PyMuPDF not installed — skipping text-extraction test")

        resp = client.get("/api/models/fusion-bancaire-mena/pdf-brief?lang=fr")
        assert resp.status_code == 200
        doc = fitz.open(stream=resp.data, filetype="pdf")
        all_text = "\n".join(page.get_text() for page in doc)
        page_count = doc.page_count
        doc.close()

        assert "BASSIRA" in all_text or "Bassira" in all_text, (
            f"Bassira brand absent from PDF (first 500 chars: {all_text[:500]!r})"
        )
        # The brief must contain the localised section markers
        assert "Bank Al-Maghrib" in all_text or "fusion" in all_text.lower()
        # 4-6 pages target
        assert 4 <= page_count <= 6, f"Page count {page_count} outside 4-6 target"

    def test_pdf_arabic_renders_without_crash(self, client):
        """Arabic variant must produce a valid PDF (RTL routing OK)."""
        resp = client.get("/api/models/crisis-drill-24h/pdf-brief?lang=ar")
        assert resp.status_code == 200
        assert resp.data[:5] == b"%PDF-"
        assert len(resp.data) > 5000

    def test_cache_control_header(self, client):
        resp = client.get("/api/models/fusion-bancaire-mena/pdf-brief?lang=en")
        assert "max-age=3600" in resp.headers.get("Cache-Control", "")
