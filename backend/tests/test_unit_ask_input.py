"""Validation des bornes d'entrée du parcours console « Posez simplement »."""

import importlib

import pytest


@pytest.fixture(scope="module")
def client():
    """Client Flask isolé, sans dépendance externe."""
    import app as flask_app_module

    importlib.reload(flask_app_module)
    return flask_app_module.create_app().test_client()


def test_ask_rejects_only_input_above_rich_brief_limit(client):
    """Le plafond doit accepter un brief complet, pas seulement un titre."""
    from app.api.simulation import _ASK_QUESTION_MAX_CHARS

    response = client.post(
        "/api/simulation/ask",
        json={"question": "x" * (_ASK_QUESTION_MAX_CHARS + 1)},
    )

    assert response.status_code == 400
    assert response.get_json()["error_code"] == "INVALID_INPUT"
