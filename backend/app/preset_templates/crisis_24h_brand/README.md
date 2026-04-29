# Crisis Drill 24h — Vidéo CEO

Scénario canonique Bassira pour DirCom / agence communication / cellule de crise. Simule 24 heures de dérive d'une fuite vidéo gênante du CEO sur Twitter / Reddit / médias / WhatsApp.

## Deux fichiers livrés

1. **`01_attachment.md`** — brief que le DirCom envoie à Bassira (perspective utilisateur). À convertir en PDF pour les démos prospects.
2. **`02_engine.md`** — sim_requirement + 6 agent system_prompts (journaliste éco, militant droits humains, influenceuse Dakar, employé loyaliste, mère de famille classe moyenne, blogueur Lagos) + 5 director events injection text + verdict shape.

## Verdict produit

```
{
  "worst_case_trajectory": [...],
  "peak_visibility_hour": "H+X",
  "vocal_minorities_radicalized": [...],
  "top_3_messages_to_emit": { "H+1": "...", "H+4": "...", "H+12": "..." }
}
```

## Cohérence engine

- 60 agents × 24 rounds = ~1440 actions baseline
- 1 round = 1 heure ⇒ `minutes_per_round = 60`
- Director events à H+1, H+4, H+8, H+12, H+18
