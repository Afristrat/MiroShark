== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-16 ~01h00 (Chantier Simulations V2 CADRÉ ET FIGÉ : spec + ADR-015→019 + 17 stories commitées ; mode Ralph demandé mais EN PAUSE SOP-013 — prototype 9 écrans publié, Council rendu NO-GO en l'état, EN ATTENTE du go explicite d'Amine + arbitrage lexique) ==
Synthèse complète et autonome — remplace et purge intégralement l'entrée du 2026-07-15
~20h30 (ses points FAIT restent acquis : brique E2E email soldée, magic link validé en
prod, 3 bugs prod corrigés — rien n'est remis en cause ci-dessous).

[ETAT]
- **`main`** HEAD = `bea69b6`, poussé sur `origin/main`. Commits de cette session :
  `5ab364d` (spec Simulations V2 + ADR-015→019 + 17 stories US-221→US-237 + dictionnaire
  tables planifiées + backlog US-216 marquée convertie), `bea69b6` (pause SOP-013 notée
  dans `.ralph/progress.md`).
- Gates re-prouvés en début de session : pytest **2258 passed, 0 failed, 42 skipped**
  (relancée intégralement), `npm run build` exit 0, prod = conteneur Coolify sur l'image
  taguée du SHA de HEAD (vérifié par `docker ps` via SSH), bassira.ma HTTP 200.
- `.ralph/prd.json` : **166 stories, 21 `passes=false`** (US-208, US-IQ-05/06/07,
  US-221→US-237). JSON valide, **fichier en CRLF** (cf. [MEMO]).
- **LOOP RALPH FORMELLEMENT EN PAUSE** (SOP-013, gate en cours) — aucune story codée.

[FAIT — cette session]
1. **Vérification par preuve de la passation précédente** (règle n°4) : git, prod
   (image = SHA HEAD), pytest, build, prd.json — tout confirmé.
2. **Deep-explore simulations** (3 agents Explore Haiku + contre-vérifications
   personnelles, erreurs d'agents corrigées). Angles morts majeurs sourcés :
   `resolve_market()` défini mais JAMAIS appelé (`polymarket/platform.py:378` — marchés
   jamais dénoués), P&L des agents faux (`cost_basis = 0.50` en dur,
   `environment.py:40`), prix AMM jamais dans le PDF (`charts.py:251` trace les stances),
   `CHINA_TIMEZONE_CONFIG` (config calée sur Pékin, `simulation_config_generator.py:30`),
   AUCUNE règle de routage d'arènes (3 checkboxes user + `/start` sans validation),
   prompts d'arènes en anglais nus (personas sans grounding), `do_nothing` de base.py
   contaminé vocabulaire trader, enum plateformes en dur (`simulation.py:3771`),
   `enabled_platforms` non requêtable, artefacts sur volume éphémère (ADR-005 ouvert).
   Insight clé : Twitter/Reddit partagent les mêmes classes → une arène MENA = un simple
   `SimulationConfig` de plus.
3. **Arbitrages d'Amine actés au fil de la session** : (a) dénouement simulé avec VRAI
   sens économique ; (b) personas au standard **ESCO** (API testée OK depuis le poste en
   FR ET AR) + enrichissement hors-taxonomie par **le 122B** → directement en Supabase ;
   (c) élévation **L99 de tous les prompts** de simulation (skill prompt-engineer-pro) +
   page console **super-admin** des prompts, **éditables en base** ; (d) rejet du menu
   fixe de critères de dénouement (« les scénarios sont infinis ») → architecture
   **resolution_spec par marché + oracle de clôture** proposée et retenue ;
   (e) renommage client **« marché de convictions »** (option renommage complet choisie
   via AskUserQuestion).
4. **Livrables commités (`5ab364d`)** : spec
   `docs/superpowers/specs/2026-07-16-simulations-v2-design.md` ; **ADR-015**
   (resolution_spec + oracle YES/NO/INVALID + void/remboursement + richesse finale =
   score de justesse), **ADR-016** (ESCO + cache `occupation_profiles` + 122B),
   **ADR-017** (registre `simulation_prompts` versionné, édition = nouvelle version,
   activation conditionnée au golden set), **ADR-018** (lexique « convictions »
   fr/en/ar), **ADR-019** (routage déterministe + override journalisé) ; **17 stories**
   US-221→US-237 (chantier `16-simulations-v2`, dépendances câblées, hard things first) ;
   dictionnaire : section « tables planifiées » (`simulation_prompts`,
   `occupation_profiles`, `market_resolutions`, colonne `enabled_platforms`).
5. **« mode ralph » reçu → gate SOP-013 appliqué intégralement** : pause formelle
   (commit `bea69b6`), périmètre recompté (21 stories), tokens charte extraits de
   `frontend/src/design-tokens.css` (pas de Design.md), **prototype navigable 9 écrans**
   publié (Artifact, thèmes clair/sombre, tokens `--wi-*` à l'identique) :
   https://claude.ai/code/artifact/28943904-102a-4642-b597-43cd11cc74a9 — écrans :
   couverture, création-arènes (routage+override), marchés de convictions avec
   dénouement, PDF dénouement, PDF comparatif Delphi, console prompts liste, prompt
   détail (versions/diff/golden set), intake Porte 2 AAR scellée, dossier devis enrichi,
   pré-seed simulation depuis devis. Écarts signalés : Artifact au lieu d'aidesigner
   (fidélité tokens privilégiée — incident v1.1.0), polices en repli system-ui (CSP),
   prototype monolingue fr.
6. **Council exécuté** (5 conseillers Sonnet + 5 revues croisées anonymisées + synthèse
   Chairman). Verdict : **NO-GO en l'état, correctifs ciblés sans refonte**.
   Convergence 4/5 : le lexique « oracle/verdict/confiance/dénouement/Delphi » contredit
   le positionnement non-prédictif ; le gate ne couvre que le décor (contrat d'interface
   du moteur manquant) ; S4 sans disclaimer (S3 en a un) ; 5 trous d'implémentation
   (états vides/erreur, schéma série de prix, scellement non tranché, retour d'état
   golden set, algo de diff). Clash arbitré : schéma cross-simulations (Expansionist) ET
   fil rouge « premier cas Porte 2 réel au plus tôt » (First Principles) — les deux.
   Erreurs factuelles des conseillers corrigées par preuve : ADR-002 interdit le claim
   commercial, pas la mesure interne ; ADR-IQ-05 existe mais mécanisme explicitement « à
   trancher en revue technique » ; routage S8 lit le montant (non scellé) ; le 122B ne
   fait pas tourner le moteur.
7. Remise faite à Amine (prototype + synthèse Council + 3 voies : go tel quel / corrige
   et re-soumets / go partiel backend) — **sa réponse n'est pas encore donnée**.

[ALERTE]
- Héritées, toujours ouvertes : **finding Stripe live checkout** (tunnel-commercial.spec
  cliquant « Crisis Drill 24h » → vraie session Checkout LIVE — arbitrage Amine jamais
  rendu) ; dette 27 tests E2E pré-existants (fixture dropdown Admin + smoke Step 1) ;
  flaky `test_md_hash_stable_with_deterministic_enricher` ; 2 emails de test résiduels
  dans a.mansouri@ ; rotation `NAHJ_SUPABASE_POSTGRES_DB` différée (décision Amine).
- Recommandations Council NON encore intégrées à la spec/stories (attente du go) :
  remonter **US-212 (lint/typecheck)** avant le loop long ; réordonner pour atteindre le
  premier cas Porte 2 réel au plus tôt ; clés/index cross-simulations dans US-226 ;
  vérification terminologie AR/RTL au prototype v2.

[BLOQUE / EN ATTENTE]
- **Gate SOP-013 ouvert** : loop Ralph en pause, AUCUNE story codée avant le **go
  explicite d'Amine** (silence ≠ accord — SOP-013 §9). Deux décisions attendues :
  (1) **lexique client** (l'Outsider conteste même « marché de convictions » ; proposer
  des variantes fr/ar si Amine le demande — le naming est SA décision) ;
  (2) **go/no-go** sur l'une des 3 voies proposées.

[NEXT]
1. Recevoir l'arbitrage lexique + le go/no-go d'Amine (cf. [BLOQUE]).
2. Si « corrige et re-soumets » (voie recommandée par le Council) : **prototype v2**
   (disclaimer S4 = S3, lexique arbitré appliqué, états manquants : min. 1 arène,
   golden set en cours/échec, scénario démo neutralisé, libellés clés en ar/RTL) + **3
   addenda de spec** (contrat d'interface oracle : schéma prix-par-round durable +
   `market_resolutions` ; mécanisme de scellement ADR-IQ-05 tranché en revue technique :
   chiffrement applicatif vs hachage+révélation ; périmètre de lecture du routage
   Branche B) + intégrer les recommandations Council ([ALERTE]) dans prd.json → nouveau
   passage devant Amine (portion concernée seulement, SOP-013 §9).
3. Après le go : reprise Ralph story par story — US-224 (renommage, quick win) ou
   US-221 (persistance, hard first) selon la voie choisie ; gates par story
   (build + pytest), commit `[US-XXX] Titre`, `/ponytail-debt` à chaque fin de story.
4. Toujours en file (inchangé) : arbitrage Stripe live checkout, dette 27 tests E2E,
   flaky, US-208.

[CTX]
- Spec : `docs/superpowers/specs/2026-07-16-simulations-v2-design.md` (architecture
  complète + §6 graphe de dépendances). ADR : `docs/08-decisions-log.md` ADR-015→019.
  Stories : `.ralph/prd.json` chantier `16-simulations-v2`. Pause SOP-013 : notée en fin
  de `.ralph/progress.md`.
- Prototype : https://claude.ai/code/artifact/28943904-102a-4642-b597-43cd11cc74a9
  (source : scratchpad session `proto-simulations-v2.html` — republier le même chemin
  garde l'URL ; depuis une autre session, passer `url:` à l'outil Artifact).
- SOP-013 : `C:\projets\sop\interne\SOP-013-prototype-navigable-avant-ralph\...md`
  (étapes 7-10 restantes : go explicite tracé AVANT toute story).
- Charte : `frontend/src/design-tokens.css` (75 tokens `--wi-*`, light+dark ; primary
  #a13f0f, bg #fff8f6, secondary #006d44, tertiary #006971, radius 24/12px,
  Outfit/Manrope). Chart stances : mint=adhésion, terra=résistance, sand=observation.
- ESCO : `python C:\Users\amans\.claude\skills\prompt-engineer-pro\scripts\esco-role.py
  "<métier>" --lang fr|ar|en` — testé OK (fiches réelles FR et AR). Pattern :
  `reference/esco-role-prompting.md` (bloc `<expertise_metier>` + compétences = axes).
- App Coolify miroshark : uuid `u6pn5mr2pgi88s13un55pkzb` ; prod bassira.ma ; instance
  Supabase dédiée `db-miroshark.ai-mpower.com` (conteneurs `*-dgybi9q5e2ggkjtaxlu2ukai`).
- Fichiers clés du moteur (deep-explore) : `wonderwall/simulations/base.py` (contrat),
  `polymarket/{platform,amm,actions,prompts,environment}.py`,
  `social_media/__init__.py` (3 SimulationConfig), `scripts/run_parallel_simulation.py`
  (lock-step + ponts), `app/services/{simulation_manager,simulation_runner,
  simulation_config_generator,wonderwall_profile_generator}.py`.

[MEMO inter-sessions]
- **`.ralph/prd.json` est en CRLF** : toute réécriture Python doit utiliser
  `open(..., 'w', newline='\r\n')` sinon diff massif de 10 000 lignes (payé cette
  session, corrigé). Round-trip `json.dumps(indent=2, ensure_ascii=False)` = stable.
- **Preuve de déploiement en 1 commande** : l'image du conteneur Coolify est taguée du
  SHA exact du commit déployé → `ssh serveuria 'docker ps --filter name=<uuid8>
  --format "{{.Image}}"'` et comparer à `git rev-parse HEAD`.
- **bash-guard bloque TOUT appel API Coolify multi-pipelines** même avec `jq -r .champ`
  par pipeline : une seule pipeline curl|jq à champ unique par commande, sinon passer
  par SSH/docker.
- **Agents Explore/Council passent souvent idle SANS envoyer leur rapport** : leur
  demander explicitement d'envoyer via SendMessage vers "main" dans le prompt, et les
  relancer par SendMessage s'ils sont idle sans rapport reçu.
- **ADR-002 : distinction cruciale** — interdit le mot « prédiction » et les claims de
  calibration dans le COPY COMMERCIAL ; la mesure interne (richesse finale, verdicts,
  Brier) est licite et même souhaitable (c'est elle qui produira les ≥ 20 outcomes).
- Repris des sessions précédentes, toujours valable : Vue Router résout sa navigation
  initiale dès `app.use(router)` (guard doit attendre la promesse d'init mémoïsée) ;
  valeurs d'env Coolify parfois des templates `${SERVICE_URL_*}` (vérifier la valeur
  RÉSOLUE) ; extraction de liens Supabase Auth sur le CHEMIN `/auth/v1/verify`, jamais
  le domaine ; matching d'emails de test sur le sujet EXACT (`_SUBJECT_BY_LOCALE`).
