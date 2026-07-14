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
# aucun LLM ; ADR-IQ-12, repli par défaut = meeting). ``_expected_route`` ci-dessous
# est une réimplémentation
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
    return "meeting"


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
        assert svc._decide_route(brief, []) == "meeting"

    def test_15_days_is_far_enough(self):
        date_15 = (datetime.now(timezone.utc).date() + timedelta(days=15)).strftime("%Y-%m-%d")
        brief = {
            "governance": "solo",
            "deadline": {"date": date_15, "overdue": False},
            "stakes": {"budget_bracket": "lt_1m", "exposure": "interne"},
        }
        assert svc._decide_route(brief, []) == "self_service"

    def test_malformed_date_falls_back_to_meeting(self):
        brief = {
            "governance": "solo",
            "deadline": {"date": "not-a-date", "overdue": False},
            "stakes": {"budget_bracket": "lt_1m", "exposure": "interne"},
        }
        assert svc._decide_route(brief, []) == "meeting"


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

    def test_routes_to_meeting_by_default(self, fake_client):
        """Repli par défaut (ADR-IQ-12) : un brief sans stake explicite (budget/
        gouvernance sous les seuils meeting, hors fenêtre self-service) part quand
        même en meeting — on ne protège plus le temps commercial en phase de
        calibrage, cf. directive Amine 2026-07-13."""
        sid = self._session_ready(
            fake_client,
            brief_overrides={
                "governance": "comite_direction",
                "stakes": {"budget_bracket": "1_10m", "exposure": "sectorielle"},
            },
        )
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert body["data"]["route"] == "meeting"

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

    def test_completion_sends_confirmation_email_best_effort(self, fake_client, monkeypatch):
        """Depuis ADR-IQ-12 (repli par défaut = meeting), self_service est la
        SEULE branche non-meeting encore atteignable par _decide_route — c'est
        elle qui sert ici à vérifier l'envoi d'email best-effort en clôture."""
        calls = []
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda *, to_email, subject, html_body, **kw: calls.append(
                {"to_email": to_email, "subject": subject, "html_body": html_body}
            ) or True,
        )
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
        assert len(calls) == 1
        assert calls[0]["to_email"] == "karim@banquepop.ma"  # cf. _valid_payload

    def test_completion_skips_email_for_meeting_route(self, fake_client, monkeypatch):
        """Depuis ce Task, la branche meeting ne déclenche plus l'email à la
        clôture — il part désormais uniquement après confirm_calcom_booking
        (créneau réellement vérifié), cf. Task 2 de ce plan."""
        calls = []
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda **kw: calls.append(kw) or True,
        )
        sid = self._session_ready(fake_client, brief_overrides={"governance": "conseil_administration"})
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert body["data"]["route"] == "meeting"
        assert calls == []

    def test_completion_returns_calcom_link_for_meeting(self, fake_client):
        sid = self._session_ready(fake_client, brief_overrides={"governance": "conseil_administration"})
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert body["data"]["route"] == "meeting"
        assert "calcom_link" in body["data"]
        assert body["data"]["calcom_link"].startswith("https://agenda.ai-mpower.com/")
        assert "email=karim%40banquepop.ma" in body["data"]["calcom_link"]

    def test_completion_email_failure_never_breaks_routing(self, fake_client, monkeypatch):
        """Best-effort total (même contrat que _log_escalation, ADR-IQ-08) —
        une panne d'email ne doit JAMAIS faire échouer complete_routing."""
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda **kw: (_ for _ in ()).throw(RuntimeError("resend down")),
        )
        sid = self._session_ready(fake_client, brief_overrides={"governance": "solo"})
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert body["success"] is True

    def test_completion_skips_email_when_no_quote_linked(self, fake_client, monkeypatch):
        """Si le lien quote_ownership a échoué à la soumission (best-effort,
        cf. submit_form), complete_routing ne doit pas planter faute
        d'email destinataire trouvable."""
        calls = []
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda **kw: calls.append(kw) or True,
        )
        sid = self._session_ready(fake_client, brief_overrides={"governance": "solo"})
        fake_client.table("quote_ownership").rows.clear()
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert calls == []

    def test_admin_notification_skipped_when_not_configured(self, fake_client, monkeypatch):
        """Par défaut (INTAKE_ESCALATION_NOTIFY_EMAIL vide), aucune notif
        admin n'est envoyée — comportement inchangé tant qu'Amine n'a pas
        configuré l'adresse sur Coolify (ADR-IQ-14)."""
        calls = []
        monkeypatch.setattr(svc, "send_email", lambda *a, **kw: calls.append(a) or True)
        monkeypatch.setattr(svc.Config, "INTAKE_ESCALATION_NOTIFY_EMAIL", "")
        sid = self._session_ready(fake_client, brief_overrides={"governance": "solo"})
        status, _body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert calls == []

    def test_admin_notification_sent_on_completion_for_self_service(self, fake_client, monkeypatch):
        """ADR-IQ-14 : notification admin best-effort à la clôture, sur le
        même canal Resend que _log_escalation (INTAKE_ESCALATION_NOTIFY_EMAIL),
        pour toutes les routes — remplace le canal SMTP legacy jamais
        configuré sur Coolify."""
        calls = []
        monkeypatch.setattr(svc, "send_email", lambda *a, **kw: calls.append(a) or True)
        monkeypatch.setattr(svc.Config, "INTAKE_ESCALATION_NOTIFY_EMAIL", "amine@ai-mpower.com")
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
        assert calls[-1][0] == "amine@ai-mpower.com"
        assert "karim@banquepop.ma" in calls[-1][2]  # cf. _valid_payload

    def test_admin_notification_sent_for_meeting_route_with_calcom_link(self, fake_client, monkeypatch):
        """Contrairement à l'email client (jamais envoyé pour meeting à la
        clôture, cf. ADR-IQ-10bis), la notif admin part bien pour TOUTES
        les routes, y compris meeting — avec le lien Cal.com dans le corps."""
        calls = []
        monkeypatch.setattr(svc, "send_email", lambda *a, **kw: calls.append(a) or True)
        monkeypatch.setattr(svc.Config, "INTAKE_ESCALATION_NOTIFY_EMAIL", "amine@ai-mpower.com")
        sid = self._session_ready(fake_client, brief_overrides={"governance": "conseil_administration"})
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert body["data"]["route"] == "meeting"
        assert len(calls) == 1
        assert calls[0][0] == "amine@ai-mpower.com"
        assert "agenda.ai-mpower.com" in calls[0][2]

    def test_admin_notification_failure_never_breaks_routing(self, fake_client, monkeypatch):
        """Best-effort total (même contrat que _log_escalation/_send_intake_confirmation,
        ADR-IQ-08) — une panne d'email admin ne doit JAMAIS faire échouer complete_routing."""
        monkeypatch.setattr(svc, "send_email", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("resend down")))
        monkeypatch.setattr(svc.Config, "INTAKE_ESCALATION_NOTIFY_EMAIL", "amine@ai-mpower.com")
        sid = self._session_ready(fake_client, brief_overrides={"governance": "solo"})
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert body["success"] is True

    def test_admin_notification_html_escapes_decision(self, fake_client, monkeypatch):
        """Le brief est une entrée non fiable — il doit être échappé avant
        injection dans le corps HTML de la notif admin."""
        calls = []
        monkeypatch.setattr(svc, "send_email", lambda *a, **kw: calls.append(a) or True)
        monkeypatch.setattr(svc.Config, "INTAKE_ESCALATION_NOTIFY_EMAIL", "amine@ai-mpower.com")
        sid = self._session_ready(fake_client, brief_overrides={
            "governance": "solo",
            "decision": "<script>alert(1)</script> " + "x" * 20,
        })
        svc.complete_routing(sid, client=fake_client)
        assert len(calls) == 1
        html_body = calls[0][2]
        assert "<script>alert(1)</script>" not in html_body
        assert "&lt;script&gt;" in html_body


class TestFinalizeSessionSelfService:
    def test_complete_routing_returns_package_recommendation_for_self_service(self, fake_client, monkeypatch):
        monkeypatch.setattr(
            svc, "create_intake_llm_client",
            lambda **kw: _StubLLM({"package_id": "adcheck_lite", "rationale": "Test de concept publicitaire."}),
        )
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides={
            "governance": "solo",
            "deadline": {"date": _FAR_DATE, "overdue": False},
            "stakes": {"budget_bracket": "lt_1m", "exposure": "interne"},
        }), client=fake_client)
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert body["data"]["route"] == "self_service"
        assert body["data"]["package_recommendation"] == {
            "package_id": "adcheck_lite", "rationale": "Test de concept publicitaire.",
        }


class _StubLLM:
    def __init__(self, output):
        self._output = output

    def chat_json(self, messages, temperature=0.3, max_tokens=1024):
        return self._output


class TestConfirmCalcomBooking:
    """Depuis ADR-IQ-09 (durcissement sécurité post-review), toute confirmation
    exige une vérification server-to-server du booking_uid auprès de l'API
    Cal.com (jamais de confiance dans un uid/email fourni par le client sans
    preuve) — ``requests.get`` est monkeypatché sur ``svc.requests``."""

    @staticmethod
    def _mock_calcom_booking(monkeypatch, *, email="karim@banquepop.ma", event_type_id=25, status="ACCEPTED", found=True):
        class _FakeResponse:
            def __init__(self, status_code, payload):
                self.status_code = status_code
                self._payload = payload

            def json(self):
                return self._payload

        def _fake_get(url, headers=None, timeout=None):
            if not found:
                return _FakeResponse(404, {"status": "error"})
            return _FakeResponse(200, {
                "data": {"status": status, "eventTypeId": event_type_id, "attendees": [{"email": email}]}
            })

        monkeypatch.setattr(svc.requests, "get", _fake_get)

    def test_persists_booking_uid(self, fake_client, monkeypatch):
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides={"governance": "conseil_administration"}), client=fake_client)
        svc.complete_routing(sid, client=fake_client)
        self._mock_calcom_booking(monkeypatch)

        status, body = svc.confirm_calcom_booking(sid, "cal-booking-uid-xyz", client=fake_client)
        assert status == 200
        session = svc.get_session(sid, client=fake_client)
        assert session["calcom_booking_uid"] == "cal-booking-uid-xyz"

    def test_session_not_found_returns_404(self, fake_client, monkeypatch):
        self._mock_calcom_booking(monkeypatch, email="ghost@example.com")
        status, body = svc.confirm_calcom_booking("does-not-exist", "uid", client=fake_client)
        assert status == 404

    def test_falls_back_to_verified_email_when_session_id_missing(self, fake_client, monkeypatch):
        """Constat empirique 2026-07-11 (ADR-IQ-09) : Cal.com ne relaie jamais
        intake_session_id au redirect de succès. Le fallback retrouve la
        session via l'email ATTESTÉ par Cal.com lui-même (pas un query param
        client), pour une réservation réellement confirmée sur le bon event
        type."""
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides={"governance": "conseil_administration"}), client=fake_client)
        svc.complete_routing(sid, client=fake_client)
        self._mock_calcom_booking(monkeypatch, email="karim@banquepop.ma")

        status, body = svc.confirm_calcom_booking(None, "cal-booking-uid-xyz", client=fake_client)
        assert status == 200
        session = svc.get_session(sid, client=fake_client)
        assert session["calcom_booking_uid"] == "cal-booking-uid-xyz"

    def test_email_fallback_ignores_already_claimed_sessions(self, fake_client, monkeypatch):
        """Deux sessions 'meeting' complétées pour le même email (le prospect a
        recommencé) : le fallback doit ignorer celle déjà réclamée par une
        précédente réservation et cibler l'autre."""
        self._mock_calcom_booking(monkeypatch, email="karim@banquepop.ma")

        sid_claimed = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid_claimed, _valid_payload(brief_overrides={"governance": "conseil_administration"}), client=fake_client)
        svc.complete_routing(sid_claimed, client=fake_client)
        svc.confirm_calcom_booking(sid_claimed, "already-claimed-uid", client=fake_client)

        sid_open = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid_open, _valid_payload(brief_overrides={"governance": "conseil_administration"}), client=fake_client)
        svc.complete_routing(sid_open, client=fake_client)

        status, body = svc.confirm_calcom_booking(None, "new-uid", client=fake_client)
        assert status == 200
        assert svc.get_session(sid_open, client=fake_client)["calcom_booking_uid"] == "new-uid"
        assert svc.get_session(sid_claimed, client=fake_client)["calcom_booking_uid"] == "already-claimed-uid"

    def test_email_fallback_returns_404_when_no_match(self, fake_client, monkeypatch):
        self._mock_calcom_booking(monkeypatch, email="inconnu@example.com")
        status, body = svc.confirm_calcom_booking(None, "uid", client=fake_client)
        assert status == 404
        assert body["error_code"] == "CONFIRMATION_FAILED"

    # ─── Durcissement sécurité (review automatique post-commit) ──────────────
    # Un uid n'est plus JAMAIS pris pour argent comptant : sans preuve Cal.com
    # d'une réservation réelle, ACCEPTED, sur le bon event type, et dont
    # l'attendee correspond à la session visée, rien n'est persisté.

    def test_rejects_uid_unknown_to_calcom(self, fake_client, monkeypatch):
        """Un uid inventé par un attaquant (spoofable-field bypass) ne doit
        jamais pouvoir écrire calcom_booking_uid."""
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides={"governance": "conseil_administration"}), client=fake_client)
        svc.complete_routing(sid, client=fake_client)
        self._mock_calcom_booking(monkeypatch, found=False)

        status, body = svc.confirm_calcom_booking(sid, "attacker-invented-uid", client=fake_client)
        assert status == 404
        assert body["error_code"] == "CONFIRMATION_FAILED"
        session = svc.get_session(sid, client=fake_client)
        assert session.get("calcom_booking_uid") is None

    def test_rejects_when_verified_email_does_not_match_targeted_session(self, fake_client, monkeypatch):
        """Un session_id connu/deviné ne suffit pas si le uid appartient
        réellement, côté Cal.com, à une réservation d'un autre attendee."""
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides={"governance": "conseil_administration"}), client=fake_client)
        svc.complete_routing(sid, client=fake_client)
        self._mock_calcom_booking(monkeypatch, email="quelquun-dautre@example.com")

        status, body = svc.confirm_calcom_booking(sid, "real-uid-wrong-attendee", client=fake_client)
        assert status != 200
        session = svc.get_session(sid, client=fake_client)
        assert session.get("calcom_booking_uid") is None

    def test_rejects_booking_on_wrong_event_type(self, fake_client, monkeypatch):
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides={"governance": "conseil_administration"}), client=fake_client)
        svc.complete_routing(sid, client=fake_client)
        self._mock_calcom_booking(monkeypatch, email="karim@banquepop.ma", event_type_id=999)

        status, body = svc.confirm_calcom_booking(sid, "uid-other-event-type", client=fake_client)
        assert status != 200
        session = svc.get_session(sid, client=fake_client)
        assert session.get("calcom_booking_uid") is None

    def test_confirmation_sends_email_confirming_meeting_not_asking_to_rebook(self, fake_client, monkeypatch):
        """L'email post-booking doit confirmer le rendez-vous, jamais
        redemander une réservation (ADR-IQ-10 bis — corrige une régression
        de contenu trouvée en revue whole-branch : l'ancienne copy 'Réservez
        votre entretien' + lien de booking était contradictoire une fois
        l'email déplacé après la réservation vérifiée)."""
        calls = []
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda *, to_email, subject, html_body, **kw: calls.append(
                {"to_email": to_email, "html_body": html_body}
            ) or True,
        )
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides={"governance": "conseil_administration"}), client=fake_client)
        svc.complete_routing(sid, client=fake_client)
        assert calls == []  # pas encore envoyé (Task 1)

        self._mock_calcom_booking(monkeypatch)
        status, _body = svc.confirm_calcom_booking(sid, "cal-booking-uid-xyz", client=fake_client)
        assert status == 200
        assert len(calls) == 1
        assert calls[0]["to_email"] == "karim@banquepop.ma"
        html_body = calls[0]["html_body"]
        assert "agenda.ai-mpower.com" not in html_body
        assert "Réservez" not in html_body

    def test_confirmation_email_failure_never_breaks_confirmation(self, fake_client, monkeypatch):
        """Best-effort — même contrat que _send_intake_confirmation partout
        ailleurs : une panne d'email ne doit jamais faire échouer la
        confirmation de réservation elle-même."""
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda **kw: (_ for _ in ()).throw(RuntimeError("resend down")),
        )
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides={"governance": "conseil_administration"}), client=fake_client)
        svc.complete_routing(sid, client=fake_client)
        self._mock_calcom_booking(monkeypatch)

        status, body = svc.confirm_calcom_booking(sid, "uid-1", client=fake_client)
        assert status == 200
        assert body["success"] is True

    def test_confirmation_failure_does_not_send_email(self, fake_client, monkeypatch):
        calls = []
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda **kw: calls.append(kw) or True,
        )
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides={"governance": "conseil_administration"}), client=fake_client)
        svc.complete_routing(sid, client=fake_client)
        self._mock_calcom_booking(monkeypatch, found=False)  # uid inconnu de Cal.com

        status, _body = svc.confirm_calcom_booking(sid, "attacker-invented-uid", client=fake_client)
        assert status == 404
        assert calls == []

    def test_rejects_cancelled_booking(self, fake_client, monkeypatch):
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides={"governance": "conseil_administration"}), client=fake_client)
        svc.complete_routing(sid, client=fake_client)
        self._mock_calcom_booking(monkeypatch, email="karim@banquepop.ma", status="CANCELLED")

        status, body = svc.confirm_calcom_booking(sid, "cancelled-uid", client=fake_client)
        assert status != 200
        session = svc.get_session(sid, client=fake_client)
        assert session.get("calcom_booking_uid") is None


class TestBuildCalcomBookingLink:
    def test_includes_locked_email_and_name_when_provided(self):
        link = svc._build_calcom_booking_link(
            "sess-1", "fr", email="karim@banquepop.ma", full_name="Karim Bensaid"
        )
        assert "email=karim%40banquepop.ma" in link
        assert "name=Karim+Bensaid" in link

    def test_omits_email_and_name_when_not_provided(self):
        link = svc._build_calcom_booking_link("sess-1", "fr")
        assert "email=" not in link
        assert "name=" not in link


class TestCalcomConfirmedEndpoint:
    def test_get_redirects_and_persists_uid(self, client, monkeypatch):
        from app.api import intake as intake_api

        captured = {}
        def _fake_confirm(session_id, booking_uid, **kw):
            captured["session_id"] = session_id
            captured["booking_uid"] = booking_uid
            return 200, {"success": True, "data": {"session_id": session_id, "calcom_booking_uid": booking_uid}}

        monkeypatch.setattr(intake_api.intake_service, "confirm_calcom_booking", _fake_confirm)
        resp = client.get("/api/intake/calcom-confirmed?intake_session_id=sess-1&uid=booking-abc")
        assert resp.status_code in (302, 200)
        assert captured["session_id"] == "sess-1"
        assert captured["booking_uid"] == "booking-abc"

    def test_get_uid_alone_is_forwarded_for_server_side_resolution(self, client, monkeypatch):
        """Reproduit le cas réel observé le 2026-07-11 : Cal.com ne relaie
        jamais `intake_session_id`. `uid` seul suffit désormais — la
        ré-identification (email ATTESTÉ par Cal.com, pas un query param
        client) est entièrement déléguée à confirm_calcom_booking."""
        from app.api import intake as intake_api

        captured = {}
        def _fake_confirm(session_id, booking_uid, **kw):
            captured["session_id"] = session_id
            captured["booking_uid"] = booking_uid
            return 200, {"success": True, "data": {"session_id": None, "calcom_booking_uid": booking_uid}}

        monkeypatch.setattr(intake_api.intake_service, "confirm_calcom_booking", _fake_confirm)
        resp = client.get("/api/intake/calcom-confirmed?uid=booking-abc&email=karim%40banquepop.ma")
        assert resp.status_code in (302, 200)
        assert captured["session_id"] is None
        assert captured["booking_uid"] == "booking-abc"

    def test_get_missing_params_returns_400(self, client):
        resp = client.get("/api/intake/calcom-confirmed")
        assert resp.status_code == 400
