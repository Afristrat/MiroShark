# PASSATION NUCLÉAIRE — MiroShark / Bassira — 2026-07-17

Synthèse autonome fondée sur l’état système du dépôt au 2026-07-17. Elle remplace intégralement la passation précédente, devenue obsolète après la clôture d’US-224 et plusieurs commits postérieurs.

## ÉTAT SYSTÈME VÉRIFIÉ

- Branche : `main`.
- HEAD local et `origin/main` : `3424bb028e3848f8ccfb60f838599944af5b6439`
  (`[US-231] Élever les prompts des trois arènes`).
- Image Coolify active vérifiée : ce même SHA exact ; `/health` = 200.
- PRD Ralph : **168 stories au total, 154 avec `passes: true`, 14 avec `passes: false`**.
- US-231 est fonctionnelle en production mais reste volontairement `passes:false` tant
  que le nouvel incident SOP-001 décrit ci-dessous n'est pas remédié.
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

- **P0 sécurité — rotation SOP-001 obligatoire** : le 2026-07-17, une sortie
  `docker inspect` a exposé dans le transcript des credentials de Supabase
  MiroShark et de services d’autres projets inclus dans la même sortie. Rotater
  exhaustivement toutes les valeurs imprimées listées par l’incident dans
  `.ralph/progress.md`, mettre à jour chaque consommateur, puis redéployer et
  recertifier. **Lot MiroShark terminé et recertifié le 2026-07-17. Les huit
  autres expositions sont des dettes propres à leurs projets : cette session ne
  doit ni les traiter ni piloter leur rotation.**

- **P0 sécurité — nouvel incident MiroShark pendant US-231** : une inspection de
  l'environnement du conteneur applicatif a imprimé les credentials MiroShark dans
  le transcript. Le lot de rotation MiroShark précédemment certifié est donc caduc
  pour les valeurs réexposées. Rotater uniquement depuis cette session propriétaire,
  propager aux consommateurs, redéployer puis recertifier avant toute suite produit.

- **15 stories Ralph restent à `passes: false`.**
- Les 298 warnings ESLint historiques et les warnings Vite de chunks/compression ont été
  éliminés dans la recertification locale. Les notes mypy `annotation-unchecked` ne sont
  pas des erreurs, mais US-212b reste le chantier structurel de typage complet.
- **US-212b** reste ouverte : burn-down mypy sur les modules encore exclus.
- **US-208** reste ouverte : Redis + worker RQ PDF réellement actifs et prouvés en production.
- La dette i18n précédemment identifiée dans `HistoryDatabase.vue` doit être recontrôlée sur HEAD avant création d’une story dédiée, car le fichier a été modifié par `162f9a4`.

## STORIES ACTUELLEMENT ÉLIGIBLES LES PLUS IMPORTANTES

### P0 Intake Qualification

- **US-IQ-05 — clôturée** : porte AAR scellée, non-fuite prouvée et parcours
  trilingue certifié en production.
- **US-IQ-07 — clôturée** : pré-seed éditable, traçabilité durable et test partagé
  de non-divulgation certifiés en production.
- **US-IQ-06 — clôturée et certifiée en production** : brief structuré,
  transcript intégral, confidentialité, routage et réservation Cal.com ; image
  fonctionnelle exacte `ce6faf66fc94dee4ce0647216507599ea7cf8d56`.

### Lot prompts et simulation

- **US-231 — fonctionnelle en production, clôture suspendue à SOP-001** : trois
  prompts L99 trilingues, neuf seeds actifs et byte-for-byte identiques aux fallbacks,
  biais d'observation retirés, image exacte `3424bb028e3848f8ccfb60f838599944af5b6439`.
- **US-229 — expertise métier ESCO injectée dans les personas** ; P1, 6 h, dépendances US-228 et US-223 satisfaites.
- **US-225 — `resolution_spec` structurée pour chaque marché** ; P1, 6 h, dépendance US-223 satisfaite.
- **US-232, US-233, US-235, US-230** sont également éligibles, mais moins prioritaires dans le PRD courant.

## ENCHAÎNEMENT HARD THINGS FIRST RECOMMANDÉ

1. **Rotater les credentials MiroShark exposés pendant la certification US-231**, puis
   recertifier l'image et les dépendances externes.
2. Marquer **US-231** `passes:true`, puis enchaîner sur **US-225**.

## PROCHAINE ACTION EXACTE

US-231 est poussée et déployée sur l'image exacte `3424bb028e3848f8ccfb60f838599944af5b6439` :
backend **2 355/0**, golden sets ciblés **43/43**, build Vite vert, neuf seeds SQL
actifs et identiques au code, `/health` à 200. La prochaine action exacte est la
**rotation SOP-001 des credentials MiroShark réexposés pendant cette certification**.
Ne pas ouvrir US-225 avant cette remédiation et sa recertification. Les dettes des
autres projets restent exclusivement dans leurs sessions propriétaires.

## SIGNAL DE COMPLÉTION

Ne jamais émettre `<promise>COMPLETE</promise>` tant que les 15 stories restantes ne sont pas toutes à `passes: true` et que les quality gates complets n’ont pas été vérifiés sur `main` au même HEAD.
