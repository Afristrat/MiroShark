"""Tests unitaires US-223 — PromptRegistry (ADR-017).

Vérifie :
  - résolution key+locale → contenu de la version active
  - fallback silencieux (None, jamais d'exception) : table vide, ligne
    absente, Supabase non configuré, erreur réseau
  - cache in-process : un second appel identique ne retape pas Supabase
  - invalidate() force une relecture
  - flux de bout en bout du builder Polymarket (registre → fallback codé)
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.auth.supabase_client import SupabaseConfigError
from app.services import prompt_registry


@pytest.fixture(autouse=True)
def _clear_cache():
    """Le cache est un module-level dict process-wide — isoler chaque test."""
    prompt_registry.invalidate()
    yield
    prompt_registry.invalidate()


def _fake_client(rows):
    """Client Supabase factice : chaîne fluide renvoyant `rows` à execute()."""
    client = MagicMock()
    client.table.return_value = client
    client.select.return_value = client
    client.eq.return_value = client
    client.limit.return_value = client
    client.execute.return_value = SimpleNamespace(data=rows)
    return client


# ─── Résolution ──────────────────────────────────────────────────────────

class TestGetResolution:
    def test_returns_content_of_active_version(self):
        client = _fake_client([{"content": "Tu es un persona de test."}])
        result = prompt_registry.get("arena.polymarket.system", "fr", client=client)
        assert result == "Tu es un persona de test."
        client.table.assert_called_with("simulation_prompts")

    def test_queries_correct_key_and_locale(self):
        client = _fake_client([{"content": "..."}])
        prompt_registry.get("oracle.resolution", "en", client=client)
        client.eq.assert_any_call("key", "oracle.resolution")
        client.eq.assert_any_call("locale", "en")
        client.eq.assert_any_call("is_active", True)


# ─── Fallback silencieux ─────────────────────────────────────────────────

class TestGetFallback:
    def test_empty_table_returns_none(self):
        client = _fake_client([])
        assert prompt_registry.get("arena.polymarket.system", "fr", client=client) is None

    def test_missing_content_field_returns_none(self):
        client = _fake_client([{"content": None}])
        assert prompt_registry.get("arena.polymarket.system", "fr", client=client) is None

    def test_supabase_not_configured_returns_none_without_raising(self, monkeypatch):
        def _raise(*a, **k):
            raise SupabaseConfigError("SUPABASE_URL not set")

        monkeypatch.setattr(prompt_registry, "get_supabase_admin", _raise)
        result = prompt_registry.get("arena.polymarket.system", "fr")
        assert result is None

    def test_network_error_returns_none_without_raising(self):
        client = MagicMock()
        client.table.side_effect = RuntimeError("connection refused")
        result = prompt_registry.get("arena.polymarket.system", "fr", client=client)
        assert result is None


# ─── Cache ───────────────────────────────────────────────────────────────

class TestCache:
    def test_second_call_does_not_hit_supabase_again(self):
        client = _fake_client([{"content": "v1"}])
        first = prompt_registry.get("arena.polymarket.system", "fr", client=client)
        client.table.reset_mock()
        second = prompt_registry.get("arena.polymarket.system", "fr", client=client)
        assert first == second == "v1"
        client.table.assert_not_called()

    def test_invalidate_specific_key_forces_reread(self):
        client = _fake_client([{"content": "v1"}])
        prompt_registry.get("arena.polymarket.system", "fr", client=client)

        prompt_registry.invalidate("arena.polymarket.system", "fr")

        client2 = _fake_client([{"content": "v2"}])
        result = prompt_registry.get("arena.polymarket.system", "fr", client=client2)
        assert result == "v2"

    def test_invalidate_all_clears_every_entry(self):
        client_a = _fake_client([{"content": "a"}])
        client_b = _fake_client([{"content": "b"}])
        prompt_registry.get("key.a", "fr", client=client_a)
        prompt_registry.get("key.b", "fr", client=client_b)

        prompt_registry.invalidate()

        new_a = _fake_client([{"content": "a2"}])
        new_b = _fake_client([{"content": "b2"}])
        assert prompt_registry.get("key.a", "fr", client=new_a) == "a2"
        assert prompt_registry.get("key.b", "fr", client=new_b) == "b2"


# ─── Flux de bout en bout — builder Polymarket (US-223 AC3) ────────────────

class TestPolymarketBuilderIntegration:
    def test_uses_registry_content_when_active_version_present(self, monkeypatch):
        from wonderwall.simulations.polymarket.prompts import PolymarketPromptBuilder

        client = _fake_client([{"content": "Registre actif : {name_str}|{profile_str}|{risk_str}"}])
        monkeypatch.setattr(
            "app.services.prompt_registry.get_supabase_admin", lambda: client,
        )

        user_info = SimpleNamespace(name="Karim", profile=None)
        out = PolymarketPromptBuilder().build_system_prompt(user_info)
        assert out == "Registre actif : Your name is Karim.|Background: Karim|non précisée"

    def test_falls_back_to_hardcoded_prompt_when_registry_empty(self, monkeypatch):
        from wonderwall.simulations.polymarket.prompts import PolymarketPromptBuilder

        client = _fake_client([])
        monkeypatch.setattr(
            "app.services.prompt_registry.get_supabase_admin", lambda: client,
        )

        user_info = SimpleNamespace(name="Karim", profile=None)
        out = PolymarketPromptBuilder().build_system_prompt(user_info)
        assert "# RÔLE" in out
        assert "Karim" in out
