"""Tests unitaires — cadres adaptatifs Cerberus pour ScenarioSuggestions.

Vérifie :
  - _detect_framework : auto-détection depuis le contenu du document
  - _clean_suggestions : validation des labels par cadre
  - Backward-compat : _SCENARIO_SUGGEST_SYSTEM_PROMPT et _VALID_SCENARIO_LABELS
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Imports des fonctions à tester
# ---------------------------------------------------------------------------

from app.api.simulation import (
    _detect_framework,
    _clean_suggestions,
    _FRAMEWORK_LABELS,
    _FRAMEWORK_PROMPTS,
    _VALID_FRAMEWORK_IDS,
    _VALID_SCENARIO_LABELS,
    _SCENARIO_SUGGEST_SYSTEM_PROMPT,
)


# ---------------------------------------------------------------------------
# _detect_framework
# ---------------------------------------------------------------------------

class TestDetectFramework:
    def test_crisis_signal_french(self):
        assert _detect_framework(
            "Suite à la crise réputationnelle de la marque, les consommateurs expriment leur mécontentement."
        ) == "crisis"

    def test_crisis_signal_english(self):
        assert _detect_framework(
            "The company is facing a major PR disaster following the data breach backlash."
        ) == "crisis"

    def test_policy_signal_french(self):
        assert _detect_framework(
            "Le projet de réglementation sur l'IA proposé par le ministre sera soumis au parlement."
        ) == "policy"

    def test_policy_signal_english(self):
        assert _detect_framework(
            "The EU AI Act directive is expected to pass through the Senate before December."
        ) == "policy"

    def test_market_signal(self):
        assert _detect_framework(
            "Bitcoin reached a new all-time high as crypto trading volume surged on major exchanges."
        ) == "market"

    def test_market_signal_stock(self):
        assert _detect_framework(
            "Le fonds de pension a repositionné son portfolio suite à la volatilité du marché bourse."
        ) == "market"

    def test_decision_signal_french(self):
        assert _detect_framework(
            "Le lancement produit est prévu pour Q3. L'équipe marketing prépare la campagne go-to-market."
        ) == "decision"

    def test_decision_signal_english(self):
        assert _detect_framework(
            "The startup is evaluating product-market fit across early adopter customer segments."
        ) == "decision"

    def test_default_cerberus(self):
        """Un texte générique doit retourner cerberus."""
        assert _detect_framework(
            "The meeting concluded with a general discussion about the future direction of the organization."
        ) == "cerberus"

    def test_crisis_takes_priority_over_policy(self):
        """Crisis signals prennent le dessus sur policy dans un texte mixte."""
        text = (
            "Le scandale autour du ministre a déclenché une crise réputationnelle majeure. "
            "La réglementation gouvernementale est mise en question."
        )
        assert _detect_framework(text) == "crisis"


# ---------------------------------------------------------------------------
# _clean_suggestions — validation par cadre
# ---------------------------------------------------------------------------

def _make_suggestion(label: str, question: str = "Will X happen within 6 months?") -> dict:
    return {
        "question": question,
        "label": label,
        "expected_yes_range": [40, 60],
        "rationale": "Based on current evidence.",
        "simulation_requirement": "Simulate the main actors and their interactions.",
    }


class TestCleanSuggestions:
    def test_cerberus_labels_accepted(self):
        payload = {
            "suggestions": [
                _make_suggestion("Challenger"),
                _make_suggestion("Defender"),
                _make_suggestion("Arbiter"),
            ]
        }
        result = _clean_suggestions(payload, framework="cerberus")
        assert len(result) == 3
        labels = [s["label"] for s in result]
        assert labels == ["Challenger", "Defender", "Arbiter"]

    def test_market_labels_accepted(self):
        payload = {
            "suggestions": [
                _make_suggestion("Bull"),
                _make_suggestion("Bear"),
                _make_suggestion("Neutral"),
            ]
        }
        result = _clean_suggestions(payload, framework="market")
        assert len(result) == 3

    def test_decision_labels_accepted(self):
        payload = {
            "suggestions": [
                _make_suggestion("Optimist"),
                _make_suggestion("Skeptic"),
                _make_suggestion("Pragmatist"),
            ]
        }
        result = _clean_suggestions(payload, framework="decision")
        assert len(result) == 3

    def test_crisis_labels_accepted(self):
        payload = {
            "suggestions": [
                _make_suggestion("Amplifier"),
                _make_suggestion("Attenuator"),
                _make_suggestion("Moderator"),
            ]
        }
        result = _clean_suggestions(payload, framework="crisis")
        assert len(result) == 3

    def test_policy_labels_accepted(self):
        payload = {
            "suggestions": [
                _make_suggestion("Progressive"),
                _make_suggestion("Conservative"),
                _make_suggestion("Technocrat"),
            ]
        }
        result = _clean_suggestions(payload, framework="policy")
        assert len(result) == 3

    def test_cross_framework_label_kept(self):
        """Un label d'un autre framework est conservé (cross-framework tolerance).
        Le LLM dévie parfois du template — on garde plutôt que de jeter."""
        payload = {
            "suggestions": [
                _make_suggestion("Bull"),
                _make_suggestion("Bear"),
                _make_suggestion("Neutral"),
            ]
        }
        result = _clean_suggestions(payload, framework="crisis")
        # Cross-framework labels kept rather than discarded so the user
        # always sees 3 suggestions instead of 0.
        assert len(result) == 3
        assert result[0]["label"] == "Bull"

    def test_cross_framework_label_cerberus_in_market(self):
        """'Challenger' d'un cadre cerberus est conservé même dans 'market'."""
        payload = {
            "suggestions": [
                _make_suggestion("Challenger"),
                _make_suggestion("Defender"),
                _make_suggestion("Arbiter"),
            ]
        }
        result = _clean_suggestions(payload, framework="market")
        assert len(result) == 3
        assert result[0]["label"] == "Challenger"

    def test_simulation_requirement_preserved(self):
        """Le champ simulation_requirement est transmis dans le résultat."""
        payload = {
            "suggestions": [
                {
                    "question": "Will X recover within 3 months?",
                    "label": "Amplifier",
                    "expected_yes_range": [20, 35],
                    "rationale": "Crisis is escalating.",
                    "simulation_requirement": "Simulate media actors and customer reactions.",
                }
            ]
        }
        result = _clean_suggestions(payload, framework="crisis")
        assert len(result) == 1
        assert result[0]["simulation_requirement"] == "Simulate media actors and customer reactions."

    def test_missing_simulation_requirement_allowed(self):
        """simulation_requirement absent → chaîne vide dans le résultat."""
        payload = {
            "suggestions": [
                {
                    "question": "Will the policy pass this quarter?",
                    "label": "Progressive",
                    "expected_yes_range": [55, 70],
                    "rationale": "Strong coalition support.",
                }
            ]
        }
        result = _clean_suggestions(payload, framework="policy")
        assert len(result) == 1
        assert result[0]["simulation_requirement"] == ""

    def test_default_framework_is_cerberus(self):
        """Sans paramètre de cadre, le défaut est cerberus."""
        payload = {
            "suggestions": [
                _make_suggestion("Challenger"),
                _make_suggestion("Defender"),
                _make_suggestion("Arbiter"),
            ]
        }
        result = _clean_suggestions(payload)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Backward-compat
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    def test_valid_scenario_labels_still_defined(self):
        assert _VALID_SCENARIO_LABELS == ("Bull", "Bear", "Neutral")

    def test_scenario_suggest_system_prompt_is_string(self):
        assert isinstance(_SCENARIO_SUGGEST_SYSTEM_PROMPT, str)
        assert len(_SCENARIO_SUGGEST_SYSTEM_PROMPT) > 50

    def test_all_framework_ids_defined(self):
        expected = {"cerberus", "market", "decision", "crisis", "policy"}
        assert _VALID_FRAMEWORK_IDS == expected

    def test_all_frameworks_have_prompts(self):
        for fw_id in _VALID_FRAMEWORK_IDS:
            assert fw_id in _FRAMEWORK_PROMPTS
            assert len(_FRAMEWORK_PROMPTS[fw_id]) > 100

    def test_all_frameworks_have_three_labels(self):
        for fw_id, labels in _FRAMEWORK_LABELS.items():
            assert len(labels) == 3, f"Framework '{fw_id}' should have 3 labels"
