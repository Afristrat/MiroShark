# US-IQ-02 Frontend — Écran Assistant : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Câbler le frontend de l'agent conversationnel de qualification (US-IQ-02) sur le
formulaire `/devis` de Bassira, pour que les branches de routage (self_service/quote_48h/
meeting), déjà correctes côté backend, deviennent enfin atteignables par un vrai clic
prospect — actuellement `QuoteView.vue` saute du formulaire à un écran « merci » statique
sans jamais appeler `agent/turn` ni `complete_routing`.

**Architecture:** Nouvel écran « Assistant » (étape 4 de `QuoteView.vue`, composant
`IntakeAgentPanel.vue`) entre le formulaire A1-A8 (étape 3) et l'écran de clôture (étape 5,
renuméroté depuis l'actuelle étape 4). Backend : extraction d'un helper `_finalize_session`
partagé par les 3 points de clôture existants (`complete_routing`, `agent_turn` en
`close:true`, `_close_session_gracefully`) pour éliminer une triplication de logique et,
accessoirement, corriger un vrai trou (aujourd'hui seul `complete_routing` envoie l'email de
confirmation — `agent_turn`/`_close_session_gracefully` ne le font JAMAIS, cf. Task 1).

**Tech Stack:** Backend Flask/Python (`uv`), Supabase (via `FakeSupabase` en test), frontend
Vue 3 `<script setup>` + Pinia + vue-i18n, tests `pytest` (backend) + Playwright (E2E frontend,
mocké réseau).

## Global Constraints

- Design source de vérité : `docs/superpowers/specs/2026-07-12-us-iq-02-frontend-design.md`
  (validé section par section avec Amine, committé `5acc4aa`, corrigé `ae2df33`).
- Aucun `any` implicite, zéro dette technique laissée — `py_compile` + `npm run build` sont
  les gates minimum (pas de typecheck TS configuré sur ce repo).
- Backend gates bloquants après CHAQUE task backend : `cd backend && uv run pytest -m "not integration"` (0 échec) + `cd backend && uv run ruff check .` (0 erreur).
- Frontend gates bloquants après CHAQUE task frontend : `cd frontend && npm run build` (0 erreur).
- **JAMAIS de serveur de dev local pour valider un changement** (SOP-011) — vérification
  visuelle réelle seulement après déploiement, sur `bassira.ma/devis`.
- `frontend/tests/e2e/intake-parcours.spec.ts` et `tunnel-commercial.spec.ts` sont
  **strictement lecture seule** : jamais de clic sur `submit`, Playwright tourne contre la
  prod réelle. Toute extension de test utilise `page.route()` (interception réseau), jamais
  un vrai POST business.
- Parité i18n fr/en/ar stricte dans le même commit (ADR-008) — fr rédigé dans ce plan fait foi,
  en/ar déjà fournis ci-dessous (pas à improviser à l'implémentation).
- Packages self-service réels (vérifiés par grep `frontend/src/views/OffersView.vue`) :
  `pmf_discovery` (10k MAD), `crisis_drill_24h` (20k MAD, `featured`), `adcheck_lite` (15k MAD).
  Ne pas confondre avec `_VALID_PACKAGES` de `quote_service.py` (flux de devis manuel, sans
  rapport).
- `frontend/src/api/index.js` (`service`) : `service.post(...)` résout DIRECTEMENT le body
  backend parsé (`{success, data}` ou lève une `Error` sur `success:false`) — jamais
  `response.data.data`, l'intercepteur a déjà déballé.

---

## Task 1 : Backend — `_finalize_session` (branche `meeting`), suppression de l'envoi email à la clôture pour cette branche

**Files:**
- Modify: `backend/app/services/intake_service.py:417-480` (`complete_routing`), `:883-1032` (`agent_turn` + `_close_session_gracefully`)
- Test: `backend/tests/test_unit_intake.py:546-604` (2 tests existants à corriger, 1 à ajouter), `backend/tests/test_unit_intake_agent.py` (2 tests à ajouter)

**Interfaces:**
- Produces: `_finalize_session(session, brief, confidential_flags, route, *, client, llm=None, attempt_llm=True) -> Dict[str, Any]` — retourne un dict à fusionner dans la réponse HTTP (`{}` pour `quote_48h`, `{"calcom_link": str}` pour `meeting` dans ce Task ; `{"package_recommendation": {...}}` pour `self_service` arrive Task 4 — dans ce Task, la branche `self_service` retourne `{}` en attendant).
- Consumes (déjà existant) : `_build_calcom_booking_link(session_id, locale, *, email=None, full_name=None) -> str`, `_send_intake_confirmation(session: dict, *, client) -> None`, `qo.get_quote_payload_from_supabase(quote_id, *, client) -> Optional[dict]`, `_decide_route(brief, confidential_flags) -> str`.

**Contexte vérifié avant d'écrire ce task** : `intake_sessions` ne stocke JAMAIS `email`/
`full_name` (confirmé par lecture de `submit_form`, lignes 248-346) — ces champs vivent
uniquement dans `quote_ownership.payload`, récupérables via `qo.get_quote_payload_from_supabase(quote_id, client=...)`, exactement le mécanisme déjà utilisé par `_send_intake_confirmation`.
Découverte importante en lisant le code existant : **aujourd'hui, seul `complete_routing`
(bouton « Passer cette étape ») envoie l'email de confirmation** — ni `agent_turn` (`close:
true`, la clôture NATURELLE d'une conversation), ni `_close_session_gracefully` (gateway LLM
down) ne l'envoient. Ce Task corrige ce trou en unifiant les 3 points de sortie sur
`_finalize_session`.

- [ ] **Step 1: Écrire les tests qui décrivent le nouveau comportement (email suspendu pour `meeting`)**

Modifier `backend/tests/test_unit_intake.py`. D'abord, **corriger** le test existant
`test_completion_sends_confirmation_email_best_effort` (ligne 546) qui utilisait la branche
`meeting` pour vérifier l'envoi d'email — cette branche n'envoie plus l'email à
`complete_routing` désormais, donc ce test doit basculer sur une branche qui envoie toujours
l'email immédiatement (`quote_48h`) :

```python
    def test_completion_sends_confirmation_email_best_effort(self, fake_client, monkeypatch):
        calls = []
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda *, to_email, subject, html_body, **kw: calls.append(
                {"to_email": to_email, "subject": subject, "html_body": html_body}
            ) or True,
        )
        sid = self._session_ready(
            fake_client,
            brief_overrides={
                "governance": "comite_direction",
                "stakes": {"budget_bracket": "1_10m", "exposure": "sectorielle"},
            },
        )
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert body["data"]["route"] == "quote_48h"
        assert len(calls) == 1
        assert calls[0]["to_email"] == "karim@banquepop.ma"  # cf. _valid_payload
```

Ensuite, **corriger** `test_completion_email_calcom_link_locks_email_and_name` (ligne 561) —
cette assertion portait sur le contenu de l'email de confirmation pour la branche `meeting`,
qui ne part plus à `complete_routing`. Remplacer ce test par une vérification que
`complete_routing` **ne** déclenche **plus** d'email pour `meeting` (l'assertion de contenu
équivalente est déplacée en Task 2, sur `confirm_calcom_booking`) :

```python
    def test_completion_skips_email_for_meeting_route(self, fake_client, monkeypatch):
        """Depuis ce Task, la branche meeting ne déclenche plus l'email à la
        clôture — il part désormais uniquement après confirm_calcom_booking
        (créneau réellement vérifié), cf. Task 2 de ce plan."""
        calls = []
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda **kw: calls.append(kw) or True,
        )
        sid = self._session_ready(fake_client, brief_overrides={"governance": "conseil_administration"})
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert body["data"]["route"] == "meeting"
        assert calls == []
```

Ajouter aussi une vérification directe du nouveau champ `calcom_link` dans la réponse de
`complete_routing` pour `meeting` :

```python
    def test_completion_returns_calcom_link_for_meeting(self, fake_client):
        sid = self._session_ready(fake_client, brief_overrides={"governance": "conseil_administration"})
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert body["data"]["route"] == "meeting"
        assert "calcom_link" in body["data"]
        assert body["data"]["calcom_link"].startswith("https://agenda.ai-mpower.com/")
        assert "email=karim%40banquepop.ma" in body["data"]["calcom_link"]
```

Enfin, dans `backend/tests/test_unit_intake_agent.py`, ajouter 2 tests dans
`TestAgentTurnHappyPath` couvrant le trou corrigé (email jamais envoyé aujourd'hui via
`agent_turn`) :

```python
    def test_close_true_sends_confirmation_email_for_non_meeting_route(self, fake_client, monkeypatch):
        """Trou corrigé par _finalize_session (Task 1 du plan US-IQ-02 frontend) :
        avant ce changement, agent_turn(close:true) ne déclenchait JAMAIS l'email
        de confirmation, contrairement à complete_routing."""
        calls = []
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda **kw: calls.append(kw) or True,
        )
        sid = _submitted_session(fake_client)  # governance par défaut = conseil_administration (_valid_brief)
        # Forcer une branche non-meeting pour ce test : budget/exposure self_service-eligible.
        fake_client.table("intake_sessions").update({
            "brief": {**svc._get_session(sid, client=fake_client)["brief"], "governance": "solo",
                      "stakes": {"budget_bracket": "1_10m", "exposure": "sectorielle"},
                      "deadline": {"date": "2099-01-01", "overdue": False}},
        }).eq("id", sid).execute()
        llm = _FakeLLM([{
            "message": "Merci, votre brief est transmis.", "insights": [],
            "confidential_flag": None, "escalation": None, "close": True,
        }])
        status, body = svc.agent_turn(sid, "Voilà, c'est tout.", client=fake_client, llm=llm)
        assert status == 200
        assert body["data"]["route"] == "quote_48h"
        assert len(calls) == 1

    def test_close_true_skips_email_for_meeting_route(self, fake_client, monkeypatch):
        calls = []
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda **kw: calls.append(kw) or True,
        )
        sid = _submitted_session(fake_client)  # governance par défaut = conseil_administration → meeting
        llm = _FakeLLM([{
            "message": "Merci, votre brief est transmis.", "insights": [],
            "confidential_flag": None, "escalation": None, "close": True,
        }])
        status, body = svc.agent_turn(sid, "Voilà, c'est tout.", client=fake_client, llm=llm)
        assert status == 200
        assert body["data"]["route"] == "meeting"
        assert "calcom_link" in body["data"]
        assert calls == []
```

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent pour la bonne raison**

Run: `cd backend && uv run pytest tests/test_unit_intake.py tests/test_unit_intake_agent.py -k "completion_sends_confirmation_email_best_effort or completion_skips_email_for_meeting_route or completion_returns_calcom_link_for_meeting or close_true_sends_confirmation_email_for_non_meeting_route or close_true_skips_email_for_meeting_route" -v`

Expected: `test_completion_sends_confirmation_email_best_effort` FAIL (route calculée n'est pas
`quote_48h` avant modif — en fait ce test passe déjà tel quel car c'est juste un changement de
scénario, donc il doit déjà PASSER puisqu'aucune logique n'a encore changé ; les 4 autres
doivent FAIL : `calcom_link` absent de `body["data"]`, `AttributeError`/`KeyError` ou assertion
`calls == []` qui échoue (l'email part encore aujourd'hui à `complete_routing` pour `meeting`,
donc `test_completion_skips_email_for_meeting_route` échoue avec `calls` non vide ; les 2 tests
`agent_turn` échouent sur `assert "calcom_link" in body["data"]` / `assert len(calls) == 1`).

- [ ] **Step 3: Ajouter les constantes et `_finalize_session` dans `intake_service.py`**

Insérer juste après `_close_session_gracefully` actuel (donc après la ligne 1032, avant
`_log_escalation`) — mais d'abord, modifier la signature et le corps de
`_close_session_gracefully` lui-même (voir Step 5). Insérer ce nouveau bloc juste AVANT la
définition actuelle de `_close_session_gracefully` (donc juste après la fermeture de
`agent_turn`, ligne 1006 `return 200, {"success": True, "data": data}`) :

```python
def _finalize_session(
    session: Dict[str, Any],
    brief: Dict[str, Any],
    confidential_flags: Optional[List[Any]],
    route: str,
    *,
    client: Any,
    llm: Any = None,
    attempt_llm: bool = True,
) -> Dict[str, Any]:
    """Construit le payload de clôture commun aux 3 points d'entrée qui
    terminent une session Intake (complete_routing, agent_turn en close,
    _close_session_gracefully) : calcom_link (branche meeting) ou
    package_recommendation (branche self_service, Task 4 de ce plan), et
    pilote l'envoi de l'email de confirmation (US-IQ-04) — jamais pour
    meeting, déplacé vers confirm_calcom_booking une fois le créneau
    réellement vérifié (Task 2 de ce plan)."""
    data: Dict[str, Any] = {}
    locale = session.get("locale") or "fr"

    if route == "meeting":
        payload = None
        quote_id = session.get("quote_id")
        if quote_id:
            try:
                payload = qo.get_quote_payload_from_supabase(quote_id, client=client)
            except Exception as exc:  # noqa: BLE001
                logger.error("_finalize_session: payload lookup failed for %s: %s", quote_id, exc.__class__.__name__)
        try:
            data["calcom_link"] = _build_calcom_booking_link(
                session["id"],
                locale,
                email=(payload or {}).get("email"),
                full_name=(payload or {}).get("full_name"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("_finalize_session: calcom link build failed: %s", exc.__class__.__name__)

    if route != "meeting":
        session_for_email = dict(session)
        session_for_email["route"] = route
        _send_intake_confirmation(session_for_email, client=client)

    return data
```

- [ ] **Step 4: Câbler `complete_routing` sur `_finalize_session`**

Utiliser Edit sur `backend/app/services/intake_service.py` :

```python
    updated_session = dict(session)
    updated_session.update(update_row)
    _send_intake_confirmation(updated_session, client=cli)

    return 200, {
        "success": True,
        "data": {
            "session_id": session_id,
            "state": "completed",
            "route": route,
        },
    }
```

remplacé par :

```python
    updated_session = dict(session)
    updated_session.update(update_row)
    extra_data = _finalize_session(updated_session, brief, session.get("confidential_flags"), route, client=cli)

    return 200, {
        "success": True,
        "data": {
            "session_id": session_id,
            "state": "completed",
            "route": route,
            **extra_data,
        },
    }
```

- [ ] **Step 5: Câbler `agent_turn` (branche `close:true`) et `_close_session_gracefully` sur `_finalize_session`**

Remplacer le bloc final d'`agent_turn` :

```python
    data: Dict[str, Any] = {
        "session_id": session_id,
        "state": update_row["state"],
        "agent_turns": new_turns,
        "message": raw_output["message"],
        "close": bool(raw_output.get("close")),
    }
    if update_row["state"] == "completed":
        data["route"] = update_row["route"]

    return 200, {"success": True, "data": data}
```

par :

```python
    data: Dict[str, Any] = {
        "session_id": session_id,
        "state": update_row["state"],
        "agent_turns": new_turns,
        "message": raw_output["message"],
        "close": bool(raw_output.get("close")),
    }
    if update_row["state"] == "completed":
        data["route"] = update_row["route"]
        closing_session = dict(session)
        closing_session.update(update_row)
        extra_data = _finalize_session(
            closing_session, brief, confidential_flags, update_row["route"],
            client=cli, llm=llm_client_obj,
        )
        data.update(extra_data)

    return 200, {"success": True, "data": data}
```

Puis remplacer sa signature et son corps entier :

```python
def _close_session_gracefully(
    session_id: str,
    brief: Dict[str, Any],
    confidential_flags: Optional[List[Any]],
    *,
    client: Any,
) -> Tuple[int, Dict[str, Any]]:
    """Repli si le gateway LLM échoue (timeout/erreur réseau) — la session
    est clôturée directement (state='completed', route calculée) plutôt
    que de laisser le worker HTTP planter ou le prospect bloqué (AC
    US-IQ-02, « pas de blocage du worker »)."""
    route = _decide_route(brief, confidential_flags)
    now_iso = datetime.now(timezone.utc).isoformat()
    update_row = {"state": "completed", "route": route, "completed_at": now_iso}
    try:
        client.table("intake_sessions").update(update_row).eq("id", session_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.error("agent_turn: graceful close failed to persist for %s: %s", session_id, exc.__class__.__name__)
        return 503, {"success": False, "error_code": "SUPABASE_UNAVAILABLE", "error": "Could not close the session."}
    return 200, {
        "success": True,
        "data": {"session_id": session_id, "state": "completed", "route": route, "agent_unavailable": True},
    }
```

par :

```python
def _close_session_gracefully(
    session: Dict[str, Any],
    brief: Dict[str, Any],
    confidential_flags: Optional[List[Any]],
    *,
    client: Any,
) -> Tuple[int, Dict[str, Any]]:
    """Repli si le gateway LLM échoue (timeout/erreur réseau) — la session
    est clôturée directement (state='completed', route calculée) plutôt
    que de laisser le worker HTTP planter ou le prospect bloqué (AC
    US-IQ-02, « pas de blocage du worker »). Le gateway étant DÉJÀ tombé,
    aucune 2e tentative LLM n'est faite pour la recommandation self-service
    (attempt_llm=False, repli déterministe immédiat, Task 4 de ce plan)."""
    session_id = session["id"]
    route = _decide_route(brief, confidential_flags)
    now_iso = datetime.now(timezone.utc).isoformat()
    update_row = {"state": "completed", "route": route, "completed_at": now_iso}
    try:
        client.table("intake_sessions").update(update_row).eq("id", session_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.error("agent_turn: graceful close failed to persist for %s: %s", session_id, exc.__class__.__name__)
        return 503, {"success": False, "error_code": "SUPABASE_UNAVAILABLE", "error": "Could not close the session."}

    closing_session = dict(session)
    closing_session.update(update_row)
    extra_data = _finalize_session(closing_session, brief, confidential_flags, route, client=client, attempt_llm=False)
    return 200, {
        "success": True,
        "data": {
            "session_id": session_id, "state": "completed", "route": route,
            "agent_unavailable": True, **extra_data,
        },
    }
```

Et mettre à jour son unique appelant (dans `agent_turn`, bloc `except` autour de
`llm_client_obj.chat_json(...)`) :

```python
        return _close_session_gracefully(session_id, brief, session.get("confidential_flags"), client=cli)
```

remplacé par :

```python
        return _close_session_gracefully(session, brief, session.get("confidential_flags"), client=cli)
```

- [ ] **Step 6: Lancer les tests ciblés puis la suite complète**

Run: `cd backend && uv run pytest tests/test_unit_intake.py tests/test_unit_intake_agent.py -v`
Expected: PASS (tous, y compris les 5 tests du Step 1).

Run: `cd backend && uv run pytest -m "not integration" -q`
Expected: PASS, 0 failure (dont les tests `TestConfirmCalcomBooking` déjà existants, qui
appellent `complete_routing` sur des sessions `meeting` sans jamais vérifier l'email — non
affectés).

Run: `cd backend && uv run ruff check .`
Expected: 0 erreur.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/intake_service.py backend/tests/test_unit_intake.py backend/tests/test_unit_intake_agent.py
git commit -m "$(cat <<'EOF'
fix(intake): _finalize_session — unifie la clôture de session, corrige l'email jamais envoyé via agent_turn

complete_routing, agent_turn(close:true) et _close_session_gracefully dupliquaient
la logique de clôture. Extraction d'un helper commun révèle et corrige un vrai
trou : seul complete_routing (bouton skip) envoyait l'email de confirmation
US-IQ-04 — la clôture NATURELLE d'une conversation (agent_turn close:true)
et le repli gateway-down ne l'envoyaient jamais. Branche meeting : l'email
n'est plus envoyé à la clôture (déplacé vers confirm_calcom_booking, Task 2),
mais calcom_link est désormais renvoyé au client pour affichage immédiat.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Fo4sC5bGsFC4RYoERoNen4
EOF
)"
```

---

## Task 2 : Backend — envoyer l'email de confirmation depuis `confirm_calcom_booking` (branche `meeting`)

**Files:**
- Modify: `backend/app/services/intake_service.py:1394-1437` (`confirm_calcom_booking`)
- Test: `backend/tests/test_unit_intake.py` (classe `TestConfirmCalcomBooking`)

**Interfaces:**
- Consumes: `_send_intake_confirmation(session: dict, *, client) -> None` (déjà existant, jamais levant).
- Produces: aucune nouvelle fonction — `confirm_calcom_booking` déclenche l'email en best-effort après succès de la vérification server-to-server (ADR-IQ-10), avant son `return 200`.

- [ ] **Step 1: Écrire le test qui décrit le nouveau comportement**

Ajouter dans `backend/tests/test_unit_intake.py`, classe `TestConfirmCalcomBooking` :

```python
    def test_confirmation_sends_email_with_locked_calcom_link(self, fake_client, monkeypatch):
        """Reprend l'assertion de contenu qui vivait avant Task 1/2 sur
        complete_routing (test_completion_email_calcom_link_locks_email_and_name,
        supprimé) — le timing a changé, pas le contenu attendu de l'email."""
        calls = []
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda *, to_email, subject, html_body, **kw: calls.append(
                {"to_email": to_email, "html_body": html_body}
            ) or True,
        )
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides={"governance": "conseil_administration"}), client=fake_client)
        svc.complete_routing(sid, client=fake_client)
        assert calls == []  # pas encore envoyé (Task 1)

        self._mock_calcom_booking(monkeypatch)
        status, _body = svc.confirm_calcom_booking(sid, "cal-booking-uid-xyz", client=fake_client)
        assert status == 200
        assert len(calls) == 1
        assert calls[0]["to_email"] == "karim@banquepop.ma"
        html_body = calls[0]["html_body"]
        assert "email=karim%40banquepop.ma" in html_body
        assert "name=Karim+Bensaid" in html_body

    def test_confirmation_email_failure_never_breaks_confirmation(self, fake_client, monkeypatch):
        """Best-effort — même contrat que _send_intake_confirmation partout
        ailleurs : une panne d'email ne doit jamais faire échouer la
        confirmation de réservation elle-même."""
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda **kw: (_ for _ in ()).throw(RuntimeError("resend down")),
        )
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides={"governance": "conseil_administration"}), client=fake_client)
        svc.complete_routing(sid, client=fake_client)
        self._mock_calcom_booking(monkeypatch)

        status, body = svc.confirm_calcom_booking(sid, "uid-1", client=fake_client)
        assert status == 200
        assert body["success"] is True

    def test_confirmation_failure_does_not_send_email(self, fake_client, monkeypatch):
        calls = []
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda **kw: calls.append(kw) or True,
        )
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides={"governance": "conseil_administration"}), client=fake_client)
        svc.complete_routing(sid, client=fake_client)
        self._mock_calcom_booking(monkeypatch, found=False)  # uid inconnu de Cal.com

        status, _body = svc.confirm_calcom_booking(sid, "attacker-invented-uid", client=fake_client)
        assert status == 404
        assert calls == []
```

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/test_unit_intake.py -k "test_confirmation_sends_email_with_locked_calcom_link or test_confirmation_email_failure_never_breaks_confirmation or test_confirmation_failure_does_not_send_email" -v`
Expected: `test_confirmation_sends_email_with_locked_calcom_link` FAIL (`assert len(calls) == 1` —
`calls` est vide, rien n'envoie encore l'email ici). Les 2 autres passent déjà trivialement
(rien à casser) — normal, elles servent de garde-fou de non-régression pour ce Task.

- [ ] **Step 3: Câbler l'envoi email dans `confirm_calcom_booking`**

Remplacer :

```python
    cli.table("intake_sessions").update({"calcom_booking_uid": booking_uid}).eq("id", session_id).execute()
    return 200, {"success": True, "data": {"session_id": session_id, "calcom_booking_uid": booking_uid}}
```

par :

```python
    cli.table("intake_sessions").update({"calcom_booking_uid": booking_uid}).eq("id", session_id).execute()

    updated_session = dict(session)
    updated_session["calcom_booking_uid"] = booking_uid
    _send_intake_confirmation(updated_session, client=cli)

    return 200, {"success": True, "data": {"session_id": session_id, "calcom_booking_uid": booking_uid}}
```

- [ ] **Step 4: Lancer les tests ciblés puis la suite complète**

Run: `cd backend && uv run pytest tests/test_unit_intake.py -v`
Expected: PASS (tous).

Run: `cd backend && uv run pytest -m "not integration" -q && cd backend && uv run ruff check .`
Expected: PASS, 0 erreur.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/intake_service.py backend/tests/test_unit_intake.py
git commit -m "$(cat <<'EOF'
feat(intake): envoie l'email de confirmation meeting depuis confirm_calcom_booking, pas avant

Suite logique de Task 1 : la branche meeting n'envoie plus l'email à la
clôture de l'agent (brief pas encore réservé) — il part désormais
uniquement après vérification server-to-server réussie du booking Cal.com
(ADR-IQ-10), regroupant confirmation email + réservation autour d'un seul
moment de vérité (décision Amine, session brainstorming 2026-07-12).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Fo4sC5bGsFC4RYoERoNen4
EOF
)"
```

---

## Task 3 : Backend — exposer `confidential_flags` dans chaque réponse `agent_turn`

**Files:**
- Modify: `backend/app/services/intake_service.py:996-1002` (bloc `data` d'`agent_turn`)
- Test: `backend/tests/test_unit_intake_agent.py`

**Interfaces:**
- Produces: `data["confidential_flags"]` — liste de `{"topic_label": str, "flagged_at": str}`, présente dans **chaque** réponse `agent_turn` (pas seulement à la clôture).

- [ ] **Step 1: Écrire les tests**

Ajouter dans `TestAgentTurnHappyPath` (`backend/tests/test_unit_intake_agent.py`) :

```python
    def test_confidential_flags_exposed_in_every_response(self, fake_client):
        sid = _submitted_session(fake_client)
        llm = _FakeLLM([{
            "message": "Je note ce point de côté — quelle est la prochaine étape ?",
            "insights": [], "confidential_flag": {"topic_label": "conflit avec un actionnaire"},
            "escalation": None, "close": False,
        }])
        status, body = svc.agent_turn(sid, "Entre nous, il y a un conflit.", client=fake_client, llm=llm)
        assert status == 200
        assert body["data"]["confidential_flags"] == [
            {"topic_label": "conflit avec un actionnaire", "flagged_at": body["data"]["confidential_flags"][0]["flagged_at"]}
        ]

    def test_confidential_flags_empty_list_when_none_flagged(self, fake_client):
        sid = _submitted_session(fake_client)
        llm = _FakeLLM([{
            "message": "D'accord, poursuivons.", "insights": [], "confidential_flag": None,
            "escalation": None, "close": False,
        }])
        status, body = svc.agent_turn(sid, "ok", client=fake_client, llm=llm)
        assert status == 200
        assert body["data"]["confidential_flags"] == []

    def test_confidential_flags_accumulate_across_turns(self, fake_client):
        sid = _submitted_session(fake_client)
        llm1 = _FakeLLM([{
            "message": "Je note ce point.", "insights": [],
            "confidential_flag": {"topic_label": "sujet A"}, "escalation": None, "close": False,
        }])
        svc.agent_turn(sid, "premier message sensible", client=fake_client, llm=llm1)

        llm2 = _FakeLLM([{
            "message": "Je note aussi ce point.", "insights": [],
            "confidential_flag": {"topic_label": "sujet B"}, "escalation": None, "close": False,
        }])
        status, body = svc.agent_turn(sid, "second message sensible", client=fake_client, llm=llm2)
        assert status == 200
        labels = [f["topic_label"] for f in body["data"]["confidential_flags"]]
        assert labels == ["sujet A", "sujet B"]
```

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/test_unit_intake_agent.py -k "confidential_flags_exposed or confidential_flags_empty or confidential_flags_accumulate" -v`
Expected: FAIL sur les 3 (`KeyError: 'confidential_flags'` — le champ n'existe pas encore dans `data`).

- [ ] **Step 3: Ajouter le champ dans le bloc `data` d'`agent_turn`**

Remplacer :

```python
    data: Dict[str, Any] = {
        "session_id": session_id,
        "state": update_row["state"],
        "agent_turns": new_turns,
        "message": raw_output["message"],
        "close": bool(raw_output.get("close")),
    }
```

par :

```python
    data: Dict[str, Any] = {
        "session_id": session_id,
        "state": update_row["state"],
        "agent_turns": new_turns,
        "message": raw_output["message"],
        "close": bool(raw_output.get("close")),
        "confidential_flags": confidential_flags,
    }
```

- [ ] **Step 4: Lancer les tests ciblés puis la suite complète**

Run: `cd backend && uv run pytest tests/test_unit_intake_agent.py -v`
Expected: PASS (tous).

Run: `cd backend && uv run pytest -m "not integration" -q && cd backend && uv run ruff check .`
Expected: PASS, 0 erreur.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/intake_service.py backend/tests/test_unit_intake_agent.py
git commit -m "$(cat <<'EOF'
feat(intake): expose confidential_flags dans chaque réponse agent_turn

Nécessaire pour la colonne « sujets verrouillés » de l'écran Assistant
frontend (US-IQ-02 frontend, Task 7) — le champ était déjà calculé
côté serveur pour le routage mais jamais renvoyé au client.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Fo4sC5bGsFC4RYoERoNen4
EOF
)"
```

---

## Task 4 : Backend — recommandation de package self-service

**Files:**
- Modify: `backend/app/services/intake_service.py` (nouvelles constantes + `_recommend_self_service_package`, extension de `_finalize_session`)
- Test: nouveau fichier `backend/tests/test_unit_intake_package_recommendation.py`

**Interfaces:**
- Produces: `_recommend_self_service_package(brief: dict, locale: str, llm: Any) -> Dict[str, str]` — retourne toujours `{"package_id": str, "rationale": str}`, jamais d'exception.
- Consumes: `create_intake_llm_client(timeout: float) -> LLMClient` (déjà existant), `llm.chat_json(messages, temperature=..., max_tokens=...) -> dict` (contrat déjà utilisé par `agent_turn`).
- Modifie le contrat de `_finalize_session` (Task 1) : la branche `self_service` remplit désormais `data["package_recommendation"]`.

- [ ] **Step 1: Écrire les tests**

Créer `backend/tests/test_unit_intake_package_recommendation.py` :

```python
"""Tests unitaires — recommandation de package self-service (US-IQ-02 frontend, Task 4).

Le client LLM est toujours un double en mémoire — aucun appel réseau réel.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services import intake_service as svc  # noqa: E402


class _FakeRecommendationLLM:
    def __init__(self, output: Dict[str, Any] | None = None, *, raises: bool = False):
        self._output = output
        self._raises = raises
        self.calls: List[Dict[str, Any]] = []

    def chat_json(self, messages, temperature=0.3, max_tokens=1024):
        self.calls.append({"messages": messages, "temperature": temperature, "max_tokens": max_tokens})
        if self._raises:
            raise RuntimeError("gateway down")
        return self._output


_BRIEF = {
    "decision": "Faut-il tester notre positionnement PMF avant la levée Série A ?",
    "options": ["Lever avant validation", "Valider le PMF d'abord"],
    "stakes": {"budget_bracket": "lt_1m", "exposure": "interne"},
}


class TestRecommendSelfServicePackage:
    def test_valid_recommendation_returned_as_is(self):
        llm = _FakeRecommendationLLM({"package_id": "pmf_discovery", "rationale": "Votre décision porte sur la validation PMF."})
        result = svc._recommend_self_service_package(_BRIEF, "fr", llm)
        assert result == {"package_id": "pmf_discovery", "rationale": "Votre décision porte sur la validation PMF."}
        assert len(llm.calls) == 1

    def test_invalid_package_id_falls_back(self):
        llm = _FakeRecommendationLLM({"package_id": "not_a_real_package", "rationale": "x"})
        result = svc._recommend_self_service_package(_BRIEF, "fr", llm)
        assert result["package_id"] == "crisis_drill_24h"
        assert result["rationale"] == ""

    def test_missing_rationale_falls_back(self):
        llm = _FakeRecommendationLLM({"package_id": "adcheck_lite"})
        result = svc._recommend_self_service_package(_BRIEF, "fr", llm)
        assert result["package_id"] == "crisis_drill_24h"

    def test_non_dict_output_falls_back(self):
        llm = _FakeRecommendationLLM("not a dict")
        result = svc._recommend_self_service_package(_BRIEF, "fr", llm)
        assert result["package_id"] == "crisis_drill_24h"

    def test_llm_exception_falls_back(self):
        llm = _FakeRecommendationLLM(raises=True)
        result = svc._recommend_self_service_package(_BRIEF, "fr", llm)
        assert result["package_id"] == "crisis_drill_24h"
        assert result["rationale"] == ""

    def test_no_llm_client_falls_back_without_calling_anything(self):
        result = svc._recommend_self_service_package(_BRIEF, "fr", None)
        assert result["package_id"] == "crisis_drill_24h"
        assert result["rationale"] == ""

    def test_prompt_lists_all_three_self_service_packages(self):
        llm = _FakeRecommendationLLM({"package_id": "crisis_drill_24h", "rationale": "x"})
        svc._recommend_self_service_package(_BRIEF, "fr", llm)
        system_content = llm.calls[0]["messages"][0]["content"]
        assert "pmf_discovery" in system_content
        assert "crisis_drill_24h" in system_content
        assert "adcheck_lite" in system_content

    def test_valid_package_ids_are_exactly_the_three_self_service_ones(self):
        assert svc._SELF_SERVICE_PACKAGES.keys() == {"pmf_discovery", "crisis_drill_24h", "adcheck_lite"}
```

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent**

Run: `cd backend && uv run pytest tests/test_unit_intake_package_recommendation.py -v`
Expected: FAIL — `AttributeError: module 'app.services.intake_service' has no attribute '_recommend_self_service_package'`.

- [ ] **Step 3: Implémenter `_recommend_self_service_package` et les constantes**

Insérer dans `backend/app/services/intake_service.py`, juste avant `def _finalize_session(` :

```python
_SELF_SERVICE_PACKAGES: Dict[str, str] = {
    "pmf_discovery": (
        "PMF Discovery (10k MAD) — validation de product-market fit avant une levée, "
        "cible fondateurs/investisseurs, 50 prospects-cible synthétiques testent la "
        "proposition de valeur sur 10 semaines."
    ),
    "crisis_drill_24h": (
        "Crisis Drill 24h (20k MAD) — stress-test d'une crise réputationnelle imminente, "
        "cible directions générales, 50 citoyens synthétiques réagissent heure par heure."
    ),
    "adcheck_lite": (
        "Adcheck Lite (15k MAD) — test de 2 concepts publicitaires avant achat media, "
        "cible directions marketing, verdict en 72h."
    ),
}
_SELF_SERVICE_PACKAGE_FALLBACK = "crisis_drill_24h"
_PACKAGE_RECOMMENDATION_TIMEOUT_SECONDS = 15.0
_PACKAGE_RECOMMENDATION_TEMPERATURE = 0.2
_PACKAGE_RECOMMENDATION_MAX_TOKENS = 256

_PACKAGE_RECOMMENDATION_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["package_id", "rationale"],
    "additionalProperties": False,
    "properties": {
        "package_id": {"type": "string", "enum": sorted(_SELF_SERVICE_PACKAGES)},
        "rationale": {"type": "string", "minLength": 1, "maxLength": 240},
    },
}


def _recommend_self_service_package(brief: Dict[str, Any], locale: str, llm: Any) -> Dict[str, str]:
    """Recommande l'un des 3 packages self-service à partir du brief —
    appel LLM best-effort (jamais bloquant) : toute erreur (gateway
    indisponible, sortie invalide, package_id hors liste) retombe sur le
    package `featured` du catalogue (`crisis_drill_24h`), sans rationale
    spécifique (design US-IQ-02 frontend, section « Recommandation de
    package self-service »)."""
    fallback = {"package_id": _SELF_SERVICE_PACKAGE_FALLBACK, "rationale": ""}
    if llm is None:
        return fallback

    catalogue = "\n".join(f"- {pid} : {desc}" for pid, desc in _SELF_SERVICE_PACKAGES.items())
    messages = [
        {
            "role": "system",
            "content": (
                "Tu recommandes UN SEUL package parmi ceux listés ci-dessous, à partir du "
                "brief d'un décideur. Réponds en JSON strict "
                '{"package_id": "<id exact>", "rationale": "<1 phrase, langue ' + locale + '>"}. '
                "Aucun texte hors de ce JSON.\n\nPackages disponibles :\n" + catalogue
            ),
        },
        {"role": "user", "content": json.dumps(brief, ensure_ascii=False)},
    ]
    try:
        raw_output = llm.chat_json(
            messages,
            temperature=_PACKAGE_RECOMMENDATION_TEMPERATURE,
            max_tokens=_PACKAGE_RECOMMENDATION_MAX_TOKENS,
        )
    except Exception as exc:  # noqa: BLE001 — best-effort, jamais bloquant
        logger.warning("_recommend_self_service_package: LLM call failed: %s", exc.__class__.__name__)
        return fallback

    if not isinstance(raw_output, dict):
        return fallback
    try:
        jsonschema.validate(raw_output, _PACKAGE_RECOMMENDATION_OUTPUT_SCHEMA)
    except jsonschema.ValidationError:
        return fallback

    return {"package_id": raw_output["package_id"], "rationale": raw_output["rationale"]}
```

- [ ] **Step 4: Lancer les tests ciblés du Step 1**

Run: `cd backend && uv run pytest tests/test_unit_intake_package_recommendation.py -v`
Expected: PASS (tous les 8).

- [ ] **Step 5: Écrire le test d'intégration `_finalize_session` ↔ recommandation**

Ajouter dans `backend/tests/test_unit_intake.py`, nouvelle classe après `TestCompleteRouting` :

```python
class TestFinalizeSessionSelfService:
    def test_complete_routing_returns_package_recommendation_for_self_service(self, fake_client, monkeypatch):
        monkeypatch.setattr(
            svc, "create_intake_llm_client",
            lambda **kw: _StubLLM({"package_id": "adcheck_lite", "rationale": "Test de concept publicitaire."}),
        )
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides={
            "governance": "solo",
            "deadline": {"date": _FAR_DATE, "overdue": False},
            "stakes": {"budget_bracket": "lt_1m", "exposure": "interne"},
        }), client=fake_client)
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert body["data"]["route"] == "self_service"
        assert body["data"]["package_recommendation"] == {
            "package_id": "adcheck_lite", "rationale": "Test de concept publicitaire.",
        }


class _StubLLM:
    def __init__(self, output):
        self._output = output

    def chat_json(self, messages, temperature=0.3, max_tokens=1024):
        return self._output
```

- [ ] **Step 6: Lancer ce test, vérifier qu'il échoue**

Run: `cd backend && uv run pytest tests/test_unit_intake.py -k test_complete_routing_returns_package_recommendation_for_self_service -v`
Expected: FAIL — `KeyError: 'package_recommendation'` (`_finalize_session` retourne encore `{}` pour `self_service`, cf. Task 1).

- [ ] **Step 7: Étendre `_finalize_session` avec la branche `self_service`**

Remplacer, dans `_finalize_session` :

```python
    data: Dict[str, Any] = {}
    locale = session.get("locale") or "fr"

    if route == "meeting":
```

par :

```python
    data: Dict[str, Any] = {}
    locale = session.get("locale") or "fr"

    if route == "self_service":
        llm_client_obj = llm
        if llm_client_obj is None and attempt_llm:
            try:
                llm_client_obj = create_intake_llm_client(timeout=_PACKAGE_RECOMMENDATION_TIMEOUT_SECONDS)
            except Exception as exc:  # noqa: BLE001
                logger.error("_finalize_session: LLM client creation failed: %s", exc.__class__.__name__)
                llm_client_obj = None
        data["package_recommendation"] = _recommend_self_service_package(brief, locale, llm_client_obj)

    if route == "meeting":
```

- [ ] **Step 8: Lancer les tests ciblés puis la suite complète**

Run: `cd backend && uv run pytest tests/test_unit_intake.py tests/test_unit_intake_agent.py tests/test_unit_intake_package_recommendation.py -v`
Expected: PASS (tous).

Run: `cd backend && uv run pytest -m "not integration" -q && cd backend && uv run ruff check .`
Expected: PASS, 0 erreur.

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/intake_service.py backend/tests/test_unit_intake.py backend/tests/test_unit_intake_package_recommendation.py
git commit -m "$(cat <<'EOF'
feat(intake): recommandation de package self-service par l'agent LLM

_finalize_session, branche self_service : un appel LLM léger (réutilise le
client agent déjà en boucle quand disponible) recommande l'un des 3
packages self-service (pmf_discovery/crisis_drill_24h/adcheck_lite) à
partir du brief, avec repli déterministe sur crisis_drill_24h (featured)
si le gateway est down ou la sortie invalide. Le frontend affiche cette
recommandation puis redirige vers /offres, tranché par le prospect
(décision Amine, session brainstorming 2026-07-12, option « hybride »).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Fo4sC5bGsFC4RYoERoNen4
EOF
)"
```

---

## Task 5 : i18n — nouvelles clés fr/en/ar

**Files:**
- Modify: `frontend/src/locales/fr.json:1893-1903` (`quote.step3`), `:1421-1495` (`errors`)
- Modify: `frontend/src/locales/en.json:1893-1903`, `:1421-1495` (mêmes offsets, structure identique)
- Modify: `frontend/src/locales/ar.json:1893-1903`, `:1421-1495` (mêmes offsets, structure identique)

**Interfaces:** aucune (données statiques, consommées par les Tasks 7/8/9 via `$t('quote.step3.assistant.*')` et `$t('errors.*')`).

- [ ] **Step 1: Ajouter `quote.step3.assistant` dans `fr.json`**

Dans `frontend/src/locales/fr.json`, remplacer :

```json
    "step3": {
      "successTitle": "Merci, nous avons reçu votre demande.",
      "successSubtitle": "Nous revenons vers vous sous 48 h ouvrées avec une proposition cadrée.",
      "calcomConfirmedTitle": "Votre entretien est confirmé.",
      "calcomConfirmedSubtitle": "Nous arrivons préparés — vous recevrez une invitation par email avec le lien de visioconférence.",
      "quoteIdLabel": "Référence",
      "errorTitle": "Envoi impossible",
      "errorFallback": "Une erreur réseau est survenue. Réessayez dans un instant.",
      "backToOffers": "Retour aux offres",
      "tryAgain": "Réessayer"
    },
```

par :

```json
    "step3": {
      "successTitle": "Merci, nous avons reçu votre demande.",
      "successSubtitle": "Nous revenons vers vous sous 48 h ouvrées avec une proposition cadrée.",
      "calcomConfirmedTitle": "Votre entretien est confirmé.",
      "calcomConfirmedSubtitle": "Nous arrivons préparés — vous recevrez une invitation par email avec le lien de visioconférence.",
      "quoteIdLabel": "Référence",
      "errorTitle": "Envoi impossible",
      "errorFallback": "Une erreur réseau est survenue. Réessayez dans un instant.",
      "backToOffers": "Retour aux offres",
      "tryAgain": "Réessayer",
      "assistant": {
        "banner": "Vous échangez avec une IA",
        "you": "Vous",
        "assistant": "Bassira",
        "placeholder": "Votre réponse…",
        "send": "Envoyer",
        "sending": "Envoi…",
        "thinking": "Bassira réfléchit…",
        "briefSummaryTitle": "Votre brief",
        "lockedTopicsTitle": "Réservé à l'échange de vive voix",
        "skipButton": "Passer cette étape",
        "recommendedPackage": "Package recommandé : {package}",
        "viewMeeting": "Voir mon créneau"
      }
    },
```

- [ ] **Step 2: Ajouter les 5 clés `errors.*` manquantes dans `fr.json`**

Dans `frontend/src/locales/fr.json`, remplacer la ligne :

```json
    "SESSION_NOT_FOUND": "Votre session a expiré. Merci de recommencer le parcours.",
```

par :

```json
    "SESSION_NOT_FOUND": "Votre session a expiré. Merci de recommencer le parcours.",
    "AGENT_BUDGET_EXHAUSTED": "Cette conversation a atteint sa limite. Cliquez sur « Passer cette étape » pour continuer.",
    "AGENT_INVALID_OUTPUT": "L'assistant a rencontré un problème. Réessayez votre message.",
    "INVALID_STATE": "Cette étape est déjà validée.",
    "BRIEF_MISSING": "Le brief de cette session est introuvable. Merci de recommencer le parcours.",
    "SUPABASE_UNAVAILABLE": "Service temporairement indisponible. Réessayez dans un instant.",
```

- [ ] **Step 3: Même structure dans `en.json`**

Remplacer :

```json
    "step3": {
      "successTitle": "Thanks · we've received your case.",
      "successSubtitle": "We'll get back to you within 48 business hours with a scoped proposal.",
      "calcomConfirmedTitle": "Your meeting is confirmed.",
      "calcomConfirmedSubtitle": "We arrive prepared — you'll receive an email invite with the video call link.",
      "quoteIdLabel": "Reference",
      "errorTitle": "Submission failed",
      "errorFallback": "A network error occurred. Please retry in a moment.",
      "backToOffers": "Back to offers",
      "tryAgain": "Retry"
    },
```

par :

```json
    "step3": {
      "successTitle": "Thanks · we've received your case.",
      "successSubtitle": "We'll get back to you within 48 business hours with a scoped proposal.",
      "calcomConfirmedTitle": "Your meeting is confirmed.",
      "calcomConfirmedSubtitle": "We arrive prepared — you'll receive an email invite with the video call link.",
      "quoteIdLabel": "Reference",
      "errorTitle": "Submission failed",
      "errorFallback": "A network error occurred. Please retry in a moment.",
      "backToOffers": "Back to offers",
      "tryAgain": "Retry",
      "assistant": {
        "banner": "You're chatting with an AI",
        "you": "You",
        "assistant": "Bassira",
        "placeholder": "Your answer…",
        "send": "Send",
        "sending": "Sending…",
        "thinking": "Bassira is thinking…",
        "briefSummaryTitle": "Your brief",
        "lockedTopicsTitle": "Reserved for a live conversation",
        "skipButton": "Skip this step",
        "recommendedPackage": "Recommended package: {package}",
        "viewMeeting": "View my slot"
      }
    },
```

Et remplacer, dans `en.json` :

```json
    "SESSION_NOT_FOUND": "Your session has expired. Please restart the process.",
```

par (vérifier la formulation exacte existante avant remplacement — si différente, garder la
ligne existante et seulement ajouter les 5 nouvelles à sa suite) :

```json
    "SESSION_NOT_FOUND": "Your session has expired. Please restart the process.",
    "AGENT_BUDGET_EXHAUSTED": "This conversation has reached its limit. Click \"Skip this step\" to continue.",
    "AGENT_INVALID_OUTPUT": "The assistant hit a snag. Please retry your message.",
    "INVALID_STATE": "This step has already been completed.",
    "BRIEF_MISSING": "This session's brief could not be found. Please restart the process.",
    "SUPABASE_UNAVAILABLE": "Service temporarily unavailable. Please retry in a moment.",
```

- [ ] **Step 4: Même structure dans `ar.json`**

Remplacer :

```json
    "step3": {
      "successTitle": "شكرًا · لقد استلمنا طلبكم.",
      "successSubtitle": "سنعود إليكم خلال 48 ساعة عمل بمقترح مُؤطَّر.",
      "calcomConfirmedTitle": "موعدكم مؤكَّد.",
      "calcomConfirmedSubtitle": "نصل مستعدين — ستتلقّون دعوة عبر البريد الإلكتروني تتضمّن رابط مكالمة الفيديو.",
      "quoteIdLabel": "المرجع",
      "errorTitle": "تعذّر الإرسال",
      "errorFallback": "حدث خطأ في الشبكة. حاولوا بعد لحظات.",
      "backToOffers": "العودة إلى العروض",
      "tryAgain": "إعادة المحاولة"
    },
```

par :

```json
    "step3": {
      "successTitle": "شكرًا · لقد استلمنا طلبكم.",
      "successSubtitle": "سنعود إليكم خلال 48 ساعة عمل بمقترح مُؤطَّر.",
      "calcomConfirmedTitle": "موعدكم مؤكَّد.",
      "calcomConfirmedSubtitle": "نصل مستعدين — ستتلقّون دعوة عبر البريد الإلكتروني تتضمّن رابط مكالمة الفيديو.",
      "quoteIdLabel": "المرجع",
      "errorTitle": "تعذّر الإرسال",
      "errorFallback": "حدث خطأ في الشبكة. حاولوا بعد لحظات.",
      "backToOffers": "العودة إلى العروض",
      "tryAgain": "إعادة المحاولة",
      "assistant": {
        "banner": "أنت تتحاور مع ذكاء اصطناعي",
        "you": "أنت",
        "assistant": "بصيرة",
        "placeholder": "إجابتك…",
        "send": "إرسال",
        "sending": "جارٍ الإرسال…",
        "thinking": "بصيرة تفكّر…",
        "briefSummaryTitle": "ملفكم",
        "lockedTopicsTitle": "مخصّص للحوار المباشر",
        "skipButton": "تخطَّ هذه الخطوة",
        "recommendedPackage": "الباقة الموصى بها: {package}",
        "viewMeeting": "عرض موعدي"
      }
    },
```

Et ajouter les 5 clés `errors.*` (même emplacement relatif que fr/en) :

```json
    "AGENT_BUDGET_EXHAUSTED": "بلغت هذه المحادثة حدّها الأقصى. اضغط على «تخطَّ هذه الخطوة» للمتابعة.",
    "AGENT_INVALID_OUTPUT": "واجه المساعد مشكلة. أعد إرسال رسالتك.",
    "INVALID_STATE": "هذه الخطوة مُثبَّتة بالفعل.",
    "BRIEF_MISSING": "تعذّر العثور على ملف هذه الجلسة. يُرجى إعادة بدء المسار.",
    "SUPABASE_UNAVAILABLE": "الخدمة غير متاحة مؤقتًا. أعد المحاولة بعد لحظات.",
```

- [ ] **Step 5: Vérifier la validité JSON des 3 fichiers**

Run: `cd frontend && node -e "JSON.parse(require('fs').readFileSync('src/locales/fr.json','utf8')); JSON.parse(require('fs').readFileSync('src/locales/en.json','utf8')); JSON.parse(require('fs').readFileSync('src/locales/ar.json','utf8')); console.log('OK')"`
Expected: `OK` (aucune `SyntaxError`).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/locales/fr.json frontend/src/locales/en.json frontend/src/locales/ar.json
git commit -m "$(cat <<'EOF'
feat(i18n): clés quote.step3.assistant.* + errors.* pour l'écran Assistant (US-IQ-02 frontend)

Parité stricte fr/en/ar (ADR-008), même commit.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Fo4sC5bGsFC4RYoERoNen4
EOF
)"
```

---

## Task 6 : Frontend — `frontend/src/api/intake.js`

**Files:**
- Modify: `frontend/src/api/intake.js`

**Interfaces:**
- Produces: `postAgentTurn(sessionId: string, message: string) -> Promise<{success: true, data: {session_id, state, agent_turns, message, close, confidential_flags, route?, calcom_link?, package_recommendation?}}>`, `completeIntakeSession(sessionId: string) -> Promise<{success: true, data: {session_id, state, route, calcom_link?, package_recommendation?}}>`.

- [ ] **Step 1: Ajouter les 2 fonctions**

Ajouter à la fin de `frontend/src/api/intake.js` :

```js

/**
 * Un tour de l'agent conversationnel de qualification (étape B, US-IQ-02).
 *
 * @param {string} sessionId
 * @param {string} message — texte du décideur (non vide, y compris l'amorce
 *   synthétique du montage de IntakeAgentPanel.vue)
 * @returns {Promise<{success:true, data:{session_id, state, agent_turns,
 *   message, close, confidential_flags, route?, calcom_link?,
 *   package_recommendation?}}>}
 */
export const postAgentTurn = (sessionId, message) => {
  return service.post(`/api/intake/session/${sessionId}/agent/turn`, { message })
}

/**
 * Clôture directement la session sans passer par le chat (bouton
 * « Passer cette étape », US-IQ-02 frontend).
 *
 * @param {string} sessionId
 * @returns {Promise<{success:true, data:{session_id, state, route,
 *   calcom_link?, package_recommendation?}}>}
 */
export const completeIntakeSession = (sessionId) => {
  return service.post(`/api/intake/session/${sessionId}/complete`, {})
}
```

- [ ] **Step 2: Vérifier que le build passe (pas de test unitaire dédié sur ce fichier — cohérent avec `startIntakeSession`/`submitIntakeForm` déjà non testés isolément, couverts par l'E2E)**

Run: `cd frontend && npm run build`
Expected: build réussi, 0 erreur.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/intake.js
git commit -m "$(cat <<'EOF'
feat(intake): postAgentTurn + completeIntakeSession dans l'API frontend

Étend frontend/src/api/intake.js (jusqu'ici startIntakeSession/
submitIntakeForm seulement) pour appeler les 2 endpoints backend déjà
existants et déployés (POST .../agent/turn, POST .../complete) — jamais
appelés depuis le frontend jusqu'ici (cf. découverte critique, passation
2026-07-12).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Fo4sC5bGsFC4RYoERoNen4
EOF
)"
```

---

## Task 7 : Frontend — composant `IntakeAgentPanel.vue`

**Files:**
- Create: `frontend/src/components/IntakeAgentPanel.vue`

**Interfaces:**
- Consumes: `postAgentTurn(sessionId, message)`, `completeIntakeSession(sessionId)` (Task 6) ; `formatApiError(err, t)` (`frontend/src/utils/error-handler.js`, déjà existant).
- Props: `sessionId: string` (requis), `brief: object` (requis, brief A1-A8 déjà soumis), `locale: string` (défaut `'fr'`).
- Emits: `closed` avec payload `{ route: string, calcomLink: string|null, packageRecommendation: {package_id, rationale}|null }`.

- [ ] **Step 1: Créer le composant**

```vue
<template>
  <!--
    IntakeAgentPanel (US-IQ-02 frontend) — écran Assistant inline (PAS un
    panneau coulissant, contrairement à ReportChatPanel dont les classes
    CSS de base sont réutilisées). Bandeau IA permanent + chat + colonne
    latérale (brief live + sujets verrouillés) + bouton skip, conforme au
    prompt Stitch §10.2 (docs/intake/10-execution-prompts.md:83-104).
  -->
  <div class="iap-root">
    <div class="iap-banner">
      <span class="material-symbols-outlined iap-banner-icon" aria-hidden="true">smart_toy</span>
      <span>{{ $t('quote.step3.assistant.banner') }}</span>
    </div>

    <div class="iap-layout">
      <section class="iap-chat" aria-label="Assistant">
        <div ref="scrollEl" class="iap-messages">
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="iap-message"
            :class="`is-${msg.role}`"
          >
            <span class="iap-message-role">
              {{ msg.role === 'user' ? $t('quote.step3.assistant.you') : $t('quote.step3.assistant.assistant') }}
            </span>
            <div class="iap-message-bubble">{{ msg.content }}</div>
          </div>

          <div v-if="isSending" class="iap-message is-assistant">
            <span class="iap-message-role">{{ $t('quote.step3.assistant.assistant') }}</span>
            <div class="iap-message-bubble is-thinking">
              <span class="iap-thinking-dot"></span>
              <span class="iap-thinking-dot"></span>
              <span class="iap-thinking-dot"></span>
              <span class="iap-thinking-text">{{ $t('quote.step3.assistant.thinking') }}</span>
            </div>
          </div>

          <div v-if="errorMsg" class="iap-error" role="alert">{{ errorMsg }}</div>
        </div>

        <form class="iap-input-row" @submit.prevent="onSubmit">
          <textarea
            v-model="draft"
            class="iap-textarea"
            rows="2"
            :placeholder="$t('quote.step3.assistant.placeholder')"
            :disabled="isSending || closed"
            @keydown.enter.exact.prevent="onSubmit"
          ></textarea>
          <button
            type="submit"
            class="iap-send-btn"
            :disabled="isSending || !draft.trim() || closed"
          >
            {{ isSending ? $t('quote.step3.assistant.sending') : $t('quote.step3.assistant.send') }}
          </button>
        </form>

        <button
          type="button"
          class="iap-skip-btn"
          :disabled="isSending || closed"
          @click="onSkip"
        >
          {{ $t('quote.step3.assistant.skipButton') }}
        </button>
      </section>

      <aside class="iap-sidebar" aria-label="Brief">
        <div class="iap-sidebar-block">
          <h3 class="iap-sidebar-title">{{ $t('quote.step3.assistant.briefSummaryTitle') }}</h3>
          <ul class="iap-brief-list">
            <li v-for="item in briefSummaryItems" :key="item.label">
              <strong>{{ item.label }}</strong> — {{ item.value }}
            </li>
          </ul>
        </div>

        <div v-if="lockedTopics.length > 0" class="iap-sidebar-block">
          <h3 class="iap-sidebar-title">{{ $t('quote.step3.assistant.lockedTopicsTitle') }}</h3>
          <ul class="iap-locked-list">
            <li v-for="(topic, idx) in lockedTopics" :key="idx">
              <span class="material-symbols-outlined iap-lock-icon" aria-hidden="true">lock</span>
              {{ topic.topic_label }}
            </li>
          </ul>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { postAgentTurn, completeIntakeSession } from '../api/intake'
import { formatApiError } from '../utils/error-handler'

const props = defineProps({
  sessionId: { type: String, required: true },
  brief: { type: Object, required: true },
  locale: { type: String, default: 'fr' },
})

const emit = defineEmits(['closed'])

const { t } = useI18n()

const messages = ref([])
const draft = ref('')
const isSending = ref(false)
const errorMsg = ref('')
const closed = ref(false)
const lockedTopics = ref([])
const scrollEl = ref(null)

const _AMORCE_BY_LOCALE = {
  fr: "Je suis prêt(e) à échanger sur mon brief.",
  en: "I'm ready to talk through my brief.",
  ar: "أنا مستعدّ للحديث عن ملفي.",
}

const briefSummaryItems = computed(() => {
  const b = props.brief || {}
  const items = []
  if (b.decision) items.push({ label: t('quote.temps1.a1.label'), value: b.decision })
  if (Array.isArray(b.options) && b.options.length > 0) {
    items.push({ label: t('quote.temps1.a2.label'), value: b.options.join(' / ') })
  }
  if (b.deadline && b.deadline.date) {
    items.push({ label: t('quote.temps1.a3.deadlineLabel'), value: b.deadline.date })
  }
  if (b.stakes && b.stakes.budget_bracket) {
    items.push({
      label: t('quote.temps3.a6.budgetLabel'),
      value: t(`quote.temps3.a6.budget.${b.stakes.budget_bracket}`),
    })
  }
  return items
})

const scrollToBottom = () => {
  nextTick(() => {
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  })
}

const applyTurnResponse = (data) => {
  messages.value.push({ role: 'assistant', content: data.message })
  lockedTopics.value = data.confidential_flags || []
  scrollToBottom()
  if (data.close) {
    closed.value = true
    emit('closed', {
      route: data.route,
      calcomLink: data.calcom_link || null,
      packageRecommendation: data.package_recommendation || null,
    })
  }
}

const sendTurn = async (text) => {
  errorMsg.value = ''
  isSending.value = true
  try {
    const res = await postAgentTurn(props.sessionId, text)
    if (res?.data?.agent_unavailable) {
      closed.value = true
      emit('closed', {
        route: res.data.route,
        calcomLink: res.data.calcom_link || null,
        packageRecommendation: res.data.package_recommendation || null,
      })
      return
    }
    applyTurnResponse(res.data)
  } catch (err) {
    errorMsg.value = formatApiError(err, t)
  } finally {
    isSending.value = false
  }
}

const onSubmit = async () => {
  const text = draft.value.trim()
  if (!text || isSending.value || closed.value) return
  messages.value.push({ role: 'user', content: text })
  draft.value = ''
  scrollToBottom()
  await sendTurn(text)
}

const onSkip = async () => {
  if (isSending.value || closed.value) return
  isSending.value = true
  errorMsg.value = ''
  try {
    const res = await completeIntakeSession(props.sessionId)
    closed.value = true
    emit('closed', {
      route: res.data.route,
      calcomLink: res.data.calcom_link || null,
      packageRecommendation: res.data.package_recommendation || null,
    })
  } catch (err) {
    errorMsg.value = formatApiError(err, t)
  } finally {
    isSending.value = false
  }
}

onMounted(() => {
  const amorce = _AMORCE_BY_LOCALE[props.locale] || _AMORCE_BY_LOCALE.fr
  sendTurn(amorce)
})
</script>

<style scoped>
.iap-root {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-md);
}

.iap-banner {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--wi-secondary-container);
  color: var(--wi-on-surface-variant);
  padding: 8px 14px;
  border-radius: var(--wi-radius-md);
  font-size: 12px;
  font-weight: 600;
  align-self: flex-start;
}
.iap-banner-icon {
  font-size: 16px !important;
}

.iap-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--wi-space-md);
}
@media (min-width: 720px) {
  .iap-layout {
    grid-template-columns: 1fr 320px;
  }
}

.iap-chat {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
  min-width: 0;
}

.iap-messages {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
  max-height: 420px;
  overflow-y: auto;
  padding: var(--wi-space-sm);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  background: var(--wi-bg);
}

.iap-message {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.iap-message.is-user {
  align-self: flex-end;
  max-width: 85%;
}
.iap-message.is-assistant {
  align-self: flex-start;
  max-width: 95%;
}

.iap-message-role {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--wi-outline);
}

.iap-message-bubble {
  padding: 10px 12px;
  border-radius: var(--wi-radius-card);
  font-size: 13px;
  line-height: 1.55;
  word-wrap: break-word;
}
.iap-message.is-user .iap-message-bubble {
  background: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
}
.iap-message.is-assistant .iap-message-bubble {
  background: var(--wi-surface);
  color: var(--wi-on-surface);
  border: 1px solid var(--wi-outline-variant);
}

.iap-message-bubble.is-thinking {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--wi-on-surface-variant);
}
.iap-thinking-dot {
  width: 5px;
  height: 5px;
  background: var(--wi-on-primary-container);
  border-radius: 50%;
  animation: iap-bounce 1s ease-in-out infinite;
}
.iap-thinking-dot:nth-child(2) { animation-delay: 0.15s; }
.iap-thinking-dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes iap-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.iap-error {
  background: var(--wi-error-container, var(--wi-surface));
  color: var(--wi-error);
  border: 1px solid var(--wi-error);
  padding: 8px 10px;
  border-radius: var(--wi-radius-sm);
  font-size: 12px;
}

.iap-input-row {
  display: flex;
  align-items: flex-end;
  gap: var(--wi-space-sm);
}
.iap-textarea {
  flex: 1;
  resize: none;
  min-height: 44px;
  max-height: 120px;
  padding: 8px 10px;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-sm);
  font-size: 13px;
  line-height: 1.5;
  color: var(--wi-on-surface);
  background: var(--wi-bg);
}
.iap-textarea:disabled { opacity: 0.6; }

.iap-send-btn {
  padding: 8px 14px;
  border: 0;
  border-radius: var(--wi-radius-sm);
  background: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.iap-send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.iap-skip-btn {
  align-self: flex-start;
  background: transparent;
  border: 1.5px solid var(--wi-outline-variant);
  color: var(--wi-on-surface-variant);
  font-size: 13px;
  font-weight: 600;
  padding: 10px 18px;
  border-radius: var(--wi-radius-interactive);
  cursor: pointer;
}
.iap-skip-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.iap-sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-md);
}
.iap-sidebar-block {
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-sm);
  background: var(--wi-surface);
}
.iap-sidebar-title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--wi-on-surface-variant);
  margin: 0 0 8px 0;
}
.iap-brief-list,
.iap-locked-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
  color: var(--wi-on-surface);
}
.iap-locked-list li {
  display: flex;
  align-items: center;
  gap: 6px;
}
.iap-lock-icon {
  font-size: 14px !important;
  color: var(--wi-outline);
}
</style>
```

- [ ] **Step 2: Vérifier le build**

Run: `cd frontend && npm run build`
Expected: build réussi, 0 erreur (composant pas encore consommé — vérifie juste que le SFC compile).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/IntakeAgentPanel.vue
git commit -m "$(cat <<'EOF'
feat(intake): composant IntakeAgentPanel.vue — écran Assistant conforme au prompt Stitch §10.2

Chat inline (base CSS ReportChatPanel adaptée en layout non-coulissant) +
bandeau IA permanent + colonne brief live/sujets verrouillés + bouton
« Passer cette étape ». Amorce automatique au montage (agent_turn avec
message synthétique, jamais affiché). Gère le repli agent_unavailable
(gateway LLM down) comme une clôture normale.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Fo4sC5bGsFC4RYoERoNen4
EOF
)"
```

---

## Task 8 : Frontend — câblage `QuoteView.vue` (renumérotation + montage + clôture)

**Files:**
- Modify: `frontend/src/views/QuoteView.vue`

**Interfaces:**
- Consumes: `IntakeAgentPanel.vue` (Task 7, props `session-id`/`brief`/`locale`, event `closed`).

- [ ] **Step 1: Importer le composant et étendre l'état local**

Remplacer :

```js
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { startIntakeSession, submitIntakeForm } from '../api/intake'
import { formatApiError } from '../utils/error-handler'
```

par :

```js
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { startIntakeSession, submitIntakeForm } from '../api/intake'
import { formatApiError } from '../utils/error-handler'
import IntakeAgentPanel from '../components/IntakeAgentPanel.vue'
```

Remplacer :

```js
const currentStep = ref(1)
// Retour depuis le redirect de succès Cal.com (US-IQ-04, branche entretien)
// — /devis?calcom_confirmed=1 saute directement à l'écran de confirmation
// au lieu de réafficher le formulaire A1-A8 déjà soumis.
const calcomConfirmed = ref(route.query.calcom_confirmed === '1')
if (calcomConfirmed.value) currentStep.value = 4
```

par :

```js
const currentStep = ref(1)
// Retour depuis le redirect de succès Cal.com (US-IQ-04, branche entretien)
// — /devis?calcom_confirmed=1 saute directement à l'écran de confirmation
// (étape 5) au lieu de réafficher le formulaire A1-A8 déjà soumis.
const calcomConfirmed = ref(route.query.calcom_confirmed === '1')
if (calcomConfirmed.value) currentStep.value = 5

// Étape 4 (écran Assistant, US-IQ-02 frontend) — session/brief conservés
// en mémoire depuis submit() pour alimenter IntakeAgentPanel sans appel
// réseau supplémentaire.
const agentSessionId = ref('')
const agentBrief = ref(null)
const agentClosePayload = ref(null) // { route, calcomLink, packageRecommendation }
```

- [ ] **Step 2: Adapter `submit()` — brief lifté hors de la fonction, saut vers l'étape 4**

Remplacer :

```js
async function submit() {
  a7Touched.value = true
  if (!temps3Valid.value || submitting.value) return
  submitting.value = true
  submitError.value = null

  const brief = {
    decision: form.a1_decision.trim(),
    options: form.a2_options.map((o) => o.trim()).filter(Boolean),
    deadline: { date: form.a3_deadline_date || null, overdue: form.a3_overdue },
    governance: form.a3_governance || null,
    past_method: form.a4_past_method,
    past_gap: form.a5_past_gap.trim() || null,
    stakes:
      form.a6_budget_bracket && form.a6_exposure
        ? {
            budget_bracket: form.a6_budget_bracket,
            jobs: form.a6_jobs !== '' && form.a6_jobs !== null ? Number(form.a6_jobs) : null,
            exposure: form.a6_exposure,
          }
        : null,
    geo: form.a7_countries.map((c) => ({ country: c, segment: form.a7_segment.trim() })),
    data_assets: form.a8_data_assets,
  }

  const payload = {
    full_name: form.full_name.trim(),
    email: form.email.trim(),
    company: form.company.trim(),
    consent_rgpd: form.consent_rgpd,
    locale: locale.value || 'fr',
    brief,
  }
  if (form.role.trim()) payload.role = form.role.trim()

  try {
    const sessionRes = await startIntakeSession({ locale: locale.value || 'fr' })
    const sessionId = sessionRes?.data?.session_id
    const formRes = await submitIntakeForm(sessionId, payload)
    quoteId.value = formRes?.data?.quote_id || ''
    submitError.value = null
    currentStep.value = 4
  } catch (err) {
    const localised = formatApiError(err, t)
    submitError.value = localised || t('quote.step3.errorFallback')
    currentStep.value = 4
  } finally {
    submitting.value = false
  }
}
```

par :

```js
async function submit() {
  a7Touched.value = true
  if (!temps3Valid.value || submitting.value) return
  submitting.value = true
  submitError.value = null

  const brief = {
    decision: form.a1_decision.trim(),
    options: form.a2_options.map((o) => o.trim()).filter(Boolean),
    deadline: { date: form.a3_deadline_date || null, overdue: form.a3_overdue },
    governance: form.a3_governance || null,
    past_method: form.a4_past_method,
    past_gap: form.a5_past_gap.trim() || null,
    stakes:
      form.a6_budget_bracket && form.a6_exposure
        ? {
            budget_bracket: form.a6_budget_bracket,
            jobs: form.a6_jobs !== '' && form.a6_jobs !== null ? Number(form.a6_jobs) : null,
            exposure: form.a6_exposure,
          }
        : null,
    geo: form.a7_countries.map((c) => ({ country: c, segment: form.a7_segment.trim() })),
    data_assets: form.a8_data_assets,
  }

  const payload = {
    full_name: form.full_name.trim(),
    email: form.email.trim(),
    company: form.company.trim(),
    consent_rgpd: form.consent_rgpd,
    locale: locale.value || 'fr',
    brief,
  }
  if (form.role.trim()) payload.role = form.role.trim()

  try {
    const sessionRes = await startIntakeSession({ locale: locale.value || 'fr' })
    const sessionId = sessionRes?.data?.session_id
    const formRes = await submitIntakeForm(sessionId, payload)
    quoteId.value = formRes?.data?.quote_id || ''
    submitError.value = null
    agentSessionId.value = sessionId
    agentBrief.value = brief
    currentStep.value = 4
  } catch (err) {
    const localised = formatApiError(err, t)
    submitError.value = localised || t('quote.step3.errorFallback')
    currentStep.value = 5
  } finally {
    submitting.value = false
  }
}

function onAgentClosed(payload) {
  agentClosePayload.value = payload
  currentStep.value = 5
}
```

- [ ] **Step 3: Template — nouvelle étape 4 (Assistant), renumérotation de l'ancienne étape 4 → 5**

Remplacer :

```html
        <!-- ───── Confirmation (succès / erreur) ───── -->
        <div v-else-if="currentStep === 4" class="quote-step-content">
```

par :

```html
        <!-- ───── Étape 4 — Assistant (US-IQ-02 frontend) ───── -->
        <div v-else-if="currentStep === 4" class="quote-step-content">
          <IntakeAgentPanel
            :session-id="agentSessionId"
            :brief="agentBrief"
            :locale="locale"
            @closed="onAgentClosed"
          />
        </div>

        <!-- ───── Étape 5 — Confirmation (succès / erreur) ───── -->
        <div v-else-if="currentStep === 5" class="quote-step-content">
```

Puis, dans ce même bloc de clôture, ajouter une branche `agentClosePayload` AVANT la branche
`submitError === null` existante (celle-ci reste en repli pour un cas déjà couvert — soumission
réussie sans jamais visiter l'Assistant, qui ne devrait plus arriver, mais reste un filet de
sécurité). Remplacer :

```html
          <template v-if="calcomConfirmed">
            <div class="quote-success">
              <div class="quote-success-icon">
                <span class="material-symbols-outlined" aria-hidden="true">event_available</span>
              </div>
              <h2 class="quote-step-title">{{ $t('quote.step3.calcomConfirmedTitle') }}</h2>
              <p class="quote-success-sub">{{ $t('quote.step3.calcomConfirmedSubtitle') }}</p>
              <router-link :to="{ name: 'Offers' }" class="quote-cta quote-cta--inline">
                {{ $t('quote.step3.backToOffers') }}
              </router-link>
            </div>
          </template>
          <template v-else-if="submitError === null">
```

par :

```html
          <template v-if="calcomConfirmed">
            <div class="quote-success">
              <div class="quote-success-icon">
                <span class="material-symbols-outlined" aria-hidden="true">event_available</span>
              </div>
              <h2 class="quote-step-title">{{ $t('quote.step3.calcomConfirmedTitle') }}</h2>
              <p class="quote-success-sub">{{ $t('quote.step3.calcomConfirmedSubtitle') }}</p>
              <router-link :to="{ name: 'Offers' }" class="quote-cta quote-cta--inline">
                {{ $t('quote.step3.backToOffers') }}
              </router-link>
            </div>
          </template>
          <template v-else-if="agentClosePayload && agentClosePayload.route === 'meeting'">
            <div class="quote-success">
              <div class="quote-success-icon">
                <span class="material-symbols-outlined" aria-hidden="true">event_available</span>
              </div>
              <h2 class="quote-step-title">{{ $t('quote.step3.successTitle') }}</h2>
              <p class="quote-success-sub">{{ $t('quote.step3.successSubtitle') }}</p>
              <a
                v-if="agentClosePayload.calcomLink"
                :href="agentClosePayload.calcomLink"
                target="_blank"
                rel="noopener"
                class="quote-cta quote-cta--inline"
              >
                {{ $t('quote.step3.assistant.viewMeeting') }}
              </a>
            </div>
          </template>
          <template v-else-if="agentClosePayload && agentClosePayload.route === 'self_service'">
            <div class="quote-success">
              <div class="quote-success-icon">
                <span class="material-symbols-outlined" aria-hidden="true">check_circle</span>
              </div>
              <h2 class="quote-step-title">{{ $t('quote.step3.successTitle') }}</h2>
              <p
                v-if="agentClosePayload.packageRecommendation"
                class="quote-success-sub"
              >
                {{ $t('quote.step3.assistant.recommendedPackage', { package: $t(`offers.packages.${agentClosePayload.packageRecommendation.package_id}.name`) }) }}
              </p>
              <router-link
                :to="{ name: 'Offers', query: { recommended: agentClosePayload.packageRecommendation ? agentClosePayload.packageRecommendation.package_id : undefined } }"
                class="quote-cta quote-cta--inline"
              >
                {{ $t('quote.step3.backToOffers') }}
              </router-link>
            </div>
          </template>
          <template v-else-if="agentClosePayload && agentClosePayload.route === 'quote_48h'">
            <div class="quote-success">
              <div class="quote-success-icon">
                <span class="material-symbols-outlined" aria-hidden="true">check_circle</span>
              </div>
              <h2 class="quote-step-title">{{ $t('quote.step3.successTitle') }}</h2>
              <p class="quote-success-sub">{{ $t('quote.step3.successSubtitle') }}</p>
              <router-link :to="{ name: 'Offers' }" class="quote-cta quote-cta--inline">
                {{ $t('quote.step3.backToOffers') }}
              </router-link>
            </div>
          </template>
          <template v-else-if="submitError === null">
```

- [ ] **Step 4: Vérifier le build**

Run: `cd frontend && npm run build`
Expected: build réussi, 0 erreur.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/QuoteView.vue
git commit -m "$(cat <<'EOF'
feat(intake): câble l'écran Assistant dans QuoteView — étapes renumérotées 1-5

submit() bascule désormais vers l'étape 4 (Assistant, IntakeAgentPanel)
au lieu de sauter directement à l'écran « merci » statique. L'écran de
clôture (renuméroté étape 5) branche son affichage sur la route retournée
par l'agent (meeting/self_service/quote_48h) — c'est le fix de la
découverte critique de la passation 2026-07-12 : depuis la mise en prod
du formulaire /devis, aucun prospect réel n'avait jamais vu l'agent ni
reçu de routage/email/lien Cal.com.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Fo4sC5bGsFC4RYoERoNen4
EOF
)"
```

---

## Task 9 : Frontend — `OffersView.vue`, préselection `?recommended=`

**Files:**
- Modify: `frontend/src/views/OffersView.vue`

**Interfaces:**
- Consumes: `packages` (array déjà existant, ligne 370), `goTo(idx)` (déjà existant, ligne 641), `activeIndex` (déjà existant, ligne 535).

- [ ] **Step 1: Importer `useRoute` et naviguer vers le package recommandé au montage**

Remplacer :

```js
import { useRouter } from 'vue-router'
```

par :

```js
import { useRoute, useRouter } from 'vue-router'
```

Remplacer :

```js
const router = useRouter()
const { locale: i18nLocale, t } = useI18n()
```

par :

```js
const router = useRouter()
const route = useRoute()
const { locale: i18nLocale, t } = useI18n()
```

- [ ] **Step 2: Ajouter la logique de préselection après `goTo`**

Remplacer :

```js
function goTo(idx) {
  if (idx < 0) idx = 0
  if (idx > displayedPackages.value.length - 1) idx = displayedPackages.value.length - 1
  activeIndex.value = idx
}
```

par :

```js
function goTo(idx) {
  if (idx < 0) idx = 0
  if (idx > displayedPackages.value.length - 1) idx = displayedPackages.value.length - 1
  activeIndex.value = idx
}

// Préselection depuis l'écran Assistant du parcours /devis (US-IQ-02
// frontend, branche self_service) — ?recommended=<package_id> navigue le
// carousel directement sur la carte concernée, sans CSS de surbrillance
// dédié (le style « carte active » du carousel suffit déjà).
function applyRecommendedPackage() {
  const recommended = route.query.recommended
  if (!recommended || typeof recommended !== 'string') return
  const idx = packages.findIndex((p) => p.id === recommended)
  if (idx === -1) return
  activeChip.value = 'all'
  goTo(idx)
}
```

- [ ] **Step 3: Appeler la fonction au montage**

Remplacer :

```js
onMounted(() => {
  document.addEventListener('keydown', onKeydown)
})
```

par :

```js
onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  applyRecommendedPackage()
})
```

- [ ] **Step 4: Vérifier le build**

Run: `cd frontend && npm run build`
Expected: build réussi, 0 erreur.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/OffersView.vue
git commit -m "$(cat <<'EOF'
feat(offers): préselection ?recommended=<package_id> depuis l'écran Assistant

Le carousel /offres navigue directement sur le package recommandé par
l'agent (branche self_service, US-IQ-02 frontend) au lieu de rester sur
la 1re carte — le prospect confirme ou change son choix lui-même.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Fo4sC5bGsFC4RYoERoNen4
EOF
)"
```

---

## Task 10 : Frontend — tests Playwright mockés (`intake-parcours.spec.ts`)

**Files:**
- Modify: `frontend/tests/e2e/intake-parcours.spec.ts`

**Interfaces:** aucune (E2E, interception réseau `page.route()`).

**Contrainte rappelée** : ce fichier est strictement lecture seule — les tests existants
remplissent le formulaire jusqu'au bouton final SANS JAMAIS cliquer submit. Les nouveaux tests
de ce Task **interceptent** `POST /api/intake/session`, `/form`, `/agent/turn`, `/complete`
avec des fixtures JSON, donc CLIQUER submit devient sûr (aucun POST business réel n'atteint le
backend — la requête est interceptée et jamais transmise).

- [ ] **Step 1: Ajouter les 3 scénarios mockés**

Ajouter à la fin de `frontend/tests/e2e/intake-parcours.spec.ts`, avant la fermeture du
`test.describe` existant (juste avant la dernière ligne `})`) :

```ts
test.describe('Écran Assistant — clôtures mockées (US-IQ-02 frontend)', () => {
  async function fillAndSubmit(page: import('@playwright/test').Page, locale: Locale) {
    await gotoLocalized(page, '/devis', locale)
    const decision = page.locator('.quote-step-content textarea').first()
    await decision.fill('Lancer la filiale Sénégal maintenant ou attendre 2027')
    const optionInputs = page.locator('.quote-option-row input[type="text"]')
    await optionInputs.nth(0).fill('Lancer maintenant')
    await optionInputs.nth(1).fill('Attendre 2027')
    await page.locator('.quote-step-content button[type="submit"]').click()
    await page.locator('.quote-step-content button[type="submit"]').click() // Temps 2 → 3
    await page.locator('.quote-checkbox-group .quote-checkbox-chip').first().click()
    const texts = page.locator('.quote-step-content input[type="text"]')
    await texts.nth(0).fill('Grand public urbain')
    await texts.nth(1).fill('Karim Bensaid')
    await texts.nth(2).fill('Banque Populaire MA')
    await page.locator('input[type="email"]').fill('karim@example.com')
    await page.locator('.quote-consent-stitch input[type="checkbox"]').check()
  }

  test('(fr) clôture route=meeting — lien Cal.com cliquable affiché', async ({ page }) => {
    await page.route('**/api/intake/session', (r) =>
      r.fulfill({ json: { success: true, data: { session_id: 'sess-mock-1', state: 'started', locale: 'fr' } } }),
    )
    await page.route('**/api/intake/session/sess-mock-1/form', (r) =>
      r.fulfill({ json: { success: true, data: { session_id: 'sess-mock-1', quote_id: 'q_mock1', state: 'form_submitted' } } }),
    )
    await page.route('**/api/intake/session/sess-mock-1/agent/turn', (r) =>
      r.fulfill({
        json: {
          success: true,
          data: {
            session_id: 'sess-mock-1', state: 'completed', agent_turns: 1,
            message: 'Merci, votre brief est transmis.', close: true,
            confidential_flags: [], route: 'meeting',
            calcom_link: 'https://agenda.ai-mpower.com/a.mansouri/entretien-bassira-20-min?email=karim%40example.com',
          },
        },
      }),
    )

    await fillAndSubmit(page, 'fr')
    await page.locator('.quote-step-content button[type="submit"]').click() // Temps 3 submit
    await expect(page.getByRole('link', { name: /voir mon créneau/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /voir mon créneau/i })).toHaveAttribute(
      'href', /agenda\.ai-mpower\.com/,
    )
  })

  test('(fr) clôture route=self_service — package recommandé affiché', async ({ page }) => {
    await page.route('**/api/intake/session', (r) =>
      r.fulfill({ json: { success: true, data: { session_id: 'sess-mock-2', state: 'started', locale: 'fr' } } }),
    )
    await page.route('**/api/intake/session/sess-mock-2/form', (r) =>
      r.fulfill({ json: { success: true, data: { session_id: 'sess-mock-2', quote_id: 'q_mock2', state: 'form_submitted' } } }),
    )
    await page.route('**/api/intake/session/sess-mock-2/agent/turn', (r) =>
      r.fulfill({
        json: {
          success: true,
          data: {
            session_id: 'sess-mock-2', state: 'completed', agent_turns: 1,
            message: 'Merci, votre brief est transmis.', close: true,
            confidential_flags: [], route: 'self_service',
            package_recommendation: { package_id: 'adcheck_lite', rationale: 'Test de concept publicitaire.' },
          },
        },
      }),
    )

    await fillAndSubmit(page, 'fr')
    await page.locator('.quote-step-content button[type="submit"]').click()
    await expect(page.locator('.quote-step-content')).toContainText('Adcheck Lite')
  })

  test('(fr) gateway LLM indisponible — bannière neutre de repli, pas d\'erreur', async ({ page }) => {
    await page.route('**/api/intake/session', (r) =>
      r.fulfill({ json: { success: true, data: { session_id: 'sess-mock-3', state: 'started', locale: 'fr' } } }),
    )
    await page.route('**/api/intake/session/sess-mock-3/form', (r) =>
      r.fulfill({ json: { success: true, data: { session_id: 'sess-mock-3', quote_id: 'q_mock3', state: 'form_submitted' } } }),
    )
    await page.route('**/api/intake/session/sess-mock-3/agent/turn', (r) =>
      r.fulfill({
        json: {
          success: true,
          data: {
            session_id: 'sess-mock-3', state: 'completed', route: 'quote_48h', agent_unavailable: true,
          },
        },
      }),
    )

    await fillAndSubmit(page, 'fr')
    await page.locator('.quote-step-content button[type="submit"]').click()
    await expect(page.getByText(/nous revenons vers vous sous 48/i)).toBeVisible()
    await expect(page.locator('.quote-error')).toHaveCount(0)
  })
})
```

- [ ] **Step 2: Lancer les 3 nouveaux tests contre la prod (lecture seule garantie par les mocks réseau)**

Run: `cd frontend && npx playwright test intake-parcours.spec.ts -g "Écran Assistant"`
Expected: PASS (3 tests). Si un sélecteur diverge du DOM réel déployé (ex. libellé exact du
bouton), ajuster le sélecteur — ne jamais retirer la contrainte read-only pour faire passer un
test.

- [ ] **Step 3: Lancer la suite E2E complète du fichier pour vérifier l'absence de régression**

Run: `cd frontend && npx playwright test intake-parcours.spec.ts`
Expected: PASS (tous, y compris les 3 tests fr/en/ar déjà existants).

- [ ] **Step 4: Commit**

```bash
git add frontend/tests/e2e/intake-parcours.spec.ts
git commit -m "$(cat <<'EOF'
test(intake): 3 scénarios Playwright mockés pour l'écran Assistant

Interception réseau (page.route()) sur session/form/agent/turn — respecte
la politique read-only du fichier (jamais de vrai POST business, cf. SOP-011)
tout en couvrant le rendu des 3 issues de clôture (meeting/self_service/
gateway down).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Fo4sC5bGsFC4RYoERoNen4
EOF
)"
```

---

## Vérification finale (avant de considérer le chantier livré)

- [ ] `cd backend && uv run pytest -m "not integration" -q` — 0 échec.
- [ ] `cd backend && uv run ruff check .` — 0 erreur.
- [ ] `cd frontend && npm run build` — 0 erreur.
- [ ] `cd frontend && npx playwright test intake-parcours.spec.ts` — 0 échec.
- [ ] **Vérification déployée réelle (SOP-011, non automatisable)** : une fois déployé sur
  `bassira.ma`, un vrai clic sur `/devis` (Amine ou Chrome connecté) jusqu'à l'écran Assistant,
  au moins une conversation réelle avec l'agent (vrai appel LLM), vérifier que la clôture
  affiche bien le contenu attendu selon la branche obtenue. C'est la SEULE preuve
  d'atteignabilité produit — le Playwright mocké de Task 10 ne couvre que le rendu.
- [ ] Poser `US-IQ-02.passes = true` dans `.ralph/prd.json` **seulement si**, en plus de ce
  chantier livré, le corpus §10.3 a été re-passé à 10/10 sur les critères 1-8 (chantier
  séparé, prompt à ajuster — cf. passation 2026-07-12, non couvert par ce plan).
