"""Super-admin prompt registry endpoints (US-233)."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, g, jsonify, request

from ..auth.decorators import require_super_admin
from ..auth.supabase_client import SupabaseConfigError
from ..services import prompt_admin_service as prompts


admin_prompts_bp = Blueprint("admin_prompts", __name__)


def _error(code: str, message: str, status: int, **extra: Any):
    return jsonify({"success": False, "error_code": code, "error": message, **extra}), status


def _actor() -> str:
    return str((getattr(g, "current_user", None) or {}).get("id") or "super-admin")


@admin_prompts_bp.get("/")
@require_super_admin
def list_prompt_versions():
    try:
        data = prompts.list_prompts(
            scope=request.args.get("scope"), key=request.args.get("key"), locale=request.args.get("locale")
        )
    except SupabaseConfigError:
        return _error("SUPABASE_NOT_CONFIGURED", "Supabase admin client is not configured.", 503)
    except Exception:
        return _error("PROMPT_LIST_FAILED", "Could not list prompt versions.", 500)
    return jsonify({"success": True, "data": data})


@admin_prompts_bp.get("/<prompt_id>")
@require_super_admin
def read_prompt_version(prompt_id: str):
    try:
        return jsonify({"success": True, "data": prompts.get_version(prompt_id)})
    except prompts.PromptNotFoundError as exc:
        return _error(exc.code, str(exc), 404)
    except SupabaseConfigError:
        return _error("SUPABASE_NOT_CONFIGURED", "Supabase admin client is not configured.", 503)
    except Exception:
        return _error("PROMPT_READ_FAILED", "Could not read prompt version.", 500)


@admin_prompts_bp.post("/")
@require_super_admin
def create_prompt_version():
    body = request.get_json(silent=True) or {}
    required = ("key", "scope", "locale", "content")
    if any(not isinstance(body.get(field), str) or not body[field].strip() for field in required):
        return _error("INVALID_PROMPT_BODY", "key, scope, locale and content are required strings.", 400)
    variables = body.get("variables", [])
    if not isinstance(variables, list) or not all(isinstance(item, str) and item for item in variables):
        return _error("INVALID_PROMPT_VARIABLES", "variables must be a list of non-empty strings.", 400)
    try:
        data = prompts.create_version(
            key=body["key"].strip(), scope=body["scope"].strip(), locale=body["locale"].strip(),
            content=body["content"], variables=variables, created_by=_actor()
        )
    except prompts.VersionConflictError as exc:
        return _error(exc.code, str(exc), 409)
    except SupabaseConfigError:
        return _error("SUPABASE_NOT_CONFIGURED", "Supabase admin client is not configured.", 503)
    except Exception:
        return _error("PROMPT_CREATE_FAILED", "Could not create prompt version.", 500)
    return jsonify({"success": True, "data": data}), 201


@admin_prompts_bp.get("/diff")
@require_super_admin
def prompt_diff():
    from_id, to_id = request.args.get("from"), request.args.get("to")
    if not from_id or not to_id:
        return _error("INVALID_DIFF_REQUEST", "from and to prompt IDs are required.", 400)
    try:
        return jsonify({"success": True, "data": prompts.diff_versions(from_id, to_id)})
    except prompts.PromptNotFoundError as exc:
        return _error(exc.code, str(exc), 404)
    except prompts.PromptAdminError as exc:
        return _error(exc.code, str(exc), 400)
    except Exception:
        return _error("PROMPT_DIFF_FAILED", "Could not compare prompt versions.", 500)


@admin_prompts_bp.post("/<prompt_id>/activate")
@require_super_admin
def activate_prompt_version(prompt_id: str):
    return _activate(prompt_id)


@admin_prompts_bp.post("/<prompt_id>/rollback")
@require_super_admin
def rollback_prompt_version(prompt_id: str):
    """Rollback is deliberately the same evaluation-gated activation primitive."""
    return _activate(prompt_id)


def _activate(prompt_id: str):
    try:
        return jsonify({"success": True, "data": prompts.activate_version(prompt_id, created_by=_actor())})
    except prompts.GoldenSetFailedError as exc:
        return _error(exc.code, str(exc), 409, cases=exc.cases)
    except prompts.PromptNotFoundError as exc:
        return _error(exc.code, str(exc), 404)
    except SupabaseConfigError:
        return _error("SUPABASE_NOT_CONFIGURED", "Supabase admin client is not configured.", 503)
    except Exception:
        return _error("PROMPT_ACTIVATION_FAILED", "Could not activate prompt version.", 500)
