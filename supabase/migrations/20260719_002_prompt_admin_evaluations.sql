-- US-233: durable deterministic evaluations and atomic prompt activation.

create table if not exists public.simulation_prompt_evaluations (
  id         uuid primary key default gen_random_uuid(),
  prompt_id  uuid not null references public.simulation_prompts(id) on delete restrict,
  passed     boolean not null,
  cases      jsonb not null,
  created_by text not null,
  created_at timestamptz not null default now(),
  constraint simulation_prompt_evaluations_cases_array check (jsonb_typeof(cases) = 'array')
);

create index if not exists idx_simulation_prompt_evaluations_prompt_created
  on public.simulation_prompt_evaluations (prompt_id, created_at desc);

alter table public.simulation_prompt_evaluations enable row level security;

drop policy if exists "super_admin_can_manage_prompt_evaluations" on public.simulation_prompt_evaluations;
create policy "super_admin_can_manage_prompt_evaluations"
  on public.simulation_prompt_evaluations for all
  using (public.is_super_admin())
  with check (public.is_super_admin());

-- Content, identity and version are immutable.  Only the atomic activation
-- function below may change is_active, and it never touches prompt content.
create or replace function public.reject_simulation_prompt_mutation()
returns trigger language plpgsql as $$
begin
  if new.key is distinct from old.key
     or new.scope is distinct from old.scope
     or new.locale is distinct from old.locale
     or new.version is distinct from old.version
     or new.content is distinct from old.content
     or new.variables is distinct from old.variables
     or new.created_by is distinct from old.created_by
     or new.created_at is distinct from old.created_at then
    raise exception 'simulation_prompts versions are immutable' using errcode = '23514';
  end if;
  return new;
end;
$$;

drop trigger if exists simulation_prompts_immutable on public.simulation_prompts;
create trigger simulation_prompts_immutable
before update on public.simulation_prompts
for each row execute function public.reject_simulation_prompt_mutation();

create or replace function public.activate_simulation_prompt(p_prompt_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  target public.simulation_prompts%rowtype;
  latest_eval public.simulation_prompt_evaluations%rowtype;
begin
  if auth.role() <> 'service_role' and not public.is_super_admin() then
    raise exception 'super-admin authorization required' using errcode = '42501';
  end if;

  select * into target from public.simulation_prompts where id = p_prompt_id for update;
  if target.id is null then
    raise exception 'prompt version not found' using errcode = 'P0002';
  end if;

  select * into latest_eval
  from public.simulation_prompt_evaluations
  where prompt_id = target.id
  order by created_at desc, id desc
  limit 1;
  if latest_eval.id is null or latest_eval.passed is not true then
    raise exception 'a passing evaluation is required before activation' using errcode = '23514';
  end if;

  update public.simulation_prompts
  set is_active = false
  where key = target.key and locale = target.locale and is_active;
  update public.simulation_prompts set is_active = true where id = target.id;

  select * into target from public.simulation_prompts where id = target.id;
  return to_jsonb(target);
end;
$$;

revoke all on function public.activate_simulation_prompt(uuid) from public;
grant execute on function public.activate_simulation_prompt(uuid) to authenticated, service_role;
