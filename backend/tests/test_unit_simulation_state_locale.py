"""Unit tests for SimulationState.locale persistence (US-038).

US-038 added an optional `locale` field to SimulationState so the
Wonderwall background subprocess (which runs outside Flask request
context) can still build per-agent system_prompts in the user's
language. These tests cover:

- Default value when omitted at construction time.
- Round-trip through to_dict / re-instantiation preserves the locale.
- Backward compat: a state.json on disk written before US-038 (no
  `locale` key) loads cleanly with the `'fr'` default.
"""

import json
import os
import tempfile

from app.services.simulation_manager import (
    SimulationManager,
    SimulationState,
    SimulationStatus,
)


# ── Default value ─────────────────────────────────────────────────────────


def test_simulation_state_default_locale_is_fr():
    """A newly-constructed SimulationState defaults to locale='fr'."""
    state = SimulationState(
        simulation_id="sim_default_locale_test",
        project_id="proj_x",
        graph_id="graph_x",
    )
    assert state.locale == "fr"
    # And it serializes through the dict layer.
    assert state.to_dict()["locale"] == "fr"


# ── Round-trip preservation ───────────────────────────────────────────────


def test_simulation_state_locale_roundtrip_through_disk():
    """Locale='ar' must round-trip cleanly through SimulationManager save/load."""
    with tempfile.TemporaryDirectory() as tmp:
        manager = SimulationManager()
        manager.SIMULATION_DATA_DIR = tmp  # type: ignore[assignment]

        state = SimulationState(
            simulation_id="sim_roundtrip_ar",
            project_id="proj_x",
            graph_id="graph_x",
            locale="ar",
        )
        manager._save_simulation_state(state)

        # Drop the in-memory cache to force a real disk read.
        manager._simulations.clear()

        loaded = manager._load_simulation_state("sim_roundtrip_ar")
        assert loaded is not None
        assert loaded.locale == "ar"


# ── Backward compat ───────────────────────────────────────────────────────


def test_simulation_state_loads_legacy_state_without_locale_field():
    """A state.json file written before US-038 (no `locale` key) must load
    with the safe `'fr'` default, NOT raise KeyError or crash.
    """
    with tempfile.TemporaryDirectory() as tmp:
        manager = SimulationManager()
        manager.SIMULATION_DATA_DIR = tmp  # type: ignore[assignment]

        sim_id = "sim_legacy_no_locale"
        sim_dir = os.path.join(tmp, sim_id)
        os.makedirs(sim_dir, exist_ok=True)

        # Legacy state.json shape — exactly as it would have looked before
        # US-038, with NO `locale` key whatsoever.
        legacy_payload = {
            "simulation_id": sim_id,
            "project_id": "proj_legacy",
            "graph_id": "graph_legacy",
            "enable_twitter": True,
            "enable_reddit": True,
            "enable_polymarket": False,
            "polymarket_market_count": 1,
            "status": SimulationStatus.READY.value,
            "entities_count": 5,
            "profiles_count": 5,
            "entity_types": ["Person"],
            "config_generated": True,
            "config_reasoning": "",
            "current_round": 0,
            "twitter_status": "not_started",
            "reddit_status": "not_started",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "error": None,
            "parent_simulation_id": None,
            "config_diff": None,
            "is_public": False,
            # NOTE: no `locale` key — this is the whole point of the test.
        }
        state_path = os.path.join(sim_dir, "state.json")
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(legacy_payload, fh)

        loaded = manager._load_simulation_state(sim_id)
        assert loaded is not None
        # Default fallback kicked in.
        assert loaded.locale == "fr"
