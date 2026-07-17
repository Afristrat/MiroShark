-- US-IQ-05 — issue réelle AAR scellée hors du brief exposé aux consommateurs.
alter table public.intake_sessions
  add column if not exists aar_outcome_sealed text,
  add column if not exists aar_outcome_commitment text;

comment on column public.intake_sessions.aar_outcome_sealed is
  'Issue réelle AAR chiffrée applicativement ; déchiffrement réservé au chemin de restitution.';
comment on column public.intake_sessions.aar_outcome_commitment is
  'Empreinte SHA-256 du clair remise au prospect à la soumission.';
