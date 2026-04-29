"""Unit tests for ``GET /api/calibration/simulations`` (US-045).

The endpoint is the inbox layer that feeds the « Sims à évaluer »
section on /calibration: it lists the public sims an operator can mark
inline so the aggregate Brier moves on the same page after each verdict.

We exercise three layers in isolation, mirroring the test_unit_calibration
pattern so a regression in any of them fails loudly:

  1. ``_gather_evaluable_simulations`` — the disk-walking + filter layer.
     We patch ``SimulationManager`` so the test stays hermetic and drive
     each branch (status filter, template filter, sim without
     simulation_config, sim without trajectory, sim without outcome).
  2. ``_build_summary_first_words`` — pure helper, hand-picked inputs.
  3. ``GET /api/calibration/simulations`` — the Flask route via the test
     client. We stub Neo4jStorage so the app factory does not dial a
     real DB.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ─── Fakes (lifted from test_unit_calibration.py — kept local so a
#     change to that file does not silently break this one) ────────────

class _FakeStatus:
    """Stand-in for ``SimulationStatus`` — only the ``.value`` attribute
    is read by the endpoint, so we expose just that."""

    def __init__(self, value: str = "completed"):
        self.value = value


def _make_state(
    simulation_id: str,
    *,
    is_public: bool = True,
    status: str = "completed",
    created_at: str = "2026-04-22T10:12:34",
):
    """Lightweight stand-in for ``SimulationState`` with only the
    attributes the inbox helper reads."""

    class _State:
        pass

    s = _State()
    s.simulation_id = simulation_id
    s.is_public = is_public
    s.profiles_count = 100
    s.created_at = created_at
    s.parent_simulation_id = None
    s.status = _FakeStatus(status)
    return s


def _write_outcome(sim_dir: Path, label: str, url: str = "https://example.com/proof") -> None:
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / "outcome.json").write_text(json.dumps({
        "label": label,
        "outcome_url": url,
        "outcome_summary": f"Outcome was {label}.",
        "submitted_at": "2026-04-27T10:00:00+00:00",
    }))


def _write_trajectory_with_bullish_share(sim_dir: Path, num_bullish: int, total: int) -> None:
    """Same shape as test_unit_calibration's helper — a final snapshot
    yielding exactly ``num_bullish / total`` as the bullish share."""
    sim_dir.mkdir(parents=True, exist_ok=True)
    positions = {}
    for i in range(num_bullish):
        positions[f"b{i}"] = {"topic": 0.5}
    for i in range(total - num_bullish):
        positions[f"n{i}"] = {"topic": 0.0}
    (sim_dir / "trajectory.json").write_text(json.dumps({
        "snapshots": [
            {"round_num": 0, "belief_positions": {a: {"topic": 0.0} for a in positions}},
            {"round_num": 1, "belief_positions": positions},
        ],
    }))


def _write_config(
    sim_dir: Path,
    *,
    template_id: str | None = None,
    requirement: str | None = None,
    title: str | None = None,
) -> None:
    sim_dir.mkdir(parents=True, exist_ok=True)
    cfg: dict = {
        "time_config": {"minutes_per_round": 60, "total_simulation_hours": 12},
    }
    if template_id is not None:
        cfg["template_id"] = template_id
    if requirement is not None:
        cfg["simulation_requirement"] = requirement
    if title is not None:
        cfg["title"] = title
    (sim_dir / "simulation_config.json").write_text(json.dumps(cfg))


# ─── Workspace fixture — mirrors the calibration_workspace pattern ───────


@pytest.fixture
def evaluables_workspace(tmp_path: Path, monkeypatch):
    """Spin up a fake simulation data directory + a fake
    ``SimulationManager.list_simulations()`` so the inbox helper can
    walk a hand-picked cohort.

    Returns a builder that lets each test register simulations with the
    artifacts (outcome, trajectory, config) it cares about.
    """
    from app.api import calibration as calib_mod
    from app.config import Config as _Config

    monkeypatch.setattr(_Config, "WONDERWALL_SIMULATION_DATA_DIR", str(tmp_path))

    states: list = []

    def add_sim(
        sim_id: str,
        *,
        bullish: int | None = 4,
        total: int = 5,
        label: str | None = None,
        template_id: str | None = None,
        is_public: bool = True,
        status: str = "completed",
        created_at: str = "2026-04-22T10:12:34",
        requirement: str | None = "First sentence here. Second sentence after.",
        title: str | None = None,
        with_config: bool = True,
    ):
        sim_dir = tmp_path / sim_id
        if label is not None:
            _write_outcome(sim_dir, label)
        if bullish is not None:
            _write_trajectory_with_bullish_share(sim_dir, bullish, total)
        if with_config:
            _write_config(
                sim_dir,
                template_id=template_id,
                requirement=requirement,
                title=title,
            )
        states.append(_make_state(
            sim_id,
            is_public=is_public,
            status=status,
            created_at=created_at,
        ))
        return sim_dir

    class _FakeManager:
        def list_simulations(self):
            return list(states)

    monkeypatch.setattr(calib_mod, "SimulationManager", lambda: _FakeManager())

    return type("Workspace", (), {
        "add_sim": staticmethod(add_sim),
        "tmp_path": tmp_path,
    })


# ─── _build_summary_first_words: pure helper ─────────────────────────────


def test_summary_first_words_uses_first_sentence():
    """Headline is the first sentence of ``simulation_requirement``,
    cut on the first ``.``/``!``/``?`` followed by whitespace so a
    period inside a token (« U.S. ») does not truncate prematurely."""
    from app.api.calibration import _build_summary_first_words

    cfg = {"simulation_requirement": "Robinhood stock shrugs off a 47% crash. Then more text."}
    out = _build_summary_first_words(cfg, fallback_id="sim_x")
    assert out == "Robinhood stock shrugs off a 47% crash."


def test_summary_first_words_falls_back_to_title():
    """No ``simulation_requirement`` → fall back to ``title``."""
    from app.api.calibration import _build_summary_first_words

    cfg = {"title": "My Simulation Title"}
    out = _build_summary_first_words(cfg, fallback_id="sim_x")
    assert out == "My Simulation Title"


def test_summary_first_words_falls_back_to_id_when_empty_config():
    """Neither requirement nor title → return the simulation id so the
    card always has something visible."""
    from app.api.calibration import _build_summary_first_words

    out = _build_summary_first_words({}, fallback_id="sim_abc123")
    assert out == "sim_abc123"


# ─── _gather_evaluable_simulations: filter + sort ────────────────────────


def test_inbox_pending_excludes_evaluated_sims(evaluables_workspace):
    """Status filter ``pending`` (default) → only sims without
    outcome.json. The sim with an outcome is excluded."""
    from app.api.calibration import _gather_evaluable_simulations

    evaluables_workspace.add_sim("sim_pending", bullish=4, total=5, label=None)
    evaluables_workspace.add_sim("sim_done", bullish=3, total=5, label="correct")

    rows = _gather_evaluable_simulations(status_filter="pending", template=None)
    ids = [r["id"] for r in rows]
    assert ids == ["sim_pending"]
    assert rows[0]["outcome"] is None
    assert rows[0]["outcome_url"] is None
    assert rows[0]["predicted_bullish_pct"] == pytest.approx(0.8)


def test_inbox_evaluated_returns_only_marked(evaluables_workspace):
    """Status filter ``evaluated`` → only sims WITH outcome.json."""
    from app.api.calibration import _gather_evaluable_simulations

    evaluables_workspace.add_sim("sim_pending", bullish=4, total=5, label=None)
    evaluables_workspace.add_sim(
        "sim_done",
        bullish=3, total=5,
        label="correct",
    )

    rows = _gather_evaluable_simulations(status_filter="evaluated", template=None)
    ids = [r["id"] for r in rows]
    assert ids == ["sim_done"]
    assert rows[0]["outcome"] == "correct"
    assert rows[0]["outcome_url"] == "https://example.com/proof"


def test_inbox_all_returns_both(evaluables_workspace):
    """Status filter ``all`` → no filter, every public+completed sim
    shows up regardless of outcome state."""
    from app.api.calibration import _gather_evaluable_simulations

    evaluables_workspace.add_sim(
        "sim_pending",
        bullish=4, total=5,
        label=None,
        created_at="2026-04-21T10:00:00",
    )
    evaluables_workspace.add_sim(
        "sim_done",
        bullish=3, total=5,
        label="correct",
        created_at="2026-04-22T10:00:00",
    )

    rows = _gather_evaluable_simulations(status_filter="all", template=None)
    ids = [r["id"] for r in rows]
    # most-recent first
    assert ids == ["sim_done", "sim_pending"]


def test_inbox_template_filter_excludes_other_templates(evaluables_workspace):
    """The ``template`` filter narrows to sims spawned from one preset.
    Sims without a ``template_id`` config key are excluded entirely
    when the filter is set — same posture as the brier endpoint."""
    from app.api.calibration import _gather_evaluable_simulations

    evaluables_workspace.add_sim(
        "sim_crypto", bullish=4, total=5, label=None,
        template_id="crypto_launch",
    )
    evaluables_workspace.add_sim(
        "sim_crisis", bullish=2, total=5, label=None,
        template_id="corporate_crisis",
    )
    evaluables_workspace.add_sim(
        "sim_adhoc", bullish=3, total=5, label=None,
        template_id=None,
    )

    rows = _gather_evaluable_simulations(
        status_filter="pending", template="crypto_launch",
    )
    assert [r["id"] for r in rows] == ["sim_crypto"]
    assert rows[0]["template_id"] == "crypto_launch"

    # Without the filter, all three show up.
    all_rows = _gather_evaluable_simulations(status_filter="pending", template=None)
    assert sorted(r["id"] for r in all_rows) == ["sim_adhoc", "sim_crisis", "sim_crypto"]


def test_inbox_excludes_private_sims(evaluables_workspace):
    """Private sims never reach the public inbox — same publish gate as
    the rest of /calibration."""
    from app.api.calibration import _gather_evaluable_simulations

    evaluables_workspace.add_sim("sim_public", bullish=4, total=5, label=None, is_public=True)
    evaluables_workspace.add_sim("sim_private", bullish=4, total=5, label=None, is_public=False)

    rows = _gather_evaluable_simulations(status_filter="pending", template=None)
    assert [r["id"] for r in rows] == ["sim_public"]


def test_inbox_excludes_failed_or_created_sims(evaluables_workspace):
    """A sim that never reached completed/running/stopped/paused has no
    prediction worth annotating — it must not show up in the inbox."""
    from app.api.calibration import _gather_evaluable_simulations

    evaluables_workspace.add_sim("sim_completed", bullish=4, total=5, label=None, status="completed")
    evaluables_workspace.add_sim("sim_failed", bullish=4, total=5, label=None, status="failed")
    evaluables_workspace.add_sim("sim_created", bullish=4, total=5, label=None, status="created")
    evaluables_workspace.add_sim("sim_running", bullish=4, total=5, label=None, status="running")

    rows = _gather_evaluable_simulations(status_filter="pending", template=None)
    ids = sorted(r["id"] for r in rows)
    assert ids == ["sim_completed", "sim_running"]


def test_inbox_minimum_payload_when_config_missing(evaluables_workspace, tmp_path):
    """A sim without ``simulation_config.json`` and without
    ``trajectory.json`` must still surface in the inbox so the operator
    can at least open it. Required fields ``id``, ``title``, ``status``
    are present; ``predicted_bullish_pct`` degrades to ``None``."""
    from app.api.calibration import _gather_evaluable_simulations

    evaluables_workspace.add_sim(
        "sim_bare",
        bullish=None,        # no trajectory.json
        label=None,
        with_config=False,   # no simulation_config.json
    )

    rows = _gather_evaluable_simulations(status_filter="pending", template=None)
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "sim_bare"
    assert row["title"] == "sim_bare"   # falls back to id
    assert row["status"] == "completed"
    assert row["predicted_bullish_pct"] is None
    assert row["template_id"] is None
    assert row["template_name"] is None
    assert row["summary_first_words"] == "sim_bare"


def test_inbox_sorts_by_created_at_desc(evaluables_workspace):
    """Most-recent sims first — the operator scans from the top."""
    from app.api.calibration import _gather_evaluable_simulations

    evaluables_workspace.add_sim("sim_old", bullish=4, total=5, label=None, created_at="2026-01-01T00:00:00")
    evaluables_workspace.add_sim("sim_new", bullish=4, total=5, label=None, created_at="2026-04-22T10:00:00")
    evaluables_workspace.add_sim("sim_mid", bullish=4, total=5, label=None, created_at="2026-03-15T05:00:00")

    rows = _gather_evaluable_simulations(status_filter="pending", template=None)
    assert [r["id"] for r in rows] == ["sim_new", "sim_mid", "sim_old"]


# ─── Endpoint: HTTP-level integration ───────────────────────────────────


@pytest.fixture
def evaluables_client(monkeypatch, tmp_path):
    """Spin up the Flask app with a fresh empty data directory.

    Stubs ``Neo4jStorage`` so the app factory doesn't dial a real DB —
    the inbox endpoint never touches Neo4j, so a noop is safe.
    """
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
    return app.test_client()


def test_endpoint_returns_empty_list_when_no_data(evaluables_client):
    """No sims on disk ⇒ 200 with an empty page and ``has_more: false``.
    """
    resp = evaluables_client.get("/api/calibration/simulations")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"] == []
    pagination = body["pagination"]
    assert pagination["limit"] == 20
    assert pagination["offset"] == 0
    assert pagination["total"] == 0
    assert pagination["has_more"] is False
    assert body["filters"]["applied"]["status"] == "pending"
    assert body["filters"]["applied"]["template"] is None


def test_endpoint_pagination_clamps_limit(evaluables_client):
    """A buggy client passing ``limit=9999`` must be clamped to 100 so
    the server never walks an unbounded slice."""
    resp = evaluables_client.get("/api/calibration/simulations?limit=9999&offset=-5")
    assert resp.status_code == 200
    pagination = resp.get_json()["pagination"]
    assert pagination["limit"] == 100
    assert pagination["offset"] == 0


def test_endpoint_normalises_unknown_status(evaluables_client):
    """A typo'd status query parameter falls back to ``pending`` rather
    than 400 — keeps stale bookmarks working."""
    resp = evaluables_client.get("/api/calibration/simulations?status=banana")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["filters"]["applied"]["status"] == "pending"


def test_endpoint_accessible_without_auth(evaluables_client):
    """No admin gate — same posture as ``GET /brier-score``. The data
    is already opted-in to the public gallery, so no privacy delta."""
    resp = evaluables_client.get("/api/calibration/simulations")
    assert resp.status_code == 200
    assert resp.status_code not in (401, 403)
