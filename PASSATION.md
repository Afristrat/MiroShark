== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-10 (soir, session très longue : merge US-IQ-01/03, incident prod résolu, US-IQ-02 codée+mergée+déployée, corpus §10.3 exécuté et revu, ADR-IQ-08 conçu — implémentation reportée) ==
Synthèse complète et autonome — ne suppose la lecture d'aucune passation antérieure.

[ETAT]
- **Prod saine** : `bassira.ma`/`prospectives.ai-mpower.com` sur gunicorn (Coolify, app
  `u6pn5mr2pgi88s13un55pkzb`, serveur `serveuria`, IP `192.168.100.24`). `main` local et
  distant synchronisés à `70c2788` (HEAD). Repo local sur `main`, aucune branche feature
  restante — toutes mergées et supprimées cette session.
- **US-IQ-01 (formulaire) + US-IQ-03 (routage) + US-IQ-02 (agent conversationnel)** :
  toutes mergées sur `main`, déployées, **vérifiées fonctionnelles en prod** (formulaire
  testé réellement après un incident corrigé — voir [FAIT] ; agent testé réellement via le
  corpus §10.3 avec le vrai modèle `qwen3.6-35b`). `.ralph/prd.json` : US-IQ-01 et US-IQ-03
  à `passes:true`. **US-IQ-02 reste volontairement `passes:false`** — le prompt v1 en prod
  a montré 2 échecs réels sur le corpus (voir [FAIT] point 4), un prompt v2 corrigé a été
  conçu mais **PAS ENCORE implémenté** (ADR-IQ-08, voir [BLOQUE]).
- **Clé virtuelle LiteLLM `bassira`** créée sur le proxy `litellm-proxy` (conteneur
  `blmesg55fcrs39723v74q0yt-220706150352`, fqdn `https://proxy.ai-mpower.com`), scoped
  `qwen3.6-35b` (demande explicite Amine). Câblage code fait (`create_intake_llm_client`
  dans `llm_client.py`), variables Coolify posées et confirmées présentes en prod
  (`INTAKE_LLM_API_KEY`, `INTAKE_LLM_BASE_URL`, `INTAKE_LLM_MODEL=qwen3.6-35b`).
- **ADR-IQ-08 conçu et documenté mais PAS implémenté** (`docs/intake/08-decisions-log.md`,
  plan complet `docs/superpowers/plans/2026-07-10-adr-iq-08-playbook-escalation.md`,
  9 tasks TDD) : escalade silencieuse (jamais vue du prospect, Amine seul notifié par
  email) + playbook vivant de corrections édité via `/admin` (PAS Google Docs — décision
  explicite d'Amine), relu par l'agent à chaque tour futur. **Amine a explicitement
  reporté l'exécution de ce plan** — rien codé, seule la conception (ADR + plan) est
  commitée et poussée.

[FAIT — cette session, dans l'ordre chronologique]
1. Merge PR #1 (US-IQ-01) puis PR #2 (US-IQ-03, retarget base → `main` avant merge) via
   `gh pr merge --merge`. `prd.json` mis à jour (`passes:true` sur les deux).
2. **Incident prod découvert et résolu** : Amine a testé le formulaire /devis en prod juste
   après le merge → erreur "Envoi impossible". Diagnostic systématique
   (`superpowers:systematic-debugging`) : logs backend → `PGRST205 Could not find the
   table 'public.intake_sessions'`. Cause racine confirmée par requête SQL directe : **la
   migration `supabase/migrations/20260709_001_intake_sessions.sql` n'avait jamais été
   appliquée en base de prod** — le merge déploie le code, PAS les migrations Supabase
   (projet Supabase séparé, hors pipeline de build Coolify). Fix : migration appliquée en
   transaction atomique (`docker exec supabase-db-dgybi9q5e2ggkjtaxlu2ukai psql`), cache
   PostgREST rafraîchi. Vérifié réellement : `POST /api/intake/session` → 200 en prod.
   **LEÇON PERMANENTE pour tout le chantier Intake** : après merge d'une PR contenant une
   migration `supabase/migrations/*.sql`, TOUJOURS vérifier/appliquer la migration en base
   de prod — ce n'est jamais automatique.
3. **US-IQ-02 codée en TDD complet** (plan `docs/superpowers/plans/2026-07-10-us-iq-02-agent.md`,
   7 tasks + 1 câblage LLM correctif, tous commités séparément) : schéma jsonschema strict
   de sortie agent, system prompts fr/en/ar v1 (texte exact §10.1 fr, traductions fidèles
   en/ar), `agent_turn()` (budget 7 tours vérifié en base, persistance immédiate,
   confidential_flags sans contenu, repli gracieux si LLM down), endpoint
   `POST /api/intake/session/<id>/agent/turn`, `create_intake_llm_client` (gateway/clé
   dédiées Bassira), corpus d'évaluation hand-run (`backend/scripts/test_intake_agent_corpus.py`).
   Mergé sur `main`, poussé. Suite pytest verte à chaque étape (2151 passed / 1 flaky
   pré-existant documenté / 42 skipped).
4. **Corpus §10.3 exécuté en conditions réelles** (dans le conteneur backend de prod, vrai
   appel LLM `qwen3.6-35b`) : **7/10 scénarios conformes**. Sur les 3 signalés en échec :
   - 1 **faux positif du script** (grep naïf sur « précision » matchant même une négation
     — l'agent refuse bien la prédiction, comportement conforme).
   - 2 **échecs réels** : (a) sur les tours à forte charge (injection de prompt, demande de
     prédiction), l'agent dépasse la limite « ≤3 phrases » en combinant disclosure+refus+
     relance ; (b) sur un scénario où le prospect livre un contenu confidentiel dès son
     premier message, l'agent traite le flag SANS s'être présenté comme IA d'abord —
     violation de la règle de transparence (AI Act art. 50) qui doit pourtant primer.
   Documenté en détail dans `.ralph/progress.md` (section « US-IQ-02 — Corpus d'évaluation
   §10.3 »). Un rapport visuel (Artifact HTML, les 10 transcripts réels + verdicts) a été
   généré et montré à Amine pour revue — pas persisté nulle part de façon durable côté
   repo, à régénérer si besoin (voir [MEMO]).
5. **Conception du prompt v2 + architecture ADR-IQ-08** (via skill `/prompt-engineer-pro`,
   sur demande explicite d'Amine) : corrige les 2 échecs réels (Règle 0 = disclosure
   toujours en premier, non négociable ; format de message qui fusionne disclosure+refus
   en une seule phrase plutôt que de compter les phrases) + ajoute un champ `escalation`
   optionnel à la sortie JSON + durcissement général contre l'imprévu (section « FACE À
   L'IMPRÉVU », refus par défaut plutôt que deviner). Débat avec Amine sur le sens
   d'« escalade silencieuse » (clarifié : invisible pour le prospect qui teste un
   jailbreak, PAS invisible pour Amine — lui seul reçoit/corrige, jamais d'auto-
   apprentissage automatique non supervisé). Amine a tranché : stockage du playbook via
   une page `/admin` (pas Google Docs, pour éviter latence/dépendance OAuth externe dans
   le chemin chaud de chaque tour). ADR-IQ-08 écrit, plan complet écrit (9 tasks TDD),
   **implémentation explicitement reportée par Amine** (session déjà très longue).
6. ADR-IQ-08 + plan commités et poussés sur `main` (`70c2788`) — documentation seule,
   aucun code touché.

[ALERTE]
- ⚠️ **Coffre DPAPI `SERVER_HOST` désynchronisé** : peut contenir `192.168.100.11`
  (périmé) au lieu de `192.168.100.24` (IP réelle confirmée cette session, SSH testé,
  hostname `serveuria-MS-7D98`). **Cette session MiroShark ne peut PAS corriger le coffre**
  (sandbox de permissions limité au repo courant) — nécessite la session **home** (CWD
  `C:\Users\amans`). Non re-vérifié si corrigé entre-temps par une autre session — vérifier
  `$env:SERVER_HOST` avant de faire confiance à l'IP, sinon utiliser `.24` en dur comme
  vérifié cette session.
- ⚠️ Aucun CI/check configuré sur `Afristrat/MiroShark` (`statusCheckRollup` vide) — rien
  ne bloque un merge cassé automatiquement, seule la vigilance manuelle (pytest+ruff avant
  chaque commit) protège.
- ⚠️ Test `tunnel-commercial.spec.ts` toujours en échec en environnement frontend-only
  (`vite preview` sans backend) — non lié, déjà expliqué dans une passation antérieure
  (US-IQ-01), ne pas re-diagnostiquer.
- ⚠️ `COOLIFY_API_TOKEN` du coffre DPAPI périmé — token de contournement utilisé cette
  session, valide sur le serveur : `/home/serveuria/.credentials/coolify-api-token-claude-20260708`.
- ⚠️ **Déploiement Coolify observé lent/asynchrone** cette session (jusqu'à ~10-15 min
  entre un push et le conteneur effectivement recréé avec le nouveau code) — toujours
  vérifier `docker ps --filter name=u6pn5mr2pgi88s13un55pkzb --format "{{.CreatedAt}}"` ET
  grepper une chaîne de code récente dans le conteneur (ex.
  `docker exec <nom> grep -c create_intake_llm_client /app/backend/app/utils/llm_client.py`)
  avant de supposer qu'un déploiement est effectif — ne jamais se fier au seul push.

[BLOQUE / EN ATTENTE D'AMINE]
- **Implémentation d'ADR-IQ-08** (playbook + escalade) — plan prêt à exécuter
  (`docs/superpowers/plans/2026-07-10-adr-iq-08-playbook-escalation.md`), reporté par
  Amine. Prochaine session : proposer le choix Subagent-Driven vs Inline comme d'habitude,
  PUIS exécuter le plan tel quel (déjà relu en self-review, cohérent avec le code existant
  — pas besoin de reconcevoir).
- **Gate §10.3 sur le prompt v2** — une fois ADR-IQ-08 implémenté et le prompt v2 déployé,
  ré-exécuter le corpus (`backend/scripts/test_intake_agent_corpus.py`, dans le conteneur
  prod) pour vérifier que les 2 échecs réels sont corrigés, avant de marquer
  `US-IQ-02.passes=true`.
- Rotation `SERVER_HOST`/`COOLIFY_API_TOKEN` dans le coffre DPAPI (session home requise).

[NEXT]
1. **PRIORITÉ 1** : reprendre l'exécution du plan ADR-IQ-08 (9 tasks, TDD, déjà écrit et
   auto-revu) — demander à Amine Subagent-Driven vs Inline, puis exécuter task par task
   exactement comme US-IQ-02 (test échoue → implémente → test passe → commit).
2. Une fois ADR-IQ-08 mergé/déployé : vérifier le déploiement effectif (cf. [ALERTE] sur la
   lenteur Coolify — grep le code dans le conteneur, pas juste `docker ps`), puis
   ré-exécuter le corpus §10.3 dans le conteneur prod avec le prompt v2.
3. Documenter le nouveau résultat du corpus dans `.ralph/progress.md`, revue humaine des
   critères 9-10 par Amine, puis marquer `US-IQ-02.passes=true` + `completedAt` dans
   `.ralph/prd.json` si le gate passe.
4. Si échec persistant sur un critère : ajuster le prompt (v2 → v3), **jamais de
   contournement dans le code** (règle explicite §10.3) — ou, une fois ADR-IQ-08 en place,
   Amine peut directement ajouter une correction au playbook via `/admin/agent-playbook`
   sans re-toucher au code.
5. Ensuite : US-IQ-04 (emails contextualisés + Cal.com, dépend de US-IQ-03 déjà mergée) est
   la suite naturelle du chantier Intake — ou US-208 (Redis+RQ PDF) en parallèle. Décision
   à Amine.

[CTX]
- **Repo GitHub** : toujours `--repo Afristrat/MiroShark` explicite sur toute commande `gh`.
- **Accès serveur** : `ssh -i C:\Users\amans\.ssh\serveurai_mnemo serveuria@192.168.100.24`.
- **LiteLLM proxy** : conteneur `blmesg55fcrs39723v74q0yt-220706150352`, API interne
  `http://localhost:4000` (curl absent dans ce conteneur — `python3 urllib.request` via
  `docker exec`). Master key : env `LITELLM_MASTER_KEY` du conteneur (jamais affichée).
  34+ clés virtuelles existantes (dont `bassira`, scoped `qwen3.6-35b`).
- **Supabase prod Bassira** : conteneur `supabase-db-dgybi9q5e2ggkjtaxlu2ukai` (service
  Coolify `supabase-miroshark`). Appliquer une migration :
  `cat migration.sql | ssh ... 'docker exec -i supabase-db-dgybi9q5e2ggkjtaxlu2ukai psql
  -U postgres -v ON_ERROR_STOP=1'` enveloppé `BEGIN;`/`COMMIT;` pour rollback auto.
- **Contrat agent US-IQ-02** (v1, à étendre par ADR-IQ-08) : `POST
  /api/intake/session/<id>/agent/turn` body `{"message": "<texte>"}` →
  `{success, data:{session_id, state, agent_turns, message, close, route?}}`. 403
  `AGENT_BUDGET_EXHAUSTED` au-delà de 7 tours. 502 `AGENT_INVALID_OUTPUT` si JSON non
  conforme. Le schéma de sortie interne (jamais renvoyé tel quel au client) sera étendu par
  ADR-IQ-08 avec un champ `escalation` optionnel.
- **Pattern service Intake** (`backend/app/services/intake_service.py`, ~850 lignes
  maintenant) : `start_session`, `submit_form`, `complete_routing` (US-IQ-01/03),
  `_validate_agent_output`, `_build_agent_messages`, `agent_turn`,
  `_close_session_gracefully` (US-IQ-02). Toutes les fonctions publiques prennent
  `client: Any = None` (injecté en test via `FakeSupabase`, sinon `get_supabase_admin()`).
- pytest backend : ~2151 passed / 1 flaky pré-existant documenté / 42 skipped (~5 min).
- Fins de ligne : `prd.json` = CRLF — réécrire en CRLF après édition Node/outil.
- Plans de référence (style à reproduire pour toute nouvelle story TDD) :
  `docs/superpowers/plans/2026-07-10-us-iq-02-agent.md` (exécuté, complet) et
  `docs/superpowers/plans/2026-07-10-adr-iq-08-playbook-escalation.md` (prêt, pas exécuté).

[MEMO inter-sessions]
- **Pattern « migration Supabase non auto-déployée »** (CRITIQUE, déjà vécu deux fois ce
  chantier) : chaque story avec une migration SQL doit être suivie d'une vérification
  explicite en base de prod après merge — le déploiement Coolify ne déploie QUE le code
  applicatif. Ne jamais supposer qu'un merge = migration appliquée.
- **Sandbox de session par répertoire** (confirmé empiriquement) : une session dont le CWD
  est ce repo ne peut PAS lire/écrire dans `~/.claude/secrets/` (Bash ET PowerShell
  bloqués) — même avec autorisation verbale explicite d'Amine. Toute correction du coffre
  DPAPI doit passer par la session **home** (CWD `C:\Users\amans`).
- **Séquençage secrets** : toute clé/token généré côté serveur transite uniquement en
  variable shell serveur ou fichier temporaire supprimé aussitôt après usage — jamais
  affiché dans le chat (pattern utilisé pour la clé LiteLLM `bassira` cette session).
- **« Escalade silencieuse » ≠ boîte noire** (clarification actée avec Amine, structurante
  pour toute future feature de supervision d'agent) : silencieux = invisible pour
  l'utilisateur qui teste le système, PAS invisible pour l'opérateur humain qui supervise.
  Toujours distinguer les deux avant de juger qu'un mécanisme d'escalade/logging pose un
  problème d'auditabilité.
- **Convention intercepteur axios** (`frontend/src/api/client.js`) : les fonctions
  retournent DIRECTEMENT `{success, data}` — jamais destructurer `{ data }` puis relire
  `.data`. Vérifié une fois de plus en lisant `AdminBrandingView.vue` cette session.
- Marque : Bassira (بصيرة) visible, `miroshark` technique. Jamais « prédiction » dans le
  copy (ADR-002). URLs publiques bassira.ma TOUJOURS (ADR-013). i18n fr/en/ar parité
  stricte (ADR-008). LLM : modèle/gateway TOUJOURS choisis par Amine, jamais par l'IA
  (ADR-004/ADR-IQ-06) — respecté cette session à chaque étape (clé/modèle 35B, choix
  `/admin` vs Google Docs, tout tranché par Amine).

— fin passation —
