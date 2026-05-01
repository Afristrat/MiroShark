# PLF Maroc — Stress test parlementaire 30 jours

Scénario Bassira pour ministères des finances, think-tanks économiques et parlementaires. Simule le parcours complet d'un Projet de Loi de Finances marocain comportant 3 mesures controversées sur 30 jours (10 rounds × 3 jours).

## Deux fichiers livrés

1. **`01_attachment.md`** — brief envoyé par le directeur des études économiques du Policy Center for the New South (PCNS), perspective client chercheur-think tank.
2. **`02_engine.md`** — sim_requirement + 6 agent system_prompts (présidente commission finances, chef groupe opposition PI, secrétaire général UMT, président GPBM, économiste PCNS, journaliste Médias24) + 3 director events (dépôt PLF, note BAM, vote commission) + verdict shape probabiliste.

## Verdict produit

```json
{
  "verdict_final": "adopté_intact | adopté_avec_amendements_majeurs | bloqué_commission",
  "probabilites": { "adopté_intact": 0.22, "adopté_avec_amendements_mesure_3": 0.51, "..." },
  "coalitions_determinantes": [...],
  "scenario_risque_maximal": { "declencheur": "...", "probabilite": 0.09 }
}
```

## Cohérence engine

- 50 agents × 10 rounds = ~500 actions baseline
- 1 round = 3 jours ⇒ `minutes_per_round = 4320`
- Director events à J+1 (round 1), J+13 (round 5), J+22 (round 8)

## Cas d'usage rétroactif (US-022)

Ce template peut être lancé sur le PLF 2024 ou PLF 2025 avec outcomes vérifiables (votes commission + plénière publiés au Bulletin Officiel) pour valider la précision prédictive Bassira.
