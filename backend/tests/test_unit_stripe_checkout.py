"""Tests unitaires US-IQ-03 — propagation ``intake_session_id`` en metadata
Stripe (``create_checkout_session``, US-205/ADR-014).

Le webhook existant n'est PAS modifié (cf. docs/intake/05-integrations.md) —
seule la création de la Checkout Session est concernée ici. Aucun appel
Stripe réel : ``requests.post`` est monkeypatché.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import pytest


_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services import stripe_service  # noqa: E402


class _FakeResponse:
    def __init__(self, status_code: int, payload: Dict[str, Any]):
        self.status_code = status_code
        self._payload = payload
        self.ok = 200 <= status_code < 300
        self.text = str(payload)

    def json(self):
        return self._payload


@pytest.fixture
def stripe_key(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")


class TestCreateCheckoutSessionIntakeMetadata:
    def test_intake_session_id_propagated_in_metadata(self, stripe_key, monkeypatch):
        captured: Dict[str, Any] = {}

        def _fake_post(url, data=None, auth=None, timeout=None):
            captured["url"] = url
            captured["data"] = data
            return _FakeResponse(200, {"id": "cs_test_1", "url": "https://checkout.stripe.com/c/pay/cs_test_1"})

        monkeypatch.setattr(stripe_service.requests, "post", _fake_post)

        stripe_service.create_checkout_session(
            package_id="pmf_discovery",
            currency="mad",
            intake_session_id="intake-sess-abc",
        )

        assert captured["data"]["metadata[intake_session_id]"] == "intake-sess-abc"

    def test_no_intake_session_id_omits_metadata_key(self, stripe_key, monkeypatch):
        captured: Dict[str, Any] = {}

        def _fake_post(url, data=None, auth=None, timeout=None):
            captured["data"] = data
            return _FakeResponse(200, {"id": "cs_test_2", "url": "https://checkout.stripe.com/c/pay/cs_test_2"})

        monkeypatch.setattr(stripe_service.requests, "post", _fake_post)

        stripe_service.create_checkout_session(package_id="pmf_discovery", currency="mad")

        assert "metadata[intake_session_id]" not in captured["data"]


class TestCheckoutEndpointPassesThroughIntakeSessionId:
    @pytest.fixture
    def app(self, monkeypatch):
        from app import storage as storage_pkg

        class _DummyStorage:
            def __init__(self, *a, **kw):
                pass

        monkeypatch.setattr(storage_pkg, "Neo4jStorage", _DummyStorage)
        from app import create_app

        app_obj = create_app()
        app_obj.config["TESTING"] = True
        return app_obj

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_endpoint_forwards_intake_session_id(self, client, monkeypatch):
        from app.api import stripe_checkout as sc_api

        captured: Dict[str, Any] = {}

        def _fake_create(*, package_id, currency, customer_email=None, intake_session_id=None):
            captured["intake_session_id"] = intake_session_id
            return {"id": "cs_test_3", "url": "https://checkout.stripe.com/c/pay/cs_test_3"}

        monkeypatch.setattr(sc_api, "create_checkout_session", _fake_create)

        resp = client.post(
            "/api/stripe/create-checkout-session",
            json={"package_id": "pmf_discovery", "currency": "mad", "intake_session_id": "intake-sess-xyz"},
        )
        assert resp.status_code == 200
        assert captured["intake_session_id"] == "intake-sess-xyz"

    def test_endpoint_omits_intake_session_id_when_absent(self, client, monkeypatch):
        from app.api import stripe_checkout as sc_api

        captured: Dict[str, Any] = {}

        def _fake_create(*, package_id, currency, customer_email=None, intake_session_id=None):
            captured["intake_session_id"] = intake_session_id
            return {"id": "cs_test_4", "url": "https://checkout.stripe.com/c/pay/cs_test_4"}

        monkeypatch.setattr(sc_api, "create_checkout_session", _fake_create)

        resp = client.post(
            "/api/stripe/create-checkout-session",
            json={"package_id": "pmf_discovery", "currency": "mad"},
        )
        assert resp.status_code == 200
        assert captured["intake_session_id"] is None
