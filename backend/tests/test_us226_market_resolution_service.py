"""US-226 tranche C: durable ordering, idempotence and final wealth."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from types import SimpleNamespace

import pytest

from app.services.market_resolution_oracle import OracleResolution
from app.services.market_resolution_service import (
    MarketResolutionError,
    load_resolution_trajectory,
    resolve_all_markets,
)
from wonderwall.simulations.polymarket.platform import SYSTEM_SETTLEMENT_ACTOR


class _Query:
    def __init__(self, client, table):
        self.client, self.table, self.filters, self.operation, self.payload = client, table, {}, "select", None

    def select(self, _columns):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def limit(self, _count):
        return self

    def insert(self, payload):
        self.operation, self.payload = "insert", dict(payload)
        return self

    def update(self, payload):
        self.operation, self.payload = "update", dict(payload)
        return self

    def execute(self):
        if self.table == "simulation_ownership":
            rows = [row for row in self.client.ownership if all(row.get(k) == v for k, v in self.filters.items())]
            return SimpleNamespace(data=rows)
        rows = self.client.resolutions
        matched = [row for row in rows if all(row.get(k) == v for k, v in self.filters.items())]
        if self.operation == "select":
            return SimpleNamespace(data=[dict(row) for row in matched])
        if self.operation == "insert":
            self.client.events.append("insert")
            if self.client.fail_insert:
                raise RuntimeError("insert failed")
            if self.client.insert_data is not _USE_INSERTED_ROW:
                if self.client.insert_commits:
                    rows.append(self.payload)
                return SimpleNamespace(data=self.client.insert_data)
            if any(
                row["simulation_id"] == self.payload["simulation_id"] and row["market_id"] == self.payload["market_id"]
                for row in rows
            ):
                raise RuntimeError("duplicate")
            rows.append(self.payload)
            return SimpleNamespace(data=[dict(self.payload)])
        self.client.events.append("update")
        if self.client.update_data is not _USE_INSERTED_ROW:
            return SimpleNamespace(data=self.client.update_data)
        for row in matched:
            row.update(self.payload)
        return SimpleNamespace(data=[dict(row) for row in matched])


_USE_INSERTED_ROW = object()


class _Client:
    def __init__(self, *, ownership=True, existing=None, fail_insert=False, insert_data=_USE_INSERTED_ROW, insert_commits=False, update_data=_USE_INSERTED_ROW):
        self.ownership = [{"simulation_id": "sim-1", "org_id": "org-1"}] if ownership else []
        self.resolutions = [dict(existing)] if existing else []
        self.events, self.fail_insert = [], fail_insert
        self.insert_data, self.insert_commits, self.update_data = insert_data, insert_commits, update_data

    def table(self, name):
        return _Query(self, name)


class _Platform:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db_cursor = self.db.cursor()
        self.db_cursor.executescript(
            "CREATE TABLE market (market_id INTEGER PRIMARY KEY, question TEXT, outcome_a TEXT, outcome_b TEXT, resolution_spec TEXT, resolved INTEGER DEFAULT 0, winning_outcome TEXT, reserve_a REAL, reserve_b REAL);"
            "CREATE TABLE market_price_snapshot (market_id INTEGER, round INTEGER, price_yes REAL, reserve_a REAL, reserve_b REAL);"
            "CREATE TABLE portfolio (user_id INTEGER PRIMARY KEY, balance REAL);"
            "CREATE TABLE position (user_id INTEGER, market_id INTEGER, outcome TEXT, shares REAL);"
        )
        self.db_cursor.execute(
            "INSERT INTO market (market_id, question, outcome_a, outcome_b, resolution_spec, reserve_a, reserve_b) VALUES (1, 'Will it pass?', 'YES', 'NO', ?, 100, 100)",
            (json.dumps({"version": 1, "deadline_round": 1, "aggregation": "all", "criteria": [{"id": "c", "description": "d", "signal": "final_stances", "operator": "count_gte", "threshold": 1}], "invalid_conditions": [{"id": "i", "description": "d"}]}),),
        )
        self.db_cursor.execute("INSERT INTO market_price_snapshot VALUES (1, 0, .5, 100, 100)")
        self.db_cursor.execute("INSERT INTO portfolio VALUES (7, 12.34567)")
        self.db_cursor.execute("INSERT INTO position VALUES (7, 1, 'YES', 1.23456)")
        self.db.commit()
        self.calls = []

    async def resolve_market(self, actor, message):
        self.calls.append((actor, message))
        self.db_cursor.execute("UPDATE market SET resolved = 1, winning_outcome = 'YES' WHERE market_id = ?", (message[0],))
        self.db_cursor.execute("UPDATE portfolio SET balance = balance + 2 WHERE user_id = 7")
        self.db.commit()
        return {"success": True, "payout_summary": {"total_amount": 2.0, "recipient_count": 1, "recipients": [{"user_id": 7, "amount": 2.0}], "already_resolved": False}}

    async def view_portfolio(self, user_id):
        return {"success": True, "balance": 12.0, "positions": []}


_TRAJECTORY = {"snapshots": [{"round": 1, "final_stances": {"a": "support"}}]}


class _Oracle:
    def __init__(self, verdict="YES"):
        self.verdict, self.calls = verdict, []

    def __call__(self, market, trajectories, prices, events, *, locale):
        self.calls.append((market, trajectories, prices, events, locale))
        if self.verdict == "UNRESOLVED":
            return OracleResolution("UNRESOLVED", "technical", None, [], "oracle.resolution", 1)
        return OracleResolution(self.verdict, "round:1:0 evidence", 0.8, [{"round": 1, "type": "trajectory", "ref": "round:1:0"}], "oracle.resolution", 1)


def _durable_yes(platform: _Platform, **changes) -> dict:
    row = {
        "simulation_id": "sim-1",
        "market_id": 1,
        "org_id": "org-1",
        "verdict": "YES",
        "prompt_version": 1,
        "prompt_key": "oracle.resolution",
        "question": "Will it pass?",
        "resolution_spec": json.loads(
            platform.db_cursor.execute(
                "SELECT resolution_spec FROM market WHERE market_id = 1"
            ).fetchone()[0]
        ),
        "price_series": [{"round": 0, "price_yes": 0.5, "reserve_a": 100.0, "reserve_b": 100.0}],
        "justification": "round:1:0 evidence",
        "confidence": 0.8,
        "evidence": [{"round": 1, "type": "trajectory", "ref": "round:1:0"}],
        "payout_summary": {"status": "pending"},
    }
    row.update(changes)
    return row


def test_us226_inserts_durable_pending_before_sqlite_settlement() -> None:
    async def scenario():
        client, platform, oracle = _Client(), _Platform(), _Oracle()
        result = await resolve_all_markets("sim-1", platform=platform, trajectory_payload=_TRAJECTORY, config={"locale": "fr"}, client=client, oracle=oracle)
        assert client.events.index("insert") < len(platform.calls)
        assert platform.calls == [(SYSTEM_SETTLEMENT_ACTOR, (1, "YES"))]
        assert result[0]["status"] == "paid"
        assert result[0]["final_wealth"] == [{
            "user_id": 7,
            "cash_balance": 14.34567,
            "open_position_value": 0.0,
            "wealth": 14.34567,
            "complete": True,
        }]
        assert oracle.calls[0][0]["outcome_a"] == "YES"
        assert oracle.calls[0][0]["outcome_b"] == "NO"
        assert oracle.calls[0][1] == _TRAJECTORY

    asyncio.run(scenario())


def test_us226_loads_only_authoritative_merged_trajectory(tmp_path) -> None:
    merged = {
        "snapshots": [{
            "round_num": 1,
            "total_posts_created": 5,
            "belief_positions": {
                "twitter-1": {"policy": 0.5},
                "polymarket-1": {"policy": -0.5},
            },
        }]
    }
    (tmp_path / "trajectory.json").write_text(json.dumps(merged), encoding="utf-8")
    (tmp_path / "trajectory_polymarket.json").write_text(
        json.dumps({"snapshots": [{"round_num": 1, "total_posts_created": 1}]}),
        encoding="utf-8",
    )

    assert load_resolution_trajectory(str(tmp_path)) == merged


def test_us226_missing_merged_trajectory_never_falls_back_to_polymarket(tmp_path) -> None:
    (tmp_path / "trajectory_polymarket.json").write_text(
        json.dumps({"snapshots": [{"round_num": 1}]}),
        encoding="utf-8",
    )

    with pytest.raises(MarketResolutionError, match="merged simulation trajectory is unavailable"):
        load_resolution_trajectory(str(tmp_path))


def test_us226_insert_failure_prevents_sqlite_settlement() -> None:
    async def scenario():
        client, platform, oracle = _Client(fail_insert=True), _Platform(), _Oracle()
        with pytest.raises(MarketResolutionError):
            await resolve_all_markets("sim-1", platform=platform, trajectory_payload=_TRAJECTORY, config={}, client=client, oracle=oracle)
        assert platform.calls == []

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "corruption",
    [
        "UPDATE market SET question = ' ' WHERE market_id = 1",
        "UPDATE market SET outcome_b = outcome_a WHERE market_id = 1",
        "UPDATE market SET resolution_spec = '{}' WHERE market_id = 1",
    ],
)
def test_us226_load_markets_revalidates_question_outcomes_and_spec(corruption) -> None:
    async def scenario():
        client, platform, oracle = _Client(), _Platform(), _Oracle()
        with platform.db:
            platform.db_cursor.execute(corruption)

        with pytest.raises(MarketResolutionError):
            await resolve_all_markets(
                "sim-1",
                platform=platform,
                trajectory_payload=_TRAJECTORY,
                config={},
                client=client,
                oracle=oracle,
            )

        assert oracle.calls == []
        assert platform.calls == []

    asyncio.run(scenario())


@pytest.mark.parametrize("insert_data", [None, []])
def test_us226_insert_without_durable_row_proof_prevents_sqlite_settlement(insert_data) -> None:
    async def scenario():
        client, platform, oracle = _Client(insert_data=insert_data), _Platform(), _Oracle()
        with pytest.raises(MarketResolutionError, match="insert failed"):
            await resolve_all_markets("sim-1", platform=platform, trajectory_payload=_TRAJECTORY, config={}, client=client, oracle=oracle)
        assert platform.calls == []

    asyncio.run(scenario())


def test_us226_lost_insert_response_refetches_the_committed_durable_winner() -> None:
    async def scenario():
        client = _Client(insert_data=None, insert_commits=True)
        platform, oracle = _Platform(), _Oracle()

        result = await resolve_all_markets("sim-1", platform=platform, trajectory_payload=_TRAJECTORY, config={}, client=client, oracle=oracle)

        assert platform.calls == [(SYSTEM_SETTLEMENT_ACTOR, (1, "YES"))]
        assert result[0]["status"] == "paid"

    asyncio.run(scenario())


def test_us226_existing_pending_skips_oracle_and_replays_settlement() -> None:
    async def scenario():
        platform = _Platform()
        existing = _durable_yes(platform)
        client, oracle = _Client(existing=existing), _Oracle()
        await resolve_all_markets("sim-1", platform=platform, trajectory_payload=_TRAJECTORY, config={}, client=client, oracle=oracle)
        assert oracle.calls == []
        assert platform.calls == [(SYSTEM_SETTLEMENT_ACTOR, (1, "YES"))]

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("field", "divergent_value"),
    [
        ("question", "A different question"),
        ("resolution_spec", {"version": 1}),
        ("price_series", []),
        ("prompt_key", "oracle.other"),
        ("prompt_version", 0),
    ],
)
def test_us226_replay_divergence_never_reaches_payout(field, divergent_value) -> None:
    async def scenario():
        platform = _Platform()
        client = _Client(existing=_durable_yes(platform, **{field: divergent_value}))

        with pytest.raises(MarketResolutionError):
            await resolve_all_markets(
                "sim-1",
                platform=platform,
                trajectory_payload=_TRAJECTORY,
                config={},
                client=client,
                oracle=_Oracle(),
            )

        assert platform.calls == []
        balance = platform.db_cursor.execute(
            "SELECT balance FROM portfolio WHERE user_id = 7"
        ).fetchone()[0]
        assert balance == 12.34567

    asyncio.run(scenario())


def test_us226_replay_revalidates_evidence_against_reconstructed_digest_before_payout() -> None:
    async def scenario():
        platform = _Platform()
        client = _Client(existing=_durable_yes(
            platform,
            justification="round:99:0 evidence",
            evidence=[{"round": 99, "type": "trajectory", "ref": "round:99:0"}],
        ))

        with pytest.raises(MarketResolutionError, match="evidence"):
            await resolve_all_markets(
                "sim-1",
                platform=platform,
                trajectory_payload=_TRAJECTORY,
                config={},
                client=client,
                oracle=_Oracle(),
            )
        assert platform.calls == []

    asyncio.run(scenario())


def test_us226_unresolved_never_settles_and_marks_wealth_incomplete() -> None:
    async def scenario():
        client, platform, oracle = _Client(), _Platform(), _Oracle("UNRESOLVED")
        result = await resolve_all_markets("sim-1", platform=platform, trajectory_payload=_TRAJECTORY, config={}, client=client, oracle=oracle)
        assert platform.calls == []
        assert result[0]["status"] == "unresolved"
        assert result[0]["final_wealth"] == [{
            "user_id": 7,
            "cash_balance": 12.34567,
            "open_position_value": 0.61728,
            "wealth": 12.96295,
            "complete": False,
        }]

    asyncio.run(scenario())


def test_us226_resolved_sqlite_market_without_durable_row_fails_before_oracle_or_insert() -> None:
    async def scenario():
        client, platform, oracle = _Client(), _Platform(), _Oracle()
        platform.db_cursor.execute("UPDATE market SET resolved = 1, winning_outcome = 'YES' WHERE market_id = 1")
        platform.db.commit()

        with pytest.raises(MarketResolutionError, match="lacks durable"):
            await resolve_all_markets("sim-1", platform=platform, trajectory_payload=_TRAJECTORY, config={}, client=client, oracle=oracle)

        assert oracle.calls == []
        assert platform.calls == []
        assert client.events == []

    asyncio.run(scenario())


def test_us226_unresolved_durable_row_conflicting_with_sqlite_settlement_fails_closed() -> None:
    async def scenario():
        existing = {
            "simulation_id": "sim-1",
            "market_id": 1,
            "org_id": "org-1",
            "verdict": "UNRESOLVED",
            "prompt_version": 1,
            "payout_summary": {"status": "unresolved"},
        }
        client, platform, oracle = _Client(existing=existing), _Platform(), _Oracle()
        platform.db_cursor.execute("UPDATE market SET resolved = 1, winning_outcome = 'YES' WHERE market_id = 1")
        platform.db.commit()

        with pytest.raises(MarketResolutionError, match="conflicts"):
            await resolve_all_markets("sim-1", platform=platform, trajectory_payload=_TRAJECTORY, config={}, client=client, oracle=oracle)

        assert oracle.calls == []
        assert platform.calls == []

    asyncio.run(scenario())


def test_us226_missing_ownership_fails_closed_before_oracle_or_payout() -> None:
    async def scenario():
        client, platform, oracle = _Client(ownership=False), _Platform(), _Oracle()
        with pytest.raises(MarketResolutionError):
            await resolve_all_markets("sim-1", platform=platform, trajectory_payload=_TRAJECTORY, config={}, client=client, oracle=oracle)
        assert oracle.calls == []
        assert platform.calls == []

    asyncio.run(scenario())


@pytest.mark.parametrize("update_data", [None, []])
def test_us226_payout_update_without_exact_durable_row_fails_closed(update_data) -> None:
    async def scenario():
        client, platform, oracle = _Client(update_data=update_data), _Platform(), _Oracle()
        with pytest.raises(MarketResolutionError, match="payout update was rejected"):
            await resolve_all_markets("sim-1", platform=platform, trajectory_payload=_TRAJECTORY, config={}, client=client, oracle=oracle)

        assert platform.calls == [(SYSTEM_SETTLEMENT_ACTOR, (1, "YES"))]

    asyncio.run(scenario())
