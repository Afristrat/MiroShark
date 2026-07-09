# 08 — Journal des décisions du module Intake (ADR-IQ-*)

> À reporter dans `docs/08-decisions-log.md` canonique (numérotation ADR-0xx suivante)
> au moment du premier commit de code. Statut global : **proposé — en validation Amine.**

## ADR-IQ-01 — Agent conversationnel APRÈS le formulaire structuré, pas à la place

**Quoi** : le parcours commence par 8 questions structurées (3 écrans) ; l'agent LLM
n'intervient qu'ensuite, pour creuser, et il est passable d'un clic.
**Pourquoi** : (1) le brief minimal exploitable (A1/A2/A7) est garanti par design même si
l'agent échoue, est passé, ou si la gateway est down — le formulaire est le chemin de
fiabilité, l'agent est le chemin de richesse ; (2) un chat nu en entrée produit des
sessions vides et du coût LLM non borné ; (3) les règles de routage restent déterministes
sur des champs structurés.
**Alternatives rejetées** : chat-first (brief non garanti, coût non borné) ; formulaire
seul (incapable de creuser — constat d'Amine du 2026-07-09).
**Signal de réexamen** : taux d'engagement de l'étape B < 20 % (l'agent n'apporte pas
assez pour sa friction).

## ADR-IQ-02 — Routage à 3 branches 100 % déterministe (aucun LLM)

**Quoi** : la branche de sortie (self-service / devis 48 h / entretien) est calculée par
des règles explicites sur le brief (table de vérité testée), jamais par l'agent.
**Pourquoi** : le routage a des conséquences commerciales et doit être auditable,
testable, stable — un LLM y introduirait de la variance et un vecteur d'injection
(« route-moi en self-service »).
**Alternatives rejetées** : scoring LLM du lead (inauditables, manipulable).
**Signal de réexamen** : > 30 % de reroutages manuels par l'admin (les seuils sont faux —
ajuster les RÈGLES, pas passer au LLM).

## ADR-IQ-03 — Pas d'outil de calendrier en V1

**Quoi** : la branche entretien propose 2-3 créneaux par email (texte), pas de Cal.com ou
équivalent.
**Pourquoi** : YAGNI (Ponytail barreau 1) — volume actuel d'entretiens ≈ 0/semaine ; un
outil de calendrier est une dépendance, une surface d'attaque et un coût de maintenance
sans problème à résoudre aujourd'hui.
**Alternatives rejetées** : Cal.com self-hosted (défendable plus tard, service Coolify
en plus à opérer) ; Calendly (données prospects chez un tiers US).
**Signal de réexamen** : > 5 entretiens/semaine planifiés manuellement.

## ADR-IQ-04 — Confidentialité différée : flag SANS contenu

**Quoi** : quand un sujet est sensible, l'agent enregistre uniquement un libellé de sujet
(« structure actionnariale », « chiffres filiale X ») dans `confidential_flags` — jamais
le contenu. Le sujet est traité de vive voix (branche entretien).
**Pourquoi** : (1) privacy by design opposable (07-legal) ; (2) transforme une friction de
confidentialité en preuve de sérieux perçue (06-UX) ; (3) réduit la surface du transcript
avant NDA.
**Alternatives rejetées** : chiffrer le contenu confidentiel en base (complexité + le
prospect n'a aucune raison de nous confier le secret AVANT le NDA) ; ne rien capter du
tout (perd la liste des sujets à couvrir en entretien).
**Signal de réexamen** : des prospects écrivent le contenu confidentiel malgré le
mécanisme (améliorer le prompt, pas le stockage).

## ADR-IQ-05 — Issue réelle de la porte AAR : scellée jusqu'à restitution

**Quoi** : dans la porte 2 (« Testez-nous sur du connu »), l'issue réelle fournie par le
prospect est stockée scellée (chiffrement applicatif OU hachage+révélation, à trancher en
revue technique) et n'est lisible ni par l'agent ni par les admins avant la restitution.
**Pourquoi** : toute fuite de l'issue vers l'équipe ou vers le contexte du LLM détruit la
valeur probante du test — le scellé est ce qui rend la démonstration honnête ET
démontrable (cousin du registre scellé M1 de la chasse moat).
**Alternatives rejetées** : stockage en clair avec discipline d'accès (invérifiable, la
promesse ne tient que par la parole).
**Signal de réexamen** : mise en œuvre du registre scellé M1 (US-220) — mutualiser le
mécanisme.

## ADR-IQ-06 — Modèle LLM de l'agent : décision d'Amine via gateway, jamais en dur

**Quoi** : `INTAKE_LLM_MODEL` (env), défaut = `LLM_MODEL_NAME` de la gateway (ADR-004).
Aucun nom de modèle dans le code.
**Pourquoi** : réaffirme ADR-004 et la règle projet (le choix des modèles appartient à
Amine) ; l'agent de qualification a des exigences propres (multilingue ar/fr/darija en
compréhension, latence courte) qui justifieront peut-être un modèle distinct — sans
toucher au code.
**Signal de réexamen** : évaluations du doc 10 insuffisantes sur le modèle par défaut.
