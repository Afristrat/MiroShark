-- ============================================================================
-- Migration 20260713_001 — Plafond agent_turns : 7 → 10 (ADR-IQ-11)
-- ============================================================================
--
-- Contexte
-- ────────
-- ADR-IQ-11 (docs/intake/08-decisions-log.md) : directive Amine 2026-07-13,
-- après test réel de /devis en prod — 8 à 10 questions de qualification sont
-- un must (les réponses servent aussi à préparer l'entretien physique), pas
-- seulement 3 à 7. `_AGENT_MAX_TURNS` (backend/app/services/intake_service.py)
-- passe à 10 dans le même commit ; cette migration relève la contrainte SQL
-- miroir pour que le 8e-10e tour ne se fasse pas rejeter par Postgres avant
-- même d'atteindre le garde-fou applicatif.
-- ============================================================================

alter table public.intake_sessions
  drop constraint intake_sessions_agent_turns_chk;

alter table public.intake_sessions
  add constraint intake_sessions_agent_turns_chk check (agent_turns >= 0 and agent_turns <= 10);

comment on column public.intake_sessions.agent_turns is
  'Compteur de tours de l''agent de qualification — budget max 10 (US-IQ-02, '
  'ADR-IQ-11), vérifié en base, jamais côté front.';

-- ────────────────────────────────────────────────────────────────────────────
-- Fin migration 20260713_001
-- ────────────────────────────────────────────────────────────────────────────
