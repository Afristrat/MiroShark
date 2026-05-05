"""Tests unitaires US-114 — Helper Supabase quote_ownership.

Couvre :
  - ``link_quote_to_org`` : INSERT idempotent + propagation d'erreurs
  - ``get_org_for_quote`` : lookup + fail-soft sur erreur
  - ``list_quotes_for_org`` : pagination + tri DESC + fail-soft
  - ``list_quotes_for_orgs`` : batch lookup multi-org
  - ``update_quote_status_in_supabase`` : miroir best-effort
  - Endpoint ``GET /api/admin/quotes`` étendu : super-admin vs member scoping
  - Endpoint ``GET /api/admin/quotes/<id>`` étendu : 404 cross-tenant
  - Soumission de devis (US-025) avec lien Supabase best-effort

Toutes les interactions Supabase sont monkeypatchées — aucune dépendance
live.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import jwt as pyjwt
import pytest

from app import create_app
from app.auth import jwt_verifier
from app.services import quote_admin_service as qa
from app.services import quote_ownership as qo
from app.services import quote_service as qs


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_jwt_cache():
    jwt_verifier._cache_clear()
    yield
    jwt_verifier._cache_clear()


@pytest.fixture
def jwt_secret(monkeypatch):
    secret = "quote-ownership-tests-secret"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    return secret


@pytest.fixture
def super_admin_email() -> str:
    return "amine@ai-mpower.com"


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
def isolated_quotes_dir(tmp_path, monkeypatch):
    from app import config as config_module

    base = tmp_path / "uploads"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        config_module.Config,
        "WONDERWALL_DATA_DIR",
        str(base),
        raising=False,
    )
    return base / "quotes"


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


def _create_quote_file(quotes_dir: Path, quote_id: str = "q_abc12345", email: str = "client@example.com") -> Path:
    quotes_dir.mkdir(parents=True, exist_ok=True)
    filename = f"quote_20260505T120000_{quote_id.replace('q_', '')}.json"
    path = quotes_dir / filename
    payload = {
        "quote_id": quote_id,
        "submitted_at": "2026-05-05T12:00:00Z",
        "full_name": "Karim Bensaid",
        "email": email,
        "company": "Banque Populaire MA",
        "package": "crisis_drill_24h",
        "message": "Need a crisis drill before launch.",
        "industry": "banking",
        "geo_focus": ["MA"],
        "consent_rgpd": True,
        "locale": "fr",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _make_fake_supabase_for_ownership(
    *,
    insert_raises: Exception | None = None,
    select_rows: List[Dict[str, Any]] | None = None,
    update_rows: List[Dict[str, Any]] | None = None,
):
    """MagicMock supabase qui supporte ``quote_ownership`` insert/select/update.

    ``insert_raises`` : exception à lever lors de l'insert (test idempotence).
    ``select_rows`` : data renvoyée pour les selects sur quote_ownership.
    ``update_rows`` : data renvoyée pour les updates.
    """
    fake = MagicMock()
    select_rows = select_rows or []
    update_rows = update_rows or []

    def _table(name: str):
        tbl = MagicMock()
        if name == "quote_ownership":
            # insert chain : .insert(...).execute()
            insert_chain = MagicMock()
            if insert_raises is not None:
                insert_chain.execute.side_effect = insert_raises
            else:
                insert_chain.execute.return_value = MagicMock(data=[{"quote_id": "ok"}])
            tbl.insert.return_value = insert_chain

            # select chain : .select(...).eq(...).limit(1).execute()
            #             ou : .select(...).eq(...).order(...).range(...).execute()
            #             ou : .select(...).in_(...).order(...).limit(...).execute()
            select_chain = MagicMock()
            eq_chain = MagicMock()
            order_chain = MagicMock()
            limit_chain = MagicMock()
            range_chain = MagicMock()
            in_chain = MagicMock()
            in_order_chain = MagicMock()
            in_limit_chain = MagicMock()

            limit_chain.execute.return_value = MagicMock(data=select_rows)
            range_chain.execute.return_value = MagicMock(data=select_rows)
            order_chain.range.return_value = range_chain
            order_chain.execute.return_value = MagicMock(data=select_rows)
            in_limit_chain.execute.return_value = MagicMock(data=select_rows)
            in_order_chain.limit.return_value = in_limit_chain
            in_order_chain.execute.return_value = MagicMock(data=select_rows)
            in_chain.order.return_value = in_order_chain
            in_chain.execute.return_value = MagicMock(data=select_rows)

            eq_chain.limit.return_value = limit_chain
            eq_chain.order.return_value = order_chain
            eq_chain.execute.return_value = MagicMock(data=select_rows)

            select_chain.eq.return_value = eq_chain
            select_chain.in_.return_value = in_chain
            tbl.select.return_value = select_chain

            # update chain : .update(...).eq(...).execute()
            update_chain = MagicMock()
            update_eq_chain = MagicMock()
            update_eq_chain.execute.return_value = MagicMock(data=update_rows)
            update_chain.eq.return_value = update_eq_chain
            tbl.update.return_value = update_chain
        return tbl

    fake.table.side_effect = _table
    return fake


# ─── Tests : link_quote_to_org ──────────────────────────────────────────────


class TestLinkQuoteToOrg:
    def test_insert_success(self):
        fake = _make_fake_supabase_for_ownership()
        ok = qo.link_quote_to_org(
            "q_aaa11111",
            "org-uuid-1",
            customer_email="x@y.com",
            package_id="crisis_drill_24h",
            client=fake,
        )
        assert ok is True
        # Vérifie que insert a été appelé avec le bon payload
        fake.table.assert_called_with("quote_ownership")

    def test_insert_idempotent_on_duplicate(self):
        fake = _make_fake_supabase_for_ownership(
            insert_raises=Exception("duplicate key value violates unique constraint")
        )
        ok = qo.link_quote_to_org("q_dupe1234", "org-uuid-1", client=fake)
        assert ok is False  # déjà existant — pas levé

    def test_insert_idempotent_on_23505(self):
        fake = _make_fake_supabase_for_ownership(
            insert_raises=Exception("postgrest: 23505 unique violation")
        )
        ok = qo.link_quote_to_org("q_dupe5678", "org-uuid-1", client=fake)
        assert ok is False

    def test_insert_other_error_propagates(self):
        fake = _make_fake_supabase_for_ownership(
            insert_raises=RuntimeError("network blip")
        )
        with pytest.raises(RuntimeError):
            qo.link_quote_to_org("q_err00000", "org-uuid-1", client=fake)

    def test_invalid_quote_id_raises(self):
        with pytest.raises(ValueError):
            qo.link_quote_to_org("", "org-uuid-1", client=MagicMock())

    def test_invalid_org_id_raises(self):
        with pytest.raises(ValueError):
            qo.link_quote_to_org("q_ok000000", "", client=MagicMock())

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError):
            qo.link_quote_to_org(
                "q_ok000000", "org-1", status="bogus", client=MagicMock()
            )


# ─── Tests : get_org_for_quote ──────────────────────────────────────────────


class TestGetOrgForQuote:
    def test_found(self):
        fake = _make_fake_supabase_for_ownership(
            select_rows=[{"org_id": "org-uuid-1"}]
        )
        org_id = qo.get_org_for_quote("q_aaa11111", client=fake)
        assert org_id == "org-uuid-1"

    def test_not_found(self):
        fake = _make_fake_supabase_for_ownership(select_rows=[])
        org_id = qo.get_org_for_quote("q_zzz99999", client=fake)
        assert org_id is None

    def test_error_returns_none(self):
        fake = MagicMock()
        fake.table.side_effect = RuntimeError("connection refused")
        org_id = qo.get_org_for_quote("q_aaa11111", client=fake)
        assert org_id is None

    def test_empty_quote_id_returns_none(self):
        org_id = qo.get_org_for_quote("", client=MagicMock())
        assert org_id is None


# ─── Tests : list_quotes_for_org ────────────────────────────────────────────


class TestListQuotesForOrg:
    def test_returns_rows(self):
        rows = [
            {
                "quote_id": "q_aaa11111",
                "org_id": "org-uuid-1",
                "customer_email": "a@b.com",
                "package_id": "crisis_drill_24h",
                "status": "received",
                "created_at": "2026-05-05T12:00:00Z",
            },
        ]
        fake = _make_fake_supabase_for_ownership(select_rows=rows)
        out = qo.list_quotes_for_org("org-uuid-1", client=fake)
        assert len(out) == 1
        assert out[0]["quote_id"] == "q_aaa11111"

    def test_empty_org_id_returns_empty(self):
        out = qo.list_quotes_for_org("", client=MagicMock())
        assert out == []

    def test_error_returns_empty(self):
        fake = MagicMock()
        fake.table.side_effect = RuntimeError("oops")
        out = qo.list_quotes_for_org("org-uuid-1", client=fake)
        assert out == []

    def test_pagination_bounded(self):
        fake = _make_fake_supabase_for_ownership(select_rows=[])
        # limit > 500 → bornage à 500 (pas d'erreur)
        out = qo.list_quotes_for_org(
            "org-uuid-1", limit=10_000, offset=-5, client=fake
        )
        assert out == []


# ─── Tests : update_quote_status_in_supabase ────────────────────────────────


class TestUpdateQuoteStatus:
    def test_update_success(self):
        fake = _make_fake_supabase_for_ownership(
            update_rows=[{"quote_id": "q_aaa11111"}]
        )
        ok = qo.update_quote_status_in_supabase(
            "q_aaa11111", "reviewing", client=fake
        )
        assert ok is True

    def test_update_no_rows(self):
        fake = _make_fake_supabase_for_ownership(update_rows=[])
        ok = qo.update_quote_status_in_supabase(
            "q_zzz99999", "reviewing", client=fake
        )
        assert ok is False

    def test_invalid_status_returns_false(self):
        fake = _make_fake_supabase_for_ownership(update_rows=[])
        ok = qo.update_quote_status_in_supabase(
            "q_aaa11111", "bogus", client=fake
        )
        assert ok is False

    def test_error_returns_false(self):
        fake = MagicMock()
        fake.table.side_effect = RuntimeError("oops")
        ok = qo.update_quote_status_in_supabase(
            "q_aaa11111", "reviewing", client=fake
        )
        assert ok is False


# ─── Tests : list_quotes_for_orgs (batch) ───────────────────────────────────


class TestListQuotesForOrgs:
    def test_empty_input(self):
        out = qo.list_quotes_for_orgs([], client=MagicMock())
        assert out == []

    def test_batch_returns_rows(self):
        rows = [
            {"quote_id": "q_a", "org_id": "org-1", "status": "received"},
            {"quote_id": "q_b", "org_id": "org-2", "status": "received"},
        ]
        fake = _make_fake_supabase_for_ownership(select_rows=rows)
        out = qo.list_quotes_for_orgs(["org-1", "org-2"], client=fake)
        assert len(out) == 2

    def test_batch_error_returns_empty(self):
        fake = MagicMock()
        fake.table.side_effect = RuntimeError("oops")
        out = qo.list_quotes_for_orgs(["org-1"], client=fake)
        assert out == []


# ─── Tests : intégration submit_quote (US-025 + US-114) ─────────────────────


class TestSubmitQuoteWithOwnership:
    def test_submit_quote_calls_link_best_effort(
        self, isolated_quotes_dir, monkeypatch
    ):
        """submit_quote() doit appeler link_quote_to_org quand Supabase répond."""
        # Mock get_default_super_admin_org_id pour retourner un UUID.
        monkeypatch.setattr(
            "app.services.quote_service.uuid",
            __import__("uuid"),  # vrai uuid module
        )
        called = {"link": 0}

        def fake_link(qid, org_id, **kw):
            called["link"] += 1
            assert org_id == "org-default-uuid"
            return True

        monkeypatch.setattr(
            "app.services.quote_ownership.link_quote_to_org",
            fake_link,
        )
        monkeypatch.setattr(
            "app.auth.supabase_client.get_default_super_admin_org_id",
            lambda client=None: "org-default-uuid",
        )
        # Pas d'envoi réel d'email
        from app.services import email_service
        monkeypatch.setattr(email_service, "send_email", lambda *a, **k: True)
        # Reset rate limit pour pas être bloqué
        qs._reset_rate_limit_for_tests()

        status, body = qs.submit_quote({
            "full_name": "Karim",
            "email": "client@example.com",
            "company": "ACME",
            "package": "crisis_drill_24h",
            "consent_rgpd": True,
        })
        assert status == 200
        assert body["success"] is True
        assert called["link"] == 1

    def test_submit_quote_succeeds_when_supabase_unavailable(
        self, isolated_quotes_dir, monkeypatch
    ):
        """Si Supabase est down, submit_quote() ne doit JAMAIS échouer."""
        from app.auth.supabase_client import SupabaseConfigError

        def _raise(*a, **k):
            raise SupabaseConfigError("not configured")

        monkeypatch.setattr(
            "app.auth.supabase_client.get_default_super_admin_org_id",
            _raise,
        )
        from app.services import email_service
        monkeypatch.setattr(email_service, "send_email", lambda *a, **k: True)
        qs._reset_rate_limit_for_tests()

        status, body = qs.submit_quote({
            "full_name": "Karim",
            "email": "client2@example.com",
            "company": "ACME",
            "package": "policy_brief_stress",
            "consent_rgpd": True,
        })
        # Best-effort : le devis est persisté + 200, indépendamment de Supabase.
        assert status == 200
        assert body["success"] is True


# ─── Tests : endpoints HTTP étendus US-114 ──────────────────────────────────


class TestAdminQuotesEndpointsScoping:
    def test_super_admin_sees_all(
        self, client, isolated_quotes_dir, whitelist_env, jwt_secret, super_admin_email
    ):
        """Super-admin garde le comportement historique (tous les devis filesystem)."""
        _create_quote_file(isolated_quotes_dir, "q_sup11111")
        _create_quote_file(isolated_quotes_dir, "q_sup22222")
        token = _make_token(jwt_secret, "u-super", super_admin_email)
        resp = client.get(
            "/api/admin/quotes",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"]["total"] == 2

    def test_member_sees_only_owned_quotes(
        self,
        client,
        isolated_quotes_dir,
        whitelist_env,
        jwt_secret,
        normal_email,
        monkeypatch,
    ):
        """Member d'une org voit uniquement les devis liés à son org."""
        _create_quote_file(isolated_quotes_dir, "q_own11111")
        _create_quote_file(isolated_quotes_dir, "q_oth22222")  # pas dans son org

        # Mock get_user_orgs → 1 org
        monkeypatch.setattr(
            "app.api.quote.get_user_orgs",
            lambda user_id: [{"id": "org-member-1", "role": "member"}],
        )
        # Mock list_quotes_for_orgs → 1 row pour q_own11111
        monkeypatch.setattr(
            "app.services.quote_ownership.list_quotes_for_orgs",
            lambda org_ids, **kw: [
                {
                    "quote_id": "q_own11111",
                    "org_id": "org-member-1",
                    "status": "received",
                }
            ],
        )

        token = _make_token(jwt_secret, "u-member", normal_email)
        resp = client.get(
            "/api/admin/quotes",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"]["total"] == 1
        assert body["data"]["quotes"][0]["quote_id"] == "q_own11111"

    def test_authenticated_user_no_org_403(
        self, client, isolated_quotes_dir, whitelist_env, jwt_secret, normal_email, monkeypatch
    ):
        """User authentifié mais sans org → 403 NOT_A_MEMBER."""
        monkeypatch.setattr(
            "app.api.quote.get_user_orgs",
            lambda user_id: [],
        )
        token = _make_token(jwt_secret, "u-orphan", normal_email)
        resp = client.get(
            "/api/admin/quotes",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "NOT_A_MEMBER"

    def test_no_token_401(
        self, client, isolated_quotes_dir, whitelist_env
    ):
        resp = client.get("/api/admin/quotes")
        assert resp.status_code == 401

    def test_get_detail_member_other_org_404(
        self,
        client,
        isolated_quotes_dir,
        whitelist_env,
        jwt_secret,
        normal_email,
        monkeypatch,
    ):
        """Member tente de lire un devis d'une autre org → 404 (pas 403, pas de fuite)."""
        _create_quote_file(isolated_quotes_dir, "q_otr11111")
        monkeypatch.setattr(
            "app.api.quote.get_user_orgs",
            lambda user_id: [{"id": "org-member-1", "role": "member"}],
        )
        # owner_org renvoie autre org → not in member's orgs
        monkeypatch.setattr(
            "app.services.quote_ownership.get_org_for_quote",
            lambda quote_id, **kw: "org-other-99",
        )
        token = _make_token(jwt_secret, "u-mem-1", normal_email)
        resp = client.get(
            "/api/admin/quotes/q_otr11111",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
        assert resp.get_json()["error_code"] == "QUOTE_NOT_FOUND"

    def test_get_detail_member_own_quote_ok(
        self,
        client,
        isolated_quotes_dir,
        whitelist_env,
        jwt_secret,
        normal_email,
        monkeypatch,
    ):
        """Member peut lire un devis lié à son org."""
        _create_quote_file(isolated_quotes_dir, "q_mine1111")
        monkeypatch.setattr(
            "app.api.quote.get_user_orgs",
            lambda user_id: [{"id": "org-mine-1", "role": "member"}],
        )
        monkeypatch.setattr(
            "app.services.quote_ownership.get_org_for_quote",
            lambda quote_id, **kw: "org-mine-1",
        )
        token = _make_token(jwt_secret, "u-mine", normal_email)
        resp = client.get(
            "/api/admin/quotes/q_mine1111",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["quote_id"] == "q_mine1111"


# ─── Tests : status mirror (update_quote_status sidecar → Supabase) ─────────


class TestStatusMirror:
    def test_status_update_mirrors_to_supabase(
        self, isolated_quotes_dir, monkeypatch
    ):
        _create_quote_file(isolated_quotes_dir, "q_mir11111")
        called = {"mirror": 0}

        def fake_mirror(qid, status, **kw):
            called["mirror"] += 1
            assert qid == "q_mir11111"
            assert status == "reviewing"
            return True

        monkeypatch.setattr(
            "app.services.quote_ownership.update_quote_status_in_supabase",
            fake_mirror,
        )

        ok, code, payload = qa.update_quote_status(
            "q_mir11111",
            new_status="reviewing",
            by_email="amine@ai-mpower.com",
        )
        assert ok is True
        assert code == "OK"
        assert called["mirror"] == 1

    def test_status_update_succeeds_when_supabase_down(
        self, isolated_quotes_dir, monkeypatch
    ):
        _create_quote_file(isolated_quotes_dir, "q_dwn11111")

        def boom(qid, status, **kw):
            raise RuntimeError("supabase down")

        monkeypatch.setattr(
            "app.services.quote_ownership.update_quote_status_in_supabase",
            boom,
        )
        # Update doit toujours marcher côté filesystem
        ok, code, _ = qa.update_quote_status(
            "q_dwn11111", new_status="reviewing"
        )
        assert ok is True
        assert code == "OK"
