-- ─────────────────────────────────────────────────────────────────────────────
-- US-203 (V2 Bloc A) — payload riche des devis dans Supabase.
--
-- AVANT : quote_ownership n'était qu'un index (quote_id → org_id, status) ;
-- le payload complet (full_name, message, geo_focus, …) vivait UNIQUEMENT
-- sur backend/uploads/quotes/quote_*.json — volume éphémère sur Coolify :
-- un redeploy pouvait effacer des leads (PII incluse) sans trace.
--
-- APRÈS : Supabase devient la SOURCE DE VÉRITÉ du payload (colonne jsonb) ;
-- le filesystem est rétrogradé en cache best-effort (dev local, export).
-- RLS : déjà activée sur la table (migration 20260505_001) — les policies
-- existantes couvrent la nouvelle colonne (même row).
-- ─────────────────────────────────────────────────────────────────────────────

alter table public.quote_ownership
  add column if not exists payload jsonb not null default '{}'::jsonb;

comment on column public.quote_ownership.payload is
  'Payload complet du devis à la soumission (US-203). Source de vérité — '
  'le fichier quotes/quote_*.json n''est plus qu''un cache best-effort. '
  'Contient des PII (full_name, email, phone) : accès via RLS org / service_role.';

comment on table public.quote_ownership is
  'Devis : index org + statut + payload complet (source de vérité depuis US-203).';
