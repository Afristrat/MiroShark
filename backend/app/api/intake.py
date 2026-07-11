"""Intake endpoints (US-IQ-01, US-IQ-02, US-IQ-03) — parcours de qualification /devis.

  * ``POST /api/intake/session`` — démarre un parcours (state='started').
  * ``POST /api/intake/session/<id>/form`` — soumet le formulaire A1-A8 +
    identité (state → 'form_submitted'), écrit aussi ``quote_ownership``
    (rétrocompatibilité admin console).
  * ``POST /api/intake/session/<id>/agent/turn`` — un tour de l'agent
    conversationnel de qualification (étape B, US-IQ-02).
  * ``POST /api/intake/session/<id>/complete`` — calcule la branche de sortie
    (routage déterministe, étape C), clôture la session et envoie l'email de
    confirmation contextualisé (best-effort, US-IQ-04).
  * ``GET /api/intake/calcom-confirmed`` — capture le redirect de succès
    Cal.com et persiste ``calcom_booking_uid`` (US-IQ-04).

Public, non authentifié — même limiteur de débit que ``/api/quote``
(``quote_service.check_rate_limit``, partagé par IP).
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, redirect, request

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


@intake_bp.route("/session/<session_id>/agent/turn", methods=["POST"])
def post_agent_turn(session_id: str):
    """Un tour de l'agent conversationnel de qualification (étape B,
    US-IQ-02). Body JSON requis : ``{"message": "<texte du décideur>"}``."""
    try:
        client_ip = request.remote_addr or ""
        if not check_rate_limit(client_ip):
            return jsonify({
                "success": False,
                "error_code": "RATE_LIMITED",
                "error": "Too many requests from this IP. Please retry in an hour.",
            }), 429

        body = request.get_json(silent=True) or {}
        user_message = body.get("message")
        if not isinstance(user_message, str) or not user_message.strip():
            return jsonify({
                "success": False,
                "error_code": "MISSING_FIELD",
                "error": "Field « message » is required.",
            }), 400

        status, resp_body = intake_service.agent_turn(session_id, user_message)
        return jsonify(resp_body), status
    except Exception:  # noqa: BLE001
        logger.exception("intake agent turn: unexpected failure")
        return jsonify({
            "success": False,
            "error_code": "UNKNOWN",
            "error": "Internal server error.",
        }), 500


@intake_bp.route("/session/<session_id>/complete", methods=["POST"])
def post_complete_session(session_id: str):
    """Calcule la branche de sortie (self_service | quote_48h | meeting),
    clôture la session et envoie l'email de confirmation contextualisé
    (best-effort, US-IQ-04) — voir ``intake_service.complete_routing``."""
    try:
        status, body = intake_service.complete_routing(session_id)
        return jsonify(body), status
    except Exception:  # noqa: BLE001
        logger.exception("intake session complete: unexpected failure")
        return jsonify({
            "success": False,
            "error_code": "UNKNOWN",
            "error": "Internal server error.",
        }), 500


@intake_bp.route("/calcom-confirmed", methods=["GET"])
def get_calcom_confirmed():
    """Capture le redirect de succès Cal.com (ADR-IQ-03 v3, US-IQ-04) — l'UID
    de la réservation confirmée (``uid``/``bookingUid``) est TOUJOURS relayé
    par Cal.com. ``intake_session_id`` NE L'EST JAMAIS (constat empirique
    2026-07-11, ADR-IQ-09 : ``forwardParamsSuccessRedirect`` ne relaie que les
    champs propres à la page de succès Cal.com). La ré-identification et sa
    preuve (email ATTESTÉ server-to-server par l'API Cal.com, JAMAIS un query
    param client — durcissement sécurité post-review) sont entièrement
    déléguées à ``intake_service.confirm_calcom_booking``. PAS un webhook
    entrant (hors scope V1)."""
    booking_uid = request.args.get("uid") or request.args.get("bookingUid")
    if not booking_uid:
        return jsonify({
            "success": False,
            "error_code": "MISSING_PARAMS",
            "error": "uid/bookingUid query param is required.",
        }), 400

    session_id = request.args.get("intake_session_id")
    status, payload = intake_service.confirm_calcom_booking(session_id, booking_uid)
    if status != 200:
        return jsonify(payload), status

    return redirect("https://bassira.ma/devis?calcom_confirmed=1", code=302)
