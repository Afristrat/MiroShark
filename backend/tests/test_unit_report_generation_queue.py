"""Durability contracts for strategic report generation."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.api.report import ReportQueueUnavailable, _enqueue_report_generation
from app.config import Config
from app.services.report_agent import ReportAgent


def test_report_generation_never_falls_back_to_gunicorn_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Config, "REDIS_URL", "")

    with pytest.raises(ReportQueueUnavailable):
        _enqueue_report_generation("report_task", {})


def test_report_route_has_no_background_thread() -> None:
    source = (Path(__file__).resolve().parents[1] / "app" / "api" / "report.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    generate = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "generate_report"
    )
    assert not any(
        isinstance(node, ast.Attribute) and node.attr == "Thread"
        for node in ast.walk(generate)
    )


def test_social_only_config_skips_prediction_market_generation() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "services"
        / "simulation_config_generator.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    generate = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "SimulationConfigGenerator"
    )
    method = next(
        node for node in generate.body if isinstance(node, ast.FunctionDef) and node.name == "generate_config"
    )
    guards = [
        node for node in ast.walk(method)
        if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "enable_polymarket"
    ]
    assert guards, "Market generation must be explicitly guarded by the arena flag"
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_generate_prediction_markets"
        for node in ast.walk(guards[0])
    )


def test_compose_worker_listens_to_report_generation_queue() -> None:
    compose = (Path(__file__).resolve().parents[2] / "docker-compose.yml").read_text(
        encoding="utf-8"
    )
    assert "report-generation" in compose


def test_report_sections_default_to_serial_generation() -> None:
    assert Config.REPORT_MAX_PARALLEL_SECTIONS == 1
    assert ReportAgent.MAX_PARALLEL_SECTIONS == 1


def test_parallel_runner_preflights_the_selected_model() -> None:
    source = (Path(__file__).resolve().parents[1] / "scripts" / "run_parallel_simulation.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    create_model = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "create_model"
    )
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_verify_model_available"
        for node in ast.walk(create_model)
    )


def test_twhin_runtime_never_downloads_model() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "wonderwall"
        / "social_platform"
        / "recsys.py"
    ).read_text(encoding="utf-8")
    assert source.count("local_files_only=True") >= 2


def test_docker_image_preloads_twhin_model() -> None:
    dockerfile = (Path(__file__).resolve().parents[2] / "Dockerfile").read_text(
        encoding="utf-8"
    )
    assert "Twitter/twhin-bert-base" in dockerfile
    assert "HF_HOME=/opt/huggingface" in dockerfile


def test_parallel_runner_limits_llm_concurrency() -> None:
    source = (Path(__file__).resolve().parents[1] / "scripts" / "run_parallel_simulation.py").read_text(
        encoding="utf-8"
    )
    assert "MIROSHARK_LLM_CONCURRENCY', '2'" in source
    assert "semaphore=60" not in source


def test_parallel_runner_allows_a_full_quality_first_round() -> None:
    source = (Path(__file__).resolve().parents[1] / "scripts" / "run_parallel_simulation.py").read_text(
        encoding="utf-8"
    )
    assert "MIROSHARK_ROUND_TIMEOUT', '1800'" in source


def test_parallel_runner_bounds_each_agent_response() -> None:
    source = (Path(__file__).resolve().parents[1] / "scripts" / "run_parallel_simulation.py").read_text(
        encoding="utf-8"
    )
    assert "MIROSHARK_AGENT_MAX_TOKENS', '1200'" in source
    assert '"max_tokens": _AGENT_MAX_TOKENS' in source


def test_twitter_recommender_defaults_to_lightweight_feed() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "wonderwall"
        / "simulations"
        / "social_media"
        / "__init__.py"
    ).read_text(encoding="utf-8")
    assert 'MIROSHARK_TWITTER_RECSYS", "random"' in source


def test_legacy_twitter_environment_uses_the_lightweight_feed_by_default() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "wonderwall"
        / "environment"
        / "env.py"
    ).read_text(encoding="utf-8")
    assert 'MIROSHARK_TWITTER_RECSYS", "random"' in source
    assert 'recsys_type="twhin-bert"' not in source
