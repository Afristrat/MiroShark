"""Tests de non-régression pour les failles d'autorisation P0."""

import pytest


@pytest.fixture
def app_client(monkeypatch, tmp_path):
    from app.config import Config

    monkeypatch.setattr(Config, "WONDERWALL_SIMULATION_DATA_DIR", str(tmp_path))

    import app.storage as storage_mod

    class NullStorage:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(storage_mod, "Neo4jStorage", NullStorage)

    from app import create_app

    app = create_app()
    app.testing = True
    app.extensions["neo4j_storage"] = None
    return app.test_client()


def test_settings_rejects_anonymous_read(app_client):
    response = app_client.get("/api/settings")

    assert response.status_code == 401
    assert response.get_json()["error_code"] == "MISSING_AUTH"


def test_settings_rejects_anonymous_update(app_client):
    response = app_client.post(
        "/api/settings",
        json={"llm": {"base_url": "https://attacker.example/v1"}},
    )

    assert response.status_code == 401
    assert response.get_json()["error_code"] == "MISSING_AUTH"
