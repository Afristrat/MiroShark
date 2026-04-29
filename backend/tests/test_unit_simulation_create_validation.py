"""Unit tests for ``POST /api/simulation/create`` graph validation (US-047).

US-047 — Validation graph non-vide à /api/simulation/create + UI préventive.

Avant US-047, créer une simulation avec un ``graph_id`` qui pointe vers un
graphe Neo4j sans entités définies passait la création (200 OK), puis
échouait silencieusement à la phase /prepare avec ``« No matching entities
found »`` — d'où une UX dégradée du Step 03 (cf commit 2399f99 et l'incident
sim_cc793c9c99b5 en prod).

Ces tests vérifient que :

  1. Un graphe vide ⇒ 400 ``error_code=GRAPH_EMPTY`` (fail-fast).
  2. Un graphe peuplé ⇒ 200 (pas de régression).
  3. Si le pre-check échoue (Neo4j down, etc.), on ne bloque pas la création
     — le manager renverra ensuite l'erreur explicite. Politique « non
     bloquant » volontaire pour ne pas masquer un crash storage par une
     fausse erreur de validation.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ─── Fakes ──────────────────────────────────────────────────────────────


class _FakeProject:
    def __init__(self, project_id: str, graph_id: str | None = "graph_xyz"):
        self.project_id = project_id
        self.graph_id = graph_id


class _FakeFilteredResult:
    def __init__(self, count: int):
        self.filtered_count = count
        self.entities = []
        self.entity_types = set()


class _FakeReader:
    def __init__(self, count: int = 0):
        self._count = count

    def filter_defined_entities(self, graph_id: str, **kwargs):
        return _FakeFilteredResult(self._count)


class _FakeSimState:
    def to_dict(self):
        return {"simulation_id": "sim_fake", "status": "created"}


# ─── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def simulation_client(monkeypatch, tmp_path):
    """Flask test client with all downstream deps stubbed.

    The endpoint reads ``current_app.extensions['neo4j_storage']``; we
    replace it with a sentinel and patch ``EntityReader`` on the import
    site so the route picks up our fake. ``ProjectManager`` and
    ``SimulationManager`` are patched per-test by the helper below.
    """
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
    # Force a non-None storage so the pre-check branch is exercised.
    app.extensions["neo4j_storage"] = object()
    return app, app.test_client()


def _patch_create_dependencies(monkeypatch, *, entity_count: int, project_exists: bool = True,
                                raise_on_reader: bool = False):
    """Patch the import-site references the create endpoint walks through."""
    import app.api.simulation as sim_api

    # ProjectManager.get_project
    def _get_project(pid):
        return _FakeProject(pid) if project_exists else None
    monkeypatch.setattr(sim_api.ProjectManager, "get_project", staticmethod(_get_project))

    # EntityReader — either the fake reader or a class that raises
    if raise_on_reader:
        class _BoomReader:
            def __init__(self, *a, **kw):
                raise RuntimeError("Neo4j down")
        monkeypatch.setattr(sim_api, "EntityReader", _BoomReader)
    else:
        monkeypatch.setattr(sim_api, "EntityReader",
                            lambda storage: _FakeReader(entity_count))

    # SimulationManager.create_simulation — only called on the happy path
    class _FakeManager:
        def create_simulation(self, **kwargs):
            return _FakeSimState()
    monkeypatch.setattr(sim_api, "SimulationManager", lambda: _FakeManager())


# ─── Tests ──────────────────────────────────────────────────────────────


def test_create_rejects_empty_graph(simulation_client, monkeypatch):
    """Graph with zero defined entities ⇒ 400 ``GRAPH_EMPTY``."""
    _, client = simulation_client
    _patch_create_dependencies(monkeypatch, entity_count=0)

    resp = client.post(
        "/api/simulation/create",
        json={"project_id": "proj_test", "graph_id": "graph_xyz"},
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["success"] is False
    assert body["error_code"] == "GRAPH_EMPTY"
    assert "no defined entities" in body["error"].lower()


def test_create_accepts_populated_graph(simulation_client, monkeypatch):
    """Graph with > 0 entities ⇒ 200 (no regression on the happy path)."""
    _, client = simulation_client
    _patch_create_dependencies(monkeypatch, entity_count=5)

    resp = client.post(
        "/api/simulation/create",
        json={"project_id": "proj_test", "graph_id": "graph_xyz"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["simulation_id"] == "sim_fake"


def test_create_does_not_block_on_pre_check_failure(simulation_client, monkeypatch):
    """If the pre-check itself errors (Neo4j down, malformed graph_id),
    we let the manager handle it rather than masking the real cause behind
    a ``GRAPH_EMPTY`` false positive."""
    _, client = simulation_client
    _patch_create_dependencies(monkeypatch, entity_count=0, raise_on_reader=True)

    resp = client.post(
        "/api/simulation/create",
        json={"project_id": "proj_test", "graph_id": "graph_xyz"},
    )
    # Manager succeeds in this fake setup, so we expect 200. The point
    # of the test is that we don't surface a GRAPH_EMPTY when the
    # pre-check itself crashed.
    assert resp.status_code == 200
    body = resp.get_json()
    assert body.get("error_code") != "GRAPH_EMPTY"


def test_create_rejects_missing_project_id(simulation_client):
    """Existing contract preserved — project_id is mandatory."""
    _, client = simulation_client
    resp = client.post("/api/simulation/create", json={})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["success"] is False
    assert "project_id" in body["error"]


def test_create_rejects_missing_graph_id(simulation_client, monkeypatch):
    """Existing contract preserved — when no graph is built yet,
    we surface ``error_code=GRAPH_NOT_BUILT`` (US-047 also tagged this
    branch with a code so the frontend can localize it)."""
    _, client = simulation_client
    import app.api.simulation as sim_api

    monkeypatch.setattr(
        sim_api.ProjectManager, "get_project",
        staticmethod(lambda pid: _FakeProject(pid, graph_id=None)),
    )

    resp = client.post(
        "/api/simulation/create",
        json={"project_id": "proj_test"},
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["success"] is False
    assert body["error_code"] == "GRAPH_NOT_BUILT"
