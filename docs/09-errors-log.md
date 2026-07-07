# Errors Log — Bassira

> QUAND écrire ici : tout bug > 15 min de debug, toute erreur de prod, toute fausse
> piste coûteuse. Claude Code : au DÉBUT d'une session de debug, lire ce fichier —
> l'erreur a peut-être déjà été payée. Les patterns/pièges de développement vivent aussi
> dans `.ralph/progress.md` (§ Codebase Patterns) — ce fichier consolide les erreurs
> PAYÉES avec leur cause racine.

## Format d'entrée
### {date} — {symptôme en une ligne}
- **Contexte** : {où, en faisant quoi}
- **Cause RACINE** : {la vraie cause, pas le symptôme}
- **Fix** : {ce qui a corrigé, commit si pertinent}
- **Leçon généralisable** : {ce qui évitera la récidive — si ça mérite une règle,
  la promouvoir dans CLAUDE.md ou en ADR}

## Entrées (amorcées depuis les erreurs déjà payées en v1 — passations)

### 2026-05-22 — /admin/analytics affichait des KPI déconnectés de la réalité
- **Contexte** : dashboard admin en prod Coolify.
- **Cause RACINE** : KPI calculés depuis le filesystem (`outcome.json`, `quote_*.json`)
  alors que les volumes Coolify sont réinitialisés à chaque deploy — la source de vérité
  était devenue Supabase depuis US-114.
- **Fix** : refonte `get_admin_analytics()` sur `simulation_ownership`/`quote_ownership`
  (commit `67c25ff`), fail-soft si Supabase down.
- **Leçon généralisable** : **aucune donnée métier persistante sur `backend/uploads/`**
  — promu en règle CLAUDE.md + ADR-005. Le payload riche des devis a le même défaut,
  toujours ouvert (US-203).

### 2026-05-22 — /client/dashboard bloqué « provide X-Org-Id header »
- **Contexte** : super-admin multi-org en prod.
- **Cause RACINE** : `_resolve_target_org` exige X-Org-Id quand l'user a > 1 org, mais
  l'interceptor axios ne propageait jamais ce header.
- **Fix** : header `X-Org-Id: <auth.currentOrgId>` injecté globalement + sélecteur d'org
  (commit `67c25ff`).
- **Leçon généralisable** : tout contrat implicite backend↔frontend (headers attendus)
  doit être porté par l'interceptor central, pas par des appels individuels. Reste ouvert :
  currentOrgId non persisté au refresh (US-211).

### 2026-05-07 — Génération de configuration en échec silencieux (Step 03)
- **Contexte** : création de simulation en prod, projet `proj_58bb8370c473`.
- **Cause RACINE** : pre-check EntityReader non bloquant — simulations créées sur un
  graphe Neo4j vide (Step 1 sauté ou extraction échouée), puis échec en aval avec un
  message trompeur ; le hint UI mentionnait une env var legacy (`OPENROUTER_API_KEY`).
- **Fix** : hints dynamiques selon `config_error` + suppression des simulations fantômes
  (US-049) — le pre-check bloquant reste à faire (US-214).
- **Leçon généralisable** : valider les préconditions À LA CRÉATION, pas à l'exécution ;
  un bouton « Retry » ne répare jamais une précondition manquante.

### 2026-04-29 — Build frontend cassé `error code: 10` après ajout de traductions
- **Contexte** : ajout de clés i18n contenant des adresses email.
- **Cause RACINE** : vue-i18n interprète `@` comme syntaxe de lien `@:key`.
- **Fix** : échapper en `{'@'}` dans les placeholders.
- **Leçon généralisable** : promu en règle CLAUDE.md (piège i18n).

### 2026-05-05 — Cascade de restarts du conteneur en prod
- **Contexte** : deploy Coolify.
- **Cause RACINE** : `FLASK_DEBUG` actif → auto-reloader Werkzeug tue le process sous
  `concurrently` → `restart: unless-stopped` → boucle.
- **Fix** : `FLASK_DEBUG=false` vérifié à chaque deploy.
- **Leçon généralisable** : fail-closed en config (ADR-006) — le boot doit REFUSER les
  défauts dangereux plutôt que compter sur la discipline humaine.

### 2026-07-07 — prospectives.ai-mpower.com en 404 (down depuis le 2026-07-01)
- **Contexte** : découvert par Amine 6 jours après le fait (aucune sonde d'alerte).
- **Cause RACINE (chaîne)** : app Coolify `miro-shark` crashée en boucle
  (`restart_count: 22` > `max_restart_count: 10`, `last_restart_type: crash`,
  `last_online_at: 2026-07-01 13:04`) → Coolify cesse de la relancer → le nettoyage
  Docker quotidien (`force_docker_cleanup`, cron `0 0 * * *`) supprime les conteneurs
  `miroshark` et `neo4j` → Traefik n'a plus de router pour le Host → 404 brut Traefik
  (text/plain, 19 octets — signature à connaître : 404 infra, pas applicatif).
  Cause du crash initial (les 22 restarts) : le crash-loop a démarré au REBOOT du serveur
  (`uptime -s` = 2026-07-01 12:59, crash à 13:04). Pistes écartées avec preuves :
  FLASK_DEBUG (false en prod), Neo4j strict validation (warning cosmétique seulement,
  `_ensure_schema()` tolère un Neo4j absent — vérifié en conditions réelles). Hypothèse
  la plus solide NON prouvée (preuves détruites avec les conteneurs) : OOM lors du
  redémarrage simultané des 187 conteneurs de l'hôte — swap à 100 % (8/8 Gi) constaté,
  aucune limite mémoire par conteneur (`limits_memory: '0'`).
- **Fix** : redéploiement via API Coolify (1ᵉʳ essai échoué sur pull registry transitoire ;
  2ᵉ abouti en ~9 min). Vérifié 2026-07-07 : racine 200, /explore 200, conteneurs stables.
  Nettoyage bonus : conteneur `ollama` orphelin (rescapé du crash, 6,7 Go RAM) supprimé —
  il partageait l'alias DNS `ollama` avec le nouveau conteneur (risque d'ambiguïté).
  Saqr (ex-Kairos, scrap.ai-mpower.com) jamais affecté — panne isolée Bassira.
- **Leçon généralisable** : (1) un down découvert par un humain = absence de monitoring
  externe (ADR-009) ; (2) `max_restart_count` atteint + cleanup quotidien = disparition
  SILENCIEUSE des conteneurs — l'alerte doit porter sur le statut d'app Coolify, pas
  seulement sur le HTTP ; (3) toujours qualifier un 404 : Traefik (infra) vs applicatif.
