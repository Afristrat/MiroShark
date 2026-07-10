-- ============================================================================
-- Migration — intake_agent_escalations + intake_agent_playbook (ADR-IQ-08)
-- ============================================================================
-- Escalade silencieuse (jamais vue du prospect — seul `message` sort vers le
-- client) + playbook vivant de corrections, édité par Amine via /admin,
-- injecté dans le system prompt de l'agent à chaque tour (US-IQ-02 v2).
-- ============================================================================

create table if not exists public.intake_agent_escalations (
  id             uuid        primary key default gen_random_uuid(),
  session_id     uuid        references public.intake_sessions(id) on delete cascade,
  category       text        not null check (category in (
    'ambiguous_request', 'out_of_scope', 'injection_attempt', 'unclear_input'
  )),
  user_message   text        not null,
  agent_message  text        not null,
  created_at     timestamptz not null default now(),
  reviewed_at    timestamptz,
  reviewer_note  text
);

comment on table public.intake_agent_escalations is
  'Tours de l''agent Intake flaggés escalation (ADR-IQ-08) — jamais exposé au '
  'prospect, revue exclusive Amine. Alimente les corrections du playbook.';
comment on column public.intake_agent_escalations.category is
  'Catégorie fermée déclarée par l''agent lui-même dans sa sortie JSON — '
  'ambiguous_request | out_of_scope | injection_attempt | unclear_input.';

create index if not exists idx_intake_agent_escalations_reviewed
  on public.intake_agent_escalations(reviewed_at) where reviewed_at is null;

alter table public.intake_agent_escalations enable row level security;

drop policy if exists "super_admin_can_read_escalations" on public.intake_agent_escalations;
create policy "super_admin_can_read_escalations"
  on public.intake_agent_escalations for select
  using (public.is_super_admin());

drop policy if exists "super_admin_can_update_escalations" on public.intake_agent_escalations;
create policy "super_admin_can_update_escalations"
  on public.intake_agent_escalations for update
  using (public.is_super_admin());

-- ────────────────────────────────────────────────────────────────────────────

create table if not exists public.intake_agent_playbook (
  id                  uuid        primary key default gen_random_uuid(),
  situation_pattern   text        not null,
  corrected_response  text        not null,
  added_by            text        not null,
  added_at            timestamptz not null default now(),
  active              boolean     not null default true
);

comment on table public.intake_agent_playbook is
  'Corrections de trajectoire ajoutées par Amine (ADR-IQ-08), injectées dans '
  'le system prompt de l''agent Intake à chaque tour tant que active=true. '
  'Jamais de modification automatique — supervision humaine exclusive.';
comment on column public.intake_agent_playbook.situation_pattern is
  'Description courte de la situation rencontrée (ex. injection combinée à '
  'une demande de prix).';
comment on column public.intake_agent_playbook.corrected_response is
  'Réponse idéale attendue pour ce type de situation — injectée comme '
  'exemple contrastif dans le system prompt.';

alter table public.intake_agent_playbook enable row level security;

drop policy if exists "super_admin_can_manage_playbook" on public.intake_agent_playbook;
create policy "super_admin_can_manage_playbook"
  on public.intake_agent_playbook for all
  using (public.is_super_admin())
  with check (public.is_super_admin());

-- ────────────────────────────────────────────────────────────────────────────
-- Fin migration — ADR-IQ-08
-- ────────────────────────────────────────────────────────────────────────────
