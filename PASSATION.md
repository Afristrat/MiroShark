== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-12 (nuit : ADR-IQ-09+10 déployés/vérifiés, MAIS découverte critique — le parcours /devis réel ne déclenche JAMAIS l'agent ni l'email/Cal.com ; brainstorming en cours pour US-IQ-02 frontend, design NON figé, AUCUN code écrit) ==
Synthèse complète et autonome — ne suppose la lecture d'aucune passation antérieure. La
synthèse du 2026-07-11 (soir/nuit) reste ci-dessous pour l'historique SMTP Cal.com/ADR-IQ-08
(toujours vrai, non contredit), mais son [NEXT] est **caduc** — remplacé par celui-ci.

[ETAT]
- **Prod à jour**, HEAD = `728bcbd`, poussé et déployé, vérifié en profondeur (conteneur
  `miroshark-u6pn5mr2pgi88s13un55pkzb-202617800083` au moment de la vérification — **le
  suffixe change à CHAQUE redéploiement**, toujours re-`docker ps` avant tout `docker exec`).
- **SMTP Cal.com CONFIRMÉ fonctionnel** (Amine a testé réellement) : email natif Cal.com reçu
  côté prospect ET côté host (`a.mansouri`), lien Google Meet présent. Ce point précis du
  chantier SMTP est clos, ne plus y revenir.
- **ADR-IQ-09** (`3ec2259`) : `forwardParamsSuccessRedirect` de Cal.com ne relaie JAMAIS
  `intake_session_id` (query param custom) — seulement ses propres champs natifs (`email`,
  `uid`, `eventTypeSlug`...), constat empirique sur l'URL de redirect réelle fournie par
  Amine. Fix : `email`/`name` (slugs natifs Cal.com) posés sur le lien de réservation +
  `disableOnPrefill=true` activé côté API Cal.com sur l'event type Intake (id 25) — le
  booker ne peut plus modifier ces 2 champs une fois préremplis. Fallback de matching par
  email côté `confirm_calcom_booking` quand `intake_session_id` absent.
- **ADR-IQ-10** (`728bcbd`) : une review de sécurité automatique post-commit a trouvé un
  vrai bypass dans le fix ADR-IQ-09 tel qu'écrit (un attaquant connaissant l'email d'un
  prospect pouvait poser n'importe quel `uid` bidon et faire croire à une réservation
  jamais faite). Fermé par vérification server-to-server OBLIGATOIRE : `confirm_calcom_
  booking` interroge désormais `GET /v2/bookings/{uid}` avec la clé serveur AVANT toute
  écriture, exige `status=ACCEPTED` + bon `eventTypeId` (25) + email attendee ATTESTÉ par
  Cal.com (jamais un query param client). Toutes les erreurs renvoient le même
  `error_code: CONFIRMATION_FAILED` (pas d'énumération). 2215 tests passed, ruff clean,
  déployé et vérifié en profondeur : conteneur re-`grep`é, endpoint testé en HTTP réel
  avec le vrai `uid` de la réservation d'hier (`7gz9u9RSvzgHcZRDqnB2rR`), logs re-lus,
  cross-check en base confirmant le comportement observé (404 attendu, pas un bug).
- **DÉCOUVERTE CRITIQUE (cette session, en testant le parcours réel)** : Amine a fait le
  test complet du VRAI formulaire `/devis` en production → jamais vu l'agent conversationnel,
  aucun email généré des 2 côtés. Root cause trouvée et vérifiée par grep exhaustif :
  `frontend/src/api/intake.js` n'expose QUE `startIntakeSession` et `submitIntakeForm` —
  **ZÉRO référence à `agent/turn` ou `complete_routing` nulle part dans `frontend/src`**.
  `QuoteView.vue` saute directement du formulaire soumis à un écran « merci » statique
  (`currentStep = 4`). Conséquence : **depuis la mise en prod de ce formulaire, AUCUN
  prospect réel n'a jamais reçu ni agent, ni routage, ni email de confirmation, ni lien
  Cal.com** — juste un ID de devis et rien d'autre. US-IQ-04 (email/Cal.com) et US-IQ-03
  (routage), bien que `passes: true`, sont donc du code correct mais **inatteignable en
  usage réel** — leur seule vérification passée était par appel API direct, jamais par un
  vrai clic sur le site.
- **Correction du diagnostic initial (auto-corrigée dans la même session)** : j'ai d'abord
  dit à Amine que l'agent (US-IQ-02) « n'avait jamais été construit » — FAUX, corrigé
  immédiatement après vérification de `.ralph/progress.md` : **le backend de l'agent EST
  déjà construit, TDD complet, mergé (`8b0f89b`), déployé, testé avec de vrais appels LLM
  en prod** (`qwen3.6-35b` via gateway LiteLLM). `US-IQ-02.passes = false` dans `prd.json`
  reflète UNIQUEMENT 2 échecs réels sur le corpus d'évaluation §10.3 (pas un manque
  d'implémentation) — cf. détail dans [NEXT]. Ce qui manque réellement : (1) le prompt à
  ajuster pour ces 2 échecs, (2) l'écran chat frontend, **explicitement hors scope du plan
  déjà écrit** `docs/superpowers/plans/2026-07-10-us-iq-02-agent.md` (§ Hors scope), et
  (3) le câblage complet du parcours qui n'existe nulle part.

[FAIT — cette session, dans l'ordre chronologique]
1. Lu la passation du 2026-07-11 soir, identifié le NEXT (réservation test réelle).
2. Amine a confirmé le SMTP Cal.com fonctionnel (email reçu des 2 côtés, lien Meet présent).
3. Amine a testé une réservation réelle → `MISSING_PARAMS` sur le redirect. Diagnostic par
   preuve système (URL réelle fournie par Amine, config Cal.com re-vérifiée via API) →
   ADR-IQ-09 identifié, implémenté en TDD (8 nouveaux tests), déployé (`3ec2259`), vérifié
   en HTTP réel + logs + DB.
4. Review de sécurité automatique post-commit + post-push a flaggé le spoofable-field bypass
   → ADR-IQ-10 conçu et implémenté en TDD (5 tests de sécurité dédiés), déployé (`728bcbd`),
   vérifié en profondeur (HTTP réel, logs, cross-check DB avec le vrai uid d'hier).
5. Amine a posé une question de contexte sur le formulaire (« les questions sont figées,
   normal ? ») → confirmé que oui par design (ADR-IQ-01), MAIS Amine a précisé n'avoir
   JAMAIS vu l'agent → investigation → découverte critique décrite ci-dessus (frontend
   jamais câblé sur agent/turn ni complete_routing).
6. Amine a demandé de construire US-IQ-02 complet (pas un stopgap minimal) → skill
   `superpowers:brainstorming` invoquée, en cours au moment de la coupure de contexte.
7. **Brainstorming — décisions actées avec Amine (AskUserQuestion, réponses explicites)** :
   a. Amorce de la conversation agent : auto-déclenchée à l'arrivée sur l'écran (premier
      tour `agent_turn` envoyé automatiquement avec un message d'amorce synthétique,
      invisible pour l'utilisateur) — PAS besoin que le prospect tape en premier.
   b. Corriger le prompt (2 échecs corpus §10.3) AVANT de construire le frontend — pas
      accepté tel quel, pas différé après.
   c. Écran 4 complet conforme au prompt Stitch §10.2 (chat + bandeau IA permanent +
      colonne latérale brief live/sujets verrouillés + bouton « Passer cette étape ») —
      PAS un MVP dégradé sans colonne latérale.
   d. Le lien Cal.com (branche `meeting`) doit être affiché ET cliquable DIRECTEMENT à
      l'écran de confirmation, pas seulement dans l'email — petit ajout backend nécessaire
      (`calcom_link` à renvoyer dans la réponse `complete_routing`/`agent_turn`/
      `_close_session_gracefully` quand `route == 'meeting'`).
8. **Correction architecturale majeure demandée par Amine, confirmée explicitement (« oui »)** :
   pour la branche `meeting` UNIQUEMENT, l'email Bassira contextualisé (`_send_intake_
   confirmation`, US-IQ-04) ne doit PLUS partir à la clôture de l'agent/skip — il doit être
   **déplacé pour ne partir qu'APRÈS que `confirm_calcom_booking` réussisse** (créneau
   réellement validé), pas avant. Raison d'Amine : évite d'envoyer « votre brief est prêt »
   à quelqu'un qui n'a peut-être jamais réservé, et regroupe la confirmation autour d'un
   seul moment de vérité (la réservation), plutôt que 2 emails déconnectés dans le temps.
   Pour `quote_48h`/`self_service` (pas d'étape Cal.com) : email inchangé, part toujours
   immédiatement à la clôture. **CECI EST UN CHANGEMENT DE COMPORTEMENT SUR DU CODE DÉJÀ
   SHIPPÉ (US-IQ-04) — PAS ENCORE IMPLÉMENTÉ, à faire dans le cadre de ce chantier US-IQ-02.**
9. Découvert et vérifié réutilisable : `frontend/src/components/ReportChatPanel.vue` — un
   pattern de chat déjà existant dans le codebase (bulles par rôle, indicateur « réflexion »,
   formulaire d'envoi) à utiliser comme base structurelle pour le nouveau composant.
10. Nouvelle SOP approuvée trouvée et vérifiée NON applicable : **SOP-013** (prototype
    navigable avant démarrage/reprise du mode Ralph) — exclut explicitement les « stories
    isolées demandées explicitement par Amine hors mode Ralph » ; ce chantier est mené en
    direct (interactif), pas en `ralph-mode`/`ralph-loop`, donc SOP-013 ne s'applique pas
    ICI (à re-vérifier si jamais ce chantier bascule en exécution Ralph autonome).
11. Point ouvert posé à Amine, **réponse pas encore reçue au moment de la coupure de
    contexte** : pour la branche `self_service`, aucune logique n'existe nulle part pour
    déterminer QUEL package Stripe (`pmf_discovery` / `crisis_drill_24h` / `adcheck_lite`)
    correspond à un brief donné. Proposition faite (pas encore validée) : rediriger vers
    `/offres` pour un choix manuel du prospect, plutôt que d'inventer un algorithme de
    sélection automatique sans arbitrage d'Amine.

[ALERTE]
- **Le brainstorming (skill `superpowers:brainstorming`) est INTERROMPU EN COURS DE
  SECTION 2** (flux de données / machine à états) — design PAS ENCORE présenté en entier,
  PAS ENCORE écrit dans `docs/superpowers/specs/`, PAS de plan écrit, **AUCUN code du
  chantier US-IQ-02 frontend n'a été touché**. Ne pas sauter à l'implémentation à la
  reprise — reprendre le brainstorming exactement où il s'est arrêté (cf. [NEXT] point 1).
- Réservation test réelle historique (`bPsTR8xUhWyYpD3pPMZbEp`, 2026-07-11) toujours active
  sur l'agenda Cal.com d'Amine — jamais annulée, risque faible.
- **US-IQ-04 et US-IQ-03 restent `passes: true` dans `prd.json`** — c'est correct au sens
  strict de leurs AC (backend vérifié par appel API direct), mais ne PAS présenter ces
  stories comme « fonctionnelles en usage réel » tant que le câblage frontend (ce chantier)
  n'est pas fait. Ne pas non plus re-marquer `passes: false` sans en parler à Amine d'abord
  — c'est une nuance de scope, pas une régression du code déjà livré.

[BLOQUE / EN ATTENTE D'AMINE]
- Réponse à la question ouverte sur le point 11 de [FAIT] (package Stripe self-service :
  redirection `/offres` vs algorithme de sélection à définir).
- Le reste du design (sections 3+ : détail backend deltas, composants frontend précis,
  i18n, gestion d'erreurs, tests) n'a pas encore été présenté à Amine — pas encore de go
  explicite sur l'ensemble du design.

[NEXT]
1. **PRIORITÉ 1 — reprendre le brainstorming US-IQ-02 exactement où il s'est arrêté** :
   - Obtenir la réponse d'Amine sur le package Stripe self-service (point 11 ci-dessus).
   - Finir de présenter le design section par section (backend deltas précis : `calcom_link`
     + `confidential_flags` dans les réponses API, timing de l'email déplacé vers
     `confirm_calcom_booking` ; composants frontend précis : `IntakeAgentPanel.vue`,
     `frontend/src/api/intake.js` à étendre avec `postAgentTurn`/`completeIntakeSession` ;
     i18n fr/en/ar ; gestion d'erreurs — budget épuisé, gateway down, retry ; plan de tests
     Playwright étendant `intake-parcours.spec.ts`).
   - Obtenir le go explicite d'Amine sur le design complet.
   - Écrire le design dans `docs/superpowers/specs/2026-07-12-us-iq-02-frontend-design.md`,
     commit, auto-review (placeholders, contradictions, ambiguïtés), faire relire par Amine.
   - Invoquer `superpowers:writing-plans` pour transformer le design validé en plan TDD
     tâche par tâche (comme fait pour US-IQ-04).
2. **Avant ou pendant l'implémentation** : ajuster `AGENT_SYSTEM_PROMPTS` (fr, puis re-dériver
   en/ar, parité ADR-008) pour les 2 échecs réels du corpus §10.3 documentés dans
   `.ralph/progress.md` section US-IQ-02 : (1) disclosure IA doit précéder TOUT traitement,
   y compris un contenu confidentiel immédiat (le cas le plus sérieux) ; (2) assouplir
   légèrement la contrainte « ≤ 3 phrases » sur les tours combinant disclosure+refus+relance
   (injection, demande de prédiction). Re-lancer le corpus (`scripts/test_intake_agent_
   corpus.py`, hand-run dans le conteneur prod, vrai appel LLM) après ajustement, viser
   10/10 critères automatiques 1-8. Puis poser `US-IQ-02.passes = true`.
3. Une fois le chantier US-IQ-02 frontend livré et vérifié en usage réel (un vrai clic sur
   le site, pas un appel API direct — SOP-011) : reconsidérer si `passes: true` sur
   US-IQ-03/04 doit être accompagné d'une note dans `progress.md` précisant la date à
   laquelle le parcours est devenu RÉELLEMENT atteignable en prod (distincte de la date
   d'implémentation backend).
4. US-IQ-05 (Porte 2 « AAR ») reste en attente derrière ce chantier, non prioritaire tant
   que le parcours standard n'est pas complètement fonctionnel en usage réel.

[CTX — ajouts cette session, en complément du CTX 2026-07-11 ci-dessous (toujours valide)]
- **`confirm_calcom_booking(session_id, booking_uid, *, client=None)`** — signature CHANGÉE
  cette session : le kwarg `email=` a été RETIRÉ (remplacé par la vérification Cal.com
  interne, `_verify_calcom_booking`). Ne pas réintroduire un paramètre `email` non vérifié.
- **`_verify_calcom_booking(booking_uid)`** (nouveau, `intake_service.py`) : seule source de
  vérité pour l'email attendee — `GET {Config.CALCOM_API_BASE_URL}/bookings/{uid}`, exige
  `status=ACCEPTED` + `eventTypeId == Config.CALCOM_EVENT_TYPE_ID` (défaut 25). Nouvelles
  variables `Config.CALCOM_API_BASE_URL` (défaut `https://api-agenda.ai-mpower.com/v2`) et
  `Config.CALCOM_EVENT_TYPE_ID` (défaut `25`) — PAS posées dans Coolify (defaults suffisent,
  vérifié cohérent avec la prod réelle), à poser explicitement seulement si ces valeurs
  doivent un jour diverger de la prod actuelle.
- **`disableOnPrefill=true`** posé côté Cal.com (API, event type 25) sur les bookingFields
  natifs `name` et `email` — vérifié après coup que les 5 autres champs (`location`,
  `title`, `notes`, `guests`, `rescheduleReason`) n'ont pas été altérés par le PATCH
  (remplacement intégral du tableau `bookingFields`, jamais un merge partiel côté API
  Cal.com — toujours renvoyer le tableau COMPLET, jamais un sous-ensemble).
- **`agent_turn(session_id, user_message, ...)`** (existant, inchangé) : exige un
  `user_message` non vide — ne peut PAS parler en premier tout seul. L'amorce automatique
  (décision 7a ci-dessus) devra envoyer un premier message synthétique non vide côté
  frontend au montage de l'écran Assistant.
- **`ReportChatPanel.vue`** (`frontend/src/components/`) : pattern de chat réutilisable
  (rôles, bulles, indicateur réflexion, formulaire d'envoi, historique) — base structurelle
  pour le futur `IntakeAgentPanel.vue`, PAS un style à copier tel quel (le nouveau composant
  doit être sobre/exécutif, pas ludique, conforme au prompt Stitch §10.2).
- **`frontend/src/api/intake.js`** : actuellement 2 fonctions seulement (`startIntakeSession`,
  `submitIntakeForm`) — à étendre avec les appels agent/complete lors de l'implémentation.
- **`frontend/tests/e2e/intake-parcours.spec.ts`** : couvre aujourd'hui UNIQUEMENT les 3
  écrans du formulaire (US-IQ-01) — à étendre pour couvrir l'écran Assistant + les 3 issues
  de branche.
- **Plan déjà écrit** `docs/superpowers/plans/2026-07-10-us-iq-02-agent.md` : couvre le
  BACKEND uniquement (déjà exécuté, mergé `8b0f89b`) — sa section « Hors scope » liste
  explicitement le frontend comme tâche distincte, à planifier séparément (ce qu'on fait).

[MEMO inter-sessions — ajouts cette session]
- **Une story marquée `passes: true` avec des tests API directs qui passent peut être
  totalement inatteignable en usage réel** si rien côté frontend n'appelle jamais les
  endpoints concernés — le pattern « vérifié via API publique » (déjà utilisé pour US-IQ-04)
  est une preuve de correction du BACKEND, jamais une preuve d'atteignabilité PRODUIT. Le
  seul test qui aurait révélé ce trou plus tôt est un vrai clic utilisateur sur le site
  (SOP-011, déjà écrite avant cette session mais pas encore assez strictement appliquée à
  « est-ce que ce code est même appelé par un vrai parcours utilisateur »).
- **Ne jamais affirmer qu'une story/un composant « n'a jamais été construit » sur la seule
  foi de `passes: false` dans `prd.json`** — `passes: false` peut aussi vouloir dire « fait
  mais gated sur un critère précis restant » (ici : 2 échecs corpus). Toujours lire
  `progress.md` ET grepper le code réel avant d'affirmer une absence totale — erreur commise
  puis auto-corrigée dans cette même session, à ne pas répéter.
- **Une review de sécurité automatique peut arriver à tout moment après un commit/push** et
  révéler un trou réel dans un fix qu'on vient tout juste de livrer et déployer — cette
  session en a eu 3 (background review sur commit, sur push, plus le premier signalement) ;
  le premier signal (« spoofable-field ») était le seul pleinement actionnable, les 2
  suivants n'ont pas pu être lus en détail (contenu tronqué par un avertissement connecteur
  claude.ai sans rapport) — si un signal de review sécurité arrive tronqué/illisible, ne
  pas l'ignorer silencieusement, le signaler à Amine si son contenu reste inaccessible.
- Marque : Bassira (بصيرة) visible, `miroshark` technique. Jamais « prédiction » dans le copy
  commercial (ADR-002). URLs publiques toujours `bassira.ma` (ADR-013).

═══════════════════════════════════════════════════════════════════════════════
== SYNTHÈSE PRÉCÉDENTE (2026-07-11 soir/nuit) — historique SMTP Cal.com/ADR-IQ-08, [NEXT] ci-dessous CADUC (remplacé par la synthèse du 2026-07-12 en tête de fichier) ==
Synthèse complète et autonome — ne suppose la lecture d'aucune passation antérieure.

[ETAT]
- **Prod à jour** : `bassira.ma`/`prospectives.ai-mpower.com` (Coolify, app `u6pn5mr2pgi88s13un55pkzb`,
  serveur `serveuria`, IP `192.168.100.24`). `main` local et distant synchronisés, HEAD =
  `5c38b51` (dernier push : doc de clôture ADR-IQ-08). Conteneur miroshark actuel :
  `miroshark-u6pn5mr2pgi88s13un55pkzb-132756713856` (⚠️ le suffixe change à CHAQUE
  redéploiement Coolify — toujours re-vérifier avec `docker ps --filter name=miroshark` avant
  un `docker exec`, ne jamais réutiliser un nom de conteneur d'un tour précédent).
- **US-IQ-04** (emails contextualisés + réservation Cal.com) — `passes: true` dans
  `.ralph/prd.json`. Implémenté (7 tasks TDD), mergé, déployé, **vérifié réellement en prod** :
  email reçu (contenu conforme), réservation Cal.com réelle faite par Amine,
  `calcom_booking_uid` persisté en base. Un bug réel trouvé par Amine en testant (redirect
  post-booking renvoyait vers le formulaire `/devis` vide au lieu d'un écran de confirmation)
  → corrigé, déployé, vérifié (`fd0af3d`).
- **ADR-IQ-08** (playbook vivant + escalade silencieuse) — mergé dans `main` (`6a306e6`,
  1 conflit réel résolu proprement dans `intake_service.py`, sans perte de logique), déployé,
  endpoints admin vérifiés en prod (`401` sans auth, pas `404`). Pas d'entrée `.ralph/prd.json`
  dédiée (c'est une décision d'architecture documentée, pas une user story).
- **Gap Cal.com natif trouvé ET corrigé cette session** : les conteneurs Cal.com self-hosted
  (`calcom-a1354o9qgw8rdkszn56o9x3o` + `calcom-api-a1354o9qgw8rdkszn56o9x3o`) n'avaient AUCUNE
  config SMTP — zéro email natif Cal.com envoyé (ni au booker, ni à Amine comme host), alors
  que la réservation s'enregistrait bien dans l'agenda. **Corrigé** : 5 variables d'env posées
  sur le service Coolify `calcom-agenda` (UUID `a1354o9qgw8rdkszn56o9x3o`) via relais SMTP
  Resend (réutilise `RESEND_API_KEY` déjà utilisé par Bassira) : `EMAIL_SERVER_HOST=
  smtp.resend.com`, `EMAIL_SERVER_PORT=465`, `EMAIL_SERVER_USER=resend`,
  `EMAIL_SERVER_PASSWORD=<RESEND_API_KEY>`, `EMAIL_FROM=noreply@ai-mpower.com`. Service
  redémarré, `healthy`, confirmé par grep dans le conteneur (noms de variables vérifiés dans
  le bundle Next.js compilé déployé — PAS deviné depuis la doc générique Cal.com, RÈGLE N°2).
- **Google Meet CONFIRMÉ déjà connecté** sur l'event type id 25 (vérifié par
  `GET /v2/event-types/25` : `locations: [{"type":"integration","integration":"google-meet",
  "credentialId":2}]` + `defaultConferencingApp: google-meet` au niveau user) — Amine utilise
  Google Workspace pour son adresse pro, déjà lié côté Cal.com AVANT cette session (aucune
  action supplémentaire nécessaire de sa part, contrairement à ce que je pensais au début).
- **Architecture confirmée avec Amine (à ne pas re-questionner)** : DEUX emails séparés, deux
  systèmes distincts — (1) email Bassira/Resend = accusé de réception du brief (déjà fait,
  US-IQ-04, fonctionne) ; (2) email Cal.com natif = confirmation du RDV avec lien Google Meet
  (booker + host), maintenant débloqué par le fix SMTP. **Pas de duplication côté Bassira** —
  décision explicite d'Amine de ne PAS coder un 2e envoi via Resend pour la confirmation RDV,
  de laisser Cal.com gérer nativement sa propre notification.

[FAIT — cette session, dans l'ordre chronologique]
1. **US-IQ-04 implémenté** (plan `docs/superpowers/plans/2026-07-11-us-iq-04-email-calcom.md`,
   skill `executing-plans`, mode Inline, choisi par Amine) : audit R1 (échappement HTML),
   config Cal.com, templates fr/en/ar, constructeur CTA + lien booking, `_send_intake_
   confirmation` câblé dans `complete_routing`, endpoint `GET /api/intake/calcom-confirmed`.
   2 angles morts du plan corrigés en route (copy EN sans le mot « minutes », import pytest
   inutile cassant ruff).
2. **Merge + push `main`** (`d81fc91`), déployé, gates re-vérifiés (2170 passed, ruff clean).
3. **Vérification réelle en prod** : parcours Intake via API publique (governance
   `conseil_administration` → route `meeting`), email réel reçu et confirmé (Gmail MCP,
   thread `19f5044fc558f9c4`) — contenu exact conforme. **Faux positif détecté et écarté** :
   l'outil `mcp__claude_ai_Gmail__get_thread` affiche le lien Cal.com comme corrompu
   (`intake_session_id�6be1f8...`, `=fa` disparaît) — reproduction locale exacte de
   `render_template`/`_build_calcom_booking_link` a prouvé que LE CODE produit le lien intact ;
   la corruption est un artefact de décodage quoted-printable DANS L'OUTIL Gmail MCP, pas dans
   l'email réel. **Ne jamais faire confiance à cet outil pour un contenu URL exact** — toujours
   revérifier par reproduction locale du code si un lien semble corrompu dans son extraction.
4. **Réservation Cal.com réelle faite par Amine** (Chrome indisponible dans cet environnement,
   extension non connectée — Amine a réservé lui-même sur le lien fourni).
   `calcom_booking_uid = bPsTR8xUhWyYpD3pPMZbEp` confirmé persisté en base (requête Supabase
   directe via conteneur). ⚠️ Réservation réelle toujours active sur l'agenda Cal.com d'Amine,
   pas annulée (risque faible, créneau test).
5. **Bug réel signalé par Amine** : après réservation, redirigé vers `/devis` (formulaire A1-A8
   VIDE) au lieu d'un écran de confirmation — `QuoteView.vue` ne consommait jamais
   `?calcom_confirmed=1`. Root cause : le plan écrit (Task 6) choisissait cette URL de redirect
   sans jamais vérifier ce qu'elle affichait réellement. **Corrigé** (`fd0af3d`) : détection du
   query param, saut direct à l'écran de succès (étape 4), message dédié fr/en/ar
   (`quote.step3.calcomConfirmedTitle/Subtitle`), stepper masqué. Déployé, vérifié (bundle
   `QuoteView-B037gR5A.js` contient `calcom_confirmed`).
6. `US-IQ-04.passes = true` posé dans `.ralph/prd.json`, documenté dans `.ralph/progress.md`.
7. **Amine a signalé, en testant la réservation réelle** : aucun email reçu ni côté prospect ni
   côté admin, alors que la réservation existe dans l'agenda. Diagnostic par preuve système :
   `env | grep -iE "smtp|email|mail"` VIDE dans les 2 conteneurs Cal.com — confirmé root cause,
   PAS un bug Bassira (email Bassira lui-même déjà confirmé reçu au point 3).
8. **ADR-IQ-08 finalisé** : branche `feat/adr-iq-08-playbook-escalation` re-vérifiée par preuve
   système (2185 passed, ruff clean, build OK — ne PAS faire confiance à la mémoire d'une
   passation précédente sans reprouver, RÈGLE N°4). 1 conflit réel avec `main` (`main` avait
   avancé de 12 commits entre-temps via US-IQ-04) dans `intake_service.py` : les 2 branches
   ajoutaient des fonctions en fin de fichier sans chevauchement fonctionnel — résolu par
   concaténation simple (bloc `_log_escalation`/playbook HEAD, puis bloc
   `_send_intake_confirmation`/Cal.com main). Merge fast-forward dans `main` (`6a306e6`), gates
   re-vérifiés sur le résultat fusionné (2204 passed, ruff clean, build OK), poussé, déployé,
   endpoints admin vérifiés (`401`, pas `404`).
9. **Amine a demandé de fixer le SMTP Cal.com plutôt que dupliquer l'envoi côté Bassira**
   (choix explicite après question de clarification — j'avais d'abord proposé du code Bassira/
   Resend, Amine a préféré la solution native). Noms exacts des variables SMTP Cal.com
   vérifiés dans le bundle Next.js compilé RÉELLEMENT DÉPLOYÉ (pas depuis la doc générique
   context7, qui ne donnait pas les noms exacts pour cette version) : `EMAIL_SERVER_HOST`,
   `EMAIL_SERVER_PORT`, `EMAIL_SERVER_USER`, `EMAIL_SERVER_PASSWORD`, `EMAIL_FROM` (confirmés
   présents dans `/calcom/apps/web/.next/server/chunks/[root-of-the-server]__11_4bs2._.js` —
   `EMAIL_FROM_NAME` et `SMTP_SECURE` NE sont PAS lus par cette version, ne pas les poser).
   Credentials SMTP Resend vérifiés via doc officielle context7 (`/websites/resend`) :
   `smtp.resend.com:465`, user `resend`, password = clé API. Posées via API Coolify
   (`POST /api/v1/services/{uuid}/envs`, PAS `/applications/{uuid}/envs` — Cal.com est un
   *service* docker-compose Coolify, pas une *application* simple). Service redémarré
   (`POST /api/v1/services/{uuid}/restart`), confirmé `healthy`, variables confirmées
   injectées dans le nouveau conteneur (noms non-sensibles affichés, `EMAIL_SERVER_PASSWORD`
   jamais affiché — juste confirmé présent).
10. **Google Meet vérifié déjà connecté** — Amine a signalé que Meet + Calendar étaient déjà
    actifs par défaut sur son compte Google Workspace ; confirmé par `GET /v2/event-types/25`
    (`locations` contient déjà `google-meet` avec `credentialId: 2`). Aucune action OAuth
    supplémentaire nécessaire — mon guide initial (connecter l'app dans Settings > Apps) était
    déjà obsolète au moment où je l'ai donné.

[ALERTE]
- Réservation test réelle (`bPsTR8xUhWyYpD3pPMZbEp`) toujours active sur l'agenda Cal.com
  d'Amine — pas annulée, risque faible (créneau de test, pas un vrai prospect).
- Service Cal.com (`calcom-agenda`) redémarré 2 fois cette session (fix SMTP) — aucune
  régression observée (`healthy`, site public `200` après chaque redémarrage), mais à
  surveiller si Amine signale un souci sur l'agenda dans les heures qui suivent.

[BLOQUE / EN ATTENTE D'AMINE]
- Rien de bloquant. **NEXT immédiat** : Amine (ou la prochaine session) doit faire une
  NOUVELLE réservation test réelle sur `https://agenda.ai-mpower.com/a.mansouri/
  entretien-bassira-20-min` pour confirmer que les 2 emails natifs Cal.com (booker + host,
  avec lien Google Meet) partent bien maintenant que le SMTP est corrigé. Question posée à
  Amine juste avant la coupure de contexte, réponse pas encore reçue au moment de cette
  passation.

[NEXT]
1. **PRIORITÉ 1** : nouvelle réservation Cal.com test réelle → confirmer réception des 2 emails
   natifs Cal.com (booker + host `a.mansouri`), lien Google Meet présent dans l'email. Si OK :
   annuler/documenter le test, considérer le chantier Cal.com définitivement clos.
2. Si les emails natifs Cal.com ne partent toujours pas malgré le SMTP configuré : vérifier les
   logs du conteneur `calcom-a1354o9qgw8rdkszn56o9x3o` au moment d'une réservation
   (`docker logs <conteneur> --since 5m`) pour une erreur SMTP explicite (auth Resend,
   TLS, etc.) — ne pas re-deviner une cause, lire l'erreur réelle.
3. Annuler la réservation test `bPsTR8xUhWyYpD3pPMZbEp` sur l'agenda si elle encombre le
   calendrier d'Amine (pas fait cette session, pas demandé explicitement).
4. Rien d'autre en attente sur US-IQ-04/ADR-IQ-08 — les deux stories sont closes, déployées,
   vérifiées. Prochain chantier V2-B-intake selon `.ralph/prd.json` : US-IQ-05 (Porte 2 « AAR »)
   ou reprise de la finalisation US-IQ-02 (2 échecs corpus §10.3 encore à trancher par Amine,
   cf. `.ralph/progress.md` section US-IQ-02 — non touchée cette session).

[CTX]
- **Repo GitHub** : `--repo Afristrat/MiroShark` explicite sur toute commande `gh`.
- **Accès serveur** : `ssh -i /c/Users/amans/.ssh/serveurai_mnemo serveuria@192.168.100.24`
  (chemin Git Bash — forward slashes, PAS de backslashes Windows dans la commande `ssh -i`,
  sinon `Identity file not accessible`).
- **Coolify API** : `$env:COOLIFY_URL` = `http://192.168.100.24:8000`, token dans le coffre.
  App miroshark = `/api/v1/applications/u6pn5mr2pgi88s13un55pkzb`. Service Cal.com = 
  `/api/v1/services/a1354o9qgw8rdkszn56o9x3o` (nom Coolify : `calcom-agenda`) — **endpoints
  différents pour applications vs services** (`/applications/{uuid}/envs` PATCH vs
  `/services/{uuid}/envs` POST, `/services/{uuid}/restart` POST). Déploiements : lister via
  `/api/v1/deployments`, filtrer par `commit`, `status` passe `in_progress` → `finished`
  (déploiement Bassira ~5-6 min, redémarrage service Cal.com ~1 min).
- **Cal.com API v2** : hostname public `https://api-agenda.ai-mpower.com/v2/...` (ADR-IQ-03
  v3), header `cal-api-version: 2024-06-14` requis sur les écritures. Event type Intake : id
  `25`, slug `entretien-bassira-20-min`, owner `a.mansouri`, 20 min, `successRedirectUrl =
  https://bassira.ma/api/intake/calcom-confirmed`, `locations` inclut déjà `google-meet`.
  Clé `CALCOM_API_KEY` déjà en env Coolify miroshark.
- **Cal.com self-hosted, conteneurs** : `calcom-a1354o9qgw8rdkszn56o9x3o` (web app, lit
  `EMAIL_SERVER_*`/`EMAIL_FROM` pour SMTP, `GOOGLE_API_CREDENTIALS` pour OAuth Google) +
  `calcom-api-a1354o9qgw8rdkszn56o9x3o` (API v2). Code source dans `/calcom` (pas de
  `.env.example` en prod — vérifier les vrais noms de vars via
  `grep -c NOM_VAR "/calcom/apps/web/.next/server/chunks/[root-of-the-server]__11_4bs2._.js"`,
  UN nom à la fois avec chemin entre guillemets échappés, jamais de regex large — le hook
  anti-fuite bloque les patterns non ancrés sur une clé exacte).
- **`render_template` (email_service.py)** : simple `str.format`, AUCUN échappement HTML —
  toujours `html.escape()` manuellement tout contenu prospect avant injection.
- **Gmail MCP (`mcp__claude_ai_Gmail__*`)** : compte connecté = `tahirisophia1@gmail.com`.
  `get_thread` a un bug de décodage quoted-printable qui corrompt les URLs contenant `=XX`
  (hex-like) juste après un `=` littéral — NE JAMAIS conclure à un bug applicatif sur la seule
  base d'un lien affiché corrompu par cet outil ; toujours reproduire localement le code de
  rendu pour vérifier la source de vérité.
- **Chrome (`mcp__claude-in-chrome__*`)** : extension non connectée dans cet environnement au
  moment de cette session — ne pas supposer disponible, vérifier par `tabs_context_mcp` avant
  de compter dessus pour une vérification visuelle/browser.
- Fins de ligne : `.ralph/prd.json` = CRLF strict — vérifier après toute édition
  (`data.count(b'\r\n')` doit égaler le nombre total de `\n`).

[MEMO inter-sessions]
- **Les docs/plans peuvent être écrits en avance sur l'infra réelle ou sur ce qu'un écran
  affiche réellement** — 3e occurrence cette session (après ADR-IQ-03 et l'event type Cal.com
  lors de sessions précédentes) : le plan US-IQ-04 choisissait `/devis?calcom_confirmed=1`
  comme redirect sans jamais vérifier que `QuoteView.vue` consommait ce param — trouvé
  uniquement parce qu'Amine a testé manuellement. **Un plan écrit, même détaillé et self-reviewé,
  n'a jamais vérifié le comportement RÉEL d'un écran tiers qu'il ne code pas lui-même** —
  tester le parcours utilisateur bout en bout reste irremplaçable, même après un plan
  apparemment complet.
- **Un outil MCP peut lui-même introduire un artefact qui ressemble à un bug applicatif**
  (le décodage quoted-printable de Gmail MCP) — avant de déclarer un bug sur la foi d'un
  outil d'extraction/lecture, reproduire la source de vérité directement (ici : rejouer le
  code de rendu localement) plutôt que de faire confiance à la première lecture.
- **Une fonctionnalité "manquante" côté produit (email de confirmation RDV) peut avoir sa
  vraie cause dans une brique tierce non couverte par les tests du repo** (Cal.com self-hosted
  sans SMTP) — le réflexe RÈGLE N°4 (preuve système, jamais de supposition) a permis de
  distinguer en quelques commandes ce qui relevait du code Bassira (déjà vérifié OK) de ce qui
  relevait de l'infra Cal.com (cassé depuis le déploiement initial, jamais remarqué faute de
  test réel avant cette session).
- Marque : Bassira (بصيرة) visible, `miroshark` technique. Jamais « prédiction » dans le copy
  commercial (ADR-002). URLs publiques toujours `bassira.ma` (ADR-013).
