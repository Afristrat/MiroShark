"""Intake endpoints (US-IQ-01) — parcours de qualification /devis « 3 temps ».

  * ``POST /api/intake/session`` — démarre un parcours (state='started').
  * ``POST /api/intake/session/<id>/form`` — soumet le formulaire A1-A8 +
    identité (state → 'form_submitted'), écrit aussi ``quote_ownership``
    (rétrocompatibilité admin console).

Public, non authentifié — même limiteur de débit que ``/api/quote``
(``quote_service.check_rate_limit``, partagé par IP).
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from ..services import intake_service
from ..services.quote_service import check_rate_limit


intake_bp = Blueprint("intake", __name__)
logger = logging.getLogger("miroshark.api.intake")


@intake_bp.route("/session", methods=["POST"])
def post_start_session():
    """Démarre un parcours de qualification. Body JSON optionnel :
    ``{"locale": "fr"|"en"|"ar", "entry_door": "standard"|"aar"}``.
    """
    try:
        client_ip = request.remote_addr or ""
        if not check_rate_limit(client_ip):
            return jsonify({
                "success": False,
                "error_code": "RATE_LIMITED",
                "error": "Too many intake sessions from this IP. Please retry in an hour.",
            }), 429

        body = request.get_json(silent=True) or {}
        data = intake_service.start_session(
            locale=body.get("locale") or "fr",
            entry_door=body.get("entry_door") or "standard",
        )
        return jsonify({"success": True, "data": data}), 200
    except Exception:  # noqa: BLE001 — filet de sécurité
        # Endpoint public non authentifié : jamais str(exc)/traceback dans la
        # réponse (fuite de chemins internes / détails Supabase) — trace
        # complète en log serveur uniquement (finding sécurité 2026-07-09).
        logger.exception("intake session start: unexpected failure")
        return jsonify({
            "success": False,
            "error_code": "UNKNOWN",
            "error": "Internal server error.",
        }), 500


@intake_bp.route("/session/<session_id>/form", methods=["POST"])
def post_submit_form(session_id: str):
    """Soumet le formulaire A1-A8 + identité pour une session démarrée."""
    try:
        client_ip = request.remote_addr or ""
        user_agent = request.headers.get("User-Agent", "") or ""
        payload = request.get_json(silent=True) or {}
        status, body = intake_service.submit_form(
            session_id,
            payload,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        return jsonify(body), status
    except Exception:  # noqa: BLE001
        logger.exception("intake form submit: unexpected failure")
        return jsonify({
            "success": False,
            "error_code": "UNKNOWN",
            "error": "Internal server error.",
        }), 500
