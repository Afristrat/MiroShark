-- ============================================================================
-- Migration 002 — VIEW publique de calibration agrégée (US-091)
-- ============================================================================
-- Expose les scores de Brier moyens par secteur, agrégés sur les sims
-- publiées et avec outcome marqué. K-anonymity stricte : seuils n>=5 par secteur,
-- sinon le secteur est masqué (pas de fuite via reverse engineering avec n petit).
--
-- Cette VIEW est consommée par /calibration v2 publique (US-095).
-- ============================================================================

create or replace view public.public_calibration_aggregates as
select
  o.sector,
  count(*)                            as n_published,
  round(avg(s.brier_score)::numeric, 3) as avg_brier,
  round(min(s.brier_score)::numeric, 3) as min_brier,
  round(max(s.brier_score)::numeric, 3) as max_brier,
  count(*) filter (where (s.outcome->>'label') = 'called_it') as n_called_it,
  count(*) filter (where (s.outcome->>'label') = 'partial')   as n_partial,
  count(*) filter (where (s.outcome->>'label') = 'wrong')     as n_wrong
from public.simulation_ownership s
join public.organizations o on s.org_id = o.id
where s.is_published = true
  and s.brier_score is not null
  and s.outcome is not null
  and o.status = 'active'
group by o.sector
having count(*) >= 5;   -- k-anonymity strict : pas de secteur exposé avec n<5

comment on view public.public_calibration_aggregates is
  'Agrégat public des scores de Brier par secteur. K-anonymity n>=5 strict.
   Consommé par la page /calibration v2 publique (US-095).
   Pas d''exposition d''org_id, d''user_id, ou d''outcome individuel.';

-- ────────────────────────────────────────────────────────────────────────────
-- Grants : lecture autorisée pour le rôle anon (visiteurs cold) et authenticated
-- ────────────────────────────────────────────────────────────────────────────
grant select on public.public_calibration_aggregates to anon, authenticated;

-- ────────────────────────────────────────────────────────────────────────────
-- Fin migration 002
-- ────────────────────────────────────────────────────────────────────────────
