"""Unit tests for POST /api/simulation/<id>/profiles.

Coverage:
  1. 400 when ``name`` is missing from the request body.
  2. 404 when the simulation directory does not exist.
  3. 200 + created profile returned (filesystem mocked in-memory).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ---------------------------------------------------------------------------
# Minimal Flask app exposing only the add_simulation_profile view.
# We cannot boot the full application (Neo4j, simulation runner) in unit
# tests, so we mount just the one route we need.
# ---------------------------------------------------------------------------

def _make_app(monkeypatch: pytest.MonkeyPatch):
    """Build a minimal Flask app with the ``add_simulation_profile`` view."""
    from flask import Flask
    from app.api.simulation import add_simulation_profile, simulation_bp

    app = Flask(__name__)
    app.register_blueprint(simulation_bp, url_prefix="/api/simulation")

    # Provide a valid admin token so auth does not block the happy-path tests.
    monkeypatch.setenv("BASSIRA_ADMIN_TOKEN", "test-secret")

    return app


# ---------------------------------------------------------------------------
# Test 1 — 400 when name is missing
# ---------------------------------------------------------------------------

def test_add_profile_missing_name_returns_400(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Sending a body without ``name`` must yield 400 / MISSING_FIELD."""
    app = _make_app(monkeypatch)

    # Point SimulationManager._get_simulation_dir at a real temp directory
    # so the 404 branch is not hit before the validation branch.
    sim_dir = tmp_path / "sim-abc"
    sim_dir.mkdir()

    with patch("app.api.simulation.SimulationManager") as MockManager:
        instance = MockManager.return_value
        instance._get_simulation_dir.return_value = str(sim_dir)

        client = app.test_client()
        res = client.post(
            "/api/simulation/sim-abc/profiles",
            json={"profession": "Journaliste"},
            headers={"Authorization": "Bearer test-secret"},
        )

    assert res.status_code == 400
    body = res.get_json()
    assert body["success"] is False
    assert body["error_code"] == "MISSING_FIELD"
    assert "name" in body["error"].lower()


# ---------------------------------------------------------------------------
# Test 2 — 404 when simulation directory does not exist
# ---------------------------------------------------------------------------

def test_add_profile_unknown_sim_returns_404(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """If the simulation directory is absent, the endpoint must return 404."""
    app = _make_app(monkeypatch)

    # Return a path that does NOT exist.
    non_existent = str(tmp_path / "ghost-sim")

    with patch("app.api.simulation.SimulationManager") as MockManager:
        instance = MockManager.return_value
        instance._get_simulation_dir.return_value = non_existent

        client = app.test_client()
        res = client.post(
            "/api/simulation/ghost-sim/profiles",
            json={"name": "Alice"},
            headers={"Authorization": "Bearer test-secret"},
        )

    assert res.status_code == 404
    body = res.get_json()
    assert body["success"] is False
    assert body["error_code"] == "SIM_NOT_FOUND"


# ---------------------------------------------------------------------------
# Test 3 — 200 + profile returned + file written
# ---------------------------------------------------------------------------

def test_add_profile_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Happy path: valid body, existing sim directory → 200 + profile saved."""
    app = _make_app(monkeypatch)

    sim_dir = tmp_path / "sim-ok"
    sim_dir.mkdir()

    with patch("app.api.simulation.SimulationManager") as MockManager:
        instance = MockManager.return_value
        instance._get_simulation_dir.return_value = str(sim_dir)

        client = app.test_client()
        res = client.post(
            "/api/simulation/sim-ok/profiles",
            json={
                "name": "karim_b",
                "username": "Karim Benali",
                "profession": "Journaliste",
                "bio": "Journaliste d'investigation basé à Casablanca.",
                "stance": "bearish",
                "interested_topics": ["politique", "économie"],
            },
            headers={"Authorization": "Bearer test-secret"},
        )

    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True

    profile = body["data"]
    assert profile["name"] == "karim_b"
    assert profile["username"] == "Karim Benali"
    assert profile["profession"] == "Journaliste"
    assert profile["stance"] == "bearish"
    assert profile["manually_added"] is True
    assert "id" in profile
    assert "politique" in profile["interested_topics"]

    # Verify the profile was persisted to disk.
    profiles_path = sim_dir / "agent_profiles.json"
    assert profiles_path.exists()
    saved = json.loads(profiles_path.read_text(encoding="utf-8"))
    assert isinstance(saved, list)
    assert len(saved) == 1
    assert saved[0]["name"] == "karim_b"
