# 01 — Spécification du module Intake (parcours de qualification /devis)

> Module de Bassira — identifiant technique : `intake`. Statut : **en validation Amine,
> aucun code autorisé avant validation des 10 documents.**
> Origine : constat du 2026-07-09 (payload `q_f767321b` vide de tout contexte de décision)
> + chasse moat-hunter du même jour (`docs/moat-hunts/2026-07-09-adhesion-confiance-bassira.md`).

## 1. Problème

Le formulaire `/devis` actuel est un formulaire de contact : il capture l'identité mais
aucun contexte de décision (`message` = libellé du sélecteur, `role`/`industry`/`geo_focus`
vides). Conséquences : devis non adaptatif, simulation non pré-seedable, entretien
commercial qui repart de zéro, aucune qualification du sérieux du prospect.

## 2. Principe fondateur

**Le parcours n'est pas un formulaire de contact : c'est le Step 0 de la simulation ET le
filtre d'engagement.** Chaque donnée capturée sert trois usages simultanés :
1. **Dimensionner le devis** (adaptatif : enjeux → palier).
2. **Pré-seeder le scénario** de simulation (décision, options, marchés, données d'ancrage).
3. **Qualifier le sérieux** (le temps investi dans les réponses = monnaie d'engagement,
   au sens Mom Test).

Cadre méthodologique : les 3 règles du Mom Test transposées au digital — parler de la vie
du prospect (sa décision), jamais du produit ; du passé spécifique, jamais de
l'hypothétique ; chercher l'engagement, jamais le compliment.

## 3. Architecture du parcours (5 étapes)

### Étape A — Formulaire structuré « 3 temps » (obligatoire, 5-8 questions)

**Temps 1 — La décision (faits présents)**
- A1. « Quelle décision devez-vous prendre ? » — texte court obligatoire (≥ 15 caractères).
- A2. « Quelles options sont réellement sur la table ? » — 2 à 4 champs courts (min 2).
  → seed direct du fork contrefactuel.
- A3. « Quand se tranche-t-elle, et devant qui ? » — échéance (date ou « déjà en retard »)
  + instance : seul / comité de direction / conseil d'administration / tutelle-ministère /
  investisseurs.

**Temps 2 — Le passé (Mom Test pur)**
- A4. « La dernière fois que vous avez pris une décision de ce poids, qu'est-ce qui vous a
  éclairé ? » — choix : étude de marché / cabinet de conseil / sondage interne / instinct /
  rien. Multi-sélection possible.
- A5. « Qu'est-ce qui a manqué à ce moment-là ? » — texte court, optionnel.

**Temps 3 — L'enjeu et la matière (devis adaptatif)**
- A6. « Qu'engage cette décision ? » — fourchettes : budget engagé (< 1 M MAD / 1-10 M /
  10-100 M / > 100 M ou équivalent devise), emplois concernés, exposition publique
  (interne / sectorielle / nationale / internationale).
- A7. « Sur quels marchés / populations ? » — pays (multi) + segment — **obligatoire**
  (remplace le `geo_focus` actuellement vide).
- A8. « Quelles données internes pourriez-vous partager pour ancrer la simulation ? » —
  cases : études existantes / données clients / verbatims / rien pour l'instant.

### Étape B — Agent conversationnel de qualification (optionnel mais proposé par défaut)

Après soumission du formulaire, un agent LLM (via la gateway LiteLLM, ADR-004 — modèle
choisi par Amine, jamais par l'IA) engage 3 à 7 échanges de creusement, en s'appuyant
UNIQUEMENT sur les réponses A1-A8 :
- Il creuse façon Mom Test : « Vous mentionnez [option A2.1] — qu'est-ce qui vous retient
  de la choisir aujourd'hui ? », « Quand [A4] a manqué, que s'est-il passé ensuite ? ».
- Il **trie le confidentiel** : quand un sujet devient sensible (chiffres internes, noms,
  conflits), il propose explicitement « Ce point semble confidentiel — je le note comme
  sujet à aborder de vive voix, sans le détailler ici ». Le sujet est flaggé SANS contenu
  (mécanisme de confidentialité différée, cf. ADR-IQ-04).
- Il s'annonce comme IA dès le premier message (AI Act art. 50, applicable 2026-08-02).
- Il ne donne JAMAIS de prix, ne promet JAMAIS de résultat prédictif (ADR-002), ne pitche
  jamais le produit.
- Budget : 7 tours maximum, puis clôture avec récapitulatif.

Sortie : un **brief structuré** (JSON validé serveur, schéma en doc 02) = le « brief armé ».

### Étape C — Routage à 3 branches (règles déterministes, pas LLM)

| Branche | Condition (sur le brief) | Sortie |
|---|---|---|
| **Self-service** | enjeu faible (A6 budget < 1 M MAD ET exposition ≤ sectorielle) ET échéance > 2 semaines | Redirection vers le package d'entrée adapté (Stripe existant, US-205) avec le brief attaché |
| **Devis 48 h** | enjeu moyen, pas d'instance de gouvernance lourde | Devis pré-rempli généré côté admin sous 48 h ; email d'accusé contextualisé |
| **Entretien 20 min** | instance = conseil/tutelle/investisseurs OU budget ≥ 10 M MAD OU ≥ 1 sujet confidentiel flaggé | Email proposant 2-3 créneaux (pas d'outil calendrier en V1, ADR-IQ-03) ; l'entretien démarre avec le brief armé + la liste des sujets confidentiels à couvrir |

### Étape D — Email de confirmation contextualisé

Remplace le générique actuel : « Votre décision : [A1] — échéance : [A3] — prochaine
étape : [selon branche] ». Jamais de contenu flaggé confidentiel dans l'email. Liens
bassira.ma (ADR-013), templates fr/en/ar (ADR-008).

### Étape E — Porte 2 « Testez-nous sur du connu » (AAR)

Entrée alternative visible sur /devis et /offres : « Vous hésitez ? Testez Bassira sur une
décision déjà tranchée dont vous connaissez l'issue. » Même parcours, champ A3 remplacé
par « Quelle a été l'issue réelle ? » (gardée scellée côté client jusqu'à la restitution).
Mécanisme issu de la chasse (AAR militaire + chef-d'œuvre, feature score 9).

## 4. Non-objectifs (V1)

- Pas de paiement dans le parcours (le routage self-service renvoie au Checkout existant).
- Pas d'outil de prise de rendez-vous intégré (créneaux proposés par email — ADR-IQ-03).
- Pas de remplacement de l'entretien oral pour le palier haut : l'agent QUALIFIE et ARME,
  l'humain conclut.
- Pas de voix (texte uniquement).
- Pas de reprise de session multi-appareils (une session = un navigateur).

## 5. KPI de succès

- Taux de complétion du formulaire A (cible ≥ 60 % des démarrages).
- Taux d'engagement de l'étape B (≥ 40 % des soumissions).
- Part des payloads « exploitables » (A1+A2+A7 remplis) : **100 %** (bloquant par design).
- Taux de conversion branche entretien → entretien tenu.
- Richesse moyenne du brief (nb de champs remplis) — baseline actuelle : ~3 champs utiles.

## 6. Liens avec l'existant

- `quote_ownership.payload` (US-203) : le brief remplace/enrichit le payload actuel.
- Console simulation : le brief pré-seede la création de scénario (US-IQ-07).
- Chasse moat : M3 (surveillance des verdicts) consommera plus tard les hypothèses du brief.
- Admin /admin/quotes : affichage du brief + sujets confidentiels (US-IQ-06).
