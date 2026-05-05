-- ============================================================================
-- Migration 20260505_002 — Table org_invitations (US-115)
-- ============================================================================
--
-- Contexte
-- ────────
-- Avant US-115, l'attribution membership user → org se faisait
-- manuellement par Amine via le SQL Editor Supabase (insert direct dans
-- ``public.org_members``). Cette migration introduit un système
-- d'invitation par email avec token magique, au design proche du flux
-- Slack/Notion :
--
--   1. Admin (org admin OU super-admin) crée une invitation pour un
--      email + un rôle.
--   2. Backend envoie un email avec lien
--      ``https://prospectives.ai-mpower.com/signup?invite=<token>``.
--   3. Le destinataire clique → signup → POST /redeem qui crée la row
--      ``org_members`` (org_id + user_id + role) atomiquement.
--   4. Token consommé (``accepted_at`` set) → ne peut plus être utilisé.
--
-- Le token est un UUID (gen_random_uuid()) : suffisamment opaque pour
-- résister à l'énumération sans avoir à générer un secret cryptographique
-- dédié. ``expires_at`` à +7 jours par défaut.
--
-- RLS
-- ───
--   - SELECT public : un visiteur authentifié peut voir une invitation
--     SI ``email = auth.email()`` ET ``expires_at > now()``. Permet au
--     frontend de pré-remplir le signup avec les metadata (org name, role)
--     sans exposer les invitations cross-tenant.
--   - INSERT : org admin (role admin/owner) OU super-admin Bassira (via
--     service_role). Pas de policy pour les members simples.
--   - UPDATE/DELETE : org admin OU service_role. Permet de revoquer
--     (delete) une invitation pending.
--
-- Note : les redemptions (création de la row ``org_members``) restent
-- exécutées côté backend Flask via ``service_role`` (atomicité +
-- contrôle du flux). Le frontend ne fait QUE lire l'invitation (GET
-- /accept) puis appelle POST /redeem une fois authentifié.
-- ============================================================================

-- ────────────────────────────────────────────────────────────────────────────
-- 1. Table org_invitations
-- ────────────────────────────────────────────────────────────────────────────
create table if not exists public.org_invitations (
  token        uuid primary key default gen_random_uuid(),
  org_id       uuid not null references public.organizations(id) on delete cascade,
  email        text not null,
  role         text not null default 'member',
  expires_at   timestamptz not null default (now() + interval '7 days'),
  accepted_at  timestamptz,
  invited_by   uuid references auth.users(id) on delete set null,
  created_at   timestamptz not null default now(),
  metadata     jsonb not null default '{}'::jsonb,
  constraint org_invitation_role_chk check (role in ('admin','member','viewer'))
);

create index if not exists idx_org_invitations_email
  on public.org_invitations(lower(email));
create index if not exists idx_org_invitations_org
  on public.org_invitations(org_id);
create index if not exists idx_org_invitations_pending
  on public.org_invitations(org_id)
  where accepted_at is null;

comment on table public.org_invitations is
  'Invitations user → org Bassira (US-115). Lien magique email + token UUID expirant.';
comment on column public.org_invitations.token is
  'Token UUID partagé dans l''URL d''invitation. Utilisé pour authentifier le redeem.';
comment on column public.org_invitations.email is
  'Email du destinataire — comparé à auth.email() à la lecture publique RLS.';
comment on column public.org_invitations.role is
  'Rôle attribué au redeem. ''owner'' n''est pas autorisé pour les invitations (le 1er owner est créé par seed.sql).';

-- ────────────────────────────────────────────────────────────────────────────
-- 2. RLS — Row Level Security
-- ────────────────────────────────────────────────────────────────────────────
alter table public.org_invitations enable row level security;

-- Lecture publique (authentifiée) : un user voit son invitation pending.
drop policy if exists "users_can_read_their_invitations" on public.org_invitations;
create policy "users_can_read_their_invitations"
  on public.org_invitations for select
  using (
    accepted_at is null
    and expires_at > now()
    and lower(email) = lower(coalesce(auth.email(), ''))
  );

-- Lecture admin : un admin/owner voit les invitations de son org (même
-- expirées ou consommées) pour audit.
drop policy if exists "admins_can_read_org_invitations" on public.org_invitations;
create policy "admins_can_read_org_invitations"
  on public.org_invitations for select
  using (org_id in (
    select org_id from public.org_members
    where user_id = auth.uid() and role in ('owner','admin')
  ));

-- Insert : un admin/owner peut créer des invitations dans son org.
drop policy if exists "admins_can_invite" on public.org_invitations;
create policy "admins_can_invite"
  on public.org_invitations for insert
  with check (org_id in (
    select org_id from public.org_members
    where user_id = auth.uid() and role in ('owner','admin')
  ));

-- Update : un admin/owner peut révoquer (set accepted_at à un sentinel)
-- ou modifier l'expiration. La création de membership est faite côté
-- backend via service_role (RLS bypass).
drop policy if exists "admins_can_update_invitations" on public.org_invitations;
create policy "admins_can_update_invitations"
  on public.org_invitations for update
  using (org_id in (
    select org_id from public.org_members
    where user_id = auth.uid() and role in ('owner','admin')
  ));

-- Delete : un admin/owner peut supprimer une invitation pending.
drop policy if exists "admins_can_delete_invitations" on public.org_invitations;
create policy "admins_can_delete_invitations"
  on public.org_invitations for delete
  using (org_id in (
    select org_id from public.org_members
    where user_id = auth.uid() and role in ('owner','admin')
  ));

-- ────────────────────────────────────────────────────────────────────────────
-- Fin migration 20260505_002
-- ────────────────────────────────────────────────────────────────────────────
