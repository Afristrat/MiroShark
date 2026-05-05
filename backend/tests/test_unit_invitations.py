"""Tests unitaires US-115 — Système d'invitation user → org.

Couvre :
  - Service ``org_invitations`` :
    * create_invitation (validation + insert)
    * get_invitation / get_invitation_with_org
    * list_pending_invitations (filtre expirés)
    * revoke_invitation
    * redeem_invitation : succès + expirée + déjà consommée + email mismatch
  - Endpoints HTTP :
    * POST /api/admin/invitations  (super-admin + org admin path)
    * GET  /api/admin/invitations
    * DELETE /api/admin/invitations/<token>
    * GET  /api/invitations/<token>/accept (public, no auth)
    * POST /api/invitations/<token>/redeem (auth required)
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import MagicMock

import jwt as pyjwt
import pytest

from app import create_app
from app.auth import jwt_verifier
from app.services import org_invitations as oi


# ─── Fixtures de base ───────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_jwt_cache():
    jwt_verifier._cache_clear()
    yield
    jwt_verifier._cache_clear()


@pytest.fixture
def jwt_secret(monkeypatch):
    secret = "invitations-tests-secret"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    return secret


@pytest.fixture
def super_admin_email() -> str:
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


def _iso(delta_days: int = 0) -> str:
    return (
        datetime.now(timezone.utc) + timedelta(days=delta_days)
    ).replace(microsecond=0).isoformat()


def _make_fake_supabase(
    *,
    invitations: List[Dict[str, Any]] | None = None,
    insert_invitation_returns: Dict[str, Any] | None = None,
    insert_member_raises: Exception | None = None,
    org_meta: Dict[str, Any] | None = None,
    delete_rows: List[Dict[str, Any]] | None = None,
    update_rows: List[Dict[str, Any]] | None = None,
):
    """MagicMock Supabase qui supporte les chaînes utilisées par le service."""
    fake = MagicMock()
    invitations = invitations or []
    insert_invitation_returns = insert_invitation_returns or {}
    org_meta = org_meta or {}
    if delete_rows is None:
        delete_rows = [{"token": "deleted"}]
    if update_rows is None:
        update_rows = [{"token": "updated"}]

    def _table(name: str):
        tbl = MagicMock()
        if name == "org_invitations":
            # Insert
            ins_chain = MagicMock()
            ins_chain.execute.return_value = MagicMock(
                data=[insert_invitation_returns] if insert_invitation_returns else []
            )
            tbl.insert.return_value = ins_chain

            # Select chains
            sel_chain = MagicMock()
            eq_chain = MagicMock()
            limit_chain = MagicMock()
            order_chain = MagicMock()
            is_null_chain = MagicMock()
            is_null_order = MagicMock()

            limit_chain.execute.return_value = MagicMock(data=invitations)
            order_chain.execute.return_value = MagicMock(data=invitations)
            is_null_order.execute.return_value = MagicMock(data=invitations)
            is_null_chain.order.return_value = is_null_order
            eq_chain.is_.return_value = is_null_chain
            eq_chain.limit.return_value = limit_chain
            eq_chain.order.return_value = order_chain
            eq_chain.execute.return_value = MagicMock(data=invitations)

            sel_chain.eq.return_value = eq_chain
            tbl.select.return_value = sel_chain

            # Delete
            del_chain = MagicMock()
            del_eq_chain = MagicMock()
            del_eq_chain.execute.return_value = MagicMock(data=delete_rows)
            del_chain.eq.return_value = del_eq_chain
            tbl.delete.return_value = del_chain

            # Update
            upd_chain = MagicMock()
            upd_eq_chain = MagicMock()
            upd_eq_chain.execute.return_value = MagicMock(data=update_rows)
            upd_chain.eq.return_value = upd_eq_chain
            tbl.update.return_value = upd_chain
        elif name == "organizations":
            sel_chain = MagicMock()
            eq_chain = MagicMock()
            limit_chain = MagicMock()
            limit_chain.execute.return_value = MagicMock(
                data=[org_meta] if org_meta else []
            )
            eq_chain.limit.return_value = limit_chain
            eq_chain.execute.return_value = MagicMock(
                data=[org_meta] if org_meta else []
            )
            sel_chain.eq.return_value = eq_chain
            tbl.select.return_value = sel_chain
        elif name == "org_members":
            ins_chain = MagicMock()
            if insert_member_raises is not None:
                ins_chain.execute.side_effect = insert_member_raises
            else:
                ins_chain.execute.return_value = MagicMock(data=[{"ok": True}])
            tbl.insert.return_value = ins_chain
        return tbl

    fake.table.side_effect = _table
    return fake


# ─── Tests : create_invitation ──────────────────────────────────────────────


class TestCreateInvitation:
    def test_create_success(self):
        fake = _make_fake_supabase(
            insert_invitation_returns={
                "token": "tok-uuid-1",
                "org_id": "org-1",
                "email": "x@y.com",
                "role": "member",
                "expires_at": _iso(7),
                "created_at": _iso(0),
            }
        )
        result = oi.create_invitation(
            "org-1", "X@Y.com", role="member", invited_by="u1", client=fake
        )
        assert result["token"] == "tok-uuid-1"
        assert result["org_id"] == "org-1"

    def test_invalid_email_raises(self):
        with pytest.raises(ValueError):
            oi.create_invitation("org-1", "no-at-symbol", client=MagicMock())

    def test_invalid_role_raises(self):
        with pytest.raises(ValueError):
            oi.create_invitation(
                "org-1", "x@y.com", role="owner", client=MagicMock()
            )

    def test_invalid_org_id_raises(self):
        with pytest.raises(ValueError):
            oi.create_invitation("", "x@y.com", client=MagicMock())

    def test_lowercased_email(self):
        captured = {}
        fake = MagicMock()

        def _table(name):
            t = MagicMock()
            ins_chain = MagicMock()
            def exec_side(*a, **k):
                return MagicMock(data=[{"token": "ok"}])
            ins_chain.execute.side_effect = exec_side
            def insert_side(payload, *a, **k):
                captured["payload"] = payload
                return ins_chain
            t.insert.side_effect = insert_side
            return t
        fake.table.side_effect = _table
        oi.create_invitation("org-1", "Foo@BAR.com", client=fake)
        assert captured["payload"]["email"] == "foo@bar.com"


# ─── Tests : get_invitation / get_invitation_with_org ───────────────────────


class TestGetInvitation:
    def test_found(self):
        rows = [{"token": "tok-1", "email": "x@y.com", "role": "member", "org_id": "org-1"}]
        fake = _make_fake_supabase(invitations=rows)
        out = oi.get_invitation("tok-1", client=fake)
        assert out is not None
        assert out["email"] == "x@y.com"

    def test_not_found(self):
        fake = _make_fake_supabase(invitations=[])
        out = oi.get_invitation("zzz", client=fake)
        assert out is None

    def test_empty_token(self):
        out = oi.get_invitation("", client=MagicMock())
        assert out is None

    def test_error_returns_none(self):
        fake = MagicMock()
        fake.table.side_effect = RuntimeError("net")
        out = oi.get_invitation("tok-x", client=fake)
        assert out is None

    def test_with_org_meta(self):
        rows = [
            {"token": "tok-2", "email": "x@y.com", "role": "admin", "org_id": "org-2"}
        ]
        fake = _make_fake_supabase(
            invitations=rows,
            org_meta={"id": "org-2", "name": "ACME", "slug": "acme", "country_code": "MA"},
        )
        out = oi.get_invitation_with_org("tok-2", client=fake)
        assert out["org_name"] == "ACME"
        assert out["org_slug"] == "acme"
        assert out["org_country_code"] == "MA"


# ─── Tests : list_pending_invitations ───────────────────────────────────────


class TestListPending:
    def test_filters_expired(self):
        rows = [
            {"token": "t1", "expires_at": _iso(7), "accepted_at": None, "org_id": "o1"},
            {"token": "t2", "expires_at": _iso(-1), "accepted_at": None, "org_id": "o1"},
        ]
        fake = _make_fake_supabase(invitations=rows)
        out = oi.list_pending_invitations("o1", client=fake)
        # Le client mock retourne les 2, le service filtre côté Python.
        assert len(out) == 1
        assert out[0]["token"] == "t1"

    def test_empty_org_id(self):
        out = oi.list_pending_invitations("", client=MagicMock())
        assert out == []

    def test_error_returns_empty(self):
        fake = MagicMock()
        fake.table.side_effect = RuntimeError("net")
        out = oi.list_pending_invitations("o1", client=fake)
        assert out == []


# ─── Tests : revoke_invitation ──────────────────────────────────────────────


class TestRevokeInvitation:
    def test_revoke_success(self):
        fake = _make_fake_supabase(delete_rows=[{"token": "tok-1"}])
        ok = oi.revoke_invitation("tok-1", client=fake)
        assert ok is True

    def test_revoke_not_found(self):
        # Forcer delete_rows à [] explicitement (pas de fallback default).
        fake = MagicMock()
        def _table(name):
            t = MagicMock()
            del_chain = MagicMock()
            del_eq_chain = MagicMock()
            del_eq_chain.execute.return_value = MagicMock(data=[])
            del_chain.eq.return_value = del_eq_chain
            t.delete.return_value = del_chain
            return t
        fake.table.side_effect = _table
        ok = oi.revoke_invitation("tok-zzz", client=fake)
        assert ok is False

    def test_empty_token(self):
        ok = oi.revoke_invitation("", client=MagicMock())
        assert ok is False


# ─── Tests : redeem_invitation ──────────────────────────────────────────────


class TestRedeemInvitation:
    def test_redeem_success(self):
        rows = [{
            "token": "tok-1",
            "org_id": "org-1",
            "email": "user@example.com",
            "role": "member",
            "expires_at": _iso(5),
            "accepted_at": None,
            "invited_by": "admin-uuid",
        }]
        fake = _make_fake_supabase(invitations=rows)
        result = oi.redeem_invitation(
            "tok-1", "new-user-uuid",
            user_email="user@example.com",
            client=fake,
        )
        assert result["ok"] is True
        assert result["org_id"] == "org-1"
        assert result["role"] == "member"

    def test_redeem_not_found(self):
        fake = _make_fake_supabase(invitations=[])
        result = oi.redeem_invitation("tok-xxx", "u-1", client=fake)
        assert result["ok"] is False
        assert result["error_code"] == "INVITATION_NOT_FOUND"

    def test_redeem_expired(self):
        rows = [{
            "token": "tok-1",
            "org_id": "org-1",
            "email": "user@example.com",
            "role": "member",
            "expires_at": _iso(-1),
            "accepted_at": None,
        }]
        fake = _make_fake_supabase(invitations=rows)
        result = oi.redeem_invitation("tok-1", "u-1", client=fake)
        assert result["ok"] is False
        assert result["error_code"] == "INVITATION_EXPIRED"

    def test_redeem_already_consumed(self):
        rows = [{
            "token": "tok-1",
            "org_id": "org-1",
            "email": "user@example.com",
            "role": "member",
            "expires_at": _iso(5),
            "accepted_at": _iso(-1),
        }]
        fake = _make_fake_supabase(invitations=rows)
        result = oi.redeem_invitation("tok-1", "u-1", client=fake)
        assert result["ok"] is False
        assert result["error_code"] == "INVITATION_ALREADY_CONSUMED"

    def test_redeem_email_mismatch(self):
        rows = [{
            "token": "tok-1",
            "org_id": "org-1",
            "email": "intended@example.com",
            "role": "member",
            "expires_at": _iso(5),
            "accepted_at": None,
        }]
        fake = _make_fake_supabase(invitations=rows)
        result = oi.redeem_invitation(
            "tok-1", "u-1",
            user_email="attacker@evil.com",
            client=fake,
        )
        assert result["ok"] is False
        assert result["error_code"] == "EMAIL_MISMATCH"

    def test_redeem_idempotent_on_duplicate_member(self):
        """Si la row org_members existe déjà, redeem reste OK."""
        rows = [{
            "token": "tok-1",
            "org_id": "org-1",
            "email": "user@example.com",
            "role": "member",
            "expires_at": _iso(5),
            "accepted_at": None,
        }]
        fake = _make_fake_supabase(
            invitations=rows,
            insert_member_raises=Exception("duplicate key (23505)"),
        )
        result = oi.redeem_invitation(
            "tok-1", "u-1",
            user_email="user@example.com",
            client=fake,
        )
        assert result["ok"] is True

    def test_redeem_invalid_token(self):
        result = oi.redeem_invitation("", "u-1", client=MagicMock())
        assert result["ok"] is False
        assert result["error_code"] == "INVALID_TOKEN"

    def test_redeem_invalid_user(self):
        result = oi.redeem_invitation("tok-1", "", client=MagicMock())
        assert result["ok"] is False
        assert result["error_code"] == "INVALID_USER"


# ─── Tests : endpoints HTTP — POST /api/admin/invitations ───────────────────


class TestPostInvitationEndpoint:
    def test_unauth_401(self, client):
        resp = client.post("/api/admin/invitations", json={"email": "x@y.com"})
        assert resp.status_code == 401

    def test_invalid_email_400(
        self, client, jwt_secret, whitelist_env, super_admin_email
    ):
        token = _make_token(jwt_secret, "u-super", super_admin_email)
        resp = client.post(
            "/api/admin/invitations",
            json={"email": "not-an-email", "org_id": "org-1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "INVALID_EMAIL"

    def test_invalid_role_400(
        self, client, jwt_secret, whitelist_env, super_admin_email
    ):
        token = _make_token(jwt_secret, "u-super", super_admin_email)
        resp = client.post(
            "/api/admin/invitations",
            json={"email": "x@y.com", "role": "owner", "org_id": "org-1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "INVALID_ROLE"

    def test_super_admin_must_provide_org_id(
        self, client, jwt_secret, whitelist_env, super_admin_email
    ):
        token = _make_token(jwt_secret, "u-super", super_admin_email)
        resp = client.post(
            "/api/admin/invitations",
            json={"email": "x@y.com", "role": "member"},  # no org_id
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "ORG_ID_REQUIRED"

    def test_super_admin_creates_invitation(
        self, client, jwt_secret, whitelist_env, super_admin_email, monkeypatch
    ):
        fake = _make_fake_supabase(
            insert_invitation_returns={
                "token": "tok-new",
                "org_id": "org-1",
                "email": "x@y.com",
                "role": "member",
                "expires_at": _iso(7),
                "created_at": _iso(0),
            },
            org_meta={"id": "org-1", "name": "ACME", "slug": "acme"},
        )
        monkeypatch.setattr(
            "app.api.invitations.get_supabase_admin",
            lambda: fake,
        )
        from app.services import email_service
        monkeypatch.setattr(email_service, "send_email", lambda *a, **k: True)

        token = _make_token(jwt_secret, "u-super", super_admin_email)
        resp = client.post(
            "/api/admin/invitations",
            json={"email": "x@y.com", "role": "member", "org_id": "org-1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.get_data(as_text=True)
        body = resp.get_json()
        assert body["data"]["invitation"]["token"] == "tok-new"
        assert body["data"]["email_sent"] is True

    def test_member_role_403(
        self, client, jwt_secret, whitelist_env, monkeypatch
    ):
        """Un user simple member (pas admin/owner) ne peut pas inviter."""
        monkeypatch.setattr(
            "app.api.invitations.get_user_orgs",
            lambda user_id: [{"id": "org-1", "role": "member"}],
        )
        token = _make_token(jwt_secret, "u-member", "user@somecorp.com")
        resp = client.post(
            "/api/admin/invitations",
            json={"email": "new@y.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "INSUFFICIENT_ROLE"

    def test_org_admin_creates_invitation(
        self, client, jwt_secret, whitelist_env, monkeypatch
    ):
        """Org admin (pas super-admin) peut inviter dans son org."""
        monkeypatch.setattr(
            "app.api.invitations.get_user_orgs",
            lambda user_id: [{"id": "org-mine", "role": "admin"}],
        )
        fake = _make_fake_supabase(
            insert_invitation_returns={
                "token": "tok-org-admin",
                "org_id": "org-mine",
                "email": "x@y.com",
                "role": "member",
                "expires_at": _iso(7),
                "created_at": _iso(0),
            },
            org_meta={"id": "org-mine", "name": "Mine", "slug": "mine"},
        )
        monkeypatch.setattr(
            "app.api.invitations.get_supabase_admin",
            lambda: fake,
        )
        from app.services import email_service
        monkeypatch.setattr(email_service, "send_email", lambda *a, **k: True)

        token = _make_token(jwt_secret, "u-orgadmin", "boss@mine.com")
        resp = client.post(
            "/api/admin/invitations",
            json={"email": "x@y.com", "role": "member"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        assert resp.get_json()["data"]["invitation"]["token"] == "tok-org-admin"


# ─── Tests : GET /api/admin/invitations (liste pending) ─────────────────────


class TestListInvitationsEndpoint:
    def test_unauth_401(self, client):
        resp = client.get("/api/admin/invitations")
        assert resp.status_code == 401

    def test_super_admin_lists_for_org(
        self, client, jwt_secret, whitelist_env, super_admin_email, monkeypatch
    ):
        fake = _make_fake_supabase(
            invitations=[
                {
                    "token": "t1", "email": "a@b.com", "role": "member",
                    "expires_at": _iso(5), "accepted_at": None, "org_id": "org-1",
                },
            ]
        )
        monkeypatch.setattr(
            "app.api.invitations.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, "u-super", super_admin_email)
        resp = client.get(
            "/api/admin/invitations?org_id=org-1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["data"]["invitations"]) == 1


# ─── Tests : DELETE /api/admin/invitations/<token> ──────────────────────────


class TestRevokeEndpoint:
    def test_unauth_401(self, client):
        resp = client.delete("/api/admin/invitations/some-token")
        assert resp.status_code == 401

    def test_super_admin_revokes(
        self, client, jwt_secret, whitelist_env, super_admin_email, monkeypatch
    ):
        fake = _make_fake_supabase(
            invitations=[{
                "token": "tok-1", "org_id": "org-1", "email": "x@y.com",
                "role": "member", "expires_at": _iso(5), "accepted_at": None,
            }],
            delete_rows=[{"token": "tok-1"}],
        )
        monkeypatch.setattr(
            "app.api.invitations.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, "u-super", super_admin_email)
        resp = client.delete(
            "/api/admin/invitations/tok-1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["revoked"] is True

    def test_invitation_not_found_404(
        self, client, jwt_secret, whitelist_env, super_admin_email, monkeypatch
    ):
        fake = _make_fake_supabase(invitations=[])
        monkeypatch.setattr(
            "app.api.invitations.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, "u-super", super_admin_email)
        resp = client.delete(
            "/api/admin/invitations/ghost-token",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


# ─── Tests : GET /api/invitations/<token>/accept (public) ───────────────────


class TestAcceptMetadataEndpoint:
    def test_no_auth_required_returns_meta(self, client, monkeypatch):
        rows = [{
            "token": "tok-1",
            "org_id": "org-1",
            "email": "x@y.com",
            "role": "member",
            "expires_at": _iso(5),
            "accepted_at": None,
        }]
        fake = _make_fake_supabase(
            invitations=rows,
            org_meta={"id": "org-1", "name": "ACME", "slug": "acme", "country_code": "MA"},
        )
        monkeypatch.setattr(
            "app.api.invitations.get_supabase_admin",
            lambda: fake,
        )
        # Pas d'Authorization header
        resp = client.get("/api/invitations/tok-1/accept")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["email"] == "x@y.com"
        assert body["data"]["org_name"] == "ACME"
        assert body["data"]["role"] == "member"

    def test_expired_410(self, client, monkeypatch):
        rows = [{
            "token": "tok-1",
            "org_id": "org-1",
            "email": "x@y.com",
            "role": "member",
            "expires_at": _iso(-1),
            "accepted_at": None,
        }]
        fake = _make_fake_supabase(invitations=rows, org_meta={"id": "org-1"})
        monkeypatch.setattr(
            "app.api.invitations.get_supabase_admin",
            lambda: fake,
        )
        resp = client.get("/api/invitations/tok-1/accept")
        assert resp.status_code == 410
        assert resp.get_json()["error_code"] == "INVITATION_EXPIRED"

    def test_already_consumed_410(self, client, monkeypatch):
        rows = [{
            "token": "tok-1",
            "org_id": "org-1",
            "email": "x@y.com",
            "role": "member",
            "expires_at": _iso(5),
            "accepted_at": _iso(-1),
        }]
        fake = _make_fake_supabase(invitations=rows, org_meta={"id": "org-1"})
        monkeypatch.setattr(
            "app.api.invitations.get_supabase_admin",
            lambda: fake,
        )
        resp = client.get("/api/invitations/tok-1/accept")
        assert resp.status_code == 410
        assert resp.get_json()["error_code"] == "INVITATION_ALREADY_CONSUMED"

    def test_not_found_404(self, client, monkeypatch):
        fake = _make_fake_supabase(invitations=[])
        monkeypatch.setattr(
            "app.api.invitations.get_supabase_admin",
            lambda: fake,
        )
        resp = client.get("/api/invitations/ghost/accept")
        assert resp.status_code == 404


# ─── Tests : POST /api/invitations/<token>/redeem ───────────────────────────


class TestRedeemEndpoint:
    def test_unauth_401(self, client):
        resp = client.post("/api/invitations/tok-1/redeem")
        assert resp.status_code == 401

    def test_email_mismatch_403(self, client, jwt_secret, whitelist_env, monkeypatch):
        rows = [{
            "token": "tok-1",
            "org_id": "org-1",
            "email": "intended@example.com",
            "role": "member",
            "expires_at": _iso(5),
            "accepted_at": None,
        }]
        fake = _make_fake_supabase(invitations=rows)
        monkeypatch.setattr(
            "app.api.invitations.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, "u-attacker", "attacker@evil.com")
        resp = client.post(
            "/api/invitations/tok-1/redeem",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "EMAIL_MISMATCH"

    def test_redeem_success(self, client, jwt_secret, whitelist_env, monkeypatch):
        rows = [{
            "token": "tok-1",
            "org_id": "org-1",
            "email": "user@example.com",
            "role": "admin",
            "expires_at": _iso(5),
            "accepted_at": None,
        }]
        fake = _make_fake_supabase(invitations=rows)
        monkeypatch.setattr(
            "app.api.invitations.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, "u-new", "user@example.com")
        resp = client.post(
            "/api/invitations/tok-1/redeem",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        body = resp.get_json()
        assert body["data"]["org_id"] == "org-1"
        assert body["data"]["role"] == "admin"

    def test_redeem_expired_410(self, client, jwt_secret, whitelist_env, monkeypatch):
        rows = [{
            "token": "tok-1",
            "org_id": "org-1",
            "email": "user@example.com",
            "role": "member",
            "expires_at": _iso(-1),
            "accepted_at": None,
        }]
        fake = _make_fake_supabase(invitations=rows)
        monkeypatch.setattr(
            "app.api.invitations.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, "u-1", "user@example.com")
        resp = client.post(
            "/api/invitations/tok-1/redeem",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 410
        assert resp.get_json()["error_code"] == "INVITATION_EXPIRED"

    def test_redeem_already_consumed_409(
        self, client, jwt_secret, whitelist_env, monkeypatch
    ):
        rows = [{
            "token": "tok-1",
            "org_id": "org-1",
            "email": "user@example.com",
            "role": "member",
            "expires_at": _iso(5),
            "accepted_at": _iso(-1),
        }]
        fake = _make_fake_supabase(invitations=rows)
        monkeypatch.setattr(
            "app.api.invitations.get_supabase_admin",
            lambda: fake,
        )
        token = _make_token(jwt_secret, "u-1", "user@example.com")
        resp = client.post(
            "/api/invitations/tok-1/redeem",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409
        assert resp.get_json()["error_code"] == "INVITATION_ALREADY_CONSUMED"


# ─── Test smoke template render ─────────────────────────────────────────────


class TestEmailTemplate:
    def test_org_invitation_template_renders(self):
        from app.services import email_service
        html = email_service.render_template(
            "org_invitation",
            {
                "org_name": "ACME",
                "org_slug": "acme",
                "role": "member",
                "invite_url": "https://prospectives.ai-mpower.com/signup?invite=abc",
                "expires_at": "2026-05-12T12:00:00+00:00",
                "email": "user@example.com",
            },
        )
        assert "ACME" in html
        assert "user@example.com" in html
        assert "signup?invite=abc" in html
        assert "2026-05-12" in html
