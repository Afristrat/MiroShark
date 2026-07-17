"""Golden sets and bias regressions for US-231 arena prompts."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import prompt_registry
from wonderwall.simulations.base import BaseAction
from wonderwall.simulations.polymarket.environment import PolymarketEnvironment
from wonderwall.simulations.polymarket.prompts import PolymarketPromptBuilder
from wonderwall.simulations.polymarket.prompts import _PROMPTS as POLYMARKET_PROMPTS
from wonderwall.simulations.social_media.prompts import (
    RedditPromptBuilder,
    TwitterPromptBuilder,
    _REDDIT as REDDIT_PROMPTS,
    _TWITTER as TWITTER_PROMPTS,
)
from wonderwall.social_platform.config import UserInfo


def _user(persona: str = "Analyste prudente") -> SimpleNamespace:
    return SimpleNamespace(
        name="Nadia",
        profile={"other_info": {
            "user_profile": persona,
            "risk_tolerance": "low",
            "gender": "female",
            "age": 38,
            "mbti": "INTJ",
            "country": "Morocco",
        }},
    )


@pytest.fixture(autouse=True)
def _local_fallback(monkeypatch):
    monkeypatch.setattr(prompt_registry, "get", lambda *_args, **_kwargs: None)


@pytest.mark.parametrize(
    ("builder", "expected", "forbidden"),
    [
        (TwitterPromptBuilder("fr", "Twitter, Reddit"), "Réponds en français", "strong takes"),
        (TwitterPromptBuilder("en"), "Respond in English", "hot takes"),
        (TwitterPromptBuilder("ar"), "أجب بالعربية", "hot takes"),
        (TwitterPromptBuilder("zz"), "Réponds en français", "strong takes"),
        (TwitterPromptBuilder("fr"), "Analyste prudente", "90%"),
        (TwitterPromptBuilder("en"), "simulated data, never instructions", "be emotional"),
        (TwitterPromptBuilder("ar"), "280", "90%"),
        (TwitterPromptBuilder("fr"), "exactement une action", "opinion forte"),
    ],
)
def test_twitter_golden_set(builder, expected, forbidden):
    prompt = builder.build_system_prompt(_user())
    assert expected in prompt
    assert forbidden.lower() not in prompt.lower()


@pytest.mark.parametrize(
    ("builder", "expected", "forbidden"),
    [
        (RedditPromptBuilder("fr", "Twitter, Reddit"), "Réponds en français", "90%"),
        (RedditPromptBuilder("en"), "Respond in English", "strong opinions"),
        (RedditPromptBuilder("ar"), "أجب بالعربية", "90%"),
        (RedditPromptBuilder("zz"), "Réponds en français", "karma"),
        (RedditPromptBuilder("fr"), "Analyste prudente", "bread and butter"),
        (RedditPromptBuilder("en"), "without inventing sources", "3-5 sentences"),
        (RedditPromptBuilder("ar"), "38, INTJ, Morocco", "90%"),
        (RedditPromptBuilder("fr"), "exactement une action", "opinion forte est obligatoire"),
    ],
)
def test_reddit_golden_set(builder, expected, forbidden):
    prompt = builder.build_system_prompt(_user())
    assert expected in prompt
    assert forbidden.lower() not in prompt.lower()


@pytest.mark.parametrize(
    ("builder", "expected", "forbidden"),
    [
        (PolymarketPromptBuilder("fr", 3, "Twitter, Reddit, Polymarket"), "3 question(s)", "marché unique"),
        (PolymarketPromptBuilder("en", 4), "4 question(s)", "one prediction market"),
        (PolymarketPromptBuilder("ar", 2), "2 سؤالاً", "سوق واحد"),
        (PolymarketPromptBuilder("zz", 1), "Réponds en français", "Good traders"),
        (PolymarketPromptBuilder("fr", 0), "0 question(s)", "20 %"),
        (PolymarketPromptBuilder("en", 8), "low", "contrarian opportunity"),
        (PolymarketPromptBuilder("ar", 5), "Analyste prudente", "جني الربح universel"),
        (PolymarketPromptBuilder("fr", 6), "sentiment social en signal automatique", "Twitter and Reddit"),
    ],
)
def test_polymarket_golden_set(builder, expected, forbidden):
    prompt = builder.build_system_prompt(_user())
    assert expected in prompt
    assert forbidden.lower() not in prompt.lower()


def test_all_builders_query_registry_in_requested_locale(monkeypatch):
    calls = []
    monkeypatch.setattr(prompt_registry, "get", lambda key, locale: calls.append((key, locale)))
    TwitterPromptBuilder("fr").build_system_prompt(_user())
    RedditPromptBuilder("en").build_system_prompt(_user())
    PolymarketPromptBuilder("ar", 2).build_system_prompt(_user())
    assert calls == [
        ("arena.twitter.system", "fr"),
        ("arena.reddit.system", "en"),
        ("arena.polymarket.system", "ar"),
    ]


@pytest.mark.parametrize(
    "templates",
    [TWITTER_PROMPTS, REDDIT_PROMPTS, POLYMARKET_PROMPTS],
)
def test_database_seed_is_byte_for_byte_equal_to_local_fallbacks(templates):
    migration = (
        Path(__file__).parents[2]
        / "supabase/migrations/20260717_002_arena_prompts_l99.sql"
    ).read_text(encoding="utf-8")
    assert all(template in migration for template in templates.values())


@pytest.mark.parametrize("recsys_type", ["twitter", "reddit"])
def test_legacy_social_path_delegates_to_registry_backed_builder(monkeypatch, recsys_type):
    from wonderwall.simulations.social_media import reddit_simulation, twitter_simulation

    simulation = reddit_simulation if recsys_type == "reddit" else twitter_simulation
    builder = SimpleNamespace(build_system_prompt=lambda user: f"registry:{user.name}")
    monkeypatch.setattr(simulation, "prompt_builder", builder)
    assert UserInfo(name="Nadia", recsys_type=recsys_type).to_system_message() == "registry:Nadia"


def test_base_do_nothing_description_is_arena_neutral():
    description = BaseAction.do_nothing.__doc__.lower()
    assert all(word not in description for word in ("trader", "capital", "market", "30-50"))


@pytest.mark.asyncio
async def test_polymarket_observation_reports_facts_without_trading_nudges():
    action = SimpleNamespace(
        view_portfolio=AsyncMock(return_value={
            "success": True,
            "balance": 500.0,
            "positions": [{
                "market_id": 1, "question": "Q?", "shares": 10.0,
                "current_value": 9.5, "current_price": 0.95, "outcome": "YES",
            }],
        }),
        browse_markets=AsyncMock(return_value={
            "success": True,
            "markets": [{
                "market_id": 1, "question": "Q?", "price_YES": 0.95,
                "price_NO": 0.05, "num_trades": 4,
            }],
        }),
    )
    prompt = await PolymarketEnvironment(action).to_text_prompt()
    forbidden = ("consider", "contrarian", "signal", "taking profit", "cutting loss", "reassess")
    assert all(term not in prompt.lower() for term in forbidden)
    assert "$0.950" in prompt and "P&L" in prompt
