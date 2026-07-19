"""Immutable prompt versions and gated activation for the super-admin API."""

from __future__ import annotations

import difflib
from typing import Any

from ..auth.supabase_client import get_supabase_admin
from . import prompt_golden_sets, prompt_registry


class PromptAdminError(RuntimeError):
    """Base error with a safe API error code."""

    code = "PROMPT_ADMIN_FAILED"


class PromptNotFoundError(PromptAdminError):
    code = "PROMPT_NOT_FOUND"


class VersionConflictError(PromptAdminError):
    code = "PROMPT_VERSION_CONFLICT"


class GoldenSetFailedError(PromptAdminError):
    code = "PROMPT_GOLDEN_SET_FAILED"

    def __init__(self, cases: list[dict[str, Any]]):
        super().__init__("Prompt golden set failed.")
        self.cases = cases


class EvaluationPersistenceError(PromptAdminError):
    code = "PROMPT_EVALUATION_PERSISTENCE_FAILED"


def _rows(response: Any) -> list[dict[str, Any]]:
    rows = getattr(response, "data", None) or []
    return list(rows) if isinstance(rows, list) else [rows]


def list_prompts(
    *, scope: str | None = None, key: str | None = None, locale: str | None = None, client: Any = None
) -> list[dict[str, Any]]:
    query = (client or get_supabase_admin()).table("simulation_prompts").select(
        "id,key,scope,locale,version,variables,is_active,created_by,created_at"
    )
    for field, value in (("scope", scope), ("key", key), ("locale", locale)):
        if value:
            query = query.eq(field, value)
    return _rows(query.order("key").order("locale").order("version", desc=True).execute())


def get_version(prompt_id: str, *, client: Any = None) -> dict[str, Any]:
    rows = _rows(
        (client or get_supabase_admin())
        .table("simulation_prompts")
        .select("id,key,scope,locale,version,content,variables,is_active,created_by,created_at")
        .eq("id", prompt_id)
        .limit(1)
        .execute()
    )
    if not rows:
        raise PromptNotFoundError("Prompt version not found.")
    return rows[0]


def create_version(
    *, key: str, scope: str, locale: str, content: str, variables: list[str], created_by: str, client: Any = None
) -> dict[str, Any]:
    cli = client or get_supabase_admin()
    existing = _rows(
        cli.table("simulation_prompts").select("version").eq("key", key).eq("locale", locale).execute()
    )
    version = max((row.get("version", 0) for row in existing if isinstance(row.get("version"), int)), default=0) + 1
    payload = {
        "key": key,
        "scope": scope,
        "locale": locale,
        "version": version,
        "content": content,
        "variables": variables,
        "is_active": False,
        "created_by": created_by,
    }
    try:
        rows = _rows(cli.table("simulation_prompts").insert(payload).execute())
    except Exception as exc:  # duplicate key from a concurrent version creator
        if "23505" in str(exc) or "duplicate" in str(exc).lower():
            raise VersionConflictError("A concurrent prompt version was created; retry.") from exc
        raise
    if not rows:
        raise PromptAdminError("Prompt version creation returned no row.")
    return rows[0]


def unified_diff(from_prompt: dict[str, Any], to_prompt: dict[str, Any]) -> str:
    """Produce a stable unified diff independent of host line endings."""
    return "".join(
        difflib.unified_diff(
            str(from_prompt.get("content", "")).splitlines(keepends=True),
            str(to_prompt.get("content", "")).splitlines(keepends=True),
            fromfile=f"v{from_prompt.get('version')}",
            tofile=f"v{to_prompt.get('version')}",
            lineterm="\n",
        )
    )


def diff_versions(from_id: str, to_id: str, *, client: Any = None) -> dict[str, Any]:
    cli = client or get_supabase_admin()
    source, target = get_version(from_id, client=cli), get_version(to_id, client=cli)
    if (source["key"], source["locale"]) != (target["key"], target["locale"]):
        raise PromptAdminError("Only versions of the same key and locale can be diffed.")
    return {"from": source, "to": target, "diff": unified_diff(source, target)}


def activate_version(prompt_id: str, *, created_by: str, client: Any = None) -> dict[str, Any]:
    """Persist an evaluation then delegate the all-or-nothing switch to SQL."""
    cli = client or get_supabase_admin()
    prompt = get_version(prompt_id, client=cli)
    cases = prompt_golden_sets.evaluate(str(prompt["content"]), prompt.get("variables"))
    evaluation = {
        "prompt_id": prompt_id,
        "passed": prompt_golden_sets.passed(cases),
        "cases": cases,
        "created_by": created_by,
    }
    if not _rows(cli.table("simulation_prompt_evaluations").insert(evaluation).execute()):
        raise EvaluationPersistenceError("Prompt evaluation was not persisted.")
    if not evaluation["passed"]:
        raise GoldenSetFailedError(cases)
    response = cli.rpc("activate_simulation_prompt", {"p_prompt_id": prompt_id}).execute()
    rows = _rows(response)
    activated = rows[0] if rows else prompt
    prompt_registry.invalidate(str(prompt["key"]), str(prompt["locale"]))
    return activated
