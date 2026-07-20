"""Routage explicable des arènes (US-235).

Le moteur ne prétend jamais couvrir une population avec une arène qui n'est
pas livrée. Les règles sont déterministes et leur résultat est sérialisable
pour être persisté dans ``arena_routing_decisions``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Final

IMPLEMENTED_ARENAS: Final[frozenset[str]] = frozenset({"twitter", "reddit", "polymarket"})

ARENA_CATALOG: Final[dict[str, dict[str, Any]]] = {
    "twitter": {"mechanism": "public_algorithmic", "status": "implemented", "populations": ["public_connected"]},
    "reddit": {"mechanism": "semi_public_community", "status": "implemented", "populations": ["public_connected", "community_participants"]},
    "polymarket": {"mechanism": "conviction_market", "status": "implemented", "populations": ["market_participants"]},
    "messaging_relay": {"mechanism": "private_messaging", "status": "planned", "populations": ["family_networks", "community_networks"]},
    "majlis": {"mechanism": "local_deliberation", "status": "candidate", "populations": ["local_leaders", "community_participants"]},
    "authority_relay": {"mechanism": "authority_relay", "status": "candidate", "populations": ["religious_audiences", "radio_audiences"]},
    "diaspora_souk": {"mechanism": "diaspora_exchange", "status": "candidate", "populations": ["diaspora", "traders"]},
}

SCENARIO_TYPES: Final[frozenset[str]] = frozenset({
    "public_reaction", "community_deliberation", "private_diffusion", "authority_response", "market_outcome",
})


@dataclass(frozen=True)
class RoutingContext:
    scenario_type: str
    populations: tuple[str, ...] = ()
    outcome_measurable: bool = False


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def recommend(context: RoutingContext) -> dict[str, Any]:
    """Retourne une décision complète, déterministe et audit-able.

    Les candidats non implémentés ne figurent jamais dans ``recommended_arenas``;
    ils deviennent une lacune de couverture visible.
    """
    if context.scenario_type not in SCENARIO_TYPES:
        raise ValueError("unsupported scenario_type")

    candidates = ["twitter", "reddit"]
    required_mechanisms: list[str] = ["public_algorithmic", "semi_public_community"]
    if context.scenario_type == "private_diffusion":
        candidates.append("messaging_relay")
        required_mechanisms.append("private_messaging")
    elif context.scenario_type == "community_deliberation":
        candidates.append("majlis")
        required_mechanisms.append("local_deliberation")
    elif context.scenario_type == "authority_response":
        candidates.append("authority_relay")
        required_mechanisms.append("authority_relay")
    elif context.scenario_type == "market_outcome" and context.outcome_measurable:
        candidates.append("polymarket")
        required_mechanisms.append("conviction_market")

    recommended = [arena for arena in _dedupe(candidates) if arena in IMPLEMENTED_ARENAS]
    unavailable = [arena for arena in _dedupe(candidates) if arena not in IMPLEMENTED_ARENAS]
    requested_populations = set(context.populations)
    covered = set().union(*(set(ARENA_CATALOG[a]["populations"]) for a in recommended))
    uncovered = sorted(requested_populations - covered)
    coverage_gaps = [
        {"arena": arena, "mechanism": ARENA_CATALOG[arena]["mechanism"], "reason": "arena_not_implemented"}
        for arena in unavailable
    ]
    coverage_gaps.extend(
        {"population": population, "reason": "no_implemented_arena_declares_coverage"}
        for population in uncovered
    )
    return {
        "policy_version": "adr019-v1",
        "context": asdict(context),
        "recommended_arenas": recommended,
        "required_mechanisms": _dedupe(required_mechanisms),
        "coverage_gaps": coverage_gaps,
        "representativeness_status": "partial" if coverage_gaps else "bounded",
    }


def parse_context(payload: Any) -> RoutingContext:
    if not isinstance(payload, dict):
        raise ValueError("routing_context must be an object")
    scenario_type = payload.get("scenario_type")
    populations = payload.get("populations", [])
    if not isinstance(scenario_type, str) or not isinstance(populations, list) or not all(isinstance(p, str) and p for p in populations):
        raise ValueError("routing_context has invalid fields")
    if scenario_type not in SCENARIO_TYPES:
        raise ValueError("unsupported scenario_type")
    return RoutingContext(scenario_type=scenario_type, populations=tuple(_dedupe(populations)), outcome_measurable=payload.get("outcome_measurable") is True)


def record_decision(simulation_id: str, decision: dict[str, Any], source: str, client: Any = None) -> None:
    """Persiste l'explication complète ; l'échec interdit la création routée."""
    from ..auth.supabase_client import get_supabase_admin

    (client or get_supabase_admin()).table("arena_routing_decisions").insert({
        "simulation_id": simulation_id,
        "policy_version": decision["policy_version"],
        "scenario_type": decision["context"]["scenario_type"],
        "requested_populations": decision["context"]["populations"],
        "recommended_arenas": decision["recommended_arenas"],
        "coverage_gaps": decision["coverage_gaps"],
        "decision_source": source,
        "decision": decision,
    }).execute()


def delete_decision(simulation_id: str, client: Any = None) -> None:
    """Compensation obligatoire si la création filesystem échoue après l'audit."""
    from ..auth.supabase_client import get_supabase_admin

    (client or get_supabase_admin()).table("arena_routing_decisions").delete().eq(
        "simulation_id", simulation_id
    ).execute()
