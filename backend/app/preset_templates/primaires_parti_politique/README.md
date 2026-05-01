# Primaires parti politique — désignation tête de liste AND (24 jours)

Scénario Bassira pour partis politiques, think-tanks politiques et cabinets conseil. Simule 24 jours de campagne interne de l'Alliance Nationale Démocratique (AND, parti marocain fictif) avec 3 candidats et 50 agents.

## Deux fichiers livrés

1. **`01_attachment.md`** — brief envoyé par le directeur de campagne AND (Rachid Habboubi), perspective client campagne politique interne.
2. **`02_engine.md`** — sim_requirement + 6 agent system_prompts (militante régionale Fès, journaliste TelQuel, politologue, jeune adhérente, diplomate France, présidente jeunesse Marrakech) + 3 director events (débat interne, sondage surprise, révélation accord transactionnel) + verdict shape probabiliste.

## Verdict produit

```json
{
  "verdict_final": "candidat_désigné / coalition_soutien / fractures_internes",
  "probabilites_designation": { "Chraibi_premier_tour": 0.42, "Benjelloun_premier_tour": 0.28, "..." },
  "fractures_internes": { "fracture_generationnelle": "...", "risque_dissidence_legislatives": "15-20%" }
}
```

## Cohérence engine

- 50 agents × 8 rounds = ~400 actions baseline
- 1 round = 3 jours ⇒ `minutes_per_round = 4320`
- Director events à J+4 (débat), J+13 (sondage), J+19 (accord transactionnel)
