"""US-B01 — Endpoints recherche dynamique seed → topics + briefs.

Deux routes publiques côté Bassira, gardées par ``@require_auth`` car
chaque appel déclenche en aval un pipeline Kairos ~170 s (coûteux). Le
JWT vient de Supabase Auth via le store Pinia côté frontend.

  * ``POST /api/research/from-seed`` — soumet une graine, retourne
    ``session_id`` + ``status='running'`` en <1 s (Kairos en background
    via ``EdgeRuntime.waitUntil``).
  * ``GET /api/research/status?session_id=<uuid>`` — polling, retourne
    le payload Kairos avec ``status ∈ {running, completed, failed, timeout}``
    et ``result`` quand complet.

Caching transparent (cf. ``services.kairos_proxy``) :
  * POST : la même (seed, lang, sector, depth) est cachée 1h pour
    éviter de re-trigger un pipeline si l'user re-clique.
  * GET : payload ``completed`` cacheable 24h pour absorber le TTL
    Kairos.

Erreurs Kairos sont relayées avec leur ``error_code`` d'origine quand
possible (validation 400) et masquées derrière des codes Bassira pour
les pannes infra (502/503/504).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, jsonify, request

from ..auth.decorators import require_auth
from ..services import kairos_proxy as kx


research_bp = Blueprint("research", __name__)
logger = logging.getLogger("miroshark.api.research")


# ─── Helpers ──────────────────────────────────────────────────────────────────


_ALLOWED_LANGS = frozenset({"fr", "en", "ar"})
_SEED_MIN = 50
_SEED_MAX = 3000
_SCOPE_PROFILE_RE = __import__("re").compile(r"^[a-zA-Z0-9_-]{1,80}$")


def _err(code: str, message: str, status: int, detail: Optional[Dict] = None):
    body: Dict[str, Any] = {"success": False, "error_code": code, "error": message}
    if detail:
        body["detail"] = detail
    return jsonify(body), status


def _parse_seed_payload(
    payload: Dict[str, Any],
) -> Tuple[
    str,
    str,
    Optional[str],
    Optional[int],
    Optional[str],
    Optional[Dict[str, Any]],
]:
    """Valide les champs attendus, lève KairosError 400 si invalide.

    Retourne (seed, lang, sector_hint, depth_hint, scope_profile, hints_override).
    """
    seed = (payload.get("seed") or "").strip()
    lang = (payload.get("lang") or "").strip().lower()
    sector = payload.get("sector_hint")
    depth = payload.get("depth_hint")
    scope_profile = payload.get("scope_profile")
    hints_override = payload.get("hints_override")

    if not seed:
        raise kx.KairosError("SEED_REQUIRED", "seed is required.", 400)
    if len(seed) < _SEED_MIN:
        raise kx.KairosError(
            "SEED_TOO_SHORT",
            f"seed must be at least {_SEED_MIN} characters.",
            400,
        )
    if len(seed) > _SEED_MAX:
        raise kx.KairosError(
            "SEED_TOO_LONG",
            f"seed must be at most {_SEED_MAX} characters.",
            400,
        )
    if lang not in _ALLOWED_LANGS:
        raise kx.KairosError(
            "LANG_UNSUPPORTED",
            f"lang must be one of {sorted(_ALLOWED_LANGS)}.",
            400,
        )
    sector_str: Optional[str] = None
    if sector is not None:
        sector_str = str(sector).strip() or None
    depth_int: Optional[int] = None
    if depth is not None:
        try:
            depth_int = int(depth)
        except (TypeError, ValueError) as exc:
            raise kx.KairosError(
                "DEPTH_HINT_INVALID",
                "depth_hint must be 0, 1, or 2.",
                400,
            ) from exc
        if depth_int not in (0, 1, 2):
            raise kx.KairosError(
                "DEPTH_HINT_INVALID",
                "depth_hint must be 0, 1, or 2.",
                400,
            )

    scope_profile_str: Optional[str] = None
    if scope_profile is not None:
        if not isinstance(scope_profile, str):
            raise kx.KairosError(
                "SCOPE_PROFILE_INVALID",
                "scope_profile must be a string (name or uuid).",
                400,
            )
        scope_profile_clean = scope_profile.strip()
        if scope_profile_clean and not _SCOPE_PROFILE_RE.match(scope_profile_clean):
            raise kx.KairosError(
                "SCOPE_PROFILE_INVALID",
                "scope_profile must match [a-zA-Z0-9_-]{1,80}.",
                400,
            )
        scope_profile_str = scope_profile_clean or None

    hints_override_clean: Optional[Dict[str, Any]] = None
    if hints_override is not None:
        if not isinstance(hints_override, dict):
            raise kx.KairosError(
                "HINTS_OVERRIDE_INVALID",
                "hints_override must be an object.",
                400,
            )
        # Validation surface — Kairos refait sa propre validation détaillée.
        allowed_keys = {"x_handles", "reddit_subs", "arxiv_categories", "rss_keywords"}
        for k, v in hints_override.items():
            if k not in allowed_keys:
                continue  # Ignore silencieusement les clés non reconnues.
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                raise kx.KairosError(
                    "HINTS_OVERRIDE_INVALID",
                    f"hints_override.{k} must be a list of strings.",
                    400,
                )
        hints_override_clean = {
            k: v for k, v in hints_override.items() if k in allowed_keys and isinstance(v, list) and v
        } or None

    return seed, lang, sector_str, depth_int, scope_profile_str, hints_override_clean


# ─── Routes ───────────────────────────────────────────────────────────────────


@research_bp.route("/from-seed", methods=["POST"])
@require_auth
def post_from_seed():
    """Soumet une graine au pipeline Kairos. Retourne un session_id en <1 s."""
    payload = request.get_json(silent=True) or {}
    try:
        seed, lang, sector, depth, scope_profile, hints_override = _parse_seed_payload(payload)
    except kx.KairosError as exc:
        return _err(exc.error_code, exc.message, exc.status, exc.detail)

    try:
        data = kx.post_from_seed(
            seed,
            lang,
            sector_hint=sector,
            depth_hint=depth,
            scope_profile=scope_profile,
            hints_override=hints_override,
        )
    except kx.KairosError as exc:
        # Trace utile pour debug coté Coolify logs sans leaker la clé.
        logger.warning(
            "research.from-seed kairos error: %s (%s) status=%s",
            exc.error_code, exc.message[:120], exc.status,
        )
        return _err(exc.error_code, exc.message, exc.status, exc.detail)
    except Exception as exc:  # noqa: BLE001 — last-ditch safety net
        logger.exception("research.from-seed unexpected: %s", exc)
        return _err("UNKNOWN", str(exc), 500)

    return jsonify({
        "success": True,
        "data": {
            "session_id": data.get("session_id"),
            "status": data.get("status", "running"),
            "cached": bool(data.get("cached")),
            "message": data.get("message"),
        },
    }), 200


@research_bp.route("/scope-profiles", methods=["GET"])
@require_auth
def list_scope_profiles():
    """GET /api/research/scope-profiles — proxy vers Kairos GET /scope-profiles.

    Permet à l'UI Bassira de fetch dynamiquement la liste des profils de
    coverage disponibles au lieu d'une liste hardcodée. Cache 1h côté
    kairos_proxy (la liste change rarement).
    """
    try:
        data = kx.get_scope_profiles()
    except kx.KairosError as exc:
        logger.warning(
            "research.scope-profiles kairos error: %s (%s) status=%s",
            exc.error_code, exc.message[:120], exc.status,
        )
        return _err(exc.error_code, exc.message, exc.status, exc.detail)
    except Exception as exc:  # noqa: BLE001
        logger.exception("research.scope-profiles unexpected: %s", exc)
        return _err("UNKNOWN", str(exc), 500)

    return jsonify({
        "success": True,
        "data": {
            "profiles": data.get("profiles", []),
            "count": data.get("count", 0),
            "cached": bool(data.get("cached")),
        },
    }), 200


@research_bp.route("/status", methods=["GET"])
@require_auth
def get_status():
    """Polling : retourne le statut + result Kairos pour un session_id donné."""
    session_id = (request.args.get("session_id") or "").strip()
    if not session_id:
        return _err("SESSION_ID_REQUIRED", "session_id query param is required.", 400)

    try:
        data = kx.get_status(session_id)
    except kx.KairosError as exc:
        logger.warning(
            "research.status kairos error: %s (%s) status=%s",
            exc.error_code, exc.message[:120], exc.status,
        )
        return _err(exc.error_code, exc.message, exc.status, exc.detail)
    except Exception as exc:  # noqa: BLE001
        logger.exception("research.status unexpected: %s", exc)
        return _err("UNKNOWN", str(exc), 500)

    return jsonify({
        "success": True,
        "data": {
            "session_id": data.get("session_id") or session_id,
            "status": data.get("status"),
            "result": data.get("result"),
            "error_detail": data.get("error_detail"),
            "telemetry": data.get("telemetry"),
            "created_at": data.get("created_at"),
            "completed_at": data.get("completed_at"),
            "cached": bool(data.get("cached")),
        },
    }), 200
