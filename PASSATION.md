== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-16 ~21h48 (Ralph EN EXÉCUTION AUTONOME : 3 stories codées/clôturées depuis le go, 1 story en cours de finalisation — US-228, US-221 suivante) ==
Synthèse complète et autonome — remplace et purge intégralement l'entrée
2026-07-16 ~21h00. Checkpoint demandé par Amine (question directe sur la
cadence de mise à jour) pendant le loop Ralph — pas déclenché par le hook
contexte cette fois, mais à jour de la même façon.

[ETAT]
- **`main`** HEAD poussé = `482130c` ([US-222]). Historique de cette session
  (dans l'ordre) : `3105320`/`db7835c`/`5262607` (re-soumission SOP-013,
  lexique tranché, go explicite — cf. passation précédente, contenu acquis) →
  `fabe269` **[US-212]** clôturée → `1e77490` **[US-223]** clôturée →
  `482130c` **[US-222]** clôturée.
- **`.ralph/prd.json` : 168 stories, 20 `passes=false`** (dernier chiffre
  vérifié après clôture US-222 ; US-228 en cours va le faire passer à 19).
- **US-228 (cache Supabase ESCO) : code écrit, gates locaux verts, PAS
  ENCORE commitée.** État exact vérifié par `git status` à l'instant :
  3 fichiers non trackés (`backend/app/services/esco_client.py`,
  `backend/tests/test_unit_esco_client.py`,
  `supabase/migrations/20260716_003_occupation_profiles.sql`) + 1 modifié
  (`docs/02-data-dictionary.md`). `uv run pytest tests/test_unit_esco_client.py`
  → 9 passed (vérifié isolément). `ruff check .` et `uv run mypy app/` → 0
  erreur (115 fichiers). **La suite pytest COMPLÈTE (2283+ tests) est en
  cours d'exécution en fond au moment de cette passation — résultat pas
  encore confirmé.** Ne pas commit/clôturer US-228 sans avoir vu ce résultat.

[FAIT — cette session, dans l'ordre]
1. Gate SOP-013 levé (lexique tranché Variante A wargaming, scellement
   ADR-IQ-05 validé), go explicite Amine reçu et tracé, ordre d'exécution
   calculé par graphe de dépendances (in-degree des dependents) — détail
   complet dans `.ralph/progress.md` (entrée du 2026-07-16, section
   « GO EXPLICITE REÇU »), pas reproduit ici (RÈGLE N°4 : la source de
   vérité est le fichier progress.md, pas cette synthèse).
2. **[US-212] Outillage qualité** — ruff+mypy+eslint configurés et verts,
   2 causes racines mypy corrigées (annotations Blueprint app/api/__init__.py
   = 68 erreurs d'un coup ; singleton TaskManager), simulation.py et
   pdf_generation.py intégralement nettoyés. Scope mypy restant (147 erreurs/
   30 modules) exclu EXPLICITEMENT et documenté (`pyproject.toml`
   `[[tool.mypy.overrides]]`), story de suivi **US-212b** tracée (P2, non
   bloquante). CI enrichie (ruff+mypy+eslint+build), Playwright smoke
   DÉLIBÉRÉMENT absent (cible bassira.ma EN PRODUCTION, documenté). Finding
   hors scope signalé à Amine (pas traité) : 11 vulnérabilités npm audit sur
   dépendances pré-existantes (axios, vite, rollup...). pytest 2258→2258
   (0 nouveau test, story outillage pure), 0 régression.
3. **[US-223] Table simulation_prompts + PromptRegistry** — migration
   (une ligne = une version immuable, index partiel unique 1 version active
   par key+locale, RLS is_super_admin(), seed idempotent v1 =
   `arena.polymarket.system`). `PromptRegistry.get()/invalidate()` cache
   in-process, fallback silencieux (ne lève jamais). Builder Polymarket
   branché en pilote (résout via registre sinon fallback identique au
   comportement actuel). **Migration créée, PAS jouée en prod** (convention
   projet — Amine via SQL Editor Supabase, pas d'accès service_role DDL
   depuis cette session). 11 tests nouveaux, pytest 2269 passed.
4. **[US-222] Arènes requêtables + registre dynamique** — 2e plus grosse
   contrainte bloquante. `arena_registry.py` (`ARENA_STATE_FLAGS` = source
   unique) remplace l'enum en dur sur 4 sites de `simulation.py`. **Angle
   mort fermé** : `/simulation/{id}/start` refuse désormais une plateforme
   non activée (`PLATFORM_NOT_ENABLED`, 400 — avant cette story, n'importe
   quelle `platform` était acceptée sans vérifier les flags `enable_*` de la
   sim). Migration `enabled_platforms text[]` sur `simulation_ownership`
   créée, **PAS jouée en prod** (même convention). 14 tests nouveaux, pytest
   2283 passed.
5. **US-228 (cache Supabase ESCO) en cours** — voir [ETAT] pour le détail
   exact non-committé. Livré : migration `occupation_profiles` (clé de cache
   `(label, lang)` = terme de recherche normalisé, PAS le prefLabel ESCO
   canonique — choix documenté dans la migration) ; `esco_client.py`
   (`get_occupation_profile(query, lang, client=None)`, cache Supabase
   d'abord, API ESCO publique sinon via `urllib` stdlib en 2 temps — adapté
   du script de référence prouvé `~/.claude/skills/prompt-engineer-pro/
   scripts/esco-role.py`, testé OK FR/AR le 2026-07-05) ; fallback silencieux
   identique aux patterns US-223/US-222 (jamais d'exception, `None` +
   log si introuvable/injoignable). 9 tests unitaires (cache hit/miss,
   échec réseau, JSON malformé, Supabase indisponible, requête vide).
   RLS : lecture `authenticated` (données non sensibles), écriture
   `is_super_admin()`. `docs/02-data-dictionary.md` : table documentée
   (17 tables au total, compté par grep, pas de mémoire).

[ALERTE]
- **Finding hors scope US-212, toujours pas traité** : 11 vulnérabilités
  `npm audit` frontend (4 modérées, 7 hautes) sur axios/vite/rollup/
  dompurify/marked/ws/form-data/postcss/picomatch/follow-redirects/
  brace-expansion — pré-existantes. Upgrade risqué sans tests dédiés
  (blast radius large). **À trancher par Amine séparément.**
- **2 migrations créées mais PAS jouées en prod** (US-223 `simulation_prompts`,
  US-222 `enabled_platforms`) + une 3e à jouer une fois US-228 commitée
  (`occupation_profiles`) : Amine doit les exécuter via le SQL Editor
  Supabase avant qu'elles existent réellement en base. Le code applicatif
  est conçu pour ne JAMAIS casser en leur absence (fallback silencieux
  systématique) — comportement identique à aujourd'hui tant qu'elles ne sont
  pas jouées, mais les FONCTIONNALITÉS nouvelles (registre de prompts actif,
  colonne enabled_platforms requêtable, cache ESCO) ne prennent effet
  qu'après exécution manuelle.
- Héritées, toujours ouvertes (non retouchées cette session) : finding
  Stripe live checkout, dette 27 tests E2E pré-existants, flaky
  `test_md_hash_stable_with_deterministic_enricher`, 2 emails de test
  résiduels, rotation `NAHJ_SUPABASE_POSTGRES_DB` différée.

[BLOQUE / EN ATTENTE]
- **Rien n'est bloqué côté décision.** US-228 attend uniquement la
  confirmation du résultat de la suite pytest complète (mécanique, pas une
  décision) avant commit + clôture.

[NEXT]
1. **Immédiat** : lire le résultat de la suite pytest complète lancée pour
   US-228 (background task). Si verte (0 failed) → marquer `passes: true`
   dans `prd.json`, logger dans `progress.md`, commit `[US-228] ...`, push.
   Si rouge → déboguer avant tout commit (jamais de `passes: true` sur un
   gate rouge — règle absolue Ralph).
2. **US-221** (persistance durable des artefacts, ADR-005) — dernière story
   du Lot 0. Migrer les artefacts de simulation (state.json, actions.jsonl,
   polymarket_simulation.db, profils...) de `backend/uploads/` (volume
   éphémère Coolify) vers Supabase Storage + métadonnées requêtables,
   lecture rétro-compatible (fallback filesystem si pas encore migré).
3. **US-224** (renommage « arène de convictions ») — quick win isolé, zéro
   dépendance, ferme le Lot 0.
4. Puis Lot 1 : US-231, US-233, US-232, US-225, US-229, US-230, US-235 (ordre
   détaillé et déjà justifié dans `.ralph/progress.md`, ne pas recalculer).

[CTX]
- Spec : `docs/superpowers/specs/2026-07-16-simulations-v2-design.md`.
  ADR : `docs/08-decisions-log.md` ADR-015→019. Stories :
  `.ralph/prd.json` chantier `16-simulations-v2` + `V2-B-intake`.
- **Pattern établi à réutiliser pour toute nouvelle table/service** (US-223,
  US-222, US-228 en sont la preuve répétée) : fallback silencieux total
  (jamais d'exception propagée au moteur), cache in-process quand pertinent,
  RLS `is_super_admin()` en écriture + service_role backend qui contourne
  RLS de toute façon, migration créée mais jouée manuellement par Amine.
- Config qualité (US-212) : `backend/pyproject.toml`, `frontend/eslint.config.js`,
  `package.json` racine (`npm run lint`/`typecheck`), `.github/workflows/tests.yml`.
- ESCO : script de référence prouvé
  `C:\Users\amans\.claude\skills\prompt-engineer-pro\scripts\esco-role.py`
  (schéma API vérifié 2026-07-05, requête en 2 temps search→resource).
- App Coolify miroshark : uuid `u6pn5mr2pgi88s13un55pkzb` ; prod bassira.ma ;
  Supabase dédiée `db-miroshark.ai-mpower.com`.

[MEMO inter-sessions]
- **`.ralph/prd.json` est en CRLF** : toute réécriture Python DOIT utiliser
  `open(..., 'w', newline='\r\n')`.
- **Root-cause fixes avant grinding ligne à ligne** (payé sur US-212, 268→200
  erreurs mypy en 1 seul changement).
- **Cadence de mise à jour de PASSATION.md** (réponse à la question d'Amine
  ce tour) : PAS de calendrier fixe. Déclenchée par un hook quand le contexte
  restant passe sous 60 %, OU sur demande explicite/checkpoint. La vraie
  sauvegarde continue à CHAQUE story reste `.ralph/progress.md` + `prd.json`,
  commités et poussés systématiquement — si la session s'interrompt entre
  deux passations, ce sont ces deux fichiers (+ git log) qui font foi, pas
  cette synthèse.
- **Convention migrations** : créées par Ralph, jamais exécutées
  automatiquement (pas d'accès service_role DDL en local) — toujours
  signaler explicitement qu'une migration attend d'être jouée par Amine.
- Preuve de déploiement en 1 commande : `ssh serveuria 'docker ps --filter
  name=<uuid8> --format "{{.Image}}"'` vs `git rev-parse HEAD`.
