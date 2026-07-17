# PASSATION NUCLÉAIRE — MiroShark / Bassira — 2026-07-17

Synthèse autonome fondée sur l’état système du dépôt au 2026-07-17. Elle remplace intégralement la passation précédente, devenue obsolète après la clôture d’US-224 et plusieurs commits postérieurs.

## ÉTAT SYSTÈME VÉRIFIÉ

- Branche : `main`.
- HEAD local : `162f9a4af225bf1276c535ffd11b53c46839b7d3` (`Refine MiroShark frontend and backend workflows`).
- `origin/main` : `162f9a4af225bf1276c535ffd11b53c46839b7d3`.
- Arbre de travail désormais modifié par la recertification décrite ci-dessous ; ces
  corrections restent locales tant qu’elles ne sont pas commitées et poussées.
- PRD Ralph : **168 stories au total, 151 avec `passes: true`, 17 avec `passes: false`**.
- Cette passation est elle-même une nouvelle modification locale tant qu’elle n’est pas commitée et poussée.

## BOUCLÉ ET PRÉSENT DANS L’HISTORIQUE GIT

### Lot fondations post-déploiement

- **US-223 — `simulation_prompts` + PromptRegistry** : commit `1e77490`.
- **US-222 — arènes requêtables + registre dynamique** : commit `482130c`.
- **US-228 — cache Supabase ESCO** : commit `c342495`.
- **US-221 — persistance durable des artefacts** : commit final `b35b8d3`.
  - Persistance aux checkpoints prepare/run/rapport.
  - Hydratation du dossier local avant reprise si le volume local a été vidé.
  - Tests de round-trip ajoutés.
- Les migrations associées à US-221/222/223/228 sont consignées dans la précédente passation comme exécutées et vérifiées en production. Cette affirmation n’a **pas été revalidée sur l’infrastructure pendant la présente mise à jour** : refaire une vérification système avant toute affirmation future sur leur état courant en production.

### Vocabulaire client et sécurité

- **US-224 — renommage « arène de convictions » (ADR-018)** : commit `fe32a1f`.
  - PRD marqué `passes: true`, `completedAt` renseigné.
  - Valeurs i18n FR/EN/AR, templates PDF et quatre composants client corrigés.
  - Assertions de templates PDF adaptées au vocabulaire « Issue ».
- **Réglages réservés aux super-admins** : commit sécurité `109ab90`.
  - Guard ajouté et tests P0 associés.
- **Mutations de simulation protégées** : commit sécurité `4bb74f8`.
  - Décorateurs d’autorisation et couverture de tests de sécurité étendue.

### Dépendances npm

- **US-213 — correction des vulnérabilités npm** : commit `5cf0b79`.
- Les lockfiles frontend et racine ont été actualisés sans changement des manifestes `package.json`.
- `.ralph/progress.md` consigne, au moment de la clôture, `npm audit --audit-level=low = 0` sur les deux graphes, build frontend vert et suite backend complète verte.
- Ces résultats sont des preuves historiques attachées à ce commit, pas une certification du HEAD actuel.

## RECERTIFICATION COMPLÈTE DU HEAD `162f9a4` — VERTE

L’audit frais du commit `162f9a4` confirme **45 fichiers** et **7 316 insertions / 7 175 suppressions** au diff brut. En ignorant les espaces, il reste **43 fichiers** et **448 insertions / 307 suppressions** sémantiques : ce commit n’était donc pas un simple changement de fins de ligne.

La recertification du 2026-07-17 a contrôlé et corrigé les contrats affectés :

- lint frontend et backend : **0 erreur, 0 warning ESLint ; Ruff vert** ;
- mypy : **succès sur 116 fichiers source, 0 erreur** ;
- build frontend : **succès, 948 modules transformés, aucun warning de chunk** ;
- parité i18n stricte : **2 060 clés FR/EN/AR** ;
- audits npm racine et frontend : **0 vulnérabilité** ;
- suite backend complète : **2 321 réussites, 60 ignorées, 0 échec** ;
- suite Playwright complète sur `https://bassira.ma` : **113 réussites, 1 ignorée, 0 échec**.

Le test Playwright ignoré est `client-account-email-roundtrip.spec.ts` : il modifie
réellement le compte de production et requiert désormais l’opt-in explicite
`BASSIRA_E2E_WRITE=1`. Il n’est donc **pas certifié exécuté** pendant cette campagne
en lecture seule. Les tests de navigation admin, du formulaire `/devis`, du checkout
Crisis Drill et de `/signup` ont été réalignés sur les contrats actuellement déployés.

Par conséquent :

- le code au HEAD `162f9a4`, complété par les corrections locales de recertification,
  franchit tous les gates automatisés non mutatifs disponibles ;
- la recertification n’est permanente dans Git qu’après commit et push des corrections
  locales listées par `git status` ;
- aucune preuve fraîche de déploiement de ces corrections locales n’a été produite ici.

## DETTES ET RISQUES ENCORE OUVERTS

- **17 stories Ralph restent à `passes: false`.**
- Les 298 warnings ESLint historiques et les warnings Vite de chunks/compression ont été
  éliminés dans la recertification locale. Les notes mypy `annotation-unchecked` ne sont
  pas des erreurs, mais US-212b reste le chantier structurel de typage complet.
- **US-212b** reste ouverte : burn-down mypy sur les modules encore exclus.
- **US-208** reste ouverte : Redis + worker RQ PDF réellement actifs et prouvés en production.
- La dette i18n précédemment identifiée dans `HistoryDatabase.vue` doit être recontrôlée sur HEAD avant création d’une story dédiée, car le fichier a été modifié par `162f9a4`.

## STORIES ACTUELLEMENT ÉLIGIBLES LES PLUS IMPORTANTES

### P0 Intake Qualification

- **US-IQ-05 — porte AAR « Testez-nous sur du connu »** ; dépendance satisfaite : US-IQ-01.
  - Scellement de l’issue réelle.
  - Preuve qu’elle n’entre ni dans le contexte agent ni dans le pré-seed.
  - Parcours complet trilingue et Playwright.
- **US-IQ-06 — vue admin enrichie** ; dépendance satisfaite : US-IQ-03.
- **US-IQ-07 — pré-seed depuis le brief** ; dépendance satisfaite : US-IQ-03.

### Lot prompts et simulation

- **US-231 — élévation L99 des trois prompts d’arènes** ; P1, 8 h, dépendance US-223 satisfaite.
- **US-229 — expertise métier ESCO injectée dans les personas** ; P1, 6 h, dépendances US-228 et US-223 satisfaites.
- **US-225 — `resolution_spec` structurée pour chaque marché** ; P1, 6 h, dépendance US-223 satisfaite.
- **US-232, US-233, US-235, US-230** sont également éligibles, mais moins prioritaires dans le PRD courant.

## ENCHAÎNEMENT HARD THINGS FIRST RECOMMANDÉ

1. **Committer et pousser atomiquement la recertification**, puis vérifier que le remote
   pointe sur ce nouveau HEAD et que le déploiement correspondant est sain.
2. **US-IQ-05 — porte AAR scellée**.
   - C’est le risque P0 le plus difficile : confidentialité, scellement cryptographique, non-fuite vers deux consommateurs et preuve E2E.
3. **US-IQ-07 — pré-seed depuis le brief**.
   - À enchaîner immédiatement après IQ-05 pour fermer la frontière de non-divulgation de `aar_known_outcome` avec un test partagé.
4. **US-IQ-06 — vue admin enrichie**.
5. **US-231 — prompts d’arènes L99**, puis **US-225** et **US-229** selon la valeur produit recherchée.

## PROCHAINE ACTION EXACTE

La recertification locale est terminée. La prochaine action technique est de la rendre
permanente par commit/push et preuve du déploiement, puis de démarrer **US-IQ-05** comme
première story fonctionnelle — avant US-231.

## SIGNAL DE COMPLÉTION

Ne jamais émettre `<promise>COMPLETE</promise>` tant que les 17 stories restantes ne sont pas toutes à `passes: true` et que les quality gates complets n’ont pas été vérifiés sur `main` au même HEAD.
