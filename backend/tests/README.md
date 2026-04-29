# Tests MiroShark backend

## Lancer les tests unitaires (par défaut, hors-ligne)

```bash
cd backend
uv run pytest tests/ --tb=short -x
```

Les tests `test_unit_*.py` ne nécessitent **aucun service externe** (pas de
Neo4j, pas de LLM, pas d'Ollama). Ils valident l'API contractuelle, le
parsing, la sérialisation et la logique pure.

## Lancer les tests d'intégration (nécessitent un backend live)

```bash
# Démarrer un backend MiroShark sur :5001 dans un autre terminal, puis :
export MIROSHARK_API_URL=http://localhost:5001
cd backend
uv run pytest tests/ -m integration --tb=short
```

Les tests `test_integration_*.py` sont marqués `@pytest.mark.integration`
et **skip automatiquement** si invoqués sans `-m integration` (cf.
`conftest.py`).

## Lancer absolument tous les tests

```bash
uv run pytest tests/ -m "integration or not integration"
```

## Markers disponibles

| Marker | Signification |
|---|---|
| `integration` | Requiert backend live à `$MIROSHARK_API_URL` |
| `slow` | Test long (≥ 1 min) — utiliser pour E2E simulation |
| `neo4j` | Requiert Neo4j live à `$NEO4J_URI` |

Voir `backend/pyproject.toml` `[tool.pytest.ini_options]` et
`backend/tests/conftest.py` `pytest_configure` pour la config exacte.
