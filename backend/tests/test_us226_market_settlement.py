"""US-226 tranche B: atomic SQLite settlement and real portfolio cost basis."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from wonderwall.simulations.polymarket.environment import PolymarketEnvironment
from wonderwall.simulations.polymarket.platform import (
    SYSTEM_SETTLEMENT_ACTOR,
    PolymarketPlatform,
)


def _platform(tmp_path) -> PolymarketPlatform:
    platform = PolymarketPlatform(str(tmp_path / "polymarket.db"))
    with platform.db:
        platform.db_cursor.executemany(
            "INSERT INTO portfolio (user_id, balance) VALUES (?, ?)",
            [(1, 100.0), (2, 10.0), (3, 10.0)],
        )
    return platform


def _market(platform: PolymarketPlatform, *, creator_id: int = 1, resolved: int = 0) -> int:
    with platform.db:
        platform.db_cursor.execute(
            "INSERT INTO market (creator_id, question, outcome_a, outcome_b, reserve_a, reserve_b, "
            "resolution_spec, resolved, created_at) VALUES (?, ?, 'YES', 'NO', 100, 100, '{}', ?, 'now')",
            (creator_id, "Will the proposal pass?", resolved),
        )
        return platform.db_cursor.lastrowid


def _balance(platform: PolymarketPlatform, user_id: int) -> float:
    return platform.db_cursor.execute(
        "SELECT balance FROM portfolio WHERE user_id = ?", (user_id,)
    ).fetchone()[0]


def test_us226_yes_pays_winners_and_replay_is_idempotent(tmp_path) -> None:
    async def scenario() -> None:
        platform = _platform(tmp_path)
        market_id = _market(platform)
        with platform.db:
            platform.db_cursor.executemany(
                "INSERT INTO position (user_id, market_id, outcome, shares) VALUES (?, ?, ?, ?)",
                [(2, market_id, "YES", 3.25), (3, market_id, "NO", 4.0)],
            )

        first = await platform.resolve_market(SYSTEM_SETTLEMENT_ACTOR, (market_id, "YES"))
        assert first["success"] is True
        assert first["already_resolved"] is False
        assert first["payout_summary"] == {
            "status": "resolved",
            "settlement_type": "payout",
            "verdict": "YES",
            "total_amount": 3.25,
            "recipient_count": 1,
            "recipients": [{"user_id": 2, "amount": 3.25}],
            "already_resolved": False,
        }
        assert _balance(platform, 2) == 13.25
        assert _balance(platform, 3) == 10.0

        replay = await platform.resolve_market(SYSTEM_SETTLEMENT_ACTOR, (market_id, "YES"))
        assert replay["success"] is True
        assert replay["already_resolved"] is True
        assert replay["payout_summary"]["total_amount"] == 3.25
        assert _balance(platform, 2) == 13.25

    asyncio.run(scenario())


def test_us226_invalid_refunds_real_net_cost_including_sell(tmp_path) -> None:
    async def scenario() -> None:
        platform = _platform(tmp_path)
        market_id = _market(platform)
        with platform.db:
            platform.db_cursor.execute("UPDATE portfolio SET balance = 94.5 WHERE user_id = 2")
            platform.db_cursor.execute(
                "INSERT INTO position (user_id, market_id, outcome, shares) VALUES (2, ?, 'YES', 5)",
                (market_id,),
            )
            platform.db_cursor.executemany(
                "INSERT INTO trade (user_id, market_id, side, outcome, shares, price, cost, created_at) "
                "VALUES (2, ?, ?, 'YES', ?, ?, ?, 'now')",
                [
                    (market_id, "buy", 10.0, 0.73, 10.0),
                    (market_id, "sell", 5.0, 0.90, -4.5),
                ],
            )

        result = await platform.resolve_market(SYSTEM_SETTLEMENT_ACTOR, (market_id, "INVALID"))
        assert result["winning_outcome"] == "INVALID"
        assert result["payout_summary"]["settlement_type"] == "void_refund"
        assert result["payout_summary"]["recipients"] == [{"user_id": 2, "amount": 5.5}]
        assert _balance(platform, 2) == 100.0

    asyncio.run(scenario())


def test_us226_invalid_refund_credits_sqlite_sum_without_pre_rounding(tmp_path) -> None:
    async def scenario() -> None:
        platform = _platform(tmp_path)
        market_id = _market(platform)
        costs = (0.123456789012345, 0.000000000000009)
        with platform.db:
            platform.db_cursor.executemany(
                "INSERT INTO trade (user_id, market_id, side, outcome, shares, price, cost, created_at) "
                "VALUES (2, ?, 'buy', 'YES', 1, 0.5, ?, 'now')",
                [(market_id, cost) for cost in costs],
            )
        sqlite_sum = platform.db_cursor.execute(
            "SELECT SUM(cost) FROM trade WHERE user_id = 2 AND market_id = ?",
            (market_id,),
        ).fetchone()[0]
        initial_balance = _balance(platform, 2)

        result = await platform.resolve_market(SYSTEM_SETTLEMENT_ACTOR, (market_id, "INVALID"))

        assert result["payout_summary"]["recipients"] == [{"user_id": 2, "amount": sqlite_sum}]
        assert _balance(platform, 2) == initial_balance + sqlite_sum

    asyncio.run(scenario())


def test_us226_conflicting_verdict_fails_closed_and_creator_permission_is_preserved(tmp_path) -> None:
    async def scenario() -> None:
        platform = _platform(tmp_path)
        market_id = _market(platform)
        denied = await platform.resolve_market(2, (market_id, "YES"))
        assert denied == {"success": False, "error": "Only the creator can resolve"}
        assert _balance(platform, 2) == 10.0
        assert platform.db_cursor.execute(
            "SELECT resolved, winning_outcome FROM market WHERE market_id = ?", (market_id,)
        ).fetchone() == (0, None)
        none_actor = await platform.resolve_market(None, (market_id, "YES"))
        assert none_actor == {"success": False, "error": "Only the creator can resolve"}

        accepted = await platform.resolve_market(1, (market_id, "YES"))
        assert accepted["success"] is True
        conflict = await platform.resolve_market(SYSTEM_SETTLEMENT_ACTOR, (market_id, "NO"))
        assert conflict == {"success": False, "error": "Conflicting settlement verdict"}
        unresolved_market = _market(platform)
        unresolved = await platform.resolve_market(SYSTEM_SETTLEMENT_ACTOR, (unresolved_market, "UNRESOLVED"))
        assert unresolved == {"success": False, "error": "UNRESOLVED cannot be settled"}
        assert platform.db_cursor.execute(
            "SELECT resolved FROM market WHERE market_id = ?", (unresolved_market,)
        ).fetchone()[0] == 0

    asyncio.run(scenario())


def test_us226_missing_recipient_portfolio_rolls_back_every_credit(tmp_path) -> None:
    async def scenario() -> None:
        platform = _platform(tmp_path)
        market_id = _market(platform)
        with platform.db:
            platform.db_cursor.executemany(
                "INSERT INTO position (user_id, market_id, outcome, shares) VALUES (?, ?, 'YES', ?)",
                [(2, market_id, 2.0), (999, market_id, 4.0)],
            )

        result = await platform.resolve_market(SYSTEM_SETTLEMENT_ACTOR, (market_id, "YES"))
        assert result == {"success": False, "error": "Settlement transaction failed"}
        assert _balance(platform, 2) == 10.0
        assert platform.db_cursor.execute(
            "SELECT resolved, winning_outcome FROM market WHERE market_id = ?", (market_id,)
        ).fetchone() == (0, None)

    asyncio.run(scenario())


def test_us226_portfolio_uses_real_cost_basis_and_hides_resolved_positions(tmp_path) -> None:
    async def scenario() -> None:
        platform = _platform(tmp_path)
        open_market = _market(platform)
        resolved_market = _market(platform)
        with platform.db:
            platform.db_cursor.executemany(
                "INSERT INTO position (user_id, market_id, outcome, shares) VALUES (2, ?, 'YES', 3)",
                [(open_market,), (resolved_market,)],
            )
            platform.db_cursor.executemany(
                "INSERT INTO trade (user_id, market_id, side, outcome, shares, price, cost, created_at) "
                "VALUES (2, ?, ?, 'YES', ?, ?, ?, 'now')",
                [
                    (open_market, "buy", 4.0, 0.73, 10.0),
                    (open_market, "sell", 1.0, 0.80, -2.5),
                ],
            )
            platform.db_cursor.execute(
                "UPDATE market SET resolved = 1, winning_outcome = 'YES' WHERE market_id = ?",
                (resolved_market,),
            )

        portfolio = await platform.view_portfolio(2)
        assert portfolio["positions"] == [
            {
                "market_id": open_market,
                "question": "Will the proposal pass?",
                "outcome": "YES",
                "shares": 3.0,
                "current_price": 0.5,
                "current_value": 1.5,
                "cost_basis": 7.5,
            }
        ]

    asyncio.run(scenario())


def test_us226_environment_uses_position_cost_basis() -> None:
    async def scenario() -> None:
        async def view_portfolio():
            return {
                "success": True,
                "balance": 100.0,
                "positions": [{
                    "market_id": 1,
                    "question": "Q?",
                    "shares": 10.0,
                    "outcome": "YES",
                    "current_price": 0.95,
                    "current_value": 9.5,
                    "cost_basis": 7.5,
                }],
            }

        async def browse_markets():
            return {"success": True, "markets": []}

        prompt = await PolymarketEnvironment(
            SimpleNamespace(view_portfolio=view_portfolio, browse_markets=browse_markets)
        ).to_text_prompt()
        assert "P&L: +2.00" in prompt
        assert "P&L: +4.50" not in prompt

    asyncio.run(scenario())
