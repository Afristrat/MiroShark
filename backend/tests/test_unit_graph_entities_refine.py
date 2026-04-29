"""Unit tests for ``POST /api/graph/entities/refine`` (US-040).

US-040 — Step 1.5 « Review & refine entities ».

After /api/graph/build succeeds, the user reviews the generated entities and
applies a diff (rename / merge / delete / add) before moving on to agent
profile generation. The whole diff lands in a single Neo4j transaction so a
partial application can never feed downstream agents.

These tests stub Neo4j with an in-memory graph and assert that the four ops
behave as documented, that the route surfaces validation errors, and that
the in-memory rollback runs when one op raises.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ─── In-memory Neo4j fake ──────────────────────────────────────────────


class _FakeRecord(dict):
    def single(self):  # pragma: no cover — _FakeResult.single is what is called
        return self


class _FakeResult:
    def __init__(self, rows: List[Dict[str, Any]]):
        self._rows = rows

    def single(self) -> Optional[Dict[str, Any]]:
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class _FakeTx:
    """Minimal Cypher-aware fake.

    The fake interprets the small set of patterns used by ``EntityRefiner``.
    It uses string matching on the query body, which is enough because the
    refiner emits a fixed catalogue of statements.
    """

    def __init__(self, graph: "_FakeGraph"):
        self.graph = graph

    def run(self, query: str, **params) -> _FakeResult:
        q = " ".join(query.split())  # collapse whitespace for matching

        # rename
        if (
            "MATCH (n:Entity {uuid: $uuid, graph_id: $gid}) SET n.name = $new_name"
            in q
        ):
            uid = params["uuid"]
            gid = params["gid"]
            new_name = params["new_name"]
            node = self.graph.nodes.get(uid)
            if node and node["graph_id"] == gid:
                node["name"] = new_name
                node["name_lower"] = new_name.lower()
                return _FakeResult([{"c": 1}])
            return _FakeResult([{"c": 0}])

        # merge — pre-check
        if "RETURN s.uuid AS s_uuid, t.uuid AS t_uuid" in q:
            src = params["src"]
            tgt = params["tgt"]
            gid = params["gid"]
            s = self.graph.nodes.get(src)
            t = self.graph.nodes.get(tgt)
            if (
                s
                and t
                and s["graph_id"] == gid
                and t["graph_id"] == gid
            ):
                return _FakeResult([{"s_uuid": src, "t_uuid": tgt}])
            return _FakeResult([])

        # merge — redirect outgoing
        if "MATCH (s:Entity {uuid: $src, graph_id: $gid})-[r:RELATION]->(o:Entity)" in q:
            src = params["src"]
            tgt = params["tgt"]
            gid = params["gid"]
            new_edges: List[Dict[str, Any]] = []
            kept: List[Dict[str, Any]] = []
            for e in self.graph.edges:
                if (
                    e["src"] == src
                    and e["graph_id"] == gid
                    and e["tgt"] != tgt
                ):
                    new_edges.append(
                        {
                            "src": tgt,
                            "tgt": e["tgt"],
                            "graph_id": e["graph_id"],
                            "props": dict(e["props"]),
                        }
                    )
                else:
                    kept.append(e)
            self.graph.edges = kept + new_edges
            return _FakeResult([])

        # merge — redirect incoming
        if "MATCH (o:Entity)-[r:RELATION]->(s:Entity {uuid: $src, graph_id: $gid})" in q:
            src = params["src"]
            tgt = params["tgt"]
            gid = params["gid"]
            new_edges = []
            kept = []
            for e in self.graph.edges:
                if (
                    e["tgt"] == src
                    and e["graph_id"] == gid
                    and e["src"] != tgt
                ):
                    new_edges.append(
                        {
                            "src": e["src"],
                            "tgt": tgt,
                            "graph_id": e["graph_id"],
                            "props": dict(e["props"]),
                        }
                    )
                else:
                    kept.append(e)
            self.graph.edges = kept + new_edges
            return _FakeResult([])

        # merge — drop residual edges touching src
        if "MATCH (s:Entity {uuid: $src, graph_id: $gid})-[r:RELATION]-(:Entity)" in q:
            src = params["src"]
            gid = params["gid"]
            self.graph.edges = [
                e
                for e in self.graph.edges
                if not (
                    (e["src"] == src or e["tgt"] == src)
                    and e["graph_id"] == gid
                )
            ]
            return _FakeResult([])

        # merge — final detach delete src
        if "MATCH (s:Entity {uuid: $src, graph_id: $gid}) DETACH DELETE s" in q:
            src = params["src"]
            gid = params["gid"]
            node = self.graph.nodes.get(src)
            if node and node["graph_id"] == gid:
                del self.graph.nodes[src]
                self.graph.edges = [
                    e
                    for e in self.graph.edges
                    if e["src"] != src and e["tgt"] != src
                ]
            return _FakeResult([])

        # delete
        if "MATCH (n:Entity {uuid: $uuid, graph_id: $gid}) WITH n, count(n) AS c" in q:
            uid = params["uuid"]
            gid = params["gid"]
            node = self.graph.nodes.get(uid)
            if node and node["graph_id"] == gid:
                # If the test asks us to fail here, raise inside the txn.
                if uid in self.graph.fail_on_delete_uuids:
                    raise RuntimeError(f"simulated cypher error on delete {uid}")
                del self.graph.nodes[uid]
                self.graph.edges = [
                    e
                    for e in self.graph.edges
                    if e["src"] != uid and e["tgt"] != uid
                ]
                return _FakeResult([{"c": 1}])
            return _FakeResult([{"c": 0}])

        # add
        if q.startswith("CREATE (n:Entity:`") and "RETURN n.uuid AS uuid" in q:
            new_uuid = params["uuid"]
            self.graph.nodes[new_uuid] = {
                "uuid": new_uuid,
                "graph_id": params["gid"],
                "name": params["name"],
                "type": _extract_label(q),
                "manually_added": True,
            }
            return _FakeResult([{"uuid": new_uuid}])

        raise AssertionError(f"unhandled query in fake: {q!r}")


def _extract_label(query: str) -> str:
    # CREATE (n:Entity:`Person` { ... })
    start = query.find("`") + 1
    end = query.find("`", start)
    return query[start:end] if start > 0 and end > start else ""


class _FakeSession:
    def __init__(self, graph: "_FakeGraph"):
        self.graph = graph

    def execute_write(self, fn, *args, **kwargs):
        # Snapshot for in-memory rollback on exception.
        snapshot = self.graph.snapshot()
        try:
            return fn(_FakeTx(self.graph), *args, **kwargs)
        except Exception:
            self.graph.restore(snapshot)
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeDriver:
    def __init__(self, graph: "_FakeGraph"):
        self.graph = graph

    def session(self):
        return _FakeSession(self.graph)


class _FakeGraph:
    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self.fail_on_delete_uuids: set = set()

    def add_node(self, uuid: str, name: str, etype: str, graph_id: str):
        self.nodes[uuid] = {
            "uuid": uuid,
            "graph_id": graph_id,
            "name": name,
            "name_lower": name.lower(),
            "type": etype,
        }

    def add_edge(
        self,
        src: str,
        tgt: str,
        graph_id: str,
        props: Optional[Dict[str, Any]] = None,
    ):
        self.edges.append(
            {
                "src": src,
                "tgt": tgt,
                "graph_id": graph_id,
                "props": dict(props or {"name": "RELATED_TO", "graph_id": graph_id}),
            }
        )

    def snapshot(self):
        return (
            {k: dict(v) for k, v in self.nodes.items()},
            [dict(e, props=dict(e["props"])) for e in self.edges],
        )

    def restore(self, snap):
        nodes, edges = snap
        self.nodes = {k: dict(v) for k, v in nodes.items()}
        self.edges = [dict(e, props=dict(e["props"])) for e in edges]


class _FakeStorage:
    """Mimics the bits of ``Neo4jStorage`` that ``EntityRefiner`` reads."""

    def __init__(self, graph: _FakeGraph):
        self._driver = _FakeDriver(graph)

    def _call_with_retry(self, func, *args, **kwargs):
        return func(*args, **kwargs)


# ─── Direct service tests ──────────────────────────────────────────────


@pytest.fixture
def populated_graph():
    g = _FakeGraph()
    g.add_node("u_ceo_1", "CEO", "Person", "graph_x")
    g.add_node("u_ceo_2", "chief_executive_officer", "Person", "graph_x")
    g.add_node("u_company", "Acme", "Organization", "graph_x")
    g.add_node("u_country", "Morocco", "Country", "graph_x")
    g.add_edge("u_ceo_1", "u_company", "graph_x", {"name": "WORKS_AT", "graph_id": "graph_x"})
    g.add_edge("u_ceo_2", "u_company", "graph_x", {"name": "WORKS_AT", "graph_id": "graph_x"})
    g.add_edge("u_company", "u_country", "graph_x", {"name": "BASED_IN", "graph_id": "graph_x"})
    return g


def test_refine_rename(populated_graph):
    """Rename updates ``name`` (and ``name_lower``) on the matching entity."""
    from app.services.entity_refiner import EntityRefiner, sanitise_refine_diff

    diff = sanitise_refine_diff({
        "renames": [
            {"entity_uuid": "u_ceo_1", "new_name": "Chief Executive Officer"}
        ]
    })
    refiner = EntityRefiner(_FakeStorage(populated_graph))
    summary = refiner.apply("graph_x", diff)

    assert summary["renames_applied"] == 1
    node = populated_graph.nodes["u_ceo_1"]
    assert node["name"] == "Chief Executive Officer"
    assert node["name_lower"] == "chief executive officer"


def test_refine_merge(populated_graph):
    """Merge folds src into target and rebinds incident edges onto target."""
    from app.services.entity_refiner import EntityRefiner, sanitise_refine_diff

    diff = sanitise_refine_diff({
        "merges": [
            {"src_uuid": "u_ceo_2", "target_uuid": "u_ceo_1"}
        ]
    })
    refiner = EntityRefiner(_FakeStorage(populated_graph))
    summary = refiner.apply("graph_x", diff)

    assert summary["merges_applied"] == 1
    assert "u_ceo_2" not in populated_graph.nodes
    assert "u_ceo_1" in populated_graph.nodes
    # the WORKS_AT edge previously rooted on u_ceo_2 must now point from
    # u_ceo_1 → u_company (and the original ceo_1→company edge remains).
    works_at = [
        e for e in populated_graph.edges
        if e["tgt"] == "u_company" and e["src"] == "u_ceo_1"
    ]
    assert len(works_at) >= 1
    # No stale edge rooted on u_ceo_2 may remain.
    assert all(e["src"] != "u_ceo_2" and e["tgt"] != "u_ceo_2"
               for e in populated_graph.edges)


def test_refine_delete(populated_graph):
    """Delete removes the entity AND every incident edge."""
    from app.services.entity_refiner import EntityRefiner, sanitise_refine_diff

    diff = sanitise_refine_diff({
        "deletes": [{"entity_uuid": "u_country"}]
    })
    refiner = EntityRefiner(_FakeStorage(populated_graph))
    summary = refiner.apply("graph_x", diff)

    assert summary["deletes_applied"] == 1
    assert "u_country" not in populated_graph.nodes
    assert all(e["src"] != "u_country" and e["tgt"] != "u_country"
               for e in populated_graph.edges)


def test_refine_add(populated_graph):
    """Add creates a new entity with a fresh UUID and the requested label."""
    from app.services.entity_refiner import EntityRefiner, sanitise_refine_diff

    diff = sanitise_refine_diff({
        "additions": [
            {"name": "Marketing Director", "entity_type": "Person"}
        ]
    })
    refiner = EntityRefiner(_FakeStorage(populated_graph))
    summary = refiner.apply("graph_x", diff)

    assert summary["additions_applied"] == 1
    assert len(summary["added_entities"]) == 1
    created = summary["added_entities"][0]
    assert created["name"] == "Marketing Director"
    assert created["entity_type"] == "Person"
    new_uuid = created["uuid"]
    # UUID must look like a real uuid4 and exist on the graph
    assert len(new_uuid) >= 32
    assert new_uuid in populated_graph.nodes
    assert populated_graph.nodes[new_uuid]["name"] == "Marketing Director"


def test_refine_atomic_rollback(populated_graph):
    """If one op fails inside the transaction, the whole batch rolls back."""
    from app.services.entity_refiner import EntityRefiner, sanitise_refine_diff

    populated_graph.fail_on_delete_uuids.add("u_company")

    diff = sanitise_refine_diff({
        "renames": [
            {"entity_uuid": "u_ceo_1", "new_name": "ShouldRollBack"}
        ],
        "deletes": [
            {"entity_uuid": "u_company"}  # rigged to raise
        ],
    })
    refiner = EntityRefiner(_FakeStorage(populated_graph))

    with pytest.raises(RuntimeError, match="simulated cypher error"):
        refiner.apply("graph_x", diff)

    # The rename must NOT have been persisted because the transaction rolled back.
    assert populated_graph.nodes["u_ceo_1"]["name"] == "CEO"
    # The company must still be present.
    assert "u_company" in populated_graph.nodes


def test_sanitise_diff_drops_self_merge_and_clamps_strings():
    """Sanitiser drops self-merges, empty rows, and over-long names."""
    from app.services.entity_refiner import sanitise_refine_diff

    diff = sanitise_refine_diff({
        "renames": [
            {"entity_uuid": "u1", "new_name": "ok"},
            {"entity_uuid": "", "new_name": "missing-uuid"},
            {"entity_uuid": "u2", "new_name": ""},
            {"entity_uuid": "u3", "new_name": "x" * 500},  # truncated
        ],
        "merges": [
            {"src_uuid": "a", "target_uuid": "a"},  # self-merge skipped
            {"src_uuid": "b", "target_uuid": "c"},
        ],
        "deletes": [
            {"entity_uuid": ""},
            {"entity_uuid": "d"},
        ],
        "additions": [
            {"name": "Valid", "entity_type": "Person"},
            {"name": "", "entity_type": "Person"},
            {"name": "BadType", "entity_type": "Has-Dashes!"},  # cleaned to HasDashes
        ],
    })
    assert len(diff.renames) == 2
    long_rename = next(r for r in diff.renames if r["entity_uuid"] == "u3")
    assert len(long_rename["new_name"]) == 200
    assert diff.merges == [{"src_uuid": "b", "target_uuid": "c"}]
    assert diff.deletes == [{"entity_uuid": "d"}]
    assert len(diff.additions) == 2
    bad = next(a for a in diff.additions if a["name"] == "BadType")
    assert bad["entity_type"] == "HasDashes"


def test_sanitise_diff_rejects_non_dict_payload():
    from app.services.entity_refiner import sanitise_refine_diff, EntityRefineError

    with pytest.raises(EntityRefineError):
        sanitise_refine_diff("not a dict")  # type: ignore[arg-type]


def test_sanitise_diff_rejects_oversized_batch():
    from app.services.entity_refiner import sanitise_refine_diff, EntityRefineError

    huge = {
        "renames": [
            {"entity_uuid": f"u{i}", "new_name": f"n{i}"} for i in range(300)
        ]
    }
    with pytest.raises(EntityRefineError, match="too many"):
        sanitise_refine_diff(huge)


# ─── Endpoint integration tests (stubbed Neo4j) ────────────────────────


@pytest.fixture
def graph_client(monkeypatch, tmp_path):
    """Flask test client with a stubbed neo4j extension."""
    from app.config import Config as _Config

    monkeypatch.setattr(_Config, "WONDERWALL_SIMULATION_DATA_DIR", str(tmp_path))

    import app.storage as storage_mod

    class _NullStorage:
        def __init__(self, *a, **kw):
            pass

    monkeypatch.setattr(storage_mod, "Neo4jStorage", _NullStorage)

    from app import create_app
    app = create_app()
    app.testing = True
    return app


def test_endpoint_refine_happy_path(graph_client, monkeypatch):
    g = _FakeGraph()
    g.add_node("u_a", "alpha", "Person", "graph_endpoint")
    g.add_node("u_b", "beta", "Person", "graph_endpoint")
    storage = _FakeStorage(g)
    graph_client.extensions["neo4j_storage"] = storage

    client = graph_client.test_client()
    resp = client.post(
        "/api/graph/entities/refine",
        json={
            "graph_id": "graph_endpoint",
            "renames": [{"entity_uuid": "u_a", "new_name": "Alpha"}],
            "additions": [{"name": "Gamma", "entity_type": "Person"}],
        },
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["renames_applied"] == 1
    assert body["data"]["additions_applied"] == 1
    assert body["data"]["graph_id"] == "graph_endpoint"
    assert g.nodes["u_a"]["name"] == "Alpha"


def test_endpoint_refine_missing_graph_id(graph_client):
    graph_client.extensions["neo4j_storage"] = object()
    client = graph_client.test_client()
    resp = client.post("/api/graph/entities/refine", json={"renames": []})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["success"] is False
    assert body["error_code"] == "MISSING_GRAPH_ID"


def test_endpoint_refine_storage_unavailable(graph_client):
    graph_client.extensions["neo4j_storage"] = None
    client = graph_client.test_client()
    resp = client.post(
        "/api/graph/entities/refine",
        json={"graph_id": "g1"},
    )
    assert resp.status_code == 503
    body = resp.get_json()
    assert body["error_code"] == "STORAGE_UNAVAILABLE"


def test_endpoint_refine_empty_diff_is_noop(graph_client):
    g = _FakeGraph()
    graph_client.extensions["neo4j_storage"] = _FakeStorage(g)
    client = graph_client.test_client()
    resp = client.post(
        "/api/graph/entities/refine",
        json={"graph_id": "g1"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["renames_applied"] == 0
    assert body["data"]["merges_applied"] == 0
