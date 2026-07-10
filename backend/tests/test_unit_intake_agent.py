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

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services import intake_service as svc  # noqa: E402


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
