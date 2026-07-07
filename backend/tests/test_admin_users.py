"""Tests unitaires US-137 — Page admin Users (liste cross-tenant inscriptions).

Couvre :
  - GET /api/admin/users — liste paginée (super-admin vs org admin vs member 403)
  - GET /api/admin/users/stats — statistiques globales
  - GET /api/admin/users/<user_id>/simulations — simulations d'un user
  - Filtre org_id, search email, pagination limit/offset
  - Scénarios RLS : super-admin voit tout, org admin scopé, member 403

Toutes les interactions Supabase sont monkeypatchées via MagicMock —
aucune dépendance live à Supabase, aucun JWT réel n'est généré.
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
    secret = "admin-users-tests-secret-xyz"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    return secret


@pytest.fixture
def super_admin_email() -> str:
    return "superadmin@bassira.ai"


@pytest.fixture
def org_admin_email() -> str:
    return "orgadmin@acme.com"


@pytest.fixture
def member_email() -> str:
    return "member@acme.com"


@pytest.fixture
def super_admin_id() -> str:
    return "uid-superadmin-0001"


@pytest.fixture
def org_admin_id() -> str:
    return "uid-orgadmin-0002"


@pytest.fixture
def member_id() -> str:
    return "uid-member-0003"


@pytest.fixture
def org_id() -> str:
    return "oid-acme-corp-0099"


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


# ─── Helpers Supabase mock ───────────────────────────────────────────────────


def _make_fake_user(
    uid: str,
    email: str,
    created_at: str = "2026-01-15T10:00:00+00:00",
    last_sign_in_at: str | None = None,
) -> MagicMock:
    """Construit un objet user Supabase Auth factice."""
    u = MagicMock()
    u.id = uid
    u.email = email
    u.created_at = created_at
    u.last_sign_in_at = last_sign_in_at
    u.user_metadata = {}
    return u


class _FakeListUsersResp:
    """Simule la réponse de auth.admin.list_users()."""
    def __init__(self, users: List[Any]):
        self.users = users


def _make_supabase_mock(
    members_rows: List[Dict[str, Any]] | None = None,
    auth_users: List[Any] | None = None,
    sims_rows: List[Dict[str, Any]] | None = None,
    membership_check_rows: List[Dict[str, Any]] | None = None,
) -> MagicMock:
    """Construit un mock Supabase complet pour les tests admin_users."""
    members_data = members_rows if members_rows is not None else []
    sims_data = sims_rows if sims_rows is not None else []
    membership_data = membership_check_rows if membership_check_rows is not None else []

    call_counts: Dict[str, int] = {"org_members": 0}

    def _make_table_mock(rows: List[Dict[str, Any]]) -> MagicMock:
        t = MagicMock()
        resp = MagicMock()
        resp.data = rows
        t.select.return_value = t
        t.eq.return_value = t
        t.in_.return_value = t
        t.order.return_value = t
        t.limit.return_value = t
        t.execute.return_value = resp
        return t

    def _table_side_effect(table_name: str) -> MagicMock:
        if table_name == "org_members":
            call_counts["org_members"] += 1
            # Premier appel : liste members pour construire la map users/orgs
            # Second appel éventuel (org admin membership check) : membership_data
            rows = (
                membership_data
                if (membership_check_rows is not None and call_counts["org_members"] > 1)
                else members_data
            )
            return _make_table_mock(rows)
        elif table_name == "simulation_ownership":
            return _make_table_mock(sims_data)
        else:
            return _make_table_mock([])

    mock_cli = MagicMock()
    mock_cli.table.side_effect = _table_side_effect
    mock_cli.auth.admin.list_users.return_value = _FakeListUsersResp(
        auth_users if auth_users is not None else []
    )
    return mock_cli


# ─── Tests : sécurité accès ──────────────────────────────────────────────────


class TestAdminUsersAccess:
    """Tests de contrôle d'accès : 401/403 pour les non autorisés."""

    def test_no_token_returns_401(self, client, whitelist_env):
        resp = client.get("/api/admin/users")
        assert resp.status_code == 401
        assert resp.get_json()["error_code"] == "MISSING_AUTH"

    def test_invalid_token_returns_401(self, client, whitelist_env, jwt_secret):
        resp = client.get(
            "/api/admin/users",
            headers={"Authorization": "Bearer not-a-real-jwt"},
        )
        assert resp.status_code == 401
        assert resp.get_json()["error_code"] == "INVALID_TOKEN"

    def test_member_returns_403(
        self, client, whitelist_env, jwt_secret, member_id, member_email, org_id, monkeypatch
    ):
        """Un simple membre (pas admin/owner) reçoit 403."""
        token = _make_token(jwt_secret, sub=member_id, email=member_email)

        members_rows = [
            {
                "user_id": member_id, "role": "member", "org_id": org_id,
                "organizations": {
                    "id": org_id, "name": "ACME Corp", "slug": "acme",
                    "sector": None, "country_code": None,
                    "status": "active", "self_service_enabled": False,
                },
            },
        ]
        mock_cli = _make_supabase_mock(members_rows=members_rows)
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)
        monkeypatch.setattr("app.api.admin_users.get_user_orgs", lambda uid, **kw: [
            {
                "id": org_id, "slug": "acme", "name": "ACME Corp",
                "sector": None, "country_code": None, "status": "active",
                "self_service_enabled": False, "role": "member",
            }
        ])

        resp = client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["error_code"] == "INSUFFICIENT_ROLE"

    def test_stats_no_token_returns_401(self, client, whitelist_env):
        resp = client.get("/api/admin/users/stats")
        assert resp.status_code == 401

    def test_simulations_no_token_returns_401(self, client, whitelist_env):
        resp = client.get("/api/admin/users/some-user-id/simulations")
        assert resp.status_code == 401


# ─── Tests : super-admin voit tout ──────────────────────────────────────────


class TestAdminUsersSuperAdmin:
    """Super-admin : accès cross-tenant complet."""

    def test_list_users_super_admin_sees_all(
        self, client, whitelist_env, jwt_secret, super_admin_id, super_admin_email,
        org_id, monkeypatch
    ):
        """Super-admin reçoit 200 avec la liste de tous les users."""
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)

        uid1, uid2 = "uid-user-alpha-001", "uid-user-beta-002"
        members_rows = [
            {
                "user_id": uid1, "role": "owner", "org_id": org_id,
                "organizations": {"id": org_id, "name": "ACME Corp", "slug": "acme"},
            },
            {
                "user_id": uid2, "role": "member", "org_id": org_id,
                "organizations": {"id": org_id, "name": "ACME Corp", "slug": "acme"},
            },
        ]
        auth_users = [
            _make_fake_user(uid1, "alpha@acme.com", "2026-01-20T00:00:00+00:00"),
            _make_fake_user(uid2, "beta@acme.com", "2026-01-10T00:00:00+00:00"),
        ]
        mock_cli = _make_supabase_mock(members_rows=members_rows, auth_users=auth_users)
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "users" in data["data"]
        assert "total" in data["data"]
        assert len(data["data"]["users"]) == 2

    def test_list_users_response_shape(
        self, client, whitelist_env, jwt_secret, super_admin_id, super_admin_email,
        org_id, monkeypatch
    ):
        """Vérifie la structure de chaque user dans la réponse."""
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        uid1 = "uid-shape-test-001"
        members_rows = [
            {
                "user_id": uid1, "role": "owner", "org_id": org_id,
                "organizations": {"id": org_id, "name": "ACME Corp", "slug": "acme"},
            },
        ]
        auth_users = [_make_fake_user(uid1, "shape@test.com")]
        mock_cli = _make_supabase_mock(members_rows=members_rows, auth_users=auth_users)
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        users = resp.get_json()["data"]["users"]
        assert len(users) == 1
        u = users[0]
        for field in ("id", "email", "created_at", "last_sign_in_at", "orgs", "meta_data"):
            assert field in u, f"Champ manquant : {field}"
        assert isinstance(u["orgs"], list)

    def test_filter_by_org_id(
        self, client, whitelist_env, jwt_secret, super_admin_id, super_admin_email,
        org_id, monkeypatch
    ):
        """Filtre ?org_id= restreint la liste à cette org."""
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        uid1 = "uid-org-filter-001"

        members_rows_filtered = [
            {
                "user_id": uid1, "role": "admin", "org_id": org_id,
                "organizations": {"id": org_id, "name": "ACME Corp", "slug": "acme"},
            },
        ]
        auth_users = [_make_fake_user(uid1, "filtered@acme.com")]
        mock_cli = _make_supabase_mock(members_rows=members_rows_filtered, auth_users=auth_users)
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            f"/api/admin/users?org_id={org_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["total"] >= 0

    def test_search_email_filter(
        self, client, whitelist_env, jwt_secret, super_admin_id, super_admin_email,
        org_id, monkeypatch
    ):
        """Filtre ?search= restreint aux emails contenant la chaîne."""
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        uid1, uid2 = "uid-search-001", "uid-search-002"
        members_rows = [
            {
                "user_id": uid1, "role": "owner", "org_id": org_id,
                "organizations": {"id": org_id, "name": "ACME Corp", "slug": "acme"},
            },
            {
                "user_id": uid2, "role": "member", "org_id": org_id,
                "organizations": {"id": org_id, "name": "ACME Corp", "slug": "acme"},
            },
        ]
        auth_users = [
            _make_fake_user(uid1, "alice@acme.com"),
            _make_fake_user(uid2, "bob@other.com"),
        ]
        mock_cli = _make_supabase_mock(members_rows=members_rows, auth_users=auth_users)
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            "/api/admin/users?search=alice",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        emails = [u["email"] for u in data["users"]]
        assert all("alice" in e.lower() for e in emails)
        assert len(emails) == 1

    def test_pagination_limit_offset(
        self, client, whitelist_env, jwt_secret, super_admin_id, super_admin_email,
        org_id, monkeypatch
    ):
        """Pagination limit/offset retourne le bon sous-ensemble."""
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        uids = [f"uid-page-{i:03d}" for i in range(5)]
        members_rows = [
            {
                "user_id": uid, "role": "member", "org_id": org_id,
                "organizations": {"id": org_id, "name": "ACME Corp", "slug": "acme"},
            }
            for uid in uids
        ]
        auth_users = [_make_fake_user(uid, f"user{i}@acme.com") for i, uid in enumerate(uids)]
        mock_cli = _make_supabase_mock(members_rows=members_rows, auth_users=auth_users)
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            "/api/admin/users?limit=2&offset=0",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["limit"] == 2
        assert data["offset"] == 0
        assert len(data["users"]) <= 2
        assert data["total"] == 5

    def test_invalid_limit_returns_400(
        self, client, whitelist_env, jwt_secret, super_admin_id, super_admin_email,
        monkeypatch
    ):
        """limit ou offset invalides retournent 400."""
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        mock_cli = _make_supabase_mock()
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            "/api/admin/users?limit=not-a-number",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "INVALID_PARAMS"


# ─── Tests : org admin scopé ─────────────────────────────────────────────────


class TestAdminUsersOrgAdmin:
    """Org admin : accès restreint à ses organisations."""

    def test_org_admin_sees_own_org_users(
        self, client, whitelist_env, jwt_secret, org_admin_id, org_admin_email,
        org_id, monkeypatch
    ):
        """Org admin voit les users de ses orgs (200)."""
        token = _make_token(jwt_secret, sub=org_admin_id, email=org_admin_email)
        target_uid = "uid-target-user-001"

        members_rows = [
            {
                "user_id": target_uid, "role": "member", "org_id": org_id,
                "organizations": {"id": org_id, "name": "ACME Corp", "slug": "acme"},
            },
        ]
        auth_users = [_make_fake_user(target_uid, "target@acme.com")]
        mock_cli = _make_supabase_mock(members_rows=members_rows, auth_users=auth_users)

        # Patch get_user_orgs pour retourner l'org admin avec rôle admin
        monkeypatch.setattr("app.api.admin_users.get_user_orgs", lambda uid, **kw: [
            {
                "id": org_id, "slug": "acme", "name": "ACME Corp",
                "sector": None, "country_code": None, "status": "active",
                "self_service_enabled": False, "role": "admin",
            }
        ])
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_org_admin_cannot_access_other_org(
        self, client, whitelist_env, jwt_secret, org_admin_id, org_admin_email,
        org_id, monkeypatch
    ):
        """Org admin reçoit 404 si filtre par org_id qui n'est pas la sienne."""
        token = _make_token(jwt_secret, sub=org_admin_id, email=org_admin_email)
        foreign_org_id = "oid-foreign-org-9999"

        mock_cli = _make_supabase_mock()

        monkeypatch.setattr("app.api.admin_users.get_user_orgs", lambda uid, **kw: [
            {
                "id": org_id, "slug": "acme", "name": "ACME Corp",
                "sector": None, "country_code": None, "status": "active",
                "self_service_enabled": False, "role": "admin",
            }
        ])
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            f"/api/admin/users?org_id={foreign_org_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
        assert resp.get_json()["error_code"] == "ORG_NOT_FOUND_FOR_USER"


# ─── Tests : endpoint /stats ─────────────────────────────────────────────────


class TestAdminUsersStats:
    """Tests du endpoint /stats."""

    def test_stats_super_admin_returns_200(
        self, client, whitelist_env, jwt_secret, super_admin_id, super_admin_email,
        org_id, monkeypatch
    ):
        """Super-admin reçoit 200 avec la structure stats attendue."""
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        uid1, uid2 = "uid-stats-001", "uid-stats-002"

        members_rows = [
            {"user_id": uid1, "org_id": org_id},
            {"user_id": uid2, "org_id": org_id},
        ]
        auth_users = [
            _make_fake_user(uid1, "s1@acme.com", last_sign_in_at="2026-05-04T10:00:00+00:00"),
            _make_fake_user(uid2, "s2@acme.com"),
        ]
        mock_cli = _make_supabase_mock(members_rows=members_rows, auth_users=auth_users)
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            "/api/admin/users/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        for field in ("total_users", "active_7d", "new_30d", "by_org"):
            assert field in data, f"Champ stats manquant : {field}"
        assert data["total_users"] == 2
        assert isinstance(data["by_org"], dict)

    def test_stats_member_returns_403(
        self, client, whitelist_env, jwt_secret, member_id, member_email,
        org_id, monkeypatch
    ):
        """Membre simple reçoit 403 sur /stats."""
        token = _make_token(jwt_secret, sub=member_id, email=member_email)
        mock_cli = _make_supabase_mock()
        monkeypatch.setattr("app.api.admin_users.get_user_orgs", lambda uid, **kw: [
            {
                "id": org_id, "slug": "acme", "name": "ACME Corp",
                "sector": None, "country_code": None, "status": "active",
                "self_service_enabled": False, "role": "member",
            }
        ])
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            "/api/admin/users/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_stats_by_org_structure(
        self, client, whitelist_env, jwt_secret, super_admin_id, super_admin_email,
        org_id, monkeypatch
    ):
        """Vérifie que by_org contient les bons comptes par org."""
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        org2 = "oid-second-org-0088"
        members_rows = [
            {"user_id": "uid-a", "org_id": org_id},
            {"user_id": "uid-b", "org_id": org_id},
            {"user_id": "uid-c", "org_id": org2},
        ]
        mock_cli = _make_supabase_mock(members_rows=members_rows)
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            "/api/admin/users/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        by_org = resp.get_json()["data"]["by_org"]
        assert by_org.get(org_id, 0) == 2
        assert by_org.get(org2, 0) == 1

    def test_stats_total_users_reflects_auth_users_not_members(
        self, client, whitelist_env, jwt_secret, super_admin_id, super_admin_email,
        org_id, monkeypatch
    ):
        """US-138 — Bug observé en prod 2026-05-08 : la table affichait
        3 utilisateurs (depuis /api/admin/users qui lit auth.users) mais
        le compteur `total_users` du card stats affichait 1 (qui ne
        comptait que les users avec membership).

        Reproduction : 3 users dans auth.users, 1 seul a une membership.
        Le total doit refléter ce qui est réellement listé (3), avec le
        compteur secondaire `users_with_org` pour la sémantique "actifs
        dans une org" (1 dans cet exemple).
        """
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        uid_with_org = "uid-bug001-with-org"
        uid_orphan_a = "uid-bug001-orphan-a"
        uid_orphan_b = "uid-bug001-orphan-b"

        # Un seul user a une membership
        members_rows = [
            {"user_id": uid_with_org, "org_id": org_id},
        ]
        # Trois users existent dans auth.users
        auth_users = [
            _make_fake_user(uid_with_org, "owner@acme.com"),
            _make_fake_user(uid_orphan_a, "orphan-a@example.com"),
            _make_fake_user(uid_orphan_b, "orphan-b@example.com"),
        ]
        mock_cli = _make_supabase_mock(members_rows=members_rows, auth_users=auth_users)
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            "/api/admin/users/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["total_users"] == 3, (
            "total_users doit refléter auth.users (3), pas la membership count "
            "(1) — Avant fix US-138 ce champ valait 1, contredisant active_7d/"
            "new_30d qui voient 3."
        )
        assert data.get("users_with_org") == 1, (
            "users_with_org doit refléter le nombre d'utilisateurs avec membership."
        )


# ─── Tests : endpoint /<user_id>/simulations ─────────────────────────────────


class TestAdminUserSimulations:
    """Tests du endpoint /<user_id>/simulations."""

    def test_super_admin_gets_user_simulations(
        self, client, whitelist_env, jwt_secret, super_admin_id, super_admin_email,
        org_id, monkeypatch
    ):
        """Super-admin reçoit 200 avec les simulations de l'user."""
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        target_uid = "uid-sim-user-001"

        sims_rows = [
            {
                "simulation_id": "sim-001",
                "org_id": org_id,
                "created_by": target_uid,
                "package_id": "pkg-standard",
                "is_published": True,
                "outcome": None,
                "brier_score": None,
                "created_at": "2026-04-01T10:00:00+00:00",
                "organizations": {"id": org_id, "name": "ACME Corp", "slug": "acme"},
            }
        ]
        mock_cli = _make_supabase_mock(sims_rows=sims_rows)
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            f"/api/admin/users/{target_uid}/simulations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "simulations" in data
        assert "total" in data
        assert "user_id" in data
        assert data["user_id"] == target_uid

    def test_simulations_response_shape(
        self, client, whitelist_env, jwt_secret, super_admin_id, super_admin_email,
        org_id, monkeypatch
    ):
        """Vérifie la structure de chaque simulation dans la réponse."""
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        target_uid = "uid-sim-shape-001"
        sims_rows = [
            {
                "simulation_id": "sim-shape-001",
                "org_id": org_id,
                "created_by": target_uid,
                "package_id": "pkg-standard",
                "is_published": False,
                "outcome": None,
                "brier_score": None,
                "created_at": "2026-03-01T10:00:00+00:00",
                "organizations": {"id": org_id, "name": "ACME Corp", "slug": "acme"},
            }
        ]
        mock_cli = _make_supabase_mock(sims_rows=sims_rows)
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            f"/api/admin/users/{target_uid}/simulations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        sims = resp.get_json()["data"]["simulations"]
        assert len(sims) == 1
        s = sims[0]
        for field in ("simulation_id", "org_id", "package_id", "is_published", "created_at"):
            assert field in s, f"Champ simulation manquant : {field}"

    def test_simulations_pagination(
        self, client, whitelist_env, jwt_secret, super_admin_id, super_admin_email,
        org_id, monkeypatch
    ):
        """Pagination limit/offset fonctionne sur les simulations."""
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        target_uid = "uid-sim-page-001"
        sims_rows = [
            {
                "simulation_id": f"sim-{i:03d}",
                "org_id": org_id,
                "created_by": target_uid,
                "package_id": None,
                "is_published": False,
                "outcome": None,
                "brier_score": None,
                "created_at": f"2026-0{i + 1:01d}-01T00:00:00+00:00",
                "organizations": {},
            }
            for i in range(4)
        ]
        mock_cli = _make_supabase_mock(sims_rows=sims_rows)
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            f"/api/admin/users/{target_uid}/simulations?limit=2&offset=0",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["total"] == 4
        assert len(data["simulations"]) == 2

    def test_member_cannot_access_simulations(
        self, client, whitelist_env, jwt_secret, member_id, member_email,
        org_id, monkeypatch
    ):
        """Membre simple reçoit 403 sur /<user_id>/simulations."""
        token = _make_token(jwt_secret, sub=member_id, email=member_email)
        mock_cli = _make_supabase_mock()
        monkeypatch.setattr("app.api.admin_users.get_user_orgs", lambda uid, **kw: [
            {
                "id": org_id, "slug": "acme", "name": "ACME Corp",
                "sector": None, "country_code": None, "status": "active",
                "self_service_enabled": False, "role": "member",
            }
        ])
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            "/api/admin/users/some-other-uid/simulations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_org_admin_cannot_access_foreign_user_simulations(
        self, client, whitelist_env, jwt_secret, org_admin_id, org_admin_email,
        org_id, monkeypatch
    ):
        """Org admin reçoit 403 pour un user hors de ses orgs."""
        token = _make_token(jwt_secret, sub=org_admin_id, email=org_admin_email)

        # Membership check retourne vide (l'user étranger n'est pas dans les orgs admin)
        mock_cli = _make_supabase_mock(membership_check_rows=[])

        monkeypatch.setattr("app.api.admin_users.get_user_orgs", lambda uid, **kw: [
            {
                "id": org_id, "slug": "acme", "name": "ACME Corp",
                "sector": None, "country_code": None, "status": "active",
                "self_service_enabled": False, "role": "admin",
            }
        ])
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.get(
            "/api/admin/users/foreign-user-uid/simulations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "ACCESS_DENIED"


# ─── Tests : US-138 — gestion membership user ↔ org ──────────────────────────


class TestUserOrgMembership:
    """Tests POST/DELETE /api/admin/users/<uid>/orgs (US-138)."""

    def _make_membership_mock(
        self,
        existing_rows=None,
        owners_rows=None,
        upsert_rows=None,
        delete_rows=None,
    ):
        """Mock Supabase pour les tests membership.

        existing_rows : retour des lookup .eq("org_id").eq("user_id").limit(1)
        owners_rows : retour du compte des owners (si test last-owner)
        """
        existing = existing_rows if existing_rows is not None else []
        owners = owners_rows if owners_rows is not None else []
        upsert_data = upsert_rows if upsert_rows is not None else []
        delete_data = delete_rows if delete_rows is not None else []

        # Les .eq() chainés peuvent retourner différents datasets selon
        # le contexte. On utilise un compteur pour distinguer.
        call_state = {"select_count": 0}

        def _build_table(name: str):
            t = MagicMock()
            t.select.return_value = t
            t.eq.return_value = t
            t.in_.return_value = t
            t.order.return_value = t
            t.limit.return_value = t

            def _execute_select():
                call_state["select_count"] += 1
                resp = MagicMock()
                # 1er select : lookup membership existante (1 row attendu)
                # 2e select : count des owners
                if call_state["select_count"] == 1:
                    resp.data = existing
                else:
                    resp.data = owners
                return resp

            t.execute.side_effect = _execute_select

            upsert_ret = MagicMock()
            upsert_ret.execute.return_value = MagicMock(data=upsert_data)
            t.upsert.return_value = upsert_ret

            delete_ret = MagicMock()
            delete_ret.eq.return_value = delete_ret
            delete_ret.execute.return_value = MagicMock(data=delete_data)
            t.delete.return_value = delete_ret
            return t

        mock_cli = MagicMock()
        mock_cli.table.side_effect = _build_table
        return mock_cli

    def test_super_admin_adds_user_to_org(
        self, client, whitelist_env, jwt_secret,
        super_admin_id, super_admin_email, org_id, monkeypatch,
    ):
        """Super-admin POSTe { org_id, role } → 200 + payload."""
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        target_uid = "uid-target-user-001"
        mock_cli = self._make_membership_mock()
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.post(
            f"/api/admin/users/{target_uid}/orgs",
            json={"org_id": org_id, "role": "admin"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()["data"]
        assert data == {"user_id": target_uid, "org_id": org_id, "role": "admin"}

    def test_invalid_role_returns_400(
        self, client, whitelist_env, jwt_secret,
        super_admin_id, super_admin_email, org_id, monkeypatch,
    ):
        """role hors {member, admin, owner} → 400 INVALID_ROLE."""
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        mock_cli = self._make_membership_mock()
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)
        resp = client.post(
            "/api/admin/users/uid-x/orgs",
            json={"org_id": org_id, "role": "god"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "INVALID_ROLE"

    def test_missing_org_id_returns_400(
        self, client, whitelist_env, jwt_secret,
        super_admin_id, super_admin_email, monkeypatch,
    ):
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        mock_cli = self._make_membership_mock()
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)
        resp = client.post(
            "/api/admin/users/uid-x/orgs",
            json={"role": "member"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "MISSING_ORG_ID"

    def test_org_admin_cannot_add_to_other_org(
        self, client, whitelist_env, jwt_secret,
        org_admin_id, org_admin_email, org_id, monkeypatch,
    ):
        """Org admin tente d'ajouter à une org dont il n'est pas admin → 403."""
        token = _make_token(jwt_secret, sub=org_admin_id, email=org_admin_email)
        mock_cli = self._make_membership_mock()
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)
        # L'org admin n'est admin que de "another-org-id", pas de org_id ciblé
        monkeypatch.setattr("app.api.admin_users.get_user_orgs", lambda uid, **kw: [
            {
                "id": "another-org-id", "slug": "other", "name": "Other",
                "sector": None, "country_code": None, "status": "active",
                "self_service_enabled": False, "role": "admin",
            }
        ])

        resp = client.post(
            "/api/admin/users/uid-victim/orgs",
            json={"org_id": org_id, "role": "member"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "ORG_NOT_FOUND_FOR_USER"

    def test_super_admin_removes_user_from_org(
        self, client, whitelist_env, jwt_secret,
        super_admin_id, super_admin_email, org_id, monkeypatch,
    ):
        """Super-admin DELETE membership existante (rôle member) → 200."""
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        target_uid = "uid-target-002"
        mock_cli = self._make_membership_mock(
            existing_rows=[{"user_id": target_uid, "role": "member"}],
        )
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.delete(
            f"/api/admin/users/{target_uid}/orgs/{org_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()["data"] == {"deleted": True}

    def test_remove_nonexistent_returns_404(
        self, client, whitelist_env, jwt_secret,
        super_admin_id, super_admin_email, org_id, monkeypatch,
    ):
        """DELETE membership inexistante → 404 MEMBERSHIP_NOT_FOUND."""
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        mock_cli = self._make_membership_mock(existing_rows=[])
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.delete(
            f"/api/admin/users/uid-nope/orgs/{org_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
        assert resp.get_json()["error_code"] == "MEMBERSHIP_NOT_FOUND"

    def test_cannot_remove_last_owner(
        self, client, whitelist_env, jwt_secret,
        super_admin_id, super_admin_email, org_id, monkeypatch,
    ):
        """Tentative de retirer le DERNIER owner → 409 LAST_OWNER."""
        token = _make_token(jwt_secret, sub=super_admin_id, email=super_admin_email)
        target_uid = "uid-last-owner"
        # 1er select retourne l'user en owner ; 2e select compte les owners (1 seul)
        mock_cli = self._make_membership_mock(
            existing_rows=[{"user_id": target_uid, "role": "owner"}],
            owners_rows=[{"user_id": target_uid}],
        )
        monkeypatch.setattr("app.api.admin_users.get_supabase_admin", lambda: mock_cli)

        resp = client.delete(
            f"/api/admin/users/{target_uid}/orgs/{org_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409
        assert resp.get_json()["error_code"] == "LAST_OWNER"
