== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-09 (fin de session, soir) ==
Synthèse complète et autonome — ne suppose la lecture d'aucune passation antérieure.

[ETAT]
- **Prod saine** : `bassira.ma` tourne sur gunicorn (plus Werkzeug), dernier commit déployé
  `c30f045`. Conteneur Coolify app `u6pn5mr2pgi88s13un55pkzb`, rebuild auto sur push `main`
  (~15 min). Base Supabase self-hosted stack `dgybi9q5e2ggkjtaxlu2ukai`
  (`db-miroshark.ai-mpower.com`). Stripe MODE LIVE compte `acct_1PHxGdHM2FpoSxES`.
- `.ralph/prd.json` v2.0.0, chantier `V2-A-blocA` : **US-201/202/203/204/205/206/207
  toutes `passes:true`** (les 5 dernières validées cette session avec preuves E2E réelles).
  **Il ne reste qu'US-208** (Redis + worker RQ PDF, `passes:false`, débloquée par US-207).
- **Nouveau chantier documenté, EN ATTENTE DE VALIDATION AMINE : module Intake**
  (qualification /devis). Pack complet de 10 documents dans `docs/intake/01..10` (commit
  `c30f045`) : parcours 3 temps calibré Mom Test + agent conversationnel LLM de creusement
  (confidentialité différée, disclosure AI Act art. 50) + routage déterministe 3 branches +
  porte AAR « Testez-nous sur du connu ». **INTERDICTION ABSOLUE de coder ce module avant
  validation explicite d'Amine sur les 10 documents** (exigence répétée deux fois).
  7 US prêtes (US-IQ-01..07 dans docs/intake/04) à transposer dans prd.json APRÈS le go.
- Chasse moat-hunter livrée : `docs/moat-hunts/2026-07-09-adhesion-confiance-bassira.md`
  (3 MOATS FORTE : registre de vérification scellé / surveillance des verdicts CreditWatch
  via Saqr / corpus micro-calibration MENA ; 7 features ; 4 US suggérées US-220..223 NON
  insérées au PRD — arbitrage Amine). hunts.jsonl + base d'analogies de la skill mis à jour.
- Cartographie `.understand-anything/knowledge-graph.json` toujours dispo (1441 nœuds).

[FAIT — session 2026-07-09]
1. **US-205 Stripe validée E2E** : Checkout Session live réelle (HTTP 200, URL
   checkout.stripe.com) + webhook signé testé DANS le conteneur (script éphémère, secret
   jamais dans le chat, venv `/app/backend/.venv/bin/python3`) + ligne `quote_ownership`
   `status='paid'` vérifiée puis purgée (`DELETE 1`).
2. **US-207 WSGI livrée et déployée** (commits `e486bcf` + `9ada172`) : `backend/wsgi.py`
   (Config.validate() au niveau module pour fail-fast avec `--preload`), gunicorn 1 worker
   × 4 threads gthread timeout 180, script npm `backend:prod` (le `start` du Dockerfile
   pointe dessus ; `npm run dev` local INCHANGÉ). Config.validate() refuse de booter hors
   dev si `NEO4J_PASSWORD='miroshark'` ou `FLASK_DEBUG=true` (5 tests ajoutés,
   test_unit_hardening.py). Preuve de boot : logs « Starting gunicorn 26.0.0 / Booting
   worker ». 1ᵉʳ deploy échoué (exit 255 transitoire à l'export d'image, PAS lié au code) →
   retrigger API Coolify OK.
3. **3 smoke tests Playwright réparés** (cassés depuis US-201 sans détection) : sélecteur
   `/calibration` obsolète (`.cal-stat-card` → `.mt-card` de MethodologieView). 15/15 verts
   contre la prod.
4. **Bug bloquant signalé par Amine corrigé en urgence** (commit `fbb53ae`) : « Cannot read
   properties of undefined (reading 'checkout_url') » sur /offres — double unwrap axios
   dans `OffersView.vue::onCtaClick` (`data.data.checkout_url` → `res.data.checkout_url`,
   l'intercepteur `api/index.js` résout déjà `response.data`). Vérifié après déploiement
   par clic Playwright réel : redirection `cs_live_…` effective, zéro erreur console.
5. **US-203 + US-204 validées par le devis réel d'Amine** : `q_f767321b` en base avec
   payload (606 o) ; le devis de la veille `q_4b573942` a survécu aux 3 redeploys de la
   nuit (preuve de survie) ; email Resend reçu par Amine ; templates emails 100 %
   bassira.ma ; défaut SQL `footer_right='bassira.ma'` confirmé en prod.
6. **Chasse moat-hunter complète** (skill, 4 agents parallèles, 23 candidates, kill 41 %,
   gate moat_scorer 0 avertissement). Sourcing OpenSERP souverain port **7001** moteur
   `duck` (Google = CAPTCHA ; crawl4ai N'EXISTE PLUS sur le serveur → WebFetch en repli).
   Findings falsification : Aaru = zéro backtest/audit/pilote/suivi (confiance déléguée à
   Accenture/EY) ; Artificial Societies = SOC 2 SÉCURITÉ seulement, claims 95 % opaques.
7. **Pack Intake rédigé** (10 docs, cf. [ETAT]) suite au constat d'Amine : payload devis
   sans contexte de décision (`message` = libellé du sélecteur). Apport d'Amine intégré :
   l'agent LLM creuse ET trie le confidentiel (« à garder de vive voix », flag sans
   contenu).

[ALERTE]
- ⚠️ **`COOLIFY_API_TOKEN` du coffre DPAPI toujours périmé** (session sandboxée : accès à
  `~/.claude/secrets` refusé — la rotation nécessite la session home ou Amine, SOP-001).
  Token valide UNIQUEMENT sur le serveur :
  `/home/serveuria/.credentials/coolify-api-token-claude-20260708` (chmod 600).
- ⚠️ Stripe toujours en mode live sans sandbox — jamais de paiement test avec vraie carte.
- ⚠️ AI Act art. 50 applicable le **2026-08-02** (~3 semaines) : l'agent Intake DOIT se
  déclarer IA (câblé dans les docs) ; vérifier aussi que rien d'autre en prod n'y déroge.
- ⚠️ Piège possible relevé (docs/intake/09 R1) : les templates emails existants passent du
  contenu prospect dans du HTML via `str.format` — auditer `quote_received.html` pour
  l'injection HTML au moment du chantier Intake.
- ⚠️ Compte `test@bassira.ma` toujours existant sans org (sort jamais tranché par Amine).

[BLOQUE / EN ATTENTE D'AMINE]
- !! **Validation du pack `docs/intake/01..10`** — rien ne se code avant. Deux arbitrages
  explicitement attendus : ADR-IQ-06 (modèle LLM de l'agent — exigence darija/arabe) et
  07-legal §2 (où partent les transcripts selon le modèle gateway → politique de
  confidentialité ou modèle souverain).
- Arbitrage US-220..223 (moats de la chasse) — suggérées, non insérées au PRD.
- Rotation `COOLIFY_API_TOKEN` (cf. [ALERTE]).
- Sort de `test@bassira.ma`.

[NEXT]
1. **Si Amine valide le pack Intake** → transposer US-IQ-01..07 dans `.ralph/prd.json`
   (chantier `V2-B-intake`) puis dérouler en Ralph, US-IQ-01 d'abord.
2. **Sinon / en parallèle : US-208** (Redis + worker RQ PDF) — dernière US du bloc A,
   débloquée : Redis + service worker dans le compose Coolify (sans `container_name`,
   `expose:` pas `ports:`), preuve d'un job async en préprod, fallback sync loggé WARNING.
3. Guide d'entretien oral 20 min (palier haut) avec les skills `problem-interview` /
   `discovery-interview-prep` — chantier de contenu, après validation Intake.

[CTX]
- Accès serveur : `ssh -i ~/.ssh/serveurai_mnemo serveuria@100.124.187.2` (Tailscale ;
  user `serveuria`). Toute op Docker/psql sur le serveur, jamais en local.
- **API Coolify — endpoints qui marchent** : historique
  `GET /api/v1/deployments/applications/{uuid_app}`, détail+logs
  `GET /api/v1/deployments/{deployment_uuid}`, retrigger `GET /api/v1/deploy?uuid={uuid_app}`
  (les endpoints `deployments/{uuid_app}` et `?application_uuid=` sont des impasses).
- **OpenSERP souverain** : `http://localhost:7001` sur le serveur (moteur `duck` fiable,
  `google` = CAPTCHA, `bing` = bruit). crawl4ai déprovisionné.
- Conteneur backend : DEUX Python — `/usr/local/bin/python3` (nu) et
  `/app/backend/.venv/bin/python3` (deps projet) : toujours le venv en `docker exec`.
  Port Flask interne 5001.
- Playwright : accès direct à une route localisée = `?lang=<locale>` obligatoire
  (`withLocale`, tests/e2e/helpers.ts), sinon les sélecteurs texte ne matchent pas.
- Fins de ligne : `prd.json` et la plupart des fichiers = CRLF — réécrire en CRLF après
  édition Node sinon diff de 4 600 lignes (piège payé 2 fois cette session).
- pytest backend : 1694 passed / 0 failed (~3 min). Suite smoke Playwright : 15 tests.

[MEMO inter-sessions]
- **Le formulaire /devis actuel capture un payload inexploitable** (constat fondateur du
  chantier Intake) : `message` = libellé du sélecteur, role/industry/geo vides. Toute
  discussion « devis adaptatif » ou « pré-seed simulation » renvoie au pack docs/intake/.
- **Convention intercepteur axios** (`frontend/src/api/index.js`) : les fonctions API
  retournent DIRECTEMENT le body `{success, data}` — jamais destructurer `{ data }` puis
  relire `.data` (bug fbb53ae). Pattern correct : `const res = await call(); res.data.x`.
- **Échec deploy Coolify « exit 255 » à l'export d'image** après build complet réussi =
  transitoire connu → un simple retrigger API suffit, ne pas fouiller le code.
- **Stripe Price immuable** (`unit_amount`/`currency`) : corriger = nouveau Price +
  `default_price` + désactiver l'ancien. `currency_options` porte les 3 devises d'un seul
  Price ; la Session choisit via `currency=`.
- **Skill moat-hunter** : sa doc prescrit encore SearXNG/crawl4ai — obsolète (ADR-012 :
  OpenSERP ; crawl4ai absent). Mettre à jour la skill à l'occasion (session home).
- Marque : Bassira (بصيرة) visible, `miroshark` technique. Jamais « prédiction » dans le
  copy (ADR-002). URLs publiques bassira.ma (ADR-013). i18n fr/en/ar parité stricte
  (ADR-008). LLM via gateway LiteLLM, modèles choisis par Amine seul (ADR-004).

— fin passation —
