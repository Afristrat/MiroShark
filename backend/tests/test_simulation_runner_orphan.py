"""US-145 — réconciliation des states orphelins du SimulationRunner.

Couvre :
    01. `_is_pid_alive(None)` / (0) / (-1) → False (entrées invalides)
    02. `_is_pid_alive(os.getpid())` → True (process courant)
    03. `_is_pid_alive(<dead-pid>)` → False (pid jamais vu / mort)
    04. `_reconcile_orphaned_state` ne touche pas un state COMPLETED/FAILED/IDLE
    05. `_reconcile_orphaned_state` skip si un monitor thread tourne dans
        `cls._processes` (même backend instance)
    06. `_reconcile_orphaned_state` skip si le PID est encore alive
        (multi-replica scenario)
    07. `_reconcile_orphaned_state` force RUNNING + dead PID → FAILED
        avec un `error` explicite
    08. `_reconcile_orphaned_state` force STARTING + no PID → FAILED
    09. `get_run_state()` applique la réconciliation au chargement

Ces tests valident le filet anti-zombie ajouté en réaction à l'incident
prod 2026-05-07 : worker spawné, crash silencieux ~4 min plus tard,
`simulation_config.json` resté à `runner_status=RUNNING / error=null`
indéfiniment, frontend incapable de distinguer worker mort vs sim lente.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

# Ajout backend/ au sys.path pour `import app.*`
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def runner(tmp_path, monkeypatch):
    """Charge SimulationRunner avec un RUN_STATE_DIR isolé par test."""
    from app.services import simulation_runner as sr_mod

    monkeypatch.setattr(sr_mod.SimulationRunner, "RUN_STATE_DIR", str(tmp_path))
    # Reset l'état in-memory pour ne pas bavarder entre tests
    sr_mod.SimulationRunner._run_states.clear()
    sr_mod.SimulationRunner._processes.clear()
    sr_mod.SimulationRunner._monitor_threads.clear()
    return sr_mod


@pytest.fixture
def fresh_state(runner):
    """Construit un SimulationRunState neuf avec sim_id valide."""

    def _make(status: str = "running", pid: int = 99999) -> "runner.SimulationRunState":
        sim_id = "sim_aabbcc112233"
        state = runner.SimulationRunState(
            simulation_id=sim_id,
            runner_status=runner.RunnerStatus(status),
            current_round=5,
            total_rounds=15,
            twitter_running=True,
            reddit_running=True,
            polymarket_running=True,
            started_at=datetime.now().isoformat(),
            process_pid=pid,
        )
        return state

    return _make


# ── Tests _is_pid_alive ──────────────────────────────────────────────────────


class TestIsPidAlive:

    def test_none_pid_is_dead(self, runner):
        assert runner._is_pid_alive(None) is False

    def test_zero_pid_is_dead(self, runner):
        assert runner._is_pid_alive(0) is False

    def test_negative_pid_is_dead(self, runner):
        assert runner._is_pid_alive(-1) is False

    def test_current_process_is_alive(self, runner):
        # Notre process pytest est forcément vivant pendant l'exécution.
        assert runner._is_pid_alive(os.getpid()) is True

    def test_obviously_dead_pid_is_dead(self, runner):
        # PID typiquement libre : on prend un nombre énorme jamais alloué.
        # Si la machine a vraiment 999_999_999 PIDs actifs, ce test
        # serait flaky. Pas le cas en pratique (Linux pid_max default 32k,
        # Windows alloue séquentiellement < 100k pour un user).
        assert runner._is_pid_alive(999_999_999) is False


# ── Tests _reconcile_orphaned_state ──────────────────────────────────────────


class TestReconcileOrphanedState:

    def test_completed_state_not_touched(self, runner, fresh_state):
        """Un state COMPLETED ne doit pas être réécrit."""
        state = fresh_state(status="completed")
        runner.SimulationRunner._reconcile_orphaned_state(state)
        assert state.runner_status == runner.RunnerStatus.COMPLETED
        assert state.error is None

    def test_failed_state_not_touched(self, runner, fresh_state):
        """Un state FAILED conservé tel quel (déjà terminal)."""
        state = fresh_state(status="failed")
        state.error = "boom"
        runner.SimulationRunner._reconcile_orphaned_state(state)
        assert state.runner_status == runner.RunnerStatus.FAILED
        assert state.error == "boom"

    def test_idle_state_not_touched(self, runner, fresh_state):
        """Un state IDLE/PAUSED/STOPPED non concerné par le filet anti-zombie."""
        for status in ("idle", "stopped"):
            state = fresh_state(status=status)
            runner.SimulationRunner._reconcile_orphaned_state(state)
            assert state.runner_status == runner.RunnerStatus(status)

    def test_running_with_alive_pid_not_touched(self, runner, fresh_state):
        """RUNNING + PID encore vivant (autre instance) → on respecte."""
        state = fresh_state(status="running", pid=os.getpid())
        runner.SimulationRunner._reconcile_orphaned_state(state)
        assert state.runner_status == runner.RunnerStatus.RUNNING

    def test_running_with_active_subprocess_not_touched(self, runner, fresh_state):
        """RUNNING + subprocess piloté localement (cls._processes) → on respecte."""
        state = fresh_state(status="running", pid=999_999_999)

        class _FakeProcess:
            def poll(self):
                return None  # alive

        runner.SimulationRunner._processes[state.simulation_id] = _FakeProcess()
        try:
            runner.SimulationRunner._reconcile_orphaned_state(state)
            assert state.runner_status == runner.RunnerStatus.RUNNING
        finally:
            runner.SimulationRunner._processes.pop(state.simulation_id, None)

    def test_running_with_dead_pid_marks_failed(self, runner, fresh_state):
        """RUNNING + PID mort + pas de subprocess local → FAILED + error explicite."""
        state = fresh_state(status="running", pid=999_999_999)
        runner.SimulationRunner._reconcile_orphaned_state(state)
        assert state.runner_status == runner.RunnerStatus.FAILED
        assert state.error is not None
        assert "Worker process disappeared" in state.error
        assert state.completed_at is not None
        assert state.twitter_running is False
        assert state.reddit_running is False
        assert state.polymarket_running is False

    def test_starting_with_no_pid_marks_failed(self, runner, fresh_state):
        """STARTING sans PID enregistré → FAILED (worker n'a jamais démarré proprement)."""
        state = fresh_state(status="starting", pid=None)
        runner.SimulationRunner._reconcile_orphaned_state(state)
        assert state.runner_status == runner.RunnerStatus.FAILED
        assert state.error is not None

    def test_stopping_with_dead_pid_marks_failed(self, runner, fresh_state):
        """STOPPING + PID mort → FAILED (le subprocess est parti avant qu'on
        ait pu le sigterm/sigkill cleanly)."""
        state = fresh_state(status="stopping", pid=999_999_999)
        runner.SimulationRunner._reconcile_orphaned_state(state)
        assert state.runner_status == runner.RunnerStatus.FAILED

    def test_existing_error_preserved(self, runner, fresh_state):
        """Si state.error contient déjà une trace, on ne l'écrase pas."""
        state = fresh_state(status="running", pid=999_999_999)
        state.error = "Previous detailed error"
        runner.SimulationRunner._reconcile_orphaned_state(state)
        assert state.error == "Previous detailed error"


# ── Tests get_run_state intégration ──────────────────────────────────────────


class TestGetRunStateOrphanIntegration:
    """get_run_state doit appliquer la réconciliation au chargement."""

    def test_loads_orphan_from_disk_and_marks_failed(self, runner, tmp_path):
        """state.json sur disque RUNNING + PID mort → get_run_state retourne FAILED."""
        sim_id = "sim_aabbcc112233"
        sim_dir = tmp_path / sim_id
        sim_dir.mkdir()
        # Construis directement le state via _save_run_state sur un state mort
        state = runner.SimulationRunState(
            simulation_id=sim_id,
            runner_status=runner.RunnerStatus.RUNNING,
            current_round=33,
            total_rounds=48,
            started_at=datetime.now().isoformat(),
            process_pid=999_999_999,  # PID volontairement invalide
        )
        runner.SimulationRunner._save_run_state(state)
        # Force un reload depuis disque (bypass le cache in-memory)
        runner.SimulationRunner._run_states.clear()

        loaded = runner.SimulationRunner.get_run_state(sim_id)
        assert loaded is not None
        assert loaded.runner_status == runner.RunnerStatus.FAILED
        assert "disappeared" in (loaded.error or "")

    def test_returns_none_for_unknown_sim(self, runner):
        """get_run_state d'une sim inexistante → None (pas d'écriture en disque)."""
        out = runner.SimulationRunner.get_run_state("sim_zzzzzzzzzzzz")
        assert out is None
