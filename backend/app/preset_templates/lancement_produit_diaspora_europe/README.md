# Sahara Gold — lancement GD Europe diaspora MENA (12 mois)

Scénario Bassira pour directeurs marketing, directeurs export et fonds MENA. Simule 12 mois du lancement de « Sahara Gold » (Cosumar) en Grande Distribution européenne — France, Belgique, Pays-Bas.

## Deux fichiers livrés

1. **`01_attachment.md`** — brief envoyé par le directeur Export de Cosumar SA (Tarik Alaoui), perspective client industriel agro-alimentaire à l'international.
2. **`02_engine.md`** — sim_requirement + 6 agent system_prompts (chef de rayon Carrefour, influenceur Khalid Bouaza, imam CCIF, nutritionniste France 5, cliente diaspora, journaliste LSA) + 3 director events (référencement Carrefour spécialités du monde, vidéo virale 2,4M vues, contre-attaque Beghin Say -30%) + verdict shape pénétration M+12.

## Verdict produit

```json
{
  "verdict_final": "pénétration_atteinte / segments_gagnants / barrières_critiques",
  "penetration_m12": { "taux_gd_france": "5.8%", "objectif_initial": "8.0%" },
  "barrieres_critiques": ["placement rayon spécialités du monde", "écart prix +15%", "contre-attaque Beghin Say"]
}
```

## Cohérence engine

- 40 agents × 12 rounds = ~480 actions baseline
- 1 round = 1 mois ⇒ `minutes_per_round = 43200`
- Director events à M+2 (référencement Carrefour), M+5 (vidéo virale), M+9 (contre-attaque Beghin Say)

## Note devise

Ce template utilise EUR comme devise principale (contexte marché européen) — exception explicitement documentée dans la spec US-022 pour le template export Europe.
