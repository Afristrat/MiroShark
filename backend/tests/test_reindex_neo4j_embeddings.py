"""Unit checks for the explicit Neo4j vector reindexing utility."""

from scripts.reindex_neo4j_embeddings import batches, vector_count


def test_batches_are_ordered_and_keep_the_tail() -> None:
    rows = [{"id": "one"}, {"id": "two"}, {"id": "three"}]

    assert list(batches(rows, 2)) == [
        [{"id": "one"}, {"id": "two"}],
        [{"id": "three"}],
    ]


def test_vector_count_requires_the_target_dimension() -> None:
    rows = [
        {"vector": [0.0, 1.0, 2.0]},
        {"vector": [0.0, 1.0]},
        {"vector": []},
    ]

    assert vector_count(rows, 3) == 1
