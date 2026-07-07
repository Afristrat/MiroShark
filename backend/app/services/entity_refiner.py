"""US-040 — Entity refiner service (Step 1.5: Review & refine entities).

After /api/graph/build succeeds, the user lands on a review screen that lists
all generated entities grouped by ``entity_type`` and lets them apply four
kinds of corrections:

  * ``rename``  — change an entity's display name
  * ``merge``   — fold one entity (``src``) into another (``target``) and
                  redirect every incoming/outgoing edge of src onto target
  * ``delete``  — remove an entity AND every incident edge
  * ``add``     — create a new entity (Person, Organization, …) on the graph

All four operations run inside a SINGLE Neo4j transaction: if any individual
op raises, the whole batch rolls back. This guarantees that a partial diff
never lands on a graph the user is about to feed into Step 2 / agent profile
generation.

The Cypher patterns we use stay aligned with how ``Neo4jStorage`` already
labels its entities (``:Entity:<EntityType> {graph_id, uuid, name, ...}``)
and its relations (``:RELATION {graph_id, ...}``). We do **not** spawn new
relationship types during a merge — every edge stays under ``:RELATION``,
we just rebind its endpoints.
"""

from __future__ import annotations

import json
import uuid as _uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from ..utils.logger import get_logger

logger = get_logger("miroshark.entity_refiner")


# ─── Validation limits ──────────────────────────────────────────────────

_NAME_MAX_CHARS = 200
_TYPE_MAX_CHARS = 60
_MAX_OPS_PER_BATCH = 200  # defensive — refuses oversize diffs


class EntityRefineError(ValueError):
    """Raised when the diff payload is structurally invalid.

    Distinguished from generic ``Exception`` so the API layer can map it to a
    400 instead of a 500.
    """


# ─── Diff dataclass ─────────────────────────────────────────────────────


@dataclass
class RefineDiff:
    """Normalised refinement diff after sanitisation."""

    renames: List[Dict[str, str]] = field(default_factory=list)
    merges: List[Dict[str, str]] = field(default_factory=list)
    deletes: List[Dict[str, str]] = field(default_factory=list)
    additions: List[Dict[str, str]] = field(default_factory=list)

    @property
    def total_ops(self) -> int:
        return (
            len(self.renames)
            + len(self.merges)
            + len(self.deletes)
            + len(self.additions)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "renames": list(self.renames),
            "merges": list(self.merges),
            "deletes": list(self.deletes),
            "additions": list(self.additions),
        }


# ─── Sanitiser ──────────────────────────────────────────────────────────


def _clean_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = value.strip()
    if len(cleaned) > _NAME_MAX_CHARS:
        cleaned = cleaned[:_NAME_MAX_CHARS]
    return cleaned


def _clean_type(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = value.strip()
    if len(cleaned) > _TYPE_MAX_CHARS:
        cleaned = cleaned[:_TYPE_MAX_CHARS]
    # Only keep characters that are legal for a Neo4j label.
    # Backticks already escape labels in our queries, but we still strip
    # anything outside [A-Za-z0-9_] to keep the resulting label readable.
    return "".join(ch for ch in cleaned if ch.isalnum() or ch == "_")


def sanitise_refine_diff(raw: Any) -> RefineDiff:
    """Validate and normalise the refinement payload coming from the frontend.

    Raises ``EntityRefineError`` on structural problems (wrong types, missing
    required fields). Truncates string fields over the documented caps. Drops
    empty / no-op entries silently.
    """
    if not isinstance(raw, dict):
        raise EntityRefineError("payload must be an object")

    diff = RefineDiff()

    raw_renames = raw.get("renames") or []
    if not isinstance(raw_renames, list):
        raise EntityRefineError("renames must be a list")
    for item in raw_renames:
        if not isinstance(item, dict):
            continue
        uid = _clean_name(item.get("entity_uuid"))
        new_name = _clean_name(item.get("new_name"))
        if not uid or not new_name:
            continue
        diff.renames.append({"entity_uuid": uid, "new_name": new_name})

    raw_merges = raw.get("merges") or []
    if not isinstance(raw_merges, list):
        raise EntityRefineError("merges must be a list")
    for item in raw_merges:
        if not isinstance(item, dict):
            continue
        src = _clean_name(item.get("src_uuid"))
        tgt = _clean_name(item.get("target_uuid"))
        if not src or not tgt or src == tgt:
            # Self-merge is a no-op; skip silently.
            continue
        diff.merges.append({"src_uuid": src, "target_uuid": tgt})

    raw_deletes = raw.get("deletes") or []
    if not isinstance(raw_deletes, list):
        raise EntityRefineError("deletes must be a list")
    for item in raw_deletes:
        if not isinstance(item, dict):
            continue
        uid = _clean_name(item.get("entity_uuid"))
        if not uid:
            continue
        diff.deletes.append({"entity_uuid": uid})

    raw_additions = raw.get("additions") or []
    if not isinstance(raw_additions, list):
        raise EntityRefineError("additions must be a list")
    for item in raw_additions:
        if not isinstance(item, dict):
            continue
        name = _clean_name(item.get("name"))
        etype = _clean_type(item.get("entity_type"))
        if not name or not etype:
            continue
        diff.additions.append({"name": name, "entity_type": etype})

    if diff.total_ops > _MAX_OPS_PER_BATCH:
        raise EntityRefineError(
            f"too many operations in one batch (got {diff.total_ops}, max {_MAX_OPS_PER_BATCH})"
        )

    return diff


# ─── Cypher executor ────────────────────────────────────────────────────


class EntityRefiner:
    """Apply a sanitised :class:`RefineDiff` to a Neo4j graph atomically.

    Designed to consume a ``Neo4jStorage``-compatible object (anything that
    exposes a ``_driver`` attribute and the ``_call_with_retry`` helper).
    """

    def __init__(self, storage: Any):
        self.storage = storage

    # -- Public ----------------------------------------------------------

    def apply(self, graph_id: str, diff: RefineDiff) -> Dict[str, Any]:
        """Apply ``diff`` to ``graph_id`` inside a single transaction.

        Returns a summary dict with per-op counts. On any Cypher error the
        whole transaction rolls back and the original exception bubbles up.
        """
        if not graph_id:
            raise EntityRefineError("graph_id is required")

        if diff.total_ops == 0:
            return {
                "graph_id": graph_id,
                "renames_applied": 0,
                "merges_applied": 0,
                "deletes_applied": 0,
                "additions_applied": 0,
                "added_entities": [],
            }

        added_entities: List[Dict[str, str]] = []

        def _txn(tx) -> Tuple[int, int, int, int]:
            r = self._apply_renames(tx, graph_id, diff.renames)
            m = self._apply_merges(tx, graph_id, diff.merges)
            d = self._apply_deletes(tx, graph_id, diff.deletes)
            a, created = self._apply_additions(tx, graph_id, diff.additions)
            added_entities.extend(created)
            return r, m, d, a

        driver = getattr(self.storage, "_driver", None)
        if driver is None:
            raise RuntimeError("storage does not expose a Neo4j driver")

        with driver.session() as session:
            renames_done, merges_done, deletes_done, adds_done = (
                self._call_with_retry(session.execute_write, _txn)
            )

        logger.info(
            f"[refine] graph_id={graph_id} renames={renames_done} "
            f"merges={merges_done} deletes={deletes_done} additions={adds_done}"
        )

        return {
            "graph_id": graph_id,
            "renames_applied": renames_done,
            "merges_applied": merges_done,
            "deletes_applied": deletes_done,
            "additions_applied": adds_done,
            "added_entities": added_entities,
        }

    # -- Internal helpers ------------------------------------------------

    def _call_with_retry(self, func, *args, **kwargs):
        """Re-use Neo4jStorage's transient-error retry policy if available."""
        helper = getattr(self.storage, "_call_with_retry", None)
        if callable(helper):
            return helper(func, *args, **kwargs)
        return func(*args, **kwargs)

    @staticmethod
    def _apply_renames(tx, graph_id: str, renames: List[Dict[str, str]]) -> int:
        if not renames:
            return 0
        applied = 0
        for op in renames:
            result = tx.run(
                """
                MATCH (n:Entity {uuid: $uuid, graph_id: $gid})
                SET n.name = $new_name,
                    n.name_lower = toLower($new_name)
                RETURN count(n) AS c
                """,
                uuid=op["entity_uuid"],
                gid=graph_id,
                new_name=op["new_name"],
            )
            applied += int(result.single()["c"])
        return applied

    @staticmethod
    def _apply_merges(tx, graph_id: str, merges: List[Dict[str, str]]) -> int:
        if not merges:
            return 0
        applied = 0
        for op in merges:
            src = op["src_uuid"]
            tgt = op["target_uuid"]

            # Refuse merge if either side is missing on this graph — keeps
            # the diff consistent and surfaces stale UUIDs as errors.
            check = tx.run(
                """
                MATCH (s:Entity {uuid: $src, graph_id: $gid})
                MATCH (t:Entity {uuid: $tgt, graph_id: $gid})
                RETURN s.uuid AS s_uuid, t.uuid AS t_uuid
                """,
                src=src,
                tgt=tgt,
                gid=graph_id,
            )
            if check.single() is None:
                raise EntityRefineError(
                    f"merge: source or target not found on graph {graph_id} "
                    f"(src={src}, target={tgt})"
                )

            # Redirect outgoing edges: (src)-[r]->(o) ⇒ (tgt)-[r2]->(o).
            # We copy the existing relationship's properties (including
            # ``graph_id``) onto the new edge so retention/temporal data
            # is preserved.
            tx.run(
                """
                MATCH (s:Entity {uuid: $src, graph_id: $gid})-[r:RELATION]->(o:Entity)
                MATCH (t:Entity {uuid: $tgt, graph_id: $gid})
                WHERE o.uuid <> $tgt
                CREATE (t)-[r2:RELATION]->(o)
                SET r2 = properties(r)
                DELETE r
                """,
                src=src,
                tgt=tgt,
                gid=graph_id,
            )

            # Redirect incoming edges: (o)-[r]->(src) ⇒ (o)-[r2]->(tgt).
            tx.run(
                """
                MATCH (o:Entity)-[r:RELATION]->(s:Entity {uuid: $src, graph_id: $gid})
                MATCH (t:Entity {uuid: $tgt, graph_id: $gid})
                WHERE o.uuid <> $tgt
                CREATE (o)-[r2:RELATION]->(t)
                SET r2 = properties(r)
                DELETE r
                """,
                src=src,
                tgt=tgt,
                gid=graph_id,
            )

            # Drop any leftover self-loops or duplicate edges between src
            # and tgt before deleting src.
            tx.run(
                """
                MATCH (s:Entity {uuid: $src, graph_id: $gid})-[r:RELATION]-(:Entity)
                DELETE r
                """,
                src=src,
                gid=graph_id,
            )

            # Finally, detach-delete the source entity.
            tx.run(
                """
                MATCH (s:Entity {uuid: $src, graph_id: $gid})
                DETACH DELETE s
                """,
                src=src,
                gid=graph_id,
            )

            applied += 1

        return applied

    @staticmethod
    def _apply_deletes(tx, graph_id: str, deletes: List[Dict[str, str]]) -> int:
        if not deletes:
            return 0
        applied = 0
        for op in deletes:
            result = tx.run(
                """
                MATCH (n:Entity {uuid: $uuid, graph_id: $gid})
                WITH n, count(n) AS c
                DETACH DELETE n
                RETURN c
                """,
                uuid=op["entity_uuid"],
                gid=graph_id,
            )
            row = result.single()
            applied += int(row["c"]) if row else 0
        return applied

    @staticmethod
    def _apply_additions(
        tx, graph_id: str, additions: List[Dict[str, str]]
    ) -> Tuple[int, List[Dict[str, str]]]:
        if not additions:
            return 0, []

        applied = 0
        created: List[Dict[str, str]] = []
        now = datetime.now(timezone.utc).isoformat()

        for op in additions:
            new_uuid = str(_uuid.uuid4())
            etype = op["entity_type"]
            # Dynamic label injection — sanitised by ``_clean_type`` to
            # ``[A-Za-z0-9_]`` only, so backtick-escaping is sufficient.
            query = (
                "CREATE (n:Entity:`"
                + etype
                + "` { uuid: $uuid, graph_id: $gid, name: $name, "
                "name_lower: toLower($name), summary: '', "
                "attributes_json: $attrs, created_at: $created_at }) "
                "RETURN n.uuid AS uuid"
            )
            result = tx.run(
                query,
                uuid=new_uuid,
                gid=graph_id,
                name=op["name"],
                attrs=json.dumps({"manually_added": True}),
                created_at=now,
            )
            row = result.single()
            if row and row["uuid"]:
                applied += 1
                created.append(
                    {
                        "uuid": row["uuid"],
                        "name": op["name"],
                        "entity_type": etype,
                    }
                )

        return applied, created
