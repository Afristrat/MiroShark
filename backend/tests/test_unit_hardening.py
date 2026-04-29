"""Tests pour le hardening prod (US-031, US-032, US-033).

Ces tests vérifient que :
- Config.DEBUG défaut à False (US-033)
- Config.validate() refuse de booter sans SECRET_KEY en mode production (US-031)
- Config.validate() tolère SECRET_KEY absent en FLASK_ENV=development (US-031)
- CORS lit CORS_ORIGINS depuis l'env (US-032)
"""

from __future__ import annotations

import importlib
import os

import pytest


def _reload_config():
    """Recharger app.config pour qu'il relise os.environ."""
    import app.config as config_module
    importlib.reload(config_module)
    return config_module.Config


def test_debug_defaults_to_false(monkeypatch):
    """US-033 : sans FLASK_DEBUG défini, DEBUG est False."""
    monkeypatch.delenv('FLASK_DEBUG', raising=False)
    Config = _reload_config()
    assert Config.DEBUG is False


def test_debug_explicit_true(monkeypatch):
    """US-033 : FLASK_DEBUG=true active bien le mode debug."""
    monkeypatch.setenv('FLASK_DEBUG', 'true')
    Config = _reload_config()
    assert Config.DEBUG is True


def test_validate_fails_without_secret_key_in_production(monkeypatch):
    """US-031 : en production, l'absence de SECRET_KEY est une erreur."""
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('LLM_API_KEY', 'dummy')
    monkeypatch.setenv('NEO4J_URI', 'bolt://localhost:7687')
    monkeypatch.setenv('NEO4J_PASSWORD', 'dummy')
    Config = _reload_config()
    errors = Config.validate()
    assert any('SECRET_KEY' in e for e in errors), (
        f"expected SECRET_KEY error in {errors!r}"
    )


def test_validate_tolerates_missing_secret_key_in_development(monkeypatch):
    """US-031 : en dev, SECRET_KEY manquant est toléré (warning seulement)."""
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.setenv('LLM_API_KEY', 'dummy')
    monkeypatch.setenv('NEO4J_URI', 'bolt://localhost:7687')
    monkeypatch.setenv('NEO4J_PASSWORD', 'dummy')
    Config = _reload_config()
    errors = Config.validate()
    assert not any('SECRET_KEY' in e for e in errors), (
        f"SECRET_KEY ne doit pas être une erreur en dev, got {errors!r}"
    )


def test_validate_accepts_explicit_secret_key(monkeypatch):
    """US-031 : SECRET_KEY défini → pas d'erreur, indépendamment de FLASK_ENV."""
    monkeypatch.setenv('SECRET_KEY', 'a' * 64)
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('LLM_API_KEY', 'dummy')
    monkeypatch.setenv('NEO4J_URI', 'bolt://localhost:7687')
    monkeypatch.setenv('NEO4J_PASSWORD', 'dummy')
    Config = _reload_config()
    errors = Config.validate()
    assert not any('SECRET_KEY' in e for e in errors)


def test_cors_origins_default_includes_prod_and_local(monkeypatch):
    """US-032 : CORS_ORIGINS par défaut inclut prod tunnel + localhost dev."""
    monkeypatch.delenv('CORS_ORIGINS', raising=False)
    # Reload app to pick up env
    import app
    importlib.reload(app)
    flask_app = app.create_app()

    # Récupère les origins effectives via flask-cors (stockées sur l'app)
    cors_config = flask_app.extensions.get('cors')
    # flask-cors stocke la config sous _options ou via app.config
    # On lit plutôt via la requête pour valider en bout de chaîne :
    client = flask_app.test_client()
    response = client.options(
        '/api/templates/list',
        headers={
            'Origin': 'https://prospectives.ai-mpower.com',
            'Access-Control-Request-Method': 'GET',
        },
    )
    # 200 ou 204 attendu selon flask-cors
    assert response.status_code in (200, 204)
    allow_origin = response.headers.get('Access-Control-Allow-Origin', '')
    assert 'prospectives.ai-mpower.com' in allow_origin or allow_origin == '*', (
        f"unexpected Allow-Origin: {allow_origin!r}"
    )


def test_cors_origins_from_env(monkeypatch):
    """US-032 : CORS_ORIGINS env override le défaut."""
    monkeypatch.setenv('CORS_ORIGINS', 'https://example.com,https://other.test')
    import app
    importlib.reload(app)
    flask_app = app.create_app()

    client = flask_app.test_client()
    response = client.options(
        '/api/templates/list',
        headers={
            'Origin': 'https://example.com',
            'Access-Control-Request-Method': 'GET',
        },
    )
    assert response.status_code in (200, 204)
    allow_origin = response.headers.get('Access-Control-Allow-Origin', '')
    assert 'example.com' in allow_origin or allow_origin == '*'
