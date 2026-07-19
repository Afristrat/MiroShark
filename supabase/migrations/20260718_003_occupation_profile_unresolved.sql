-- US-229 / ADR-016: terms absent from ESCO for later enrichment by US-230.
create table public.occupation_profile_unresolved (
  label      text        not null check (btrim(label) <> ''),
  lang       text        not null check (btrim(lang) <> ''),
  created_at timestamptz not null default now(),
  primary key (label, lang)
);

comment on table public.occupation_profile_unresolved is
  'Best-effort trace of occupations unresolved by ESCO; US-230 input.';

alter table public.occupation_profile_unresolved enable row level security;

-- No client policy: only backend service_role writes this table.
