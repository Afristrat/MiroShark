# 03 — Instructions de codage du module Intake (CLAUDE.md du module)

> À lire par toute session/agent qui codera le module. Hérite intégralement du CLAUDE.md
> racine et du CLAUDE.md global — rien ici ne les contredit, tout les précise.

## Contraintes non négociables

1. **Aucun code avant validation par Amine des 10 documents de ce dossier.** Ce document
   ne devient exécutoire qu'après cette validation.
2. **LLM exclusivement via `backend/app/utils/llm_client.py`** (OpenAI-compatible, gateway
   LiteLLM — ADR-004). AUCUN SDK nouveau (échelle Ponytail, barreau 5 : dépendance déjà
   installée). Le modèle de l'agent est une variable d'env (`INTAKE_LLM_MODEL` ou
   réutilisation de `LLM_MODEL_NAME`) — **le choix du modèle appartient à Amine, jamais à
   l'IA** (mémoire projet + ADR-004).
3. **La clé LLM ne touche JAMAIS le frontend** : l'agent est un endpoint backend
   (`POST /api/intake/agent/turn`), le front n'échange qu'avec Flask.
4. **i18n polyglotte intégral** (ADR-008/US-217) : chaque écran, chaque message d'erreur,
   chaque email, ET le system prompt de l'agent existent en fr/en/ar — parité stricte dans
   le même commit ; `@` échappé `{'@'}` dans les placeholders vue-i18n.
5. **Supabase = source de vérité** : brief et transcript en base, jamais sur
   `backend/uploads/` (leçon US-203, volume éphémère). Migration SQL + mise à jour de
   `docs/02-data-dictionary.md` dans le même commit.
6. **Validation aux frontières** : le brief produit par l'agent est validé par jsonschema
   côté serveur AVANT écriture ; tout ce qui vient du prospect (formulaire ET réponses à
   l'agent) est traité comme non fiable (cf. 09-risques : injection).
7. **Design tokens `--wi-*` uniquement** (Causse) — aucun `--ms-*` nouveau.
8. **Rate limiting** : réutiliser le pattern des dicts internes existants
   (`_ENRICH_RATE_HITS`, cf. progress.md) — l'endpoint agent est public donc limité par IP
   ET par session (7 tours max, compteur `agent_turns` en base, vérifié serveur).
9. **Tests** : pytest unitaires (routage, validation jsonschema, machine à états, budget
   de tours) + Playwright sur le parcours complet (formulaire → routage) avec agent mocké.
   L'agent réel n'est JAMAIS appelé dans les tests (mock du llm_client, pattern
   test_enricher.py).
10. **Gates avant tout commit** : `cd backend && uv run pytest -m "not integration"` +
    `ruff check .` + `cd frontend && npm run build` — zéro échec, zéro dette.

## Architecture cible (indicative — l'implémenteur peut mieux proposer, en le justifiant)

- `backend/app/api/intake.py` — blueprint `/api/intake/*` : `POST /session` (démarre),
  `POST /session/<id>/form` (soumet A1-A8), `POST /session/<id>/agent/turn` (étape B),
  `POST /session/<id>/complete` (routage + email).
- `backend/app/services/intake_service.py` — machine à états, validation brief, routage
  (règles déterministes de la spec §3.C — PAS de LLM dans le routage).
- `backend/app/services/intake_agent.py` — construction des prompts (depuis les templates
  du doc 10), appel llm_client, parsing/validation de la sortie, gestion des flags
  confidentiels, budget de tours.
- `frontend/src/views/IntakeView.vue` (ou refonte de QuoteView) — les 3 temps + le chat.
- Emails : templates dans `backend/app/templates/emails/` (pattern existant, table-based,
  palette Causse).

## Pièges du repo applicables (ne pas repayer)

- Werkzeug/gunicorn : pas de traitement lourd dans le thread HTTP — l'appel LLM de
  l'étape B est court (1 tour), mais prévoir timeout 30 s et retour d'erreur gracieux
  (clé i18n), jamais de blocage du worker au-delà.
- vue-i18n `@` → `{'@'}`.
- Compose Coolify : pas de `container_name`, `expose:` pas `ports:`.
- Le hook pre-commit exécute Ruff sur tout le repo.
- `get_supabase_admin()` peut lever `SupabaseConfigError` : l'acquérir DANS les try des
  helpers fail-soft.
