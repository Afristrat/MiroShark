-- ============================================================================
-- Migration — occupation_profiles (US-228, ADR-016)
-- ============================================================================
-- Cache Supabase des fiches métiers ESCO (+ enrichissement 122B, US-230) pour
-- le bloc <expertise_metier> injecté dans les system prompts des personas
-- (US-229, story dépendante — pas câblée ici).
--
-- Clé de cache : (label, lang) où `label` est le TERME DE RECHERCHE normalisé
-- (trim + lowercase) fourni par l'appelant — pas nécessairement le prefLabel
-- canonique ESCO retourné par l'API (qui peut légèrement différer). Ce choix
-- garantit qu'un second appel avec le MÊME terme de recherche est servi par
-- le cache sans toucher le réseau (US-228 AC3), sans colonne supplémentaire
-- hors du schéma documenté dans la spec §3.2/§4.
-- ============================================================================

create table if not exists public.occupation_profiles (
  id                uuid        primary key default gen_random_uuid(),
  occupation_uri    text        not null,
  label             text        not null,
  lang              text        not null,
  definition        text        not null default '',
  essential_skills  jsonb       not null default '[]'::jsonb,
  optional_skills   jsonb       not null default '[]'::jsonb,
  source            text        not null check (source in ('esco', 'llm_122b')),
  fetched_at        timestamptz not null default now(),
  unique (label, lang)
);

comment on table public.occupation_profiles is
  'Cache des fiches métiers ESCO (+ 122B pour les rôles hors-taxonomie, '
  'US-230) — ADR-016. Clé de cache (label, lang) = terme de recherche '
  'normalisé, pas nécessairement le prefLabel ESCO canonique.';
comment on column public.occupation_profiles.label is
  'Terme de recherche normalisé (trim + lowercase) — clé de cache, PAS '
  'garanti identique au prefLabel ESCO retourné (cf. commentaire table).';
comment on column public.occupation_profiles.source is
  'esco = fiche taxonomie officielle ; llm_122b = enrichissement pour rôle '
  'hors-taxonomie (influenceur, militant en ligne...) via gateway LiteLLM (US-230).';

create index if not exists idx_occupation_profiles_label_lang
  on public.occupation_profiles (label, lang);

alter table public.occupation_profiles enable row level security;

-- Écriture réservée service_role (backend) + is_super_admin() côté client
-- authentifié (pipeline 122B / future console admin US-230). Lecture élargie
-- à authenticated : données non sensibles (taxonomie ESCO publique +
-- enrichissement LLM), consommées par le moteur de simulation pour tout
-- utilisateur générant des personas (pas seulement les super-admins).
drop policy if exists "authenticated_can_read_occupation_profiles" on public.occupation_profiles;
create policy "authenticated_can_read_occupation_profiles"
  on public.occupation_profiles for select
  using (auth.role() = 'authenticated');

drop policy if exists "super_admin_can_write_occupation_profiles" on public.occupation_profiles;
create policy "super_admin_can_write_occupation_profiles"
  on public.occupation_profiles for insert
  with check (public.is_super_admin());

drop policy if exists "super_admin_can_update_occupation_profiles" on public.occupation_profiles;
create policy "super_admin_can_update_occupation_profiles"
  on public.occupation_profiles for update
  using (public.is_super_admin())
  with check (public.is_super_admin());

drop policy if exists "super_admin_can_delete_occupation_profiles" on public.occupation_profiles;
create policy "super_admin_can_delete_occupation_profiles"
  on public.occupation_profiles for delete
  using (public.is_super_admin());

-- ────────────────────────────────────────────────────────────────────────────
-- Fin migration — US-228 / ADR-016
-- ────────────────────────────────────────────────────────────────────────────
