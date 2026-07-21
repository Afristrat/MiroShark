"""Provider capability checks for the OpenAI-compatible embedding client."""

from __future__ import annotations

from typing import Any

from app.storage.embedding_service import EmbeddingService


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}]}


def test_qwen_native_dimensions_omits_the_openai_dimensions_parameter(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def post(*_args: Any, **kwargs: Any) -> _Response:
        captured.update(kwargs["json"])
        return _Response()

    monkeypatch.setattr("app.storage.embedding_service.requests.post", post)
    service = EmbeddingService(
        provider="openai",
        model="qwen3-emb-8b",
        base_url="http://dgx-2:8004",
        dimensions=4096,
        request_dimensions=False,
    )

    assert service.embed("native dimension model") == [0.1, 0.2, 0.3]
    assert captured == {"model": "qwen3-emb-8b", "input": ["native dimension model"]}


def test_provider_that_supports_dimension_control_keeps_the_parameter(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def post(*_args: Any, **kwargs: Any) -> _Response:
        captured.update(kwargs["json"])
        return _Response()

    monkeypatch.setattr("app.storage.embedding_service.requests.post", post)
    service = EmbeddingService(
        provider="openai",
        model="text-embedding-3-large",
        base_url="https://example.invalid/v1",
        dimensions=1024,
        request_dimensions=True,
    )

    service.embed("dimension controllable model")

    assert captured["dimensions"] == 1024
