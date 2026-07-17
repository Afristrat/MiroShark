"""Unit tests for US-007 — backend renvoie ``error_code`` structuré.

US-007 — Refactor des retours d'erreur Flask pour exposer un code SCREAMING_SNAKE_CASE
en plus du libellé texte historique. Le frontend mappe ce code vers
``$t('errors.<CODE>')`` via le helper ``frontend/src/utils/error-handler.js``,
ce qui permet enfin de localiser les erreurs critiques en français/arabe.

Backward-compat critique : la clé ``error`` reste TOUJOURS présente côté
backend pour ne pas casser les clients qui ne connaissent pas encore
``error_code``.

Ces tests vérifient sur quelques routes représentatives que :

  1. Un ``error_code`` SCREAMING_SNAKE_CASE est bien présent dans le payload.
  2. La clé ``error`` (fallback EN) est toujours présente.
  3. ``success`` reste à ``False``.
  4. Le code HTTP n'a pas changé.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


_SCREAMING_SNAKE_CASE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _assert_error_envelope(body, *, expected_code, http_status):
    """Tous les retours d'erreur US-007 doivent satisfaire ce contrat."""
    assert body is not None, "body must be JSON"
    assert body.get("success") is False, "success must be False"
    assert "error" in body, "error fallback string must always be present (backward-compat)"
    assert isinstance(body["error"], str) and body["error"], "error must be a non-empty string"
    assert "error_code" in body, "error_code must be present (US-007)"
    code = body["error_code"]
    assert _SCREAMING_SNAKE_CASE.match(code), (
        f"error_code must be SCREAMING_SNAKE_CASE, got {code!r}"
    )
    assert code == expected_code, f"expected error_code={expected_code}, got {code}"


# ─── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def app_client(monkeypatch, tmp_path):
    """Flask test client with downstream deps stubbed (storage, etc.)."""
    from app.config import Config as _Config

    monkeypatch.setattr(_Config, "WONDERWALL_SIMULATION_DATA_DIR", str(tmp_path))

    import app.storage as storage_mod

    class _NullStorage:
        def __init__(self, *a, **kw):
            pass

    monkeypatch.setattr(storage_mod, "Neo4jStorage", _NullStorage)

    from app import create_app
    app = create_app()
    app.testing = True
    # Default to no storage so STORAGE_UNAVAILABLE branches surface naturally.
    app.extensions["neo4j_storage"] = None
    return app, app.test_client()


# ─── Simulation routes ──────────────────────────────────────────────────


def test_simulation_create_missing_project_id(app_client):
    """``MISSING_PROJECT_ID`` when project_id is absent."""
    _, client = app_client
    resp = client.post("/api/simulation/create", json={})
    assert resp.status_code == 400
    _assert_error_envelope(resp.get_json(), expected_code="MISSING_PROJECT_ID", http_status=400)


def test_simulation_get_not_found(app_client, monkeypatch):
    """``SIMULATION_NOT_FOUND`` when the simulation ID doesn't resolve."""
    _, client = app_client
    import app.api.simulation as sim_api

    class _Manager:
        def get_simulation(self, sid):
            return None

    monkeypatch.setattr(sim_api, "SimulationManager", lambda: _Manager())
    resp = client.get("/api/simulation/sim_doesnotexist")
    assert resp.status_code == 404
    _assert_error_envelope(
        resp.get_json(), expected_code="SIMULATION_NOT_FOUND", http_status=404
    )


def test_simulation_branch_counterfactual_missing_field(app_client):
    """``MISSING_FIELD`` when injection_text is absent."""
    _, client = app_client
    resp = client.post(
        "/api/simulation/branch-counterfactual",
        json={},  # no parent_simulation_id, no injection_text
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["success"] is False
    assert body["error_code"] == "MISSING_FIELD"
    assert "error" in body


# ─── Graph routes ───────────────────────────────────────────────────────


def test_graph_get_project_not_found(app_client):
    """``PROJECT_NOT_FOUND`` from the project lookup endpoint."""
    _, client = app_client
    resp = client.get("/api/graph/project/proj_does_not_exist")
    assert resp.status_code == 404
    _assert_error_envelope(
        resp.get_json(), expected_code="PROJECT_NOT_FOUND", http_status=404
    )


def test_graph_fetch_url_missing_field(app_client):
    """``MISSING_FIELD`` when url is absent from the body."""
    _, client = app_client
    resp = client.post("/api/graph/fetch-url", json={})
    assert resp.status_code == 400
    _assert_error_envelope(
        resp.get_json(), expected_code="MISSING_FIELD", http_status=400
    )


def test_graph_build_storage_unavailable(app_client):
    """``STORAGE_UNAVAILABLE`` when Neo4j storage isn't initialized."""
    app, client = app_client
    app.extensions["neo4j_storage"] = None
    resp = client.post("/api/graph/build", json={"project_id": "proj_x"})
    assert resp.status_code == 503
    _assert_error_envelope(
        resp.get_json(), expected_code="STORAGE_UNAVAILABLE", http_status=503
    )


def test_graph_refine_entities_missing_graph_id(app_client):
    """``MISSING_GRAPH_ID`` when graph_id is absent (US-040 pre-existing code)."""
    app, client = app_client
    app.extensions["neo4j_storage"] = object()  # any non-None storage
    resp = client.post("/api/graph/entities/refine", json={})
    assert resp.status_code == 400
    _assert_error_envelope(
        resp.get_json(), expected_code="MISSING_GRAPH_ID", http_status=400
    )


# ─── Report routes ──────────────────────────────────────────────────────


def test_report_generate_missing_simulation_id(app_client):
    """``MISSING_SIMULATION_ID`` when no simulation_id in body."""
    _, client = app_client
    resp = client.post("/api/report/generate", json={})
    assert resp.status_code == 400
    _assert_error_envelope(
        resp.get_json(), expected_code="MISSING_SIMULATION_ID", http_status=400
    )


def test_report_get_not_found(app_client):
    """``REPORT_NOT_FOUND`` when the report id is unknown."""
    _, client = app_client
    resp = client.get("/api/report/report_doesnotexist")
    assert resp.status_code == 404
    _assert_error_envelope(
        resp.get_json(), expected_code="REPORT_NOT_FOUND", http_status=404
    )


# ─── Settings routes ────────────────────────────────────────────────────


def test_settings_invalid_preset(app_client, monkeypatch):
    """``INVALID_INPUT`` when preset name isn't in the allowed list."""
    import app.auth.decorators as auth_decorators

    monkeypatch.setenv("BASSIRA_SUPER_ADMIN_EMAILS", "admin@example.test")
    monkeypatch.setattr(
        auth_decorators,
        "verify_supabase_jwt",
        lambda _token: {"sub": "user-admin", "email": "admin@example.test"},
    )
    _, client = app_client
    resp = client.post(
        "/api/settings",
        headers={"Authorization": "Bearer test-token"},
        json={"preset": "definitely_not_a_preset"},
    )
    assert resp.status_code == 400
    _assert_error_envelope(
        resp.get_json(), expected_code="INVALID_INPUT", http_status=400
    )


# ─── Backward-compat ────────────────────────────────────────────────────


def test_backward_compat_error_key_always_present(app_client):
    """A client that only knows the legacy ``error`` key must still work.

    Sweep a handful of error endpoints and check ``error`` is always a
    non-empty string — the new ``error_code`` is purely additive.
    """
    _, client = app_client

    cases = [
        ("POST", "/api/simulation/create", {}),
        ("POST", "/api/simulation/branch-counterfactual", {}),
        ("GET", "/api/graph/project/proj_x", None),
        ("POST", "/api/graph/fetch-url", {}),
        ("POST", "/api/report/generate", {}),
    ]

    for method, path, payload in cases:
        if method == "POST":
            resp = client.post(path, json=payload)
        else:
            resp = client.get(path)
        body = resp.get_json()
        assert body is not None, f"{method} {path}: not JSON"
        assert body.get("success") is False, f"{method} {path}: success!=False"
        assert isinstance(body.get("error"), str) and body["error"], (
            f"{method} {path}: error key missing or empty"
        )
        assert isinstance(body.get("error_code"), str) and body["error_code"], (
            f"{method} {path}: error_code missing or empty"
        )
