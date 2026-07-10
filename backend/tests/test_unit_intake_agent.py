"""Tests unitaires US-IQ-02 — agent conversationnel de qualification.

Couvre :
  - Validation jsonschema de la sortie de l'agent (message/insights/
    confidential_flag/close)
  - Construction du contexte agent (system prompt + brief + historique),
    exclusion stricte de ``aar_known_outcome``
  - Garde-fou budget 7 tours (403 sur le 8e, vérifié en base)
  - Persistance immédiate de chaque tour (transcript, agent_turns,
    confidential_flags)
  - Repli gracieux si le client LLM lève une exception (gateway down)
  - Endpoint Flask ``POST /api/intake/session/<id>/agent/turn``

Le client LLM est toujours un double en mémoire — aucun appel réseau réel.
Le corpus fixture ≥10 transcripts (grille §10.3, critères automatiques
1-8) vit dans ``backend/scripts/test_intake_agent_corpus.py`` (appel LLM
réel, hors suite bloquante — cf. conftest.py, convention hand-run scripts).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services import intake_service as svc  # noqa: E402


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


@pytest.fixture
def fake_client(monkeypatch):
    from tests.test_unit_intake import FakeSupabase

    cli = FakeSupabase()
    cli.table("organizations").rows.append({"id": "org-bassira-1", "slug": "aimpower-bassira"})
    monkeypatch.setattr(svc, "get_default_super_admin_org_id", lambda _c=None: "org-bassira-1")
    return cli


# ─── Schéma de sortie de l'agent ──────────────────────────────────────────────


class TestAgentOutputSchema:
    def test_valid_output_passes(self):
        data = {
            "message": "Qu'est-ce qui vous retient de choisir l'option A ?",
            "insights": ["Le budget est déjà voté en interne."],
            "confidential_flag": None,
            "close": False,
        }
        assert svc._validate_agent_output(data) is None

    def test_valid_output_with_confidential_flag_passes(self):
        data = {
            "message": "Je note ce point de côté.",
            "insights": [],
            "confidential_flag": {"topic_label": "conflit avec un actionnaire"},
            "close": False,
        }
        assert svc._validate_agent_output(data) is None

    def test_missing_required_field_rejected(self):
        data = {"message": "x", "insights": [], "close": False}
        assert svc._validate_agent_output(data) is not None

    def test_extra_field_rejected(self):
        data = {
            "message": "x", "insights": [], "confidential_flag": None,
            "close": False, "price_hint": "5000 MAD",
        }
        assert svc._validate_agent_output(data) is not None

    def test_wrong_type_close_rejected(self):
        data = {"message": "x", "insights": [], "confidential_flag": None, "close": "false"}
        assert svc._validate_agent_output(data) is not None

    def test_confidential_flag_without_topic_label_rejected(self):
        data = {"message": "x", "insights": [], "confidential_flag": {}, "close": False}
        assert svc._validate_agent_output(data) is not None


# ─── Constructeur de contexte agent ───────────────────────────────────────────


def _brief_with_aar(**overrides) -> Dict[str, Any]:
    brief = {
        "decision": "Faut-il ouvrir 12 agences supplémentaires dans le Sud du pays ?",
        "options": ["Ouvrir 12 agences", "Ouvrir 4 agences pilotes"],
        "deadline": {"date": "2026-09-01", "overdue": False},
        "governance": "conseil_administration",
        "past_method": ["etude"],
        "past_gap": "Données terrain insuffisantes.",
        "stakes": {"budget_bracket": "10_100m", "jobs": 240, "exposure": "nationale"},
        "geo": [{"country": "MA", "segment": "retail bancaire rural"}],
        "data_assets": ["etudes"],
        "aar_known_outcome": "Nous avions finalement ouvert 6 agences, succès mitigé.",
        "agent_insights": [],
        "brief_version": "1",
    }
    brief.update(overrides)
    return brief


class TestBuildAgentMessages:
    def test_system_prompt_selected_by_locale(self):
        for locale in ("fr", "en", "ar"):
            messages = svc._build_agent_messages(_brief_with_aar(), locale, [], "bonjour")
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == svc.AGENT_SYSTEM_PROMPTS[locale].format(
                locale=locale,
                brief_formulaire_json=json.dumps(
                    {k: v for k, v in _brief_with_aar().items() if k != "aar_known_outcome"},
                    ensure_ascii=False,
                ),
                messages_precedents=json.dumps([], ensure_ascii=False),
            )

    def test_unknown_locale_falls_back_to_fr(self):
        messages = svc._build_agent_messages(_brief_with_aar(), "de", [], "bonjour")
        assert messages[0]["content"].startswith(
            svc.AGENT_SYSTEM_PROMPTS["fr"].split("{brief_formulaire_json}")[0][:40]
        )

    def test_last_message_is_current_user_input(self):
        messages = svc._build_agent_messages(_brief_with_aar(), "fr", [], "Ma question")
        assert messages[-1] == {"role": "user", "content": "Ma question"}

    def test_aar_known_outcome_never_in_system_prompt(self):
        """R8 (docs/intake/10-execution-prompts.md notes d'implémentation) —
        le champ aar_known_outcome ne doit JAMAIS entrer dans le contexte
        construit pour l'agent, quel que soit son contenu."""
        brief = _brief_with_aar(aar_known_outcome="SECRET_MARKER_ISSUE_REELLE_XYZ")
        messages = svc._build_agent_messages(brief, "fr", [], "salut")
        assert "SECRET_MARKER_ISSUE_REELLE_XYZ" not in messages[0]["content"]

    def test_previous_transcript_embedded_as_data(self):
        prior = [{"role": "user", "content": "premier message", "ts": "2026-07-10T10:00:00Z"}]
        messages = svc._build_agent_messages(_brief_with_aar(), "fr", prior, "suite")
        assert "premier message" in messages[0]["content"]


# ─── agent_turn — happy path ──────────────────────────────────────────────────


class _FakeLLM:
    """Double de LLMClient — retourne une séquence de sorties JSON scriptées."""

    def __init__(self, outputs):
        self._outputs = list(outputs)
        self.calls = []

    def chat_json(self, messages, temperature=0.3, max_tokens=1024):
        self.calls.append({"messages": messages, "temperature": temperature, "max_tokens": max_tokens})
        if not self._outputs:
            raise AssertionError("no more scripted outputs")
        return self._outputs.pop(0)


def _submitted_session(fake_client) -> str:
    from tests.test_unit_intake import _valid_payload

    sid = svc.start_session(client=fake_client)["session_id"]
    svc.submit_form(sid, _valid_payload(), client=fake_client)
    return sid


class TestAgentTurnHappyPath:
    def test_first_turn_transitions_to_agent_active_and_persists_transcript(self, fake_client):
        sid = _submitted_session(fake_client)
        llm = _FakeLLM([{
            "message": "Vous mentionnez ouvrir 12 agences — qu'est-ce qui vous retient de trancher aujourd'hui ?",
            "insights": ["Le comité hésite sur le rythme d'ouverture."],
            "confidential_flag": None,
            "close": False,
        }])
        status, body = svc.agent_turn(sid, "Nous hésitons sur le rythme.", client=fake_client, llm=llm)
        assert status == 200
        assert body["success"] is True
        assert body["data"]["state"] == "agent_active"
        assert body["data"]["agent_turns"] == 1
        assert "retient de trancher" in body["data"]["message"]

        session = svc._get_session(sid, client=fake_client)
        assert session["state"] == "agent_active"
        assert session["agent_turns"] == 1
        assert len(session["transcript"]) == 2  # user + assistant
        assert session["transcript"][0]["role"] == "user"
        assert session["transcript"][0]["content"] == "Nous hésitons sur le rythme."
        assert session["transcript"][1]["role"] == "assistant"

    def test_close_true_completes_session_with_route(self, fake_client):
        sid = _submitted_session(fake_client)
        llm = _FakeLLM([{
            "message": "Merci, votre brief est transmis.",
            "insights": ["Blocage réel identifié : arbitrage budgétaire."],
            "confidential_flag": None,
            "close": True,
        }])
        status, body = svc.agent_turn(sid, "Voilà, c'est tout.", client=fake_client, llm=llm)
        assert status == 200
        assert body["data"]["state"] == "completed"
        assert body["data"]["route"] in ("self_service", "quote_48h", "meeting")

        session = svc._get_session(sid, client=fake_client)
        assert session["state"] == "completed"
        assert session["route"] is not None
        assert session["completed_at"] is not None

    def test_llm_called_with_correct_model_and_temperature(self, fake_client, monkeypatch):
        sid = _submitted_session(fake_client)
        captured = {}

        def _fake_create_llm_client(**kwargs):
            captured.update(kwargs)
            return _FakeLLM([{
                "message": "ok", "insights": [], "confidential_flag": None, "close": False,
            }])

        monkeypatch.setattr(svc, "create_llm_client", _fake_create_llm_client)
        svc.agent_turn(sid, "salut", client=fake_client)
        assert captured["timeout"] == 30.0
        assert "model" in captured

    def test_session_not_found_returns_404(self, fake_client):
        llm = _FakeLLM([])
        status, body = svc.agent_turn("does-not-exist", "hello", client=fake_client, llm=llm)
        assert status == 404
        assert body["error_code"] == "SESSION_NOT_FOUND"

    def test_wrong_state_returns_409(self, fake_client):
        sid = svc.start_session(client=fake_client)["session_id"]  # jamais soumis
        llm = _FakeLLM([])
        status, body = svc.agent_turn(sid, "hello", client=fake_client, llm=llm)
        assert status == 409
        assert body["error_code"] == "INVALID_STATE"


# ─── agent_turn — garde-fou budget 7 tours ────────────────────────────────────


class TestAgentTurnBudgetGuard:
    def test_eighth_turn_rejected_even_if_client_retries(self, fake_client):
        sid = _submitted_session(fake_client)
        # Simule 7 tours déjà joués directement en base (sans passer par
        # l'agent — on isole le garde-fou du reste de la logique).
        fake_client.table("intake_sessions").update({
            "agent_turns": 7, "state": "agent_active",
        }).eq("id", sid).execute()

        llm = _FakeLLM([])  # ne doit JAMAIS être appelé
        status, body = svc.agent_turn(sid, "encore une question", client=fake_client, llm=llm)
        assert status == 403
        assert body["error_code"] == "AGENT_BUDGET_EXHAUSTED"
        assert llm.calls == []  # le LLM n'a pas été sollicité — vérifié en base d'abord

    def test_seventh_turn_still_allowed(self, fake_client):
        sid = _submitted_session(fake_client)
        fake_client.table("intake_sessions").update({
            "agent_turns": 6, "state": "agent_active",
        }).eq("id", sid).execute()

        llm = _FakeLLM([{"message": "dernière question", "insights": [], "confidential_flag": None, "close": False}])
        status, body = svc.agent_turn(sid, "ok", client=fake_client, llm=llm)
        assert status == 200
        assert body["data"]["agent_turns"] == 7
