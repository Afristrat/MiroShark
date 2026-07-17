== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-17 (contexte session sous 60 % — synthèse forcée, US-224 EN COURS NON COMMITÉ) ==
Synthèse complète et autonome — remplace et purge intégralement l'entrée
2026-07-16 ~22h20 (US-221 qu'elle décrivait comme « en checkpoint » est
maintenant TERMINÉE, poussée, vérifiée — plus rien à reprendre dessus).

[ETAT]
- **`origin/main` = `main` local = `b35b8d3`** ([US-221], vérifié synchronisé
  par `git status --short --branch` juste avant cette synthèse : aucune
  divergence affichée).
- **16 fichiers modifiés EN LOCAL, NON COMMITÉS, NON POUSSÉS** (story US-224
  en cours, code complet mais gate pytest pas encore confirmé) :
  `frontend/src/locales/{fr,en,ar}.json`, 8 templates
  `backend/app/templates/pdf_report/**/*.j2`
  (`00_cover`, `01_exec_summary`, `02_toc`, `05_verdict`, `06_recommendations`,
  `_method_limits`, `exec/_main`, `one-pager/_main`, `public/_main`), 4
  composants Vue (`HistoryDatabase.vue`, `Step4Report.vue`,
  `ComparisonView.vue`, `EmbedView.vue`).
- **`npm run build` → exit 0, vérifié** (build complet, warnings de taille de
  chunk pré-existants uniquement, sans lien).
- **`uv run pytest -m "not integration"` → LANCÉ EN ARRIÈRE-PLAN, RÉSULTAT
  INCONNU au moment d'écrire cette synthèse** (contexte tombé sous 60 % avant
  la fin du run, ~7 min habituellement). **NE RIEN supposer sur le résultat.**
  Fichier de sortie : `/tmp/pytest_us224.txt` (sur CE poste Windows — n'existe
  plus si nouvelle session/machine ; relancer si besoin).
- **`.ralph/prd.json` : US-221 passes=true (poussée). US-224 toujours
  passes=false** (le tracker de tâches interne montre #41/#60-64 completed,
  #42 US-224 encore pending — cohérent avec le code non commité).
- Ruff + mypy : 0 erreur sur l'état d'avant US-224 (vérifiés lors de la
  clôture d'US-221) — **PAS re-vérifiés sur les fichiers modifiés par
  US-224** (aucun fichier `.py` backend touché par US-224, seulement des
  `.j2`/`.vue`/`.json` — donc ruff/mypy ne sont normalement pas concernés,
  mais ce n'est pas re-confirmé explicitement).

[FAIT — cette session, dans l'ordre]
1. **Migrations US-222/223/228/221 jouées et vérifiées en prod** (les 4
   fichiers `supabase/migrations/20260716_00{1,2,3,4}_*.sql`, poussés mais
   jamais exécutés jusqu'ici). Conteneur ciblé par UUID exact
   (`supabase-db-dgybi9q5e2ggkjtaxlu2ukai`, labels Coolify
   `projectName: miroshark` vérifiés avant exécution — après un incident de
   ciblage trop large, cf. [ALERTE]). Vérification fraîche indépendante
   (`information_schema` + `storage.buckets`) : les 3 tables + colonne +
   bucket sont bien présents. App prod confirmée tourner exactement sur le
   commit contenant ce code. `prd.json`/`progress.md`/`docs/02-data-dictionary.md`
   mis à jour en conséquence (table `simulation_artifacts` documentée,
   compteur RLS 17→18).
2. **[US-221] Persistance durable des artefacts — CLÔTURÉE, poussée
   (`b35b8d3`)**. Écriture câblée à 3 checkpoints (fin prepare, fin run, fin
   rapport), tous en thread d'arrière-plan (jamais le thread HTTP). Gap réel
   trouvé et fermé : `SimulationRunner.start_simulation` ne rematérialisait
   jamais le dossier local si le volume Coolify avait été vidé entre
   `/prepare` et `/start`. 17 tests nouveaux dont un round-trip complet
   (sync → suppression réelle du dossier local → hydratation → contenu
   identique) qui prouve l'AC2. Suite complète à ce moment-là : 2309 passed,
   0 failed. Détail exhaustif dans `.ralph/progress.md` (entrée
   2026-07-17 — US-221 Persistance durable des artefacts CLÔTURÉE).
3. **[US-224] Renommage « arène de convictions » (ADR-018) — CODE COMPLET,
   PAS COMMITÉ, PAS VÉRIFIÉ PYTEST.** Story estimée 2h, réalité beaucoup plus
   grande (même leçon qu'US-221 cette session — aurait dû être scindée à
   l'écriture). Détail dans [CTX].

[ALERTE]
- **NE PAS marquer US-224 `passes: true` avant d'avoir VU le résultat du
  pytest en cours** (fichier `/tmp/pytest_us224.txt`, ou relancer
  `cd backend && uv run pytest -m "not integration" --tb=short -q`). Risque
  concret identifié mais NON vérifié : les tests
  `test_pdf_visual_regression.py`, `test_md_templates.py`,
  `test_pdf_context_schema.py`, `test_unit_report_agent_narrative.py`
  référencent tous "Verdict"/"Confiance" (trouvé par grep avant de lancer le
  run) — certains pourraient asserter du texte littéral qui vient de changer
  dans les templates `.j2` (ex. "Verdict" → "Issue", "Confiance" →
  "Convergence"). **Si des tests échouent dessus : ce sont des snapshots/
  assertions à mettre à jour pour refléter le nouveau vocabulaire, PAS une
  régression fonctionnelle** — mais à vérifier au cas par cas, ne pas
  supposer.
- **Rien n'est commité ni poussé pour US-224.** Si une session future
  reprend sans lire ceci, `git status --short` révèle immédiatement les 16
  fichiers modifiés — ne pas les écraser, c'est le travail de cette session.
- Incident secrets (2026-07-16 tard) : sentinelle a flaggé
  `NAHJ_SUPABASE_POSTGRES_DB` (secret d'un AUTRE projet, Nahda) 5 fois de
  suite pendant les commandes SSH de migration — faux positif quasi certain
  sur la chaîne générique `postgres`. Amine a tranché : pas de rotation.
  Documenté en mémoire Claude Code (`incident_nahda_secret_leak_20260716`),
  pas d'action requise ici.
- Findings hors scope hérités, toujours pas traités : 11 vulnérabilités
  `npm audit` frontend (US-212), flaky PDF pipeline
  (`test_md_hash_stable_with_deterministic_enricher`, isolé = toujours vert,
  confirmé sans lien avec US-221/224 ce jour encore).
- **Dette i18n pré-existante découverte, VOLONTAIREMENT PAS corrigée** (hors
  scope US-224, bien plus grosse) : `frontend/src/components/HistoryDatabase.vue`,
  section « Resolve Prediction Section » (~lignes 326-378) — environ 15
  chaînes anglaises codées en dur (jamais `$t()`), ex. « Did the simulation
  correctly predict what happened? », « Record Outcome », « YES — It
  happened », etc. Seule la chaîne contenant littéralement le mot interdit
  (« Prediction Outcome » → « Real-World Outcome ») a été corrigée pour
  satisfaire l'AC d'US-224. Le reste est une dette i18n séparée, à traiter
  dans une story dédiée si Amine le juge prioritaire.

[BLOQUE / EN ATTENTE]
- Rien n'est bloqué par une décision technique. Le seul blocage est
  d'ordre contextuel (fin de session forcée par le budget de contexte,
  pas un problème de code).

[NEXT]
**Reprendre exactement ici, dans l'ordre :**
1. Vérifier le résultat du pytest lancé en fin de session précédente : lire
   `/tmp/pytest_us224.txt` s'il existe encore, sinon relancer
   `cd backend && uv run pytest -m "not integration" --tb=short -q`.
2. Si des échecs touchent des templates/tests PDF référençant
   "Verdict"/"Confiance" : lire le diff exact, corriger le test ou le
   snapshot pour refléter "Issue"/"Convergence" (nouveau vocabulaire
   ADR-018) — PAS revenir en arrière sur le renommage.
3. Si tout est vert : `git add` les 16 fichiers listés en [ETAT], commit
   `[US-224] Renommage « arène de convictions » (ADR-018)` (format standard
   AGENTS.md), push sur `main`.
4. Marquer `US-224` `passes: true` dans `.ralph/prd.json` (+ `completedAt`,
   `files_touched`, note résumant le périmètre réel — bien plus large que
   l'estimation initiale, cf. [CTX]) et logger l'itération dans
   `.ralph/progress.md`.
5. Puis Lot 1 : US-231, US-233, US-232, US-225, US-229, US-230, US-235
   (ordre déjà justifié dans `.ralph/progress.md`, section US-221 du
   2026-07-16 ~22h20 — toujours valable).

[CTX]
- **Portée réelle d'US-224** (bien au-delà de `_method_limits.md.j2` +
  quelques clés UI mentionnées dans l'AC d'origine) :
  - **Renommage cœur** : « marché de prédiction »/« prediction market »/
    « سوق تنبؤ » → « arène de convictions »/« conviction arena »/
    « ساحة القناعات » ; marchés individuels → « questions »/« question(s) »/
    « سؤال/أسئلة ». Couvre `_method_limits.md.j2` (3 langues), libellés
    polymarket (`predictionMarkets`, `marketCountTitle`, `marketSingular/
    Plural`, `markets`, `marketsTitle`, `polymarket.title/subtitle`,
    `MARKET_NOT_FOUND`), hero desc (`home.hero.desc`), label nav
    `verified` (« Prédictions vérifiées »/« Verified predictions » — présent
    en FR **ET** EN, pas seulement AR — un premier grep shell avait raté les
    caractères accentués français, corrigé par une méthode Python UTF-8
    robuste).
  - **Halo lexical ADR-018** (oracle→adjudication, verdict→issue,
    dénouement→clôture, confiance→degré de convergence, Delphi→lecture
    croisée) : appliqué sur ~10 templates PDF (`Outcome.verdict`/
    `Outcome.confidence`/`KpiHero.confidence_pct` — labels renommés, PAS les
    noms de champs Pydantic eux-mêmes, techniques) et sur les puces
    marketing des 6 packages `/offres` (PMF Discovery, Crisis Drill,
    Adcheck Lite/Pro, Product Launch, Policy Stress Test — "Verdict:
    viable/borderline/nope" etc, dans les 3 langues).
  - **Dérive arabe indépendante corrigée** (bug de parité pré-existant,
    hors ADR-018 mais découvert et réparé au passage, US-217) : plusieurs
    endroits où l'arabe disait « تنبؤ » alors que le FR/EN ne l'avaient
    JAMAIS dit (`promptPlaceholder` l.183, package Crisis Watch l.1669/1675,
    description Cohort Replay l.1647, `called_it` l.2447).
  - **4 bugs de texte codé en dur trouvés et corrigés** (violaient l'AC ET
    la règle i18n globale du projet) dans des composants Vue, hors des
    fichiers de locale : `HistoryDatabase.vue` (« Prediction Outcome » →
    « Real-World Outcome »), `ComparisonView.vue` (« Prediction Market Final
    Prices » → « Conviction Arena Final Prices »), `Step4Report.vue`
    (« Prediction Scenario: » → « Scenario: » — **attention**, la regex de
    parsing `Step4Report.vue:726` (`/Prediction\s*(?:scenario|Scenario):/`)
    n'a PAS été touchée intentionnellement : elle parse un texte source
    différent, techniquement interne, jamais affiché tel quel au client),
    `EmbedView.vue` (« Prédiction correcte/manquée » → « Résolution
    exacte/manquée »).
- **2 arbitrages Amine obtenus cette session** :
  1. Slogan anti-prédiction (« Ce que Bassira ne fait pas », item n°1,
     contexte de NÉGATION, ADR-002/US-201) : reformulé plutôt que laissé tel
     quel — `n1t` : FR « Annoncer l'avenir », EN « Announce the future », AR
     « الإعلان عن المستقبل ». Corps (`n1b`) inchangé (ne contenait déjà pas
     le mot interdit).
  2. Placeholder i18n `{verdict}` dans `subCompleted` (fr/en.json l.474) :
     Amine avait validé le renommer en `{issue}` (+ toucher le composant
     Vue `TopicResearchPanel.vue`) sur la base de mon cadrage initial —
     **cadrage qui s'est révélé FAUX après vérification du code** : ce
     placeholder vient de `research.verdict.{pass,warn,deepen,fail}`, le
     statut d'un outil de recherche/audit interne SANS RAPPORT avec le
     verdict de simulation ADR-018. **PAS touché**, décision corrigée et
     signalée à Amine dans la conversation — ne pas revenir dessus sans
     nouvelle preuve contraire.
- Exclusions techniques confirmées et volontairement NON touchées (vocabulaire
  interne, conforme à la clause ADR-018 « le vocabulaire technique interne ne
  change pas ») : `FeedOracle`/`ORACLE_SEED_ENABLED` (outil externe sans
  rapport), `arbiter`/« الحَكَم » (archétype de persona, pas l'oracle),
  `sortConfidence` (confiance d'extraction d'entité de graphe, domaine
  différent), noms de clés JSON i18n (`predictionMarkets` etc. — seules les
  VALEURS ont changé, jamais les clés, pour ne pas casser les références
  `$t('...')` dans les `.vue`), noms de champs Pydantic (`Outcome.verdict`,
  `.confidence`) et classes CSS (`.one-pager-verdict`).
- Balayage final effectué et documenté (zéro occurrence résiduelle hors
  exclusions ci-dessus) : `fr.json`, `en.json`, `ar.json` (recherche
  Python UTF-8 robuste, diacritiques arabes ignorées), les 8 templates PDF
  modifiés, et tout `frontend/src/**/*.vue` (recherche séparée qui a trouvé
  les 4 bugs codés en dur). **PAS re-balayé après les 4 fixes Vue** — à
  refaire en 30 secondes avant de commit si doute (script Python déjà
  écrit dans cette session, reproductible).

[MEMO inter-sessions]
- **`.ralph/prd.json` est en CRLF** : `open(..., 'w', newline='\r\n')`.
- **Pour toute story dont l'AC contient un grep de vérification
  (« zéro occurrence de X ») : ne JAMAIS faire confiance à un premier grep
  shell avec des caractères accentués/arabes** — vérifié deux fois cette
  session que `grep -i` avec classes de caractères accentuées (`[ée]`) peut
  rater des occurrences selon l'encodage du shell. Toujours re-vérifier avec
  un script Python UTF-8 direct (`io.open(..., encoding='utf-8')` +
  `.lower()` + `in`) avant de déclarer un grep-AC satisfait.
- **Piège heredoc Python découvert cette session** : taper des caractères
  typographiques français (espace insécable avant `h`/`%`, apostrophes
  courbes) directement dans un heredoc Bash peut introduire des octets
  différents de ceux réellement présents dans le fichier cible → échec de
  `content.count(old)` malgré une apparence identique à l'œil. Pour des
  remplacements de texte français/arabe complexes (guillemets imbriqués
  multiples), préférer Read+Edit (fiable, zéro échec cette session) à un
  script Python heredoc dès que la chaîne dépasse ~2 niveaux de guillemets
  imbriqués.
- **Avant de commiter un état non entièrement vérifié** : le committer
  quand même EN LOCAL si le travail est fait (ne jamais perdre de travail),
  mais ne JAMAIS pousser tant que les gates complets n'ont pas tourné —
  convention tenue toute la session précédente sur US-221, **PAS ENCORE
  appliquée à US-224** (rien n'est même committé localement à ce stade,
  contrairement à US-221 qui avait un commit WIP local) — à faire au tout
  début de la prochaine session, avant même de relancer pytest, pour ne pas
  perdre les 16 fichiers modifiés en cas d'incident.
- Preuve de déploiement : `ssh serveuria 'docker ps --filter name=<uuid8>
  --format "{{.Image}}"'` vs `git rev-parse HEAD`.
- App Coolify miroshark : uuid `u6pn5mr2pgi88s13un55pkzb` ; prod bassira.ma.
