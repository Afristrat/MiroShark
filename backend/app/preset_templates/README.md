# Preset Templates — Scénarios Bassira

Templates de simulations pré-définies exposés par `GET /api/templates/list` et utilisés par le frontend `TemplateGallery.vue` pour permettre à l'utilisateur de lancer une simulation en un clic.

## 5 scénarios canoniques (US-042)

Chaque scénario suit le **pattern à 2 fichiers** :

1. **`01_attachment.md`** — brief customer-facing, perspective utilisateur. Ce que le prospect Bassira nous enverrait en pièce jointe avec sa demande. Format mail-style. Convertible en PDF pour les démos via le script `scripts/build_attachment_pdfs.py` (dépendance : `pip install reportlab`).
2. **`02_engine.md`** — config technique pour le moteur Bassira : `simulation_requirement` LLM-readable >1500 caractères, 6 agent `system_prompts` complets ancrés sur scenario + persona, 5 `director_event_slots` avec injection text intégral, `expected_outcome` verdict structuré.

Plus un fichier JSON racine `<id>.json` pour `/api/templates/list` (metadata + pointeurs vers les 2 fichiers ci-dessus + recommended_settings + variants éventuels).

| Template | Verdict produit | Time config |
|---|---|---|
| **`pmf_startup_tech`** | `viable / borderline / nope` + confidence + top 3 segments + top 3 frictions | 10 semaines × 1 round/semaine |
| **`crisis_24h_brand`** | worst_case_trajectory + peak_visibility_hour + vocal minorities radicalisées + 3 messages prêts à émettre H+1/H+4/H+12 | 24 heures × 1 round/heure |
| **`adcheck_pre_launch`** | ranking A/B/C avec scores + per-concept top arguments+objections + backfire risk | 3 jours × 4h/round |
| **`policy_brief_stress`** | survives yes/no/with_amendment + top 3 amendements concession + qui flippe + arguments fragiles | 5 jours ouvrés × 4h/round |
| **`product_launch_v2`** | adoption_curve par jour + churn_peak_day + top 5 influencers à mobiliser + top 3 signaux à monitor | 7 jours × 6h/round |

## Anciens templates (à classer, hors-scope US-042)

Les templates suivants existent depuis des phases antérieures et restent fonctionnels pour /api/templates/list mais ne suivent pas encore le pattern à 2 fichiers :

- `campus_controversy.json`
- `corporate_crisis.json`
- `crypto_launch.json`
- `historical_whatif.json`
- `political_debate.json`
- `product_announcement.json`
- `she_start_cohort_replay.json` (+ sous-dossier complet) — utilise un pattern à 3 fichiers (seed_template.md, personas.md, README.md), à harmoniser ultérieurement avec le pattern à 2 fichiers.

## Comment ajouter un nouveau scénario

1. Créer le sous-dossier `backend/app/preset_templates/<id>/`.
2. Écrire `<id>/01_attachment.md` (perspective customer, 600-800 mots).
3. Écrire `<id>/02_engine.md` (sim_requirement + 6 agent system_prompts + 5 director events + verdict shape).
4. Écrire `<id>/README.md` (overview + lien entre les 2 fichiers).
5. Écrire `backend/app/preset_templates/<id>.json` avec metadata + pointeurs.
6. Tests : `cd backend && uv run pytest tests/test_unit_templates_schema.py` doit passer.
7. (Optionnel) Générer le PDF : `python scripts/build_attachment_pdfs.py <id>`.

## Cohérence avec les autres US

- **US-037** `SimulationConfigGenerator` parse `simulation_requirement` du JSON pour adapter `time_config`.
- **US-038** `WonderwallProfileGenerator` injecte les agent `system_prompts` du `02_engine.md` au moment de la création des agents.
- **US-039** Frontend Step1 lit `recommended_settings` + `seed_personas` pour pré-remplir le formulaire.
- **US-041** `ReportAgent` injecte `simulation_requirement` + `expected_outcome` du `02_engine.md` dans son prompt système pour produire un rapport narratif aligné.
