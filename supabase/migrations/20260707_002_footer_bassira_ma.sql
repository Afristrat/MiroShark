-- ============================================================================
-- Migration 20260707_002 — Correction domaine footer_right bassira.ai → bassira.ma (US-204)
-- ============================================================================
--
-- Contexte
-- ────────
-- ADR-013 (docs/08-decisions-log.md) : toute URL publique et tout lien de
-- renvoi pointe **bassira.ma**. Le défaut posé par la migration 20260506_001
-- ('bassira.ai') est un bug de marque — jamais retenu par Amine.
--
-- Cette migration corrige :
--   1. Le DEFAULT de la colonne pour toute nouvelle row.
--   2. Les rows ACTIVES existantes (valid_to IS NULL) encore sur l'ancien
--      défaut — simple correctif de bug, pas une décision métier versionnée,
--      donc UPDATE direct plutôt qu'une nouvelle version append-only.
-- ============================================================================

alter table public.pdf_branding
  alter column footer_right set default 'bassira.ma';

update public.pdf_branding
  set footer_right = 'bassira.ma'
  where footer_right = 'bassira.ai'
    and valid_to is null;

-- ────────────────────────────────────────────────────────────────────────────
-- Fin migration 20260707_002
-- ────────────────────────────────────────────────────────────────────────────
