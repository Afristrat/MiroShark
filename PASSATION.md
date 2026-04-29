== PASSATION MiroShark 2026-04-29T09:35:00+01:00 ==

[ETAT]
- branche main `aa9eb40` à jour avec origin · t ✓ (174+8+12+5 pytest, npm build OK)
- prod prospectives.ai-mpower.com **DOWN** depuis ~07:34 ·
  status Coolify=`exited:unhealthy`, HTTP 404 sur /
- worktree design Playful & Soft existe : `.claude/worktrees/agent-a189a386` (branche `worktree-agent-a189a386`) — non mergé sur main
- 19/35 stories Ralph passes=true sur main · 16 restantes

[FAIT cette session]
✓ US-000 Sécuriser pytest quality gates (markers integration/slow/neo4j + smoke tests)
✓ US-001 Setup vue-i18n@11 + structure locales fr/ar/en + détection 4 niveaux
✓ US-002 Externaliser Home + ScenarioSuggestions + TrendingTopics + TemplateGallery (~67 chaînes, ar.json complet)
✓ US-003+004+005+006 Externaliser Step1-5 + vues simulation + Explore/Embed + 12 panneaux/charts (~235 chaînes, ~1230 entrées JSON)
✓ US-017+018 Backend template She Start cohort_replay 3 variants A/B/C + seed_template.md + 8 archetypes mentors + 5 tests pytest
✓ US-020 Backend /api/calibration/brier-score (12 tests, 3 couches, hypothèse template_id documentée)
✓ US-026 Favicon multi-formats + manifest PWA + apple-touch-icon
✓ US-029 Composable useScrollFadeIn (IntersectionObserver + prefers-reduced-motion) sur 3 vues
✓ US-030 Skeletons .ms-skeleton sur ExploreView + SimulationView
✓ US-031+032+033 Hardening prod : SECRET_KEY (relâché en warn vu PB Coolify), CORS_ORIGINS whitelist, FLASK_DEBUG=false default
✓ US-034 Security headers middleware (X-Frame-Options + CSP + HSTS + Referrer-Policy + Permissions-Policy, /share et /embed exemptés)

[BLOQUE]
✗ Coolify deploy fail systémique sur DNS Docker BuildKit
  Erreur exacte (deployment esgv7bbpi… 08:35:40) :
    failed to solve: ghcr.io/astral-sh/uv:0.9.26 :
    dial tcp: lookup ghcr.io on 127.0.0.53:53: server misbehaving
  Fait : `/etc/docker/daemon.json` configuré avec dns 1.1.1.1+8.8.8.8 ✓
    → `docker run curl https://api.github.com/zen` retourne OK
    → MAIS BuildKit (utilisé par `docker compose build`) utilise un autre résolveur
       (probablement `127.0.0.53` du host = systemd-resolved)
  À tester côté serveur : `nslookup ghcr.io` (probable timeout)
  Fix candidats :
    a. `sudo nano /etc/systemd/resolved.conf` → `DNS=1.1.1.1 8.8.8.8` + `sudo systemctl restart systemd-resolved`
    b. `/etc/buildkit/buildkitd.toml` config DNS pour buildkitd
    c. Coolify : Server Settings → Custom DNS server (1.1.1.1)

[ALERTE]
!! prod offline depuis 2h30 (au moment de la passation) — 0 simulations en cours, pas de revenu impacté car pas de clients actifs, mais le track-record /verified ne progresse pas
!! 19 commits utiles bloqués sur main, code prêt mais pas exposé
!! BuildKit DNS bloqueur affecte AUSSI les futurs deploys d'autres apps (qalem, dto, etc.) si elles rebuild
!! Le sub-agent A i18n a externalisé surgicalement Step4Report (5143l) et SettingsPanel (1576l) — texte avancé interne pas couvert (acceptable pour MVP)
!! La worktree design Playful & Soft (agent-a189a386) n'a JAMAIS été mergée sur main — `frontend/src/design-tokens.css` et `frontend/src/styles/components.css` n'existent PAS sur main → les classes `.ms-skeleton`, `.ms-anim-fade-in`, `.ms-card`, `.ms-btn-*` référencées par US-026/029/030 et i18n sub-agents sont actuellement orphelines (CSS no-op au runtime)
?? Le commit `aa9eb40` (relâchement Config.validate SECRET_KEY) est anti-US-031 par esprit — à durcir une fois la cause Coolify env-var injection résolue

[NEXT prio P0]
1. Fix DNS BuildKit (cf. [BLOQUE] options a/b/c) → relancer deploy Coolify → prod revient online
2. Merger worktree `agent-a189a386` sur main (rebase ou cherry-pick), surtout `frontend/src/design-tokens.css`, `frontend/src/styles/components.css`, `frontend/DESIGN.md` — sinon le design Playful & Soft + skeletons + scroll fade-ins ne s'affichent pas
3. Désactiver Coolify env-var "Build time" sur SECRET_KEY/FLASK_ENV/CORS_ORIGINS (les marquer "Runtime only" via UI Coolify ; warning aperçu dans les logs)

[NEXT prio P1 — 16 stories Ralph restantes]
- US-007 Backend renvoie error_code (refactor ~30 messages dans simulation.py + report.py + graph.py + share.py + settings.py + helper error-handler.js frontend) ~6h
- US-008 Composant LanguageSwitcher.vue dans navbar + persistance localStorage ~2h
- US-009 RTL complet : CSS logical properties (margin-inline-start) sur 15+ composants + polices arabes (Tajawal/Almarai) ~6h (ar.json déjà rempli par sub-agent A)
- US-010 Tests Playwright multi-locale (5 vues × 3 locales, vérifier pas de clé brute affichée, dir=rtl) ~3h
- US-011→US-015 Migrer 26 fichiers Vue restants au design Playful & Soft (overrides ciblés ou refonte complète selon profondeur) ~12h
- US-016 Audit final design tokens + cleanup CSS dupliqué (-10% bundle CSS attendu) ~3h
- US-019 Frontend Template Gallery card She Start avec UI custom A/B/C (dépend US-017 ✓) ~3h
- US-021 Frontend page /calibration avec D3 calibration plot + stats (dépend US-020 ✓) ~4h
- US-022 3 case studies retro publiables (REQUIERT INTERVENTION HUMAINE Amine pour choix sujets) ~4h
- US-023 Page publique /offres avec 3 packages Crisis Drill / Policy Brief / Pre-Launch Adcheck ~3h
- US-024 Génération PDF brandé AIMPOWER (export simulation report) ~5h
- US-025 Form devis + webhook email SMTP ~3h
- US-027 Dark mode toggle (prefers-color-scheme + override) ~4h
- US-028 Audit contraste WCAG AA + corrections via axe-core Playwright ~2h

[CTX session]
- durée ≈ 8h (00:00–09:35)
- ~150 tool calls
- 5 sub-agents lancés (4 finis, 1 design en worktree non mergé)
- 8 commits sur main : `c1bb387` US-000, `d790032` US-001, `95e8c48` US-031+032+033, `f0b6f3d` compose env vars, `7b4f0e5` US-017+018, `aa9eb40` US-031 relax, et autres groupés
- $ : non instrumenté
- branches : `main` (à jour) + `worktree-agent-a189a386` (non mergée)

[MEMO inter-sessions]
- API Coolify token (rotation possible) : `mZV3t49u058ar3Gaq8POCHzjZ2LU7x3lJlRIPCXW5700c32d`
- App UUID Coolify : `u6pn5mr2pgi88s13un55pkzb`
- Project UUID : `e6kerffaobuwy2uo9n5sdihu` (Ventures)
- Server UUID : `etbh3cvs6qxr9l6w5hrcunj5` (localhost)
- Trigger deploy : `curl -s -X GET -H "Authorization: Bearer <token>" "https://coolify.ai-mpower.com/api/v1/deploy?uuid=u6pn5mr2pgi88s13un55pkzb&force=true"`
- LLM_MODEL_NAME courant : `kimi-k2-turbo-preview` (Moonshot, kimi-k2.6 imposait temperature=1)
- LLM_BASE_URL : `https://api.moonshot.ai/v1`
- API key Moonshot du screenshot Settings : `sk-m8R8aQpjZH9KZ45lcEPeOa8Vdz04ID65BiH0BNdCLlWymV6Z` — **À ROTATER** (visible dans capture envoyée à Claude)
- Tunnel CF : `nahda-tunnel` (ID `7156c3f9-07a4-472d-963a-efaf59769d40`), service systemd `cloudflared-nahda.service`, config `/home/serveurai/.cloudflared/config-nahda.yml`
- Sous-domaine : `prospectives.ai-mpower.com` → `localhost:80` (Traefik) → container miroshark port 3000
- Domain Coolify pour app : `http://prospectives.ai-mpower.com:3000` (PAS https — CF gère le TLS, sinon boucle redirect)
- Quality gates Ralph imposées par config :
    `cd frontend && npm run build`
    `cd backend && uv run pytest tests/ --tb=short -x`
    `npx playwright test --reporter=list` (UI stories)
- Convention commit : `[US-XXX] Titre` puis `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
- Branche stratégie (choix utilisateur 4C) : direct main avec commits atomiques par story
- Compte GitHub Afristrat : token gh CLI configuré, scopes 'gist', 'read:org', 'repo', 'workflow'
- Git Credential Manager Windows : foire avec git push background → tuer process zombies + `gh auth setup-git` pour reconfigurer
- Fichiers Ralph : `.ralph/prd.json` (35 stories, source de vérité passes=true/false), `.ralph/plan.md` (ordre + signal `<promise>COMPLETE</promise>`), `.ralph/progress.md` (log + patterns/pièges), `AGENTS.md` racine (guide Ralph), `backlog.yaml` (format ralph-loop.sh)
- Convention dossier preset_templates : `backend/app/preset_templates/<id>.json` + `<id>/` sous-dossier pour seed/personas/README
- Service Coolify Compose : Coolify injecte env vars dans TOUS les services compose → `NEO4J_PASSWORD` côté Coolify devient setting Neo4j `PASSWORD` qui crashe strict_validation → fix `NEO4J_server_config_strict__validation_enabled=false` déjà en place dans compose
- Compose : `container_name:` doit être omis (Coolify gère, sinon DNS interne casse)
- Compose : utiliser `expose:` pas `ports:` (conflits multi-app sur même hôte)

[Recommandations pour la nouvelle session]
1. Lire `.ralph/prd.json` pour identifier les passes=false (16 stories)
2. Lire `.ralph/progress.md` pour patterns et pièges
3. Lire `AGENTS.md` racine pour le mode opératoire
4. **AVANT de toucher à quoi que ce soit côté Ralph** : vérifier que la prod est UP. Si DOWN, fix DNS BuildKit en priorité absolue (cf. [BLOQUE])
5. **Avant de continuer le loop Ralph** : merger la worktree `agent-a189a386` sur main pour activer `.ms-*` classes
6. Skipper US-022 (case studies) tant qu'Amine n'a pas choisi les 3 sujets
7. Pour les stories volumineuses (US-011→015 design migration, US-007 error codes) : déléguer à des sub-agents en parallèle avec fichiers disjoints

— fin passation —
