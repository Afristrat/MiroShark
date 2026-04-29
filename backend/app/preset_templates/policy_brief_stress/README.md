# Policy Brief Stress Test — Loi fintech mobile (5 jours)

Scénario canonique Bassira pour conseiller cabinet ministériel / think tank / lead gouvernance. Stress-teste un projet de loi fintech mobile P2P contre opposition politique + banques classiques + autorité monétaire BCEAO sur 5 jours ouvrés.

## Deux fichiers livrés

1. **`01_attachment.md`** — brief que le conseiller cabinet envoie à Bassira (perspective utilisateur, projet de loi en pièce jointe). À convertir en PDF pour les démos prospects.
2. **`02_engine.md`** — sim_requirement + 6 agent system_prompts (conseiller cabinet, opposition, économiste banque, PDG fintech, avocate financière, journaliste TelQuel) + 5 director events + verdict shape.

## Verdict produit

```
{
  "survives": "yes" | "no" | "with_major_amendment",
  "top_3_amendments_to_concede": [...],
  "who_flips_against": [...],
  "top_3_arguments_failing_real_world": [...]
}
```

## Cohérence engine

- 50 agents × 10 rounds (5 jours × 2 sessions/jour AM+PM) = ~500 actions baseline
- 1 round = 4 heures ⇒ `minutes_per_round = 240`
- Director events à J1-PM, J2-AM, J3-AM (audition), J3-PM (sondage), J5-AM (compromis)
