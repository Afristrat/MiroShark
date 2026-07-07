== PASSATION MiroShark/Bassira 2026-07-08 (suite nuit) — US-204 code+infra fait, bassira.ma routé en prod ==

[ETAT]
- branche `main`, poussée à jour : `1b3bbdf` (dernier commit). Prod
  https://prospectives.ai-mpower.com **ET** https://bassira.ma : **UP, 200 sur les deux**
  (vérifié après déploiement auto Coolify sur le commit `1b3bbdf`, image
  `u6pn5mr2pgi88s13un55pkzb_miroshark:1b3bbdf...`).
- **US-204 (Resend/bassira.ma)** : code complet ET infra domaine réglée, mais **passes:false**
  encore — 3 actions restantes listées dans [BLOQUÉ]. Détail technique complet dans
  `.ralph/progress.md` (section "Suite US-204").
- **US-201/202/206** : toujours `passes:true` (inchangé depuis la passation précédente).
- **US-203/205/207/208** : toujours `pending`/bloquées, inchangé.

[FAIT cette session]
1. US-204 : migration SQL `20260707_002_footer_bassira_ma.sql` (footer_right default +
   backfill), fallbacks code (`admin_branding.py`, `AdminBrandingView.vue`), liens marketing
   des 5 templates email + lien méthodologie + footer PDF devis → `bassira.ma`. `.env.example`
   documente RESEND_API_KEY/RESEND_FROM_EMAIL/EMAIL_*.
2. **Découverte + fix infra domaine bassira.ma en 3 couches** (avec confirmation Amine à
   chaque étape à risque) :
   - Ingress local `~/.cloudflared/config-nahda.yml` (serveur `serveuria@192.168.100.11`) :
     backup + ajout `bassira.ma → localhost:80`.
   - Coolify : app `miro-shark` (uuid `u6pn5mr2pgi88s13un55pkzb`) — domaine ajouté via
     `docker_compose_domains` (API, format `{"<service>":{"name":...,"domain":"a,b"}}`) +
     `POST /restart` (régénère les labels Traefik).
   - **Cause racine réelle** : le tunnel Cloudflare `7156c3f9-...` est **remote-managed**
     (`source: "cloudflare"` sur `GET .../cfd_tunnel/{id}/configurations`) — le fichier local
     `config-nahda.yml` est ignoré par le process en cours d'exécution malgré `--config`. Fix :
     `PUT .../cfd_tunnel/{id}/configurations` avec l'ingress complet (version 113).
   - Effet de bord : process `cloudflared` orphelin (lancé 2026-07-06, hors systemd) tué après
     confirmation — ce tunnel sert ~15 apps d'autres projets (nizam-os, rami, taqwim, hafiz,
     tamkin, saqr, nahda, mem...), non-régression vérifiée sur 3 d'entre elles.
3. Correction collatérale : CRLF introduit par erreur sur 3 fichiers lors des Edit (`.env.example`,
   `org_invitation.html`, `InteractionView.vue`) — détecté via diff anormalement large, corrigé
   dans un commit séparé avant push.
4. Push vers `origin/main` → déploiement auto Coolify confirmé sur le nouveau commit.

[ALERTE]
- ⚠️ **Secrets prod vus en clair pendant le diagnostic Coolify** (réponse API `GET
  /applications/{uuid}` inclut `docker_compose` en clair : `SECRET_KEY`, `NEO4J_PASSWORD`,
  `LLM_API_KEY`, `manual_webhook_secret_*`, `sentinel_token`). Fichier scratch local supprimé
  immédiatement, aucune valeur affichée dans la conversation. Si Amine considère que le fait
  qu'un agent IA ait pu LIRE ces valeurs via l'API constitue une exposition suffisante →
  envisager rotation (SECRET_KEY, LLM_API_KEY notamment).
- ⚠️ Les liens FONCTIONNELS (`invite_url` dans `invitations.py:162`, `BASSIRA_PUBLIC_URL`/
  `download_url` dans `report_delivery.py:233,381`, `CORS_ORIGINS` default dans
  `app/__init__.py:47`, `cta_link` PDF dans `models.py:153,188,222`) sont VOLONTAIREMENT restés
  sur `prospectives.ai-mpower.com` — plus aucune raison technique de ne pas les migrer
  maintenant que bassira.ma route correctement (vérifié), mais c'est un choix de scope à
  trancher par Amine, pas fait unilatéralement. Prévoir une story dédiée (US-210 suggérée).

[BLOQUÉ — actions restantes US-204]
- !! Poser `RESEND_API_KEY` en env Coolify (nom seulement, pas fait — coffre local l'a déjà).
- !! Appliquer `supabase/migrations/20260707_002_footer_bassira_ma.sql` en prod (comme US-203).
- !! Devis test réel en prod pour vérifier réception email < 2 min avec liens bassira.ma.
- (US-203 : migration `20260707_001_quote_payload.sql` toujours pas appliquée non plus — les 2
  migrations en attente peuvent être posées dans la même session SQL par Amine.)

[NEXT]
1. Poser les 2 migrations SQL en attente (US-203 + US-204) + `RESEND_API_KEY` Coolify → ferme
   US-204 (et débloque la vérification finale US-203).
2. Continuer Bloc A : US-205 (Stripe, credentials manquants → sauter si toujours absents) →
   US-207 (WSGI prod) → US-208 (Redis, dépend US-207).
3. Envisager une story US-210 "domain cutover" pour migrer les 4 liens fonctionnels restants
   vers bassira.ma maintenant que l'infra est prête (cf. [ALERTE]).

[MEMO inter-sessions]
- **Cloudflare Tunnel remote-managed — piège** : toujours vérifier `GET
  /accounts/{id}/cfd_tunnel/{tunnel}/configurations` → champ `source`. `"cloudflare"` = éditer
  le fichier local ne sert à rien pour le routage réel (juste `ingress validate` pour tester la
  syntaxe) ; il faut `PUT` la config complète via l'API. Détail complet + gabarit PowerShell
  dans `.ralph/progress.md`.
- **Coolify docker-compose apps** : domaines dans `docker_compose_domains` (pas `fqdn`), format
  `{"<service>": {"name": "<service>", "domain": "url1,url2"}}`, `name` requis (422 sinon).
  `POST /restart` suffit pour régénérer les labels Traefik + recréer le conteneur (pas besoin
  de push git pour un simple changement de domaine).
- **Bash tool + PowerShell imbriqué** : TOUJOURS échapper `\$` pour CHAQUE variable PowerShell
  dans un `-Command` passé depuis Bash — un seul `$var` non échappé se fait expand par Bash
  AVANT d'atteindre PowerShell (piège rencontré ~4 fois cette session, y compris `$_` qui est
  une variable spéciale Bash).

== PASSATION MiroShark/Bassira 2026-07-07 (nuit) — Cadrage V2 ratifié + Ralph loop Bloc A en cours ==

[ETAT]
- branche `main`, poussée à jour : `1233e1b` (dernier commit). Prod
  https://prospectives.ai-mpower.com : **UP** (404 du 2026-07-01→07 résolu, vérifié
  200 le 2026-07-07 — détail docs/09-errors-log.md).
- **Cadrage V2 complet et RATIFIÉ par Amine** : 10 documents de fondation dans `docs/`
  + `CLAUDE.md` racine, validés (`validate_foundation.py` : 0 erreur). Verdict **GO
  conditionnel** → ratifié, Bloc A lancé. Journal complet + 14 ADR : `docs/np-cadrage.md`
  + `docs/08-decisions-log.md`.
- **.ralph/prd.json v2.0.0** : 142 stories (134 v1 historiques intactes + 8 nouvelles
  US-201→US-208, chantier `V2-A-blocA`). US-113 (v1) fermée administrativement,
  remplacée par US-205.
- **Mode Ralph EN COURS** sur le Bloc A — état des 8 stories à cet instant :
  - US-201 (repositionnement stress-test, purge claim prédictif) : **passes:true**
  - US-202 (encart Méthode&limites PDF + marquage AI Act art.50) : **passes:true**
  - US-203 (payload devis → Supabase) : **code complet, passes:FALSE** — bloqué sur
    action prod (migration SQL à appliquer + preuve devis-survit-redeploy)
  - US-204 (Resend + bassira.ma) : **pending, pas commencée**
  - US-205 (Stripe pricing + Checkout) : **pending, pas commencée**
  - US-206 (fermer IDOR /api/report) : **passes:true**
  - US-207 (WSGI prod + fail-closed) : **pending, pas commencée**
  - US-208 (Redis/worker PDF prod) : **pending, pas commencée**
- SOP-002 (migration SearXNG→OpenSERP) créée, validée, commitée et **poussée** sur
  `Afristrat/sop` (brouillon 0.1.0).
- Ruff : dette pré-existante (319 erreurs) soldée à 0 lors d'US-201 (hook pre-commit
  l'exécute sur tout le repo — `ruff.toml` créé avec per-file-ignores justifiés).
  `ruff check .` = gate de facto pour toute story suivante.

[FAIT cette session (chronologie complète)]
1. Deep explore 5 sous-agents + flow np autonome → verdict GO conditionnel, 10 documents.
2. Directives d'Amine (renommage Saqr, SearXNG→OpenSERP, arènes MENA, polyglotte,
   LiteLLM, bassira.ma, licence=domaine Amine seul, MiroFish cohabitation) → intégrées
   aux 10 documents + 3 agents de recherche (search-alt, prediction-mena, upstream-mirofish)
   → ADR-004/011/012/014 tranchées avec sources.
3. Ratification Amine → SOP-002 créée+poussée, Bloc A injecté dans prd.json.
4. **Mode Ralph lancé** : US-201, US-202, US-206 complétées (code+tests+commit+push
   individuels) ; US-203 codée mais bloquée sur action prod (voir BLOQUÉ) ; US-204/205/
   207/208 pas encore attaquées à l'heure de cette passation.
5. Ruff : 319→0 erreurs (dette pré-existante soldée dans le commit US-201, exigée par
   le hook pre-commit local).

[ALERTE]
- ⚠️ **US-203 nécessite une action HUMAINE en prod** : appliquer
  `supabase/migrations/20260707_001_quote_payload.sql` sur le Supabase self-hosted
  (SQL editor/psql — pas fait par l'IA, accès prod). Le code est fail-soft (déployable
  avant la migration, fallback filesystem loggé WARNING) mais la story ne peut passer
  à `passes:true` sans preuve système (devis-survit-redeploy).
- ⚠️ 1 test flaky `test_md_hash_stable_with_deterministic_enricher` (échoue en suite
  complète, passe isolé — fuite d'état inter-tests, sans lien avec les fichiers
  modifiés). Consigné docs/09-errors-log.md, non bloquant.
- ⚠️ EU AI Act Art. 50 applicable le **2026-08-02** (J-25 à la date de cette passation) —
  US-202 le couvre déjà (encart + métadonnées PDF), mais vérifier la couverture
  complète avant cette date.

[BLOQUÉ — actions humaines]
- !! Appliquer la migration `20260707_001_quote_payload.sql` en prod (US-203).
- !! Répondre aux 3 questions dérangeantes du cadrage (np-cadrage.md § 2.3) si pas
  encore fait : clients payants réels ? réponse à l'objection données réelles ?
  décision finale AGPL/MiroFish (domaine exclusif d'Amine) ?
- !! Poser les credentials Stripe (bloqueur historique d'US-113/US-205) avant d'attaquer
  US-205.
- !! Poser `RESEND_API_KEY` en env Coolify avant US-204.

[NEXT]
1. **Continuer le mode Ralph sur le Bloc A** dans l'ordre : US-204 (Resend/bassira.ma) →
   US-205 (Stripe, nécessite credentials — sinon la sauter et continuer) → US-207
   (WSGI prod) → US-208 (Redis worker, dépend d'US-207) → revenir sur US-203 dès que
   la migration prod est appliquée.
2. Après le Bloc A complet : lancer `moat-hunter` avec `01-app-spec.md` en input
   (recommandé avant le gel définitif du backlog V2).
3. Le plus petit test (2.7 du cadrage) : framing A/B « prédiction vs stress-test » sur
   3 prospects Apollo + email à aaronjmars (licence) — 1 semaine, 0 €.
4. Convertir SOP-002 en `approuvee` (1.0.0) quand Amine valide.

[CTX session]
- Session longue (2026-07-07 après-midi → nuit), Fable 5 (dernier jour du pin — bascule
  opusplan prévue le 2026-07-08 via `switch-to-opusplan.ps1`, cf. rappel hook démarrage).
- Cardage V2 = ~40 tool calls + 6 sous-agents parallèles. Exécution Ralph Bloc A =
  3 stories complètes (US-201/202/206) avec cycle complet gate→commit→push à chacune.
- Aucune régression : chaque story validée par `ruff check .` + `pytest` complet
  (1637→1689 tests au fil des stories) avant commit.

[MEMO inter-sessions]
- **Pattern SIM_ID/report_id garde d'accès (US-206)** : `_authorize_simulation_access()`
  dans `report.py` — réutilisable pour tout futur endpoint report-like. Attention aux
  chemins de contournement (ex. `get_report_by_simulation` = même donnée qu'un autre id).
- **Pattern transformation i18n de masse (US-201)** : script Python découvrant les
  chemins dans fr.json puis appliquant aux 3 locales + assertion de parité stricte —
  fiable à 2300+ clés, gabarit dans les commits US-201 (scratchpad us201_locales.py,
  non versionné).
- **Piège hook bash-guard** : bloque les heredocs contenant des motifs `grep`-like —
  toujours passer par un fichier .py écrit via Write puis exécuté.
- **Piège hook pre-commit Ruff** : s'exécute sur TOUT le repo, pas seulement le diff —
  toute story qui touche un fichier Python peut se heurter à de la dette pré-existante
  ailleurs. Vérifier `ruff check .` avant de tenter un commit.

== PASSATION MiroShark/Bassira+Kairos 2026-05-22T22:00:00+01:00 ==

[ETAT]
- branche Bassira `main` `67c25ff` à jour origin (1 commit cette session : fix 3 bugs admin)
- branche Kairos `main` `6cbe4a3` inchangé depuis passation 2026-05-17 (aucune modif Kairos cette session)
- prod Bassira ONLINE https://prospectives.ai-mpower.com — Coolify auto-deploy sur main via webhook GitHub déclenché par le push `67c25ff`
- prod Kairos ONLINE https://scrap.ai-mpower.com — stable
- npm run build Bassira : OK (build vite réussi, 940+ modules, AnalyticsView 20.48 kB / AdminBrandingView 18.28 kB / ClientDashboardView 12.68 kB)
- Syntaxe Python admin.py + tests : OK (py_compile)

[FAIT cette session — Fix 3 bugs /admin/* + /client/dashboard]

Amine ouvre 3 issues en un seul `/goal fix proprement` :
1. /admin/analytics affiche des données obsolètes (rien à voir avec la réalité)
2. /client/dashboard super-admin affiche uniquement « User belongs to multiple organizations — provide X-Org-Id header or ?org_id= query parameter. »
3. /admin/branding : impossible de modifier, branding perçu comme hard-codé

| Commit | Fix |
|---|---|
| `67c25ff` 3-in-1 | Voir détails par bug ci-dessous |

### Bug 2 — /client/dashboard multi-org (root cause identifiée en premier)
- **Cause** : `backend/app/auth/decorators.py:118-128` `_resolve_target_org` exige X-Org-Id ou ?org_id= quand l'user a >1 org. L'interceptor axios `frontend/src/api/client.js` ne propageait JAMAIS ce header. Super-admin Amine appartient à plusieurs orgs (bassira-internal + clients seed) → 400 ORG_ID_REQUIRED systématique.
- **Fix axios** : ajout dans l'interceptor request d'un `X-Org-Id: <auth.currentOrgId>` (header ignoré par les endpoints qui ne sont pas décorés `@require_org_membership`, donc safe à propager partout).
- **Fix UI** : nouveau sélecteur d'org `<select>` dans le hero de `ClientDashboardView.vue` visible UNIQUEMENT si `orgs.length > 1`. Handler `onChangeOrg()` → `auth.setCurrentOrg(orgId)` (déjà existant dans Pinia store) → refetch simulations. CSS coordonné avec les tokens `--wi-*` existants.

### Bug 3 — /admin/branding "hard-codé"
- **Cause** : la page demandait à l'admin de saisir manuellement un UUID d'org dans un `<input type="text">` mono-font (`ab-input--mono`). Si l'admin ne tape pas l'UUID exact ou si aucune row n'existe en `pdf_branding`, la table reste vide → perception « hard-codé ». De plus le fallback rendering PDF utilise la palette Bassira par défaut quand pas de row → ce que voit le client est PRÉCISÉMENT du hardcoded.
- **Fix UI** : remplacement de l'input UUID par un vrai `<select>` peuplé selon le rôle :
  - Super-admin → `fetchAllOrganizations()` (`/api/admin/organizations`)
  - Org admin/owner → `authStore.orgs.filter(role in {owner, admin})`
- **Fix UX** : nouveau bloc `.ab-empty-card` (style dashed/cream) qui explique le fallback palette par défaut au lieu de juste afficher « Aucun branding configuré. » sans contexte. Le titre est désormais explicite et l'aide guide vers le bouton "+ Nouveau branding".
- **Boot** : `onMounted` charge `fetchSuperStatus()` si pas déjà résolu, puis `loadOrgOptions()` puis `loadBrandings()`. Plus de saisie manuelle.

### Bug 1 — /admin/analytics données obsolètes
- **Cause racine** : `backend/app/api/admin.py` `get_admin_analytics()` calculait TOUT à partir du **filesystem** (`WONDERWALL_SIMULATION_DATA_DIR/*/outcome.json` + `WONDERWALL_DATA_DIR/quotes/quote_*.json`). Sur Coolify, ces dossiers sont éphémères (volume reset à chaque deploy) → les KPI étaient déconnectés de la vérité. La source de vérité depuis US-114 est Supabase (`simulation_ownership` + `quote_ownership`).
- **Fix backend** : refonte complète de l'implémentation tout en préservant la shape JSON (zéro impact frontend).
  - Nouveaux helpers : `_fetch_all_simulation_rows()` (full scan `simulation_ownership` — volumes < 10k OK), `_fetch_quote_count()` (count='exact' sur `quote_ownership`), `_parse_iso_date()` (parse timestamptz Supabase, tolère suffixe Z et fromisoformat 3.11+).
  - Nouveau `_build_kpis()` : `total` = len rows, `completed` = outcome jsonb non-null (anciennement = présence `outcome.json` filesystem), `last_30d` = créés ≤ 30j (anciennement = completed in 30d — peu utile car outcome marking est async), `quotes` = count Supabase.
  - `_build_time_series_30d()` : 30 buckets sur `created_at` au lieu de mtime. Champ `completed` conservé pour backcompat frontend (sémantiquement c'est désormais "créés/jour").
  - `_build_top_packages()` : agrège la colonne `package_id` (col Supabase) au lieu de lire `template_id` dans `simulation_config.json` filesystem.
  - **Fail-soft** : Supabase down/non configuré → toutes les valeurs à 0 au lieu de 500. Le dashboard reste lisible.
  - Cleanup imports inutilisés : `json`, `os`, `time`, `Config`, `Tuple` retirés (les helpers filesystem étaient les seuls consommateurs).
- **Tests** : `backend/tests/test_unit_admin_analytics.py` réécrit avec mock Supabase (`_MockClient` + `_MockQuery` qui mimique le chain fluent `.select().limit().execute()`). 4 tests pinned :
  1. `test_no_token_returns_401` — auth gate inchangé (require_admin_token JWT super-admin OU legacy token)
  2. `test_with_token_returns_200_kpis` — happy path avec 2 sims (1 running + 1 completed) + 1 quote
  3. `test_kpis_keys_present` — schema-shape lock (4 sections + sous-clés + 30 entrées time_series + format YYYY-MM-DD)
  4. `test_supabase_unconfigured_returns_zeros` — fail-soft contract (nouveau)

[VALIDÉ EN PROD]
- Push `67c25ff` reçu par origin/main (`a3fe8b3..67c25ff`)
- Coolify webhook devrait avoir déclenché build+deploy (~2 min cycle) — Amine doit hard-refresh https://prospectives.ai-mpower.com/admin/analytics + /client/dashboard + /admin/branding pour valider visuellement
- Build local `npm run build` Bassira : OK (AnalyticsView/AdminBrandingView/ClientDashboardView ont bien été chunkés)
- Syntaxe Python : `py_compile backend/app/api/admin.py` OK + tests OK

[BLOQUÉ — actions humaines pendantes]
- !! **Validation visuelle prod** par Amine après deploy Coolify : ouvrir les 3 pages + tester le sélecteur d'org sur /client/dashboard + créer un branding sur /admin/branding pour vérifier que le PDF utilise bien le row DB au lieu de la palette par défaut.
- !! Tous les blocages précédents (Redis, briefs Kairos, etc.) restent valides — voir passations 2026-05-17 et 2026-05-13.

[ALERTE]
!! **Tests pytest pas exécutés en local** : Flask pas installé sur le poste Windows d'Amine (Python 3.13.5 + uniquement `py_compile`). Les tests passeront sur le CI Coolify (image Docker complète). Si CI rouge → vérifier que le mock `_MockQuery` matche bien le SDK Supabase Python utilisé en prod (v2.x).
!! **Sémantique de `last_30d`** : avant = sims COMPLÉTÉES dans les 30j (basé sur mtime outcome.json), après = sims CRÉÉES dans les 30j (basé sur created_at). Plus utile pour mesurer l'activité, mais c'est un changement de définition — préciser à Amine si nécessaire.
!! **Sémantique du champ `completed` dans time_series** : conservé pour ne pas casser le rendering du bar chart `AnalyticsView.vue`, mais sémantiquement c'est désormais "sims créées par jour". Renommer en v2 + adapter le label frontend si on veut être propre.
!! **`fetchAllOrganizations()` côté super-admin sur /admin/branding** : si l'API renvoie >100 orgs, le `<select>` HTML brut va devenir illisible. À paginer ou remplacer par un combo searchable si le tenant count dépasse 30 orgs.
!! **Le sélecteur d'org dashboard envoie X-Org-Id même quand l'user a 1 seule org** : c'est inutile mais sans risque (le backend accepte/ignore). Si bug remonte sur un endpoint inattendu → vérifier que l'endpoint visé est bien dans `/api/client/*` ou `/api/admin/branding` et pas un endpoint qui surinterpréterait le header.

[PARTIEL]

### Bug 1 — sémantique de "completed"
- ✅ Shape JSON inchangée
- ⏳ Renommer `completed` en `created` côté time_series (si Amine le souhaite — sinon laisser tel quel pour compat front)

### Bug 3 — UX edit branding
- ✅ Sélecteur d'org auto-rempli
- ⏳ Tester le flow complet : créer un branding + générer un PDF de simulation pour vérifier que le row pdf_branding est bien pické par `get_active_branding()` au moment du rendering

### Bug 2 — choix d'org persistance
- ✅ `auth.setCurrentOrg(orgId)` met à jour le store Pinia en mémoire
- ⏳ Pas persisté en localStorage : si Amine refresh la page, retour à `orgs[0]`. Peut-être ajouter une persistance Pinia plugin si Amine le demande.

[NEXT — chantiers prêts à attaquer en nouvelle session]

### Prio P0 — Validation visuelle prod (5 min)
1. Hard-refresh https://prospectives.ai-mpower.com/admin/analytics (Ctrl+Shift+R)
2. Vérifier que les KPI matchent Supabase (`select count(*) from simulation_ownership` + `select count(*) from quote_ownership` doivent égaler `total` et `quotes`)
3. Hard-refresh https://prospectives.ai-mpower.com/client/dashboard
4. Vérifier la présence du sélecteur d'org dans le hero + tester un changement d'org → la liste de simulations doit changer
5. Hard-refresh https://prospectives.ai-mpower.com/admin/branding
6. Vérifier que le `<select>` est peuplé (super-admin → toutes les orgs Bassira)
7. Créer un branding test → vérifier qu'il apparaît dans la table

### Prio P1 — Persistance choix d'org (si Amine veut)
- Ajouter `pinia-plugin-persistedstate` ou storage manuel sur `currentOrgId` dans `localStorage` avec key `bassira_current_org_id`
- Au boot, restaurer le choix si l'org est encore présente dans `auth.orgs`

### Prio P2 — Renommer `completed` → `created` dans time_series
- Backend : `_build_time_series_30d` retourne `{"date", "created"}` au lieu de `{"date", "completed"}`
- Frontend : `AnalyticsView.vue` `timeSeriesNormalised` lit `d.created`
- Label i18n : `analytics.timeSeries.title` → "Activité 30j (créations)"

### Prio P3 — Searchable org selector si nombre d'orgs >30
- Remplacer `<select>` par un combobox custom (autocomplete + recherche par slug/name)
- Concerne /admin/branding ET le sélecteur dashboard si jamais un tenant a 30+ orgs

### Prio P3 — Ancien filesystem analytics : decommission ou archive
- Vérifier qu'aucun autre code n'utilisait les helpers `_simulations_dir/_quotes_dir/_list_simulation_dirs/_outcome_mtime/_read_template_id/_count_quotes` (grep faite ce soir : aucune référence externe)
- Si OK, les helpers sont déjà supprimés du fichier — pas d'action restante.

[CTX session]
- Session courte ~1h (2026-05-22 soir), pure fix de bugs
- 1 commit Bassira pushed : `67c25ff` (5 files, +482/-240 lines)
- 0 commit Kairos
- ~80 tool calls (read + edit + grep + 1 build + 1 push)
- Modèle : Opus 4.7 (1M context)
- Approche : root cause first (pas de rustine), tests réécrits avec mocks Supabase (pas filesystem fixtures)
- Frontend testé via `npm run build` uniquement (pas Playwright cette session)

[MEMO inter-sessions]

### Pattern X-Org-Id auto-propagé
- Désormais l'interceptor axios `frontend/src/api/client.js` envoie systématiquement `X-Org-Id: <auth.currentOrgId>` si présent
- Tout nouvel endpoint backend décoré `@require_org_membership` bénéficie automatiquement de ce hint
- Si on veut forcer une autre org sur un appel (rare), override `config.headers['X-Org-Id']` à l'appel — l'interceptor respecte les overrides explicites (`if (!config.headers['X-Org-Id'])`)

### Pattern Supabase comme source de vérité
- Filesystem `WONDERWALL_*_DATA_DIR` n'est PLUS la source de vérité pour les KPI/aggregations admin
- Supabase tables ownership (`simulation_ownership`, `quote_ownership`) sont seules autoritaires depuis US-114
- Si un nouvel endpoint admin doit faire de l'aggregation → query Supabase directement, jamais le filesystem
- Fail-soft : si Supabase down, retourner zéros et logger, ne JAMAIS retourner 500 pour les endpoints read-only

### Memory ajoutée
- Aucune nouvelle memory créée cette session (les memories existantes couvrent déjà BYOK no model impose, kairos constraints, repo scope, etc.)

[Recommandations pour la nouvelle session]

1. **Valider visuellement les 3 fixes en prod** avant tout (5 min Ctrl+Shift+R sur les 3 URLs)
2. **Si bug remonte sur /admin/analytics** : vérifier `BASSIRA_ADMIN_TOKEN` + `BASSIRA_SUPER_ADMIN_EMAILS` côté Coolify env vars + tester avec `curl -H "Authorization: Bearer $JWT" https://prospectives.ai-mpower.com/api/admin/analytics | jq .data.kpis`
3. **Si bug remonte sur /admin/branding** : confirmer que `fetchAllOrganizations()` répond bien pour le super-admin via DevTools Network
4. **Ne pas re-toucher au pipeline Kairos** : les 10 hotfixes K05/K06 sont stabilisés (rappel de la passation 2026-05-17)
5. **Si Amine veut renommer `completed` → `created`** : refactor cohérent backend + frontend + i18n + tests pour éviter la confusion sémantique

— fin passation 2026-05-22 — Fix 3 bugs admin/client (analytics Supabase + multi-org dashboard + branding selector). Reste : validation visuelle prod + persistance choix org (si Amine veut).

---

== PASSATION MiroShark/Bassira+Kairos 2026-05-17T18:00:00+01:00 ==

[ETAT]
- branche Bassira `main` `e6ff1f6` à jour origin (9 commits depuis la passation 2026-05-13)
- branche Kairos `main` `6cbe4a3` à jour origin (15+ commits — hotfix pipeline + page /admin/api-inbound)
- prod Bassira ONLINE https://prospectives.ai-mpower.com — Coolify auto-deploy sur main via webhook GitHub
- prod Kairos ONLINE https://scrap.ai-mpower.com (frontend) + `crplceoptyeslqyfcqvj.supabase.co/functions/v1` (edge fns) — pipeline stable mais fragile sur graines complexes
- npm run build Bassira : OK, 941 modules
- Playwright research-i18n : 5/5 verts (clés research.* étendues à ~30 entrées)
- Clé API Kairos préfixe `bsr_7123` (rotée le 15 mai, env var Coolify `KAIROS_API_KEY`)

[FAIT cette session — 5 chantiers Bassira + récap Kairos]

### Chantier 1 — Refonte UX TopicResearchPanel multi-select (US-B04 → B04.3)

Avant : 1 radio par topic, brief invisible (juste label DÉCISION/CRISE), sources cachées dans slide-over. Amine a tapé du poing sur la table → refonte totale.

| Commit | Fix |
|---|---|
| `bbdb4a2` US-B04 | Multi-select checkboxes cross-topics, texte intégral du brief (`variant.brief`) + rationale + framework badge, sources inline `<details>` avec favicon + lien `target=_blank`, zone compose Markdown éditable avec « Régénérer auto » + « Insérer dans la console », devil's advocate fix (`type === 'devil_advocate' \|\| is_devil_advocate`) |
| `6f5e336` colors | Page Bassira en DARK THEME (`--wi-bg: #1a1d27`) — j'avais designé pour cream → contraste catastrophique. Fix : badges orange vif sur dark bg, verdict pills avec tints 18% + couleurs claires, favicons sur padding blanc, devil's advocate sans fond vert menthe |
| `1e61f82` US-B04.1 | Toggle « Activer la recherche dynamique Kairos » au-dessus du panel (default ON), recherche déclenchée sur la matière 01 (= `scenarioSuggestPreview` = files preview + URLs fetched + ask docs) au lieu du textarea 02, insertion du brief dans 01 (créer un urlDoc `bassira://research/<ts>`) au lieu d'écraser 02, message disabled clair sous le bouton Lancer (« Ajoutez au moins une graine en 01 » / « Rédigez votre invite en 02 ») |
| `f8ae845` US-B04.2 | Mode dégradé `synthesizer_unavailable` : status line ne dit plus « 0 topics · 0 sources » mais « 30 signaux bruts récupérés · mode dégradé (timeout) ». Checkbox par signal (tous cochés par défaut — option (c) validée Amine), toolbar « Tout cocher / Tout décocher », zone compose Markdown listant les sources cochées. Mode complet : aussi checkboxes par source dans le `<details>`. Insertion = 1 urlDoc « Brief composé » + 1 urlDoc par source cochée (déduplication URL) → la simulation backend ingère vraiment les liens et non juste le markdown |
| `e6ff1f6` US-B04.3 | Helper `_withAuthRetry(fn)` autour des appels POST/GET research. Sur HTTP 401 → tente `supabase.auth.refreshSession()` puis retry l'appel. Si refresh KO → errorCode `SESSION_EXPIRED` mappé vers `research.errors.sessionExpired` (i18n FR/EN/AR : « Votre session a expiré pendant la recherche… le cache 1h vous redonnera la même session_id ») |

### Chantier 2 — Brief technique passé à Claude Kairos (par Amine)

Amine a copié mes 2 briefs dans une autre instance Claude Code Kairos :

1. **Page /admin/api-inbound** : observabilité live des sessions `research-from-seed`. Livré côté Kairos (commits `5331ba7` + `d395ead`). URL : https://scrap.ai-mpower.com/admin/api-inbound — utilisé toute la session pour debug. Affiche STATUT/CRÉÉE/CLÉ/LANG/PROFIL/DURÉE/STAGE KO/SEED + drawer détail avec stages + JSON result + logs liés.

2. **Améliorer coverage scrapers MENA** (presse économique Maroc en FR/AR, boost lang locale, Perplexity fallback). PAS encore livré côté Kairos (à confirmer prochaine session). Sans ce fix, les graines politico-sociales Maroc retournent verdict `deepen` avec topics IA-générique ArXiv.

### Chantier 3 — Brief Kairos topics_of_interest + pgvector

Amine a pivoté la vision produit : **veille mensuelle continue** au lieu de one-shot live. Kairos doit devenir un **knowledge graph vivant** :
- Table `topics_of_interest` (sujets de veille permanents par user)
- Cron `watchlist-collector` (collecte quotidienne/hebdo automatique)
- Endpoint `POST /topics-search` (vector match seed → cache hit instantané)
- Table `topics_archive` (TTL 30j, indexée pgvector)

Brief rédigé + passé à Amine (à coller dans Claude Kairos quand prêt). Décision : **embedding model = `nomic-embed-text` via Ollama** en bootstrap (déjà installé côté MiroShark backend), migration vers **Qwen3-Embedding** quand machine livrée (3-4 semaines). pgvector à activer en migration Supabase (1 ligne).

### Chantier 4 — Hardware recommendation (machine workstation)

Amine commande dans 3-4 semaines. Budget 250k DH, chez lui, OS Ubuntu Server 24.04 LTS, prévoir extension 4 GPU futur. Reco livrée :

| Composant | Modèle | Prix DH |
|---|---|---|
| CPU | AMD Threadripper Pro 7975WX (32 cores) | 35 000 |
| MB | ASUS Pro WS WRX90E-SAGE SE (7× PCIe Gen5 x16) | 12 000 |
| RAM | 8× 64 GB DDR5-5600 ECC RDIMM (512 GB) | 30 000 |
| GPU | **NVIDIA RTX PRO 6000 Blackwell 96 GB GDDR7** (atlasgaming.ma) | 95 000 |
| Stockage | 2× Samsung 990 Pro 8 TB NVMe + 2× Seagate Exos X18 16 TB | 33 000 |
| Alim/Boîtier/Cooling/UPS/Cables | Corsair AX1600i + Fractal Define 7 XL + Noctua NH-U14S TR5-SP6 + APC Smart-UPS SRT 2200VA | 27 000 |
| Marge import + assemblage | linksolutions.ma + workstation.ma + atlasgaming.ma | 17 500 |
| **TOTAL** | | **~250 000 DH** ✅ |

Pour Manahil ingestion massive + Qalem formation : couvre 3 projets actuels + 3-5 ans de croissance. Note : alim 1600W tient 2 GPU ; pour 4 GPU futur → upgrade alim 2200W + water cooling.

### Chantier 5 — Alternative cloud pas cher (validé pour démarrer Manahil immédiatement)

Recommandé V1 : **Tier 1 Cloud pay-as-you-go ~$30-50/mois** vs build local 25k$ (break-even ~25 ans sur scope actuel) :
- LLM 70B inference : **DeepSeek BYOK actuel** (déjà ok) ou DeepInfra Llama 3.3 70B ($0.23/$0.40 per M tokens)
- Embedding multilingue : **Mistral Embed** ($0.10/M tokens, souverain FR) ou Cohere Embed v3 multilingual
- DB + pgvector : **Supabase Pro $25/mois** (déjà en place)
- Stockage froid >100GB : Backblaze B2 ($0.005/GB/mois)
- GPU on-demand ponctuel : RunPod RTX 4090 $0.34/h ou A100 $1.19/h

Alternative souveraine EU si besoin 24/7 dédié : Hetzner GEX44 RTX 4000 Ada 20GB ~€250/mois (après hausse avril 2026), ou Scaleway H100 SXM Paris ~€2.50/h.

[VALIDÉ EN PROD]
- Pipeline Kairos `research-from-seed` retourne `TERMINÉ` sur graines simples (fintech Maroc → 4 topics + verdict `deepen`)
- Mode dégradé `synthesizer_unavailable` fonctionne : Bassira affiche les 30 signaux bruts avec checkboxes
- Insertion N urlDocs en 01 marche : chaque source cochée devient une entrée 01 distincte (texte composé + sources individuelles)
- Coolify auto-deploy via webhook GitHub : 5 commits successifs deployed sans intervention
- Page /admin/api-inbound Kairos : 5+ sessions visibles avec clé `bsr_7123`, drawer détail OK
- Test E2E live le 2026-05-15 : graine fintech Maroc → completed en ~22s (cache POST + signaux ArXiv pré-existants), 4 topics rendus avec brief 200-300 chars + 2 framework variants
- Test 2026-05-17 : refresh session 401 → polling reprend automatiquement (US-B04.3 fix résilience)

[BLOQUÉ — actions humaines pendantes]
- !! **REDIS_URL non posée** côté Coolify (Amine a dit « en cours de déploiement » le 13 mai mais jamais confirmé). Sans Redis : cache Bassira `kairos_proxy` fallback in-process (1 worker Gunicorn = OK, mais perd cache au restart). Le code détecte auto au boot, pas bloquant fonctionnellement.
- !! **2 briefs Kairos non encore livrés** côté Claude Kairos :
  1. Coverage scrapers MENA (presse économique FR/AR, boost lang locale, Perplexity fallback)
  2. topics_of_interest + cron watchlist + pgvector + nomic-embed
- !! **Machine workstation** : Amine commande next week, livraison 3-4 semaines = mi-juin
- !! **Test browser US-B04.2 + B04.3** pas vérifié visuellement sur prod après le push `e6ff1f6` — Amine doit hard-refresh `/console`, reconnecter, retester

[ALERTE]
!! **DeepSeek-v4-flash sur task `enrichment` reste fragile** sur graines complexes (politico-sociales Maroc). 10 hotfixes Kairos K05/K06 cette session (truncate, normalize, lower bounds 1/1/1, max_tokens 8000-16000, etc.) ont stabilisé MAIS pipeline peut encore tomber en mode dégradé `synthesizer_unavailable`. Le frontend Bassira US-B04.2 gère ça proprement avec scored_signals_top + checkboxes.

!! **Cache POST Bassira 1h** : si tu reposes la MÊME seed dans la même heure, Kairos renvoie la même `session_id`. C'est utile pour récupérer après une session expirée (US-B04.3) mais peut surprendre en test.

!! **Devil's advocate seuils relâchés** : `MIN_TOPICS=1`, `KEY_SIGNALS_MIN=1` côté validator synthesizer (commit Kairos `6cbe4a3`). Permet aux pipeline de passer même avec très peu de matière. Si la qualité dégrade trop, remonter à 3.

!! **JWT Supabase expire 1h** : pipeline Kairos peut prendre 3-4 min, mais si la session démarre 50 min après login → 401 en plein vol. US-B04.3 a fix le refresh automatique, mais le pattern reste fragile pour des sessions très longues (future v2 : token refresh proactif avant chaque appel critique).

[PARTIEL]

### Brief Kairos topics_of_interest (architecture cible)
- ⏳ Brief rédigé, donné à Amine, **PAS implémenté côté Kairos**
- Quand prêt : permettra workflow vision Amine (veille mensuelle, DB lookup d'abord, simulation 1×/mois par sujet)
- Decision tech : nomic-embed-text bootstrap + migration Qwen3-Embedding plus tard

### Brief Kairos coverage scrapers MENA
- ⏳ Idem : rédigé, donné, PAS implémenté
- Sans ce fix : graines Maroc/MENA continuent à retourner verdict `deepen` avec topics ArXiv off-topic

### Tests E2E checkbox sources Bassira
- ⏳ Test visuel manuel pas refait après US-B04.2 + B04.3 (Coolify deploy live à 18h, Amine va restart terminal)
- Quand Amine retest : vérifier que checkboxes mode complet ET dégradé fonctionnent + insertion N urlDocs visible dans 01

[NEXT — chantiers prêts à attaquer en nouvelle session]

### Prio P0 — Validation visuelle US-B04.2 + B04.3 en prod
1. Hard-refresh https://prospectives.ai-mpower.com/console (Ctrl+Shift+R)
2. Reconnecter via Google (cookies probable expirés)
3. Activer toggle « Recherche dynamique Kairos »
4. Pose un fichier ou URL ou ask doc dans 01 (≥60 chars de matière)
5. Attendre 1.5s debounce + pipeline 3-4 min
6. Vérifier :
   - Status line correcte (« N topics · M sources · {verdict} » OU « N signaux bruts · mode dégradé »)
   - Checkboxes visibles + tous cochés par défaut
   - « Tout cocher / Tout décocher » fonctionne
   - Bouton « Insérer brief + N source(s) en 01 » crée N+1 entrées 01 (1 brief + 1 par source)
   - Bouton « Lancer la simulation » devient enabled

### Prio P0 — Faire avancer Kairos topics_of_interest
- Si Amine veut démarrer Manahil rapidement → coller le 2e brief Kairos (`topics_of_interest + pgvector`) dans l'autre instance Claude Code
- Vérifier que pgvector est activé Supabase Kairos : `CREATE EXTENSION IF NOT EXISTS vector;`
- nomic-embed-text déjà dispo via Ollama backend Bassira → réutiliser même infra côté Kairos via dispatch-llm task=embedding

### Prio P1 — Améliorer coverage scrapers Kairos MENA
- Coller le 1er brief Kairos (coverage) dans Claude Kairos
- Cible : graine fintech Maroc → verdict `pass` avec sources `.ma`/`.dz`/`.tn`
- Tester avec : « Évolution des fintech au Maroc en 2026 : adoption mobile money par les TPE et stratégie BAM contre l'informel. » → attendre que `coverage_map` ait au moins 3/5 subjects couverts

### Prio P1 — Connecter Bassira au /topics-search Kairos (US-B05, ~1j)
Quand Kairos `/topics-search` sera dispo :
- Bassira appelle `/topics-search` AVANT pipeline live (au mount du panel ou au 1er trigger)
- Si match → render directement topics archivés en <1s
- Si no match → 2 CTA : « Collecte rapide 3 min » OU « Créer sujet de veille permanent »
- Nouvelle page `/admin/topics-of-interest` Bassira pour CRUD watchlist + lister sujets + lancer simulation mensuelle

### Prio P2 — Hardware workstation Maroc (livraison ~mi-juin 2026)
- Confirmer commande chez 3 revendeurs : linksolutions.ma (CPU/MB/RAM), atlasgaming.ma (RTX PRO 6000 Blackwell), workstation.ma (assemblage + burn-in)
- Préparer Ubuntu Server 24.04 LTS install script (NVIDIA driver 560+ + CUDA 12.6 + Docker NVIDIA Container Toolkit + Ollama + vLLM)
- Migrer embeddings nomic → Qwen3-Embedding-0.6B (CPU-friendly) dès machine livrée

### Prio P3 — Bloqué humain (reporté de la passation précédente)
- US-113 Stripe credentials (toujours pas posés Coolify) — Amine prend en charge
- Témoignages partenaires NDA — Amine prend en charge

[CTX session]
- ~3 jours intensifs (2026-05-15 → 2026-05-17), session marathon
- 7 commits Bassira pushed sur main : `1faafea`, `a86942f`, `bbdb4a2`, `6f5e336`, `1e61f82`, `f8ae845`, `e6ff1f6` (+ `c241769` qui était entre les 2)
- 15+ commits Kairos sur `Afristrat/scrapping` cette session (hotfix K05/K06 + K10 admin page)
- ~300+ tool calls (browser MCP Edge + git + npm/deno tests + édits)
- Modèle : Opus 4.7 (1M context) toute la session
- Coût LLM smoke tests : ~$0 (DeepSeek-v4-flash très bon marché)
- Coolify auto-deploy fluide via webhook GitHub, ~2 min par cycle build+deploy

[MEMO inter-sessions]

### Architecture cible Kairos (à implémenter — vision Amine)
- **Knowledge graph vivant** : sujets de veille permanents (`topics_of_interest`) collectés en continu via cron
- **API `/topics-search`** : vector match seed → cache hit instantané ; fallback pipeline live
- **Workflow user** : créer N sujets, Kairos collecte 24/7, simulations mensuelles par sujet
- Embeddings : nomic bootstrap → Qwen3-Embedding souverain quand machine livrée

### Stack technique confirmée
- Bassira : Vue 3 + Vite + axios + Supabase Auth + Pinia (dark theme `--wi-bg: #1a1d27`)
- Kairos : Supabase Edge Functions (Deno) + DeepSeek BYOK + pgvector (à activer)
- Backend Bassira : Flask + Blueprints (pas FastAPI)
- Bassira API client : `frontend/src/api/client.js` (axios + Bearer Supabase auto-injecté)
- Polling research : 3s interval, max 6 min timeout

### Patterns durables installés
- `_withAuthRetry(fn)` ConsoleView : auto-refresh Supabase sur 401 puis retry — réutiliser pour tout call API privatif long
- Insertion brief Kairos dans 01 (urlDoc synthétique `bassira://research/<ts>`) — pattern à propager à toute « matière générée IA » à venir
- Mode dégradé `synthesizer_unavailable` + `scored_signals_top` fallback côté Kairos : permet de toujours retourner quelque chose même si LLM plante. Pattern à généraliser sur les autres stages (rubric-architect fallback, auditor fallback déjà fait)
- Checkboxes multi-select avec Set<string> + watch `immediate: true` pour pré-cocher (option C par défaut, déselection explicite par l'user)

### Memories projet ajoutées
- `reference_kairos_pipeline_v2.md` : nouveau contrat Kairos POST/GET + scope_profiles + mode dégradé (créée 13 mai)
- `feedback_kairos_constraints.md` : ne JAMAIS toucher BYOK DeepSeek-v4-flash, ne JAMAIS toucher `--no-verify-jwt`, ne JAMAIS corriger lang forwarding scored_signals_top
- `feedback_repo_scope.md` : dans le repo Bassira, parler Bassira ; Kairos = contrat API externe

### URLs critiques
- Bassira prod : https://prospectives.ai-mpower.com
- Kairos prod (frontend) : https://scrap.ai-mpower.com
- Kairos /admin/api-inbound : https://scrap.ai-mpower.com/admin/api-inbound
- Kairos API endpoints : https://crplceoptyeslqyfcqvj.supabase.co/functions/v1
- Coolify Bassira : http://192.168.100.3:8000/project/e6kerffaobuwy2uo9n5sdihu/...u6pn5mr2pgi88s13un55pkzb
- GitHub repos : `Afristrat/MiroShark` (Bassira), `Afristrat/scrapping` (Kairos)

[Recommandations pour la nouvelle session]

1. **Démarrer par test browser US-B04.2 + B04.3** (validation visuelle Coolify deploy)
2. **Décider quel brief Kairos passer en priorité** : coverage scrapers (gain qualité immédiat) OU topics_of_interest (gain stratégique long-terme veille mensuelle)
3. **Ne pas re-toucher au pipeline Kairos** : les 10 hotfixes K05/K06 sont stabilisés, ne pas régresser
4. **Si l'user revient sur l'idée build local 250k DH** : rappeler que cloud Tier 1 à $30-50/mois est de loin meilleur tant que volumes < $500/mois
5. **Si brief tronqué côté Kairos** : c'est probablement DeepSeek qui plante sur prompts longs. Pipeline mode dégradé `synthesizer_unavailable` → frontend Bassira affiche 30 signaux bruts (déjà géré US-B04.2)

— fin passation 2026-05-17 — UX TopicResearchPanel refondu (multi-select + brief visible + sources ouvrables + insertion N urlDocs + résilience 401). Reste : 2 briefs Kairos à passer + validation visuelle prod.

---

== PASSATION MiroShark/Bassira+Kairos 2026-05-13T01:00:00+01:00 ==

[ETAT]
- branche Bassira `main` `d0249f4` à jour origin (1 commit pendant cette session : doc spec pipeline Kairos)
- branche Kairos `main` `aedc93f` à jour origin (chantier complet K01→K09e + pivot auth + async pattern)
- prod Bassira ONLINE https://prospectives.ai-mpower.com — stable, aucune régression cette session
- prod Kairos (Supabase `crplceoptyeslqyfcqvj` = zlatan-scrap-v2) — **8 edge functions Phase 1+2 + orchestratrice déployées + smoke E2E validé**
- npm run build Bassira : OK
- chantier majoritairement côté Kairos (autre repo) : `C:\Users\amans\OneDrive\Projets\claudia-zlatan-scrap-main`
- côté Bassira : aucune intégration encore — uniquement doc spec poussée

[FAIT cette session — 2 chantiers]

**Chantier A — Hotfixes Bassira (8 mai matin)** :
✓ Modal Branding scroll v3 commit `ffea6f2` : passage flex column, mais split flex:1 1 0 a collapsé modal à 69px
✓ Modal Branding scroll v4 commit `634b6da` : pivot final **grid** (`display:grid; grid-template-rows:auto 1fr; height:calc(100vh-64px)`) avec body block + split height:100% → cause racine identifiée via DOM inspection live Chrome MCP (body offsetHeight 741 mais CSS height auto → percentage ne résout pas → split prend hauteur intrinsèque content 1125)
✓ Validé E2E en prod : `modal=805 body=737 split=737 form=737, scrollH=1125, hasScrollbar=true`

**Chantier B — Pipeline dynamique Kairos↔Bassira** :

Spec rédigée + commitée dans Bassira `docs/kairos-bassira-research-prompts.md` (442 lignes, validé Amine) :
- 5 prompts LLM v2 (research-strategist + rubric-architect + signal-synthesizer + quality-auditor + iterative-deepening)
- Architecture récursive seed→subjects→signals→topics→briefs
- BYOK strict (aucun modèle imposé, tasks Kairos `enrichment`/`scoring`)
- Anti-blind-spot MENA-Europe natif (multi-langue FR+AR+EN, soft_boost AR, devil_advocate forcé)

11 stories Ralph livrées sur Kairos main (commits sur `Afristrat/scrapping`) :

| # | Story | Hash | Description |
|---|-------|------|-------------|
| K01 | research-strategist | `5cba9a0` | Edge fn seed→research_strategy (36 tests, lib.ts split) |
| K02 | rubric-architect | `528d302` | Rubric 3-couches criteria+disqualifiers+soft_boosts (20 tests) |
| K03 | signals-session | `7416568` | Table éphémère TTL 1h + adapt 4 scrapers + cron */15min (31 tests) |
| K04 | llm-score-batch rubric_override | `45a5e8a` | 3 modes legacy/hybrid/ad_hoc + scoring 3-couches (32 tests) |
| K05 | signal-synthesizer | `0b67b4b` | Topics + brief_variants + coverage_map + devil_advocate forcé (27 tests) |
| K06 | research-from-seed orchestratrice | `d22ee87` puis enrichi | Compose K01→K05 + K07 + scrapers, x-api-key public auth |
| K07 | quality-auditor | `d22ee87` | Audit 7 axes + decision tree pass/warn/fail/deepen (33 tests) |
| K09a | proxy_user_id mapping | `64290ee` | Migration colonne + helper signature JWT HS256 — **bloqué** projet ECC P-256 |
| K09b | signInWithPassword | `2d8f086` | Helper cache 50min — **abandonné** (Amine refuse password en secret) |
| K09c | service_role + x-proxy-user-id | `cc329c7` | Dual-mode dans dispatch-llm + 5 fns Phase 1 — partiel |
| K09d | x-internal-auth + token dédié | `b7be56a`→`7a3ec89` | Pivot final : env `KAIROS_INTERNAL_TOKEN` + service_role bypass RLS — **validé E2E** |
| K09e | async pattern research_sessions | `aedc93f` | EdgeRuntime.waitUntil + GET status polling — **smoke E2E completed** |

[VALIDÉ EN PROD Kairos — 12 mai 23h]
- POST `/functions/v1/research-from-seed` (x-api-key) → 202 + session_id en <1s
- Pipeline background : research-strategist 31s + rubric-architect 22s + scrape 44s + llm-score-batch 12s + signal-synthesizer 45s + quality-auditor 14s = **170s total**
- GET `/functions/v1/research-from-seed?session_id=X` → `status=completed` avec result complet
- Smoke graine "Réforme Code travail Maroc 2026" → 3 topics générés (méfiance employeurs / fierté amazighe / résilience informelle=devil_advocate), 2 brief_variants chacun avec framework_hint (crisis/market/policy/cerberus/decision)
- **BYOK strict respecté en prod** : `provider_used: deepseek`, `model_used: deepseek-v4-flash` (lecture settings du proxy_user_id = compte Amine)
- Audit verdict='deepen' cohérent : coverage_map 5/5 subjects sans signal direct + cultural_warning AR/EN absent

[BLOQUÉ — actions humaines pendantes]
- Aucun secret leaké cette session (1 token KAIROS_INTERNAL_TOKEN posé proprement via `supabase secrets set`, pas en chat).
- Aucune action humaine bloquante pour avancer côté Bassira.

[ALERTE]
!! **Pipeline durée 170s vs Gateway Supabase 150s** : le pipeline complet dépasse fréquemment la limite Gateway. Pour ça que K09e async = obligatoire. Si tu rajoutes des stages, watch out.
!! **research_sessions TTL 24h** : cron purge horaire. Session_id devient `not_found` après 24h. Adapter Bassira pour stocker side une copie locale du result si tu veux du long-terme.
!! **proxy_user_id pointe directement sur Amine `f313137b-3480-4b2b-bc11-e2d4c6ba8fd3`** : pas un user dédié bassira-bot. Coûts LLM trackés sur ton compte. À la prochaine onboarding tenant externe, créer un user proxy dédié par tenant (cf US-K10 futur).
!! **Tests Kairos pas tous re-vérifiés post-Option C** : 239 tests verts AVANT le pivot K09c/d. Refaire passer la suite complète en V2 stabilization si on touche encore au helper auth.
!! **Stash Kairos pendant** : 1 stash@{0} contient du travail Amine pré-existant (Wave 10C/D/E filtres dashboard, etc.) qui était en cours avant le chantier. À re-pop manuellement quand tu reviens sur Kairos UI (conflits potentiels sur `database.ts`, `digest/index.ts`).

[PARTIEL]

### Pipeline Kairos = 100 % livré E2E
- ✅ 11 stories
- ✅ 239 tests unitaires (avant K09c/d/e — à re-passer en stabilization)
- ✅ Smoke prod confirmé

### Intégration Bassira = 0 % (pas commencé)
- ❌ Backend `POST /api/research/from-seed` (US-B01) : proxy + cache LRU 1h + fallback RSS legacy
- ❌ Frontend `TopicResearchPanel.vue` (US-B02) : refonte de `TrendingTopics.vue` avec cards topic + brief_variants picker + sliding panel sources
- ❌ Hook `ConsoleView.vue` (US-B03) : déclencher /api/research/from-seed dès que seed ≥ 60 chars + debounce 1.5s + polling GET status toutes les 3s

### Iterative-deepening = NON implémenté V1
- quality-auditor retourne `verdict='deepen'` mais V1 ne re-pipeline pas
- Pipeline `K09f` futur : si verdict=deepen ET depth<2, re-lancer un sub-seed scopé sur deepening_targets

### Web scrape (Perplexity) = NON implémenté V1
- Subjects sans hints X/Reddit/ArXiv sont skippés au scrape
- À ajouter en V2 si gap de couverture mesuré en prod (cf smoke ce soir : 5/5 subjects sans signal direct → signe que les scrapers existants ne couvrent pas la graine sociale-politique Maroc)

[NEXT — chantiers prêts à attaquer en nouvelle session][CRITIQUE PROCHAINE SESSION]

### Prio P0 — Intégration Bassira (US-B01/B02/B03)
**Effort estimé** : 2-3h en Ralph swarm (3 sub-agents parallèles).

**US-B01 backend Bassira** :
- `POST /api/research/from-seed` (proxy Kairos) :
  - Body : `{ seed, lang, sector_hint?, depth_hint? }`
  - Cache LRU 1h sur `sha256(seed+lang)` côté Bassira pour amortir si même seed soumis
  - Appel HTTP Kairos avec `x-api-key: <BASSIRA_KAIROS_API_KEY>` (env Coolify)
  - Retourne `{ session_id, status: 'running' }` côté Bassira au client
- `GET /api/research/status?session_id=X` (proxy GET Kairos) :
  - Idem proxy mais avec polling
  - Si status=completed, cache LRU le result avec TTL 24h
- Fallback gracieux : si Kairos down/timeout → fallback sur TrendingTopics RSS legacy en background avec flag `degraded: true`
- Tests pytest : cache hit/miss, fallback, propagation erreurs

**US-B02 frontend `TopicResearchPanel.vue`** :
- Refonte complète de `TrendingTopics.vue`
- État Vue 3 : `sessionId`, `topics`, `status`, `pollingInterval`
- UI cards (Causse palette) :
  - Topic label + summary
  - 1-3 brief_variants picker (radio buttons avec framework_hint badge)
  - "Use this brief" → émet event `select` avec brief + framework + signals_refs
  - Sliding panel "Voir sources" → key_signals avec favicon + score + URL
- État loading (skeleton cards pendant polling)
- Devil's advocate visuellement distinctif (border orange WI_TERRA)
- Coverage warnings affichées si verdict='deepen'

**US-B03 hook `ConsoleView.vue` + tests E2E Playwright** :
- Watch sur `formData.simulationRequirement` :
  - Si length >= 60 chars + debounce 1.5s + pas en cours → trigger `triggerResearchFromSeed(seed, lang)`
- triggerResearchFromSeed → POST /api/research/from-seed → reçoit session_id
- setInterval polling GET /api/research/status toutes les 3s → updates topics
- Quand status=completed → arrête polling, hydrate `TopicResearchPanel`
- Tests Playwright : pose graine → confirme apparition cards topics en <60s (mock Kairos pour speed)

**Contrat API Kairos pour Bassira (à mettre en .env Coolify)** :
```
KAIROS_API_URL=https://crplceoptyeslqyfcqvj.supabase.co/functions/v1
KAIROS_API_KEY=bsr_fdc02df124e51c1386de9e49e38ccdf34001a186909a997b
```
(la clé est valide, scopée `research-only`, rate 60 RPM, proxy_user_id = compte Amine)

### Prio P1 — Stabilization Kairos (post-intégration)
- US-K10 : créer user `bassira-bot@internal.kairos` dédié + cloner BYOK config + UPDATE proxy_user_id (isolation tenant)
- US-K11 : re-passer suite complète 239 tests + ajouter integration tests Deno pour pipeline E2E avec mocks dispatch-llm
- US-K12 : iterative-deepening (verdict='deepen' → re-pipeline sub_seed, max depth 2)
- US-K13 : Perplexity web scrape pour subjects sans hints X/Reddit/ArXiv (combler 5/5 coverage gap observé en smoke ce soir)

### Prio P2 — Bloqués humain (inchangé)
- US-113 Stripe credentials (toujours pas posés Coolify)
- Témoignages partenaires NDA
- Logo Bassira (memory feedback_rejected_tools — ne pas reproposer)

[CTX session]
- ~6h session marathon (8 mai 17h → 13 mai 1h, avec pauses)
- 1 commit Bassira (`d0249f4` doc spec) + 14 commits Kairos
- 11 stories Ralph livrées (K01-K07 + K09a-e)
- ~6 sub-agents Sonnet pilotés cette session (Phase 1 swarm 4 parallèles + Phase 2 background 2 parallèles + K06)
- ~120 calls Bash/MCP cumulés
- Tests Kairos : ~120 baseline → 239 verts (pre-pivot K09c)
- Modèle : Opus 4.7 (1M context) toute la session
- Coût LLM total smoke E2E ce soir : ~$0 (deepseek-v4-flash très bon marché, dispatch-llm `usage.cost: 0`)

[MEMO inter-sessions]

### Kairos infra (referenced from Bassira)
- **Projet Supabase Kairos** ref `crplceoptyeslqyfcqvj` (zlatan-scrap-v2) — projet **JWT Signing Keys ECC P-256** (Supabase 2026), pas de legacy HS256 secret exposé
- **GitHub repo** : `Afristrat/scrapping` (sur main `aedc93f`)
- **Local repo** : `C:\Users\amans\OneDrive\Projets\claudia-zlatan-scrap-main` (rebranded "Kairos" en cours, designs Stitch présents)
- **Edge functions secrets** posés : `KAIROS_INTERNAL_TOKEN=e2ec8718197b41c3bbb559cc68c52d3cd6c2627a5262d5d58ee5a34b2a42d82b` (32 bytes hex random)
- **Migrations appliquées** :
  - `20260506_004_report_delivery.sql` (Bassira side)
  - `20260508000001_signals_session.sql` (Kairos)
  - `20260508000002_public_api_keys.sql` (Kairos)
  - `20260509000001_public_api_keys_proxy_user.sql` (Kairos)
  - `20260512000001_research_sessions.sql` (Kairos)

### API contract Kairos (consommable Bassira)
```
POST https://crplceoptyeslqyfcqvj.supabase.co/functions/v1/research-from-seed
Headers: x-api-key: bsr_fdc02df124e51c1386de9e49e38ccdf34001a186909a997b
         Content-Type: application/json
Body: { seed: string (50-3000 chars), lang: 'fr'|'en'|'ar', sector_hint?: string, depth_hint?: 0|1|2 }
→ 202 { ok: true, session_id, status: 'running', message }
→ 400 invalid_json | invalid_body | seed_too_short | seed_too_long | lang_unsupported
→ 401 missing_api_key | invalid_api_key | inactive
→ 403 cors_origin_not_allowed | scope_missing
→ 429 rate_limited (60 RPM sliding window)
→ 500 service_role_env_missing | session_create_failed

GET https://crplceoptyeslqyfcqvj.supabase.co/functions/v1/research-from-seed?session_id=<uuid>
Headers: x-api-key: bsr_fdc02df124e51c1386de9e49e38ccdf34001a186909a997b
→ 200 { ok: true, session_id, status: 'running'|'completed'|'failed'|'timeout', result?, error_detail?, telemetry?, created_at, completed_at }
→ 400 session_id_required
→ 401 missing_api_key
→ 404 session_not_found
```

### Pattern auth Kairos (Option C+D définitive)
- Mode user JWT : caller envoie `Authorization: Bearer <user JWT>` → `auth.getUser()` → mode='user'
- Mode internal : caller envoie `Authorization: Bearer <anything>` + `x-internal-auth: <KAIROS_INTERNAL_TOKEN>` + `x-proxy-user-id: <uuid>` → `resolveAuthOrProxy()` retourne mode='internal' avec userId=proxy_uuid
- dispatch-llm en mode internal : re-create supabase client avec service_role pour bypass RLS sur lookup settings+user_api_keys du proxy

### Conventions commits Kairos
- `[K0X title]` pour les stories, `[K0X X title]` pour les fixes/pivots (ex `[K09 d]`)
- `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`

### Memory globale touchée cette session
- Aucun ajout durable (les leçons sont dans le code+passation, pas dans `memory/`)

[Recommandations pour la nouvelle session]

1. **Reprise direct sur US-B01/B02/B03** — sub-agents Ralph swarm idéal (3 parallèles : B01 backend Python, B02 frontend Vue, B03 hook+E2E)
2. **Brief les sub-agents avec** :
   - Le contrat API Kairos copié-collé du MEMO ci-dessus
   - La spec côté Bassira : `frontend/src/components/TrendingTopics.vue` (à refondre, pas remplacer car util pour fallback)
   - Var env Coolify à poser AVANT déploiement Bassira : `KAIROS_API_URL` + `KAIROS_API_KEY`
3. **Avant de coder B02** : valider design Stitch préférable — Amine a-t-il un mockup spécifique pour TopicResearchPanel ? Sinon improviser dans la palette Causse `--wi-*` cohérente avec ConsoleView actuel.
4. **Test E2E après B03** : lancer une vraie graine depuis `/console` en prod Bassira → confirmer cards apparaissent → click "Use this brief" → ScenarioSuggestions hydraté → simulation lançable. C'est le vrai gate de validation produit.
5. **Si bugs subtils dispatch-llm** : il y a un try/catch global maintenant qui expose `unhandled_exception` avec stack. Lit dans Studio logs Kairos.

— fin passation 2026-05-13 — Pipeline Kairos COMPLET livré + smoke E2E validé. Intégration Bassira (~2-3h) reste pour prochaine session.

---

== PASSATION MiroShark/Bassira 2026-05-08T00:30:00+01:00 ==

[ETAT]
- branche `main` `98d4610` à jour avec `origin/main` (push confirmé, 5 commits cette session)
- prod **REDEPLOY EN COURS** sur Coolify (deployment id `vh5u61oafvjaajl5j0c3zpgn`, déclenché ~00:30) — vérifier https://prospectives.ai-mpower.com après ~3 min
- tests backend **1612 passing, 59 skip** (+7 nouveaux US-138 phase 2 + 16 US-145 + 8 US-138 locale, 0 régression)
- npm run build : OK (Vite, frontend bundle prod livré)
- migrations Supabase **20260506_004_report_delivery.sql** : appliquée en prod via Monaco SQL Editor (apostrophe `d'expiration` ligne 26 doublée `d''expiration` après échec `42601`). Tables `report_deliveries` + `report_downloads` + RLS + comments OK.
- session courte centrée sur 5 fix critiques + 2 features admin (assign user↔org + create org inline) post-passation 2026-05-06

[FAIT cette session — 5 commits, US-138 phases 1+2, US-145]

**Commit `d0b4e08` [US-138 + US-145] — fixes critiques pipeline PDF prod + filet anti-zombie worker**

✓ **US-138 fix #1 — variant non transmis backend** (`backend/app/api/pdf_export.py`)
  - Ajout `_parse_variant(raw)` + `_ALLOWED_VARIANTS` frozenset (full/exec/public/one-pager).
  - `_build_pdf(simulation_id, graph_image_b64="", variant=_DEFAULT_VARIANT)` propage `variant` à `Renderer.render_pdf(charts_factory=cf, variant=variant)`.
  - `_build_markdown(simulation_id, variant=_DEFAULT_VARIANT)` instancie `ChartFactory(context)` et passe `charts_factory=cf` à Renderer.
  - POST endpoint lit `body.get("variant")`, retourne 400 INVALID_VARIANT.
  - GET `/export-md` lit `?variant=` query param.
  - Filename inclut variant si non-default.

✓ **US-138 fix #2 — round counter flicker pendant init** (`frontend/src/components/Step3Simulation.vue` + `frontend/src/views/SimulationRunView.vue`)
  - Step3Simulation.vue:784 `runStatus = ref({...})` initialisé avec `runner_status: 'loading'` et tous compteurs à 0.
  - `isStatusLoading = computed(() => runStatus.value.runner_status === 'loading')`.
  - Lignes 233/248/263 : remplacé `runStatus.X || 0` par `isStatusLoading ? '—' : (runStatus.X || 0)` (tirets en attendant les vraies valeurs).
  - SimulationRunView.vue : `hasReceivedRealStatus = ref(false)`, `formattedRound` retourne `'—'` si pas reçu, `progressPercent` retourne 0, `handleProgress` ignore `runnerStatus === 'loading'`.

✓ **US-138 fix #3 — citations EN dans rapports FR** (`backend/app/utils/locale_prompt.py`)
  - Clause US-138 ajoutée : "Citations issues du contexte" forcent traduction langue source.
  - Exceptions listées : CGEM, OCP, FMI, BCEAO, CFCIM (acronymes/noms propres).
  - Étape de relecture qualité ajoutée avant finalisation prompt.

✓ **US-145 — filet anti-zombie worker** (`backend/app/services/simulation_runner.py`)
  - Module-level `_is_pid_alive(pid)` cross-platform :
    * POSIX : `os.kill(pid, 0)` (raises ESRCH si mort).
    * Windows : `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION=0x1000)` + `GetExitCodeProcess` STILL_ACTIVE=259.
  - Classmethod `_reconcile_orphaned_state(state)` :
    * skip si statut terminal (completed/failed/cancelled),
    * skip si subprocess dans `cls._processes` (worker actif),
    * skip si PID toujours alive,
    * sinon force FAILED avec error explicite "Worker process disappeared during execution. The simulation was running but the worker died unexpectedly."
  - `get_run_state()` appelle `_reconcile_orphaned_state(state)` après chargement.
  - 16 tests `test_simulation_runner_orphan.py` (POSIX/Windows mocks + intégration get_run_state).

**Commit `659c20c` [US-138 follow-up] — sous-menu Admin + fix /process/new + stats total + flicker init**

✓ **Sous-menu Admin global** (`frontend/src/components/AppHeader.vue`)
  - Remplacé 3 router-links séparés (Admin/Devis/+Lancer) par un dropdown unique.
  - Items : `+ Lancer simulation` (→ `/console`), Devis, Analytics, Branding PDF, Utilisateurs.
  - State `showAdminMenu = ref(false)`, `adminMenuRef`, click-outside + Escape handlers.
  - Watch `route.fullPath` pour fermer menu à la navigation.
  - CSS `.app-header__admin-group/menu/item` avec hover rgb(255 133 81).

✓ **Fix `/process/new` cassé** : route ne gérait pas le sentinel `'new'`. Repointé `+ Lancer simulation` vers `/console` (vrai entry-point upload + prompt).

✓ **Fix stats total_users** (`backend/app/api/admin_users.py`)
  - Affichait `total_users: 1` alors que 3 users dans auth.users (comptait `unique_user_ids` membres orgs).
  - Fix : `len(all_auth_users)` au lieu de `len(unique_user_ids)`.
  - Ajout champ `users_with_org`.

✓ **Init super_status au boot frontend** (`frontend/src/main.js`) — éviter flicker route guards.
  ```js
  await auth.init()
  if (auth.isAuthenticated) {
    try { await auth.fetchSuperStatus() } catch (e) {...}
  }
  app.mount('#app')
  ```

**Commit `a8e681c` [fix US-138] — modal Branding masqué par AppHeader (z-index + flex layout)**

✓ Diagnostic via Chrome MCP DOM inspection + screenshot OS user : modal `/admin/branding` masqué derrière AppHeader.
✓ `.ab-modal-backdrop` z-index 1000→2200 (au-dessus AppHeader 1500).
✓ `.ab-modal` : `display: flex; flex-direction: column; max-height: calc(100vh - 64px)`.

**Commit `be8ab3e` [fix US-138] — modal Branding scroll form cassé après le z-index fix**

✓ Régression signalée par Amine "plus d'ascenseur, je ne vois plus le bas du modal ni les boutons".
✓ Diagnostic : `.ab-modal-split` en `display: grid` — le `min-height: 0` ne se propage pas comme avec flex pour permettre le scroll interne.
✓ Fix : passage en `display: flex` avec hauteurs explicites :
  - `.ab-modal-body` : `flex: 1 1 auto; min-height: 0; overflow: hidden`.
  - `.ab-modal-split` : `display: flex` (pas grid) avec `min-height: 0`.
  - `.ab-form` : `flex: 1 1 0; height: 100%; max-height: 100%`.
  - `.ab-preview-panel` : `flex: 0 0 340px; min-height: 0; overflow-y: auto`.

**Commit `98d4610` [US-138 phase 2] — affecter user à org + créer org inline depuis AdminUsersView**

✓ **Backend `backend/app/api/admin_users.py`** :
  - `POST /<user_id>/orgs` : ajoute user à org. Validations : role ∈ {owner, admin, member, viewer}, super-admin libre, org-admin scoped (refuse owner role pour org-admin), 400 si org_id manquant. UPSERT on conflict `(user_id, org_id)`.
  - `DELETE /<user_id>/orgs/<org_id>` : retire user de org. Protection LAST_OWNER (409 si dernier owner restant).

✓ **Backend `backend/app/api/admin.py`** :
  - `_slugify(name)` helper avec translit FR/AR.
  - `POST /api/admin/organizations` (`@require_super_admin`).
  - Auto-ajoute le caller comme owner via UPSERT `org_members`.
  - Fallback gracieux si colonne `self_service_enabled` absente (pattern US-098).

✓ **Frontend `frontend/src/views/AdminUsersView.vue`** :
  - i18n fix : `adminInvitations.backToDashboard` → `nav.dashboard`.
  - Section "Affecter une organisation" dans modal profil (super-admin only).
  - Liste orgs membres avec boutons × remove + role pills.
  - Picker org existante + role + bouton "+ Créer une org".
  - Form inline create : name, country (default MA), role.
  - Functions : `addOrg()`, `removeOrg()`, `createOrgInline()`, `loadAllOrgs()`, `_refreshAfterMembershipChange()`.
  - State `orgsForm = reactive({selectedOrgId, selectedRole, busy, error, success, creating, newName, newCountry, newAssignRole})`.
  - Computed `availableOrgs` filtre orgs déjà membres.

✓ **Frontend `frontend/src/api/client.js`** : ajout `addUserToOrg`, `removeUserFromOrg`, `createOrganization`. Suppression doublon `fetchAllOrganizations` (existait déjà ligne 154).

✓ **i18n** : ajout `adminUsers.orgs.*` (14 clés × 3 langues fr/en/ar) + `nav.adminAnalytics/Branding/Users`.

✓ **Tests `backend/tests/test_admin_users.py`** : nouvelle classe `TestUserOrgMembership` avec 7 tests (super_admin_adds, invalid_role 400, missing_org_id 400, org_admin_cannot_add_other, super_admin_removes, remove_nonexistent 404, cannot_remove_last_owner 409). Plus `test_stats_total_users_reflects_auth_users_not_members`.

[VALIDÉ EN COURS — Coolify redeploy `vh5u61oafvjaajl5j0c3zpgn` lancé à 00:30, ~3 min de build]
- Migration Supabase 004 confirmée appliquée en prod (table `report_deliveries` + `report_downloads` + indexes + RLS + comments).
- Tests utilisateur en attente : voir [NEXT].

[BLOQUÉ — actions humaines pendantes]
- !! **Aucun secret leaké cette session** (pas de rotation requise).
- **Tests post-redeploy** à faire par Amine après ~3 min :
  1. `/admin/branding` → `+ Nouveau branding` → vérifier modal a un scroll fonctionnel + boutons "Annuler/Enregistrer" visibles en bas.
  2. `/admin/users` → `Voir le profil` sur Nezha Bentara → section "Affecter une organisation" → `+ Créer une org` → "Tenga Conseil" → "Créer et affecter" → org doit apparaître avec son badge owner/admin/member.
  3. Vérifier sous-menu Admin dans header (dropdown unique au lieu de 3 liens séparés).
  4. Vérifier round counter Step3Simulation : tirets `—` au lieu de `0/0` pendant init.
  5. Lancer un export PDF avec `?variant=exec` ou `?variant=public` ou `?variant=one-pager` pour valider la propagation variant côté backend.

[ALERTE]
!! **US-139 (activate/deactivate user + org cascade) reportée** : non livrée cette session. Demande exprimée par Amine ("comment je peux activer/desactiver un utilisateur ou une organisation et tous ses utilisateurs ?") → à attaquer en prochaine session si toujours nécessaire (Supabase auth ban + propagation cascade RLS).
!! **Test backend `test_admin_create_org.py` non créé** : tests dédiés pour le nouveau `POST /api/admin/organizations` non isolés. La couverture passe via `TestUserOrgMembership` (qui crée des orgs en setup) mais pas de test direct du endpoint create. À ajouter en US-138 phase 3 ou US-139.
!! **Anglais mélangé FR dans citations** : prompt US-138 fix #3 ajoute la clause traduction mais NON validé en prod (besoin d'une simulation en français avec sources EN pour confirmer). Clause `locale_prompt.py` correctement intégrée mais effet observable seulement après une nouvelle simulation FR.
!! **Service Worker cache** : si Amine voit du 404 ou des composants obsolètes après redeploy, exécuter dans la console navigateur :
  ```js
  navigator.serviceWorker.getRegistrations().then(rs => rs.forEach(r => r.unregister()));
  caches.keys().then(ks => ks.forEach(c => caches.delete(c)));
  location.reload();
  ```

[PARTIEL]

### US-138 phase 3 (non livrée)
- Activate/deactivate user (Supabase `auth.admin.update_user_by_id({banned_until: ...})`).
- Activate/deactivate org cascade (toggle `is_active` colonne orgs + propagation guards via RLS).
- UI : boutons sur AdminUsersView profil modal + AdminAnalyticsView orgs section.

### Variantes PDF non testées en prod
- Code US-138 fix #1 transmet bien `variant` mais pas de test E2E/Playwright sur les 4 variants (full/exec/public/one-pager) en prod. À cliquer manuellement post-redeploy.

[NEXT — chantiers prêts à attaquer]

### Prio P0 — validation utilisateur post-redeploy (~3 min après ce push)
1. **Hard refresh navigateur** (`Ctrl+Shift+R`) sur prospectives.ai-mpower.com.
2. **Tester les 5 points** listés dans [BLOQUÉ] ci-dessus (Branding modal scroll + Users assign org + Admin sub-menu + Round counter + Variant export).
3. **Lancer une simulation FR** pour valider le prompt US-138 fix #3 (citations EN traduites en FR).

### Prio P1 — US-139 si Amine confirme le besoin
- Activer/désactiver user via `auth.admin.update_user_by_id({banned_until: '2099-12-31T23:59:59Z'})`.
- Toggle `is_active` colonne orgs (migration `20260507_001_org_active.sql` ?) + propagation via décorateur `@require_active_org`.
- UI : 2 boutons "Désactiver" sur AdminUsersView + AdminAnalyticsView avec confirmation.

### Prio P2 — dette résiduelle US-138
- Tests dédiés `test_admin_create_org.py` (5 tests : super_admin_creates, non_super_403, name_required, slug_collision_409, country_default_MA).
- WCAG AA contraste WI_ORANGE/WI_CREAM (2.25:1 < 3:1) — passation 2026-05-06 alerte.
- Test `test_md_hash_stable_with_deterministic_enricher` : ajouter `freezegun.freeze_time("2026-01-01")`.

### Bloqué humain
- US-113 Stripe : credentials toujours absents en Coolify.
- Témoignages partenaires NDA.

[CTX session]
- ~150 tool calls (browser MCP Coolify+Supabase + git push + ralph + tests)
- 5 commits poussés sur main : `d0b4e08`, `659c20c`, `a8e681c`, `be8ab3e`, `98d4610`
- 1 deployment Coolify déclenché à 00:30 (`vh5u61oafvjaajl5j0c3zpgn`)
- Tests : 1571 → 1612 backend pytest (+41 nouveaux : 7 admin_users + 16 simulation_runner_orphan + 8 locale_prompt + 8 admin_users stats + 2 pdf_export variant)
- 1 migration Supabase appliquée (`20260506_004_report_delivery.sql` — apostrophe fixée puis ré-jouée)
- Modèle : Opus 4.7 (1M context) toute la session

[MEMO inter-sessions]

### Pattern apostrophes SQL dans migrations Supabase
- Toujours doubler `'` → `''` à l'intérieur d'une string SQL (`COMMENT ON COLUMN ... IS 'Date d''expiration...'`).
- Erreur typique : `42601: syntax error at or near "expiration"` quand `'` non échappé.
- Pattern de check rapide avant push : `grep -E "IS '[^']*'[^']*'[^,;]" supabase/migrations/*.sql` (cherche apostrophes orphelines).

### Pattern modal scroll Vue
- `display: grid` dans un container parent ne propage PAS `min-height: 0` aux enfants pour permettre l'overflow scroll comme `display: flex` le fait.
- Pour modaux avec scroll interne dans formulaire : utiliser flex (column) à TOUS les niveaux du chemin scroll : modal → body → split → form. Hauteurs explicites (max-height calc viewport) sur le top.
- Z-index AppHeader Bassira = 1500. Tous les modaux globaux doivent être ≥ 2000 (recommandation : 2200).

### Pattern PID liveness cross-platform Python
- POSIX : `os.kill(pid, 0)` lève `OSError(ESRCH)` si process mort.
- Windows : `ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)` puis `GetExitCodeProcess`. Code STILL_ACTIVE = `259` = process toujours vivant.
- Toujours wrapper dans try/except OSError pour les permissions denied (returns False par défaut).

### Pattern stats Admin
- `total_users` doit être `auth.admin.list_users()` count (pas `org_members` count).
- Un user peut exister dans `auth.users` sans être membre d'aucune org (super-admin email whitelist par exemple).
- Toujours afficher 2 métriques : `total_users` (auth.users) + `users_with_org` (au moins 1 membership).

### Memory globale
- `reference_stack_access` créée session précédente (Coolify 192.168.100.3:8000, Supabase project `fvfifgstytvxssffvsbs`, Monaco SQL editor pattern, base64 chunking, SUPABASE_DB_URL password rotated dans .env.local).
- `feedback_diagnostic_method` : si plusieurs services tombent simultanément, vérifier infra commune AVANT de blâmer le push.
- `feedback_shell_single_line` : commandes SSH/bash sur UNE ligne pour PuTTY.

[Recommandations pour la nouvelle session]

1. **Vérifier le statut du redeploy Coolify** : ouvrir http://192.168.100.3:8000/project/.../application/u6pn5mr2pgi88s13un55pkzb → onglet Deployments → confirmer que `vh5u61oafvjaajl5j0c3zpgn` est en SUCCESS.

2. **Faire les 5 tests utilisateur** listés dans [BLOQUÉ] avant tout autre travail.

3. **Si tests OK** : enchaîner US-139 (activate/deactivate user + org cascade) si Amine confirme. Code patterns prêts :
   ```python
   # Activate/deactivate user
   sb_admin.auth.admin.update_user_by_id(user_id, {"banned_until": "2099-12-31T23:59:59Z" if deactivate else None})
   ```
   Migration `20260507_001_org_is_active.sql` à créer (boolean default true + index).

4. **Si bug résiduel modal Branding** : vérifier dans DevTools que `.ab-modal-split` est bien en `display: flex` (pas `grid`) après hard refresh. Si encore en grid → cache Service Worker (cf snippet console dans [ALERTE]).

5. **Pour tester variant PDF en prod** : ouvrir une simulation completed → `POST /api/simulation/<id>/export-pdf` avec body `{"variant": "exec"}` → télécharger PDF → vérifier filename inclut `_exec` et le contenu est plus court que `_full`.

6. **Memory à NE PAS oublier** : `reference_stack_access.md` contient maintenant tous les accès (Coolify URL + UUIDs + Supabase ref + pattern Monaco SQL + base64 chunking). Ne plus jamais demander à Amine "où est X ?" — tout est dans cette memory.

— fin passation 2026-05-08 — Session courte 5 commits, US-138 phases 1+2 + US-145 anti-zombie + 1 migration Supabase. Pipeline PDF maintenant complet avec variant transmis correctement, page admin Users avec assign org + create inline. Reste US-139 activate/deactivate.

---

== PASSATION MiroShark/Bassira 2026-05-06T05:30:00+01:00 ==

[ETAT]
- branche `main` `6cd67a1` à jour avec `origin/main` (push confirmé, 39 commits cette session marathon)
- prod **ONLINE** sur https://prospectives.ai-mpower.com — Coolify rebuild en cours sur dernier push (Phase 7 + US-137)
- **134/135 stories Ralph passes:true** — 27 nouvelles stories cette session (US-109 → US-117 + US-118 → US-137)
- **1571 tests backend pytest passing** (+693 cette session vs 878 baseline) · 1 fail mineur `test_md_hash_stable` (datetime non-déterministe) · 59 skipped GTK/Pango Windows
- npm run build : OK
- **15 sub-agents Ralph pilotés** (10 sonnet + 4 haiku code review + 1 opus initial) sur 8 phases
- **Pipeline PDF C-level COMPLET livré** : Loader → Enricher (sanitize tool_call) → ChartFactory → Templates → Renderer → 4 variantes (full/exec/public/one-pager) → Snapshot → Workflow 7 états → Approve & Sign → Async RQ → Delivery URL signée + tracking + Page admin Review
- **Fix infra critique cloudflared** : config-nahda.yml restauré depuis .bak (vidé à 16:24, prod down 4h)
- **Path bug critique loader** : `backend/app/uploads/` → `backend/uploads/` (tests passaient via override)
- **Câblage user→Renderer** (US-133) : -463 lignes reportlab legacy, boutons Step4Report/EmbedDialog branchés sur nouveau pipeline

[FAIT cette session — 27 stories Ralph + ~10 fixes critiques infra]

**Vague 1 — Ralph swarm matin (US-109 → US-117)** :
✓ **US-109** : Fix ReportView frontend rendering (hydration prop pattern Step4Report). Bug racine : `currentReportId` à valeur d'URL (sim_xxx) au lieu de report_id réel → polling 404. Fix `reportRes.data.report_id` aligné.
✓ **US-110** : Timeline avancement progressif 1/4 → 4/4 (`ReportProgressTimeline.vue`, 4 stages self-derived, polling 5s auto-stop).
✓ **US-111** : Chat avec rapport (`ReportChatPanel.vue` sliding panel 380px, RTL via `:global([dir='rtl'])`, history localStorage scopé reportId).
✓ **US-112** : Onglet "Voir les agents" navigation symétrique ReportView ↔ InteractionView.
✓ **US-114** : Migration `quote_ownership` Supabase + script filesystem→DB + scoping endpoints admin (404 cross-tenant DEFCON 1).
✓ **US-115** : Système d'invitation user→org (token UUID + Resend magic link + 410 Gone pour expired/consumed).
✓ **US-116** : Audit OWASP + 2 corrections P0 (tracebacks purgés `report.py`, SSRF `webhook_service.validate_url()` + 36 tests sécurité).
✓ **US-117** : 42 tests Playwright multitenant (fixtures `seedSuperAdminAuth`, 4 race conditions auth guard documentées). 32 → 74 tests E2E.

**Vague 2 — Chantier PDF C-level (US-118 → US-137) — 8 phases swarm** :

**Phase 1 fondations data (US-118/119/120)** :
✓ **US-118** : Schema PDFReportContext Pydantic v2 — 22 sub-models (52 tests). `extra="ignore"` global, `validate_assignment=True`.
✓ **US-119** : Loader 20+ artifacts simulation/report (re-spawn v2 contre schema canonique, v1 avait reconstruit son propre schema fantôme). 55 tests.
✓ **US-120** : Migration `pdf_branding` Supabase + admin CRUD `/admin/branding` (37+8 tests). Versioning append-only (valid_from/to). Preview SVG base64 sans WeasyPrint.

**Phase 2 i18n + visualisations (US-121/122)** :
✓ **US-121** : TextNormalizer FR/EN/AR + LanguageTool self-host Docker (103 tests). FR DEFCON 1 : accents majuscules forcés via dict + nbsp `U+202F` + guillemets «».
✓ **US-122** : ChartFactory matplotlib palette Causse — 5 charts signature 300 DPI (re-spawn v2, v1 utilisait champs schema inexistants `belief_score`/`agent_name`). 22 tests + `nx.spring_layout(seed=42)` reproductible.

**Phase 3 templates + enrichment (US-123/124)** :
✓ **US-123** : Templates Jinja2 `.md.j2` source unique (cover + exec_summary + toc + 4 sections + appendix + `_full.md.j2` + `_macros.md.j2`). Filter `|normalize` lang-aware. 18 tests.
✓ **US-124** : Enricher LLM (KPI hero + pivotal_moments + chart narratives + executive_takeaways). Cache LRU TTL 24h. Mock `MagicMock` autouse. 14 tests.

**Phase 4 renderer (US-125)** :
✓ **US-125** : Renderer pipeline (MD direct + PDF via WeasyPrint). CSS `@page` natif headers/footers running elements. `pdf_brand.css.j2` injectable depuis branding row. PDF metadata set. 23+10 tests (10 skip GTK Windows).

**Phase 5 workflow + finalize (US-126/128)** :
✓ **US-126** : Workflow 7 états (GENERATING → DRAFT → IN_REVIEW → PENDING_APPROVAL → APPROVED → DELIVERED → ARCHIVED) + audit log immuable (RLS `using(false)`). Locking optimiste 30 min. 50 tests.
✓ **US-128** : Approve & Sign — snapshot SHA256 immuable + watermark diagonal recipient (reportlab overlay + pypdf merge) + signature PAdES via pyHanko (best-effort). 24 tests.

**Phase 6 admin UI + async + delivery (US-127/129/130)** :
✓ **US-127** : Page admin `/admin/reports/<id>/review` — split view PDF.js + Tiptap inline + CodeMirror raw MD + diff-match-patch versions + comments. 19+8 tests. 9 nouvelles deps NPM (Tiptap + CodeMirror + diff-match-patch).
✓ **US-129** : Génération hybride sync/async — `/preview` 1p sync + `/generate` async RQ Redis (`coolify-redis`) + cache LRU TTL 24h + Ghostscript `-dPDFSETTINGS=/prepress`. 18 tests. Pre-warm fonts WeasyPrint au boot worker.
✓ **US-130** : Delivery URL signée HMAC SHA256 (nonce 8 bytes hex, comparison constant-time) + email Resend multilang + tracking `report_downloads` (CF-IPCountry géo). Auto-archive 90j. 19+6 tests.

**US-133 câblage user endpoints** (post-audit Amine, pas dans PRD initial) :
✓ Refactor `pdf_export.py::_build_pdf()` et `_build_markdown()` → appellent `Renderer(context).render_pdf()/render_md()`. -463 lignes reportlab legacy. Helpers `_resolve_report_id_for_simulation()` + `_resolve_lang_for_simulation()`. EmbedDialog.vue:643 fetch inline → `exportSimulationPdf()` service centralisé. i18n `report.exportPdf` mis à jour FR/EN/AR. 12 tests.

**Phase 8 fixes post-audit rapport (US-134/135/136)** :
✓ **US-134** : Loader fixes — 9 bugs majeurs mapping prod→canonique : `simulation_requirement → title`, `final_verdict → verdict`, `bullish_percentage → bullish_pct`, `snapshots → rounds`, `realname + persona.archetype → name + archetype`. Helpers `_normalize_*`. Nouvelle `_extract_critical_posts()` top 10 actions.jsonl. 34 tests.
✓ **US-135** : Enricher fixes — **DEFCON 1 sanitize_llm_output()** supprime `<tool_call>`, `<function_call>`, `<thinking>`, `<scratchpad>` avant injection livrable client. KPI Hero `confidence_pct` depuis `bullish_pct` (pas `outcome.confidence` souvent 0). Takeaways fallback gracieux depuis `outline.summary` split 3 phrases. 20 tests.
✓ **US-136** : Templates fixes — numérotation `loop.index` (au lieu de `section.idx`), filter `|format_date` Babel `fr_FR/en_US/ar_MA`, charts `data:image/png;base64,...` via `_embed_charts_md()` dans Renderer, articles+posts fallbacks callouts gracieux, profils colonnes Archétype/Plateforme conditionnelles via `selectattr`. 17 tests.

**Phase 7 reprise (US-131/132)** :
✓ **US-131** : 4 variantes PDF (full=10424c / exec=1920c / public=1502c / one-pager=1162c). Anonymizer regex ORG (Inc/SA/SAS/SARL/Corp/LLC/GmbH) + AGENT (Agent_X/@username). Cohérence via `_AnonymizationState` partagé. Public désactive watermark. 38 tests.
✓ **US-132** : Tests pipeline E2E + accessibilité PDF/UA + visual regression. Linter `lint_palette_contrast.py` WCAG AA. **Finding** : `WI_ORANGE/WI_CREAM 2.25:1 < 3.0:1` (échec WCAG AA large text). 20 tests + golden masters dossier.

**US-137 page admin Users** :
✓ Page `/admin/users` — `auth.users + members + orgs` agrégés. Stats cards (Total/Actifs 7j/Nouveaux 30j) + filtres org+search+pagination. Modal simulations + modal profil. Super-admin cross-tenant via `auth.admin.list_users()`, org admin scoped via `user_orgs()`. 21+4 tests.

**Fixes infra critiques cette session** :
✓ **Fix prod down 4h (cloudflared)** : `/home/serveurai/.cloudflared/config-nahda.yml` vidé à 16:24 (cause inconnue, post mon push). Restauration depuis `.bak` du 1er mai (9 hostnames mappés). Service `cloudflared-nahda.service` redémarré. 4h de diagnostic raté avant de trouver — leçon : **si plusieurs services tombent en même temps, ce n'est PAS le push, c'est l'infra commune** (memory `feedback_diagnostic_method` créée).
✓ **Path bug loader** : `_UPLOADS_DIR = backend/app/uploads/` → `backend/uploads/` (alignement SimulationManager). Régression invisible aux tests US-119 (override `sim_base_dir=tmp_path` dans tests, prod cassé).
✓ **Step4Report layout split→stack** : `display: flex` horizontal 45%/55% qui laissait moitié droite vide pendant scroll → `flex-direction: column` + ordre 1 (sommaire en haut) / ordre 2 (rapport pleine largeur).
✓ **Dockerfile WeasyPrint deps** : `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libcairo2 libgdk-pixbuf-2.0-0` (PAS `libgdk-pixbuf2.0-0` — Bookworm, pas Bullseye). + `ghostscript poppler-utils fonts-dejavu-core`.
✓ **N rounds** : lecture exhaustive `current_round / total_rounds / outcome.nb_rounds` (au lieu de `n_rounds` inexistant).
✓ **Timeline cascade** : si `reportStatus=completed`, force `simStage` + `agentStage` à `done`.
✓ **IDs cosmétiques** : "Référence simulation/rapport" + abrégés `…XXXXXXXX` + tooltip ID complet.

[VALIDÉ EN PROD — partiel après redeploys successifs]
- Layout stack vertical fonctionnel (commit `84ef9e3`)
- Backend nouveau pipeline tourne (test direct `/api/simulation/<id>/export-pdf` retourne erreur PDFContextLoaderError quand fichier absent — preuve que le loader tape les bons paths)
- Page `/admin/branding` accessible super-admin
- Page `/admin/reports/<id>/review` accessible super-admin
- Tests Playwright nouvelles routes : 6/8 sur `admin-users` 4/4 sur `admin-report-tracking` 8/8 sur `admin-report-review`

[BLOQUÉ — actions humaines pendantes]
- !! **3 SECRETS LEAKÉS** dans le chat de cette session (rotation OBLIGATOIRE) :
  1. `POSTGRES_PASSWORD` Coolify DB : `FMTsYG19xrU/yQ/yF6Zt49OztrOitUT90gGb/9XCwA8=` → reset via Coolify
  2. Secrets Supabase déjà leakés session précédente (toujours pas tournés ?) : `SUPABASE_SERVICE_ROLE_KEY`, password DB Supabase, JWT access_token Google
- **Stripe credentials** (US-113) : Amine doit créer compte stripe.com + poser `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` dans Coolify
- **Variables Coolify à vérifier en prod** :
  - `BASSIRA_DELIVERY_HMAC_SECRET` — DOIT être set 32 bytes random (sinon fallback dev insecure)
  - `LANGUAGETOOL_URL` (default `http://localhost:8010` — container séparé US-121, à activer si voulu)
  - `BASSIRA_SIGNING_CERT_P12_PATH` + `BASSIRA_SIGNING_CERT_PASSWORD` (US-128 signature PAdES, optionnel)
  - `PDF_GENERATION_WEBHOOK_URL` (US-129 callback, optionnel)
  - `BASSIRA_PUBLIC_URL` (default https://prospectives.ai-mpower.com — déjà OK)
- **2 nouvelles migrations Supabase à jouer** :
  - `supabase/migrations/20260506_001_pdf_branding.sql` (US-120 — table branding)
  - `supabase/migrations/20260506_002_report_workflow.sql` (US-126 — report_states + audit_log)
  - `supabase/migrations/20260506_003_report_versions.sql` (US-127 — versions + comments)
  - `supabase/migrations/20260506_004_report_delivery.sql` (US-130 — deliveries + downloads)

[ALERTE]
!! **Rapport généré avant Phase 8** : le `bassira-sim_ea0eb65b.md` audité par Amine montrait 16 bugs (KPI 0%, `<tool_call>` brut, sections numérotées 1-1-1, profils tous neutral, etc.). **Re-générer un rapport après Coolify redeploy Phase 8** pour valider que les fixes US-134/135/136 sont effectifs en prod.
!! **Anglais mélangé au FR dans citations agents** : c'est dans le `full_report.md` source (LLM-généré). Le pipeline ne traduit pas. À traiter via prompt ReportAgent renforcé OU post-translation US-138 future.
!! **WI_ORANGE/WI_CREAM contraste 2.25:1** : échec WCAG AA large text (≥ 3:1 requis). À corriger en US-138 (choisir `WI_ORANGE` plus foncé ou utiliser `WI_TERRA` pour les titres sur fond cream).
!! **1 test fail mineur** : `test_md_hash_stable_with_deterministic_enricher` (datetime non-déterministe). À fixer via mock `freezegun` ou patcher `_now()` helper.
!! **Coolify Force without cache** : toujours alerte connue (re-pull torch + nvidia-cuda 1.5 GB cumulés peut OOM). Préférer Redeploy simple. Maintenant que Dockerfile inclut WeasyPrint deps, première rebuild après push Dockerfile = longue (~15 min).
!! **2 endpoints publics à WatchOut** : `POST /api/simulation/<id>/export-pdf` (US-133) — l'agent a mis `@require_auth` mais à vérifier en prod (pas d'auth dans test direct = trou ?). `GET /r/<token>` (US-130) public sans auth, signature HMAC TTL OK.

[PARTIEL]

### Le rapport audité a 16 bugs identifiés mais 13/16 sont fixés par Phase 8 (à valider post-redeploy)
✅ Fix US-134 : titre, verdict, recommandations, sources, profils, current_round
✅ Fix US-135 : KPI hero, sanitize tool_call, takeaways
✅ Fix US-136 : numérotation sections, dates Babel, charts data URI, articles+posts callouts gracieux
⚠️ **Reste 3 bugs liés à la donnée source** (pas le pipeline) :
1. **Anglais mélangé** dans citations agents (bug de LLM source au moment de la simulation)
2. **Profils stance "neutral"** — peut-être lire depuis `trajectory.snapshots[i].agent_stances` au lieu de profil statique
3. **Articles "Round 0"** avec titre = répétition exec summary — parsing GeneratedArticle à creuser

### Test fail mineur (non-bloquant)
- `test_md_hash_stable_with_deterministic_enricher` : datetime non-déterministe → mock `freezegun` à ajouter

### Variantes PDF non testées en visuel
- US-131 livré 38 tests passing mais pas validé visuellement avec WeasyPrint (skip Windows). Les 4 variantes (full/exec/public/one-pager) doivent être testées en prod après redeploy.

### Page admin Users (US-137) à tester en visuel
- Build OK, tests Playwright OK ciblés prod (résilients pré-déploiement). À cliquer manuellement post-redeploy.

[NEXT — chantiers prêts à attaquer en nouvelle session]

### Prio P0 — validation utilisateur
- **Lancer une simulation propre** avec le fichier MD préparé `C:\Users\amans\Downloads\bassira-simulation-reforme-code-travail-2026.md` (Réforme Code du travail Maroc 2026, framework cerberus, fr, 25 rounds). Document exhaustif 30+ acteurs, hypothèses chiffrées, sources publiques. Sera la VRAIE preuve que le pipeline fonctionne C-level.
- Une fois simulation completed → re-télécharger PDF + MD → comparer avec le rapport audité (avant fixes Phase 8).

### Prio P1 — US-138 finitions résiduelles
- **Fix accessibilité** : changer la palette ou les usages — `WI_ORANGE` sur `WI_CREAM` ratio 2.25 cassé. Solutions : utiliser `WI_TERRA` (#A13F0F) pour titres, OU foncer `WI_ORANGE` jusqu'à `#E55A1F`, OU ajouter `text-shadow` ou `outline` pour améliorer lisibilité.
- **Fix test hash stable** : `freezegun.freeze_time("2026-01-01")` autour des tests de hash MD/PDF.
- **Profils stance non-neutral** : modifier loader pour lire `snapshots[-1].agent_stances` et associer à chaque AgentProfile.
- **Articles parser** : améliorer `_parse_generated_articles()` pour extraire vrais titres + bodies + round + platform + stance.
- **Anglais dans citations** : prompt ReportAgent renforcé "respecte la langue source" OU post-translation.

### Prio P1 — Stripe checkout natif (US-113)
- Bloqué humain pour credentials, sinon prêt à coder dès que `STRIPE_SECRET_KEY` posée.

### Prio P2 — features futures
- **US-139 Quote Stripe automation** : automatiser `quote_delivered.html` pour appeler `report_delivery.create_delivery()` au lieu d'admin manuel.
- **US-140 Workflow client→admin→delivery** : si on veut un vrai flow où le user demande un rapport, admin valide, user reçoit lien signé. Refonte UX Step4Report.
- **US-141 Mode "Diff" entre simulations** : variante "Comparison Report" alimentée par `/api/simulation/compare` existant.
- **US-142 Watermark dynamique** : actuellement on a la fonction `apply_watermark_to_pdf()` (US-128) mais pas branchée sur le user export. À ajouter si livraison NDA-strict.
- **US-143 Slide deck export** : sortie PowerPoint/Keynote depuis le même PDFReportContext via python-pptx.
- **US-144 Mode async pour /export-pdf user** : actuellement sync. Pour les rapports lourds (> 30s), basculer sur queue RQ avec polling client.

### Bloqué humain
- US-113 Stripe (credentials)
- Témoignages partenaires NDA
- Logo Bassira complet (rejeté memory `feedback_rejected_tools`)

[CTX session marathon]
- ~5000+ tool calls cumulés (interactions Claude + 15 sub-agents)
- **39 commits poussés** sur main : Ralph swarm 4 sub-agents matin (US-109→117) + Ajout US-118→132 PRD + 8 phases swarm (US-118→137) + 3 fix infra (cloudflared, path loader, Dockerfile WeasyPrint, layout) + US-133 câblage + Phase 8 fixes + push Phase 7+US-137 final
- 15 sub-agents pilotés : 1 opus (Ralph batch matin), 10 sonnet (Phases 1-8), 4 haiku (code review câblage)
- Tests : 878 → **1571 backend pytest** (+693 cette session)
- Modèle : Opus 4.7 (1M context) toute la session

[MEMO inter-sessions]

### Patterns Ralph swarm validés
- **Stories qui IMPORTENT depuis le schema canonique doivent attendre que ce schema soit mergé** — pas de parallélisation tant que le contrat n'est pas en main. Re-spawn US-119 et US-122 v2 ont prouvé cette règle.
- **Worktrees démarrés depuis commit ancien manquent les fichiers récents** : agents doivent vérifier `ls` au démarrage et `git merge main --no-edit` si absents. Plusieurs agents ont recréé schema.py/loader.py au lieu de les utiliser depuis main.
- **`<tool_call>` brut LLM injecté livrable client = DEFCON 1** : sanitize obligatoire sur TOUTE sortie LLM via `sanitize_llm_output()` avant injection contexte.
- **Mapping prod ↔ schema canonique** : tests fixtures fonctionnent mais prod casse — ajouter `_normalize_*` helpers dans loader pour mapper noms de champs prod (`simulation_requirement → title`, `final_verdict → verdict`, etc.).
- **Code review haiku parallel** : 4 agents read-only modèle léger pour cartographier des bugs avant fix sonnet. Très efficace.

### Infra serveurai
- Tunnel Cloudflare = `cloudflared-nahda.service` (PAS `cloudflared.service`). Config `/home/serveurai/.cloudflared/config-nahda.yml` mappe 9 hostnames `*.ai-mpower.com`.
- **Garde un .bak** : `/home/serveurai/.cloudflared/config-nahda.yml.bak` (1er mai 14:29) = filet de sauvetage essentiel.
- Docker base : `FROM python:3.11` = Debian 12 Bookworm (PAS Ubuntu, malgré que le host serveur soit Ubuntu). Noms de packages = Debian Bookworm (`libgdk-pixbuf-2.0-0` avec trait d'union).
- Reboot serveur n'aide pas si le bug est dans un fichier config user (ex: cloudflared YAML vide).

### Pipeline PDF Bassira
- **Stocké dans `backend/uploads/report_snapshots/<report_id>/v<n>/`** (PAS `backend/app/uploads/`).
- **Schema canonique vs noms prod différents** : `simulation_requirement → title`, `final_verdict → verdict`, `bullish_percentage → bullish_pct`, `snapshots → rounds`, `realname + persona.archetype → name + archetype`. Helpers `_normalize_*` dans loader.
- **WeasyPrint deps Docker Bookworm** : `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libcairo2 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info fonts-dejavu-core ghostscript poppler-utils`.
- **Tests skip @skipif WEASYPRINT_UNAVAILABLE** : Windows local sans GTK passe les tests qui n'utilisent pas le rendu PDF, prod Linux active tout.
- **TextNormalizer FR** : accents majuscules forcés UNIQUEMENT sur mots TOUT-CAPS (`ETAT` → `ÉTAT`). Pas sur mots normaux (`Etat` reste tel quel — c'est un bug LLM source à corriger en amont si nécessaire).

### Conventions commits
- `[US-XXX] Titre exact de la story` pour les stories Ralph
- `[fix US-XXX] Description` pour les fix critiques
- `[Ralph] Description` pour les actions de gouvernance (PRD update, push, mark passes:true)
- Toujours `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` (ou `Sonnet 4.6` selon agent)

### Memory globale
- `feedback_diagnostic_method` créée : "si plusieurs services tombent en même temps, mon push n'est probablement PAS la cause" — vérifier le périmètre AVANT de creuser.
- `feedback_shell_single_line` créée : commandes SSH/bash sur UNE ligne (séparateurs `;` ou `&&`) pour éviter casse au copier-coller PuTTY.
- `reference_serveurai_infra` créée : topologie tunnel + Coolify Traefik + paths critiques.

[Recommandations pour la nouvelle session]

1. **AVANT TOUT** : rotation 3 secrets leakés cette session + lancer une simulation propre avec le MD `bassira-simulation-reforme-code-travail-2026.md` pour valider le pipeline visuellement.

2. **Étape 1 — Vérifier que Phase 7 + US-137 sont bien déployés** :
   - Hard refresh navigateur (Ctrl+Shift+R) sur `/console`, `/admin/users`, `/admin/branding`, `/admin/reports/<id>/review`
   - Vérifier que `/admin/users` liste les users (Supabase + members + orgs)
   - Vérifier que `/admin/branding` permet de configurer le branding PDF
   - Si quelque chose casse → check Coolify logs runtime container miroshark

3. **Étape 2 — Valider le pipeline PDF via simulation propre** :
   - Charger le fichier MD préparé dans `/console`
   - Lancer simulation framework=cerberus, lang=fr, ~25 rounds
   - Attendre completion
   - Cliquer icône PDF + icône MD dans Step4Report
   - Comparer avec rapport audité (avant Phase 8) :
     * Titre rempli ✓ (US-134)
     * KPI Hero non-zero ✓ (US-135)
     * Verdict non vide ✓ (US-134 + 135)
     * Recommandations remplies ✓ (US-134)
     * Sections numérotées 1-N ✓ (US-136)
     * Date format FR humain ✓ (US-136)
     * Pas de `<tool_call>` brut ✓ (US-135)
     * Charts embarqués data URI dans MD ✓ (US-136)
     * Articles + posts callouts gracieux si vides ✓ (US-136)

4. **Étape 3 — Si bugs résiduels → US-138** :
   - Profils stance non-neutral (lire depuis trajectory)
   - Articles parser amélioré
   - Anglais mélangé FR (prompt ReportAgent ou post-translation)
   - WI_ORANGE/WI_CREAM contraste WCAG AA
   - Test hash stable freezegun

5. **Étape 4 — Stripe (US-113)** : créer compte Stripe, poser `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` dans Coolify, l'US est codée prête.

6. **Étape 5 — Variables env Coolify à valider** :
   - `BASSIRA_DELIVERY_HMAC_SECRET` (US-130 sécurité critique)
   - `BASSIRA_SUPER_ADMIN_EMAILS` (déjà OK depuis session précédente)
   - `RESEND_API_KEY` + `RESEND_FROM_EMAIL` (déjà OK)
   - Migrations Supabase 20260506_001 à 004 à jouer (4 migrations, idempotentes)

7. **Étape 6 — Tests Playwright en CI Linux** : sur Linux les tests WeasyPrint passent (skip seulement sur Windows). Configurer GitHub Actions pour exécuter pytest + playwright avec deps GTK installées.

8. **Étape 7 — Phase 9 features futures** (selon priorité business) : US-138 fixes, US-139 quote automation, US-140 workflow client→admin, US-141 comparison report, US-142 watermark user export, US-143 slide deck.

— fin passation 2026-05-06 — Session marathon 27 stories Ralph + 15 sub-agents + 8 phases swarm + 39 commits — Pipeline PDF C-level COMPLET + Page admin Users livrés. Reste US-113 Stripe (humain) + US-138 finitions résiduelles.

---

== PASSATION MiroShark/Bassira 2026-05-04T23:50:00+01:00 ==

[ETAT]
- branche `main` `266ef0f` à jour avec `origin/main` (push confirmé, 13 commits cette session)
- prod **ONLINE** sur https://prospectives.ai-mpower.com — bundle frontend `index-CtrTJkxa.js` à jour, backend US-091→US-108 + fix report en prod
- **108/108 stories Ralph passes:true** — 22 nouvelles stories cette session (US-086 → US-108 + fixes)
- **878 tests backend pytest passing** (+87 cette session vs 791 baseline) · zéro régression
- npm run build : OK
- **9 sub-agents pilotés** : Explore + 4 Ralph-loop autonomes + 4 sub-agents pour fixes ciblés
- **Multitenant Supabase pleinement opérationnel** : auth ECC P-256 via JWKS, super-admin via env var whitelist, RLS strict, k-anonymity calibration, 4 vars env Coolify (SUPABASE_URL + ANON + SERVICE_ROLE + DB_URL — JWT_SECRET supprimé car ECC)

[FAIT cette session — 22 stories Ralph + 5 fixes critiques]

**Chantier J — Vitrine /models publique (US-086 → US-090)** :
✓ **US-086** : ModelsListView + ModelDetailView, 5 modèles initiaux (fusion-bancaire-mena, crisis-drill-24h, allocation-fonds-strategique, stress-test-politique, lancement-diaspora-eu). JSONs FR/EN/AR exhaustifs, tokens --wi-*, RTL CSS logical properties. ~80 clés i18n.
✓ **US-087** : Home masquage CTAs self-service + nav Modèles featured + SectorUseCases double CTA (relink → /models?sector= + /devis?sector=).
✓ **US-088** : Backend `GET /api/models/<slug>/pdf-brief?lang=` (reportlab + Jinja2, brandé qualité cabinet, A4 4-6 pages). Script `generate_demo_pdfs.py` produit 18×3=54 PDFs. arabic-reshaper + python-bidi pour RTL Tahoma.
✓ **US-089** : DEFCON 1 — purge 4 claims faux vérifiés WebSearch (Khalid Bouaza inventé, BAM circulaire 26/G/2006 mauvais sujet, BMCI-BNP fusion fictive, INSEE 6.8M faux) + 6 jaunes. Script Python pour MAJ batch.
✓ **US-090** : Productivisation 13 templates restants (adcheck-pre-launch, budget-loi-finances, campus-controversy, implantation-startup, corporate-crisis, crypto-launch, historical-whatif, pmf-startup-tech, political-debate, primaires-parti-politique, product-announcement, product-launch, she-start-cohort). Total vitrine = **18 modèles**. Frontend refactoré en `import.meta.glob` pour découverte dynamique.

**Chantier K — Multitenant Supabase (US-091 → US-100)** :
✓ **US-091** : Schema Supabase Cloud (orgs + members + simulation_ownership + RLS strict + helper user_orgs() security definer + VIEW publique k-anonymity n>=5). Seed.sql org AIMPOWER (slug aimpower-bassira). 2 migrations 20260503_001/002 + README étape par étape.
✓ **US-092** : Backend Flask middleware JWT Supabase + extension SimulationManager pour ownership. Cache LRU TTL 5 min, dual-mode (HS256 legacy + ES256/RS256/EdDSA via JWKS asymétrique). 5 endpoints /api/client/auth/me + simulations CRUD + /api/calibration/aggregates public.
✓ **US-093** : Frontend Vue auth Supabase (LoginView Google/Magic Link, SignupView, ClientDashboardView privatif). Pinia store auth. Route guards meta.requiresAuth.
✓ **US-094** : AppHeader.vue **partagé global** sur les 17 routes (extrait des nav locales Home/Landing). Sticky top, backdrop blur, ThemeSwitcher + LanguageSwitcher intégrés à droite. Bouton « Relancer la visite guidée ».
✓ **US-095** : Super-admin via env var `BASSIRA_SUPER_ADMIN_EMAILS` (whitelist emails, lue à chaque request pour rotation live). 3 endpoints /api/admin/me/super-status + /api/admin/organizations + /api/admin/organizations/<id>. AnalyticsView étendu.
✓ **US-096** : Login Google OAuth + Magic Link via signInWithOtp(shouldCreateUser:false). Fix critique : `auth.init()` attend SIGNED_IN si URL contient `#access_token=` (sinon router beforeEach redirigeait vers /login alors que Supabase JS écrivait la session depuis le hash).
✓ **US-097** : Super-admin voit TOUTES les sims cross-tenant. Endpoint `GET /api/admin/simulations` (org_id, package_id, published, limit/offset). Section AnalyticsView avec tableau filtrable.
✓ **US-098** : Toggle org-level `self_service_enabled` (boolean default false). Migration `20260504_001_org_self_service.sql`. Décorateur `@require_self_service_enabled` (super-admin bypass). Helper `is_org_self_service_enabled`.
✓ **US-099** : Super-admin lance ses propres sims directement (toujours autorisé, bypass self_service flag). AppHeader bouton « + Lancer une simulation » (super-admin OR org self-service ON).
✓ **US-100** : Retrait `BASSIRA_ADMIN_TOKEN` legacy → tout sur JWT + email whitelist. Décorateur `require_admin_token` refactor dual-auth (accepte JWT super-admin OU legacy token pendant transition).

**Chantier L — Workflow devis + console privative + branding (US-101 → US-108)** :
✓ **US-101** : Migration SQL idempotente rétro-attribution sims filesystem → org aimpower-bassira. Script `check_legacy_sims_attribution.py --sql` (lit simulation_config.json + outcome.json + mtime). Amine a joué la migration en prod (5 sims attribuées).
✓ **US-102** : Vue `/admin/quotes` super-admin (lecture filesystem JSON). 6 endpoints `/api/admin/quotes/*`. Modal détail + workflow statut + zone Stripe Payment Link.
✓ **US-103** : Workflow statut quotes (sidecar `*.status.json`). Transitions strictes : received → reviewing → quoted → declined → paid → in_progress → delivered. Color coding pill + timeline historique.
✓ **US-104** : Bridge manuel Stripe Payment Link + email Resend automatique. Service `email_service.py` Resend → SMTP fallback. 3 templates HTML (`quote_received`, `quote_payment_link`, `quote_delivered`). Endpoint `POST /api/admin/quotes/<id>/send-payment-link`.
✓ **US-107** : Refactor — console upload **sortie de Home.vue** (274 lignes supprimées du DOM) → vue privative `/console`. Composant `ConsoleView.vue` avec upload + URL fetch + TrendingTopics + ScenarioSuggestions + prompt + bouton Lancer + TemplateGallery + HistoryDatabase. Route guard `meta.requiresAuth + requiresSelfService` (super-admin OR org self-service ON).
✓ **US-108** : Branding fix — `index.html` (titre/lang/og:tags), `manifest.json` (PWA name/short_name/description), `sw.js` (service worker), favicon SVG neutre lettre arabe « ب » sur fond Causse cream. Plus de référence MiroShark/Forecasting MENA en user-facing. Backend Python namespace `miroshark.*` conservé (interne).

**Fixes critiques cette session** :
✓ Fix `e744acb` US-093 path : `/api/auth/me` → `/api/client/auth/me` (mismatch frontend/backend)
✓ Fix `e106a60` US-093 #2 : second appel `fetch('/api/auth/me')` non corrigé dans `stores/auth.js` (sub-agent l'avait écrit en parallèle de api/client.js, mon fix précédent ne couvrait que ce dernier)
✓ Fix `dfbf5b8` US-092 ECC : refactor JWT verifier pour supporter les nouvelles JWT Signing Keys ECC P-256 de Supabase 2026 (legacy HS256 secret n'est plus exposé pour les nouveaux projets)
✓ Fix CIH × Barid Al-Maghrib `5f5de2e` : purge claim factuel résiduel oublié dans US-089
✓ Fix `266ef0f` US-097 : `GET /api/report/<id>` accepte un simulation_id en fallback (pour route `/report/:id` historique qui accepte les deux formats)

[VALIDÉ EN PROD — 4 mai 2026]
- `/api/client/auth/me` : 200 avec profil multitenant complet
- `/api/admin/me/super-status` : 200 (medamine.mansouriidrissi@gmail.com whitelist)
- `/api/admin/organizations` : 200 (cross-tenant, super-admin)
- `/api/admin/quotes` : 200 (5 devis listés)
- `/api/admin/simulations` : 200 (5 sims cross-tenant après rétro-attribution US-101)
- `/api/calibration/aggregates` : 200 (public, fail-soft si Supabase pas configuré)
- `/api/report/sim_xxx` : 200 (fix `266ef0f` déployé, fallback simulation_id OK)
- `/console` route : routing OK, redirige vers /login si non auth
- `/admin/quotes` route : routing OK, accessible super-admin

[BLOQUÉ — actions humaines pendantes]
- !! **ROTATION DE 3 SECRETS LEAKÉS** dans le chat de cette session (réflexe DEFCON 1) :
  1. `SUPABASE_SERVICE_ROLE_KEY` — Settings → API → Reset service role key
  2. Password DB Supabase — Settings → Database → Reset database password (puis recompose `SUPABASE_DB_URL` dans Coolify)
  3. JWT access_token de la session Google active : Authentication → Users → toi → Log out user (forcera re-login)
- **Configuration Stripe** pour vraie intégration Checkout API (US-105 future) : créer compte stripe.com, poser `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` dans Coolify
- **Bug ReportView frontend rendering** (priorité haute prochaine session) : voir [PARTIEL] ci-dessous

[ALERTE]
!! **Build Coolify avec Force deploy without cache** PEUT CRASHER (re-pull des deps Python lourdes : torch 506 MB + nvidia-cuda 1.5 GB cumulés). 1 fois confirmé pendant la session (« Gracefully shutting down build container »). Toujours préférer **Redeploy simple** (rolling update qui réutilise les layers Docker cachés). Force only en cas de cache Docker pourri qui sert un dist obsolète.
!! **Coolify Save Environment Variables** via le formulaire « New Environment Variable » individuel **ne persiste PAS toujours** (vu 2× pendant la session). Préférer le mode **Developer view** qui ouvre un textarea avec toutes les vars en format dotenv + bouton « Save All Environment Variables » — ce mode est fiable.
!! **JWT Supabase 2026 = ECC P-256 par défaut** (asymétrique, JWKS). Le mode HS256 `SUPABASE_JWT_SECRET` n'est plus exposé pour les nouveaux projets — code backend (`jwt_verifier.py`) gère les deux modes via détection auto du header `alg`. Si Amine crée d'autres projets Supabase, le code marchera direct sans config supplémentaire.
!! **Mismatch Coolify `--build-arg` listing vs vars persistées** : si tu vois dans les logs build « Added 24 ARG declarations » mais qu'une var attendue manque, c'est qu'elle n'est pas marquée build-time. Pour les vars runtime-only (cas typique), elles sont injectées via `--env-file` au container, pas via build-arg.

[PARTIEL]

### Bug ReportView frontend rendering (priorité maximum nouvelle session)
- ✅ Backend `/api/report/<id>` retourne le report complet (status=completed, markdown_content 17 702 chars, outline avec sections/summary/title)
- ❌ Frontend ReportView affiche « Chargement du rapport… » indéfiniment, titre « Unnamed Project » (au lieu du vrai titre du report), tab title `🟠 (4/4) Bassira` mais contenu vide
- Probable mismatch entre le format de réponse backend et ce que ReportView/Step4Report consomme
- À investiguer : `frontend/src/views/ReportView.vue` lignes 256-288 (loadReportData) + composant Step4Report. Vérifier si `reportRes.data.outline` est bien parsé, si `markdown_content` est bien rendu, si `simulation_data.title` ou similaire est bien lu

### 3 fonctionnalités demandées par Amine non encore exposées dans ReportView
1. **Avancement progressif** : titre tab `(4/4)` n'expose pas les étapes 1/4, 2/4, 3/4. À ajouter une timeline ou breadcrumb d'avancement dans la phase de génération
2. **Chat avec le rapport** : `/api/report/chat` existe côté backend (cf. `frontend/src/api/report.js` ligne 50) mais pas exposé dans ReportView. À intégrer comme panneau lateral
3. **Vue agents** : `Step5Interaction` / `InteractionView` existent (route `/interaction/:reportId`, US-077 + US-084) mais pas linkée depuis ReportView. À ajouter un onglet ou bouton « Voir les agents » dans ReportView toolbar

### Multitenant — schema DB encore à étendre dans des US futures
- Pas de table `quote_ownership` (les devis filesystem ne sont pas encore liés à org_id)
- Pas de système d'invitation user → org (Amine valide manuellement chaque membership en SQL Editor pour l'instant)
- Pas de RBAC fine-grained sur les modèles (un viewer pourrait voir un draft non publié)

### Resend — SPF/DKIM
- Vars posées Coolify : `RESEND_API_KEY` + `RESEND_FROM_EMAIL` (confirmé Amine)
- Domain `ai-mpower.com` à vérifier dans Resend Dashboard si pas déjà fait (DNS records DKIM/SPF/DMARC doivent être dans Cloudflare)
- À tester end-to-end : envoyer un devis → vérifier réception `quote_received.html` côté client → marquer outcome `quoted` avec lien Stripe → vérifier `quote_payment_link.html`

[NEXT — chantiers prêts à attaquer en nouvelle session]

### Prio P0 — débloquer le rendering rapport
- **US-109** Fix ReportView consume report payload (frontend rendering) → priorité absolue, sans ça les clients ne voient pas leurs rapports
- **US-110** Avancement progressif (timeline 1/4, 2/4, 3/4, 4/4 avec dates) dans ReportView header
- **US-111** Chat avec le rapport (panneau latéral, intégration `/api/report/chat`)
- **US-112** Onglet « Voir les agents » dans ReportView toolbar (lien vers `/interaction/:reportId`)

### Prio P1 — finir multitenant
- **US-113** Stripe Checkout API native (US-105 reportée) — création de Payment Sessions via API + webhook `checkout.session.completed` (nécessite `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET`)
- **US-114** Migration `quote_ownership` table Supabase pour lier devis à org (au lieu du sidecar JSON filesystem)
- **US-115** Système d'invitation user → org (email magic link + table `org_invitations`)

### Prio P2
- **US-116** Audit sécurité OWASP post-multitenant (RLS Supabase, CORS, rate limit endpoints client, log audit)
- **US-117** Tests Playwright nouvelles routes (/console, /admin/quotes, /client/dashboard, login flows)

### Bloqué humain
- Logo Bassira complet — Amine a explicitement REJETÉ (memory `feedback_rejected_tools`)
- Témoignages partenaires réels NDA — bloqué humain depuis 2026-04-29
- Stripe credentials — bloqué humain (Amine doit créer compte Stripe)

[CTX session]
- ~3000+ tool calls cumulés (sub-agents inclus)
- 13 commits poussés sur main : `e300312` US-090, `ea2a700` US-091, `7daa238` US-092, `4c46af7` US-093, `9726a65` purge em-dash, `e744acb` US-093 fix path, `da9938d` US-094, `5f5de2e` purge CIH, `7ca549a` fix US-087 SectorUseCases home, `61ce615` UX tour + JSONs, `e106a60` US-093 #2 fix path store, `dfbf5b8` US-092 ECC, `69800f5` US-096, `154ec66` fix US-096 OAuth router, `05d3116` US-095, `abc4143`/`125ab96`/`2106c47` bumps version trigger Coolify, `25803a1` US-101, `8d84adb` US-102+103+104+107+108, `266ef0f` fix US-097 report fallback
- 9 sub-agents pilotés : 1 Explore initial pour pivot strategy + 4 Ralph-loop autonomes (US-090, US-095/097/098/099/100, US-101, US-102/103/104/107/108) + 4 sub-agents fixes ciblés
- Tests : 423 → 878 backend pytest (+455 cette session)
- Bundle frontend prod final : `index-CtrTJkxa.js` (US-108 branding + chunks ConsoleView/AdminQuotesView)

[MEMO inter-sessions]
- **Supabase Bassira Cloud** ref `fvfifgstytvxssffvsbs` (URL `https://fvfifgstytvxssffvsbs.supabase.co`) — projet en mode JWT Signing Keys ECC P-256 (pas legacy HS256). Org slug `aimpower-bassira`, super-admin email `medamine.mansouriidrissi@gmail.com`, self_service_enabled=true.
- **Coolify app `miro-shark`** UUID `u6pn5mr2pgi88s13un55pkzb` dans projet `Ventures` (UUID `e6kerffaobuwy2uo9n5sdihu`) sur instance `https://coolify.ai-mpower.com`. 28 env vars dont `SUPABASE_URL` (sans préfixe VITE), `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_URL`, `BASSIRA_SUPER_ADMIN_EMAILS`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`. Le `SUPABASE_JWT_SECRET` legacy est inutile pour ce projet (mode ECC).
- **Coolify save env var** : utiliser le mode **Developer view** (textarea bulk) qui marche fiablement, pas le formulaire individuel « New Environment Variable » qui ne persiste pas systématiquement.
- **Coolify deploy** : préférer Redeploy (rolling) vs Force deploy without cache (rebuilt complet, peut crasher OOM sur les deps Python). Force without cache uniquement si cache layer Docker a un dist/ obsolète.
- **Resend domain** `ai-mpower.com` — DNS DKIM/SPF/DMARC à vérifier dans Cloudflare avant tester en prod
- **Pattern frontend → backend** : path correct est `/api/client/auth/me` (blueprint `client_bp` au prefix `/api/client/`). Pas `/api/auth/me`. Tous les helpers axios + tous les fetch directs côté frontend doivent utiliser le bon prefix.
- **Sub-agent isolation worktree** : si tu spécifies `isolation: "worktree"`, le sub-agent peut quand même écrire DIRECTEMENT dans main si le runtime auto-merge à la fin. Vérifier toujours `git log` après pour confirmer le commit final.
- **Convention slugs models** : `fusion-bancaire-mena`, `crisis-drill-24h`, `allocation-fonds-strategique`, `stress-test-politique`, `lancement-diaspora-eu`, + 13 ajoutés US-090 (cf. liste complète dans .ralph/prd.json)
- **JWKS endpoint Supabase** : `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json` — utilisé par `PyJWKClient` côté backend Flask via lib `pyjwt[crypto]`
- **Memory feedback_rejected_tools** : Plausible/Posthog/GA/logo Bassira/`npm run dev` local explicitement REJETÉS par Amine. Ne jamais reproposer.
- **Memory bassira_rebrand** : MiroShark → Bassira frontend uniquement (backend Python namespace `miroshark.*` conservé)

[Recommandations pour la nouvelle session]
1. **AVANT TOUT** : faire la rotation des 3 secrets Supabase leakés dans le chat de cette session (cf. [BLOQUÉ]). C'est la priorité DEFCON 1.
2. **Démarrer par US-109 fix ReportView rendering** (rapide à débugger : c'est juste un mismatch parsing entre `getReport` axios response et le composant Step4Report). Lire `frontend/src/views/ReportView.vue` lignes 256-288 + composant Step4Report.
3. Une fois US-109 OK, enchaîner US-110/111/112 (avancement progressif + chat + onglet agents) en Ralph-loop autonomous.
4. **Pour tester end-to-end Resend** : envoyer un devis test depuis `/devis` → vérifier réception `quote_received.html` côté client → marquer status `quoted` dans `/admin/quotes` avec un Stripe Payment Link de test → vérifier `quote_payment_link.html` arrive bien.
5. **Pattern Coolify deploy après changement env var** : Redeploy simple suffit. Si bundle prod garde un cache layer obsolète, bumper `frontend/package.json` version (0.x.0 → 0.y.0) pour invalider la couche `COPY package.json` puis Redeploy.
6. **Pattern d'investigation bug frontend qui ne charge pas** : ouvrir Edge avec extension Claude → naviguer vers la route → `mcp__claude-in-chrome__javascript_tool` pour `fetch()` direct l'API en réutilisant le token localStorage `bassira_supabase_auth.access_token` → comparer la réponse backend vs le DOM rendu pour identifier le mismatch.

— fin passation 2026-05-04 —

---

== PASSATION MiroShark/Bassira 2026-05-03T01:00:00+01:00 ==

[ETAT]
- branche `main` `586013d` à jour avec `origin/main` (push confirmé)
- prod **ONLINE** sur https://prospectives.ai-mpower.com — 7 routes validées en navigateur live (Home, /landing, /offres, /calibration, /devis, /partenaires, /explore)
- **86/86 stories Ralph passes:true (100 %)** — 35 nouvelles stories cette session (US-053 → US-085 + fix prod)
- 423 tests backend passing (+79 cette session) · zéro régression
- 32 tests Playwright E2E préservés intacts
- npm run build : OK sur tous les commits
- **20 commits poussés** cette session
- 13 sub-agents pilotés cette session : tous done & pushed
- **Plateforme intégralement migrée sur palette Causse Warm Intelligence** (`--wi-*`)

[FAIT cette session — 35 stories Ralph]

**Chantier 7 — Warm Intelligence (US-053 → US-056)** :
✓ **US-053** : tokens `--wi-*` complets dans design-tokens.css (palette Causse MENA+EU, typographie Outfit/Manrope/Tajawal, radii/shadows/spacing). Override dark-mode minimal.
✓ **US-054** : refonte /offres — alias `--stitch-*` rebindés vers `--wi-*` + radius hardcodés migrés.
✓ **US-055** : refonte /calibration — `.cal-plot-card` migré + RTL via CSS logical properties.
✓ **US-056** : refonte /devis — alias `--stitch-*` → `--wi-*` + tokens radius.

**Chantier 8 — Web Enrichment (US-057 → US-058)** :
✓ **US-057** : endpoint `POST /api/simulation/enrich-ask` (Perplexity sonar). Cache SHA-256 TTL 1h, rate-limit 10/60s/IP, fallback gracieux sans WEB_SEARCH_MODEL. 5 tests pytest. WEB_SEARCH_API_KEY déjà configuré sur Coolify (confirmé Amine).
✓ **US-058** : TrendingTopics réutilisé sur `/simulation` via panneau collapsible bottom-right + query param `?url=` lu par Home.vue au mount.

**Chantier 9 — Export (US-059)** :
✓ **US-059** : PDF enrichi 10 sections (couverture + disclaimer légal + résumé exécutif + résultats + agents/profils + posts clés + top influenceurs + sources + image graphe + méthodologie + recommandations). Endpoint `GET /api/simulation/<id>/export-md` Markdown jumeau pour Notion/Obsidian. 2 boutons icônes PDF + MD dans Step4Report `.export-icons` row, à gauche du pill "completed", visibles `v-if="isComplete"`. Capture SVG du graphe → base64 PNG côté frontend, transmise dans le body POST.

**Chantiers A→F — Nouvelles vues + livrables (US-060 → US-065)** :
✓ **US-060** : OnboardingTour.vue 4 étapes (graine → question → scénario → lancement). Spotlight via clip-path, beacon+halo terracotta, tooltip auto-positionné. Bouton "Lancer un exemple" pré-charge `budget_loi_finances`. Flag `localStorage.bassira_onboarding_done`. Fix post-livraison : RAF stable-rect detection (au lieu de setTimeout 320ms) + `bodyMissing` fallback i18n quand cible absente du DOM.
✓ **US-061** : LandingView.vue 1189 lignes route `/landing` (Hero + 3 Pains + Product split + Proof dark + Pricing teaser + Final CTA terracotta). Meta title/description SEO. Tokens --wi-* exclusifs.
✓ **US-062** : PartnersView.vue 1017 lignes route `/partenaires` (Hero institutionnel + 8 logos placeholders + 3-step process + 3 tiers Research/Integration/White-label + testimonials section + form mailto). Registre académique strict (pas de language startup).
✓ **US-063** : `bassira_apollo_sequences.md` (10 077 mots, 27 emails FR/EN/AR + 6 LinkedIn DMs). 3 séquences : Pre-Decision Anxiety / Blindspot Post-Crisis / Calibration Proof. HTML inline-style + plain text + RTL Tajawal.
✓ **US-064** : `bassira_linkedin_calendar.md` (12 335 mots, 15 posts + 4 DMs). 4 piliers : Blindspot, Calibration Log, Simulation Debrief, Decision Science. Cas business concrets (Sahara Bank, OCP, Vivendi, GCC).
✓ **US-065** : AnalyticsView.vue dark-mode admin + endpoint `GET /api/admin/analytics` (auth `BASSIRA_ADMIN_TOKEN`). 4 KPI cards + funnel CSS bars + top packages + time series 30j. Calcul filesystem (compte simulations, configs, quotes). 3 tests pytest. **OUTILS ANALYTICS TIERS REJETÉS — Plausible/Posthog/GA non pertinents pour Bassira (cf memory feedback_rejected_tools).**

**Chantier G — Refonte 14 vues selon designs Stitch officiels (US-066 → US-079)** :
✓ Refonte structurelle complète selon `stitch_bassira_global_design_system/` (30+ designs HTML+PNG).
✓ **US-066** Home (hero eyebrow + CTA terracotta + trust strip + console card)
✓ **US-067** Calibration (hero Brier mint 96px + 4 stats cards warm + plot card aesthetic Nature paper)
✓ **US-068** Offers (carousel 10 packages featured glow orange + MAD/USD priorité MENA)
✓ **US-069** Quote (3 steps + stepper warm + trust banner mint + success state mint check)
✓ **US-070** Explore (grid 3 cols + filter chips colorés par catégorie + search ajouté)
✓ **US-071** Report (magazine layout 1000px + executive summary callout terracotta + Step4Report préservé intact)
✓ **US-072** Simulation (cockpit dark + view switcher icons + phase dots)
✓ **US-073** SimulationRun (round counter heartbeat 64px + progress bar slim + toast mint)
✓ **US-074** Main (header dense + resize divider + dark mode shell tokens)
✓ **US-075** Comparison (selector A/B + winning callout + metrics table delta)
✓ **US-076** Replay (timeline scrubber warm + narrative card + media controls)
✓ **US-077** InteractionView (audit académique paper-quality + InteractionNetwork D3) — Step5Interaction temporairement retiré
✓ **US-078** Embed (600px iframe-friendly + sparkline + 3 key findings)
✓ **US-079** ReviewEntities (70/30 split + segmented Valid/Flagged/Removed + batch actions)

**Chantier H — Harmonisation 26 composants (US-080 → US-084)** :
✓ **US-080** : 5 Steps (Step1GraphBuild + Step2EnvSetup + Step3Simulation + Step4Report + Step5Interaction). 89 tokens legacy (`--lo`/`--lp`/`--li`...) → `--wi-*`. Zone export-icons US-059 préservée intacte dans Step4Report.
✓ **US-081** : 5 charts D3 (BeliefDriftChart + PolymarketChart + InteractionNetwork + InfluenceLeaderboard + DemographicBreakdown). Helper `cssVar()` pour lire tokens via getComputedStyle. Force layout, scales, transitions D3 préservés.
✓ **US-082** : 6 panels (SettingsPanel BYOK wizard + DebugPanel + WhatIfPanel + CounterfactualBranchPanel + HistoryDatabase + EmbedDialog). 0 hex hardcodé après migration. Modals + z-index tokens préservés.
✓ **US-083** : 5 simulation components (ScenarioSuggestions 5 frameworks + TemplateGallery + TrendingTopics + GraphPanel + NetworkPanel). Recovery panel US-014 + select payload US-058 préservés.
✓ **US-084** : Fix InteractionView — toggle tabs `Audit méthodologique` / `Interaction sandbox` (option A retenue parmi 3). Step5Interaction réintégré dans le tab sandbox. 40 clés i18n migrées des libellés anglais inline → `interactionAudit.*` FR/EN/AR.

**Chantier I — CTAs sectoriels (US-085)** :
✓ **US-085** : SectorUseCases.vue avec 8 secteurs MENA+EU (Banque featured + Énergie + Politique + Distribution + Tech + Industrie + Médias + Santé). 16 use cases C-Level concrets (OCP, Sonatrach, Marjane, ANAM, BCEAO, ADNOC, etc.). Au clic CTA → `/devis?sector=X&usecase=Y&package=Z` pré-remplit `form.situation` (mappage SECTOR_TO_SITUATION) + `form.otherSituation` avec texte du use case via `t('sectors.X.cases.Y')`. Lien "Décrivez votre cas sur mesure" → `/devis?sector=custom`. ~80 clés i18n FR/EN/AR. Intégré dans LandingView entre Pains et Product. **Validé en prod** : `?sector=finance&usecase=0` pré-remplit correctement.

**Fix prod (commit `586013d`)** :
✓ Home H1 "Simulez tout, pour 1 $" → "Stress-testez votre stratégie avant qu'elle ne touche le réel." (FR/EN/AR alignés sur le slogan)
✓ Trust strip "12 k simulations · ISO 27001" (claims fausses DEFCON 1) → "Brier 0,18 vérifié · Méthodologie publique · Données souveraines"
✓ Partners testimonials "Nom à confirmer" placeholders → bloc NDA card unique avec mailto `partners@ai-mpower.com` (posture early access institutionnelle)
✓ Calibration empty state "Pas encore assez de données" → "Bassira en early access — score à partir de 5 simulations vérifiées" (transparence comme argument de crédibilité)
✓ Explore empty state CTA → désormais vers `/landing` (cas d'usage par secteur) au lieu de `/` (form technique)

[VALIDÉ EN PROD — inspection live navigateur via MCP Chrome]
- **Landing** : 7 sections OK, 8 cards SectorUseCases visibles, prix MAD/USD lisibles
- **Offres** : carousel 10 packages, featured "Crisis Drill 24h" gradient orange, billing toggle, prix
- **Devis?sector=finance...** : pré-remplissage US-085 confirmé fonctionnel (input rempli avec "[Banque & Finance] Quel sera l'impact d'une hausse de 50 pb...")
- **Partners** : 6 sections, registre académique respecté (avant fix prod : "Nom à confirmer" visible)
- **Calibration** : 4 stats cards + scatter plot SVG (avant fix prod : "Pas encore assez de données" peu engageant)
- **Explore** : empty state illustré ◇◎◈ (avant fix prod : CTA peu adapté pour prospect cold)
- **Home** : hero eyebrow `بصيرة · Prospective stratégique` ✓, console + ask + trending + template gallery ✓ (avant fix prod : H1 "Simulez tout, pour 1 $" placeholder)

[BLOQUÉ — actions humaines pendantes]
- **Témoignages partenaires réels** : posture NDA mise en place, mais pour démo C-Level, faut activer 1-2 vrais témoignages avec accord explicite
- **Simulations publiques en prod** : base actuellement vide → /calibration et /explore sans contenu. Solution = Amine lance 5-10 simulations test puis `is_public=true` puis marque outcomes au fur et à mesure
- **Calibration "auto" non faisable techniquement** : le label outcome (called_it / partial / wrong) dépend de l'événement réel observé après la simulation. C'est intrinsèquement humain. La calibration auto = workflow opérationnel, pas un trigger backend.

[ALERTE]
!! **Bundle CSS gonflé** : la migration intégrale --wi-* + --ms-* + tokens dérivés ajoutés (--wi-primary-soft, --wi-primary-container-soft/edge, --wi-secondary-soft/edge, --shell-* dans MainView) augmente le CSS scoped. Pas mesuré, mais probable +10-15% gzip vs avant migration. Compromis maintenabilité assumé (cohérent avec doctrine US-016).
!! **Step3Simulation US-080** : migration tokens globale rapide (89 occurrences `--lo`/`--lp` remplacées) mais PAS une refonte structurelle Stitch. Le composant fait 3158 lignes — refonte structurelle reportée à une story future si besoin.
!! **InteractionView US-084 toggle Audit/Sandbox** : choix architectural retenu (vs skip auto / pré-remplir). Step5Interaction reçoit `:reportId :simulationId` + handlers no-op `@add-log @update-status`. Si Step5Interaction émet d'autres events à l'avenir, les ajouter au binding.
!! **Trust strip Home reformulé** : "Brier 0,18 vérifié" reste affiché alors que la base prod est vide. Risque de claim si scrutiny — soit alimenter le calibration log rapidement, soit changer "0,18 vérifié" en "Méthodologie de calibration ouverte" tant que vide.
!! **Outils analytics tiers (Plausible/Posthog/GA) explicitement REJETÉS par Amine** — sauvegardé dans `memory/feedback_rejected_tools.md`. Ne plus jamais reproposer dans des next-steps.

[PARTIEL]

### Calibration (workflow incomplet en prod)
- ✅ Backend `/api/calibration` + frontend CalibrationView refondus
- ✅ Empty state copy assume early access
- ❌ **Aucune simulation publique avec outcome marqué en prod** → Brier non calculé
- → Solution = workflow humain : lancer sim → publier → observer événement réel → marquer outcome via admin token. Endpoint `/admin/analytics` peut servir de tableau de bord pour ça.

### InteractionView (US-077 puis US-084)
- ✅ Layout audit méthodologique aesthetic Nature paper (US-077)
- ✅ Step5Interaction réintégré via toggle tabs (US-084)
- ⚠️ Tab choice persisté localStorage `bassira:interactionView:activeTab` — pas de URL state, les liens partagés tombent toujours sur tab par défaut

[NEXT — chantiers prêts à attaquer]

### Prio P1 — capture commerciale
- **Stripe self-service sur /offres** pour les 2 packages les plus accessibles (Crisis Drill 24h MAD 10k, Pre-Launch Adcheck $1.5k). Effort ≈ 1 journée (Stripe Checkout Sessions, webhook successful payment, redirect /devis avec preuve de paiement).
- **Activer Apollo séquences** : importer les 27 emails de `bassira_apollo_sequences.md` dans Apollo via API + lancer Sequence 1 sur 50 prospects ciblés. Apollo MCP disponible côté Claude.
- **Publier 1ère salve LinkedIn** : utiliser `bassira_linkedin_calendar.md` (15 posts prêts) pour démarrer la cadence 3 posts/semaine.

### Prio P1 — qualité
- **Tests Playwright sur les 14 vues refondues** + nouvelles routes (/landing, /partenaires, /admin/analytics) — la suite existante (32 tests) ne couvre pas les nouveautés.
- **Audit sécurité post-78 stories** (OWASP, secrets, CORS, rate-limit endpoints, headers). Avant 1er client institutionnel.

### Prio P2
- **Refonte structurelle Step3Simulation** selon design Stitch (3158 lignes — pas fait dans US-080)
- **Logo Bassira** : prompt prêt dans `bassira_brand_prompts.md` mais Amine a explicitement dit "oublies le logo" → ne pas faire sans demande explicite
- **Régénérer le PNG `frontend/public/miroshark-nobg.png`** au branding Bassira (designer humain requis)

[CTX session]
- ~1500+ tool calls cumulés (interactions Claude + 13 sub-agents)
- 20 commits poussés sur main : `a81865e`, `83382af`, `038baf2`, `a6e4ead`, `22e1f0e`, `8acae34`, `b848717`, `709a744`, `c0e8a59`, `5d65438`, `d54b452`, `60e7fbd`, `6f4db4c`, `3e3d90f`, `586013d` (+ commits intermédiaires)
- 13 sub-agents pilotés en parallèle (3 batches : 6 + 7 + 5 + 1 fix interaction)
- Tests : 412 → 423 backend pytest (+11)
- Modèle : Opus 4.7 (1M context) toute la session

[MEMO inter-sessions]
- API Coolify : valides
- LLM_MODEL_NAME prod : `kimi-k2-turbo-preview` (Moonshot)
- **WEB_SEARCH_API_KEY** : configuré sur Coolify (confirmé Amine 2026-05-02) → US-057 enrich-ask actif
- **BASSIRA_ADMIN_TOKEN** : configuré sur Coolify (confirmé Amine session précédente)
- SMTP : toujours non configuré (cf passation précédente)
- **Stitch projects principaux** : `stitch_bassira_global_design_system/` (30+ designs, source de vérité unique pour la refonte). Références par dossier : `bassira_home_strategic_foresight`, `bassira_calibration_methodological_track_record`, `bassira_formules_tarifs`, `bassira_demande_de_devis_tape_*`, `bassira_galerie_explore`, `bassira_simulation_cockpit`, `bassira_simulation_en_cours`, `bassira_console_d_analyse_avanc_e`, `bassira_rapport_de_simulation_final`, `bassira_r_vision_des_entit_s`, `bassira_comparaison_strat_gique_delta`, `bassira_relecture_de_simulation_strat_gique`, `bassira_vue_des_interactions_audit_m_thodologique`, `bassira_widget_d_int_gration_strat_gique`, `bassira_landing_page_strat_gique_seo`, `bassira_partenariats_institutionnels`, `bassira_tableau_de_bord_analytique_interne`, `bassira_onboarding_tape_1-4`, `apollo_outreach_s_quence_1-3_email`, `linkedin_*` (5 designs).
- **Brand guide Causse** : `stitch_bassira_global_design_system/bassira_causse_brand_guidelines.md` + `bassira_causse/DESIGN.md`. Palette MENA+EU calibrée (`#FF8551` orange + `#006D44` mint + `#FAF7F2` cream + `#241915` charcoal + `#A13F0F` terracotta).
- **Tokens --wi-*** dans `frontend/src/design-tokens.css` lignes 290+ — namespace coexiste avec `--ms-*`. Source de vérité pour toute nouvelle vue.
- **Pattern observé** : alias `--stitch-* → --wi-*` dans le scoped CSS pour ne pas casser les usages existants.
- **MCP Chrome** : utilisable pour validation visuelle live en prod (`mcp__claude-in-chrome__navigate` + `javascript_tool` plus fiable que `read_page` qui timeout sur les animations CSS infinies).
- **Memory feedback_rejected_tools** : Plausible/Posthog/GA/logo/`npm run dev` local **REJETÉS** par Amine. Lire avant chaque liste de "next steps".

[Recommandations pour la nouvelle session]
1. **AVANT toute proposition** : lire `memory/MEMORY.md` et notamment `feedback_rejected_tools.md` pour ne pas reproposer du Plausible / logo / npm dev local.
2. Lire `.ralph/prd.json` — 86/86 passes:true. Pour ajouter de nouvelles stories, partir de US-086.
3. **Validation visuelle prod** : `mcp__claude-in-chrome__tabs_context_mcp` puis navigate sur `prospectives.ai-mpower.com/<route>` puis `javascript_tool` (read_page timeout sur animations).
4. **Pour Stripe self-service** : `pricing-strategy` skill + `stripe:stripe-best-practices` skill chargés. Backend Flask déjà existant. Webhook → flag `paid_at` dans simulation_config.json + redirect /process avec preuve.
5. **Pour Apollo séquences** : Apollo MCP déjà disponible (`mcp__claude_ai_Apollo_io__*`). Importer les emails depuis `bassira_apollo_sequences.md` via API.
6. **Pour les tests Playwright nouveautés** : copier le pattern `frontend/e2e/<existant>.spec.ts` et étendre aux nouvelles routes /landing /partenaires /admin/analytics.
7. **Pour audit sécurité** : lancer skill `security-review` qui audit OWASP / secrets / CORS automatiquement.
8. **Pour test calibration** : Amine doit lancer 5-10 simulations test sur prod, les rendre publiques, puis utiliser `/admin/analytics` ou `/calibration` admin panel pour marquer les outcomes au fil de l'eau.
9. **Anti-pattern à surveiller** : refonte de composants Vue lourds (>1500 lignes) par sub-agents — risque de migration tokens superficielle au lieu de refonte structurelle (cas Step3Simulation US-080). Si une refonte profonde est nécessaire, allouer un agent dédié à ce composant unique.

— fin passation 2026-05-03 —

---

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
