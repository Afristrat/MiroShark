# Data Dictionary — Bassira V2

> Contrat de nommage. Toute table/colonne se vérifie ICI avant d'être nommée ; toute
> création met ce fichier à jour DANS LE MÊME COMMIT. SQL en snake_case ; le code
> applicatif suit les conventions de son langage.
> État extrait des migrations réelles `supabase/migrations/` le 2026-07-07 (10 fichiers,
> 12 tables, **RLS activée sur les 12** — vérifié).

## Vue d'ensemble

| Table | Migration | PII | Rôle |
|---|---|---|---|
| organizations | 20260503_001 | non | Tenants |
| org_members | 20260503_001 | user_id | Appartenance + rôle |
| simulation_ownership | 20260503_001 | non | Mapping simulation ↔ org, outcome, Brier |
| quote_ownership | 20260505_001 | **customer_email** | Mapping devis ↔ org |
| org_invitations | 20260505_002 | **email** | Invitations (token UUID, TTL 7 j) |
| pdf_branding | 20260506_001 | non | Branding PDF versionné (append-only) |
| report_states | 20260506_002 | non | État workflow rapport (7 états) |
| report_audit_log | 20260506_002 | **ip_address, user_agent, actor_email** | Audit immuable (UPDATE/DELETE bloqués) |
| report_versions | 20260506_003 | non | Versioning markdown |
| report_comments | 20260506_003 | non | Annotations par paragraphe |
| report_deliveries | 20260506_004 | **recipient_email, recipient_name** | Livraison URL signée TTL |
| report_downloads | 20260506_004 | **ip_address, user_agent, country_code** | Tracking téléchargements |

## `organizations`
Tenant racine du multi-org.
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| id | uuid | pk, default gen_random_uuid() | | non |
| name | text | not null | Nom affiché | non |
| slug | text | not null, unique | Identifiant URL | non |
| sector | text | | banque/énergie/politique/… | non |
| country_code | text | | ISO 3166-1 alpha-2 | non |
| status | text | not null, check in (active, suspended, trial) | | non |
| created_at / updated_at | timestamptz | not null, default now() | | non |
| metadata | jsonb | not null, default '{}' | | non |

## `org_members`
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| id | uuid | pk | | non |
| org_id | uuid | fk organizations.id, on delete cascade, not null | tenant | non |
| user_id | uuid | fk auth.users.id, on delete cascade, not null, unique (org_id, user_id) | | oui |
| role | text | not null, check in (owner, admin, member, viewer) | | non |
| created_at | timestamptz | not null, default now() | | non |
| invited_by | uuid | fk auth.users.id | | oui |

## `simulation_ownership`
Métadonnées légères ; le payload riche (profils, trajectoire, state.json) vit sur
`backend/uploads/` — **[V2-P0]** à migrer vers stockage durable (ADR-005).
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| simulation_id | text | pk | id Bassira (sim_xxx) | non |
| org_id | uuid | fk organizations.id, cascade, not null | | non |
| created_by | uuid | fk auth.users.id | | oui |
| created_at | timestamptz | not null, default now() | | non |
| package_id | text | | package /devis d'origine | non |
| is_published | boolean | not null, default false | galerie publique | non |
| outcome | jsonb | | {label, observed_at, source_url, notes} | non |
| brier_score | numeric | | calculé après outcome | non |
| metadata | jsonb | not null, default '{}' | | non |

## `quote_ownership`
✅ US-203 (migration 20260707_001) : la colonne `payload` fait de Supabase la **source
de vérité** du devis complet ; `backend/uploads/quotes/` est rétrogradé en cache
best-effort (le bug P0 « leads PII sur volume éphémère » est corrigé à la racine).
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| quote_id | text | pk | ex. `q_abc12345` (devis manuel) ou `stripe_cs_...` (achat self-service US-205/ADR-014, préfixe = ID de la Checkout Session) | non |
| org_id | uuid | fk organizations.id, cascade, not null | | non |
| customer_email | text | | contact à la soumission | **oui** |
| package_id | text | | | non |
| status | text | not null, check in (received, reviewing, quoted, declined, paid, in_progress, delivered) | | non |
| created_at | timestamptz | not null, default now() | | non |
| metadata | jsonb | not null, default '{}' | | non |
| payload | jsonb | not null, default '{}' | payload complet à la soumission (full_name, phone, message, geo_focus…) — source de vérité US-203 | **oui** (full_name, email, phone, client_ip) |

## `org_invitations`
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| token | uuid | pk, default gen_random_uuid() | token d'invitation | non |
| org_id | uuid | fk organizations.id, cascade, not null | | non |
| email | text | not null | destinataire | **oui** |
| role | text | not null, check in (admin, member, viewer) | | non |
| expires_at | timestamptz | not null, default now()+7 days | | non |
| accepted_at | timestamptz | | | non |
| invited_by | uuid | fk auth.users.id, set null | | oui |
| created_at | timestamptz | not null, default now() | | non |
| metadata | jsonb | not null, default '{}' | | non |

## `pdf_branding`
Versionné temporellement (valid_from/valid_to, null = actif). Défauts = palette Causse.
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| id | uuid | pk | | non |
| org_id | uuid | fk organizations.id, cascade, not null | | non |
| name | text | not null | | non |
| logo_url | text | | | non |
| header_left/center/right | text | not null, defaults ({{logo}}, {{section}}, Page {{page}}/{{total}}) | templates | non |
| footer_left/center/right | text | not null, defaults ({{report_id}} · CONFIDENTIEL, {{generated_at}}, bassira.ma) — défaut corrigé en bassira.ma par la migration 20260707_002 (ADR-013, US-204) | | non |
| palette_primary | text | not null, default '#FF8551' | | non |
| palette_secondary | text | not null, default '#006D44' | | non |
| palette_text | text | not null, default '#241915' | | non |
| palette_background | text | not null, default '#FAF7F2' | | non |
| font_titles / font_body / font_mono | text | not null, defaults Outfit / Manrope / JetBrains Mono | | non |
| disclaimer_text | jsonb | not null, default trilingue fr/en/ar | | non |
| valid_from / valid_to | timestamptz | not null default now() / null = actif | versioning | non |

## `report_states`
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| report_id | text | pk | | non |
| state | text | not null, check in (GENERATING, DRAFT, IN_REVIEW, PENDING_APPROVAL, APPROVED, DELIVERED, ARCHIVED) | | non |
| current_version | int | not null, default 1 | | non |
| last_transition_at | timestamptz | not null, default now() | | non |
| last_transition_by / locked_by | uuid | fk auth.users.id | | oui |
| locked_at | timestamptz | | verrou d'édition | non |
| org_id | uuid | fk organizations.id, cascade, not null | | non |
| created_at / updated_at | timestamptz | not null, default now() | | non |

## `report_audit_log` — IMMUABLE (triggers bloquent UPDATE/DELETE)
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| id | uuid | pk | | non |
| report_id | text | not null | | non |
| from_state / to_state | text | to_state not null | | non |
| actor_id | uuid | fk auth.users.id | | oui |
| actor_email | text | | | **oui** |
| ip_address | inet | | | **oui** |
| user_agent | text | | | **oui** |
| snapshot_hash | text | | intégrité | non |
| comment | text | | | non |
| created_at | timestamptz | not null, default now() | | non |

## `report_versions`
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| version_id | uuid | pk | | non |
| report_id | text | not null, unique (report_id, version_number) | | non |
| version_number | int | not null | | non |
| markdown_content | text | not null, default '' | | non |
| created_by | uuid | fk auth.users.id, set null | | oui |
| created_at | timestamptz | not null, default now() | | non |
| comment | text | | | non |

## `report_comments`
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| comment_id | uuid | pk | | non |
| report_id | text | not null | | non |
| version_id | uuid | fk report_versions.version_id, set null | | non |
| paragraph_anchor | text | not null, default '' | sélecteur/hash paragraphe | non |
| author_id | uuid | fk auth.users.id, set null | | oui |
| body | text | not null, default '' | | non |
| resolved | bool | not null, default false | | non |
| created_at | timestamptz | not null, default now() | | non |

## `report_deliveries`
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| id | uuid | pk | | non |
| report_id | text | not null | | non |
| version | integer | not null | | non |
| recipient_email | text | not null | | **oui** |
| recipient_name | text | not null, default '' | | **oui** |
| signing_token | text | unique, not null | URL signée | non |
| expires_at | timestamptz | not null | TTL | non |
| sent_at | timestamptz | | | non |
| sent_by | uuid | fk auth.users.id, set null | | oui |
| language | text | not null, default 'fr' | | non |
| email_status | text | not null, default 'pending' | | non |
| created_at / updated_at | timestamptz | not null, default now() | | non |

## `report_downloads`
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| id | uuid | pk | | non |
| delivery_id | uuid | fk report_deliveries.id, cascade, not null | | non |
| downloaded_at | timestamptz | not null, default now() | | non |
| ip_address | inet | | | **oui** |
| user_agent | text | | | **oui** |
| country_code | text | | | **oui** |
| referer | text | | | non |

## Conventions transverses

- **RLS activée sur les 12 tables** (règle absolue) — état vérifié dans les migrations.
- Toute table porte `created_at` ; soft-delete : **non** (suppression cascade par org) —
  réexaminer en ADR si un client exige la rétention.
- Colonnes PII (marquées **oui** en gras) → reprises dans `docs/07-legal-compliance.md`.
- Invariantes en CONTRAINTE SQL d'abord (not null, unique, check, fk) — une validation
  purement applicative d'une invariante exprimable en SQL se justifie en ADR (Ponytail).
- ⚠️ **Pièges connus** (à corriger en V2, voir backlog) :
  - `public.is_super_admin()` référence une table `super_admin_emails` qui n'existe dans
    aucune migration → retourne toujours false ; la vraie whitelist est la variable
    d'environnement backend nommée BASSIRA_SUPER_ADMIN_EMAILS (voir 05-integrations.md).
    Ne JAMAIS s'appuyer sur cette fonction.
  - Policies `FOR ALL TO authenticated` sur report_deliveries/report_downloads : un
    org-admin peut théoriquement forger des lignes de tracking via un client Supabase.
  - Le payload riche (devis, snapshots rapports, artefacts simulation) est
    filesystem-only sur volume éphémère — source de vérité à migrer (ADR-005).
