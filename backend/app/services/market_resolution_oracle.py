"""Bounded, auditable market adjudication contract for US-226 / ADR-015."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from ..utils.llm_client import create_smart_llm_client
from ..utils.logger import get_logger
from . import prompt_registry
from wonderwall.simulations.polymarket.resolution_spec import validate_resolution_spec

logger = get_logger("miroshark.services.market_resolution_oracle")

ORACLE_PROMPT_KEY = "oracle.resolution"
ORACLE_PROMPT_VERSION = 1
ORACLE_MAX_ATTEMPTS = 2
_MAX_DIGEST_ITEMS = 64
_MAX_OBJECT_KEYS = 32
_MAX_TEXT_LENGTH = 1_000
_MAX_JUSTIFICATION_LENGTH = 1_200
_MAX_EVIDENCE = 16


@dataclass(frozen=True)
class OracleResolution:
    """Validated result ready for durable persistence by the caller."""

    verdict: str
    justification: str
    confidence: Optional[float]
    evidence: List[Dict[str, Any]]
    prompt_key: str
    prompt_version: int


def _bounded_json(value: Any, *, depth: int = 0) -> Any:
    """Deterministically retain only JSON-safe, bounded simulation data."""
    if depth > 5:
        return "[truncated]"
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        return _bounded_text(value)
    if isinstance(value, (int, float)):
        return value if not isinstance(value, float) or math.isfinite(value) else "[non-finite]"
    if isinstance(value, Mapping):
        return {
            _bounded_text(str(key))[:128]: _bounded_json(value[key], depth=depth + 1)
            for key in sorted(value, key=lambda candidate: str(candidate))[:_MAX_OBJECT_KEYS]
        }
    if isinstance(value, (list, tuple)):
        return [_bounded_json(item, depth=depth + 1) for item in value[:_MAX_DIGEST_ITEMS]]
    return _bounded_text(str(value))


def _bounded_text(value: str) -> str:
    """Keep untrusted text data-like inside the XML envelope."""
    return value[:_MAX_TEXT_LENGTH].replace("<", "\\u003c").replace(">", "\\u003e")


def _round(value: Any, fallback: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else fallback


def _digest_items(rows: Iterable[Any], prefix: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"{prefix} digest item is invalid")
        round_number = _round(row.get("round"), _round(row.get("round_num"), index))
        payload = {key: value for key, value in row.items() if key not in {"round", "round_num", "ref"}}
        items.append({"round": round_number, "data": _bounded_json(payload)})
    sorted_items = sorted(items, key=lambda item: (item["round"], _canonical_json(item["data"])))
    if len(sorted_items) > _MAX_DIGEST_ITEMS:
        selected = {
            round(index * (len(sorted_items) - 1) / (_MAX_DIGEST_ITEMS - 1))
            for index in range(_MAX_DIGEST_ITEMS)
        }
        sorted_items = [item for index, item in enumerate(sorted_items) if index in selected]
    for index, item in enumerate(sorted_items):
        item["ref"] = f"{prefix}:{item['round']}:{index}"
    return sorted_items


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _trajectory_snapshots(payload: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    snapshots = payload.get("snapshots")
    if not isinstance(snapshots, list) or any(not isinstance(snapshot, Mapping) for snapshot in snapshots):
        raise ValueError("merged trajectory snapshots are invalid")
    return snapshots


def _content_count(snapshots: Sequence[Mapping[str, Any]]) -> int:
    count = 0
    for snapshot in snapshots:
        if "total_posts_created" in snapshot:
            value = snapshot["total_posts_created"]
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError("trajectory content count is invalid")
            count += value
        else:
            contents = snapshot.get("contents", [])
            if not isinstance(contents, list):
                raise ValueError("trajectory contents are invalid")
            count += len(contents)
    return count


def _beliefs(snapshot: Mapping[str, Any]) -> Dict[str, Dict[str, float]]:
    positions = snapshot.get("belief_positions", {})
    if not isinstance(positions, Mapping):
        raise ValueError("trajectory belief positions are invalid")
    result: Dict[str, Dict[str, float]] = {}
    for persona_id, topics in positions.items():
        if not isinstance(topics, Mapping):
            raise ValueError("trajectory persona beliefs are invalid")
        result[str(persona_id)] = {}
        for topic, value in topics.items():
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                raise ValueError("trajectory belief value is invalid")
            result[str(persona_id)][str(topic)] = float(value)
    return result


def _trajectory_aggregates(snapshots: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    if not snapshots:
        return {"final_stances": {"population": 0, "topics": {}}, "trajectory_deltas": {}}
    ordered = sorted(snapshots, key=lambda row: (_round(row.get("round"), _round(row.get("round_num"), 0)), _canonical_json(row)))
    first, last = ordered[0], ordered[-1]
    first_round = _round(first.get("round"), _round(first.get("round_num"), 0))
    last_round = _round(last.get("round"), _round(last.get("round_num"), 0))
    first_beliefs, last_beliefs = _beliefs(first), _beliefs(last)
    topics = sorted({topic for beliefs in (*first_beliefs.values(), *last_beliefs.values()) for topic in beliefs})
    stance_topics: Dict[str, Any] = {}
    deltas: Dict[str, Any] = {}
    for topic in topics:
        first_values = [beliefs[topic] for beliefs in first_beliefs.values() if topic in beliefs]
        last_values = [beliefs[topic] for beliefs in last_beliefs.values() if topic in beliefs]
        support = sum(value > 0.2 for value in last_values)
        oppose = sum(value < -0.2 for value in last_values)
        neutral = len(last_values) - support - oppose
        population = len(last_values)
        stance_topics[topic] = {
            "population": population,
            "counts": {"support": support, "neutral": neutral, "oppose": oppose},
            "shares": {
                "support": support / population if population else 0.0,
                "neutral": neutral / population if population else 0.0,
                "oppose": oppose / population if population else 0.0,
            },
        }
        if first_values and last_values:
            first_mean = math.fsum(first_values) / len(first_values)
            final_mean = math.fsum(last_values) / len(last_values)
            deltas[topic] = {
                "first_round": first_round,
                "last_round": last_round,
                "first_population": len(first_values),
                "last_population": len(last_values),
                "first_mean": first_mean,
                "final_mean": final_mean,
                "delta": final_mean - first_mean,
            }
    return {
        "final_stances": {"population": len(last_beliefs), "topics": stance_topics},
        "trajectory_deltas": deltas,
    }


def build_resolution_digest(
    market: Mapping[str, Any],
    trajectory_payload: Mapping[str, Any],
    price_series: Sequence[Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]] = (),
) -> Dict[str, Any]:
    """Build the only bounded data set that an adjudicator may inspect."""
    market_id = market.get("market_id")
    question = market.get("question")
    outcome_a = market.get("outcome_a")
    outcome_b = market.get("outcome_b")
    resolution_spec = market.get("resolution_spec")
    if not isinstance(market_id, int) or isinstance(market_id, bool) or market_id <= 0:
        raise ValueError("market_id must be a positive integer")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("market question is required")
    if not isinstance(outcome_a, str) or not outcome_a.strip():
        raise ValueError("market outcome_a is required")
    if not isinstance(outcome_b, str) or not outcome_b.strip():
        raise ValueError("market outcome_b is required")
    if outcome_a == outcome_b:
        raise ValueError("market outcomes must be distinct")
    if not isinstance(resolution_spec, Mapping):
        raise ValueError("resolution_spec is required")
    # US-225 validated deadline_round against the simulation plan at creation.
    # The Oracle owns no total-round context, so it validates structure only.
    validate_resolution_spec(dict(resolution_spec))
    if not isinstance(trajectory_payload, Mapping):
        raise ValueError("merged trajectory digest is invalid")
    trajectories = _trajectory_snapshots(trajectory_payload)
    if not isinstance(price_series, Sequence) or isinstance(price_series, (str, bytes)):
        raise ValueError("price digest is invalid")
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
        raise ValueError("event digest is invalid")
    trajectory_items = _digest_items(trajectories, "round")
    price_items = _digest_items(price_series, "price")
    event_items = _digest_items(events, "event")
    content_count = _content_count(trajectories)
    metric_round = trajectory_items[-1]["round"] if trajectory_items else 0
    metrics = {
        "event_count": len(events),
        "content_count": content_count,
        "trajectory_count": len(trajectories),
        "price_snapshot_count": len(price_series),
        **_trajectory_aggregates(trajectories),
    }
    return {
        "resolution_spec": _bounded_json(resolution_spec),
        "market": {
            "market_id": market_id,
            "question": _bounded_json(question.strip()),
            "outcomes": [_bounded_json(outcome_a.strip()), _bounded_json(outcome_b.strip())],
        },
        "simulation_digest": {
            "trajectories": trajectory_items,
            "price_series": price_items,
            "events": event_items,
            "metrics": {"round": metric_round, "ref": f"metric:{metric_round}:0", "data": metrics},
        },
    }


def validate_oracle_output(result: Any, digest: Mapping[str, Any]) -> OracleResolution:
    """Reject every output that cannot be persisted under the frozen contract."""
    if not isinstance(result, dict) or set(result) != {"verdict", "justification", "confidence", "evidence"}:
        raise ValueError("oracle output has missing or unexpected fields")
    verdict = result["verdict"]
    justification = result["justification"]
    confidence = result["confidence"]
    evidence = result["evidence"]
    if verdict not in {"YES", "NO", "INVALID"}:
        raise ValueError("oracle verdict is invalid")
    if not isinstance(justification, str) or not justification.strip() or len(justification) > _MAX_JUSTIFICATION_LENGTH:
        raise ValueError("oracle justification is invalid")
    if not isinstance(evidence, list) or len(evidence) > _MAX_EVIDENCE:
        raise ValueError("oracle evidence is invalid")
    valid_refs = {
        item["ref"]: (item.get("round"), evidence_type)
        for collection, evidence_type in (
            (digest.get("simulation_digest", {}).get("trajectories", []), "trajectory"),
            (digest.get("simulation_digest", {}).get("price_series", []), "price"),
            (digest.get("simulation_digest", {}).get("events", []), "event"),
            ([digest.get("simulation_digest", {}).get("metrics", {})], "metric"),
        )
        if isinstance(collection, list)
        for item in collection
        if isinstance(item, Mapping) and isinstance(item.get("ref"), str)
    }
    validated_evidence: List[Dict[str, Any]] = []
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {"round", "type", "ref"}:
            raise ValueError("oracle evidence item is invalid")
        round_number, evidence_type, ref = item["round"], item["type"], item["ref"]
        if not isinstance(ref, str) or ref not in valid_refs:
            raise ValueError("oracle evidence reference is not in the digest")
        if not isinstance(round_number, int) or isinstance(round_number, bool) or round_number < 0:
            raise ValueError("oracle evidence round is invalid")
        expected_round, expected_type = valid_refs[ref]
        if evidence_type != expected_type or round_number != expected_round:
            raise ValueError("oracle evidence must link its round, type and digest ref")
        if ref not in justification:
            raise ValueError("oracle justification must cite each evidence reference")
        validated_evidence.append({"round": round_number, "type": evidence_type, "ref": ref})
    if not validated_evidence:
        raise ValueError("resolved oracle output requires evidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError("oracle confidence must be a finite number in [0, 1]")
    return OracleResolution(verdict, justification.strip(), float(confidence), validated_evidence, ORACLE_PROMPT_KEY, ORACLE_PROMPT_VERSION)


def _normalize_structured_evidence_citations(result: Any) -> Any:
    """Make explicit citations from the model's structured evidence auditable.

    Some OpenAI-compatible providers return valid evidence objects but omit their
    ``ref`` strings from the prose justification.  The refs are already part of
    the same model response, so appending only missing refs neither invents a
    source nor weakens the strict evidence boundary enforced below.
    """
    if not isinstance(result, dict) or not isinstance(result.get("justification"), str):
        return result
    evidence = result.get("evidence")
    if not isinstance(evidence, list):
        return result
    refs = [item.get("ref") for item in evidence if isinstance(item, dict) and isinstance(item.get("ref"), str)]
    missing_refs = [ref for ref in dict.fromkeys(refs) if ref and ref not in result["justification"]]
    if not missing_refs:
        return result
    normalized = dict(result)
    normalized["justification"] = f"{result['justification'].strip()} Sources : {', '.join(missing_refs)}."
    return normalized


def resolve_market(
    market: Mapping[str, Any],
    trajectory_payload: Mapping[str, Any],
    price_series: Sequence[Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]] = (),
    *,
    locale: str = "fr",
    llm: Any = None,
) -> OracleResolution:
    """Ask the LLM only to resolve ambiguity; permanent failure stays UNRESOLVED."""
    digest = build_resolution_digest(market, trajectory_payload, price_series, events)
    active = prompt_registry.get_active(ORACLE_PROMPT_KEY, locale)
    if active is None:
        return OracleResolution(
            "UNRESOLVED", "Resolution unavailable: active adjudication prompt is missing.", None, [],
            ORACLE_PROMPT_KEY, ORACLE_PROMPT_VERSION,
        )
    prompt = active.content
    version = active.version
    client = llm or create_smart_llm_client(timeout=60.0)
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "<untrusted_simulation_data>\n" + _canonical_json(digest) + "\n</untrusted_simulation_data>"},
    ]
    for attempt in range(ORACLE_MAX_ATTEMPTS):
        try:
            response = client.chat_json(messages=messages, temperature=0.0)
            resolution = validate_oracle_output(_normalize_structured_evidence_citations(response), digest)
            return OracleResolution(
                resolution.verdict, resolution.justification, resolution.confidence,
                resolution.evidence, ORACLE_PROMPT_KEY, version,
            )
        except Exception as exc:  # noqa: BLE001 - untrusted model boundary
            logger.warning("Oracle adjudication attempt %s/%s failed: %s", attempt + 1, ORACLE_MAX_ATTEMPTS, exc.__class__.__name__)
            if attempt + 1 < ORACLE_MAX_ATTEMPTS:
                messages = messages + [{
                    "role": "system",
                    "content": "Return the strict JSON contract only: valid keys, cited digest refs, finite confidence, and no extra text.",
                }]
    return OracleResolution(
        "UNRESOLVED", "Resolution unavailable: invalid adjudication response.", None, [], ORACLE_PROMPT_KEY, version,
    )
