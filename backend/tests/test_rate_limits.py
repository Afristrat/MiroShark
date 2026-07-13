"""Tests de sécurité — US-116 — Rate limits (A04 OWASP).

Vérifie que les endpoints sensibles disposent d'un rate limit par IP
et que les endpoints protégés retournent 429 après saturation.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture(scope="module")
def client():
    import app as flask_app_module
    importlib.reload(flask_app_module)
    flask_app = flask_app_module.create_app()
    return flask_app.test_client()


# ─── /api/simulation/enrich-ask ─────────────────────────────────────────────


def test_enrich_ask_rate_limit_exists(client, monkeypatch):
    """A04 — /enrich-ask retourne 429 après 10 appels depuis la même IP."""
    # On réinitialise l'état du rate limiter en patchant le dict interne.
    import app.api.simulation as sim_module
    original_hits = sim_module._ENRICH_RATE_HITS.copy()
    sim_module._ENRICH_RATE_HITS.clear()

    try:
        # 10 appels → OK ou erreur LLM (pas 429)
        for i in range(10):
            r = client.post(
                "/api/simulation/enrich-ask",
                json={"question": f"test question {i}"},
                headers={"X-Forwarded-For": "1.2.3.4"},
            )
            assert r.status_code != 429, f"429 prématuré à l'appel {i+1}"

        # 11ème appel → doit être 429
        r = client.post(
            "/api/simulation/enrich-ask",
            json={"question": "one too many"},
            headers={"X-Forwarded-For": "1.2.3.4"},
        )
        assert r.status_code == 429, (
            f"Attendu 429 (rate limit), obtenu {r.status_code}"
        )
        data = r.get_json() or {}
        assert data.get("success") is False
        assert "RATE_LIMITED" in str(data.get("error", ""))
    finally:
        # Restaurer l'état original pour ne pas polluer les autres tests
        sim_module._ENRICH_RATE_HITS.clear()
        sim_module._ENRICH_RATE_HITS.update(original_hits)


def test_enrich_ask_rate_limit_per_ip(client, monkeypatch):
    """A04 — Le rate limit est par IP : deux IPs différentes ont des quotas indépendants."""
    import app.api.simulation as sim_module
    original_hits = sim_module._ENRICH_RATE_HITS.copy()
    sim_module._ENRICH_RATE_HITS.clear()

    try:
        # Saturer IP1
        for _ in range(11):
            client.post(
                "/api/simulation/enrich-ask",
                json={"question": "ip1 question"},
                headers={"X-Forwarded-For": "10.0.0.1"},
            )

        # IP2 ne doit pas être affectée
        r = client.post(
            "/api/simulation/enrich-ask",
            json={"question": "ip2 question"},
            headers={"X-Forwarded-For": "10.0.0.2"},
        )
        assert r.status_code != 429, (
            f"IP2 ne devrait pas être rate-limitée (IP1 l'est), obtenu {r.status_code}"
        )
    finally:
        sim_module._ENRICH_RATE_HITS.clear()
        sim_module._ENRICH_RATE_HITS.update(original_hits)


# ─── /api/simulation/suggest-scenarios ──────────────────────────────────────


def test_suggest_scenarios_rate_limit_exists(client):
    """A04 — /suggest-scenarios retourne 429 après 10 appels depuis la même IP."""
    import app.api.simulation as sim_module
    original_hits = sim_module._SCENARIO_RATE_HITS.copy()
    sim_module._SCENARIO_RATE_HITS.clear()

    try:
        for i in range(10):
            r = client.post(
                "/api/simulation/suggest-scenarios",
                json={"content_preview": f"document preview {i}", "framework": "cerberus"},
                headers={"X-Forwarded-For": "2.3.4.5"},
            )
            assert r.status_code != 429, f"429 prématuré à l'appel {i+1}"

        r = client.post(
            "/api/simulation/suggest-scenarios",
            json={"content_preview": "one more", "framework": "cerberus"},
            headers={"X-Forwarded-For": "2.3.4.5"},
        )
        assert r.status_code == 429, (
            f"Attendu 429 (rate limit suggest-scenarios), obtenu {r.status_code}"
        )
    finally:
        sim_module._SCENARIO_RATE_HITS.clear()
        sim_module._SCENARIO_RATE_HITS.update(original_hits)


# ─── /api/quote ─────────────────────────────────────────────────────────────


def test_quote_rate_limit_function_exists():
    """A04 — Le module quote_service expose bien check_rate_limit()."""
    from app.services.quote_service import check_rate_limit  # noqa: F401
    assert callable(check_rate_limit)


def test_quote_rate_limit_enforced(client):
    """A04 — check_rate_limit retourne False après épuisement du quota."""
    import time
    from app.services import quote_service

    test_ip = "9.9.9.99"

    # Sauvegarder et vider l'état
    with quote_service._rate_limit_lock:
        original = dict(quote_service._rate_limit)
        quote_service._rate_limit.clear()

    try:
        # Pré-remplir le bucket au-delà du seuil (max 5/heure)
        with quote_service._rate_limit_lock:
            quote_service._rate_limit[test_ip] = [time.time()] * 10

        result = quote_service.check_rate_limit(test_ip)
        assert result is False, (
            "check_rate_limit doit retourner False quand le quota est épuisé"
        )

        # Une IP fraîche doit toujours passer
        result_other = quote_service.check_rate_limit("8.8.8.8")
        assert result_other is True, (
            "check_rate_limit doit retourner True pour une IP sans historique"
        )
    finally:
        with quote_service._rate_limit_lock:
            quote_service._rate_limit.clear()
            quote_service._rate_limit.update(original)


# ─── /api/intake/session/<id>/agent/turn ────────────────────────────────────


def test_agent_turn_rate_limit_independent_from_quote_bucket():
    """A04 — check_agent_turn_rate_limit a son propre bucket (40/h), distinct
    de check_rate_limit (5/h) — régression du bug 2026-07-13 (chat épuisé
    après ~3 questions car il partageait le bucket de soumission)."""
    import time
    from app.services import quote_service

    test_ip = "9.9.9.98"

    with quote_service._rate_limit_lock:
        original_quote = dict(quote_service._rate_limit)
        quote_service._rate_limit.clear()
    with quote_service._agent_turn_rate_limit_lock:
        original_turn = dict(quote_service._agent_turn_rate_limit)
        quote_service._agent_turn_rate_limit.clear()

    try:
        # Épuiser le bucket de soumission (5/h) ne doit PAS affecter le chat.
        with quote_service._rate_limit_lock:
            quote_service._rate_limit[test_ip] = [time.time()] * 10
        assert quote_service.check_agent_turn_rate_limit(test_ip) is True, (
            "le chat ne doit pas être bloqué par le quota de soumission épuisé"
        )

        # Le chat tolère bien plus de 5 tours (le cas réel : 8-10 questions).
        with quote_service._agent_turn_rate_limit_lock:
            quote_service._agent_turn_rate_limit[test_ip] = [time.time()] * 8
        assert quote_service.check_agent_turn_rate_limit(test_ip) is True, (
            "8 tours de chat ne doivent pas épuiser le quota de 40/h"
        )

        # Le bucket du chat s'épuise bien à son propre seuil.
        with quote_service._agent_turn_rate_limit_lock:
            quote_service._agent_turn_rate_limit[test_ip] = [time.time()] * 40
        assert quote_service.check_agent_turn_rate_limit(test_ip) is False, (
            "check_agent_turn_rate_limit doit retourner False au-delà de 40/h"
        )
    finally:
        with quote_service._rate_limit_lock:
            quote_service._rate_limit.clear()
            quote_service._rate_limit.update(original_quote)
        with quote_service._agent_turn_rate_limit_lock:
            quote_service._agent_turn_rate_limit.clear()
            quote_service._agent_turn_rate_limit.update(original_turn)
