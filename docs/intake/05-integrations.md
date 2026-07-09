# 05 — Intégrations du module Intake

## Existantes (réutilisées, zéro nouveau contrat)

| Intégration | Usage dans le module | Point d'attention |
|---|---|---|
| **Gateway LiteLLM** (ADR-004) | Agent de qualification (étape B) via `llm_client.py` existant | Modèle = décision Amine (env `INTAKE_LLM_MODEL`, défaut = `LLM_MODEL_NAME`). Prévoir le fallback gateway déjà en place. Timeout 30 s, 1 appel par tour, 7 tours max — coût borné par design. |
| **Supabase self-hosted** (stack `dgybi…`) | Table `intake_sessions`, lien `quote_ownership` | Service-role uniquement (parcours public sans auth) ; RLS sans policy anon ; pg_cron pour les purges J+30/J+90. |
| **Resend** (US-204, ADR-013) | Emails contextualisés par branche | Expéditeur AI-MPower, liens bassira.ma, templates fr/en/ar. Échappement HTML du contenu prospect (cf. 09). |
| **Stripe Checkout** (US-205, ADR-014) | Branche self-service : propagation `intake_session_id` en metadata de la Checkout Session | Ne PAS toucher au webhook existant au-delà de l'ajout du metadata — il vient d'être vérifié E2E (2026-07-09). |
| **Console simulation** | US-IQ-07 : pré-seed du scénario depuis le brief | Contrat interne (pas d'API nouvelle) : le brief est lu depuis `intake_sessions` par `simulation_config_generator`. |
| **Cal.com self-hosted** (`agenda.ai-mpower.com`, DÉJÀ en production — ADR-IQ-03 v2) | Branche entretien : lien de réservation vers l'event type « Entretien Bassira — 20 min », localisé selon la langue de session | ⚠️ **API appelée en réseau interne uniquement** (service `calcom-api`, `localhost:3002`/réseau Docker — la route publique `/api/*` est bloquée par un challenge Cloudflare, vérifié 2026-07-09). Clé : env Coolify `CALCOM_API_KEY` (POST envs = JSON minimal `{key,value}`). Endpoints utiles : `GET /v2/me` (validation), `GET /v2/event-types`, `GET /v2/slots`. Le lien de réservation envoyé au prospect reste public (page web Cal.com, hors challenge). |

## Explicitement absentes en V1

| Intégration écartée | Pourquoi | Signal de réexamen |
|---|---|---|
| CRM externe | La vue admin /admin/quotes EST le CRM au volume actuel | Pipeline > 30 devis actifs simultanés |
| Saqr | Aucun rôle dans l'intake (Saqr consomme les SORTIES de Bassira, US-218) | — |
| Analytics tiers | Rejeté durablement par Amine (mémoire `feedback_rejected_tools`) — les KPI du funnel se mesurent en SQL sur `intake_sessions.state` | Ne jamais reproposer |

## Flux de données (résumé)

```
Prospect → Formulaire A (Flask) → intake_sessions (Supabase)
        → Agent B (Flask → gateway LiteLLM → Flask) → brief + flags + TRANSCRIPT durable (Supabase)
        → Routage C (Flask, déterministe) → route (Supabase)
        → Email D (Resend, contextualisé, locale de session) / Checkout (Stripe)
          / Réservation Cal.com (lien localisé ; API interne localhost:3002)
Admin   → /admin/quotes (brief, flags, transcript = pièce du dossier de devis)
Console → pré-seed simulation (US-IQ-07)
```

**Règle transversale langue (directive Amine 2026-07-09)** : TOUTE correspondance et TOUT
livrable suit la locale de session de l'utilisateur — emails, page/lien de réservation
Cal.com, devis, PDF, relances. Aucune sortie du module ne peut être émise dans une autre
langue que celle choisie par l'utilisateur.

Aucune donnée du parcours ne quitte l'infra (Supabase self-hosted + gateway LiteLLM) hors
Resend (contenu d'email minimisé) et Stripe (metadata = identifiant opaque uniquement).
