# Allocation fonds souverain — 400M USD (10 semaines)

Scénario Bassira pour comités d'investissement, CFO et fonds souverains MENA. Simule 10 semaines de délibération d'un fonds institutionnel panafricain (FAID, CFC Casablanca) devant allouer 400M USD entre 4 options mutuellement exclusives.

## Deux fichiers livrés

1. **`01_attachment.md`** — brief envoyé par la CFO du Fonds Africain d'Investissement Durable (FAID), perspective client institutionnel panafricain.
2. **`02_engine.md`** — sim_requirement + 6 agent system_prompts (analyste Goldman Sachs, BNP Paribas CIB BERD, IFC AgriTech, CDG Investissements, IRESEN, Reuters Africa) + 3 director events (due diligence surprises, choc phosphates OCP, offre concurrente asiatique) + verdict shape IRR.

## Verdict produit

```json
{
  "verdict_final": "option_gagnante / facteurs_critiques / risques_bloquants",
  "ranking_options": { "1er": "Option B", "2eme": "Option D", "3eme": "Option C", "4eme": "Option A" },
  "verdict_option_a_irr": { "irr_post_choc": "12.5%", "hurdle_rate": "14.0%", "verdict": "sous hurdle rate" }
}
```

## Cohérence engine

- 30 agents × 10 rounds = ~300 actions baseline
- 1 round = 1 semaine ⇒ `minutes_per_round = 10080`
- Director events à S+2 (due diligence), S+5 (choc phosphates), S+8 (offre concurrente)
