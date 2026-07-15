== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-15 ~19h00 (Brique E2E email : Task 1-5 TOUTES closes, magic link réel validé bout-en-bout en prod — 3 bugs de prod distincts trouvés et corrigés) ==
Synthèse complète et autonome — ne suppose la lecture d'aucune passation antérieure,
remplace et purge intégralement l'entrée du 2026-07-15 ~02h30 (tous ses points FAIT/Task 1-3
restent acquis et ne sont pas remis en cause ci-dessous, juste non répétés en détail).

[ETAT]
- **`main`** HEAD = `eb332c3`, poussé sur `origin/main`. Commits produit cette session (en
  plus des 5 déjà connus 0e11da7→988e472) : `6e32bd5` (bascule bassira.ma : redirect_to
  magic link + 6 occurrences codées en dur de prospectives.ai-mpower.com + CORS_ORIGINS
  Coolify), `3210ffc` (debug temporaire, retiré), `eb332c3` (**vrai correctif** : race
  condition guard router / auth.init()).
- Suite pytest backend : **2258 passed, 0 failed, 42 skipped** (revérifiée après les
  changements backend de cette session — le flaky `test_md_hash_stable_with_
  deterministic_enricher` est passé cette fois, timing-dépendant comme documenté, toujours
  pas corrigé au fond, cf. [NEXT]).
- Build front (`npm run build`) vert (exit 0), revérifié 2× (avant et après le vrai fix).
- **Suite E2E Playwright complète (114 tests) : 86 passed, 28 failed** — **AUCUN de ces 28
  échecs n'est une régression de cette session** (triage détaillé ci-dessous, [ALERTE]).
  `client-dashboard.spec.ts` (Lot B, 9 tests) et `auth-flow(s).spec.ts` intégralement verts.
- `.gitignore` : `test-results/`, `.playwright-mcp/`, `.understand-anything/` ajoutés
  (untracked oubliés, point [NEXT] de la passation précédente — traité).

[FAIT — cette session, après la reprise du 2026-07-15 ~02h30]
1. **Décision Amine actée** : correction immédiate de `API_EXTERNAL_URL` (infra Supabase
   miroshark) + rotation de `NAHJ_SUPABASE_POSTGRES_DB` **différée** (faux positif jugé peu
   sensible, non prioritaire).
2. **Bug de prod #1 corrigé** : `API_EXTERNAL_URL` sur le service Coolify Supabase dédié
   miroshark (`dgybi9q5e2ggkjtaxlu2ukai`) — `http://supabase-kong:8000` (hostname Docker
   interne) → `https://db-miroshark.ai-mpower.com`. Redémarrage du service appliqué et
   vérifié (`running:healthy`).
3. **Test relancé → toujours en échec** (regex d'extraction câblée sur `*.supabase.co`,
   cassée pour un domaine self-hébergé custom) → corrigée dans `gmail-reader.ts`
   (`MAGIC_LINK_RE` généralisée sur `/auth/v1/verify`, peu importe le domaine) + 3e cas de
   test ajouté (`gmail-reader.test.mjs`, 3/3 verts).
4. **Directive Amine reçue en cours de route** : « plus jamais `prospectives.ai-mpower.com`
   ni `db-miroshark.ai-mpower.com` nulle part dans l'app, tout doit utiliser bassira.ma ».
5. **Bug de prod #2 découvert et corrigé** : `GOTRUE_SITE_URL` (même service Coolify) valait
   `${SERVICE_URL_SUPABASEKONG}` (template Coolify, résolu en `http://db-miroshark.ai-mpower.
   com` — le domaine technique Supabase lui-même). Or `_send_magic_link()` n'envoyait aucun
   `redirect_to` explicite → GoTrue retombait sur `SITE_URL` par défaut → tout magic link
   redirigeait vers le domaine Supabase brut, jamais vers l'app. Vérifié (lecture seule,
   sans rien modifier avant confirmation) que `bassira.ma` sert EXACTEMENT le même build que
   `prospectives.ai-mpower.com` (bundle JS identique `index-ePmacGrZ.js`) → cohérent ADR-013.
   Corrigé → `https://bassira.ma`.
6. **Audit complet des occurrences codées en dur** de `prospectives.ai-mpower.com` dans le
   code applicatif (hors docs/historique) : 6 sites trouvés et corrigés en une passe (accord
   Amine) — `client_account_service.py::_send_magic_link` (ajout `redirect_to` explicite via
   nouvelle var `BASSIRA_PUBLIC_URL`, défaut `bassira.ma`), `api/invitations.py` (invite_url),
   `api/models.py` ×3 (cta_link PDF modèles, 3 locales), `services/report_delivery.py` ×2
   (défaut `BASSIRA_PUBLIC_URL` incohérent avec `stripe_service.py`), `app/__init__.py`
   (défaut `CORS_ORIGINS`). Tests unitaires alignés (`test_unit_invitations.py`,
   `test_unit_hardening.py`). `playwright.config.ts` + `frontend/tests/e2e/README.md` +
   `supabase/seed.sql` également alignés. Variable Coolify `CORS_ORIGINS` (app applicative
   `u6pn5mr2pgi88s13un55pkzb`) corrigée → `https://bassira.ma,http://localhost:3000`.
   Suite pytest complète (2258 passed) + build revérifiés avant commit/push/deploy.
7. **Test relancé après déploiement du code → nouvel échec, différent** : la navigation
   atteint bien `/client/dashboard` (progrès), mais le contenu affiché est le formulaire de
   login, pas le dashboard.
8. **Bug de prod #3 trouvé, le plus profond : race condition auth** — instrumentation
   console.log temporaire (commit `3210ffc`, déployé, retiré ensuite) a prouvé que la
   session Supabase est BIEN établie (localStorage peuplé, `/auth/v1/user` → 200) mais que
   le guard `router.beforeEach` redirige quand même vers `/login` **avant** que
   `auth.init()` n'ait fini de traiter l'event `SIGNED_IN`. Cause racine : Vue Router résout
   sa navigation initiale dès `app.use(router)`, **indépendamment** du `await auth.init()`
   fait dans `main.js` avant `app.mount()` — l'hypothèse du commentaire du code d'origine
   (US-096) était fausse. Quand Supabase JS traite le hash `#access_token=...` puis le
   retire via `history.replaceState`, une SECONDE navigation se déclenche pendant que
   `auth.init()` attend encore — l'ancienne heuristique de bypass (hash contient
   `access_token=`) ne protège plus cette seconde navigation, où le hash est déjà vide.
   **Corrigé** (commit `eb332c3`) : `auth.init()` rendu idempotent (promesse mémoïsée
   module-scope) ; le guard l'attend explicitement au lieu de se fier au hash. Build + push
   + déploiement + reconfirmation conteneur recréé.
9. **Task 4 relancée après ce vrai correctif → PASSE** (22.4s, 1 passed). Round-trip complet
   validé bout-en-bout en prod réelle : devis créé → avancé à payé via l'admin → email réel
   reçu (Gmail DWD) → magic link extrait → navigation → session établie → dashboard affiché.
10. **Task 5 (gates finaux)** : bug de syntaxe préexistant corrigé en passant (bloquait TOUTE
    la suite E2E) — `admin-report-tracking.spec.ts` avait un commentaire JSDoc contenant
    littéralement `*/` (dans `reports/*/deliveries`), fermant le bloc de commentaire
    prématurément. Suite complète relancée : 86/114 verts, 28 échecs tous triés et confirmés
    **pré-existants, sans rapport avec cette session** (cf. [ALERTE]).

[ALERTE]
- **⚠️ POINT SÉRIEUX NON RÉSOLU, à faire trancher par Amine** : `tunnel-commercial.spec.ts`
  (censé être strictement read-only, s'arrêter avant toute soumission — cf. en-tête
  `playwright.config.ts`) a fini par naviguer vers une **vraie session Stripe Checkout LIVE**
  (`https://checkout.stripe.com/c/pay/cs_live_...`) en cliquant le CTA « Crisis Drill 24h »
  depuis `/offres`. Découvert en fin de suite complète, PAS creusé plus loin ni interagi avec
  cette page Stripe (hors mandat, touche un système de paiement réel). Confirmé sans lien
  avec cette session : aucun fichier touché ici ne concerne `/offres`, `QuoteView.vue`, ou
  `stripe_service.py`. À investiguer séparément — est-ce un comportement voulu (Stripe
  Payment Link direct pour ce package précis) ou une régression antérieure non détectée ?
- **27 autres échecs E2E confirmés pré-existants, dette de test non traitée cette session** :
  (a) ~24 tests admin (`admin-branding`, `admin-quotes`, `admin-report-review`,
  `admin-report-tracking`, `console-multitenant` volets super-admin) échouent parce que
  `fixtures/auth.ts::navigateAuthenticated` attend un lien admin (`a[href="/admin/quotes"]`)
  en état VISIBLE, alors que ce lien vit désormais derrière un dropdown « Admin » à ouvrir
  (menu réorganisé à un moment non identifié, jamais répercuté dans le fixture). (b) 3 tests
  smoke (`smoke-fr/en/ar` sur `/devis`) attendent 3 boutons radio pour le Step 1 du tunnel
  devis, alors que Step 1 a été redesigné en question texte libre (« Quelle décision devez-
  vous prendre ? ») — confirmé par capture d'écran, le rendu est correct, seul le test est
  périmé. Aucun de ces fichiers (`fixtures/auth.ts`, composant header, `QuoteView.vue`) n'a
  été touché cette session. Backlog de nettoyage de tests à ouvrir séparément (pas fait ici,
  hors scope strict de la brique E2E email).
- Points hérités de la passation précédente, toujours non résolus (statu quo, non repris
  cette session) : rotation `NAHJ_SUPABASE_POSTGRES_DB` (décision Amine : différée), 2
  emails de test résiduels dans `a.mansouri@` (mise à la corbeille jamais retentée).

[BLOQUE / EN ATTENTE]
- RAS — Task 4 et Task 5 sont closes. Le seul point réellement en attente d'arbitrage Amine
  est le finding Stripe live checkout ci-dessus (ALERTE).

[NEXT]
1. **Décision Amine sur le finding Stripe live checkout** (tunnel-commercial.spec.ts) —
   investiguer si le CTA « Crisis Drill 24h » sur `/offres` route intentionnellement vers un
   Payment Link Stripe direct, ou si c'est une régression à corriger.
2. Nettoyage de la dette de tests E2E pré-existante (27 tests) — chantier séparé, pas
   urgent : mettre à jour `fixtures/auth.ts` pour ouvrir le dropdown Admin avant de chercher
   les liens, et réécrire les assertions Step 1 du tunnel devis (radios → texte libre).
3. Corriger le test flaky `test_md_hash_stable_with_deterministic_enricher` (freeze du
   temps) — connu depuis le 2026-07-11, jamais traité, quelques minutes.
4. Reprendre l'ordre de priorité déjà validé avec Amine (difficulté croissante) — `US-208`
   (Redis+RQ worker PDF actifs en prod, dépendance `US-207` déjà `passes=true`), puis
   `US-IQ-07` (pré-seed simulation depuis le brief), puis Lot C (Cal.com embarqué), Lot D
   (white-label Cal.com), `US-IQ-05`/`US-IQ-06`. 4 stories `passes=false` confirmées dans
   `.ralph/prd.json` sur 149 au total.
5. Nettoyer les 2 emails de test résiduels dans la boîte `a.mansouri@` (GAM trash, syntaxe à
   revoir).

[CTX]
- App Coolify miroshark : uuid `u6pn5mr2pgi88s13un55pkzb`. Prod = `bassira.ma` ==
  `prospectives.ai-mpower.com` (même build, bundle JS identique vérifié) — bassira.ma est
  désormais le domaine canonique partout dans le code applicatif et les tests.
  `prospectives.ai-mpower.com` reste fonctionnel (alias Coolify) mais n'est plus référencé
  nulle part dans le code.
- **Instance Supabase dédiée miroshark** : conteneurs `supabase-kong-
  dgybi9q5e2ggkjtaxlu2ukai` / `supabase-db-dgybi9q5e2ggkjtaxlu2ukai`, domaine public
  `db-miroshark.ai-mpower.com`. Ce domaine reste le domaine TECHNIQUE de l'API Supabase Auth
  (utilisé en interne pour `SUPABASE_URL`, `VITE_SUPABASE_URL`, `API_EXTERNAL_URL`) — non
  migré vers un sous-domaine bassira.ma (décision explicite d'Amine : provisionner un
  sous-domaine dédié type `db.bassira.ma`, chantier SOP-005 séparé, PAS commencé cette
  session malgré la décision prise — à ouvrir explicitement si toujours voulu).
  `API_EXTERNAL_URL=https://db-miroshark.ai-mpower.com`, `GOTRUE_SITE_URL=https://bassira.ma`.
- Nouvelle convention backend : `BASSIRA_PUBLIC_URL` (env var, défaut `https://bassira.ma`)
  — utilisée par `client_account_service.py`, `api/invitations.py`,
  `services/report_delivery.py`, `services/stripe_service.py`. Pas encore posée
  explicitement dans les env Coolify de l'app (les 4 sites tournent sur leur défaut Python
  actuellement, tous alignés sur bassira.ma — poser la variable serait redondant tant que le
  défaut reste correct, mais fragile si un jour quelqu'un modifie un seul défaut sans les
  autres : envisager de la poser explicitement en env Coolify pour une source de vérité
  unique).
- Spec E2E email : `docs/superpowers/specs/2026-07-15-e2e-email-roundtrip-design.md`.
- Plan E2E email : `docs/superpowers/plans/2026-07-15-e2e-email-roundtrip-plan.md` — les 5
  tâches sont closes, le plan peut être archivé/marqué terminé.
- Fichiers modifiés cette session (au-delà de ceux déjà listés le 2026-07-15 ~02h30) :
  `backend/app/__init__.py`, `backend/app/api/invitations.py`, `backend/app/api/models.py`,
  `backend/app/services/client_account_service.py`,
  `backend/app/services/report_delivery.py`, `backend/tests/test_unit_hardening.py`,
  `backend/tests/test_unit_invitations.py`, `frontend/playwright.config.ts`,
  `frontend/tests/e2e/README.md`, `frontend/tests/e2e/fixtures/gmail-reader.{ts,test.mjs}`,
  `frontend/tests/e2e/client-account-email-roundtrip.spec.ts`,
  `frontend/tests/e2e/admin-report-tracking.spec.ts` (bug syntaxe), `supabase/seed.sql`,
  `frontend/src/stores/auth.js`, `frontend/src/router/index.js`, `.gitignore`.
- Mode de travail : exécution INLINE sur `main` (consentement Amine hérité, reconfirmé
  explicitement à plusieurs reprises cette session via AskUserQuestion).

[MEMO inter-sessions]
- **Vue Router résout sa navigation initiale dès `app.use(router)`, PAS gaté par
  `app.mount()`** — tout code qui suppose qu'un `await xxx.init()` avant `app.mount()`
  protège les guards `beforeEach` d'un état pas encore prêt est FAUX dans cette architecture.
  Le seul pattern fiable : mémoïser la promesse d'init et la faire attendre explicitement
  PAR le guard lui-même (cf. `stores/auth.js::init()` + `router/index.js::beforeEach`,
  2026-07-15). À vérifier sur tout futur guard qui dépend d'un état async chargé au boot.
- **Piège Coolify template Supabase** : les valeurs d'env var peuvent être des références
  template (`${SERVICE_URL_SUPABASEKONG}`) plutôt que des littéraux — `GOTRUE_SITE_URL`
  était configuré ainsi, résolu dynamiquement vers le domaine Kong lui-même. Toujours
  vérifier la VALEUR RÉSOLUE (pas juste le nom de la variable) avant de diagnostiquer.
- **Domaine self-hébergé Supabase ≠ regex générique `*.supabase.co`** — toute logique de
  test/extraction de lien Supabase Auth écrite en supposant le SaaS managé casse sur une
  instance self-hébergée à domaine custom. Généraliser sur le CHEMIN (`/auth/v1/verify`),
  jamais sur le domaine.
- **`createQuote()` et `_send_magic_link()` envoient chacun un email avec « Bassira » dans
  le sujet au même destinataire** — tout matching de test sur un email doit cibler le sujet
  EXACT du template voulu (`_SUBJECT_BY_LOCALE` dans `client_account_service.py`), jamais un
  préfixe de marque générique.
- Repris du 2026-07-15 ~02h30, toujours valable : piège identification conteneur Kong/
  Supabase (jamais en boucle batchée), convention nommage `supabase-kong-<uuid>`/
  `supabase-db-<uuid>`, `API_EXTERNAL_URL` et `GOTRUE_SITE_URL` distincts et pas
  auto-synchronisés par le template Coolify.
