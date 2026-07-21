"""Le graphe vide ne doit jamais être exposé comme prêt à simuler."""

from contextlib import nullcontext
from types import SimpleNamespace

import pytest


def test_build_graph_job_fails_when_extraction_produces_no_nodes(monkeypatch):
    from app.models.project import ProjectStatus
    from app.workers import simulation_preparation_worker as worker
    import rq
    from app.models import project as project_module
    from app.services import graph_builder, text_processor

    project = SimpleNamespace(graph_id=None, status=ProjectStatus.GRAPH_BUILDING, error=None)
    saved_projects = []
    job = SimpleNamespace(meta={}, save_meta=lambda: None)
    storage = SimpleNamespace(wait_for_processing=lambda episodes: None)
    app = SimpleNamespace(extensions={"neo4j_storage": storage}, app_context=lambda: nullcontext())

    class EmptyGraphBuilder:
        def __init__(self, storage):
            self.storage = storage

        def create_graph(self, name):
            return "graph-empty"

        def set_ontology(self, graph_id, ontology):
            return None

        def add_text_batches(self, graph_id, chunks, max_workers, progress_callback):
            return []

        def get_graph_data(self, graph_id):
            return {"node_count": 0, "edge_count": 0}

    monkeypatch.setattr(rq, "get_current_job", lambda: job)
    monkeypatch.setattr(worker, "create_app", lambda: app)
    monkeypatch.setattr(project_module.ProjectManager, "get_project", lambda project_id: project)
    monkeypatch.setattr(project_module.ProjectManager, "save_project", lambda value: saved_projects.append(value))
    monkeypatch.setattr(graph_builder, "GraphBuilderService", EmptyGraphBuilder)
    monkeypatch.setattr(text_processor.TextProcessor, "split_text", lambda *args, **kwargs: ["source"])

    with pytest.raises(ValueError, match="aucune entité exploitable"):
        worker.build_graph_job(
            task_id="task-1", project_id="proj-1", graph_name="Test", text="source",
            ontology={}, chunk_size=1000, chunk_overlap=50, max_workers=1,
        )

    assert project.status is ProjectStatus.FAILED
    assert "aucune entité exploitable" in project.error
    assert saved_projects
