"""Smoke tests — vérifier que l'app démarre sans dépendance externe.

Garantit la stabilité du quality gate `pytest tests/` pour le Ralph loop :
même sans Neo4j / LLM / Ollama joignable, le backend doit pouvoir
construire une instance Flask via ``create_app``.
"""

from __future__ import annotations


def test_create_app_does_not_crash():
    """L'app Flask se construit sans accès aux services externes."""
    from app import create_app

    app = create_app()
    assert app is not None
    assert app.name == "app"


def test_app_has_expected_blueprints():
    """Les blueprints API critiques sont enregistrés."""
    from app import create_app

    app = create_app()
    blueprint_names = {bp.name for bp in app.blueprints.values()}

    # Au moins ces blueprints essentiels au produit doivent être présents.
    expected = {"simulation", "graph", "report", "settings"}
    missing = expected - blueprint_names
    assert not missing, f"blueprints manquants: {missing} (présents: {blueprint_names})"


def test_config_validate_returns_iterable():
    """``Config.validate`` doit renvoyer une liste itérable d'erreurs (peut être vide)."""
    from app.config import Config

    errors = Config.validate()
    assert hasattr(errors, "__iter__"), "Config.validate() doit retourner un itérable"
