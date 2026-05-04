-- ============================================================================
-- Migration 003 — Toggle org-level self_service_enabled (US-098)
-- ============================================================================
-- Ajoute un flag booléen `self_service_enabled` sur public.organizations.
-- Quand true : les membres de l'org peuvent lancer eux-mêmes des simulations
-- via les endpoints self-service Step1-5 (POST /api/simulation/create,
-- POST /api/graph/build, POST /api/simulation/start).
-- Quand false (default) : seul le mode commande analyste est ouvert
-- (POST /api/client/simulations) — les Step1-5 retournent 403
-- SELF_SERVICE_DISABLED pour les membres normaux.
--
-- Les super-admins Bassira (whitelist email côté backend) bypassent ce flag.
--
-- Default: false (sécurité par défaut — chaque nouvelle org est en mode
-- commande analyste tant qu'Amine n'active pas explicitement le self-service).
-- ============================================================================

alter table public.organizations
  add column if not exists self_service_enabled boolean not null default false;

comment on column public.organizations.self_service_enabled is
  'Si true : les membres de l''org peuvent lancer des simulations en self-service (Step1-5). Sinon : mode commande analyste uniquement (sauf super-admin Bassira).';

-- Index utile pour la dashboard super-admin et les helpers backend.
create index if not exists idx_organizations_self_service
  on public.organizations(self_service_enabled);

-- ────────────────────────────────────────────────────────────────────────────
-- Note : RLS reste inchangée. Le flag est lu côté backend par le décorateur
-- @require_self_service_enabled qui :
--   1. Lit g.current_org (issu de @require_org_membership)
--   2. Vérifie organizations.self_service_enabled = true
--   3. Si non : 403 SELF_SERVICE_DISABLED (avec bypass si g.is_super_admin)
-- ────────────────────────────────────────────────────────────────────────────
