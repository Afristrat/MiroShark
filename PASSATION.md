== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-15 ~02h30 (Brique E2E email : Task 1-3 faites, Task 4 BLOQUÉE sur un bug de prod réel découvert en testant — décision Amine en attente) ==
Synthèse complète et autonome — ne suppose la lecture d'aucune passation antérieure,
remplace et purge intégralement l'entrée du 2026-07-14 ~23h00 (Lot B compte-client, tous ses
points restent acquis et ne sont pas remis en cause ci-dessous, juste non répétés).

[ETAT]
- **`main`** HEAD = `988e472`, poussé sur `origin/main`. 5 commits produit cette session
  (dans l'ordre) : `0e11da7` (spec E2E email), `a2c74f9` (plan E2E email, 5 tâches TDD),
  `46d811f` (Task 1 spike — GO confirmé + correction navigation SPA), `5a3fa33` (Task 2 —
  fixture `gmail-reader.ts`), `988e472` (Task 3 — correction doc RESEND_API_KEY périmée).
- **`git status` montre 1 fichier non commité** : `frontend/tests/e2e/client-account-email-
  roundtrip.spec.ts` (code de la Task 4, écrit mais JAMAIS passé — bloqué avant même de
  pouvoir tourner, cf. [BLOQUE]). Ne pas le committer tel quel avant d'avoir confirmé qu'il
  passe. `.playwright-mcp/` et `test-results/` untracked également, probablement à ajouter
  au `.gitignore` (non fait cette session, à vérifier).
- Suite pytest backend re-vérifiée en tout DÉBUT de session (avant tout changement) :
  **2257 passed, 1 failed, 42 skipped** — le 1 failed est `test_pdf_pipeline_e2e.py::
  TestPipelineMarkdown::test_md_hash_stable_with_deterministic_enricher`, un test flaky
  DÉJÀ DOCUMENTÉ depuis 2026-07-11 (comparaison d'horodatage non gelé, traverse une
  frontière de seconde) — PAS une régression de cette session, PAS corrigé cette session
  (hors scope du plan E2E email, à corriger séparément — quelques minutes, `freeze_time`).
- Build front (`npm run build`) vert (exit 0), revérifié en tout début de session.
- E2E `client-dashboard.spec.ts` (9 tests, Lot B) rejoué contre
  `https://prospectives.ai-mpower.com` en tout début de session : 9/9 verts, reconfirmé.

[FAIT — cette session]
1. **Brainstorming + spec + plan pour la brique E2E "round-trip email"** (alerte de clôture
   du Lot B : magic link jamais testé de bout en bout). Décision Amine : pas de Mailosaur,
   réutiliser le compte de service DWD Google Workspace déjà opérationnel (GAM7,
   `afriquestrategie.com`). Spec : `docs/superpowers/specs/2026-07-15-e2e-email-roundtrip-
   design.md`. Plan : `docs/superpowers/plans/2026-07-15-e2e-email-roundtrip-plan.md` (5
   tâches TDD).
2. **Secret ajouté au coffre** : `BASSIRA_ADMIN_PASSWORD` (mot de passe réel de
   `medamine.mansouriidrissi@gmail.com`, super-admin Bassira) — via `add-secret.ps1`
   (SOP-001 barrière 5), login réel testé et confirmé en prod.
3. **Task 1 (spike)** : preuve système que l'adressage Gmail `+tag`
   (`a.mansouri+e2e-...@afriquestrategie.com`) est bien livré et lisible via le compte de
   service DWD — **GO confirmé** (2 messages reçus, `Delivered-To` préserve le tag complet).
   Découverte annexe : `page.goto('/admin/quotes')` en navigation directe après un login
   frais fait courir une race avec la réhydratation de session Supabase → rebond sur
   `/login`. Fix : navigation SPA via le menu (`.app-header__admin-toggle` puis
   `a[href="/admin/quotes"]`), jamais de `goto` direct vers une route protégée juste après
   login.
4. **Task 2** : `frontend/tests/e2e/fixtures/gmail-reader.ts` — lecture Gmail via
   `googleapis` (nouvelle devDependency) + JWT du compte de service
   (`C:\Users\amans\.gam\oauth2service.json`, impersonation `a.mansouri@afriquestrategie.com`).
   Expose `extractMagicLink(html)`, `waitForEmail(opts)`, `trashMessage(id)`. TDD via
   `node:test` (2/2 verts, `gmail-reader.test.mjs`).
5. **Task 3** : `docs/05-integrations.md` corrigé — `RESEND_API_KEY` affirmait à tort
   « JAMAIS configurée en prod (US-204, bloquant) » alors que US-204 est `passes=true`
   depuis 2026-07-09 et la clé est confirmée présente sur le conteneur prod live.

[ALERTE]
- **BUG DE PRODUCTION RÉEL CONFIRMÉ, PAS ENCORE CORRIGÉ** : le magic link envoyé par
  `ensure_client_account()` (Lot B, `client_account_service.py::_send_magic_link`) est
  **cassé pour tout vrai client** depuis le lancement du Lot B. Cause : sur l'instance
  Supabase self-hébergée dédiée à miroshark (conteneur `supabase-kong-
  dgybi9q5e2ggkjtaxlu2ukai`, domaine public `db-miroshark.ai-mpower.com`),
  `API_EXTERNAL_URL=http://supabase-kong:8000` (hostname Docker interne, injoignable hors
  du serveur) alors que `GOTRUE_SITE_URL=http://db-miroshark.ai-mpower.com` est correct.
  Le lien magique généré pointe donc vers un host qui ne résout pas pour un vrai client.
  **Correctif proposé (pas encore appliqué)** : aligner `API_EXTERNAL_URL` sur
  `https://db-miroshark.ai-mpower.com`. En attente du feu vert d'Amine.
- **Fausse alerte corrigée** : j'ai initialement diagnostiqué (à tort) un mélange de
  données entre Bassira et Nahda, suite à une erreur d'attribution de conteneur (confusion
  entre `supabase-kong-h53gldd7e8gr9zccvsnmpinw` = Nahda et `supabase-kong-
  dgybi9q5e2ggkjtaxlu2ukai` = miroshark). **Infirmé par audit complet et méthodique des 10
  instances Supabase du serveur** (une par une, jamais en boucle batchée) — la base
  miroshark contient exactement 13 tables, toutes propres à Bassira
  (`intake_sessions, org_invitations, org_members, organizations, pdf_branding,
  quote_ownership, report_audit_log, report_comments, report_deliveries, report_downloads,
  report_states, report_versions, simulation_ownership`), aucune table étrangère. Rapport
  complet livré à Amine en 10 fichiers séparés (un par instance, sortie `psql` brute) dans
  le scratchpad de session — pas dans ce repo (touche d'autres produits : Assas, Qalem,
  Saqr, Rami, Nahda 3095 MB/142 tables, Taqwim, Ania, Sawt, Tamkin).
- **Secret `NAHJ_SUPABASE_POSTGRES_DB` exposé 3× en transcript** pendant l'audit (valeur
  générique de type nom de base par défaut, matche du texte banal type "postgres" dans
  quasi toute sortie `psql` — faux positif structurel, pas une vraie fuite d'un secret
  sensible). Rotation SOP-001 recommandée mais PAS FAITE — décision en attente d'Amine.
  Fait notable : les clés `NAHJ_SUPABASE_*` du coffre (11 clés) ne correspondent à
  **aucune** des 10 instances Supabase trouvées sur le serveur — orpheline, ou 11e instance
  pas encore provisionnée/exposée (cohérent avec "Nahj a moins de 48h" — dixit Amine).
- **Hook `secret-sentinel.ps1` désactivé temporairement puis restauré** dans
  `C:\Users\amans\.claude\settings.json` pendant l'audit (à la demande explicite d'Amine,
  pour ne pas interrompre l'audit à chaque faux positif). **Restauré et vérifié actif**
  en fin de session — config identique à l'originale.
- Données de test créées via le flux applicatif réel pendant Task 1 + tentative Task 4
  (devis + comptes clients taggés `a.mansouri+e2e-*@afriquestrategie.com` /
  `+e2e-spike-*@afriquestrategie.com`) — confirmé sans risque : tout est allé dans la base
  miroshark elle-même (isolée, cf. ci-dessus), reconnaissable par le pattern d'email,
  jamais nettoyé automatiquement (pas de suppression Supabase dans le chemin chaud du
  test, décision du spec). 2 emails de test résiduels dans la boîte `a.mansouri@` (la
  commande GAM de mise à la corbeille a échoué en syntaxe, jamais retentée).

[BLOQUE / EN ATTENTE]
- **Task 4 (spec E2E round-trip complet) ne peut pas passer tant que le bug
  `API_EXTERNAL_URL` n'est pas corrigé** — le lien magique extrait par `gmail-reader.ts`
  serait injoignable depuis un navigateur externe (`http://supabase-kong:8000`
  ne résout pas). Le fichier `client-account-email-roundtrip.spec.ts` est écrit
  (voir [ETAT]) mais jamais lancé avec succès.
- Décision Amine nécessaire, dans l'ordre :
  1. Corrige-t-on `API_EXTERNAL_URL` maintenant (périmètre confirmé isolé à l'instance
     miroshark, aucun risque cross-produit) ?
  2. Rotation de `NAHJ_SUPABASE_POSTGRES_DB` — maintenant ou plus tard ?

[NEXT]
1. **Dès accord Amine** : corriger `API_EXTERNAL_URL` sur le conteneur
   `supabase-kong-dgybi9q5e2ggkjtaxlu2ukai` (probablement via variable d'env Coolify du
   service Supabase dédié à miroshark — PAS le repo applicatif — à localiser via l'UI/API
   Coolify, resource distincte de l'app `u6pn5mr2pgi88s13un55pkzb`).
2. Relancer Task 4 (`client-account-email-roundtrip.spec.ts`) une fois le correctif
   déployé — devrait passer du premier coup si le lien devient joignable.
3. Task 5 du plan (gates finaux : suite E2E complète + build + mise à jour passation) —
   pas encore commencée.
4. Corriger le test flaky `test_md_hash_stable_with_deterministic_enricher` (freeze du
   temps) — connu depuis le 2026-07-11, jamais traité, quelques minutes.
5. Une fois Task 4/5 closes : reprendre l'ordre de priorité déjà validé avec Amine
   (difficulté croissante) — `US-208` (Redis+RQ worker PDF actifs en prod, dépendance
   `US-207` déjà `passes=true`), puis `US-IQ-07` (pré-seed simulation depuis le brief),
   puis Lot C (Cal.com embarqué), Lot D (white-label Cal.com), `US-IQ-05`/`US-IQ-06`.
6. Nettoyer `.gitignore` pour `.playwright-mcp/` et `test-results/` (untracked, probable
   oubli).

[CTX]
- App Coolify miroshark : uuid `u6pn5mr2pgi88s13un55pkzb`. Prod =
  `prospectives.ai-mpower.com`, liens publics `bassira.ma` (ADR-013).
- **Instance Supabase dédiée miroshark** (distincte de l'app Coolify ci-dessus) :
  conteneurs `supabase-kong-dgybi9q5e2ggkjtaxlu2ukai` / `supabase-db-
  dgybi9q5e2ggkjtaxlu2ukai`, domaine public `db-miroshark.ai-mpower.com`. `SUPABASE_URL`
  du backend = `https://db-miroshark.ai-mpower.com` (vérifié sur le conteneur prod live).
- Spec E2E email : `docs/superpowers/specs/2026-07-15-e2e-email-roundtrip-design.md`.
- Plan E2E email : `docs/superpowers/plans/2026-07-15-e2e-email-roundtrip-plan.md` (mis à
  jour avec le résultat réel du spike Task 1, y compris la correction de navigation SPA).
- Nouveaux fichiers : `frontend/tests/e2e/fixtures/gmail-reader.ts` +
  `gmail-reader.test.mjs`, `frontend/tests/e2e/client-account-email-roundtrip.spec.ts`
  (non commité).
- Secret ajouté : `BASSIRA_ADMIN_PASSWORD` dans le coffre DPAPI.
- Mode de travail : exécution INLINE sur `main` (consentement Amine hérité de la session
  Lot B, reconfirmé implicitement cette session).
- Rapport d'audit des 10 instances Supabase : dans le scratchpad de session (pas dans ce
  repo, pas dans git) — `audit-supabase-serveuria-20260715.md` + dossier
  `supabase-instances/01-...` à `10-...`. À redemander si besoin, non persistant au-delà
  de la session Claude Code.

[MEMO inter-sessions]
- **Ne jamais identifier un conteneur Kong/Supabase par une boucle shell batchée** — la
  sortie peut se désaligner entre le nom du conteneur et son résultat (cause de l'erreur
  d'attribution Nahda/miroshark cette session). Toujours une commande, un conteneur, un
  résultat vérifié avant de passer au suivant.
- **Convention de nommage des instances Supabase self-hébergées sur serveuria** :
  `supabase-kong-<uuid>` / `supabase-db-<uuid>`, même `<uuid>` pour les deux — sauf Tamkin
  qui a un nommage propre (`tamkin-kong`/`tamkin-db`). Le domaine public réel se lit
  UNIQUEMENT via le label Traefik (`docker inspect <conteneur> --format
  '{{json .Config.Labels}}'`), jamais supposé depuis le nom du conteneur ni depuis une
  variable d'environnement interne (`GOTRUE_SITE_URL` peut être périmée/incohérente avec
  le routage Traefik réel, comme vu sur l'instance Nahda dont `GOTRUE_SITE_URL` était
  cohérente mais que j'avais mal associée au domaine miroshark par erreur de conteneur).
- **Piège Coolify/Supabase self-hosted** : `API_EXTERNAL_URL` et `GOTRUE_SITE_URL` sont
  deux variables distinctes, pas automatiquement synchronisées par le template Coolify.
  `SITE_URL` correct n'implique PAS que `API_EXTERNAL_URL` (base des `action_link` générés
  par `generate_link()`) le soit aussi — à vérifier systématiquement ensemble sur toute
  nouvelle instance Supabase self-hébergée provisionnée via Coolify.
- **Secrets génériques dans le coffre DPAPI** : une valeur de secret trop générique (nom
  de base par défaut type "postgres") déclenche la sentinelle en faux positif sur presque
  toute sortie de commande légitime — signalé mais pas corrigé (reclassification ou
  rotation vers une valeur moins générique à envisager, hors scope de cette session).
