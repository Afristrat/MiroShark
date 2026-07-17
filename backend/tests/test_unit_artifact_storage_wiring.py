"""Tests unitaires US-221 — câblage des checkpoints d'écriture ET de lecture
(ADR-005) : fin de préparation + rematérialisation avant démarrage
(SimulationManager/SimulationRunner.start_simulation), fin de run
(SimulationRunner._monitor_simulation). Le checkpoint d'écriture de fin de
génération de rapport (ReportAgent.generate_report) n'est pas testé
end-to-end ici : la méthode mobilise un pipeline LLM/ReAct multi-phases dont
le mock complet serait disproportionné par rapport au risque d'une ligne
d'appel supplémentaire vers une fonction déjà testée en isolation
(test_unit_artifact_storage.py) et qui ne lève jamais. Cf. .ralph/progress.md
pour la décision de portée.
"""

from __future__ import annotations

import json
import os
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services import artifact_storage as artifact_storage_module
from app.services import simulation_manager as simulation_manager_module
from app.services import simulation_runner as simulation_runner_module
from app.services import webhook_service as webhook_service_module
from app.services.entity_reader import FilteredEntities
from app.services.simulation_manager import SimulationManager
from app.services.simulation_runner import RunnerStatus, SimulationRunner, SimulationRunState


class _FakeEntityReaderNoMatch:
    """Court-circuite la lecture du graphe : 0 entité trouvée (branche
    d'échec précoce déjà existante dans prepare_simulation, ligne ~430)."""

    def __init__(self, storage):
        pass

    def filter_defined_entities(self, **kwargs):
        return FilteredEntities(entities=[], entity_types=set(), total_count=0, filtered_count=0)


class _FakeEntityReaderRaises:
    def __init__(self, storage):
        pass

    def filter_defined_entities(self, **kwargs):
        raise RuntimeError("simulated graph read failure")


@pytest.fixture
def manager(tmp_path, monkeypatch):
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(tmp_path))
    return SimulationManager()


class TestPrepareSimulationSyncsArtifacts:
    def test_no_matching_entities_still_syncs_directory(self, manager, monkeypatch):
        """Branche de sortie précoce (existante, ligne ~430) : passe quand
        même par le `finally` — c'est justement le point de la story."""
        monkeypatch.setattr(simulation_manager_module, "EntityReader", _FakeEntityReaderNoMatch)
        sync_mock = Mock(return_value=0)
        monkeypatch.setattr(
            artifact_storage_module, "sync_directory_to_storage", sync_mock,
        )

        state = manager.create_simulation(project_id="p1", graph_id="g1")
        result = manager.prepare_simulation(
            simulation_id=state.simulation_id,
            simulation_requirement="req",
            document_text="doc",
            storage=Mock(),
        )

        assert result.status.value == "failed"
        sync_mock.assert_called_once()
        called_sim_id, called_dir = sync_mock.call_args[0]
        assert called_sim_id == state.simulation_id
        assert called_dir.endswith(state.simulation_id)

    def test_exception_during_preparation_still_syncs_directory(self, manager, monkeypatch):
        """Best-effort : même un crash en cours de préparation ne doit pas
        empêcher la synchronisation de ce qui a déjà été écrit sur disque."""
        monkeypatch.setattr(simulation_manager_module, "EntityReader", _FakeEntityReaderRaises)
        sync_mock = Mock(return_value=0)
        monkeypatch.setattr(
            artifact_storage_module, "sync_directory_to_storage", sync_mock,
        )

        state = manager.create_simulation(project_id="p2", graph_id="g2")
        with pytest.raises(RuntimeError, match="simulated graph read failure"):
            manager.prepare_simulation(
                simulation_id=state.simulation_id,
                simulation_requirement="req",
                document_text="doc",
                storage=Mock(),
            )

        sync_mock.assert_called_once()
        called_sim_id, _called_dir = sync_mock.call_args[0]
        assert called_sim_id == state.simulation_id


class _FakeCompletedProcess:
    """Process déjà terminé — le monitor thread sort de la boucle au 1er tour."""

    def __init__(self, returncode: int = 0):
        self.returncode = returncode

    def poll(self):
        return self.returncode


class TestMonitorSimulationSyncsArtifactsAtRunEnd:
    def _seed_state(self, monkeypatch, tmp_path, simulation_id: str, returncode: int):
        monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(tmp_path))
        state = SimulationRunState(simulation_id=simulation_id, runner_status=RunnerStatus.RUNNING)
        # `_run_states`/`_processes` sont des dicts de CLASSE partagés entre
        # tous les tests du process pytest. On remplace l'attribut par une
        # copie enrichie (jamais de mutation in-place du dict original) pour
        # que monkeypatch restaure l'objet original intact au teardown — pas
        # de pollution pour d'autres modules (ex. test_simulation_runner_orphan.py).
        monkeypatch.setattr(
            SimulationRunner, "_run_states",
            {**SimulationRunner._run_states, simulation_id: state},
        )
        monkeypatch.setattr(
            SimulationRunner, "_processes",
            {**SimulationRunner._processes, simulation_id: _FakeCompletedProcess(returncode)},
        )
        return state

    def test_natural_completion_syncs_directory(self, tmp_path, monkeypatch):
        simulation_id = "sim_monitor_ok"
        self._seed_state(monkeypatch, tmp_path, simulation_id, returncode=0)
        sync_mock = Mock(return_value=0)
        monkeypatch.setattr(
            artifact_storage_module, "sync_directory_to_storage", sync_mock,
        )

        # push_notification_service importe `fcntl` (POSIX-only) — indisponible
        # sous Windows. Pas besoin de le mocker : le SUT enveloppe déjà cet
        # appel dans un try/except Exception (résilience existante), donc le
        # ModuleNotFoundError est avalé exactement comme n'importe quel autre
        # échec du canal push, sans faire échouer le test.
        monkeypatch.setattr(
            webhook_service_module, "fire_webhook_for_simulation", Mock(),
        )
        SimulationRunner._monitor_simulation(simulation_id)

        sync_mock.assert_called_once_with(simulation_id, str(tmp_path / simulation_id))

    def test_process_failure_still_syncs_directory(self, tmp_path, monkeypatch):
        simulation_id = "sim_monitor_fail"
        self._seed_state(monkeypatch, tmp_path, simulation_id, returncode=1)
        sync_mock = Mock(return_value=0)
        monkeypatch.setattr(
            artifact_storage_module, "sync_directory_to_storage", sync_mock,
        )

        monkeypatch.setattr(
            webhook_service_module, "fire_webhook_for_simulation", Mock(),
        )
        SimulationRunner._monitor_simulation(simulation_id)

        sync_mock.assert_called_once_with(simulation_id, str(tmp_path / simulation_id))


class _FakeStartedProcess:
    """Popen factice : déjà terminé (poll() renvoie tout de suite), a un pid."""

    def __init__(self, pid: int = 4242, returncode: int = 0):
        self.pid = pid
        self.returncode = returncode

    def poll(self):
        return self.returncode


def _fake_supabase_client_with_config(simulation_id: str, config_bytes: bytes):
    """Client factice : un seul artefact indexé (simulation_config.json)."""
    client = Mock()
    row = {
        "simulation_id": simulation_id,
        "relative_path": "simulation_config.json",
        "storage_path": f"simulations/{simulation_id}/simulation_config.json",
    }
    client.table.return_value = client
    client.select.return_value = client
    client.eq.return_value = client
    client.execute.return_value = SimpleNamespace(data=[row])
    client.storage = SimpleNamespace(
        from_=lambda bucket_id: SimpleNamespace(download=lambda path: config_bytes),
    )
    return client


class TestStartSimulationHydratesBeforeReadingConfig:
    """AC1 : /start ne doit pas échouer avec « config manquante » si le volume
    local a été vidé entre /prepare et /start, tant que Storage a le fichier."""

    def test_config_absent_locally_but_present_in_storage_is_rematerialized(
        self, tmp_path, monkeypatch,
    ):
        simulation_id = "sim_start_hydrate"
        monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(tmp_path))
        monkeypatch.setattr(SimulationRunner, "_run_states", {**SimulationRunner._run_states})
        monkeypatch.setattr(SimulationRunner, "_processes", {**SimulationRunner._processes})
        monkeypatch.setattr(
            SimulationRunner, "_action_queues", {**SimulationRunner._action_queues},
        )

        config = {
            "time_config": {"total_simulation_hours": 1, "minutes_per_round": 30},
        }
        fake_client = _fake_supabase_client_with_config(
            simulation_id, json.dumps(config).encode("utf-8"),
        )
        monkeypatch.setattr(artifact_storage_module, "get_supabase_admin", lambda: fake_client)

        # Le dossier local n'existe PAS du tout (volume Coolify vidé) : sans
        # le chokepoint ensure_simulation_dir_hydrated, ceci lèverait
        # ValueError("Simulation config does not exist...").
        sim_dir = os.path.join(str(tmp_path), simulation_id)
        assert not os.path.isdir(sim_dir)

        fake_process = _FakeStartedProcess()
        monkeypatch.setattr(simulation_runner_module.subprocess, "Popen", lambda *a, **k: fake_process)
        monkeypatch.setattr(
            artifact_storage_module, "sync_directory_to_storage", Mock(return_value=0),
        )
        monkeypatch.setattr(
            webhook_service_module, "fire_webhook_for_simulation", Mock(),
        )

        # Le monitor thread réel n'est pas pertinent ici (déjà testé en
        # isolation dans TestMonitorSimulationSyncsArtifactsAtRunEnd) — un vrai
        # thread daemon courrait avec ce test contre le même objet `state`
        # mutable (race non déterministe sur runner_status). On neutralise son
        # démarrage pour isoler strictement ce qui est sous test : l'hydratation
        # avant lecture de la config.
        fake_thread = Mock()
        monkeypatch.setattr(
            simulation_runner_module.threading, "Thread", lambda *a, **k: fake_thread,
        )

        run_state = SimulationRunner.start_simulation(
            simulation_id=simulation_id, platform="twitter",
        )

        assert run_state.runner_status == RunnerStatus.RUNNING
        assert os.path.exists(os.path.join(sim_dir, "simulation_config.json"))
