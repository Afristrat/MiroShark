"""Tests pour US-034 (security headers).

Vérifie que les headers HTTP de sécurité sont bien posés sur les
endpoints API mais pas sur les routes embeddables (share, embed,
share-card.png, replay.gif) qui doivent pouvoir vivre dans une iframe
tierce (Slack/Discord/Twitter unfurl).
"""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture(scope="module")
def client():
    import app
    importlib.reload(app)
    flask_app = app.create_app()
    return flask_app.test_client()


def test_api_route_has_xframe_sameorigin(client):
    """Les routes /api/* renvoient X-Frame-Options: SAMEORIGIN."""
    r = client.get('/api/templates/list')
    # 200 ou 503 selon la dispo de Neo4j ; on vérifie surtout les headers
    assert r.headers.get('X-Frame-Options') == 'SAMEORIGIN'


def test_api_route_has_nosniff(client):
    r = client.get('/api/templates/list')
    assert r.headers.get('X-Content-Type-Options') == 'nosniff'


def test_api_route_has_referrer_policy(client):
    r = client.get('/api/templates/list')
    assert r.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'


def test_api_route_has_permissions_policy(client):
    r = client.get('/api/templates/list')
    perms = r.headers.get('Permissions-Policy', '')
    assert 'camera=()' in perms
    assert 'microphone=()' in perms
    assert 'geolocation=()' in perms


def test_share_route_does_not_have_xframe(client):
    """Les routes /share/* doivent pouvoir s'embedder partout."""
    r = client.get('/share/notarealsim')
    # 404 attendu (sim inexistante) — peu importe, on regarde les headers
    assert r.headers.get('X-Frame-Options') is None, (
        "X-Frame-Options ne doit pas être posé sur /share/* "
        f"(reçu: {r.headers.get('X-Frame-Options')!r})"
    )


def test_share_card_does_not_have_xframe(client):
    """Les share-cards PNG doivent pouvoir s'embedder."""
    r = client.get('/api/simulation/notarealsim/share-card.png')
    assert r.headers.get('X-Frame-Options') is None


def test_csp_present_on_api(client):
    """CSP appliqué aux endpoints non-embeddables."""
    r = client.get('/api/templates/list')
    csp = r.headers.get('Content-Security-Policy', '')
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'self'" in csp


def test_csp_not_on_share(client):
    """Pas de CSP sur les routes embeddables (sinon iframe casse)."""
    r = client.get('/share/notarealsim')
    assert r.headers.get('Content-Security-Policy') is None
