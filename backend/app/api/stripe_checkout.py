"""Checkout Stripe self-service pour le palier d'entrée (US-205, ADR-014).

  ``POST /api/stripe/create-checkout-session`` — public, appelé par le
  bouton d'achat des 3 packages d'entrée sur ``/offres``. Retourne l'URL
  Stripe hébergée vers laquelle rediriger le client.

  ``POST /api/stripe/webhook`` — appelé par Stripe (signature vérifiée),
  sur ``checkout.session.completed`` insère une ligne ``quote_ownership``
  avec ``status='paid'`` directement (pas de ligne intermédiaire — évite
  un devis fantôme si le client abandonne le paiement).

Aucune authentification requise sur ces deux endpoints : l'achat en
self-service est volontairement sans compte (friction minimale), et le
webhook s'authentifie par signature HMAC, pas par session utilisateur.
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from ..auth.supabase_client import get_supabase_admin
from ..services import quote_ownership as qo
from ..services.stripe_service import (
    PACKAGE_PRICE_IDS,
    StripeAPIError,
    StripeConfigError,
    create_checkout_session,
    verify_webhook_signature,
)


stripe_bp = Blueprint("stripe_checkout", __name__)
logger = logging.getLogger("miroshark.api.stripe_checkout")

# Org interne de rattachement pour les devis self-service sans compte —
# même org que la rétro-attribution filesystem historique (US-114,
# scripts/migrate_quotes_to_supabase.py). Résolue paresseusement (pas au
# import) pour ne pas dépendre de Supabase au chargement du module.
_FALLBACK_ORG_SLUG = "aimpower-bassira"
_fallback_org_id_cache: str | None = None


def _fallback_org_id() -> str | None:
    global _fallback_org_id_cache
    if _fallback_org_id_cache:
        return _fallback_org_id_cache
    try:
        client = get_supabase_admin()
        resp = (
            client.table("organizations")
            .select("id")
            .eq("slug", _FALLBACK_ORG_SLUG)
            .limit(1)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if rows:
            _fallback_org_id_cache = rows[0].get("id")
        return _fallback_org_id_cache
    except Exception as exc:  # noqa: BLE001
        logger.error("Could not resolve fallback org %r: %s", _FALLBACK_ORG_SLUG, exc.__class__.__name__)
        return None


@stripe_bp.route("/create-checkout-session", methods=["POST"])
def post_create_checkout_session():
    body = request.get_json(silent=True) or {}
    package_id = (body.get("package_id") or "").strip()
    currency = (body.get("currency") or "").strip().lower()
    customer_email = (body.get("customer_email") or "").strip() or None
    # US-IQ-03 : propagé par le front quand le checkout provient de la
    # branche self-service du parcours de qualification (jamais requis).
    intake_session_id = (body.get("intake_session_id") or "").strip() or None

    if package_id not in PACKAGE_PRICE_IDS:
        return jsonify({
            "success": False,
            "error_code": "UNKNOWN_PACKAGE",
            "error": f"Package '{package_id}' is not available for self-service checkout.",
        }), 400

    try:
        session = create_checkout_session(
            package_id=package_id,
            currency=currency,
            customer_email=customer_email,
            intake_session_id=intake_session_id,
        )
    except ValueError as exc:
        return jsonify({"success": False, "error_code": "INVALID_REQUEST", "error": str(exc)}), 400
    except StripeConfigError:
        logger.error("Stripe checkout requested but STRIPE_SECRET_KEY is not configured.")
        return jsonify({
            "success": False,
            "error_code": "STRIPE_NOT_CONFIGURED",
            "error": "Payment is not available right now.",
        }), 503
    except StripeAPIError:
        return jsonify({
            "success": False,
            "error_code": "STRIPE_API_ERROR",
            "error": "Could not start the checkout session.",
        }), 502

    return jsonify({"success": True, "data": {"checkout_url": session.get("url")}}), 200


@stripe_bp.route("/webhook", methods=["POST"])
def post_stripe_webhook():
    sig_header = request.headers.get("Stripe-Signature", "")
    try:
        event = verify_webhook_signature(request.get_data(), sig_header)
    except StripeConfigError:
        logger.error("Stripe webhook received but STRIPE_WEBHOOK_SECRET is not configured.")
        return jsonify({"error": "webhook not configured"}), 503
    except ValueError as exc:
        logger.warning("Stripe webhook signature rejected: %s", exc)
        return jsonify({"error": "invalid signature"}), 400

    event_type = event.get("type")
    if event_type != "checkout.session.completed":
        # On n'écoute que cet événement — 200 pour éviter les retries Stripe
        # inutiles sur des types qu'on n'a jamais demandés.
        return jsonify({"received": True, "ignored": event_type}), 200

    session = event.get("data", {}).get("object", {})
    package_id = (session.get("metadata") or {}).get("bassira_package_id")
    customer_email = session.get("customer_details", {}).get("email") or session.get("customer_email")
    checkout_session_id = session.get("id")

    if not package_id or package_id not in PACKAGE_PRICE_IDS:
        logger.error(
            "checkout.session.completed without a known bassira_package_id (session=%s)",
            checkout_session_id,
        )
        return jsonify({"received": True, "error": "missing package metadata"}), 200

    org_id = _fallback_org_id()
    if not org_id:
        logger.error(
            "Cannot record paid checkout session %s — fallback org %r not found.",
            checkout_session_id, _FALLBACK_ORG_SLUG,
        )
        return jsonify({"received": True, "error": "fallback org not found"}), 200

    quote_id = f"stripe_{checkout_session_id}"
    try:
        qo.link_quote_to_org(
            quote_id,
            org_id,
            customer_email=customer_email,
            package_id=package_id,
            status="paid",
            payload={
                "source": "stripe_self_service",
                "checkout_session_id": checkout_session_id,
                "currency": session.get("currency"),
                "amount_total": session.get("amount_total"),
            },
        )
    except Exception as exc:  # noqa: BLE001 — ne jamais faire échouer le webhook (Stripe retry sinon)
        logger.error(
            "Failed to record quote_ownership for paid session %s: %s",
            checkout_session_id, exc.__class__.__name__,
        )

    return jsonify({"received": True}), 200
