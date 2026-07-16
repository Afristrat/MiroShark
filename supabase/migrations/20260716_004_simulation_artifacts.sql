-- ============================================================================
-- Migration — bucket Storage + simulation_artifacts (US-221, ADR-005)
-- ============================================================================
-- Persistance durable des artefacts de simulation (state.json, actions.jsonl,
-- trajectory.json, profils, DB SQLite polymarket/twitter/reddit...) —
-- jusqu'ici UNIQUEMENT sur backend/uploads/simulations/ (volume Coolify
-- éphémère, ADR-005). Premier usage de Supabase Storage dans ce projet —
-- aucun bucket créé avant cette migration.
--
-- Design "hydratation de répertoire" (pas un mapping fichier par fichier) :
-- un objet Storage par fichier local, sous le préfixe
-- `simulations/<simulation_id>/<chemin relatif>`. `simulation_artifacts` est
-- la table de métadonnées REQUÊTABLE (quels fichiers existent, taille,
-- dernière synchro) — la source de vérité binaire reste le bucket Storage,
-- cette table ne fait qu'indexer.
-- ============================================================================

-- Bucket privé : accès exclusivement service_role (backend), comme le reste
-- des accès Supabase de ce projet — pas de policy anon/authenticated, RLS
-- storage.objects par défaut refuse tout sauf service_role qui la contourne.
insert into storage.buckets (id, name, public)
values ('simulation-artifacts', 'simulation-artifacts', false)
on conflict (id) do nothing;

create table if not exists public.simulation_artifacts (
  id              uuid        primary key default gen_random_uuid(),
  simulation_id   text        not null,
  relative_path   text        not null,
  storage_path    text        not null,
  size_bytes      bigint      not null default 0,
  synced_at       timestamptz not null default now(),
  unique (simulation_id, relative_path)
);

comment on table public.simulation_artifacts is
  'Index requêtable des artefacts de simulation synchronisés vers le bucket '
  'Storage "simulation-artifacts" (US-221, ADR-005). La source de vérité '
  'binaire est le bucket ; cette table permet de savoir SANS lister le '
  'bucket quels fichiers existent durablement pour une simulation.';
comment on column public.simulation_artifacts.relative_path is
  'Chemin relatif au dossier de la simulation (ex. "state.json", '
  '"twitter/actions.jsonl", "polymarket_simulation.db").';
comment on column public.simulation_artifacts.storage_path is
  'Chemin complet dans le bucket (simulations/<simulation_id>/<relative_path>).';

create index if not exists idx_simulation_artifacts_simulation_id
  on public.simulation_artifacts (simulation_id);

alter table public.simulation_artifacts enable row level security;

-- Écriture/lecture exclusivement service_role (backend) — même pattern que
-- les autres tables opérationnelles de ce projet (aucune policy anon).
drop policy if exists "super_admin_can_manage_simulation_artifacts" on public.simulation_artifacts;
create policy "super_admin_can_manage_simulation_artifacts"
  on public.simulation_artifacts for all
  using (public.is_super_admin())
  with check (public.is_super_admin());

-- ────────────────────────────────────────────────────────────────────────────
-- Fin migration — US-221 / ADR-005
-- ────────────────────────────────────────────────────────────────────────────
