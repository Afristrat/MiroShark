== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-09 (soir, US-IQ-03 codée, PR #2 empilée sur PR #1) ==
Synthèse complète et autonome — ne suppose la lecture d'aucune passation antérieure.

[ETAT]
- **Prod saine, inchangée** : `bassira.ma`/`prospectives.ai-mpower.com` tourne sur gunicorn,
  dernier commit déployé `fe062c9e` (avant cette session). Aucun push sur `main` cette
  session — deux PR ouvertes, empilées :
  - **PR #1** https://github.com/Afristrat/MiroShark/pull/1 — US-IQ-01 (formulaire),
    branche `feat/us-iq-01-intake-form`, base `main`. Pas encore mergée.
  - **PR #2** https://github.com/Afristrat/MiroShark/pull/2 — US-IQ-03 (routage),
    branche `feat/us-iq-03-routing`, base **`feat/us-iq-01-intake-form`** (PAS `main` —
    stacked PR, car elle dépend du code non mergé de la PR #1). À retargeter sur `main`
    après merge de la PR #1 (GitHub le fait souvent automatiquement, à vérifier).
  - Repo local actuellement sur `feat/us-iq-03-routing` — `git checkout main` avant tout
    travail sans lien avec ce chantier.
- `.ralph/prd.json` v2.0.0, 149 stories. Chantier `V2-A-blocA` : US-201..207 `passes:true`,
  US-208 (Redis+RQ PDF) encore ouverte, indépendante. Chantier `V2-B-intake` : **US-IQ-01 et
  US-IQ-03 CODÉES et testées mais PAS marquées `passes:true` dans prd.json** (choix
  délibéré, comme pour IQ-01 : `.ralph/prd.json` non touché en attendant validation Amine /
  merge des PR). US-IQ-02, 04, 05, 06, 07 toujours `passes:false`, non commencées.
- **Décision Amine cette session (mode d'exécution)** : rester en **interactif** pour la
  suite du chantier Intake — PAS de relance du Ralph headless malgré le script corrigé
  (cause racine non traitée : le repo vit sous OneDrive, cf. MEMO incident Ralph headless).
  Ne pas re-proposer le headless sans nouvelle demande explicite d'Amine.

[FAIT — cette session]
1. **US-IQ-03 codée, testée, committée, PR #2 ouverte** (empilée sur PR #1, non mergée) :
   - `backend/app/services/intake_service.py` — `_decide_route(brief, confidential_flags)`
     (fonction pure, aucun I/O, aucun LLM — ADR-IQ-02) + `complete_routing(session_id)`
     (nouveau endpoint `POST /api/intake/session/<id>/complete`, state → 'completed').
     Priorité stricte : **entretien** (gouvernance conseil/tutelle/investisseurs OU budget
     10-100M/>100M OU ≥1 sujet confidentiel flaggé) **> self-service** (budget <1M ET
     exposition interne/sectorielle ET échéance strictement >14 jours) **> devis 48h**
     (repli). L'entretien est évalué en premier — ses critères sont des seuils de risque qui
     doivent l'emporter même sur un dossier qui ressemblerait sinon à du self-service.
   - Machine à états SQL : **déjà satisfaite par le trigger posé en US-IQ-01**
     (`20260709_001_intake_sessions.sql::trg_intake_sessions_guard_state`) — vérifié par
     inspection du code SQL cette session (rang croissant started<form_submitted<
     agent_active<completed, `completed`/`abandoned` terminaux). Aucune nouvelle migration.
     **Non vérifié en base live** (migration pas encore appliquée en prod, PR #1 pas
     mergée) — même statut d'attente que pour US-IQ-01.
   - Stripe (`backend/app/services/stripe_service.py::create_checkout_session`) : nouveau
     paramètre optionnel `intake_session_id` → `metadata[intake_session_id]` sur la Checkout
     Session. Endpoint `POST /api/stripe/create-checkout-session` le lit dans le body et le
     transmet. **Webhook `POST /api/stripe/webhook` NON touché** (directive explicite
     05-integrations.md) — le metadata est juste propagé pour traçabilité/évolutions
     futures, rien ne le consomme encore côté webhook.
   - Admin : `GET /api/admin/quotes/<quote_id>` (`backend/app/api/quote.py::get_quote_admin`)
     enrichi d'un champ `data.intake` (session_id/state/route/confidential_flags) quand le
     devis est lié à une session intake (`payload.intake_session_id`) — best-effort, ne fait
     jamais échouer le détail du devis si la session est absente/injoignable. Satisfait l'AC
     « sujets confidentiels récupérables via l'API admin » sans construire la vue dédiée
     (US-IQ-06, story séparée).
   - Tests : `test_unit_intake.py` (+table de vérité exhaustive paramétrée — 400 cas,
     produit d'axes enjeu(10)×gouvernance(5)×échéance(4)×flags(2), comparée à une
     réimplémentation indépendante de la spec, PAS un appel circulaire à
     `_decide_route` ; + tests `complete_routing` machine à états, 404/409 ; + endpoint),
     nouveau `test_unit_stripe_checkout.py` (propagation metadata + passthrough endpoint),
     `test_unit_quote_admin.py` (+2 tests enrichissement `data.intake`).
   - **Vérifié réellement** : `uv run pytest -m "not integration"` → **2127 passed / 1 failed
     / 42 skipped** (1 échec = `test_md_hash_stable_with_deterministic_enricher`, flaky
     **pré-existant et déjà documenté** le 2026-07-07 dans `docs/09-errors-log.md`, re-lancé
     ISOLÉMENT cette session → 1 passed ; aucun lien avec US-IQ-03, pipeline PDF jamais
     touché). `ruff check .` → All checks passed. `cd frontend && npm run build` → OK
     (aucun fichier frontend modifié, gate de non-régression uniquement).
2. Aucun autre changement cette session (pas de travail Cal.com/infra/secrets — chantier
   focalisé sur US-IQ-03 uniquement).

[ALERTE]
- ⚠️ **Test `tunnel-commercial.spec.ts` échoue en environnement frontend-only** (`vite
  preview` sans backend) — PAS une régression, déjà expliqué (US-IQ-01) : `crisis_drill_24h`
  self-service appelle Stripe au clic, échoue silencieusement sans backend. Ne pas
  re-diagnostiquer.
- ⚠️ **Coolify preview deployments NE SONT PAS actifs** sur l'app
  `u6pn5mr2pgi88s13un55pkzb` — pousser une branche/ouvrir une PR ne déclenche aucun build de
  preview. Webhook GitHub côté Coolify à configurer si cette voie est un jour souhaitée
  (hors scope de cette session, toujours vrai).
- ⚠️ **PR ouverte par erreur puis fermée** sur `aaronjmars/MiroShark#243` lors de la session
  précédente (dépôt tiers upstream, comportement par défaut de `gh pr create` sur un fork).
  Toujours `gh pr create --repo Afristrat/MiroShark` explicite — vérifié à nouveau respecté
  cette session (PR #2 créée directement au bon endroit).
- ⚠️ `COOLIFY_API_TOKEN` du coffre DPAPI **toujours périmé** — token de contournement valide
  UNIQUEMENT sur le serveur : `/home/serveuria/.credentials/coolify-api-token-claude-20260708`
  (rotation dans le coffre toujours en attente, session home ou Amine, SOP-001). Non
  utilisé cette session (aucune opération Coolify).
- ⚠️ IP serveur `serveuria` dernière valeur confirmée **`192.168.100.24`** (2026-07-09,
  session précédente) — non re-vérifiée cette session (aucune opération serveur). Toujours
  lire `$env:SERVER_HOST` du coffre plutôt que coder l'IP en dur.

[BLOQUE / EN ATTENTE D'AMINE]
- **PR #1 ET PR #2 en attente de review/merge** — merger #1 d'abord (base de #2). Pas de
  preview visuelle automatique disponible (voir ALERTE Coolify). US-IQ-03 est backend-only
  (aucun écran) — rien à vérifier visuellement pour cette PR spécifiquement.
- Arbitrage US-220..223 (moats de la chasse, suggérées, non insérées au PRD) — hors urgence.
- Rotation `COOLIFY_API_TOKEN` (coffre périmé).
- Sort de `test@bassira.ma` toujours existant sans org.
- Décision webhook vs polling pour `calcom_booking_uid` (US-IQ-04) — non tranchée, à
  trancher à l'implémentation de US-IQ-04 si ça bloque.

[NEXT]
1. **PRIORITÉ 1** : obtenir la review/merge de la PR #1 (Amine), puis de la PR #2 (retarget
   base sur `main` si GitHub ne le fait pas seul). Ensuite marquer `US-IQ-01` ET `US-IQ-03`
   `passes:true` + `completedAt` dans `.ralph/prd.json` (volontairement pas fait avant
   validation Amine, même logique que IQ-01).
2. **Poursuivre en interactif** (décision confirmée cette session, cf. ETAT) : US-IQ-02
   (agent conversationnel, dépend uniquement de US-IQ-01 déjà codée) est la prochaine story
   naturelle — avant de commencer, relire `docs/intake/01-intake-spec.md` §Étape B et
   `docs/intake/10-execution-prompts.md` §10.1 (system prompt agent) + §10.3 (grille
   d'évaluation, corpus fixture ≥10 transcripts). US-IQ-04/06/07 débloquées par US-IQ-03
   (codée, pas mergée) — peuvent être codées par-dessus `feat/us-iq-03-routing` si Amine
   valide qu'on continue à empiler sans attendre les merges (c'est le choix fait cette
   session pour IQ-03 sur IQ-01, cohérent à reconduire sauf avis contraire).
3. US-208 (Redis+RQ PDF) reste ouverte en parallèle si Intake est mis en pause.

[CTX]
- **Chaîne de branches** : `main` ← `feat/us-iq-01-intake-form` (PR #1) ←
  `feat/us-iq-03-routing` (PR #2, checkout local actuel). Toute nouvelle story IQ-0x qui
  continue d'empiler devrait partir de `feat/us-iq-03-routing`, pas de `main`.
- **Repo GitHub** : toujours `--repo Afristrat/MiroShark` explicite sur toute commande `gh`.
- Accès serveur : `ssh -i $env:SERVER_SSH_KEY serveuria@$env:SERVER_HOST` (coffre — IP DHCP,
  jamais coder en dur). Non utilisé cette session.
- **Cal.com** : endpoint public `https://api-agenda.ai-mpower.com/v2/...` (sans `/api`),
  header `Authorization: Bearer $CALCOM_API_KEY`. Ne PAS utiliser `agenda.ai-mpower.com`.
  Pertinent pour US-IQ-04 (pas encore commencée).
- Contrat payload intake (US-IQ-01, inchangé) : `{full_name, email, company, consent_rgpd,
  brief: {decision, options, deadline:{date,overdue}, governance, past_method, past_gap,
  stakes:{budget_bracket,jobs,exposure}, geo:[{country,segment}], data_assets}}`. Le
  `brief` est imbriqué, PAS à plat.
- **Nouveau contrat routage (US-IQ-03)** : `POST /api/intake/session/<id>/complete` (body
  vide) → `{success, data:{session_id, state:'completed', route}}`. `route` ∈
  `self_service|quote_48h|meeting`. Le front doit ensuite, pour `self_service`, appeler
  `POST /api/stripe/create-checkout-session` avec `intake_session_id` dans le body — ce
  n'est PAS fait automatiquement par `/complete` (le choix du package d'entrée adapté reste
  une décision produit/UX non spécifiée par les AC de US-IQ-03, cf. US-IQ-04/frontend).
- pytest backend : 2127 passed / 1 flaky pré-existant documenté (~3-4 min) sur
  `feat/us-iq-03-routing`.
- Fins de ligne : `prd.json` = CRLF — réécrire en CRLF après édition Node.

[MEMO inter-sessions]
- **Incident Ralph headless (résolu, ne pas reproduire)** : `ralph-loop.sh` avait 3 bugs
  réels, corrigés dans le script en session précédente, MAIS un circuit breaker a quand même
  été déclenché — cause racine probable : contention de lock Git, le repo vit sous OneDrive
  et le `.git` partagé, lui, ne l'est pas (contrairement à Qalem/Building ideas/Stratégie,
  délibérément hors OneDrive). **Corriger le script ne corrige pas la cause racine** — Amine
  a confirmé cette session de rester en interactif tant que ce point d'architecture n'est
  pas traité (migration du repo hors OneDrive = chantier à part, non entamé).
- **Le module Intake résout un problème RÉEL constaté par Amine** : le formulaire /devis
  actuel produisait des payloads inexploitables (`message`=libellé du sélecteur, champs
  vides, cf. incident `q_f767321b`). US-IQ-01 rend ce payload pauvre impossible par
  construction ; US-IQ-03 transforme ce brief riche en décision commerciale auditable
  (routage déterministe, testé exhaustivement — jamais de boîte noire LLM sur cette
  décision, ADR-IQ-02).
- **Convention intercepteur axios** (`frontend/src/api/index.js`) : les fonctions API
  retournent DIRECTEMENT le body `{success, data}` — jamais destructurer `{ data }` puis
  relire `.data` (bug déjà payé, commit `fbb53ae`). Pertinent dès que le frontend consommera
  `/complete` (US-IQ-04+).
- **Pattern « empiler une PR sur une PR non mergée »** (nouveau cette session) : quand une
  story dépend du code d'une story précédente pas encore mergée, créer la nouvelle branche
  DEPUIS la branche de la story précédente (pas depuis `main`) et ouvrir la PR avec
  `--base <branche-précédente>` — évite d'attendre un merge pour avancer, au prix d'un
  retarget manuel de la base une fois le merge amont fait. Décision explicite de continuer
  ainsi (cf. ETAT/NEXT) plutôt que d'attendre chaque review.
- **Séquençage secrets, règle absolue** : ne JAMAIS purger presse-papier/historique Win+V
  avant preuve système que le stockage a réussi (HTTP 201 vérifié).
- Marque : Bassira (بصيرة) visible, `miroshark` technique. Jamais « prédiction » dans le
  copy (ADR-002). URLs publiques bassira.ma TOUJOURS (ADR-013). i18n fr/en/ar parité stricte
  (ADR-008 + règle transversale langue module Intake). LLM via gateway LiteLLM, modèles
  choisis par Amine seul (ADR-004/ADR-IQ-06).

— fin passation —
