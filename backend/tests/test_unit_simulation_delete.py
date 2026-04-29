"""Unit tests for ``DELETE /api/simulation/<id>`` (US-049).

Verifies the deletion endpoint added to wipe a simulation from the
history (directory + state.json + profiles + trajectory + outcome).

Three contractual paths must hold:

  1. Existing sim → 200 ``{deleted: true}``, directory gone afterwards.
  2. Already-absent sim → 200 ``{deleted: false}`` (idempotent — the
     resource is gone either way, so the client can issue the same
     DELETE twice without surfacing a 404 spam in the UI).
  3. Running sim → 409 ``error_code=SIMULATION_RUNNING`` with the
     directory left intact so the runner doesn't crash mid-trajectory.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ─── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def sim_client(monkeypatch, tmp_path):
    """Flask test client with WONDERWALL_SIMULATION_DATA_DIR pointed at
    a temp directory so each test starts hermetic."""
    from app.config import Config as _Config

    monkeypatch.setattr(_Config, "WONDERWALL_SIMULATION_DATA_DIR", str(tmp_path))

    # SimulationManager reads the dir from the same Config attribute via
    # SimulationManager.SIMULATION_DATA_DIR — patch the class attribute too.
    from app.services.simulation_manager import SimulationManager
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(tmp_path))

    import app.storage as storage_mod

    class _NullStorage:
        def __init__(self, *a, **kw):
            pass

    monkeypatch.setattr(storage_mod, "Neo4jStorage", _NullStorage)

    from app import create_app
    app = create_app()
    app.testing = True
    return tmp_path, app.test_client()


def _seed_sim(tmp_path: Path, sim_id: str, status: str = "created") -> Path:
    """Drop a fake simulation directory with a minimal state.json so
    the manager picks it up via list_simulations."""
    sim_dir = tmp_path / sim_id
    sim_dir.mkdir()
    (sim_dir / "state.json").write_text(
        json.dumps({
            "simulation_id": sim_id,
            "project_id": "proj_test",
            "graph_id": "graph_xyz",
            "status": status,
            "created_at": "2026-04-29T18:00:00",
            "config_generated": False,
            "is_public": False,
        }),
        encoding="utf-8",
    )
    # Sprinkle a couple of artefacts so we can verify shutil.rmtree
    # actually wipes the whole directory, not just state.json.
    (sim_dir / "trajectory.json").write_text("[]", encoding="utf-8")
    (sim_dir / "profiles" / "reddit").mkdir(parents=True)
    (sim_dir / "profiles" / "reddit" / "agent_001.json").write_text("{}", encoding="utf-8")
    return sim_dir


# ─── Tests ─────────────────────────────────────────────────────────────


def test_delete_existing_simulation_removes_directory(sim_client):
    """Existing sim → 200 {deleted:true} and the directory is gone."""
    tmp_path, client = sim_client
    sim_dir = _seed_sim(tmp_path, "sim_to_remove")
    assert sim_dir.exists()

    resp = client.delete("/api/simulation/sim_to_remove")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["simulation_id"] == "sim_to_remove"
    assert body["data"]["deleted"] is True
    assert not sim_dir.exists()


def test_delete_absent_simulation_is_idempotent(sim_client):
    """Sim that never existed → 200 {deleted:false} (idempotent).

    The point: a flaky client can hammer DELETE without seeing 404
    spam in the UI; the resource is gone either way."""
    _, client = sim_client
    resp = client.delete("/api/simulation/sim_never_existed")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["deleted"] is False


def test_delete_running_simulation_returns_409(sim_client):
    """Running sim → 409 SIMULATION_RUNNING, directory preserved."""
    tmp_path, client = sim_client
    sim_dir = _seed_sim(tmp_path, "sim_active", status="running")

    resp = client.delete("/api/simulation/sim_active")
    assert resp.status_code == 409
    body = resp.get_json()
    assert body["success"] is False
    assert body["error_code"] == "SIMULATION_RUNNING"
    assert "stop" in body["error"].lower()
    # Directory must still be there — we don't want to corrupt an
    # active trajectory by half-deleting state.
    assert sim_dir.exists()


def test_delete_double_call_second_is_idempotent(sim_client):
    """First call deletes (200 deleted:true), second sees nothing
    (200 deleted:false). Useful for retry logic in the UI."""
    tmp_path, client = sim_client
    _seed_sim(tmp_path, "sim_twice")

    first = client.delete("/api/simulation/sim_twice")
    assert first.status_code == 200
    assert first.get_json()["data"]["deleted"] is True

    second = client.delete("/api/simulation/sim_twice")
    assert second.status_code == 200
    assert second.get_json()["data"]["deleted"] is False


def test_delete_completed_simulation_succeeds(sim_client):
    """Status completed/stopped/failed/paused all wipe cleanly —
    only RUNNING is special-cased."""
    tmp_path, client = sim_client
    for status in ("completed", "stopped", "failed", "paused", "ready"):
        sim_id = f"sim_{status}"
        _seed_sim(tmp_path, sim_id, status=status)
        resp = client.delete(f"/api/simulation/{sim_id}")
        assert resp.status_code == 200, f"status={status} should be deletable"
        assert resp.get_json()["data"]["deleted"] is True


def test_delete_does_not_affect_other_simulations(sim_client):
    """Deleting sim_A must not touch sim_B's directory — basic sanity
    check that the path scoping is correct."""
    tmp_path, client = sim_client
    _seed_sim(tmp_path, "sim_keep")
    _seed_sim(tmp_path, "sim_drop")

    resp = client.delete("/api/simulation/sim_drop")
    assert resp.status_code == 200
    assert (tmp_path / "sim_keep").exists()
    assert not (tmp_path / "sim_drop").exists()
