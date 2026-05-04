-- ============================================================================
-- Migration 20260504_002 — Rétro-attribution des sims filesystem
--                          (pré-multitenant US-091) → org aimpower-bassira
-- ============================================================================
--
-- Contexte
-- ────────
-- Les simulations créées AVANT US-091 (déploiement multitenant) existent
-- uniquement sur le filesystem du backend (``backend/uploads/simulations/
-- sim_xxxxxxxxxxxx/``) et n'ont aucune entrée dans la table Supabase
-- ``public.simulation_ownership``. Conséquence : la vue cross-tenant
-- super-admin de US-097 (``/admin/analytics``) affiche un total non nul
-- mais un tableau vide, ce qui donne une fausse incohérence à l'œil.
--
-- Cette migration rétro-attribue ces sims à l'organisation interne
-- ``aimpower-bassira`` (slug fixe seedé en étape A de ``seed.sql``).
--
-- Caractéristiques
-- ────────────────
-- • Idempotente : ``on conflict (simulation_id) do nothing`` — la rejouer
--   N fois ne crée aucun doublon ni écrasement.
-- • Sans dépendance applicative : pure SQL Supabase, à exécuter dans le
--   SQL Editor par Amine après vérif que US-091/098 sont bien déployées.
-- • Auditable : chaque ligne ``VALUES`` est générée par
--   ``backend/scripts/check_legacy_sims_attribution.py --sql`` lancé sur
--   l'environnement où vivent les vrais dossiers (= la prod Coolify).
--   La sortie de ce script est à coller à la place du bloc placeholder
--   ci-dessous.
--
-- ⚠️ À exécuter UNE FOIS, après déploiement US-091 + US-098 + US-100,
--    et avant le chantier US-1xx « commande de devis » qui s'appuiera
--    sur ``simulation_ownership`` pour rattacher les nouvelles sims.
-- ============================================================================

with target_org as (
  select id from public.organizations where slug = 'aimpower-bassira'
)
insert into public.simulation_ownership
  (simulation_id, org_id, created_at, package_id, is_published, outcome, brier_score)
values
  -- ─── BLOC À REMPLACER ────────────────────────────────────────────────────
  -- Lance sur la prod (ou un snapshot prod monté en local) :
  --
  --     cd backend && uv run python scripts/check_legacy_sims_attribution.py --sql
  --
  -- Puis colle la sortie ici, en remplaçant la ligne placeholder ci-dessous.
  -- La requête reste runnable même sans aucune sim réelle : la ligne
  -- ``__placeholder__`` est insérée puis immédiatement supprimée par le
  -- ``delete`` qui suit (no-op fonctionnel, garde la migration valide).
  --
  -- Exemple de ligne attendue (NE PAS exécuter telle quelle) :
  -- ('sim_eabf56674a12', (select id from target_org), '2026-04-29T19:00:00Z'::timestamptz, 'crisis_24h_brand', false, null, null),
  --
  -- no sims to backfill — placeholder neutralisant inséré ci-dessous pour
  -- garder la migration syntaxiquement valide tant qu'aucune sim n'a été
  -- listée. Dès que tu colleras la sortie du script Python à la place,
  -- supprime cette ligne placeholder (le ``delete`` final restera
  -- inoffensif puisqu'aucune ligne ``__placeholder__`` ne sera présente).
  ('__placeholder__', (select id from target_org), now(), null, false, null, null)
  -- ────────────────────────────────────────────────────────────────────────
on conflict (simulation_id) do nothing;

-- Nettoyage du placeholder factice (no-op si la liste réelle a été collée).
delete from public.simulation_ownership where simulation_id = '__placeholder__';

-- ============================================================================
-- Vérification post-exécution (à lancer après la migration)
-- ============================================================================
--
-- -- 1) Compter les sims attribuées à aimpower-bassira :
-- select count(*) as sims_attributed
--   from public.simulation_ownership s
--   join public.organizations o on o.id = s.org_id
--  where o.slug = 'aimpower-bassira';
--
-- -- 2) Lister les sims les plus récentes pour spot-check :
-- select s.simulation_id, s.created_at, s.package_id, s.is_published
--   from public.simulation_ownership s
--   join public.organizations o on o.id = s.org_id
--  where o.slug = 'aimpower-bassira'
--  order by s.created_at desc
--  limit 20;
--
-- -- 3) Comparer avec l'inventaire filesystem (côté prod) :
-- --    cd backend && uv run python scripts/check_legacy_sims_attribution.py
-- --    Le count doit matcher exactement.
-- ============================================================================
