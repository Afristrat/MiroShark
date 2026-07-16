"""Tests unitaires US-222 — arena_registry (registre dynamique des arènes).

Vérifie :
  - list_arena_names() liste les 3 arènes enregistrées (source unique)
  - is_valid_platform() accepte les arènes + la sentinelle 'parallel', rejette le reste
  - is_platform_enabled() : validation croisée contre les flags enable_* de SimulationState
"""

from __future__ import annotations

from types import SimpleNamespace

from app.services import arena_registry


class TestListArenaNames:
    def test_lists_the_three_registered_arenas(self):
        names = arena_registry.list_arena_names()
        assert set(names) == {"twitter", "reddit", "polymarket"}

    def test_never_includes_the_parallel_sentinel(self):
        assert "parallel" not in arena_registry.list_arena_names()


class TestIsValidPlatform:
    def test_registered_arenas_are_valid(self):
        for name in arena_registry.list_arena_names():
            assert arena_registry.is_valid_platform(name)

    def test_parallel_sentinel_is_valid(self):
        assert arena_registry.is_valid_platform("parallel")

    def test_unknown_platform_is_invalid(self):
        assert not arena_registry.is_valid_platform("mastodon")

    def test_empty_string_is_invalid(self):
        assert not arena_registry.is_valid_platform("")


class TestIsPlatformEnabled:
    def _state(self, **flags):
        defaults = {"enable_twitter": False, "enable_reddit": False, "enable_polymarket": False}
        defaults.update(flags)
        return SimpleNamespace(**defaults)

    def test_enabled_platform_returns_true(self):
        state = self._state(enable_twitter=True)
        assert arena_registry.is_platform_enabled("twitter", state) is True

    def test_disabled_platform_returns_false(self):
        state = self._state(enable_twitter=False)
        assert arena_registry.is_platform_enabled("twitter", state) is False

    def test_polymarket_flag_checked_independently(self):
        state = self._state(enable_twitter=True, enable_polymarket=False)
        assert arena_registry.is_platform_enabled("polymarket", state) is False

    def test_parallel_sentinel_always_enabled(self):
        state = self._state()  # tout désactivé
        assert arena_registry.is_platform_enabled("parallel", state) is True

    def test_unknown_platform_returns_false(self):
        state = self._state(enable_twitter=True)
        assert arena_registry.is_platform_enabled("mastodon", state) is False

    def test_missing_attribute_on_state_defaults_to_false(self):
        # SimulationState réel porte toujours les 3 flags — robustesse si un
        # état legacy/partiel arrive sans l'attribut.
        state = SimpleNamespace()
        assert arena_registry.is_platform_enabled("twitter", state) is False
