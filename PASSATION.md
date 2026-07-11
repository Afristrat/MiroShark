== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-11 (soir/nuit : US-IQ-04 + ADR-IQ-08 mergés et déployés, SMTP Cal.com corrigé, Google Meet confirmé connecté — reste à faire une réservation test réelle pour valider les 2 emails natifs Cal.com) ==
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
