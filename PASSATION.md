== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-16 ~22h20 (Ralph EN PAUSE sur demande Amine : 4 stories clôturées et poussées, US-221 en CHECKPOINT LOCAL NON VÉRIFIÉ — reprendre en session fraîche) ==
Synthèse complète et autonome — remplace et purge intégralement l'entrée
2026-07-16 ~21h48. Arrêt demandé explicitement par Amine (« tu es partie
trop loin, on reprend dans une session fraîche ») pendant l'exécution
d'US-221 — pas un blocage technique, une décision de gestion de session.

[ETAT]
- **`origin/main` = `c342495`** ([US-228], entièrement vérifié et poussé).
- **`main` local = `9687c99`**, **1 commit d'AVANCE sur origin, PAS POUSSÉ**
  délibérément (checkpoint WIP non gate-vérifié — ne jamais pousser un état
  non testé, convention tenue toute la session). Vérifié à l'instant par
  `git rev-list --count origin/main..HEAD` = 1.
- **`.ralph/prd.json` : 168 stories, 19 `passes=false`.** US-221 **N'EST PAS**
  marquée `passes=true` (correct — elle n'est pas terminée). Le compteur
  reflète l'état après clôture d'US-228 (dernière story réellement close).
- **`ruff check .` et `uv run mypy app/` → 0 erreur** sur l'état actuel du
  commit `9687c99` (116 fichiers) — vérifié juste avant ce commit.
  **AUCUNE suite pytest complète relancée sur cet état** — ni les tests
  unitaires d'US-221 (n'existent pas encore), ni la suite globale.
  **NE RIEN supposer sur le comportement réel avant d'avoir fait tourner
  les gates complets.**

[FAIT — cette session, dans l'ordre]
1. Gate SOP-013 levé (lexique tranché, scellement ADR-IQ-05 validé), go
   explicite Amine reçu et tracé — ordre d'exécution par graphe de
   dépendances. Détail dans `.ralph/progress.md` (ne pas reproduire ici).
2. **[US-212] Outillage qualité** — poussée (`fabe269`). ruff+mypy+eslint+CI,
   2 causes racines mypy corrigées, US-212b tracée (burn-down non bloquant).
3. **[US-223] Table simulation_prompts + PromptRegistry** — poussée
   (`1e77490`). Migration créée non jouée en prod.
4. **[US-222] Arènes requêtables + registre dynamique** — poussée
   (`482130c`). Angle mort `/start` fermé. Migration créée non jouée.
5. **[US-228] Cache Supabase ESCO** — poussée (`c342495`). Client ESCO
   cache-first, adapté du script de référence prouvé esco-role.py. Flaky
   pré-existant `test_md_hash_stable_with_deterministic_enricher` récidivé
   2x, confirmé sans lien (isolé = vert), documenté.
6. **US-221 (persistance durable, ADR-005) — DÉMARRÉE, ARRÊTÉE EN COURS
   SUR DEMANDE AMINE.** Contexte de la décision : investigation préalable a
   révélé 58 sites de lecture/écriture dispersés sans chokepoint existant +
   zéro précédent d'usage Supabase Storage dans ce projet. **AskUserQuestion
   posée à Amine** avec 4 options (scopé/complet/reporté/autre) — **réponse :
   "Complet tel quel"**, risque accepté explicitement. Travail engagé sur
   cette base, puis interrompu par Amine avant complétion — voir [CTX] pour
   le détail exact de ce qui existe et ce qui manque.

[ALERTE]
- **US-221 : ne JAMAIS marquer `passes=true` sans avoir vérifié l'AC2 à la
  lettre** (« après suppression simulée du dossier local, GET status/
  résultats/rapport fonctionnent toujours ») — ce test n'a PAS été écrit ni
  exécuté. Le mécanisme d'hydratation est câblé en LECTURE seulement ; SANS
  écriture aux checkpoints (non câblée), Storage sera TOUJOURS vide → tout
  appel à `ensure_simulation_dir_hydrated` sera un no-op silencieux (aucune
  erreur, mais aucune durabilité réelle non plus). **L'AC ne peut PAS passer
  tant que la tâche #62 (écriture checkpoints) n'est pas faite.**
- Findings hors scope signalés, toujours pas traités : 11 vulnérabilités
  `npm audit` frontend (US-212), flaky PDF pipeline récidivé 2x (US-228).
- 3 migrations créées, AUCUNE jouée en prod : `20260716_001_simulation_prompts.sql`,
  `20260716_002_enabled_platforms.sql`, `20260716_003_occupation_profiles.sql`
  (poussées, donc dans le repo distant). `20260716_004_simulation_artifacts.sql`
  (bucket Storage + table) existe seulement en LOCAL (commit non poussé).
  **Amine doit toutes les jouer via le SQL Editor Supabase avant qu'elles
  n'existent réellement en base** — le code applicatif ne casse jamais en
  leur absence (fallback silencieux systématique, comportement identique à
  avant chaque story tant que non jouées).
- Héritées, non retouchées : finding Stripe live checkout, dette 27 tests
  E2E, 2 emails de test résiduels, rotation `NAHJ_SUPABASE_POSTGRES_DB`.

[BLOQUE / EN ATTENTE]
- **Rien n'est bloqué par une décision** — c'est un arrêt de session
  volontaire. US-221 attend une session fraîche pour reprendre le travail
  restant (liste précise en [NEXT]).

[NEXT]
**Reprendre US-221 exactement où elle s'est arrêtée — ordre recommandé :**
1. **Relire ce PASSATION.md + `.ralph/progress.md` + `git show 9687c99 --stat`**
   pour voir précisément le diff du commit WIP avant de continuer dessus.
2. **Task #62** (tracker interne, à recréer si perdu) : câbler
   `artifact_storage.sync_directory_to_storage(simulation_id, sim_dir)` aux
   points de contrôle : fin de `SimulationManager.prepare_simulation()`, fin
   de run (`SimulationRunner.stop_simulation` ou détection de complétion),
   fin de génération de rapport. SANS ce câblage, l'hydratation en lecture
   est un no-op — l'AC ne peut pas être vérifiée avant.
3. **Vérifier `quote_admin_service.py`/`quote_service.py`** : investigation
   de cette session a déjà conclu que ce sont des FAUX POSITIFS (ils
   dérivent juste un chemin `quotes/` sibling de `simulations/`, aucune
   lecture d'artefact de simulation) — ne pas les retoucher sauf nouvelle
   preuve contraire. **`webhook_service.py:422` n'a PAS été vérifié** — à
   faire.
4. **Task #64** : tests unitaires `artifact_storage.py` (upload, download,
   hydratation, fallback Supabase indisponible — même patron que
   `test_unit_prompt_registry.py`/`test_unit_esco_client.py`, déjà 2 fois
   éprouvé cette session) + test bout-en-bout simulant la suppression du
   dossier local (AC2 explicite de la story).
5. Relancer `ruff check .` + `uv run mypy app/` + suite pytest complète.
   Si vert : commit `[US-221] ...` (remplace ou vient après le WIP —
   décision libre : `git commit --amend` sur le WIP local puisqu'il n'est
   PAS poussé, ou nouveau commit par-dessus), push, marquer `passes: true`
   dans `prd.json`, logger dans `progress.md`.
6. Puis **US-224** (renommage « arène de convictions », quick win isolé,
   zéro dépendance) ferme le Lot 0.
7. Lot 1 : US-231, US-233, US-232, US-225, US-229, US-230, US-235 (ordre
   détaillé et déjà justifié dans `.ralph/progress.md`).

[CTX]
- **Détail exact du commit WIP `9687c99`** (`git show 9687c99 --stat` pour
  la liste précise) :
  - `backend/app/services/artifact_storage.py` (NEUF) : module complet —
    `sync_directory_to_storage()`, `ensure_simulation_dir_hydrated()`,
    `is_durably_persisted()`, `_list_artifacts()`. Design "hydratation de
    répertoire" (pas fichier par fichier) : la table `simulation_artifacts`
    indexe quels fichiers existent durablement, le bucket Storage privé
    `simulation-artifacts` porte le binaire. Fallback silencieux total
    (jamais d'exception).
  - `supabase/migrations/20260716_004_simulation_artifacts.sql` (NEUVE) :
    `insert into storage.buckets` (bucket privé) + table
    `simulation_artifacts` + RLS `is_super_admin()`.
  - **Hydratation câblée en LECTURE** (via `ensure_simulation_dir_hydrated`,
    appelé juste après construction de `sim_dir`, AVANT tout accès fichier) :
    - `app/api/simulation.py` : ~27 sites (25 mécaniques + 2 f-string + 3
      raffinements resolution.json/quality.json/trajectory.json). **2 sites
      DÉLIBÉRÉMENT exclus** : share-cards et replay-gifs (caches régénérables
      à la demande, hors scope ADR-005 — décision documentée dans le code).
    - `app/services/simulation_manager.py` : `_load_simulation_state()`
      (chokepoint central — couvre `get_simulation`, `get_profiles`, le
      fork lineage via `_load_simulation_state(parent_simulation_id)`) +
      `get_simulation_config()`. **`_get_simulation_dir()` elle-même N'A PAS
      été touchée** (contrat documenté US-051 : doit rester pure, sans effet
      de bord, quand `create=False`) — hydratation câblée UN NIVEAU AU-DESSUS,
      dans les méthodes qui lisent réellement.
    - `app/services/graph_tools.py` : 2 sites (`_load_agent_profiles`,
      calcul dominant_platform).
    - `app/services/report_pdf/loader.py` : `PDFContextLoader.load()` —
      LE chokepoint de génération de rapport/PDF (couvre l'AC "rapport").
    - `app/api/observability.py` : 3 sites non-streaming (events paginés,
      stats, llm-calls). Le tailer SSE live (`/events/stream`) délibérément
      NON câblé — c'est du direct streaming d'un run actif, pas un artefact
      post-hoc (décision documentée dans le raisonnement de session, pas
      encore dans un commentaire code).
    - `app/api/calibration.py` : 2 sites (boucle sur toutes les sims
      publiques pour le calcul Brier).
  - **PAS câblé du tout** : l'écriture (`sync_directory_to_storage` n'est
    appelée NULLE PART dans le code applicatif à ce stade — seulement
    définie dans le module). C'est la tâche la plus importante restante.
  - **`app/services/simulation_runner.py`** : quasi pas concerné (1 seule
    occurrence, définition de constante) — probablement pas besoin
    d'hydratation propre, à confirmer en relisant le fichier.
  - **Scripts subprocess** (`scripts/run_twitter_simulation.py`,
    `run_reddit_simulation.py`, `run_parallel_simulation.py`, 8 occurrences
    au total) : **PAS DU TOUT regardés cette session** — ce sont des
    process séparés qui écrivent `actions.jsonl` en continu pendant un run
    actif ; la stratégie prévue (sync en fin de run, pas en temps réel) n'a
    pas encore été conçue en détail pour ces scripts.
- Spec : `docs/superpowers/specs/2026-07-16-simulations-v2-design.md`.
  ADR-005 (persistance) référencée dans le CLAUDE.md racine, pas un ADR
  numéroté séparé dans `08-decisions-log.md` — à vérifier/créer si besoin
  en clôturant US-221.
- Config qualité (US-212) : `backend/pyproject.toml`,
  `frontend/eslint.config.js`, `package.json` racine.
- App Coolify miroshark : uuid `u6pn5mr2pgi88s13un55pkzb` ; prod bassira.ma.

[MEMO inter-sessions]
- **`.ralph/prd.json` est en CRLF** : `open(..., 'w', newline='\r\n')`.
- **US-221 = la story la plus lourde du chantier (8h estimées, la plus
  grosse) — c'est normal qu'elle dépasse une session.** Pas un signe
  d'échec, juste un signe qu'il fallait la découper. Pour toute future
  story de cette ampleur : proposer explicitement de la scinder en
  sous-stories AVANT de commencer à coder (comme US-212b l'a fait a
  posteriori pour le mypy burn-down), plutôt que de découvrir l'ampleur en
  cours de route.
- **Avant de commiter un état non entièrement vérifié** : le committer
  quand même EN LOCAL (ne jamais perdre de travail), mais **ne JAMAIS
  pousser tant que les gates complets (ruff+mypy+pytest complet) n'ont pas
  tourné** — convention tenue cette session (`9687c99` local seulement).
- **Root-cause fixes avant grinding ligne à ligne** (payé sur US-212).
- **Scope de linter/story jamais lancé = décision de proportionnalité
  assumable, documentée, jamais un blanc-seing pour une dette invisible.**
- Preuve de déploiement : `ssh serveuria 'docker ps --filter name=<uuid8>
  --format "{{.Image}}"'` vs `git rev-parse HEAD`.
