-- ============================================================================
-- Migration 20260506_001 — Table pdf_branding (US-120)
-- ============================================================================
--
-- Contexte
-- ────────
-- Cette migration introduit la table ``public.pdf_branding`` qui stocke les
-- configurations de mise en page PDF (header, footer, palette de couleurs,
-- typographie, disclaimer) par organisation.
--
-- Architecture de versioning
-- ──────────────────────────
-- La table est « append-only » : une mise à jour crée une NOUVELLE row avec
-- ``valid_from = now()`` et marque l'ancienne row avec ``valid_to = now()``.
-- Cela permet un audit complet de l'historique de branding sans perdre de
-- données. La version active est celle avec ``valid_from <= now()`` et
-- ``(valid_to IS NULL OR valid_to > now())``.
--
-- Placeholders supportés dans header_*/footer_* :
--   {{logo}}, {{section}}, {{page}}, {{total}}, {{report_id}},
--   {{client_name}}, {{date}}, {{org_name}}, {{generated_at}}
--
-- RLS
-- ───
--   - SELECT : super-admin bypass + member voit son org
--   - INSERT : org admin/owner OU super-admin
--   - UPDATE : org admin/owner OU super-admin (en pratique le backend
--     crée une nouvelle row au lieu d'UPDATE — la policy est là pour
--     les migrations futures directes)
--   - DELETE : super-admin uniquement
-- ============================================================================

-- ────────────────────────────────────────────────────────────────────────────
-- 1. Table pdf_branding
-- ────────────────────────────────────────────────────────────────────────────
create table if not exists public.pdf_branding (
  id                  uuid primary key default gen_random_uuid(),
  org_id              uuid not null references public.organizations(id) on delete cascade,
  name                text not null,

  -- Logo
  logo_url            text,

  -- Header / footer (template strings avec placeholders {{...}})
  header_left         text not null default '{{logo}}',
  header_center       text not null default '{{section}}',
  header_right        text not null default 'Page {{page}}/{{total}}',
  footer_left         text not null default '{{report_id}} · CONFIDENTIEL',
  footer_center       text not null default '{{generated_at}}',
  footer_right        text not null default 'bassira.ai',

  -- Palette couleurs (valeurs CSS hex)
  palette_primary     text not null default '#FF8551',
  palette_secondary   text not null default '#006D44',
  palette_text        text not null default '#241915',
  palette_background  text not null default '#FAF7F2',

  -- Typographie
  font_titles         text not null default 'Outfit',
  font_body           text not null default 'Manrope',
  font_mono           text not null default 'JetBrains Mono',

  -- Disclaimer multilingue
  disclaimer_text     jsonb not null default '{
    "fr": "Confidentiel · Probabiliste · Usage interne",
    "en": "Confidential · Probabilistic · Internal use",
    "ar": "سري · احتمالي · استخدام داخلي"
  }'::jsonb,

  -- Versioning temporel
  valid_from          timestamptz not null default now(),
  valid_to            timestamptz,            -- null = version active

  -- Audit
  created_by          uuid references auth.users(id) on delete set null,
  created_at          timestamptz not null default now(),

  -- Contraintes
  constraint pdf_branding_name_not_empty check (char_length(trim(name)) > 0),
  constraint pdf_branding_valid_range check (valid_to is null or valid_to > valid_from)
);

-- Index pour la récupération du branding actif par org
create index if not exists idx_pdf_branding_org_valid_from
  on public.pdf_branding(org_id, valid_from desc);

-- Index partiel pour les versions actives uniquement
create index if not exists idx_pdf_branding_active
  on public.pdf_branding(org_id)
  where valid_to is null;

comment on table public.pdf_branding is
  'Configuration de mise en page PDF par org Bassira (US-120). Versioning append-only.';
comment on column public.pdf_branding.valid_from is
  'Date de début de validité. La version active a valid_from <= now() et (valid_to IS NULL OR valid_to > now()).';
comment on column public.pdf_branding.valid_to is
  'Date de fin de validité. NULL = version courante. Mise à jour par le backend lors d''un changement de branding.';
comment on column public.pdf_branding.disclaimer_text is
  'Disclaimer de bas de page multilingue. JSON avec clés "fr", "en", "ar".';

-- ────────────────────────────────────────────────────────────────────────────
-- 2. RLS — Row Level Security
-- ────────────────────────────────────────────────────────────────────────────
alter table public.pdf_branding enable row level security;

-- SELECT : les membres d'une org voient le branding de leur org.
-- Le super-admin (service_role) bypass automatiquement la RLS.
drop policy if exists "members_can_read_org_branding" on public.pdf_branding;
create policy "members_can_read_org_branding"
  on public.pdf_branding for select
  using (org_id in (select public.user_orgs()));

-- INSERT : org admin/owner peut créer un branding.
drop policy if exists "admins_can_create_branding" on public.pdf_branding;
create policy "admins_can_create_branding"
  on public.pdf_branding for insert
  with check (org_id in (
    select org_id from public.org_members
    where user_id = auth.uid() and role in ('owner', 'admin')
  ));

-- UPDATE : org admin/owner peut modifier (en pratique : le backend crée
-- une nouvelle row — cette policy protège les accès directs futurs).
drop policy if exists "admins_can_update_branding" on public.pdf_branding;
create policy "admins_can_update_branding"
  on public.pdf_branding for update
  using (org_id in (
    select org_id from public.org_members
    where user_id = auth.uid() and role in ('owner', 'admin')
  ));

-- DELETE : super-admin uniquement (pas de self-delete par les org admins).
-- En production le super-admin passe par service_role → RLS bypass.
-- Cette policy protège les accès directs via JWT utilisateur.
-- Aucun user normal ne peut supprimer un branding.
drop policy if exists "only_service_role_can_delete_branding" on public.pdf_branding;
create policy "only_service_role_can_delete_branding"
  on public.pdf_branding for delete
  using (false);

-- ────────────────────────────────────────────────────────────────────────────
-- Fin migration 20260506_001
-- ────────────────────────────────────────────────────────────────────────────
