"""Deterministic, local contracts used to gate prompt activation (US-233)."""

from __future__ import annotations

import re
from typing import Any


_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_MAX_CONTENT_LENGTH = 50_000


def evaluate(content: str, variables: Any) -> list[dict[str, Any]]:
    """Run the stable prompt contract without network or model calls.

    ``variables`` documents values available to a prompt and may intentionally
    include data used only by an upstream builder.  The safe invariant is thus
    one-way: a literal placeholder must be declared, while an unused declared
    variable remains valid.
    """
    declared = variables if isinstance(variables, list) else []
    declared_names = {item for item in declared if isinstance(item, str) and item}
    used_names = set(_PLACEHOLDER.findall(content))
    cases: list[dict[str, Any]] = [
        {
            "name": "content_not_empty",
            "passed": bool(content.strip()),
            "detail": "Prompt content must not be empty.",
        },
        {
            "name": "content_within_limit",
            "passed": len(content) <= _MAX_CONTENT_LENGTH,
            "detail": f"Prompt content must not exceed {_MAX_CONTENT_LENGTH} characters.",
        },
        {
            "name": "placeholders_declared",
            "passed": used_names <= declared_names,
            "detail": "Prompt placeholders must be declared in variables.",
            "unexpected": sorted(used_names - declared_names),
        },
    ]
    return cases


def passed(cases: list[dict[str, Any]]) -> bool:
    """Return the aggregate result from persisted deterministic cases."""
    return bool(cases) and all(case.get("passed") is True for case in cases)
