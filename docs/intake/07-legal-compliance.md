# 07 — Conformité légale du module Intake

> Périmètre : RGPD (prospects UE), loi marocaine 09-08, EU AI Act. Ce document identifie
> les obligations — il ne constitue pas un avis juridique (les verdicts juridiques
> appartiennent à Amine, cf. mémoire projet `feedback_legal_scope`).

## 1. EU AI Act — article 50 (transparence) — ÉCHÉANCE PROCHE

- **Applicable le 2 août 2026** (dans ~3 semaines). L'agent conversationnel est un système
  d'IA interagissant avec des personnes : **obligation d'informer clairement** que
  l'interlocuteur est une IA.
- Réponse produit : disclosure au premier message de l'agent + bandeau permanent (doc 06).
  Non désactivable, dans les 3 locales.
- Cohérence avec l'existant : le marquage de contenu synthétique des PDF (US-202,
  `/SyntheticContent=true`) répond au même article — le module s'aligne.

## 2. RGPD / loi 09-08 — traitement des données du parcours

| Donnée | Base légale | Minimisation | Rétention |
|---|---|---|---|
| Identité (nom, email, société) | Mesures précontractuelles (art. 6.1.b RGPD) | Déjà collectée aujourd'hui — inchangé | Durée de la relation commerciale |
| Brief (décision, options, enjeux, geo) | Mesures précontractuelles | Fourchettes plutôt que montants exacts (A6) ; pas de données de personnes tierces sollicitées | Conservé avec le devis |
| **Transcript de l'agent** | Mesures précontractuelles + intérêt légitime (qualification) | L'agent N'INVITE JAMAIS à écrire des données sensibles ; le tri confidentiel (flag sans contenu) est une mesure de **privacy by design** opposable | **Purge J+90** après complétion (pg_cron) — documentée dans la politique de confidentialité |
| Sessions abandonnées | — | — | **Purge J+30** intégrale |
| `aar_known_outcome` (porte 2) | Mesures précontractuelles | Scellé (chiffrement applicatif ou hachage — ADR-IQ-05) : ni les admins ni l'agent n'y accèdent avant restitution | Purge avec la session si non convertie |

- **Consentement** : la case `consent_rgpd` existante est conservée ; le texte doit être
  étendu pour couvrir l'étape B (transcript) et la rétention ci-dessus.
- **DSR (droits d'accès/suppression)** : `intake_sessions` doit être incluse dans toute
  procédure d'export/suppression par email du prospect — prévoir la requête SQL type dans
  la doc admin.
- **Flux transfrontière** : l'appel LLM transite par la gateway LiteLLM — vérifier AVANT
  mise en prod quel modèle/hébergeur est configuré et le refléter dans la politique de
  confidentialité. Si le modèle par défaut est hébergé hors Maroc/UE, le transcript part
  chez ce fournisseur : à trancher par Amine (BYOK/modèle souverain possible via la
  gateway).

## 3. Ce que l'agent n'a PAS le droit de faire (garde-fous légaux, encodés dans le prompt doc 10)

- Solliciter des données sensibles (santé, opinions politiques, religion…) ou des données
  de tiers identifiés.
- Donner un prix, un délai contractuel, ou toute promesse engageante (seul le devis signé
  engage).
- Faire un claim prédictif ou de calibration (ADR-002 — le risque ici est aussi
  COMMERCIAL : une promesse écrite dans un transcript est opposable).
- Fournir un conseil juridique, financier ou réglementaire.

## 4. Politique de confidentialité — mises à jour requises (même release)

1. Section « Assistant de qualification (IA) » : finalité, rétention J+90, droit d'opposition
   (bouton « Passer »).
2. Mention du sous-traitant LLM effectif (selon configuration gateway).
3. Mention des purges automatiques J+30/J+90.

## 5. Risque spécifique documenté

Le transcript peut contenir des informations stratégiques du prospect AVANT tout NDA.
Mesures : tri confidentiel proactif (l'agent propose de différer), accès restreint
super-admin, purge J+90, et mention explicite dans le premier message de l'agent
(« si un sujet est confidentiel, dites-le »). Le NDA reste le véhicule de la branche
entretien — l'agent ne s'y substitue pas.
