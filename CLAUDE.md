# CLAUDE.md — Bassira (base MiroShark)

SaaS B2B de simulation multi-agents : des centaines de personas LLM réagissent à un
scénario (réseaux sociaux simulés + marché de prédiction, heure par heure) → rapport
C-Level PDF. Marque visible : **Bassira (بصيرة)** ; identifiants techniques : `miroshark`.
Stade : **en production** (https://prospectives.ai-mpower.com, Coolify, auto-deploy sur
push `main`). Cible : C-Level et institutions MENA, vente sur devis (MAD/USD, jamais EUR).

## Stack et commandes

- **Backend** : Flask (Python 3.11, `uv`) — moteur `backend/wonderwall/`, API `backend/app/api/`
- **Frontend** : Vue 3 + Vite + Pinia + vue-i18n (fr pivot / en / ar RTL) — PAS de TypeScript
- **Données** : Supabase (12 tables multi-org, RLS partout) + Neo4j (graphe d'entités) +
  filesystem `backend/uploads/` (artefacts de simulation — éphémère sur Coolify, prudence)
- Dev complet : `npm run dev` (concurrently backend+frontend) — **ne PAS lancer en local
  sans demande explicite** (préférence d'Amine)
- Build front : `npm run build` · Tests backend : `cd backend && uv run pytest -m "not integration"`
- Tests E2E : `cd frontend && npx playwright test` (fixtures auth : `tests/e2e/fixtures/auth.ts`)
- ⚠️ Lint/typecheck : AUCUN outillage configuré à ce jour — chantier V2 (US backlog) ;
  en attendant, `py_compile` + `npm run build` sont les gates minimum.

## Règles absolues

- Règles du CLAUDE.md global : héritées, non recopiées (Ponytail full inclus).
- À chaque fin de story Ralph : `/ponytail-debt` — tout marqueur sans déclencheur se
  corrige séance tenante.
- Avant de nommer toute table/colonne : lire `docs/02-data-dictionary.md`, le mettre à
  jour dans le même commit. Invariantes de données = contraintes SQL, pas du code app.
- Toute décision structurante → entrée ADR dans `docs/08-decisions-log.md` ; toute
  nouvelle dépendance prouve qu'aucun échelon Ponytail inférieur ne suffisait.
- **LLM via gateway LiteLLM** (décision Amine 2026-07-07, ADR-004) : modèle par défaut
  type DeepSeek v4 Flash + fallback sur un autre modèle ; le client LLM
  (`backend/app/utils/llm_client.py`) reste OpenAI-compatible générique et le BYOK
  client passe par la gateway. Le choix des modèles appartient à Amine, jamais à l'IA.
- **Jamais le mot « prédiction » ni de claim de calibration** dans le copy commercial
  tant que < 20 outcomes réels publics (ADR-002) — positionnement « stress-test de décision ».
- **Saqr** (ex-Kairos — renommage 2026-07-07) est un service EXTERNE (contrat API) : ne
  jamais toucher son code depuis ce repo ; ne jamais modifier le flag `--no-verify-jwt`
  ni le lang forwarding. **Saqr et Nahda CONSOMMENT les sorties de Bassira** — contrat
  API sortant à définir (US-218).
- **URLs publiques et liens de renvoi : bassira.ma TOUJOURS** (ADR-013). Le défaut SQL
  `pdf_branding.footer_right` était sur `'bassira.ai'` — corrigé par la migration
  `20260707_002_footer_bassira_ma.sql`, vérifié appliqué en base live le 2026-07-09
  (`column_default = 'bassira.ma'`, 0 row active encore sur `bassira.ai`). Emails via
  Resend sur l'adresse AI-MPower, liens pointant bassira.ma.
- Écriture de données de simulation : Supabase est la source de vérité des métadonnées
  (`simulation_ownership`) ; toute nouvelle donnée métier persistante va en Supabase,
  PAS sur `backend/uploads/` (volume éphémère — bug analytics déjà payé, admin.py:24-27).
- i18n **POLYGLOTTE INTÉGRAL** (décision Amine 2026-07-07, US-217) : clés ar/en/fr +
  langues additionnelles, sur le frontend, le backend (messages/erreurs) ET les livrables
  (PDF, emails) — sans exception. Parité stricte entre locales actives dans le même
  commit ; échapper `@` en `{'@'}` dans les placeholders (piège vue-i18n).
- Design tokens : cible = famille `--wi-*` (Causse) ; ne plus introduire de `--ms-*`.

## Spécificités qui piègent

- Prod = serveur dev Werkzeug (`backend/run.py:45`) jusqu'à la story WSGI — ne pas
  ajouter de traitement lourd dans le thread HTTP (le worker PDF retombe en sync si
  `REDIS_URL` absent).
- `.ralph/` actif : lire `prd.json` + `progress.md` + `AGENTS.md` avant toute action
  (règle globale). `backlog.yaml` racine est MORT (figé US-034) — ignorer.
- `railway.json` / `render.yaml` : cibles jamais utilisées — seul Coolify compte.
- Fixtures de tests `backend/tests/` : les tokens/clés sont FACTICES (vérifié) — ne pas
  les « corriger ».

## Documents de référence (lire avant d'agir sur le sujet)

| Sujet | Fichier |
|---|---|
| Produit, périmètre V2 | docs/01-app-spec.md |
| Données (12 tables, PII, pièges RLS) | docs/02-data-dictionary.md |
| Features et backlog V2 | docs/04-feature-backlog.md |
| Intégrations externes | docs/05-integrations.md |
| Marque, palette Causse, voix | docs/06-brand-brief.md |
| Légal (AGPL, AI Act, 09-08) | docs/07-legal-compliance.md |
| Décisions et pourquoi (ADR) | docs/08-decisions-log.md |
| Bugs déjà payés | docs/09-errors-log.md |
| Prompts IA externes (Stitch…) | docs/10-execution-prompts.md |
| Cadrage et verdict V2 | docs/np-cadrage.md |
| Docs moteur upstream | docs/ARCHITECTURE.md, docs/API.md, docs/FEATURES.md |
