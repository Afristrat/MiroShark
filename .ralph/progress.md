# Progress log — MiroShark Ralph loop

> Append-only. Une entrée par story complétée. Patterns/pièges en bas.

## Codebase Patterns (mise à jour continue)

### Frontend
- **baseURL axios** dans `frontend/src/api/index.js` doit rester relative (`''`) en prod pour passer par le reverse-proxy. La worktree dev utilise `.env.development` avec `VITE_API_TARGET` pointant vers la prod.
- **Compose détourné** : le service Vite dev tourne sur 0.0.0.0:3000 (`host: true` dans `vite.config.js`) avec `allowedHosts: true` pour accepter le hostname Cloudflare tunnel.
- **Design tokens** : `frontend/src/design-tokens.css` est la source de vérité unique des couleurs/spacing/radius. Le rebind legacy (`--color-orange` → `--ms-orange`) permet la migration progressive.

### Backend
- **Vue Compose Coolify** : les env vars de l'app Coolify sont **injectées dans tous les services du compose**, ce qui peut casser des images strict-validate (Neo4j 5 par défaut). Always validate `NEO4J_server_config_strict__validation_enabled=false` est en place.
- **Flask debug propagation** : `concurrently` tue le container quand Flask debug auto-reloader détecte un changement → cascade `restart: unless-stopped` Docker → restart loop. Toujours valider `FLASK_DEBUG=false` pour les déploiements stables.
- **DNS interne Docker** : avec Coolify, ne pas utiliser `container_name` dans le compose → préfix de Coolify casse les aliases de service.

### Infra
- **Tunnel Cloudflare** = `nahda-tunnel`, le service systemd s'appelle `cloudflared-nahda.service` (PAS `cloudflared.service`).
- **Reload après ajout sous-domaine** : `cloudflared tunnel route dns nahda-tunnel <sub>.ai-mpower.com` + ajout ingress + `sudo systemctl restart cloudflared-nahda`.

### Tests
- À documenter au fur et à mesure (pytest configs, Playwright fixtures, etc.).

## Pièges à éviter (déjà rencontrés)

- **Tunnel vers `https://...:port` côté Coolify Domains** crée des boucles HTTP redirect. Toujours utiliser `http://...:port` quand Cloudflare termine déjà le TLS.
- **Image GHCR privée** dans le compose upstream → toujours préférer `build: .` depuis le Dockerfile local sauf si l'image est publique.
- **`ports:` host-mode** dans le compose causent des conflits multi-app sur le même hôte Coolify. Utiliser `expose:` (réseau Docker interne).
- **Brand split Bassira / miroshark** depuis 2026-04-29 : la marque visible utilisateur est **Bassira** (بصيرة) sur tout le frontend (titres, hero, locales, watermarks, exports PNG, manifest PWA). MAIS l'identifiant technique `miroshark` reste partout dans le backend : MCP server key (`mcpServers: { miroshark: ... }` exposé à Claude Desktop / Cursor / `@miroshark`), loggers `get_logger('miroshark.api.*')`, CSS class `.miroshark-banner`, default graph name `'MiroShark Graph'`, doc title Swagger, GitHub repo `aaronjmars/MiroShark`, app Coolify `miro-shark`, container name. Les rares strings frontend qui réfèrent à un identifiant backend (mcp.js comment, SettingsPanel "Wire MiroShark's knowledge graph" → matche `@miroshark` que tape l'utilisateur) gardent volontairement « MiroShark ». Logo `frontend/public/miroshark-nobg.png` : path conservé, le PNG visuel doit être regénéré au branding « Bassira » par un designer (TODO non bloquant).

## Log d'itérations

### 2026-04-29 — US-009 Support RTL complet (logical properties + Tajawal + ar.json validé)
- **Statut** : passes: true
- **Volume** : 26 fichiers Vue migrés (15 prio + 11 résiduels), 201 directional CSS props remplacées par leurs équivalentes logiques, +font Tajawal, +`:lang(ar)` rule dans design-tokens.css
- **Quality gates** : npm run build OK 305 kB main / 90 kB gzip (identique pré-migration : logical props ont la même taille bytes que physiques) ; backend pytest 202/202 ; aucune régression LTR (toujours mêmes valeurs résolues quand dir=ltr)
- **Mapping appliqué** :
  - margin-left/right → margin-inline-start/end
  - padding-left/right → padding-inline-start/end
  - border-left/right (+ leur shorthand : border-left-color, border-left-style, etc.) → border-inline-start/end
  - text-align: left/right → text-align: start/end
  - float: left/right → float: inline-start/end
  - Standalone `left:`/`right:` (positioning) → inset-inline-start/end (uniquement quand au début de ligne, pour ne pas matcher transitions ou property names)
- **Tooling** : `scripts/migrate_logical_props.py` Python helper avec regex conservatrices, scope limité aux blocs `<style>` des .vue (pas <template>/<script>). Dry-run + apply. Réutilisable pour d'autres projets.
- **AR fonts** : Tajawal (Google Fonts, weights 400/500/700) chargée dans `index.html` aux côtés de Young Serif + Space Mono. Activée via `[lang="ar"]` dans `design-tokens.css` qui override `--ms-font-display` et `--ms-font-body` (mono conservée). `<html lang>` est posé par `applyDirection(locale)` du module i18n.js (déjà testé US-001).
- **ar.json** : 534/534 keys déjà complètes (audit Python : `set(flat(fr).keys()) - set(flat(ar).keys()) = ∅`). Crédit sub-agent A qui avait livré ar.json full en US-002 et continué via US-003→006. 5 valeurs « non-arabes » détectées sont légitimes (noms propres GitHub/Français/English, placeholder X, exemple sk-or-…).
- **Skip intentionnel** : PolymarketChart.vue ligne 371 — `left: leftSide ? ${tx-160}px : ${tx+12}px` dans un objet style JS Vue inline pour un tooltip positionné aux coordonnées curseur. Logique physique délibérée (le tooltip doit suivre le curseur de la même façon en LTR et RTL, pas flipper).
- **Bénéfice infra** : tous les composants migrés flippent automatiquement quand `<html dir="rtl">`, sans code Vue/JS supplémentaire. Le LanguageSwitcher (US-008) déclenche déjà le flip via `setLocale → applyDirection`.

### 2026-04-29 — US-008 LanguageSwitcher (FR/AR/EN dropdown, widget flottant)
- **Statut** : passes: true
- **Fichiers** : frontend/src/components/LanguageSwitcher.vue (nouveau, 158 l), frontend/src/App.vue (+2 imports template + 6 lignes CSS floating)
- **Quality gates** : npm run build OK (305 kB main / 90 kB gzip, +2 kB pour le composant), backend pytest 202/202 (zéro régression : aucun fichier backend touché)
- **Architecture** :
  - Widget flottant top-right (`position: fixed; inset-inline-end: 16px`) → couvre Home + toutes les vues en un seul mount via App.vue (DRY)
  - `inset-inline-end` au lieu de `right` → flip RTL automatique sans media query
  - Bouton dropdown accessible (aria-expanded, aria-haspopup, role=listbox, ESC pour fermer, click-outside)
  - Réutilise `setLocale(i18nInstance, loc)` et `applyDirection` du module i18n.js → dir=rtl/lang attributes + bassira_locale storage déjà gérés (US-001)
  - Labels options via clés i18n EXISTANTES `language.{fr,ar,en}` (noms natifs identiques cross-locale, tels que rendus par chaque fr/ar/en.json) → user voit toujours « Français / العربية / English » indépendamment de sa locale courante
  - Drapeaux : 🇫🇷 (fr) / 🇲🇦 (ar, MA pas SA — ciblage Maghreb cohérent avec le brand) / 🇬🇧 (en)
- **AC déférée** : « Test Playwright : changement de langue persiste après reload » → reportée à US-010 (set up commun de la suite Playwright multi-locale, qui couvrira aussi les ACs Playwright de US-002→006). Validation manuelle recommandée : `?lang=ar` dans l'URL → reload → dir=rtl + locale ar persistée.
- **Pattern à retenir** : pour les autres composables qui doivent connaître la locale active, utiliser `useI18n()` + accéder à `locale.value` réactif. Pour DÉCLENCHER un changement, importer l'instance via `import i18nInstance from './i18n'` et appeler `setLocale(i18nInstance, code)` (helper du module qui orchestre instance + storage + dir).

### 2026-04-29 — Rebrand frontend MiroShark → Bassira (hors Ralph, prereq UI cohérente)
- **Statut** : commité hors prd.json (pas une story Ralph)
- **Volume** : 30 fichiers, ~93 remplacements (en/fr/ar locales, index.html, manifest.json, sw.js, 14 vues/composants, design-tokens header, services worker, watermarks chart, download filenames `bassira-*.png`)
- **Quality gates** : npm run build OK (303 kB main), backend pytest 202/202 (zéro régression : aucun fichier backend touché)
- **Scope préservé (4 catégories de strings techniques)** :
  - `aaronjmars/MiroShark` GitHub URLs (3 occurrences) — repo upstream
  - `https://miroshark.app` placeholder URL d'exemple
  - `/miroshark-nobg.png` LOGO_URL — fichier asset existant en `frontend/public/`
  - `miroshark` MCP server key — backend identifier que l'utilisateur tape (`@miroshark` dans Cursor)
- **Outils** : `scripts/rebrand_bassira.py` Python script avec sentinels pour protéger les 4 catégories. AR transliteration `ميروشارك` → `بصيرة`. Locale storage key migré `miroshark_locale` → `bassira_locale` (pas de users prod existants).

### 2026-04-29 — US-034 Security headers (HSTS, X-Frame-Options, CSP, Referrer-Policy, Permissions-Policy)
- **Statut** : passes: true
- **Fichiers** : backend/app/security_headers.py (nouveau), backend/app/__init__.py, backend/tests/test_unit_security_headers.py
- **Quality gates** : 8/8 tests security passent
- **Approche** :
  - Middleware Flask `after_request` → setdefault les headers (n'override pas si déjà posé)
  - `/share/*`, `/embed/*`, `/api/simulation/<id>/share-card.png|replay.gif` SANS X-Frame-Options ni CSP (pour social unfurl Slack/Discord/Twitter)
  - HSTS conditionnel à `FLASK_ENV != 'development'` (sinon dev local en HTTP foire)
  - CSP minimal qui tolère encore unsafe-inline + Google Fonts (à durcir post US-016)

### 2026-04-29 — US-031 + US-032 + US-033 Hardening prod minimal
- **Statut** : passes: true (3 stories en un seul commit, fichier config.py touché par les 3)
- **Fichiers** : backend/app/config.py, backend/app/__init__.py, backend/tests/test_unit_hardening.py
- **Quality gates** : 174 tests passed, 17 skipped (intégration), 0 régression
- **Changes** :
  - SECRET_KEY default → fallback per-process random (`secrets.token_hex(32)`) + flag `SECRET_KEY_FROM_ENV`
  - Config.validate() refuse de booter si SECRET_KEY absent + FLASK_ENV != 'development'
  - DEBUG default 'False' (était 'True')
  - CORS lit `CORS_ORIGINS` depuis env, defaults `https://prospectives.ai-mpower.com,http://localhost:3000,http://127.0.0.1:3000`
- **Learnings** :
  - importlib.reload(app.config) suffit pour tester monkeypatch.setenv sur Config classvars.
  - flask-cors gère bien les listes Python comme value de `origins`. Pas besoin d'array YAML.
  - Le sub-agent US-002 tourne en parallèle sans conflit (backend vs frontend).

### 2026-04-29 — US-017 + US-018 She Start template + seed (sub-agent B)
- **Statut** : passes: true (2 stories ensemble, même PR backend)
- **Fichiers** : preset_templates/she_start_cohort_replay.json (162 l) + sous-dossier (seed_template 603 l, personas 127 l, README 90 l) + templates.py (+3 l) + test_unit_she_start_template.py (193 l, 5 tests)
- **Quality gates** : 5/5 she_start, 202 total passed, 17 skipped — test_unit_templates_schema valide automatiquement le nouveau JSON
- **Architecture** : 1 fichier JSON par template (convention existante) + sous-dossier sibling pour artefacts seed/personas/README
- **Variants A/B/C** : Ground Truth Replay, Cohort Twin (5 runs), Blind Spot Hunt (5 leaders retirées)
- **Persona archetypes** : 8 mentors (M-BRA, M-GRO, M-JUR, M-FUN, M-TEC, M-OPS, M-LEA, M-AFR)
- **Director event slots** : S3 (Pitch Fire), S5 (intervention), S7 (sélection GITEX) — paramétrables par utilisateur
- **PMF criteria formalisé** : ≥3 clients OU ≥50 utilisateurs OU ≥7/10 jury, 2 sur 3 → validé
- **API additions** : `has_variants` + `variants_count` dans GET /api/templates/list (rétrocompatible)

### 2026-04-29 — US-020 Backend endpoint /api/calibration/brier-score (sub-agent C)
- **Statut** : passes: true
- **Fichiers** : backend/app/api/calibration.py (nouveau, 462 l), test_unit_calibration.py (490 l), __init__.py x2
- **Quality gates** : 12/12 calibration tests, 197 total passed, 17 skipped
- **Architecture** : 3 couches testables séparément (compute pure / gather I/O / Flask route)
- **Source données** : SimulationManager.list_simulations() filtre `is_public=True` + `outcome.json` + `trajectory.json`
- **Brier formula** : Y={1.0 correct, 0.5 partial, 0.0 wrong}, p=bullish_share du dernier snapshot trajectory, Brier=mean((Y-p)^2)
- **Hypothèse documentée** : `template_id` dans simulation_config.json n'est pas encore écrit par le pipeline → filtre template traité comme exclusion silencieuse pour l'instant
- **Endpoint** : GET /api/calibration/brier-score (public, sans auth) avec `?template=&from=&to=`, cache HTTP 60s, retourne 200 même `n=0`

### 2026-04-29 — US-002 Externaliser textes Home + ScenarioSuggestions + TrendingTopics + TemplateGallery
- **Statut** : passes: true (délégué à sub-agent général en arrière-plan)
- **Volume** : ~67 chaînes externalisées dans 4 fichiers Vue + 3 fichiers locales
- **Quality gates** : npm run build exit 0 (731 modules)
- **Détails** :
  - Home.vue : ~38 chaînes (hero, panel, steps, console, error toasts via useI18n)
  - ScenarioSuggestions.vue : ~8 chaînes (Bull/Bear/Neutral, useThis, range)
  - TrendingTopics.vue : ~8 chaînes (label, refreshes, time relatif)
  - TemplateGallery.vue : ~13 chaînes (gallery, agents/rounds/branches, oracle, difficulty)
  - ar.json complet (aucun TODO) — bonus livré par le sub-agent
- **Learnings** :
  - useI18n() en `<script setup>` requiert `const { t } = useI18n()` puis `t('key')` (pas `$t` qui est uniquement disponible en `<template>`)
  - Renommer `const t = Date.parse(...)` en `const ts = ...` pour éviter shadowing du t i18n
  - Symboles purs (◎ ◈ ↑ ↓ →) et identifiants techniques (PDF, MD, TXT, MiroShark-V1.0) laissés tels quels — ne sont pas du chrome UI

### 2026-04-29 — US-001 Setup vue-i18n + structure locales
- **Statut** : passes: true
- **Fichiers** : frontend/src/i18n.js, frontend/src/locales/{fr,ar,en}.json, main.js, vite.config.js, package.json
- **Versions** : vue-i18n@^11.4.0 (et non v9 — v11 est maintenue actif)
- **Quality gates** : npm run build ✓ (199.89 kB main bundle / 66.10 kB gzip)
- **Learnings** :
  - vue-i18n 11 est la version maintenue (anciennement v9). API similaire (`createI18n`, `legacy: false`).
  - Le `@intlify/unplugin-vue-i18n` plugin Vite est obligatoire pour pré-compiler les JSON et activer `runtimeOnly: true` (bundle plus léger).
  - Détection 4 niveaux : URL `?lang=` → `localStorage` → `navigator.language` → fallback `fr`.
  - `applyDirection()` est appelé au chargement de l'instance i18n → pas besoin de toucher App.vue.

### 2026-04-29 — US-000 Sécuriser pytest pour quality gates Ralph
- **Statut** : passes: true
- **Fichiers touchés** : backend/pyproject.toml, backend/tests/test_unit_smoke.py, backend/tests/README.md
- **Durée** : ~10 min
- **Quality gates** : pytest 167 passed / 17 skipped intégration ✓ ; npm run build ✓
- **Learnings** :
  - Le repo avait déjà `conftest.py` avec markers + skip auto des integration. Bonne hygiène.
  - 17 fichiers `test_unit_*.py` déjà présents : le projet est plus mature qu'attendu côté tests.
  - Smoke tests minimaux (create_app, blueprints, Config.validate) suffisent pour US-000 car le reste de la suite valide déjà la majorité des composants.
