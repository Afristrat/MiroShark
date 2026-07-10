"""Quote-request endpoint (US-025) + admin console (US-102/103/104).

Public ``POST /api/quote`` — accepts the multi-step form submitted from
the ``/devis`` route in the SPA. The route is the closing edge of the
commercial tunnel:

  ``/`` → ``/offres`` (US-023) → ``/devis`` (this) → email to sales

US-102 / US-103 / US-104 ajoutent une console super-admin :

  * ``GET /api/admin/quotes`` — liste paginée + filtres
  * ``GET /api/admin/quotes/<quote_id>`` — détail
  * ``PATCH /api/admin/quotes/<quote_id>/status`` — transition workflow
  * ``PATCH /api/admin/quotes/<quote_id>/notes`` — notes admin
  * ``POST /api/admin/quotes/<quote_id>/send-payment-link`` — email
    Stripe payment link (transition automatique vers ``quoted``)
  * ``POST /api/admin/quotes/<quote_id>/send-delivered`` — email
    livraison (transition automatique vers ``delivered``)

Tous les endpoints admin sont gardés par ``@require_super_admin``.
"""

from __future__ import annotations

import logging
import traceback
from typing import Any, Dict, Optional

from flask import Blueprint, g, jsonify, request

from ..auth.decorators import (
    is_super_admin_email,
    require_auth,
    require_super_admin,
)
from ..auth.supabase_client import (
    SupabaseConfigError,
    get_user_orgs,
)
from ..services.quote_service import check_rate_limit, submit_quote
from ..services import quote_admin_service as qa
from ..services import quote_ownership as qo
from ..services import intake_service


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


# ─── Admin console (US-102 / US-103 / US-104) ───────────────────────────────


# Blueprint séparé pour les routes admin — monté à `/api/admin/quotes`.
admin_quote_bp = Blueprint("admin_quotes", __name__)


def _err(code: str, message: str, status: int):
    return jsonify({
        "success": False,
        "error_code": code,
        "error": message,
    }), status


def _current_admin_email() -> Optional[str]:
    """Lit l'email du super-admin courant (posé par require_auth)."""
    user = getattr(g, "current_user", None) or {}
    return user.get("email") if isinstance(user, dict) else None


def _parse_int(raw: Optional[str], default: int, min_v: int, max_v: int) -> int:
    if raw is None:
        return default
    try:
        n = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return max(min_v, min(max_v, n))


@admin_quote_bp.route("", methods=["GET"])
@require_auth
def list_quotes_admin():
    """Liste paginée des devis.

    Comportement (US-114) :
      - **Super-admin Bassira** (email whitelist) → voit TOUS les devis
        filesystem, comme avant.
      - **Membre d'une org** (JWT valide + appartient à >=1 org) → voit
        uniquement les devis liés à ses orgs via la table
        ``quote_ownership`` (RLS strict, lookup via service_role côté
        backend pour résoudre l'email → org).
      - **User authentifié sans org** → 403 ``NOT_A_MEMBER``.

    Query :
      - ``limit`` (default 50, max 200)
      - ``offset`` (default 0)
      - ``status`` — filtre exact (received | reviewing | … | delivered)
    """
    try:
        limit = _parse_int(request.args.get("limit"), 50, 1, 200)
        offset = _parse_int(request.args.get("offset"), 0, 0, 1_000_000)
        status_filter = (request.args.get("status") or "").strip() or None

        user = getattr(g, "current_user", None) or {}
        email = user.get("email") if isinstance(user, dict) else None

        # 1. Super-admin → vue cross-tenant complète (filesystem only).
        if is_super_admin_email(email):
            items, total = qa.list_quotes(
                limit=limit,
                offset=offset,
                status_filter=status_filter,
            )
            return jsonify({
                "success": True,
                "data": {
                    "quotes": items,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                },
            }), 200

        # 2. Membre d'une org → scoping via quote_ownership.
        user_id = user.get("id") if isinstance(user, dict) else None
        if not user_id:
            return _err("INVALID_TOKEN", "Token missing 'sub' claim.", 401)

        try:
            user_orgs = get_user_orgs(user_id)
        except SupabaseConfigError:
            return _err(
                "SUPABASE_NOT_CONFIGURED",
                "Backend Supabase admin client is not configured.",
                503,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("list_quotes_admin user_orgs failed: %s", exc)
            return _err("ADMIN_QUOTES_FAILED", "Could not resolve user orgs.", 500)

        if not user_orgs:
            return _err(
                "NOT_A_MEMBER",
                "Authenticated user is not a member of any organization.",
                403,
            )

        org_ids = [o.get("id") for o in user_orgs if o.get("id")]
        try:
            ownership_rows = qo.list_quotes_for_orgs(org_ids)
        except Exception as exc:  # noqa: BLE001
            logger.error("list_quotes_for_orgs failed: %s", exc)
            return _err("ADMIN_QUOTES_FAILED", "Could not list quotes.", 500)

        # On indexe les rows ownership par quote_id pour pouvoir
        # joindre avec le filesystem (qui contient le payload riche).
        owned_ids = {row["quote_id"] for row in ownership_rows if row.get("quote_id")}

        # Lit le filesystem complet puis filtre sur les ids autorisés.
        # Le volume de devis reste petit (handful par semaine) — pas de
        # besoin d'optimisation ; la logique reste identique au super-admin.
        all_items, _ = qa.list_quotes(
            limit=10_000, offset=0, status_filter=status_filter
        )
        scoped_items = [it for it in all_items if it.get("quote_id") in owned_ids]
        total = len(scoped_items)
        page = scoped_items[offset : offset + limit]

        return jsonify({
            "success": True,
            "data": {
                "quotes": page,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        }), 200
    except Exception as exc:  # noqa: BLE001
        logger.error("list_quotes_admin failed: %s", exc)
        return _err("ADMIN_QUOTES_FAILED", "Could not list quotes.", 500)


@admin_quote_bp.route("/<quote_id>", methods=["GET"])
@require_auth
def get_quote_admin(quote_id: str):
    """Détail d'un devis : payload + status sidecar.

    Super-admin → tous les devis. Member → seulement les devis liés à
    une de ses orgs via ``quote_ownership`` (US-114).
    """
    user = getattr(g, "current_user", None) or {}
    email = user.get("email") if isinstance(user, dict) else None
    is_super = is_super_admin_email(email)

    if not is_super:
        # Vérification ownership avant tout accès au filesystem.
        user_id = user.get("id") if isinstance(user, dict) else None
        if not user_id:
            return _err("INVALID_TOKEN", "Token missing 'sub' claim.", 401)
        try:
            user_orgs = get_user_orgs(user_id)
        except SupabaseConfigError:
            return _err(
                "SUPABASE_NOT_CONFIGURED",
                "Backend Supabase admin client is not configured.",
                503,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("get_quote_admin user_orgs failed: %s", exc)
            return _err("ADMIN_QUOTES_FAILED", "Could not resolve user orgs.", 500)

        if not user_orgs:
            return _err(
                "NOT_A_MEMBER",
                "Authenticated user is not a member of any organization.",
                403,
            )
        owner_org = qo.get_org_for_quote(quote_id)
        user_org_ids = {str(o.get("id")) for o in user_orgs if o.get("id")}
        if owner_org is None or str(owner_org) not in user_org_ids:
            # Le devis n'a pas d'ownership ou n'appartient pas à une de
            # ses orgs : 404 plutôt que 403 pour éviter la fuite
            # d'existence de devis cross-tenant.
            return _err("QUOTE_NOT_FOUND", "Quote not found.", 404)

    payload = qa.read_quote_payload(quote_id)
    if payload is None:
        return _err("QUOTE_NOT_FOUND", "Quote not found.", 404)
    status_payload = qa.read_quote_status(quote_id)

    # US-IQ-03 (branche entretien) : les sujets confidentiels flaggés doivent
    # être récupérables via l'API admin — best-effort, n'échoue jamais le
    # détail du devis si la session intake est absente/injoignable.
    intake_summary = None
    intake_session_id = (payload or {}).get("intake_session_id")
    if intake_session_id:
        try:
            session = intake_service.get_session(intake_session_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_quote_admin: intake session lookup failed for %s: %s", intake_session_id, exc.__class__.__name__)
            session = None
        if session:
            intake_summary = {
                "session_id": intake_session_id,
                "state": session.get("state"),
                "route": session.get("route"),
                "confidential_flags": session.get("confidential_flags") or [],
            }

    return jsonify({
        "success": True,
        "data": {
            "quote_id": quote_id,
            "payload": payload,
            "status": status_payload,
            "intake": intake_summary,
        },
    }), 200


@admin_quote_bp.route("/<quote_id>/status", methods=["PATCH"])
@require_super_admin
def patch_quote_status(quote_id: str):
    """Transition de statut + maj éventuelle de payment_link / notes / delivered_url.

    Body JSON :
      ``{"status": "...", "notes": "...", "payment_link": "...", "delivered_url": "..."}``
    """
    body = request.get_json(silent=True) or {}
    new_status = body.get("status")
    notes = body.get("notes")
    payment_link = body.get("payment_link")
    delivered_url = body.get("delivered_url")

    if not isinstance(new_status, str):
        return _err("INVALID_BODY", "Field `status` is required.", 400)

    ok, code, payload = qa.update_quote_status(
        quote_id,
        new_status=new_status,
        by_email=_current_admin_email(),
        notes=notes if isinstance(notes, str) else None,
        payment_link=payment_link if isinstance(payment_link, str) else None,
        delivered_url=delivered_url if isinstance(delivered_url, str) else None,
    )
    if not ok:
        if code == "QUOTE_NOT_FOUND":
            return _err(code, "Quote not found.", 404)
        if code == "INVALID_STATUS":
            return _err(code, "Status is not in the allowed enum.", 400)
        if code == "INVALID_TRANSITION":
            return _err(code, "Status transition not allowed.", 409)
        return _err(code, "Could not update quote status.", 500)

    return jsonify({"success": True, "data": {"status": payload}}), 200


@admin_quote_bp.route("/<quote_id>/notes", methods=["PATCH"])
@require_super_admin
def patch_quote_notes(quote_id: str):
    """Mise à jour des notes admin (sans transition de statut)."""
    body = request.get_json(silent=True) or {}
    notes = body.get("notes")
    if not isinstance(notes, str):
        return _err("INVALID_BODY", "Field `notes` (string) is required.", 400)
    ok, code, payload = qa.update_quote_notes(quote_id, notes=notes)
    if not ok:
        if code == "QUOTE_NOT_FOUND":
            return _err(code, "Quote not found.", 404)
        return _err(code, "Could not update notes.", 500)
    return jsonify({"success": True, "data": {"status": payload}}), 200


# ─── Email actions (US-104) ─────────────────────────────────────────────────


_PACKAGE_LABELS_FR = {
    "crisis_drill_24h": "Stress-test 24 h",
    "policy_brief_stress": "Note de cadrage politique",
    "pre_launch_adcheck": "Vérif pré-lancement",
    "custom": "Analyse sur mesure",
}


def _format_email_block(text: Optional[str]) -> str:
    """Formate une éventuelle ``custom_message`` en HTML inline pour le template.

    Retourne une chaîne vide si pas de message — le template substitue
    ``{custom_message_block}`` directement.
    """
    if not text or not isinstance(text, str):
        return ""
    safe = (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
    )
    return (
        "<div style='margin-top:16px;padding:14px 16px;background:#FFF1EC;"
        "border-inline-start:3px solid #FF8551;border-radius:6px;font-size:14px;color:#3a2e29;'>"
        f"{safe}</div>"
    )


def _client_email_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "full_name": payload.get("full_name") or "—",
        "company": payload.get("company") or "—",
        "quote_id": payload.get("quote_id") or "",
        "package_label": _PACKAGE_LABELS_FR.get(
            payload.get("package") or "", payload.get("package") or "Bassira"
        ),
    }


@admin_quote_bp.route("/<quote_id>/send-payment-link", methods=["POST"])
@require_super_admin
def send_payment_link(quote_id: str):
    """Envoie l'email Stripe Payment Link au client + transition → ``quoted``.

    Body JSON : ``{"payment_link": "https://buy.stripe.com/...", "custom_message": "..."}``
    """
    from ..services.email_service import render_template, send_email

    body = request.get_json(silent=True) or {}
    payment_link = body.get("payment_link")
    custom_message = body.get("custom_message")

    if not isinstance(payment_link, str) or not payment_link.strip().startswith("http"):
        return _err(
            "INVALID_BODY",
            "Field `payment_link` must be a valid http(s) URL.",
            400,
        )

    payload = qa.read_quote_payload(quote_id)
    if payload is None:
        return _err("QUOTE_NOT_FOUND", "Quote not found.", 404)
    client_email = payload.get("email")
    if not client_email:
        return _err("MISSING_EMAIL", "Quote has no client email — cannot send.", 400)

    ctx = _client_email_context(payload)
    ctx["payment_link"] = payment_link.strip()
    ctx["custom_message_block"] = _format_email_block(custom_message)

    html_body = render_template("quote_payment_link", ctx)
    sent = send_email(
        to_email=client_email,
        subject=f"Bassira — Votre devis {ctx['package_label']} est prêt",
        html_body=html_body,
        reply_to="contact@ai-mpower.com",
    )

    # Transition statut → quoted (en restant fail-soft si déjà au-delà).
    now_iso = qa._iso_now()
    current = qa.read_quote_status(quote_id)
    if qa.is_valid_transition(current["status"], "quoted"):
        qa.update_quote_status(
            quote_id,
            new_status="quoted",
            by_email=_current_admin_email(),
            notes=(custom_message if isinstance(custom_message, str) else None),
            payment_link=payment_link.strip(),
            last_email_sent_at=now_iso,
        )
    else:
        # Statut déjà à `quoted` ou plus loin — on stocke juste les méta.
        # On utilise update_quote_status avec idempotence (current==new).
        qa.update_quote_status(
            quote_id,
            new_status=current["status"],
            by_email=_current_admin_email(),
            notes=(custom_message if isinstance(custom_message, str) else None),
            payment_link=payment_link.strip(),
            last_email_sent_at=now_iso,
        )

    return jsonify({
        "success": True,
        "data": {
            "email_sent": bool(sent),
            "status": qa.read_quote_status(quote_id),
        },
    }), 200


@admin_quote_bp.route("/<quote_id>/send-delivered", methods=["POST"])
@require_super_admin
def send_delivered(quote_id: str):
    """Envoie l'email de livraison + transition → ``delivered``.

    Body JSON : ``{"delivered_url": "https://notion.so/...", "custom_message": "..."}``
    """
    from ..services.email_service import render_template, send_email

    body = request.get_json(silent=True) or {}
    delivered_url = body.get("delivered_url")
    custom_message = body.get("custom_message")

    if not isinstance(delivered_url, str) or not delivered_url.strip().startswith("http"):
        return _err(
            "INVALID_BODY",
            "Field `delivered_url` must be a valid http(s) URL.",
            400,
        )

    payload = qa.read_quote_payload(quote_id)
    if payload is None:
        return _err("QUOTE_NOT_FOUND", "Quote not found.", 404)
    client_email = payload.get("email")
    if not client_email:
        return _err("MISSING_EMAIL", "Quote has no client email — cannot send.", 400)

    ctx = _client_email_context(payload)
    ctx["delivered_url"] = delivered_url.strip()
    ctx["custom_message_block"] = _format_email_block(custom_message)

    html_body = render_template("quote_delivered", ctx)
    sent = send_email(
        to_email=client_email,
        subject=f"Bassira — Votre rapport {ctx['package_label']} est livré",
        html_body=html_body,
        reply_to="contact@ai-mpower.com",
    )

    now_iso = qa._iso_now()
    current = qa.read_quote_status(quote_id)
    if qa.is_valid_transition(current["status"], "delivered"):
        ok, code, _ = qa.update_quote_status(
            quote_id,
            new_status="delivered",
            by_email=_current_admin_email(),
            notes=(custom_message if isinstance(custom_message, str) else None),
            delivered_url=delivered_url.strip(),
            last_email_sent_at=now_iso,
        )
        if not ok:
            return _err(code, "Could not transition to delivered.", 409)
    else:
        # Idempotent : déjà delivered ou statut incompatible (déclined etc.).
        qa.update_quote_status(
            quote_id,
            new_status=current["status"],
            by_email=_current_admin_email(),
            notes=(custom_message if isinstance(custom_message, str) else None),
            delivered_url=delivered_url.strip(),
            last_email_sent_at=now_iso,
        )

    return jsonify({
        "success": True,
        "data": {
            "email_sent": bool(sent),
            "status": qa.read_quote_status(quote_id),
        },
    }), 200


# ─── Admin Intake — escalades + playbook (ADR-IQ-08) ────────────────────────


@admin_quote_bp.route("/intake/escalations", methods=["GET"])
@require_super_admin
def list_intake_escalations():
    """Liste les escalades de l'agent Intake (ADR-IQ-08). Query :
    ``unreviewed_only`` (bool, default false)."""
    unreviewed_only = (request.args.get("unreviewed_only") or "").lower() in ("1", "true", "yes")
    items, total = intake_service.list_escalations(unreviewed_only=unreviewed_only)
    return jsonify({"success": True, "data": {"escalations": items, "total": total}}), 200


@admin_quote_bp.route("/intake/escalations/<escalation_id>", methods=["PATCH"])
@require_super_admin
def patch_intake_escalation(escalation_id: str):
    """Marque une escalade comme revue. Body : ``{"reviewer_note": "..."}`` optionnel."""
    body = request.get_json(silent=True) or {}
    note = body.get("reviewer_note")
    status, payload = intake_service.mark_escalation_reviewed(
        escalation_id, reviewer_note=note if isinstance(note, str) else None,
    )
    return jsonify(payload), status


@admin_quote_bp.route("/intake/playbook", methods=["GET"])
@require_super_admin
def list_intake_playbook():
    """Liste toutes les entrées du playbook (actives et inactives)."""
    items, total = intake_service.list_playbook_entries()
    return jsonify({"success": True, "data": {"entries": items, "total": total}}), 200


@admin_quote_bp.route("/intake/playbook", methods=["POST"])
@require_super_admin
def post_intake_playbook():
    """Ajoute une correction au playbook. Body :
    ``{"situation_pattern": "...", "corrected_response": "..."}``."""
    body = request.get_json(silent=True) or {}
    status, payload = intake_service.create_playbook_entry(
        situation_pattern=body.get("situation_pattern") or "",
        corrected_response=body.get("corrected_response") or "",
        added_by=_current_admin_email() or "unknown",
    )
    return jsonify(payload), status


@admin_quote_bp.route("/intake/playbook/<entry_id>", methods=["PATCH"])
@require_super_admin
def patch_intake_playbook(entry_id: str):
    """Active/désactive une entrée. Body : ``{"active": true|false}``."""
    body = request.get_json(silent=True) or {}
    active = body.get("active")
    if not isinstance(active, bool):
        return _err("MISSING_FIELD", "Field `active` (boolean) is required.", 400)
    status, payload = intake_service.set_playbook_entry_active(entry_id, active=active)
    return jsonify(payload), status
