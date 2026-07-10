"""Wrapper d'intégration pour le corpus d'évaluation de l'agent (US-IQ-02).

Skip par défaut (cf. conftest.py) — run explicite avec `pytest -m
integration`. Nécessite LLM_API_KEY réel : ce test appelle le LLM pour de
vrai, ce n'est PAS un test unitaire.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.integration
def test_intake_agent_corpus_runs_without_crashing():
    script = Path(__file__).resolve().parent.parent / "scripts" / "test_intake_agent_corpus.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, timeout=300,
    )
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    assert result.returncode == 0
