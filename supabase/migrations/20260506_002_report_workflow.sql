-- ============================================================================
-- Migration 002 — Workflow états rapport + audit log immuable (US-126)
-- ============================================================================
-- Tables :
--   1. report_states    — état courant d'un rapport (1 row par report)
--   2. report_audit_log — journal immuable insert-only de toutes les transitions
--
-- Fonctionnalités :
--   - 7 états : GENERATING → DRAFT → IN_REVIEW → PENDING_APPROVAL
--               → APPROVED → DELIVERED → ARCHIVED
--   - Locking optimiste sur IN_REVIEW (auto-release 30 min)
--   - RLS stricte : INSERT/UPDATE uniquement via service_role (backend)
--   - Audit log : UPDATE/DELETE bloqués (immutabilité garantie par policy)
-- ============================================================================

-- ────────────────────────────────────────────────────────────────────────────
-- Helper : is_super_admin() — lookup whitelist via config Postgres
-- ────────────────────────────────────────────────────────────────────────────
-- Note : La whitelist des super-admins est stockée dans la table super_admin_emails
-- (créée par US-095) ou vérifiée côté backend via BASSIRA_SUPER_ADMIN_EMAILS.
-- Pour la RLS Supabase, on crée une fonction qui retourne true si l'user courant
-- appartient à la relation org_members avec un rôle super-admin fictif.
-- En pratique, la table super_admin_emails est celle de référence (US-095).
-- Si elle n'existe pas (env de test), la fonction retourne false gracieusement.

create or replace function public.is_super_admin()
returns boolean
language plpgsql
security definer
set search_path = public
stable
as $$
declare
  v_email text;
begin
  -- Récupérer l'email de l'user courant depuis auth.users
  select email into v_email
    from auth.users
   where id = auth.uid()
   limit 1;

  if v_email is null then
    return false;
  end if;

  -- Vérifier dans la table super_admin_emails si elle existe
  if exists (
    select 1
      from information_schema.tables
     where table_schema = 'public'
       and table_name   = 'super_admin_emails'
  ) then
    return exists (
      select 1
        from public.super_admin_emails
       where lower(email) = lower(v_email)
    );
  end if;

  return false;
end;
$$;

comment on function public.is_super_admin() is
  'Helper RLS : retourne true si l''utilisateur courant est dans la whitelist super-admin Bassira.';

-- ────────────────────────────────────────────────────────────────────────────
-- 1. report_states — état courant d'un rapport
-- ────────────────────────────────────────────────────────────────────────────
create table if not exists public.report_states (
  report_id            text        primary key,
  state                text        not null default 'GENERATING',
  current_version      int         not null default 1,
  last_transition_at   timestamptz not null default now(),
  last_transition_by   uuid        references auth.users(id),
  locked_by            uuid        references auth.users(id),
  locked_at            timestamptz,
  org_id               uuid        not null references public.organizations(id) on delete cascade,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  constraint report_states_state_chk check (state in (
    'GENERATING',
    'DRAFT',
    'IN_REVIEW',
    'PENDING_APPROVAL',
    'APPROVED',
    'DELIVERED',
    'ARCHIVED'
  ))
);

comment on table public.report_states is
  'État courant d''un rapport Bassira — 1 row par report_id, mis à jour à chaque transition.';
comment on column public.report_states.report_id is
  'Identifiant du rapport au format report_<12 hex>.';
comment on column public.report_states.state is
  'État courant parmi GENERATING / DRAFT / IN_REVIEW / PENDING_APPROVAL / APPROVED / DELIVERED / ARCHIVED.';
comment on column public.report_states.locked_by is
  'UUID de l''utilisateur qui a verrouillé le rapport pour révision (IN_REVIEW).';
comment on column public.report_states.locked_at is
  'Timestamp du verrouillage — auto-release après 30 min d''inactivité.';

-- Index pour dashboard (filtrage par org + état)
create index if not exists idx_report_states_org_state
  on public.report_states(org_id, state);

-- Trigger updated_at
drop trigger if exists trg_report_states_updated_at on public.report_states;
create trigger trg_report_states_updated_at
  before update on public.report_states
  for each row execute function public.trg_touch_updated_at();

-- ────────────────────────────────────────────────────────────────────────────
-- 2. report_audit_log — journal immuable insert-only
-- ────────────────────────────────────────────────────────────────────────────
create table if not exists public.report_audit_log (
  id            uuid        primary key default gen_random_uuid(),
  report_id     text        not null,
  from_state    text,
  to_state      text        not null,
  actor_id      uuid        references auth.users(id),
  actor_email   text,
  ip_address    inet,
  user_agent    text,
  snapshot_hash text,
  comment       text,
  created_at    timestamptz not null default now()
);

comment on table public.report_audit_log is
  'Journal immuable de toutes les transitions d''état des rapports — insert-only, pas d''UPDATE ni DELETE.';
comment on column public.report_audit_log.from_state is
  'État source de la transition (null si création initiale).';
comment on column public.report_audit_log.to_state is
  'État cible de la transition.';
comment on column public.report_audit_log.snapshot_hash is
  'Hash SHA-256 du contenu du rapport au moment de la transition (pour preuve de non-altération).';
comment on column public.report_audit_log.ip_address is
  'Adresse IP de l''acteur au moment de la transition.';

-- Index pour requêtes history (plus récent en premier)
create index if not exists idx_report_audit_log_report_created
  on public.report_audit_log(report_id, created_at desc);

-- ────────────────────────────────────────────────────────────────────────────
-- RLS — Row Level Security
-- ────────────────────────────────────────────────────────────────────────────
alter table public.report_states   enable row level security;
alter table public.report_audit_log enable row level security;

-- ─── report_states ──────────────────────────────────────────────────────────

-- SELECT : membre de l'org OU super-admin
drop policy if exists "members_can_read_report_states" on public.report_states;
create policy "members_can_read_report_states"
  on public.report_states for select
  using (
    org_id in (select public.user_orgs())
    or public.is_super_admin()
  );

-- INSERT : service_role uniquement (le backend Flask pousse les transitions)
-- → Pas de policy INSERT publique : RLS bloque tout INSERT non-service_role.

-- UPDATE : service_role uniquement (idem)
-- → Pas de policy UPDATE publique.

-- ─── report_audit_log ───────────────────────────────────────────────────────

-- SELECT : membre de la même org OU super-admin
-- Note : audit_log ne stocke pas org_id directement — on joint via report_states
drop policy if exists "members_can_read_audit_log" on public.report_audit_log;
create policy "members_can_read_audit_log"
  on public.report_audit_log for select
  using (
    public.is_super_admin()
    or exists (
      select 1
        from public.report_states rs
       where rs.report_id = report_audit_log.report_id
         and rs.org_id in (select public.user_orgs())
    )
  );

-- INSERT : service_role uniquement (pas de policy INSERT publique)

-- UPDATE : BLOQUÉ — immutabilité garantie
drop policy if exists "audit_log_no_update" on public.report_audit_log;
create policy "audit_log_no_update"
  on public.report_audit_log for update
  using (false);

-- DELETE : BLOQUÉ — immutabilité garantie
drop policy if exists "audit_log_no_delete" on public.report_audit_log;
create policy "audit_log_no_delete"
  on public.report_audit_log for delete
  using (false);

-- ────────────────────────────────────────────────────────────────────────────
-- Fin migration 002 — US-126
-- ────────────────────────────────────────────────────────────────────────────
