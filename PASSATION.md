== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-09 (soir, chantier Intake rédigé) ==
Synthèse complète et autonome — ne suppose la lecture d'aucune passation antérieure.

[ETAT]
- **Prod saine** : `bassira.ma` tourne sur gunicorn (plus Werkzeug), dernier commit déployé
  `c30f045`. Conteneur Coolify app `u6pn5mr2pgi88s13un55pkzb`, rebuild auto sur push `main`
  (~15 min). Base Supabase self-hosted stack `dgybi9q5e2ggkjtaxlu2ukai`
  (`db-miroshark.ai-mpower.com`). Stripe MODE LIVE compte `acct_1PHxGdHM2FpoSxES`.
- `.ralph/prd.json` v2.0.0, 149 stories. Chantier `V2-A-blocA` : **US-201 à 207 toutes
  `passes:true`**. Il ne reste qu'**US-208** (Redis + worker RQ PDF, `passes:false`,
  débloquée par US-207) pour clore ce bloc.
- **Nouveau chantier `V2-B-intake` PRÊT À EXÉCUTER** : module de qualification /devis.
  10 documents de fondation VALIDÉS par Amine dans `docs/intake/01..10` (commits `c30f045`
  puis `542dba8` pour les révisions) + **7 US rédigées et poussées dans prd.json** (commit
  `3ed413f`) : US-IQ-01 (formulaire 3 temps) → US-IQ-02 (agent conversationnel, dép.
  US-IQ-01) → US-IQ-03 (routage 3 branches, dép. US-IQ-01) → US-IQ-04 (emails+Cal.com, dép.
  US-IQ-03) / US-IQ-05 (porte AAR, dép. US-IQ-01) / US-IQ-06 (vue admin, dép. US-IQ-03) /
  US-IQ-07 (pré-seed simulation, dép. US-IQ-03). **Toutes `passes:false` — AUCUN CODE ÉCRIT
  pour ce module, prêt pour l'exécution Ralph.**
- Chasse moat-hunter livrée : `docs/moat-hunts/2026-07-09-adhesion-confiance-bassira.md`
  (3 MOATS FORTE ; 4 US suggérées US-220..223 NON insérées au PRD — arbitrage Amine, hors
  urgence).
- Cartographie `.understand-anything/knowledge-graph.json` toujours dispo (1441 nœuds).

[FAIT — session 2026-07-09, deuxième moitié (après la 1ʳᵉ passation du soir)]
1. **Directives Amine intégrées dans les 10 documents Intake** (commit `542dba8`) :
   - **Cal.com self-hosted DÉJÀ installé** (`agenda.ai-mpower.com`) remplace le
     « pas d'outil calendrier » de la v1 — ADR-IQ-03 réécrite.
   - **Langue transversale** : toute correspondance/livrable (emails, réservation,
     devis, PDF) suit la locale de session — règle gravée dans spec/UX/intégrations.
   - **Transcript de qualification = pièce DURABLE du dossier** (nouveau ADR-IQ-07) :
     ma purge J+90 initiale était une erreur, corrigée — conservation tant que le dossier
     de devis existe, persistance tour par tour, jamais perdu.
2. **Investigation Cal.com sur le serveur** : stack Coolify `a1354o9qgw8rdkszn56o9x3o`
   PARTAGÉE (Hermes l'utilise aussi). App web `calcom-…` (port interne 3001, image
   cal.diy). Service API v2 `calcom-api-…` (port interne **3002**, image custom registre
   local). ⚠️ **La route publique `agenda.ai-mpower.com/api/*` est derrière un challenge
   Cloudflare** — API à appeler EXCLUSIVEMENT en interne. Base Postgres partagée
   `database-…`/`calendso`, user `unicorn_user`.
3. **Clé `CALCOM_API_KEY` posée en env Coolify miroshark**, validée par correspondance
   SHA-256 contre `ApiKey.hashedKey` en base (le hash porte sur la clé SANS le préfixe
   `cal_`). Presse-papier purgé SEULEMENT après confirmation 201.
4. **Défaut découvert et NON résolu** : le service `calcom-api` rejette actuellement
   TOUTE clé (`401 Invalid API Key` sur `/v2/me`), alors que la clé matche en base et que
   `API_KEY_PREFIX=cal_` est correct des deux côtés. Stack partagée → fix hors périmètre
   Bassira, à traiter par la session qui possède cette infra (probablement home ou
   Hermes). N'empêche PAS US-IQ-04 (le lien de réservation public fonctionne
   indépendamment de l'API) mais À VÉRIFIER avant l'implémentation de l'appel API réel.
5. **Dette notée (pas implémentée, sur demande explicite d'Amine)** : gestion des secrets
   en deux fichiers — un index de NOMS consultable + le coffre DPAPI des valeurs. Spec et
   recommandations complètes dans la mémoire `feedback_secrets_index_deux_fichiers.md`
   (home). Action différée à une session avec accès `~/.claude/secrets`.
6. **7 US-IQ rédigées** (skill `/ralph-tui-prd`, format adapté au schéma prd.json de ce
   repo — pas de pipeline ralph-tui séparé, ce repo n'en a pas) et poussées (`3ed413f`).

[ALERTE]
- ⚠️ **`COOLIFY_API_TOKEN` du coffre DPAPI toujours périmé** — rotation nécessite la
  session home ou Amine (SOP-001). Token valide UNIQUEMENT sur le serveur :
  `/home/serveuria/.credentials/coolify-api-token-claude-20260708` (chmod 600).
- ⚠️ **Cal.com API v2 : 401 sur toute clé** (cf. [FAIT] point 4) — à re-tester avant de
  coder US-IQ-04. Si toujours cassé, escalader vers la session propriétaire de la stack
  `a1354o9qgw8rdkszn56o9x3o` (ne PAS déboguer depuis une session Bassira — stack partagée).
- ⚠️ AI Act art. 50 applicable le **2026-08-02** (~3 semaines) — l'agent Intake (US-IQ-02)
  DOIT se déclarer IA dès son premier message (déjà câblé dans le prompt doc 10).
- ⚠️ Stripe mode live sans sandbox — jamais de paiement test avec vraie carte.
- ⚠️ Compte `test@bassira.ma` toujours existant sans org (sort jamais tranché).

[BLOQUE / EN ATTENTE D'AMINE]
- Arbitrage US-220..223 (moats de la chasse, suggérées, non insérées au PRD).
- Rotation `COOLIFY_API_TOKEN`.
- Sort de `test@bassira.ma`.
- Décision de webhook vs polling pour la confirmation de réservation Cal.com
  (`calcom_booking_uid`, US-IQ-04) — laissé ouvert à l'implémentation, trancher si
  ambiguïté bloque la story.

[NEXT]
1. **PRIORITÉ — dérouler le chantier `V2-B-intake` en mode Ralph**, dans l'ORDRE des
   dépendances : US-IQ-01 (aucune dép.) → US-IQ-02 ET US-IQ-03 (dép. US-IQ-01, parallélisables) →
   US-IQ-04/05/06/07 (dép. US-IQ-01 ou US-IQ-03 selon la story, cf. prd.json). Avant
   US-IQ-04 : re-tester Cal.com API v2 en interne (cf. [ALERTE]).
2. **US-208** (Redis + worker RQ PDF) reste ouverte en parallèle si Intake est mis en
   pause — dernière US du bloc A, indépendante du chantier Intake.
3. Guide d'entretien oral 20 min (palier haut, skills `problem-interview` /
   `discovery-interview-prep`) — après que US-IQ-01..04 tournent en prod.

[CTX]
- Accès serveur : `ssh -i ~/.ssh/serveurai_mnemo serveuria@100.124.187.2` (Tailscale ;
  user `serveuria`). Toute op Docker/psql sur le serveur, jamais en local.
- API Coolify : historique `GET /api/v1/deployments/applications/{uuid_app}`, détail+logs
  `GET /api/v1/deployments/{deployment_uuid}`, retrigger `GET /api/v1/deploy?uuid=...`.
  POST env var = JSON minimal `{key,value}` (le champ `is_build_time` est refusé → 422).
- OpenSERP souverain : `http://localhost:7001` sur le serveur (moteur `duck` fiable,
  `google`=CAPTCHA). crawl4ai déprovisionné.
- Conteneur backend miroshark : DEUX Python — `/usr/local/bin/python3` (nu) et
  `/app/backend/.venv/bin/python3` (deps projet) : toujours le venv en `docker exec`.
  Port Flask interne 5001.
- **Cal.com** : app web interne `:3001`, API v2 interne `:3002` (conteneurs
  `calcom-a1354o9qgw8rdkszn56o9x3o` / `calcom-api-a1354o9qgw8rdkszn56o9x3o`), public
  `agenda.ai-mpower.com` derrière challenge Cloudflare pour `/api/*`. DB `calendso`
  partagée, user `unicorn_user`.
- Playwright : accès direct à une route localisée = `?lang=<locale>` obligatoire
  (`withLocale`, tests/e2e/helpers.ts).
- Fins de ligne : `prd.json` et la plupart des fichiers = **CRLF** — réécrire en CRLF
  après toute édition Node, sinon diff de 4600+ lignes (piège payé plusieurs fois).
- pytest backend : 1694 passed / 0 failed avant ce chantier (~3 min). Suite smoke
  Playwright : 15 tests.

[MEMO inter-sessions]
- **Le module Intake résout un problème RÉEL constaté par Amine** : le formulaire /devis
  actuel produit des payloads inexploitables (`message`=libellé du sélecteur, champs
  vides). Toute discussion « devis adaptatif »/« pré-seed simulation » renvoie à
  `docs/intake/`.
- **Convention intercepteur axios** (`frontend/src/api/index.js`) : les fonctions API
  retournent DIRECTEMENT le body `{success, data}` — jamais destructurer `{ data }` puis
  relire `.data` (bug déjà payé, commit `fbb53ae`). Pattern correct :
  `const res = await call(); res.data.x`.
- **Séquençage secrets, règle absolue** : ne JAMAIS purger presse-papier/historique
  Win+V avant preuve système que le stockage a réussi (HTTP 201 vérifié). Cf. mémoire
  `feedback_secrets_index_deux_fichiers.md`.
- **Stripe Price immuable** (`unit_amount`/`currency`) : corriger = nouveau Price +
  `default_price` + désactiver l'ancien.
- **Skill moat-hunter** : sa doc prescrit encore SearXNG/crawl4ai — obsolète (ADR-012 :
  OpenSERP ; crawl4ai absent). À mettre à jour à l'occasion (session home).
- Marque : Bassira (بصيرة) visible, `miroshark` technique. Jamais « prédiction » dans le
  copy (ADR-002). URLs publiques bassira.ma (ADR-013). i18n fr/en/ar parité stricte
  (ADR-008 + règle transversale langue du module Intake). LLM via gateway LiteLLM,
  modèles choisis par Amine seul (ADR-004/ADR-IQ-06).

— fin passation —
