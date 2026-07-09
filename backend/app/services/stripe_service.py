"""Stripe self-service Checkout pour le palier d'entrée (US-205, ADR-014).

Portée volontairement limitée aux 3 packages d'entrée — les paliers plus
chers restent sur le circuit devis manuel (Payment Link admin, US-104) :
cf. ADR-007 et ADR-014 dans docs/08-decisions-log.md.

Appelle l'API REST Stripe directement via ``requests`` (déjà dépendance du
projet) plutôt que le SDK officiel ``stripe`` — pas de nouvelle dépendance
pour deux opérations HTTP simples (échelle Ponytail).

Catalogue Stripe (mode live, créé le 2026-07-09 — cf. ADR-014) : chaque
package a UN SEUL objet Price portant les 3 devises en ``currency_options``
(MAD/USD/EUR), la devise effective étant choisie explicitement à la
création de la Checkout Session via le paramètre ``currency``.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from typing import Any, Dict, Optional

import requests


logger = logging.getLogger("miroshark.stripe")

_API_BASE = "https://api.stripe.com/v1"

# package_id -> Price ID Stripe (mode live). Modifier ce mapping = décision
# de catalogue, pas une config d'environnement — cf. ADR-014.
PACKAGE_PRICE_IDS: Dict[str, str] = {
    "pmf_discovery": "price_1Tr4hBHM2FpoSxESlmb3WXlR",
    "crisis_drill_24h": "price_1Tr4hCHM2FpoSxESlD4heCqI",
    "adcheck_lite": "price_1Tr4hEHM2FpoSxESig2ZeeD1",
}

_VALID_CURRENCIES = {"mad", "usd", "eur"}


class StripeConfigError(RuntimeError):
    """STRIPE_SECRET_KEY ou STRIPE_WEBHOOK_SECRET absente de l'environnement."""


class StripeAPIError(RuntimeError):
    """Réponse d'erreur renvoyée par l'API Stripe."""


def _secret_key() -> str:
    key = (os.environ.get("STRIPE_SECRET_KEY") or "").strip()
    if not key:
        raise StripeConfigError("STRIPE_SECRET_KEY is not configured")
    return key


def create_checkout_session(
    *,
    package_id: str,
    currency: str,
    customer_email: Optional[str] = None,
) -> Dict[str, Any]:
    """Crée une Checkout Session Stripe hébergée pour un package d'entrée.

    Args:
        package_id: doit être une clé de ``PACKAGE_PRICE_IDS``.
        currency: ``mad``, ``usd`` ou ``eur`` (insensible à la casse).
        customer_email: pré-remplit l'email sur la page Stripe (optionnel).

    Returns:
        Le JSON de la Checkout Session Stripe (contient ``id`` et ``url``
        vers lesquels rediriger le client).

    Raises:
        ValueError: package_id ou currency invalide.
        StripeConfigError: clé API absente.
        StripeAPIError: Stripe a refusé la requête.
    """
    if package_id not in PACKAGE_PRICE_IDS:
        raise ValueError(f"Unknown or non-self-service package_id: {package_id!r}")
    currency = (currency or "").strip().lower()
    if currency not in _VALID_CURRENCIES:
        raise ValueError(f"Unsupported currency: {currency!r}")

    base_url = os.environ.get("BASSIRA_PUBLIC_URL", "https://bassira.ma").rstrip("/")
    price_id = PACKAGE_PRICE_IDS[package_id]

    data = {
        "mode": "payment",
        "currency": currency,
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "success_url": f"{base_url}/devis/paiement-reussi?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{base_url}/offres",
        "metadata[bassira_package_id]": package_id,
    }
    if customer_email:
        data["customer_email"] = customer_email

    resp = requests.post(
        f"{_API_BASE}/checkout/sessions",
        data=data,
        auth=(_secret_key(), ""),
        timeout=15,
    )
    if not resp.ok:
        logger.error(
            "Stripe checkout session creation failed: HTTP %s — %s",
            resp.status_code, resp.text[:500],
        )
        raise StripeAPIError(f"Stripe API error ({resp.status_code})")
    return resp.json()


def verify_webhook_signature(payload: bytes, sig_header: str, *, tolerance_seconds: int = 300) -> Dict[str, Any]:
    """Vérifie la signature ``Stripe-Signature`` d'un webhook entrant.

    Implémentation manuelle de l'algorithme documenté par Stripe (HMAC-SHA256
    sur ``"{timestamp}.{payload}"``) — évite le SDK pour une primitive stdlib
    de ~15 lignes (``hmac`` + ``hashlib``).

    Returns:
        Le corps JSON désérialisé de l'événement, si la signature est valide.

    Raises:
        StripeConfigError: STRIPE_WEBHOOK_SECRET absente.
        ValueError: en-tête manquant/malformé, signature invalide, ou
                    timestamp hors tolérance (protection anti-replay).
    """
    secret = (os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip()
    if not secret:
        raise StripeConfigError("STRIPE_WEBHOOK_SECRET is not configured")
    if not sig_header:
        raise ValueError("Missing Stripe-Signature header")

    parts: Dict[str, str] = {}
    for item in sig_header.split(","):
        if "=" in item:
            k, v = item.split("=", 1)
            parts.setdefault(k.strip(), v.strip())

    timestamp = parts.get("t")
    signature = parts.get("v1")
    if not timestamp or not signature:
        raise ValueError("Malformed Stripe-Signature header")

    if abs(time.time() - int(timestamp)) > tolerance_seconds:
        raise ValueError("Webhook timestamp outside tolerance window")

    signed_payload = f"{timestamp}.".encode() + payload
    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Webhook signature mismatch")

    import json
    return json.loads(payload)
