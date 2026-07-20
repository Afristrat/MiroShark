-- US-235: décision ADR-019 durable, relisible et non silencieuse.
create table if not exists public.arena_routing_decisions (
  id uuid primary key default gen_random_uuid(),
  simulation_id text not null unique,
  policy_version text not null,
  scenario_type text not null,
  requested_populations text[] not null default '{}',
  recommended_arenas text[] not null default '{}',
  coverage_gaps jsonb not null default '[]'::jsonb,
  decision_source text not null check (decision_source in ('policy', 'user_override')),
  decision jsonb not null,
  created_at timestamptz not null default now()
);
alter table public.arena_routing_decisions enable row level security;
revoke all on public.arena_routing_decisions from anon, authenticated;
grant all on public.arena_routing_decisions to service_role;
comment on table public.arena_routing_decisions is 'US-235: audit ADR-019, règle appliquée ou override explicite; aucune arène non implémentée n''est simulée.';
