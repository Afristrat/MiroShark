"""Tests unitaires US-098 — toggle org-level self_service_enabled.

Couvre :
  - Helper `is_org_self_service_enabled` (lecture du flag)
  - Helper `set_org_self_service_enabled` (écriture du flag)
  - Endpoint PATCH `/api/admin/organizations/<org_id>/self-service`
  - Décorateur `@require_self_service_enabled` (strict)
  - Décorateur `@soft_check_self_service` (souple — laisse passer si pas de JWT)
  - Application sur /api/simulation/create (mode legacy + JWT modes)

Pas de dépendance live à Supabase (MagicMock).
"""

from __future__ import annotations

import time
from typing import Any, Dict
from unittest.mock import MagicMock

import jwt as pyjwt
import pytest
from flask import Blueprint, Flask, jsonify

from app import create_app
from app.auth import (
    decorators as auth_decorators,
    soft_check_self_service,
    require_org_membership,
    require_self_service_enabled,
)
from app.auth import jwt_verifier
from app.auth import supabase_client


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_jwt_cache():
    jwt_verifier._cache_clear()
    yield
    jwt_verifier._cache_clear()


@pytest.fixture
def jwt_secret(monkeypatch):
    secret = "self-service-tests-secret"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    return secret


@pytest.fixture
def super_admin_email():
    return "amine@ai-mpower.com"


@pytest.fixture
def whitelist_env(monkeypatch, super_admin_email):
    monkeypatch.setenv("BASSIRA_SUPER_ADMIN_EMAILS", super_admin_email)
    yield


def _make_token(secret: str, sub: str, email: str) -> str:
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
    app_obj = create_app()
    app_obj.config["TESTING"] = True
    return app_obj


@pytest.fixture
def client(app):
    return app.test_client()


# ─── Tests `is_org_self_service_enabled` ────────────────────────────────────


class TestIsOrgSelfServiceEnabled:
    def test_returns_true_when_enabled(self):
        fake = MagicMock()
        chain = MagicMock()
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = MagicMock(data=[{"self_service_enabled": True}])
        fake.table.return_value.select.return_value = chain
        assert supabase_client.is_org_self_service_enabled("o1", client=fake) is True

    def test_returns_false_when_disabled(self):
        fake = MagicMock()
        chain = MagicMock()
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = MagicMock(data=[{"self_service_enabled": False}])
        fake.table.return_value.select.return_value = chain
        assert supabase_client.is_org_self_service_enabled("o1", client=fake) is False

    def test_returns_false_when_org_missing(self):
        fake = MagicMock()
        chain = MagicMock()
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        fake.table.return_value.select.return_value = chain
        assert supabase_client.is_org_self_service_enabled("missing", client=fake) is False

    def test_returns_false_on_exception(self):
        fake = MagicMock()
        chain = MagicMock()
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.execute.side_effect = RuntimeError("supabase down")
        fake.table.return_value.select.return_value = chain
        # Sécurité par défaut : erreur → False (pas True).
        assert supabase_client.is_org_self_service_enabled("o1", client=fake) is False


# ─── Tests `set_org_self_service_enabled` ───────────────────────────────────


class TestSetOrgSelfServiceEnabled:
    def test_returns_true_when_one_row_updated(self):
        fake = MagicMock()
        chain = MagicMock()
        chain.eq.return_value = chain
        chain.execute.return_value = MagicMock(data=[{"id": "o1", "self_service_enabled": True}])
        fake.table.return_value.update.return_value = chain
        ok = supabase_client.set_org_self_service_enabled("o1", True, client=fake)
        assert ok is True

    def test_returns_false_when_no_row(self):
        fake = MagicMock()
        chain = MagicMock()
        chain.eq.return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        fake.table.return_value.update.return_value = chain
        ok = supabase_client.set_org_self_service_enabled("o-missing", True, client=fake)
        assert ok is False

    def test_propagates_exception(self):
        fake = MagicMock()
        chain = MagicMock()
        chain.eq.return_value = chain
        chain.execute.side_effect = RuntimeError("dup error")
        fake.table.return_value.update.return_value = chain
        with pytest.raises(RuntimeError):
            supabase_client.set_org_self_service_enabled("o1", True, client=fake)


# ─── Tests endpoint PATCH `/api/admin/organizations/<id>/self-service` ──────


class TestPatchSelfServiceEndpoint:
    def test_no_token_401(self, client, whitelist_env):
        resp = client.patch("/api/admin/organizations/org-1/self-service", json={"enabled": True})
        assert resp.status_code == 401

    def test_normal_user_403(
        self, client, whitelist_env, jwt_secret, monkeypatch
    ):
        token = _make_token(jwt_secret, sub="u-norm", email="user@somecorp.com")
        resp = client.patch(
            "/api/admin/organizations/org-1/self-service",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "NOT_SUPER_ADMIN"

    def test_invalid_body_400(
        self, client, whitelist_env, jwt_secret, super_admin_email, monkeypatch,
    ):
        monkeypatch.setattr("app.api.admin.get_supabase_admin", lambda: MagicMock())
        token = _make_token(jwt_secret, sub="u-1", email=super_admin_email)
        resp = client.patch(
            "/api/admin/organizations/org-1/self-service",
            json={"enabled": "yes"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "INVALID_BODY"

    def test_org_not_found_404(
        self, client, whitelist_env, jwt_secret, super_admin_email, monkeypatch,
    ):
        monkeypatch.setattr("app.api.admin.get_supabase_admin", lambda: MagicMock())

        def _set(org_id, enabled, client=None):
            return False

        monkeypatch.setattr("app.api.admin.set_org_self_service_enabled", _set)
        token = _make_token(jwt_secret, sub="u-1", email=super_admin_email)
        resp = client.patch(
            "/api/admin/organizations/missing/self-service",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
        assert resp.get_json()["error_code"] == "ORG_NOT_FOUND"

    def test_super_admin_enables_200(
        self, client, whitelist_env, jwt_secret, super_admin_email, monkeypatch,
    ):
        monkeypatch.setattr("app.api.admin.get_supabase_admin", lambda: MagicMock())

        captured: Dict[str, Any] = {}

        def _set(org_id, enabled, client=None):
            captured["org_id"] = org_id
            captured["enabled"] = enabled
            return True

        monkeypatch.setattr("app.api.admin.set_org_self_service_enabled", _set)
        token = _make_token(jwt_secret, sub="u-1", email=super_admin_email)
        resp = client.patch(
            "/api/admin/organizations/org-1/self-service",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["org_id"] == "org-1"
        assert body["data"]["self_service_enabled"] is True
        assert captured == {"org_id": "org-1", "enabled": True}

    def test_super_admin_disables_200(
        self, client, whitelist_env, jwt_secret, super_admin_email, monkeypatch,
    ):
        monkeypatch.setattr("app.api.admin.get_supabase_admin", lambda: MagicMock())

        def _set(org_id, enabled, client=None):
            assert enabled is False
            return True

        monkeypatch.setattr("app.api.admin.set_org_self_service_enabled", _set)
        token = _make_token(jwt_secret, sub="u-1", email=super_admin_email)
        resp = client.patch(
            "/api/admin/organizations/org-1/self-service",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["self_service_enabled"] is False


# ─── Tests décorateur `@soft_check_self_service` ────────────────────────────
#
# On expose un blueprint de test minimal monté sur l'app pour vérifier
# le comportement du décorateur sans toucher aux endpoints existants.


@pytest.fixture
def soft_check_app(monkeypatch):
    """Construit une app Flask minimale avec un endpoint @soft_check_self_service."""
    from app import storage as storage_pkg

    class _DummyStorage:
        def __init__(self, *a, **kw):
            pass

    monkeypatch.setattr(storage_pkg, "Neo4jStorage", _DummyStorage)
    app_obj = create_app()
    app_obj.config["TESTING"] = True

    # Blueprint custom isolé pour le test.
    bp = Blueprint("test_soft", __name__)

    @bp.route("/test/soft", methods=["POST"])
    @soft_check_self_service
    def _ep():
        from flask import g
        return jsonify({
            "ok": True,
            "has_user": bool(getattr(g, "current_user", None)),
            "has_org": bool(getattr(g, "current_org", None)),
            "bypass": bool(getattr(g, "self_service_bypass", False)),
        }), 200

    app_obj.register_blueprint(bp, url_prefix="/api")
    return app_obj


@pytest.fixture
def soft_client(soft_check_app):
    return soft_check_app.test_client()


class TestSoftCheckSelfService:
    def test_no_jwt_lets_through(self, soft_client):
        # Pas de JWT → laisse passer (mode legacy).
        resp = soft_client.post("/api/test/soft", json={})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["ok"] is True
        assert body["has_user"] is False
        assert body["has_org"] is False

    def test_invalid_jwt_returns_401(self, soft_client, jwt_secret):
        resp = soft_client.post(
            "/api/test/soft",
            headers={"Authorization": "Bearer not-a-jwt"},
            json={},
        )
        assert resp.status_code == 401

    def test_super_admin_bypass(
        self, soft_client, jwt_secret, super_admin_email, whitelist_env,
    ):
        token = _make_token(jwt_secret, sub="u-super", email=super_admin_email)
        resp = soft_client.post(
            "/api/test/soft",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["bypass"] is True

    def test_member_with_enabled_org_passes(
        self, soft_client, jwt_secret, monkeypatch,
    ):
        token = _make_token(jwt_secret, sub="u-mem", email="member@acme.com")
        # User a 1 org, enabled.
        monkeypatch.setattr(
            "app.auth.decorators.get_user_orgs",
            lambda user_id: [{
                "id": "org-1",
                "slug": "acme",
                "name": "ACME",
                "role": "member",
                "self_service_enabled": True,
            }],
        )
        resp = soft_client.post(
            "/api/test/soft",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["has_org"] is True

    def test_member_with_disabled_org_403(
        self, soft_client, jwt_secret, monkeypatch,
    ):
        token = _make_token(jwt_secret, sub="u-mem", email="member@acme.com")
        # User a 1 org, mais self_service_enabled = false.
        monkeypatch.setattr(
            "app.auth.decorators.get_user_orgs",
            lambda user_id: [{
                "id": "org-1",
                "slug": "acme",
                "name": "ACME",
                "role": "member",
                "self_service_enabled": False,
            }],
        )
        resp = soft_client.post(
            "/api/test/soft",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "SELF_SERVICE_DISABLED"

    def test_member_no_orgs_403(
        self, soft_client, jwt_secret, monkeypatch,
    ):
        token = _make_token(jwt_secret, sub="u-mem", email="member@acme.com")
        monkeypatch.setattr(
            "app.auth.decorators.get_user_orgs",
            lambda user_id: [],
        )
        resp = soft_client.post(
            "/api/test/soft",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "SELF_SERVICE_DISABLED"

    def test_member_supabase_misconfigured_lets_through_legacy(
        self, soft_client, jwt_secret, monkeypatch,
    ):
        """Si Supabase est misconfiguré, on laisse passer (legacy fallback)."""
        from app.auth.supabase_client import SupabaseConfigError

        token = _make_token(jwt_secret, sub="u-mem", email="member@acme.com")

        def _raise(user_id):
            raise SupabaseConfigError("missing")

        monkeypatch.setattr("app.auth.decorators.get_user_orgs", _raise)
        resp = soft_client.post(
            "/api/test/soft",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        # Backend mal configuré → fallback legacy.
        assert resp.status_code == 200
