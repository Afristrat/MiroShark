"""Guard the OpenAI-compatible contract used by every simulation runner."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "script_name, factory_name",
    [
        ("run_parallel_simulation.py", "create_model"),
        ("run_twitter_simulation.py", "_create_model"),
        ("run_reddit_simulation.py", "_create_model"),
    ],
)
def test_runner_disables_native_tool_choice(script_name: str, factory_name: str):
    """Prevent unsupported ``tool_choice=auto`` requests to the 35B vLLM."""
    script = Path(__file__).resolve().parents[1] / "scripts" / script_name
    tree = ast.parse(script.read_text(encoding="utf-8"))

    factories = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "create"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "ModelFactory"
    ]
    assert factories, f"{script_name} does not call ModelFactory.create"

    matching = []
    for call in factories:
        config = next(
            (keyword.value for keyword in call.keywords if keyword.arg == "model_config_dict"),
            None,
        )
        if isinstance(config, ast.Dict):
            values = {
                key.value: value.value
                for key, value in zip(config.keys, config.values)
                if isinstance(key, ast.Constant) and isinstance(value, ast.Constant)
            }
            matching.append(values)

    assert {"tool_choice": "none"} in matching, (
        f"{script_name}:{factory_name} must disable native tool calling"
    )
