== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-12 20h07 (CHANTIER US-IQ-02 FRONTEND CLOS — 10/10 tasks mergées et déployées sur main, agent conversationnel enfin atteignable en prod ; NEXT = vérification réelle par clic humain + chantier séparé corpus §10.3) ==
Synthèse complète et autonome — ne suppose la lecture d'aucune passation antérieure.
Remplace entièrement les synthèses précédentes de ce chantier (14h02/14h36/16h07) — leur
[NEXT] est soldé. Design (`docs/superpowers/specs/2026-07-12-us-iq-02-frontend-design.md`)
et plan (`docs/superpowers/plans/2026-07-12-us-iq-02-frontend-implementation.md`) restent
la référence technique complète si besoin de re-dériver un détail d'implémentation.

[ETAT]
- **`main`** : HEAD = `6d2a4f8`, poussé sur `origin/main`, déploiement Coolify déclenché.
  Le worktree de ce chantier (`us-iq-02-frontend`) a été nettoyé et supprimé — tout son
  contenu est désormais uniquement dans l'historique de `main`.
- **Déploiement confirmé en prod par preuve directe** (pas par supposition — RÈGLE N°4) :
  après le premier push (`825069c`), une chaîne i18n unique écrite cette session pour
  Task 5 (« l'échange de vive voix ») a été retrouvée dans le bundle JS réellement servi
  par `https://bassira.ma/devis`, confirmant que le nouveau code frontend est bien en ligne
  avant de relancer Task 10 contre la cible réelle.
- **Les 10 tasks du plan sont faites, chacune revue individuellement (spec + qualité) ;
  3 ont nécessité un cycle correctif** (Task 3 : un chemin de réponse `agent_turn` oublié ;
  Task 5 : une chaîne anglaise divergente + un BOM parasite dans un message de commit ;
  Task 10 : bloquée à raison tant que Tasks 1-9 n'étaient pas déployées, débloquée après).
- **Une revue finale whole-branch (Opus) sur les Tasks 1-9 a trouvé un vrai défaut de PLAN**
  (pas d'implémentation, invisible à toute revue tâche par tâche) : l'email de confirmation
  `meeting`, déplacé par Task 2 pour partir APRÈS vérification de la réservation Cal.com,
  gardait son ancien texte « Réservez votre entretien » + un lien de réservation — contra-
  diction directe avec l'écran affichant « Votre entretien est confirmé », risque de double
  réservation. **Corrigé** (`3814d62`) : nouvelle copy fr/en/ar de confirmation post-
  réservation sans lien, cohérente avec l'écran ; `_build_confirmation_cta` simplifié
  (calcom_link n'est plus utilisé par aucune branche) ; 5 tests mis à jour ; re-revue
  Approved. Le champ `calcom_link` renvoyé au FRONTEND (Task 1, pour le lien cliquable
  « Voir mon créneau » sur l'écran de clôture) est un mécanisme séparé, non touché, toujours
  correct.
- **Suite backend finale** : 2234 passed (± 1 flake pré-existant intermittent, sans rapport,
  déjà diagnostiqué : `test_pdf_pipeline_e2e.py::TestPipelineMarkdown::test_md_hash_stable_
  with_deterministic_enricher`, différence de timestamp d'1 seconde dans un test de
  génération PDF, RIEN à voir avec ce chantier). Ruff clean. Build frontend vert à chaque
  étape. **Playwright** : 6/6 verts contre la prod réelle déployée (3 tests US-IQ-01
  pré-existants + 3 nouveaux scénarios mockés — réseau intercepté, aucun POST business réel
  possible, contrainte read-only du fichier respectée).

[FAIT — chronologie complète de ce chantier, sessions cumulées]
1. Brainstorming (skill `superpowers:brainstorming`) → design validé section par section
   avec Amine (7 « oui ») → committé.
2. `superpowers:writing-plans` → plan 10 tasks, code complet à chaque étape, committé.
   2 erreurs corrigées AVANT l'écriture du plan (grep du vrai code, pas de supposition) :
   les noms de packages self-service réels, et la localisation réelle d'email/full_name
   (`quote_ownership`, pas `intake_sessions`).
3. Amine a choisi le mode d'exécution **Subagent-Driven** → `superpowers:using-git-worktrees`
   → worktree isolé créé (raison : repo en PRODUCTION, auto-deploy Coolify sur push `main`,
   10 tasks directement sur `main` auraient fait 10 déploiements incomplets).
4. **Tasks 1-4 (backend)** exécutées séquentiellement (jamais 2 implémenteurs en parallèle —
   red flag explicite de la skill, risque de corruption du même index git partagé) : chacune
   dispatch implémenteur → re-vérification indépendante de la suite complète par le
   controller (jamais fait confiance au seul rapport du sous-agent, qui ne montre parfois
   qu'un sous-ensemble scope) → dispatch reviewer → cycle correctif si besoin → commit.
5. **Task 5 (i18n)** : 1 déviation de contenu (`en.json` « form » au lieu de « process ») +
   1 BOM parasite dans un message de commit corrigés.
6. **Tasks 6-9 (frontend)** : `intake.js`, `IntakeAgentPanel.vue` (nouveau composant, 425
   lignes, transcription exacte du plan), câblage `QuoteView.vue` (renumérotation 5 étapes —
   **la task qui corrige le bug racine de tout ce chantier**), préselection `OffersView.vue`.
   Toutes approuvées, 0 Critical/Important au-delà de ce qui a été corrigé.
7. **Task 10 (Playwright)** : bloquée à la 1ʳᵉ tentative — root cause diagnostiquée par
   l'implémenteur lui-même (Playwright teste TOUJOURS contre `bassira.ma` réel, jamais un
   serveur local ; les Tasks 1-9 n'existaient que dans le worktree, jamais déployées) — a
   correctement refusé de committer un résultat trompeur plutôt que de truquer un test vert.
8. **Décision d'Amine** (`AskUserQuestion`) : merger+déployer Tasks 1-9 maintenant pour
   pouvoir terminer Task 10 contre le vrai bundle, plutôt qu'attendre la fin des 10 tasks.
9. Revue finale whole-branch (Opus) sur Tasks 1-9 → 1 défaut de plan trouvé et corrigé
   (cf. [ETAT]) → re-vérifié → merge (`825069c`) → **push confirmé par Amine** (« Merge
   commit et push ») → déploiement vérifié en prod par preuve directe.
10. Task 10 relancée avec succès contre le bundle déployé → 6/6 verts → revue Approved →
    merge (`6d2a4f8`) → push.
11. Nettoyage : stash purgé (contenu mergé), worktree supprimé (confirmé que `main` contenait
    bien tous les commits avant suppression).

[ALERTE]
- **`US-IQ-02.passes` reste `false` dans `.ralph/prd.json`** — décision assumée, PAS un oubli.
  Le gate de cette story exige aussi que le corpus d'évaluation §10.3 (2 échecs réels connus,
  documentés dans `.ralph/progress.md` section US-IQ-02, sessions précédentes) soit re-passé
  à 10/10 sur les critères automatiques 1-8 — chantier séparé, prompt à ajuster
  (`AGENT_SYSTEM_PROMPTS`), non touché par ce chantier frontend.
- Les commits de ce chantier sont désormais UNIQUEMENT dans l'historique de `main` — le
  worktree qui les a produits n'existe plus. Toute investigation future se fait par
  `git log`/`git show` sur `main`, pas en cherchant un worktree.
- Réservation test réelle historique (`bPsTR8xUhWyYpD3pPMZbEp`, 2026-07-11) toujours active
  sur l'agenda Cal.com d'Amine — jamais annulée depuis, non traité par ce chantier (hors
  périmètre), risque faible.

[BLOQUE / EN ATTENTE D'AMINE]
- Rien de bloquant. Le chantier est **techniquement clos et déployé** — la seule chose qui
  reste est la vérification humaine en usage réel (cf. NEXT 1), qui ne peut être faite que
  par Amine (ou via Chrome connecté) et n'a pas encore eu lieu au moment de cette passation.

[NEXT]
1. **PRIORITÉ 1 — vérification réelle en prod (SOP-011)** : un vrai clic humain sur
   `bassira.ma/devis`, jusqu'à l'écran Assistant, une vraie conversation avec l'agent (vrai
   appel LLM), vérifier que la clôture affiche le contenu attendu selon la branche obtenue
   (lien Cal.com pour meeting, recommandation de package pour self_service, email reçu au
   bon moment). C'est la SEULE preuve d'atteignabilité produit qui compte — le Playwright
   mocké de Task 10 ne couvre que le rendu, pas un vrai parcours avec un vrai LLM. Pas encore
   fait au moment de cette passation.
2. **Chantier séparé, non urgent** : ajuster `AGENT_SYSTEM_PROMPTS` (fr, puis re-dériver
   en/ar, parité ADR-008) pour les 2 échecs réels du corpus §10.3 (détail exact dans
   `.ralph/progress.md` section US-IQ-02, sessions antérieures à ce chantier frontend — à
   relire, pas dans ce fichier). Re-lancer le corpus (`scripts/test_intake_agent_corpus.py`,
   hand-run dans le conteneur prod, vrai appel LLM), viser 10/10 critères 1-8. Poser
   `US-IQ-02.passes = true` seulement après.
3. US-IQ-05 (Porte 2 « AAR ») reste derrière, non prioritaire.
4. Si jamais remarqué par un utilisateur réel : les 2 observations produit de la revue
   finale (Minor, non bloquantes) — latence jusqu'à 15s sur le bouton « Passer cette étape »
   pour self_service (appel LLM synchrone dans le thread HTTP Werkzeug, cohérent avec
   l'existant) ; l'amorce automatique de conversation consomme 1 tour de budget (6 tours
   réels sur 7 pour le décideur, probablement voulu).

[CTX]
- Repo GitHub `--repo Afristrat/MiroShark`. `main` = `6d2a4f8`.
- Design : `docs/superpowers/specs/2026-07-12-us-iq-02-frontend-design.md`.
- Plan (référence technique complète, code exact de chaque task) :
  `docs/superpowers/plans/2026-07-12-us-iq-02-frontend-implementation.md`.
- Le ledger de progression du worktree (`.superpowers/sdd/progress.md`) a été détruit avec
  le worktree (scratch, gitignored, comportement attendu) — cette passation en est le
  résumé durable.

[MEMO inter-sessions]
- **Packages self-service réels** : `pmf_discovery` (10k MAD), `crisis_drill_24h` (20k MAD,
  featured), `adcheck_lite` (15k MAD) — seuls ceux-là dans `OffersView.vue` ont
  `selfService: true`. Ne pas confondre avec `_VALID_PACKAGES` de `quote_service.py`.
- **Playwright de ce repo teste TOUJOURS contre `bassira.ma` réel**, jamais un serveur
  local — leçon durement apprise sur Task 10 : un chantier multi-tasks avec des tests E2E
  ne peut pas les valider avant d'avoir mergé+déployé le code qu'ils testent, si la politique
  du repo interdit un environnement de preview local.
- **`_build_confirmation_cta` n'a plus besoin de `calcom_link`** depuis `3814d62` — si un
  futur chantier veut réintroduire un lien dans un email `meeting`, bien vérifier D'ABORD à
  quel moment cet email part (avant ou après réservation) avant de choisir la copy, sous
  peine de répéter l'erreur trouvée par la revue finale de ce chantier.
- **Une revue finale whole-branch trouve des choses qu'aucune revue tâche par tâche ne peut
  voir** — ce chantier en est la preuve concrète (le défaut de copy email n'existait dans
  aucun diff de tâche individuelle, seulement dans la combinaison Task 1 + Task 2 vue
  ensemble). Toujours la faire sur un chantier multi-tasks, même si chaque tâche est déjà
  approuvée individuellement.
- Marque : Bassira (بصيرة) visible, `miroshark` technique. Jamais « prédiction » dans le copy
  commercial (ADR-002). URLs publiques toujours `bassira.ma` (ADR-013).
