== PASSATION MiroShark 2026-04-29T18:00:00+01:00 ==

[ETAT]
- branche `main` `160376b` à jour avec `origin/main`
- prod **ONLINE** sur https://prospectives.ai-mpower.com (HTTP 200, build mode prod minifié)
- Coolify app status : `running:unknown` (Sentinel pas en healthcheck mais HTTP OK)
- 31/46 stories Ralph passes:true (67%)
- 296 backend tests passing (vs 167 baseline début session) · zéro régression
- npm run build : OK (~305 kB main / 90 kB gzip)
- 4 sub-agents pilotés en parallèle cette session : tous done & pushed
- branche worktree `agent-a189a386` toujours présente (legacy, non mergée)

[FAIT cette session — 14 stories Ralph + 5 fixes infra]
✓ **Fix DNS BuildKit** Coolify : systemd-resolved + buildkitd.toml configurés (côté serveur Linux), prod reverse-proxy fonctionne
✓ **US-036** Build prod Coolify : `Dockerfile` ajoute `RUN npm run build` avant CMD, root `package.json` ajoute script `start` (concurrently backend + `vite preview --host --port 3000`), `vite.config.js` ajoute block `preview:` avec proxy `/api`. Plus de Vite dev server en prod.
✓ **US-042** 5 scénarios canoniques pan-Afrique : `pmf_startup_tech` / `crisis_24h_brand` / `adcheck_pre_launch` / `policy_brief_stress` / `product_launch_v2`, chacun avec 2 fichiers (`01_attachment.md` brief customer + `02_engine.md` config technique : `simulation_requirement` >1500 chars FR + 6 agent system_prompts ancrés persona/sources + 5 director events injection text + verdict shape) + `<id>.json` template metadata. 30 personas nominaux pan-Afrique (Karim Casa, Aïcha Dakar, Ousmane Abidjan, Fatou Lagos, etc.). Helper `scripts/build_attachment_pdfs.py` (reportlab) si Amine veut PDFs plus tard.
✓ **US-019** TemplateGallery card She Start avec 3 sub-actions A/B/C (Replay/Twin/Blind Spot). i18n FR/AR/EN, click pré-remplit form simulation avec params variant.
✓ **US-021** Page publique `/calibration` (sub-agent en début de session) : SVG vanilla scatter + 4 stats cards + filters sidebar.
✓ **US-037** SimulationConfigGenerator parse `simulation_requirement` → time config adaptive (4 priorités : template recommended_settings > regex > keyword > default 72h). Court-circuite l'appel LLM `_generate_time_config` quand source ≠ default → -1 LLM call par préparation.
✓ **US-038** Per-agent system_prompts (200-400 mots déterministes ancrés persona/scenario) + propagation locale via `SimulationState.locale` au Wonderwall subprocess. Plan A (champ natif) + Plan B (prepend dans `persona` entre balises sentinelles) combinés.
✓ **US-011** Design migration `.ms-*` Step2EnvSetup + Step4Report + Step5Interaction (mode hybride classes legacy + .ms-* additives — code livré dans commit hybride accidentel `241ffd6`)
✓ **US-015** Design migration MainView + SimulationRunView + ReportView (idem, marker `f067038`). ProcessView.vue n'existe pas dans le repo (vérifié router/index.js).
✓ **US-041** ReportAgent narratif : 4 sections obligatoires FR auto-injectées (« Le pari a-t-il été tenu ? » / « Qui a basculé ? » / « Qu'est-ce qui nous a surpris ? » / « Qu'aurait-il fallu pour basculer le résultat ? ») + `PLAN_SYSTEM_PROMPT_BASE` templatable avec `{simulation_requirement}` + `_NARRATIVE_SECTIONS_REQUIRED` constants + garde-fou Python ré-injecte sections manquantes par exact title match.
✓ **US-043** Backend honore locale UI dans tous les LLM outputs sync : helper `backend/app/utils/locale_prompt.py` avec `LOCALE_FULL_NAMES`, `get_request_locale()` (lit `X-Bassira-Locale` header, default `fr`), `localize_system_prompt()` (append directive forte + sentinel idempotent + exception identifiants techniques PascalCase/UPPER_SNAKE_CASE/JSON keys). Wrappé sur 10 system_prompts (ontology + 4 graph_tools + 3 report_agent + 2 simulation). Frontend axios interceptor envoie le header.
✓ **US-044** LanguageSwitcher visibilité renforcée : `!important position:fixed` (combat le scoped style du composant), background `--ms-orange-soft` au lieu de blanc timide, border 1.5px orange, shadow orange teintée, animation lang-switcher-fadein 600ms, z-index 1500.
✓ **US-044b** Refonte navbar Home + Explore Playful & Soft : drop GitHub + Explorer (demande Amine), ajout Calibration + Scénarios (button scrollIntoView vers `#templates-gallery`), background cream au lieu de noir, hauteur 56px, settings btn circulaire avec hover rotate(40deg).
✓ **US-045** Backend `GET /api/calibration/simulations` paginé public : status=pending|evaluated|all + template + limit/offset, filtre sims completed avec/sans `outcome.json`, intègre `_resolve_template_name`, `_build_summary_first_words` (split intelligent ponctuation pour pas tronquer « U.S. »), 15 nouveaux tests.
✓ **US-046** Frontend `/calibration` section « Sims à évaluer » : cards `.ms-card` empilées, 4 boutons inline outcome (Called it/Partial/Wrong/N/A) avec backgrounds `--ms-mint/-peach/-rose/-bg-muted`, optimistic UI + revert si erreur, toast CSS-only 200ms, refresh auto brier-score après chaque évaluation, filtre rapide Pending (default)/Evaluated/Tous, pagination Précédent/Suivant. N/A est no-op (pas de DELETE outcome backend, documenté).

✓ **Quick fixes infra livrés** :
  - `a7df38f` axios baseURL `''` (était `http://localhost:5001` legacy fork upstream → 503 sur tout `/api/*` en prod)
  - `3c041ba` LanguageSwitcher CSS scoped override
  - `c8ec8fd` `/api/calibration/brier-score` expose `filters.templates_available` peuplé depuis preset_templates dir
  - `875e768` CalibrationView dropdown rend `tpl.name` au lieu de `tpl.id` (fix mismatch shape)
  - `160376b` consolidation prd.json US-041+US-045+US-046 passes:true

[BLOQUE]
- Aucun blocage technique majeur.
- Worktree `agent-a189a386` legacy toujours présent en local. PNG logo `/miroshark-nobg.png` (watermark des charts) montre encore l'ancien brand visuellement — à régénérer par un designer (TODO non bloquant).
- Auth `POST /api/simulation/<id>/outcome` côté frontend ne passe pas de `Authorization: Bearer` (état antérieur, pas une régression de cette session). Soit `MIROSHARK_ADMIN_TOKEN=""` en mode dev sur Coolify, soit reverse-proxy injecte le header. À valider en démo prospect.

[ALERTE]
!! Risque double-padding sur certains boutons après US-011/US-015 (mode hybride classes legacy + `.ms-*` additives) : `.action-btn .primary`, `.next-step-btn`, `.export-btn`, `.send-btn`, `.survey-submit-btn`, `.retry-config-btn`. Validation visuelle Playwright (US-010 pas encore implémentée) recommandée. Si conflit observé, retirer padding legacy en 2e passe rapide (~10 min).
!! Garde-fou US-041 : si LLM traduit/reformule les titres des 4 sections narratives malgré la consigne « do not translate », doublon EN+FR pourrait apparaître. `title_en` est pré-câblé en data, à activer pour matching fuzzy si Amine voit le doublon en démo.
!! Commit hybride `241ffd6` mal-attribué : `[US-038]` mais contient AUSSI les 6 fichiers Vue de US-011/US-015 (auto-stage harness multi-worktree). Marker `f067038` traçable. Resplit propre possible mais non strictement nécessaire — code en prod déjà.
?? `git reset HEAD~2` détecté dans le reflog (entre HEAD@{1} et HEAD@{2} de cette session) — origine inconnue (probablement un harness de sub-agent). Mon commit US-045/046 prd.json a dû être recovered via cherry-pick. Pas de perte finale mais comportement à surveiller en futures sessions multi-agents.

[NEXT prio P0]
1. **US-039** Step1 form enrichi : key actors (chips, max 8), geo locale (select MA/DZ/TN/SN/CI/multi), time horizon (adapté à US-037), key tensions (textarea), expected stakeholders. Defaults intelligents par template choisi. i18n + RTL via `inset-inline-*`.
2. **US-040** Step1.5 (nouveau) Review & refine entities entre graph build et profile generation : nouvelle vue `ReviewEntitiesView.vue`, liste entités par type avec actions inline (rename, merge dropdown, delete), ajout manuel, POST `/api/graph/entities/refine` (nouveau endpoint Neo4j), bouton Skip pour user pressés.

Avec ces 2 stories le **chantier 9-simulation-quality est entièrement clôt**.

[NEXT prio P1 — chantiers commerciaux]
- **US-023** Page publique `/offres` 3 packages (Crisis Drill 24h MAD/USD, Policy Brief Stress, Pre-Launch Adcheck) — Stitch mockup déjà disponible https://stitch.withgoogle.com/projects/2155552315589216528 (sharing public activé)
- **US-025** Form devis multi-step (deps US-023) — Stitch mockup dans le même projet
- **US-024** Génération PDF brandé AIMPOWER (deps US-016 design tokens audit final)
- **US-007** Backend renvoie `error_code` + frontend traduit via `errors.<code>` (~30 messages dans simulation.py + report.py + graph.py + share.py + settings.py + helper error-handler.js frontend)
- **US-010** Suite Playwright multi-locale (5 vues × 3 locales, vérifier pas de clé brute affichée, dir=rtl) — clôt la dette technique des AC Playwright différées de US-002→009 + US-019 + US-021 + US-046

[NEXT prio P1 — design cleanup]
- **US-012** + **US-013** + **US-014** design migration des composants restants (panels, charts, ExploreView/EmbedView/ReplayView/ComparisonView)
- **US-016** Audit final design tokens + cleanup CSS dupliqué (débloque US-024 + US-027 + US-028 cascade)

[NEXT prio P2 — UX polish]
- US-027 Dark mode toggle (deps US-016)
- US-028 Audit contraste WCAG AA (deps US-016)
- US-022 3 case studies retro publiables dans `/verified` — `requires_human_codesign: true` (Amine doit choisir 3 sujets)

[CTX session — démarrée ~2026-04-29 09:00, durée ~9h]
- ~600+ tool calls cumulés (toutes interactions Claude + 5 sub-agents)
- 18+ commits poussés sur main : `64cc393`, `d680a39`, `5f3638c`, `a7df38f`, `3c041ba`, `57bb150`, `d6d228a`, `ad0d4b3`, `6598271`, `241ffd6`, `f067038`, `4efc306`, `c8ec8fd`, `e6c5eb5`, `875e768`, `b07ec25`, `3dc3fb2`, `fd8af51`, `144a952`, `160376b` (et autres patches)
- 5 sub-agents pilotés : Calibration page (US-021), US-037, US-038, US-011+015 (hybride), US-045+046, US-041
- Bassira rebrand (déjà fait en session précédente) : marque user-facing partout, identifiant technique `miroshark` reste dans backend (MCP server key, loggers, repo GitHub)
- Tests : 167 → 296 passed (+129)
- $ : non instrumenté

[MEMO inter-sessions]
- API Coolify token : `mZV3t49u058ar3Gaq8POCHzjZ2LU7x3lJlRIPCXW5700c32d`
- App UUID Coolify : `u6pn5mr2pgi88s13un55pkzb`
- Project UUID : `e6kerffaobuwy2uo9n5sdihu` (Ventures)
- Server UUID : `etbh3cvs6qxr9l6w5hrcunj5` (localhost = host.docker.internal)
- Trigger deploy manuel : `curl -X GET -H "Authorization: Bearer <token>" "https://coolify.ai-mpower.com/api/v1/deploy?uuid=u6pn5mr2pgi88s13un55pkzb&force=true"`
- Webhook GitHub auto-deploy : actif sur `main` push
- Tunnel CF : `nahda-tunnel`, service `cloudflared-nahda.service`, config `/home/serveurai/.cloudflared/config-nahda.yml`
- Domain : `prospectives.ai-mpower.com` → `localhost:80` (Traefik) → container miroshark port 3000 (`vite preview` depuis US-036)
- LLM_MODEL_NAME prod : `kimi-k2-turbo-preview` (Moonshot, base_url `https://api.moonshot.ai/v1`)
- API key Moonshot rotated (la précédente avait fuité dans capture screenshot)
- **Brand split Bassira / miroshark depuis 2026-04-29** : marque user-facing = **Bassira** (بصيرة) sur tout le frontend (titres, hero, locales, watermarks, exports PNG, manifest PWA). Identifiant technique `miroshark` reste dans le backend : MCP server key, loggers `get_logger('miroshark.*')`, CSS class `.miroshark-banner`, default graph name `'MiroShark Graph'`, GitHub repo `aaronjmars/MiroShark`, app Coolify `miro-shark`. Logo `/miroshark-nobg.png` reste pour ne pas casser les watermarks.
- **Devises** : MAD + USD jamais EUR (règle durable Amine, valable pour tous projets futurs cf. memory `currency_usd_never_eur.md`).
- **Personas pan-Afrique** : 30 personas nominaux disponibles dans les 5 templates US-042 (réutilisables comme banque pour de futurs templates ou démos).
- **i18n** : storage key `bassira_locale` (renommé depuis `miroshark_locale` lors du rebrand). Langues : `fr` (default), `ar` (RTL avec Tajawal Google Fonts), `en`. Detection 4 niveaux : URL `?lang=` → localStorage → navigator.language → `fr`.
- **Stitch projects** : `https://stitch.withgoogle.com/projects/2155552315589216528` (Pricing + Calibration + Devis 3 screens dans 1 projet, sharing public activé). Projet exploration `880731974029839904` (variante calibration cyan/dark) à supprimer si voulu.
- **Sub-agents pattern observé** : déléguer fichiers DISJOINTS, leur dire `NE PUSH PAS` pour que je consolide, mais sub-agent peut commit. Risque : auto-stage harness multi-worktree peut bundler des fichiers non-attendus dans le commit (cf incident US-038/241ffd6). Solution future : git stash + commit paths explicites.
- **5 templates US-042 file shape** :
  - Racine : `backend/app/preset_templates/<id>.json` (metadata pour `/api/templates/list`)
  - Sous-dossier : `<id>/01_attachment.md` (brief customer prêt-à-PDF), `<id>/02_engine.md` (sim_requirement + 6 system_prompts + 5 director events + verdict shape), `<id>/README.md` (overview)
- **Time config matching** (US-037) : la regex backend reconnaît FR + EN sur `mois|months`, `semaines|weeks|sem`, `jours ouvrés|business days`, `jours|days|j`, `heures|hours|h`. Pour les 5 templates, le `simulation_requirement` mentionne explicitement la durée → priorité 2 regex couvre d'office (template recommended_settings priorité 1 pas encore câblée caller-side, story future).
- Quality gates Ralph : `cd frontend && npm run build` (must pass) + `cd backend && uv run pytest tests/ --tb=short -x` (must pass). Playwright `npx playwright test --reporter=list` non implémenté (US-010 pending).
- Convention commit : `[US-XXX] Titre` puis `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
- Branche stratégie : direct main avec commits atomiques par story (sub-agents OK).
- Compte GitHub : `Afristrat/MiroShark` (token gh CLI configuré).

[Recommandations pour la nouvelle session]
1. Lire `.ralph/prd.json` pour identifier les stories `passes: false` restantes (15 stories).
2. Lire `.ralph/progress.md` pour patterns détaillés et pièges déjà rencontrés.
3. Lire `AGENTS.md` racine pour le mode opératoire Ralph.
4. **AVANT de toucher au code** : vérifier que la prod est UP (`curl -o /dev/null -w "%{http_code}" https://prospectives.ai-mpower.com/`).
5. **Pour valider l'argument commercial /calibration** : marker manuellement les 2 sims complétées en prod via la nouvelle UI « Sims à évaluer » → Brier doit monter en temps réel.
6. **Pour la démo Maghreb/Afrique** : tester la bascule FR/AR via le LanguageSwitcher floating top-right → tout l'UI bascule en arabe avec dir=rtl + Tajawal font + brand بصيرة.
7. **US-039 + US-040 prio next** pour clôturer chantier 9-simulation-quality.
8. **Skipper US-022** (3 case studies retro) tant qu'Amine n'a pas choisi les 3 sujets.
9. Pour les stories volumineuses (US-007, US-027 cascade), déléguer à des sub-agents en parallèle avec fichiers disjoints. Si auto-stage suspect, brief le sub-agent avec `git stash` avant commit + commit paths explicites.
10. Si modifs locales sur prd.json + progress.md : commit en batch après que tous les sub-agents finissent pour éviter les conflits inter-agents.

— fin passation —
