== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-11 (nuit, session très longue : ADR-IQ-08 complet non mergé, diagnostic email intake + correction ADR-IQ-03 + création event type Cal.com réel, plan US-IQ-04 écrit — exécution en attente du choix d'Amine) ==
Synthèse complète et autonome — ne suppose la lecture d'aucune passation antérieure.

[ETAT]
- **Prod inchangée depuis le début de session** : `bassira.ma`/`prospectives.ai-mpower.com`
  sur gunicorn (Coolify, app `u6pn5mr2pgi88s13un55pkzb`, serveur `serveuria`, IP
  `192.168.100.24`). Déployé = `e6d6bb3` (docs uniquement, poussé en tout début de
  session). Rien de fonctionnel n'a été déployé cette session — tout le travail (ADR-IQ-08
  complet, plan US-IQ-04) vit sur des branches locales NON mergées, NON poussées.
- **3 branches actives créées cette session** (repo local `C:\Users\amans\OneDrive\Projets\MiroShark`) :
  - `feat/adr-iq-08-playbook-escalation` (HEAD `792ec5d`) — **ADR-IQ-08 100% implémenté,
    9/9 tasks, tous les gates verts** (pytest 2184 passed, ruff 0 erreur, npm build OK).
    **PAS mergée, PAS poussée, aucune PR ouverte.**
  - `feat/us-iq-04-email-calcom` (HEAD `3d5f1fb`) — **uniquement le plan d'implémentation
    écrit et commité** (`docs/superpowers/plans/2026-07-11-us-iq-04-email-calcom.md`,
    7 tasks TDD). **Zéro code d'implémentation.** Créée à partir de `main` (donc contient
    déjà la correction ADR-IQ-03 v3).
  - `main` local est **1 commit en avance sur `origin/main`** (`a98ac0c`, correction
    ADR-IQ-03 — docs uniquement, pas encore poussé).
  - Deux worktrees pré-existantes non liées à cette session (`worktree-agent-a189a386`,
    `worktree-agent-a2980770`) — ne pas y toucher, ne pas confondre avec les branches
    ci-dessus.
- `.ralph/prd.json` : US-IQ-01, US-IQ-02, US-IQ-03 à `passes:true` (mergées sessions
  précédentes). US-IQ-04, US-208, US-IQ-05/06/07 toujours `passes:false`.
- **Session interrompue exactement au moment où Amine devait choisir le mode d'exécution
  du plan US-IQ-04** (Subagent-Driven vs Inline) — question posée, jamais répondue avant
  la bascule /clear.

[FAIT — cette session, dans l'ordre chronologique]
1. **Auto-correction en tout début de session** : la passation précédente n'avait pas été
   citée dans la toute première réponse (règle de preuve d'injection ratée) — corrigé
   immédiatement sur signalement d'Amine, fichier persisté relu intégralement.
2. **Rattrapage d'un residu de la session précédente** : `docs/superpowers/plans/2026-07-10-us-iq-02-agent.md`
   n'avait jamais été commité malgré la passation qui l'affirmait ; `PASSATION.md` avait
   une mise à jour locale jamais poussée. Les deux corrigés et poussés (`e6d6bb3`).
3. **ADR-IQ-08 implémenté intégralement en Inline** (choix d'Amine), 9 tasks TDD, sur
   branche `feat/adr-iq-08-playbook-escalation` :
   - Task 1 : migration `intake_agent_escalations` + `intake_agent_playbook`
     (`20260710_001_intake_agent_playbook.sql`), data-dictionary à jour (13→15 tables).
   - Task 2 : champ `escalation` requis dans `AGENT_TURN_OUTPUT_SCHEMA` — a aussi corrigé
     2 tests pré-existants non anticipés par le plan écrit.
   - Task 3 : `_log_escalation` (logging + notification email best-effort,
     `INTAKE_ESCALATION_NOTIFY_EMAIL`). **Faille XSS détectée par la revue de sécurité
     automatique du commit** (`user_message` injecté sans échappement dans l'email HTML de
     notification à Amine) — corrigée immédiatement (`html.escape`), verrouillée par test.
   - Task 4 : `_fetch_active_playbook` + injection du playbook dans le system prompt.
   - Task 5 : **prompt v2 fr/en/ar** (Règle 0 disclosure en premier, format fusionné
     identité+refus, champ `escalation` dans la sortie JSON) — remplace le v1 qui avait 2
     échecs réels sur le corpus §10.3 (session précédente).
   - Task 6/7 : endpoints admin `/api/admin/quotes/intake/escalations` et `/playbook`.
     **Le plan prévoyait de mocker `require_super_admin` après import — ça ne marche pas**
     (décorateur déjà appliqué à la fonction de route au moment de l'import). Réécrit avec
     un vrai JWT + whitelist (pattern `test_unit_admin_organizations.py`).
   - Task 8 : vue `AdminAgentPlaybookView.vue` + entrée dans le menu Admin (`AppHeader.vue`
     — hors scope du plan écrit mais nécessaire, sinon la page n'était atteignable qu'en
     tapant l'URL). Tokens `--wi-*` alignés sur les vraies valeurs de repli déjà en usage
     (le plan avait deviné d'autres couleurs).
   - Task 9 : gate `test_flask_routes_are_documented_or_allowlisted` cassé par les 4
     nouvelles routes (non anticipé) — corrigé en les allowlistant (même statut que les
     routes sœurs `/api/admin/quotes/*`).
4. **Diagnostic d'un signalement réel d'Amine (SOP-003)** : « je n'ai pas reçu de mail
   après une demande ». Investigation complète (logs conteneur, base Supabase directe,
   filesystem `uploads/quotes/`) : **PAS un bug**. Les 2 demandes test d'Amine
   (`q_d955bf4b`, `q_e396a14e`) sont passées par le **nouveau flow Intake** (US-IQ-01/03),
   pas par l'ancien `/devis`. Le code de `submit_form` (`intake_service.py:302-319`) écrit
   délibérément `package_id=None` (normal, pas de package choisi à ce stade) et **n'appelle
   aucune fonction d'envoi d'email** — c'est exactement le trou que US-IQ-04 doit combler.
   **Fausse piste corrigée en cours de route** : j'avais d'abord cru `resend` non installé
   en testant `python3` système au lieu du venv `uv` dans le conteneur — le paquet est en
   réalité bien présent et l'ancien `/devis` envoie ses emails normalement.
5. **ADR-IQ-03 corrigée v2→v3** (doc périmée découverte en préparant le plan US-IQ-04) :
   la v2 affirmait un appel API Cal.com en réseau Docker interne (`localhost:3002`) —
   jamais confirmé fonctionnel. Sonde live comparative faite en direct : le hostname
   public `https://api-agenda.ai-mpower.com/v2/...` atteint réellement l'API (erreur JSON
   propre sur clé invalide) ; `agenda.ai-mpower.com/api/v2` est bloqué Cloudflare (« DNS
   points to prohibited IP »). 4 fichiers docs corrigés + `08-decisions-log.md`
   (ADR-IQ-03 v3). **Auto-correction supplémentaire** : ma première rédaction de la v3
   affirmait « miroshark et calcom-api sont sur des réseaux Docker disjoints » comme fait
   confirmé — en relisant ma propre mémoire `reference_calcom_agenda`, cette affirmation
   faisait en réalité partie d'une confusion antérieure jamais vérifiée. Reformulé sans
   cette affirmation non prouvée (le seul fait solide : le hostname public marche, point).
6. **Event type Cal.com « Entretien Bassira — 20 min » créé réellement** — il n'existait
   PAS malgré sa mention partout (ADR-IQ-03, spec, prd.json depuis le 2026-07-09 : doc
   écrite en avance sur l'infra). Sur demande explicite d'Amine (« Crée moi l'événement
   toi-même »), créé via `POST /v2/event-types` (header `cal-api-version: 2024-06-14`
   requis) : id `25`, slug `entretien-bassira-20-min`, 20 min, owner `a.mansouri`. URL de
   réservation confirmée 200 OK : `https://agenda.ai-mpower.com/a.mansouri/entretien-bassira-20-min`.
   ⚠️ Créé SANS visioconférence (`locations: []`) — les autres event types du compte ont
   Google Meet configuré, celui-ci non (à ajouter manuellement dans l'UI Cal.com par
   Amine si souhaité).
7. **Plan US-IQ-04 écrit** (`docs/superpowers/plans/2026-07-11-us-iq-04-email-calcom.md`,
   skill `superpowers:writing-plans`) — 7 tasks TDD complètes avec code intégral : audit/fix
   R1 (échappement HTML du contenu prospect dans l'email existant, faille similaire à celle
   trouvée au point 3), config Cal.com, 3 templates email localisés fr/en/ar + CTA par
   branche (self_service/quote_48h/meeting), constructeur de lien de réservation Cal.com
   (pas d'appel API nécessaire — page publique statique), câblage dans `complete_routing`
   (best-effort, même contrat que `_log_escalation`), endpoint de capture de confirmation
   Cal.com (`GET /api/intake/calcom-confirmed`, via `forwardParamsSuccessRedirect`, PAS un
   webhook entrant — celui-ci reste hors scope V1), gates finaux + vérification réelle en
   prod (réservation test + email réel). Self-review fait, aucun placeholder, signatures
   cohérentes entre tasks. **Amine a répondu « 1. et 2. après »** à la question d'ordre
   (US-IQ-04 d'abord, finalisation ADR-IQ-08 ensuite) — **la question suivante (Subagent-
   Driven vs Inline pour exécuter ce plan) était posée, sans réponse au moment du /clear.**

[ALERTE]
- ⚠️ **2 branches complètes/en cours non mergées, non poussées** — tout le travail de
  cette session est local uniquement. Si la machine ou le repo est perdu avant merge, tout
  ce travail (ADR-IQ-08 + plan US-IQ-04 + corrections ADR-IQ-03) disparaît.
- ⚠️ `main` local 1 commit en avance sur `origin/main` (correction ADR-IQ-03, docs
  uniquement) — jamais poussé cette session, à faire ou confirmer avec Amine.
- ⚠️ **Mutation réelle sur l'infra Cal.com de production** cette session : un nouvel event
  type a été créé via API sur l'instance `agenda.ai-mpower.com` (autorisation explicite
  d'Amine). Pas de rollback fait ni prévu — c'est un ajout, pas une modification d'un
  event type existant, risque faible.
- ⚠️ Tant que US-IQ-04 n'est pas implémenté, **aucun prospect passant par le nouveau flow
  Intake ne recevra d'email de confirmation** — comportement actuel en prod, connu et
  documenté, pas un bug à corriger en urgence hors de ce chantier.
- ⚠️ Rien de nouveau sur les alertes de la session précédente (coffre `SERVER_HOST`/
  `COOLIFY_API_TOKEN` périmés, CI absent sur le repo, test `tunnel-commercial.spec.ts`
  connu en échec hors-scope) — toujours valables, non revérifiées cette session.

[BLOQUE / EN ATTENTE D'AMINE]
- **Choix du mode d'exécution du plan US-IQ-04** (Subagent-Driven vs Inline) — question
  posée en toute fin de session, sans réponse. **Reprendre exactement ici.**
- Finalisation ADR-IQ-08 (merge/PR/déploiement + re-run corpus §10.3 avec le prompt v2)
  — explicitement reportée après US-IQ-04 par Amine (« 1. et 2. après »).
- Décision Amine en attente (non bloquante) : ajouter une visioconférence Google Meet à
  l'event type Cal.com `entretien-bassira-20-min` — pas fait, pas demandé explicitement.

[NEXT]
1. **PRIORITÉ 1** : redemander à Amine (ou reprendre directement si le premier message est
   un simple « go »/« reprends » sans autre précision — cf. protocole reprise automatique)
   le mode d'exécution du plan `docs/superpowers/plans/2026-07-11-us-iq-04-email-calcom.md`,
   puis l'exécuter task par task (TDD : test échoue → implémente → test passe → commit),
   sur la branche `feat/us-iq-04-email-calcom` déjà créée.
2. Task 7 du plan US-IQ-04 exige une vérification RÉELLE en prod (pas seulement les tests
   unitaires) : réservation Cal.com test réelle + email réel reçu, AVANT de marquer
   `US-IQ-04.passes=true` dans `.ralph/prd.json`. Ne pas sauter cette étape.
3. Étape Task 7 Step 5 du plan : poser `successRedirectUrl` sur l'event type Cal.com (id 25)
   via `PATCH /v2/event-types/25` — **uniquement APRÈS** que l'endpoint
   `/api/intake/calcom-confirmed` soit effectivement déployé en prod (sinon un prospect
   réel serait redirigé vers un 404).
4. Une fois US-IQ-04 mergé/déployé/vérifié : reprendre la finalisation d'ADR-IQ-08 (branche
   `feat/adr-iq-08-playbook-escalation`, déjà prête, 9/9 tasks, gates verts) — proposer
   merge/PR à Amine, déployer, puis ré-exécuter le corpus §10.3 avec le prompt v2 pour
   enfin marquer `US-IQ-02.passes=true`.
5. Vérifier si `main` local doit être poussé (1 commit en avance, correction ADR-IQ-03
   docs-only) — probablement oui, à faire au prochain point de contact avec Amine.

[CTX]
- **Repo GitHub** : `--repo Afristrat/MiroShark` explicite sur toute commande `gh`.
- **Accès serveur** : `ssh -i C:\Users\amans\.ssh\serveurai_mnemo serveuria@192.168.100.24`.
- **Gotcha critique découvert cette session** : dans le conteneur backend, `python3`
  (système) ≠ le venv réellement utilisé par gunicorn (`uv run gunicorn ...` → dépendances
  dans `backend/.venv`). Pour vérifier un paquet Python installé en prod, TOUJOURS
  `docker exec <conteneur> sh -c 'cd /app/backend && uv run python3 -c "import X"'`, jamais
  `python3` nu — sinon faux négatif garanti (vécu cette session avec `resend`).
- **Cal.com API v2** : hostname public `https://api-agenda.ai-mpower.com/v2/...` (ADR-IQ-03
  v3), chemin SANS préfixe `/api`. `POST /v2/event-types` exige le header
  `cal-api-version: 2024-06-14`. Event type Intake : id `25`, slug
  `entretien-bassira-20-min`, owner `a.mansouri`, 20 min, sans visioconf. Clé
  `CALCOM_API_KEY` déjà posée en env Coolify miroshark (2026-07-09).
- **`render_template` (email_service.py) ne fait AUCUN échappement HTML** — simple
  `str.format`. TOUJOURS `html.escape()` manuellement tout contenu prospect avant
  injection (pattern déjà appliqué dans `_log_escalation` et prévu dans le plan US-IQ-04
  Task 1/5). Deux failles de ce type trouvées et corrigées cette session
  (`_log_escalation` par revue auto, `_send_client_confirmation` par audit R1 planifié).
- **Endpoints `@require_super_admin` en test** : le décorateur est appliqué à la fonction
  de route au moment de l'IMPORT du module — monkeypatcher `require_super_admin` après
  coup ne défait rien. Utiliser un vrai JWT + `BASSIRA_SUPER_ADMIN_EMAILS` (pattern complet
  dans `tests/test_unit_admin_organizations.py`, repris dans
  `tests/test_unit_admin_intake_agent.py`).
- **`complete_routing()` (intake_service.py)** est le point d'accroche explicite documenté
  pour US-IQ-04 (son propre docstring le dit : « Ne gère PAS l'email de confirmation ni la
  réservation Cal.com — US-IQ-04, qui dépend de cette story »).
- **`qo.get_quote_payload_from_supabase(quote_id, client=cli)`** (quote_ownership.py) est
  la fonction existante pour récupérer l'email/nom/société d'un prospect Intake depuis
  `quote_ownership.payload` — pas de duplication à créer.
- pytest backend fin de session : 2184 passed / 1 flaky pré-existant documenté
  (`test_md_hash_stable_with_deterministic_enricher`) / 42 skipped (WeasyPrint absent).
- Fins de ligne : `prd.json` = CRLF — réécrire en CRLF après édition Node/outil.

[MEMO inter-sessions]
- **Les docs peuvent être écrites en avance sur l'infra réelle** (leçon structurante de
  cette session, deux fois : ADR-IQ-03 décrivait un mécanisme jamais vérifié fonctionnel ;
  l'event type Cal.com était documenté partout sans exister). Avant de construire sur une
  affirmation d'un doc/ADR/prd.json concernant un système EXTERNE, revérifier par preuve
  système directe (règle fondamentale n°4) — ne jamais faire confiance à la doc seule pour
  un fait d'infra tiers.
- **Une mémoire peut elle-même contenir une confusion non résolue** — la mémoire
  `reference_calcom_agenda` mentionnait « réseaux Docker disjoints » comme partie d'une
  « confusion initiale », pas comme un fait confirmé ; je l'avais quand même réécrit comme
  un fait affirmatif dans l'ADR au premier jet. Toujours relire le texte EXACT d'une
  mémoire avant de la citer comme preuve, pas juste son intitulé/résumé.
- **Zéro dette de plan** (extension de la RÈGLE N°3) : un plan écrit par une session
  précédente peut lui-même avoir des angles morts non anticipés (tests d'auth cassés dans
  ADR-IQ-08 Task 6/7, gate OpenAPI non prévu, 2 tests pré-existants cassés par un schéma
  étendu) — les corriger au fil de l'exécution plutôt que de suivre le plan aveuglément,
  et le documenter dans le message de commit.
- Marque : Bassira (بصيرة) visible, `miroshark` technique. Jamais « prédiction » dans le
  copy (ADR-002). URLs publiques bassira.ma TOUJOURS (ADR-013). i18n fr/en/ar parité
  stricte (ADR-008). LLM/modèles : toujours choisis par Amine (ADR-004/ADR-IQ-06).

— fin passation —
