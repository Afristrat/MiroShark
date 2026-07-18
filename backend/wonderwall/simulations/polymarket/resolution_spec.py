"""Canonical validation for auditable prediction-market resolution contracts."""
from __future__ import annotations

import math
import re


_RESOLUTION_SIGNALS = {
    "final_stances": {"count_gte", "count_lte", "share_gte", "share_lte"},
    "contents": {"count_gte", "count_lte"},
    "trajectory": {"delta_gte", "delta_lte"},
    "events": {"count_gte", "count_lte"},
}
_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def is_finite_number(value: object) -> bool:
    """Return whether a JSON scalar is a finite number, excluding booleans."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_resolution_spec(spec: object, total_rounds: int | None = None) -> None:
    """Validate the ADR-015 contract without coercing untrusted input.

    ``total_rounds`` is supplied by the generator, where the deadline must fit
    the planned simulation. Persistence validates the same structure without a
    round upper bound because it does not own that simulation context.
    """
    if total_rounds is not None and (
        not isinstance(total_rounds, int) or isinstance(total_rounds, bool) or total_rounds < 1
    ):
        raise ValueError("total_rounds must be a positive integer")
    if not isinstance(spec, dict):
        raise ValueError("resolution_spec must be an object")
    if set(spec) != {"version", "deadline_round", "aggregation", "criteria", "invalid_conditions"}:
        raise ValueError("resolution_spec has missing or unexpected fields")
    if spec["version"] != 1:
        raise ValueError("resolution_spec.version must be 1")

    deadline = spec["deadline_round"]
    if not isinstance(deadline, int) or isinstance(deadline, bool) or deadline < 1:
        raise ValueError("resolution_spec.deadline_round must be a positive integer")
    if total_rounds is not None and deadline > total_rounds:
        raise ValueError("resolution_spec.deadline_round is outside simulation rounds")
    aggregation = spec["aggregation"]
    if not isinstance(aggregation, str) or aggregation not in {"all", "any"}:
        raise ValueError("resolution_spec.aggregation must be all or any")

    criteria = spec["criteria"]
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("resolution_spec.criteria must be a non-empty list")
    criterion_ids: set[str] = set()
    for criterion in criteria:
        if not isinstance(criterion, dict) or set(criterion) != {
            "id", "description", "signal", "operator", "threshold"
        }:
            raise ValueError("resolution_spec criterion has missing or unexpected fields")
        criterion_id = criterion["id"]
        if not isinstance(criterion_id, str) or not _IDENTIFIER_RE.fullmatch(criterion_id):
            raise ValueError("resolution_spec criterion id must be stable snake_case")
        if criterion_id in criterion_ids:
            raise ValueError("resolution_spec criterion ids must be unique")
        criterion_ids.add(criterion_id)
        signal = criterion["signal"]
        if not isinstance(signal, str) or signal not in _RESOLUTION_SIGNALS:
            raise ValueError("resolution_spec criterion signal is not supported")
        operator = criterion["operator"]
        if not isinstance(operator, str) or operator not in _RESOLUTION_SIGNALS[signal]:
            raise ValueError("resolution_spec criterion operator is incompatible with signal")
        if not isinstance(criterion["description"], str) or not criterion["description"].strip():
            raise ValueError("resolution_spec criterion description is required")
        threshold = criterion["threshold"]
        if not is_finite_number(threshold):
            raise ValueError("resolution_spec criterion threshold must be finite numeric scalar")
        if operator.startswith("share_") and not 0 <= threshold <= 1:
            raise ValueError("resolution_spec share threshold must be within 0 and 1")

    invalid_conditions = spec["invalid_conditions"]
    if not isinstance(invalid_conditions, list) or not invalid_conditions:
        raise ValueError("resolution_spec.invalid_conditions must be a non-empty list")
    invalid_ids: set[str] = set()
    for condition in invalid_conditions:
        if not isinstance(condition, dict) or set(condition) != {"id", "description"}:
            raise ValueError("invalid condition has missing or unexpected fields")
        condition_id = condition["id"]
        if not isinstance(condition_id, str) or not _IDENTIFIER_RE.fullmatch(condition_id):
            raise ValueError("invalid condition id must be stable snake_case")
        if condition_id in invalid_ids:
            raise ValueError("invalid condition ids must be unique")
        invalid_ids.add(condition_id)
        if not isinstance(condition["description"], str) or not condition["description"].strip():
            raise ValueError("invalid condition description is required")
