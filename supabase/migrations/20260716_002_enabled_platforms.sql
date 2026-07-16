-- ============================================================================
-- Migration — simulation_ownership.enabled_platforms (US-222)
-- ============================================================================
-- Arènes activées à la création de la simulation, requêtables en SQL (jusqu'ici
-- perdues dans les flags enable_twitter/enable_reddit/enable_polymarket du
-- state filesystem — aucune requête cross-simulations possible). Peuplée
-- uniquement pour les simulations avec org_id (mode multitenant, US-092) —
-- même périmètre que le reste de simulation_ownership.
-- ============================================================================

alter table public.simulation_ownership
  add column if not exists enabled_platforms text[] not null default '{}';

comment on column public.simulation_ownership.enabled_platforms is
  'Arènes activées à la création (ex. {twitter,reddit}) — source de vérité '
  'SQL, dérivée de SimulationState.enable_* au moment de create_simulation() '
  '(US-222). Le registre de noms d''arènes canonique reste '
  'app/services/arena_registry.py (Python, pas SQL) — cette colonne est un '
  'snapshot par simulation, pas le registre lui-même.';

-- ────────────────────────────────────────────────────────────────────────────
-- Fin migration — US-222
-- ────────────────────────────────────────────────────────────────────────────
