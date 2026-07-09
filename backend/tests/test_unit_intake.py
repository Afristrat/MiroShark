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

import itertools
import sys
import uuid
from datetime import datetime, timedelta, timezone
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

    def test_post_complete_delegates_to_service(self, client, monkeypatch):
        from app.api import intake as intake_api

        def _fake_complete(session_id, **_kw):
            assert session_id == "sess-1"
            return 200, {
                "success": True,
                "data": {"session_id": "sess-1", "state": "completed", "route": "meeting"},
            }

        monkeypatch.setattr(intake_api.intake_service, "complete_routing", _fake_complete)
        resp = client.post("/api/intake/session/sess-1/complete")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["route"] == "meeting"


# ─── _decide_route — table de vérité exhaustive (US-IQ-03, étape C) ─────────
#
# Règles de docs/intake/01-intake-spec.md §3.C (ADR-IQ-02, 100% déterministe,
# aucun LLM). ``_expected_route`` ci-dessous est une réimplémentation
# INDÉPENDANTE de la spec — pas un appel à ``svc._decide_route`` — pour que
# le test vérifie vraiment le comportement contre la spec, pas contre
# lui-même.

_FAR_DATE = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
_NEAR_DATE = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")

_DEADLINES = {
    "far": {"date": _FAR_DATE, "overdue": False},
    "near": {"date": _NEAR_DATE, "overdue": False},
    "overdue": {"date": None, "overdue": True},
    "unset": {"date": None, "overdue": False},
}

# (budget_bracket, exposure) — axe « enjeu » (A6), couvrant les frontières
# des deux règles qui en dépendent : self-service (budget lt_1m + exposure
# interne/sectorielle) et entretien (budget >= 10_100m, quelle que soit
# l'exposition).
_ENJEUX = [
    ("lt_1m", "interne"),
    ("lt_1m", "sectorielle"),
    ("lt_1m", "nationale"),
    ("lt_1m", "internationale"),
    ("1_10m", "interne"),
    ("1_10m", "sectorielle"),
    ("1_10m", "nationale"),
    ("1_10m", "internationale"),
    ("10_100m", "interne"),
    ("gt_100m", "internationale"),
]

_GOVERNANCES = ["solo", "comite_direction", "conseil_administration", "tutelle", "investisseurs"]

_FLAG_SETS = {
    "none": [],
    "one": [{"topic_label": "structure actionnariale", "flagged_at": "2026-07-10T10:00:00Z"}],
}


def _expected_route(budget_bracket, exposure, governance, deadline_key, flags_key) -> str:
    has_flag = flags_key == "one"
    if governance in ("conseil_administration", "tutelle", "investisseurs"):
        return "meeting"
    if budget_bracket in ("10_100m", "gt_100m"):
        return "meeting"
    if has_flag:
        return "meeting"
    if budget_bracket == "lt_1m" and exposure in ("interne", "sectorielle") and deadline_key == "far":
        return "self_service"
    return "quote_48h"


_TRUTH_TABLE_CASES = [
    (budget_bracket, exposure, governance, deadline_key, flags_key)
    for (budget_bracket, exposure), governance, deadline_key, flags_key in itertools.product(
        _ENJEUX, _GOVERNANCES, _DEADLINES.keys(), _FLAG_SETS.keys()
    )
]


class TestRouteDecisionTruthTable:
    @pytest.mark.parametrize(
        "budget_bracket,exposure,governance,deadline_key,flags_key", _TRUTH_TABLE_CASES
    )
    def test_matches_expected_route(self, budget_bracket, exposure, governance, deadline_key, flags_key):
        brief = {
            "governance": governance,
            "deadline": _DEADLINES[deadline_key],
            "stakes": {"budget_bracket": budget_bracket, "exposure": exposure},
        }
        confidential_flags = _FLAG_SETS[flags_key]
        expected = _expected_route(budget_bracket, exposure, governance, deadline_key, flags_key)
        assert svc._decide_route(brief, confidential_flags) == expected


class TestDeadlineBoundary:
    def test_exactly_14_days_is_not_far_enough(self):
        date_14 = (datetime.now(timezone.utc).date() + timedelta(days=14)).strftime("%Y-%m-%d")
        brief = {
            "governance": "solo",
            "deadline": {"date": date_14, "overdue": False},
            "stakes": {"budget_bracket": "lt_1m", "exposure": "interne"},
        }
        assert svc._decide_route(brief, []) == "quote_48h"

    def test_15_days_is_far_enough(self):
        date_15 = (datetime.now(timezone.utc).date() + timedelta(days=15)).strftime("%Y-%m-%d")
        brief = {
            "governance": "solo",
            "deadline": {"date": date_15, "overdue": False},
            "stakes": {"budget_bracket": "lt_1m", "exposure": "interne"},
        }
        assert svc._decide_route(brief, []) == "self_service"

    def test_malformed_date_falls_back_to_quote_48h(self):
        brief = {
            "governance": "solo",
            "deadline": {"date": "not-a-date", "overdue": False},
            "stakes": {"budget_bracket": "lt_1m", "exposure": "interne"},
        }
        assert svc._decide_route(brief, []) == "quote_48h"


# ─── complete_routing — service + machine à états ────────────────────────────


class TestCompleteRouting:
    def _session_ready(
        self,
        fake_client,
        *,
        brief_overrides: Dict[str, Any] | None = None,
        confidential_flags: List[Any] | None = None,
        state: str = "form_submitted",
    ) -> str:
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides=brief_overrides or {}), client=fake_client)
        update: Dict[str, Any] = {}
        if confidential_flags is not None:
            update["confidential_flags"] = confidential_flags
        if state != "form_submitted":
            update["state"] = state
        if update:
            fake_client.table("intake_sessions").update(update).eq("id", sid).execute()
        return sid

    def test_routes_to_meeting_for_high_governance(self, fake_client):
        sid = self._session_ready(fake_client, brief_overrides={"governance": "conseil_administration"})
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert body["data"]["route"] == "meeting"
        assert body["data"]["state"] == "completed"

    def test_routes_to_self_service_for_low_stakes_far_deadline(self, fake_client):
        sid = self._session_ready(
            fake_client,
            brief_overrides={
                "governance": "solo",
                "deadline": {"date": _FAR_DATE, "overdue": False},
                "stakes": {"budget_bracket": "lt_1m", "exposure": "interne"},
            },
        )
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert body["data"]["route"] == "self_service"

    def test_routes_to_quote_48h_by_default(self, fake_client):
        sid = self._session_ready(
            fake_client,
            brief_overrides={
                "governance": "comite_direction",
                "stakes": {"budget_bracket": "1_10m", "exposure": "sectorielle"},
            },
        )
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert body["data"]["route"] == "quote_48h"

    def test_meeting_route_triggered_by_confidential_flag_alone(self, fake_client):
        sid = self._session_ready(
            fake_client,
            brief_overrides={
                "governance": "solo",
                "deadline": {"date": _FAR_DATE, "overdue": False},
                "stakes": {"budget_bracket": "lt_1m", "exposure": "interne"},
            },
            confidential_flags=[{"topic_label": "conflit associés", "flagged_at": "2026-07-10T10:00:00Z"}],
        )
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert body["data"]["route"] == "meeting"

    def test_persists_route_and_completed_state(self, fake_client):
        sid = self._session_ready(fake_client, brief_overrides={"governance": "conseil_administration"})
        svc.complete_routing(sid, client=fake_client)
        session = svc.get_session(sid, client=fake_client)
        assert session["state"] == "completed"
        assert session["route"] == "meeting"
        assert session["completed_at"] is not None

    def test_session_not_found_returns_404(self, fake_client):
        status, body = svc.complete_routing("does-not-exist", client=fake_client)
        assert status == 404
        assert body["error_code"] == "SESSION_NOT_FOUND"

    def test_wrong_state_returns_409(self, fake_client):
        sid = svc.start_session(client=fake_client)["session_id"]  # 'started', pas de brief
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 409
        assert body["error_code"] == "INVALID_STATE"

    def test_already_completed_returns_409(self, fake_client):
        sid = self._session_ready(fake_client, brief_overrides={"governance": "conseil_administration"})
        svc.complete_routing(sid, client=fake_client)
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 409
        assert body["error_code"] == "INVALID_STATE"

    def test_agent_active_state_is_routable(self, fake_client):
        sid = self._session_ready(
            fake_client, brief_overrides={"governance": "conseil_administration"}, state="agent_active"
        )
        status, _body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
