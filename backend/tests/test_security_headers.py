"""Tests de sécurité — US-116 — Headers HTTP (A05 OWASP).

Vérifie que les headers de sécurité critiques sont présents sur les
endpoints API non-embeddables et absents sur les routes /share/* qui
doivent pouvoir être embarquées en iframe.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture(scope="module")
def client():
    import app as flask_app_module
    importlib.reload(flask_app_module)
    flask_app = flask_app_module.create_app()
    return flask_app.test_client()


# ─── Headers de base ────────────────────────────────────────────────────────


def test_x_content_type_options_on_api(client):
    """A05 — X-Content-Type-Options: nosniff sur les routes API."""
    r = client.get("/api/templates/list")
    assert r.headers.get("X-Content-Type-Options") == "nosniff", (
        "X-Content-Type-Options: nosniff manquant sur /api/templates/list"
    )


def test_referrer_policy_on_api(client):
    """A05 — Referrer-Policy présent sur les routes API."""
    r = client.get("/api/templates/list")
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_x_frame_options_on_api(client):
    """A05 — X-Frame-Options: SAMEORIGIN sur les routes API (anti-clickjacking)."""
    r = client.get("/api/templates/list")
    assert r.headers.get("X-Frame-Options") == "SAMEORIGIN"


def test_permissions_policy_on_api(client):
    """A05 — Permissions-Policy bloque camera/microphone/geolocation."""
    r = client.get("/api/templates/list")
    perms = r.headers.get("Permissions-Policy", "")
    assert "camera=()" in perms
    assert "microphone=()" in perms
    assert "geolocation=()" in perms


def test_csp_on_api(client):
    """A05 — CSP présent et contient default-src + frame-ancestors."""
    r = client.get("/api/templates/list")
    csp = r.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp, f"default-src manquant dans CSP: {csp!r}"
    assert "frame-ancestors 'self'" in csp, f"frame-ancestors manquant dans CSP: {csp!r}"


# ─── Routes embeddables ──────────────────────────────────────────────────────


def test_no_x_frame_on_share_routes(client):
    """A05 — Les routes /share/* ne doivent PAS avoir X-Frame-Options
    pour permettre les unfurls Slack/Discord/Twitter."""
    r = client.get("/share/sim_notexistent123")
    assert r.headers.get("X-Frame-Options") is None, (
        f"X-Frame-Options ne devrait pas être posé sur /share/*: "
        f"{r.headers.get('X-Frame-Options')!r}"
    )


def test_no_csp_on_share_routes(client):
    """A05 — Pas de CSP sur /share/* (sinon les iframes tierces cassent)."""
    r = client.get("/share/sim_notexistent123")
    assert r.headers.get("Content-Security-Policy") is None


def test_no_x_frame_on_share_card(client):
    """A05 — Les share-card PNG doivent s'embedder sans restriction."""
    r = client.get("/api/simulation/sim_notexistent123/share-card.png")
    assert r.headers.get("X-Frame-Options") is None


# ─── HSTS ───────────────────────────────────────────────────────────────────


def test_hsts_in_production_mode(monkeypatch, tmp_path):
    """A05 — HSTS est posé en mode production (FLASK_ENV != development)."""
    monkeypatch.setenv("FLASK_ENV", "production")
    import app as flask_app_module
    importlib.reload(flask_app_module)
    prod_app = flask_app_module.create_app()
    with prod_app.test_client() as c:
        r = c.get("/api/templates/list")
        hsts = r.headers.get("Strict-Transport-Security", "")
        assert "max-age=" in hsts, f"HSTS manquant en mode production: {hsts!r}"
        assert "includeSubDomains" in hsts


def test_no_hsts_in_development_mode(monkeypatch):
    """A05 — HSTS absent en mode développement (évite les redirect loops)."""
    monkeypatch.setenv("FLASK_ENV", "development")
    import app as flask_app_module
    importlib.reload(flask_app_module)
    dev_app = flask_app_module.create_app()
    with dev_app.test_client() as c:
        r = c.get("/api/templates/list")
        hsts = r.headers.get("Strict-Transport-Security")
        assert hsts is None, f"HSTS ne devrait pas être posé en dev: {hsts!r}"
