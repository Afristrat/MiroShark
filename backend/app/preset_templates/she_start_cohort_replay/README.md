# She Start — Cohort Replay (template MiroShark)

Template dédié à la **validation scientifique** de la cohorte She Start, l'incubateur féminin opéré par l'AFEM (Association des Femmes Chefs d'Entreprises du Maroc). L'objectif est de mesurer la fidélité prédictive de MiroShark face à la cohorte réelle, sa stabilité statistique, et ses angles morts sur la détection de leadership.

---

## Contenu du template

| Fichier | Rôle |
|---|---|
| `../she_start_cohort_replay.json` | Définition principale du template (chargée par `GET /api/templates/she_start_cohort_replay`). Expose les 3 variants A/B/C, les agents, les rounds, le marché de prédiction par défaut et les slots Director Mode. |
| `seed_template.md` | Document seed prêt à remplir (35 candidates, 5 mentors, 3 jurés, 2 banquiers, 5 observateurs, chronologie S1→S10, slots événements S3/S5/S7, critère PMF formalisé). |
| `personas.md` | 8 archétypes mentors (voice, posture, expertise, biais) parmi lesquels Amine + Asma sélectionnent les 5 mentors injectés. |
| `README.md` | Ce fichier — guide d'utilisation. |

---

## Les 3 variants

| Variant | Code | Runs | Cohorte | Objectif scientifique |
|---|---|---|---|---|
| A | `ground_truth_replay` | 1 | 35 candidates | Comparer MiroShark à la vérité-terrain (Ground Truth). |
| B | `cohort_twin` | 5 (parallèles) | 35 candidates | Mesurer la stabilité statistique (variance inter-runs). |
| C | `blind_spot_hunt` | 1 | 30 candidates (5 leaders réels masqués) | Détecter les angles morts du modèle sur le leadership. |

Tous les variants partagent :
- 10 rounds (1 round = 1 semaine)
- 5 mentors + 3 jurés + 2 banquiers + 5 observateurs
- Marché de prédiction : « X % de la cohorte aura validé son PMF en S10 (cible 30 %) »
- Slots Director Mode aux semaines S3, S5, S7

---

## Comment utiliser le template (workflow Amine + Asma)

### Étape 1 — Préparation des données (offline)

1. Ouvrir `seed_template.md` et remplir **toutes** les sections marquées `[à remplir]` :
   - 35 fiches candidates (prénom_nom, secteur, business_model, stade_démarrage, background, motivation, contraintes, force, faiblesse).
   - 5 mentors (en s'appuyant sur les 8 archétypes de `personas.md`).
   - 3 jurés (affiliation + critères + biais).
   - 2 banquiers (institution Maroc + posture risque PME).
   - 5 observateurs presse marocaine.
   - Slots événements S3 / S5 / S7 (laissés vides ou remplis).
2. Vérifier la conformité **CNDP loi 09-08** sur les données nominatives (anonymisation si pas de consentement).
3. Vérifier que les dispositifs publics cités (Tamwilcom, Intelaka, Damane) sont **toujours en vigueur** au moment du lancement (sources : portails CCG-Tamwilcom, ANPME).
4. Faire valider le seed par Amine **et** Asma avant lancement.

### Étape 2 — Création de la simulation (UI MiroShark)

1. Aller sur l'écran de création de simulation.
2. Choisir le template **« She Start — Cohort Replay »**.
3. Choisir le variant (A, B ou C).
4. Coller le contenu rempli de `seed_template.md` dans le champ seed_document (ou laisser MiroShark charger automatiquement le fichier rempli si la fonctionnalité d'upload est disponible).
5. Pour le **Variant B (Cohort Twin)** : lancer 5 simulations en parallèle avec graines aléatoires différentes.
6. Pour le **Variant C (Blind Spot Hunt)** : retirer du seed les 5 fiches des candidates identifiées comme leaders réelles.

### Étape 3 — Director Mode (optionnel)

Aux rounds 3, 5 et 7, l'utilisateur peut injecter un événement via le Director Mode (perturbation milieu de programme, choc externe, événement à fort effet de levier). Si aucun événement n'est injecté, le round se déroule de façon nominale.

### Étape 4 — Lecture des résultats

- **Variant A** : courbe de convergence du marché de prédiction sur 10 rounds + cartographie des leaders émergents. Comparer à la cohorte réelle.
- **Variant B** : distribution sur 5 runs du % PMF S10, écart-type inter-runs, classement des leaders robustes (présents dans les 5 runs) vs sensibles à l'aléa.
- **Variant C** : liste des leaders émergents désignés par MiroShark + comparaison avec les 5 leaders réels masqués (taux de découverte indirecte = précision sur le leadership non-évident).

---

## Critère PMF observable (rappel)

Une candidate **valide son PMF** à S10 si elle satisfait ≥ 2 des 3 critères :
1. ≥ 3 clients payants confirmés
2. ≥ 50 utilisateurs actifs (sur 30 jours glissants)
3. ≥ 7/10 de score moyen jury

---

## Endpoints API

- `GET /api/templates/list` → la fiche `she_start_cohort_replay` apparaît dans la liste avec `has_variants: true` et `variants_count: 3`.
- `GET /api/templates/she_start_cohort_replay` → renvoie le template complet incluant le tableau `variants` (A, B, C) avec leurs paramètres détaillés.

---

## Roadmap

- US-017 (présent) : template backend + 3 variants exposés via API.
- US-018 (présent) : seed_template.md, personas.md, README.md.
- US-019 (à venir) : intégration UI dans le sélecteur de templates (frontend).
