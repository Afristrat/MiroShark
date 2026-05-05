-- ============================================================================
-- Migration 20260505_001 — Table quote_ownership pour lier devis ↔ org (US-114)
-- ============================================================================
--
-- Contexte
-- ────────
-- Avant US-114, les devis publics (POST /api/quote, US-025) sont stockés
-- uniquement en filesystem dans ``backend/uploads/quotes/quote_*.json``
-- avec un sidecar ``*.status.json`` (workflow super-admin US-103).
-- Aucun lien explicite n'existe entre un devis et une organisation
-- Bassira → impossible pour un membre d'une org de voir « ses » devis
-- sans passer par le super-admin (qui voit tout).
--
-- Cette migration introduit ``public.quote_ownership`` :
--   quote_id (text PK)  ──>  org_id (uuid FK)
--                            + customer_email + package_id + status
--                            + created_at
--
-- Le filesystem reste la source de vérité pour le payload riche du devis
-- (full_name, message, geo_focus, …) et pour le workflow status sidecar.
-- Cette table sert uniquement à indexer « quel quote appartient à quelle
-- org » de manière requêtable depuis Supabase, avec RLS strict.
--
-- RLS
-- ───
--   - SELECT : un membre voit les devis de son org (org_id IN user_orgs())
--   - INSERT/UPDATE/DELETE : aucune policy publique — uniquement
--     service_role (backend Flask) peut écrire. Le super-admin Bassira
--     bypasse RLS via service_role aussi.
--
-- Pas d'exposition au rôle ``anon`` (les devis ne sont jamais visibles
-- côté visiteur public).
--
-- Caractéristiques
-- ────────────────
-- • Idempotente : tous les ``CREATE`` utilisent ``IF NOT EXISTS`` et les
--   ``CREATE POLICY`` sont précédés d'un ``DROP POLICY IF EXISTS``.
-- • Pas de breaking change : la table est nouvelle, ne touche pas à
--   l'existant. Les devis pré-US-114 sont rétro-attribués via
--   ``backend/scripts/migrate_quotes_to_supabase.py`` (idempotent).
-- ============================================================================

-- ────────────────────────────────────────────────────────────────────────────
-- 1. Table quote_ownership
-- ────────────────────────────────────────────────────────────────────────────
create table if not exists public.quote_ownership (
  quote_id        text primary key,                                  -- ex: "q_abc12345"
  org_id          uuid not null references public.organizations(id) on delete cascade,
  customer_email  text,                                              -- email du contact à la soumission
  package_id      text,                                              -- crisis_drill_24h | policy_brief_stress | …
  status          text not null default 'received',                  -- miroir du sidecar filesystem (received | reviewing | quoted | declined | paid | in_progress | delivered)
  created_at      timestamptz not null default now(),
  metadata        jsonb not null default '{}'::jsonb,
  constraint quote_status_chk check (
    status in ('received','reviewing','quoted','declined','paid','in_progress','delivered')
  )
);

create index if not exists idx_quote_ownership_org        on public.quote_ownership(org_id);
create index if not exists idx_quote_ownership_status     on public.quote_ownership(status);
create index if not exists idx_quote_ownership_email      on public.quote_ownership(customer_email);
create index if not exists idx_quote_ownership_package    on public.quote_ownership(package_id);

comment on table public.quote_ownership is
  'Mapping quote_id (filesystem) ↔ org Bassira propriétaire (US-114). Le payload riche reste en JSON sur disque.';
comment on column public.quote_ownership.quote_id is
  'Identifiant du devis tel qu''écrit par quote_service.py (format ''q_<hex8>'').';
comment on column public.quote_ownership.status is
  'Miroir best-effort du sidecar filesystem ``quote_*.status.json`` — peut être stale jusqu''à la prochaine MAJ.';

-- ────────────────────────────────────────────────────────────────────────────
-- 2. RLS — Row Level Security
-- ────────────────────────────────────────────────────────────────────────────
alter table public.quote_ownership enable row level security;

-- Lecture : un user voit les devis de son org (helper user_orgs() défini
-- en migration 20260503_001).
drop policy if exists "members_can_read_org_quotes" on public.quote_ownership;
create policy "members_can_read_org_quotes"
  on public.quote_ownership for select
  using (org_id in (select public.user_orgs()));

-- INSERT/UPDATE/DELETE : pas de policy publique. Le backend Flask passe
-- par get_supabase_admin() (service_role) qui bypasse RLS pour les
-- opérations de rétro-attribution et de mise à jour de statut.
-- Le super-admin Bassira bypasse aussi via service_role.

-- ────────────────────────────────────────────────────────────────────────────
-- Fin migration 20260505_001
-- ────────────────────────────────────────────────────────────────────────────
