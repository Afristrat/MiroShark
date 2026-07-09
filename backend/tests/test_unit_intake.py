"""Tests unitaires US-IQ-01 — module Intake (parcours de qualification /devis).

Couvre :
  - ``start_session`` : création + défauts sur locale/entry_door invalides
  - ``submit_form`` : validation A1 (>=15 car.), A2 (2-4 options), A7 (geo
    obligatoire) — un payload aussi pauvre que ``q_f767321b`` (2026-07-09,
    l'incident qui a motivé ce chantier) doit être rejeté en 400
  - ``submit_form`` : happy path (brief construit, state → form_submitted,
    quote_ownership lié pour rétrocompatibilité admin)
  - ``submit_form`` : session introuvable (404) / état invalide (409)
  - Endpoints Flask ``POST /api/intake/session`` et
    ``POST /api/intake/session/<id>/form``

Toutes les interactions Supabase sont doublées par un fake stateful en
mémoire — aucune dépendance live.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pytest


_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services import intake_service as svc  # noqa: E402


# ─── Fake Supabase client (stateful, en mémoire) ─────────────────────────────


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table: "_FakeTable", op: str, payload=None):
        self._table = table
        self._op = op
        self._payload = payload
        self._filters: Dict[str, Any] = {}

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def limit(self, n):
        return self

    def select(self, *_a, **_kw):
        self._op = "select"
        return self

    def execute(self):
        if self._op == "insert":
            row = dict(self._payload)
            row.setdefault("id", str(uuid.uuid4()))
            self._table.rows.append(row)
            return _Result([row])
        if self._op == "select":
            rows = [
                r for r in self._table.rows
                if all(r.get(k) == v for k, v in self._filters.items())
            ]
            return _Result(rows)
        if self._op == "update":
            matched = [
                r for r in self._table.rows
                if all(r.get(k) == v for k, v in self._filters.items())
            ]
            for r in matched:
                r.update(self._payload)
            return _Result(matched)
        raise AssertionError(f"unsupported op {self._op}")


class _FakeTable:
    def __init__(self, name: str):
        self.name = name
        self.rows: List[Dict[str, Any]] = []

    def insert(self, payload):
        return _Query(self, "insert", payload)

    def select(self, *_a, **_kw):
        return _Query(self, "select")

    def update(self, payload):
        return _Query(self, "update", payload)


class FakeSupabase:
    """Fake client Supabase minimal — un ``_FakeTable`` stateful par nom."""

    def __init__(self):
        self._tables: Dict[str, _FakeTable] = {}

    def table(self, name: str) -> _FakeTable:
        if name not in self._tables:
            self._tables[name] = _FakeTable(name)
        return self._tables[name]


@pytest.fixture
def fake_client(monkeypatch):
    cli = FakeSupabase()
    # Une org par défaut, pour que le lien quote_ownership réussisse.
    cli.table("organizations").rows.append({"id": "org-bassira-1", "slug": "aimpower-bassira"})
    monkeypatch.setattr(svc, "get_default_super_admin_org_id", lambda _c=None: "org-bassira-1")
    return cli


# ─── Payloads de test ─────────────────────────────────────────────────────────


def _valid_brief(**overrides) -> Dict[str, Any]:
    brief = {
        "decision": "Faut-il ouvrir 12 agences supplémentaires dans le Sud du pays ?",
        "options": ["Ouvrir 12 agences", "Ouvrir 4 agences pilotes", "Ne rien faire cette année"],
        "deadline": {"date": "2026-09-01", "overdue": False},
        "governance": "conseil_administration",
        "past_method": ["etude", "instinct"],
        "past_gap": "Les données terrain manquaient de granularité régionale.",
        "stakes": {"budget_bracket": "10_100m", "jobs": 240, "exposure": "nationale"},
        "geo": [{"country": "MA", "segment": "retail bancaire rural"}],
        "data_assets": ["etudes", "donnees_clients"],
    }
    brief.update(overrides)
    return brief


def _valid_payload(*, brief_overrides: Dict[str, Any] | None = None, **overrides) -> Dict[str, Any]:
    payload = {
        "full_name": "Karim Bensaid",
        "email": "karim@banquepop.ma",
        "company": "Banque Populaire MA",
        "consent_rgpd": True,
        "brief": _valid_brief(**(brief_overrides or {})),
    }
    payload.update(overrides)
    return payload


# ─── start_session ────────────────────────────────────────────────────────────


class TestStartSession:
    def test_defaults(self, fake_client):
        data = svc.start_session(locale="fr", entry_door="standard", client=fake_client)
        assert data["state"] == "started"
        assert data["locale"] == "fr"
        assert data["entry_door"] == "standard"
        assert data["session_id"]

    def test_invalid_locale_falls_back_to_fr(self, fake_client):
        data = svc.start_session(locale="de", entry_door="standard", client=fake_client)
        assert data["locale"] == "fr"

    def test_invalid_entry_door_falls_back_to_standard(self, fake_client):
        data = svc.start_session(locale="fr", entry_door="bogus", client=fake_client)
        assert data["entry_door"] == "standard"


# ─── submit_form — validation bloquante A1/A2/A7 ─────────────────────────────


class TestSubmitFormValidation:
    def _started_session_id(self, fake_client) -> str:
        return svc.start_session(client=fake_client)["session_id"]

    def test_a1_too_short_rejected(self, fake_client):
        sid = self._started_session_id(fake_client)
        status, body = svc.submit_form(sid, _valid_payload(brief_overrides={"decision": "Trop court"}), client=fake_client)
        assert status == 400
        assert body["error_code"] == "A1_TOO_SHORT"

    def test_a2_too_few_options_rejected(self, fake_client):
        sid = self._started_session_id(fake_client)
        status, body = svc.submit_form(sid, _valid_payload(brief_overrides={"options": ["Seule option"]}), client=fake_client)
        assert status == 400
        assert body["error_code"] == "A2_TOO_FEW"

    def test_a7_missing_geo_rejected(self, fake_client):
        sid = self._started_session_id(fake_client)
        status, body = svc.submit_form(sid, _valid_payload(brief_overrides={"geo": []}), client=fake_client)
        assert status == 400
        assert body["error_code"] == "A7_REQUIRED"

    def test_incident_payload_q_f767321b_style_is_rejected(self, fake_client):
        """Reproduit le payload pauvre du 2026-07-09 (message=libellé, champs
        vides) qui a motivé le chantier — doit être impossible par construction.
        """
        sid = self._started_session_id(fake_client)
        poor_payload = {
            "full_name": "Test User",
            "email": "test@example.com",
            "company": "Acme",
            "consent_rgpd": True,
            "brief": {"decision": "", "options": [], "geo": []},
        }
        status, body = svc.submit_form(sid, poor_payload, client=fake_client)
        assert status == 400
        assert body["success"] is False

    def test_missing_identity_rejected(self, fake_client):
        sid = self._started_session_id(fake_client)
        payload = _valid_payload()
        del payload["email"]
        status, body = svc.submit_form(sid, payload, client=fake_client)
        assert status == 400
        assert body["error_code"] == "MISSING_FIELD"

    def test_rgpd_not_accepted_rejected(self, fake_client):
        sid = self._started_session_id(fake_client)
        status, body = svc.submit_form(sid, _valid_payload(consent_rgpd=False), client=fake_client)
        assert status == 400
        assert body["error_code"] == "RGPD_NOT_ACCEPTED"


# ─── submit_form — happy path + machine à états ──────────────────────────────


class TestSubmitFormHappyPath:
    def test_valid_payload_transitions_to_form_submitted(self, fake_client):
        sid = svc.start_session(client=fake_client)["session_id"]
        status, body = svc.submit_form(sid, _valid_payload(), client=fake_client)
        assert status == 200
        assert body["success"] is True
        assert body["data"]["state"] == "form_submitted"
        assert body["data"]["quote_id"].startswith("q_")

        session = svc._get_session(sid, client=fake_client)
        assert session["state"] == "form_submitted"
        assert session["brief"]["decision"] == _valid_payload()["brief"]["decision"]
        assert session["brief"]["options"] == _valid_payload()["brief"]["options"]
        assert session["brief"]["geo"] == [{"country": "MA", "segment": "retail bancaire rural"}]
        assert session["brief"]["brief_version"] == "1"

    def test_quote_ownership_linked_for_backward_compat(self, fake_client):
        sid = svc.start_session(client=fake_client)["session_id"]
        _status, body = svc.submit_form(sid, _valid_payload(), client=fake_client)
        quote_id = body["data"]["quote_id"]

        linked = fake_client.table("quote_ownership").rows
        assert len(linked) == 1
        assert linked[0]["quote_id"] == quote_id
        assert linked[0]["org_id"] == "org-bassira-1"
        assert linked[0]["payload"]["intake_session_id"] == sid

    def test_session_not_found_returns_404(self, fake_client):
        status, body = svc.submit_form("does-not-exist", _valid_payload(), client=fake_client)
        assert status == 404
        assert body["error_code"] == "SESSION_NOT_FOUND"

    def test_resubmit_after_form_submitted_returns_409(self, fake_client):
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(), client=fake_client)
        status, body = svc.submit_form(sid, _valid_payload(), client=fake_client)
        assert status == 409
        assert body["error_code"] == "INVALID_STATE"


# ─── Endpoints Flask ──────────────────────────────────────────────────────────


@pytest.fixture
def app(monkeypatch):
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
def client(app):
    return app.test_client()


class TestIntakeEndpoints:
    def test_post_session_start(self, client, fake_client, monkeypatch):
        from app.api import intake as intake_api

        monkeypatch.setattr(intake_api.intake_service, "start_session", lambda **_kw: {
            "session_id": "sess-1", "state": "started", "locale": "fr", "entry_door": "standard",
        })
        resp = client.post("/api/intake/session", json={"locale": "fr"})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"]["session_id"] == "sess-1"

    def test_post_form_delegates_to_service(self, client, monkeypatch):
        from app.api import intake as intake_api

        def _fake_submit(session_id, payload, **_kw):
            assert session_id == "sess-1"
            return 400, {"success": False, "error_code": "A1_TOO_SHORT", "error": "..."}

        monkeypatch.setattr(intake_api.intake_service, "submit_form", _fake_submit)
        resp = client.post("/api/intake/session/sess-1/form", json={"decision": "x"})
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "A1_TOO_SHORT"
