"""Read-only durable market-resolution API (US-226)."""

from __future__ import annotations

import math
from typing import Any, List, Mapping, Tuple

from flask import jsonify

from . import report_bp
from .report import _authorize_simulation_access
from ..auth import supabase_client as sbc
from ..utils.logger import get_logger

logger = get_logger("miroshark.api.market_resolutions")

_PUBLIC_FIELDS = (
    "market_id",
    "question",
    "resolution_spec",
    "verdict",
    "justification",
    "confidence",
    "evidence",
    "price_series",
    "payout_summary",
    "prompt_key",
    "prompt_version",
    "resolved_at",
)
_FINAL_STATUSES = {"paid", "refunded", "unresolved"}


def _error(code: str, message: str, status: int) -> Tuple[Any, int]:
    return jsonify({"success": False, "error_code": code, "error": message}), status


def _valid_final_wealth(final_wealth: Any, complete: bool) -> bool:
    if not isinstance(final_wealth, list):
        return False
    for item in final_wealth:
        if not isinstance(item, dict) or item.get("complete") is not complete:
            return False
        user_id = item.get("user_id")
        if not isinstance(user_id, int) or isinstance(user_id, bool):
            return False
        for key in ("cash_balance", "open_position_value", "wealth"):
            value = item.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                return False
    return True


def _final_wealth(rows: List[Mapping[str, Any]]) -> tuple[List[Any], bool]:
    """Expose final wealth only when every durable resolution agrees on it."""
    if not rows:
        return [], False

    summaries = [row.get("payout_summary") for row in rows]
    status_by_verdict = {"YES": "paid", "NO": "paid", "INVALID": "refunded", "UNRESOLVED": "unresolved"}
    for row, summary in zip(rows, summaries):
        verdict = row.get("verdict")
        if (
            not isinstance(summary, dict)
            or summary.get("status") not in _FINAL_STATUSES
            or not isinstance(verdict, str)
            or status_by_verdict.get(verdict) != summary.get("status")
        ):
            return [], False

    first_summary = summaries[0]
    assert isinstance(first_summary, dict)
    final_wealth = first_summary.get("final_wealth")
    complete = first_summary.get("complete")
    if not isinstance(final_wealth, list) or not isinstance(complete, bool):
        return [], False
    if not _valid_final_wealth(final_wealth, complete):
        return [], False
    if any(
        summary.get("final_wealth") != final_wealth or summary.get("complete") is not complete
        for summary in summaries[1:]
        if isinstance(summary, dict)
    ):
        return [], False
    if complete != all(row.get("verdict") != "UNRESOLVED" for row in rows):
        return [], False
    return final_wealth, complete


@report_bp.route("/<simulation_id>/market-resolutions", methods=["GET"])
def get_market_resolutions(simulation_id: str):
    """Return durable adjudication records, scoped by canonical ownership."""
    denied = _authorize_simulation_access(simulation_id, allow_published=True)
    if denied is not None:
        return denied

    try:
        owner = sbc.get_simulation_owner(simulation_id)
    except Exception as exc:  # noqa: BLE001 - durable ownership must fail closed
        logger.error("market resolution ownership read failed: %s", exc.__class__.__name__)
        return _error("OWNERSHIP_UNAVAILABLE", "Resolution records are unavailable.", 503)
    if not isinstance(owner, dict):
        return _error("SIMULATION_NOT_FOUND", "Simulation was not found.", 404)
    org_id = owner.get("org_id")
    if not isinstance(org_id, str) or not org_id.strip():
        return _error("OWNERSHIP_INVALID", "Resolution records are unavailable.", 403)

    try:
        response = (
            sbc.get_supabase_admin()
            .table("market_resolutions")
            .select(",".join(_PUBLIC_FIELDS))
            .eq("simulation_id", simulation_id)
            .eq("org_id", org_id)
            .order("market_id")
            .execute()
        )
        rows = getattr(response, "data", None)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise RuntimeError("invalid durable resolution response")
    except Exception as exc:  # noqa: BLE001 - no partial cross-tenant response
        logger.error("market resolution query failed: %s", exc.__class__.__name__)
        return _error("RESOLUTIONS_UNAVAILABLE", "Resolution records are unavailable.", 503)

    resolutions = [{field: row.get(field) for field in _PUBLIC_FIELDS} for row in rows]
    final_wealth, complete = _final_wealth(rows)
    return jsonify({
        "success": True,
        "data": {
            "simulation_id": simulation_id,
            "resolutions": resolutions,
            "final_wealth": final_wealth,
            "complete": complete,
        },
    })
