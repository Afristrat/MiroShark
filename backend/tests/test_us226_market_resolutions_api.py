"""US-226 durable market-resolution read API contract."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from flask import Flask, jsonify

from app.api import report_bp
from app.api import market_resolutions as api
from app.services import market_resolution_service as service


class _Query:
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.filters: list[tuple[str, object]] = []
        self.order_by = None

    def select(self, _fields: str):
        self.fields = _fields
        return self

    def eq(self, key: str, value: object):
        self.filters.append((key, value))
        return self

    def order(self, field: str):
        self.order_by = field
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows)


class _Client:
    def __init__(self, rows: list[dict]):
        self.query = _Query(rows)
        self.table_name = None

    def table(self, name: str):
        self.table_name = name
        return self.query


@pytest.fixture
def app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(report_bp, url_prefix="/api/report")
    return app


def _row(*, summary: dict, verdict: str = "YES") -> dict:
    return {
        "simulation_id": "sim-1",
        "market_id": 1,
        "question": "Will it pass?",
        "resolution_spec": {"version": 1},
        "verdict": verdict,
        "justification": "Durable evidence.",
        "confidence": None if verdict == "UNRESOLVED" else 0.9,
        "evidence": [] if verdict == "UNRESOLVED" else [{"ref": "round:1:0"}],
        "price_series": [{"round": 1, "price_yes": 0.6, "reserve_a": 10.0, "reserve_b": 5.0}],
        "payout_summary": summary,
        "prompt_key": "oracle.resolution",
        "prompt_version": 1,
        "resolved_at": "2026-07-18T00:00:00+00:00",
        "org_id": "org-1",
    }


def _allow(monkeypatch: pytest.MonkeyPatch, calls: list[bool]) -> None:
    monkeypatch.setattr(api, "_authorize_simulation_access", lambda _sim, *, allow_published: calls.append(allow_published))


def _wire_reader(monkeypatch: pytest.MonkeyPatch, client: _Client, owner: object = None) -> None:
    monkeypatch.setattr(service, "get_simulation_owner", lambda _sim: {"org_id": "org-1"} if owner is None else owner)
    monkeypatch.setattr(service, "get_supabase_admin", lambda: client)


def test_us226_route_is_registered_and_auth_refusal_is_propagated(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        api,
        "_authorize_simulation_access",
        lambda _sim, *, allow_published: (jsonify({"success": False, "error_code": "AUTH_REQUIRED"}), 401),
    )

    response = app.test_client().get("/api/report/sim-1/market-resolutions")

    assert response.status_code == 401
    assert response.get_json()["error_code"] == "AUTH_REQUIRED"
    assert any(rule.rule == "/api/report/<simulation_id>/market-resolutions" for rule in app.url_map.iter_rules())


def test_us226_owner_missing_fails_closed_after_public_access_check(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []
    _allow(monkeypatch, calls)
    monkeypatch.setattr(service, "get_simulation_owner", lambda _sim: None)

    response = app.test_client().get("/api/report/sim-1/market-resolutions")

    assert response.status_code == 404
    assert calls == [True]


def test_us226_owner_read_error_fails_closed(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    _allow(monkeypatch, [])
    monkeypatch.setattr(service, "get_simulation_owner", lambda _sim: (_ for _ in ()).throw(RuntimeError("offline")))

    response = app.test_client().get("/api/report/sim-1/market-resolutions")

    assert response.status_code == 503
    assert response.get_json()["error_code"] == "OWNERSHIP_UNAVAILABLE"


def test_us226_resolution_query_is_scoped_to_canonical_owner_and_exposes_consistent_wealth(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []
    _allow(monkeypatch, calls)
    wealth = [{"user_id": 7, "cash_balance": 12.34567, "open_position_value": 0.0, "wealth": 12.34567, "complete": True}]
    client = _Client([_row(summary={"status": "paid", "final_wealth": wealth, "complete": True})])
    _wire_reader(monkeypatch, client)

    response = app.test_client().get("/api/report/sim-1/market-resolutions")

    assert response.status_code == 200
    assert calls == [True]
    assert client.table_name == "market_resolutions"
    assert client.query.filters == [("simulation_id", "sim-1"), ("org_id", "org-1")]
    assert client.query.order_by == "market_id"
    data = response.get_json()["data"]
    assert data["final_wealth"] == wealth
    assert data["complete"] is True
    assert "org_id" not in data["resolutions"][0]


@pytest.mark.parametrize(
    "summaries",
    [
        [{"status": "pending"}],
        [{"status": "unexpected", "final_wealth": [], "complete": False}],
        [{"status": "paid", "final_wealth": [{"user_id": 7, "cash_balance": float("nan"), "open_position_value": 0, "wealth": 0, "complete": True}], "complete": True}],
        [{"status": "paid", "final_wealth": [{"user_id": "7", "cash_balance": 1, "open_position_value": 0, "wealth": 1, "complete": True}], "complete": True}],
        [
            {"status": "paid", "final_wealth": [{"wealth": 1}], "complete": True},
            {"status": "paid", "final_wealth": [{"wealth": 2}], "complete": True},
        ],
    ],
)
def test_us226_pending_or_divergent_summaries_never_expose_arbitrary_wealth(app: Flask, monkeypatch: pytest.MonkeyPatch, summaries: list[dict]) -> None:
    _allow(monkeypatch, [])
    rows = [_row(summary=summary) | {"market_id": index + 1} for index, summary in enumerate(summaries)]
    _wire_reader(monkeypatch, _Client(rows))

    response = app.test_client().get("/api/report/sim-1/market-resolutions")

    assert response.status_code == 200
    assert response.get_json()["data"].get("final_wealth") == []
    assert response.get_json()["data"].get("complete") is False


def test_us226_supabase_failure_fails_closed(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    _allow(monkeypatch, [])
    monkeypatch.setattr(service, "get_simulation_owner", lambda _sim: {"org_id": "org-1"})
    monkeypatch.setattr(service, "get_supabase_admin", lambda: (_ for _ in ()).throw(RuntimeError("offline")))

    response = app.test_client().get("/api/report/sim-1/market-resolutions")

    assert response.status_code == 503
    assert response.get_json()["error_code"] == "RESOLUTIONS_UNAVAILABLE"


def test_us226_api_accepts_only_paid_refunded_mapping_and_marks_complete(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    _allow(monkeypatch, [])
    wealth = [{"user_id": 7, "cash_balance": 20.0, "open_position_value": 0.0, "wealth": 20.0, "complete": True}]
    rows = [
        _row(verdict="YES", summary={"status": "paid", "final_wealth": wealth, "complete": True}),
        _row(verdict="NO", summary={"status": "paid", "final_wealth": wealth, "complete": True}) | {"market_id": 2},
        _row(verdict="INVALID", summary={"status": "refunded", "final_wealth": wealth, "complete": True}) | {"market_id": 3},
    ]
    _wire_reader(monkeypatch, _Client(rows))

    data = app.test_client().get("/api/report/sim-1/market-resolutions").get_json()["data"]

    assert data["complete"] is True
    assert data["final_wealth"] == wealth


def test_us226_api_unresolved_mapping_is_valid_but_never_complete(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    _allow(monkeypatch, [])
    wealth = [{"user_id": 7, "cash_balance": 20.0, "open_position_value": 1.0, "wealth": 21.0, "complete": False}]
    rows = [
        _row(verdict="YES", summary={"status": "paid", "final_wealth": wealth, "complete": False}),
        _row(verdict="UNRESOLVED", summary={"status": "unresolved", "final_wealth": wealth, "complete": False}) | {"market_id": 2},
    ]
    _wire_reader(monkeypatch, _Client(rows))

    data = app.test_client().get("/api/report/sim-1/market-resolutions").get_json()["data"]

    assert data["complete"] is False
    assert data["final_wealth"] == wealth


@pytest.mark.parametrize("verdict", [None, True, "MAYBE"])
def test_us226_api_malformed_verdict_fails_closed(
    app: Flask, monkeypatch: pytest.MonkeyPatch, verdict: object
) -> None:
    _allow(monkeypatch, [])
    wealth = [{"user_id": 7, "cash_balance": 20.0, "open_position_value": 0.0, "wealth": 20.0, "complete": True}]
    row = _row(verdict="YES", summary={"status": "paid", "final_wealth": wealth, "complete": True})
    row["verdict"] = verdict
    _wire_reader(monkeypatch, _Client([row]))

    response = app.test_client().get("/api/report/sim-1/market-resolutions")

    assert response.status_code == 503
    assert response.get_json()["error_code"] == "RESOLUTIONS_UNAVAILABLE"


def test_us227_zero_durable_rows_are_absent_not_an_error(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    _allow(monkeypatch, [])
    _wire_reader(monkeypatch, _Client([]))

    response = app.test_client().get("/api/report/sim-1/market-resolutions")

    assert response.status_code == 200
    assert response.get_json()["data"] == {
        "simulation_id": "sim-1",
        "resolutions": [],
        "final_wealth": [],
        "complete": False,
    }


def test_us227_cross_tenant_row_fails_closed(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    _allow(monkeypatch, [])
    row = _row(summary={"status": "paid", "final_wealth": [], "complete": True})
    row["org_id"] = "org-other"
    _wire_reader(monkeypatch, _Client([row]))

    response = app.test_client().get("/api/report/sim-1/market-resolutions")

    assert response.status_code == 503
    assert response.get_json()["error_code"] == "RESOLUTIONS_UNAVAILABLE"
