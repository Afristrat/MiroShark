# MiroShark — Guide pour agents Ralph

> Lecture obligatoire avant la première itération. Mise à jour à chaque pattern important découvert.

## Contexte produit

MiroShark = **moteur de simulation d'intelligence collective**. Un texte (article, scénario, question) → 150-300 personas autonomes interagissent en parallèle sur **Twitter / Reddit / Polymarket** simulés. Output : rapport ReACT analytique + GIF replay du belief drift + share card PNG. Coût : 1-3,50 $/run, 10 min.

Déployé en prod sur `https://prospectives.ai-mpower.com` (Coolify, IP infra AIMPOWER).
Repo GitHub : `Afristrat/MiroShark` (fork upstream `aaronjmars/miroshark`).

## Stack

| Couche | Tech | Path |
|---|---|---|
| Frontend | Vue 3 + Vite + axios | `frontend/` |
| Backend | Flask + Blueprints | `backend/app/api/*.py` |
| DB graphe | Neo4j 5 | container compose |
| Embeddings | Ollama `nomic-embed-text` | container compose |
| LLM | OpenAI-compatible (Moonshot Kimi) | env vars `LLM_*` |
| Build | Docker Compose via Coolify | `docker-compose.yml` |

## Avant chaque itération

1. **Lire** `.ralph/prd.json` → identifier la story prioritaire avec `passes: false` ET dont toutes les `dependencies` ont `passes: true`.
2. **Lire** `.ralph/progress.md` → patterns + pièges des itérations précédentes.
3. **Vérifier** que la prod ne soit pas en `restarting:unknown` avant de toucher quoi que ce soit côté backend qui sera déployé.

## Pendant l'itération

### Faire
- Travailler sur **une seule story** à la fois.
- Suivre les patterns documentés dans `progress.md`.
- Préserver les emojis/icônes existants dans les composants Vue (le style ASCII orange/Evangelion est intentionnel mais en cours de remplacement par Playful & Soft).
- Préserver les events/props émis aux composants parents (no breaking changes silencieux).
- Préserver l'accessibilité existante (`aria-*`).
- Pour les fichiers `.vue` : garder la logique `<script>` intacte sauf si la story l'exige explicitement.

### Ne pas faire
- Ne pas modifier `docker-compose.yml`, `package.json`, `pyproject.toml` sans raison liée à la story.
- Ne pas créer de nouvelles dépendances npm/pip non triviales sans flag explicite dans la story.
- Ne pas pousser sur `main` si les quality gates échouent.
- Ne pas désactiver de tests existants pour faire passer une story.

## Quality gates (obligatoires avant `passes: true`)

```bash
cd frontend && npm run build
cd backend && uv run pytest tests/ --tb=short -x
# Pour stories UI :
npx playwright test --reporter=list
```

Si l'un échoue → debug, relance. Pas de raccourci.

## Stratégie de commits

- **Une story = un commit atomique sur `main`**.
- Format :
  ```
  [US-XXX] Titre court de la story

  Description compacte :
  - acceptance criteria principal
  - autres bullets

  Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
  ```
- Push direct sur `main` après quality gates verts (pas de PR).
- Si pre-commit hook échoue : **investiguer et fixer**, jamais `--no-verify`.

## Mise à jour des artefacts Ralph

À chaque story complétée :
1. `.ralph/prd.json` → la story passe à `passes: true` + ajouter `completedAt` ISO + métadonnées (fichiers touchés, durée).
2. `.ralph/progress.md` → log dater + story + learnings éventuels (pattern découvert, piège à éviter).

## Patterns connus du projet (à enrichir au fil du loop)

### Frontend
- **API axios** : `frontend/src/api/index.js` — `baseURL = ''` pour utiliser le proxy Vite. Ne pas remettre une URL absolue sans raison.
- **Design tokens** : tous dans `frontend/src/design-tokens.css` (variables `--ms-*`). Les anciennes variables `--color-orange` etc. sont encore mappées pour compatibilité, mais à supprimer progressivement.
- **Classes utilitaires** : dans `frontend/src/styles/components.css` (`.ms-card`, `.ms-btn-*`, `.ms-badge-*`, `.ms-input`, `.ms-skeleton`). Privilégier ces classes au CSS scoped redondant.
- **Routes** : router dans `frontend/src/router/`. La route `/verified` partage la même vue que `/explore` avec une prop `verifiedOnly`.

### Backend
- **Blueprints** : un fichier par domaine dans `backend/app/api/*.py`. Préfixe `/api/<bp_name>/...`.
- **Auth admin** : bearer token unique via env `MIROSHARK_ADMIN_TOKEN` sur les routes `/publish`, `/resolve`, `/outcome`. Fail-closed si absent.
- **LLM client** : `backend/app/utils/llm_client.py`. Lit `Config.LLM_*` au runtime. Toujours respecter la config en place.
- **Templates** : dans `backend/app/templates/` (path à valider avec le code de `backend/app/api/templates.py`).
- **Erreurs** : aujourd'hui retournées en strings libres → la story `US-007` impose la migration vers `error_code` snake_case.

### Infra
- **Coolify env vars** : injectées dans **tous** les services du compose. Faire attention aux env vars `NEO4J_*` qui sont auto-mappées en settings Neo4j (cf. fix `NEO4J_server_config_strict__validation_enabled=false` dans le compose).
- **Tunnel Cloudflare** : `nahda-tunnel`, ID `7156c3f9-07a4-472d-963a-efaf59769d40`, config `/home/serveurai/.cloudflared/config-nahda.yml` côté serveur.
- **DNS** : sous-domaine `prospectives.ai-mpower.com` déjà routé. Pour ajouter un autre sous-domaine : `cloudflared tunnel route dns nahda-tunnel <sub>.ai-mpower.com` côté serveur + ajouter ingress dans `config-nahda.yml`.

## Sécurité

- **Jamais de secrets hardcodés** (env vars uniquement).
- **API key Moonshot** : env `LLM_API_KEY` côté Coolify. La key actuelle d'Amine est dans Coolify Env Vars (à rotater régulièrement).
- **Token admin** : env `MIROSHARK_ADMIN_TOKEN` côté Coolify. Utilisé pour `/publish`, `/resolve`, `/outcome`.
- **Neo4j password** : env `NEO4J_PASSWORD` côté Coolify (lit le compose qui injecte dans `NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}`).
- **CORS** : actuellement `*` — la story `US-032` impose la migration vers whitelist.

## Internationalisation (post-US-001)

- 3 locales : `fr` (pivot), `ar` (RTL), `en` (fallback).
- Toutes les chaînes UI passent par `$t('section.subsection.key')`.
- Aucune string EN visible dans les `<template>`.
- RTL via `document.documentElement.dir = 'rtl'` quand locale = ar.
- Polices arabes via Google Fonts (Tajawal ou Almarai).

## Signal de complétion

Quand toutes les stories de `prd.json` ont `passes: true` :
```
<promise>COMPLETE</promise>
```

Ne jamais émettre ce signal avant vérification complète des quality gates sur `main`.
