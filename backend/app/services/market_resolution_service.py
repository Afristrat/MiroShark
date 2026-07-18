"""Durable orchestration of Oracle adjudication and SQLite settlement (US-226)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from ..auth.supabase_client import get_supabase_admin
from ..utils.logger import get_logger
from . import market_resolution_oracle
from wonderwall.simulations.polymarket.amm import get_prices
from wonderwall.simulations.polymarket.platform import SYSTEM_SETTLEMENT_ACTOR
from wonderwall.simulations.polymarket.resolution_spec import validate_resolution_spec

logger = get_logger("miroshark.services.market_resolution_service")


class MarketResolutionError(RuntimeError):
    """Fail-closed boundary for durable resolution and settlement."""


def _rows(response: Any) -> List[Dict[str, Any]]:
    data = getattr(response, "data", None)
    return data if isinstance(data, list) else []


def _require_org_id(client: Any, simulation_id: str) -> str:
    rows = _rows(
        client.table("simulation_ownership")
        .select("org_id")
        .eq("simulation_id", simulation_id)
        .limit(1)
        .execute()
    )
    if len(rows) != 1 or not isinstance(rows[0].get("org_id"), str) or not rows[0]["org_id"]:
        raise MarketResolutionError("simulation ownership is unavailable")
    return rows[0]["org_id"]


def _existing_resolution(client: Any, simulation_id: str, market_id: int, org_id: str) -> Optional[Dict[str, Any]]:
    rows = _rows(
        client.table("market_resolutions")
        .select("*")
        .eq("simulation_id", simulation_id)
        .eq("market_id", market_id)
        .limit(1)
        .execute()
    )
    if not rows:
        return None
    if rows[0].get("org_id") != org_id:
        raise MarketResolutionError("market resolution ownership mismatch")
    return rows[0]


def _load_markets(platform: Any) -> List[Dict[str, Any]]:
    rows = platform.db_cursor.execute(
        "SELECT market_id, question, outcome_a, outcome_b, resolution_spec, resolved, winning_outcome "
        "FROM market ORDER BY market_id"
    ).fetchall()
    markets = []
    for market_id, question, outcome_a, outcome_b, resolution_spec_json, resolved, winning_outcome in rows:
        if not isinstance(market_id, int) or isinstance(market_id, bool) or market_id <= 0:
            raise MarketResolutionError("market identifier is invalid")
        try:
            resolution_spec = json.loads(resolution_spec_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise MarketResolutionError("market resolution contract is invalid") from exc
        if not isinstance(resolution_spec, dict):
            raise MarketResolutionError("market resolution contract is invalid")
        try:
            validate_resolution_spec(resolution_spec)
        except ValueError as exc:
            raise MarketResolutionError("market resolution contract is invalid") from exc
        if not isinstance(question, str) or not question.strip():
            raise MarketResolutionError("market question is invalid")
        if not isinstance(outcome_a, str) or not outcome_a.strip() or not isinstance(outcome_b, str) or not outcome_b.strip() or outcome_a == outcome_b:
            raise MarketResolutionError("market outcomes are invalid")
        prices = platform.db_cursor.execute(
            "SELECT round, price_yes, reserve_a, reserve_b FROM market_price_snapshot "
            "WHERE market_id = ? ORDER BY round",
            (market_id,),
        ).fetchall()
        markets.append({
            "market_id": market_id,
            "question": question,
            "outcome_a": outcome_a,
            "outcome_b": outcome_b,
            "resolution_spec": resolution_spec,
            "price_series": [
                {"round": round_number, "price_yes": price_yes, "reserve_a": reserve_a, "reserve_b": reserve_b}
                for round_number, price_yes, reserve_a, reserve_b in prices
            ],
            "resolved": bool(resolved),
            "winning_outcome": winning_outcome,
        })
    return markets


def load_resolution_trajectory(simulation_dir: str) -> Dict[str, Any]:
    """Load the authoritative all-arena trajectory written immediately before closure."""
    if not isinstance(simulation_dir, str) or not simulation_dir.strip():
        raise MarketResolutionError("simulation directory is required")
    try:
        payload = json.loads((Path(simulation_dir) / "trajectory.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MarketResolutionError("merged simulation trajectory is unavailable") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("snapshots"), list):
        raise MarketResolutionError("merged simulation trajectory is invalid")
    return payload


def _pending_summary(verdict: str) -> Dict[str, Any]:
    return {"status": "unresolved" if verdict == "UNRESOLVED" else "pending"}


def _insert_resolution(client: Any, row: Dict[str, Any]) -> None:
    response = client.table("market_resolutions").insert(row).execute()
    data = getattr(response, "data", None)
    if not isinstance(data, list) or len(data) != 1:
        raise MarketResolutionError("durable resolution insert was rejected")
    inserted = data[0]
    if (
        inserted.get("simulation_id") != row["simulation_id"]
        or inserted.get("market_id") != row["market_id"]
        or inserted.get("org_id") != row["org_id"]
    ):
        raise MarketResolutionError("durable resolution insert ownership mismatch")


def _update_resolution(client: Any, simulation_id: str, market_id: int, org_id: str, summary: Dict[str, Any]) -> None:
    response = (
        client.table("market_resolutions")
        .update({"payout_summary": summary})
        .eq("simulation_id", simulation_id)
        .eq("market_id", market_id)
        .eq("org_id", org_id)
        .execute()
    )
    data = getattr(response, "data", None)
    if not isinstance(data, list) or len(data) != 1:
        raise MarketResolutionError("durable payout update was rejected")
    row = data[0]
    if row.get("simulation_id") != simulation_id or row.get("market_id") != market_id or row.get("org_id") != org_id:
        raise MarketResolutionError("durable payout update ownership mismatch")


async def _settle_resolution(
    client: Any,
    simulation_id: str,
    org_id: str,
    platform: Any,
    row: Dict[str, Any],
) -> Dict[str, Any]:
    verdict = row.get("verdict")
    market_id = row.get("market_id")
    if not isinstance(market_id, int) or isinstance(market_id, bool) or market_id <= 0:
        raise MarketResolutionError("durable market identifier is invalid")
    if verdict == "UNRESOLVED":
        summary = dict(row.get("payout_summary") or _pending_summary(verdict))
        summary["status"] = "unresolved"
        _update_resolution(client, simulation_id, market_id, org_id, summary)
        return summary
    if verdict not in {"YES", "NO", "INVALID"}:
        raise MarketResolutionError("durable verdict is invalid")
    settlement = await platform.resolve_market(SYSTEM_SETTLEMENT_ACTOR, (market_id, verdict))
    if not settlement.get("success"):
        raise MarketResolutionError("SQLite settlement failed")
    summary = dict(settlement["payout_summary"])
    summary["status"] = "refunded" if verdict == "INVALID" else "paid"
    _update_resolution(client, simulation_id, market_id, org_id, summary)
    return summary


async def _final_wealth(platform: Any, *, complete: bool) -> List[Dict[str, Any]]:
    user_ids = [row[0] for row in platform.db_cursor.execute("SELECT user_id FROM portfolio ORDER BY user_id").fetchall()]
    wealth = []
    for user_id in user_ids:
        cash_row = platform.db_cursor.execute(
            "SELECT balance FROM portfolio WHERE user_id = ?", (user_id,)
        ).fetchone()
        if cash_row is None:
            raise MarketResolutionError("portfolio is unavailable")
        open_value = 0.0
        positions = platform.db_cursor.execute(
            "SELECT p.shares, p.outcome, m.reserve_a, m.reserve_b, m.outcome_a "
            "FROM position p JOIN market m ON m.market_id = p.market_id "
            "WHERE p.user_id = ? AND p.shares > 0 AND m.resolved = 0",
            (user_id,),
        ).fetchall()
        for shares, outcome, reserve_a, reserve_b, outcome_a in positions:
            price_a, price_b = get_prices(reserve_a, reserve_b)
            open_value += float(shares) * (price_a if outcome == outcome_a else price_b)
        cash_balance = float(cash_row[0])
        wealth.append({
            "user_id": user_id,
            "cash_balance": cash_balance,
            "open_position_value": open_value,
            "wealth": cash_balance + open_value,
            "complete": complete,
        })
    return wealth


def _validate_existing_row(
    row: Mapping[str, Any], market: Mapping[str, Any], trajectory_payload: Mapping[str, Any], events: Sequence[Mapping[str, Any]]
) -> None:
    market_id = market["market_id"]
    if row.get("market_id") != market_id or row.get("verdict") not in {"YES", "NO", "INVALID", "UNRESOLVED"}:
        raise MarketResolutionError("durable resolution is invalid")
    version = row.get("prompt_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise MarketResolutionError("durable resolution is invalid")
    if not isinstance(row.get("payout_summary"), dict):
        raise MarketResolutionError("durable resolution is invalid")
    if row.get("question") != market["question"] or row.get("resolution_spec") != market["resolution_spec"] or row.get("price_series") != market["price_series"]:
        raise MarketResolutionError("durable resolution diverges from SQLite market")
    if row.get("prompt_key") != market_resolution_oracle.ORACLE_PROMPT_KEY:
        raise MarketResolutionError("durable resolution prompt is invalid")
    if not isinstance(row.get("justification"), str) or not row["justification"].strip() or not isinstance(row.get("evidence"), list):
        raise MarketResolutionError("durable resolution evidence is invalid")
    confidence = row.get("confidence")
    if row["verdict"] == "UNRESOLVED":
        if confidence is not None or row["evidence"]:
            raise MarketResolutionError("durable unresolved resolution is invalid")
    elif not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise MarketResolutionError("durable resolution confidence is invalid")
    else:
        try:
            digest = market_resolution_oracle.build_resolution_digest(market, trajectory_payload, market["price_series"], events)
            market_resolution_oracle.validate_oracle_output({
                "verdict": row["verdict"], "justification": row["justification"], "confidence": confidence, "evidence": row["evidence"],
            }, digest)
        except ValueError as exc:
            raise MarketResolutionError("durable resolution evidence is invalid") from exc


async def resolve_all_markets(
    simulation_id: str,
    *,
    platform: Any,
    trajectory_payload: Mapping[str, Any],
    config: Mapping[str, Any],
    injected_events: Sequence[Mapping[str, Any]] = (),
    client: Any = None,
    oracle: Callable[..., market_resolution_oracle.OracleResolution] = market_resolution_oracle.resolve_market,
) -> List[Dict[str, Any]]:
    """Persist an Oracle result before any SQLite payout, then settle idempotently."""
    if not isinstance(simulation_id, str) or not simulation_id.strip():
        raise MarketResolutionError("simulation_id is required")
    cli = client or get_supabase_admin()
    org_id = _require_org_id(cli, simulation_id)
    if not isinstance(trajectory_payload, Mapping):
        raise MarketResolutionError("merged simulation trajectory is invalid")
    locale = config.get("locale", "fr") if isinstance(config.get("locale", "fr"), str) else "fr"
    rows: List[Dict[str, Any]] = []

    for market in _load_markets(platform):
        market_id = market["market_id"]
        row = _existing_resolution(cli, simulation_id, market_id, org_id)
        if row is None:
            if market["resolved"]:
                raise MarketResolutionError("resolved SQLite market lacks durable adjudication")
            resolution = oracle(market, trajectory_payload, market["price_series"], injected_events, locale=locale)
            row = {
                "simulation_id": simulation_id,
                "market_id": market_id,
                "org_id": org_id,
                "question": market["question"],
                "resolution_spec": market["resolution_spec"],
                "verdict": resolution.verdict,
                "justification": resolution.justification,
                "confidence": resolution.confidence,
                "evidence": resolution.evidence,
                "price_series": market["price_series"],
                "payout_summary": _pending_summary(resolution.verdict),
                "prompt_key": resolution.prompt_key,
                "prompt_version": resolution.prompt_version,
            }
            try:
                _insert_resolution(cli, row)
            except Exception as exc:  # noqa: BLE001 - race is resolved by its durable winner
                row = _existing_resolution(cli, simulation_id, market_id, org_id)
                if row is None:
                    raise MarketResolutionError("durable resolution insert failed") from exc
        if row["verdict"] == "UNRESOLVED" and market["resolved"]:
            raise MarketResolutionError("unresolved durable row conflicts with SQLite settlement")
        _validate_existing_row(row, market, trajectory_payload, injected_events)
        summary = await _settle_resolution(cli, simulation_id, org_id, platform, row)
        rows.append({"row": row, "summary": summary})

    complete = all(entry["row"].get("verdict") != "UNRESOLVED" for entry in rows)
    final_wealth = await _final_wealth(platform, complete=complete)
    for entry in rows:
        row, summary = entry["row"], dict(entry["summary"])
        summary["final_wealth"] = final_wealth
        summary["complete"] = complete
        _update_resolution(cli, simulation_id, row["market_id"], org_id, summary)
        entry["summary"] = summary
    return [entry["summary"] for entry in rows]
