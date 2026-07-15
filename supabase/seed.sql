-- ============================================================================
-- Seed initial Bassira (à exécuter UNE FOIS après les migrations 001 + 002)
-- ============================================================================
-- À exécuter en 2 étapes pour éviter de polluer la DB avec un fake user_id :
--
--   Étape A — Maintenant : crée l'organisation "AIMPOWER · Bassira" (sans owner)
--   Étape B — Après ton signup via Supabase Auth (UI Vue ou dashboard) :
--             remplace <YOUR_AUTH_USER_ID> par ton vrai user_id et exécute la
--             section commentée [B].
-- ============================================================================

-- ────────────────────────────────────────────────────────────────────────────
-- [A] Crée l'organisation AIMPOWER (org de Bassira en interne)
-- ────────────────────────────────────────────────────────────────────────────
insert into public.organizations (name, slug, sector, country_code, status, metadata)
values (
  'AIMPOWER',
  'aimpower-bassira',
  'recherche',                         -- secteur métier de l'éditeur Bassira
  'MA',
  'active',
  jsonb_build_object(
    'description',  'Organisation interne Bassira — éditeur de la plateforme',
    'is_internal',  true,
    'website',      'https://bassira.ma'
  )
)
on conflict (slug) do nothing;

-- ────────────────────────────────────────────────────────────────────────────
-- [B] Une fois ton signup fait — récupère ton auth.users.id depuis :
--      Supabase Dashboard → Authentication → Users → clique sur ton email → ID
--
--    Puis exécute le bloc ci-dessous en remplaçant <YOUR_AUTH_USER_ID> :
-- ────────────────────────────────────────────────────────────────────────────
/*
insert into public.org_members (org_id, user_id, role)
select o.id, '<YOUR_AUTH_USER_ID>'::uuid, 'owner'
from public.organizations o
where o.slug = 'aimpower-bassira'
on conflict (org_id, user_id) do update set role = 'owner';
*/

-- ────────────────────────────────────────────────────────────────────────────
-- [C] (Optionnel) Pour rétro-attribuer les sims existantes en filesystem à
--     l'org AIMPOWER. À exécuter UNE FOIS après le déploiement du backend
--     qui aura listé tes sim_xxxxx existants. Le sub-agent US-092 produira
--     un script Python qui appelle ce SQL avec la liste des simulation_id
--     existants — ne pas exécuter manuellement avant.
-- ────────────────────────────────────────────────────────────────────────────
-- (placeholder, voir US-092)
