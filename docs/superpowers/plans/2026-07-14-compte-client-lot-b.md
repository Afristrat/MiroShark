# Compte client multi-tenant (Lot B) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Créer automatiquement un compte client (org + user + magic link) au moment de l'engagement réel (réservation Cal.com, ou devis payé via le circuit admin manuel) et exposer les demandes de l'org dans le portail client existant.

**Architecture:** Une fonction backend idempotente `ensure_client_account()` appelée depuis deux points d'entrée existants (`confirm_calcom_booking`, `update_quote_status`), jamais depuis le webhook Stripe self-service. Un nouvel endpoint `GET /api/client/quotes` réutilise le décorateur `require_org_membership` déjà en place. Le front ajoute une section dans `ClientDashboardView.vue` — aucune nouvelle page, aucun nouveau composant d'auth (déjà en prod).

**Tech Stack:** Flask (Python 3.11, `uv`), Supabase (`supabase-py>=2.7.0`, client admin `service_role`), Vue 3 + Pinia + vue-i18n, pytest, Playwright.

## Global Constraints

- i18n polyglotte intégral obligatoire (fr/en/ar) sur tout nouveau label utilisateur (US-217, CLAUDE.md) — parité stricte entre locales dans le même commit.
- Zéro dette technique : `py_compile` + tests backend + `npm run build` doivent passer avant de clore chaque tâche (aucun outillage lint/typecheck configuré sur ce repo — gate minimum documenté dans CLAUDE.md).
- Aucune nouvelle policy RLS SQL (déjà couverte par `members_can_read_org_quotes`, migration `20260505_001`) — si une tâche découvre le contraire en testant, s'arrêter et documenter avant de continuer.
- Le webhook Stripe self-service (`stripe_checkout.py`, `checkout.session.completed`) ne doit **jamais** être modifié par ce plan — aucune tâche n'y touche.
- Toute fonction du module `ensure_client_account` doit être best-effort et ne **jamais** faire échouer son appelant (`confirm_calcom_booking` / `update_quote_status`) — pattern déjà établi par `_send_admin_notification` (ADR-IQ-14).
- Vérification déployée obligatoire (SOP-011) : pas de `npm run dev` local pour valider — tests automatisés + Playwright uniquement.
- Spec de référence : `docs/superpowers/specs/2026-07-14-compte-client-design.md` (commit `b803f9a`).

---

## File Structure

| Fichier | Rôle |
|---|---|
| `backend/app/services/client_account_service.py` (**nouveau**) | `ensure_client_account()` — logique idempotente complète |
| `backend/app/services/intake_service.py` (modifier, fin de `confirm_calcom_booking`) | Déclencheur booking Cal.com |
| `backend/app/services/quote_admin_service.py` (modifier, fin de `update_quote_status`) | Déclencheur devis payé (circuit manuel) |
| `backend/app/api/client.py` (modifier, ajout d'une route) | `GET /api/client/quotes` |
| `frontend/src/api/client.js` (modifier, ajout d'une fonction) | `listClientQuotes()` |
| `frontend/src/views/ClientDashboardView.vue` (modifier) | Section "Mes demandes" |
| `frontend/src/locales/{fr,en,ar}.json` (modifier) | Clés `client.dashboard.quotes.*` |
| `backend/tests/test_unit_client_account.py` (**nouveau**) | Tests `ensure_client_account` |
| `backend/tests/test_unit_client_quotes.py` (**nouveau**) | Tests endpoint `GET /api/client/quotes` |
| `frontend/tests/e2e/client-account.spec.ts` (**nouveau**) | E2E : booking → magic link → dashboard |

---

## Task 1 : Vérifier le contrat exact de l'API admin Supabase (`generate_link`)

**Contexte** : aucun usage de `auth.admin.create_user` / `auth.admin.generate_link` n'existe encore dans ce repo. `supabase-py>=2.7.0` les expose via `client.auth.admin`, mais la forme exacte de la réponse (`.user.id`, `.properties.action_link` ou équivalent) doit être confirmée contre la version réellement installée avant d'écrire du code dessus — ne pas deviner.

**Files:**
- Aucun fichier produit — script jetable dans le scratchpad.

- [ ] **Step 1: Vérifier la version installée**

Run: `cd backend && uv run python -c "import supabase; print(supabase.__version__)"`
Expected: une version `>=2.7.0` (ex. `2.9.1`)

- [ ] **Step 2: Script jetable pour inspecter la réponse réelle**

Écrire `backend/scripts/_probe_generate_link.py` (temporaire, à supprimer après) :

```python
import os
from app.auth.supabase_client import get_supabase_admin

os.environ.setdefault("SUPABASE_URL", os.environ["SUPABASE_URL"])
cli = get_supabase_admin()
resp = cli.auth.admin.generate_link({
    "type": "magiclink",
    "email": "probe-ensure-client-account@example.invalid",
})
print(type(resp))
print(resp)
```

Run (contre l'environnement de dev/preview Coolify, **jamais prod**) :
`cd backend && SUPABASE_URL=$PREVIEW_URL SUPABASE_SERVICE_ROLE_KEY=$PREVIEW_KEY uv run python scripts/_probe_generate_link.py`

Expected: un objet avec un attribut exposant `user.id` (uuid créé) et un attribut exposant le lien d'action (`properties.action_link` dans les versions récentes du SDK officiel). Noter la forme EXACTE observée — elle conditionne le code du Task 2.

- [ ] **Step 3: Nettoyer**

Supprimer `backend/scripts/_probe_generate_link.py` et l'utilisateur de test créé (`cli.auth.admin.delete_user(user_id)` en one-liner Python, ou via le dashboard Supabase Auth).

- [ ] **Step 4: Commit**

Pas de commit pour cette tâche (rien de permanent) — mais noter la forme de réponse observée dans le message du commit du Task 2 pour traçabilité.

---

## Task 2 : `ensure_client_account()` — service backend

**Files:**
- Create: `backend/app/services/client_account_service.py`
- Test: `backend/tests/test_unit_client_account.py`

**Interfaces:**
- Consumes: `get_supabase_admin()` (`app/auth/supabase_client.py`), `get_user_orgs(user_id, client=...)` (idem), `send_email()` + `render_template()` (`app/services/email_service.py`), `get_quote_payload_from_supabase()` (`app/services/quote_ownership.py`).
- Produces:
  ```python
  def ensure_client_account(
      email: str,
      full_name: str,
      org_name: Optional[str],
      *,
      source: str,  # "calcom_booking" | "quote_paid"
      client: Any = None,
  ) -> Dict[str, Any]:
      """Returns {"org_id": str|None, "user_id": str|None, "created": bool}."""
  ```
  Ne lève **jamais** d'exception — toute erreur est loggée et retourne `{"org_id": None, "user_id": None, "created": False}`.

- [ ] **Step 1: Écrire le test d'idempotence (échoue)**

```python
"""Tests unitaires Lot B — ensure_client_account (compte client multi-tenant).

Couvre :
  - Création complète (auth.users + organizations + org_members) si l'email
    est inconnu.
  - Idempotence : un email déjà membre d'une org retourne l'org existante,
    ne recrée rien, n'envoie pas de nouveau magic link.
  - Re-rattachement des quote_ownership de l'org de repli vers la nouvelle org.
  - Best-effort : toute exception interne est absorbée, jamais propagée.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from app.services import client_account_service as cas


def _admin_client_stub(*, existing_user=None, existing_org_member=None):
    cli = MagicMock()
    return cli


class TestEnsureClientAccountIdempotence:
    def test_existing_member_returns_existing_org_without_recreating(self, monkeypatch):
        cli = MagicMock()

        # Simule un auth.users existant pour cet email.
        monkeypatch.setattr(
            cas, "_find_user_by_email",
            lambda email, *, client: {"id": "user-existing-uuid", "email": email},
        )
        monkeypatch.setattr(
            cas, "_find_org_membership",
            lambda user_id, *, client: {"org_id": "org-existing-uuid", "role": "owner"},
        )
        create_org_mock = MagicMock()
        monkeypatch.setattr(cas, "_create_org_and_membership", create_org_mock)
        send_link_mock = MagicMock()
        monkeypatch.setattr(cas, "_send_magic_link", send_link_mock)

        result = cas.ensure_client_account(
            "karim@example.com", "Karim Bensaid", "Atlas Capital",
            source="calcom_booking", client=cli,
        )

        assert result == {
            "org_id": "org-existing-uuid",
            "user_id": "user-existing-uuid",
            "created": False,
        }
        create_org_mock.assert_not_called()
        send_link_mock.assert_not_called()

    def test_new_email_creates_org_and_sends_magic_link(self, monkeypatch):
        cli = MagicMock()
        monkeypatch.setattr(cas, "_find_user_by_email", lambda email, *, client: None)
        monkeypatch.setattr(
            cas, "_create_org_and_membership",
            lambda email, full_name, org_name, *, client: {
                "org_id": "org-new-uuid", "user_id": "user-new-uuid",
            },
        )
        reattach_mock = MagicMock()
        monkeypatch.setattr(cas, "_reattach_quote_ownership", reattach_mock)
        send_link_mock = MagicMock()
        monkeypatch.setattr(cas, "_send_magic_link", send_link_mock)

        result = cas.ensure_client_account(
            "nouveau@example.com", "Nouveau Client", "Nouvelle Org",
            source="quote_paid", client=cli,
        )

        assert result == {
            "org_id": "org-new-uuid",
            "user_id": "user-new-uuid",
            "created": True,
        }
        reattach_mock.assert_called_once_with(
            "org-new-uuid", "nouveau@example.com", client=cli,
        )
        send_link_mock.assert_called_once_with(
            "nouveau@example.com", "Nouveau Client", client=cli,
        )

    def test_never_raises_on_internal_error(self, monkeypatch):
        cli = MagicMock()

        def _boom(*a, **kw):
            raise RuntimeError("simulated Supabase outage")

        monkeypatch.setattr(cas, "_find_user_by_email", _boom)

        result = cas.ensure_client_account(
            "erreur@example.com", "X", None, source="calcom_booking", client=cli,
        )

        assert result == {"org_id": None, "user_id": None, "created": False}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_unit_client_account.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.client_account_service'`

- [ ] **Step 3: Implémentation minimale**

```python
"""Service ensure_client_account (Lot B — compte client multi-tenant).

Point d'entrée unique : ``ensure_client_account()``, appelée depuis deux
déclencheurs UNIQUEMENT — ``confirm_calcom_booking`` (réservation Cal.com)
et ``update_quote_status`` (devis payé, circuit admin manuel). Jamais
depuis le webhook Stripe self-service (``stripe_checkout.py``) — ce
circuit reste volontairement sans compte (ADR-007/US-205).

Idempotence : clé de dédup = email. Un email déjà rattaché à une org
retourne cette org sans rien recréer ni renvoyer de magic link.

Best-effort total : ne lève jamais d'exception — chaque étape est loggée,
toute erreur retourne ``{"org_id": None, "user_id": None, "created": False}``.
Pattern identique à ``_send_admin_notification`` (ADR-IQ-14).
"""

from __future__ import annotations

import re
import secrets
from typing import Any, Dict, Optional

from ..auth.supabase_client import get_supabase_admin
from ..utils.logger import get_logger
from . import quote_ownership as qo
from .email_service import render_template, send_email

logger = get_logger("miroshark.client_account")

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_FALLBACK_ORG_SLUG = "aimpower-bassira"


def _slugify(value: str) -> str:
    slug = _SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return slug or "org"


def _find_user_by_email(email: str, *, client: Any) -> Optional[Dict[str, Any]]:
    resp = client.auth.admin.list_users()
    users = getattr(resp, "users", None) or resp
    for u in users:
        u_email = getattr(u, "email", None) or (u.get("email") if isinstance(u, dict) else None)
        if u_email and u_email.strip().lower() == email.strip().lower():
            u_id = getattr(u, "id", None) or (u.get("id") if isinstance(u, dict) else None)
            return {"id": u_id, "email": u_email}
    return None


def _find_org_membership(user_id: str, *, client: Any) -> Optional[Dict[str, Any]]:
    resp = (
        client.table("org_members")
        .select("org_id, role")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = getattr(resp, "data", None) or []
    return rows[0] if rows else None


def _unique_slug(base_slug: str, *, client: Any) -> str:
    slug = base_slug
    for _ in range(3):
        resp = (
            client.table("organizations")
            .select("id")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )
        if not (getattr(resp, "data", None) or []):
            return slug
        slug = f"{base_slug}-{secrets.token_hex(2)}"
    return f"{base_slug}-{secrets.token_hex(4)}"


def _create_org_and_membership(
    email: str,
    full_name: str,
    org_name: Optional[str],
    *,
    client: Any,
) -> Dict[str, Any]:
    base_slug = _slugify(org_name or email.split("@")[0])
    slug = _unique_slug(base_slug, client=client)

    org_resp = (
        client.table("organizations")
        .insert({
            "name": org_name or full_name or email,
            "slug": slug,
            "status": "trial",
        })
        .execute()
    )
    org_rows = getattr(org_resp, "data", None) or []
    if not org_rows:
        raise RuntimeError("organizations insert returned no row")
    org_id = org_rows[0]["id"]

    created_user = client.auth.admin.create_user({
        "email": email,
        "email_confirm": True,
        "user_metadata": {"full_name": full_name},
    })
    user_obj = getattr(created_user, "user", None) or created_user
    user_id = getattr(user_obj, "id", None) or (
        user_obj.get("id") if isinstance(user_obj, dict) else None
    )
    if not user_id:
        raise RuntimeError("auth.admin.create_user returned no user id")

    client.table("org_members").insert({
        "org_id": org_id,
        "user_id": user_id,
        "role": "owner",
    }).execute()

    return {"org_id": org_id, "user_id": user_id}


def _reattach_quote_ownership(org_id: str, email: str, *, client: Any) -> None:
    try:
        client.table("quote_ownership").update({"org_id": org_id}).eq(
            "customer_email", email
        ).execute()
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.error(
            "_reattach_quote_ownership failed for org=%s: %s",
            org_id, exc.__class__.__name__,
        )


def _send_magic_link(email: str, full_name: str, *, client: Any) -> None:
    try:
        resp = client.auth.admin.generate_link({
            "type": "magiclink",
            "email": email,
        })
        # Forme exacte confirmée au Task 1 — ``properties.action_link``
        # pour supabase-py>=2.7.0.
        action_link = getattr(getattr(resp, "properties", None), "action_link", None)
        if not action_link and isinstance(resp, dict):
            action_link = (resp.get("properties") or {}).get("action_link")
        if not action_link:
            logger.error("_send_magic_link: no action_link in generate_link response")
            return
        html_body = render_template("client_account_ready", {
            "full_name": full_name or email,
            "magic_link": action_link,
        })
        send_email(
            to_email=email,
            subject="Bassira — Votre espace client est prêt",
            html_body=html_body,
            reply_to="contact@ai-mpower.com",
        )
    except Exception as exc:  # noqa: BLE001 — best-effort, ne bloque jamais l'appelant
        logger.error("_send_magic_link failed for %s: %s", email, exc.__class__.__name__)


def ensure_client_account(
    email: str,
    full_name: str,
    org_name: Optional[str],
    *,
    source: str,
    client: Any = None,
) -> Dict[str, Any]:
    """Crée ou retrouve le compte client associé à ``email`` (idempotent).

    Args:
        email: email attesté du client (jamais un email non vérifié).
        full_name: nom complet, best-effort (peut être vide).
        org_name: nom d'organisation si connu (sinon dérivé de l'email).
        source: ``"calcom_booking"`` | ``"quote_paid"`` — traçabilité log
            uniquement, aucune branche logique différente.
        client: client Supabase admin injecté (tests).

    Returns:
        ``{"org_id": str|None, "user_id": str|None, "created": bool}``.
        Ne lève jamais — toute erreur retourne des ``None``.
    """
    if not email or "@" not in email:
        logger.error("ensure_client_account: invalid email (source=%s)", source)
        return {"org_id": None, "user_id": None, "created": False}

    try:
        cli = client or get_supabase_admin()

        existing_user = _find_user_by_email(email, client=cli)
        if existing_user:
            membership = _find_org_membership(existing_user["id"], client=cli)
            if membership:
                return {
                    "org_id": membership["org_id"],
                    "user_id": existing_user["id"],
                    "created": False,
                }

        created = _create_org_and_membership(email, full_name, org_name, client=cli)
        _reattach_quote_ownership(created["org_id"], email, client=cli)
        _send_magic_link(email, full_name, client=cli)

        logger.info(
            "ensure_client_account: created org=%s user=%s (source=%s)",
            created["org_id"], created["user_id"], source,
        )
        return {
            "org_id": created["org_id"],
            "user_id": created["user_id"],
            "created": True,
        }
    except Exception as exc:  # noqa: BLE001 — best-effort total, jamais propagé
        logger.error(
            "ensure_client_account failed (source=%s): %s",
            source, exc.__class__.__name__,
        )
        return {"org_id": None, "user_id": None, "created": False}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_unit_client_account.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Créer le template email manquant**

Create: `backend/app/templates/emails/client_account_ready.html` (suivre le format existant de `templates/emails/org_invitation.html` — placeholders `{full_name}`, `{magic_link}` substitués par `render_template`). Vérifier avec :

Run: `cd backend && uv run python -c "from app.services.email_service import render_template; print(render_template('client_account_ready', {'full_name': 'Karim', 'magic_link': 'https://x'}))"`
Expected: HTML rendu sans `KeyError`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/client_account_service.py backend/tests/test_unit_client_account.py backend/app/templates/emails/client_account_ready.html
git commit -m "feat(compte-client): ensure_client_account() idempotent (Lot B, US-B1)"
```

---

## Task 3 : Déclencheur booking Cal.com

**Files:**
- Modify: `backend/app/services/intake_service.py:1786-1796` (fin de `confirm_calcom_booking`)
- Test: `backend/tests/test_unit_intake.py` (fichier existant — ajouter un test)

**Interfaces:**
- Consumes: `ensure_client_account(email, full_name, org_name, *, source, client)` (Task 2).
- Produces: rien de nouveau exposé — modification interne de `confirm_calcom_booking`.

- [ ] **Step 1: Écrire le test (échoue)**

Ajouter à `backend/tests/test_unit_intake.py` :

```python
class TestConfirmCalcomBookingEnsuresAccount:
    def test_confirm_booking_calls_ensure_client_account(self, monkeypatch):
        from app.services import intake_service as svc

        captured = {}

        def _fake_ensure(email, full_name, org_name, *, source, client):
            captured["email"] = email
            captured["source"] = source
            return {"org_id": "org-x", "user_id": "user-x", "created": True}

        monkeypatch.setattr(svc, "ensure_client_account", _fake_ensure)
        monkeypatch.setattr(svc, "_verify_calcom_booking", lambda uid: "karim@example.com")
        monkeypatch.setattr(svc, "_get_session", lambda sid, *, client: {
            "id": sid, "quote_id": "q_test123",
        })
        monkeypatch.setattr(svc, "_get_session_email", lambda session, *, client: "karim@example.com")
        monkeypatch.setattr(svc.qo, "get_quote_payload_from_supabase", lambda qid, *, client: {
            "email": "karim@example.com", "full_name": "Karim Bensaid", "organization": "Atlas Capital",
        })
        monkeypatch.setattr(svc, "_send_intake_confirmation", lambda session, *, client: None)

        cli = MagicMock()
        cli.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        status, body = svc.confirm_calcom_booking("sess-1", "booking-uid-1", client=cli)

        assert status == 200
        assert captured["email"] == "karim@example.com"
        assert captured["source"] == "calcom_booking"
```

(Ajouter `from unittest.mock import MagicMock` en tête de fichier si absent.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_unit_intake.py::TestConfirmCalcomBookingEnsuresAccount -v`
Expected: FAIL — `ensure_client_account` non appelée / `AttributeError` (pas encore importée dans `intake_service`)

- [ ] **Step 3: Implémentation**

Dans `backend/app/services/intake_service.py`, ajouter l'import (avec les autres imports de service, ligne ~43) :

```python
from .client_account_service import ensure_client_account
```

Modifier la fin de `confirm_calcom_booking` (remplace les lignes 1790-1796) :

```python
    cli.table("intake_sessions").update({"calcom_booking_uid": booking_uid}).eq("id", session_id).execute()

    updated_session = dict(session)
    updated_session["calcom_booking_uid"] = booking_uid
    _send_intake_confirmation(updated_session, client=cli)

    quote_id = session.get("quote_id")
    payload = qo.get_quote_payload_from_supabase(quote_id, client=cli) if quote_id else None
    ensure_client_account(
        verified_email,
        (payload or {}).get("full_name") or "",
        (payload or {}).get("organization"),
        source="calcom_booking",
        client=cli,
    )

    return 200, {"success": True, "data": {"session_id": session_id, "calcom_booking_uid": booking_uid}}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_unit_intake.py -v`
Expected: PASS (test ajouté + suite intake existante toujours verte, 505+1 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/intake_service.py backend/tests/test_unit_intake.py
git commit -m "feat(compte-client): déclencheur booking Cal.com → ensure_client_account (Lot B, US-B2)"
```

---

## Task 4 : Déclencheur devis payé (circuit manuel uniquement)

**Files:**
- Modify: `backend/app/services/quote_admin_service.py:414-480` (dans `update_quote_status`)
- Test: `backend/tests/test_unit_quote_admin.py` (fichier existant — ajouter un test)

**Interfaces:**
- Consumes: `ensure_client_account(...)` (Task 2), `read_quote_payload(quote_id)` (déjà existant, ligne 166).
- Produces: rien de nouveau exposé.

- [ ] **Step 1: Écrire le test (échoue)**

Ajouter à `backend/tests/test_unit_quote_admin.py` :

```python
class TestUpdateQuoteStatusTriggersEnsureAccount:
    def test_transition_to_paid_calls_ensure_client_account(self, monkeypatch, tmp_path):
        from app.services import quote_admin_service as qas

        # Setup fichier payload + sidecar minimal (réutiliser le pattern
        # des tests existants du fichier pour créer un devis "quoted").
        monkeypatch.setattr(qas, "quotes_dir", lambda: tmp_path)
        quote_id = "q_paidtest1"
        payload_path = tmp_path / f"quote_20260714T000000_{quote_id[2:]}.json"
        payload_path.write_text('{"email": "client@example.com", "full_name": "Client Test", "organization": "Test Org"}', encoding="utf-8")
        sidecar = payload_path.with_suffix(".status.json")
        sidecar.write_text('{"status": "quoted", "history": [], "payment_link": null, "last_email_sent_at": null, "notes": null, "delivered_url": null}', encoding="utf-8")

        captured = {}
        def _fake_ensure(email, full_name, org_name, *, source, client=None):
            captured["email"] = email
            captured["source"] = source
            return {"org_id": "org-x", "user_id": "user-x", "created": True}
        monkeypatch.setattr(qas, "ensure_client_account", _fake_ensure)
        monkeypatch.setattr(qas, "update_quote_status_in_supabase", lambda *a, **kw: True)

        ok, code, _ = qas.update_quote_status(quote_id, new_status="paid", by_email="admin@ai-mpower.com")

        assert ok is True
        assert captured["email"] == "client@example.com"
        assert captured["source"] == "quote_paid"

    def test_transition_not_to_paid_does_not_trigger(self, monkeypatch, tmp_path):
        from app.services import quote_admin_service as qas

        monkeypatch.setattr(qas, "quotes_dir", lambda: tmp_path)
        quote_id = "q_notpaid1"
        payload_path = tmp_path / f"quote_20260714T000001_{quote_id[2:]}.json"
        payload_path.write_text('{"email": "x@example.com"}', encoding="utf-8")
        sidecar = payload_path.with_suffix(".status.json")
        sidecar.write_text('{"status": "received", "history": [], "payment_link": null, "last_email_sent_at": null, "notes": null, "delivered_url": null}', encoding="utf-8")

        ensure_mock = MagicMock()
        monkeypatch.setattr(qas, "ensure_client_account", ensure_mock)

        ok, code, _ = qas.update_quote_status(quote_id, new_status="reviewing")

        assert ok is True
        ensure_mock.assert_not_called()
```

(Ajouter `from unittest.mock import MagicMock` en tête si absent.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_unit_quote_admin.py::TestUpdateQuoteStatusTriggersEnsureAccount -v`
Expected: FAIL — `ensure_client_account` non appelée

- [ ] **Step 3: Implémentation**

Dans `backend/app/services/quote_admin_service.py`, ajouter l'import (avec les autres imports, ligne ~46) :

```python
from .client_account_service import ensure_client_account
```

Modifier `update_quote_status` — insérer juste avant le `return True, "OK", new_payload` final (après le bloc du miroir Supabase, ligne ~478) :

```python
    if new_status == "paid" and current_status != "paid":
        payload = read_quote_payload(quote_id) or {}
        client_email = payload.get("email")
        if client_email:
            ensure_client_account(
                client_email,
                payload.get("full_name") or "",
                payload.get("organization") or payload.get("company"),
                source="quote_paid",
            )
        else:
            logger.warning(
                "update_quote_status: paid transition for %s without email in payload — "
                "ensure_client_account skipped.",
                quote_id,
            )

    return True, "OK", new_payload
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_unit_quote_admin.py -v`
Expected: PASS (2 nouveaux tests + suite existante verte)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/quote_admin_service.py backend/tests/test_unit_quote_admin.py
git commit -m "feat(compte-client): déclencheur devis payé (circuit manuel) → ensure_client_account (Lot B, US-B3)"
```

---

## Task 5 : Endpoint `GET /api/client/quotes`

**Files:**
- Modify: `backend/app/api/client.py` (ajout d'une route)
- Test: `backend/tests/test_unit_client_quotes.py` (nouveau)

**Interfaces:**
- Consumes: `require_org_membership(role_min="viewer")` (`app/auth/decorators.py`), `list_quotes_for_org(org_id, *, limit, offset, client)` (`app/services/quote_ownership.py`, déjà existant).
- Produces: `GET /api/client/quotes?limit=&offset=` → `{"success": true, "data": {"quotes": [...], "total": int}}`. Chaque item : `{quote_id, package_id, status, created_at}` (jamais `customer_email` ni `payload` — pas de PII superflue exposée au client).

- [ ] **Step 1: Écrire le test (échoue)**

```python
"""Tests unitaires Lot B — GET /api/client/quotes (US-B4)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest

from app import create_app


@pytest.fixture
def app_client(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "client-quotes-test-secret")
    app = create_app()
    return app.test_client()


def _bearer(user_id="user-abc", email="karim@example.com"):
    token = pyjwt.encode(
        {"sub": user_id, "email": email, "role": "authenticated"},
        "client-quotes-test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


class TestClientQuotesEndpoint:
    def test_requires_auth(self, app_client):
        resp = app_client.get("/api/client/quotes")
        assert resp.status_code == 401

    def test_returns_scoped_quotes_for_single_org_member(self, app_client, monkeypatch):
        from app.api import client as client_api

        monkeypatch.setattr(
            client_api, "get_user_orgs",
            lambda user_id: [{"id": "org-1", "slug": "atlas", "name": "Atlas", "role": "owner"}],
        )
        monkeypatch.setattr(
            "app.services.quote_ownership.list_quotes_for_org",
            lambda org_id, **kw: [
                {"quote_id": "q_1", "package_id": "crisis_drill_24h", "status": "delivered", "created_at": "2026-07-12T10:00:00Z", "org_id": org_id, "customer_email": "karim@example.com"},
            ],
        )

        resp = app_client.get("/api/client/quotes", headers=_bearer())

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert len(body["data"]["quotes"]) == 1
        item = body["data"]["quotes"][0]
        assert item["quote_id"] == "q_1"
        assert "customer_email" not in item

    def test_no_org_returns_403(self, app_client, monkeypatch):
        from app.api import client as client_api
        monkeypatch.setattr(client_api, "get_user_orgs", lambda user_id: [])

        resp = app_client.get("/api/client/quotes", headers=_bearer())

        assert resp.status_code == 403
        assert resp.get_json()["error_code"] == "NOT_A_MEMBER"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_unit_client_quotes.py -v`
Expected: FAIL — 404 (route inexistante)

- [ ] **Step 3: Implémentation**

Dans `backend/app/api/client.py`, ajouter l'import du service (avec les autres imports, après ligne 39) :

```python
from ..services import quote_ownership as qo
```

Ajouter la route (après `list_org_simulations`, avant `create_org_simulation`) :

```python
# ─── /quotes ────────────────────────────────────────────────────────────────

@client_bp.route("/quotes", methods=["GET"])
@require_org_membership(role_min="viewer")
def list_org_quotes():
    """Liste les devis de l'organisation courante (US-B4, Lot B).

    Payload allégé — jamais ``customer_email`` ni ``payload`` complet
    (PII) exposés au client : uniquement ce qu'il a besoin de voir sur
    ses propres demandes.
    """
    org = getattr(g, "current_org", None) or {}
    org_id = org.get("id")
    if not org_id:
        return _err("ORG_RESOLUTION_FAILED", "Could not resolve current org.", 500)

    limit = min(max(int(request.args.get("limit", 50) or 50), 1), 200)
    offset = max(int(request.args.get("offset", 0) or 0), 0)

    rows = qo.list_quotes_for_org(org_id, limit=limit, offset=offset)
    quotes = [
        {
            "quote_id": r.get("quote_id"),
            "package_id": r.get("package_id"),
            "status": r.get("status"),
            "created_at": r.get("created_at"),
        }
        for r in rows
    ]
    return jsonify({
        "success": True,
        "data": {"quotes": quotes, "total": len(quotes), "limit": limit, "offset": offset},
    }), 200
```

Note : `require_org_membership` pose déjà `g.current_user` via `require_auth` interne, donc un test sans header `Authorization` obtient bien 401 avant même d'atteindre la logique org.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_unit_client_quotes.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/client.py backend/tests/test_unit_client_quotes.py
git commit -m "feat(compte-client): endpoint GET /api/client/quotes (Lot B, US-B4)"
```

---

## Task 6 : Section "Mes demandes" — front

**Files:**
- Modify: `frontend/src/api/client.js` (ajout d'une fonction)
- Modify: `frontend/src/views/ClientDashboardView.vue` (template + script)
- Modify: `frontend/src/locales/fr.json`, `frontend/src/locales/en.json`, `frontend/src/locales/ar.json`

**Interfaces:**
- Consumes: `GET /api/client/quotes` (Task 5).
- Produces: `listClientQuotes(params = {})` exportée de `api/client.js`, consommée par `ClientDashboardView.vue`.

- [ ] **Step 1: Ajouter la fonction API**

Dans `frontend/src/api/client.js`, ajouter à côté de `listClientSimulations` (même pattern d'appel — suivre exactement la structure de la fonction voisine, `apiClient.get('/client/simulations', { params })` ou équivalent déjà en place dans ce fichier) :

```javascript
export function listClientQuotes(params = {}) {
  return apiClient.get('/client/quotes', { params })
}
```

(Utiliser le nom exact de l'instance axios déjà exportée/utilisée par `listClientSimulations` dans ce fichier — vérifier avant d'écrire, ne pas supposer `apiClient`.)

- [ ] **Step 2: Ajouter les clés i18n (fr, en, ar — même commit, parité stricte)**

Dans `frontend/src/locales/fr.json`, sous `client.dashboard` (après le bloc `"stats"`, avant `"table"`) :

```json
      "quotes": {
        "title": "Mes demandes",
        "badgeNew": "NOUVEAU",
        "empty": "Aucune demande pour le moment.",
        "statusLabels": {
          "received": "Devis reçu",
          "reviewing": "En cours d'analyse",
          "quoted": "Devis envoyé",
          "declined": "Refusée",
          "paid": "Payée",
          "in_progress": "En cours",
          "delivered": "Livré"
        },
        "cta": {
          "viewReport": "Voir le rapport →",
          "details": "Détails"
        }
      },
```

Dans `frontend/src/locales/en.json`, même structure, valeurs traduites :

```json
      "quotes": {
        "title": "My requests",
        "badgeNew": "NEW",
        "empty": "No requests yet.",
        "statusLabels": {
          "received": "Quote received",
          "reviewing": "Under review",
          "quoted": "Quote sent",
          "declined": "Declined",
          "paid": "Paid",
          "in_progress": "In progress",
          "delivered": "Delivered"
        },
        "cta": {
          "viewReport": "View report →",
          "details": "Details"
        }
      },
```

Dans le fichier arabe (localiser via `Glob frontend/src/locales/ar*.json` — vérifier le nom exact avant d'éditer, RTL) :

```json
      "quotes": {
        "title": "طلباتي",
        "badgeNew": "جديد",
        "empty": "لا توجد طلبات حتى الآن.",
        "statusLabels": {
          "received": "تم استلام العرض",
          "reviewing": "قيد المراجعة",
          "quoted": "تم إرسال العرض",
          "declined": "مرفوض",
          "paid": "مدفوع",
          "in_progress": "قيد التنفيذ",
          "delivered": "تم التسليم"
        },
        "cta": {
          "viewReport": "عرض التقرير ←",
          "details": "التفاصيل"
        }
      },
```

- [ ] **Step 3: Ajouter l'état + le fetch dans `<script setup>`**

Dans `ClientDashboardView.vue`, ajouter l'import (avec les autres imports d'`api/client`) :

```javascript
import {
  listClientSimulations,
  listClientQuotes,
  markOutcome,
  publishSimulation
} from '../api/client'
```

Ajouter un ref à côté de `simulations` :

```javascript
const quotes = ref([])
```

Ajouter une fonction à côté de `fetchSimulations` :

```javascript
async function fetchQuotes() {
  try {
    const res = await listClientQuotes()
    const payload = res?.data || res
    quotes.value = Array.isArray(payload?.quotes) ? payload.quotes : []
  } catch (err) {
    // Best-effort : une section en échec n'empêche pas le reste du dashboard.
    quotes.value = []
  }
}

function quoteStatusLabel(status) {
  const key = `client.dashboard.quotes.statusLabels.${status || 'received'}`
  const v = t(key)
  return v && v !== key ? v : status
}
```

Modifier `onMounted` pour appeler `fetchQuotes()` en parallèle de `fetchSimulations()` :

```javascript
onMounted(async () => {
  if (!auth.profileLoaded && auth.isAuthenticated) {
    try {
      await auth.fetchProfile()
    } catch (err) {
      errorMessage.value = err?.message || t('client.dashboard.errors.profileFailed')
    }
  }
  if (auth.orgs.length > 0) {
    await Promise.all([fetchSimulations(), fetchQuotes()])
  }
})
```

- [ ] **Step 4: Ajouter la section dans le `<template>`**

Insérer après la section `dash-stats` existante (avant la fermeture de `<main class="dash-main">`), en suivant les classes CSS déjà présentes dans le fichier (`dash-*`) pour rester cohérent visuellement — reproduire la structure validée dans la maquette (`.superpowers/brainstorm/51331-1784056764/content/dashboard-mes-demandes.html`) avec les vraies classes du composant plutôt que le style inline de la maquette :

```html
      <section v-if="quotes.length > 0" class="dash-quotes" aria-label="Mes demandes">
        <div class="dash-quotes-header">
          <h2 class="dash-quotes-title">{{ $t('client.dashboard.quotes.title') }}</h2>
        </div>
        <div class="dash-quotes-list">
          <article v-for="q in quotes" :key="q.quote_id" class="dash-quote-card">
            <div class="dash-quote-info">
              <div class="dash-quote-package">{{ q.package_id || '—' }}</div>
              <div class="dash-quote-meta">{{ formatDate(q.created_at) }} · {{ q.quote_id }}</div>
            </div>
            <div class="dash-quote-actions">
              <span class="dash-quote-status" :data-status="q.status">
                {{ quoteStatusLabel(q.status) }}
              </span>
              <a
                v-if="q.status === 'delivered'"
                :href="`/report/${q.quote_id}`"
                class="dash-quote-cta dash-quote-cta--primary"
              >
                {{ $t('client.dashboard.quotes.cta.viewReport') }}
              </a>
              <router-link
                v-else
                :to="{ name: 'ClientDashboard', query: { quote_id: q.quote_id } }"
                class="dash-quote-cta"
              >
                {{ $t('client.dashboard.quotes.cta.details') }}
              </router-link>
            </div>
          </article>
        </div>
      </section>
```

Ajouter les classes CSS correspondantes dans le bloc `<style>` du composant, en réutilisant les couleurs déjà utilisées ailleurs dans le fichier pour `dash-stat-card` (ne pas introduire de nouvelles valeurs hexadécimales — reprendre les tokens `--wi-*` déjà utilisés dans ce fichier, cf. `docs/06-brand-brief.md`).

- [ ] **Step 5: Build front**

Run: `cd frontend && npm run build`
Expected: build vert, 0 erreur.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/client.js frontend/src/views/ClientDashboardView.vue frontend/src/locales/fr.json frontend/src/locales/en.json frontend/src/locales/ar.json
git commit -m "feat(compte-client): section \"Mes demandes\" dans ClientDashboardView (Lot B, US-B5)"
```

---

## Task 7 : Tests E2E Playwright (parcours réels)

**Files:**
- Create: `frontend/tests/e2e/client-account.spec.ts`

**Interfaces:**
- Consumes: fixtures `tests/e2e/fixtures/auth.ts` (existant).
- Produces: rien — tests uniquement.

**Contexte** : SOP-011 — ces tests s'exécutent contre l'environnement Coolify déployé (preview), jamais un serveur `npm run dev` local. Deux parcours à couvrir, chacun nécessite un environnement de test avec accès à une boîte mail de test (Mailosaur, boîte dédiée, ou lecture directe de la table `intake_sessions`/logs pour extraire le lien magic — à trancher selon l'infra de test E2E déjà en place pour les autres specs Playwright du repo).

- [ ] **Step 1: Étudier le pattern existant**

Run: `cd frontend && cat tests/e2e/fixtures/auth.ts` (ou lire via l'outil Read) pour connaître le mécanisme d'auth déjà utilisé par les autres specs E2E — probablement un login programmatique qui court-circuite le vrai flux email. **Ne pas dupliquer un nouveau mécanisme d'auth E2E si un fixture existant peut être étendu.**

- [ ] **Step 2: Écrire le test parcours booking Cal.com**

```typescript
import { test, expect } from '@playwright/test'

test.describe('Lot B — compte client via booking Cal.com', () => {
  test('booking confirmé crée le compte et le dashboard affiche la demande', async ({ page, request }) => {
    // 1. Parcours /devis jusqu'à la branche meeting (réutiliser le
    //    helper déjà utilisé par les tests ADR-IQ-12/13/14/15 de ce repo
    //    pour driver le chat intake — chercher tests/e2e/intake-*.spec.ts
    //    comme référence avant d'écrire ce test).
    // 2. Confirmer un booking Cal.com réel via l'API de test (ou mock
    //    server-to-server si l'environnement de test n'a pas accès à un
    //    vrai calendrier Cal.com jetable) → doit résoudre le même point
    //    d'ancrage que _verify_calcom_booking.
    // 3. Vérifier réception de l'email "client_account_ready" (fixture
    //    boîte de test — même mécanisme que les autres tests email E2E
    //    du repo, si disponible).
    // 4. Suivre le magic link, arriver sur /client/dashboard authentifié.
    // 5. Vérifier que la section "Mes demandes" affiche la demande.
    expect(true).toBe(true) // placeholder de structure — implémenter
                             // après avoir identifié le fixture email
                             // E2E réel du repo (Step 1).
  })
})
```

**Note pour l'implémenteur** : ce test ne peut pas être entièrement écrit sans savoir comment ce repo teste déjà la réception d'un email en E2E (aucun pattern trouvé lors de la préparation de ce plan — à chercher en premier, cf. Step 1). Si aucun mécanisme n'existe, ce sera une tâche de fondation E2E à part entière, pas un simple ajout — le signaler à Amine avant de continuer plutôt que d'inventer un mock qui ne prouve rien.

- [ ] **Step 3: Écrire le test parcours devis payé (admin)**

Même structure que Step 2, mais déclenché via `PATCH /api/admin/quotes/<id>/status` avec `new_status: "paid"` (authentifié comme admin, réutiliser les fixtures admin déjà en place pour les tests E2E de la console `/admin/quotes`).

- [ ] **Step 4: Run les tests contre l'environnement Coolify preview**

Run: `cd frontend && npx playwright test client-account.spec.ts`
Expected: PASS — si un des deux tests ne peut être complété faute de fixture email (Step 2 note), le signaler explicitement plutôt que de le laisser passer sur un placeholder silencieux.

- [ ] **Step 5: Commit**

```bash
git add frontend/tests/e2e/client-account.spec.ts
git commit -m "test(compte-client): E2E booking Cal.com + devis payé → dashboard (Lot B, US-B6)"
```

---

## Self-Review

**1. Spec coverage** :
- US-B1 (`ensure_client_account`) → Task 2. ✓
- US-B2 (déclencheur Cal.com) → Task 3. ✓
- US-B3 (déclencheur devis payé, exclusion self-service) → Task 4, condition `new_status == "paid" and current_status != "paid"` garantit la non-duplication et la non-interférence avec le webhook Stripe (jamais touché). ✓
- US-B4 (endpoint) → Task 5, réutilise `require_org_membership` déjà en place (plus simple que le pattern `invitations.py` envisagé dans le spec — mise à jour justifiée, décorateur idiomatique du fichier `client.py`). ✓
- US-B5 (front) → Task 6, i18n fr/en/ar dans le même commit. ✓
- US-B6 (E2E) → Task 7, avec un point d'incertitude explicite (fixture email E2E) plutôt qu'un faux positif.

**2. Placeholder scan** : Task 7 contient un `expect(true).toBe(true)` explicitement documenté comme non-final avec la raison exacte (mécanisme email E2E non identifié dans ce repo) — c'est un flag honnête, pas un TODO caché. Toutes les autres tâches ont du code complet exécutable.

**3. Type consistency** : `ensure_client_account(email, full_name, org_name, *, source, client)` — signature identique entre Task 2 (définition), Task 3 et Task 4 (appels). Retour `{"org_id", "user_id", "created"}` cohérent partout.

**Risque signalé pour l'implémenteur** : Task 1 (vérification `generate_link`) DOIT être exécutée avant Task 2 Step 3 — le code de `_send_magic_link` suppose `resp.properties.action_link`, à confirmer contre la version réelle installée.
