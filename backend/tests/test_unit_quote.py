"""Unit tests for US-025 — POST /api/quote.

Pure offline tests — Flask test client + monkeypatch over
``smtplib.SMTP`` and ``Config.WONDERWALL_DATA_DIR``. No real network, no
real disk outside ``tmp_path``.

We cover the eight behaviours US-025 commits to:

1. A well-formed payload returns 200, persists a JSON file, returns a
   ``q_<8 hex>`` id and an ISO ``submitted_at``.
2. Missing email → 400 ``MISSING_FIELD``.
3. Malformed email → 400 ``INVALID_EMAIL``.
4. ``consent_rgpd: false`` → 400 ``RGPD_NOT_ACCEPTED``.
5. Unknown package → 400 ``INVALID_PACKAGE``.
6. SMTP raises → handler still returns 200 and the file is on disk
   (best-effort by design).
7. Overlong text fields are truncated (``full_name`` capped at 100,
   ``message`` at 800).
8. Generated ``quote_id`` matches ``q_<8 hex>``.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest


_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ─── Shared fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def isolated_quotes_dir(tmp_path, monkeypatch):
    """Point the quote service at a throwaway ``tmp_path/uploads``.

    We set ``WONDERWALL_DATA_DIR`` on the *currently-live*
    ``app.config.Config`` so no real directory under
    ``backend/uploads/`` is touched. The service re-imports
    ``Config`` on every call (so it survives ``importlib.reload`` in
    other test modules), so we patch the live module attribute rather
    than a cached reference.
    """
    from app import config as config_module

    base = tmp_path / "uploads"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        config_module.Config,
        "WONDERWALL_DATA_DIR",
        str(base),
        raising=False,
    )
    return base


@pytest.fixture
def smtp_mock(monkeypatch):
    """Replace ``smtplib.SMTP`` with a minimal context-manager stub.

    Exposes ``.calls`` so individual tests can assert on what was sent
    without actually opening a socket.
    """
    import smtplib

    class _StubSMTP:
        calls: list = []

        def __init__(self, host, port, timeout=10):
            type(self).calls.append({"event": "init", "host": host, "port": port})

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ehlo(self):
            type(self).calls.append({"event": "ehlo"})

        def starttls(self):
            type(self).calls.append({"event": "starttls"})

        def login(self, user, password):
            type(self).calls.append({"event": "login", "user": user})

        def sendmail(self, sender, recipients, body):
            type(self).calls.append({
                "event": "sendmail",
                "sender": sender,
                "recipients": recipients,
                "body_len": len(body),
            })

    _StubSMTP.calls = []
    monkeypatch.setattr(smtplib, "SMTP", _StubSMTP)
    monkeypatch.setenv("EMAIL_SMTP_HOST", "smtp.test.local")
    monkeypatch.setenv("EMAIL_SMTP_PORT", "587")
    monkeypatch.setenv("EMAIL_SMTP_USER", "user")
    monkeypatch.setenv("EMAIL_SMTP_PASSWORD", "pass")
    monkeypatch.setenv("EMAIL_FROM", "noreply@ai-mpower.com")
    monkeypatch.setenv("EMAIL_TO", "contact@ai-mpower.com")
    return _StubSMTP


@pytest.fixture
def reset_rate_limit():
    """Wipe the in-memory rate-limit dict between tests so each test
    starts fresh — otherwise the 6th test from the same fixture run
    would 429.
    """
    from app.services import quote_service

    quote_service._reset_rate_limit_for_tests()
    yield
    quote_service._reset_rate_limit_for_tests()


@pytest.fixture
def client(isolated_quotes_dir, reset_rate_limit, monkeypatch):
    """Flask test client — minimal app with only ``quote_bp`` mounted.

    Builds a bare ``Flask`` instance rather than ``create_app()`` so the
    test does not need a Neo4j connection or LLM credentials.
    """
    from flask import Flask
    from app.api.quote import quote_bp

    app = Flask(__name__)
    app.testing = True
    app.register_blueprint(quote_bp, url_prefix="/api/quote")
    return app.test_client()


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _valid_payload(**overrides):
    base = {
        "full_name": "Karim Bensaid",
        "email": "karim@example.com",
        "company": "Banque Populaire MA",
        "role": "Head of Communications",
        "phone": "+212600123456",
        "package": "crisis_drill_24h",
        "expected_simulations_per_year": 4,
        "target_deadline": "1_month",
        "industry": "banking",
        "geo_focus": ["MA"],
        "message": "We want to drill our crisis comms team next quarter.",
        "consent_rgpd": True,
        "locale": "fr",
    }
    base.update(overrides)
    return base


# ─── Tests ───────────────────────────────────────────────────────────────────


def test_submit_valid_quote_returns_200_and_stores_file(
    client, smtp_mock, isolated_quotes_dir
):
    """A valid payload returns 200 and writes a single JSON file under
    the configured quotes directory."""
    res = client.post("/api/quote", json=_valid_payload())
    assert res.status_code == 200, res.get_data(as_text=True)
    body = res.get_json()
    assert body["success"] is True
    assert "quote_id" in body["data"]
    assert "submitted_at" in body["data"]

    quotes_dir = isolated_quotes_dir / "quotes"
    files = list(quotes_dir.glob("quote_*.json"))
    assert len(files) == 1, f"expected one quote file, got {files}"

    record = json.loads(files[0].read_text(encoding="utf-8"))
    assert record["quote_id"] == body["data"]["quote_id"]
    # Email is preserved (not HTML-escaped — it's never rendered as HTML).
    assert record["email"] == "karim@example.com"
    # Package + locale survive the round-trip.
    assert record["package"] == "crisis_drill_24h"
    assert record["locale"] == "fr"

    # SMTP was attempted — depuis US-104, on envoie deux emails :
    #   1. Notification interne sales (legacy US-025) → contact@ai-mpower.com
    #   2. Confirmation au client (US-104) → email du payload
    sent = [c for c in smtp_mock.calls if c["event"] == "sendmail"]
    assert len(sent) == 2
    recipients = {tuple(c["recipients"]) for c in sent}
    assert ("contact@ai-mpower.com",) in recipients
    assert ("karim@example.com",) in recipients


def test_quote_missing_email_returns_400_MISSING_FIELD(client, smtp_mock):
    payload = _valid_payload()
    payload.pop("email")
    res = client.post("/api/quote", json=payload)
    assert res.status_code == 400
    body = res.get_json()
    assert body["success"] is False
    assert body["error_code"] == "MISSING_FIELD"
    # No email was attempted.
    assert smtp_mock.calls == []


def test_quote_invalid_email_format_returns_400_INVALID_EMAIL(client, smtp_mock):
    res = client.post("/api/quote", json=_valid_payload(email="not-an-email"))
    assert res.status_code == 400
    body = res.get_json()
    assert body["error_code"] == "INVALID_EMAIL"


def test_quote_consent_false_returns_400_RGPD_NOT_ACCEPTED(client, smtp_mock):
    res = client.post("/api/quote", json=_valid_payload(consent_rgpd=False))
    assert res.status_code == 400
    body = res.get_json()
    assert body["error_code"] == "RGPD_NOT_ACCEPTED"


def test_quote_invalid_package_returns_400_INVALID_PACKAGE(client, smtp_mock):
    res = client.post("/api/quote", json=_valid_payload(package="enterprise_unicorn"))
    assert res.status_code == 400
    body = res.get_json()
    assert body["error_code"] == "INVALID_PACKAGE"


def test_quote_smtp_failure_does_not_break_response(
    client, isolated_quotes_dir, monkeypatch
):
    """SMTP raising mid-send must not prevent the 200 + file persistence.

    The lead is captured on disk before the email attempt, so a
    flapping SMTP server should never lose a quote.
    """
    import smtplib

    class _BoomSMTP:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def ehlo(self):
            pass

        def starttls(self):
            pass

        def login(self, *a, **kw):
            pass

        def sendmail(self, *a, **kw):
            raise smtplib.SMTPException("simulated SMTP failure")

    monkeypatch.setattr(smtplib, "SMTP", _BoomSMTP)
    monkeypatch.setenv("EMAIL_SMTP_HOST", "smtp.test.local")
    monkeypatch.setenv("EMAIL_SMTP_PORT", "587")
    monkeypatch.setenv("EMAIL_SMTP_USER", "user")
    monkeypatch.setenv("EMAIL_SMTP_PASSWORD", "pass")

    res = client.post("/api/quote", json=_valid_payload())
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True

    files = list((isolated_quotes_dir / "quotes").glob("quote_*.json"))
    assert len(files) == 1


def test_quote_truncates_overlong_fields(client, smtp_mock, isolated_quotes_dir):
    """``full_name`` > 100 chars is truncated, ``message`` > 800 too."""
    long_name = "A" * 250
    long_message = "M" * 1500
    res = client.post(
        "/api/quote",
        json=_valid_payload(full_name=long_name, message=long_message),
    )
    assert res.status_code == 200, res.get_data(as_text=True)

    files = list((isolated_quotes_dir / "quotes").glob("quote_*.json"))
    record = json.loads(files[0].read_text(encoding="utf-8"))
    # Sanitisation is applied AFTER truncation, so the cap is on the raw
    # length pre-escape. A pure ASCII "A" survives html.escape unchanged,
    # so length 100 is exact here.
    assert len(record["full_name"]) == 100
    assert len(record["message"]) == 800


def test_quote_id_format(client, smtp_mock):
    res = client.post("/api/quote", json=_valid_payload())
    assert res.status_code == 200
    quote_id = res.get_json()["data"]["quote_id"]
    assert re.fullmatch(r"q_[0-9a-f]{8}", quote_id), (
        f"unexpected quote_id format: {quote_id!r}"
    )
