# Hub MENA startup deeptech — Casablanca vs Dubaï vs Nairobi (8 semaines)

Scénario Bassira pour founders, DG et conseils d'administration. Simule 8 semaines de décision de hub régional MENA pour BioSynth AI (deeptech diagnostic médical IA, Série A 18M USD) entre Casablanca, Dubaï et Nairobi.

## Deux fichiers livrés

1. **`01_attachment.md`** — brief envoyé par la CEO de BioSynth AI (Yasmine Kaddouri), perspective fondatrice en décision de localisation stratégique.
2. **`02_engine.md`** — sim_requirement + 6 agent system_prompts (OCP Ventures, Wamda Capital Dubaï, Algebra Ventures Nairobi, AMDL, Kenyatta Hospital, talent ML Casablanca) + 3 director events (package D33 Dubaï, accord AMDL, Series B concurrent Nairobi) + verdict shape multicritère.

## Verdict produit

```json
{
  "verdict_final": "ville_choisie / facteurs_déterminants / risques_migration",
  "ranking_villes": { "1er": "Casablanca", "2eme": "Dubaï", "3eme": "Nairobi" },
  "facteurs_discriminants": { "factor_1": "Accès réglementaire hôpitaux publics", "..." }
}
```

## Cohérence engine

- 35 agents × 8 rounds = ~280 actions baseline
- 1 round = 1 semaine ⇒ `minutes_per_round = 10080`
- Director events à S+2 (package D33), S+4 (accord AMDL), S+7 (Series B Diagno AI)
