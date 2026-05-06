# Progress log — MiroShark Ralph loop

> Append-only. Une entrée par story complétée. Patterns/pièges en bas.

## Codebase Patterns (mise à jour continue)

### Frontend
- **baseURL axios** dans `frontend/src/api/index.js` doit rester relative (`''`) en prod pour passer par le reverse-proxy. La worktree dev utilise `.env.development` avec `VITE_API_TARGET` pointant vers la prod.
- **Compose détourné** : le service Vite dev tourne sur 0.0.0.0:3000 (`host: true` dans `vite.config.js`) avec `allowedHosts: true` pour accepter le hostname Cloudflare tunnel.
- **Design tokens** : `frontend/src/design-tokens.css` est la source de vérité unique des couleurs/spacing/radius. Le rebind legacy (`--color-orange` → `--ms-orange`) permet la migration progressive.
- **Auth Supabase + Pinia (US-093)** : `frontend/src/stores/auth.js` (Pinia store), `frontend/src/lib/supabase.js` (singleton anon), `frontend/src/api/client.js` (axios + bearer auto). Init du store en IIFE async dans `main.js` AVANT `app.mount()` pour que `router.beforeEach` voie l'état auth réel. Routes protégées via `meta.requiresAuth` + redirect `/login?redirect=<path>`. **Piège vue-i18n** : le caractère `@` est interprété comme syntaxe `@:link` → escape obligatoire dans les placeholders email avec `{'@'}` sinon erreur de compilation `error code: 10` au build.
- **Classes scoped Vue** : les classes définies en `<style scoped>` ne sont pas accessibles depuis un autre composant (attribut `[data-v-*]` unique). Pour partager des styles d'inputs/cards entre vues, soit dupliquer (préfixe distinct par composant), soit déplacer dans `styles/components.css` global.

### Backend
- **Vue Compose Coolify** : les env vars de l'app Coolify sont **injectées dans tous les services du compose**, ce qui peut casser des images strict-validate (Neo4j 5 par défaut). Always validate `NEO4J_server_config_strict__validation_enabled=false` est en place.
- **Flask debug propagation** : `concurrently` tue le container quand Flask debug auto-reloader détecte un changement → cascade `restart: unless-stopped` Docker → restart loop. Toujours valider `FLASK_DEBUG=false` pour les déploiements stables.
- **DNS interne Docker** : avec Coolify, ne pas utiliser `container_name` dans le compose → préfix de Coolify casse les aliases de service.

### Infra
- **Tunnel Cloudflare** = `nahda-tunnel`, le service systemd s'appelle `cloudflared-nahda.service` (PAS `cloudflared.service`).
- **Reload après ajout sous-domaine** : `cloudflared tunnel route dns nahda-tunnel <sub>.ai-mpower.com` + ajout ingress + `sudo systemctl restart cloudflared-nahda`.

### Tests
- **Playwright E2E — pattern auth injection (US-117)** : pour tester des routes protégées par Pinia auth sans connexion réelle, utiliser la fixture `seedSuperAdminAuth(page)` / `seedRegularUserAuth(page)` + la stratégie 2 phases `navigateAuthenticated(page, path, authSignal)`. Toutes ces fonctions sont dans `frontend/tests/e2e/fixtures/auth.ts`. Ne jamais utiliser `page.goto(protected_path)` directement pour les routes nécessitant auth — race condition quasi garantie avec le guard Pinia.
- **Signal d'auth stable** : super-admin → `a.app-header__link[href="/console"]` ou `a[href="/admin/quotes"]` ; user normal → `a[href="/client/dashboard"]`. Ces liens apparaissent seulement quand `fetchSuperStatus()` a abouti (réactif Pinia → AppHeader).
- **Modale onboarding** : la première visite déclenche `.onb-root` sur `/` — fermer via `passerBtn.click({ force: true })` avant de cliquer les nav links.
- **Playwright base pattern** : smoke tests en `gotoLocalized(page, path, locale)` (helper dans `helpers.ts`). Guards non-auth en `page.goto` direct + `waitForURL`. Guards auth en 2 phases via `navigateAuthenticated`.

## Pièges à éviter (déjà rencontrés)

- **Tunnel vers `https://...:port` côté Coolify Domains** crée des boucles HTTP redirect. Toujours utiliser `http://...:port` quand Cloudflare termine déjà le TLS.
- **Image GHCR privée** dans le compose upstream → toujours préférer `build: .` depuis le Dockerfile local sauf si l'image est publique.
- **`ports:` host-mode** dans le compose causent des conflits multi-app sur le même hôte Coolify. Utiliser `expose:` (réseau Docker interne).
- **Brand split Bassira / miroshark** depuis 2026-04-29 : la marque visible utilisateur est **Bassira** (بصيرة) sur tout le frontend (titres, hero, locales, watermarks, exports PNG, manifest PWA). MAIS l'identifiant technique `miroshark` reste partout dans le backend : MCP server key (`mcpServers: { miroshark: ... }` exposé à Claude Desktop / Cursor / `@miroshark`), loggers `get_logger('miroshark.api.*')`, CSS class `.miroshark-banner`, default graph name `'MiroShark Graph'`, doc title Swagger, GitHub repo `aaronjmars/MiroShark`, app Coolify `miro-shark`, container name. Les rares strings frontend qui réfèrent à un identifiant backend (mcp.js comment, SettingsPanel "Wire MiroShark's knowledge graph" → matche `@miroshark` que tape l'utilisateur) gardent volontairement « MiroShark ». Logo `frontend/public/miroshark-nobg.png` : path conservé, le PNG visuel doit être regénéré au branding « Bassira » par un designer (TODO non bloquant).

### Runbook — « Échec de la génération de la configuration » Step 03

**Symptôme** : utilisateur voit Step 03 en erreur sur `/simulation/<id>` avec message backend.

**Diagnostic en 1 commande** :
```bash
curl -s "https://prospectives.ai-mpower.com/api/simulation/<id>/config/realtime" | jq -r '.data.config_error'
```

**Mapping cause → résolution** :
- `"No matching entities found, please check if the graph is built correctly"` → graphe Neo4j vide pour ce `graph_id`. Le user a sauté Step 1 ou l'extraction document a échoué. **Fix** : recréer la simulation depuis le début en s'assurant que Step 1 a bien construit le graphe (vérifier `/api/graph/<graph_id>/entities`).
- `"Agent profiles not found — run /prepare first"` (sur clic Retry) → conséquence du cas précédent : le bouton « Relancer » n'aide pas si /prepare n'a jamais réussi. **Fix** : recréer la simulation, ne pas spammer Retry.
- `"Config generation timed out after 90 seconds"` → LLM lent ou indisponible. **Fix** : vérifier prod LLM (`LLM_BASE_URL=https://api.moonshot.ai/v1`), retry après 1-2 min.
- `"...API key... / quota / model..."` → env vars backend Coolify. **Fix** : vérifier `LLM_API_KEY`, `LLM_MODEL_NAME=kimi-k2-turbo-preview`, `LLM_BASE_URL`.

**Note historique** : avant 2026-04-29 le hint UI mentionnait `OPENROUTER_API_KEY` (legacy upstream), trompeur depuis la migration Moonshot. Corrigé : hint dynamique selon le `config_error` (`hintEntities` / `hintProfiles` / `hintTimeout` / `hintLLM`) + retry frontend extrait `err.response.data.error` au lieu d'afficher `err.message` axios brut.

## Log d'itérations

### 2026-05-05 — US-109 + US-110 + US-111 + US-112 Fix ReportView + timeline + chat + agents (worktree agent-aa6c11cd)

- **Statut** : 4 stories passes:true (chantier Q-report-experience). Worktree branch `worktree-agent-aa6c11cd`, 4 commits successifs c0ff7fd / 58485ce / d0bc9c5 / cc3089a, prêts à merger sur main.

#### US-109 — Fix ReportView consume report payload (frontend rendering)
- **Bug racine** : Step4Report.vue se reposait *exclusivement* sur le polling `getAgentLog(reportId, fromLine)` pour reconstruire `reportOutline` + `generatedSections`. Pour un report déjà `status='completed'` (donc agent-log statique ou tronqué après archivage), le polling reconstituait peut-être l'outline à la 1ère poll mais le rendu UI restait visuellement bloqué sur "Chargement du rapport…" tant que la route renvoyait un sim_xxx au lieu d'un report_id (Step4Report polling alors `/api/report/sim_xxx/agent-log` qui n'existe pas, fallback US-097 sur backend get_report étant invisible côté Step4Report).
- **Fix architectural** : nouvelle prop `initialReport` sur Step4Report. Quand fournie *et* `status === 'completed'`, hydratation immédiate de `reportOutline` (depuis `outline.title/summary/sections[].title`) + `generatedSections[idx]` (depuis chaque `sections[i].content` si présent, sinon fallback sur `_splitMarkdownIntoSections(markdown_content, outline.sections)` qui découpe sur `## ` headings) + `isComplete=true` + `emit('update-status', 'completed')` + `stopPolling()`. Le polling ne démarre que si `!isComplete`.
- **Fix routing** : ReportView aligne `currentReportId` avec `reportData.report_id` réel renvoyé par le backend (cf US-097 fallback sim_xxx → report). Sans ça, Step4Report polling continuait sur le mauvais ID.
- **Fix DEFCON 1** : suppression du placeholder factice « Market Sentiment Resilience Under Regulatory Stress » dans `projectTitle` (et son équivalent dans `projectSummary`). Priorité réelle : `reportMeta.outline.title > projectData.name > simulation_requirement > '—'`. Aucun titre fabriqué.
- **Fix tab title** : `document.title` utilise désormais le vrai `outline.title` tronqué à 60 chars (au lieu du compteur générique `(4/4) Bassira`).

#### US-110 — Timeline avancement progressif 1/4 → 4/4
- Nouveau composant `frontend/src/components/ReportProgressTimeline.vue` (4 stages : graphBuild → simulation → agents → report).
- Statut de chaque stage *dérivé* des données existantes (`reportMeta.status` + `simulationData.runner_status` + `simulationData.completed_at` + `projectData.graph_id`) — aucun nouvel endpoint backend nécessaire. `agents` = done dès que simulation est done (synthèse agents = output dérivé du runner).
- Polling 5 s sur `getReport` + `getSimulation` tant que `allStagesDone === false`. Auto-stop dès que tout est done. `watch(allStagesDone)` redémarre/arrête dynamiquement.
- 28 clés i18n FR/EN/AR (`report.progress.title/step/of/status.* + stages.<id>.title/subtitle`). Polices Causse Warm Intelligence (--wi-*). RTL via `inset-inline-*` + grid → flex en mobile.

#### US-111 — Chat avec le rapport
- Nouveau composant `frontend/src/components/ReportChatPanel.vue` (sliding panel 380px à droite, fullscreen mobile <600px).
- Endpoint backend `POST /api/report/chat` *déjà existant* (cf `frontend/src/api/report.js::chatWithReport`). Le panel lui passe `{simulation_id, message, chat_history}` avec history reconstruit depuis `messages.value.slice(0, -1)` (on exclut le dernier user message qu'on vient juste de pousser).
- Persistance localStorage clé `bassira:report:<reportId>:chat` (40 derniers messages, slice protège du quota). `clearHistory()` retire la clé.
- Markdown rendu via `renderMarkdown` (utility partagée Step4Report). Bulles user terracotta (--wi-primary-container) vs assistant cream (--wi-surface). 3 thinking-dots animés durant l'envoi.
- 13 clés i18n FR/EN/AR (`report.chat.*` + `report.actions.openChat/closeChat`). Toggle via bouton dans toolbar ReportView.
- RTL : `inset-inline-end: 0` (panel passe à gauche en RTL) + `:global([dir='rtl'])` pour inverser la direction du slide CSS.

#### US-112 — Onglet « Voir les agents »
- Bouton dans toolbar ReportView (icône users) → `router.push({ name: 'Interaction', params: { reportId } })`.
- Bouton symétrique « Retour au rapport » dans toolbar InteractionView (`iv-back-btn`) → `router.push({ name: 'Report', params: { reportId } })`. Fallback `router.back()` si pas de reportId.
- 3 clés i18n FR/EN/AR (`report.actions.viewAgents/viewAgentsAria/backToReport`).
- Pattern : si InteractionView est ouvert directement par URL externe (sans navigation depuis ReportView), le bouton retour pointe quand même vers le bon report grâce au `route.params.reportId` lu au mount.

#### Quality gates (4/4 commits passent)
- `cd frontend && npm run build` → OK pour chaque commit. Bundle principal 773.93 kB (vs 767.87 kB avant US-110/111/112) — +6 kB pour 2 nouveaux composants + 88 nouvelles clés i18n × 3 langues, raisonnable.
- `cd backend && uv run pytest tests/ --tb=short -x` → **878 passed, 17 skipped, 0 régression**. Aucune story n'a touché au backend (les endpoints `/api/report/*` étaient tous déjà présents).
- Playwright : non lancé dans le worktree (suite e2e cible la prod, pas le dev local).

#### Décisions architecturales notables
- **Hydration vs polling** : Step4Report garde le polling pour la génération live (status `planning`/`generating`), mais l'hydration directe via `initialReport` est strictement préférable dès que `status === 'completed'`. Pas de boucle inutile sur un rapport statique. `stopPolling()` appelé immédiatement post-hydration.
- **`_splitMarkdownIntoSections` fallback** : seulement utilisé si l'outline JSON ne contient pas le content de chaque section (anciens reports backend pre-2026-05). Le backend actuel (`save_outline` + `save_section`) garantit que `outline.sections[i].content` est rempli, donc le fallback ne s'active jamais en pratique sur les nouveaux reports.
- **Timeline self-derived** : volontairement pas de nouvel endpoint `/api/simulation/<id>/progress` parce que tout l'info est déjà dispo. Évite une dette « new endpoint à maintenir ».
- **Chat history scope** : par reportId pas par simulationId. Cohérent avec la convention frontend (la route est `/report/:reportId`). Si un user re-génère un rapport (nouveau report_id), il commence un nouveau chat (volontaire, le contexte sémantique change).
- **Bouton retour InteractionView** : choix de `router.push` au lieu de `router.back()` parce que l'utilisateur peut arriver sur InteractionView par lien direct (URL externe), auquel cas back() ne pointerait pas vers le rapport.

#### Patterns nouveaux à propager
- **Hydration depuis payload + fallback polling** : pattern réutilisable pour tout composant Vue qui poll un endpoint. Si le parent peut fournir l'état complet, hydrater directement et n'activer le polling que pour le mode incrémental. Voir `Step4Report::hydrateFromReport` + `watch(() => props.initialReport)`.
- **Timeline 4 stages dérivée** : pattern à étendre pour SimulationRunView (montrer `prepare → run → analyze → report`). Cf `ReportProgressTimeline.vue` comme template.
- **Sliding panel `:global([dir='rtl'])`** : Vue scoped CSS isole les sélecteurs par data-attribute. Pour cibler un état HTML root (dir=rtl), utiliser `:global()` autour du sélecteur. Sinon le RTL ne flip pas.

---

### 2026-05-05 — US-117 Tests Playwright E2E multitenant (50+ tests)

- **Statut** : passes:true (chantier Q-e2e-multitenant).
- **Périmètre** : extension de la suite Playwright (32 → 74 tests) avec les nouvelles routes multitenant introduites en US-091→108.
- **Fichiers créés** :
  - `frontend/tests/e2e/fixtures/auth.ts` : fixtures `seedSuperAdminAuth(page)` + `seedRegularUserAuth(page)` + `navigateAuthenticated(page, path, signal)`. Stratégie d'injection en 2 phases : (1) `addInitScript` qui monkey-patche `window.fetch` en contexte browser pour intercepter les appels Supabase Auth + `/api/client/auth/me` + `/api/admin/me/super-status` AVANT l'init Pinia ; (2) `page.route` pour les appels réseau cross-origin Supabase. URL Supabase prod : `https://fvfifgstytvxssffvsbs.supabase.co`.
  - `frontend/tests/e2e/auth-flows.spec.ts` : 14 tests — /login UI (bouton Google OAuth, Magic Link, validation email, intent ?redirect=), /signup form (5 champs, bouton submit, lien retour).
  - `frontend/tests/e2e/console-multitenant.spec.ts` : 4 tests — guard non-auth, super-admin accès rendu, bouton Lancer, redirect user normal.
  - `frontend/tests/e2e/admin-quotes.spec.ts` : 7 tests — guard non-auth, guard user normal → redirect not-super-admin, accès super-admin (h1, filtre, topbar link, état vide ou table, subtitle).
  - `frontend/tests/e2e/admin-organizations.spec.ts` : 4 tests — guard API non-auth 401/403, AdminQuotesView topbar analytics link, mock API contract JSON (2 orgs), self_service_enabled count.
  - `frontend/tests/e2e/client-dashboard.spec.ts` : 7 tests — guard non-auth, user normal (rendu, org info, CTA Commander), super-admin (rendu, CTA Lancer simulation, CTA Commander).
- **Piège principal résolu — race condition auth guard** : la race entre `auth.init()` + `fetchSuperStatus()` (async non-awaited) et le `router.beforeEach` guard causait une redirection vers `/login` même avec session injectée. **Solution** : stratégie 2 phases — charger une page publique `/`, attendre le signal DOM d'auth stable (`a[href="/console"]` ou `a[href="/admin/quotes"]` dans AppHeader pour super-admin, `a[href="/client/dashboard"]` pour user normal), puis naviguer vers la route protégée via click sur le lien header (Vue Router push client-side, pas de rechargement = store Pinia préservé).
- **Piège 2 — modale onboarding bloque click** : au premier login, une modale `.onb-root` d'onboarding apparaît sur `/`. Elle intercepte le click sur le lien Console header. Fix : `navigateAuthenticated` ferme d'abord la modale via click sur « Passer » (force: true) avant de cliquer le lien.
- **Piège 3 — Supabase URL cross-origin** : le SDK Supabase JS appelle `https://fvfifgstytvxssffvsbs.supabase.co/auth/v1/...` (pas la même origine que la prod). Le mock `page.route('**/auth/v1/**', ...)` ne couvre pas les requêtes cross-origin → remplacé par monkey-patch `window.fetch` en `addInitScript` qui intercepte toutes les URLs contenant `.supabase.co/auth/v1`.
- **Piège 4 — fetchSuperStatus non-awaited dans init()** : le store Pinia appelle `fetchSuperStatus().catch(...)` sans await dans `auth.init()`. Au moment où le guard router évalue `isSuperAdmin`, la requête peut ne pas avoir abouti → `isSuperAdmin = false` → redirect erronée. Résolu par le signal DOM (attendre `a[href="/console"]` dans le header, visible seulement quand `isSuperAdmin = true`).
- **Quality gates** :
  - `cd frontend && npx playwright test --reporter=list` → **74 passed, 0 failed** (23,3 s).
  - `cd frontend && npm run build` → **OK** (exit 0). Warnings chunk size pré-existants uniquement.

---

### 2026-05-05 — US-102 + US-103 + US-104 + US-107 + US-108 Console super-admin devis + ConsoleView privative + branding fix

- **Statut** : 5 stories passes:true (chantiers N-quotes-admin, O-self-service-console, P-branding-fix).

#### US-108 — Branding fix résiduel
- `frontend/index.html` : title `Bassira · Prospective stratégique`, `lang="fr"`, favicon SVG primary + fallback ICO/PNG.
- `frontend/public/favicon.svg` : SVG inline 64×64 — lettre arabe ب (ba) sur fond `#FAF7F2` Causse, glyph en `#FF8551` orange. Placeholder neutre (Amine a explicitement rejeté la création de logo produit).
- `frontend/public/manifest.json` : `name="Bassira"`, description « Plateforme de prospective stratégique pour décideurs MENA, Europe et Afrique ». Suppression mentions « Universal Swarm Intelligence Engine ».
- Locales fr/en/ar : remplacement `MiroShark` → `Bassira` dans `home.scenarios.sheStart.variantATitle` (chaîne user-facing). Locale en : `home.hero.tag` "Universal Swarm Intelligence Engine" → "Strategic Foresight Engine".
- Backend Python `miroshark.*` namespace **intentionnellement préservé** (loggers `miroshark.api.*`, package, MCP) car identifiant technique interne, jamais exposé visuellement.

#### US-107 — Console upload privative /console
- **Refactor majeur** : extraction de tout le bloc console (upload zone, ask-mode, fetch URL, TrendingTopics, ScenarioSuggestions, textarea, bouton Lancer, TemplateGallery, HistoryDatabase) depuis `Home.vue` vers une nouvelle vue dédiée `ConsoleView.vue` (route `/console`).
- **Router guard étendu** : `meta.requiresSelfService` (super-admin OR `currentOrg.self_service_enabled`). Si KO → redirect `/client/dashboard?reason=no-self-service`. `meta.requiresSuperAdmin` ajouté pour US-102 (redirect `/client/dashboard?reason=not-super-admin`).
- **Home.vue purifiée** : suppression *complète* du DOM dashboard-section, TemplateGallery, HistoryDatabase + scripts associés (fetchUrlDoc, runAskMode, startSimulation, formData, files, urlDocs, askDocs, etc.). Home devient page produit pure (hero + CTAs + SectorUseCases + Onboarding). 1760 → 1486 lignes.
- **Hero CTA tertiaire** conditionnel "Lancer une simulation" → `/console` (visible super-admin OR self-service ON).
- **AppHeader** : entrée nav "Console" (visible super-admin OR self-service) + entrée "Devis" (super-admin only).
- **ClientDashboardView** : bouton "Lancer une simulation moi-même" pointe désormais vers `/console` (au lieu de `/process/new` directement).
- **Tests Playwright** `console.spec.ts` : 2 tests valident que `/console` et `/admin/quotes` non-auth redirigent vers `/login?redirect=...`.

#### US-103 — Workflow statut quotes (sidecar)
- Service `quote_admin_service.py` : enum VALID_STATUSES (received|reviewing|quoted|declined|paid|in_progress|delivered) + ALLOWED_TRANSITIONS map. Sidecar `quote_<id>.status.json` à côté du payload original (US-025), structure `{status, history[], payment_link, last_email_sent_at, notes, delivered_url}`.
- Helpers : `read_quote_payload`, `read_quote_status` (default `received` si sidecar absent), `list_quotes` (paginé + filtre status), `update_quote_status` (valide transition + ajoute entry historique avec `by_email`), `update_quote_notes` (update isolé sans transition).
- Pattern `is_valid_transition(current, next)` : retourne True pour idempotence (current==next), False pour transitions interdites. Statuts terminaux : `delivered` et `declined`.

#### US-102 — Endpoints + AdminQuotesView
- Nouveau blueprint `admin_quote_bp` monté à `/api/admin/quotes`. Tous les endpoints gardés par `@require_super_admin` (compose `@require_auth` + whitelist email).
- Routes : `GET /` (liste), `GET /<id>` (détail), `PATCH /<id>/status` (transition), `PATCH /<id>/notes` (notes admin), `POST /<id>/send-payment-link` (US-104), `POST /<id>/send-delivered` (US-104).
- Frontend `AdminQuotesView.vue` : table 7 colonnes (id, date, contact, package, situation 100c, status pill couleur, actions) + modal détail (dump payload + transitions next-state buttons + zone payment_link + zone delivered + notes admin + timeline historique). Color coding pills selon brief : received=grey, reviewing=blue, quoted=orange, declined=red, paid=mint, in_progress=terracotta, delivered=green.
- API client : `fetchAdminQuotes`, `fetchAdminQuoteDetail`, `patchAdminQuoteStatus`, `patchAdminQuoteNotes`, `sendAdminQuotePaymentLink`, `sendAdminQuoteDelivered` ajoutés à `frontend/src/api/client.js`.

#### US-104 — Resend email + bridge manuel Stripe
- Service unifié `email_service.py` : `send_email(to, subject, html_body)` essaie Resend (si `RESEND_API_KEY` set) → SMTP legacy (US-025) → no-op. Best-effort, ne lève jamais. Helper `render_template(name, ctx)` charge `app/templates/emails/<name>.html` avec `str.format` substitution.
- 3 templates HTML inline (table-based, retina-safe, palette Causse Warm Intelligence) : `quote_received.html` (auto-envoyé client à la soumission US-025), `quote_payment_link.html` (envoyé par admin avec un Stripe Payment Link), `quote_delivered.html` (envoyé par admin avec un lien Notion/PDF).
- Bridge manuel Stripe : pas d'API Stripe en code. Amine génère le Payment Link via Stripe Dashboard, le colle dans le form admin, click "Envoyer" → email client + transition statut → `quoted`.
- `quote_service.py` mis à jour : `_send_client_confirmation()` ajouté à `submit_quote()` après le persist (US-025 inchangé) : envoie un email au client en plus de la notification interne sales.
- Dépendance `resend>=2.0.0` ajoutée à `backend/pyproject.toml`. Tests Resend mockés via `monkeypatch.setitem(sys.modules, "resend", fake)` — pas de SDK installé requis pour CI.
- **Action Amine post-merge** : `RESEND_API_KEY` + `RESEND_FROM_EMAIL` déjà posées dans Coolify (confirmé par Amine). Run `uv sync` sur prod après pull pour installer le SDK.

#### Tests créés (39 nouveaux)
- `tests/test_unit_quote_admin.py` : 39 tests dans 6 classes :
  - `TestStatusTransitions` (11) : couverture exhaustive des transitions valides + interdites + terminaux + idempotence + invalid statuses.
  - `TestQuoteAdminService` (8) : list_empty / list_one_quote / read_status_default / update_writes_sidecar / invalid_transition / unknown_quote / invalid_status / update_notes / filter_by_status.
  - `TestAdminQuotesEndpoints` (10) : auth (401/403) + list super-admin + detail + 404 + patch status valid/invalid/missing + patch notes + filter.
  - `TestSendPaymentLink` (3) : email envoyé + transition automatique vers quoted + sidecar payment_link / invalid URL 400 / quote not found 404. Mock Resend via `monkeypatch.setattr(email_service, "send_email")`.
  - `TestSendDelivered` (1) : full workflow received→reviewing→quoted→paid→in_progress→delivered avec email final.
  - `TestEmailService` (5) : no_backend_returns_false / resend_success (mock SDK) / empty_recipient_skipped / render_template_known / render_template_missing_fallbacks.

#### Quality gates
- `cd backend && uv run pytest -q` → **878 passed, 17 skipped, 0 régression** (vs 839 baseline US-101, +39 nouveaux). 25,65 s.
- `cd frontend && npm run build` → **OK** en 16,79 s. ConsoleView chunk 69,96 kB / AdminQuotesView chunk 10,92 kB. Warning chunk-size pré-existant uniquement sur le chunk principal (767 kB).
- `tests/test_unit_openapi.py` : 8/8 OK après ajout de `admin_quote_bp` au `_BLUEPRINT_PREFIXES` map + ajout des 6 routes admin/quotes dans `_UNDOCUMENTED_ALLOWLIST` (super-admin endpoints, internal-only).
- `tests/test_unit_quote.py` : 1 test ajusté (`test_submit_valid_quote_returns_200_and_stores_file`) pour attendre 2 sendmail (sales + client confirmation) au lieu de 1.

---

### 2026-05-05 — US-116 Audit sécurité OWASP post-multitenant + corrections P0

- **Statut** : passes:true — rapport livré, 2 P0 corrigés, 36 tests ajoutés.

#### Findings principaux
- **A05 P0 CORRIGÉ** : `traceback.format_exc()` exposé dans les réponses JSON 500 publiques de `report.py` (14 occurrences). Tracebacks déplacés vers les logs serveur uniquement. Permet aux attaquants de voir les chemins de fichiers, versions bibliothèques et structure interne.
- **A10 P0 CORRIGÉ** : `webhook_service.validate_url()` n'effectuait aucune vérification d'IP — SSRF possible si `WEBHOOK_URL=http://169.254.169.254/`. Correction : résolution DNS + blocage RFC 1918, loopback, link-local, reserved.
- **A01 OK** : RLS Supabase strict sur `organizations`, `org_members`, `simulation_ownership`. Cross-tenant IDOR bloqué double couche (app + RLS). Tous les endpoints `/api/admin/*` et `/api/client/*` correctement protégés.
- **A02 OK** : JWT dual-mode ES256/HS256 solide. Aucun secret JWT ni service_role key exposé.
- **A04 P1** : `/api/report/generate` et `/api/report/chat` sans rate limit (appels LLM coûteux). Documénté pour next sprint.
- **A06 P1** : npm — axios HIGH (DoS + SSRF bypass, `^1.13.2` → fix `≥1.15.1`), vite/rollup HIGH (dev only). pip-audit non disponible en CI (à intégrer).
- **A09 OK** : JWT jamais loggué, super-admin audit en sha256 court. 3 `print()` résiduels dans services internes (pas de secrets, P2).
- **A10 OK** : url_fetcher.py bloque les IP privées avant fetch LLM.

#### Tests créés (36 nouveaux)
- `tests/test_security_headers.py` (10) : headers A05 sur endpoints API + absents sur /share/*.
- `tests/test_rate_limits.py` (5) : rate limits enrich-ask, suggest-scenarios, quote.
- `tests/test_idor.py` (21) : auth A01 sur tous les endpoints admin + stack trace absente + SSRF webhook + SSRF url_fetcher.

#### Quality gates
- `cd backend && uv run pytest -q` → **914 passed, 17 skipped, 0 régression** (vs 878 baseline US-108). 42 s.
- Rapport : `docs/SECURITY_AUDIT_2026-05.md` complet (10 catégories OWASP, preuves file:line).

#### Codebase Patterns ajoutés
- **Stack traces publiques** : ne JAMAIS passer `"traceback": traceback.format_exc()` dans les réponses JSON d'endpoints publics. Garder le traceback dans `logger.error()` uniquement.
- **SSRF webhook** : toujours appeler `_is_private_ip(host)` dans les `validate_url()` qui acceptent des URLs arbitraires (pattern de webhook_service.py réutilisable).
- **Test rate limits** : utiliser le dict interne `_ENRICH_RATE_HITS` / `_SCENARIO_RATE_HITS` pour forcer l'état en test (thread-safe car pas de lock sur ces dicts — ils utilisent le GIL).

---

#### Décisions architecturales notables
- **Sidecar JSON plutôt que table SQL** : cohérent avec le pattern US-025 (quotes sont déjà des fichiers filesystem). Pas de migration SQL nécessaire, lecture/écriture trivialement testables avec `tmp_path`. Coût : pas de filtre status complexe en SQL — mais le volume actuel (handful per week) ne justifie pas une table.
- **3 templates HTML inline plutôt que Jinja** : aucune logique conditionnelle complexe (1 placeholder optionnel `custom_message_block` rendu directement en HTML pré-formaté côté Python). `str.format` suffit, pas de dépendance Jinja2 supplémentaire (déjà présente via Flask mais on évite de la coupler aux templates email pour les rendre testables sans contexte Flask).
- **Bridge manuel Stripe vs API Stripe** : le brief impose explicitement de ne PAS coder l'intégration Stripe Payment Link API. Amine génère le lien via Dashboard, on fait que l'envoyer par email. Coût : 1 manipulation manuelle par devis, mais 0 secret Stripe à gérer côté backend, 0 webhook à brancher, 0 surface d'attaque PCI-DSS.
- **Emails Resend avec fallback SMTP** : préserve l'expérience legacy US-025 (qui fonctionnait sur SMTP). Si Amine désactive Resend en supprimant la clé, on retombe automatiquement sur SMTP sans rien changer. Si les deux sont absents, le quote est quand même persisté sur disque (best-effort by design).
- **Refactor Home.vue : suppression complète, pas de v-if** : le brief insiste explicitement « pas juste masquer via v-if, supprimer du template ». La conséquence est que la home publique est désormais une vraie page produit légère (hero + SectorUseCases + Onboarding). 274 lignes supprimées de Home.vue. Le bloc reproduit *à l'identique* dans ConsoleView pour préserver la mécanique upload + ScenarioSuggestions + handleSuggestionUse + handleTrendingSelect.
- **Guard router en cascade dans beforeEach** : un seul `useAuthStore()` lookup, on évalue séquentiellement `requiresAuth` → `requiresSelfService` → `requiresSuperAdmin`. Plus efficace que 3 guards séparés et plus lisible.


- **Statut** : passes:true (chantier M-multitenant-supabase, follow-up US-100). Avant chantier devis.
- **Bug d'origine** : Amine a remonté que `/admin/analytics` (super-admin) affiche un compteur global de sims (« 6 au total ») mais le tableau cross-tenant US-097 reste vide. Cause identifiée : les sims créées avant US-091 vivent uniquement sur le filesystem (`backend/uploads/simulations/sim_*/`) et n'ont aucune entrée dans `public.simulation_ownership`. La table SQL drive le tableau, le compteur lit autre chose → divergence.
- **Solution livrée — pure SQL + script utilitaire Python** :
  - `supabase/migrations/20260504_002_backfill_legacy_sims.sql` : migration idempotente (`on conflict (simulation_id) do nothing`) qui insère les sims orphelines dans `simulation_ownership` avec org_id résolu par CTE `target_org` (slug `aimpower-bassira`). Inclut un placeholder neutralisant (`__placeholder__`) supprimé en fin de migration pour rester valide tant qu'aucune sim n'a été listée. Le bloc VALUES est destiné à être remplacé par la sortie du script Python.
  - `backend/scripts/check_legacy_sims_attribution.py` : script de lecture pure (aucune dépendance Supabase). Deux modes : `list` (défaut, tableau lisible) + `--sql` (émet les `VALUES (...)` prêts à coller). Lit `simulation_config.json` (clés `template_id` ou `package_id`), `outcome.json` (objet entier + extraction `brier_score`), et le mtime du dossier (ISO 8601 UTC) pour `created_at`. Échappement SQL côté Python : apostrophes doublées, `null` pour les champs absents, `::jsonb` cast pour outcome.
  - `supabase/README.md` : nouvelle Étape 9 qui documente (a) quand jouer la migration, (b) procédure de génération via le script, (c) queries SQL de vérification post-exec, (d) procédure pour ajouter de nouvelles sims rétroactivement plus tard sans toucher la migration.
- **Pas de tests pytest** : SQL pur, le script Python ne fait que de la lecture filesystem. Le script SERT lui-même à la validation post-migration : Amine compare `count(*)` Supabase ↔ `len(sims)` script.
- **Pourquoi pas d'auto-exec** : pas d'accès direct à Supabase live pour le sub-agent (pas de service_role key en local), et les sims réelles vivent sur le serveur Coolify (le filesystem local d'Amine n'a que `notarealsim/`, ce que confirme le run du script en local : « 0 sim trouvée »). Donc Amine doit lancer le script sur prod, copier la sortie dans la migration, puis Run dans le SQL Editor.
- **Quality gates** :
  - `python scripts/check_legacy_sims_attribution.py` (local) → « 0 sim trouvée » (attendu, pas de filesystem prod local).
  - `python scripts/check_legacy_sims_attribution.py --sql` (local) → commentaire « no sims to backfill » (attendu).
  - SQL syntaxiquement valide (placeholder neutralisé puis supprimé garde la migration runnable en l'état).
- **Pattern consolidé** : *« Script Python read-only filesystem + migration SQL idempotente avec placeholder neutralisable »* — utilisable pour toute future rétro-attribution (autres orgs, autres tables liées au filesystem).

### 2026-05-04 — US-100 Retirer BASSIRA_ADMIN_TOKEN legacy → JWT + email whitelist
- **Statut** : passes:true (chantier M-multitenant-supabase, follow-up US-099). Story finale du chantier.
- **Backend** :
  - `simulation.py @require_admin_token` : refactor en mode **dual-auth**.
    - PRIMARY : essaie de décoder le Bearer comme JWT Supabase + check email whitelist `BASSIRA_SUPER_ADMIN_EMAILS`. Si match → 200, pose `g.is_super_admin=True`.
    - FALLBACK : si JWT KO, compare le bearer au legacy `BASSIRA_ADMIN_TOKEN` / `MIROSHARK_ADMIN_TOKEN`. Si match → 200 + log warning « legacy admin token used » pour traçabilité.
    - Si rien ne matche : 401 (auth header présent mais ni JWT super-admin ni legacy correct) ou 503 (legacy unset + JWT non super-admin).
  - Le décorateur `require_admin_token` reste utilisé par les endpoints existants (`/api/admin/analytics`, `/publish`, `/resolve`, `/outcome`) sans modification — la transition est transparente.
- **Frontend** :
  - `AnalyticsView.vue` :
    - **Suppression complète** du formulaire admin token + `sessionStorage.getItem('bassira_admin_token')` + actions `login()` / `logout()`.
    - `authed` devient `computed(() => isAuthenticated && isSuperAdmin)` — décision 100 % basée sur le store Supabase.
    - Le gate (template `v-if="!authed"`) affiche désormais soit un CTA Login (`/login?redirect=/admin/analytics`) si pas connecté, soit un message « Accès super-admin requis » + lien retour `/` si connecté mais sans privilège.
    - `fetchData()` utilise `client.get('/api/admin/analytics')` (axios qui injecte automatiquement le Bearer JWT) au lieu de l'ancien `api.get` + sessionStorage.
    - Suppression du bouton `analytics-logout` du topbar (l'utilisateur se déconnecte via AppHeader désormais).
    - Doublon `const isSuperAdmin` retiré (conflit avec le scope US-100 auth gate).
  - i18n FR/EN/AR : nouveau namespace `analytics.gateSuperAdmin.{aria, title, notLoggedIn, notSuperAdmin, loginCta, backHome}`. Anciennes clés `analytics.gate.*` conservées pour compat (non utilisées mais non-cassantes).
- **Tests créés (7 nouveaux)** : `test_unit_admin_token_dual_auth.py` :
  - JWT super-admin valide → 200 (sans warning).
  - Legacy token valide → 200 + warning « legacy ».
  - JWT non super-admin + legacy unset → 503 ADMIN_AUTH_NOT_CONFIGURED.
  - JWT non super-admin + legacy set mais non-matching → 401 UNAUTHORIZED.
  - Pas de token + legacy set → 401.
  - Pas de token + legacy unset → 503.
  - JWT super-admin → pas de log warning legacy.
- **Quality gates** :
  - `cd backend && uv run pytest tests/test_unit_admin_token_dual_auth.py -v` → **7 PASS** en 4,11 s.
  - `cd backend && uv run pytest -q` → **839 passed, 17 skipped, 0 régression** (vs 832 baseline US-099, +7 nouveaux).
  - `cd frontend && npm run build` → **OK** en 14,17 s, après correction d'un doublon `const isSuperAdmin` (conflit de portée entre US-100 auth gate et US-095 cross-tenant section).
- **Décisions architecturales notables** :
  - **Dual-auth en cascade plutôt que feature flag** : le décorateur `@require_admin_token` essaie d'abord JWT, fallback legacy. Pas de feature flag à maintenir, transition transparente — un client n'envoyant que le legacy token continue de fonctionner durant la phase de migration. Le warning émet un signal explicite pour piloter l'arrêt définitif (US-101+).
  - **Chemin JWT prioritaire** : on ne perd pas de cycles si le caller envoie déjà un JWT super-admin. Le legacy n'est tenté que si le JWT est invalide (mauvais format, signature KO, etc.). Le path heureux super-admin ne paie pas le coût hmac.
  - **Frontend complètement réecrit, pas patché** : la suppression du sessionStorage pose un risque de boucles HTTP si un user a un vieux token en cache. On a évité ce piège en faisant `authed = computed(...)` (donc le composant n'invoque jamais `sessionStorage.removeItem` qui aurait laissé une trace). Le code legacy `analytics.gate.*` reste dans les locales pour ne pas casser un éventuel autre composant qui l'utiliserait — mais `grep` confirme qu'il n'y a qu'un seul appelant supprimé.
  - **Pas de migration de `/publish`, `/resolve`, `/outcome` côté frontend** : ces endpoints utilisent déjà le décorateur `@require_admin_token` côté backend, donc ils acceptent désormais aussi le JWT super-admin. Un opérateur existant qui scriptait avec `BASSIRA_ADMIN_TOKEN` continuera de fonctionner ; un super-admin connecté côté UI peut désormais aussi appeler ces endpoints depuis le client web s'il y en a besoin.
- **Apprentissage clé** : pour migrer un système d'auth legacy (token partagé) vers un système moderne (JWT par utilisateur) sans casser, le pattern « décorateur dual-auth en cascade » est plus simple qu'un middleware d'auth séparé. Il garde un seul point de gating, un seul code path de logging, et permet au backend d'émettre des warnings explicites pour piloter la dépréciation. Le coût additionnel par requête (un essai JWT raté avant de tomber sur le legacy) est négligeable comparé au temps DB de l'endpoint qui suit.

### 2026-05-04 — US-099 Super-admin lance ses propres simulations directement
- **Statut** : passes:true (chantier M-multitenant-supabase, follow-up US-098).
- **Backend** :
  - `supabase_client.py` : helper `get_default_super_admin_org_id()` qui résout l'org `slug='aimpower-bassira'` (créée par US-091 seed.sql) en UUID. Retourne None si l'org n'existe pas (déploiement frais sans seed) — l'endpoint /api/simulation/create fallback alors en mode legacy (pas d'ownership recordé), sans crash.
  - `simulation.py /api/simulation/create` : refactor pour résoudre `resolved_org_id` à partir de :
    1. `g.current_org.id` (membre normal d'une org → soft_check_self_service l'a posé).
    2. Sinon, si `g.is_super_admin` → `get_default_super_admin_org_id()` (US-099).
    3. Sinon, `org_id=None` (legacy public, rétro-compat).
  - `created_by` est aussi propagé depuis `g.current_user.id` quand JWT présent.
  - `package_id` aussi remonté depuis le body JSON pour cohérence avec `/api/client/simulations` (US-092).
- **Frontend** :
  - `AppHeader.vue` : nouveau bouton « + Lancer simulation » (super-admin only, visible à côté de l'entrée Admin). Style CTA primaire (background `--wi-primary`, font-weight 600). Conduit vers `/process/new`.
  - `Home.vue` : already done en US-098 (showSelfServiceConsole computed `isSuperAdmin || (isAuthenticated && currentOrg.self_service_enabled)`).
  - i18n FR/EN/AR : `nav.launchSimulation` + `nav.launchSimulationTitle`.
- **Tests créés (7 nouveaux)** : `test_unit_super_admin_simulation.py` :
  - `TestGetDefaultSuperAdminOrgId` (3) : returns-uuid / returns-none-when-missing / returns-none-on-exception.
  - `TestSuperAdminCreateSimulation` (4) : super-admin-no-org-resolves-default / super-admin-with-X-Org-Id (toujours default car bypass) / super-admin-default-missing-falls-back-legacy / legacy-no-jwt-no-org-id.
- **Quality gates** :
  - `cd backend && uv run pytest tests/test_unit_super_admin_simulation.py -v` → **7 PASS** en 14,67 s.
  - `cd backend && uv run pytest -q` → **832 passed, 17 skipped, 0 régression** (vs 825 baseline US-098, +7 nouveaux).
  - `cd frontend && npm run build` → **OK**.
- **Décisions architecturales notables** :
  - **Slug `aimpower-bassira` en constante module** (`_DEFAULT_SUPER_ADMIN_ORG_SLUG`) plutôt qu'env var : c'est un identifiant produit (pas une config d'opérateur). L'évolution vers une env var pourrait être nécessaire si Bassira lance un fork (un autre groupe founder pour un autre marché) — non urgent.
  - **Fallback gracieux quand org introuvable** : si `aimpower-bassira` n'existe pas en base (seed pas joué), `get_default_super_admin_org_id` retourne None et le endpoint fonctionne quand même (sim créée filesystem, pas de record ownership). Cela évite de bloquer le super-admin dans un environnement de test.
  - **X-Org-Id ignoré pour les super-admins** : par construction, `soft_check_self_service` bypass complet pour super-admin sans poser `g.current_org`. Si Amine veut explicitement attribuer une sim à une autre org, il devra utiliser `/api/client/simulations` (qui lui exige une vraie membership). Comportement clair, pas de surprise.
- **Apprentissage clé** : pour permettre à un super-admin de lancer une simulation sans casser le multitenant, le pattern « ownership rattaché à l'org Bassira par défaut + slug constant » est plus simple qu'un mode « no-tenant » spécial. Toutes les sims gardent un propriétaire org dans `simulation_ownership`, le super-admin a son propre dashboard `/admin/analytics` qui voit aussi sa propre org, et l'audit trail Brier reste cohérent.

### 2026-05-04 — US-098 Toggle org-level self_service_enabled
- **Statut** : passes:true (chantier M-multitenant-supabase, follow-up US-097).
- **Migration SQL** : `supabase/migrations/20260504_001_org_self_service.sql` créée mais **NON exécutée par Ralph** — Amine doit la jouer dans le SQL Editor avant déploiement (note ajoutée dans `supabase/README.md` étape 8). La migration est idempotente (`add column if not exists`) avec default=false (sécurité par défaut).
- **Backend** :
  - `supabase_client.py` : helper `is_org_self_service_enabled(org_id)` (read avec fallback `False` sur erreur — sécurité par défaut), helper `set_org_self_service_enabled(org_id, enabled)` (write, returns True si ≥1 row affectée). `get_user_orgs` mis à jour pour SELECT `self_service_enabled` avec **fallback automatique** au SELECT legacy si la colonne n'existe pas (migration pas encore jouée → l'app continue de tourner).
  - `decorators.py` : 2 nouveaux décorateurs.
    - `@require_self_service_enabled` (strict) : exige `g.current_org` (donc à chaîner après `@require_org_membership`). Vérifie le flag sinon 403 SELF_SERVICE_DISABLED. Bypass si super-admin (US-099 préparé).
    - `@soft_check_self_service` (souple) : ne casse pas les endpoints publics existants. Si JWT absent → laisse passer (mode legacy). Si JWT présent → check membre + flag, 403 si non. Permet d'appliquer US-098 progressivement sur `/api/simulation/create`, `/api/graph/build`, `/api/simulation/start` sans casser les flows.
  - `admin.py` : endpoint `PATCH /api/admin/organizations/<org_id>/self-service` (super-admin only) + colonne `self_service_enabled` exposée dans `list_all_organizations` (avec fallback legacy si migration pas jouée).
  - `client.py` : `auth_me` expose `self_service_enabled` dans le payload des orgs (consommé côté frontend par `currentOrg.self_service_enabled`).
- **Frontend** :
  - `AnalyticsView.vue` : nouvelle colonne « Self-service » avec toggle on/off par org (super-admin only). `setOrgSelfService(orgId, enabled)` ajoutée à `api/client.js`. Update optimiste de l'état local après PATCH OK ; en cas d'erreur, rollback visuel (la valeur reste celle d'avant) + message dans `orgsError`. CSS toggle sans `!important` (custom checkbox + transition transform).
  - `Home.vue` : `showSelfServiceConsole` devient `computed(isSuperAdmin || (isAuthenticated && currentOrg.self_service_enabled))` (was `ref(false)` constant US-087).
  - `ClientDashboardView.vue` : ajout d'un bouton secondaire « Lancer une simulation moi-même » (icône rocket_launch) visible uniquement si `canSelfService` (super-admin OU org avec flag actif). Conduit vers `/process/new`.
  - i18n FR/EN/AR : namespaces `analytics.selfServiceToggle.*` (column / on / off / help / error) et `dashboard.selfServiceCta.*` (label / title).
- **Tests créés (20 nouveaux)** : `test_unit_self_service_toggle.py` :
  - `TestIsOrgSelfServiceEnabled` (4) : enabled / disabled / org-missing / exception → False.
  - `TestSetOrgSelfServiceEnabled` (3) : update OK / no row / exception propagated.
  - `TestPatchSelfServiceEndpoint` (6) : no-token 401 / normal-user 403 / invalid-body 400 / org-not-found 404 / super-admin enables 200 / super-admin disables 200.
  - `TestSoftCheckSelfService` (7) : no-jwt-lets-through / invalid-jwt 401 / super-admin bypass / member-with-enabled-org passes / member-with-disabled-org 403 / member-no-orgs 403 / supabase-misconfigured-lets-through-legacy.
- **Quality gates** :
  - `cd backend && uv run pytest tests/test_unit_self_service_toggle.py -v` → **20 PASS** en 3,46 s.
  - `cd backend && uv run pytest -q` → **825 passed, 17 skipped, 0 régression** (vs 805 baseline US-097, +20 nouveaux).
  - `cd frontend && npm run build` → **OK** en 14,58 s, 832 kB chunk principal.
- **Action Amine post-merge** :
  1. Jouer `supabase/migrations/20260504_001_org_self_service.sql` dans le SQL Editor.
  2. Redeploy backend Coolify (la nouvelle colonne est utilisée par les helpers + endpoint PATCH).
  3. Activer le flag pour son org : soit via UI `/admin/analytics` toggle, soit via SQL `update public.organizations set self_service_enabled=true where slug='aimpower-bassira';`.
- **Décisions architecturales notables** :
  - **2 décorateurs (strict + souple) plutôt qu'1** : permettait soit (a) de casser les flows existants en exigeant l'auth sur `/create`, `/build`, `/start`, soit (b) de garder le comportement legacy pour les requêtes publiques. On a choisi (b) avec `@soft_check_self_service` qui devient strict UNIQUEMENT quand un JWT est fourni — le frontend self-service envoie déjà le bearer token via `api/client.js`, donc l'expérience client est exactement comme prévu sans casser les flows historiques. Le décorateur strict reste exposé pour les futurs endpoints (US-101+).
  - **Fallback SELECT pour la migration en transition** : `get_user_orgs` et `list_all_organizations` détectent l'absence de colonne `self_service_enabled` (`if "column" in str(exc)`) et retombent sur le SELECT legacy — l'app reste fonctionnelle tant que la migration n'est pas jouée, sans erreur 500 visible aux utilisateurs.
  - **Sécurité par défaut** : `default=false` côté DB + `is_org_self_service_enabled` retourne False sur erreur → toute org créée est en mode commande analyste tant qu'Amine ne l'active pas explicitement. C'est la posture safe-by-default conforme à la philosophie zero-trust côté backend.
  - **Toggle UI sans `!important`** : custom checkbox CSS (appearance: none + ::before pseudo) avec `transition: transform` pour glisser le pin. RTL géré via `inset-inline-*` + `[dir="rtl"]` translateX inversé. Aucun `!important` introduit (US-016 respect).
- **Apprentissage clé** : pour activer une feature multitenant progressivement, le pattern « décorateur souple JWT-aware » (`@soft_check_self_service`) est plus pragmatique que le pattern « décorateur strict + feature flag » : le décorateur souple respecte le contrat de l'endpoint actuel pour les requêtes non-authentifiées (legacy public mode reste fonctionnel) et n'active la nouvelle vérification que pour les requêtes authentifiées. Pas de breaking change, pas de feature flag à maintenir.

### 2026-05-04 — US-097 Super-admin voit toutes les simulations cross-tenant
- **Statut** : passes:true (chantier M-multitenant-supabase, follow-up US-095).
- **Endpoint backend** : `GET /api/admin/simulations` (require_super_admin) — service_role bypass RLS pour lire `simulation_ownership` toutes orgs confondues. Filtres : `org_id`, `package_id`, `published` (true|false), pagination `limit` (1-200, default 50) + `offset` (0+).
- **Enrichissement org** : helper `_enrich_sims_with_org_info` fait 1 lookup batch sur `organizations` via `.in_('id', distinct_org_ids)` au lieu de N+1 queries. Si l'enrichment échoue (Supabase down), on retourne quand même les sims avec `org_name=None / org_slug=None` (fail-soft, robustesse opérateur).
- **Frontend AnalyticsView** : nouvelle section « Toutes les simulations » (visible si `isSuperAdmin`) avec filtres (org dropdown alimenté par les orgs déjà chargées via US-095, package input texte, published select ternaire), pagination prev/next 50 par page, table 7 colonnes (sim · org · package · published · outcome · brier · createdAt). Reset bouton.
- **Tests créés (14 nouveaux)** : `test_unit_admin_simulations.py` :
  - `TestAuth` (3) : no-token 401 / invalid-token 401 / normal-user 403.
  - `TestListSimulations` (8) : empty / single+enrichment / filter org_id / filter package_id / filter published true|false / pagination limit+offset / limit-cap-at-200.
  - `TestRobustness` (3) : Supabase config 503 / select-failure 500 / org-enrichment-failure-does-not-brick (sim retournée, org_name=None).
- **Quality gates** :
  - `cd backend && uv run pytest tests/test_unit_admin_simulations.py -v` → **14 PASS** en 3,58 s.
  - `cd backend && uv run pytest -q` → **805 passed, 17 skipped, 0 régression** (vs 791 baseline US-095, +14 nouveaux).
  - `cd frontend && npm run build` → **OK**, 832 kB chunk principal (warning chunk-size pré-existant uniquement).
- **Décisions architecturales** :
  - **Pagination via `range(offset, offset+limit-1)`** (Postgrest convention) plutôt que `limit/offset` séparés : l'API supabase-py expose `range` qui translate vers `Range: 0-49` côté HTTP — pattern idiomatique Postgrest.
  - **`count="exact"` lors du select** : retourne le total exact dans `response.count` même quand on pagine. Coût négligeable pour <100k rows ; on bascule sur `"estimated"` si la table dépasse 1M.
  - **Filtre `published` ternaire côté frontend** : `'' | 'true' | 'false'` mappé sur `undefined | true | false` côté backend → permet de distinguer « tous » de « non publiés » sans mauvaise inférence.
  - **Pas de filtre `status` pour l'instant** : `simulation_ownership` ne stocke pas le status filesystem évolutif ; un filtre côté Python sur les sims paginées n'aurait pas de sens. Reporté en US-101+ si besoin (avec une nouvelle colonne `last_known_status`).
- **Apprentissage clé** : pour un endpoint super-admin avec filtres dynamiques, le pattern « MagicMock chain partagé pour toutes les méthodes (eq, order, range) → execute() » permet d'écrire un seul fixture `_make_fake_supabase_with_sims` réutilisable entre 14 tests. Capturer les calls `eq()` dans un dict `_captured` exposé sur le mock permet ensuite d'asserter en bloc « le filtre a bien été propagé à Postgrest » sans inspecter le SQL généré (qu'on ne contrôle pas).

### 2026-05-03 — US-095 Super-admin Bassira : voir toutes les organisations + interface admin

- **Statut** : passes:true (chantier M-multitenant-supabase, follow-up US-092 + US-093 + US-094).
- **Problème** : Amine est founder Bassira et doit pouvoir auditer TOUTES les organisations clientes (cross-tenant) sans avoir à ouvrir la console SQL Supabase à chaque inspection. RLS Postgres l'empêche par construction de voir hors de ses orgs côté frontend (et c'est volontaire — la sécurité multitenant ne dépend pas de la confiance dans le code Vue). Solution : exposer côté backend des endpoints `/api/admin/organizations*` gardés par un décorateur `@require_super_admin` + un flag frontend conditionnel pour révéler une entrée nav « Admin » et une section « Toutes les organisations » dans `AnalyticsView`.
- **Architecture** :
  - **Identification du super-admin** : variable d'environnement backend `BASSIRA_SUPER_ADMIN_EMAILS` (liste d'emails séparés par virgules, ex. `amine@ai-mpower.com,partner@ai-mpower.com`). Lue par le backend à chaque requête (pas au démarrage) pour permettre :
    1. Le monkeypatching pytest sans relancer Flask.
    2. La mise à jour live sur Coolify sans redémarrer le process.
  - **Pas de table DB** pour le MVP : 0 migration, 0 seed à maintenir, juste une env var Coolify modifiable en 30 secondes. Un scaling futur (multiples founders par groupe) se fera via une table `super_admins` dédiée — non bloquant aujourd'hui (Bassira a 1 founder).
  - **Service_role bypass RLS uniquement côté backend** : les endpoints super-admin utilisent `get_supabase_admin()` (singleton US-092) pour requêter les tables sans filtre RLS. La clé `SUPABASE_SERVICE_ROLE_KEY` reste strictement côté serveur — jamais exposée au frontend, jamais loggée.
  - **Zero-trust côté frontend** : le store Pinia `auth.js` charge `is_super_admin` via `/api/admin/me/super-status`, MAIS la décision d'autorisation reste 100 % côté serveur. Un user qui forcerait `isSuperAdminFlag = true` côté JavaScript verrait la nav « Admin », clickerait sur `/admin/analytics`, mais recevrait 403 `NOT_SUPER_ADMIN` à chaque tentative de fetch. Pas de leak — le frontend ne fait que cacher l'UI inutile.
- **Modules backend créés/modifiés** :
  - `backend/app/auth/decorators.py` : ajout helper `_super_admin_emails()` (parse env), `is_super_admin_email(email)` (testable en isolation), décorateur `@require_super_admin` (compose `@require_auth` + check whitelist + log audit hash sha256 court — JAMAIS l'email en clair). Codes d'erreur : 401 MISSING_AUTH/INVALID_TOKEN, 403 NOT_SUPER_ADMIN, 503 SUPER_ADMIN_NOT_CONFIGURED (whitelist vide ou absente).
  - `backend/app/auth/__init__.py` : exporte `require_super_admin` + `is_super_admin_email`.
  - `backend/app/api/admin.py` : import des décorateurs auth + `get_supabase_admin`. 3 nouveaux endpoints :
    - `GET /api/admin/me/super-status` (`@require_auth` seulement — un user normal reçoit `{is_super_admin: false}`, pas une 403).
    - `GET /api/admin/organizations` (`@require_super_admin`). Lit `public.organizations` ordonnée par `created_at DESC`, puis enrichit chaque org avec `_aggregate_org_stats()` (simulations_count + published_count + avg_brier depuis `simulation_ownership`) et `_count_org_members()` (count exact sur `org_members`). Robustesse : toute erreur Supabase per-org → stats à `None` plutôt que 500 (l'opérateur préfère `—` à un brick).
    - `GET /api/admin/organizations/<org_id>` (`@require_super_admin`). Retourne `{organization, members, simulations}`. Pour les emails des members : on tente `cli.auth.admin.get_user_by_id(user_id)` sur le client supabase-py, et on retombe à `email: null` si l'API admin n'est pas dispo (variation SDK). 404 si org_id inconnu.
  - `backend/tests/test_unit_openapi.py` : ajout des 3 routes super-admin à `_UNDOCUMENTED_ALLOWLIST` (elles sont internes-only, pas dans le contrat OpenAPI public).
- **Modules frontend créés/modifiés** :
  - `frontend/src/api/client.js` : ajout 3 méthodes `fetchSuperStatus()`, `fetchAllOrganizations()`, `fetchOrganizationDetail(orgId)` qui réutilisent l'axios bearer-injecté.
  - `frontend/src/stores/auth.js` : ajout state `isSuperAdminFlag` + `superAdminLoaded`, getter `isSuperAdmin`, action `fetchSuperStatus()` (fail-soft : 401/5xx/network → `false`, jamais d'exception bubble). Hook dans `init()` (boot avec session existante), `login()` (après fetchProfile), `logout()` (purge), et listener `SIGNED_OUT` (purge).
  - `frontend/src/components/AppHeader.vue` : ajout entrée nav `<router-link to="/admin/analytics">` avec class `app-header__link--admin` conditionnelle sur `isAuthenticated && isSuperAdmin`. Style : pastille discrète qui passe en `--wi-primary` au hover (signal de pouvoir cross-tenant sans crier).
  - `frontend/src/views/AnalyticsView.vue` : ajout section `analytics-superadmin` (table 10 colonnes : slug · name · sector · country · status · members · sims · published · avgBrier · createdAt) + modal `analytics-org-modal` (drill-down détail au click sur une row). Au mount, si `authStore.isAuthenticated`, on appelle `fetchSuperStatus()` puis `loadAllOrganizations()` si super-admin. Format Brier : `Number(b).toFixed(3)`. Format date : `iso.slice(0, 10)` UTC. Click outside modal → close.
  - `frontend/src/locales/{fr,en,ar}.json` : ajout `nav.admin` + `nav.adminTitle` + namespace complet `analytics.superAdmin.{sectionTitle, sectionHelp, loading, error, empty, table.*, detail.*}`. Trad arabe formelle (وحدة تحكم المشرف الرئيسي لبصيرة).
- **Tests créés (28 nouveaux)** : `backend/tests/test_unit_admin_organizations.py` :
  - `TestIsSuperAdminEmail` (8 tests) : whitelist vide / unset / présent / absent / case-insensitive / strip whitespace / None / non-string.
  - `TestRequireSuperAdmin` (6 tests via `/api/admin/organizations`) : no-token 401 / invalid-token 401 / email-not-whitelist 403 / whitelist-unset 503 / whitelist-empty 503 / super-admin-allowed 200.
  - `TestSuperStatusEndpoint` (4 tests) : no-token 401 / not-whitelist false / whitelist true / no-whitelist false (sans erreur).
  - `TestListAllOrganizations` (5 tests) : empty / single-org-with-stats (vérifie members_count, sims_count, published_count, avg_brier=0.25 ignoré-None) / supabase-misconfigured 503 / select-failure 500 / normal-user 403.
  - `TestGetOrganizationDetail` (5 tests) : no-token 401 / normal-user 403 / org-not-found 404 / detail-with-members-and-sims (verifie email=None quand auth.admin pas dispo) / supabase-config 503.
- **Quality gates** :
  - `cd backend && uv run pytest tests/test_unit_admin_organizations.py -v` → **28 PASS** en 2,52 s.
  - `cd backend && uv run pytest -q` → **791 passed, 17 skipped, 0 régression** (vs 763 baseline US-092, +28 nouveaux).
  - `cd frontend && npm run build` → **OK**, 836+ modules. Aucune erreur, aucun warning nouveau (1 warning chunk size pré-existant).
- **Décisions architecturales notables** :
  - **Lecture de l'env var à chaque requête** (pas au démarrage Flask) : permet à Amine de modifier la liste sur Coolify et de voir l'effet au prochain request — sans `restart` du service. Coût négligeable (un `os.getenv` + un `split`).
  - **Composition de décorateurs `@require_super_admin` = `@require_auth` + check email** : on n'expose pas un super-admin sans JWT valide. L'attaquant qui poserait un email super-admin dans un faux header `X-Email` ne passerait pas — le décorateur lit `g.current_user['email']` issu des claims JWT vérifiés par `verify_supabase_jwt`.
  - **Log d'audit minimal sur denial** : on log `email_hash=<sha256[:8]>` au lieu de l'email en clair. Permet à un opérateur de corréler des tentatives répétées (même hash = même attaquant) sans fuiter la PII dans les logs Coolify.
  - **Fail-soft sur le frontend `fetchSuperStatus`** : 401 / 5xx / network → `isSuperAdminFlag=false`. Pas d'exception bubble qui briquerait la session. L'utilisateur verra simplement l'app comme s'il n'était pas super-admin (les endpoints renverront 403 si quelqu'un force).
  - **Modal détail vs nouvelle vue** : on a choisi un modal in-place plutôt qu'une route dédiée `/admin/organizations/<id>` côté frontend pour réduire la complexité (aucune nouvelle route Vue Router à enregistrer, drill-down expand/collapse familier). Le backend expose bien une route REST `<org_id>` standard, c'est juste l'UX frontend qui a choisi un modal.
  - **Stats agrégées calculées côté backend** : `simulations_count`, `published_count`, `avg_brier` sont calculées en Python à partir d'un SELECT sur `simulation_ownership`. Pour 100 orgs avec 1000 sims chacune (100k rows), c'est encore acceptable (~200ms). Au-delà, on basculera sur des SQL `count(*) FILTER (WHERE is_published)` agrégés ou une VIEW matérialisée. Pas de prematurè optimization.
  - **Routes super-admin dans l'allowlist OpenAPI** : ce ne sont pas des endpoints publics tiers, ils sont gardés par une whitelist email côté serveur. L'OpenAPI spec ne les documente pas — elles sont volontairement opaques pour des consommateurs externes (Cursor, Claude Desktop, partenaires API). Le test `test_unit_openapi.py` les passe en allowlist pour ne pas régresser.
- **Action Coolify (à faire par Amine)** :
  ```
  BASSIRA_SUPER_ADMIN_EMAILS=<email_signup_supabase>
  ```
  À poser sur le service `bassira-backend` (anciennement `miro-shark`) avec l'email exact qu'il a utilisé pour signup côté Supabase Auth. Tant que l'env var est vide / absente, **aucun super-admin n'existe** (tout `/api/admin/organizations` retourne 503 SUPER_ADMIN_NOT_CONFIGURED, et `/me/super-status` retourne `is_super_admin=false`). Stratégie « safe-by-default » : pas de super-admin par accident en dev local.
- **Apprentissage clé** : le pattern « super-admin via env var + helper testable + décorateur composé » permet à un projet multitenant qui n'a pas encore besoin d'une UI gestion-des-rôles complète d'avoir un super-admin opérationnel en 200 lignes de code (backend + frontend) avec coverage tests proche de 100 %. La mise à l'échelle (passage env-var → table DB) est triviale plus tard car le seul point d'extension est `_super_admin_emails()` qui peut faire un `cli.table('super_admins').select(...)` quand le besoin se présente.

### 2026-05-03 — US-094 AppHeader.vue partagé sur toutes les pages
- **Statut** : passes:true (chantier N-nav-globale, follow-up US-087 + US-093).
- **Problème** : la nav header n'existait que dans `Home.vue` (`.navbar`) et `LandingView.vue` (`.lp-topbar`). Les 14+ autres routes (`/models`, `/calibration`, `/offres`, `/devis`, `/partenaires`, `/explore`, `/verified`, `/models/:slug`, `/login`, `/signup`, `/client/dashboard`, `/process/:id`, `/simulation/:id`, `/report/:id`, `/interaction/:id`, `/replay/:id`, `/compare`, `/embed/:id`, `/admin/analytics`) tombaient sur un écran sans nav, sans logo Bassira, sans accès aux Modèles/Offres/Login. Amine demande explicitement « Menu qui doit être dans toutes les pages ».
- **Fichiers créés** :
  - `frontend/src/components/AppHeader.vue` (310 lignes) : composant Vue 3 `<script setup>` avec brand router-link "/", 6 nav links (Accueil · Modèles featured · Calibration · Offres · Partenaires · Contact), login adaptatif Pinia (`storeToRefs(authStore).isAuthenticated`), bouton Relancer la visite guidée (CustomEvent `bassira:reopen-tour`), ThemeSwitcher + LanguageSwitcher intégrés. Sticky top, backdrop blur 10px, `z-index: var(--ms-z-floating-lang)` (1500) pour passer au-dessus des modals. Animation `app-header-fadein` 480ms. Tokens `--wi-*` exclusifs (zéro hex hardcodé sauf valeurs fallback identiques aux tokens). RTL via `inset-inline-*` / `padding-inline-*` / `inset-block-*` exclusifs — jamais `left/right/top/bottom`. Responsive : nav links horizontalement scrollable (overflow-x:auto, scrollbar masquée) jusqu'à 540px où le wrap-flex passe les links sur une ligne dédiée.
- **Fichiers modifiés** :
  - `frontend/src/App.vue` : ne contient plus que `<AppHeader />` + `<router-view />` + `<DebugPanel />`. Tout le `<script setup>` (computed restartLabel, async restartTour, imports ThemeSwitcher/LanguageSwitcher) supprimé — déplacé dans AppHeader.vue. CSS global tokens/reset/scrollbar/animations préservé intégralement, seuls les blocs `body .lang-switcher--floating`, `@keyframes lang-switcher-fadein`, `.restart-tour-btn` et leurs media queries reduced-motion sont retirés (ces éléments vivent désormais dans AppHeader).
  - `frontend/src/views/Home.vue` : retrait complet de la `<nav class="navbar">` (50 lignes) y compris les 7 router-link et le bouton ⚙. Le bouton ⚙ Paramètres (admin-only, ouvre SettingsPanel pour config LLM) est déplacé en `<button class="home-settings-trigger">` flottant bottom-left, opacité 0.25 au repos, 1 au hover, rotation 40deg au hover. CSS `.navbar / .nav-brand / .nav-links / .nav-link / .nav-link--featured / .nav-link-action / .settings-btn / .compass / .arrow / .legacy-explore-link-removed / .legacy-github-link-removed` supprimés (≈90 lignes CSS retirées). Imports `useAuthStore` + `storeToRefs` retirés du script (devenus inutiles). SettingsPanel et OnboardingTour préservés.
  - `frontend/src/views/LandingView.vue` : retrait complet de `<header class="lp-topbar">` avec `.lp-nav` (38 lignes template). CSS `.lp-topbar / .lp-brand / .lp-nav / .lp-nav-link / .lp-nav-link--featured / .lp-nav-cta` + media query mobile supprimés (≈60 lignes CSS retirées). Imports `useAuthStore` + `storeToRefs` retirés. La `.lp-footer-nav` au footer est préservée (différente de la top-bar).
  - `.ralph/prd.json` : entrée US-094 ajoutée (passes:true, dependencies US-087+US-093).
- **Override CSS non-scoped dans AppHeader.vue** : ThemeSwitcher.vue et LanguageSwitcher.vue posent `position: fixed` en `<style scoped>` (avec attribut `[data-v-*]` spécificité 0,1,1) pour rester floating sur les routes sans header. Pour les neutraliser à l'intérieur du nouveau header sticky, AppHeader.vue ajoute un second bloc `<style>` (non-scoped) qui sélectionne `.app-header .lang-switcher` et `.app-header .theme-switcher` en spécificité 0,2,0 — donc bat la spécificité scoped sans `!important`, conformément à la règle US-016 (« jamais d'!important »).
- **i18n** : aucune nouvelle clé. Toutes les clés `nav.{brand,home,homeTitle,models,modelsTitle,calibration,calibrationTitle,offers,offersTitle,partners,partnersTitle,contact,contactTitle,login,loginTitle,dashboard,dashboardTitle}` existaient déjà dans `frontend/src/locales/{fr,en,ar}.json` (US-087 + US-093). Les libellés du bouton restart-tour restent in-component (3 langues) comme dans App.vue d'origine — convention qui évite de polluer le namespace global pour 3 strings techniques.
- **Quality gates** :
  - `cd frontend && npm run build` → **OK 8,70s**, 836 modules. Aucune erreur, aucun warning nouveau (1 warning chunk size pré-existant sur stress-test-politique-Bzn9Gue8.js).
  - Aucun sélecteur `.navbar / .lp-topbar` dans `frontend/tests/` — pas d'adaptation Playwright nécessaire.
  - Tokens vérifiés présents dans `design-tokens.css` : `--wi-bg / --wi-on-bg / --wi-surface / --wi-surface-container-low / --wi-on-surface-variant / --wi-primary / --wi-primary-soft / --wi-on-primary / --wi-outline-variant / --wi-radius-pill / --wi-radius-md / --wi-space-sm / --wi-space-md / --wi-font-heading / --wi-font-body / --ms-z-floating-lang / --ms-transition / --ms-ease / --ms-font-mono`.
- **Décisions architecturales** :
  - **Header dans App.vue (avant router-view)** plutôt que dans chaque vue : garantit la présence sur les 17 routes existantes ET sur toutes les routes futures sans toucher aux vues. Coût : impossible de masquer la nav sur certaines vues spéciales (ex. embed view, future page splash) ; si besoin futur, on ajoutera un `meta.hideHeader` sur la route + un `v-if="!route.meta?.hideHeader"` autour de `<AppHeader />`.
  - **z-index 1500 (var(--ms-z-floating-lang))** identique à celui que portait LanguageSwitcher floating : conserve le comportement existant (header au-dessus des modals à 1000-1200) sans refonte du système de z-index. Cohérent avec le pattern « le menu de navigation est toujours accessible ».
  - **Bouton ⚙ Paramètres** déplacé hors nav publique : c'est un trigger admin/dev (config LLM via SettingsPanel) qui n'a aucune valeur pour un visiteur cold sur `/models` ou `/calibration`. Il reste accessible sur `/` via un trigger flottant bottom-left à opacité 0,25 (visible discrètement pour qui sait, invisible pour les autres) — l'admin futur (US-088+) basculera ce trigger derrière `meta.requiresAdmin`.
- **Apprentissage clé** : extraire un composant partagé est l'occasion de réconcilier 2 implémentations divergentes (Home.vue `.navbar` orientée tokens `--ms-*` vs LandingView.vue `.lp-topbar` orientée tokens `--wi-*`). On a tranché pour `--wi-*` exclusifs (cohérent avec la roadmap Causse Warm Intelligence US-066 → US-085) et abandonné le namespace `--ms-*` pour la nav. Ce type de consolidation post-hoc est plus rapide quand on l'aborde comme une **extraction** (déplacer le code existant vers un composant) plutôt qu'une **réécriture** (créer from scratch un nouveau header) : on garde la mémoire de design (entrée Modèles featured US-087, login adaptatif US-093) sans avoir à les redécouvrir.

### 2026-05-03 — US-092 Backend Flask : middleware JWT Supabase + extension ownership multitenant

- **Statut** : passes:true (chantier M-multitenant-supabase, follow-up US-091).
- **Modules créés** :
  - `backend/app/auth/jwt_verifier.py` — `verify_supabase_jwt(token)` HS256 + cache LRU TTL 5min (256 entrées, TTL borné par exp). Lève `InvalidTokenError` (exception spécifique au module pour ne pas leak les internals PyJWT).
  - `backend/app/auth/supabase_client.py` — singleton `get_supabase_admin()` (service_role) + helpers `get_user_orgs`, `get_user_role_in_org`, `record_simulation_ownership`, `get_simulation_owner`, `mark_outcome`, `publish_simulation`, `get_public_calibration_aggregates`. Hiérarchie `ROLE_RANK = {viewer:1, member:2, admin:3, owner:4}` + `role_meets_minimum()`.
  - `backend/app/auth/decorators.py` — `@require_auth`, `@require_org_membership(role_min)`, `@require_owner_or_admin` (alias). Multi-org : sélection via `X-Org-Id` header ou `?org_id=` query param ; auto-select si 1 seule org. Codes d'erreur API : 401 MISSING_AUTH/INVALID_TOKEN, 403 NOT_A_MEMBER/ROLE_TOO_LOW/FORBIDDEN_ORG, 404 ORG_NOT_FOUND_FOR_USER, 400 ORG_ID_REQUIRED, 503 SUPABASE_NOT_CONFIGURED/AUTH_NOT_CONFIGURED.
  - `backend/app/api/client.py` — 5 endpoints `/api/client/*` (auth/me, simulations GET/POST, outcome, publish).
- **Modules modifiés** :
  - `backend/app/services/simulation_manager.py` — `create_simulation(org_id?, created_by?, package_id?)` (rétro-compat : sans `org_id`, aucun appel Supabase) + `list_simulations_for_org(org_id)` (hydratation filesystem défensive — `status="missing"` si dossier absent) + `is_user_authorized_to_read(simulation_id, user_id)` (sim sans ownership = publique legacy ; sinon membership requis ; fail-closed sur erreur Supabase).
  - `backend/app/api/calibration.py` — endpoint public `GET /api/calibration/aggregates` lit la VIEW k-anonymity n>=5.
  - `backend/app/__init__.py` — register `client_bp` au prefix `/api/client`.
  - `backend/pyproject.toml` — ajout `pyjwt[crypto]>=2.10.0` (déjà dans uv.lock via dépendance transitive) et `supabase>=2.7.0` (nouvelle dep).
- **Tests créés (63 nouveaux)** :
  - `tests/test_unit_auth_jwt.py` (33 tests) : `verify_supabase_jwt` valide / expiré / signature KO / malformé / sub manquant / secret backend manquant / cache hit / cache purge expiré ; `@require_auth` no-token / malformed-header / invalid / valid / cookie fallback / secret unset 503 ; `@require_org_membership` no-orgs / single-auto-select / multi-no-hint / X-Org-Id / ?org_id= / unknown-org / role-too-low / supabase-config-missing ; `@require_owner_or_admin` member-rejected / admin-passes / owner-passes ; `role_meets_minimum` hiérarchie complète.
  - `tests/test_unit_client_simulations.py` (19 tests) : 5 endpoints client × scénarios (no-token, missing-fields, member-rejected, invalid-label/brier, not-owned-404, wrong-org-403, admin-marks-OK, owner-publishes-OK, etc.) + `/api/calibration/aggregates` no-auth + supabase-misconfigured-fail-soft.
  - `tests/test_unit_simulation_manager_ownership.py` (11 tests) : rétro-compat sans org_id (pas d'appel Supabase, vérifié par `MagicMock.side_effect=AssertionError`) ; org_id triggers ownership recording ; supabase-failure-doesnt-break-creation (fail-soft) ; `is_user_authorized_to_read` 5 cas (unowned-public, in-org-OK, not-in-org-rejected, supabase-error-fail-closed, missing-org_id-rejected) ; `list_simulations_for_org` (missing-filesystem, hydratation-OK, empty-org).
- **Quality gates** :
  - `cd backend && uv run pytest tests/test_unit_auth_jwt.py` → **33 PASS** en 15,08 s.
  - `cd backend && uv run pytest tests/test_unit_simulation_manager_ownership.py` → **11 PASS** en 12,33 s.
  - `cd backend && uv run pytest tests/test_unit_client_simulations.py` → **19 PASS** en 3,37 s.
  - `cd backend && uv run pytest -q` → **763 passed, 17 skipped, 0 régression** (vs 700 baseline US-090, +63 nouveaux).
- **Décisions architecturales notables** :
  - **HS256 par défaut** pour Supabase Auth (la clé `SUPABASE_JWT_SECRET` est le secret partagé HS256 visible dans le dashboard Supabase Settings → API → JWT Settings). On accepte l'absence de claim `aud` pour rester compatible avec d'éventuels tokens custom.
  - **Cache JWT TTL borné par `exp`** : on ne risque jamais de servir un token plus longtemps que sa durée de vie effective (TTL plafonné à `min(now+5min, exp-5s)`).
  - **Politique de log** : aucun JWT, aucun header `Authorization` jamais loggué (cf rules/supabase.md). Les exceptions PyJWT sont catégorisées par classe (`exc.__class__.__name__`) sans payload.
  - **Singleton Supabase admin** : protégé par lock (multi-thread Flask). Helper `reset_supabase_admin()` exposé pour les tests.
  - **Rétro-compatibilité forte** : `create_simulation()` sans `org_id` reste strictement filesystem-only — pas d'écriture Supabase. Vital pour les modèles publics `/models/<slug>` et `/explore` qui n'ont pas d'org propriétaire.
  - **Fail-soft sur /api/calibration/aggregates** : si Supabase est misconfiguré (dev local sans secret), retour `200 {data: []}` au lieu de 503. La page calibration v2 s'affichera vide, mais ne brique pas le frontend en environnement de développement.
  - **Fail-closed sur is_user_authorized_to_read** : toute erreur Supabase = `False` (jamais d'autorisation accidentelle).
  - **Idempotence ownership** : `record_simulation_ownership` swallow l'erreur duplicate-key (23505) — la sim peut déjà avoir une ligne ownership sans que cela soit une erreur.
  - **Mocks pytest** : aucune dépendance live à Supabase. Les helpers prennent un `client=` injectable, et les tests monkeypatchent soit `app.auth.supabase_client.<helper>` soit le module `app.api.client.<helper>` selon la cible (les imports `from … import` créent des aliases locaux qui doivent être patchés au point d'usage). C'est le pattern standard de monkeypatching pour les modules Python — à reproduire pour US-093+.
- **Apprentissage clé** : le pattern « décorateur factory + alias » (`require_org_membership(role_min)` + `require_owner_or_admin = require_org_membership(role_min="admin")`) garde l'extension future ouverte (on pourra ajouter `require_owner_only` sans toucher la base) tout en exposant des alias lisibles dans les routes. La hiérarchie de rôles est isolée dans `supabase_client.role_meets_minimum()` pour pouvoir être testée en pur Python sans dépendance Flask, et réutilisée par `is_user_authorized_to_read`.

### 2026-05-03 — US-090 Vitrine /models — productivisation des 13 templates restants
- **Statut** : passes: true (chantier L-models-pdf-brief, follow-up US-086 + US-088 + US-089). 18 modèles publiés au total, 54 PDFs générés en FR/EN/AR.
- **13 templates productivisés** : adcheck-pre-launch, budget-loi-finances, campus-controversy, implantation-startup, corporate-crisis, crypto-launch, historical-whatif, pmf-startup-tech, political-debate, primaires-parti-politique, product-announcement, product-launch, she-start-cohort.
- **Schéma JSON** : strictement identique à fusion-bancaire-mena (slug, sector, preset_source, title fr/en/ar, subtitle, summary_short, context_long, decision_question, agents_simulated [role_key + profile fr/en/ar], key_insights, brier_illustrative entre 0,20 et 0,24, tags, cta_label, use_cases_decisionmakers).
- **Frontend** :
  - `ModelsListView.vue` et `ModelDetailView.vue` refactorés en `import.meta.glob('../models/*.json', { eager: true })` avec tri par priorité sectorielle. Les 18 fichiers JSON sont découverts à build-time sans liste hardcodée à maintenir.
  - `ModelDetailView.vue` : ajout de `agentRoleLabel(roleKey)` qui fait fallback en libellé snake_case→CapitalizedWords si la clé i18n est absente. Ce comportement préserve la lisibilité utilisateur quand on ajoute un nouveau modèle dont les agents ont des role_key inédits.
  - `MODEL_TO_SITUATION` étendu pour mapper les 13 nouveaux slugs sur crisis|policy|campaign (cohérent avec les 3 radios de QuoteView).
  - CSS `--ml-sector-pill` et `--md-sector-pill` étendu pour 7 nouvelles familles (communication, politique-publique, marketing-export, startup-tech, crypto, histoire-contrefactuel, education) et 1 famille additionnelle (programme-entrepreneurial pour future extension). Toutes dérivent des tokens `--wi-*` existants pour conserver la palette Causse Warm Intelligence.
  - Locales `fr.json`, `en.json`, `ar.json` étendues sur `models.cards.sector.*` avec libellés institutionnels (FR : « Marketing & Export », « Startup & Tech », « Histoire & Contrefactuel », « Éducation & Recherche »…). En arabe : terminologie standard MENA, registre formel.
- **Backend** :
  - `backend/app/models_data/` synchronisé strictement : 13 nouveaux JSON identiques à frontend (vérifié `diff` vide × 18 paires).
  - `backend/tests/test_models_pdf.py` : `_SLUGS` étendu de 5 à 18. Le test paramétré matrice 18×3 = 54 entrées × 5 assertions chacune (status / content-type / disposition / magic-bytes / size) génère 270 paramétrés ; total 277 paramétrés PASS.
- **DEFCON 1 strict** :
  - Aucun nom propre d'individu réel dans les 13 nouveaux JSON. Influenceurs, dirigeants, journalistes, candidats sont tous formulés génériquement (ex : « influenceur food halal francophone de l'ordre du million d'abonnés », « parlementaire de l'opposition », « directrice de campagne »).
  - Aucun nom de produit ou société fictif présenté comme acteur du scénario (DataVault, NeuralCoin, Whitfield, OmniTech Aria, BioSynth AI, Diagno AI…) — uniquement archétypes (« scale-up cloud archétypale », « token IA archétypal », « université privée de premier rang », « grand groupe technologique »).
  - Aucune référence légale numérotée non vérifiée. Quand pertinent : « loi bancaire 103-12 » (déjà DEFCON 1 OK US-089), « cadre RGPD » générique, « PSD2 ou équivalents régionaux ».
  - Aucun chiffre précis non sourcé. Quand pertinent, plages réalistes (« 25 à 35 % », « 4 à 8 points », « 25 % des trajectoires ») sans valeur ponctuelle inventée.
  - Sources publiques institutionnelles citées : Bank Al-Maghrib, AMMC, GPBM, CGEM, UMT, AFEM, AMDIE, DIFC Authority, Kenya Investment Authority, AVCA, Partech Africa, ARCOM, HACA, CNIL, CNDP, GSMA, Inside Higher Ed, Chronicle of Higher Education, Times Higher Education, CASE, NACAC, CoinGecko, CoinMarketCap, SEC, ESMA, AMF, FINMA, VARA, FATF Travel Rule, ANAPEC, GEM Morocco, CSA Research, NielsenIQ Tech, Counterpoint Research, TelQuel, Hespress, Le360, Africa Report, Jeune Afrique. Toutes sont des institutions / publications publiques réelles.
- **Fichiers** : 26 JSON nouveaux ou réécrits (13 paires frontend+backend) + 4 fichiers infra (ModelsListView.vue, ModelDetailView.vue, 3 locales i18n, test_models_pdf.py).
- **Quality gates** :
  - `diff frontend/src/models/<slug>.json backend/app/models_data/<slug>.json` → vide pour les 18 paires.
  - `cd backend && uv run pytest tests/test_models_pdf.py -v` → **277 paramétrés PASS** en 20,8 s.
  - `cd backend && uv run pytest tests/` → **700 passed, 17 skipped, 0 régression** (vs 505 baseline US-088, +195 = 13 nouveaux slugs × 3 langues × 5 assertions).
  - `cd frontend && npm run build` → OK en 13,82 s (1 warning chunk size pré-existant).
  - **Vérification DEFCON 1 textuelle** (scan Python sur 36 fichiers : 18 JSON × 2 + scan automatisé) : 0 chaîne interdite parmi 35+ patterns interdits.
  - **Vérification DEFCON 1 PyMuPDF** sur les 54 PDFs régénérés : 0 chaîne interdite.
  - 54 PDFs régénérés via `uv run python scripts/generate_demo_pdfs.py` (FR ≈ 10,7-11,9 KB, EN ≈ 10,4-11,3 KB, AR ≈ 56,3-58,0 KB avec fonte arabe Tahoma embedded).
- **Pattern de génération neutre — règles appliquées systématiquement aux 13 modèles** :
  - **Aucun nom propre individuel** : les agents ont un `role_key` descriptif (ex : `core_audience_persona`, `crypto_influencer`, `regional_activist`) et un `profile` qui décrit la fonction sans nommer l'individu.
  - **Aucun nom propre fictif d'organisation présentée comme acteur du scénario** : tous les acteurs simulés sont génériques (« un grand groupe technologique », « une scale-up cloud », « un grand parti politique structuré »). Les institutions publiques réelles citées le sont uniquement comme **source de calibration** (« sources : Bank Al-Maghrib, GPBM, presse économique »), jamais comme partie prenante du scénario.
  - **Toute opération M&A / institution sectorielle citée** est vérifiée : Tamwilcom, Intelaka, Damane Express (CCG-Tamwilcom Maroc), AVCA, Partech Africa Tech, AMDIE, DIFC, Kenya Investment Authority sont tous des programmes / institutions publiques réelles.
  - **Plages réalistes plutôt que chiffres ponctuels inventés** : « 25-35 % », « 4-8 points », « 30-50 % » plutôt qu'un nombre précis non sourcé.
  - **Tous les events historiques** sont présentés au conditionnel hypothétique (« simulation d'un what-if politique majeur ») ou comme dynamique archétypale (« crises archétypales du secteur ») — jamais nommément.
- **Apprentissage clé** : pour productiviser des templates rapidement avec rigueur DEFCON 1, le cadre cabinet conseil suivant fonctionne : (a) conserver le `role_key` du brief original mais réécrire complètement le `profile` en formulation générique, (b) résumer le contexte stratégique en abstrayant tous les noms propres, (c) calibrer les insights sur des plages plutôt que des points fixes, (d) citer les sources de calibration (institutions publiques réelles) sans les présenter comme parties prenantes. Cette discipline permet de produire 13 modèles en quelques heures sans introduire de claim factuel à risque.

### 2026-05-03 — US-089 Correction DEFCON 1 modèles publics — purge claims factuels non vérifiés
- **Statut** : passes: true (chantier L-models-pdf-brief, follow-up US-086/US-088).
- **10 corrections appliquées** :
  - **4 rouges** (faits vérifiés faux par WebSearch) : (1) Khalid Bouaza — influenceur introuvable dans tout classement food halal France/Maroc, sub-agent l'avait inventé → remplacé par formulation générique « influenceur food halal francophone de l'ordre du million d'abonnés » dans les 3 langues. (2) Circulaire BAM 26/G/2006 — vérifiée sur bkam.ma, son vrai sujet est Bâle II/III calcul fonds propres, PAS les acquisitions bancaires → remplacée par « loi bancaire n°103-12 du 24 décembre 2014 et ses circulaires d'application sur les prises de participation ». (3) « BMCI-BNP » — fusion inexistante (BMCI est filiale BNP Paribas depuis 2000, jamais fusionnée avec elle ; vraie opération en cours = BMCI × Crédit du Maroc Holmarcom 2026) → remplacé par « fusion BMCI × Crédit du Maroc (Holmarcom 2026), cession SGMB → Saham Bank (2024), fusion historique Attijari × Wafa Bank (2003-2004) ». Rôle agent `concurrent_credit_du_maroc` renommé `concurrent_panafricain` car Crédit du Maroc disparaît T4 2026 comme acteur indépendant. (4) INSEE 6,8 M Maghreb France — chiffre faux d'un facteur 3 (vrai chiffre INSEE 2024 ≈ 2,2 M nés au Maghreb sur 7,6 M immigrés totaux, 29 %) → remplacé par « ~2,2 M de personnes nées au Maghreb (INSEE 2024, immigrés) auxquelles s'ajoutent les descendants d'immigrés (INSEE Trajectoires et Origines) ».
  - **6 jaunes** (imprécisions) : (5) « CCC France » sigle non identifié → ARCOM (Autorité de régulation de la communication audiovisuelle et numérique). (6) Crises nominatives Carrefour Maroc 2018 / Inwi 2021 / Royal Air Maroc 2023 / Heineken / Boohoo / BrewDog présentées comme « documentées » sans source → remplacées par catégories d'industries génériques (grandes enseignes de distribution, opérateurs télécoms, transporteurs nationaux, secteur brasserie, retail textile). (7) « Maroc loi paiement 2018 » → loi bancaire 103-12 (2014) + directives BAM sur services de paiement (2018-2020). (8) « Nigeria CBN guidelines 2020 » → guidelines CBN sur paiements mobiles et monnaie électronique (2018-2021). (9) Sigle « BCB » ambigu en contexte UEMOA → CBN (Nigeria), CBRT (Turquie). (10) « Maroc Telecom Pension Fund rapports publics » non vérifiable → AVCA (African Private Capital Association) benchmarks publics + doctrine d'investissement publique de gestionnaires comme CDG Capital.
- **Fichiers** : 10 JSON (5 paires frontend/backend, identité préservée par `cp` après chaque édition + `diff` validé vide pour les 5).
- **Quality gates** :
  - `cd backend && uv run pytest tests/test_models_pdf.py -v` → **82 PASS** en 5.77 s.
  - `cd backend && uv run pytest tests/` → **505 passed, 17 skipped, 0 régression**.
  - `cd frontend && npm run build` → OK (1 warning chunk size pré-existant).
  - 15 PDFs régénérés via `uv run python scripts/generate_demo_pdfs.py` (FR/EN ≈ 10-11 KB, AR ≈ 56-58 KB avec Tahoma embedded).
  - **Vérification PyMuPDF** sur les 15 PDFs : 0 chaîne interdite parmi `['Khalid Bouaza', '26/G/2006', 'BMCI-BNP', '6,8 M', 'CCC France', 'Carrefour Maroc 2018', 'Inwi 2021', 'Royal Air Maroc 2023', 'Heineken', 'Boohoo', 'BrewDog', 'Maroc Telecom Pension Fund', 'Maroc loi paiement 2018']`. Présence vérifiée des nouvelles formulations FR clés (loi 103-12, Holmarcom, Saham Bank, 2,2 M, Trajectoires et Origines, ARCOM, CBN, CBRT, AVCA, CDG Capital).
- **Pattern à intégrer dans les briefs futurs** :
  - **Avant tout claim factuel dans un livrable client (PDF, JSON public, copy commerciale)** : vérifier source + date + chiffre via WebSearch ou source institutionnelle. Une formulation prudente sans nom propre vaut mieux qu'une affirmation précise non sourcée.
  - **Sub-agents générateurs de contenu narratif** ont une tendance documentée à inventer des noms propres « plausibles » (influenceurs, marques, sigles) pour donner de la consistance. **Règle implicite à imposer dans tout brief future** : aucun nom propre dans un livrable narratif sans source explicite citée dans le brief, sinon utiliser des formulations génériques (« influenceur de l'ordre du million d'abonnés », « grandes enseignes de distribution »).
  - **Identité frontend/backend pour les fichiers de référence** : workflow simple = éditer un côté, `cp` vers l'autre, `diff` à zéro. Ne jamais éditer les deux indépendamment.
- **Apprentissage clé** : la dette factuelle (claims faux dans des livrables client) est aussi grave qu'une dette technique. La règle DEFCON 1 (zéro tolérance données erronées) doit être systématiquement vérifiée avant tout export, et tout sub-agent qui génère du contenu factuel doit être briefé explicitement sur l'interdiction des noms propres non sourcés.

### 2026-05-03 — US-088 Backend `/api/models/<slug>/pdf-brief` (5 modèles × 3 langues)
- **Statut** : passes: true (chantier L-models-pdf-brief). Endpoint public, 4-6 pages A4 portrait, brandé Bassira qualité cabinet conseil, 15 PDFs prêts à imprimer pour le RDV C-level d'Amine cette semaine.
- **Fichiers** :
  - `backend/app/api/models.py` (+475 l) : blueprint `models_bp`, helpers `_load_model`/`_pick`/`_fmt_brier`/`_xml_safe`/`_shape_arabic`/`_ensure_arabic_font` + `_build_pdf` reportlab. Détection runtime fonte arabe (Tahoma Windows / NotoSansArabic / DejaVuSans Linux / `app/static/fonts/` bundlés) + shaping `arabic_reshaper` + bidi `python-bidi`.
  - `backend/app/__init__.py` : enregistrement `models_bp` à `/api/models` (3 lignes).
  - `backend/app/models_data/{fusion-bancaire-mena, crisis-drill-24h, allocation-fonds-strategique, stress-test-politique, lancement-diaspora-eu}.json` : 5 sources de vérité backend, schéma US-086 (slug, sector, preset_source, title fr/en/ar, subtitle, summary_short, context_long, decision_question, agents_simulated, key_insights, brier_illustrative, tags, cta_label, use_cases_decisionmakers).
  - `frontend/src/models/*.json` : 5 mirroirs identiques (sub-agent US-086 n'avait pas encore mergé sa worktree au moment du run, j'ai créé les JSON depuis les preset_templates et les ai partagés).
  - `backend/scripts/generate_demo_pdfs.py` : script standalone qui réutilise le test client Flask pour produire les 15 PDFs dans `backend/uploads/demo_pdfs/` (FR + EN ≈ 10-11 KB, AR ≈ 57 KB avec Tahoma embedded).
  - `backend/tests/test_models_pdf.py` (+220 l) : 82 tests paramétrés (matrice 5×3 sur status/content-type/disposition/magic bytes/size + 404/400/cache/RTL no-crash + brand string + page count 4-6 via PyMuPDF).
  - `backend/tests/test_unit_openapi.py` : ajout `models_bp → /api/models` dans `_BLUEPRINT_PREFIXES`.
  - `backend/openapi.yaml` : tag `Models` + path `/api/models/{slug}/pdf-brief` documenté complet (params slug + lang, 200/400/404).
  - `backend/pyproject.toml` : +`arabic-reshaper>=3.0.0` + `python-bidi>=0.4.2` (justification : sans shaping arabe le PDF AR est inutilisable — caractères non contextuels et ordre logique au lieu de visuel ; ces deux libs sont les standards pour reportlab + arabe).
- **Quality gates** :
  - `cd backend && uv run pytest tests/test_models_pdf.py -v` → **82 PASS** en 10.55 s.
  - `cd backend && uv run pytest tests/` (régression complète) → **505 passed, 17 skipped, 0 régression**.
  - 15 PDFs générés sans erreur via `uv run python scripts/generate_demo_pdfs.py`.
- **Décisions techniques** :
  - **reportlab plutôt que weasyprint+Jinja** : la spec brief mentionnait un template HTML mais l'instruction Étape 3 ordonnait explicitement la cohérence avec `pdf_export.py` US-024 et l'absence de nouvelle dépendance lourde. reportlab est déjà installé et utilisé pour le PDF de simulation — réutiliser le même mécanisme garantit (a) la cohérence visuelle de la stack PDF, (b) l'absence de régression sur le déploiement Coolify (weasyprint nécessite des libs système — pango/cairo/gdk-pixbuf — qu'on n'a pas voulu introduire pour un endpoint d'appoint).
  - **Détection runtime de la fonte arabe** : impossible de bundler Tahoma (license MS non redistribuable). Le code essaie 9 paths candidats (bundles internes en priorité, puis Linux, puis Windows, puis macOS). En prod Coolify il faudra `apt install fonts-noto-arabic` ou `fonts-dejavu` au runtime sur l'image Docker — TODO documenté dans le code mais non bloquant pour le RDV (Amine génère depuis Windows local).
  - **Shaping arabe explicite** : reportlab ne fait aucun shape RTL ni reordering bidi. `arabic_reshaper.reshape()` produit les formes contextuelles (ﺑ ﺒ ﺐ ﺑ), `bidi.algorithm.get_display()` réordonne logique→visuel. L'absence de l'une ou l'autre dégrade gracieusement (le texte reste lisible mais non shapé).
  - **Schéma JSON multilingue uniforme** : tous les champs textuels (title, subtitle, summary_short, context_long, decision_question, key_insights, cta_label, use_cases_decisionmakers, agents[].profile) sont des dicts `{fr, en, ar}`. Helper `_pick(field, lang)` extrait avec fallback FR puis EN puis "". Cela permet l'extension future (ajout d'une 4ème langue) sans toucher au PDF generator.
  - **Branding qualité cabinet** : palette Causse Warm Intelligence stricte (#FF8551 orange / #006D44 mint / #FAF7F2 cream / #241915 charcoal / #A13F0F terracotta), top accent bar 4mm orange, footer 1.5mm terracotta + ribbon « Document confidentiel · Usage professionnel » + texte localisé « Page X / Bassira · بصيرة ». Encadrés couleur : decision question (terracotta soft #FFF3EE), méthodologie (mint soft #E8F4EF), CTA (terracotta soft + center-aligned).
  - **Pages 4-6** : couverture + decision/contexte + agents/méthodologie + insights/use cases + disclaimer/CTA = 5 pages effectives (vérifié par PyMuPDF dans `test_pdf_contains_bassira_brand`).
  - **DEFCON 1 chiffres** : aucun chiffre Brier réel inventé. Les 5 modèles ont des `brier_illustrative` documentés comme tels, et la méthodologie dans le PDF mentionne explicitement « calibration en cours de constitution sur les modèles publiés en 2026 ». Les sources citées (Bank Al-Maghrib, BCEAO, INSEE, NielsenIQ, AVCA, GPBM, LSA, Linéaires, Africa Report, TelQuel, FoodService Vision, IRESEN, OCP) sont toutes des institutions ou publications publiques réelles — aucune affirmation factuelle nouvelle n'est faite à leur sujet, juste qu'elles sont des sources publiques de calibration.
- **Ce qui a basculé en cours de route** :
  - Première version sans shaping arabe : PDFs AR 9 KB avec caractères non shapés et ordre logique → inutilisable. Détecté en inspectant un PDF avec PyMuPDF. Ajout `arabic-reshaper` + `python-bidi` + détection fonte → PDFs AR 57 KB avec rendu correct (vérifié visuellement sur l'extraction PyMuPDF : `Bassira · ﺑﺼﻴﺮﺓ ﺻﻔﺤﺔ 1` rend bien).
  - Test test_unit_openapi `test_flask_routes_are_documented_or_allowlisted` ne plantait pas avec un blueprint inconnu (il skip silencieusement les bps non mappés) — mais pour propreté j'ai ajouté `models_bp → /api/models` dans `_BLUEPRINT_PREFIXES` ET la spec dans `openapi.yaml` (tag Models complet avec params + responses). Cela garantit que les futurs endpoints `/api/models/...` ne dérivent pas silencieusement.
- **Pour Amine — récupération immédiate des PDFs RDV** :
  - Chemin : `C:/Users/amans/OneDrive/Projets/MiroShark/backend/uploads/demo_pdfs/`
  - 15 fichiers : `bassira-modele-<slug>-<lang>.pdf` (5 slugs × 3 langues)
  - Slugs : `fusion-bancaire-mena` · `crisis-drill-24h` · `allocation-fonds-strategique` · `stress-test-politique` · `lancement-diaspora-eu`
  - Régénération en 1 commande : `cd backend && uv run python scripts/generate_demo_pdfs.py`
- **Apprentissages pour futures sessions** :
  - reportlab + arabe = piège silencieux. Toujours tester l'extraction PyMuPDF pour vérifier le rendu visuel, pas juste `len(resp.data) > N`.
  - Pour un endpoint qui ressemble à un duplicate (deux générateurs PDF dans la même app), valoriser la cohérence en réutilisant les mêmes helpers/styles plutôt que dupliquer reportlab boilerplate. Les `_COLOR_*` du brief sont identiques aux constantes US-024.
  - Le pattern `_pick(field, lang)` + `_xml_safe(_localise(text))` est généralisable à tout futur endpoint qui doit produire du contenu multilingue avec shaping conditionnel.

### 2026-04-29 — Batch robustesse erreurs : US-047 + US-039 + US-040 + US-007
- **Statut** : passes: true sur les 4 stories — clôt le chantier 9-simulation-quality + le chantier 6-i18n-erreurs.
- **Déclencheur** : incident sim_cc793c9c99b5 où l'utilisateur voyait « Request failed with status code 400 » au lieu d'un message localisé au Step 03 « Génération de la configuration ». Le diagnostic a révélé une cause racine multi-étapes : graph Neo4j vide → /prepare échoue silencieusement → user clique Retry → POST 400 → frontend affiche err.message axios brut + un hint legacy mentionnant à tort OpenRouter (la prod tourne sur Moonshot kimi-k2 depuis la migration).
- **Stratégie** : 4 commits atomiques par story + 1 fix UX préalable.
  - **`2399f99` Step03-Fix** : hints contextuels Step 03 (entities/profiles/timeout/llm) + extraction err.response.data.error dans handleConfigRetry + locales fr/en/ar débrandées d'OpenRouter + admin US-038 passes:true.
  - **`7771bf0` US-047 backend** : fail-fast à /api/simulation/create — pre-check filtered_count > 0 via EntityReader, sinon 400 error_code=GRAPH_EMPTY. Pre-check non bloquant si Neo4j down. 5 tests hermétiques.
  - **`a8d9f99` US-039** : carte « Refine context » dépliable dans le workbench Step1 (5 champs : key_actors / geo_locale / time_horizon / key_tensions / expected_stakeholders). Defaults par template via détection keyword. Persistance localStorage. POST /api/graph/build avec refinement_only:true. 37 clés i18n × 3 langues.
  - **`c026fc5` US-040** : Step1.5 Review entities (rename/merge/delete/add). EntityRefiner class avec 4 ops Cypher en transaction unique. ReviewEntitiesView Vue avec group by type, rename inline, select merge, toggle delete. Banner orange dans MainView. 12/12 tests + 313/313 backend non-régression.
  - **`822b1f3` US-007** : 259 retours d'erreur structurés sur 50 codes uniques (4 fichiers backend). Helper formatApiError(error, t) avec fallback gracieux. 64 clés errors.* × 3 langues. 4 composants migrés (Step2EnvSetup, Step1GraphBuild, CalibrationView, ReviewEntitiesView). Backward-compat préservée. 11 nouveaux tests pytest.
  - **Final** : US-047 frontend (bouton Lancer disabled si graphStats.nodes === 0 + hint i18n disabledEmptyGraph + tooltip).
- **Tests cumulés** : 313 → 324 backend pytest passing (+11). Build frontend PASS sur tous les commits. Aucun rollback.
- **Pièges détectés** :
  - Coordination sub-agents multi-locales : 3 sub-agents qui touchent fr.json/en.json/ar.json en parallèle = race condition filesystem. Solution appliquée : séquentialité stricte (US-039 → US-040 → US-007), commit entre chaque pour partir d'une base propre.
  - Le sub-agent US-040 a dû toucher `backend/openapi.yaml` (non listé) car le test `test_flask_routes_are_documented_or_allowlisted` est strict — légitime, garder en tête pour les futures stories backend.
  - L'auto-deploy Coolify rebuild à chaque push, donc 5 cycles consommés. Acceptable mais à grouper davantage si pression budget.
- **Apprentissages pour futures sessions** :
  - Pour bug UX en prod, faire d'abord un curl `/api/<endpoint>/realtime` avant d'aller dans le code → expose le vrai message backend caché derrière la couche axios.
  - Quand on a un layer d'erreur multi-couches (axios → frontend hint → backend message → state.json), le pattern de débogage systématique est : trace le flow complet, identifie la couche qui ment ou dégrade, fix au bon niveau, ne JAMAIS patcher juste la couche visible.
  - Le pattern « Step 1.5 Review entities » (US-040) est généralisable : insérer une étape de validation utilisateur entre génération automatique LLM et opération downstream coûteuse → réduit les échecs en cascade.

### 2026-04-29 — US-045 + US-046 Calibration inbox (backend + frontend)
- **Statut** : passes: true (les deux stories) — débloque l'argument commercial /calibration en permettant à Amine de marquer ses sims existantes pour faire bouger le Brier sur la page publique.
- **Fichiers** :
  - `backend/app/api/calibration.py` : +`GET /api/calibration/simulations` (~250 l ajoutées), helpers `_read_simulation_config`, `_read_outcome_for_inbox`, `_build_summary_first_words`, `_resolve_template_name`, `_gather_evaluable_simulations`. Co-localisé avec le brier-score pour garder template_id / outcome / trajectory readers en un seul module.
  - `backend/tests/test_unit_calibration_simulations.py` : nouveau, 15 tests (filter pending/evaluated/all, template filter, private-sim exclusion, failed-status exclusion, missing-config degradation, sort order, HTTP-level smoke).
  - `frontend/src/views/CalibrationView.vue` : nouvelle `<section class="calib-evaluables">` ~470 l (template + script + scoped CSS) sous le block méthodologie/CTA.
  - `frontend/src/locales/{fr,ar,en}.json` : nouveau bloc `calibration.evaluables.*` (28 lignes par locale).
- **Quality gates** : `pytest 279 passed (15 new), 17 skipped` ; `npm run build` ✓ 5.77 s, CalibrationView-DaIL9u4o.js → 20.52 kB gzip 6.06 kB.
- **Commits** : `b07ec25` (US-045), `3dc3fb2` (US-046).
- **Endpoint shape** : `GET /api/calibration/simulations?status=pending|evaluated|all&limit=20&offset=0&template=<id>` → `{success, data: [{id, title, template_id, template_name, created_at, status, is_public, predicted_bullish_pct, outcome, outcome_url, summary_first_words}], pagination: {limit, offset, total, has_more}, filters: {applied: {status, template}}}`.
- **Décisions techniques** :
  - Status query param normalisé à `pending` sur valeur inconnue plutôt que 400 (UX : un bookmark stale ne casse pas la page).
  - Statuts éligibles : `completed`/`running`/`stopped`/`paused` (failed et created exclus — pas de prédiction à scorer).
  - `summary_first_words` = première phrase de `simulation_requirement` (split sur `. `/`! `/`? ` avec espace pour ne pas tronquer « U.S. »), fallback `title`, fallback `simulation_id`.
  - Sims sans `simulation_config.json` ni `trajectory.json` apparaissent quand même dans l'inbox avec champs minimums (id, title=id, status, predicted_bullish_pct=null) — l'opérateur peut au moins les ouvrir.
  - Bouton « N/A » côté frontend = no-op POST (pas de DELETE outcome.json côté backend) → toast success en 2 s sans toucher l'état serveur. Documenté dans le commit pour ne pas surprendre.
  - Optimistic UI : on mute la card côté Vue avant le POST, on revert sur `catch`.
  - Toast : CSS-only fade-in 200 ms + auto-dismiss 3 s (pas de toast lib ajoutée à la stack).
  - Après POST réussi en filter `pending`, la card est filtrée localement de la liste + `fetchData()` re-fetch /brier-score → big number Brier bouge en live sans full reload.
- **Auth posture** : `GET /simulations` est public (no token) — même posture que /brier-score, déjà documentée dans le module. Le `POST /outcome` reste gated par `MIROSHARK_ADMIN_TOKEN` côté backend ; le frontend l'appelle sans token comme le fait déjà EmbedDialog.vue, le déploiement gère ça via reverse-proxy.
- **Learnings** :
  - Réutiliser `_read_predicted_bullish_prob` (déjà dans calibration.py) pour la cohérence avec /brier-score : si le calcul change un jour, il change pour les deux endpoints d'un coup.
  - Cache `_resolve_template_name` per-request via dict local — un inbox de 47 sims ne re-lit pas 47 fois `crypto_launch.json` du disque.
  - `Number.isFinite(sim.predicted_bullish_pct)` côté frontend gère `null` proprement → on n'affiche pas le chip mono dans ce cas.
  - `vue-i18n` `{count}` interpolation marche en `t('key', { count })` dans `<script setup>` exactement comme `$t` dans `<template>`.

### 2026-04-29 — US-037 SimulationConfigGenerator parse simulation_requirement → time config adaptative
- **Statut** : passes: true (chantier 9-simulation-quality, débloque US-038/US-039/US-041)
- **Fichiers** :
  - `backend/app/services/simulation_config_generator.py` : +`import re`, +helper top-level `_resolve_time_config()` (~120 l, 4 priorités), +param kwarg optionnel `recommended_settings: Optional[Dict[str, Any]] = None` sur `generate_config()`, branchement résolution + log INFO français + court-circuit LLM time config quand `source != "default"` (économie LLM call), `_parse_time_config()` étendu avec `forced_rounds`/`forced_minutes_per_round` qui bypassent les clamps legacy (24-336h / 30-120 mpr).
  - `backend/tests/test_unit_simulation_time_config.py` : nouveau, 17 tests pure-Python (no LLM, no Neo4j) → run dans le quality gate offline.
- **Quality gates** :
  - `cd backend && uv run pytest tests/ --tb=short -x` → **249 passed, 17 skipped (integration), 0 régression** (baseline était 232 ; +17 nouveaux tests).
  - Aucun frontend touché → pas de `npm run build` requis pour cette story.
- **Architecture / priorité de résolution** (l'ordre compte, premier match gagne) :
  1. **`recommended_settings.{rounds, minutes_per_round}`** si tous deux > 0 → `source="template"`. Couvre les 5 templates canoniques US-042 (PMF 10×10080, Crisis 24×60, Adcheck 18×240, Policy 10×240, Launch 28×360). Param non encore câblé côté caller (cf "review_point" PRD) mais le helper est prêt.
  2. **Regex** sur `simulation_requirement` (FR + EN, case-insensitive). Patterns avec lookbehind anti-range (`(?<![\d\-])` pour éviter "10-15 hours" → 15) :
     - `mois|months?` → 1 round = 1 semaine, N×4 rounds
     - `semaines?|weeks?|sem\b` → 1 round = 1 semaine (10080 min), N rounds
     - `jours? ouvrés?|business days?` → 1 round = 4h (240 min), N×2 rounds (2 sessions/jour)
     - `jours?|days?|j\b` → 1 round = 4h (240 min), N×6 rounds (24h coverage). Override 6h (360 min) si la phrase contient « 1 round = 6h » explicite.
     - `heures?|hours?|h\b` → 1 round = 60 min, N rounds
     - **Spécificité business_day > day** : si "5 jours ouvrés" matche les deux, on drop le match `day` qui chevauche. Sinon on aurait pris 30×240 (le plus long horizon) au lieu de 10×240.
     - **Multi-durées** : "5 jours, 10 semaines" → on prend la plus grande horizon totale (10 sem = 100800 min > 5j = 7200 min). Documenté dans le code et testé.
  3. **Keyword fallback** loose : `crisis|crise|24h|24 h` → 24×60 ; `adcheck|3 jours` → 18×240 ; `pmf|10 semaines` → 10×10080.
  4. **Default legacy** 72 rounds × 60 min (backward compat — comportement actuel).
- **Branchement caller** (volontairement out of scope US-037) : `simulation_manager.prepare_simulation` (ligne 457) et `api/simulation.py` retry endpoint (ligne 2660) appellent encore `generate_config(...)` SANS passer `recommended_settings`. Conséquence pratique :
  - La priorité 1 (template) n'est jamais hit en prod tant qu'une story future ne fait pas le câblage `preset template → ProjectManager → generate_config(recommended_settings=...)`.
  - MAIS : le `simulation_requirement` des 5 templates US-042 contient déjà la phrase « 10 semaines », « 24 heures », « 5 jours ouvrés », « 3 jours », « 7 jours » → la priorité 2 (regex) couvre les 5 scénarios canoniques d'office. Pour Crisis : `simulation_requirement = "Voir engine.md — fuite vidéo CEO à H+0, dérive Twitter/Reddit/médias/WhatsApp 24 heures, 1 round = 1 heure."` → regex extrait "24 heures" → 24×60. Pour Adcheck : `"...18 rounds × 4h..."` → regex matche "18 rounds × 4h" → mais notre regex ne reconnaît pas ce format spécifique. À surveiller dans la story de câblage future.
- **Logging** : `logger.info("US-037: time config résolu rounds=%d, minutes_per_round=%d, source=%s", ...)` une fois par appel `generate_config`. Coût négligeable (1 log INFO par préparation, déjà bruyant en LLM logs).
- **Coût LLM** : -1 call LLM par préparation de simulation depuis template (le path déterministe court-circuite `_generate_time_config`). Les autres steps (event_config, agents, prediction markets) inchangés.
- **Apprentissages / patterns** :
  - **Lookbehind regex pour éviter capture de range** : `(?<![\d\-])(\d+)\s*(unit)` empêche `10-15 hours` de matcher comme `15 hours`. Crucial pour les requirements riches.
  - **Specificity dedup post-finditer** : quand deux unités regex peuvent matcher le même span (cas "jours" vs "jours ouvrés"), trier par spécificité dans une 2e passe est plus simple que de coder un grand pattern alternatif. Le code reste lisible et chaque regex est testable indépendamment.
  - **Bypass clamps legacy via params optionnels `forced_*`** : permet d'ajouter une 2e voie d'écriture sans casser le contrat de la 1ère. Pattern réutilisable pour d'autres parsers backend qui veulent court-circuiter une normalisation par défaut.
  - **Out-of-scope discipline** : la story demandait de NE PAS toucher l'API contract (`simulation_manager` / `api/simulation.py`). Le câblage final reste pour une story dédiée — `recommended_settings` est en kwarg optionnel donc additif et zéro-risque.
- **Pièges détectés** :
  - Le clamp legacy `total_simulation_hours = max(24, min(336, raw))` aurait écrasé silencieusement PMF (1680h) → 336h. Le bypass via `forced_*` est obligatoire pour les templates longs.
  - `minutes_per_round = max(30, min(120, ...))` aurait écrasé 240 (Adcheck/Policy), 360 (Launch), 10080 (PMF) → 120. Même bypass nécessaire.
  - Le regex `j\b` (abbrev "j") matche aussi "j'ai" si on n'est pas attentif. Le `\b` après le chiffre + le `\d{1,3}` lookbehind anti-range rendent les faux positifs improbables, mais à surveiller si un user écrit littéralement "5j ouvrés" sans espace — testé OK car `jours? ouvrés?` matche aussi `jours ouvrés` (avec espace).

### 2026-04-29 — US-042 5 scénarios canoniques preset_templates (codesignés avec Amine)
- **Statut** : passes: true (premier de la chaîne chantier 9-simulation-quality, débloque US-037, US-038, US-041)
- **Volume** : 5 scénarios × (1 JSON template + 3 fichiers MD : README/01_attachment/02_engine) = **20 fichiers** + 1 README top-level + 1 script Python helper. Total ~15 000 mots de contenu.
- **Pattern adopté** : **2 fichiers par scénario** (à la place du pattern `she_start` à 3 fichiers seed/personas/README). Validé par Amine (memory `bassira_template_two_file_pattern.md`) :
  - `01_attachment.md` = perspective customer (prêt-à-PDF, mail-style, 600-800 mots) → ce que le prospect Bassira nous enverrait. Convertible en PDF via `scripts/build_attachment_pdfs.py` (reportlab, optionnel — Amine a confirmé que les MD sont suffisants pour la démo).
  - `02_engine.md` = config technique : `simulation_requirement` LLM-readable >1500 chars, **6 agent system_prompts complets** (200-400 mots chacun, ancrés sur scenario + persona role + valeurs + sources d'autorité), **5 director events** avec injection text intégral, `expected_outcome` verdict structuré, `time_config`.
  - `README.md` lie les 2 fichiers + cohérence engine.
- **Q&A codesign** (round avec Amine 2026-04-29) :
  - Q1 : 5 scénarios validés (`pmf_startup_tech`, `crisis_24h_brand`, `adcheck_pre_launch`, `policy_brief_stress`, `product_launch_v2`)
  - Q2 : Pan-Afrique (Maroc + Sénégal + Côte d'Ivoire + Nigeria + Cameroun + Tunisie)
  - Q3 : Personas nominaux (« Karim Bennani CTO Casa », « Khadija El Idrissi mère Marrakech », etc.)
  - Q4 : 5 verdict shapes structurés validés (`viable/borderline/nope` pour PMF, `worst_case_trajectory + peak_hour + 3 messages` pour Crisis, `ranking ABC + backfire risk` pour Adcheck, `survives + amendments + flippers` pour Policy, `adoption_curve + churn_peak + 5 influencers + 3 signals` pour Launch).
  - Q5 : 25 director events (5 par scénario) tous validés par Amine.
  - Q6 : Tous scénarios en français pour la démo.
- **Apprentissages / patterns** :
  - **Cohérence inter-rounds** est cruciale : chaque agent maintient sa position d'un round à l'autre sauf info nouvelle décisive. Documenté explicitement dans chaque system_prompt.
  - **Sources d'autorité par persona** ancrent les arguments dans des sources crédibles pour le rôle (Stack Overflow + Hacker News pour CTO ; Le360 + TelQuel pour journaliste ; doctrine BCEAO + GAFI pour avocate compliance).
  - **Time config par scénario** : 10080 min/round (1 semaine PMF), 60 min/round (Crisis 24h), 240 min/round (Adcheck 3j et Policy 5j ouvrés), 360 min/round (Launch 7j).
  - **Devises** : MAD + USD jamais EUR (règle durable Amine, memory `currency_usd_never_eur.md`).
  - **Director events injection text** doit être assez riche pour que le LLM puisse raisonner — ~150-300 mots par event, pas juste un label.
- **Quality gates** :
  - Aucun changement code (templates statiques) → npm build sans impact.
  - `cd backend && uv run pytest tests/ --tb=short -x` → 202 passed, 17 skipped, zéro régression (les nouveaux templates seront validés par `test_unit_templates_schema` qui auto-découvre les fichiers preset_templates/*.json).
- **Prochaine étape Ralph (chantier 9 ordre exécution)** : US-037 SimulationConfigGenerator parse simulation_requirement → time config adaptive (les 5 templates servent maintenant de référence pour le parsing).

### 2026-04-29 — US-021 Frontend page /calibration (D3 scatter + stats publiques)
- **Statut** : passes: true
- **Fichiers** : `frontend/src/views/CalibrationView.vue` (nouveau, ~700 l template+style+script), `frontend/src/router/index.js` (+6 l route /calibration), `frontend/src/locales/{fr,ar,en}.json` (+~70 keys section `calibration.*` chacun, MÊMES keys cross-locale)
- **Quality gates** :
  - `cd frontend && npm run build` → OK : nouveau chunk `CalibrationView-*.js` 12.62 kB / 3.92 kB gzip + `CalibrationView-*.css` 9.40 kB / 1.93 kB gzip ; `index-*.js` toujours sous 100 kB gzip
  - `cd backend && uv run pytest tests/ --tb=short -x` → 202 passed, 17 skipped (intégration), zéro régression (aucun fichier backend touché)
- **Architecture** :
  - SVG vanilla scatter (pas d'import d3 dans la vue — la lib est déjà dans le bundle pour d'autres views, mais ce plot est trivial, viewBox 760x560 avec `width: 100%` ⇒ fully responsive, height auto via CSS)
  - 10 buckets de probabilité plottés en `<circle>` avec `r = clamp(sqrt(n)*2, 4, 20)` ; les buckets vides (`n=0`) sont filtrés pour ne pas polluer le plot avec des points à `observed=null`
  - Diagonale référence en `stroke-dasharray: 4 4` couleur `--ms-text-subtle` (calibration parfaite)
  - Grille interne, axes, ticks 0/0.2/0.4/0.6/0.8/1, axis titles via `<text>` (rotation -90° pour Y)
  - Tooltip = `<div>` absolu suivant la souris (pattern PolymarketChart) — `transform: translate(-50%, calc(-100% - 14px))` pour que le tooltip s'ancre au-dessus du curseur centré, fonctionne identiquement LTR/RTL (pas de flip souhaité, le tooltip doit suivre la coordonnée physique)
- **Shape backend / brief mismatch** :
  - Le brief promettait `data.outcomes.{called_it,partial,wrong}` + `delta_vs_previous_month` + `data.filters.templates_available`
  - Le backend (`backend/app/api/calibration.py`) retourne actuellement la forme PLATE : `{success, brier, n, n_called_it, n_partial, n_wrong, accuracy, calibration_plot}` sans delta ni filters
  - Le composant lit en priorité la forme réelle (`d.n_called_it`) avec FALLBACK vers la forme imbriquée (`d.outcomes?.called_it`) pour rester forward-compat si le backend ajoute le wrapper plus tard
  - Le chip de delta est détecté à l'exécution : `data.delta_vs_previous_month ?? data.delta_vs_previous`. Tant que ce champ est absent, le chip est simplement non rendu — pas de crash, pas de placeholder « N/A »
  - `availableTemplates` lit `data.filters.templates_available` puis `data.templates_available` à plat → liste vide → select n'affiche que « All templates »
- **Patterns réutilisés** :
  - `useScrollFadeIn(sectionRefs)` (US-029) sur 4 sections : hero / stats / plot+filters / methodology+CTA
  - `.ms-card`, `.ms-btn ms-btn-secondary --sm`, `.ms-btn-ghost --sm`, `.ms-badge ms-badge-{success,warning,danger}`, `.ms-skeleton`, `.ms-mono`, `.ms-input`, `.ms-select`
  - LanguageSwitcher mounté globalement par `App.vue` (US-008) ⇒ pas d'ajout dans la page
  - CSS logical properties partout (`max-width`, `padding-inline`, `inset-inline-end` côté `cal-back-arrow` non requis mais flex-row natif gère le RTL) ; pas de `margin-left/right` ni `right:`/`left:` non-tooltip
  - `axios` via `frontend/src/api/index.js` (intercepteur qui unwrap response.data, gestion timeout)
- **Locales** : 3 fichiers traduits avec accents (ÉRR, À, Ç…) ; AR avec terminologie correcte (درجة براير, التواتر المرصود, المعايرة)
- **CTA** : `<router-link to="/devis">` qui pointe vers une route pas encore créée — c'est volontaire (cf brief, l'autre story US-025 créera /devis ou /offres). Vue Router renvoie le 404 par défaut si on clique avant la création — non bloquant pour US-021
- **AC déférée** : « Test Playwright : page charge, plot rendu » → reportée à US-010 (set up commun de la suite multi-locale)
- **Pattern à retenir** : pour un endpoint backend dont le shape promet plus que ce qu'il fournit aujourd'hui (cas fréquent quand frontend et backend bossent en parallèle), CODER LA LECTURE EN COUCHES : forme réelle PRIORITAIRE puis fallback vers la forme imbriquée envisagée. `Number.isFinite(value)` est plus sûr que `value !== undefined` pour les chiffres car il rejette aussi `null` et `NaN`

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

### 2026-05-03 — US-087 Pivot home : masquage CTA self-service + nav Modèles + SectorUseCases relink
- **Statut** : passes: true (chantier J-pivot-models, premier de la chaîne).
- **Contexte** : pivot stratégique demandé par Amine — la home publique ne doit plus inviter le visiteur cold à lancer une simulation lui-même. Elle l'oriente vers les modèles publics (/models, US-086 en parallèle) ou vers la prise de contact commerciale (/devis). Le self-service Step1-5 reste accessible techniquement (URLs directes /process/:id, /simulation/:id) — c'est uniquement la promotion publique qui est stoppée.
- **Fichiers** :
  - `frontend/src/views/Home.vue` : nav header refactorée (Accueil · Modèles · Calibration · Offres · Partenaires · Contact, « Modèles » en position 2 avec classe `.nav-link--featured` terracotta), hero CTA scindé en row primary (« Voir les modèles » → /models) + secondary (« Commander une analyse » → /devis), block console upload + TemplateGallery + HistoryDatabase masqués via `v-if="showSelfServiceConsole"` (flag local à `false` tant qu'aucun système d'auth admin/client n'est en place — US-088 à venir). Fonctions `scrollToConsole` et `scrollToTemplates` retirées (plus appelées).
  - `frontend/src/views/LandingView.vue` : nav top gagne entrée « Modèles » en première position, classe `.lp-nav-link--featured`.
  - `frontend/src/components/SectorUseCases.vue` : remplacement du CTA unique « Tester ce cas » par un double CTA card — `Voir le modèle` (primary, route `/models?sector=<id>`) + `Demander une analyse personnalisée` (ghost, route `/devis?sector=&usecase=&package=` qui conserve la mécanique SECTOR_TO_SITUATION US-085 dans QuoteView).
  - `frontend/src/locales/{fr,en,ar}.json` : nouvelles keys `nav.{home,homeTitle,models,modelsTitle,partners,partnersTitle,contact,contactTitle}`, `home.heroCta.{viewModels,viewModelsTitle,orderAnalysis,orderAnalysisTitle}`, `sectors.cardCta.{viewModel,viewModelTitle,requestCustom,requestCustomTitle}`, `landing.nav.models`. Aucun touch au namespace `models.*` top-level (réservé à US-086 en parallèle).
  - `frontend/tests/e2e/helpers.ts` : fixtures `FX.<locale>.home.{title,launchCta}` mises à jour pour pointer vers les nouveaux CTAs (« Voir les modèles » / « Browse our models » / « تصفّح النماذج ») et les hero titles actuels (« Stress-testez votre stratégie » / etc., qui étaient déjà dans les locales mais pas dans les fixtures).
  - `frontend/tests/e2e/smoke-{fr,en,ar}.spec.ts` : titres de tests Home renommés pour refléter le nouveau CTA (« Voir les modèles (US-087) »). Le corps des tests est intact — il pioche `FX.home.launchCta` du fixture, donc le test continue de valider qu'un CTA principal existe.
- **Quality gates** :
  - `npm run build` → OK, bundle index 557 kB / 159 kB gzip (avant US-087 : ~563 kB / 161 kB ; on retire un peu de CSS du fait des fonctions scrollTo retirées).
  - `npm run typecheck` / `npm run lint` : non configurés sur le frontend Vue 3 (pas de scripts dans package.json, pas de TypeScript dans les .vue, pas de eslint config). Build Vite est la seule garantie de syntaxe Vue/JS.
  - `npx playwright test --list` → 32 tests parsés OK, fixtures alignées. Run complet non lancé (chromium dépend de l'environnement, repo local-only sans accès DNS).
- **Décisions techniques** :
  - **Préservation du DOM self-service** : les blocs `console-intro`, `dashboard-section`, `templates-gallery`, `HistoryDatabase` sont gardés intégralement dans Home.vue, juste enveloppés d'un `v-if="showSelfServiceConsole"`. Quand US-088 ajoutera l'auth admin/client, il suffira de remplacer `const showSelfServiceConsole = ref(false)` par `computed(() => isAuthenticated.value && hasSelfServiceAccess.value)` — zéro refactor template.
  - **Nav 6 entrées (Home) vs 4 entrées (Landing)** : la nav Home est plus complète (Accueil · Modèles · Calibration · Offres · Partenaires · Contact) ; la nav LandingView reste minimaliste (Modèles · Brier score · Tarifs · Demander une démo) car LandingView est ciblée cold LinkedIn/Google avec une attention de 8 secondes — moins d'options = mieux. Cohérence : « Modèles » présent dans les deux, en position priorité haute.
  - **`/models` route inexistante** : US-086 livre `/models` et `/models/:slug` en parallèle. Vue Router log juste un warning au runtime quand le sub-agent US-086 n'a pas encore mergé, pas d'erreur de build. Quand les deux sub-agents mergent, la nav devient fonctionnelle d'office.
  - **Nav header dans Home.vue (et pas un AppHeader.vue partagé)** : le projet n'a pas de composant nav header global (App.vue mount juste `<router-view />` + LanguageSwitcher + ThemeSwitcher + DebugPanel). Chaque vue a sa propre nav (Home.vue, LandingView.vue, ExploreView.vue, etc.). Le brief autorisait ce cas — on touche la nav de Home et celle de LandingView pour cohérence sur les deux landings publiques.
  - **`nav-link--featured` (CSS)** : classe ajoutée sur l'entrée « Modèles » avec `color: var(--wi-primary)` + `font-weight: 600`. Le `:hover` utilise `var(--wi-primary-soft)` pour le background. Les autres entrées gardent leur visuel neutre `var(--ms-text-muted)`.
- **Pièges détectés** :
  - **Espace insécable U+00A0 dans helpers.ts** : le fixture `'Simulez tout, pour 1 $'` contenait un `\xa0` invisible avant le `$`. L'outil Edit ne matchait pas sur l'espace régulier — il a fallu faire le replace en Python pour préserver l'encoding. Apprentissage : pour les patches sur du texte FR multi-caractères, vérifier l'encoding via Python avant de débattre avec Edit.
  - **Fixtures Playwright désynchronisées avant US-087** : `FX.home.title` cherchait `Simulez tout, pour 1 $` qui n'est plus dans `home.hero.title` depuis le rebrand 2026-04-29 (qui a posé `Stress-testez votre stratégie...`). Donc les tests smoke Home étaient déjà cassés AVANT US-087. Cet ajustement de fixtures les rend de nouveau alignés avec les locales — sans étendre le scope au-delà des 2 champs touchés (title + launchCta).
- **Suite recommandée** :
  - **US-088 (futur)** : ajouter un système d'auth admin/client minimal pour réactiver showSelfServiceConsole. Pattern recommandé : sessionStorage `bassira_admin_token` + reactive `useAuth()` composable + `computed(() => isAuthenticated.value)`.
  - **US-086 merge** : dès que la branche US-086 (route /models) merge, la nav devient fonctionnelle. Aucun coordination filesystem nécessaire car les namespaces i18n sont disjoints (`nav.*` US-087 vs `models.*` US-086).

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

### 2026-05-02 — Session : Warm Intelligence + Web Enrichment (US-053 à US-058)
- **Chantiers** : 7-warm-intelligence (4 stories), 8-web-enrichment (2 stories)
- **PRD** : 6 nouvelles stories ajoutées, ID US-053 → US-058
- **Patterns à retenir** :
  - Tokens Warm Intelligence : namespace --wi-* (pas --warm-* qui collision existant)
  - Source : stitch_bassira_simulation_pricing_page/warm_intelligence/DESIGN.md
  - Perplexity : WebEnricher déjà dans web_enrichment.py — extend, ne pas recréer
  - TrendingTopics.vue : déjà opérationnel sur Home.vue — réutiliser sans modifier

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

### 2026-05-03 — US-093 Frontend Vue auth Supabase + ClientDashboardView privatif
- **Statut** : passes: true
- **Fichiers créés** : frontend/src/lib/supabase.js, frontend/src/stores/auth.js, frontend/src/api/client.js, frontend/src/views/{LoginView,SignupView,ClientDashboardView}.vue, frontend/tests/e2e/auth-flow.spec.ts, frontend/.env.local
- **Fichiers modifiés** : frontend/src/main.js (Pinia + auth.init), frontend/src/router/index.js (3 routes + beforeEach), frontend/src/views/{Home,LandingView}.vue (nav adaptative), frontend/src/locales/{fr,en,ar}.json (nav.login/dashboard/logout + auth.* + client.*)
- **Dépendances ajoutées** : `@supabase/supabase-js`, `pinia`
- **Durée** : ~50 min
- **Quality gates** : npm run build ✓ (838 modules, 13.36 s) ; playwright list ✓ (4 nouveaux tests détectés)
- **Learnings** :
  - vue-i18n traite `@` comme syntaxe de message lié (`@:link`) → escape obligatoire avec `{'@'}` dans les placeholders email. Sinon erreur de compilation au build (`error code: 10`).
  - storeToRefs(authStore) côté template/setup pour préserver la réactivité des getters Pinia (`isAuthenticated`).
  - Init du store auth en IIFE async dans main.js AVANT app.mount() pour que le router beforeEach voie l'état auth réel dès la première navigation.
  - Le fichier .env.local est gitignoré via `*.local` (déjà dans .gitignore frontend) → safe d'y poser les placeholders Supabase pour le build local.
  - Les classes scoped Vue ne se partagent pas entre composants : il a fallu redéfinir `.dash-field` / `.dash-input` dans ClientDashboardView au lieu de réutiliser `.auth-field` / `.auth-input` qui sont scoped à LoginView.
  - Pour respecter la rétrocompatibilité, les routes publiques (/, /models, /calibration, /offres, /devis, /landing, /partenaires, /explore) sont restées intactes ; seuls /login, /signup, /client/dashboard ont été ajoutés.
  - Tokens `--wi-*` exclusifs : zéro hex hardcodé dans les 3 nouvelles vues + RTL via CSS logical properties (margin-inline-*, padding-inline-*, inset-inline-end).
  - L'attribution org reste manuelle pour le MVP (cf. supabase/seed.sql) : le SignupView affiche un message d'attente d'invitation 24 h.

### 2026-05-05 — US-114 Migration table quote_ownership Supabase
- **Statut** : passes: true (worktree agent-a7fb2c3e, à merger sur main)
- **Fichiers créés** : `supabase/migrations/20260505_001_quote_ownership.sql`, `backend/app/services/quote_ownership.py`, `backend/tests/test_unit_quote_ownership.py`, `scripts/migrate_quotes_to_supabase.py`
- **Fichiers modifiés** : `backend/app/api/quote.py` (scoping super-admin vs member sur GET /api/admin/quotes + /<id>), `backend/app/services/quote_service.py` (lien Supabase best-effort dans submit_quote), `backend/app/services/quote_admin_service.py` (mirror status sidecar → Supabase), `backend/tests/test_unit_quote_admin.py` (test_list_normal_user_403 adapté à la nouvelle sémantique)
- **Quality gates** : pytest 910 passed, 17 skipped (+32 nouveaux tests US-114), zéro régression. Migration SQL idempotente (IF NOT EXISTS + DROP POLICY IF EXISTS).
- **Learnings** :
  - **Pattern best-effort Supabase** : tous les liens `quote_ownership` (insert au submit, mirror au status update) sont enrobés d'un try/except large qui ne lève jamais. Le filesystem reste source de vérité ; Supabase est un index requêtable.
  - **Idempotence INSERT** : la convention « duplicate key (23505) → log + return False, autres exceptions → propagate » permet aux scripts de migration de tourner N fois sans erreur tout en remontant les vraies pannes.
  - **Scoping endpoint admin** : pour préserver le contrat existant super-admin tout en élargissant aux members, la meilleure approche est `@require_auth` + branchement interne sur `is_super_admin_email(email)`. Évite la duplication d'endpoint et garde une URL unique `/api/admin/quotes`.
  - **Fuite cross-tenant** : un member tentant de lire un devis qui ne lui appartient pas reçoit 404 (et non 403) pour ne pas révéler l'existence d'un quote_id valide cross-org (DEFCON 1, OWASP A01).
  - **Test évolution sémantique** : quand un endpoint change de contrat (super-admin only → super-admin OR member), il faut adapter les tests existants en respectant la nouvelle sémantique tout en couvrant les cas limites (user sans org, user mauvaise org). Le test `test_list_normal_user_403` est resté à 403 mais sous la condition `NOT_A_MEMBER` au lieu de `NOT_SUPER_ADMIN`.
  - **MagicMock chain pour Supabase** : pour mocker `cli.table().select().eq().limit().execute()` etc., construire une chaîne explicite avec `.return_value` — un seul `MagicMock()` global ne supporte pas `select_chain.in_()` et `select_chain.eq()` simultanément avec data différente. Helper `_make_fake_supabase_for_ownership()` factorise cette construction pour les 32 tests US-114.

### 2026-05-05 — US-115 Système d'invitation user → org
- **Statut** : passes: true (worktree agent-a7fb2c3e, à merger sur main)
- **Fichiers créés** :
  - `supabase/migrations/20260505_002_org_invitations.sql` (table + 5 RLS policies)
  - `backend/app/services/org_invitations.py` (5 helpers : create/get/list/revoke/redeem)
  - `backend/app/api/invitations.py` (5 endpoints : POST/GET/DELETE admin + GET accept public + POST redeem)
  - `backend/app/templates/emails/org_invitation.html` (template HTML brand Bassira)
  - `backend/tests/test_unit_invitations.py` (46 tests)
  - `frontend/src/views/AdminInvitationsView.vue` (form + liste pending + revoke)
- **Fichiers modifiés** :
  - `backend/app/__init__.py` (register admin_invitations_bp + invitations_bp)
  - `frontend/src/api/client.js` (5 nouvelles méthodes API)
  - `frontend/src/router/index.js` (route /admin/invitations)
- **Quality gates** : pytest 956 passed (+46 nouveaux tests US-115), 17 skipped, zéro régression. Migration SQL idempotente (CREATE...IF NOT EXISTS + DROP POLICY IF EXISTS partout).
- **Learnings** :
  - **Token UUID natif Postgres** via `gen_random_uuid()` : ~122 bits d'entropie, suffisant contre l'énumération sans avoir à créer un module crypto Python dédié. Plus simple à débugger qu'un secret HMAC custom.
  - **RLS policy public read avec auth.email()** : `lower(email) = lower(coalesce(auth.email(), ''))` permet à un user authentifié de voir SON invitation pending sans avoir à hacker un endpoint. Pattern réutilisable pour d'autres invitations (sims partagées, exports, etc.).
  - **Endpoint `/accept` public** : le pattern « lecture metadata sans auth pour pré-remplir signup » est crucial UX-wise — sans ça, le destinataire qui clique sur le lien doit deviner pour quelle org il est invité avant de créer son compte. On expose `email`, `role`, `org_name`, `expires_at` ; pas plus.
  - **EMAIL_MISMATCH au redeem** : sécurité multi-couches. Même si le token leakait via screenshot, l'auth.email() du JWT doit matcher l'invitation.email pour que la création de membership passe. Empêche l'usurpation de membership croisée.
  - **Idempotence redeem org_members** : si la row `(org_id, user_id)` existe déjà (cas d'un user qui clique 2× sur le lien après être déjà membre), on log + on continue à marquer l'invitation consommée. Pas d'erreur user-facing.
  - **MagicMock `or` falsy trap** : `delete_rows = delete_rows or [{"token": "deleted"}]` écrase aussi `[]` (falsy). Pour permettre au caller de passer une liste vide explicite, utiliser `if delete_rows is None:` à la place du `or`.
  - **Layout du blueprint séparé** : un blueprint pour `/api/admin/invitations` (decorée `@require_auth` + branchement super-admin/org-admin) et un autre pour `/api/invitations/<token>` (mix public + auth). Évite la confusion des préfixes URL.

### 2026-05-05 — US-120 — Migration pdf_branding Supabase + admin CRUD UI (worktree agent-af218de6)

- **Statut** : passes:true — tous les quality gates backend OK. Frontend build OK. Playwright en attente déploiement prod (pattern établi : les E2E testent la prod).
- **Branch** : main (worktree agent-af218de6)

#### Fichiers créés
- `supabase/migrations/20260506_001_pdf_branding.sql` — table + 5 RLS policies (versioning append-only)
- `backend/app/services/pdf_branding.py` — 5 helpers : get_active_branding, create_branding, list_branding, update_branding, validate_placeholders
- `backend/app/api/admin_branding.py` — blueprint admin_branding_bp : GET/POST/PATCH + POST preview (SVG base64)
- `backend/tests/test_pdf_branding.py` — 37 tests (service + endpoints + RLS scenarios)
- `frontend/src/views/AdminBrandingView.vue` — Vue 3 composition API, split layout (form + preview live), tokens --wi-*
- `frontend/tests/e2e/admin-branding.spec.ts` — 8 tests Playwright (guards + super-admin UI)

#### Fichiers modifiés
- `backend/app/__init__.py` — register admin_branding_bp at /api/admin/branding
- `frontend/src/api/client.js` — 4 nouvelles méthodes : fetchAdminBrandings, createAdminBranding, patchAdminBranding, previewAdminBranding
- `frontend/src/router/index.js` — route /admin/branding (requiresAuth + requiresSuperAdmin)
- `frontend/src/locales/fr.json` — clés adminBranding.* (FR)
- `frontend/src/locales/en.json` — clés adminBranding.* (EN)
- `frontend/src/locales/ar.json` — clés adminBranding.* (AR)

#### Quality gates
- `pytest tests/test_pdf_branding.py` : **37/37 passed**
- `pytest tests/ --ignore=integration` : **1029/1029 passed, 0 régression**
- `npm run build` / `npx vite build` : **exit 0**, 853 modules transformés
- `playwright admin-branding.spec.ts` : **1/8 passed** (tests testent prod — route pas encore déployée, pattern identique à US-117 avant déploiement)

#### Learnings
- **Versioning append-only SQL** : une mise à jour branding crée une nouvelle row avec `valid_from=now()` et expire l'ancienne avec `valid_to=now()`. Requête active : `WHERE valid_from <= now() AND (valid_to IS NULL OR valid_to > now()) ORDER BY valid_from DESC LIMIT 1`. Préserve l'historique complet sans perte de données.
- **Piège vue-i18n : double accolades dans les valeurs JSON** : `{{logo}}` dans une valeur JSON est interprété comme un placeholder vue-i18n et déclenche `error code: 9` au build Vite. Solution : remplacer par une description textuelle (ex: `"logo, section, page"`) dans le fichier JSON. Les valeurs JS dans `<script setup>` ne sont pas affectées.
- **Piège Vue template : double accolades dans les fallback strings** : `{{ $t('key') || 'Texte {{logo}}' }}` cause `Unterminated string constant` au compile Vue. Le compilateur parse `{{` en interpolation. Même fix : éviter les doubles accolades dans les strings inline du template.
- **Patch target pytest** : pour mocker `get_supabase_admin` dans un blueprint Flask, patcher l'import du MODULE blueprint (`app.api.admin_branding.get_supabase_admin`), PAS le module source (`app.auth.supabase_client.get_supabase_admin`). Sinon le mock n'affecte pas l'objet déjà importé dans le blueprint.
- **SVG preview** : alternative légère à WeasyPrint/pdf2image pour les aperçus de branding. Génère un SVG A4 (595×842) avec header + zone contenu + footer. Les placeholders `{{...}}` sont résolus avec des valeurs d'exemple. Retourné en base64 pour une img `src=data:image/svg+xml;base64,...`. Zéro dépendance système supplémentaire.
- **RLS DELETE restrictif** : pour les ressources de configuration (branding), `DELETE` uniquement via `service_role` (RLS bypass) — pas de policy publique. La policy `using (false)` bloque tout accès JWT. Le super-admin passe par `service_role` directement depuis le backend Flask.
- **Debounce preview 1s** : déclencher l'aperçu live sur chaque keystroke casse l'UX (trop d'appels). 1 seconde de debounce après `@input` est le bon compromis. L'aperçu se met à jour automatiquement après la pause de frappe.

### 2026-05-05 — US-119 — Loader complet (charge tous les artifacts simulation + report)

- **Statut** : passes:true — tous les quality gates backend OK.
- **Branch** : worktree-agent-a2c116f3

#### Fichiers créés
- `backend/app/services/report_pdf/loader.py` — `PDFContextLoader.load()` + `PDFContextLoaderError`
- `backend/tests/test_pdf_context_loader.py` — 55 tests (54 passent + 1 skip real-sim)
- `backend/tests/fixtures/sim_aabbcc112233/` — 9 fichiers de fixtures simulation
- `backend/tests/fixtures/report_a1b2c3d4e5f6/` — 4 fichiers de fixtures report

#### Fichiers modifiés
- `backend/app/services/report_pdf/__init__.py` — export `PDFContextLoader` + `PDFContextLoaderError`

#### Quality gates
- `pytest tests/test_pdf_context_loader.py` : **55 passed, 1 skipped (real sim absent)**
- `pytest tests/test_pdf_context_schema.py` (US-118 no regression) : **52/52 passed**
- `pytest tests/` : **1136/1136 passed, 18 skipped, 0 régression**

#### Learnings
- **Fixtures nommées avec l'ID** : pour que `PDFContextLoader.load(simulation_id=X, sim_base_dir=fixtures/)` trouve `fixtures/X/`, les dossiers de fixtures doivent être nommés avec l'ID exact (`sim_aabbcc112233/`), pas un nom générique (`sim_test/`). Erreur classique découverte au premier run.
- **`extra="ignore"` côté loader** : grâce à la config Pydantic sur tous les sub-models, le loader peut passer le dict brut via `model_validate()` sans filtrer les champs. Les clés inconnues (ex. `"summary"` dans outcome) sont silencieusement ignorées.
- **Chemin indépendant de Flask** : calculer `_SIMULATIONS_DIR` et `_REPORTS_DIR` depuis `__file__` (sans importer `Config`) rend le loader testable hors contexte Flask et évite les imports circulaires.
- **Fallback chain profiles** : le fallback `agent_profiles → reddit → twitter CSV → polymarket` doit court-circuiter dès qu'une source retourne une liste non-vide. Un fichier JSON vide (`[]`) doit déclencher le fallback suivant (pas seulement `None`).
- **counterfactual_injection.json** : peut être un objet unique (dict) ou une liste. Le parser doit gérer les deux cas et retourner toujours `List[Counterfactual]`.
- **events.jsonl → DirectorEvent** : les événements bruts JSONL sont mappés en `DirectorEvent` (champs `round`, `event_type`, `description`, `impact`). Les champs manquants sont comblés par les defaults Pydantic.
- **Paramètres override** `sim_base_dir` / `rep_base_dir` : indispensables pour les tests afin de pointer vers les fixtures sans toucher aux répertoires de production.
- **Merge main avant US** : cette worktree avait 6 commits de retard sur main (US-118, US-120 mergés entre-temps). Un `git merge main --no-edit` fast-forward a résolu le problème avant de démarrer US-119.

---

### 2026-05-05 — US-122 ChartFactory matplotlib palette Causse (5 charts signature)

- **Statut** : passes:true — worktree `worktree-agent-ae155daa`, commit `f3d8de2`.
- **Fichiers créés** :
  - `backend/app/services/report_pdf/_style.py` : `apply_causse_style()` — palette Causse Warm Intelligence (WI_ORANGE `#FF8551`, WI_MINT `#006D44`, WI_CREAM `#FAF7F2`, WI_CHARCOAL `#241915`, WI_TERRA `#A13F0F`, WI_SAND `#E8DDC9`, WI_INK `#1A0F0A`), polices Outfit/Manrope avec fallback DejaVu Sans, DPI 300, spines top/right off, grid WI_SAND opacity 0.4.
  - `backend/app/services/report_pdf/charts.py` : `ChartFactory(context: PDFReportContext)` avec 5 méthodes `→ bytes PNG 300 DPI` :
    - `belief_drift()` — line chart score/round par stance + callouts PivotalMoment.round/agent
    - `polymarket_curves()` — % bullish/bearish/neutral par round depuis trajectoire (+ annotation Outcome.bullish_pct/bearish_pct)
    - `demographic_pyramid()` — pyramide horizontale genre si dimension='genre', sinon bar chart horizontal par segment
    - `influence_leaderboard()` — top-10 agents par score max (AgentState.score agrégé par name), coloré par stance dominante
    - `interaction_network()` — networkx Graph depuis SocialNetwork.nodes/edges, spring_layout(seed=42), couleur par SocialNode.group, taille par weight
  - `backend/tests/test_charts.py` : 22 tests (import Agg, rcParams, 5 charts ×  données/placeholder, reproducibilité, magic bytes PNG, top10 limit, nœuds isolés)
- **Fichiers portés depuis main** (US-118/119/120 déjà mergés mais absents du worktree) :
  - `backend/app/services/report_pdf/schema.py`, `loader.py`, `__init__.py`
  - `backend/tests/test_pdf_context_schema.py`, `test_pdf_context_loader.py`
  - `backend/tests/fixtures/` (sim_aabbcc112233/ + report_a1b2c3d4e5f6/)
- **Dépendances ajoutées** à `pyproject.toml` + `uv.lock` : `matplotlib>=3.8` (→ 3.10.9 installé), `networkx>=3.0` (→ 3.6.1 déjà présent via camel-ai).

#### Quality gates
- `pytest tests/test_charts.py` : **22 passed** en 67 s.
- `pytest tests/test_pdf_context_schema.py + test_pdf_context_loader.py` : **107 passed, 1 skipped** (sim réelle absente, attendu).
- `pytest tests/` (suite complète) : **1121 passed, 18 skipped, 0 failed** en 94 s. Zéro régression.

#### Learnings — adaptation au schema canonique
- **`Round.round_idx`** (pas `round_index`) : le champ est `round_idx` dans le schema US-118. Utiliser `r.round_idx` pour le tri et l'axe X des charts.
- **`PivotalMoment` sans champ `label`** : le schema a `round`, `agent`, `event`, `delta_score`. Pour les callouts du belief_drift, utiliser `pm.agent[:12]` comme étiquette.
- **`SocialNode.group`** (pas `archetype`, pas `stance`) : la couleur du réseau est basée sur `SocialNode.group`. La stance est dans `AgentState`, pas dans `SocialNode`.
- **`Round` n'a pas de `market_probs`** : le champ n'existe pas dans le schema. Les polymarket curves sont calculées depuis `AgentState.stance` (comptage bullish/bearish/neutral per round), pas depuis un champ dédié.
- **Backend Agg obligatoire** : `matplotlib.use("Agg")` doit être appelé AVANT `import matplotlib.pyplot`. Placer l'appel au niveau module dans `_style.py` ET dans `charts.py` (double garde) évite les imports circulaires et les imports par tiers qui reset le backend.
- **Worktree isolé** : les fichiers mergés en main depuis d'autres worktrees (US-118, US-119) ne sont PAS présents dans un nouveau worktree basé sur un commit antérieur. Il faut les `cp` manuellement ou les retravailler from scratch. La prochaine fois, vérifier `ls backend/app/services/report_pdf/` dès le début.
- **Fixtures pytest** : `test_pdf_context_loader.py` nécessite `backend/tests/fixtures/sim_aabbcc112233/` (plusieurs JSONs). Ces fixtures n'existaient pas dans le worktree — copier depuis main avant d'exécuter la suite complète.

### 2026-05-05 — US-123 Templates Jinja2 Markdown source unique + macros (worktree agent-ab3dea9e)

- **Statut** : passes:true. 18/18 tests, 1261 passed full suite, 0 régression.

#### US-123 — Templates Jinja2 Markdown source unique + macros réutilisables

**Fichiers créés :**
- `backend/app/templates/pdf_report/_macros.md.j2` — 5 macros : `kpi_card`, `callout`, `pull_quote`, `table_from_data`, `chart_with_narrative`
- `backend/app/templates/pdf_report/00_cover.md.j2` à `07_appendix.md.j2` — 8 sections du rapport
- `backend/app/templates/pdf_report/_full.md.j2` — assembleur avec front-matter YAML + includes
- `backend/app/services/report_pdf/jinja_env.py` — `get_jinja_env()`, `render_section()`, `render_full_report()` + filter `|normalize`
- `backend/tests/test_md_templates.py` — 18 tests couvrant toutes les sections, edge cases, YAML front-matter

**Fichiers modifiés :**
- `backend/app/services/report_pdf/__init__.py` — export `get_jinja_env`, `render_section`, `render_full_report`

#### Patterns nouveaux à propager

- **Filter Jinja2 `|normalize`** : enregistré via `env.filters['normalize'] = _normalize_filter` dans `jinja_env.py`. Défensif : `None` → `''`, lang invalide → fallback `'fr'`, exception → `str(value)`. Toujours appeler `TextNormalizer(lang).normalize(text).normalized`, pas `NormalizedText` directement.
- **Mock LanguageTool en CI** : `with patch("app.services.text_normalizer.languagetool_client.check", return_value=[])` — à placer en fixture `autouse=True, scope="module"` dans tout test qui appelle TextNormalizer massivement. Évite 5 s × N timeouts HTTP.
- **yaml.safe_load sur ISO 8601** : `yaml.safe_load` parse automatiquement `2026-05-05T12:00:00Z` en `datetime.datetime`. Comparer avec `str(parsed["generated_at"]).startswith("2026-05-05")` plutôt qu'une égalité string directe.
- **Jinja2 `trim_blocks=True` + `lstrip_blocks=True`** : combinés avec `{%- -%}` pour contrôler les whitespaces dans les templates Markdown. Sans ça, les tables GFM et les listes génèrent des lignes vides parasites.
- **Include dans Jinja2** : `{% include '00_cover.md.j2' %}` dans `_full.md.j2` utilise le FileSystemLoader de l'environnement — les includes partagent le même contexte que le template parent. Pas besoin de `from ... import` pour les macros incluses dans les sections.

---
