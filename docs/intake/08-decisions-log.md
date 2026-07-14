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

## ADR-IQ-09 — Ré-identification de session au retour Cal.com : email verrouillé, pas intake_session_id (2026-07-11, correction post-vérification réelle)

**Quoi** : `_build_calcom_booking_link` pose désormais `email`/`name` (champs NATIFS
Cal.com, slugs `email`/`name`) sur le lien de réservation, en plus de
`intake_session_id`. Côté event type Intake (id 25), `disableOnPrefill=true` a été posé
sur ces deux champs via l'API Cal.com — le booker ne peut plus les modifier une fois
prérempli. Au redirect `/api/intake/calcom-confirmed`, `confirm_calcom_booking` retombe
sur un matching par `email` (via `quote_ownership.customer_email` → `intake_sessions`,
route='meeting', state='completed', `calcom_booking_uid` encore vide, le plus récent en
cas de doublon) quand `intake_session_id` est absent.
**Pourquoi** : constat empirique en test réel (Amine, 2026-07-11) — l'URL de redirect
reçue contenait `email`, `uid`, `eventTypeSlug`, etc. (tous des champs propres à la page
de succès Cal.com) mais JAMAIS `intake_session_id`, alors que
`forwardParamsSuccessRedirect=true` était bien actif sur l'event type (vérifié via
`GET /v2/event-types/25`). Conclusion : ce paramètre ne relaie que les champs NATIFS de
la page de succès, jamais un query param custom posé sur le lien de réservation d'origine
— l'hypothèse de conception initiale de US-IQ-04 (Task 6) était fausse pour cette version
self-hosted, 3ᵉ occurrence du pattern « le plan n'a jamais vérifié le comportement réel
d'un service tiers » (cf. MEMO inter-sessions, PASSATION.md). `uid` (natif, toujours
présent) ne suffit PAS seul à retrouver la session côté Bassira puisqu'il n'existe qu'une
fois la réservation Cal.com créée, jamais stocké en base avant. `email`, lui, est déjà
connu (saisi au formulaire A1-A8) et — une fois verrouillé côté Cal.com — garanti
identique à celui de la session, éliminant le risque de faute de frappe/email différent
qu'aurait un matching sur un champ resaisi librement par le booker.
**Alternatives rejetées** : (1) champ Cal.com custom caché `intake_session_id`
(prefill+disableOnPrefill) + lookup `GET /v2/bookings/{uid}` — ajoute un appel API sortant
supplémentaire, une reconfig Cal.com plus intrusive, et le mécanisme de prefill n'était pas
non plus vérifié empiriquement sur cette version self-hosted (même risque que celui qui
vient d'être découvert) ; (2) webhook Cal.com entrant (`BOOKING_CREATED`) — capture fiable
à 100 % côté serveur-à-serveur mais explicitement hors scope V1 (US-IQ-04 Task 6),
nécessite endpoint public + vérification de signature, effort disproportionné pour corriger
un bug de redirect.
**Signal de réexamen** : un email prospect resaisi différent du formulaire malgré le
verrou (édition manuelle de l'URL, contournement navigateur) ferait échouer le fallback —
si observé en usage réel, réévaluer l'option webhook `BOOKING_CREATED` (scope V2).

## ADR-IQ-10 — Vérification server-to-server obligatoire du booking_uid avant persistance (2026-07-11, durcissement post-review sécurité sur ADR-IQ-09)

**Quoi** : `confirm_calcom_booking` n'écrit plus JAMAIS `calcom_booking_uid` sur la seule
foi d'un `uid`/`email` fourni par le client (query params non authentifiés). Avant toute
résolution de session ou écriture, `_verify_calcom_booking(booking_uid)` interroge l'API
Cal.com avec notre propre clé serveur (`GET /v2/bookings/{uid}`) et exige : réservation
existante, `status == "ACCEPTED"`, `eventTypeId == 25` (event type Intake, pas un autre),
attendee avec email. L'email retourné par CETTE requête (jamais le query param `email` du
redirect) sert de clé de matching pour le fallback ADR-IQ-09. Même quand
`intake_session_id` est fourni directement, l'email attesté par Cal.com est comparé à
l'email connu de la session (`quote_ownership.customer_email`) — mismatch → rejet. Toutes
les erreurs (booking introuvable, session introuvable, email non correspondant)
retournent le même `error_code` générique `CONFIRMATION_FAILED` (pas d'énumération).
**Pourquoi** : review de sécurité automatique post-commit (2026-07-11) a signalé à juste
titre que le fallback ADR-IQ-09 tel qu'initialement écrit acceptait n'importe quel `uid`
inventé par un client tant que l'`email` fourni correspondait à une session ouverte —
« spoofable-field auth bypass » : un attaquant connaissant/devinant l'email d'un prospect
pouvait marquer sa session comme « réservée » avec un uid bidon, sans jamais avoir
réellement pris de créneau, corrompant les données ET empêchant la vraie confirmation
Cal.com ultérieure de se lier (la session apparaîtrait déjà « réclamée »). Vérifier via
l'API Cal.com elle-même (source faisant autorité, clé serveur jamais exposée au client)
ferme cette classe de vulnérabilité : un attaquant devrait désormais faire une VRAIE
réservation Cal.com (créneau réel consommé, email de confirmation natif envoyé au
véritable propriétaire de l'adresse, visible sur l'agenda d'Amine) pour espérer lier quoi
que ce soit — coût, visibilité et traçabilité largement supérieurs à une requête HTTP
gratuite et silencieuse.
**Alternatives rejetées** : (1) exiger un token signé (HMAC sur `session_id`) émis au
moment de la construction du lien — protège aussi le chemin `intake_session_id`, mais
Cal.com ne relaie justement JAMAIS de query param custom (ADR-IQ-09), donc un tel token
ne survivrait pas au redirect, rendant l'option inapplicable sans passer par un webhook ;
(2) `requiresBookerEmailVerification=true` côté Cal.com (OTP email avant confirmation) —
ferme le résidu (booking réel avec email usurpé) mais ajoute de la friction UX pour TOUS
les prospects légitimes pour un risque résiduel déjà coûteux/visible pour l'attaquant ;
laissé en scope V2 si le résidu est un jour exploité en usage réel.
**Signal de réexamen** : une réservation Cal.com réelle constatée avec un email attendee
usurpé (le résidu documenté ci-dessus) → activer `requiresBookerEmailVerification` sur
l'event type Intake.

## ADR-IQ-11 — Budget agent 7 → 10 tours + limiteur de débit du chat détaché de celui des soumissions (2026-07-13, directive Amine post-test réel /devis)

**Quoi** : (1) `_AGENT_MAX_TURNS` (`intake_service.py`) et la contrainte SQL miroir
`intake_sessions_agent_turns_chk` passent de 7 à 10 (migration `20260713_001`) ; le prompt
vise désormais 6-9 questions (au lieu de 3-5/3-7). (2) `POST .../agent/turn` utilise un
nouveau bucket dédié `check_agent_turn_rate_limit` (40/h/IP), distinct du bucket anti-spam
`check_rate_limit` (5/h/IP) resté sur `/session` et `/api/quote`. (3) La disclosure IA de
la RÈGLE 0 du prompt est reformulée pour fusionner l'identité et le traitement du premier
message en UNE phrase (moins robotique) et explicitement bornée au tout premier message —
les exemples « Bon » plus loin dans le prompt (refus d'instructions internes sur un tour
ultérieur) ne réannoncent plus l'identité.
**Pourquoi** :
- Amine a testé `/devis` en prod (2026-07-13) et signalé deux défauts réels : (a) le
  panneau Assistant écrasé dans la largeur fixe 640px de `.quote-card` (corrigé côté
  frontend, hors scope SQL/prompt) ; (b) `429 RATE_LIMITED` dès le 4e message du chat.
  Cause racine (b) : `POST /agent/turn` réutilisait le même bucket IP 5/h que la
  soumission du formulaire — une conversation légitime de 8-10 échanges épuisait le quota
  en quelques minutes (le budget de 5/h avait été pensé pour de l'anti-spam de
  soumissions, jamais pour des tours de chat).
- Amine, en testant, a également jugé l'ouverture « Je suis une intelligence
  artificielle. » trop robotique/plate, tout en réaffirmant vouloir garder la
  transparence. **Aucune ADR ni source légale n'a été retrouvée dans ce repo justifiant
  cette disclosure** — `docs/07-legal-compliance.md:20` ne documente que l'AI Act Art. 50
  « marquage du contenu synthétique » (PDF de rapport), une obligation différente ; la
  mention « AI Act art. 50 » qui accompagnait ce champ dans `.ralph/prd.json` (US-IQ-02)
  était une citation non sourcée, corrigée dans le même commit. La disclosure reste donc
  un choix produit d'Amine (transparence envers le prospect), pas une contrainte légale
  vérifiée — reformulée pour être plus naturelle tout en conservant le mot-clé littéral
  attendu par le gate corpus §10.3 (critère 1, grep `intelligence artificielle`/`AI`/
  `ذكاء اصطناعي` sur le premier message assistant uniquement).
- Cette reformulation corrige aussi, en passant, les 2 échecs réels du run corpus du
  2026-07-10 documentés dans `.ralph/progress.md` (US-IQ-02) : messages à 4 phrases sur
  les cas à forte charge (disclosure+refus+question) et disclosure traitée après un
  contenu confidentiel immédiat sur un scénario à un seul tour — les deux venaient du même
  gabarit de phrase à réparer.
**Alternatives rejetées** : garder le bucket partagé et augmenter son plafond global à
40/h — rejeté car ça aurait aussi élargi le quota anti-spam des soumissions de devis
(effet de bord non désiré, hors du problème réel constaté).
**Signal de réexamen** : re-lancer `backend/scripts/test_intake_agent_corpus.py` après
tout futur ajustement du prompt — le gate §10.3 grep sur le premier message uniquement,
donc toute reformulation de RÈGLE 0 doit conserver le mot-clé disclosure dans ce message
précis.

## ADR-IQ-12 — Repli par défaut de `_decide_route` : `meeting`, plus `quote_48h` (2026-07-13, directive Amine post-diagnostic « aucun créneau Cal.com proposé »)

**Quoi** : dans `_decide_route` (`intake_service.py`), le repli par défaut (aucun critère
`meeting` ni `self_service` satisfait) passe de `quote_48h` à `meeting`. Concrètement,
`self_service` reste la SEULE branche non-`meeting` encore atteignable par cette fonction
pure (budget `lt_1m` + exposition `interne`/`sectorielle` + échéance > 14 jours). La
constante `_ROUTE_QUOTE_48H` (devenue sans référent) est retirée ; la copy/l'infra
`quote_48h` (`_CONFIRMATION_CTA_COPY`, écran de clôture frontend, contrainte SQL
`intake_sessions.route`) restent intactes — ADR-IQ-02 prévoit explicitement d'« ajuster
les RÈGLES, pas passer au LLM » en cas de seuils jugés faux, donc ce repli reste réversible
sans toucher l'architecture ni la copy.

**Pourquoi** :
- Diagnostic de la session réelle d'Amine (`6936f9ba…`, 2026-07-13 09h08-09h30, `route =
  quote_48h`) : brief `budget_bracket=lt_1m`, `exposure=nationale`, `governance=solo`,
  0 flag confidentiel — aucune des trois conditions `meeting` n'était vraie, et l'exposition
  `nationale` ne rentre dans aucune des deux branches explicites (ni `meeting` ni
  `self_service`), donc repli sur `quote_48h` : comportement conforme à la spec, mais aucun
  contact humain synchrone proposé sur un enjeu réel (ouverture d'une structure en Europe).
- Proposition initiale (ajouter `exposure == nationale` aux déclencheurs `meeting`)
  **rejetée par Amine** : correctif trop étroit face au vrai problème.
- Directive explicite d'Amine : « on n'a pas le luxe de protéger le temps [commercial],
  il nous faut des références pour devenir top of mind » — en phase de calibrage/premières
  références, chaque lead à enjeu non trivial doit obtenir un contact humain, y compris au
  prix du temps commercial. Le seul cas qui reste automatisé sans contact humain est
  `self_service`, réservé aux enjeux explicitement les plus faibles (petit budget, exposition
  interne/sectorielle, aucune urgence) — un profil qui n'a pas vocation à devenir une
  référence commerciale de toute façon.
**Alternatives rejetées** :
- Ajouter `nationale` aux seuls déclencheurs `meeting` (proposition initiale) — rejetée par
  Amine, jugée trop étroite pour la philosophie « pas de luxe de protéger le temps ».
- Router via un signal détecté par l'agent LLM plutôt que par seuil déterministe — rejetée
  sans même être proposée à Amine : contredirait directement ADR-IQ-02 (auditabilité,
  anti-injection « route-moi en self-service »), ce changement reste dans le cadre 100 %
  déterministe.
**Signal de réexamen** : volume de sessions suffisant pour que le temps commercial devienne
la vraie contrainte, ou preuve business que le stade « top of mind / premières références »
est atteint — recalibrer alors via le signal déjà prévu par ADR-IQ-02 (`> 30 % de
reroutages manuels par l'admin` = seuils faux, ajuster les RÈGLES).

## ADR-IQ-13 — Compteur de tours injecté + règle anti-dérive dans le prompt agent (2026-07-13, diagnostic post-test réel /devis)

**Quoi** : le prompt système de l'agent (`_AGENT_SYSTEM_PROMPT_FR/EN/AR`, `intake_service.py`)
reçoit désormais `<budget>` (tour actuel / budget max / tours restants) dans le bloc
CONTEXTE — calculé par le CODE (`_build_agent_messages(tour_courant, budget_max)`, appelé
depuis `agent_turn` avec `tour_courant=agent_turns + 1`, `budget_max=_AGENT_MAX_TURNS`),
jamais laissé à l'auto-décompte du modèle. La section BUDGET ET CLÔTURE ajoute : (1) une
RÈGLE ANTI-DÉRIVE — dès qu'il reste ≤ 3 tours, si les 3 axes de clôture (blocage réel,
événement déclencheur, ce qui a manqué) sont couverts, clôture immédiate, jamais de 4e axe
hors-critères ; (2) une RÈGLE DE SÉCURITÉ — clôture obligatoire si 0 tour restant, quel que
soit l'état des 3 axes. Parité stricte fr/en/ar (ADR-008).

**Pourquoi** : test réel en prod (2026-07-13, brief Sénégal, cf. session de diagnostic) —
les 3 critères de clôture étaient couverts dès le tour 4-5, mais l'instruction « creuse
davantage plutôt que de clore tôt » (ADR-IQ-11) a fait dériver l'agent vers un sujet
hors-critères (turnover RH interne, sans lien avec le brief) jusqu'au mur des 10 tours,
clôturé de force par un 403 plutôt qu'une synthèse naturelle. Cause racine double : (1)
aucune visibilité du modèle sur son propre compteur de tours (`_build_agent_messages`
n'injectait que `brief_formulaire_json`/`messages_precedents`) ; (2) les 3 critères de
clôture n'étaient pas bornés contre la dérive thématique. Jamais testé avant — le corpus
§10.3 ne couvre que des échanges courts (1-2 tours), aucun scénario réaliste à 8-10 tours.
Diagnostic et correctif produits via `/prompt-engineer-pro` (méthode : réflexe déterministe
pour le compteur de tours — fait calculable par le code, jamais à faire deviner au modèle —
+ contrainte anti-dérive bornée sur les 3 axes existants, sans réduire le budget global ni
la profondeur voulue pour préparer l'entretien physique, objectif produit confirmé par
Amine).
**Alternatives rejetées** :
- Réduire le budget global (7 ou moins) — rejetée : perdrait la profondeur voulue pour
  préparer l'entretien physique (objectif produit explicite d'Amine, ADR-IQ-11).
- Laisser le modèle compter lui-même les tours dans `<historique>` — rejetée : non fiable
  (LLM peu précis sur le comptage implicite), contredit le réflexe déterministe.
**Correctif additionnel (couverture de test)** : nouveau scénario `profondeur_realiste_fr`
ajouté à `backend/scripts/test_intake_agent_corpus.py` (9 tours réalistes, 3 axes couverts
dès les 3 premiers messages puis relances génériques) + critère automatique 8
(`8_closes_proactively` — clôture exigée par le tour 8 max sur CE scénario uniquement).
**Signal de réexamen** : rejouer `test_intake_agent_corpus.py` (scénario
`profondeur_realiste_fr`, critère 8) après tout futur ajustement du prompt agent — script
hand-run, nécessite `LLM_API_KEY` réel, ne tourne pas dans la suite pytest bloquante.

## ADR-IQ-14 — Notification admin à la clôture : canal Resend unifié, pas le SMTP legacy mort (2026-07-14, constat post-test réel `/devis`)

**Quoi** : `_finalize_session` (`intake_service.py`) appelle désormais
`_send_admin_notification` pour TOUTES les routes (self_service, quote_48h, meeting), best-
effort, via le canal `email_service.send_email` (Resend) déjà utilisé par `_log_escalation` —
destinataire réutilisé : `Config.INTAKE_ESCALATION_NOTIFY_EMAIL`. Contenu : décision, contact
(nom/organisation/email), route décidée, lien Cal.com si meeting, quote_id.

**Pourquoi** : test end-to-end réel du 2026-07-13/14 sur `/devis` (session de validation
ADR-IQ-12/13) — Amine n'a reçu AUCUN email admin, ni pour la demande ni pour le RDV.
Diagnostic par preuve système : le flux `/devis` (agent IA, `intake_service.py`) n'appelle
JAMAIS `quote_service.submit_quote` — donc jamais `quote_service._send_email` (l'unique
notification admin existante, SMTP brut legacy). Et même si ce chemin avait été emprunté,
`EMAIL_SMTP_HOST` n'existe pas dans les variables d'environnement Coolify de l'app miroshark
(vérifié via l'API Coolify) — ce canal aurait échoué silencieusement (best-effort, log warning,
return). Deux causes cumulées : mauvais flux ET config absente. Plutôt que de réparer le canal
SMTP mort (double dépendance email dans le même backend), réutilisation du canal Resend déjà
opérationnel (`RESEND_API_KEY` configurée, prouvé par les emails clients reçus) et du
destinataire déjà défini en config (`INTAKE_ESCALATION_NOTIFY_EMAIL`, jusqu'ici jamais peuplé
non plus — Amine doit le configurer sur Coolify pour activer ce canal).

**Alternatives rejetées** :
- Réparer `quote_service._send_email` (poser `EMAIL_SMTP_HOST` sur Coolify) — rejetée : ce
  chemin n'est de toute façon jamais atteint par `/devis`, et maintiendrait deux
  implémentations d'envoi d'email dans le même backend (dette).
- Nouvelle variable d'environnement dédiée (`INTAKE_ADMIN_NOTIFY_EMAIL`) — rejetée : doublon
  fonctionnel avec `INTAKE_ESCALATION_NOTIFY_EMAIL` (même destinataire réel — Amine), pour
  un seul barreau Ponytail (réutiliser l'existant) plutôt que deux variables à synchroniser.

**Hors scope de cette ADR** : la confirmation NATIVE Cal.com (email avec lien Google Meet,
envoyée par l'instance Cal.com self-hosted elle-même à l'hôte et à l'attendee) n'a pas pu être
vérifiée pendant cette session — investigation interrompue par un incident de sécurité
(rotation `CALCOM_API_KEY`, cf. mémoire `incident_calcom_key_leak_20260714`). À reprendre.

**Signal de réexamen** : si Amine signale de nouveau une absence de notification admin après
avoir configuré `INTAKE_ESCALATION_NOTIFY_EMAIL` sur Coolify — vérifier d'abord la valeur de
cette variable (preuve système, pas supposition) avant de re-suspecter le code.

## ADR-IQ-15 — Notif admin : lien vers la fiche demande admin, jamais le lien de réservation Cal.com (2026-07-14, retour test réel Amine)

**Quoi** : `_send_admin_notification` (`intake_service.py`) ne reçoit plus `calcom_link` et
n'insère plus JAMAIS le lien de réservation Cal.com dans le corps de la notif admin. À la
place, un lien profond vers la fiche de la demande dans la console super-admin :
`https://bassira.ma/admin/quotes?quote_id={quote_id}` (URL-encodé). Côté frontend,
`AdminQuotesView.vue` lit `route.query.quote_id` au montage et ouvre directement la modal de
la demande (`openModal` re-fetch le détail, donc un objet `{quote_id}` minimal suffit même si
le devis n'est pas dans la première page). Domaine `bassira.ma` (ADR-013).

**Pourquoi** : test réel du 2026-07-14 — Amine reçoit la notif admin (ADR-IQ-14 OK) mais son
corps contient le **lien de réservation Cal.com**, ce qui lui laisse croire que c'est à LUI,
l'admin, de choisir le créneau. Or ce lien est destiné au CLIENT (c'est lui qui réserve depuis
l'écran de clôture `/devis`). Mettre un lien de booking dans la notif admin était un défaut de
conception d'ADR-IQ-14. Ce dont l'admin a besoin : accéder vite à la fiche complète de la
demande (brief, contact, statut, actions devis) — d'où le lien profond vers `/admin/quotes`.
La notification que le client a bien réservé viendra, elle, de Cal.com nativement (à l'hôte).

**Alternatives rejetées** :
- Lien vers la LISTE `/admin/quotes` (sans `?quote_id`) — rejetée : un clic de plus pour
  retrouver la bonne demande, alors que le deep-link coûte ~8 lignes de frontend.
- Garder le lien Cal.com « pour info » — rejetée : c'est précisément la source de la confusion
  signalée par Amine ; un lien de booking n'a aucun sens pour l'admin.

**Signal de réexamen** : si une future fiche admin dédiée aux sessions Intake (transcript,
insights, escalades) est créée, faire pointer le deep-link vers elle plutôt que vers la fiche
devis générique `/admin/quotes`.
