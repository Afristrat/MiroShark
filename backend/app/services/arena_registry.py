"""Registre dynamique des arènes de simulation (US-222).

Source UNIQUE des arènes disponibles : ajouter une arène = l'enregistrer
dans ``ARENA_STATE_FLAGS`` ci-dessous (et déclarer son ``SimulationConfig``
dans ``wonderwall.simulations.*``) — aucun enum à retoucher dans
``app/api/simulation.py``.

Import tardif des ``SimulationConfig`` (torch/camel-ai/sentence-transformers
sont des dépendances lourdes du moteur wonderwall — ne jamais les tirer au
chargement du module Flask, cf. convention déjà en place dans
``scripts/run_parallel_simulation.py``).
"""

from __future__ import annotations

from typing import Any

# Arène -> attribut booléen correspondant sur SimulationState
# (app/services/simulation_manager.py). Un 4e arène (ex. US-237, relais de
# messagerie) s'ajoute en une ligne ici + son propre champ enable_* sur
# SimulationState — zéro modification de app/api/simulation.py.
ARENA_STATE_FLAGS: dict[str, str] = {
    "twitter": "enable_twitter",
    "reddit": "enable_reddit",
    "polymarket": "enable_polymarket",
}

# Valeur spéciale acceptée par /simulation/start : "toutes les arènes
# activées, en lock-step" — n'est PAS une arène en soi, jamais dans
# ARENA_STATE_FLAGS ni dans list_arena_names().
PARALLEL_SENTINEL = "parallel"


def list_arena_names() -> list[str]:
    """Retourne les noms d'arènes enregistrées (hors sentinelle 'parallel')."""
    return list(ARENA_STATE_FLAGS.keys())


def is_valid_platform(platform: str) -> bool:
    """True si ``platform`` est une arène enregistrée OU la sentinelle 'parallel'."""
    return platform == PARALLEL_SENTINEL or platform in ARENA_STATE_FLAGS


def is_platform_enabled(platform: str, state: Any) -> bool:
    """True si ``platform`` est activée sur cette simulation (``state``).

    ``state`` : ``SimulationState`` — porte les flags ``enable_twitter`` etc.
    La sentinelle 'parallel' est toujours considérée activée : elle délègue
    aux flags individuels côté runner (aucune arène n'est démarrée si aucun
    flag n'est actif, ce n'est pas la responsabilité de cette fonction).
    """
    if platform == PARALLEL_SENTINEL:
        return True
    flag_name = ARENA_STATE_FLAGS.get(platform)
    if flag_name is None:
        return False
    return bool(getattr(state, flag_name, False))
