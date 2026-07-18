"""US-226: durable resolution table contract and tenant boundary."""

from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260718_002_market_resolutions.sql"
)


def test_us226_market_resolutions_migration_contract() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "create table public.market_resolutions" in sql
    assert "market_id       bigint" in sql
    assert "primary key (simulation_id, market_id)" in sql
    assert "org_id          uuid             not null" in sql
    assert "unique (simulation_id, org_id)" in sql
    assert "foreign key (simulation_id, org_id)" in sql
    assert "references public.simulation_ownership (simulation_id, org_id)" in sql
    assert "verdict in ('YES', 'NO', 'INVALID', 'UNRESOLVED')" in sql
    assert "jsonb_typeof(evidence) = 'array'" in sql
    assert "price_series    jsonb            not null default '[]'::jsonb" in sql
    assert "payout_summary  jsonb            not null default '{}'::jsonb" in sql
    assert "market_resolutions_confidence_chk" in sql
    assert "idx_market_resolutions_org_resolved" in sql


def test_us226_rls_is_read_only_for_tenant_members() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "alter table public.market_resolutions enable row level security" in sql
    assert "on public.market_resolutions for select" in sql
    assert "org_id in (select public.user_orgs())" in sql
    assert "No client write policy" in sql
    assert "controlled durable updates" in sql
    assert "for insert" not in sql
    assert "for update" not in sql
    assert "for delete" not in sql


def test_us226_seed_is_versioned_and_stable() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "'oracle.resolution'" in sql
    assert "YES|NO|INVALID|UNRESOLVED" not in sql
    evidence_example = '"round":1,"type":"trajectory","ref":"round:1:0"'
    assert sql.count(evidence_example) == 3
    assert sql.count("'system-seed-US-226'") == 3
    for locale in ("fr", "en", "ar"):
        assert f"'oracle.resolution', 'oracle', '{locale}', 1" in sql
    assert "on conflict (key, locale, version) do nothing" in sql
