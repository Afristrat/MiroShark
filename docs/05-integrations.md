# Integrations — Bassira V2

> Chaque service externe est un risque accepté. Les valeurs vivent dans les env vars
> Coolify (prod) et le coffre DPAPI du poste — ce fichier ne contient QUE des noms de
> variables. État constaté le 2026-07-07 (deep explore + .env.example + passations).

| Service | Usage | Variables (env Coolify / coffre) | Plan/limites | Criticité si down | Repli |
|---|---|---|---|---|---|
| **Supabase** | Auth JWT + 12 tables multi-org (source de vérité métadonnées) | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY` (+ `SUPABASE_JWT_*` legacy) — ⚠️ absentes de .env.example, à documenter (US-212) | Self-hosted sur serveuria | **Fatale** : auth et ownership morts | Aucun — c'est le socle. Backups Postgres à vérifier |
| **Neo4j** | Graphe d'entités/relations par simulation | `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` — ⚠️ défaut hardcodé 'miroshark' à bannir (US-207) | Conteneur Coolify | **Fatale** pour toute nouvelle simulation | Aucun ; les sims terminées restent lisibles (artefacts) |
| **LLM via gateway LiteLLM** (décision Amine 2026-07-07) | Boucle agents (850+ appels/run), rapports, NER — défaut : modèle type DeepSeek v4 Flash, fallback sur un second modèle configuré dans LiteLLM | `LLM_BASE_URL` → gateway LiteLLM, `LLM_API_KEY`, `LLM_MODEL_NAME` + profils `SMART_*`, `NER_*`, `WONDERWALL_MODEL_NAME` (routing/fallback côté gateway) | Coût selon modèle ; #1 cost driver (config.py:173) | **Fatale** pour les runs | Fallback natif LiteLLM ; BYOK client via la gateway (ADR-004) |
| **Saqr** (ex-Kairos, scrap.ai-mpower.com) | Signaux/recherche seed (scope_profile, hints_override → scored_signals_top) — Saqr est AUSSI consommateur des sorties Bassira (voir § Consommateurs) | Clé API préfixe `bsr_7123` (env Coolify) — contrat V2 du 2026-05-15 | Service frère self-hosted | Dégradée : simulation possible sans ancrage signaux (quality_warning) | Mode dégradé natif du contrat V2 |
| **Resend** | Emails de livraison rapports (US-130) + notifications devis — expéditeur : adresse **AI-MPower** ; liens de renvoi : **bassira.ma toujours** (décision Amine 2026-07-07, ADR-013) | `RESEND_API_KEY` — configurée en prod (US-204, `passes=true` depuis 2026-07-09 ; présence revérifiée sur le conteneur live 2026-07-15) | Plan free Resend : 100 mails/j | Haute : leads invisibles, livraisons mortes | File d'attente + relance manuelle admin |
| **Stripe** | Checkout self-service + **création du PRICING** (products/prices des packages, décision Amine 2026-07-07) (US-205) | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` — comptes/credentials jamais posés (blocage historique US-113) | Standard 2,9 % + 0,30 $ | Basse (canal devis manuel subsiste) | Payment Link manuel (bridge actuel) |
| **FeedOracle MCP** | Seeds « Live Oracle Data » opt-in (484 tools) | Config MCP côté runtime | Service tiers externe | Basse : feature opt-in | Désactiver l'option |
| **Langfuse** | Observabilité LLM (metadata session=simulation_id) | `LANGFUSE_*` (llm_client.py) | Self-hosted/cloud | Basse : perte de traces seulement | Logs applicatifs |
| **OpenSERP** (à déployer — US-219, ADR-012) | Recherche web headless souveraine (remplace SearXNG, bloqué structurellement) : enrichissement web des simulations, trending, sourcing | Service Coolify `karust/openserp` port 7000 — pas de clé (self-hosted) | MIT, gratuit | Moyenne : enrichissement dégradé | Repli Serper.dev (`SERPER_API_KEY`, ~2 $/mois au volume visé) sur erreur/CAPTCHA uniquement — non souverain, filet de disponibilité |
| **Cloudflare Tunnel** | Exposition prospectives.ai-mpower.com (tunnel `nahda-tunnel`, service `cloudflared-nahda`) | Config serveur `/home/serveurai/.cloudflared/` | Free | **Fatale** : site injoignable (cf. 404 du 2026-07-07) | Redémarrage service ; monitoring externe à ajouter |
| **Coolify** | Build + deploy auto sur push main (webhook GitHub) | `COOLIFY_API_TOKEN` (coffre) | Self-hosted serveuria | Haute : plus de deploys (prod continue de tourner) | Deploy manuel docker sur le serveur |
| **GitHub** | Repo `Afristrat/MiroShark` (fork `aaronjmars/miroshark`) | Auth git du poste | — | Moyenne : plus de push/webhook | Push différé (DNS parfois intermittent — retenter d'abord) |

## Consommateurs des sorties Bassira (flux sortants — décision Amine 2026-07-07)

| Consommateur | Ce qu'il consomme | Contrat |
|---|---|---|
| **Saqr** (ex-Kairos) | Sorties Bassira (rapports, signaux de simulation, entre autres) | À définir — US-218 |
| **Nahda** | Sorties Bassira ; par ailleurs un second canal de prospective basé **MiroFish** (B2G / grandes missions) cohabitera aux côtés de Bassira (B2B) | À définir — US-218 + cadrage MiroFish |

## Règles

- **Ponytail échelons 2-5** : tout service AJOUTÉ après cette fondation prouve dans son
  entrée ADR qu'aucun échelon inférieur ne suffisait (codebase → stdlib → plateforme →
  dépendance déjà installée). « npm install » n'est jamais le premier réflexe.
- **Anti-leak** : aucune valeur de secret dans ce fichier, dans le chat, ni dans un commit.
  Rotation → SOP-001 (coffre DPAPI).
- Le monitoring externe de la prod (uptime + alerte) n'existe pas — c'est une dépendance
  MANQUANTE assumée, à trancher en ADR lors du Bloc A (le 404 du 2026-07-07 a été découvert
  par un humain, pas par une sonde).
