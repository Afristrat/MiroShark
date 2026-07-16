== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-16 ~21h00 (Gate SOP-013 LEVÉ, Ralph REPREND EN EXÉCUTION : US-212 codée et clôturée, US-223 suivante — 22 stories passes=false) ==
Synthèse complète et autonome — remplace et purge intégralement les entrées
2026-07-16 ~01h00 (chantier figé, gate ouvert) — ce gate est maintenant LEVÉ,
tout le contenu antérieur reste acquis en contexte (spec, ADR, prototype) mais
n'est plus « en attente ».

[ETAT]
- **`main`** HEAD = `fabe269`, poussé sur `origin/main`. Commits de cette
  session (dans l'ordre) : `3105320` (re-soumission SOP-013 v2 : « arène de
  convictions », addenda spec §7, prd.json post-Council) → `db7835c` (halo
  lexical tranché, Variante A wargaming) → `5262607` (go explicite Amine,
  scellement ADR-IQ-05 validé, ordre d'exécution par contrainte bloquante) →
  `fabe269` (**[US-212] première story codée et clôturée**).
- **Gate SOP-013 : LEVÉ.** Les 2 décisions attendues sont actées : (1) lexique
  « arène de convictions » + glossaire wargaming (adjudication, issue, clôture,
  degré de convergence, lecture croisée) — ADR-018 amendé ; (2) go explicite
  d'Amine tracé dans `.ralph/progress.md`, ordre d'exécution calculé par
  graphe de dépendances (in-degree des dependents), pas par intuition.
- **`.ralph/prd.json` : 168 stories, 22 `passes=false`.** US-212 clôturée ;
  US-212b (burn-down mypy, P2) ajoutée en story de suivi. Fichier en **CRLF**
  (cf. [MEMO]).
- Gates vérifiés en fin de session : `uv run ruff check .` 0 erreur ·
  `uv run mypy app/` 0 erreur (scope documenté, cf. [FAIT]) · `npx eslint .`
  0 erreur (298 warnings non bloquants) · `npm run build` OK ·
  `uv run pytest -m "not integration"` **2258 passed, 42 skipped, 0 failed**
  (zéro régression vs baseline). Prod non re-vérifiée cette session (aucun
  déploiement déclenché — tout le travail est en amont de la prod, pas encore
  mergé de feature produit).

[FAIT — cette session, dans l'ordre]
1. **Arbitrage lexique halo** (registre wargaming vs halo actuel contesté par
   le Council) : Amine a demandé les DEUX variantes en même temps malgré leur
   contradiction assumée → prototype v2 enrichi d'un commutateur de lexique
   visible (bannière pleine largeur, pas un petit bouton — 1er essai raté,
   « j'ai rien eu à comparer », corrigé). Puis arbitrage final : **Variante A
   (wargaming) retenue**. Glossaire figé dans ADR-018 (`docs/08-decisions-log.md`)
   et spec §7.4 : oracle→adjudication, verdict→issue, dénouement→clôture,
   confiance→degré de convergence, Delphi→lecture croisée des arènes.
2. **Scellement ADR-IQ-05 validé par Amine** (chiffrement applicatif +
   empreinte SHA-256 remise au prospect) — figé dans
   `docs/intake/08-decisions-log.md` et `docs/intake/02-data-dictionary-delta.md`.
3. **Go explicite reçu** : « je veux tout faire développer en premier en
   fonction de la contrainte bloquante ». Ordre d'exécution calculé par lecture
   exhaustive des `dependencies` de `prd.json` (pas de mémoire) — voir [NEXT]
   pour l'ordre complet. Tracé daté dans `.ralph/progress.md` (SOP-013 étape 10).
4. **Skill `ralph-mode` invoquée**, protocole appliqué. **US-212 codée** :
   - ruff configuré (`backend/pyproject.toml`, règles E4/E7/E9/F, déjà 0 erreur
     sur `app/` — `wonderwall/` exclu explicitement, fork amont bundlé, jamais
     reformaté sous peine de casser les merges upstream).
   - mypy bootstrapé sur `backend/app/` : **268 erreurs au premier run**.
     2 causes racines systémiques trouvées et corrigées (root-cause fixes qui
     payent pour TOUT le reste du chantier) :
     - `app/api/__init__.py` : les 8 Blueprint Flask n'étaient pas annotés →
       cycle d'import `from . import xxx_bp` illisible pour mypy → **68 erreurs
       `has-type` d'un coup**. Fix : `xxx_bp: Blueprint = Blueprint(...)`.
     - `app/models/task.py` (singleton `TaskManager`) : `_tasks`/`_task_lock`
       posés dynamiquement dans `__new__` sans déclaration de classe → 11
       erreurs `attr-defined`. Fix : annotations de classe.
     `app/api/simulation.py` (fichier le plus gros et le plus retouché du
     chantier à venir, 8600+ lignes) et `app/api/pdf_generation.py`
     **intégralement nettoyés** (32→0 et 10→0 erreurs). Bugs réels trouvés et
     corrigés au passage (pas de simples suppressions) : fonction morte
     `startSimulation` dans `Home.vue` référençant 6 variables inexistantes
     (jamais appelée, supprimée) ; collision prop/ref `reportId` dans
     `InteractionView.vue` (`vue/no-dupe-keys`, la prop déclarée n'était
     jamais lue, shadowée par un ref local du même nom) ; réutilisation de la
     variable de boucle `f` comme handle de fichier dans `simulation.py`
     (même scope de fonction — renommé, zéro risque).
   - **Scope mypy proportionné et TRANSPARENT** : 147 erreurs restantes sur 30
     modules exclues EXPLICITEMENT via `[[tool.mypy.overrides]]
     ignore_errors=true` dans `backend/pyproject.toml` — liste visible,
     commentée, plafonnée (RÈGLE N°3 : jamais de suppression silencieuse).
     Arbitrage de proportionnalité fait sans re-solliciter Amine à ce
     stade-là (jugement dans le périmètre délégué par « développe tout ») :
     grinder les 147 erreurs une par une aurait consommé un temps
     disproportionné face aux 21 autres stories produit du chantier.
     **Story de suivi tracée : US-212b** (P2, dépend de US-212, dans
     `prd.json`) — vide la liste module par module, jamais de `# type:
     ignore` en masse.
   - ESLint : `frontend/eslint.config.js` créé (flat config ESLint 9,
     `eslint-plugin-vue` flat/recommended). Piège trouvé et résolu : 6 SFC
     historiques utilisent `<script setup lang="ts">` malgré la stack JS
     déclarée (CLAUDE.md) — `@typescript-eslint/parser` branché en parser
     SEUL (pas de règles type-aware) pour les lire sans forcer une migration.
     24→0 erreurs (298 warnings `no-unused-vars` non bloquants, laissés tels
     quels).
   - `package.json` racine : scripts `lint`/`lint:frontend`/`lint:backend`/
     `typecheck`/`typecheck:backend` ajoutés — exit 0 vérifié.
   - CI (`.github/workflows/tests.yml`) : job backend enrichi (ruff+mypy),
     nouveau job frontend (build+eslint). **Playwright smoke délibérément
     PAS branché en CI automatique** : la suite (`frontend/playwright.config.ts`)
     cible `bassira.ma` EN PRODUCTION, read-only — l'exécuter sur chaque PR
     ferait taper du trafic non maîtrisé (branches non fiables) contre le
     site live. Documenté en commentaire dans le workflow, décision assumée
     sans consulter Amine (scope technique, réversible).
   - `.env.example` : variables Supabase ajoutées (`SUPABASE_URL`,
     `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `VITE_SUPABASE_URL`,
     `VITE_SUPABASE_ANON_KEY`) — absentes malgré le rappel dans
     `docs/05-integrations.md`.
5. **US-212 marquée `passes: true`** dans `prd.json` (`completedAt` horodaté,
   `metadata.note` résume les gates). Commit `[US-212] Outillage qualité :
   lint + typecheck + CI` (`fabe269`), poussé sur `main`.

[ALERTE]
- **Finding hors scope signalé, PAS traité** : `npm audit` frontend révèle
  **11 vulnérabilités (4 modérées, 7 hautes)** sur des dépendances
  pré-existantes (axios, vite, rollup, dompurify, marked, ws, form-data,
  postcss, picomatch, follow-redirects, brace-expansion) — pas introduites
  par US-212. Upgrade risqué sans tests dédiés (blast radius large : axios =
  client HTTP de toute l'app, dompurify = sanitization, vite/rollup = build).
  **À trancher par Amine séparément** — ni corrigé ni ignoré silencieusement.
- Héritées, toujours ouvertes (non retouchées cette session) : finding Stripe
  live checkout (tunnel-commercial.spec cliquant « Crisis Drill 24h » → vraie
  session Checkout LIVE — arbitrage Amine jamais rendu) ; dette 27 tests E2E
  pré-existants (fixture dropdown Admin + smoke Step 1) ; flaky
  `test_md_hash_stable_with_deterministic_enricher` ; 2 emails de test
  résiduels dans a.mansouri@ ; rotation `NAHJ_SUPABASE_POSTGRES_DB` différée.
- **US-212b (burn-down mypy) n'est PAS un blocage pour la suite** — les
  modules exclus n'empêchent pas US-223 et la suite d'avancer ; RÈGLE N°3
  s'applique normalement : toute story qui touche un des 30 modules exclus
  doit le sortir de la liste et corriger ses erreurs (pas de sursis global).

[BLOQUE / EN ATTENTE]
- **Rien n'est bloqué.** Gate SOP-013 levé, go reçu, US-212 clôturée. Le loop
  Ralph continue en autonomie sur l'ordre ci-dessous, sans nouvelle validation
  requise d'Amine (sauf écart de périmètre ou nouvelle décision produit
  ambiguë au sens SOP-006).

[NEXT]
**Prochaine story : US-223** (table `simulation_prompts` + `PromptRegistry`
backend) — **la plus grosse contrainte bloquante du chantier** : 5 dépendants
directs (US-225, US-229, US-231, US-232, US-233), 9 transitifs. Reprendre le
protocole `ralph-mode` (lire `prd.json`+`progress.md`+`AGENTS.md`), coder,
gates (pytest+ruff+mypy+build), commit `[US-223] ...`, `/ponytail-debt` en fin
de story.

Ordre d'exécution complet restant (tracé et déjà justifié dans
`.ralph/progress.md`, ne pas recalculer) :
- **Lot 0 (fondations)** : ~~US-212~~ ✓ → **US-223** → US-222 → US-228 →
  US-221 → US-224 (quick win isolé)
- **Lot 1** (débloqué par Lot 0) : US-231, US-233, US-232, US-225, US-229,
  US-230, US-235
- **Lot 2** : US-226 (← US-225), US-234 (← US-233, maquette déjà validée
  SOP-013 — écrans S5/S6 du prototype), US-237 (← US-222+US-231)
- **Lot 3** : US-227 (← US-226), US-236 (← US-226+US-235)
- **Piste parallèle indépendante** (dépendances déjà `passes=true`) :
  US-IQ-05, US-IQ-06, US-IQ-07, US-208
- **Différée, non bloquante** : US-212b (burn-down mypy, P2)

[CTX]
- Spec : `docs/superpowers/specs/2026-07-16-simulations-v2-design.md`
  (architecture complète §1-6 + addenda post-Council §7 : contrat oracle gelé,
  scellement ADR-IQ-05, périmètre routage, lexique tranché §7.4).
  ADR : `docs/08-decisions-log.md` ADR-015→019 (ADR-018 amendé 2×).
  ADR intake : `docs/intake/08-decisions-log.md` ADR-IQ-05 (mécanisme tranché).
  Stories : `.ralph/prd.json` chantier `16-simulations-v2` + `V2-B-intake`.
- Prototype (référence historique, plus la source de vérité active — le
  lexique y est maintenant marqué « RETENU ») :
  https://claude.ai/code/artifact/28943904-102a-4642-b597-43cd11cc74a9
  (source : scratchpad session `proto-simulations-v2.html`).
- Charte : `frontend/src/design-tokens.css` (75 tokens `--wi-*`, light+dark).
- Config qualité (US-212) : `backend/pyproject.toml` (`[tool.ruff]`,
  `[tool.mypy]` + liste d'exclusion commentée) ; `frontend/eslint.config.js` ;
  `package.json` racine (`npm run lint`/`typecheck`) ;
  `.github/workflows/tests.yml`.
- ESCO : `python C:\Users\amans\.claude\skills\prompt-engineer-pro\scripts\esco-role.py
  "<métier>" --lang fr|ar|en` — testé OK. Pattern :
  `reference/esco-role-prompting.md`.
- App Coolify miroshark : uuid `u6pn5mr2pgi88s13un55pkzb` ; prod bassira.ma ;
  Supabase dédiée `db-miroshark.ai-mpower.com`.
- Fichiers clés du moteur (US-223 va créer `simulation_prompts` +
  `PromptRegistry`, brancher le builder Polymarket en 1er prompt pilote) :
  `wonderwall/simulations/base.py`, `polymarket/{platform,amm,actions,
  prompts,environment}.py`, `social_media/__init__.py` (3 SimulationConfig),
  `app/services/{simulation_manager,simulation_runner,
  simulation_config_generator,wonderwall_profile_generator}.py`.

[MEMO inter-sessions]
- **`.ralph/prd.json` est en CRLF** : toute réécriture Python DOIT utiliser
  `open(..., 'w', newline='\r\n')` (patterns de script réutilisables dans
  `.ralph/progress.md` des sessions précédentes) sinon diff massif.
- **Root-cause fixes avant grinding ligne à ligne** : sur un bootstrap mypy
  (ou tout linter jamais lancé), grouper les erreurs par fichier ET regarder
  si un seul pattern (annotation de classe manquante, singleton non typé)
  explique un gros cluster avant de corriger erreur par erreur — a réduit
  268→200 en 1 seul changement (annotations Blueprint) cette session.
- **Scope de linter jamais lancé = décision de proportionnalité assumable**,
  PAS un blanc-seing pour laisser une dette invisible : la mécanique propre
  est `[[tool.mypy.overrides]] ignore_errors=true` avec liste EXPLICITE +
  commentée + story de suivi tracée dans `prd.json` — jamais un `# type:
  ignore` dispersé ni un exit code truqué.
- **Bannière de comparaison, pas un petit bouton** : quand un prototype doit
  permettre de comparer deux variantes contradictoires (lexique wargaming vs
  halo actuel), la différence doit être VISUELLEMENT évidente (bannière
  pleine largeur, mots surlignés) — un bouton discret en haut à droite avec
  un texte qui change ne suffit pas, Amine ne l'a pas vu la première fois.
- **`npm run lint`/`npm run typecheck` existent maintenant à la racine** —
  à utiliser dans TOUTE story future touchant du code (gates AGENTS.md à
  mettre à jour en conséquence si pas déjà fait par une story ultérieure).
- Preuve de déploiement en 1 commande (toujours valide) :
  `ssh serveuria 'docker ps --filter name=<uuid8> --format "{{.Image}}"'` et
  comparer à `git rev-parse HEAD`.
- ADR-002 : distinction cruciale — interdit « prédiction » dans le COPY
  COMMERCIAL ; la mesure interne (richesse finale, verdicts/issues
  d'adjudication) reste libre.
