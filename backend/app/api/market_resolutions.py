"""Read-only durable market-resolution API (US-226)."""

from __future__ import annotations

from typing import Any, Tuple

from flask import jsonify

from . import report_bp
from .report import _authorize_simulation_access
from ..services.market_resolution_service import MarketResolutionReadError, read_market_resolutions
from ..utils.logger import get_logger

logger = get_logger("miroshark.api.market_resolutions")

def _error(code: str, message: str, status: int) -> Tuple[Any, int]:
    return jsonify({"success": False, "error_code": code, "error": message}), status


@report_bp.route("/<simulation_id>/market-resolutions", methods=["GET"])
def get_market_resolutions(simulation_id: str):
    """Return durable adjudication records, scoped by canonical ownership."""
    denied = _authorize_simulation_access(simulation_id, allow_published=True)
    if denied is not None:
        return denied

    try:
        result = read_market_resolutions(simulation_id)
    except MarketResolutionReadError as exc:
        logger.error("market resolution read failed: %s", exc.code)
        if exc.code == "SIMULATION_NOT_FOUND":
            return _error(exc.code, "Simulation was not found.", 404)
        if exc.code == "OWNERSHIP_INVALID":
            return _error(exc.code, "Resolution records are unavailable.", 403)
        return _error(exc.code, "Resolution records are unavailable.", 503)
    return jsonify({
        "success": True,
        "data": {
            "simulation_id": simulation_id,
            "resolutions": result.resolutions,
            "final_wealth": result.final_wealth,
            "complete": result.complete,
        },
    })
