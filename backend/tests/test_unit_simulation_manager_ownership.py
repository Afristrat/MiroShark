"""Tests unitaires US-092 — extension SimulationManager pour ownership.

Vérifie :
  - rétro-compat : `create_simulation()` sans `org_id` ne touche pas Supabase
  - extension : `create_simulation(org_id=…)` appelle bien
    `record_simulation_ownership`
  - `is_user_authorized_to_read` : ownership matching / non-matching
  - `list_simulations_for_org` : hydratation filesystem + tolérance à
    l'absence d'un dossier sim (status="missing")

Tous les helpers Supabase sont monkeypatchés.
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from app.services.simulation_manager import (
    SimulationManager,
    SimulationStatus,
)


@pytest.fixture
def sim_dir(tmp_path, monkeypatch):
    """Pointe la SIMULATION_DATA_DIR vers un tmp pour isoler les tests."""
    monkeypatch.setattr(
        SimulationManager, "SIMULATION_DATA_DIR", str(tmp_path),
    )
    return tmp_path


# ─── create_simulation — rétro-compatibilité ────────────────────────────────

class TestCreateSimulationLegacy:
    def test_no_org_id_does_not_touch_supabase(self, sim_dir, monkeypatch):
        sentinel = MagicMock(side_effect=AssertionError("should not be called"))
        monkeypatch.setattr(
            "app.auth.supabase_client.record_simulation_ownership",
            sentinel,
        )

        sm = SimulationManager()
        state = sm.create_simulation(project_id="proj1", graph_id="graph1")

        assert state.simulation_id.startswith("sim_")
        assert state.status == SimulationStatus.CREATED
        sentinel.assert_not_called()


# ─── create_simulation — extension multitenant ──────────────────────────────

class TestCreateSimulationOwnership:
    def test_org_id_triggers_ownership_recording(self, sim_dir, monkeypatch):
        captured: Dict[str, Any] = {}

        def fake_record(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr(
            "app.auth.supabase_client.record_simulation_ownership",
            fake_record,
        )

        sm = SimulationManager()
        state = sm.create_simulation(
            project_id="proj1",
            graph_id="graph1",
            org_id="org-uuid-1",
            created_by="user-uuid-1",
            package_id="crisis-drill-24h",
        )

        assert captured["simulation_id"] == state.simulation_id
        assert captured["org_id"] == "org-uuid-1"
        assert captured["user_id"] == "user-uuid-1"
        assert captured["package_id"] == "crisis-drill-24h"

    def test_enabled_platforms_reflects_flags_at_creation(self, sim_dir, monkeypatch):
        """US-222 : enabled_platforms dérivé des flags enable_* à la création."""
        captured: Dict[str, Any] = {}

        def fake_record(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr(
            "app.auth.supabase_client.record_simulation_ownership",
            fake_record,
        )

        sm = SimulationManager()
        sm.create_simulation(
            project_id="proj1",
            graph_id="graph1",
            enable_twitter=True,
            enable_reddit=False,
            enable_polymarket=True,
            org_id="org-uuid-1",
        )

        assert set(captured["enabled_platforms"]) == {"twitter", "polymarket"}
        assert "reddit" not in captured["enabled_platforms"]

    def test_enabled_platforms_empty_when_all_disabled(self, sim_dir, monkeypatch):
        captured: Dict[str, Any] = {}

        def fake_record(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr(
            "app.auth.supabase_client.record_simulation_ownership",
            fake_record,
        )

        sm = SimulationManager()
        sm.create_simulation(
            project_id="proj1",
            graph_id="graph1",
            enable_twitter=False,
            enable_reddit=False,
            enable_polymarket=False,
            org_id="org-uuid-1",
        )

        assert captured["enabled_platforms"] == []

    def test_supabase_failure_prevents_orphaned_creation(
        self, sim_dir, monkeypatch
    ):
        # Si Supabase est indisponible, la sim doit quand même être créée
        # côté filesystem. Le caller peut re-essayer le record plus tard.
        def _raise(**kwargs):
            raise RuntimeError("Supabase unreachable")

        monkeypatch.setattr(
            "app.auth.supabase_client.record_simulation_ownership",
            _raise,
        )

        sm = SimulationManager()
        with pytest.raises(RuntimeError, match="Supabase unreachable"):
            sm.create_simulation(
                project_id="proj1",
                graph_id="graph1",
                org_id="org-uuid-1",
            )
        assert list(sim_dir.iterdir()) == []

    def test_prediction_market_requires_ownership(self, sim_dir):
        sm = SimulationManager()
        with pytest.raises(ValueError, match="organization ownership"):
            sm.create_simulation(
                project_id="proj1",
                graph_id="graph1",
                enable_polymarket=True,
            )
        assert list(sim_dir.iterdir()) == []


# ─── is_user_authorized_to_read ─────────────────────────────────────────────

class TestIsUserAuthorizedToRead:
    def test_unowned_sim_is_public(self, sim_dir, monkeypatch):
        monkeypatch.setattr(
            "app.auth.supabase_client.get_simulation_owner",
            lambda sim_id, client=None: None,
        )
        sm = SimulationManager()
        assert sm.is_user_authorized_to_read(
            "sim_aaaaaaaaaaaa", "user-1"
        ) is True

    def test_user_in_owning_org_authorized(self, sim_dir, monkeypatch):
        monkeypatch.setattr(
            "app.auth.supabase_client.get_simulation_owner",
            lambda sim_id, client=None: {"org_id": "org-1"},
        )
        monkeypatch.setattr(
            "app.auth.supabase_client.get_user_role_in_org",
            lambda user_id, org_id, client=None: "admin"
            if (user_id == "user-1" and org_id == "org-1") else None,
        )
        sm = SimulationManager()
        assert sm.is_user_authorized_to_read(
            "sim_aaaaaaaaaaaa", "user-1"
        ) is True

    def test_user_not_in_owning_org_rejected(self, sim_dir, monkeypatch):
        monkeypatch.setattr(
            "app.auth.supabase_client.get_simulation_owner",
            lambda sim_id, client=None: {"org_id": "org-1"},
        )
        monkeypatch.setattr(
            "app.auth.supabase_client.get_user_role_in_org",
            lambda user_id, org_id, client=None: None,
        )
        sm = SimulationManager()
        assert sm.is_user_authorized_to_read(
            "sim_aaaaaaaaaaaa", "user-2"
        ) is False

    def test_supabase_error_fails_closed(self, sim_dir, monkeypatch):
        def _raise(*a, **kw):
            raise RuntimeError("network")

        monkeypatch.setattr(
            "app.auth.supabase_client.get_simulation_owner", _raise
        )
        sm = SimulationManager()
        assert sm.is_user_authorized_to_read(
            "sim_aaaaaaaaaaaa", "user-1"
        ) is False

    def test_owner_row_missing_org_id_rejected(self, sim_dir, monkeypatch):
        monkeypatch.setattr(
            "app.auth.supabase_client.get_simulation_owner",
            lambda sim_id, client=None: {"org_id": None},
        )
        sm = SimulationManager()
        assert sm.is_user_authorized_to_read(
            "sim_aaaaaaaaaaaa", "user-1"
        ) is False


# ─── list_simulations_for_org ───────────────────────────────────────────────

class TestListSimulationsForOrg:
    def test_returns_missing_when_filesystem_absent(
        self, sim_dir, monkeypatch
    ):
        # Stub la query Supabase : 1 sim référencée mais aucun dossier
        # filesystem associé.
        rows = [{
            "simulation_id": "sim_zzzzzzzzzzzz",
            "package_id": "crisis-drill-24h",
            "created_at": "2026-05-03T10:00:00Z",
            "is_published": False,
            "outcome": None,
            "brier_score": None,
            "created_by": "user-1",
        }]
        fake_response = MagicMock(data=rows)

        class _FakeTable:
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def order(self, *a, **kw): return self
            def execute(self): return fake_response

        class _FakeClient:
            def table(self, name): return _FakeTable()

        monkeypatch.setattr(
            "app.auth.supabase_client.get_supabase_admin",
            lambda: _FakeClient(),
        )

        sm = SimulationManager()
        result = sm.list_simulations_for_org("org-1")
        assert len(result) == 1
        assert result[0]["simulation_id"] == "sim_zzzzzzzzzzzz"
        assert result[0]["status"] == "missing"
        assert result[0]["package_id"] == "crisis-drill-24h"

    def test_hydrates_filesystem_state(self, sim_dir, monkeypatch):
        # Crée une vraie sim filesystem, puis stub Supabase pour qu'elle
        # soit listée.
        sm = SimulationManager()
        state = sm.create_simulation(project_id="p1", graph_id="g1")
        sim_id = state.simulation_id

        rows = [{
            "simulation_id": sim_id,
            "package_id": None,
            "created_at": "2026-05-03T10:00:00Z",
            "is_published": True,
            "outcome": {"label": "called_it"},
            "brier_score": 0.18,
            "created_by": "user-1",
        }]
        fake_response = MagicMock(data=rows)

        class _FakeTable:
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def order(self, *a, **kw): return self
            def execute(self): return fake_response

        class _FakeClient:
            def table(self, name): return _FakeTable()

        monkeypatch.setattr(
            "app.auth.supabase_client.get_supabase_admin",
            lambda: _FakeClient(),
        )

        result = sm.list_simulations_for_org("org-1")
        assert len(result) == 1
        row = result[0]
        assert row["simulation_id"] == sim_id
        assert row["status"] == SimulationStatus.CREATED.value
        assert row["is_published"] is True
        assert row["outcome"]["label"] == "called_it"
        assert row["brier_score"] == 0.18
        assert row["locale"] == "fr"

    def test_empty_org_returns_empty(self, sim_dir, monkeypatch):
        fake_response = MagicMock(data=[])

        class _FakeTable:
            def select(self, *a, **kw): return self
            def eq(self, *a, **kw): return self
            def order(self, *a, **kw): return self
            def execute(self): return fake_response

        class _FakeClient:
            def table(self, name): return _FakeTable()

        monkeypatch.setattr(
            "app.auth.supabase_client.get_supabase_admin",
            lambda: _FakeClient(),
        )

        sm = SimulationManager()
        assert sm.list_simulations_for_org("empty-org") == []
