# Adcheck pre-launch — 3 concepts pub Ramadan (3 jours)

Scénario canonique Bassira pour lead marketing / agence créa. Évalue 3 concepts publicitaires Ramadan sur une audience marocaine 25-45 ans synthétique avec extension Maghreb-Afrique de l'Ouest, sur 3 jours. Verdict : ranking A/B/C + top arguments / top objections / backfire risk.

## Deux fichiers livrés

1. **`01_attachment.md`** — brief que le lead marketing envoie à Bassira (perspective utilisateur, avec les 3 concepts en pièces jointes mentionnées dans le mail). À convertir en PDF pour les démos prospects.
2. **`02_engine.md`** — sim_requirement + 6 agent system_prompts + 5 director events + verdict shape.

## Verdict produit

```
{
  "ranking": [{"concept": "A", "score": 72.5}, {"concept": "B", "score": 68.0}, {"concept": "C", "score": 41.0}],
  "per_concept_top_arguments": {...},
  "per_concept_top_objections": {...},
  "backfire_risk": {"concept": "C", "cause_racine": "..."}
}
```

## Cohérence engine

- 60 agents × 18 rounds (J1-J3 × 6 par jour) = ~1080 actions baseline
- 1 round = 4 heures ⇒ `minutes_per_round = 240`
- Director events à J1-H+12, J1-H+20, J2-H+8, J2-H+16, J3-H+4
