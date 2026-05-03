"""Tests unitaires US-095 — super-admin Bassira + endpoints admin orgs.

Couvre :
  - `is_super_admin_email` (helper libre — whitelist parsing)
  - `@require_super_admin` (décorateur Flask, composé de @require_auth)
  - `GET /api/admin/me/super-status` (révèle is_super_admin sans rôle requis)
  - `GET /api/admin/organizations` (liste cross-tenant via service_role)
  - `GET /api/admin/organizations/<id>` (détail : org + members + sims)

Toutes les interactions Supabase sont monkeypatchées via MagicMock —
aucune dépendance live à Supabase, aucun JWT réel n'est généré contre
un secret externe.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List
from unittest.mock import MagicMock

import jwt as pyjwt
import pytest

from app import create_app
from app.auth import decorators as auth_decorators
from app.auth import jwt_verifier


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_jwt_cache():
    jwt_verifier._cache_clear()
    yield
    jwt_verifier._cache_clear()


@pytest.fixture
def jwt_secret(monkeypatch):
    secret = "admin-orgs-tests-secret"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    return secret


@pytest.fixture
def super_admin_email() -> str:
    return "amine@ai-mpower.com"


@pytest.fixture
def normal_email() -> str:
    return "user@somecorp.com"


@pytest.fixture
def super_admin_user_id() -> str:
    return "user-superadmin-uuid-1111"


@pytest.fixture
def normal_user_id() -> str:
    return "user-normal-uuid-2222"


@pytest.fixture
def whitelist_env(monkeypatch, super_admin_email):
    """Pose la whitelist super-admin avec un email + un alias bonus."""
    monkeypatch.setenv(
        "BASSIRA_SUPER_ADMIN_EMAILS",
        f"{super_admin_email}, partner@ai-mpower.com",
    )
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
    """Construit l'app Flask sans Neo4j live."""
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


# ─── Tests `is_super_admin_email` (helper libre) ────────────────────────────


class TestIsSuperAdminEmail:
    def test_empty_whitelist_returns_false(self, monkeypatch):
        monkeypatch.setenv("BASSIRA_SUPER_ADMIN_EMAILS", "")
        assert auth_decorators.is_super_admin_email("amine@ai-mpower.com") is False

    def test_unset_whitelist_returns_false(self, monkeypatch):
        monkeypatch.delenv("BASSIRA_SUPER_ADMIN_EMAILS", raising=False)
        assert auth_decorators.is_super_admin_email("amine@ai-mpower.com") is False

    def test_email_in_whitelist(self, monkeypatch):
        monkeypatch.setenv(
            "BASSIRA_SUPER_ADMIN_EMAILS", "amine@ai-mpower.com,bob@example.com"
        )
        assert auth_decorators.is_super_admin_email("amine@ai-mpower.com") is True
        assert auth_decorators.is_super_admin_email("bob@example.com") is True

    def test_email_not_in_whitelist(self, monkeypatch):
        monkeypatch.setenv("BASSIRA_SUPER_ADMIN_EMAILS", "amine@ai-mpower.com")
        assert auth_decorators.is_super_admin_email("eve@somecorp.com") is False

    def test_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("BASSIRA_SUPER_ADMIN_EMAILS", "Amine@AI-MPower.com")
        assert auth_decorators.is_super_admin_email("amine@ai-mpower.com") is True
        assert auth_decorators.is_super_admin_email("AMINE@AI-MPOWER.COM") is True

    def test_strip_whitespace(self, monkeypatch):
        monkeypatch.setenv(
            "BASSIRA_SUPER_ADMIN_EMAILS",
            "  amine@ai-mpower.com  ,  bob@example.com  ",
        )
        assert auth_decorators.is_super_admin_email("amine@ai-mpower.com") is True
        assert auth_decorators.is_super_admin_email("bob@example.com") is True

    def test_none_returns_false(self, monkeypatch):
        monkeypatch.setenv("BASSIRA_SUPER_ADMIN_EMAILS", "amine@ai-mpower.com")
        assert auth_decorators.is_super_admin_email(None) is False
        assert auth_decorators.is_super_admin_email("") is False

    def test_non_string_returns_false(self, monkeypatch):
        monkeypatch.setenv("BASSIRA_SUPER_ADMIN_EMAILS", "amine@ai-mpower.com")
        assert auth_decorators.is_super_admin_email(12345) is False  # type: ignore[arg-type]
        assert auth_decorators.is_super_admin_email([]) is False  # type: ignore[arg-type]


# ─── Tests `@require_super_admin` via /api/admin/organizations ──────────────


class TestRequireSuperAdmin:
    def test_no_token_401(self, client, whitelist_env):
        resp = client.get("/api/admin/organizations")
        assert resp.status_code == 401
        assert resp.get_json()["error_code"] == "MISSING_AUTH"

    def test_invalid_token_401(self, client, whitelist_env, jwt_secret):
        resp = client.get(
            "/api/admin/organizations",
            headers={"Authorization": "Bearer not-a-valid-jwt"},
        )
        assert resp.status_code == 401
        assert resp.get_json()["error_code"] == "INVALID_TOKEN"

    def test_email_not_whitelist_403(
        self, client, whitelist_env, jwt_secret, normal_user_id, normal_email
    ):
        token = _make_token(jwt_secret, sub=normal_user_id, email=normal_email)
        resp = client.get(
            "/api/admin/organizations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        body = resp.get_json()
        assert body["error_code"] == "NOT_SUPER_ADMIN"

    def test_whitelist_unset_503(
        self, client, jwt_secret, super_admin_user_id, super_admin_email, monkeypatch
    ):
        monkeypatch.delenv("BASSIRA_SUPER_ADMIN_EMAILS", raising=False)
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/organizations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 503
        assert resp.get_json()["error_code"] == "SUPER_ADMIN_NOT_CONFIGURED"

    def test_whitelist_empty_503(
        self, client, jwt_secret, super_admin_user_id, super_admin_email, monkeypatch
    ):
        monkeypatch.setenv("BASSIRA_SUPER_ADMIN_EMAILS", "   ")
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/organizations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 503
        assert resp.get_json()["error_code"] == "SUPER_ADMIN_NOT_CONFIGURED"

    def test_super_admin_allowed(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        # Mock get_supabase_admin pour ne pas dépendre de Supabase live.
        fake_client = _make_fake_supabase_with_orgs([])
        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            lambda: fake_client,
        )
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/organizations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"]["organizations"] == []


# ─── Tests `GET /api/admin/me/super-status` ─────────────────────────────────


class TestSuperStatusEndpoint:
    def test_no_token_401(self, client, whitelist_env):
        resp = client.get("/api/admin/me/super-status")
        assert resp.status_code == 401

    def test_user_not_whitelist_returns_false(
        self, client, whitelist_env, jwt_secret, normal_user_id, normal_email
    ):
        token = _make_token(jwt_secret, sub=normal_user_id, email=normal_email)
        resp = client.get(
            "/api/admin/me/super-status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"]["is_super_admin"] is False
        assert body["data"]["email"] == normal_email

    def test_user_whitelist_returns_true(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email,
    ):
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/me/super-status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"]["is_super_admin"] is True
        assert body["data"]["email"] == super_admin_email

    def test_no_whitelist_user_returns_false(
        self, client, jwt_secret, super_admin_user_id, super_admin_email, monkeypatch
    ):
        # Pas de whitelist → personne n'est super-admin → endpoint
        # retourne false (pas d'erreur, l'endpoint n'exige pas le rôle).
        monkeypatch.delenv("BASSIRA_SUPER_ADMIN_EMAILS", raising=False)
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/me/super-status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["is_super_admin"] is False


# ─── Tests `GET /api/admin/organizations` ───────────────────────────────────


def _make_fake_supabase_with_orgs(orgs: List[Dict[str, Any]]):
    """Construit un MagicMock supabase qui retourne les orgs fournies.

    Les calls suivants sont supportés :
      - .table('organizations').select(...).order(...).execute()
      - .table('simulation_ownership').select(...).eq('org_id', ...).execute()
      - .table('org_members').select(..., count='exact').eq('org_id', ...).execute()
    """
    fake = MagicMock()

    def _table(name: str):
        tbl = MagicMock()
        if name == "organizations":
            select = MagicMock()
            order = MagicMock()
            order.execute.return_value = MagicMock(data=orgs)
            select.order.return_value = order
            tbl.select.return_value = select
        elif name == "simulation_ownership":
            select = MagicMock()
            eq = MagicMock()
            eq.execute.return_value = MagicMock(data=[])
            select.eq.return_value = eq
            tbl.select.return_value = select
        elif name == "org_members":
            select = MagicMock()
            eq = MagicMock()
            eq.execute.return_value = MagicMock(data=[], count=0)
            select.eq.return_value = eq
            tbl.select.return_value = select
        else:
            tbl.select.return_value = MagicMock()
        return tbl

    fake.table.side_effect = _table
    return fake


class TestListAllOrganizations:
    def test_empty_list(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        fake = _make_fake_supabase_with_orgs([])
        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/organizations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["organizations"] == []

    def test_single_org_with_stats(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        org = {
            "id": "org-uuid-1",
            "slug": "acme",
            "name": "ACME Corp",
            "sector": "tech",
            "country_code": "MA",
            "status": "active",
            "created_at": "2026-04-01T10:00:00Z",
        }
        # MagicMock customisé pour servir simulation_ownership avec data
        fake = MagicMock()

        def _table(name: str):
            tbl = MagicMock()
            if name == "organizations":
                select = MagicMock()
                order = MagicMock()
                order.execute.return_value = MagicMock(data=[org])
                select.order.return_value = order
                tbl.select.return_value = select
            elif name == "simulation_ownership":
                select = MagicMock()
                eq = MagicMock()
                eq.execute.return_value = MagicMock(data=[
                    {"simulation_id": "s1", "is_published": True, "brier_score": 0.20},
                    {"simulation_id": "s2", "is_published": False, "brier_score": 0.30},
                    {"simulation_id": "s3", "is_published": True, "brier_score": None},
                ])
                select.eq.return_value = eq
                tbl.select.return_value = select
            elif name == "org_members":
                select = MagicMock()
                eq = MagicMock()
                eq.execute.return_value = MagicMock(data=[], count=4)
                select.eq.return_value = eq
                tbl.select.return_value = select
            return tbl

        fake.table.side_effect = _table
        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            lambda: fake,
        )

        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/organizations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        orgs = body["data"]["organizations"]
        assert len(orgs) == 1
        first = orgs[0]
        assert first["id"] == "org-uuid-1"
        assert first["slug"] == "acme"
        assert first["name"] == "ACME Corp"
        assert first["sector"] == "tech"
        assert first["country_code"] == "MA"
        assert first["status"] == "active"
        assert first["members_count"] == 4
        assert first["simulations_count"] == 3
        assert first["published_count"] == 2
        # avg_brier moyenne de 0.20 et 0.30 (None ignoré) = 0.25
        assert first["avg_brier"] == pytest.approx(0.25)

    def test_supabase_misconfigured_503(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        from app.auth.supabase_client import SupabaseConfigError

        def _raise():
            raise SupabaseConfigError("missing")

        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            _raise,
        )
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/organizations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 503
        assert resp.get_json()["error_code"] == "SUPABASE_NOT_CONFIGURED"

    def test_supabase_select_failure_500(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        fake = MagicMock()

        def _table(name: str):
            tbl = MagicMock()
            select = MagicMock()
            order = MagicMock()
            order.execute.side_effect = RuntimeError("db unreachable")
            select.order.return_value = order
            tbl.select.return_value = select
            return tbl

        fake.table.side_effect = _table
        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/organizations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 500
        assert resp.get_json()["error_code"] == "ADMIN_ORGS_FAILED"

    def test_normal_user_403(
        self, client, whitelist_env, jwt_secret,
        normal_user_id, normal_email, monkeypatch,
    ):
        token = _make_token(jwt_secret, sub=normal_user_id, email=normal_email)
        resp = client.get(
            "/api/admin/organizations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "NOT_SUPER_ADMIN"


# ─── Tests `GET /api/admin/organizations/<id>` ──────────────────────────────


class TestGetOrganizationDetail:
    def test_no_token_401(self, client, whitelist_env):
        resp = client.get("/api/admin/organizations/org-uuid-1")
        assert resp.status_code == 401

    def test_normal_user_403(
        self, client, whitelist_env, jwt_secret,
        normal_user_id, normal_email,
    ):
        token = _make_token(jwt_secret, sub=normal_user_id, email=normal_email)
        resp = client.get(
            "/api/admin/organizations/org-uuid-1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_org_not_found_404(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        fake = MagicMock()

        def _table(name: str):
            tbl = MagicMock()
            select = MagicMock()
            eq = MagicMock()
            limit = MagicMock()
            limit.execute.return_value = MagicMock(data=[])
            eq.limit.return_value = limit
            eq.execute.return_value = MagicMock(data=[], count=0)
            select.eq.return_value = eq
            tbl.select.return_value = select
            return tbl

        fake.table.side_effect = _table
        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/organizations/unknown-org-uuid",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
        assert resp.get_json()["error_code"] == "ORG_NOT_FOUND"

    def test_org_detail_with_members_and_sims(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        org = {
            "id": "org-uuid-1",
            "slug": "acme",
            "name": "ACME Corp",
            "sector": "tech",
            "country_code": "MA",
            "status": "active",
            "created_at": "2026-04-01T10:00:00Z",
            "metadata": {"plan": "trial"},
        }
        members_rows = [
            {"user_id": "u1", "role": "owner", "created_at": "2026-04-01T10:00:00Z"},
            {"user_id": "u2", "role": "member", "created_at": "2026-04-02T10:00:00Z"},
        ]
        sims_rows = [
            {
                "simulation_id": "sim_aaaa",
                "package_id": "crisis-drill-24h",
                "is_published": True,
                "outcome": {"label": "called_it"},
                "brier_score": 0.18,
                "created_at": "2026-04-15T10:00:00Z",
                "created_by": "u1",
            },
        ]

        fake = MagicMock()

        def _table(name: str):
            tbl = MagicMock()
            if name == "organizations":
                select = MagicMock()
                eq = MagicMock()
                limit = MagicMock()
                limit.execute.return_value = MagicMock(data=[org])
                eq.limit.return_value = limit
                select.eq.return_value = eq
                tbl.select.return_value = select
            elif name == "org_members":
                select = MagicMock()
                eq = MagicMock()
                eq.execute.return_value = MagicMock(data=members_rows, count=len(members_rows))
                select.eq.return_value = eq
                tbl.select.return_value = select
            elif name == "simulation_ownership":
                select = MagicMock()
                eq = MagicMock()
                order = MagicMock()
                order.execute.return_value = MagicMock(data=sims_rows)
                eq.order.return_value = order
                eq.execute.return_value = MagicMock(data=sims_rows)
                select.eq.return_value = eq
                tbl.select.return_value = select
            return tbl

        fake.table.side_effect = _table
        # Pas d'admin auth disponible → email reste None pour les members.
        fake.auth = None
        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            lambda: fake,
        )

        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/organizations/org-uuid-1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        data = body["data"]
        assert data["organization"]["id"] == "org-uuid-1"
        assert data["organization"]["slug"] == "acme"
        assert len(data["members"]) == 2
        assert data["members"][0]["user_id"] == "u1"
        assert data["members"][0]["role"] == "owner"
        assert data["members"][0]["email"] is None  # auth.admin pas dispo
        assert len(data["simulations"]) == 1
        assert data["simulations"][0]["simulation_id"] == "sim_aaaa"
        assert data["simulations"][0]["is_published"] is True
        assert data["simulations"][0]["brier_score"] == 0.18

    def test_org_detail_supabase_config_503(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        from app.auth.supabase_client import SupabaseConfigError

        def _raise():
            raise SupabaseConfigError("missing")

        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            _raise,
        )
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/organizations/some-uuid",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 503
        assert resp.get_json()["error_code"] == "SUPABASE_NOT_CONFIGURED"
