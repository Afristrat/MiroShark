"""Unit tests US-102 / US-103 / US-104 — Console super-admin /api/admin/quotes.

Couvre :
  - Service ``quote_admin_service`` : list / read / status sidecar / transitions
  - Endpoints ``/api/admin/quotes`` (list, detail, PATCH status, PATCH notes,
    POST send-payment-link, POST send-delivered)
  - Email service helpers (template rendering, Resend mock, fallback no-op)

Toutes les interactions Resend / SMTP sont monkeypatchées — aucun envoi réel.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import jwt as pyjwt
import pytest

from app import create_app
from app.auth import jwt_verifier
from app.services import email_service, quote_admin_service as qa


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_jwt_cache():
    jwt_verifier._cache_clear()
    yield
    jwt_verifier._cache_clear()


@pytest.fixture
def jwt_secret(monkeypatch):
    secret = "quote-admin-tests-secret"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    return secret


@pytest.fixture
def super_admin_email() -> str:
    return "amine@ai-mpower.com"


@pytest.fixture
def whitelist_env(monkeypatch, super_admin_email):
    monkeypatch.setenv("BASSIRA_SUPER_ADMIN_EMAILS", super_admin_email)
    yield


def _make_token(secret: str, email: str) -> str:
    now = int(time.time())
    return pyjwt.encode(
        {
            "sub": "user-uuid-1234",
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
    """Pointe les services quote vers un répertoire jetable."""
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
    """App Flask sans Neo4j live."""
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


def _create_quote(quotes_dir: Path, quote_id: str = "q_abc12345", email: str = "client@example.com") -> Path:
    """Crée un fichier quote minimaliste sur disque, retourne son path."""
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


# ─── Tests : transitions service-level ──────────────────────────────────────


class TestStatusTransitions:
    def test_received_to_reviewing_allowed(self):
        assert qa.is_valid_transition("received", "reviewing") is True

    def test_received_to_quoted_forbidden(self):
        assert qa.is_valid_transition("received", "quoted") is False

    def test_reviewing_to_quoted_allowed(self):
        assert qa.is_valid_transition("reviewing", "quoted") is True

    def test_quoted_to_paid_allowed(self):
        assert qa.is_valid_transition("quoted", "paid") is True

    def test_quoted_to_declined_allowed(self):
        assert qa.is_valid_transition("quoted", "declined") is True

    def test_paid_to_in_progress_allowed(self):
        assert qa.is_valid_transition("paid", "in_progress") is True

    def test_in_progress_to_delivered_allowed(self):
        assert qa.is_valid_transition("in_progress", "delivered") is True

    def test_delivered_terminal(self):
        # delivered ne doit pas pouvoir transitionner vers autre chose
        for tgt in ["received", "reviewing", "quoted", "paid", "in_progress", "declined"]:
            assert qa.is_valid_transition("delivered", tgt) is False

    def test_declined_terminal(self):
        for tgt in ["received", "reviewing", "quoted", "paid", "in_progress", "delivered"]:
            assert qa.is_valid_transition("declined", tgt) is False

    def test_invalid_status_returns_false(self):
        assert qa.is_valid_transition("received", "totally_made_up") is False

    def test_idempotent_same_status(self):
        # Redéclarer le même statut est toléré (pour mises à jour de méta).
        for s in qa.VALID_STATUSES:
            assert qa.is_valid_transition(s, s) is True


# ─── Tests : list_quotes / read_quote_status ────────────────────────────────


class TestQuoteAdminService:
    def test_list_empty(self, isolated_quotes_dir):
        items, total = qa.list_quotes()
        assert items == []
        assert total == 0

    def test_list_one_quote_default_status(self, isolated_quotes_dir):
        _create_quote(isolated_quotes_dir, "q_aaa11111")
        items, total = qa.list_quotes()
        assert total == 1
        assert items[0]["quote_id"] == "q_aaa11111"
        assert items[0]["status"]["status"] == "received"
        assert items[0]["status"]["history"] == []

    def test_read_status_default_when_no_sidecar(self, isolated_quotes_dir):
        _create_quote(isolated_quotes_dir, "q_bbb22222")
        st = qa.read_quote_status("q_bbb22222")
        assert st["status"] == "received"
        assert st["payment_link"] is None

    def test_update_status_writes_sidecar(self, isolated_quotes_dir):
        _create_quote(isolated_quotes_dir, "q_ccc33333")
        ok, code, payload = qa.update_quote_status(
            "q_ccc33333",
            new_status="reviewing",
            by_email="amine@ai-mpower.com",
        )
        assert ok is True
        assert code == "OK"
        assert payload["status"] == "reviewing"
        assert len(payload["history"]) == 1
        assert payload["history"][0]["status"] == "reviewing"
        assert payload["history"][0]["by"] == "amine@ai-mpower.com"

        # Re-read should reflect.
        st = qa.read_quote_status("q_ccc33333")
        assert st["status"] == "reviewing"

    def test_update_status_invalid_transition(self, isolated_quotes_dir):
        _create_quote(isolated_quotes_dir, "q_ddd44444")
        ok, code, _ = qa.update_quote_status(
            "q_ddd44444",
            new_status="paid",  # received → paid invalide
        )
        assert ok is False
        assert code == "INVALID_TRANSITION"

    def test_update_status_unknown_quote(self, isolated_quotes_dir):
        ok, code, _ = qa.update_quote_status(
            "q_ghostxxx",
            new_status="reviewing",
        )
        assert ok is False
        assert code == "QUOTE_NOT_FOUND"

    def test_update_status_invalid_status_value(self, isolated_quotes_dir):
        _create_quote(isolated_quotes_dir, "q_eee55555")
        ok, code, _ = qa.update_quote_status(
            "q_eee55555",
            new_status="banana",
        )
        assert ok is False
        assert code == "INVALID_STATUS"

    def test_update_notes_no_status_change(self, isolated_quotes_dir):
        _create_quote(isolated_quotes_dir, "q_fff66666")
        ok, code, payload = qa.update_quote_notes("q_fff66666", notes="Internal memo")
        assert ok is True
        assert code == "OK"
        assert payload["notes"] == "Internal memo"
        assert payload["status"] == "received"  # pas changé

    def test_filter_by_status(self, isolated_quotes_dir):
        _create_quote(isolated_quotes_dir, "q_aaa10001", email="a@x.com")
        _create_quote(isolated_quotes_dir, "q_bbb10002", email="b@x.com")
        # promote q_bbb10002 to reviewing
        qa.update_quote_status("q_bbb10002", new_status="reviewing")
        items_received, _ = qa.list_quotes(status_filter="received")
        items_reviewing, _ = qa.list_quotes(status_filter="reviewing")
        assert len(items_received) == 1
        assert items_received[0]["quote_id"] == "q_aaa10001"
        assert len(items_reviewing) == 1
        assert items_reviewing[0]["quote_id"] == "q_bbb10002"


class TestUpdateQuoteStatusEnsureClientAccount:
    """Lot B (compte client) — déclencheur ensure_client_account, uniquement
    sur la transition VERS "paid" du circuit devis manuel admin. Ne doit
    jamais se déclencher sur les autres transitions, ni se re-déclencher sur
    une redéclaration idempotente de "paid" (current == new)."""

    def test_transition_to_paid_calls_ensure_client_account(self, isolated_quotes_dir, monkeypatch):
        _create_quote(isolated_quotes_dir, "q_paidtest1", email="client@example.com")
        qa.update_quote_status("q_paidtest1", new_status="reviewing")
        qa.update_quote_status("q_paidtest1", new_status="quoted")

        calls = []
        monkeypatch.setattr(
            qa, "ensure_client_account",
            lambda email, full_name, org_name, *, source, locale="fr", client=None: (
                calls.append({
                    "email": email, "full_name": full_name, "org_name": org_name,
                    "source": source, "locale": locale,
                }) or {"org_id": "org-x", "user_id": "user-x", "created": True}
            ),
        )

        ok, code, _ = qa.update_quote_status(
            "q_paidtest1", new_status="paid", by_email="amine@ai-mpower.com",
        )

        assert ok is True
        assert code == "OK"
        assert len(calls) == 1
        assert calls[0]["email"] == "client@example.com"
        assert calls[0]["full_name"] == "Karim Bensaid"
        assert calls[0]["org_name"] == "Banque Populaire MA"
        assert calls[0]["source"] == "quote_paid"
        assert calls[0]["locale"] == "fr"

    def test_transition_not_to_paid_does_not_trigger(self, isolated_quotes_dir, monkeypatch):
        _create_quote(isolated_quotes_dir, "q_notpaid1")
        ensure_mock = MagicMock()
        monkeypatch.setattr(qa, "ensure_client_account", ensure_mock)

        ok, _code, _ = qa.update_quote_status("q_notpaid1", new_status="reviewing")

        assert ok is True
        ensure_mock.assert_not_called()

    def test_idempotent_redeclare_paid_does_not_retrigger(self, isolated_quotes_dir, monkeypatch):
        _create_quote(isolated_quotes_dir, "q_paidtest2")
        qa.update_quote_status("q_paidtest2", new_status="reviewing")
        qa.update_quote_status("q_paidtest2", new_status="quoted")
        qa.update_quote_status("q_paidtest2", new_status="paid")

        ensure_mock = MagicMock()
        monkeypatch.setattr(qa, "ensure_client_account", ensure_mock)

        ok, _code, _ = qa.update_quote_status("q_paidtest2", new_status="paid")

        assert ok is True
        ensure_mock.assert_not_called()

    def test_missing_email_in_payload_skips_without_failing(self, isolated_quotes_dir, monkeypatch):
        _create_quote(isolated_quotes_dir, "q_noemail1")
        # Corrompt le payload pour retirer l'email (cas défensif).
        payload_path = next(isolated_quotes_dir.glob("*noemail1*.json"))
        data = json.loads(payload_path.read_text(encoding="utf-8"))
        data.pop("email", None)
        payload_path.write_text(json.dumps(data), encoding="utf-8")

        qa.update_quote_status("q_noemail1", new_status="reviewing")
        qa.update_quote_status("q_noemail1", new_status="quoted")

        ensure_mock = MagicMock()
        monkeypatch.setattr(qa, "ensure_client_account", ensure_mock)

        ok, code, _ = qa.update_quote_status("q_noemail1", new_status="paid")

        assert ok is True
        assert code == "OK"
        ensure_mock.assert_not_called()


# ─── Tests : endpoints HTTP ─────────────────────────────────────────────────


class TestAdminQuotesEndpoints:
    def test_list_no_auth_401(self, client, isolated_quotes_dir, whitelist_env):
        resp = client.get("/api/admin/quotes")
        assert resp.status_code == 401

    def test_list_normal_user_403(
        self, client, isolated_quotes_dir, whitelist_env, jwt_secret, monkeypatch
    ):
        # US-114 — la sémantique a évolué : un user authentifié non super-admin
        # peut accéder s'il appartient à au moins une org. Sans org → 403.
        monkeypatch.setattr(
            "app.api.quote.get_user_orgs",
            lambda user_id: [],  # user sans org
        )
        token = _make_token(jwt_secret, "user@somecorp.com")
        resp = client.get(
            "/api/admin/quotes",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "NOT_A_MEMBER"

    def test_list_super_admin_returns_quotes(
        self, client, isolated_quotes_dir, whitelist_env, jwt_secret, super_admin_email
    ):
        _create_quote(isolated_quotes_dir, "q_lst10001")
        token = _make_token(jwt_secret, super_admin_email)
        resp = client.get(
            "/api/admin/quotes",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"]["total"] == 1
        assert body["data"]["quotes"][0]["quote_id"] == "q_lst10001"

    def test_get_detail_super_admin(
        self, client, isolated_quotes_dir, whitelist_env, jwt_secret, super_admin_email
    ):
        _create_quote(isolated_quotes_dir, "q_det10001")
        token = _make_token(jwt_secret, super_admin_email)
        resp = client.get(
            "/api/admin/quotes/q_det10001",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["quote_id"] == "q_det10001"
        assert body["data"]["payload"]["full_name"] == "Karim Bensaid"
        assert body["data"]["status"]["status"] == "received"

    def test_get_detail_exposes_intake_confidential_flags(
        self, client, isolated_quotes_dir, whitelist_env, jwt_secret, super_admin_email, monkeypatch
    ):
        """US-IQ-03 — branche entretien : les sujets confidentiels flaggés
        doivent être récupérables via l'API admin détail devis."""
        path = _create_quote(isolated_quotes_dir, "q_iq030001")
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["intake_session_id"] = "intake-sess-abc"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        from app.api import quote as quote_api

        monkeypatch.setattr(
            quote_api.intake_service,
            "get_session",
            lambda session_id, **_kw: {
                "state": "completed",
                "route": "meeting",
                "confidential_flags": [{"topic_label": "structure actionnariale", "flagged_at": "2026-07-10T10:00:00Z"}],
            } if session_id == "intake-sess-abc" else None,
        )

        token = _make_token(jwt_secret, super_admin_email)
        resp = client.get(
            "/api/admin/quotes/q_iq030001",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["intake"]["route"] == "meeting"
        assert body["data"]["intake"]["confidential_flags"][0]["topic_label"] == "structure actionnariale"

    def test_get_detail_no_intake_session_returns_none(
        self, client, isolated_quotes_dir, whitelist_env, jwt_secret, super_admin_email
    ):
        _create_quote(isolated_quotes_dir, "q_iq030002")
        token = _make_token(jwt_secret, super_admin_email)
        resp = client.get(
            "/api/admin/quotes/q_iq030002",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["intake"] is None

    def test_get_detail_404(
        self, client, isolated_quotes_dir, whitelist_env, jwt_secret, super_admin_email
    ):
        token = _make_token(jwt_secret, super_admin_email)
        resp = client.get(
            "/api/admin/quotes/q_ghostzzz",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
        assert resp.get_json()["error_code"] == "QUOTE_NOT_FOUND"

    def test_patch_status_valid(
        self, client, isolated_quotes_dir, whitelist_env, jwt_secret, super_admin_email
    ):
        _create_quote(isolated_quotes_dir, "q_pst10001")
        token = _make_token(jwt_secret, super_admin_email)
        resp = client.patch(
            "/api/admin/quotes/q_pst10001/status",
            json={"status": "reviewing", "notes": "Looks legit"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["status"]["status"] == "reviewing"
        assert body["data"]["status"]["history"][0]["notes"] == "Looks legit"

    def test_patch_status_invalid_transition(
        self, client, isolated_quotes_dir, whitelist_env, jwt_secret, super_admin_email
    ):
        _create_quote(isolated_quotes_dir, "q_pst10002")
        token = _make_token(jwt_secret, super_admin_email)
        resp = client.patch(
            "/api/admin/quotes/q_pst10002/status",
            json={"status": "delivered"},  # received → delivered impossible
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409
        assert resp.get_json()["error_code"] == "INVALID_TRANSITION"

    def test_patch_status_missing_field(
        self, client, isolated_quotes_dir, whitelist_env, jwt_secret, super_admin_email
    ):
        _create_quote(isolated_quotes_dir, "q_pst10003")
        token = _make_token(jwt_secret, super_admin_email)
        resp = client.patch(
            "/api/admin/quotes/q_pst10003/status",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "INVALID_BODY"

    def test_patch_notes(
        self, client, isolated_quotes_dir, whitelist_env, jwt_secret, super_admin_email
    ):
        _create_quote(isolated_quotes_dir, "q_not10001")
        token = _make_token(jwt_secret, super_admin_email)
        resp = client.patch(
            "/api/admin/quotes/q_not10001/notes",
            json={"notes": "VIP — fast lane"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"]["notes"] == "VIP — fast lane"

    def test_filter_status(
        self, client, isolated_quotes_dir, whitelist_env, jwt_secret, super_admin_email
    ):
        _create_quote(isolated_quotes_dir, "q_flt10001")
        _create_quote(isolated_quotes_dir, "q_flt10002")
        qa.update_quote_status("q_flt10002", new_status="reviewing")
        token = _make_token(jwt_secret, super_admin_email)
        resp = client.get(
            "/api/admin/quotes?status=reviewing",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["total"] == 1
        assert body["data"]["quotes"][0]["quote_id"] == "q_flt10002"


# ─── Tests : email actions (US-104) ─────────────────────────────────────────


class TestSendPaymentLink:
    def test_email_sent_and_status_transitioned(
        self,
        client,
        isolated_quotes_dir,
        whitelist_env,
        jwt_secret,
        super_admin_email,
        monkeypatch,
    ):
        _create_quote(isolated_quotes_dir, "q_pay10001")
        # promote received → reviewing pour pouvoir aller à quoted.
        qa.update_quote_status("q_pay10001", new_status="reviewing")

        sent_calls = []
        def fake_send(to_email, subject, html_body, **kwargs):
            sent_calls.append({
                "to": to_email, "subject": subject,
                "html_len": len(html_body),
                "kwargs": kwargs,
            })
            return True

        # Le endpoint fait un `from ..services.email_service import send_email`
        # local, donc il faut patcher l'attribut du module.
        monkeypatch.setattr(email_service, "send_email", fake_send)

        token = _make_token(jwt_secret, super_admin_email)
        resp = client.post(
            "/api/admin/quotes/q_pay10001/send-payment-link",
            json={
                "payment_link": "https://buy.stripe.com/test_123",
                "custom_message": "Please pay within 7 days.",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        body = resp.get_json()
        assert body["data"]["email_sent"] is True
        assert body["data"]["status"]["status"] == "quoted"
        assert body["data"]["status"]["payment_link"] == "https://buy.stripe.com/test_123"
        assert body["data"]["status"]["last_email_sent_at"] is not None
        assert len(sent_calls) == 1
        assert sent_calls[0]["to"] == "client@example.com"

    def test_invalid_payment_link_400(
        self,
        client,
        isolated_quotes_dir,
        whitelist_env,
        jwt_secret,
        super_admin_email,
    ):
        _create_quote(isolated_quotes_dir, "q_pay10002")
        token = _make_token(jwt_secret, super_admin_email)
        resp = client.post(
            "/api/admin/quotes/q_pay10002/send-payment-link",
            json={"payment_link": "not-a-url"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "INVALID_BODY"

    def test_quote_not_found_404(
        self,
        client,
        isolated_quotes_dir,
        whitelist_env,
        jwt_secret,
        super_admin_email,
    ):
        token = _make_token(jwt_secret, super_admin_email)
        resp = client.post(
            "/api/admin/quotes/q_ghost000/send-payment-link",
            json={"payment_link": "https://buy.stripe.com/x"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestSendDelivered:
    def test_full_workflow_to_delivered(
        self,
        client,
        isolated_quotes_dir,
        whitelist_env,
        jwt_secret,
        super_admin_email,
        monkeypatch,
    ):
        _create_quote(isolated_quotes_dir, "q_dlv10001")
        # Walk through the workflow to reach in_progress.
        qa.update_quote_status("q_dlv10001", new_status="reviewing")
        qa.update_quote_status("q_dlv10001", new_status="quoted")
        qa.update_quote_status("q_dlv10001", new_status="paid")
        qa.update_quote_status("q_dlv10001", new_status="in_progress")

        # Le endpoint fait un import local depuis services.email_service.
        monkeypatch.setattr(email_service, "send_email", lambda *a, **k: True)

        token = _make_token(jwt_secret, super_admin_email)
        resp = client.post(
            "/api/admin/quotes/q_dlv10001/send-delivered",
            json={
                "delivered_url": "https://notion.so/report-123",
                "custom_message": "Thanks!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        body = resp.get_json()
        assert body["data"]["status"]["status"] == "delivered"
        assert body["data"]["status"]["delivered_url"] == "https://notion.so/report-123"


# ─── Tests : email_service helpers ──────────────────────────────────────────


class TestEmailService:
    def test_send_email_no_backend_returns_false(self, monkeypatch):
        monkeypatch.delenv("RESEND_API_KEY", raising=False)
        monkeypatch.delenv("EMAIL_SMTP_HOST", raising=False)
        ok = email_service.send_email(
            "x@y.com", "Test", "<p>Hi</p>",
        )
        assert ok is False

    def test_send_email_resend_success(self, monkeypatch):
        monkeypatch.setenv("RESEND_API_KEY", "re_abc")
        # Stub the resend module
        import sys
        fake = MagicMock()
        fake.Emails.send.return_value = {"id": "msg_xyz"}
        monkeypatch.setitem(sys.modules, "resend", fake)
        ok = email_service.send_email(
            "x@y.com", "Test", "<p>Hi</p>",
            from_email="from@bassira.test",
        )
        assert ok is True
        # SDK called with correct payload
        fake.Emails.send.assert_called_once()
        kwargs = fake.Emails.send.call_args[0][0]
        assert kwargs["to"] == ["x@y.com"]
        assert kwargs["from"] == "from@bassira.test"
        assert kwargs["subject"] == "Test"

    def test_send_email_empty_recipient_skipped(self, monkeypatch):
        monkeypatch.setenv("RESEND_API_KEY", "re_abc")
        ok = email_service.send_email("", "Test", "<p>Hi</p>")
        assert ok is False

    def test_render_template_known(self):
        html = email_service.render_template(
            "quote_received",
            {
                "full_name": "Karim",
                "company": "ACME",
                "package_label": "Crisis Drill",
                "industry_label": "banking",
                "quote_id": "q_test",
            },
        )
        assert "Karim" in html
        assert "ACME" in html
        assert "Crisis Drill" in html
        assert "q_test" in html

    def test_render_template_missing_fallbacks(self):
        # Template inexistant → fallback HTML générique.
        html = email_service.render_template("does_not_exist", {"a": "b"})
        assert "Bassira" in html
        assert "<b>a</b>" in html
