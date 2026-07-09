# 04 — Backlog du module Intake (US-IQ-*)

> À transposer dans `.ralph/prd.json` (chantier `V2-B-intake`) APRÈS validation d'Amine.
> Ordre = ordre d'exécution recommandé. Chaque US est autonome et livrable seule.

## US-IQ-01 — Formulaire structuré « 3 temps » (sans agent)

**Description** : remplacer le formulaire /devis actuel par le parcours A1-A8 de la spec
(3 écrans, validation par étape, A1/A2/A7 bloquants). Écriture dans `intake_sessions`
(state `form_submitted`) + `quote_ownership` comme aujourd'hui (rétrocompatible).
**AC** :
- Les 8 questions dans les 3 locales (parité vérifiée), RTL correct en arabe.
- Un devis soumis produit un `brief` validé jsonschema avec A1, A2 (≥2), A7 remplis — un
  payload vide comme `q_f767321b` est rendu IMPOSSIBLE par design.
- Micro-copy « pourquoi cette question » sur chaque temps.
- Migration + delta fusionné dans `docs/02-data-dictionary.md` même commit.
- pytest + build + Playwright parcours verts.
**Effort** : M · **Deps** : aucune.

## US-IQ-02 — Agent conversationnel de qualification (étape B)

**Description** : endpoint backend + UI chat post-formulaire. System prompt du doc 10,
via llm_client/gateway. Budget 7 tours (compteur serveur), disclosure IA au 1ᵉʳ message,
tri confidentiel (flags sans contenu), production des `agent_insights`.
**AC** :
- L'agent ne donne jamais de prix, ne promet jamais de prédiction, ne pitche pas — vérifié
  par la grille d'évaluation du doc 10 sur ≥ 10 transcripts synthétiques.
- Un sujet flaggé confidentiel n'apparaît NI dans le brief NI dans les emails — test.
- 8ᵉ tour refusé par le serveur (403 + clé i18n) même si le front le demande.
- Rate limit IP + timeout 30 s + repli gracieux si gateway down (le parcours continue sans
  l'étape B, state `completed` direct).
- Modèle lu depuis l'env, jamais en dur.
**Effort** : L · **Deps** : US-IQ-01.

## US-IQ-03 — Routage à 3 branches + machine à états

**Description** : règles déterministes de la spec §3.C (AUCUN LLM dans le routage),
écriture de `route`, transitions d'état contraintes en SQL.
**AC** :
- Table de vérité complète testée (chaque combinaison enjeu×gouvernance×échéance → branche
  attendue) — tests unitaires exhaustifs.
- Branche self-service : redirection vers le package adapté avec `intake_session_id`
  propagé jusqu'au Checkout Stripe (metadata).
- Branche entretien : les sujets confidentiels flaggés listés dans la vue admin.
**Effort** : S · **Deps** : US-IQ-01 (US-IQ-02 optionnelle — le routage fonctionne sur le
seul formulaire).

## US-IQ-04 — Emails contextualisés

**Description** : refonte de `quote_received.html` (+ variantes par branche) : décision,
échéance, prochaine étape explicite. Branche entretien : proposition de 2-3 créneaux
(texte, pas d'outil calendrier — ADR-IQ-03).
**AC** :
- Email reflète A1/A3/branche ; AUCUN contenu flaggé confidentiel ; tout contenu prospect
  échappé HTML (cf. 09-risques) ; liens bassira.ma ; fr/en/ar selon locale de session.
- Envoi réel vérifié en prod (pattern de preuve US-204).
**Effort** : S · **Deps** : US-IQ-03.

## US-IQ-05 — Porte 2 « Testez-nous sur du connu » (AAR)

**Description** : entrée alternative sur /devis et /offres, champ « issue réelle » scellé
(cf. ADR-IQ-05), `entry_door='aar'`.
**AC** : parcours complet porte 2 fonctionnel ; l'issue réelle n'apparaît dans aucune vue
admin standard avant restitution ; copy 3 locales.
**Effort** : S · **Deps** : US-IQ-01.

## US-IQ-06 — Vue admin enrichie

**Description** : `/admin/quotes` affiche le brief structuré (sections lisibles, pas un
dump JSON), les sujets confidentiels, la branche de routage, le transcript (accès
super-admin, mention de la purge J+90).
**AC** : détail d'un devis montre le brief formaté ; filtre par branche ; aucune
régression sur les devis legacy (payload ancien format).
**Effort** : S · **Deps** : US-IQ-03.

## US-IQ-07 — Pré-seed de simulation depuis le brief

**Description** : depuis la console (super-admin ou self-service), « créer une simulation
depuis ce devis » : décision → scénario, options → forks, geo → population cible,
data_assets → rappel d'ancrage.
**AC** : une simulation créée depuis un brief a son scénario pré-rempli et éditable ;
traçabilité `intake_session_id` → `simulation_ownership`.
**Effort** : M · **Deps** : US-IQ-03.

## Hors périmètre V1 (parking lot, conditions de sortie)

- Outil de calendrier intégré (sortie : > 5 entretiens/semaine planifiés manuellement).
- Reprise de session cross-device (sortie : demande client réelle).
- Agent vocal (sortie : jamais sans décision explicite d'Amine).
- Guide d'entretien oral 20 min outillé (`problem-interview`/`discovery-interview-prep`) —
  chantier de contenu, pas de code.
