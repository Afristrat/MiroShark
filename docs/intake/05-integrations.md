# 05 — Intégrations du module Intake

## Existantes (réutilisées, zéro nouveau contrat)

| Intégration | Usage dans le module | Point d'attention |
|---|---|---|
| **Gateway LiteLLM** (ADR-004) | Agent de qualification (étape B) via `llm_client.py` existant | Modèle = décision Amine (env `INTAKE_LLM_MODEL`, défaut = `LLM_MODEL_NAME`). Prévoir le fallback gateway déjà en place. Timeout 30 s, 1 appel par tour, 7 tours max — coût borné par design. |
| **Supabase self-hosted** (stack `dgybi…`) | Table `intake_sessions`, lien `quote_ownership` | Service-role uniquement (parcours public sans auth) ; RLS sans policy anon ; pg_cron pour les purges J+30/J+90. |
| **Resend** (US-204, ADR-013) | Emails contextualisés par branche | Expéditeur AI-MPower, liens bassira.ma, templates fr/en/ar. Échappement HTML du contenu prospect (cf. 09). |
| **Stripe Checkout** (US-205, ADR-014) | Branche self-service : propagation `intake_session_id` en metadata de la Checkout Session | Ne PAS toucher au webhook existant au-delà de l'ajout du metadata — il vient d'être vérifié E2E (2026-07-09). |
| **Console simulation** | US-IQ-07 : pré-seed du scénario depuis le brief | Contrat interne (pas d'API nouvelle) : le brief est lu depuis `intake_sessions` par `simulation_config_generator`. |

## Explicitement absentes en V1

| Intégration écartée | Pourquoi | Signal de réexamen |
|---|---|---|
| Outil de calendrier (Cal.com, Calendly) | Échelle Ponytail barreau 1 (YAGNI) : volume d'entretiens actuel ≈ 0/semaine ; 2-3 créneaux proposés par email suffisent | > 5 entretiens/semaine planifiés manuellement (ADR-IQ-03) |
| CRM externe | La vue admin /admin/quotes EST le CRM au volume actuel | Pipeline > 30 devis actifs simultanés |
| Saqr | Aucun rôle dans l'intake (Saqr consomme les SORTIES de Bassira, US-218) | — |
| Analytics tiers | Rejeté durablement par Amine (mémoire `feedback_rejected_tools`) — les KPI du funnel se mesurent en SQL sur `intake_sessions.state` | Ne jamais reproposer |

## Flux de données (résumé)

```
Prospect → Formulaire A (Flask) → intake_sessions (Supabase)
        → Agent B (Flask → gateway LiteLLM → Flask) → brief + flags (Supabase)
        → Routage C (Flask, déterministe) → route (Supabase)
        → Email D (Resend, contextualisé) / Checkout (Stripe) / Créneaux (email)
Admin   → /admin/quotes (brief, flags, transcript)
Console → pré-seed simulation (US-IQ-07)
```

Aucune donnée du parcours ne quitte l'infra (Supabase self-hosted + gateway LiteLLM) hors
Resend (contenu d'email minimisé) et Stripe (metadata = identifiant opaque uniquement).
