"""Tests unitaires — report_delivery.py (US-130).

Couvre :
  1.  generate_signing_token + verify (valide)
  2.  verify token expiré
  3.  verify token falsifié (HMAC altéré)
  4.  verify token mal formé
  5.  create_delivery — mock Supabase + mock send_email
  6.  create_delivery — email failed → email_status = 'failed'
  7.  log_download — insertion de tracking
  8.  list_deliveries — tri + enrichissement display_status
  9.  list_downloads — tri par date
  10. re_send_link — nouveau token, invalide l'ancien
  11. re_send_link — delivery introuvable → ValueError
  12. auto_archive_after_90_days — compte les rows mises à jour
  13. Endpoint POST /api/admin/reports/<id>/deliver — super-admin → 201
  14. Endpoint POST /api/admin/reports/<id>/deliver — non super-admin → 403
  15. Endpoint GET  /r/<token> — token valide → PDF streamé
  16. Endpoint GET  /r/<token> — token invalide → 404
  17. Endpoint GET  /r/<token> — token expiré → 404
  18. Endpoint GET  /api/admin/reports/<id>/deliveries — super-admin → 200
  19. Endpoint POST /api/admin/reports/<id>/deliveries/<did>/resend — super-admin → 200
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# ─── Import du module sous test ───────────────────────────────────────────────

from app.services.report_delivery import (
    auto_archive_after_90_days,
    create_delivery,
    generate_signing_token,
    list_deliveries,
    list_downloads,
    log_download,
    re_send_link,
    verify_signing_token,
)


# ─── Helpers / fixtures ───────────────────────────────────────────────────────


def _make_supabase_mock(rows: List[Dict[str, Any]] = None):
    """Crée un faux client Supabase qui retourne ``rows`` pour tout appel."""
    rows = rows or []
    mock_resp = MagicMock()
    mock_resp.data = rows

    mock_cli = MagicMock()
    # Chaîne fluente : .table().select().eq().order().execute() → mock_resp
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.lt.return_value = mock_table
    mock_table.neq.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.execute.return_value = mock_resp
    mock_cli.table.return_value = mock_table
    return mock_cli, mock_resp, mock_table


# ═══════════════════════════════════════════════════════════════════════════════
# 1. generate_signing_token + verify valide
# ═══════════════════════════════════════════════════════════════════════════════

def test_generate_and_verify_token_valid():
    token = generate_signing_token("report-abc", 1, "client@example.com", expires_in_seconds=3600)
    assert isinstance(token, str)
    assert "." in token  # format payload.sig

    payload = verify_signing_token(token)
    assert payload is not None
    assert payload["rid"] == "report-abc"
    assert payload["ver"] == 1
    assert payload["eml"] == "client@example.com"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Token expiré → None
# ═══════════════════════════════════════════════════════════════════════════════

def test_verify_token_expired():
    # TTL 1 seconde
    token = generate_signing_token("report-xyz", 2, "x@y.com", expires_in_seconds=1)
    # Attendre l'expiration (time travel via mock)
    import app.services.report_delivery as mod

    original_now = mod._now_utc

    # Simuler 2 secondes dans le futur
    def _future_now():
        return datetime.now(tz=timezone.utc) + timedelta(seconds=2)

    mod._now_utc = _future_now
    try:
        result = verify_signing_token(token)
    finally:
        mod._now_utc = original_now

    assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Token falsifié (signature altérée) → None
# ═══════════════════════════════════════════════════════════════════════════════

def test_verify_token_tampered_signature():
    token = generate_signing_token("rep", 1, "a@b.com", expires_in_seconds=3600)
    payload_b64, sig = token.split(".", 1)
    # Altérer la signature
    tampered_sig = sig[:-4] + "XXXX"
    tampered_token = f"{payload_b64}.{tampered_sig}"
    assert verify_signing_token(tampered_token) is None


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Token mal formé → None
# ═══════════════════════════════════════════════════════════════════════════════

def test_verify_token_malformed():
    assert verify_signing_token("") is None
    assert verify_signing_token("notavalidtoken") is None
    assert verify_signing_token("a.b.c") is None  # 2 points → invalide
    assert verify_signing_token("onlyone") is None  # 0 points → invalide


# ═══════════════════════════════════════════════════════════════════════════════
# 5. create_delivery — Supabase mock + email OK
# ═══════════════════════════════════════════════════════════════════════════════

def test_create_delivery_success():
    mock_cli, mock_resp, mock_table = _make_supabase_mock(rows=[{
        "id": "delivery-001",
        "report_id": "rep-001",
        "version": 1,
        "recipient_email": "client@test.com",
        "recipient_name": "Alice",
        "signing_token": "tok",
        "expires_at": "2026-12-31T00:00:00+00:00",
        "email_status": "pending",
        "sent_at": None,
    }])

    with patch("app.services.report_delivery.send_email", return_value=True):
        delivery = create_delivery(
            "rep-001", 1, "client@test.com", "Alice",
            expiry_days=7, language="fr",
            client=mock_cli,
        )

    assert delivery["report_id"] == "rep-001"
    assert delivery["email_status"] == "sent"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. create_delivery — email failed → email_status = 'failed'
# ═══════════════════════════════════════════════════════════════════════════════

def test_create_delivery_email_failed():
    mock_cli, mock_resp, mock_table = _make_supabase_mock(rows=[{
        "id": "delivery-002",
        "report_id": "rep-002",
        "version": 1,
        "recipient_email": "bad@test.com",
        "recipient_name": "Bob",
        "signing_token": "tok2",
        "expires_at": "2026-12-31T00:00:00+00:00",
        "email_status": "pending",
        "sent_at": None,
    }])

    with patch("app.services.report_delivery.send_email", return_value=False):
        delivery = create_delivery(
            "rep-002", 1, "bad@test.com", "Bob",
            client=mock_cli,
        )

    assert delivery["email_status"] == "failed"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. log_download — insertion
# ═══════════════════════════════════════════════════════════════════════════════

def test_log_download_inserts_row():
    mock_cli, _, mock_table = _make_supabase_mock(rows=[])

    log_download(
        "delivery-001", "1.2.3.4", "Mozilla/5.0", "FR",
        referer="https://example.com",
        client=mock_cli,
    )

    # Vérifier qu'insert a été appelé
    mock_cli.table.assert_called_with("report_downloads")
    mock_table.insert.assert_called_once()
    inserted = mock_table.insert.call_args[0][0]
    assert inserted["delivery_id"] == "delivery-001"
    assert inserted["ip_address"] == "1.2.3.4"
    assert inserted["country_code"] == "FR"
    assert inserted["referer"] == "https://example.com"


# ═══════════════════════════════════════════════════════════════════════════════
# 8. list_deliveries — tri + display_status
# ═══════════════════════════════════════════════════════════════════════════════

def test_list_deliveries_enriches_status():
    past_expires = "2020-01-01T00:00:00+00:00"
    future_expires = "2099-01-01T00:00:00+00:00"
    rows = [
        {"id": "d1", "report_id": "r", "email_status": "sent", "expires_at": past_expires},
        {"id": "d2", "report_id": "r", "email_status": "sent", "expires_at": future_expires},
        {"id": "d3", "report_id": "r", "email_status": "pending", "expires_at": future_expires},
    ]
    mock_cli, _, _ = _make_supabase_mock(rows=rows)

    deliveries = list_deliveries("r", client=mock_cli)
    assert len(deliveries) == 3

    by_id = {d["id"]: d for d in deliveries}
    # d1 est expiré (expires_at dans le passé + email_status sent)
    assert by_id["d1"]["display_status"] == "expired"
    # d2 est envoyé et non expiré
    assert by_id["d2"]["display_status"] == "sent"
    # d3 est pending
    assert by_id["d3"]["display_status"] == "pending"


# ═══════════════════════════════════════════════════════════════════════════════
# 9. list_downloads
# ═══════════════════════════════════════════════════════════════════════════════

def test_list_downloads_returns_rows():
    rows = [
        {"id": "dl1", "delivery_id": "d1", "country_code": "MA", "downloaded_at": "2026-05-01T10:00:00+00:00"},
        {"id": "dl2", "delivery_id": "d1", "country_code": "FR", "downloaded_at": "2026-05-02T10:00:00+00:00"},
    ]
    mock_cli, _, _ = _make_supabase_mock(rows=rows)
    downloads = list_downloads("d1", client=mock_cli)
    assert len(downloads) == 2
    assert downloads[0]["country_code"] == "MA"


# ═══════════════════════════════════════════════════════════════════════════════
# 10. re_send_link — nouveau token
# ═══════════════════════════════════════════════════════════════════════════════

def test_re_send_link_generates_new_token():
    old_token = "oldtoken.oldsig"
    existing = [{
        "id": "d1",
        "report_id": "rep-001",
        "version": 1,
        "recipient_email": "c@c.com",
        "recipient_name": "Charlie",
        "language": "fr",
        "signing_token": old_token,
        "email_status": "sent",
    }]
    mock_cli, mock_resp, mock_table = _make_supabase_mock(rows=existing)

    with patch("app.services.report_delivery.send_email", return_value=True):
        delivery = re_send_link("d1", client=mock_cli)

    # Le nouveau token doit être différent de l'ancien
    assert delivery.get("signing_token") != old_token
    assert delivery.get("email_status") == "sent"


# ═══════════════════════════════════════════════════════════════════════════════
# 11. re_send_link — delivery introuvable → ValueError
# ═══════════════════════════════════════════════════════════════════════════════

def test_re_send_link_not_found():
    mock_cli, _, _ = _make_supabase_mock(rows=[])  # aucune row

    with pytest.raises(ValueError, match="Delivery introuvable"):
        re_send_link("nonexistent-id", client=mock_cli)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. auto_archive_after_90_days
# ═══════════════════════════════════════════════════════════════════════════════

def test_auto_archive_after_90_days():
    archived_rows = [{"id": "d1"}, {"id": "d2"}]
    mock_cli, _, _ = _make_supabase_mock(rows=archived_rows)

    count = auto_archive_after_90_days(client=mock_cli)
    assert count == 2


# ═══════════════════════════════════════════════════════════════════════════════
# Tests endpoint Flask — nécessite l'app Flask
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def flask_app():
    """Crée une instance Flask pour les tests endpoint."""
    import os
    os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "fake-service-role-key")
    os.environ.setdefault("BASSIRA_SUPER_ADMIN_EMAILS", "superadmin@bassira.com")
    os.environ.setdefault("BASSIRA_DELIVERY_HMAC_SECRET", "00" * 32)

    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture()
def client(flask_app):
    with flask_app.test_client() as c:
        yield c


def _super_admin_claims() -> Dict[str, Any]:
    return {
        "sub": "super-admin-uuid",
        "email": "superadmin@bassira.com",
        "aud": "authenticated",
        "role": "authenticated",
        "exp": 9999999999,
    }


def _regular_user_claims() -> Dict[str, Any]:
    return {
        "sub": "regular-user-uuid",
        "email": "user@acme.com",
        "aud": "authenticated",
        "role": "authenticated",
        "exp": 9999999999,
    }


def _fake_token() -> str:
    """JWT syntaxiquement valide (3 segments) mais non vérifié cryptographiquement."""
    import base64 as _b64
    header = _b64.b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
    payload = _b64.b64encode(b'{"sub":"x"}').decode().rstrip("=")
    return f"{header}.{payload}.fakesig"


# ─── 13. POST /api/admin/reports/<id>/deliver — super-admin → 201 ────────────

def test_endpoint_create_delivery_super_admin(client):
    """Super-admin peut créer une livraison."""
    mock_delivery = {
        "id": "del-001",
        "report_id": "rep-001",
        "version": 1,
        "recipient_email": "c@c.com",
        "recipient_name": "Client",
        "signing_token": "tok.sig",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "email_status": "sent",
        "sent_at": "2026-05-05T10:00:00+00:00",
    }
    with (
        patch("app.auth.decorators.verify_supabase_jwt", return_value=_super_admin_claims()),
        patch("app.api.report_delivery.get_supabase_admin") as mock_get_cli,
        patch("app.api.report_delivery.rd.create_delivery", return_value=mock_delivery),
    ):
        # Mock report_states lookup
        mock_cli = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = [{"current_version": 1}]
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = mock_resp
        mock_cli.table.return_value = mock_table
        mock_get_cli.return_value = mock_cli

        resp = client.post(
            "/api/admin/reports/rep-001/deliver",
            json={
                "recipient_email": "c@c.com",
                "recipient_name": "Client",
                "expiry_days": 7,
                "language": "fr",
            },
            headers={"Authorization": f"Bearer {_fake_token()}"},
        )

    assert resp.status_code == 201
    data = resp.get_json()
    assert data["success"] is True
    assert data["data"]["id"] == "del-001"


# ─── 14. POST /api/admin/reports/<id>/deliver — non super-admin → 403 ─────────

def test_endpoint_create_delivery_non_super_admin(client):
    """Un utilisateur non super-admin reçoit 403."""
    with patch("app.auth.decorators.verify_supabase_jwt", return_value=_regular_user_claims()):
        resp = client.post(
            "/api/admin/reports/rep-001/deliver",
            json={"recipient_email": "x@x.com"},
            headers={"Authorization": f"Bearer {_fake_token()}"},
        )
    assert resp.status_code == 403
    data = resp.get_json()
    assert data["error_code"] == "FORBIDDEN"


# ─── 15. GET /r/<token> — token valide → PDF streamé ────────────────────────

def test_endpoint_download_report_valid_token(tmp_path, client):
    """GET /r/<token> avec un token valide stream le PDF."""
    # Créer un faux PDF
    pdf_content = b"%PDF-1.4 fake pdf content"
    pdf_dir = tmp_path / "rep-001" / "v1"
    pdf_dir.mkdir(parents=True)
    pdf_file = pdf_dir / "full.pdf"
    pdf_file.write_bytes(pdf_content)

    with (
        patch("app.api.report_delivery.rd.verify_signing_token", return_value={
            "rid": "rep-001", "ver": 1, "eml": "c@c.com", "exp": 9999999999,
        }),
        patch("app.api.report_delivery.rd.log_download"),
        patch("app.api.report_delivery.get_supabase_admin") as mock_get_cli,
        patch("app.api.report_delivery._snapshot_pdf_path", return_value=pdf_file),
    ):
        mock_cli = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = [{"id": "del-001"}]
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = mock_resp
        mock_cli.table.return_value = mock_table
        mock_get_cli.return_value = mock_cli

        resp = client.get("/r/valid.token")

    assert resp.status_code == 200
    assert resp.content_type == "application/pdf"
    assert resp.data == pdf_content


# ─── 16. GET /r/<token> — token invalide → 404 ───────────────────────────────

def test_endpoint_download_report_invalid_token(client):
    """Token invalide → 404 TOKEN_INVALID_OR_EXPIRED."""
    resp = client.get("/r/badtoken.badsig")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["error_code"] == "TOKEN_INVALID_OR_EXPIRED"


# ─── 17. GET /r/<token> — token expiré → 404 ─────────────────────────────────

def test_endpoint_download_report_expired_token(client):
    """Token expiré → verify retourne None → 404."""
    with patch("app.api.report_delivery.rd.verify_signing_token", return_value=None):
        resp = client.get("/r/some.token")
    assert resp.status_code == 404


# ─── 18. GET /api/admin/reports/<id>/deliveries — super-admin → 200 ──────────

def test_endpoint_list_deliveries_super_admin(client):
    """Super-admin peut lister les livraisons d'un rapport."""
    deliveries_data = [
        {"id": "d1", "report_id": "rep-001", "email_status": "sent", "display_status": "sent"},
    ]
    with (
        patch("app.auth.decorators.verify_supabase_jwt", return_value=_super_admin_claims()),
        patch("app.api.report_delivery.get_supabase_admin") as mock_get_cli,
        patch("app.api.report_delivery.rd.list_deliveries", return_value=deliveries_data),
    ):
        mock_cli = MagicMock()
        mock_get_cli.return_value = mock_cli

        resp = client.get(
            "/api/admin/reports/rep-001/deliveries",
            headers={"Authorization": f"Bearer {_fake_token()}"},
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert len(data["data"]["deliveries"]) == 1


# ─── 19. POST resend — super-admin → 200 ─────────────────────────────────────

def test_endpoint_resend_super_admin(client):
    """Super-admin peut re-envoyer un lien de téléchargement."""
    updated_delivery = {
        "id": "d1",
        "report_id": "rep-001",
        "version": 1,
        "signing_token": "newtoken.newsig",
        "email_status": "sent",
    }
    with (
        patch("app.auth.decorators.verify_supabase_jwt", return_value=_super_admin_claims()),
        patch("app.api.report_delivery.get_supabase_admin") as mock_get_cli,
        patch("app.api.report_delivery.rd.re_send_link", return_value=updated_delivery),
    ):
        mock_cli = MagicMock()
        mock_get_cli.return_value = mock_cli

        resp = client.post(
            "/api/admin/reports/rep-001/deliveries/d1/resend",
            json={},
            headers={"Authorization": f"Bearer {_fake_token()}"},
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["data"]["signing_token"] == "newtoken.newsig"
