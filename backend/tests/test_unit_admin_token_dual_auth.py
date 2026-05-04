"""Tests unitaires US-100 — dual-auth admin (JWT super-admin + legacy token).

Couvre :
  - Authentification primary (JWT super-admin) sur /api/admin/analytics
  - Authentification fallback (BASSIRA_ADMIN_TOKEN legacy)
  - Log warning émis lors d'usage du legacy token
  - Aucune régression : un token legacy valide reste accepté
  - 401 si JWT non super-admin et token legacy KO
  - 503 si rien configuré (legacy unset + JWT user pas super-admin)
"""

from __future__ import annotations

import time
from unittest.mock import patch

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
    secret = "us-100-dual-auth-secret"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    return secret


@pytest.fixture
def super_admin_email():
    return "amine@ai-mpower.com"


@pytest.fixture
def whitelist_env(monkeypatch, super_admin_email):
    monkeypatch.setenv("BASSIRA_SUPER_ADMIN_EMAILS", super_admin_email)
    yield


@pytest.fixture
def admin_token_env(monkeypatch):
    """Pose un BASSIRA_ADMIN_TOKEN legacy pour tester le fallback."""
    token = "legacy-admin-token-for-tests"
    monkeypatch.setenv("BASSIRA_ADMIN_TOKEN", token)
    return token


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


# ─── Tests ──────────────────────────────────────────────────────────────────


class TestDualAuthAdminAnalytics:
    def test_jwt_super_admin_accepted(
        self, client, whitelist_env, jwt_secret, super_admin_email,
    ):
        """JWT super-admin valide → 200 (pas besoin de legacy token)."""
        token = _make_token(jwt_secret, sub="user-super", email=super_admin_email)
        resp = client.get(
            "/api/admin/analytics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.get_json()
        body = resp.get_json()
        assert body["success"] is True
        assert "kpis" in body["data"]

    def test_legacy_token_still_accepted(
        self, client, admin_token_env, jwt_secret,
    ):
        """Legacy token (BASSIRA_ADMIN_TOKEN) → 200 + log warning."""
        # Pas de whitelist → seul le path legacy peut réussir.
        with patch("app.api.simulation.logger.warning") as mock_warn:
            resp = client.get(
                "/api/admin/analytics",
                headers={"Authorization": f"Bearer {admin_token_env}"},
            )
        assert resp.status_code == 200, resp.get_json()
        # Le warning « legacy admin token used » doit avoir été loggué.
        assert mock_warn.called
        warn_calls = [str(c) for c in mock_warn.call_args_list]
        assert any("legacy" in s.lower() for s in warn_calls), warn_calls

    def test_jwt_normal_user_rejected_with_legacy_unset(
        self, client, jwt_secret, monkeypatch,
    ):
        """JWT valide mais email non whitelist + pas de legacy token → 503."""
        monkeypatch.delenv("BASSIRA_SUPER_ADMIN_EMAILS", raising=False)
        monkeypatch.delenv("BASSIRA_ADMIN_TOKEN", raising=False)
        monkeypatch.delenv("MIROSHARK_ADMIN_TOKEN", raising=False)
        token = _make_token(jwt_secret, sub="u-norm", email="user@somecorp.com")
        resp = client.get(
            "/api/admin/analytics",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Pas super-admin (pas de whitelist) ni legacy token : 503 fail-closed.
        assert resp.status_code == 503
        assert resp.get_json()["error_code"] == "ADMIN_AUTH_NOT_CONFIGURED"

    def test_jwt_normal_user_rejected_with_legacy_set(
        self, client, jwt_secret, admin_token_env, monkeypatch,
    ):
        """JWT non super-admin + legacy token configuré mais JWT ≠ legacy → 401."""
        monkeypatch.delenv("BASSIRA_SUPER_ADMIN_EMAILS", raising=False)
        token = _make_token(jwt_secret, sub="u-norm", email="user@somecorp.com")
        # Le JWT n'est pas le legacy token. Le décorateur :
        #   1. tente JWT super-admin → KO (pas whitelist)
        #   2. fallback legacy : compare token JWT au legacy admin token → KO
        # → 401.
        resp = client.get(
            "/api/admin/analytics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        assert resp.get_json()["error_code"] == "UNAUTHORIZED"

    def test_no_token_returns_401(self, client, admin_token_env):
        """Pas d'Authorization header → 401 (legacy admin token configuré)."""
        resp = client.get("/api/admin/analytics")
        assert resp.status_code == 401
        assert resp.get_json()["error_code"] == "UNAUTHORIZED"

    def test_no_auth_no_legacy_returns_503(self, client, monkeypatch):
        """Pas d'auth + pas de legacy token configuré → 503 fail-closed."""
        monkeypatch.delenv("BASSIRA_ADMIN_TOKEN", raising=False)
        monkeypatch.delenv("MIROSHARK_ADMIN_TOKEN", raising=False)
        resp = client.get("/api/admin/analytics")
        assert resp.status_code == 503
        assert resp.get_json()["error_code"] == "ADMIN_AUTH_NOT_CONFIGURED"

    def test_jwt_super_admin_no_legacy_warning(
        self, client, whitelist_env, jwt_secret, super_admin_email,
    ):
        """JWT super-admin → ne doit PAS logguer le warning legacy."""
        token = _make_token(jwt_secret, sub="user-super", email=super_admin_email)
        with patch("app.api.simulation.logger.warning") as mock_warn:
            resp = client.get(
                "/api/admin/analytics",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        # Aucun warning « legacy » ne doit être loggué.
        warn_calls = [str(c) for c in mock_warn.call_args_list]
        assert not any("legacy" in s.lower() for s in warn_calls), warn_calls
