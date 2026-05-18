"""Unit tests for US-065 — GET /api/admin/analytics.

Pure offline tests — Flask test client + mocked Supabase client.
No filesystem, no Neo4j boot, no network.

Three behaviours pinned here:

  1. ``test_no_token_returns_401`` — without an ``Authorization``
     header (but with the env var set so the deploy is "configured"),
     the endpoint returns 401 with the generic envelope. The 401-vs-503
     distinction matters because 503 means "operator forgot to set the
     secret"; we don't want to confuse that with "client didn't send a
     header".
  2. ``test_with_token_returns_200_kpis`` — happy path. With the correct
     bearer token and a mocked Supabase responding with one running sim,
     one completed sim and one quote, the endpoint returns 200 and the
     KPI counters reflect what the mock returns.
  3. ``test_kpis_keys_present`` — schema-shape pin. Every key the
     SPA renders (``kpis``, ``funnel``, ``time_series``,
     ``top_packages``) must be present, with the documented sub-shape.
     A drift here would crash the dashboard, not just hide a column.
  4. ``test_supabase_unconfigured_returns_zeros`` — fail-soft contract.
     When Supabase is unconfigured the dashboard renders zero rather
     than crashing — exactly what a fresh deploy should look like.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest


_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ─── Mock Supabase plumbing ──────────────────────────────────────────────────


class _MockQuery:
    """Mimics the fluent chain used by ``app.api.admin``.

    Supports ``select(...) [.limit(n)] .execute()`` for both
    ``simulation_ownership`` (full scan) and ``quote_ownership``
    (count='exact').
    """

    def __init__(self, rows, count=None):
        self._rows = rows
        self._count = count

    def select(self, *_args, **kwargs):
        if kwargs.get("count") == "exact":
            return _MockQuery(self._rows, count=len(self._rows))
        return self

    def limit(self, _n):
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows, count=self._count)


class _MockClient:
    def __init__(self, sim_rows, quote_rows):
        self._sim_rows = sim_rows
        self._quote_rows = quote_rows

    def table(self, name):
        if name == "simulation_ownership":
            return _MockQuery(self._sim_rows)
        if name == "quote_ownership":
            return _MockQuery(self._quote_rows)
        raise AssertionError(f"unexpected table: {name}")


@pytest.fixture
def populated_supabase(monkeypatch):
    """Install a Supabase mock with one running sim + one completed + one quote."""
    from app.api import admin as admin_module

    now_iso = datetime.now(timezone.utc).isoformat()
    sim_rows = [
        {
            "simulation_id": "sim_running",
            "created_at": now_iso,
            "package_id": "crisis_24h_brand",
            "is_published": False,
            "outcome": None,
            "brier_score": None,
        },
        {
            "simulation_id": "sim_done",
            "created_at": now_iso,
            "package_id": "crisis_24h_brand",
            "is_published": True,
            "outcome": {"label": "called_it"},
            "brier_score": 0.12,
        },
    ]
    quote_rows = [{"quote_id": "q_abcd1234"}]

    mock = _MockClient(sim_rows, quote_rows)
    monkeypatch.setattr(admin_module, "get_supabase_admin", lambda: mock)
    return mock


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


def test_no_token_returns_401(populated_supabase, monkeypatch):
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


def test_with_token_returns_200_kpis(populated_supabase, monkeypatch):
    """Happy path — correct token, mocked Supabase with one running sim,
    one completed sim and one quote. Verify every counter matches what
    the mock returned.
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
    # created_at = "now" → both sims fall in the 30-day window.
    assert kpis["last_30d"] == 2
    assert kpis["quotes"] == 1

    # Top packages aggregated from package_id.
    top = body["data"]["top_packages"]
    assert top, "top_packages should not be empty when sims carry package_id"
    assert top[0]["package"] == "crisis_24h_brand"
    assert top[0]["n"] == 2


def test_kpis_keys_present(populated_supabase, monkeypatch):
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


def test_supabase_unconfigured_returns_zeros(monkeypatch):
    """Fail-soft contract — Supabase outage degrades to zero values.

    When ``get_supabase_admin()`` raises ``SupabaseConfigError`` (fresh
    deploy, missing env vars), the analytics endpoint MUST still return
    a well-formed 200 with zero counters rather than 500. The dashboard
    needs a stable signal even when the data layer is down.
    """
    from app.api import admin as admin_module
    from app.auth.supabase_client import SupabaseConfigError

    def _raise():
        raise SupabaseConfigError("not configured")

    monkeypatch.setattr(admin_module, "get_supabase_admin", _raise)
    monkeypatch.setenv("BASSIRA_ADMIN_TOKEN", "right-token")

    app = _make_app()
    res = app.test_client().get(
        "/api/admin/analytics",
        headers={"Authorization": "Bearer right-token"},
    )
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["kpis"] == {
        "total": 0,
        "completed": 0,
        "last_30d": 0,
        "quotes": 0,
    }
    assert data["top_packages"] == []
    assert len(data["time_series"]) == 30
    assert all(entry["completed"] == 0 for entry in data["time_series"])
