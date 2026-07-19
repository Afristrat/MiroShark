"""US-233 migration contract: immutable prompts, RLS and atomic gate."""

from pathlib import Path


MIGRATION = Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "20260719_002_prompt_admin_evaluations.sql"


def test_us233_migration_has_durable_evaluation_gate_and_rls() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "create table if not exists public.simulation_prompt_evaluations" in sql
    assert "prompt_id  uuid not null references public.simulation_prompts(id)" in sql
    assert "jsonb_typeof(cases) = 'array'" in sql
    assert "alter table public.simulation_prompt_evaluations enable row level security" in sql
    assert "super_admin_can_manage_prompt_evaluations" in sql


def test_us233_migration_enforces_immutable_content_and_atomic_activation() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "simulation_prompts versions are immutable" in sql
    assert "create or replace function public.activate_simulation_prompt" in sql
    assert "security definer" in sql
    assert "latest_eval.id is null or latest_eval.passed is not true" in sql
    assert "update public.simulation_prompts\n  set is_active = false" in sql
    assert "update public.simulation_prompts set is_active = true where id = target.id" in sql
    assert "grant execute on function public.activate_simulation_prompt(uuid) to authenticated, service_role" in sql
