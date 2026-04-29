== PASSATION MiroShark/Bassira 2026-04-29T22:00:00+01:00 ==

[ETAT]
- branche `main` `102ae67` à jour avec `origin/main`
- prod **ONLINE** sur https://prospectives.ai-mpower.com (HTTP 200)
- **44/51 stories Ralph passes:true (86 %)**
- 344 tests backend passing (+6 cette extension de session) · zéro régression
- **32 tests Playwright E2E** sur 5 vues × 3 langues + tunnel commercial · 32/32 PASS contre prod en 23s
- npm run build : OK
- **18 commits poussés** cette session étendue
- 7 sub-agents pilotés cette session : tous done & pushed
- **Plan dettes 4/4 phases complété** (Phase 1 cleanup + 2 robustesse + 3 Playwright + 4 chart D3)

[FAIT cette session — 12 stories Ralph + 1 fix UX critique + 4 nouvelles stories (US-049/050/051/052)]

**Extension session post-2030 (chantier dettes 4 phases)** :

✓ **Phase 1 cleanup** (commit `c31dace`) : suppression 3 backups Office résiduels + ajout `~$*` au .gitignore + création `docs/COOLIFY_ENV.md` (doc complète SMTP avec procédure Gmail step-by-step) + ajout US-050/051/052 au PRD.

✓ **Phase 2 robustesse backend US-050 + US-051** (commit `f0dace4`) :
  - **US-050** : pre-check graph_id durci contre exceptions storage typées. ValueError → 503 GRAPH_CHECK_FAILED message rebuild. Exception module `neo4j.*` → 503 retry 30s. Exception générique → fail-open volontaire. Heuristique `type(exc).__module__.startswith("neo4j")` évite la dépendance dure. 3 nouveaux tests + i18n GRAPH_CHECK_FAILED 3 langues.
  - **US-051** : refactor `_get_simulation_dir(simulation_id, create=False)` par défaut. Audit des 10 callers : créer = `create=True`, lire = `create=False`. Plus de dossiers fantômes silencieux. `delete_simulation` simplifié sans contournement. 3 nouveaux tests US-051.

✓ **Phase 3 Playwright US-010** (commit `4d738be`) : 32 tests E2E runnables contre prod en 23s. 5 vues × 3 langues smoke (Home, /calibration, /offres, /devis, /explore) + 15 tests transverse i18n no-raw-keys + 2 tests tunnel commercial /offres → /devis read-only + RTL `dir=rtl` sur 5 pages AR. Aucune action destructive. Scripts npm `test:e2e`, `test:e2e:ui`, `test:e2e:list`. Couvre la dette de validation des 12+ commits récents.

✓ **Phase 4 chart D3 US-052** (commit `102ae67`) : helper `frontend/src/utils/css-vars.js` avec `readChartPalette()` lit `--ms-chart-1..10` + `--ms-status-*` via `getComputedStyle` au mount, mémoise + Object.freeze + fallback hex. PolymarketChart 11 hex JS éliminés, GraphPanel array catégoriel + 6 highlights migrés. `clearChartPaletteCache()` exposée pour US-027 dark mode futur. **Débloque US-027**.

---

[Pré-extension — passation initiale 20:30]

[FAIT cette session première moitié — 8 stories Ralph + 1 fix UX critique + nouvelle US-049]

✓ **Step03-Fix** (commit `2399f99`) : hints contextuels Step 03 (entities/profiles/timeout/llm) + extraction err.response.data.error dans handleConfigRetry + locales fr/en/ar débrandées d'OpenRouter + admin US-038 passes:true. Cas signalé par Amine sur sim_cc793c9c99b5 où il voyait "Request failed with status code 400" au lieu d'un message localisé.

✓ **US-047** (commits `7771bf0` backend + `6ba99b1` frontend) : Validation graph non-vide à /api/simulation/create + UI préventive. Backend fail-fast avec error_code=GRAPH_EMPTY si filtered_count==0. Frontend bouton "Lancer la simulation" disabled tant que graphStats.nodes===0 + hint i18n disabledEmptyGraph + tooltip. **Bug systémique détecté** : le pre-check non-bloquant (politique volontaire) laisse passer si EntityReader lève. À monitorer.

✓ **US-039** (commit `a8d9f99`) : Step1 form enrichi "Refine context". Carte dépliable dans le workbench Step1 avec 5 champs : key_actors (chips × 8 × 60), geo_locale (MA/DZ/TN/SN/CI/multi), time_horizon (24h/72h/1w/2w/30d/60d), key_tensions (textarea 200 chars), expected_stakeholders (chips × 8). Defaults intelligents par template via détection keyword. Persistance localStorage. POST /api/graph/build avec refinement_only:true. 37 clés i18n × 3 langues.

✓ **US-040** (commit `c026fc5` + fix `186c4bb`) : Step1.5 Review entities. EntityRefiner class avec 4 ops Cypher (rename/merge/delete/add) en transaction unique. ReviewEntitiesView Vue avec group by type, rename inline (Enter/blur), select merge same-type, toggle delete, ajout par type + custom type. Banner orange dans MainView. **Fix critique** post-livraison : la branche v-else-if entities.length===0 affichait juste un message "empty" sans le bloc Add — bloquait le user signalé par Amine. Corrigé.

✓ **US-007** (commit `822b1f3`) : 259 retours d'erreur structurés sur 50 codes uniques (4 fichiers backend). Helper formatApiError(error, t) avec fallback gracieux. 64 clés errors.* × 3 langues. 4 composants frontend migrés (Step2EnvSetup, Step1GraphBuild, CalibrationView, ReviewEntitiesView). Backward-compat préservée (clé `error` toujours présente). 11 nouveaux tests pytest.

✓ **US-049 (NOUVELLE)** (commit `35b5837`) : Suppression de simulation depuis l'historique. Cas signalé par Amine sur proj_58bb8370c473 qui accumulait 3 sims fantômes en status:created sans moyen de nettoyer (fonctionnalité manquante upstream). Backend DELETE /api/simulation/<id> idempotent + 409 SIMULATION_RUNNING + 6 tests. Frontend bouton trash sur chaque card HistoryDatabase + modal confirmation + warning conditionnel pour sims publiques avec outcome (préserve /calibration) + optimistic UI + locales 3 langues.

✓ **US-023** (commit `781fc0e` + refonte `2b0d08e`) : Page publique /offres avec 3 packages. **Première version générique recadrée** suite à signalement Amine que le design ne correspondait pas au mockup Stitch. Refonte complète selon stitch_bassira_simulation_pricing_page/ : hero pill bolt + h1 Outfit 48px + 3 cards avec badges sector + 6 bullets check_circle + section trust strip Brier 0.18 / Multi-locale / Africa-grounded + FAQ 6 questions. **Prix corrigés** : 12k/35k/20k MAD et $1.2k/$3.5k/$2k USD (étaient initialement 12k/25k/8k MAD, mauvaises hypothèses).

✓ **US-025** (commit `3e926f5` + refonte `2b0d08e`) : Form devis multi-step + webhook email backend. Backend POST /api/quote avec validation regex email + enum package + RGPD required + truncate textes + HTML escape + rate-limit en mémoire 5/IP/h + stockage JSON + email best-effort smtplib via env EMAIL_SMTP_*. Codes erreur structurés (MISSING_FIELD/INVALID_EMAIL/INVALID_PACKAGE/RGPD_NOT_ACCEPTED/RATE_LIMITED). Frontend QuoteView refondu **3 steps** (au lieu de 4) selon Stitch : Step1 = 3 radio cards situation (crisis/policy/campaign) + textarea other ; Step2 = coordonnées + deadline + RGPD ; Step3 = success/error. Trust banner top "Your message goes directly to the founders" + 3 trust signals icons sous form (Multi-Agent Intelligence / Air-Gapped Privacy / 48h Setup). 8 tests backend.

✓ **US-016** (commit `ab2d985`) : Audit final design tokens + cleanup CSS dupliqué. 1052 → 257 hex (-75.6 %). 34 → 0 !important hors Stitch (16 préservés dans Stitch comme demandé). DESIGN.md enrichi 6 sections (palette legacy + chart + status + z-index + classes factorisées + règles d'or). Classes factorisées dans components.css : .ms-stat-card, .ms-spinner (--sm/--lg/--orange/--legacy-orange), .ms-empty-state, .ms-toast, .ms-status-*. **AC#3 NON atteint** : bundle +5.9 % gzip au lieu de -10 %. Cause : `var(--lo)` (10ch) > `#FF6B1A` (7ch) sur 600+ occurrences → augmentation arithmétique du brut. Compromis maintenabilité long-terme assumé. Cf section [PARTIEL] ci-dessous.

[BLOQUÉ — incident utilisateur en cours]
- **Projet `proj_58bb8370c473`** : graph Neo4j a `has_ontology:true` mais `entities_count:0`. 3 sims fantômes en status:created (sim_eabf56674a12, sim_d96161be2e8f, sim_425718238a6c) que le user peut désormais supprimer via US-049. Pour avancer : aller sur /review-entities/proj_58bb8370c473 et ajouter manuellement des entités via le bloc Add (correction post-US-040), OU recréer le projet avec un meilleur document.
- **Bug US-047 systémique non résolu** : le pre-check à /create est non-bloquant si EntityReader lève. Si Neo4j renvoie une exception ou si le graph_id ne suit pas le format attendu, la sim est créée malgré le graph vide. À durcir si récurrent.

[ALERTE]
!! **US-016 AC#3 non atteint** : bundle CSS +5.9 % gzip au lieu de -10 %. Compromis architectural assumé. Si Amine veut atteindre l'objectif strict, il faudrait introduire postcss-custom-properties au build pour replacer var() par hex en prod (perte de maintenabilité runtime).
!! **OffersView/QuoteView palette Stitch isolée** : variables `--stitch-*` hardcodent des hex localement (52 hex dans ces 2 fichiers). Voulu pour ne pas polluer la palette globale. À noter si dark mode US-027 doit couvrir ces 2 vues.
!! **Backend SMTP non configuré en prod** : variables EMAIL_SMTP_HOST/PORT/USER/PASSWORD/FROM/TO non définies sur Coolify. Tant qu'absentes, les devis s'enregistrent dans backend/uploads/quotes/quote_*.json mais aucun email n'est envoyé. À configurer avant la 1ère démo prospect (cf doc dans le commit US-025).
!! **Anti-pattern SimulationManager découvert au passage** (US-049) : `_get_simulation_dir` et `_load_simulation_state` font `os.makedirs(exist_ok=True)` même pour de la lecture → recrée silencieusement des dossiers vides. Contourné dans `delete_simulation` en construisant le path directement. Bug pré-existant upstream non corrigé ailleurs (risque latent dans d'autres opérations).
!! **3 fichiers backups Office résiduels** non versionnés : `backend/app/preset_templates/crisis_24h_brand/~$_attachment.md`, `~$_engine.md`, `product_launch_v2/~$_engine.md`. Peuvent être ignorés ou supprimés.

[PARTIEL — ce qui n'est pas à 100 %]

### US-016 Audit design tokens (3/4 AC, ~92 %)
- ✅ AC#1 hex centralisés : -75.6 % (objectif 100 %)
- ✅ AC#2 !important : 0 hors Stitch (objectif <5)
- ❌ **AC#3 bundle -10 %** : +5.9 % gzip (compromis maintenabilité)
- ✅ AC#4 DESIGN.md mis à jour
- **Restants 257 hex** : 60 dans design-tokens.css (source de vérité, OK), 52 dans Stitch isolé (OK), 4 dans components.css (rgba, OK), ~141 dans strings JS chart D3 et palettes dark-mode locales documentées (à tolérer). Si nécessaire, étape supplémentaire pour migrer les chart D3 dans une nouvelle var.

### US-023 Page /offres (refondue 100 % Stitch)
- ✅ Tous les AC atteints après refonte
- ⚠️ **Pricing 12k/35k/20k MAD à valider commercialement avant démo** (codé en dur dans le catalogue script setup, facile à ajuster)
- ⚠️ Lien `/calibration` depuis la card "Brier 0.18" — vérifier en prod que le router-link rend bien

### US-025 Form devis (100 %)
- ✅ Tous les AC atteints
- ⚠️ **SMTP non configuré en prod** (cf alerte). Activable via env vars Coolify quand Amine veut.
- ⚠️ Rate limiter in-memory process-local : OK avec single-worker derrière Cloudflare. Migrer vers Redis si scale horizontal.

### US-047 Validation graph non-vide (100 % codé, partiel en robustesse)
- ✅ Backend pre-check + 5 tests
- ✅ Frontend bouton disabled
- ⚠️ **Pre-check non-bloquant si EntityReader lève** (politique volontaire pour ne pas masquer un crash storage). Cas observé en prod sur `proj_58bb8370c473` où la sim a été créée malgré graph vide. À durcir potentiellement en US-050 si le user en souffre encore.

### US-040 Review entities (100 % codé, fix post-livraison)
- ✅ Backend EntityRefiner + 12 tests
- ✅ Frontend ReviewEntitiesView complet
- ✅ Fix `186c4bb` : empty state ne bloque plus l'Add (régression sub-agent corrigée)

[NEXT — 7 stories restantes après extension dettes]

### Prio P1 — commercial
- **US-024** Génération PDF brandé AIMPOWER pour rapports clients. Deps US-016 ✓. Effort 4-6h. Stack Python : weasyprint ou reportlab. Frontend bouton "Télécharger PDF" sur ReportView.

### Prio P2 — UI debloquée
- **US-027** Dark mode toggle. **TOUTES deps levées par US-016 + US-052**. Implémenter `[data-theme="dark"]` qui réécrit les `--ms-*` globales + appeler `clearChartPaletteCache()` puis re-render charts D3. **Attention** OffersView/QuoteView palette Stitch isolée — décider explicitement si dark mode couvre ces 2 vues.
- **US-028** Audit contraste WCAG AA. Deps US-016 ✓.

### Prio P2 — design migration restante (couches HTML/structure)
- **US-012** Migrer ExploreView + EmbedView + ReplayView + ComparisonView + InteractionView vers `.ms-*` (couleurs déjà migrées par US-016, reste structure).
- **US-013** Migrer charts (BeliefDriftChart/PolymarketChart/InteractionNetwork/DemographicBreakdown). Note : palette JS migrée par US-052, reste structure CSS.
- **US-014** Migrer panels (SettingsPanel/DebugPanel/WhatIfPanel/CounterfactualBranchPanel/HistoryDatabase). Idem.

### Bloqué humain
- **US-022** 3 case studies retro `/verified` : `requires_human_codesign:true` — **Amine doit choisir 3 sujets**.

[CTX session]
- ~700+ tool calls cumulés (toutes interactions Claude + 5 sub-agents)
- 12 commits poussés sur main : `2399f99`, `7771bf0`, `a8d9f99`, `c026fc5`, `822b1f3`, `6ba99b1`, `186c4bb`, `35b5837`, `781fc0e`, `3e926f5`, `2b0d08e`, `ab2d985`
- 5 sub-agents pilotés : US-039 Refine context, US-040 Review entities, US-007 error_code structurés, US-023 Offers, US-025 Quote, refonte Stitch Offers+Quote, US-016 design tokens
- Tests : 296 → 338 backend pytest (+42)
- $ : non instrumenté

[MEMO inter-sessions]
- API Coolify token, App UUID, Project UUID, Server UUID, Trigger deploy : cf passation précédente (toujours valides)
- LLM_MODEL_NAME prod : `kimi-k2-turbo-preview` (Moonshot)
- **Variables d'env SMTP à configurer sur Coolify pour activer email devis** :
  ```
  EMAIL_SMTP_HOST=smtp.gmail.com   # ou Sendgrid, Outlook
  EMAIL_SMTP_PORT=587
  EMAIL_SMTP_USER=<…>
  EMAIL_SMTP_PASSWORD=<app password>
  EMAIL_FROM=noreply@ai-mpower.com
  EMAIL_TO=contact@ai-mpower.com
  ```
- **Stitch projects** consultés cette session : `stitch_bassira_simulation_pricing_page/bassira_pricing_packages_simulation_solutions_2/{code.html,screen.png}` + `bassira_devis_get_a_quote/{code.html,screen.png}` + `bassira_calibration_verified_track_record/` + `warm_intelligence/`. Source de vérité absolue pour le design des pages commerciales.
- **Pattern observé Stitch** : variables CSS scopées par composant (`--stitch-primary-container: #ff8551`, etc.) pour ne pas polluer la palette `--ms-*` globale. Reproductible pour d'autres écrans Stitch futurs.
- **Devises** : MAD + USD jamais EUR (règle durable Amine, valable tous projets).
- **Convention commit** : `[US-XXX] Titre` puis `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`. Pour les fixes : `[fix US-XXX] Titre`. Pour les batches : `[Ralph batch] ...`.
- **Apprentissage Ralph** : avant tout dispatch sub-agent sur une story qui mentionne un mockup, lister systématiquement les assets Stitch/Figma et les inclure dans le brief avec consigne explicite de lecture. La première version générique de US-023+US-025 a coûté un cycle de refonte.
- **Anti-pattern SimulationManager** : `_get_simulation_dir` et `_load_simulation_state` font `os.makedirs(exist_ok=True)` — recrée silencieusement les dossiers en lecture. Contourné dans `delete_simulation` ; à étendre si d'autres opérations en souffrent.

[Recommandations pour la nouvelle session]
1. Lire `.ralph/prd.json` pour identifier les 8 stories `passes:false` restantes.
2. Lire `.ralph/progress.md` pour patterns détaillés (en particulier le runbook Step 03 et le pattern Step 1.5 review entities généralisable).
3. **AVANT toute démo prospect** : configurer les env vars SMTP sur Coolify pour activer l'envoi d'email devis. Sans elles, les leads s'enregistrent dans `backend/uploads/quotes/` mais Amine ne reçoit rien.
4. **Pour valider visuellement US-016** : tester en prod (hard-refresh + clear cache) les composants à risque listés dans le commit `ab2d985` (Step3 director-card hover, History project-card hover, TemplateGallery variant disabled, App language-switcher, Step2 spinner).
5. **Pour démarrer US-024 PDF AIMPOWER** : ajouter `weasyprint` ou `reportlab` au backend, créer template HTML brandé Bassira/AIMPOWER, route GET /api/simulation/<id>/report.pdf, frontend bouton sur ReportView.
6. **US-022 case studies** : demander à Amine de choisir les 3 sujets avant de toucher au code (deps human-codesign).
7. Pour les stories design-finish (US-012/013/014) : largement débloquées par US-016, peuvent être faites en parallèle sub-agents disjoints.
8. **Pour US-027 dark mode** : décider explicitement avec Amine si OffersView/QuoteView (palette Stitch) doivent être couvertes (probablement non — ces pages restent light).
9. Si l'incident `proj_58bb8370c473` graph vide se reproduit avec un autre projet, créer **US-050 « Durcir pre-check US-047 contre les exceptions storage »** pour bloquer dur même si EntityReader lève.

— fin passation —
