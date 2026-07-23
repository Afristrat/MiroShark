"""Durable RQ worker for long-running strategic report generation."""

from __future__ import annotations

import logging
from typing import Any

from app import create_app

logger = logging.getLogger("miroshark.report_generation_worker")


def _set_job_progress(job: Any, *, progress: int, message: str, detail: dict[str, Any]) -> None:
    job.meta.update({"progress": progress, "message": message, "progress_detail": detail})
    job.save_meta()


def generate_report_job(
    *,
    task_id: str,
    report_id: str,
    simulation_id: str,
    graph_id: str,
    simulation_requirement: str,
    locale: str,
) -> dict[str, Any]:
    """Generate and persist a report outside Gunicorn's ephemeral process."""
    from rq import get_current_job

    from app.services.graph_tools import GraphToolsService
    from app.services.report_agent import ReportAgent, ReportManager, ReportStatus

    job = get_current_job()
    if job is None:
        raise RuntimeError("La génération de rapport exige un job RQ actif")

    app = create_app()
    with app.app_context():
        storage = app.extensions.get("neo4j_storage")
        if storage is None:
            raise RuntimeError("Le stockage Neo4j est indisponible")

        _set_job_progress(
            job,
            progress=0,
            message="Initialisation du rapport stratégique",
            detail={"current_stage": "initializing", "stage_index": 1},
        )
        graph_tools = GraphToolsService(storage=storage)
        agent = ReportAgent(
            graph_id=graph_id,
            simulation_id=simulation_id,
            simulation_requirement=simulation_requirement,
            graph_tools=graph_tools,
            locale=locale,
        )

        def progress_callback(stage: str, progress: int, message: str) -> None:
            _set_job_progress(
                job,
                progress=max(0, min(99, int(progress))),
                message=f"[{stage}] {message}",
                detail={"current_stage": stage, "stage_progress": progress},
            )

        try:
            report = agent.generate_report(
                progress_callback=progress_callback,
                report_id=report_id,
            )
            ReportManager.save_report(report)
            if report.status != ReportStatus.COMPLETED:
                raise RuntimeError(report.error or "La génération du rapport a échoué")
        except Exception:
            logger.exception("Génération du rapport échouée task=%s report=%s", task_id, report_id)
            raise

        result = {
            "report_id": report.report_id,
            "simulation_id": simulation_id,
            "status": "completed",
        }
        _set_job_progress(
            job,
            progress=100,
            message="Rapport stratégique terminé",
            detail={"current_stage": "completed", "stage_index": 4},
        )
        return result
