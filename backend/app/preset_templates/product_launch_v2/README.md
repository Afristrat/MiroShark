# Product Launch B2C — 1 semaine

Scénario canonique Bassira pour PM / GTM lead / growth. Simule 1 semaine de lancement produit B2C pan-Afrique, focus trajectoire d'adoption + pic de churn early-adopters J5.

## Deux fichiers livrés

1. **`01_attachment.md`** — brief que le PM/GTM lead envoie à Bassira (perspective utilisateur). À convertir en PDF pour les démos prospects.
2. **`02_engine.md`** — sim_requirement + 6 agent system_prompts (early adopter Casa, pragmatique prof Yaoundé, sceptique tech Tunis, créatrice contenu Lagos, support utilisateur Marrakech, marketing concurrent Dakar) + 5 director events + verdict shape.

## Verdict produit

```
{
  "adoption_curve_per_day": [
    {"day": 1, "adoption_cumul_pct": 0.8},
    {"day": 2, "adoption_cumul_pct": 2.4},
    ...
  ],
  "churn_peak_day": "J5",
  "churn_peak_magnitude_pct": 12.5,
  "top_5_influencers_to_mobilize": [...],
  "top_3_signals_to_monitor": [...]
}
```

## Cohérence engine

- 60 agents × 28 rounds (7 jours × 4 sessions/jour) = ~1680 actions baseline
- 1 round = 6 heures ⇒ `minutes_per_round = 360`
- Director events à J1-PM, J2-AM, J3-PM, J5-AM, J6-PM
