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

## ADR-IQ-03 — Créneaux d'entretien via Cal.com self-hosted EXISTANT (v3 — corrige le mécanisme d'appel API de la v2 du 2026-07-09)

**Quoi** : la branche entretien envoie un lien de réservation Cal.com
(`agenda.ai-mpower.com`, instance self-hosted déjà en production sur le serveur) vers un
event type dédié « Entretien Bassira — 20 min », localisé selon la langue de session.
**Pourquoi** : la v1 de cette ADR écartait l'outil de calendrier par YAGNI — prémisse
FAUSSE : Cal.com était déjà installé et opéré sur l'infra (directive Amine 2026-07-09).
Le YAGNI ne s'applique pas à un outil existant : l'utiliser est le barreau Ponytail 5
(dépendance déjà installée), pas une dépendance nouvelle.
**Contraintes techniques vérifiées (v2, 2026-07-09)** : l'API v2 tourne dans un service
dédié (`calcom-api-…`) — la v2 de cette ADR affirmait un appel en réseau Docker interne
(`localhost:3002`), prémisse **écartée en v3** : ce chemin n'a jamais été confirmé
fonctionnel depuis le conteneur `miroshark` (raison exacte non retestée — bind loopback
suspecté, non déterminant) ; il est de toute façon **inutile**, le hostname public
suffit et est le seul chemin vérifié bout-en-bout.
**Correction v3 (vérifiée bout-en-bout 2026-07-09 puis reconfirmée par sonde live
2026-07-10 22h52)** : le backend appelle l'API via le hostname **public dédié**
`https://api-agenda.ai-mpower.com/v2/...` (PAS `agenda.ai-mpower.com/api/v2`, qui renvoie
une page Cloudflare « DNS points to prohibited IP », confirmé par sonde comparative sur
les deux hostnames). `api-agenda.ai-mpower.com` route directement vers l'API Cal.com
(erreur JSON `ForbiddenException` propre sur clé invalide — preuve que la requête atteint
bien le service, pas un WAF). Clé : env Coolify `CALCOM_API_KEY` (POST envs Coolify =
JSON minimal `{key, value}` — le champ `is_build_time` est refusé par cette version).
Endpoints utiles : `GET /v2/me` (validation), `GET /v2/event-types`, `GET /v2/slots`,
`POST /v2/event-types` (création — utilisé le 2026-07-10 pour créer l'event type
« Entretien Bassira » id=25, slug `entretien-bassira-20-min`, 20 min, sans visioconf
associée — à compléter manuellement dans l'UI Cal.com si besoin d'un lien Meet).
**Alternatives rejetées** : créneaux par email en texte (v1 — remplacée) ; réseau Docker
interne (v2 — écarté, non nécessaire) ; Calendly (données prospects chez un tiers US).
**Signal de réexamen** : indisponibilité récurrente de l'instance Cal.com, ou changement
de topologie réseau Docker qui rendrait `calcom-api` de nouveau joignable en interne.

## ADR-IQ-07 — Le transcript de qualification est une pièce DURABLE du dossier (directive Amine 2026-07-09)

**Quoi** : l'échange utilisateur↔IA de l'étape B n'est JAMAIS perdu : il fait partie
intégrante de la préqualification et du devis. Il est conservé tant que le dossier de
devis / la relation commerciale existe, versionné avec le brief, visible dans la vue
admin, et transmis comme contexte à l'équipe pour l'entretien et l'établissement du devis.
**Pourquoi** : le transcript EST la matière du devis adaptatif — le purger (comme le
proposait la v1 du doc 07 : purge J+90) détruirait la valeur du parcours. Directive
explicite d'Amine : « je ne dois jamais le perdre ».
**Conséquences** : (1) rétention alignée sur le dossier de devis (07-legal mis à jour —
base : mesures précontractuelles puis exécution du contrat) ; (2) le prospect est informé
que l'échange nourrit son devis (transparence, bandeau de l'étape B) ; (3) la purge ne
subsiste QUE pour les sessions abandonnées sans devis (J+30) ; (4) l'export/suppression
DSR inclut le transcript.
**Alternatives rejetées** : purge J+90 (v1 — incompatible avec la fonction commerciale du
transcript) ; anonymisation différée (détruirait le lien dossier↔échange).
**Signal de réexamen** : demande de suppression RGPD d'un prospect non converti (procédure
DSR à appliquer, cas par cas).

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

## ADR-IQ-08 — Playbook vivant de corrections + escalade silencieuse (2026-07-10, directive Amine)

**Quoi** : le prompt v2 de l'agent (post-corpus §10.3) ajoute un champ optionnel
`escalation` (catégorie fermée, jamais de contenu) à la sortie JSON structurée. Quand un
tour sort du cadre normal (imprévu, injection, ambiguïté, langue incomprise), il est loggé
dans une nouvelle table `intake_agent_escalations` (lecture réservée super-admin, jamais
exposée au prospect) et notifie Amine (email Resend). Amine seul consulte, tranche, et
ajoute une correction dans une nouvelle table `intake_agent_playbook` — des paires
{situation, réponse corrigée} — via une page d'admin dédiée (`/admin`, PAS Google Docs).
Le contenu actif du playbook est injecté dans le system prompt de l'agent, entre le prompt
de base et le contexte variable (brief/historique), et relu à CHAQUE tour, sur TOUTE
session future — pas seulement celle où l'incident a eu lieu.
**Pourquoi** : un prompt statique ne peut structurellement pas couvrir tous les scénarios
non envisagés — c'est mathématiquement impossible de lister à l'avance tous les inputs
adversariaux. Le playbook vivant transforme chaque incident en amélioration durable, sous
supervision humaine explicite (Amine corrige, jamais l'agent seul), traçable (log +
correction versionnée en base), sans jamais de fine-tuning ni d'ajustement automatique du
comportement — cohérent avec la règle « tout échec = ajustement du prompt, jamais de
contournement dans le code » (§10.3), appliquée en continu plutôt qu'en un seul passage.
« Silencieux » signifie invisible pour le prospect qui tente un jailbreak (l'escalade
n'apparaît jamais dans `message`, seul champ renvoyé au client) — PAS invisible pour
Amine, qui reçoit systématiquement la notification.
**Alternatives rejetées** : Google Docs comme source lue en prod par `agent_turn`
(latence/fiabilité d'un fetch externe dans un chemin déjà contraint à 30s, nouvelle
dépendance OAuth non documentée dans `05-integrations.md`, alors que Supabase est déjà la
source de vérité du repo, RLS et backup inclus). Fine-tuning/auto-apprentissage du modèle à
partir des conversations réelles (risque de dérive de qualité sans jugement humain, risque
de fuite de contenu confidentiel via `confidential_flags` si mal isolé).
**Signal de réexamen** : volume d'escalades > ce qu'Amine peut trancher manuellement en
temps utile (deviendrait un signal pour prioriser/grouper les corrections, pas pour
automatiser la correction elle-même).
