"""Contrats de durabilité de la préparation de simulation."""

from __future__ import annotations

import pytest

from app.api.simulation import (
    SimulationQueueUnavailable,
    _enqueue_config_retry,
    _enqueue_simulation_preparation,
    _get_rq_prepare_status,
)
from app.config import Config
from app.services.wonderwall_profile_generator import WonderwallProfileGenerator
from app.api.graph import _enqueue_graph_build


def test_preparation_never_falls_back_to_a_gunicorn_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sans Redis, l'API échoue explicitement au lieu de créer un thread volatile."""
    monkeypatch.setattr(Config, "REDIS_URL", "")

    with pytest.raises(SimulationQueueUnavailable):
        _enqueue_simulation_preparation("task-1", {})


def test_prepare_status_skips_rq_when_redis_is_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Config, "REDIS_URL", "")

    assert _get_rq_prepare_status("task-1") is None


def test_config_retry_never_falls_back_to_a_gunicorn_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Config, "REDIS_URL", "")

    with pytest.raises(SimulationQueueUnavailable):
        _enqueue_config_retry("task-1", {})


def test_graph_build_never_falls_back_to_a_gunicorn_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Config, "REDIS_URL", "")

    with pytest.raises(RuntimeError, match="file de construction"):
        _enqueue_graph_build("task-1", {})


def test_profile_generator_uses_the_bounded_profile_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_client(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("app.services.wonderwall_profile_generator.create_llm_client", fake_client)
    monkeypatch.setattr(Config, "PROFILE_LLM_TIMEOUT_SECONDS", 17.0)

    WonderwallProfileGenerator(model_name="simulation-model")

    assert captured["timeout"] == 17.0
    assert captured["model"] == "simulation-model"
