"""Tests unitaires — endpoint POST /api/simulation/enrich-ask (US-057)."""

from __future__ import annotations

import hashlib
import time

import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestEnrichAsk:
    def test_missing_question_returns_400(self, client):
        resp = client.post(
            "/api/simulation/enrich-ask",
            json={},
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert data["error"] == "MISSING_QUESTION"

    def test_empty_question_returns_400(self, client):
        resp = client.post(
            "/api/simulation/enrich-ask",
            json={"question": "   "},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_no_web_search_model_returns_empty_context(self, client, monkeypatch):
        """Sans WEB_SEARCH_MODEL configuré → contexte vide, pas d'erreur."""
        from app.config import Config
        monkeypatch.setattr(Config, "WEB_SEARCH_MODEL", "")

        resp = client.post(
            "/api/simulation/enrich-ask",
            json={"question": "What if interest rates rise sharply?"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["context"] == ""
        assert data["data"]["cached"] is False

    def test_cache_hit_returns_cached_true(self, client, monkeypatch):
        """Une deuxième requête identique doit retourner cached: True."""
        from app.config import Config
        from app.api import simulation as sim_module

        monkeypatch.setattr(Config, "WEB_SEARCH_MODEL", "")

        question = "Cache test question unique 12345"
        cache_key = hashlib.sha256(question.encode()).hexdigest()

        sim_module._ENRICH_CACHE[cache_key] = {
            "result": {"context": "test context", "sources": [], "model": "test"},
            "expires_at": time.time() + 3600,
        }

        resp = client.post(
            "/api/simulation/enrich-ask",
            json={"question": question},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["cached"] is True
        assert data["data"]["context"] == "test context"

        # Nettoyage
        del sim_module._ENRICH_CACHE[cache_key]

    def test_rate_limit_returns_429(self, client, monkeypatch):
        """Après trop de requêtes, le rate-limiter renvoie 429."""
        from app.api import simulation as sim_module

        def always_limited(_ip):
            return True

        monkeypatch.setattr(sim_module, "_enrich_rate_limited", always_limited)

        resp = client.post(
            "/api/simulation/enrich-ask",
            json={"question": "Any question"},
            content_type="application/json",
        )
        assert resp.status_code == 429
        assert resp.get_json()["error"] == "RATE_LIMITED"
