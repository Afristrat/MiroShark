"""US-225 golden set: the deterministic market-contract validator is the gate."""

from __future__ import annotations

import asyncio
import ast
from copy import deepcopy
from pathlib import Path
import re

import pytest

from app.services import simulation_config_generator as generator_module
from app.services.simulation_config_generator import (
    EventConfig,
    SimulationConfigGenerator,
    _MARKET_GENERATION_PROMPT,
    _validate_generated_markets,
)
from wonderwall.simulations.polymarket.platform import PolymarketPlatform


def _market(signal: str = "final_stances", operator: str = "count_gte") -> dict:
    return {
        "question": "Will the simulated coalition support the proposal?",
        "outcome_a": "YES",
        "outcome_b": "NO",
        "initial_probability": 0.62,
        "reasoning": "The scenario contains credible support and opposition.",
        "resolution_spec": {
            "version": 1,
            "deadline_round": 4,
            "aggregation": "all",
            "criteria": [{
                "id": "support_threshold",
                "description": "At least three final stances support the proposal.",
                "signal": signal,
                "operator": operator,
                "threshold": 3,
            }],
            "invalid_conditions": [{
                "id": "missing_final_state",
                "description": "The required final state was not recorded.",
            }],
        },
    }


def _result(market: dict | None = None) -> dict:
    return {"markets": [market or _market()]}


@pytest.mark.parametrize(
    "name, payload, valid",
    [
        ("final_stances", _result(_market()), True),
        ("contents", _result(_market("contents", "count_gte")), True),
        ("trajectory", _result(_market("trajectory", "delta_lte")), True),
        ("events", _result(_market("events", "count_lte")), True),
        ("duplicate_criterion_id", _result(), False),
        ("incompatible_operator", _result(_market("events", "delta_gte")), False),
        ("missing_invalid_conditions", _result(), False),
        ("non_yes_no_outcome", _result(), False),
    ],
)
def test_us225_market_contract_golden_set(name: str, payload: dict, valid: bool) -> None:
    """Eight executable nominal/adversarial cases for the actual validator."""
    candidate = deepcopy(payload)
    spec = candidate["markets"][0]["resolution_spec"]
    if name == "duplicate_criterion_id":
        spec["criteria"].append(deepcopy(spec["criteria"][0]))
    elif name == "missing_invalid_conditions":
        spec["invalid_conditions"] = []
    elif name == "non_yes_no_outcome":
        candidate["markets"][0]["outcome_b"] = "MAYBE"

    if valid:
        assert _validate_generated_markets(candidate, 1, 4) == candidate["markets"]
    else:
        with pytest.raises(ValueError):
            _validate_generated_markets(candidate, 1, 4)


class _SequenceLLM:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    def chat_json(self, *, messages: list[dict], temperature: float) -> dict:
        self.calls.append({"messages": messages, "temperature": temperature})
        return self.responses.pop(0)


def _generator_with(responses: list[dict]) -> tuple[SimulationConfigGenerator, _SequenceLLM]:
    generator = object.__new__(SimulationConfigGenerator)
    llm = _SequenceLLM(responses)
    generator.smart_llm = llm
    return generator, llm


def test_us225_retries_invalid_contract_then_uses_valid_registry_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    invalid = _result()
    invalid["markets"][0]["resolution_spec"]["criteria"] = []
    generator, llm = _generator_with([invalid, _result()])
    resolved: list[tuple[str, str]] = []

    def registry_get(key: str, locale: str) -> str:
        resolved.append((key, locale))
        return "locale={locale_name}; count={market_count}; rounds={total_rounds}"

    monkeypatch.setattr(generator_module.prompt_registry, "get", registry_get)
    markets = generator._generate_prediction_markets(
        "context", "requirement", EventConfig(hot_topics=["topic"]),
        total_rounds=4, locale="ar",
    )

    assert len(markets) == 1
    assert resolved == [("config.market_generation", "ar")]
    assert len(llm.calls) == 2
    assert llm.calls[0]["temperature"] == 0.2
    assert "locale=Arabic; count=1; rounds=4" in llm.calls[0]["messages"][0]["content"]


def test_us225_fails_closed_after_bounded_invalid_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    invalid = _result()
    invalid["markets"][0]["outcome_a"] = "MAYBE"
    generator, llm = _generator_with([deepcopy(invalid), deepcopy(invalid)])
    monkeypatch.setattr(generator_module.prompt_registry, "get", lambda *_: None)

    with pytest.raises(RuntimeError, match="failed after 2 attempts"):
        generator._generate_prediction_markets("context", "requirement", EventConfig(), total_rounds=4)
    assert len(llm.calls) == 2


def test_us225_retry_generation_propagates_state_locale() -> None:
    """The retry route must retain the locale for generation and persisted config."""
    source = (Path(__file__).resolve().parents[1] / "app" / "api" / "simulation.py").read_text(
        encoding="utf-8"
    )
    calls = [
        node for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "generate_config"
    ]
    assert any(
        any(
            keyword.arg == "locale"
            and isinstance(keyword.value, ast.Attribute)
            and keyword.value.attr == "locale"
            for keyword in call.keywords
        )
        for call in calls
    )
    retry = next(
        node for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.FunctionDef) and node.name == "run_config_retry"
    )
    assignments = [node for node in ast.walk(retry) if isinstance(node, ast.Assign)]
    assert any(
        ast.unparse(assignment.targets[0]) == "config_data['locale']"
        and ast.unparse(assignment.value) == "state.locale"
        for assignment in assignments
    )
    assert any(
        isinstance(node, ast.Call)
        and ast.unparse(node.func) == "json.dump"
        and node.args
        and ast.unparse(node.args[0]) == "config_data"
        for node in ast.walk(retry)
    )


def test_us225_sqlite_propagates_contract_and_snapshots_are_idempotent(tmp_path: Path) -> None:
    asyncio.run(_assert_sqlite_contract_and_snapshots(tmp_path))


async def _assert_sqlite_contract_and_snapshots(tmp_path: Path) -> None:
    platform = PolymarketPlatform(str(tmp_path / "polymarket.db"))
    resolution_spec = _market()["resolution_spec"]

    created = await platform.create_market(1, ("Will the proposal pass?", "YES", "NO", 0.63, resolution_spec))
    assert created["success"] is True
    market_id = created["market_id"]
    assert platform.db_cursor.execute(
        "SELECT resolution_spec FROM market WHERE market_id = ?", (market_id,)
    ).fetchone()[0] == '{"aggregation":"all","criteria":[{"description":"At least three final stances support the proposal.","id":"support_threshold","operator":"count_gte","signal":"final_stances","threshold":3}],"deadline_round":4,"invalid_conditions":[{"description":"The required final state was not recorded.","id":"missing_final_state"}],"version":1}'

    platform.tick_clock()
    first_snapshot = platform.db_cursor.execute(
        "SELECT round, price_yes, reserve_a, reserve_b FROM market_price_snapshot"
    ).fetchone()
    assert first_snapshot[0] == 0
    assert first_snapshot[1] == pytest.approx(0.63)

    platform.sandbox_clock.time_step -= 1
    platform.tick_clock()
    assert platform.db_cursor.execute("SELECT COUNT(*) FROM market_price_snapshot").fetchone()[0] == 1

    platform.tick_clock()
    assert platform.db_cursor.execute("SELECT COUNT(*) FROM market_price_snapshot").fetchone()[0] == 2
    assert platform.db_cursor.execute(
        "SELECT COUNT(*) FROM market_price_snapshot WHERE round = 1"
    ).fetchone()[0] == 1

    rejected = await platform.create_market(1, ("Uncontracted market", "YES", "NO", 0.5))
    assert rejected == {"success": False, "error": "resolution_spec is required"}

    malformed = await platform.create_market(1, ("Malformed market", "YES", "NO", 0.5, {}))
    assert malformed == {
        "success": False,
        "error": "resolution_spec has missing or unexpected fields",
    }

    malformed_type_specs = (
        ("aggregation", "resolution_spec.aggregation must be all or any"),
        ("signal", "resolution_spec criterion signal is not supported"),
        ("operator", "resolution_spec criterion operator is incompatible with signal"),
    )
    for field, expected_error in malformed_type_specs:
        malformed_type = deepcopy(resolution_spec)
        if field == "aggregation":
            malformed_type[field] = []
        else:
            malformed_type["criteria"][0][field] = []
        rejected_type = await platform.create_market(
            1, (f"Malformed {field}", "YES", "NO", 0.5, malformed_type)
        )
        assert rejected_type == {"success": False, "error": expected_error}
    assert platform.db_cursor.execute("SELECT COUNT(*) FROM market").fetchone()[0] == 1


def test_us225_parallel_seeds_and_resume_clock_are_wired() -> None:
    """Both runner modes preserve the generated contract and resume round index."""
    source = (Path(__file__).resolve().parents[1] / "scripts" / "run_parallel_simulation.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    seed_actions = []
    resume_assignments = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = ast.unparse(node.targets[0])
            if target.endswith("sandbox_clock.time_step") and ast.unparse(node.value) == "start_round":
                resume_assignments += 1
        if not isinstance(node, ast.Call) or ast.unparse(node.func) != "ManualAction":
            continue
        keywords = {keyword.arg: keyword.value for keyword in node.keywords}
        if not (
            isinstance(keywords.get("action_type"), ast.Constant)
            and keywords["action_type"].value == "create_market"
            and isinstance(keywords.get("action_args"), ast.Dict)
        ):
            continue
        action_args = keywords["action_args"]
        seed_actions.append({
            key.value for key in action_args.keys if isinstance(key, ast.Constant)
        })

    assert sum({"initial_probability", "resolution_spec"}.issubset(args) for args in seed_actions) == 2
    assert resume_assignments == 2


def test_us225_prompt_seed_matches_fallback_for_all_locales() -> None:
    """The immutable SQL seed cannot drift from the offline L99 fallback."""
    migration = (
        Path(__file__).resolve().parents[2]
        / "supabase"
        / "migrations"
        / "20260718_001_market_generation_prompt.sql"
    ).read_text(encoding="utf-8")
    templates = re.findall(r"\$prompt\$(.*?)\$prompt\$", migration, flags=re.DOTALL)

    assert templates == [_MARKET_GENERATION_PROMPT]
    assert "cross join (values ('fr'), ('en'), ('ar')) as locales(locale)" in migration
    assert "'[\"market_count\", \"total_rounds\", \"locale_name\"]'::jsonb" in migration
    assert "'config.market_generation'" in migration
    assert "on conflict (key, locale, version) do nothing" in migration
