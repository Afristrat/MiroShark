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

import sys
from pathlib import Path

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
