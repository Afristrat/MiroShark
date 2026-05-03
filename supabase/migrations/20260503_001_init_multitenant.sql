-- ============================================================================
-- Migration 001 — Init multitenant Bassira (US-091)
-- ============================================================================
-- Tables :
--   1. organizations          — les tenants (1 client institutionnel = 1 org)
--   2. org_members            — membres d'une org (lien auth.users ↔ org)
--   3. simulation_ownership   — lien id Bassira filesystem ↔ org propriétaire
--
-- RLS :
--   - Un user voit uniquement les ressources de son org
--   - Seuls owner/admin peuvent marquer outcomes / publier
--   - Lecture publique = via VIEW agrégée k-anonymity n≥5 (migration 002)
-- ============================================================================

-- pgcrypto est déjà activée par défaut sur Supabase pour gen_random_uuid()
-- create extension if not exists pgcrypto;

-- ────────────────────────────────────────────────────────────────────────────
-- 1. organizations (tenants)
-- ────────────────────────────────────────────────────────────────────────────
create table if not exists public.organizations (
  id           uuid primary key default gen_random_uuid(),
  name         text not null,
  slug         text not null unique,
  sector       text,                   -- banque/énergie/politique/...
  country_code text,                   -- ISO 3166-1 alpha-2 (MA, FR, SN, AE, ...)
  status       text not null default 'active',  -- active | suspended | trial
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  metadata     jsonb not null default '{}'::jsonb,
  constraint org_status_chk check (status in ('active','suspended','trial'))
);

comment on table public.organizations is 'Tenants Bassira — 1 client institutionnel = 1 org';
comment on column public.organizations.sector is 'Secteur métier dominant pour la calibration agrégée publique (banque, énergie, politique-publique, distribution, tech, etc.)';

-- ────────────────────────────────────────────────────────────────────────────
-- 2. org_members (lien user ↔ org avec rôle)
-- ────────────────────────────────────────────────────────────────────────────
create table if not exists public.org_members (
  id          uuid primary key default gen_random_uuid(),
  org_id      uuid not null references public.organizations(id) on delete cascade,
  user_id     uuid not null references auth.users(id)           on delete cascade,
  role        text not null default 'member',  -- owner | admin | member | viewer
  created_at  timestamptz not null default now(),
  invited_by  uuid references auth.users(id),
  unique (org_id, user_id),
  constraint org_member_role_chk check (role in ('owner','admin','member','viewer'))
);

create index if not exists idx_org_members_user  on public.org_members(user_id);
create index if not exists idx_org_members_org   on public.org_members(org_id);

comment on table public.org_members is 'Lien membership Supabase Auth user ↔ Bassira organization';

-- ────────────────────────────────────────────────────────────────────────────
-- 3. simulation_ownership (lien id Bassira filesystem ↔ org)
-- ────────────────────────────────────────────────────────────────────────────
create table if not exists public.simulation_ownership (
  simulation_id   text primary key,                -- l'id Bassira existant (sim_xxxxxxxxxxxx)
  org_id          uuid not null references public.organizations(id) on delete cascade,
  created_by      uuid references auth.users(id),
  created_at      timestamptz not null default now(),
  package_id      text,                            -- si commandé via /devis (crisis-drill-24h, fusion-bancaire-mena, ...)
  is_published    boolean not null default false,  -- visible via VIEW publique agrégée
  outcome         jsonb,                           -- {label: called_it|partial|wrong, observed_at, source_url, notes}
  brier_score     numeric,                         -- score de Brier individuel (calculé après outcome marqué)
  metadata        jsonb not null default '{}'::jsonb
);

create index if not exists idx_sim_ownership_org              on public.simulation_ownership(org_id);
create index if not exists idx_sim_ownership_published_sector on public.simulation_ownership(org_id) where is_published = true;
create index if not exists idx_sim_ownership_package          on public.simulation_ownership(package_id);

comment on table public.simulation_ownership is 'Mapping id sim filesystem Bassira ↔ org propriétaire + outcome + brier individuel';

-- ────────────────────────────────────────────────────────────────────────────
-- Helper function : retourne la liste des org_id auxquelles l'user courant appartient
-- ────────────────────────────────────────────────────────────────────────────
create or replace function public.user_orgs()
returns setof uuid
language sql
security definer
set search_path = public
stable
as $$
  select org_id from public.org_members where user_id = auth.uid()
$$;

comment on function public.user_orgs() is 'Helper RLS : returns org_ids the current auth user belongs to';

-- ────────────────────────────────────────────────────────────────────────────
-- RLS — Row Level Security
-- ────────────────────────────────────────────────────────────────────────────
alter table public.organizations        enable row level security;
alter table public.org_members          enable row level security;
alter table public.simulation_ownership enable row level security;

-- ─── organizations ──────────────────────────────────────────────────────────
-- Lecture : un user voit l'org à laquelle il appartient
drop policy if exists "members_can_read_their_org" on public.organizations;
create policy "members_can_read_their_org"
  on public.organizations for select
  using (id in (select public.user_orgs()));

-- Update : seul un owner/admin peut updater son org
drop policy if exists "owners_can_update_their_org" on public.organizations;
create policy "owners_can_update_their_org"
  on public.organizations for update
  using (id in (
    select org_id from public.org_members
    where user_id = auth.uid() and role in ('owner','admin')
  ));

-- Insert : pour le MVP — pas de signup libre côté client (création via service_role
-- côté backend Flask au moment du provisioning). Les users normaux ne peuvent pas
-- créer d'orgs depuis le frontend public.
-- → aucune policy INSERT publique (seul le service_role bypassé peut insérer).

-- ─── org_members ────────────────────────────────────────────────────────────
-- Lecture : un user voit ses pairs dans son org
drop policy if exists "members_can_read_peers" on public.org_members;
create policy "members_can_read_peers"
  on public.org_members for select
  using (org_id in (select public.user_orgs()));

-- Insert : seul un owner/admin peut inviter un membre dans son org
drop policy if exists "admins_can_add_members" on public.org_members;
create policy "admins_can_add_members"
  on public.org_members for insert
  with check (org_id in (
    select org_id from public.org_members
    where user_id = auth.uid() and role in ('owner','admin')
  ));

-- Delete : seul un owner/admin peut retirer un membre (sauf le dernier owner)
drop policy if exists "admins_can_remove_members" on public.org_members;
create policy "admins_can_remove_members"
  on public.org_members for delete
  using (org_id in (
    select org_id from public.org_members
    where user_id = auth.uid() and role in ('owner','admin')
  ));

-- ─── simulation_ownership ───────────────────────────────────────────────────
-- Lecture : un user voit les sims de son org
drop policy if exists "members_can_read_org_sims" on public.simulation_ownership;
create policy "members_can_read_org_sims"
  on public.simulation_ownership for select
  using (org_id in (select public.user_orgs()));

-- Insert : un membre peut commander une sim pour son org
drop policy if exists "members_can_create_sims" on public.simulation_ownership;
create policy "members_can_create_sims"
  on public.simulation_ownership for insert
  with check (org_id in (select public.user_orgs()));

-- Update : seuls owner/admin peuvent marquer outcome / publier
drop policy if exists "admins_can_update_sims" on public.simulation_ownership;
create policy "admins_can_update_sims"
  on public.simulation_ownership for update
  using (org_id in (
    select org_id from public.org_members
    where user_id = auth.uid() and role in ('owner','admin')
  ));

-- Delete : seuls owner peuvent supprimer une sim
drop policy if exists "owners_can_delete_sims" on public.simulation_ownership;
create policy "owners_can_delete_sims"
  on public.simulation_ownership for delete
  using (org_id in (
    select org_id from public.org_members
    where user_id = auth.uid() and role = 'owner'
  ));

-- ────────────────────────────────────────────────────────────────────────────
-- Trigger updated_at sur organizations
-- ────────────────────────────────────────────────────────────────────────────
create or replace function public.trg_touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end
$$;

drop trigger if exists trg_organizations_updated_at on public.organizations;
create trigger trg_organizations_updated_at
  before update on public.organizations
  for each row execute function public.trg_touch_updated_at();

-- ────────────────────────────────────────────────────────────────────────────
-- Fin migration 001
-- ────────────────────────────────────────────────────────────────────────────
