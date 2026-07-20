import pytest

from app.config import Config
from app.utils.llm_client import LLMClient


class _Completions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = type("Message", (), {"content": "ok"})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


class _Client:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": _Completions()})()


def _client(monkeypatch, override: str) -> LLMClient:
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setattr(Config, "LLM_MODEL_NAME", "test-model")
    monkeypatch.setattr(Config, "LLM_TEMPERATURE_OVERRIDE", override)
    monkeypatch.setattr("app.utils.llm_client.OpenAI", lambda **_: _Client())
    return LLMClient()


def test_temperature_override_wins_over_caller_value(monkeypatch):
    client = _client(monkeypatch, "1")

    assert client.chat([{"role": "user", "content": "hello"}], temperature=0.3) == "ok"
    assert client.client.chat.completions.kwargs["temperature"] == 1.0


def test_invalid_temperature_override_fails_closed(monkeypatch):
    with pytest.raises(ValueError, match="LLM_TEMPERATURE_OVERRIDE"):
        _client(monkeypatch, "invalid")
