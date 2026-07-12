# Design — US-IQ-02 frontend : écran Assistant (agent conversationnel de qualification)

Date : 2026-07-12. Statut : validé section par section avec Amine (brainstorming interactif,
hors mode Ralph — SOP-013 non applicable). Prochaine étape : `superpowers:writing-plans`.

## Contexte et problème

Le backend de l'agent conversationnel de qualification (US-IQ-02) est construit, testé (TDD),
mergé (`8b0f89b`) et déployé — mais **jamais câblé côté frontend**. `frontend/src/api/intake.js`
n'expose que `startIntakeSession`/`submitIntakeForm` ; `QuoteView.vue` saute directement du
formulaire A1-A8 soumis à un écran « merci » statique. Conséquence vérifiée : depuis la mise en
prod du formulaire `/devis`, aucun prospect réel n'a jamais vu l'agent, ni reçu de routage, ni
d'email contextualisé, ni de lien Cal.com — uniquement un ID de devis.

Ce document couvre le câblage complet : nouvel écran Assistant (étape 4), deltas backend
nécessaires pour l'alimenter, et le changement de timing de l'email de confirmation pour la
branche `meeting` (US-IQ-04, décision Amine actée en session précédente).

**Hors scope** : ajustement du system prompt de l'agent pour les 2 échecs du corpus §10.3
(traité séparément, avant ou en parallèle de l'implémentation de ce design — cf. passation) ;
US-IQ-05 (Porte 2 AAR) ; US-IQ-06 (vue admin enrichie).

## Décisions actées

1. **Amorce automatique** : premier tour `agent_turn` envoyé au montage de l'écran avec un
   message synthétique non vide, jamais affiché au prospect — l'agent parle en premier sans que
   le prospect ait besoin de taper quoi que ce soit.
2. **Prompt corrigé avant le frontend** : les 2 échecs corpus §10.3 sont ajustés (chantier
   séparé) avant de considérer US-IQ-02 pleinement clos, indépendamment de ce chantier frontend.
3. **Écran 4 complet conforme au prompt Stitch §10.2** (`docs/intake/10-execution-prompts.md:83-104`)
   — chat + bandeau IA permanent + colonne latérale (brief live + sujets verrouillés) + bouton
   « Passer cette étape ». Pas de version dégradée sans colonne latérale.
4. **Lien Cal.com affiché et cliquable directement à l'écran de clôture** (branche `meeting`),
   pas seulement dans l'email.
5. **Timing de l'email de confirmation déplacé pour la branche `meeting` uniquement** :
   `_send_intake_confirmation` (US-IQ-04) ne part plus à la clôture de l'agent/skip, mais
   uniquement après succès de `confirm_calcom_booking` (créneau réellement validé, ADR-IQ-10).
   Branches `quote_48h`/`self_service` : comportement inchangé, email immédiat à la clôture.
6. **Package self-service recommandé par l'agent, tranché par `/offres`** (option hybride,
   choisie par Amine face à 3 options — cf. section "Recommandation de package self-service").

## Renumérotation des étapes (`QuoteView.vue`)

- Étape 4 (nouvelle) : écran Assistant.
- Étape 5 (renommée depuis l'actuelle étape 4, ligne 396) : écran de clôture.
- Le stepper visuel (`Math.min(currentStep, 3)`) reste inchangé, les étapes 4/5 restent hors
  stepper comme aujourd'hui.
- `submit()` (ligne 577) : au succès de `submitIntakeForm`, `currentStep.value = 4` (au lieu du
  saut direct vers l'ancienne étape 4/nouvelle étape 5). L'échec technique du submit lui-même
  (avant toute session créée) garde son comportement actuel, renuméroté vers l'étape 5.
- Redirection Cal.com existante (`?calcom_confirmed=1` → `currentStep = 4` aujourd'hui,
  ligne 488) : à corriger pour pointer vers l'étape **5** dans la nouvelle numérotation.

## Recommandation de package self-service

Seuls 3 packages du catalogue (`frontend/src/views/OffersView.vue`) ont `selfService: true` :
`pmf_discovery` (10k MAD, PMF pré-levée, founders), `crisis_drill_24h` (20k MAD, crise
réputationnelle, DG, featured), `adcheck_lite` (15k MAD, test de 2 concepts pub, marketing).
Aucune logique n'existe pour choisir lequel correspond à un brief donné (A1 décision / A2
options sont du texte libre fr/en/ar).

**Approche retenue** : au moment où `_decide_route` calcule `self_service`, un appel LLM
supplémentaire (réutilise l'agent déjà dans la boucle, pas de nouveau composant) reçoit les 3
descriptions de packages + le brief complet, renvoie `{package_id, rationale}` (1 phrase).
Validation stricte : `package_id` doit être dans `{pmf_discovery, crisis_drill_24h,
adcheck_lite}}`, sinon repli déterministe sur `crisis_drill_24h` (le package `featured`) sans
rationale spécifique. Dans `_close_session_gracefully` (gateway LLM indisponible), pas de second
appel LLM — repli direct sur `crisis_drill_24h`.

Le frontend affiche la recommandation (`rationale`) dans le message de clôture de l'agent, puis
redirige vers `/offres?recommended=<package_id>` — **delta frontend à ajouter dans
`OffersView.vue`** : lire le query param, scroller vers la carte concernée et la mettre en
surbrillance (aucun mécanisme de préselection par query param n'existe aujourd'hui).

## Deltas backend (`backend/app/services/intake_service.py`)

**Problème de duplication identifié** : la logique de clôture (calcul de `route`, décision
d'envoi email, construction de payload) existe dupliquée dans 3 points d'entrée indépendants :
`complete_routing` (ligne 417), la branche `close: true` d'`agent_turn` (ligne 984), et
`_close_session_gracefully` (ligne 1009). Extraction d'un helper commun :

```python
def _finalize_session(session, brief, confidential_flags, route, *, client, llm=None) -> dict:
    """Construit le payload de clôture commun aux 3 points d'entrée : calcom_link (branche
    meeting) ou package_recommendation (branche self_service), et pilote l'envoi de l'email
    de confirmation (jamais pour meeting — déplacé vers confirm_calcom_booking)."""
```

Utilisé par les 3 call sites, qui gardent seulement leur logique propre (persistance,
gestion d'erreurs HTTP spécifique).

**Contenu du helper, par branche** :
- `meeting` : `email`/`full_name` ne sont **pas** sur la row `intake_sessions` (vérifié par
  grep de `submit_form`) — ils vivent dans `quote_ownership`, récupérables via
  `qo.get_quote_payload_from_supabase(session["quote_id"], client=client)`, exactement le
  mécanisme déjà utilisé par `_send_intake_confirmation`. `calcom_link =
  _build_calcom_booking_link(session["id"], locale, email=payload.get("email"),
  full_name=payload.get("full_name"))` (déjà pur, aucun appel réseau) → `data["calcom_link"]`.
  `_send_intake_confirmation` **non appelé ici**.
- `self_service` : recommandation de package (section précédente) → `data["package_recommendation"] = {package_id, rationale}`. Email envoyé normalement (inchangé).
- `quote_48h` : inchangé, email envoyé normalement.

**`agent_turn`** : `data["confidential_flags"]` (liste de `{topic_label, flagged_at}`, jamais de
contenu) ajouté à **chaque** réponse (pas seulement à la clôture) — alimente la colonne
« sujets verrouillés » en direct pendant la conversation. Ce champ existe déjà côté serveur
(calculé pour le routage) mais n'est aujourd'hui jamais exposé au client.

**`confirm_calcom_booking`** : après succès de la vérification server-to-server (ADR-IQ-10),
appel de `_send_intake_confirmation` ajouté ici pour la branche `meeting`.

**Endpoints HTTP** — déjà existants, aucun nouveau nécessaire : `POST
/api/intake/session/<id>/agent/turn` et `POST /api/intake/session/<id>/complete`
(`backend/app/api/intake.py:88,121`).

## Composants frontend

**Un seul composant** : `IntakeAgentPanel.vue`, monté par `QuoteView.vue` à l'étape 4.

```vue
<IntakeAgentPanel :session-id="sessionId" :brief="brief" :locale="locale" @closed="onAgentClosed" />
```

- **Props** : `sessionId`, `brief` (déjà en mémoire depuis `submit()`, alimente la colonne
  « brief live » sans appel réseau), `locale`.
- **Émission unique** : `closed` avec `{ route, calcomLink?, packageRecommendation? }` —
  `QuoteView` bascule `currentStep.value = 5` et stocke le payload pour l'affichage de clôture.

**Réutilisation de `frontend/src/components/ReportChatPanel.vue`** : classes CSS
`rcp-message`/`rcp-message-bubble`/`rcp-thinking-dot`/`rcp-textarea`/`rcp-send-btn` reprises
comme base (tokens `--wi-*`, déjà RTL-safe). `position: fixed` (panneau coulissant) abandonné —
`IntakeAgentPanel` est **inline**, layout 2 colonnes (`grid-template-columns: 1fr 320px`, colonne
unique empilée en mobile/logical RTL). Pas de `localStorage` (persistance déjà backend, via
`transcript` en base).

**Amorce automatique** (`onMounted`) : appel direct `postAgentTurn(sessionId, <amorce locale>)`
(ex. fr : « Je suis prêt(e) à échanger sur mon brief. ») — la bulle « user » correspondante
n'est **jamais poussée dans `messages.value`**, seule la réponse assistant l'est.

**Colonne latérale** :
- `briefSummaryItems` — computed statique sur la prop `brief` (A1 décision, A2 options, A3
  échéance, A6 enjeu).
- `lockedTopics` — `ref([])`, alimenté en poussant `data.confidential_flags` après chaque tour ;
  rendu avec icône cadenas + `topic_label`.

**Bouton « Passer cette étape »** : appelle `completeIntakeSession(sessionId)` directement
(sans passer par le chat) — émet `closed` avec le payload retourné.

**`frontend/src/api/intake.js`** — 2 ajouts :

```js
export const postAgentTurn = (sessionId, message) =>
  service.post(`/api/intake/session/${sessionId}/agent/turn`, { message })

export const completeIntakeSession = (sessionId) =>
  service.post(`/api/intake/session/${sessionId}/complete`, {})
```

## i18n (fr/en/ar)

Convention existante : les clés de l'écran de clôture vivent sous `quote.step3.*`
(`calcomConfirmedTitle` etc.), découplées du numéro `currentStep`. Nouvelles clés sous
`quote.step3.assistant.*` pour rester cohérent :

- `banner` — « Vous échangez avec une IA »
- `you` / `assistant` — pattern repris de `report.chat.you`/`.assistant`
- `placeholder`, `send`, `sending`, `thinking` — repris de `report.chat.*`
- `briefSummaryTitle` — « Votre brief »
- `lockedTopicsTitle` — « Réservé à l'échange de vive voix »
- `skipButton` — « Passer cette étape »
- `recommendedPackage` — « Package recommandé : {package} »
- `viewMeeting` — « Voir mon créneau »

Parité stricte fr/en/ar dans le même commit (ADR-008). Échapper `@` en `{'@'}` si un placeholder
en contient.

## Gestion d'erreurs

Le mécanisme générique `formatApiError(err, t)` (`frontend/src/utils/error-handler.js`) mappe
tout `error_code` backend vers `errors.<CODE>` — aucun nouveau code de gestion d'erreur, juste
des clés `errors.*` à ajouter (fr/en/ar) :

- `AGENT_BUDGET_EXHAUSTED` (403, 7 tours atteints) — invite à cliquer « Passer cette étape ».
- `AGENT_INVALID_OUTPUT` (502) — invite à réessayer le message.
- `INVALID_STATE` (409) — étape déjà validée.
- `BRIEF_MISSING` (409) — filet de sécurité générique (cas théorique à ce stade du parcours).
- `SUPABASE_UNAVAILABLE` (503) — service temporairement indisponible.

**Cas spécial — gateway LLM indisponible** (`_close_session_gracefully`, HTTP 200 avec
`data.agent_unavailable === true`) : pas une erreur HTTP. `IntakeAgentPanel` détecte ce champ et
clôt immédiatement la conversation avec une bannière neutre (« Votre brief a été transmis, nous
prenons le relais »), émet `closed` avec le payload de repli déterministe comme une clôture
normale.

## Plan de tests

**Contrainte structurante** : `frontend/tests/e2e/intake-parcours.spec.ts` est strictement
lecture seule par politique du repo (jamais de clic sur `submit`, Playwright tourne contre la
prod réelle — SOP-011). Le plan de tests de l'écran Assistant doit respecter la même politique.

**E2E Playwright (extension du fichier existant)** : interception réseau (`page.route()`) sur
`POST /api/intake/session`, `/form`, `/agent/turn`, `/complete` avec fixtures JSON — teste le
rendu de l'écran Assistant (bandeau, bulles, colonne, skip, RTL ar) sans appel business réel.
3 scénarios mockés :
1. Clôture `route=meeting` → `calcom_link` cliquable affiché.
2. Clôture `route=self_service` → `package_recommendation` affiché.
3. `agent_unavailable=true` → bannière neutre de repli.

**Backend pytest (TDD)**, sur `_finalize_session` et les 3 call sites :
- `confidential_flags` exposé dans chaque réponse `agent_turn`.
- `self_service` : `package_id` valide conservé ; invalide/absent → repli `crisis_drill_24h` ;
  dans `_close_session_gracefully` → repli direct sans appel LLM.
- `meeting` : `calcom_link` présent et bien construit ; `_send_intake_confirmation` **jamais**
  appelé dans `complete_routing`/`agent_turn`-close/`_close_session_gracefully` pour cette
  branche (assertion de non-appel, mock).
- `confirm_calcom_booking` : `_send_intake_confirmation` appelé uniquement après succès de
  `_verify_calcom_booking`.
- `quote_48h`/`self_service` : `_send_intake_confirmation` toujours appelé immédiatement
  (non-régression).

**Vérification déployée réelle (SOP-011)** : un vrai clic sur `bassira.ma/devis` par Amine (ou
via Chrome connecté) une fois livré — seule preuve valable en usage réel, le Playwright mocké ne
couvre que le rendu.
