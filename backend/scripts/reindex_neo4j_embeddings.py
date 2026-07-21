"""Rebuild only Neo4j vector properties and indexes for a new embedding model.

This utility never deletes graph nodes, relationships, or non-vector
properties.  It is deliberately an explicit, one-shot maintenance command:
run ``--dry-run`` first, stop graph-writing workers, then run ``--apply``.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from neo4j import GraphDatabase

from app.config import Config
from app.storage.embedding_service import EmbeddingService

logger = logging.getLogger("miroshark.reindex_embeddings")


@dataclass(frozen=True)
class VectorTarget:
    """One vector-bearing Neo4j schema target."""

    name: str
    index_name: str
    read_query: str
    write_query: str
    create_index_query: str


def _vector_index_query(index_name: str, schema: str) -> str:
    return f"""
CREATE VECTOR INDEX {index_name} IF NOT EXISTS
FOR {schema}
OPTIONS {{indexConfig: {{
  `vector.dimensions`: $dimensions,
  `vector.similarity_function`: 'cosine'
}}}}
"""


TARGETS = (
    VectorTarget(
        name="entities",
        index_name="entity_embedding",
        read_query="""
MATCH (n:Entity)
WITH n, coalesce(nullif(trim(n.summary), ''), nullif(trim(n.name), '')) AS text
WHERE text IS NOT NULL
RETURN elementId(n) AS id, text
ORDER BY id
""",
        write_query="""
UNWIND $rows AS row
MATCH (n) WHERE elementId(n) = row.id
SET n.embedding = row.vector
""",
        create_index_query=_vector_index_query("entity_embedding", "(n:Entity) ON (n.embedding)"),
    ),
    VectorTarget(
        name="facts",
        index_name="fact_embedding",
        read_query="""
MATCH ()-[r:RELATION]-()
WITH r, coalesce(nullif(trim(r.fact), ''), nullif(trim(r.name), '')) AS text
WHERE text IS NOT NULL
RETURN elementId(r) AS id, text
ORDER BY id
""",
        write_query="""
UNWIND $rows AS row
MATCH ()-[r]-() WHERE elementId(r) = row.id
SET r.fact_embedding = row.vector
""",
        create_index_query=_vector_index_query(
            "fact_embedding", "()-[r:RELATION]-() ON (r.fact_embedding)"
        ),
    ),
    VectorTarget(
        name="communities",
        index_name="community_embedding",
        read_query="""
MATCH (n:Community)
WITH n, coalesce(nullif(trim(n.summary), ''), nullif(trim(n.name), '')) AS text
WHERE text IS NOT NULL
RETURN elementId(n) AS id, text
ORDER BY id
""",
        write_query="""
UNWIND $rows AS row
MATCH (n) WHERE elementId(n) = row.id
SET n.summary_embedding = row.vector
""",
        create_index_query=_vector_index_query(
            "community_embedding", "(n:Community) ON (n.summary_embedding)"
        ),
    ),
)


def batches(rows: list[dict[str, str]], size: int) -> Iterator[list[dict[str, str]]]:
    """Yield deterministic non-empty batches without a third-party dependency."""
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def vector_count(rows: Iterable[dict[str, Any]], dimensions: int) -> int:
    """Count rows whose vector has exactly the requested dimensionality."""
    return sum(1 for row in rows if len(row.get("vector") or []) == dimensions)


class Reindexer:
    """Performs a resumable vector-only Neo4j migration."""

    def __init__(self, embedding: EmbeddingService, batch_size: int) -> None:
        self.embedding = embedding
        self.batch_size = batch_size
        self.driver = GraphDatabase.driver(
            Config.NEO4J_URI, auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD)
        )

    def close(self) -> None:
        self.driver.close()

    def _rows(self, target: VectorTarget) -> list[dict[str, str]]:
        with self.driver.session() as session:
            return [dict(record) for record in session.run(target.read_query)]

    def preflight(self) -> dict[str, int]:
        sample = self.embedding.embed("Bassira embedding migration preflight")
        if len(sample) != self.embedding.dimensions:
            raise RuntimeError(
                "Embedding provider returned an unexpected vector length: "
                f"expected {self.embedding.dimensions}, got {len(sample)}"
            )
        return {target.name: len(self._rows(target)) for target in TARGETS}

    def apply(self) -> dict[str, int]:
        counts = self.preflight()
        with self.driver.session() as session:
            for target in TARGETS:
                session.run(f"DROP INDEX {target.index_name} IF EXISTS").consume()

        for target in TARGETS:
            rows = self._rows(target)
            for group in batches(rows, self.batch_size):
                vectors = self.embedding.embed_batch([row["text"] for row in group])
                payload = [
                    {"id": row["id"], "vector": vector}
                    for row, vector in zip(group, vectors, strict=True)
                ]
                if vector_count(payload, self.embedding.dimensions) != len(payload):
                    raise RuntimeError(f"Invalid {target.name} embedding batch")
                with self.driver.session() as session:
                    session.run(target.write_query, rows=payload).consume()

        with self.driver.session() as session:
            for target in TARGETS:
                session.run(
                    target.create_index_query, dimensions=self.embedding.dimensions
                ).consume()
            session.run("CALL db.awaitIndexes(600)").consume()
        return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="perform the migration")
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    return args


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if Config.EMBEDDING_PROVIDER.lower() != "openai":
        raise RuntimeError("This migration requires the OpenAI-compatible Qwen endpoint")
    reindexer = Reindexer(EmbeddingService(), args.batch_size)
    try:
        counts = reindexer.preflight()
        logger.info("Preflight passed: %s", counts)
        if not args.apply:
            logger.info("Dry run complete; no Neo4j data or indexes changed")
            return 0
        counts = reindexer.apply()
        logger.info("Migration complete: %s", counts)
        return 0
    finally:
        reindexer.close()


if __name__ == "__main__":
    raise SystemExit(main())
