"""Unit tests for the public Brier-score / calibration-plot endpoint.

Exercises three layers in isolation so a regression in any of them
fails loudly:

  1. ``_compute_calibration`` — pure aggregation. We feed a hand-picked
     5-sim dataset whose Brier score and bucket distribution can be
     re-derived in a calculator (Brier = 0.08, accuracy = 0.6).
  2. ``_gather_samples`` — the disk-walking layer that turns a
     ``SimulationManager.list_simulations()`` result + on-disk
     ``outcome.json``/``trajectory.json`` artifacts into the tuples
     consumed by step 1. We patch the manager so the test stays
     hermetic, and we drive the helper through the template + date
     filters.
  3. ``GET /api/calibration/brier-score`` — the Flask route. We hit it
     with ``app.test_client()`` to verify (a) it returns 200 with
     ``brier == None`` when there is no data, and (b) no auth is
     required (the endpoint is the commercial argument — must be
     publicly callable).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ─── Fakes ───────────────────────────────────────────────────────────────────


class _FakeStatus:
    value = "completed"


def _make_state(
    simulation_id: str,
    *,
    is_public: bool = True,
    created_at: str = "2026-04-22T10:12:34",
):
    """Lightweight stand-in for ``SimulationState`` with only the
    attributes the calibration helper reads."""
    class _State:
        pass
    s = _State()
    s.simulation_id = simulation_id
    s.is_public = is_public
    s.profiles_count = 100
    s.created_at = created_at
    s.parent_simulation_id = None
    s.status = _FakeStatus()
    return s


def _write_outcome(sim_dir: Path, label: str) -> None:
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / "outcome.json").write_text(json.dumps({
        "label": label,
        "outcome_url": "https://example.com/proof",
        "outcome_summary": f"Outcome was {label}.",
        "submitted_at": "2026-04-27T10:00:00+00:00",
    }))


def _write_trajectory_with_bullish_share(sim_dir: Path, num_bullish: int, total: int) -> None:
    """Write a trajectory.json whose final snapshot yields exactly
    ``num_bullish / total`` as the bullish share (the predicted YES
    probability).

    Bullish iff mean topic position > 0.2 — we set bullish agents to
    0.5 and the rest to 0.0 (neutral) so the helper's threshold logic
    is exercised the same way it is in production.
    """
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


def _write_template_id(sim_dir: Path, template_id: str) -> None:
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / "simulation_config.json").write_text(json.dumps({
        "simulation_requirement": "Test scenario",
        "template_id": template_id,
        "time_config": {"minutes_per_round": 60, "total_simulation_hours": 12},
    }))


# ─── _compute_calibration: pure aggregation ──────────────────────────────────


def test_compute_calibration_brier_on_hand_picked_dataset():
    """Hand-picked 5-sim dataset whose Brier score can be re-derived
    on paper. The exact expected value is the contract: anyone changing
    the math has to update both this test and the formula.

        s1: p=0.8, correct  → Y=1.0, sq_err=0.04
        s2: p=0.6, partial  → Y=0.5, sq_err=0.01
        s3: p=0.3, incorrect→ Y=0.0, sq_err=0.09
        s4: p=0.9, correct  → Y=1.0, sq_err=0.01
        s5: p=0.5, wrong    → Y=0.0, sq_err=0.25
        ---
        sum = 0.40, n = 5 ⇒ Brier = 0.08
        accuracy = (correct + partial) / n = 3/5 = 0.6
    """
    from app.api.calibration import _compute_calibration

    samples = [
        (0.8, 1.0, "correct"),
        (0.6, 0.5, "partial"),
        (0.3, 0.0, "incorrect"),
        (0.9, 1.0, "correct"),
        (0.5, 0.0, "wrong"),
    ]

    result = _compute_calibration(samples)

    assert result["n"] == 5
    assert result["brier"] == pytest.approx(0.08, abs=1e-6)
    assert result["accuracy"] == pytest.approx(0.6, abs=1e-6)
    assert result["n_called_it"] == 2
    assert result["n_partial"] == 1
    assert result["n_wrong"] == 2


def test_compute_calibration_buckets_correctly_distributed():
    """Same 5-sim dataset; verify each prediction lands in the right
    decile bucket and that empty buckets are reported with ``n: 0``.

        p=0.3 → bucket idx 3 (centre 0.35)
        p=0.5 → bucket idx 5 (centre 0.55)
        p=0.6 → bucket idx 6 (centre 0.65)
        p=0.8 → bucket idx 8 (centre 0.85)
        p=0.9 → bucket idx 9 (centre 0.95)
    """
    from app.api.calibration import _compute_calibration

    samples = [
        (0.8, 1.0, "correct"),
        (0.6, 0.5, "partial"),
        (0.3, 0.0, "incorrect"),
        (0.9, 1.0, "correct"),
        (0.5, 0.0, "wrong"),
    ]

    plot = _compute_calibration(samples)["calibration_plot"]
    assert len(plot) == 10

    by_bucket = {row["bucket"]: row for row in plot}
    # Buckets that received samples
    assert by_bucket[0.35]["n"] == 1
    assert by_bucket[0.35]["predicted"] == pytest.approx(0.3, abs=1e-6)
    assert by_bucket[0.35]["observed"] == pytest.approx(0.0, abs=1e-6)

    assert by_bucket[0.55]["n"] == 1
    assert by_bucket[0.55]["observed"] == pytest.approx(0.0, abs=1e-6)  # wrong

    assert by_bucket[0.65]["n"] == 1
    assert by_bucket[0.65]["observed"] == pytest.approx(1.0, abs=1e-6)  # partial counts as hit

    assert by_bucket[0.85]["n"] == 1
    assert by_bucket[0.85]["observed"] == pytest.approx(1.0, abs=1e-6)

    assert by_bucket[0.95]["n"] == 1
    assert by_bucket[0.95]["observed"] == pytest.approx(1.0, abs=1e-6)

    # The other 5 buckets are empty — must still appear in the plot
    # so the frontend can render an evenly spaced grid.
    empty_centres = {0.05, 0.15, 0.25, 0.45, 0.75}
    for c in empty_centres:
        assert by_bucket[c]["n"] == 0
        assert by_bucket[c]["observed"] is None
        assert by_bucket[c]["predicted"] == c


def test_compute_calibration_empty_dataset_returns_none_brier():
    """No samples ⇒ ``brier`` and ``accuracy`` are ``None`` and the
    plot still has 10 zero-count buckets so the frontend can render an
    empty grid without branching on missing data."""
    from app.api.calibration import _compute_calibration

    result = _compute_calibration([])

    assert result["n"] == 0
    assert result["brier"] is None
    assert result["accuracy"] is None
    assert result["n_called_it"] == 0
    assert result["n_partial"] == 0
    assert result["n_wrong"] == 0
    assert len(result["calibration_plot"]) == 10
    for row in result["calibration_plot"]:
        assert row["n"] == 0
        assert row["observed"] is None


def test_bucket_index_handles_edges():
    """``p == 1.0`` lands in bucket 9 (closed-on-the-right at the top)
    and ``p == 0.0`` lands in bucket 0 (closed-on-the-left at the
    bottom). Out-of-range values are clipped — defense-in-depth in
    case a future trajectory yields a slightly out-of-range share."""
    from app.api.calibration import _bucket_index

    assert _bucket_index(0.0) == 0
    assert _bucket_index(0.05) == 0
    assert _bucket_index(0.099999) == 0
    assert _bucket_index(0.1) == 1
    assert _bucket_index(0.5) == 5
    assert _bucket_index(0.999) == 9
    assert _bucket_index(1.0) == 9
    # Defensive: out-of-range values should not crash.
    assert _bucket_index(-0.5) == 0
    assert _bucket_index(1.5) == 9


# ─── _gather_samples: filtering against on-disk artifacts ────────────────────


@pytest.fixture
def calibration_workspace(tmp_path: Path, monkeypatch):
    """Spin up a fake simulation data directory + matching
    ``SimulationManager.list_simulations`` result.

    Returns a builder that lets each test register simulations with
    the artifacts (outcome, trajectory, template_id) it cares about.
    """
    from app.api import calibration as calib_mod
    from app.config import Config as _Config

    monkeypatch.setattr(_Config, "WONDERWALL_SIMULATION_DATA_DIR", str(tmp_path))

    states: list = []

    def add_sim(
        sim_id: str,
        *,
        bullish: int,
        total: int,
        label: str | None,
        template_id: str | None = None,
        is_public: bool = True,
        created_at: str = "2026-04-22T10:12:34",
    ):
        sim_dir = tmp_path / sim_id
        if label is not None:
            _write_outcome(sim_dir, label)
        _write_trajectory_with_bullish_share(sim_dir, bullish, total)
        if template_id is not None:
            _write_template_id(sim_dir, template_id)
        states.append(_make_state(sim_id, is_public=is_public, created_at=created_at))
        return sim_dir

    class _FakeManager:
        def list_simulations(self):
            return list(states)

    monkeypatch.setattr(calib_mod, "SimulationManager", lambda: _FakeManager())

    return type("Workspace", (), {
        "add_sim": staticmethod(add_sim),
        "tmp_path": tmp_path,
    })


def test_gather_samples_skips_sims_without_outcome(calibration_workspace):
    """A simulation without an ``outcome.json`` artifact must not
    contribute to the Brier score — we cannot score what nobody marked.
    """
    from app.api.calibration import _gather_samples

    calibration_workspace.add_sim("sim_marked", bullish=4, total=5, label="correct")
    calibration_workspace.add_sim("sim_unmarked", bullish=4, total=5, label=None)

    samples = _gather_samples(template=None, date_from=None, date_to=None)

    assert len(samples) == 1
    p, y, label = samples[0]
    assert p == pytest.approx(0.8)
    assert y == 1.0
    assert label == "correct"


def test_gather_samples_skips_private_sims(calibration_workspace):
    """Calibration aggregates only over the publicly-published cohort —
    a private sim with an outcome is the operator's own QA, not a
    data point that should move the public Brier."""
    from app.api.calibration import _gather_samples

    calibration_workspace.add_sim("sim_public", bullish=4, total=5, label="correct", is_public=True)
    calibration_workspace.add_sim("sim_private", bullish=1, total=5, label="incorrect", is_public=False)

    samples = _gather_samples(template=None, date_from=None, date_to=None)
    assert len(samples) == 1


def test_gather_samples_template_filter_excludes_other_templates(calibration_workspace):
    """The ``template`` query parameter narrows the cohort to sims
    spawned from one preset. Sims without a ``template_id`` config key
    are excluded entirely — otherwise an ad-hoc sim would silently
    leak into every template's bucket."""
    from app.api.calibration import _gather_samples

    calibration_workspace.add_sim(
        "sim_crisis",
        bullish=4, total=5, label="correct",
        template_id="corporate_crisis",
    )
    calibration_workspace.add_sim(
        "sim_crypto",
        bullish=2, total=5, label="incorrect",
        template_id="crypto_launch",
    )
    calibration_workspace.add_sim(
        "sim_adhoc",
        bullish=3, total=5, label="partial",
        # no template_id → excluded by template filter
    )

    samples = _gather_samples(
        template="corporate_crisis",
        date_from=None,
        date_to=None,
    )
    assert len(samples) == 1
    assert samples[0][2] == "correct"

    # Without the filter, every marked sim shows up.
    all_samples = _gather_samples(template=None, date_from=None, date_to=None)
    assert len(all_samples) == 3


def test_gather_samples_date_range_filter(calibration_workspace):
    """``from`` and ``to`` are inclusive ``YYYY-MM-DD`` bounds against
    the simulation's ``created_at`` day."""
    from app.api.calibration import _gather_samples

    calibration_workspace.add_sim(
        "sim_jan",
        bullish=4, total=5, label="correct",
        created_at="2026-01-15T10:00:00",
    )
    calibration_workspace.add_sim(
        "sim_apr",
        bullish=3, total=5, label="partial",
        created_at="2026-04-22T10:00:00",
    )
    calibration_workspace.add_sim(
        "sim_jun",
        bullish=1, total=5, label="incorrect",
        created_at="2026-06-01T10:00:00",
    )

    # Bound covering only April.
    apr_only = _gather_samples(
        template=None,
        date_from="2026-04-01",
        date_to="2026-04-30",
    )
    assert len(apr_only) == 1
    assert apr_only[0][2] == "partial"

    # Lower bound only — picks up April + June.
    after_feb = _gather_samples(
        template=None,
        date_from="2026-02-01",
        date_to=None,
    )
    assert len(after_feb) == 2

    # Upper bound only — picks up January + April.
    before_may = _gather_samples(
        template=None,
        date_from=None,
        date_to="2026-04-30",
    )
    assert len(before_may) == 2


def test_gather_samples_skips_sims_without_trajectory(calibration_workspace, tmp_path):
    """An outcome-marked sim without a trajectory has no derivable
    predicted probability — we drop it rather than fabricate a 0.5
    fallback that would distort the Brier."""
    from app.api.calibration import _gather_samples

    sim_dir = tmp_path / "sim_no_traj"
    sim_dir.mkdir()
    _write_outcome(sim_dir, "correct")
    # No trajectory.json on purpose.
    # Manually inject a state pointing at this dir so the manager picks
    # it up — we have to reuse the workspace's underlying state list,
    # which is closed-over by the fake manager. Easiest: use the
    # builder for a sentinel and then delete its trajectory.
    calibration_workspace.add_sim(
        "sim_traj_then_remove",
        bullish=4, total=5, label="correct",
    )
    (tmp_path / "sim_traj_then_remove" / "trajectory.json").unlink()

    samples = _gather_samples(template=None, date_from=None, date_to=None)
    assert samples == []


# ─── Endpoint: HTTP-level integration with the Flask test client ─────────────


@pytest.fixture
def client_no_data(monkeypatch, tmp_path):
    """Spin up the Flask app with a fresh empty data directory so
    ``GET /api/calibration/brier-score`` has no sims to aggregate.

    We monkey-patch ``Neo4jStorage`` to a no-op stub because the app
    factory tries to connect on startup, and the unit test should not
    require a running Neo4j.
    """
    from app.config import Config as _Config
    monkeypatch.setattr(_Config, "WONDERWALL_SIMULATION_DATA_DIR", str(tmp_path))

    # Stub Neo4jStorage so app factory doesn't try to dial a real DB.
    import app.storage as storage_mod

    class _NullStorage:
        def __init__(self, *a, **kw):
            pass

    monkeypatch.setattr(storage_mod, "Neo4jStorage", _NullStorage)

    from app import create_app
    app = create_app()
    app.testing = True
    return app.test_client()


def test_endpoint_returns_200_with_null_brier_when_empty(client_no_data):
    """Empty dataset must still return 200 — "no data" is not an error
    on a calibration dashboard. ``brier`` and ``accuracy`` are
    ``null``; the calibration plot still has its 10 buckets."""
    resp = client_no_data.get("/api/calibration/brier-score")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["brier"] is None
    assert body["accuracy"] is None
    assert body["n"] == 0
    assert body["n_called_it"] == 0
    assert body["n_partial"] == 0
    assert body["n_wrong"] == 0
    assert isinstance(body["calibration_plot"], list)
    assert len(body["calibration_plot"]) == 10


def test_endpoint_accessible_without_auth(client_no_data):
    """The endpoint is the commercial argument — it must respond
    without an admin token. We assert by sending no ``Authorization``
    header at all and getting a clean 200."""
    resp = client_no_data.get("/api/calibration/brier-score")
    assert resp.status_code == 200
    # Any 401/403 here would mean an admin gate was wired in by
    # mistake — guard against that regression explicitly.
    assert resp.status_code not in (401, 403)


def test_endpoint_passes_query_filters_through(client_no_data):
    """Even with all three filters set, an empty dataset still returns
    200. This locks in that ``template``/``from``/``to`` parameters
    don't break the route plumbing."""
    resp = client_no_data.get(
        "/api/calibration/brier-score"
        "?template=corporate_crisis&from=2026-01-01&to=2026-12-31"
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["n"] == 0
