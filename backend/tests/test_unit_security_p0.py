"""Tests de non-régression pour les failles d'autorisation P0."""

import pytest
from types import SimpleNamespace


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


def test_report_delete_rejects_anonymous_before_deletion(app_client, monkeypatch):
    from app.services.report_agent import ReportManager

    deleted = []
    monkeypatch.setattr(
        ReportManager,
        "get_report",
        lambda report_id: SimpleNamespace(simulation_id="sim_owned"),
    )
    monkeypatch.setattr(
        ReportManager,
        "delete_report",
        lambda report_id: deleted.append(report_id) or True,
    )

    response = app_client.delete("/api/report/report_owned")

    assert response.status_code == 401
    assert response.get_json()["error_code"] == "MISSING_AUTH"
    assert deleted == []


@pytest.mark.parametrize("role", [None, "viewer", "member"])
def test_report_delete_rejects_non_admin_of_owner_org(
    app_client, monkeypatch, role,
):
    from app.auth import decorators
    from app.auth import supabase_client
    from app.services.report_agent import ReportManager

    deleted = []
    monkeypatch.setattr(
        decorators,
        "verify_supabase_jwt",
        lambda token: {"sub": "user-1", "email": "member@example.test"},
    )
    monkeypatch.setattr(
        supabase_client,
        "get_simulation_owner",
        lambda simulation_id: {"org_id": "org-owner"},
    )
    monkeypatch.setattr(
        supabase_client,
        "get_user_role_in_org",
        lambda user_id, org_id: role,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report",
        lambda report_id: SimpleNamespace(simulation_id="sim_owned"),
    )
    monkeypatch.setattr(
        ReportManager,
        "delete_report",
        lambda report_id: deleted.append(report_id) or True,
    )

    response = app_client.delete(
        "/api/report/report_owned",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 403
    assert response.get_json()["error_code"] == "ROLE_TOO_LOW"
    assert deleted == []


def test_report_delete_fails_closed_without_durable_ownership(
    app_client, monkeypatch,
):
    from app.auth import decorators
    from app.auth import supabase_client
    from app.services.report_agent import ReportManager

    monkeypatch.setattr(
        decorators,
        "verify_supabase_jwt",
        lambda token: {"sub": "user-1", "email": "admin@example.test"},
    )
    monkeypatch.setattr(
        supabase_client,
        "get_simulation_owner",
        lambda simulation_id: None,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report",
        lambda report_id: SimpleNamespace(simulation_id="sim_legacy"),
    )

    response = app_client.delete(
        "/api/report/report_legacy",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 403
    assert response.get_json()["error_code"] == "OWNERSHIP_REQUIRED"


@pytest.mark.parametrize("role", ["admin", "owner"])
def test_report_delete_allows_admin_of_owner_org(
    app_client, monkeypatch, role,
):
    from app.auth import decorators
    from app.auth import supabase_client
    from app.services.report_agent import ReportManager

    deleted = []
    monkeypatch.setattr(
        decorators,
        "verify_supabase_jwt",
        lambda token: {"sub": "user-1", "email": "admin@example.test"},
    )
    monkeypatch.setattr(
        supabase_client,
        "get_simulation_owner",
        lambda simulation_id: {"org_id": "org-owner"},
    )
    monkeypatch.setattr(
        supabase_client,
        "get_user_role_in_org",
        lambda user_id, org_id: role,
    )
    monkeypatch.setattr(
        ReportManager,
        "get_report",
        lambda report_id: SimpleNamespace(simulation_id="sim_owned"),
    )
    monkeypatch.setattr(
        ReportManager,
        "delete_report",
        lambda report_id: deleted.append(report_id) or True,
    )

    response = app_client.delete(
        "/api/report/report_owned",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert deleted == ["report_owned"]


def test_director_injection_rejects_anonymous(app_client):
    response = app_client.post(
        "/api/simulation/sim_owned/director/inject",
        json={"event_text": "Injected event"},
    )

    assert response.status_code == 401
    assert response.get_json()["error_code"] == "MISSING_AUTH"


def test_director_injection_rejects_member_of_owner_org(app_client, monkeypatch):
    from app.auth import decorators
    from app.auth import supabase_client

    monkeypatch.setattr(
        decorators,
        "verify_supabase_jwt",
        lambda token: {"sub": "user-1", "email": "member@example.test"},
    )
    monkeypatch.setattr(
        supabase_client,
        "get_simulation_owner",
        lambda simulation_id: {"org_id": "org-owner"},
    )
    monkeypatch.setattr(
        supabase_client,
        "get_user_role_in_org",
        lambda user_id, org_id: "member",
    )

    response = app_client.post(
        "/api/simulation/sim_owned/director/inject",
        headers={"Authorization": "Bearer valid-token"},
        json={"event_text": "Injected event"},
    )

    assert response.status_code == 403
    assert response.get_json()["error_code"] == "ROLE_TOO_LOW"


def test_director_event_records_authenticated_actor(tmp_path):
    from director_events import add_event

    event = add_event(
        str(tmp_path),
        "Injected event",
        round_num=3,
        submitted_by="user-1",
    )

    assert event["submitted_by"] == "user-1"
