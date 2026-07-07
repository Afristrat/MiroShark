"""Tests unitaires US-092 — endpoints /api/client/* + /api/calibration/aggregates.

Tous les helpers Supabase sont monkeypatchés pour fournir des données
fictives. Aucune connexion live à Supabase.
"""

from __future__ import annotations

import time
from typing import Any, Dict
from unittest.mock import MagicMock

import jwt as pyjwt
import pytest

from app import create_app
from app.auth import jwt_verifier


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_jwt_cache():
    jwt_verifier._cache_clear()
    yield
    jwt_verifier._cache_clear()


@pytest.fixture
def jwt_secret(monkeypatch):
    secret = "client-tests-secret"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    return secret


@pytest.fixture
def admin_user_id() -> str:
    return "user-admin-uuid-1234"


@pytest.fixture
def member_user_id() -> str:
    return "user-member-uuid-5678"


@pytest.fixture
def org_id() -> str:
    return "org-aimpower-bassira-uuid"


def _make_token(secret: str, sub: str, email: str = "user@aimpower.org") -> str:
    now = int(time.time())
    return pyjwt.encode(
        {
            "sub": sub,
            "email": email,
            "aud": "authenticated",
            "role": "authenticated",
            "iat": now,
            "exp": now + 3600,
        },
        secret,
        algorithm="HS256",
    )


@pytest.fixture
def app(monkeypatch):
    """Construit l'app Flask complète sans dépendre de Neo4j."""
    # Évite l'init Neo4j en monkeypatchant `Neo4jStorage` à None.
    from app import storage as storage_pkg

    class _DummyStorage:
        def __init__(self, *a, **kw):
            pass

    monkeypatch.setattr(storage_pkg, "Neo4jStorage", _DummyStorage)
    app_obj = create_app()
    app_obj.config["TESTING"] = True
    return app_obj


@pytest.fixture
def client(app):
    return app.test_client()


# ─── Helpers ────────────────────────────────────────────────────────────────

def _patch_orgs(monkeypatch, *, admin_user_id, org_id, role="owner"):
    """Patche `get_user_orgs` pour rendre `admin_user_id` admin de `org_id`."""
    def _fake_get_user_orgs(user_id, client=None):
        if user_id == admin_user_id:
            return [{
                "id": org_id,
                "slug": "aimpower-bassira",
                "name": "Aimpower Bassira",
                "sector": "tech",
                "country_code": "MA",
                "status": "active",
                "role": role,
            }]
        return []

    # Le décorateur importe la fonction sous le nom `get_user_orgs`,
    # tandis que l'endpoint /auth/me l'importe directement.
    monkeypatch.setattr(
        "app.auth.decorators.get_user_orgs", _fake_get_user_orgs
    )
    monkeypatch.setattr(
        "app.api.client.get_user_orgs", _fake_get_user_orgs
    )


# ─── /api/client/auth/me ────────────────────────────────────────────────────

class TestAuthMe:
    def test_no_token_401(self, client):
        resp = client.get("/api/client/auth/me")
        assert resp.status_code == 401

    def test_valid_token_returns_orgs(
        self, client, jwt_secret, admin_user_id, org_id, monkeypatch
    ):
        _patch_orgs(monkeypatch, admin_user_id=admin_user_id, org_id=org_id)
        token = _make_token(jwt_secret, sub=admin_user_id)
        resp = client.get(
            "/api/client/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["user_id"] == admin_user_id
        assert len(data["orgs"]) == 1
        assert data["orgs"][0]["slug"] == "aimpower-bassira"
        assert data["orgs"][0]["role"] == "owner"

    def test_user_with_no_orgs_returns_empty(
        self, client, jwt_secret, admin_user_id, monkeypatch
    ):
        monkeypatch.setattr(
            "app.api.client.get_user_orgs", lambda user_id, client=None: []
        )
        token = _make_token(jwt_secret, sub=admin_user_id)
        resp = client.get(
            "/api/client/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["orgs"] == []


# ─── GET /api/client/simulations ────────────────────────────────────────────

class TestListSimulations:
    def test_no_token_401(self, client):
        resp = client.get("/api/client/simulations")
        assert resp.status_code == 401

    def test_member_can_list(
        self, client, jwt_secret, admin_user_id, org_id, monkeypatch
    ):
        _patch_orgs(
            monkeypatch,
            admin_user_id=admin_user_id, org_id=org_id, role="member",
        )

        # Stub la méthode de SimulationManager
        fake_sims = [
            {
                "simulation_id": "sim_aaaaaaaaaaaa",
                "package_id": "crisis-drill-24h",
                "created_at": "2026-05-03T10:00:00Z",
                "status": "completed",
                "is_published": False,
                "outcome": None,
                "brier_score": None,
                "entities_count": 12,
                "profiles_count": 12,
                "config_generated": True,
                "locale": "fr",
                "created_by": admin_user_id,
            }
        ]
        monkeypatch.setattr(
            "app.api.client.SimulationManager.list_simulations_for_org",
            lambda self, org_id: fake_sims,
        )

        token = _make_token(jwt_secret, sub=admin_user_id)
        resp = client.get(
            "/api/client/simulations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["org_id"] == org_id
        assert len(data["simulations"]) == 1
        assert data["simulations"][0]["simulation_id"] == "sim_aaaaaaaaaaaa"


# ─── POST /api/client/simulations ───────────────────────────────────────────

class TestCreateSimulation:
    def test_missing_fields_400(
        self, client, jwt_secret, admin_user_id, org_id, monkeypatch
    ):
        _patch_orgs(monkeypatch, admin_user_id=admin_user_id, org_id=org_id)
        token = _make_token(jwt_secret, sub=admin_user_id)
        resp = client.post(
            "/api/client/simulations",
            json={"project_id": "proj1"},  # graph_id manquant
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "MISSING_FIELDS"

    def test_creates_and_records_ownership(
        self, client, jwt_secret, admin_user_id, org_id, monkeypatch
    ):
        _patch_orgs(monkeypatch, admin_user_id=admin_user_id, org_id=org_id)

        fake_state = MagicMock()
        fake_state.simulation_id = "sim_newxxxxxxxx"
        fake_state.status = MagicMock(value="created")

        captured: Dict[str, Any] = {}

        def fake_create(self, **kwargs):
            captured.update(kwargs)
            return fake_state

        monkeypatch.setattr(
            "app.api.client.SimulationManager.create_simulation",
            fake_create,
        )

        token = _make_token(jwt_secret, sub=admin_user_id)
        resp = client.post(
            "/api/client/simulations",
            json={
                "project_id": "proj1",
                "graph_id": "graph1",
                "package_id": "crisis-drill-24h",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["data"]["simulation_id"] == "sim_newxxxxxxxx"
        assert body["data"]["org_id"] == org_id
        # On a bien forwardé org_id, created_by, package_id à create_simulation
        assert captured["org_id"] == org_id
        assert captured["created_by"] == admin_user_id
        assert captured["package_id"] == "crisis-drill-24h"


# ─── POST /api/client/simulations/<id>/outcome ──────────────────────────────

class TestPostOutcome:
    def test_member_role_rejected(
        self, client, jwt_secret, member_user_id, org_id, monkeypatch
    ):
        _patch_orgs(
            monkeypatch,
            admin_user_id=member_user_id, org_id=org_id, role="member",
        )
        token = _make_token(jwt_secret, sub=member_user_id)
        resp = client.post(
            "/api/client/simulations/sim_xxxxxxxxxxxx/outcome",
            json={"label": "called_it", "observed_at": "2026-05-04T00:00:00Z"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "ROLE_TOO_LOW"

    def test_invalid_label_400(
        self, client, jwt_secret, admin_user_id, org_id, monkeypatch
    ):
        _patch_orgs(monkeypatch, admin_user_id=admin_user_id, org_id=org_id)
        token = _make_token(jwt_secret, sub=admin_user_id)
        resp = client.post(
            "/api/client/simulations/sim_xxxxxxxxxxxx/outcome",
            json={"label": "maybe", "observed_at": "2026-05-04T00:00:00Z"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "INVALID_LABEL"

    def test_missing_observed_at_400(
        self, client, jwt_secret, admin_user_id, org_id, monkeypatch
    ):
        _patch_orgs(monkeypatch, admin_user_id=admin_user_id, org_id=org_id)
        token = _make_token(jwt_secret, sub=admin_user_id)
        resp = client.post(
            "/api/client/simulations/sim_xxxxxxxxxxxx/outcome",
            json={"label": "called_it"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "MISSING_FIELDS"

    def test_brier_out_of_range_400(
        self, client, jwt_secret, admin_user_id, org_id, monkeypatch
    ):
        _patch_orgs(monkeypatch, admin_user_id=admin_user_id, org_id=org_id)
        token = _make_token(jwt_secret, sub=admin_user_id)
        resp = client.post(
            "/api/client/simulations/sim_xxxxxxxxxxxx/outcome",
            json={
                "label": "called_it",
                "observed_at": "2026-05-04T00:00:00Z",
                "brier_score": 1.5,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "INVALID_BRIER"

    def test_not_owned_returns_404(
        self, client, jwt_secret, admin_user_id, org_id, monkeypatch
    ):
        _patch_orgs(monkeypatch, admin_user_id=admin_user_id, org_id=org_id)
        monkeypatch.setattr(
            "app.api.client.get_simulation_owner",
            lambda sim_id, client=None: None,
        )
        token = _make_token(jwt_secret, sub=admin_user_id)
        resp = client.post(
            "/api/client/simulations/sim_xxxxxxxxxxxx/outcome",
            json={"label": "called_it", "observed_at": "2026-05-04T00:00:00Z"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
        assert resp.get_json()["error_code"] == "SIMULATION_NOT_OWNED"

    def test_wrong_org_returns_403(
        self, client, jwt_secret, admin_user_id, org_id, monkeypatch
    ):
        _patch_orgs(monkeypatch, admin_user_id=admin_user_id, org_id=org_id)
        monkeypatch.setattr(
            "app.api.client.get_simulation_owner",
            lambda sim_id, client=None: {"org_id": "other-org-uuid"},
        )
        token = _make_token(jwt_secret, sub=admin_user_id)
        resp = client.post(
            "/api/client/simulations/sim_xxxxxxxxxxxx/outcome",
            json={"label": "called_it", "observed_at": "2026-05-04T00:00:00Z"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "FORBIDDEN_ORG"

    def test_admin_can_mark(
        self, client, jwt_secret, admin_user_id, org_id, monkeypatch
    ):
        _patch_orgs(
            monkeypatch,
            admin_user_id=admin_user_id, org_id=org_id, role="admin",
        )
        monkeypatch.setattr(
            "app.api.client.get_simulation_owner",
            lambda sim_id, client=None: {"org_id": org_id},
        )

        captured: Dict[str, Any] = {}

        def fake_mark(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr("app.api.client._mark_outcome", fake_mark)

        token = _make_token(jwt_secret, sub=admin_user_id)
        resp = client.post(
            "/api/client/simulations/sim_xxxxxxxxxxxx/outcome",
            json={
                "label": "called_it",
                "observed_at": "2026-05-04T00:00:00Z",
                "source_url": "https://example.com/news",
                "brier_score": 0.12,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()["data"]
        assert body["label"] == "called_it"
        assert body["brier_score"] == 0.12
        assert captured["label"] == "called_it"
        assert captured["source_url"] == "https://example.com/news"
        assert captured["brier_score"] == 0.12
        assert captured["marker_user_id"] == admin_user_id


# ─── POST /api/client/simulations/<id>/publish ──────────────────────────────

class TestPostPublish:
    def test_member_role_rejected(
        self, client, jwt_secret, member_user_id, org_id, monkeypatch
    ):
        _patch_orgs(
            monkeypatch,
            admin_user_id=member_user_id, org_id=org_id, role="member",
        )
        token = _make_token(jwt_secret, sub=member_user_id)
        resp = client.post(
            "/api/client/simulations/sim_xxxxxxxxxxxx/publish",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_owner_publishes(
        self, client, jwt_secret, admin_user_id, org_id, monkeypatch
    ):
        _patch_orgs(monkeypatch, admin_user_id=admin_user_id, org_id=org_id)
        monkeypatch.setattr(
            "app.api.client.get_simulation_owner",
            lambda sim_id, client=None: {"org_id": org_id},
        )

        captured: Dict[str, Any] = {}

        def fake_publish(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr(
            "app.api.client._publish_simulation", fake_publish
        )

        token = _make_token(jwt_secret, sub=admin_user_id)
        resp = client.post(
            "/api/client/simulations/sim_xxxxxxxxxxxx/publish",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()["data"]
        assert body["is_published"] is True
        assert captured["simulation_id"] == "sim_xxxxxxxxxxxx"
        assert captured["marker_user_id"] == admin_user_id

    def test_not_owned_returns_404(
        self, client, jwt_secret, admin_user_id, org_id, monkeypatch
    ):
        _patch_orgs(monkeypatch, admin_user_id=admin_user_id, org_id=org_id)
        monkeypatch.setattr(
            "app.api.client.get_simulation_owner",
            lambda sim_id, client=None: None,
        )
        token = _make_token(jwt_secret, sub=admin_user_id)
        resp = client.post(
            "/api/client/simulations/sim_xxxxxxxxxxxx/publish",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


# ─── GET /api/calibration/aggregates ────────────────────────────────────────

class TestPublicAggregates:
    def test_no_auth_required(self, client, monkeypatch):
        fake_rows = [
            {"sector": "banque", "n_published": 8, "avg_brier": 0.21},
            {"sector": "energie", "n_published": 6, "avg_brier": 0.19},
        ]
        monkeypatch.setattr(
            "app.api.calibration.get_public_calibration_aggregates"
            if False else
            "app.auth.supabase_client.get_public_calibration_aggregates",
            lambda client=None: fake_rows,
        )
        resp = client.get("/api/calibration/aggregates")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert len(body["data"]) == 2
        assert body["data"][0]["sector"] == "banque"

    def test_supabase_misconfigured_returns_empty(
        self, client, monkeypatch
    ):
        from app.auth.supabase_client import SupabaseConfigError

        def _raise(client=None):
            raise SupabaseConfigError("missing")

        monkeypatch.setattr(
            "app.auth.supabase_client.get_public_calibration_aggregates",
            _raise,
        )
        resp = client.get("/api/calibration/aggregates")
        # On retourne 200 avec liste vide pour ne pas brique la page
        # calibration v2 en environnement dev sans clé Supabase.
        assert resp.status_code == 200
        assert resp.get_json()["data"] == []
