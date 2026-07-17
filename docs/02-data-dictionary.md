# Data Dictionary — Bassira V2

> Contrat de nommage. Toute table/colonne se vérifie ICI avant d'être nommée ; toute
> création met ce fichier à jour DANS LE MÊME COMMIT. SQL en snake_case ; le code
> applicatif suit les conventions de son langage.
> État extrait des migrations réelles `supabase/migrations/` le 2026-07-07 (10 fichiers,
> 12 tables, **RLS activée sur les 12** — vérifié). + `intake_sessions` (20260709_001,
> US-IQ-01) → 13 tables, RLS activée sur les 13.

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
| intake_sessions | 20260709_001 | **transcript, brief** | Parcours de qualification /devis (US-IQ-01, module Intake) |

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
| enabled_platforms | text[] | not null, default '{}' | arènes activées à la création (US-222, migration 20260716_002) — snapshot SQL requêtable dérivé de `SimulationState.enable_*`, source de vérité du nom canonique = `app/services/arena_registry.py` | non |

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

## `intake_sessions`
US-IQ-01 (migration 20260709_001) — parcours de qualification /devis « 3 temps »
(docs/intake/01-intake-spec.md), remplace le contexte de décision jamais capturé par
l'ancien formulaire de contact. Une row par parcours démarré, même abandonné (funnel).
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| id | uuid | pk, default gen_random_uuid() | | non |
| quote_id | text | fk quote_ownership.quote_id, set null | posé à form_submitted ; null si abandon avant | non |
| state | text | not null, check in (started, form_submitted, agent_active, completed, abandoned) | machine à états, trigger anti-transition-arrière | non |
| brief | jsonb | | brief structuré validé jsonschema — schéma docs/intake/02-data-dictionary-delta.md | **oui** (decision, geo, stakes) |
| transcript | jsonb | | échanges étape B agent : [{role,content,ts}] — pièce durable, jamais purgée (ADR-IQ-07) | **oui** |
| calcom_booking_uid | text | | UID réservation Cal.com (branche entretien) | non |
| confidential_flags | jsonb | not null, default '[]' | sujets flaggés, jamais de contenu (ADR-IQ-04) | non |
| route | text | check in (self_service, quote_48h, meeting) | branche de sortie (étape C) | non |
| entry_door | text | not null, default 'standard', check in (standard, aar) | porte 1 ou porte 2 AAR (US-IQ-05) | non |
| locale | text | not null, default 'fr', check in (fr, en, ar) | | non |
| agent_turns | int | not null, default 0, check 0-10 | compteur budget agent (US-IQ-02, ADR-IQ-11) | non |
| created_at | timestamptz | not null, default now() | | non |
| completed_at | timestamptz | | | non |

RLS : aucune policy anon — écriture exclusivement backend service_role, lecture
`is_super_admin()` (même piège connu que report_states, cf. Pièges connus ci-dessous —
n'affecte pas le backend qui bypass RLS en service_role). Rétention : `transcript` conservé
tant que le dossier existe (aucune purge sur session liée à un `quote_id`) ; sessions
`abandoned` sans `quote_id` purgées à J+30 (pg_cron, non encore implémenté — US-IQ-01 pose
le schéma, la purge est hors scope V1).

## `intake_agent_escalations`
ADR-IQ-08 (migration 20260710_001) — tours de l'agent Intake flaggés `escalation` par
l'agent lui-même (scénario imprévu, ambigu, tentative d'injection). Jamais exposé au
prospect — revue exclusive Amine via `/admin`.
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| id | uuid | pk, default gen_random_uuid() | | non |
| session_id | uuid | fk intake_sessions.id, cascade | | non |
| category | text | not null, check in (ambiguous_request, out_of_scope, injection_attempt, unclear_input) | déclarée par l'agent | non |
| user_message | text | not null | message du prospect ayant déclenché l'escalade | **oui** |
| agent_message | text | not null | réponse effective de l'agent | non |
| created_at | timestamptz | not null, default now() | | non |
| reviewed_at | timestamptz | | posé quand Amine marque revu | non |
| reviewer_note | text | | note libre d'Amine | non |

RLS : lecture + update `is_super_admin()` uniquement, aucune policy anon.

## `intake_agent_playbook`
ADR-IQ-08 (migration 20260710_001) — corrections de trajectoire ajoutées par Amine,
injectées dans le system prompt de l'agent Intake tant que `active=true`. Jamais de
modification automatique.
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| id | uuid | pk, default gen_random_uuid() | | non |
| situation_pattern | text | not null | description courte de la situation | non |
| corrected_response | text | not null | réponse idéale, injectée comme exemple contrastif | non |
| added_by | text | not null | email de l'admin ayant ajouté l'entrée | non |
| added_at | timestamptz | not null, default now() | | non |
| active | boolean | not null, default true | désactivable sans suppression | non |

RLS : toutes opérations réservées `is_super_admin()`, aucune policy anon.

## `simulation_prompts`
ADR-017 (migration 20260716_001) — registre versionné des prompts du moteur de
simulation. Une ligne = une version IMMUABLE ; éditer crée une nouvelle version,
activer = basculer `is_active`. Résolu par `PromptRegistry.get(key, locale)`
(`backend/app/services/prompt_registry.py`), cache in-process, fallback sur le prompt
codé en dur si table vide/injoignable — le moteur ne casse jamais à cause du registre.
Pilote branché (US-223) : `arena.polymarket.system` (locale `en`, version 1 = seed du
prompt actuellement codé dans `wonderwall/simulations/polymarket/prompts.py`).
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| id | uuid | pk, default gen_random_uuid() | | non |
| key | text | not null | identifiant technique stable (ex. arena.polymarket.system) | non |
| scope | text | not null | regroupement fonctionnel pour la console (ex. arena, oracle) | non |
| locale | text | not null | fr \| en \| ar | non |
| version | integer | not null | unique avec (key, locale) | non |
| content | text | not null | corps du prompt, placeholders `{var}` | non |
| variables | jsonb | not null, default [] | liste informative des placeholders attendus | non |
| is_active | boolean | not null, default false | une seule version active par (key, locale) — index partiel unique | non |
| created_by | text | not null | email admin ou `system-seed-US-223` | non |
| created_at | timestamptz | not null, default now() | | non |

RLS : toutes opérations réservées `is_super_admin()`, aucune policy anon (backend lit/
écrit via service_role, contourne RLS — même pattern que `intake_agent_playbook`).

## `occupation_profiles`
ADR-016 (migration 20260716_003) — cache des fiches métiers ESCO (+ enrichissement 122B
hors-taxonomie, US-230). Clé de cache `(label, lang)` = terme de recherche normalisé
(trim + lowercase), pas nécessairement le prefLabel ESCO canonique retourné par l'API.
Client `backend/app/services/esco_client.py` : cache d'abord, API ESCO publique sinon
(`urllib` stdlib, requête en 2 temps : `/search` puis `/resource/occupation`), échec
réseau → `None` journalisé (jamais d'exception — persona généré sans bloc
`<expertise_metier>`, cf. US-229).
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| id | uuid | pk, default gen_random_uuid() | | non |
| occupation_uri | text | not null | identifiant ESCO canonique | non |
| label | text | not null | terme de recherche normalisé — clé de cache avec lang | non |
| lang | text | not null | fr \| en \| ar \| ... | non |
| definition | text | not null, default '' | description ESCO dans la langue demandée | non |
| essential_skills | jsonb | not null, default [] | libellés des compétences essentielles | non |
| optional_skills | jsonb | not null, default [] | libellés des compétences optionnelles | non |
| source | text | not null, check in (esco, llm_122b) | esco = taxonomie officielle ; llm_122b = enrichissement hors-taxonomie (US-230) | non |
| fetched_at | timestamptz | not null, default now() | | non |

RLS : lecture `authenticated` (données non sensibles, taxonomie ESCO publique) ; écriture
(insert/update/delete) réservée `is_super_admin()`.

## `simulation_artifacts`
ADR-005 (migration 20260716_004) — index requêtable des artefacts de simulation
synchronisés vers le bucket Storage privé `simulation-artifacts` (US-221). La source de
vérité binaire est le bucket ; cette table permet de savoir SANS lister le bucket quels
fichiers existent durablement pour une simulation. Design « hydratation de répertoire » :
un objet Storage par fichier local, sous le préfixe `simulations/<simulation_id>/<chemin
relatif>`. Écrit par `sync_directory_to_storage()`, lu par `ensure_simulation_dir_hydrated()`
et `is_durably_persisted()` (`backend/app/services/artifact_storage.py`) — jamais
d'exception propagée, Supabase indisponible = comportement filesystem pur inchangé.
| Colonne | Type | Contraintes | Description | PII |
|---|---|---|---|---|
| id | uuid | pk, default gen_random_uuid() | | non |
| simulation_id | text | not null | unique avec (simulation_id, relative_path) | non |
| relative_path | text | not null | chemin relatif au dossier de simulation (ex. state.json, twitter/actions.jsonl) | non |
| storage_path | text | not null | chemin complet dans le bucket (simulations/<simulation_id>/<relative_path>) | non |
| size_bytes | bigint | not null, default 0 | | non |
| synced_at | timestamptz | not null, default now() | | non |

RLS : toutes opérations réservées `is_super_admin()`, aucune policy anon (backend lit/écrit
via service_role, contourne RLS — même pattern que `simulation_prompts`). Bucket Storage
`simulation-artifacts` : privé, accès exclusivement service_role.

## Conventions transverses

- **RLS activée sur les 18 tables** (règle absolue) — état vérifié dans les migrations.
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
  - Le payload riche (devis, snapshots rapports) reste filesystem-only sur volume
    éphémère. Les artefacts de simulation ont désormais un chemin de persistance durable
    (`simulation_artifacts` + bucket Storage, ADR-005 → US-221) : lecture rétro-compatible
    câblée sur les principaux chokepoints (`SimulationManager`, `SimulationRunner.start_simulation`,
    `graph_tools.py`, `report_pdf/loader.py`, `observability.py`, `calibration.py`) et écriture
    câblée en fin de préparation/run (`report_pdf` : câblage fait, non testé end-to-end —
    cf. `.ralph/progress.md`). Les scripts subprocess (`scripts/run_*_simulation.py`) ne sont
    PAS encore couverts côté lecture — risque résiduel documenté, pas encore fermé.

## Tables et colonnes PLANIFIÉES — chantier Simulations V2 (spec 2026-07-16, PAS ENCORE MIGRÉES)

> Réservation de noms (contrat de nommage). Chaque objet passera en section définitive de
> ce dictionnaire AU COMMIT de sa migration (même commit — règle CLAUDE.md). Détail :
> `docs/superpowers/specs/2026-07-16-simulations-v2-design.md` §4 et ADR-015/016/017/019.

| Objet planifié | Story | Rôle | RLS prévue |
|---|---|---|---|
| `market_resolutions` | US-226 | Verdicts de l'oracle de clôture (`simulation_id`, `market_id`, `question`, `resolution_spec` jsonb, `verdict` ∈ {YES, NO, INVALID}, `justification`, `confidence`, `oracle_prompt_version`, `resolved_at`) | lecture org propriétaire ; écriture service |
