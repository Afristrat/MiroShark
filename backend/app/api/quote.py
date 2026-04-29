"""Quote-request endpoint (US-025).

Public ``POST /api/quote`` — accepts the multi-step form submitted from
the ``/devis`` route in the SPA. The route is the closing edge of the
commercial tunnel:

  ``/`` → ``/offres`` (US-023) → ``/devis`` (this) → email to sales

Why a dedicated blueprint :

  * Keeps the existing API surface (``simulation``, ``report``, ``graph``,
    ``calibration`` …) untouched — none of those modules want a
    leads-table dependency.
  * Makes the rate limiter scoped (``check_rate_limit`` only fires on
    this route — legit users browsing /api/simulation/public never hit
    the bucket).
  * Lets the OpenAPI drift test see the route after we add ``quote_bp``
    to the test's prefix map.

The handler is intentionally thin — every piece of logic (validation,
sanitisation, persistence, email) lives in
``app/services/quote_service.py`` so the unit tests can drive the same
code paths without spinning up a Flask app.
"""

from __future__ import annotations

import logging
import traceback

from flask import Blueprint, jsonify, request

from ..services.quote_service import check_rate_limit, submit_quote


quote_bp = Blueprint("quote", __name__)
logger = logging.getLogger("miroshark.api.quote")


@quote_bp.route("", methods=["POST"])
def post_quote():
    """Accept a quote-request payload, persist it, fire a notification email.

    Returns 200 with ``{success, data:{quote_id, submitted_at}}`` on
    success, 400 with a SCREAMING_SNAKE error_code on validation
    failure, 429 when the rate limiter trips, 500 on disk-write failure.
    """
    try:
        client_ip = request.remote_addr or ""
        user_agent = request.headers.get("User-Agent", "") or ""

        # Rate limit *before* parsing JSON — protects against a flood
        # of malformed POSTs as well as well-formed ones.
        if not check_rate_limit(client_ip):
            return jsonify({
                "success": False,
                "error_code": "RATE_LIMITED",
                "error": (
                    "Too many quote requests from this IP. Please retry "
                    "in an hour or reach us at contact@ai-mpower.com."
                ),
            }), 429

        payload = request.get_json(silent=True) or {}
        status, body = submit_quote(
            payload,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        return jsonify(body), status

    except Exception as exc:  # noqa: BLE001 — last-ditch safety net
        logger.error("quote: unexpected failure: %s", exc)
        return jsonify({
            "success": False,
            "error_code": "UNKNOWN",
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }), 500
