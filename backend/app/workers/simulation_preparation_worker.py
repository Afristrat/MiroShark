"""Tâche RQ durable de préparation des simulations.

La préparation peut durer plusieurs minutes. Elle ne doit jamais s'exécuter
dans un worker Gunicorn, car un redéploiement ou un timeout HTTP détruirait le
thread et laisserait une simulation dans un état ambigu.
"""

from __future__ import annotations

import logging
from typing import Any

from app import create_app

logger = logging.getLogger("miroshark.simulation_preparation_worker")

_STAGE_WEIGHTS = {
    "reading": (0, 20),
    "generating_profiles": (20, 70),
    "generating_config": (70, 90),
    "copying_scripts": (90, 100),
}
_STAGE_NAMES = {
    "reading": "Lecture des entités du graphe",
    "generating_profiles": "Génération des profils agents",
    "generating_config": "Génération de la configuration",
    "copying_scripts": "Préparation des scripts de simulation",
}


def _set_job_progress(job: Any, *, progress: int, message: str, detail: dict[str, Any]) -> None:
    job.meta.update({"progress": progress, "message": message, "progress_detail": detail})
    job.save_meta()


def prepare_simulation_job(
    *,
    task_id: str,
    simulation_id: str,
    simulation_requirement: str,
    document_text: str,
    entity_types: list[str],
    use_llm_for_profiles: bool,
    parallel_profile_count: int,
    locale: str,
) -> dict[str, Any]:
    """Prépare une simulation dans le processus RQ, avec progression durable."""
    from rq import get_current_job

    from app.services.simulation_manager import SimulationManager, SimulationStatus

    job = get_current_job()
    if job is None:
        raise RuntimeError("La préparation exige un job RQ actif")

    app = create_app()
    with app.app_context():
        storage = app.extensions.get("neo4j_storage")
        if storage is None:
            raise RuntimeError("Le stockage Neo4j est indisponible")

        manager = SimulationManager()
        stage_details: dict[str, dict[str, Any]] = {}
        _set_job_progress(
            job,
            progress=0,
            message="Démarrage de la préparation de la simulation",
            detail={"current_stage": "reading", "stage_index": 1, "total_stages": 4},
        )

        def progress_callback(stage: str, progress: int, message: str, **kwargs: Any) -> None:
            start, end = _STAGE_WEIGHTS.get(stage, (0, 100))
            current_progress = int(start + (end - start) * progress / 100)
            stage_index = list(_STAGE_WEIGHTS).index(stage) + 1 if stage in _STAGE_WEIGHTS else 1
            stage_details[stage] = {
                "stage_name": _STAGE_NAMES.get(stage, stage),
                "stage_progress": progress,
                "current": kwargs.get("current", 0),
                "total": kwargs.get("total", 0),
                "item_name": kwargs.get("item_name", ""),
            }
            detail = stage_details[stage]
            prefix = f"[{stage_index}/4] {_STAGE_NAMES.get(stage, stage)}"
            detailed_message = f"{prefix} : {detail['current']}/{detail['total']} — {message}" if detail["total"] else f"{prefix} : {message}"
            _set_job_progress(
                job,
                progress=current_progress,
                message=detailed_message,
                detail={
                    "current_stage": stage,
                    "current_stage_name": _STAGE_NAMES.get(stage, stage),
                    "stage_index": stage_index,
                    "total_stages": 4,
                    "stage_progress": progress,
                    "current_item": detail["current"],
                    "total_items": detail["total"],
                    "item_description": message,
                },
            )

        try:
            result_state = manager.prepare_simulation(
                simulation_id=simulation_id,
                simulation_requirement=simulation_requirement,
                document_text=document_text,
                defined_entity_types=entity_types,
                use_llm_for_profiles=use_llm_for_profiles,
                progress_callback=progress_callback,
                parallel_profile_count=parallel_profile_count,
                storage=storage,
                locale=locale,
            )
        except Exception as exc:
            state = manager.get_simulation(simulation_id)
            if state:
                state.status = SimulationStatus.FAILED
                state.error = str(exc)
                manager._save_simulation_state(state)
            _set_job_progress(job, progress=0, message="Préparation échouée", detail={"error_code": "SIMULATION_PREPARATION_FAILED"})
            logger.exception("Préparation échouée task=%s simulation=%s", task_id, simulation_id)
            raise

        result = result_state.to_simple_dict()
        _set_job_progress(job, progress=100, message="Préparation terminée", detail={"current_stage": "completed", "stage_index": 4, "total_stages": 4})
        return result
