"""Service du module Intake — parcours de qualification /devis (US-IQ-01).

Remplace le formulaire de contact `/devis` par le parcours structuré « 3
temps » (A1-A8, docs/intake/01-intake-spec.md). Deux opérations exposées :

  * ``start_session(locale, entry_door)`` — démarre une ``intake_sessions``
    row (state='started'), avant toute réponse.
  * ``submit_form(session_id, payload)`` — valide le formulaire A1-A8 +
    identité, construit le brief structuré, écrit ``intake_sessions``
    (state='form_submitted') ET ``quote_ownership`` (rétrocompatibilité
    admin console — même mécanisme que ``quote_service.submit_quote``).

Validation manuelle (pas de dépendance ``jsonschema`` — cohérent avec
``quote_service._validate_payload``, aucun échelon Ponytail inférieur ne
suffisant n'a été identifié pour justifier la dépendance). A1/A2/A7 sont
bloquants côté serveur : un payload aussi pauvre que ``q_f767321b``
(2026-07-09, la donnée qui a motivé ce chantier) devient impossible par
construction.

Supabase est la SEULE source de vérité (pas de fallback filesystem — le
module Intake est postérieur à la leçon US-203 : « aucune donnée
persistante sur volume éphémère »). Une panne Supabase retourne 503.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..auth.supabase_client import SupabaseConfigError, get_default_super_admin_org_id, get_supabase_admin
from ..utils.logger import get_logger
from . import quote_ownership as qo

logger = get_logger("miroshark.intake")


_VALID_LOCALES = {"fr", "en", "ar"}
_VALID_ENTRY_DOORS = {"standard", "aar"}
_VALID_GOVERNANCE = {"solo", "comite_direction", "conseil_administration", "tutelle", "investisseurs"}
_VALID_PAST_METHOD = {"etude", "conseil", "sondage_interne", "instinct", "rien"}
_VALID_BUDGET_BRACKET = {"lt_1m", "1_10m", "10_100m", "gt_100m"}
_VALID_EXPOSURE = {"interne", "sectorielle", "nationale", "internationale"}
_VALID_DATA_ASSETS = {"etudes", "donnees_clients", "verbatims", "rien"}

_MIN_DECISION_LEN = 15
_MIN_OPTIONS = 2
_MAX_OPTIONS = 4

BRIEF_VERSION = "1"


def _err(code: str, message: str) -> Tuple[Optional[str], Optional[str]]:
    return code, message


# ─── Étape 1 : démarrage de session ──────────────────────────────────────────


def start_session(
    *,
    locale: str = "fr",
    entry_door: str = "standard",
    client: Any = None,
) -> Dict[str, Any]:
    """Crée une ``intake_sessions`` row (state='started') et la retourne.

    ``locale``/``entry_door`` hors énumération retombent silencieusement
    sur les défauts ('fr' / 'standard') — un query param mal formé ne
    doit jamais faire échouer le démarrage d'un parcours public.
    """
    if locale not in _VALID_LOCALES:
        locale = "fr"
    if entry_door not in _VALID_ENTRY_DOORS:
        entry_door = "standard"

    cli = client or get_supabase_admin()
    row = {
        "state": "started",
        "locale": locale,
        "entry_door": entry_door,
    }
    response = cli.table("intake_sessions").insert(row).execute()
    rows = getattr(response, "data", None) or []
    if not rows:
        raise RuntimeError("intake_sessions insert returned no row")
    created = rows[0]
    return {
        "session_id": created["id"],
        "state": created["state"],
        "locale": created["locale"],
        "entry_door": created["entry_door"],
    }


# ─── Étape 2 : validation du formulaire A1-A8 + identité ────────────────────


def _validate_form(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Retourne ``(error_code, error_message)`` si invalide, sinon ``(None, None)``.

    Contrat : identité à plat (``full_name``/``email``/``company``/
    ``consent_rgpd``), questions A1-A8 imbriquées sous ``payload["brief"]``
    — un objet qui correspond 1:1 à la colonne ``intake_sessions.brief``.
    Ordre des checks : identité d'abord, puis A1 → A8 dans l'ordre du
    parcours (le message d'erreur pointe vers le premier écran fautif).
    """
    if not isinstance(payload, dict):
        return _err("MISSING_FIELD", "Invalid request body.")

    for field in ("full_name", "email", "company"):
        raw = payload.get(field)
        if not isinstance(raw, str) or not raw.strip():
            return _err("MISSING_FIELD", f"Field « {field} » is required.")

    if payload.get("consent_rgpd") is not True:
        return _err("RGPD_NOT_ACCEPTED", "RGPD consent is required to process the request.")

    brief = payload.get("brief")
    if not isinstance(brief, dict):
        return _err("MISSING_FIELD", "Field « brief » is required.")

    # A1 — décision, bloquant, >= 15 caractères.
    decision = brief.get("decision")
    if not isinstance(decision, str) or len(decision.strip()) < _MIN_DECISION_LEN:
        return _err(
            "A1_TOO_SHORT",
            f"Field « brief.decision » (A1) must be at least {_MIN_DECISION_LEN} characters.",
        )

    # A2 — options, bloquant, 2 à 4 éléments non vides.
    options = brief.get("options")
    if not isinstance(options, list):
        return _err("A2_INVALID", "Field « brief.options » (A2) must be an array.")
    clean_options = [o.strip() for o in options if isinstance(o, str) and o.strip()]
    if len(clean_options) < _MIN_OPTIONS:
        return _err(
            "A2_TOO_FEW",
            f"Field « brief.options » (A2) requires at least {_MIN_OPTIONS} non-empty entries.",
        )
    if len(clean_options) > _MAX_OPTIONS:
        clean_options = clean_options[:_MAX_OPTIONS]

    # A3 — échéance + gouvernance (non bloquant sur la date, gouvernance validée si fournie).
    governance = brief.get("governance")
    if governance is not None and governance not in _VALID_GOVERNANCE:
        return _err("A3_INVALID_GOVERNANCE", f"Field « brief.governance » (A3) has an unknown value: {governance!r}.")

    # A4 — méthode passée, optionnelle mais validée si fournie (multi-sélection).
    past_method = brief.get("past_method") or []
    if not isinstance(past_method, list) or any(
        m not in _VALID_PAST_METHOD for m in past_method
    ):
        return _err("A4_INVALID", "Field « brief.past_method » (A4) contains an unknown value.")

    # A6 — enjeu (stakes), validé si fourni.
    stakes = brief.get("stakes") or {}
    budget_bracket = stakes.get("budget_bracket")
    if budget_bracket is not None and budget_bracket not in _VALID_BUDGET_BRACKET:
        return _err("A6_INVALID_BUDGET", f"Field « brief.stakes.budget_bracket » (A6) has an unknown value: {budget_bracket!r}.")
    exposure = stakes.get("exposure")
    if exposure is not None and exposure not in _VALID_EXPOSURE:
        return _err("A6_INVALID_EXPOSURE", f"Field « brief.stakes.exposure » (A6) has an unknown value: {exposure!r}.")

    # A7 — géo, BLOQUANT (remplace le geo_focus actuellement vide).
    geo = brief.get("geo")
    if not isinstance(geo, list) or len(geo) == 0:
        return _err("A7_REQUIRED", "Field « brief.geo » (A7) is required — at least one country + segment.")
    for entry in geo:
        if not isinstance(entry, dict) or not entry.get("country") or not entry.get("segment"):
            return _err("A7_INVALID", "Field « brief.geo » (A7) entries require « country » and « segment ».")

    # A8 — data assets, validé si fourni.
    data_assets = brief.get("data_assets") or []
    if not isinstance(data_assets, list) or any(
        d not in _VALID_DATA_ASSETS for d in data_assets
    ):
        return _err("A8_INVALID", "Field « brief.data_assets » (A8) contains an unknown value.")

    return None, None


def _build_brief(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Construit le brief structuré (schéma docs/intake/02-data-dictionary-delta.md)
    à partir d'un ``payload["brief"]`` déjà validé par ``_validate_form``.
    """
    brief_in = payload.get("brief") or {}
    options = [o.strip() for o in (brief_in.get("options") or []) if isinstance(o, str) and o.strip()][:_MAX_OPTIONS]
    deadline = brief_in.get("deadline") or {}
    stakes = brief_in.get("stakes") or {}
    jobs_raw = stakes.get("jobs")
    jobs = int(jobs_raw) if isinstance(jobs_raw, (int, float)) and not isinstance(jobs_raw, bool) else None
    return {
        "decision": brief_in["decision"].strip(),
        "options": options,
        "deadline": {
            "date": deadline.get("date") if isinstance(deadline.get("date"), str) else None,
            "overdue": bool(deadline.get("overdue")),
        },
        "governance": brief_in.get("governance"),
        "past_method": [m for m in (brief_in.get("past_method") or []) if m in _VALID_PAST_METHOD],
        "past_gap": (brief_in.get("past_gap") or "").strip() or None,
        "stakes": {
            "budget_bracket": stakes.get("budget_bracket"),
            "jobs": jobs,
            "exposure": stakes.get("exposure"),
        },
        "geo": [
            {"country": e.get("country"), "segment": e.get("segment")}
            for e in (brief_in.get("geo") or [])
            if isinstance(e, dict) and e.get("country") and e.get("segment")
        ],
        "data_assets": [d for d in (brief_in.get("data_assets") or []) if d in _VALID_DATA_ASSETS],
        "aar_known_outcome": (brief_in.get("aar_known_outcome") or "").strip() or None,
        "agent_insights": [],
        "brief_version": BRIEF_VERSION,
    }


def _get_session(session_id: str, *, client: Any) -> Optional[Dict[str, Any]]:
    response = (
        client.table("intake_sessions")
        .select("*")
        .eq("id", session_id)
        .limit(1)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    return rows[0] if rows else None


def submit_form(
    session_id: str,
    payload: Dict[str, Any],
    *,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    client: Any = None,
) -> Tuple[int, Dict[str, Any]]:
    """Valide + persiste le formulaire A1-A8. Retourne ``(http_status, body)``.

    Écrit ``intake_sessions`` (brief, state='form_submitted', quote_id) ET
    ``quote_ownership`` (rétrocompatibilité admin console — même mécanisme
    que ``quote_service._persist_quote_supabase``, sans passer par la
    validation stricte de ``submit_quote`` qui exige un ``package`` de
    l'ancien enum).
    """
    if not session_id or not isinstance(session_id, str):
        return 400, {"success": False, "error_code": "MISSING_FIELD", "error": "session_id is required."}

    error_code, error_msg = _validate_form(payload)
    if error_code is not None:
        return 400, {"success": False, "error_code": error_code, "error": error_msg}

    cli = client or get_supabase_admin()

    try:
        session = _get_session(session_id, client=cli)
    except Exception as exc:  # noqa: BLE001
        logger.error("submit_form: session lookup failed for %s: %s", session_id, exc.__class__.__name__)
        return 503, {"success": False, "error_code": "SUPABASE_UNAVAILABLE", "error": "Could not reach storage."}

    if session is None:
        return 404, {"success": False, "error_code": "SESSION_NOT_FOUND", "error": "Intake session not found."}
    if session["state"] != "started":
        return 409, {
            "success": False,
            "error_code": "INVALID_STATE",
            "error": f"Session is in state {session['state']!r}, expected 'started'.",
        }

    brief = _build_brief(payload)
    quote_id = f"q_{uuid.uuid4().hex[:8]}"

    # Rétrocompatibilité admin console (US-IQ-01 acceptance criteria) :
    # une ligne quote_ownership « comme aujourd'hui », org par défaut si
    # aucune org explicite (mode public — même fallback que quote_service).
    try:
        target_org_id = get_default_super_admin_org_id(cli)
    except SupabaseConfigError:
        target_org_id = None
    except Exception as exc:  # noqa: BLE001
        logger.warning("submit_form: default org lookup failed: %s", exc.__class__.__name__)
        target_org_id = None

    quote_linked = False
    if target_org_id:
        try:
            qo.link_quote_to_org(
                quote_id,
                target_org_id,
                customer_email=payload.get("email"),
                package_id=None,
                status="received",
                payload={
                    "full_name": payload.get("full_name"),
                    "email": payload.get("email"),
                    "company": payload.get("company"),
                    "intake_session_id": session_id,
                    "brief_summary": brief["decision"][:200],
                    "client_ip": (client_ip or "")[:64],
                    "user_agent": (user_agent or "")[:200],
                },
                client=cli,
            )
            quote_linked = True
        except Exception as exc:  # noqa: BLE001 — rétrocompat best-effort, ne bloque pas le parcours
            logger.warning("submit_form: quote_ownership link failed for %s: %s", quote_id, exc.__class__.__name__)

    update_row: Dict[str, Any] = {
        "state": "form_submitted",
        "brief": brief,
    }
    if quote_linked:
        update_row["quote_id"] = quote_id

    try:
        cli.table("intake_sessions").update(update_row).eq("id", session_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.error("submit_form: intake_sessions update failed for %s: %s", session_id, exc.__class__.__name__)
        return 503, {"success": False, "error_code": "SUPABASE_UNAVAILABLE", "error": "Could not persist the form."}

    return 200, {
        "success": True,
        "data": {
            "session_id": session_id,
            "state": "form_submitted",
            "quote_id": quote_id if quote_linked else None,
        },
    }
