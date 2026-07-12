"""Tests unitaires — recommandation de package self-service (US-IQ-02 frontend, Task 4).

Le client LLM est toujours un double en mémoire — aucun appel réseau réel.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services import intake_service as svc  # noqa: E402


class _FakeRecommendationLLM:
    def __init__(self, output: Dict[str, Any] | None = None, *, raises: bool = False):
        self._output = output
        self._raises = raises
        self.calls: List[Dict[str, Any]] = []

    def chat_json(self, messages, temperature=0.3, max_tokens=1024):
        self.calls.append({"messages": messages, "temperature": temperature, "max_tokens": max_tokens})
        if self._raises:
            raise RuntimeError("gateway down")
        return self._output


_BRIEF = {
    "decision": "Faut-il tester notre positionnement PMF avant la levée Série A ?",
    "options": ["Lever avant validation", "Valider le PMF d'abord"],
    "stakes": {"budget_bracket": "lt_1m", "exposure": "interne"},
}


class TestRecommendSelfServicePackage:
    def test_valid_recommendation_returned_as_is(self):
        llm = _FakeRecommendationLLM({"package_id": "pmf_discovery", "rationale": "Votre décision porte sur la validation PMF."})
        result = svc._recommend_self_service_package(_BRIEF, "fr", llm)
        assert result == {"package_id": "pmf_discovery", "rationale": "Votre décision porte sur la validation PMF."}
        assert len(llm.calls) == 1

    def test_invalid_package_id_falls_back(self):
        llm = _FakeRecommendationLLM({"package_id": "not_a_real_package", "rationale": "x"})
        result = svc._recommend_self_service_package(_BRIEF, "fr", llm)
        assert result["package_id"] == "crisis_drill_24h"
        assert result["rationale"] == ""

    def test_missing_rationale_falls_back(self):
        llm = _FakeRecommendationLLM({"package_id": "adcheck_lite"})
        result = svc._recommend_self_service_package(_BRIEF, "fr", llm)
        assert result["package_id"] == "crisis_drill_24h"

    def test_non_dict_output_falls_back(self):
        llm = _FakeRecommendationLLM("not a dict")
        result = svc._recommend_self_service_package(_BRIEF, "fr", llm)
        assert result["package_id"] == "crisis_drill_24h"

    def test_llm_exception_falls_back(self):
        llm = _FakeRecommendationLLM(raises=True)
        result = svc._recommend_self_service_package(_BRIEF, "fr", llm)
        assert result["package_id"] == "crisis_drill_24h"
        assert result["rationale"] == ""

    def test_no_llm_client_falls_back_without_calling_anything(self):
        result = svc._recommend_self_service_package(_BRIEF, "fr", None)
        assert result["package_id"] == "crisis_drill_24h"
        assert result["rationale"] == ""

    def test_prompt_lists_all_three_self_service_packages(self):
        llm = _FakeRecommendationLLM({"package_id": "crisis_drill_24h", "rationale": "x"})
        svc._recommend_self_service_package(_BRIEF, "fr", llm)
        system_content = llm.calls[0]["messages"][0]["content"]
        assert "pmf_discovery" in system_content
        assert "crisis_drill_24h" in system_content
        assert "adcheck_lite" in system_content

    def test_valid_package_ids_are_exactly_the_three_self_service_ones(self):
        assert svc._SELF_SERVICE_PACKAGES.keys() == {"pmf_discovery", "crisis_drill_24h", "adcheck_lite"}
