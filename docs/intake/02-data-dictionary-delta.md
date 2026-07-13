# 02 — Delta dictionnaire de données (module Intake)

> **DELTA à fusionner dans `docs/02-data-dictionary.md` dans le MÊME commit que toute
> migration** (règle CLAUDE.md du repo). Les noms ci-dessous sont proposés — vérifier les
> collisions contre le dictionnaire canonique avant migration.

## Nouvelle table : `intake_sessions`

Une ligne par parcours de qualification démarré (même abandonné — mesure du funnel).

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| `id` | uuid | PK, default gen_random_uuid() | |
| `quote_id` | text | NULL, FK → quote_ownership(quote_id) | Posée à la soumission du formulaire A ; NULL si abandon avant |
| `state` | text | NOT NULL, CHECK IN ('started','form_submitted','agent_active','completed','abandoned') | Machine à états du parcours |
| `brief` | jsonb | NULL | Le brief structuré (schéma ci-dessous), validé serveur avant écriture |
| `transcript` | jsonb | NULL | Échanges de l'étape B : `[{role, content, ts}]` — **pièce DURABLE du dossier de devis (ADR-IQ-07), jamais purgée tant que le dossier existe** ; donnée personnelle, cf. rétention |
| `calcom_booking_uid` | text | NULL | UID de la réservation Cal.com (branche entretien), posé au booking confirmé |
| `confidential_flags` | jsonb | NOT NULL default '[]' | Sujets flaggés « à aborder de vive voix » : `[{topic_label, flagged_at}]` — **jamais de contenu, uniquement un libellé de sujet** |
| `route` | text | NULL, CHECK IN ('self_service','quote_48h','meeting') | Branche de sortie (étape C) |
| `entry_door` | text | NOT NULL default 'standard', CHECK IN ('standard','aar') | Porte 1 ou porte 2 (« Testez-nous sur du connu ») |
| `locale` | text | NOT NULL default 'fr' | fr / en / ar |
| `agent_turns` | int | NOT NULL default 0, CHECK ≤ 10 | Compteur de tours de l'agent (budget, ADR-IQ-11) |
| `created_at` | timestamptz | NOT NULL default now() | |
| `completed_at` | timestamptz | NULL | |

**RLS** : parcours public (pas d'auth) → aucune policy `anon` en lecture/écriture directe ;
tout passe par le backend en service-role. Lecture réservée super-admin (pattern
`/api/admin/*` existant). Invariante SQL, pas code applicatif (règle repo) : les CHECK
ci-dessus + trigger interdisant la transition `completed → started`.

## Schéma JSON du champ `brief` (validé serveur — jsonschema)

```json
{
  "decision": "string, obligatoire (A1)",
  "options": ["string", "2 à 4 éléments (A2)"],
  "deadline": {"date": "ISO ou null", "overdue": "bool (A3)"},
  "governance": "solo|comite_direction|conseil_administration|tutelle|investisseurs (A3)",
  "past_method": ["etude|conseil|sondage_interne|instinct|rien (A4)"],
  "past_gap": "string ou null (A5)",
  "stakes": {"budget_bracket": "lt_1m|1_10m|10_100m|gt_100m", "jobs": "int|null", "exposure": "interne|sectorielle|nationale|internationale (A6)"},
  "geo": [{"country": "ISO-3166", "segment": "string (A7)"}],
  "data_assets": ["etudes|donnees_clients|verbatims|rien (A8)"],
  "aar_known_outcome": "string|null — porte 2 uniquement, scellé (cf. 07-legal)",
  "agent_insights": ["string — synthèses factuelles produites par l'agent, étape B"],
  "brief_version": "1"
}
```

## Extension `quote_ownership.payload`

Le payload actuel (US-203) reste la structure d'enveloppe ; le brief y est référencé par
`intake_session_id` (uuid) — PAS de duplication du brief dans le payload (une seule source
de vérité : `intake_sessions.brief`). Champs actuels conservés tels quels
(rétrocompatibilité admin).

## Rétention (cf. 07-legal-compliance — révisée ADR-IQ-07, directive Amine 2026-07-09)

- `transcript` : **CONSERVÉ tant que le dossier de devis / la relation commerciale
  existe** — il fait partie intégrante de la préqualification et alimente le devis.
  AUCUNE purge automatique sur les sessions liées à un `quote_id`. Inclus dans tout
  export/suppression DSR.
- `aar_known_outcome` : chiffré applicativement OU stocké haché + révélé seulement à la
  restitution (à trancher en revue de code — les deux options documentées en ADR-IQ-05).
- Sessions `abandoned` SANS `quote_id` : purge complète à J+30 (pg_cron) — seules ces
  sessions orphelines sont purgées.

## Ce qui ne change PAS

- `quote_ownership` : aucune colonne nouvelle (le lien se fait par le payload).
- Aucune donnée de simulation sur filesystem (leçon US-203) : tout en Supabase.
