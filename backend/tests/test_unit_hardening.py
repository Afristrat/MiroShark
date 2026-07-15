"""Tests pour le hardening prod (US-031, US-032, US-033, US-207).

Ces tests vérifient que :
- Config.DEBUG défaut à False (US-033)
- Config.validate() refuse de booter sans SECRET_KEY en mode production (US-031)
- Config.validate() tolère SECRET_KEY absent en FLASK_ENV=development (US-031)
- CORS lit CORS_ORIGINS depuis l'env (US-032)
- Config.validate() refuse de booter sur NEO4J_PASSWORD/FLASK_DEBUG par défaut
  dangereux hors développement (US-207, ADR-006)
"""

from __future__ import annotations

import importlib



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


def test_validate_warns_but_tolerates_missing_secret_key(monkeypatch, caplog):
    """US-031 (relaxé) : sans SECRET_KEY, on warn fort mais on ne bloque pas
    le boot — Coolify env-var injection est trop flaky pour qu'on veuille
    refuser de démarrer. La sécurité reste assurée par le fallback random
    per-process (sessions valides le temps de la vie du container).
    """
    import logging
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('LLM_API_KEY', 'dummy')
    monkeypatch.setenv('NEO4J_URI', 'bolt://localhost:7687')
    monkeypatch.setenv('NEO4J_PASSWORD', 'dummy')
    Config = _reload_config()
    with caplog.at_level(logging.WARNING, logger='app.config'):
        errors = Config.validate()
    assert not any('SECRET_KEY' in e for e in errors), (
        f"SECRET_KEY ne doit plus être bloquant, got {errors!r}"
    )
    assert any('SECRET_KEY missing' in r.message for r in caplog.records), (
        "un warning SECRET_KEY missing doit être loggé"
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


def test_validate_refuses_default_neo4j_password_outside_dev(monkeypatch):
    """US-207/ADR-006 : NEO4J_PASSWORD='miroshark' (défaut connu) hors dev
    doit bloquer le boot."""
    monkeypatch.delenv('NEO4J_PASSWORD', raising=False)
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('LLM_API_KEY', 'dummy')
    monkeypatch.setenv('NEO4J_URI', 'bolt://localhost:7687')
    Config = _reload_config()
    assert Config.NEO4J_PASSWORD == 'miroshark'
    errors = Config.validate()
    assert any('NEO4J_PASSWORD' in e and 'default' in e for e in errors), (
        f"NEO4J_PASSWORD par défaut doit être bloquant en production, got {errors!r}"
    )


def test_validate_tolerates_default_neo4j_password_in_dev(monkeypatch):
    """US-207/ADR-006 : le même défaut est toléré en FLASK_ENV=development
    (docker-compose.yml et .env locaux s'appuient dessus)."""
    monkeypatch.delenv('NEO4J_PASSWORD', raising=False)
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.setenv('LLM_API_KEY', 'dummy')
    monkeypatch.setenv('NEO4J_URI', 'bolt://localhost:7687')
    Config = _reload_config()
    errors = Config.validate()
    assert not any('NEO4J_PASSWORD' in e and 'default' in e for e in errors)


def test_validate_accepts_non_default_neo4j_password_in_prod(monkeypatch):
    """US-207/ADR-006 : un mot de passe non-défaut passe sans erreur en prod."""
    monkeypatch.setenv('NEO4J_PASSWORD', 'a-real-secret')
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('LLM_API_KEY', 'dummy')
    monkeypatch.setenv('NEO4J_URI', 'bolt://localhost:7687')
    Config = _reload_config()
    errors = Config.validate()
    assert not any('NEO4J_PASSWORD' in e for e in errors)


def test_validate_refuses_flask_debug_outside_dev(monkeypatch):
    """US-207/ADR-006 : FLASK_DEBUG=true hors dev doit bloquer le boot
    (pattern restart-loop déjà payé, cf. progress.md)."""
    monkeypatch.setenv('FLASK_DEBUG', 'true')
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('LLM_API_KEY', 'dummy')
    monkeypatch.setenv('NEO4J_URI', 'bolt://localhost:7687')
    monkeypatch.setenv('NEO4J_PASSWORD', 'a-real-secret')
    Config = _reload_config()
    errors = Config.validate()
    assert any('FLASK_DEBUG' in e for e in errors), (
        f"FLASK_DEBUG=true doit être bloquant en production, got {errors!r}"
    )


def test_validate_tolerates_flask_debug_in_dev(monkeypatch):
    """US-207/ADR-006 : FLASK_DEBUG=true reste toléré en développement."""
    monkeypatch.setenv('FLASK_DEBUG', 'true')
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.setenv('LLM_API_KEY', 'dummy')
    monkeypatch.setenv('NEO4J_URI', 'bolt://localhost:7687')
    monkeypatch.setenv('NEO4J_PASSWORD', 'a-real-secret')
    Config = _reload_config()
    errors = Config.validate()
    assert not any('FLASK_DEBUG' in e for e in errors)


def test_cors_origins_default_includes_prod_and_local(monkeypatch):
    """US-032 : CORS_ORIGINS par défaut inclut prod tunnel + localhost dev."""
    monkeypatch.delenv('CORS_ORIGINS', raising=False)
    # Reload app to pick up env
    import app
    importlib.reload(app)
    flask_app = app.create_app()

    # Récupère les origins effectives via flask-cors (stockées sur l'app)
    # flask-cors stocke la config sous _options ou via app.config
    # On lit plutôt via la requête pour valider en bout de chaîne :
    client = flask_app.test_client()
    response = client.options(
        '/api/templates/list',
        headers={
            'Origin': 'https://bassira.ma',
            'Access-Control-Request-Method': 'GET',
        },
    )
    # 200 ou 204 attendu selon flask-cors
    assert response.status_code in (200, 204)
    allow_origin = response.headers.get('Access-Control-Allow-Origin', '')
    assert 'bassira.ma' in allow_origin or allow_origin == '*', (
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
