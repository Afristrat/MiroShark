-- US-IQ-07 — traçabilité durable du devis vers la simulation créée.
alter table public.simulation_ownership
  add column if not exists intake_session_id uuid references public.intake_sessions(id) on delete set null;

create index if not exists idx_simulation_ownership_intake_session
  on public.simulation_ownership(intake_session_id) where intake_session_id is not null;
