"""US-226 runner ordering contract, checked without starting a simulation."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest


_RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "run_parallel_simulation.py"


def _function(tree: ast.Module, name: str) -> ast.AsyncFunctionDef:
    return next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == name)


def _call_lines(function: ast.AsyncFunctionDef, expression: str) -> list[int]:
    return [
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and ast.unparse(node.func) == expression
    ]


def _awaited_call_lines(function: ast.AsyncFunctionDef, expression: str) -> list[int]:
    return [
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Await)
        and isinstance(node.value, ast.Call)
        and ast.unparse(node.value.func) == expression
    ]


def _resolution_events_helper():
    tree = ast.parse(_RUNNER.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_resolution_events"
    )
    namespace = {"json": json, "os": __import__("os")}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(_RUNNER), "exec"), namespace)
    return namespace["_resolution_events"]


def test_us226_standalone_resolution_follows_trajectory_and_precedes_end_log() -> None:
    source = _RUNNER.read_text(encoding="utf-8")
    function = _function(ast.parse(source), "run_polymarket_simulation")

    saved = _call_lines(function, "belief_tracker.save_trajectory")
    resolved = _awaited_call_lines(function, "resolve_all_markets")
    ended = _call_lines(function, "action_logger.log_simulation_end")

    assert len(saved) == len(resolved) == len(ended) == 1
    assert saved[0] < resolved[0] < ended[0]


def test_us226_sync_resolution_runs_once_after_all_trajectories_and_before_end_logs() -> None:
    source = _RUNNER.read_text(encoding="utf-8")
    function = _function(ast.parse(source), "run_synchronized_simulation")

    saved = _call_lines(function, "tracker.save_trajectory")
    resolved = _awaited_call_lines(function, "resolve_all_markets")
    ended = _call_lines(function, "logger.log_simulation_end")

    assert len(saved) == len(resolved) == 1
    assert len(ended) == 1
    assert saved[0] < resolved[0] < ended[0]


def test_us226_runner_uses_explicit_or_validated_directory_simulation_id() -> None:
    source = _RUNNER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    helper = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_resolution_simulation_id")
    calls = [ast.unparse(node.func) for node in ast.walk(helper) if isinstance(node, ast.Call)]

    assert "os.environ.get" in calls
    assert "os.path.basename" in calls
    assert "validate_simulation_id" in calls


def test_us226_runner_does_not_swallow_resolution_failure_before_end_logging() -> None:
    tree = ast.parse(_RUNNER.read_text(encoding="utf-8"))
    for function_name in ("run_polymarket_simulation", "run_synchronized_simulation"):
        function = _function(tree, function_name)
        protected_calls = [
            ast.unparse(call.func)
            for handler in ast.walk(function)
            if isinstance(handler, ast.Try)
            for call in ast.walk(handler)
            if isinstance(call, ast.Call)
        ]
        assert "resolve_all_markets" not in protected_calls


def test_us226_social_runners_have_no_undefined_resolution_events_reference() -> None:
    tree = ast.parse(_RUNNER.read_text(encoding="utf-8"))

    for function_name in ("run_twitter_simulation", "run_reddit_simulation"):
        function = _function(tree, function_name)
        assert "injected_events" not in {
            node.id for node in ast.walk(function) if isinstance(node, ast.Name)
        }


def test_us226_sync_uses_promoted_counterfactual_without_a_runtime_duplicate(tmp_path: Path) -> None:
    function = _function(ast.parse(_RUNNER.read_text(encoding="utf-8")), "run_synchronized_simulation")
    resolution_calls = [
        call
        for call in ast.walk(function)
        if isinstance(call, ast.Call) and ast.unparse(call.func) == "resolve_all_markets"
    ]

    consumed = _call_lines(function, "consume_pending_events")
    assert len(consumed) == 1
    assert "injected_events" not in {
        node.id for node in ast.walk(function) if isinstance(node, ast.Name)
    }
    assert not any("trigger_round" in ast.unparse(node.test) for node in ast.walk(function) if isinstance(node, ast.If))
    assert len(resolution_calls) == 1
    assert consumed[0] < resolution_calls[0].lineno
    assert any(
        keyword.arg == "injected_events"
        and ast.unparse(keyword.value) == "_resolution_events(simulation_dir, [])"
        for keyword in resolution_calls[0].keywords
    )

    event = {"injected_at_round": 3, "event_text": "[COUNTERFACTUAL] shock: text"}
    (tmp_path / "director_events_history.json").write_text(json.dumps([event]), encoding="utf-8")
    assert _resolution_events_helper()(str(tmp_path), []) == [
        {"round": 3, "source": "director", "content": event["event_text"]}
    ]


def test_us226_resolution_events_reject_malformed_runtime_events(tmp_path: Path) -> None:
    resolution_events = _resolution_events_helper()

    with pytest.raises(RuntimeError, match="runtime injected event"):
        resolution_events(str(tmp_path), [{"round": True, "source": "counterfactual", "content": "x"}])
