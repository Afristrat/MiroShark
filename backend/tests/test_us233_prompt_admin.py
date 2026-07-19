"""US-233 contracts: immutable prompt versions and SQL-gated activation."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest
from flask import Flask

from app.api.admin_prompts import admin_prompts_bp
from app.auth import decorators
from app.services import prompt_admin_service as service


class _Table:
    def __init__(self, client: "_Client", name: str) -> None:
        self.client, self.name, self.filters, self.action, self.payload = client, name, [], "select", None

    def select(self, _columns: str) -> "_Table":
        return self

    def eq(self, key: str, value: Any) -> "_Table":
        self.filters.append((key, value))
        return self

    def limit(self, _count: int) -> "_Table":
        return self

    def order(self, _field: str, desc: bool = False) -> "_Table":
        return self

    def insert(self, payload: dict[str, Any]) -> "_Table":
        self.action, self.payload = "insert", payload
        return self

    def execute(self) -> SimpleNamespace:
        rows = self.client.rows[self.name]
        if self.action == "insert":
            inserted = deepcopy(self.payload)
            inserted.setdefault("id", f"{self.name}-{len(rows) + 1}")
            rows.append(inserted)
            return SimpleNamespace(data=[deepcopy(inserted)])
        return SimpleNamespace(data=[deepcopy(row) for row in rows if all(row.get(k) == v for k, v in self.filters)])


class _Rpc:
    def __init__(self, client: "_Client", prompt_id: str) -> None:
        self.client, self.prompt_id = client, prompt_id

    def execute(self) -> SimpleNamespace:
        self.client.rpc_calls.append(self.prompt_id)
        target = next(row for row in self.client.rows["simulation_prompts"] if row["id"] == self.prompt_id)
        for row in self.client.rows["simulation_prompts"]:
            if row["key"] == target["key"] and row["locale"] == target["locale"]:
                row["is_active"] = row["id"] == target["id"]
        return SimpleNamespace(data=[deepcopy(target)])


class _Client:
    def __init__(self, prompts: list[dict[str, Any]]) -> None:
        self.rows = {"simulation_prompts": deepcopy(prompts), "simulation_prompt_evaluations": []}
        self.rpc_calls: list[str] = []

    def table(self, name: str) -> _Table:
        return _Table(self, name)

    def rpc(self, name: str, arguments: dict[str, str]) -> _Rpc:
        assert name == "activate_simulation_prompt"
        return _Rpc(self, arguments["p_prompt_id"])


class _NoEvaluationClient(_Client):
    def table(self, name: str) -> _Table:
        table = super().table(name)
        if name == "simulation_prompt_evaluations":
            table.execute = lambda: SimpleNamespace(data=[])  # type: ignore[method-assign]
        return table


def _prompt(prompt_id: str, version: int, content: str, active: bool = False) -> dict[str, Any]:
    return {
        "id": prompt_id, "key": "pilot.contract", "scope": "pilot", "locale": "fr", "version": version,
        "content": content, "variables": ["name"], "is_active": active, "created_by": "seed",
    }


def test_create_version_keeps_old_row_immutable_and_advances_version() -> None:
    client = _Client([_prompt("v1", 1, "Bonjour {name}", True)])
    result = service.create_version(
        key="pilot.contract", scope="pilot", locale="fr", content="Salut {name}",
        variables=["name"], created_by="admin", client=client,
    )
    assert result["version"] == 2
    assert client.rows["simulation_prompts"][0]["content"] == "Bonjour {name}"
    assert client.rows["simulation_prompts"][0]["is_active"] is True
    assert client.rows["simulation_prompts"][1]["is_active"] is False


def test_diff_is_deterministic() -> None:
    client = _Client([_prompt("v1", 1, "Bonjour {name}\n"), _prompt("v2", 2, "Salut {name}\n")])
    result = service.diff_versions("v1", "v2", client=client)
    assert result["diff"] == "--- v1\n+++ v2\n@@ -1 +1 @@\n-Bonjour {name}\n+Salut {name}\n"


def test_activation_refuses_failed_cases_and_persists_evaluation() -> None:
    client = _Client([_prompt("v2", 2, "Prompt with {unknown} placeholder")])
    with pytest.raises(service.GoldenSetFailedError) as caught:
        service.activate_version("v2", created_by="admin", client=client)
    assert any(not case["passed"] for case in caught.value.cases)
    assert client.rows["simulation_prompt_evaluations"][0]["passed"] is False
    assert client.rpc_calls == []


def test_activation_fails_closed_when_evaluation_insert_returns_no_row() -> None:
    client = _NoEvaluationClient([_prompt("v2", 2, "Salut {name}")])
    with pytest.raises(service.EvaluationPersistenceError):
        service.activate_version("v2", created_by="admin", client=client)
    assert client.rpc_calls == []


def test_us232_style_seed_with_documented_but_unused_data_passes() -> None:
    cases = service.prompt_golden_sets.evaluate(
        "You are the time-configuration system. Return one JSON object.",
        ["time_profile", "scenario", "locale"],
    )
    assert service.prompt_golden_sets.passed(cases) is True


def test_activation_and_rollback_persist_evaluations_and_invalidate_targeted_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _Client([_prompt("v1", 1, "Bonjour {name}", True), _prompt("v2", 2, "Salut {name}")])
    invalidated: list[tuple[str, str]] = []
    monkeypatch.setattr(service.prompt_registry, "invalidate", lambda key, locale: invalidated.append((key, locale)))

    service.activate_version("v2", created_by="admin", client=client)
    service.activate_version("v1", created_by="admin", client=client)  # rollback uses the same primitive

    assert client.rpc_calls == ["v2", "v1"]
    assert [row["passed"] for row in client.rows["simulation_prompt_evaluations"]] == [True, True]
    assert next(row for row in client.rows["simulation_prompts"] if row["id"] == "v1")["is_active"] is True
    assert next(row for row in client.rows["simulation_prompts"] if row["id"] == "v2")["is_active"] is False
    assert invalidated == [("pilot.contract", "fr"), ("pilot.contract", "fr")]


@pytest.fixture
def api_client(monkeypatch: pytest.MonkeyPatch):
    app = Flask(__name__)
    app.register_blueprint(admin_prompts_bp, url_prefix="/api/admin/prompts")
    app.config["TESTING"] = True
    monkeypatch.setenv("BASSIRA_SUPER_ADMIN_EMAILS", "super@example.test")
    monkeypatch.setattr(
        decorators, "verify_supabase_jwt",
        lambda token: {"sub": "admin-id", "email": "super@example.test" if token == "super" else "user@example.test"},
    )
    return app.test_client()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/"), ("get", "/version"), ("post", "/"),
        ("get", "/diff?from=a&to=b"), ("post", "/version/activate"),
        ("post", "/version/rollback"),
    ],
)
def test_every_route_rejects_missing_auth_and_non_super_admin(api_client, method: str, path: str) -> None:
    assert getattr(api_client, method)(f"/api/admin/prompts{path}").status_code == 401
    response = getattr(api_client, method)(
        f"/api/admin/prompts{path}", headers={"Authorization": "Bearer ordinary"}
    )
    assert response.status_code == 403
    assert response.get_json()["error_code"] == "NOT_SUPER_ADMIN"


def test_activation_endpoint_returns_explicit_failed_cases(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _Client([_prompt("bad", 2, "Unknown {variable}")])
    monkeypatch.setattr(service, "get_supabase_admin", lambda: client)
    response = api_client.post("/api/admin/prompts/bad/activate", headers={"Authorization": "Bearer super"})
    assert response.status_code == 409
    assert response.get_json()["error_code"] == "PROMPT_GOLDEN_SET_FAILED"
    assert response.get_json()["cases"]


def test_rollback_endpoint_restores_old_version_end_to_end(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _Client([_prompt("old", 1, "Bonjour {name}", True), _prompt("new", 2, "Salut {name}")])
    monkeypatch.setattr(service, "get_supabase_admin", lambda: client)
    headers = {"Authorization": "Bearer super"}
    assert api_client.post("/api/admin/prompts/new/activate", headers=headers).status_code == 200
    response = api_client.post("/api/admin/prompts/old/rollback", headers=headers)
    assert response.status_code == 200
    assert client.rpc_calls == ["new", "old"]
    assert next(row for row in client.rows["simulation_prompts"] if row["id"] == "old")["is_active"] is True
