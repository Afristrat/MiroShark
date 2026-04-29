# PMF startup tech B2B — 10 semaines

Scénario canonique Bassira pour founder pré-Série A qui veut valider le PMF de son SaaS B2B avec une cohorte synthétique de 50 prospects-cible pan-Afrique avant de lever.

## Deux fichiers livrés

1. **`01_attachment.md`** — le brief customer-facing : ce que le founder prospect Bassira nous envoie en pièce jointe avec sa demande. Format mail-style, perspective utilisateur. À convertir en PDF pour les démos prospects (`pandoc 01_attachment.md -o 01_attachment.pdf`).

2. **`02_engine.md`** — le côté moteur Bassira : `simulation_requirement` LLM-readable, 6 agent `system_prompts` (1 par persona archétype), 5 director events injection text complet, verdict shape, time_config.

## Verdict produit

```
{
  "verdict": "viable" | "borderline" | "nope",
  "confidence": 0.0-1.0,
  "top_3_segments": ["...", "...", "..."],
  "top_3_frictions": ["...", "...", "..."]
}
```

## Cohérence engine

- 50 agents × 10 rounds = 500 actions baseline (~50/round)
- 1 round = 1 semaine ⇒ `minutes_per_round = 10080`
- Director events à S2, S4, S5, S7, S9 (cf JSON template)
