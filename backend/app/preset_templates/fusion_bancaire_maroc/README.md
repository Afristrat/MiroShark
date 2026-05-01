# OPA CIH Bank — Barid Al-Maghrib Finance (20 semaines)

Scénario Bassira pour banques, fonds PE et régulateurs financiers. Simule 20 semaines du processus d'approbation BAM d'une OPA amicale CIH Bank sur Barid Al-Maghrib Finance (4,2M clients).

## Deux fichiers livrés

1. **`01_attachment.md`** — brief envoyé par le directeur M&A CDG Investissements (Noureddine Bensouda), perspective client deal team.
2. **`02_engine.md`** — sim_requirement + 6 agent system_prompts (CDG Investissements, syndicats FDT BAMF, Fitch Ratings, BAM supervision, Crédit du Maroc concurrent, LesEco.ma) + 3 director events (annonce OPA, contre-offre Crédit du Maroc, note Fitch) + verdict shape probabiliste BAM.

## Verdict produit

```json
{
  "verdict_bam": "approuvée_sans_condition / approuvée_avec_cessions / bloquée",
  "probabilites": { "approuvée_avec_engagements_comportementaux": 0.52, "..." },
  "conditions_probables": ["accord social", "renforcement fonds propres CIH", "maintien réseau rural"]
}
```

## Cohérence engine

- 35 agents × 10 rounds = ~350 actions baseline
- 1 round = 2 semaines ⇒ `minutes_per_round = 20160`
- Director events à S+1 (annonce OPA), S+7-8 (contre-offre), S+15-16 (note Fitch)
