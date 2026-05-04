"""Tests unitaires US-097 — `/api/admin/simulations` (super-admin cross-tenant).

Couvre :
  - Auth : 401 sans token, 403 si non super-admin
  - Réponse de base : empty / single / multi
  - Filtres : org_id, package_id, published
  - Pagination : limit, offset, total
  - Robustesse : Supabase config 503, select failure 500

Toutes les interactions Supabase sont monkeypatchées via MagicMock.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List
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
    secret = "admin-sims-tests-secret"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    return secret


@pytest.fixture
def super_admin_email() -> str:
    return "amine@ai-mpower.com"


@pytest.fixture
def super_admin_user_id() -> str:
    return "user-superadmin-uuid-aaaa"


@pytest.fixture
def normal_user_id() -> str:
    return "user-normal-uuid-bbbb"


@pytest.fixture
def normal_email() -> str:
    return "user@somecorp.com"


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


# ─── Mock helpers ───────────────────────────────────────────────────────────


def _make_fake_supabase_with_sims(
    sims: List[Dict[str, Any]],
    orgs_lookup: List[Dict[str, Any]] | None = None,
    total: int | None = None,
):
    """Construit un MagicMock supabase qui retourne les sims fournies.

    Le builder simule la chaîne :
      .table('simulation_ownership')
      .select(..., count="exact")
      [.eq('org_id', ...).eq('package_id', ...).eq('is_published', ...)]
      .order('created_at', desc=True)
      .range(offset, offset+limit-1)
      .execute() → MagicMock(data=sims, count=total)

    Pour `_enrich_sims_with_org_info` :
      .table('organizations').select(...).in_('id', [...]).execute()
      → MagicMock(data=orgs_lookup)
    """
    fake = MagicMock()

    captured: Dict[str, Any] = {"eq_calls": []}

    def _build_query_chain(rows, count):
        # Chain of MagicMocks: select → [eq*] → order → range → execute
        chain = MagicMock()

        def _eq(col, val):
            captured["eq_calls"].append((col, val))
            return chain

        def _order(col, desc=False):
            return chain

        def _range(start, end):
            return chain

        def _execute():
            return MagicMock(data=rows, count=count)

        chain.eq.side_effect = _eq
        chain.order.side_effect = _order
        chain.range.side_effect = _range
        chain.execute.side_effect = _execute
        return chain

    def _table(name: str):
        tbl = MagicMock()
        if name == "simulation_ownership":
            chain = _build_query_chain(sims, total if total is not None else len(sims))
            tbl.select.return_value = chain
        elif name == "organizations":
            select_mock = MagicMock()
            in_mock = MagicMock()
            in_mock.execute.return_value = MagicMock(data=orgs_lookup or [])
            select_mock.in_.return_value = in_mock
            tbl.select.return_value = select_mock
        else:
            tbl.select.return_value = MagicMock()
        return tbl

    fake.table.side_effect = _table
    fake._captured = captured
    return fake


# ─── Tests Auth ─────────────────────────────────────────────────────────────


class TestAuth:
    def test_no_token_401(self, client, whitelist_env):
        resp = client.get("/api/admin/simulations")
        assert resp.status_code == 401
        assert resp.get_json()["error_code"] == "MISSING_AUTH"

    def test_invalid_token_401(self, client, whitelist_env, jwt_secret):
        resp = client.get(
            "/api/admin/simulations",
            headers={"Authorization": "Bearer xxx-not-jwt"},
        )
        assert resp.status_code == 401
        assert resp.get_json()["error_code"] == "INVALID_TOKEN"

    def test_normal_user_403(
        self, client, whitelist_env, jwt_secret, normal_user_id, normal_email
    ):
        token = _make_token(jwt_secret, sub=normal_user_id, email=normal_email)
        resp = client.get(
            "/api/admin/simulations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "NOT_SUPER_ADMIN"


# ─── Tests Réponse base ─────────────────────────────────────────────────────


class TestListSimulations:
    def test_empty_list(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        fake = _make_fake_supabase_with_sims([])
        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/simulations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"]["simulations"] == []
        assert body["data"]["total"] == 0
        assert body["data"]["limit"] == 50
        assert body["data"]["offset"] == 0

    def test_single_sim_with_org_enrichment(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        sim_row = {
            "simulation_id": "sim-uuid-1",
            "org_id": "org-uuid-1",
            "created_by": "user-1",
            "created_at": "2026-04-01T10:00:00Z",
            "package_id": "fusion-bancaire-mena",
            "is_published": True,
            "outcome": {"label": "called_it"},
            "brier_score": 0.18,
        }
        org_lookup = [{"id": "org-uuid-1", "slug": "acme", "name": "ACME Corp"}]
        fake = _make_fake_supabase_with_sims([sim_row], orgs_lookup=org_lookup, total=1)
        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/simulations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        sims = body["data"]["simulations"]
        assert len(sims) == 1
        s = sims[0]
        assert s["simulation_id"] == "sim-uuid-1"
        assert s["org_id"] == "org-uuid-1"
        assert s["org_name"] == "ACME Corp"
        assert s["org_slug"] == "acme"
        assert s["package_id"] == "fusion-bancaire-mena"
        assert s["is_published"] is True
        assert s["outcome"]["label"] == "called_it"
        assert s["brier_score"] == 0.18
        assert body["data"]["total"] == 1

    def test_filter_org_id(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        fake = _make_fake_supabase_with_sims([], total=0)
        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/simulations?org_id=org-xxx",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        # Vérifie que .eq('org_id', 'org-xxx') a été appelé
        eq_calls = fake._captured["eq_calls"]
        assert ("org_id", "org-xxx") in eq_calls

    def test_filter_package_id(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        fake = _make_fake_supabase_with_sims([], total=0)
        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/simulations?package_id=fusion-bancaire-mena",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        eq_calls = fake._captured["eq_calls"]
        assert ("package_id", "fusion-bancaire-mena") in eq_calls

    def test_filter_published_true(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        fake = _make_fake_supabase_with_sims([], total=0)
        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/simulations?published=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        eq_calls = fake._captured["eq_calls"]
        assert ("is_published", True) in eq_calls

    def test_filter_published_false(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        fake = _make_fake_supabase_with_sims([], total=0)
        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/simulations?published=false",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        eq_calls = fake._captured["eq_calls"]
        assert ("is_published", False) in eq_calls

    def test_pagination_limit_and_offset(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        fake = _make_fake_supabase_with_sims([], total=0)
        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/simulations?limit=25&offset=50",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["limit"] == 25
        assert body["data"]["offset"] == 50

    def test_pagination_limit_capped_at_max(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        fake = _make_fake_supabase_with_sims([], total=0)
        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        # limit demandé > max → bornage à 200
        resp = client.get(
            "/api/admin/simulations?limit=99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["limit"] == 200


# ─── Tests Robustesse ───────────────────────────────────────────────────────


class TestRobustness:
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
            "/api/admin/simulations",
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
            chain = MagicMock()
            chain.eq.return_value = chain
            chain.order.return_value = chain
            chain.range.return_value = chain
            chain.execute.side_effect = RuntimeError("db unreachable")
            tbl.select.return_value = chain
            return tbl

        fake.table.side_effect = _table
        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/simulations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 500
        assert resp.get_json()["error_code"] == "ADMIN_SIMS_FAILED"

    def test_org_enrichment_failure_does_not_brick(
        self, client, whitelist_env, jwt_secret,
        super_admin_user_id, super_admin_email, monkeypatch,
    ):
        """Si l'enrichment org échoue, on doit toujours retourner les sims (org_name=None)."""
        sim_row = {
            "simulation_id": "sim-1",
            "org_id": "org-1",
            "created_by": "u",
            "created_at": "2026-04-01T10:00:00Z",
            "package_id": "p",
            "is_published": False,
            "outcome": None,
            "brier_score": None,
        }
        fake = MagicMock()

        def _table(name: str):
            tbl = MagicMock()
            if name == "simulation_ownership":
                chain = MagicMock()
                chain.eq.return_value = chain
                chain.order.return_value = chain
                chain.range.return_value = chain
                chain.execute.return_value = MagicMock(data=[sim_row], count=1)
                tbl.select.return_value = chain
            elif name == "organizations":
                # Erreur lors du lookup batch — l'endpoint doit être robuste.
                chain = MagicMock()
                chain.in_.return_value = chain
                chain.execute.side_effect = RuntimeError("orgs fetch error")
                tbl.select.return_value = chain
            return tbl

        fake.table.side_effect = _table
        monkeypatch.setattr(
            "app.api.admin.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, sub=super_admin_user_id, email=super_admin_email)
        resp = client.get(
            "/api/admin/simulations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        sims = body["data"]["simulations"]
        assert len(sims) == 1
        # L'enrichment a failed → org_name et org_slug doivent être None.
        assert sims[0]["org_name"] is None
        assert sims[0]["org_slug"] is None
        assert sims[0]["simulation_id"] == "sim-1"
