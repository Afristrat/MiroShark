"""Tests unitaires Lot B — GET /api/client/quotes (US-B4).

Suit le pattern déjà établi par test_unit_client_simulations.py : app Flask
complète (sans Neo4j live), JWT HS256 signé localement, `get_user_orgs`
monkeypatché (décorateur + endpoint), Supabase jamais appelé en vrai.
"""

from __future__ import annotations

import time

import jwt as pyjwt
import pytest

from app.auth import jwt_verifier


@pytest.fixture(autouse=True)
def _reset_jwt_cache():
    jwt_verifier._cache_clear()
    yield
    jwt_verifier._cache_clear()


@pytest.fixture
def jwt_secret(monkeypatch):
    secret = "client-quotes-tests-secret"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    return secret


@pytest.fixture
def member_user_id() -> str:
    return "user-member-uuid-quotes"


@pytest.fixture
def org_id() -> str:
    return "org-atlas-uuid"


def _make_token(secret: str, sub: str, email: str = "karim@example.com") -> str:
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


def _patch_orgs(monkeypatch, *, user_id, org_id, role="member"):
    def _fake_get_user_orgs(uid, client=None):
        if uid == user_id:
            return [{
                "id": org_id,
                "slug": "atlas",
                "name": "Atlas Capital",
                "sector": None,
                "country_code": "MA",
                "status": "active",
                "role": role,
            }]
        return []

    monkeypatch.setattr("app.auth.decorators.get_user_orgs", _fake_get_user_orgs)
    monkeypatch.setattr("app.api.client.get_user_orgs", _fake_get_user_orgs)


class TestClientQuotesEndpoint:
    def test_requires_auth(self, client):
        resp = client.get("/api/client/quotes")
        assert resp.status_code == 401

    def test_returns_scoped_quotes_for_member(self, client, jwt_secret, member_user_id, org_id, monkeypatch):
        _patch_orgs(monkeypatch, user_id=member_user_id, org_id=org_id)
        monkeypatch.setattr(
            "app.api.client.qo.list_quotes_for_org",
            lambda oid, **kw: [
                {
                    "quote_id": "q_1", "org_id": oid, "package_id": "crisis_drill_24h",
                    "status": "delivered", "created_at": "2026-07-12T10:00:00Z",
                    "customer_email": "karim@example.com",
                },
            ],
        )

        token = _make_token(jwt_secret, sub=member_user_id)
        resp = client.get("/api/client/quotes", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        quotes = body["data"]["quotes"]
        assert len(quotes) == 1
        item = quotes[0]
        assert item["quote_id"] == "q_1"
        assert item["package_id"] == "crisis_drill_24h"
        assert item["status"] == "delivered"
        assert "customer_email" not in item
        assert "payload" not in item

    def test_no_org_returns_403(self, client, jwt_secret, member_user_id, monkeypatch):
        monkeypatch.setattr("app.auth.decorators.get_user_orgs", lambda uid, client=None: [])
        monkeypatch.setattr("app.api.client.get_user_orgs", lambda uid, client=None: [])

        token = _make_token(jwt_secret, sub=member_user_id)
        resp = client.get("/api/client/quotes", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "NOT_A_MEMBER"

    def test_empty_list_returns_200(self, client, jwt_secret, member_user_id, org_id, monkeypatch):
        _patch_orgs(monkeypatch, user_id=member_user_id, org_id=org_id)
        monkeypatch.setattr("app.api.client.qo.list_quotes_for_org", lambda oid, **kw: [])

        token = _make_token(jwt_secret, sub=member_user_id)
        resp = client.get("/api/client/quotes", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        assert resp.get_json()["data"]["quotes"] == []
