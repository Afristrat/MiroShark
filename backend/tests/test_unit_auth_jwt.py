"""Tests unitaires US-092 — vérification JWT Supabase + décorateurs.

Aucune dépendance live à Supabase : tous les helpers Supabase sont
monkeypatchés pour retourner des fixtures statiques. Les JWT sont signés
en HS256 avec un secret fourni via `monkeypatch.setenv("SUPABASE_JWT_SECRET", ...)`.
"""

from __future__ import annotations

import time
from typing import Any, Dict
from unittest.mock import MagicMock

import jwt as pyjwt
import pytest
from flask import Flask, g, jsonify

from app.auth import jwt_verifier
from app.auth.jwt_verifier import InvalidTokenError, verify_supabase_jwt
from app.auth.decorators import (
    require_auth,
    require_org_membership,
    require_owner_or_admin,
)
from app.auth import supabase_client as sup_mod


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_jwt_cache():
    """Vide le cache LRU entre chaque test pour garantir l'isolation."""
    jwt_verifier._cache_clear()
    yield
    jwt_verifier._cache_clear()


@pytest.fixture
def jwt_secret(monkeypatch):
    """Pose un secret HS256 connu et le retourne."""
    secret = "test-secret-please-do-not-use-in-prod"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    return secret


def _make_token(secret: str, **overrides: Any) -> str:
    """Forge un JWT HS256 valide pour les tests."""
    now = int(time.time())
    claims: Dict[str, Any] = {
        "sub": "11111111-2222-3333-4444-555555555555",
        "email": "amine@aimpower.org",
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    return pyjwt.encode(claims, secret, algorithm="HS256")


@pytest.fixture
def app() -> Flask:
    """Mini app Flask pour exercer les décorateurs en isolation."""
    a = Flask(__name__)
    a.config["TESTING"] = True

    @a.route("/protected")
    @require_auth
    def protected():
        return jsonify({"ok": True, "user": g.current_user["id"]}), 200

    @a.route("/org-member")
    @require_org_membership(role_min="member")
    def org_member():
        return jsonify({
            "ok": True,
            "org_id": g.current_org["id"],
            "role": g.current_org["role"],
        }), 200

    @a.route("/org-admin")
    @require_owner_or_admin
    def org_admin():
        return jsonify({"ok": True, "role": g.current_org["role"]}), 200

    return a


# ─── verify_supabase_jwt ────────────────────────────────────────────────────

class TestVerifyJwt:
    def test_valid_token_returns_claims(self, jwt_secret):
        token = _make_token(jwt_secret)
        claims = verify_supabase_jwt(token)
        assert claims["sub"] == "11111111-2222-3333-4444-555555555555"
        assert claims["email"] == "amine@aimpower.org"

    def test_empty_token_raises(self, jwt_secret):
        with pytest.raises(InvalidTokenError):
            verify_supabase_jwt("")
        with pytest.raises(InvalidTokenError):
            verify_supabase_jwt("   ")

    def test_expired_token_raises(self, jwt_secret):
        token = _make_token(jwt_secret, exp=int(time.time()) - 60)
        with pytest.raises(InvalidTokenError):
            verify_supabase_jwt(token)

    def test_wrong_signature_raises(self, jwt_secret):
        token = _make_token("another-secret-different")
        with pytest.raises(InvalidTokenError):
            verify_supabase_jwt(token)

    def test_malformed_token_raises(self, jwt_secret):
        with pytest.raises(InvalidTokenError):
            verify_supabase_jwt("not.a.jwt")

    def test_missing_sub_raises(self, jwt_secret):
        # On signe un token sans `sub` (PyJWT acceptera la signature mais
        # `verify_supabase_jwt` exige le claim).
        now = int(time.time())
        token = pyjwt.encode(
            {"exp": now + 3600},  # `require=["exp", "sub"]` côté décodage → KO
            jwt_secret,
            algorithm="HS256",
        )
        with pytest.raises(InvalidTokenError):
            verify_supabase_jwt(token)

    def test_secret_missing_raises(self, monkeypatch):
        monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
        # On forge un token avec un secret quelconque ; peu importe
        # puisque le secret backend est manquant.
        token = _make_token("whatever")
        with pytest.raises(InvalidTokenError) as exc:
            verify_supabase_jwt(token)
        assert "SUPABASE_JWT_SECRET" in str(exc.value)

    def test_cache_hit_avoids_redecoding(self, jwt_secret, monkeypatch):
        token = _make_token(jwt_secret)
        verify_supabase_jwt(token)  # primer le cache

        # Second appel : on patch jwt.decode pour vérifier qu'il n'est pas
        # rappelé tant que l'entrée cache est encore valide.
        sentinel = MagicMock(side_effect=AssertionError("should not be called"))
        monkeypatch.setattr(jwt_verifier.jwt, "decode", sentinel)
        claims2 = verify_supabase_jwt(token)
        assert claims2["sub"] == "11111111-2222-3333-4444-555555555555"
        sentinel.assert_not_called()

    def test_cache_purges_expired(self, jwt_secret):
        # Force une entrée expirée dans le cache et on s'assure qu'elle
        # est purgée et qu'une re-validation est tentée.
        token = _make_token(jwt_secret)
        jwt_verifier._cache[token] = (time.time() - 1, {"sub": "stale"})
        claims = verify_supabase_jwt(token)
        # La nouvelle validation a ramené les vrais claims, pas le stub.
        assert claims["sub"] == "11111111-2222-3333-4444-555555555555"


# ─── @require_auth ──────────────────────────────────────────────────────────

class TestRequireAuth:
    def test_no_token_returns_401(self, app):
        client = app.test_client()
        resp = client.get("/protected")
        assert resp.status_code == 401
        assert resp.get_json()["error_code"] == "MISSING_AUTH"

    def test_malformed_header_returns_401(self, app, jwt_secret):
        client = app.test_client()
        resp = client.get("/protected", headers={"Authorization": "Token foo"})
        assert resp.status_code == 401
        assert resp.get_json()["error_code"] == "MISSING_AUTH"

    def test_invalid_token_returns_401(self, app, jwt_secret):
        client = app.test_client()
        resp = client.get(
            "/protected",
            headers={"Authorization": "Bearer not.a.real.token"},
        )
        assert resp.status_code == 401
        assert resp.get_json()["error_code"] == "INVALID_TOKEN"

    def test_valid_token_passes(self, app, jwt_secret):
        token = _make_token(jwt_secret)
        client = app.test_client()
        resp = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["ok"] is True
        assert body["user"] == "11111111-2222-3333-4444-555555555555"

    def test_cookie_fallback_works(self, app, jwt_secret):
        token = _make_token(jwt_secret)
        client = app.test_client()
        client.set_cookie("sb-access-token", token)
        resp = client.get("/protected")
        assert resp.status_code == 200

    def test_secret_unset_returns_503(self, app, monkeypatch):
        monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
        # On forge un token quelconque ; le décorateur retournera 503
        # parce que le secret backend est manquant.
        token = _make_token("anything")
        client = app.test_client()
        resp = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 503
        assert resp.get_json()["error_code"] == "AUTH_NOT_CONFIGURED"


# ─── @require_org_membership ────────────────────────────────────────────────

class TestRequireOrgMembership:
    def test_invalid_role_min_raises(self):
        with pytest.raises(ValueError):
            require_org_membership(role_min="superuser")

    def test_no_orgs_returns_403(self, app, jwt_secret, monkeypatch):
        token = _make_token(jwt_secret)
        monkeypatch.setattr(
            "app.auth.decorators.get_user_orgs",
            lambda user_id: [],
        )
        client = app.test_client()
        resp = client.get(
            "/org-member",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "NOT_A_MEMBER"

    def test_single_org_auto_selected(self, app, jwt_secret, monkeypatch):
        token = _make_token(jwt_secret)
        monkeypatch.setattr(
            "app.auth.decorators.get_user_orgs",
            lambda user_id: [{
                "id": "org-uuid-1",
                "slug": "aimpower-bassira",
                "name": "Aimpower Bassira",
                "sector": "tech",
                "country_code": "MA",
                "status": "active",
                "role": "owner",
            }],
        )
        client = app.test_client()
        resp = client.get(
            "/org-member",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["org_id"] == "org-uuid-1"
        assert body["role"] == "owner"

    def test_multi_org_without_hint_returns_400(
        self, app, jwt_secret, monkeypatch
    ):
        token = _make_token(jwt_secret)
        monkeypatch.setattr(
            "app.auth.decorators.get_user_orgs",
            lambda user_id: [
                {"id": "a", "role": "member", "slug": "a", "name": "A"},
                {"id": "b", "role": "admin", "slug": "b", "name": "B"},
            ],
        )
        client = app.test_client()
        resp = client.get(
            "/org-member",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "ORG_ID_REQUIRED"

    def test_x_org_id_header_resolves(self, app, jwt_secret, monkeypatch):
        token = _make_token(jwt_secret)
        monkeypatch.setattr(
            "app.auth.decorators.get_user_orgs",
            lambda user_id: [
                {"id": "a", "role": "member", "slug": "a", "name": "A"},
                {"id": "b", "role": "admin", "slug": "b", "name": "B"},
            ],
        )
        client = app.test_client()
        resp = client.get(
            "/org-member",
            headers={"Authorization": f"Bearer {token}", "X-Org-Id": "b"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["org_id"] == "b"

    def test_query_param_org_id_resolves(self, app, jwt_secret, monkeypatch):
        token = _make_token(jwt_secret)
        monkeypatch.setattr(
            "app.auth.decorators.get_user_orgs",
            lambda user_id: [
                {"id": "a", "role": "member", "slug": "a", "name": "A"},
                {"id": "b", "role": "admin", "slug": "b", "name": "B"},
            ],
        )
        client = app.test_client()
        resp = client.get(
            "/org-member?org_id=a",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["org_id"] == "a"

    def test_unknown_org_id_returns_404(self, app, jwt_secret, monkeypatch):
        token = _make_token(jwt_secret)
        monkeypatch.setattr(
            "app.auth.decorators.get_user_orgs",
            lambda user_id: [{"id": "a", "role": "owner", "slug": "a", "name": "A"}],
        )
        client = app.test_client()
        resp = client.get(
            "/org-member",
            headers={"Authorization": f"Bearer {token}", "X-Org-Id": "zzz"},
        )
        assert resp.status_code == 404
        assert resp.get_json()["error_code"] == "ORG_NOT_FOUND_FOR_USER"

    def test_role_too_low_returns_403(self, app, jwt_secret, monkeypatch):
        token = _make_token(jwt_secret)
        monkeypatch.setattr(
            "app.auth.decorators.get_user_orgs",
            lambda user_id: [{
                "id": "a", "role": "viewer",
                "slug": "a", "name": "A",
            }],
        )
        client = app.test_client()
        resp = client.get(
            "/org-member",  # exige `member` minimum
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "ROLE_TOO_LOW"

    def test_supabase_not_configured_returns_503(
        self, app, jwt_secret, monkeypatch
    ):
        from app.auth.supabase_client import SupabaseConfigError

        token = _make_token(jwt_secret)

        def _raise(_user_id):
            raise SupabaseConfigError("missing")

        monkeypatch.setattr("app.auth.decorators.get_user_orgs", _raise)
        client = app.test_client()
        resp = client.get(
            "/org-member",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 503
        assert resp.get_json()["error_code"] == "SUPABASE_NOT_CONFIGURED"


# ─── @require_owner_or_admin ────────────────────────────────────────────────

class TestRequireOwnerOrAdmin:
    def test_member_role_rejected(self, app, jwt_secret, monkeypatch):
        token = _make_token(jwt_secret)
        monkeypatch.setattr(
            "app.auth.decorators.get_user_orgs",
            lambda user_id: [{
                "id": "a", "role": "member", "slug": "a", "name": "A",
            }],
        )
        client = app.test_client()
        resp = client.get(
            "/org-admin",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "ROLE_TOO_LOW"

    def test_admin_role_passes(self, app, jwt_secret, monkeypatch):
        token = _make_token(jwt_secret)
        monkeypatch.setattr(
            "app.auth.decorators.get_user_orgs",
            lambda user_id: [{
                "id": "a", "role": "admin", "slug": "a", "name": "A",
            }],
        )
        client = app.test_client()
        resp = client.get(
            "/org-admin",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["role"] == "admin"

    def test_owner_role_passes(self, app, jwt_secret, monkeypatch):
        token = _make_token(jwt_secret)
        monkeypatch.setattr(
            "app.auth.decorators.get_user_orgs",
            lambda user_id: [{
                "id": "a", "role": "owner", "slug": "a", "name": "A",
            }],
        )
        client = app.test_client()
        resp = client.get(
            "/org-admin",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["role"] == "owner"


# ─── role_meets_minimum (utilitaire pur) ────────────────────────────────────

class TestRoleHierarchy:
    def test_owner_beats_admin(self):
        assert sup_mod.role_meets_minimum("owner", "admin") is True

    def test_admin_beats_member(self):
        assert sup_mod.role_meets_minimum("admin", "member") is True

    def test_member_below_admin(self):
        assert sup_mod.role_meets_minimum("member", "admin") is False

    def test_viewer_below_member(self):
        assert sup_mod.role_meets_minimum("viewer", "member") is False

    def test_unknown_role_returns_false(self):
        assert sup_mod.role_meets_minimum("superuser", "admin") is False
        assert sup_mod.role_meets_minimum("owner", "robot") is False

    def test_none_returns_false(self):
        assert sup_mod.role_meets_minimum(None, "viewer") is False
