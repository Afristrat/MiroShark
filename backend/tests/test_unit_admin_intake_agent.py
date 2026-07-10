"""Tests unitaires ADR-IQ-08 — admin escalations + playbook.

Les endpoints sont gardés par ``@require_super_admin``, appliqué à la
fonction de route au moment de l'import du module — un monkeypatch du
décorateur après import ne défait pas une décoration déjà en place. Les
tests d'endpoint utilisent donc un vrai JWT + whitelist, même pattern que
``test_unit_admin_organizations.py`` (aucune dépendance Supabase live)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import jwt as pyjwt
import pytest

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.auth import jwt_verifier  # noqa: E402
from app.services import intake_service as svc  # noqa: E402


@pytest.fixture
def fake_client(monkeypatch):
    from tests.test_unit_intake import FakeSupabase

    cli = FakeSupabase()
    cli.table("organizations").rows.append({"id": "org-bassira-1", "slug": "aimpower-bassira"})
    monkeypatch.setattr(svc, "get_default_super_admin_org_id", lambda _c=None: "org-bassira-1")
    return cli


class TestListEscalations:
    def test_lists_unreviewed_first(self, fake_client):
        fake_client.table("intake_agent_escalations").rows.extend([
            {"id": "e1", "session_id": "s1", "category": "out_of_scope",
             "user_message": "m1", "agent_message": "a1", "reviewed_at": None},
            {"id": "e2", "session_id": "s2", "category": "injection_attempt",
             "user_message": "m2", "agent_message": "a2", "reviewed_at": "2026-07-10T10:00:00Z"},
        ])
        items, total = svc.list_escalations(client=fake_client)
        assert total == 2
        assert items[0]["id"] == "e1"  # non revu en premier

    def test_filters_unreviewed_only(self, fake_client):
        fake_client.table("intake_agent_escalations").rows.extend([
            {"id": "e1", "reviewed_at": None},
            {"id": "e2", "reviewed_at": "2026-07-10T10:00:00Z"},
        ])
        items, total = svc.list_escalations(client=fake_client, unreviewed_only=True)
        assert total == 1
        assert items[0]["id"] == "e1"


class TestMarkEscalationReviewed:
    def test_marks_reviewed_with_note(self, fake_client):
        fake_client.table("intake_agent_escalations").rows.append(
            {"id": "e1", "reviewed_at": None, "reviewer_note": None}
        )
        status, body = svc.mark_escalation_reviewed("e1", reviewer_note="Faux positif", client=fake_client)
        assert status == 200
        assert body["success"] is True
        row = fake_client.table("intake_agent_escalations").rows[0]
        assert row["reviewed_at"] is not None
        assert row["reviewer_note"] == "Faux positif"

    def test_not_found_returns_404(self, fake_client):
        status, body = svc.mark_escalation_reviewed("does-not-exist", reviewer_note=None, client=fake_client)
        assert status == 404


@pytest.fixture(autouse=True)
def _reset_jwt_cache():
    jwt_verifier._cache_clear()
    yield
    jwt_verifier._cache_clear()


@pytest.fixture
def jwt_secret(monkeypatch):
    secret = "adr-iq-08-tests-secret"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    return secret


@pytest.fixture
def super_admin_email() -> str:
    return "amine@ai-mpower.com"


@pytest.fixture
def super_admin_user_id() -> str:
    return "user-superadmin-uuid-adr-iq-08"


@pytest.fixture
def whitelist_env(monkeypatch, super_admin_email):
    monkeypatch.setenv("BASSIRA_SUPER_ADMIN_EMAILS", super_admin_email)
    yield


def _make_token(secret: str, sub: str, email: str) -> str:
    now = int(time.time())
    return pyjwt.encode(
        {"sub": sub, "email": email, "aud": "authenticated", "role": "authenticated",
         "iat": now, "exp": now + 3600},
        secret, algorithm="HS256",
    )


@pytest.fixture
def super_admin_headers(jwt_secret, whitelist_env, super_admin_user_id, super_admin_email):
    token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def app(monkeypatch):
    from app import storage as storage_pkg

    class _DummyStorage:
        def __init__(self, *a, **kw):
            pass

    monkeypatch.setattr(storage_pkg, "Neo4jStorage", _DummyStorage)
    from app import create_app
    app_obj = create_app()
    app_obj.config["TESTING"] = True
    return app_obj


@pytest.fixture
def client(app):
    return app.test_client()


class TestEscalationsEndpoint:
    def test_get_requires_super_admin(self, client):
        resp = client.get("/api/admin/quotes/intake/escalations")
        assert resp.status_code == 401
        assert resp.get_json()["error_code"] == "MISSING_AUTH"

    def test_get_delegates_to_service(self, client, monkeypatch, super_admin_headers):
        from app.api import quote as quote_api
        monkeypatch.setattr(
            quote_api.intake_service, "list_escalations",
            lambda **kw: ([{"id": "e1"}], 1),
        )
        resp = client.get("/api/admin/quotes/intake/escalations", headers=super_admin_headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["total"] == 1
