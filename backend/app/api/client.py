"""Endpoints client multitenant Bassira (US-092).

Ce blueprint expose les routes consommées par le **frontend client
authentifié** (dashboard organisationnel) :

  - GET  /api/client/auth/me                          — profil + orgs
  - GET  /api/client/simulations                      — liste org-scopée
  - POST /api/client/simulations                      — création scopée
  - POST /api/client/simulations/<sim_id>/outcome     — marquage outcome
  - POST /api/client/simulations/<sim_id>/publish     — publication

Toutes les routes ci-dessus sont protégées par un JWT Supabase. Les
endpoints d'écriture critiques (`outcome`, `publish`) requièrent un
rôle `admin` ou `owner` dans l'organisation cible. Cf.
``app.auth.decorators`` pour la mécanique exacte.

L'endpoint public `GET /api/calibration/aggregates` est défini dans le
blueprint `calibration_bp` séparé (cf. `api/calibration.py`).
"""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, g, jsonify, request

from ..auth.decorators import (
    require_auth,
    require_org_membership,
    require_owner_or_admin,
)
from ..auth.supabase_client import (
    SupabaseConfigError,
    get_user_orgs,
    mark_outcome as _mark_outcome,
    publish_simulation as _publish_simulation,
    get_simulation_owner,
)
from ..services.simulation_manager import SimulationManager
from ..utils.logger import get_logger


client_bp = Blueprint("client", __name__)
logger = get_logger("miroshark.api.client")


# ─── Helpers ────────────────────────────────────────────────────────────────

def _err(code: str, message: str, status: int):
    """Réponse d'erreur API standard (cohérent avec le reste du backend)."""
    return jsonify({
        "success": False,
        "error_code": code,
        "error": message,
    }), status


def _json_body() -> Dict[str, Any]:
    """Récupère un body JSON tolérant aux requêtes vides."""
    return request.get_json(silent=True) or {}


# ─── /auth/me ───────────────────────────────────────────────────────────────

@client_bp.route("/auth/me", methods=["GET"])
@require_auth
def auth_me():
    """Retourne le profil + organisations auxquelles l'utilisateur appartient.

    Le frontend appelle cet endpoint juste après login pour afficher le
    sélecteur d'organisation et alimenter le dashboard. Si la config
    Supabase admin est manquante côté backend, on retourne 503 explicite.
    """
    user = getattr(g, "current_user", None) or {}
    user_id = user.get("id")
    if not user_id:
        return _err("INVALID_TOKEN", "Token missing 'sub' claim.", 401)

    try:
        orgs = get_user_orgs(user_id)
    except SupabaseConfigError as exc:
        logger.error("Supabase admin config missing: %s", exc)
        return _err(
            "SUPABASE_NOT_CONFIGURED",
            "Backend Supabase admin client is not configured.",
            503,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("auth_me failed: %s", exc.__class__.__name__)
        return _err(
            "INTERNAL_AUTH_ERROR",
            "Could not resolve user organizations.",
            500,
        )

    return jsonify({
        "success": True,
        "data": {
            "user_id": user_id,
            "email": user.get("email"),
            "orgs": [
                {
                    "id": o.get("id"),
                    "slug": o.get("slug"),
                    "name": o.get("name"),
                    "sector": o.get("sector"),
                    "country_code": o.get("country_code"),
                    "role": o.get("role"),
                    # US-098 — flag toggle self-service par org
                    "self_service_enabled": bool(o.get("self_service_enabled", False)),
                }
                for o in orgs
            ],
        },
    }), 200


# ─── /simulations (liste) ───────────────────────────────────────────────────

@client_bp.route("/simulations", methods=["GET"])
@require_org_membership(role_min="member")
def list_org_simulations():
    """Liste les simulations de l'organisation courante (US-092)."""
    org = getattr(g, "current_org", None) or {}
    org_id = org.get("id")
    if not org_id:
        return _err("ORG_RESOLUTION_FAILED", "Could not resolve current org.", 500)

    try:
        sm = SimulationManager()
        sims = sm.list_simulations_for_org(org_id)
    except SupabaseConfigError as exc:
        logger.error("Supabase admin config missing: %s", exc)
        return _err(
            "SUPABASE_NOT_CONFIGURED",
            "Backend Supabase admin client is not configured.",
            503,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("list_org_simulations failed: %s", exc.__class__.__name__)
        return _err(
            "INTERNAL_ERROR",
            "Could not list simulations for organization.",
            500,
        )

    return jsonify({
        "success": True,
        "data": {
            "org_id": org_id,
            "simulations": sims,
        },
    }), 200


# ─── /simulations (création) ────────────────────────────────────────────────

@client_bp.route("/simulations", methods=["POST"])
@require_org_membership(role_min="member")
def create_org_simulation():
    """Crée une simulation rattachée à l'organisation courante.

    Body JSON (tous optionnels sauf indication) :
        - project_id : str (requis)
        - graph_id : str (requis)
        - package_id : str | None — slug du package (ex. ``crisis-drill-24h``)
        - enable_twitter : bool = True
        - enable_reddit : bool = True
        - enable_polymarket : bool = False
        - polymarket_market_count : int = 1
    """
    body = _json_body()
    project_id = (body.get("project_id") or "").strip()
    graph_id = (body.get("graph_id") or "").strip()
    if not project_id or not graph_id:
        return _err(
            "MISSING_FIELDS",
            "`project_id` and `graph_id` are required.",
            400,
        )

    org = getattr(g, "current_org", None) or {}
    user = getattr(g, "current_user", None) or {}
    org_id = org.get("id")
    user_id = user.get("id")

    try:
        sm = SimulationManager()
        state = sm.create_simulation(
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=bool(body.get("enable_twitter", True)),
            enable_reddit=bool(body.get("enable_reddit", True)),
            enable_polymarket=bool(body.get("enable_polymarket", False)),
            polymarket_market_count=int(body.get("polymarket_market_count", 1) or 1),
            org_id=org_id,
            created_by=user_id,
            package_id=(body.get("package_id") or None),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("create_org_simulation failed: %s", exc.__class__.__name__)
        return _err(
            "INTERNAL_ERROR",
            "Could not create simulation.",
            500,
        )

    return jsonify({
        "success": True,
        "data": {
            "simulation_id": state.simulation_id,
            "status": state.status.value,
            "org_id": org_id,
            "package_id": body.get("package_id"),
        },
    }), 201


# ─── /simulations/<id>/outcome ──────────────────────────────────────────────

@client_bp.route("/simulations/<simulation_id>/outcome", methods=["POST"])
@require_owner_or_admin
def post_outcome(simulation_id: str):
    """Marque l'outcome d'une simulation appartenant à l'org courante.

    Body JSON :
        - label : `called_it` | `partial` | `wrong` (requis)
        - observed_at : ISO 8601 (requis)
        - source_url : URL publique (optionnel)
        - brier_score : float dans [0, 1] (optionnel)
    """
    body = _json_body()
    label = (body.get("label") or "").strip()
    observed_at = (body.get("observed_at") or "").strip()
    source_url = body.get("source_url")
    brier_score = body.get("brier_score")

    if label not in {"called_it", "partial", "wrong"}:
        return _err(
            "INVALID_LABEL",
            "`label` must be one of called_it | partial | wrong.",
            400,
        )
    if not observed_at:
        return _err(
            "MISSING_FIELDS",
            "`observed_at` is required (ISO 8601).",
            400,
        )

    if brier_score is not None:
        try:
            brier_score = float(brier_score)
        except (TypeError, ValueError):
            return _err(
                "INVALID_BRIER",
                "`brier_score` must be a numeric value in [0, 1].",
                400,
            )
        if not (0.0 <= brier_score <= 1.0):
            return _err(
                "INVALID_BRIER",
                "`brier_score` must be in [0, 1].",
                400,
            )

    org = getattr(g, "current_org", None) or {}
    user = getattr(g, "current_user", None) or {}
    org_id = org.get("id")

    try:
        owner = get_simulation_owner(simulation_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("get_simulation_owner failed: %s", exc.__class__.__name__)
        return _err("INTERNAL_ERROR", "Could not resolve simulation owner.", 500)

    if owner is None:
        return _err(
            "SIMULATION_NOT_OWNED",
            "Simulation has no ownership record — cannot mark outcome.",
            404,
        )
    if str(owner.get("org_id")) != str(org_id):
        return _err(
            "FORBIDDEN_ORG",
            "Simulation does not belong to the current organization.",
            403,
        )

    try:
        _mark_outcome(
            simulation_id=simulation_id,
            label=label,
            observed_at=observed_at,
            source_url=(source_url.strip() if isinstance(source_url, str) else None),
            brier_score=brier_score,
            marker_user_id=user.get("id"),
        )
    except ValueError as exc:
        return _err("INVALID_LABEL", str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        logger.error("mark_outcome failed: %s", exc.__class__.__name__)
        return _err("INTERNAL_ERROR", "Could not mark outcome.", 500)

    return jsonify({
        "success": True,
        "data": {
            "simulation_id": simulation_id,
            "label": label,
            "observed_at": observed_at,
            "brier_score": brier_score,
        },
    }), 200


# ─── /simulations/<id>/publish ──────────────────────────────────────────────

@client_bp.route("/simulations/<simulation_id>/publish", methods=["POST"])
@require_owner_or_admin
def post_publish(simulation_id: str):
    """Bascule `is_published = true` pour exposer la sim dans la VIEW agrégée.

    L'authentification valide qu'on est admin/owner de l'org propriétaire.
    """
    org = getattr(g, "current_org", None) or {}
    user = getattr(g, "current_user", None) or {}
    org_id = org.get("id")

    try:
        owner = get_simulation_owner(simulation_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("get_simulation_owner failed: %s", exc.__class__.__name__)
        return _err("INTERNAL_ERROR", "Could not resolve simulation owner.", 500)

    if owner is None:
        return _err(
            "SIMULATION_NOT_OWNED",
            "Simulation has no ownership record — cannot publish.",
            404,
        )
    if str(owner.get("org_id")) != str(org_id):
        return _err(
            "FORBIDDEN_ORG",
            "Simulation does not belong to the current organization.",
            403,
        )

    try:
        _publish_simulation(
            simulation_id=simulation_id,
            marker_user_id=user.get("id"),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("publish_simulation failed: %s", exc.__class__.__name__)
        return _err("INTERNAL_ERROR", "Could not publish simulation.", 500)

    return jsonify({
        "success": True,
        "data": {
            "simulation_id": simulation_id,
            "is_published": True,
        },
    }), 200
