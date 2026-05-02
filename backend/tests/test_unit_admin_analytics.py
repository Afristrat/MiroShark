"""Unit tests for US-065 — GET /api/admin/analytics.

Pure offline tests — Flask test client, monkeypatched ``Config``
paths pointed at a ``tmp_path`` filesystem. No real disk outside the
fixture, no Neo4j boot, no network.

Three behaviours pinned here:

  1. ``test_no_token_returns_401`` — without an ``Authorization``
     header (but with the env var set so the deploy is "configured"),
     the endpoint returns 401 with the generic envelope. The 401-vs-503
     distinction matters because 503 means "operator forgot to set the
     secret"; we don't want to confuse that with "client didn't send a
     header".
  2. ``test_with_token_returns_200_kpis`` — happy path. With the
     correct bearer token and a populated ``tmp_path`` simulating a
     fresh-but-active deploy (one running sim, one completed sim, one
     persisted quote), the endpoint returns 200 and the KPI counters
     reflect what's on disk.
  3. ``test_kpis_keys_present`` — schema-shape pin. Every key the
     SPA renders (``kpis``, ``funnel``, ``time_series``,
     ``top_packages``) must be present, with the documented
     sub-shape. A drift here would crash the dashboard, not just
     hide a column.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest


_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ─── Shared fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def isolated_data_dirs(tmp_path, monkeypatch):
    """Point Config at a throwaway ``tmp_path/uploads`` tree.

    Layout::

        tmp_path/uploads/
            simulations/
                sim_running/                       # no outcome.json
                    simulation_config.json         # template_id="crisis_24h_brand"
                sim_done/
                    outcome.json                   # mtime = now (last 30d)
                    simulation_config.json         # template_id="crisis_24h_brand"
            quotes/
                quote_<ts>_<id>.json
    """
    from app import config as config_module

    base = tmp_path / "uploads"
    sims_dir = base / "simulations"
    quotes_dir = base / "quotes"
    sims_dir.mkdir(parents=True, exist_ok=True)
    quotes_dir.mkdir(parents=True, exist_ok=True)

    # Running simulation: config but no outcome — should count toward
    # ``total`` but not toward ``completed``.
    sim_running = sims_dir / "sim_running"
    sim_running.mkdir()
    (sim_running / "simulation_config.json").write_text(
        json.dumps({"template_id": "crisis_24h_brand"}),
        encoding="utf-8",
    )

    # Completed simulation: counts toward both ``total`` and ``completed``,
    # plus the 30-day window since mtime is "now".
    sim_done = sims_dir / "sim_done"
    sim_done.mkdir()
    (sim_done / "simulation_config.json").write_text(
        json.dumps({"template_id": "crisis_24h_brand"}),
        encoding="utf-8",
    )
    outcome_path = sim_done / "outcome.json"
    outcome_path.write_text(
        json.dumps({"label": "correct"}),
        encoding="utf-8",
    )

    # One persisted quote so ``quotes`` is non-zero.
    (quotes_dir / "quote_20260501T000000_abcd1234.json").write_text(
        json.dumps({"full_name": "test"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        config_module.Config,
        "WONDERWALL_SIMULATION_DATA_DIR",
        str(sims_dir),
        raising=False,
    )
    monkeypatch.setattr(
        config_module.Config,
        "WONDERWALL_DATA_DIR",
        str(base),
        raising=False,
    )
    return base


def _make_app():
    """Boot a minimal Flask app that mounts ``admin_bp``.

    We can't use the real ``create_app`` factory because it boots
    Neo4j and the simulation runner — both unavailable in the unit
    environment. Mounting the blueprint on a stub app exercises the
    same route + decorator code path with zero infra.
    """
    from flask import Flask

    from app.api.admin import admin_bp

    app = Flask(__name__)
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    return app


# ─── Tests ───────────────────────────────────────────────────────────────────


def test_no_token_returns_401(isolated_data_dirs, monkeypatch):
    """Without an Authorization header, the endpoint must return 401.

    The env var is set so we're testing "client didn't send a token",
    not "server isn't configured" (that would be 503).
    """
    monkeypatch.setenv("BASSIRA_ADMIN_TOKEN", "right-token")
    app = _make_app()
    res = app.test_client().get("/api/admin/analytics")
    assert res.status_code == 401
    body = res.get_json()
    assert body["success"] is False
    assert body["error"] == "Unauthorized"


def test_with_token_returns_200_kpis(isolated_data_dirs, monkeypatch):
    """Happy path — correct token, populated tmp filesystem.

    The fixture sets up exactly two simulations (one running, one
    completed) and one quote. Verify every counter matches what we
    seeded.
    """
    monkeypatch.setenv("BASSIRA_ADMIN_TOKEN", "right-token")
    app = _make_app()
    res = app.test_client().get(
        "/api/admin/analytics",
        headers={"Authorization": "Bearer right-token"},
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True

    kpis = body["data"]["kpis"]
    assert kpis["total"] == 2
    assert kpis["completed"] == 1
    # outcome.json was just written → its mtime is "now" → in window.
    assert kpis["last_30d"] == 1
    assert kpis["quotes"] == 1

    # Top packages aggregated from simulation_config.json.
    top = body["data"]["top_packages"]
    assert top, "top_packages should not be empty when sims carry template_id"
    assert top[0]["package"] == "crisis_24h_brand"
    assert top[0]["n"] == 2


def test_kpis_keys_present(isolated_data_dirs, monkeypatch):
    """Schema-shape pin — the SPA renders all four sections.

    A missing ``time_series`` array (or a renamed key) would crash
    the dashboard, so we lock the shape independently of the values.
    """
    monkeypatch.setenv("BASSIRA_ADMIN_TOKEN", "right-token")
    app = _make_app()
    res = app.test_client().get(
        "/api/admin/analytics",
        headers={"Authorization": "Bearer right-token"},
    )
    assert res.status_code == 200
    data = res.get_json()["data"]

    # Top-level sections.
    for key in ("kpis", "funnel", "time_series", "top_packages"):
        assert key in data, f"missing top-level key: {key}"

    # KPI sub-keys — the four cards on the dashboard.
    for key in ("total", "completed", "last_30d", "quotes"):
        assert key in data["kpis"], f"missing kpi key: {key}"
        assert isinstance(data["kpis"][key], int), (
            f"kpis.{key} must be int, got {type(data['kpis'][key]).__name__}"
        )

    # Funnel — list of {step, n} dicts.
    assert isinstance(data["funnel"], list)
    assert data["funnel"], "funnel should always have ≥1 step"
    for entry in data["funnel"]:
        assert "step" in entry and "n" in entry

    # Time series — exactly 30 days, oldest → today, ISO YYYY-MM-DD.
    assert isinstance(data["time_series"], list)
    assert len(data["time_series"]) == 30, (
        f"time_series must be 30 entries, got {len(data['time_series'])}"
    )
    for entry in data["time_series"]:
        assert "date" in entry and "completed" in entry
        # Format YYYY-MM-DD (length 10, two dashes at fixed positions).
        assert len(entry["date"]) == 10
        assert entry["date"][4] == "-" and entry["date"][7] == "-"

    # Top packages — list of {package, n} dicts.
    assert isinstance(data["top_packages"], list)
    for entry in data["top_packages"]:
        assert "package" in entry and "n" in entry
