-- ============================================================================
-- Migration — table intake_sessions (US-IQ-01, chantier V2-B-intake)
-- ============================================================================
-- Remplace le formulaire /devis « formulaire de contact » par un parcours de
-- qualification structuré (docs/intake/01-intake-spec.md). Une row par
-- parcours démarré, même abandonné (mesure du funnel).
--
-- Schéma : docs/intake/02-data-dictionary-delta.md (fusionné dans le même
-- commit dans docs/02-data-dictionary.md, règle CLAUDE.md du repo).
--
-- RLS : parcours public, aucune policy anon en lecture/écriture directe —
-- tout passe par le backend en service_role. Lecture réservée super-admin.
-- Invariante SQL (pas code applicatif) : CHECK sur state + trigger
-- interdisant les transitions arrière (ex. completed → started).
-- ============================================================================

create table if not exists public.intake_sessions (
  id                   uuid        primary key default gen_random_uuid(),
  quote_id             text        references public.quote_ownership(quote_id) on delete set null,
  state                text        not null default 'started',
  brief                jsonb,
  transcript           jsonb,
  calcom_booking_uid   text,
  confidential_flags   jsonb       not null default '[]'::jsonb,
  route                text,
  entry_door           text        not null default 'standard',
  locale               text        not null default 'fr',
  agent_turns          int         not null default 0,
  created_at           timestamptz not null default now(),
  completed_at         timestamptz,
  constraint intake_sessions_state_chk check (state in (
    'started', 'form_submitted', 'agent_active', 'completed', 'abandoned'
  )),
  constraint intake_sessions_route_chk check (route is null or route in (
    'self_service', 'quote_48h', 'meeting'
  )),
  constraint intake_sessions_entry_door_chk check (entry_door in ('standard', 'aar')),
  constraint intake_sessions_locale_chk check (locale in ('fr', 'en', 'ar')),
  constraint intake_sessions_agent_turns_chk check (agent_turns >= 0 and agent_turns <= 7)
);

comment on table public.intake_sessions is
  'Parcours de qualification /devis « 3 temps » (US-IQ-01, module Intake) — 1 row par '
  'parcours démarré, même abandonné. Remplace le contexte de décision jamais capturé par '
  'l''ancien formulaire de contact (constat 2026-07-09, payload q_f767321b vide).';
comment on column public.intake_sessions.quote_id is
  'Posé à la soumission du formulaire A (état form_submitted) ; NULL si abandon avant.';
comment on column public.intake_sessions.state is
  'Machine à états : started → form_submitted → agent_active → completed, ou abandoned '
  'depuis n''importe quel état non terminal. Transitions contraintes par trigger (voir plus bas).';
comment on column public.intake_sessions.brief is
  'Brief structuré validé serveur (jsonschema) — schéma docs/intake/02-data-dictionary-delta.md.';
comment on column public.intake_sessions.transcript is
  'Échanges de l''étape B (agent conversationnel) : [{role, content, ts}]. Pièce DURABLE du '
  'dossier de devis (ADR-IQ-07, directive Amine 2026-07-09) — jamais purgée tant que le '
  'dossier existe. Donnée personnelle, cf. rétention doc 02-data-dictionary-delta.md.';
comment on column public.intake_sessions.confidential_flags is
  'Sujets flaggés « à aborder de vive voix » : [{topic_label, flagged_at}]. JAMAIS de '
  'contenu, uniquement un libellé de sujet (ADR-IQ-04).';
comment on column public.intake_sessions.route is
  'Branche de sortie (étape C, routage déterministe US-IQ-03) : self_service | quote_48h | meeting.';
comment on column public.intake_sessions.entry_door is
  'standard (porte 1) ou aar (porte 2 « Testez-nous sur du connu », US-IQ-05).';
comment on column public.intake_sessions.agent_turns is
  'Compteur de tours de l''agent de qualification — budget max 7 (US-IQ-02), vérifié en '
  'base, jamais côté front.';

create index if not exists idx_intake_sessions_quote_id
  on public.intake_sessions(quote_id) where quote_id is not null;
create index if not exists idx_intake_sessions_state
  on public.intake_sessions(state);

-- ────────────────────────────────────────────────────────────────────────────
-- Trigger : transitions d'état contraintes (invariante SQL, pas code applicatif)
-- ────────────────────────────────────────────────────────────────────────────
-- Rang croissant started(0) < form_submitted(1) < agent_active(2) < completed(3).
-- abandoned est atteignable depuis tout état non terminal. completed et
-- abandoned sont terminaux : aucune transition sortante autorisée.

create or replace function public.trg_intake_sessions_guard_state()
returns trigger
language plpgsql
as $$
declare
  v_rank_old int;
  v_rank_new int;
begin
  if TG_OP = 'UPDATE' and new.state is distinct from old.state then
    if old.state in ('completed', 'abandoned') then
      raise exception 'intake_sessions: transition % -> % refusée (état terminal)', old.state, new.state;
    end if;

    if new.state = 'abandoned' then
      return new; -- abandon autorisé depuis tout état non terminal
    end if;

    v_rank_old := case old.state
      when 'started' then 0 when 'form_submitted' then 1
      when 'agent_active' then 2 when 'completed' then 3 else -1 end;
    v_rank_new := case new.state
      when 'started' then 0 when 'form_submitted' then 1
      when 'agent_active' then 2 when 'completed' then 3 else -1 end;

    if v_rank_new < v_rank_old then
      raise exception 'intake_sessions: transition arrière % -> % refusée', old.state, new.state;
    end if;
  end if;
  return new;
end;
$$;

comment on function public.trg_intake_sessions_guard_state() is
  'Garde-fou machine à états intake_sessions — refuse toute transition arrière ou sortant '
  'd''un état terminal (completed/abandoned). Invariante posée en SQL (règle repo).';

drop trigger if exists trg_intake_sessions_guard_state on public.intake_sessions;
create trigger trg_intake_sessions_guard_state
  before update on public.intake_sessions
  for each row execute function public.trg_intake_sessions_guard_state();

-- ────────────────────────────────────────────────────────────────────────────
-- RLS
-- ────────────────────────────────────────────────────────────────────────────
alter table public.intake_sessions enable row level security;

-- Aucune policy anon : parcours public géré exclusivement par le backend en
-- service_role (bypass RLS). Lecture réservée super-admin (pattern
-- /api/admin/* existant, cf. is_super_admin() posée en 20260506_002).
drop policy if exists "super_admin_can_read_intake_sessions" on public.intake_sessions;
create policy "super_admin_can_read_intake_sessions"
  on public.intake_sessions for select
  using (public.is_super_admin());

-- ────────────────────────────────────────────────────────────────────────────
-- Fin migration — US-IQ-01
-- ────────────────────────────────────────────────────────────────────────────
