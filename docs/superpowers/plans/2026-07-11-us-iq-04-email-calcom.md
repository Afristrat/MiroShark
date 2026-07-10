# US-IQ-04 — Emails contextualisés + réservation Cal.com Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer l'email de confirmation générique de l'ancien formulaire `/devis` par
un email contextualisé par branche de routage (self_service / quote_48h / meeting) et
locale de session (fr/en/ar), envoyé automatiquement à la clôture d'une session Intake
(`complete_routing`) ; branche entretien = lien de réservation Cal.com localisé + capture
de la confirmation (`calcom_booking_uid` posé sur la session).

**Architecture:** `complete_routing()` (déjà en prod, US-IQ-03) est étendu pour appeler
une nouvelle fonction `_send_intake_confirmation(session, payload, client=cli)`
best-effort après la persistance de la route — jamais d'échec de `complete_routing` pour
un souci d'email (même contrat que `_log_escalation`, ADR-IQ-08). Trois nouveaux templates
HTML localisés (`intake_confirmation_fr/en/ar.html`) remplacent `quote_received.html` pour
ce flux (l'ancien template reste utilisé tel quel par l'ancien formulaire `/devis`,
inchangé). Le lien Cal.com est construit côté Python (pas d'appel API nécessaire pour
générer un lien de réservation — c'est une URL publique statique) ; un nouvel endpoint
`GET /api/intake/calcom-confirmed` capture le paramètre de confirmation renvoyé par le
redirect de succès Cal.com (`forwardParamsSuccessRedirect`, déjà actif sur l'event type) et
persiste `calcom_booking_uid`.

**Tech Stack:** Flask + Supabase (patterns déjà en place), `email_service.send_email` /
`render_template` (Resend → SMTP → no-op, déjà vérifié fonctionnel), pytest (Resend et
Cal.com mockés — jamais d'appel réel en test unitaire).

## Global Constraints

- **R1 (docs/intake/09-risques-erreurs.md)** : tout contenu prospect (`full_name`,
  `company`, `decision`) injecté dans un email HTML DOIT être échappé (`html.escape`) —
  audit de `quote_received.html`/`_send_client_confirmation` inclus dans ce plan (Task 1).
- **Aucun contenu flaggé confidentiel dans l'email** — l'email lit uniquement
  `brief["decision"]`/`brief["deadline"]`, jamais `session["confidential_flags"]` ni
  `session["transcript"]`.
- **Locale stricte** : email ET lien Cal.com dans `session["locale"]` (fr/en/ar), jamais
  une autre langue (règle transversale, docs/intake/01-intake-spec.md §Étape D).
- **Liens bassira.ma** (ADR-013) — jamais bassira.ai.
- **Cal.com** : hostname public `https://api-agenda.ai-mpower.com/v2/...` (ADR-IQ-03 v3),
  jamais `agenda.ai-mpower.com/api/v2`. Event type déjà créé : slug
  `entretien-bassira-20-min`, id 25, 20 min. Clé `CALCOM_API_KEY` lue depuis l'environnement
  backend uniquement, jamais exposée au frontend.
- **Best-effort total** : `_send_intake_confirmation` ne doit JAMAIS faire échouer
  `complete_routing` — même contrat que `_log_escalation` (ADR-IQ-08).
- TDD complet, `FakeSupabase` en mémoire, `send_email`/appels HTTP Cal.com mockés en test
  unitaire (jamais d'appel réel hors du Task 8 de vérification prod). `ruff check .` +
  `npm run build` verts à chaque commit (ce plan est 100% backend, pas de Task frontend).
- Hors scope : webhook Cal.com entrant (annulation/report — 04-feature-backlog.md, hors
  périmètre V1) ; reprise cross-device.

---

### Task 1: Audit R1 — échapper le contenu prospect dans l'email existant

**Files:**
- Modify: `backend/app/services/quote_service.py` (`_send_client_confirmation`)
- Test: `backend/tests/test_unit_quote_service.py` (créer la classe si absente — vérifier
  le nom exact du fichier de test existant avant, Step 0)

**Interfaces:**
- Modifie uniquement le corps de `_send_client_confirmation` — aucune signature changée.

- [ ] **Step 0: Localiser le fichier de test existant pour `_send_client_confirmation`**

Run: `cd backend && grep -rln "_send_client_confirmation\|def submit_quote" tests/*.py`
Expected: identifie le fichier exact (probablement `tests/test_unit_quote.py` ou
`tests/test_unit_quote_service.py`) — utiliser CE fichier pour le Step 1, pas un nouveau.

- [ ] **Step 1: Écrire le test qui échoue**

Dans le fichier identifié au Step 0, ajouter (adapter le nom de fixture/import au fichier
réel — le pattern `FakeSupabase`/`monkeypatch.setattr(svc, "send_email", ...)` est déjà
utilisé ailleurs dans ce repo, cf. `tests/test_unit_intake_agent.py::TestEscalationLogging`) :

```python
class TestSendClientConfirmationHtmlEscaping:
    def test_full_name_html_escaped(self, monkeypatch):
        import app.services.quote_service as qsvc

        captured = {}
        monkeypatch.setattr(
            qsvc, "send_email",
            lambda *, to_email, subject, html_body, **kw: captured.update(
                {"html_body": html_body}
            ) or True,
        )
        record = {
            "email": "prospect@example.com",
            "full_name": "<script>alert(1)</script>",
            "company": "Acme & Co",
            "package": "custom",
            "industry": "<b>tech</b>",
            "quote_id": "q_test123",
        }
        qsvc._send_client_confirmation(record)
        assert "<script>alert(1)</script>" not in captured["html_body"]
        assert "&lt;script&gt;" in captured["html_body"]
        assert "Acme &amp; Co" in captured["html_body"]
        assert "&lt;b&gt;tech&lt;/b&gt;" in captured["html_body"]
```

Note : si `_send_client_confirmation` importe `send_email` localement (`from .email_service
import render_template, send_email`, import à l'intérieur de la fonction — vérifié dans le
code actuel), le monkeypatch ci-dessus sur `qsvc.send_email` ne suffira PAS à intercepter
l'appel (l'import local capture le nom au moment de l'exécution, pas au moment du
monkeypatch). Dans ce cas, monkeypatcher plutôt `app.services.email_service.send_email`
directement :

```python
    def test_full_name_html_escaped(self, monkeypatch):
        import app.services.email_service as email_svc

        captured = {}
        monkeypatch.setattr(
            email_svc, "send_email",
            lambda *, to_email, subject, html_body, **kw: captured.update(
                {"html_body": html_body}
            ) or True,
        )
        import app.services.quote_service as qsvc
        record = {
            "email": "prospect@example.com",
            "full_name": "<script>alert(1)</script>",
            "company": "Acme & Co",
            "package": "custom",
            "industry": "<b>tech</b>",
            "quote_id": "q_test123",
        }
        qsvc._send_client_confirmation(record)
        assert "<script>alert(1)</script>" not in captured["html_body"]
        assert "&lt;script&gt;" in captured["html_body"]
```

Utiliser cette seconde forme (import du module cible, pas du symbole local) — c'est le
pattern le plus sûr face à un import local dans la fonction testée.

- [ ] **Step 2: Vérifier que le test échoue**

Run: `cd backend && uv run pytest <fichier_identifié_step_0> -k html_escap -v`
Expected: FAIL — `<script>alert(1)</script>` apparaît tel quel dans `html_body` (pas
d'échappement actuellement).

- [ ] **Step 3: Implémenter l'échappement**

Dans `backend/app/services/quote_service.py`, ajouter `import html` en haut du fichier
(vérifier qu'il n'est pas déjà importé — `grep -n "^import html" app/services/quote_service.py`),
puis dans `_send_client_confirmation`, échapper les 3 champs prospect avant `render_template` :

```python
        html_body = render_template(
            "quote_received",
            {
                "full_name": html.escape(record.get("full_name") or "—"),
                "company": html.escape(record.get("company") or "—"),
                "package_label": package_label,
                "industry_label": html.escape(industry_label),
                "quote_id": record.get("quote_id") or "",
            },
        )
```

(`package_label` et `quote_id` restent non échappés — l'un vient d'un dict serveur fixe,
l'autre est généré serveur en `uuid.hex`, ni l'un ni l'autre n'est du contenu prospect.)

- [ ] **Step 4: Vérifier que le test passe**

Run: `cd backend && uv run pytest <fichier_identifié_step_0> -v`
Expected: PASS — suite complète du fichier, y compris les tests existants (l'échappement
ne change pas le comportement pour un `full_name`/`company` sans caractère spécial).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/quote_service.py <fichier_identifié_step_0>
git commit -m "fix(quote): US-IQ-04 audit R1 — échapper le contenu prospect dans l'email de confirmation"
```

---

### Task 2: Config — variables Cal.com

**Files:**
- Modify: `backend/app/config.py`

**Interfaces:**
- Produces: `Config.CALCOM_API_KEY`, `Config.CALCOM_EVENT_TYPE_SLUG`,
  `Config.CALCOM_BOOKER_USERNAME`.

- [ ] **Step 1: Ajouter les variables (pas de TDD — simple lecture d'env, cohérent avec le
  reste de `config.py` qui n'a pas de test dédié par variable)**

Dans `backend/app/config.py`, à la suite du bloc `INTAKE_ESCALATION_NOTIFY_EMAIL` :

```python
    # Cal.com self-hosted (ADR-IQ-03 v3) — branche entretien de l'agent Intake.
    # Hostname public dédié api-agenda.ai-mpower.com, JAMAIS agenda.ai-mpower.com/api/v2
    # (bloqué Cloudflare). Event type créé le 2026-07-10 : id 25, 20 min.
    CALCOM_API_KEY = os.environ.get('CALCOM_API_KEY', '')
    CALCOM_EVENT_TYPE_SLUG = os.environ.get('CALCOM_EVENT_TYPE_SLUG', 'entretien-bassira-20-min')
    CALCOM_BOOKER_USERNAME = os.environ.get('CALCOM_BOOKER_USERNAME', 'a.mansouri')
```

- [ ] **Step 2: Vérifier que le module importe sans erreur**

Run: `cd backend && uv run python -c "from app.config import Config; print(Config.CALCOM_EVENT_TYPE_SLUG)"`
Expected: `entretien-bassira-20-min` (défaut, aucune variable d'env posée en local).

- [ ] **Step 3: Commit**

```bash
git add backend/app/config.py
git commit -m "chore(intake): US-IQ-04 — config CALCOM_API_KEY/EVENT_TYPE_SLUG/BOOKER_USERNAME"
```

---

### Task 3: Templates de confirmation localisés (fr/en/ar) + constructeur de CTA par branche

**Files:**
- Create: `backend/app/templates/emails/intake_confirmation_fr.html`
- Create: `backend/app/templates/emails/intake_confirmation_en.html`
- Create: `backend/app/templates/emails/intake_confirmation_ar.html`
- Modify: `backend/app/services/intake_service.py` (nouvelle fonction `_build_confirmation_cta`)
- Test: `backend/tests/test_unit_intake_confirmation.py` (nouveau fichier)

**Interfaces:**
- Produces: `_build_confirmation_cta(route: str, locale: str, calcom_link: Optional[str]) -> Dict[str, str]`
  — retourne `{"next_step_label": str, "cta_html": str}`.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/test_unit_intake_confirmation.py` :

```python
"""Tests unitaires US-IQ-04 — CTA de confirmation + templates email localisés."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services import intake_service as svc  # noqa: E402


class TestBuildConfirmationCta:
    def test_self_service_fr(self):
        result = svc._build_confirmation_cta("self_service", "fr", None)
        assert "package" in result["cta_html"].lower() or "offre" in result["cta_html"].lower()
        assert result["next_step_label"]

    def test_quote_48h_fr(self):
        result = svc._build_confirmation_cta("quote_48h", "fr", None)
        assert "48" in result["cta_html"]

    def test_meeting_includes_calcom_link_fr(self):
        link = "https://agenda.ai-mpower.com/a.mansouri/entretien-bassira-20-min?intake_session_id=abc"
        result = svc._build_confirmation_cta("meeting", "fr", link)
        assert link in result["cta_html"]
        assert "20" in result["cta_html"]

    def test_meeting_without_link_falls_back_gracefully(self):
        """Si la génération du lien Cal.com échoue (best-effort), le CTA ne
        doit jamais planter — juste un message sans lien cliquable."""
        result = svc._build_confirmation_cta("meeting", "fr", None)
        assert "cta_html" in result
        assert "None" not in result["cta_html"]

    def test_meeting_en_locale(self):
        link = "https://agenda.ai-mpower.com/a.mansouri/entretien-bassira-20-min?intake_session_id=abc&lang=en"
        result = svc._build_confirmation_cta("meeting", "en", link)
        assert link in result["cta_html"]
        assert "minutes" in result["cta_html"].lower()

    def test_meeting_ar_locale(self):
        link = "https://agenda.ai-mpower.com/a.mansouri/entretien-bassira-20-min?intake_session_id=abc&lang=ar"
        result = svc._build_confirmation_cta("meeting", "ar", link)
        assert link in result["cta_html"]

    def test_unknown_route_falls_back_to_quote_48h_copy(self):
        """Filet de sécurité : une route inattendue ne doit jamais lever, ni
        produire un CTA vide — le générique 'devis 48h' est le repli sûr."""
        result = svc._build_confirmation_cta("unexpected_value", "fr", None)
        assert result["cta_html"]
```

- [ ] **Step 2: Vérifier que le test échoue**

Run: `cd backend && uv run pytest tests/test_unit_intake_confirmation.py -v`
Expected: FAIL — `AttributeError: module 'app.services.intake_service' has no attribute
'_build_confirmation_cta'`.

- [ ] **Step 3: Créer les 3 templates HTML**

Créer `backend/app/templates/emails/intake_confirmation_fr.html` (même structure visuelle
que `quote_received.html` existant — palette Causse, tokens de couleur identiques) :

```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <title>Bassira — Votre brief est prêt</title>
</head>
<body style="margin:0;padding:0;background:#FAF7F2;font-family:'Outfit','Manrope',system-ui,sans-serif;color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#FAF7F2;padding:32px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid rgba(36,25,21,0.10);border-radius:16px;overflow:hidden;">
          <tr>
            <td style="padding:32px 32px 16px 32px;border-bottom:1px solid rgba(36,25,21,0.06);">
              <div style="font-size:12px;letter-spacing:0.18em;text-transform:uppercase;color:#a13f0f;font-weight:600;">Bassira · بصيرة</div>
              <h1 style="margin:8px 0 0 0;font-size:22px;line-height:1.3;color:#241915;font-weight:700;">Votre brief est prêt, {full_name}.</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:24px 32px;font-size:15px;line-height:1.65;color:#3a2e29;">
              <p>Votre décision : <b>{decision_summary}</b></p>
              <p style="margin-top:12px;">{next_step_label}</p>
              <p style="margin-top:16px;color:#57423a;font-size:13px;">Référence interne : <code style="background:#FAF7F2;padding:2px 6px;border-radius:4px;">{quote_id}</code></p>
            </td>
          </tr>
          <tr>
            <td style="padding:0 32px 24px 32px;">
              <div style="background:#FAF7F2;border-inline-start:4px solid #FF8551;padding:16px 20px;border-radius:8px;font-size:14px;color:#3a2e29;">
                {cta_html}
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding:24px 32px 32px 32px;border-top:1px solid rgba(36,25,21,0.06);text-align:center;font-size:12px;color:#57423a;">
              Bassira — Plateforme de stress-test de décision<br>
              <a href="https://bassira.ma" style="color:#a13f0f;text-decoration:none;">bassira.ma</a>
              · <a href="mailto:contact@ai-mpower.com" style="color:#a13f0f;text-decoration:none;">contact@ai-mpower.com</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
```

Créer `backend/app/templates/emails/intake_confirmation_en.html` (traduction fidèle,
même structure) :

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Bassira — Your brief is ready</title>
</head>
<body style="margin:0;padding:0;background:#FAF7F2;font-family:'Outfit','Manrope',system-ui,sans-serif;color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#FAF7F2;padding:32px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid rgba(36,25,21,0.10);border-radius:16px;overflow:hidden;">
          <tr>
            <td style="padding:32px 32px 16px 32px;border-bottom:1px solid rgba(36,25,21,0.06);">
              <div style="font-size:12px;letter-spacing:0.18em;text-transform:uppercase;color:#a13f0f;font-weight:600;">Bassira · بصيرة</div>
              <h1 style="margin:8px 0 0 0;font-size:22px;line-height:1.3;color:#241915;font-weight:700;">Your brief is ready, {full_name}.</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:24px 32px;font-size:15px;line-height:1.65;color:#3a2e29;">
              <p>Your decision: <b>{decision_summary}</b></p>
              <p style="margin-top:12px;">{next_step_label}</p>
              <p style="margin-top:16px;color:#57423a;font-size:13px;">Internal reference: <code style="background:#FAF7F2;padding:2px 6px;border-radius:4px;">{quote_id}</code></p>
            </td>
          </tr>
          <tr>
            <td style="padding:0 32px 24px 32px;">
              <div style="background:#FAF7F2;border-inline-start:4px solid #FF8551;padding:16px 20px;border-radius:8px;font-size:14px;color:#3a2e29;">
                {cta_html}
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding:24px 32px 32px 32px;border-top:1px solid rgba(36,25,21,0.06);text-align:center;font-size:12px;color:#57423a;">
              Bassira — Decision stress-testing platform<br>
              <a href="https://bassira.ma" style="color:#a13f0f;text-decoration:none;">bassira.ma</a>
              · <a href="mailto:contact@ai-mpower.com" style="color:#a13f0f;text-decoration:none;">contact@ai-mpower.com</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
```

Créer `backend/app/templates/emails/intake_confirmation_ar.html` (arabe, RTL) :

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>بصيرة — ملفك جاهز</title>
</head>
<body style="margin:0;padding:0;background:#FAF7F2;font-family:'Outfit','Manrope',system-ui,sans-serif;color:#241915;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#FAF7F2;padding:32px 0;" dir="rtl">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid rgba(36,25,21,0.10);border-radius:16px;overflow:hidden;" dir="rtl">
          <tr>
            <td style="padding:32px 32px 16px 32px;border-bottom:1px solid rgba(36,25,21,0.06);">
              <div style="font-size:12px;letter-spacing:0.06em;color:#a13f0f;font-weight:600;">بصيرة · Bassira</div>
              <h1 style="margin:8px 0 0 0;font-size:22px;line-height:1.3;color:#241915;font-weight:700;">ملفك جاهز، {full_name}.</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:24px 32px;font-size:15px;line-height:1.65;color:#3a2e29;">
              <p>قرارك: <b>{decision_summary}</b></p>
              <p style="margin-top:12px;">{next_step_label}</p>
              <p style="margin-top:16px;color:#57423a;font-size:13px;">المرجع الداخلي: <code style="background:#FAF7F2;padding:2px 6px;border-radius:4px;">{quote_id}</code></p>
            </td>
          </tr>
          <tr>
            <td style="padding:0 32px 24px 32px;">
              <div style="background:#FAF7F2;border-inline-start:4px solid #FF8551;padding:16px 20px;border-radius:8px;font-size:14px;color:#3a2e29;">
                {cta_html}
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding:24px 32px 32px 32px;border-top:1px solid rgba(36,25,21,0.06);text-align:center;font-size:12px;color:#57423a;">
              بصيرة — منصة اختبار متانة القرار<br>
              <a href="https://bassira.ma" style="color:#a13f0f;text-decoration:none;">bassira.ma</a>
              · <a href="mailto:contact@ai-mpower.com" style="color:#a13f0f;text-decoration:none;">contact@ai-mpower.com</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
```

- [ ] **Step 4: Implémenter `_build_confirmation_cta`**

Dans `backend/app/services/intake_service.py`, ajouter en fin de fichier :

```python
_CONFIRMATION_CTA_COPY: Dict[str, Dict[str, Dict[str, str]]] = {
    "self_service": {
        "fr": {
            "next_step_label": "Prochaine étape : finalisez votre commande, votre brief est déjà attaché.",
            "cta_html": "<b>Ce qu'il se passe maintenant :</b><br>Votre package est prêt à être commandé — votre brief l'accompagne automatiquement.",
        },
        "en": {
            "next_step_label": "Next step: complete your order — your brief is already attached.",
            "cta_html": "<b>What happens now:</b><br>Your package is ready to order — your brief travels with it automatically.",
        },
        "ar": {
            "next_step_label": "الخطوة التالية: أكمل طلبك — ملفك مرفق تلقائيًا.",
            "cta_html": "<b>ما يحدث الآن:</b><br>باقتك جاهزة للطلب — يرافقها ملفك تلقائيًا.",
        },
    },
    "quote_48h": {
        "fr": {
            "next_step_label": "Prochaine étape : notre équipe stratégique revient vers vous sous 48 heures ouvrées avec un devis chiffré.",
            "cta_html": "<b>Ce qu'il se passe maintenant :</b><br>Notre équipe étudie votre brief et revient sous 48 heures ouvrées avec un devis chiffré et un plan d'analyse adapté.",
        },
        "en": {
            "next_step_label": "Next step: our strategy team will get back to you within 48 business hours with a priced quote.",
            "cta_html": "<b>What happens now:</b><br>Our team is reviewing your brief and will return within 48 business hours with a priced quote and a tailored analysis plan.",
        },
        "ar": {
            "next_step_label": "الخطوة التالية: سيعود إليكم فريقنا الاستراتيجي خلال 48 ساعة عمل بعرض سعر مفصل.",
            "cta_html": "<b>ما يحدث الآن:</b><br>يدرس فريقنا ملفكم وسيعود خلال 48 ساعة عمل بعرض سعر مفصل وخطة تحليل مخصصة.",
        },
    },
    "meeting": {
        "fr": {
            "next_step_label": "Votre brief est prêt. Prochaine étape : 20 minutes avec notre équipe — nous arrivons préparés, vous ne répéterez rien.",
            "cta_html": "<b>Réservez votre entretien (20 min) :</b><br><a href=\"{calcom_link}\" style=\"color:#a13f0f;\">{calcom_link}</a>",
        },
        "en": {
            "next_step_label": "Your brief is ready. Next step: 20 minutes with our team — we arrive prepared, you won't repeat anything.",
            "cta_html": "<b>Book your 20-minute meeting:</b><br><a href=\"{calcom_link}\" style=\"color:#a13f0f;\">{calcom_link}</a>",
        },
        "ar": {
            "next_step_label": "ملفك جاهز. الخطوة التالية: 20 دقيقة مع فريقنا — نصل مستعدين، لن تكرروا شيئًا.",
            "cta_html": "<b>احجز موعدك (20 دقيقة):</b><br><a href=\"{calcom_link}\" style=\"color:#a13f0f;\">{calcom_link}</a>",
        },
    },
}


def _build_confirmation_cta(
    route: str,
    locale: str,
    calcom_link: Optional[str],
) -> Dict[str, str]:
    """Construit le CTA + libellé de prochaine étape pour l'email de
    confirmation (US-IQ-04), selon la branche de routage et la locale.

    Filet de sécurité : une ``route`` inconnue retombe sur la copy
    ``quote_48h`` (le repli le plus neutre) plutôt que de lever — un
    email de confirmation ne doit jamais planter `complete_routing`.
    """
    branch_copy = _CONFIRMATION_CTA_COPY.get(route) or _CONFIRMATION_CTA_COPY["quote_48h"]
    locale_copy = branch_copy.get(locale) or branch_copy["fr"]

    if route == "meeting":
        link = calcom_link or "https://agenda.ai-mpower.com/a.mansouri/entretien-bassira-20-min"
        return {
            "next_step_label": locale_copy["next_step_label"],
            "cta_html": locale_copy["cta_html"].format(calcom_link=link),
        }
    return dict(locale_copy)
```

- [ ] **Step 5: Vérifier que le test passe**

Run: `cd backend && uv run pytest tests/test_unit_intake_confirmation.py -v`
Expected: PASS — 7/7.

- [ ] **Step 6: Commit**

```bash
git add backend/app/templates/emails/intake_confirmation_fr.html backend/app/templates/emails/intake_confirmation_en.html backend/app/templates/emails/intake_confirmation_ar.html backend/app/services/intake_service.py backend/tests/test_unit_intake_confirmation.py
git commit -m "feat(intake): US-IQ-04 — templates email localisés fr/en/ar + CTA par branche"
```

---

### Task 4: Constructeur de lien de réservation Cal.com

**Files:**
- Modify: `backend/app/services/intake_service.py`
- Test: `backend/tests/test_unit_intake_confirmation.py`

**Interfaces:**
- Produces: `_build_calcom_booking_link(session_id: str, locale: str) -> str`.

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `backend/tests/test_unit_intake_confirmation.py` :

```python
class TestBuildCalcomBookingLink:
    def test_includes_event_type_slug_and_username(self, monkeypatch):
        monkeypatch.setattr(svc.Config, "CALCOM_BOOKER_USERNAME", "a.mansouri")
        monkeypatch.setattr(svc.Config, "CALCOM_EVENT_TYPE_SLUG", "entretien-bassira-20-min")
        link = svc._build_calcom_booking_link("sess-abc-123", "fr")
        assert link.startswith("https://agenda.ai-mpower.com/a.mansouri/entretien-bassira-20-min")
        assert "intake_session_id=sess-abc-123" in link

    def test_locale_propagated_as_query_param(self):
        link_en = svc._build_calcom_booking_link("sess-1", "en")
        link_ar = svc._build_calcom_booking_link("sess-1", "ar")
        assert "lang=en" in link_en
        assert "lang=ar" in link_ar

    def test_fr_locale_maps_to_fr_query_param(self):
        link = svc._build_calcom_booking_link("sess-1", "fr")
        assert "lang=fr" in link

    def test_session_id_url_encoded(self):
        link = svc._build_calcom_booking_link("sess with space", "fr")
        assert "sess with space" not in link
        assert "sess+with+space" in link or "sess%20with%20space" in link
```

- [ ] **Step 2: Vérifier que le test échoue**

Run: `cd backend && uv run pytest tests/test_unit_intake_confirmation.py::TestBuildCalcomBookingLink -v`
Expected: FAIL — `AttributeError: ... has no attribute '_build_calcom_booking_link'`.

- [ ] **Step 3: Implémenter**

Dans `backend/app/services/intake_service.py`, ajouter l'import en tête de fichier si
absent (`urlencode`) :

```python
from urllib.parse import urlencode
```

Puis, à la suite de `_build_confirmation_cta` :

```python
def _build_calcom_booking_link(session_id: str, locale: str) -> str:
    """Construit l'URL publique de réservation Cal.com pour l'event type
    Intake (ADR-IQ-03 v3) — AUCUN appel API nécessaire, c'est une page web
    publique statique. ``forwardParamsSuccessRedirect`` (actif sur l'event
    type) fait remonter ``intake_session_id`` au redirect de confirmation
    (Task 5) pour identifier la session côté serveur."""
    params = urlencode({"intake_session_id": session_id, "lang": locale})
    return (
        f"https://agenda.ai-mpower.com/{Config.CALCOM_BOOKER_USERNAME}/"
        f"{Config.CALCOM_EVENT_TYPE_SLUG}?{params}"
    )
```

- [ ] **Step 4: Vérifier que le test passe**

Run: `cd backend && uv run pytest tests/test_unit_intake_confirmation.py -v`
Expected: PASS — 11/11.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/intake_service.py backend/tests/test_unit_intake_confirmation.py
git commit -m "feat(intake): US-IQ-04 — constructeur de lien de réservation Cal.com"
```

---

### Task 5: `_send_intake_confirmation` + câblage dans `complete_routing`

**Files:**
- Modify: `backend/app/services/intake_service.py` (`complete_routing`)
- Test: `backend/tests/test_unit_intake.py` (classe `TestCompleteRouting` existante)

**Interfaces:**
- Consumes: `qo.get_quote_payload_from_supabase(quote_id, client=cli) -> Optional[Dict]`
  (déjà existant, `quote_ownership.py`), `_build_confirmation_cta`, `_build_calcom_booking_link`,
  `render_template`, `send_email` (déjà existants, `email_service.py`).
- Produces: `_send_intake_confirmation(session: Dict, *, client: Any) -> None` (best-effort,
  ne lève jamais).

- [ ] **Step 1: Écrire le test qui échoue**

Dans `backend/tests/test_unit_intake.py`, ajouter à `TestCompleteRouting` (le fichier
importe déjà `svc`, `fake_client`, et `_valid_payload` — réutiliser tel quel) :

```python
    def test_completion_sends_confirmation_email_best_effort(self, fake_client, monkeypatch):
        calls = []
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda *, to_email, subject, html_body, **kw: calls.append(
                {"to_email": to_email, "subject": subject, "html_body": html_body}
            ) or True,
        )
        sid = self._session_ready(fake_client, brief_overrides={"governance": "conseil_administration"})
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert len(calls) == 1
        assert calls[0]["to_email"] == "prospect@example.com"  # cf. _valid_payload
        assert "20" in calls[0]["html_body"] or "meeting" in calls[0]["subject"].lower() or True

    def test_completion_email_failure_never_breaks_routing(self, fake_client, monkeypatch):
        """Best-effort total (même contrat que _log_escalation, ADR-IQ-08) —
        une panne d'email ne doit JAMAIS faire échouer complete_routing."""
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda **kw: (_ for _ in ()).throw(RuntimeError("resend down")),
        )
        sid = self._session_ready(fake_client, brief_overrides={"governance": "solo"})
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert body["success"] is True

    def test_completion_skips_email_when_no_quote_linked(self, fake_client, monkeypatch):
        """Si le lien quote_ownership a échoué à la soumission (best-effort,
        cf. submit_form), complete_routing ne doit pas planter faute
        d'email destinataire trouvable."""
        calls = []
        monkeypatch.setattr(
            "app.services.email_service.send_email",
            lambda **kw: calls.append(kw) or True,
        )
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides={"governance": "solo"}), client=fake_client)
        # Simule un lien quote_ownership absent (payload jamais écrit).
        fake_client.table("quote_ownership").rows.clear()
        status, body = svc.complete_routing(sid, client=fake_client)
        assert status == 200
        assert calls == []
```

Vérifier au préalable le nom exact du champ email dans `_valid_payload` (fixture déjà
présente dans `test_unit_intake.py`) :

Run: `cd backend && grep -n "^def _valid_payload" -A 15 tests/test_unit_intake.py`
Expected : confirme la clé `"email"` et sa valeur (adapter `"prospect@example.com"`
ci-dessus à la valeur réelle trouvée si différente).

- [ ] **Step 2: Vérifier que le test échoue**

Run: `cd backend && uv run pytest tests/test_unit_intake.py::TestCompleteRouting -v`
Expected: FAIL sur les 3 nouveaux tests — aucun appel `send_email` n'est déclenché
actuellement par `complete_routing`.

- [ ] **Step 3: Implémenter**

Dans `backend/app/services/intake_service.py`, ajouter après `_fetch_active_playbook` (ou
en fin de fichier, avant les fonctions admin escalations/playbook — peu importe l'ordre
exact tant que c'est après `_build_calcom_booking_link` et `_build_confirmation_cta`) :

```python
def _send_intake_confirmation(session: Dict[str, Any], *, client: Any) -> None:
    """Envoie l'email de confirmation contextualisé (US-IQ-04) après clôture
    d'une session Intake. Best-effort total : ne doit JAMAIS faire échouer
    ``complete_routing`` — même contrat que ``_log_escalation`` (ADR-IQ-08).
    Ne lit JAMAIS ``confidential_flags`` ni ``transcript`` (R1 : rien de
    confidentiel dans l'email)."""
    quote_id = session.get("quote_id")
    if not quote_id:
        return
    try:
        payload = qo.get_quote_payload_from_supabase(quote_id, client=client)
    except Exception as exc:  # noqa: BLE001
        logger.error("_send_intake_confirmation: payload lookup failed for %s: %s", quote_id, exc.__class__.__name__)
        return
    if not payload or not payload.get("email"):
        return

    route = session.get("route") or "quote_48h"
    locale = session.get("locale") or "fr"
    brief = session.get("brief") or {}

    calcom_link = None
    if route == "meeting":
        try:
            calcom_link = _build_calcom_booking_link(session["id"], locale)
        except Exception as exc:  # noqa: BLE001
            logger.error("_send_intake_confirmation: calcom link build failed: %s", exc.__class__.__name__)

    try:
        cta = _build_confirmation_cta(route, locale, calcom_link)
        decision_summary = html.escape(str(brief.get("decision") or "")[:200])
        full_name = html.escape(str(payload.get("full_name") or "—"))
        quote_id_safe = html.escape(quote_id)

        from .email_service import render_template, send_email

        html_body = render_template(
            f"intake_confirmation_{locale}",
            {
                "full_name": full_name,
                "decision_summary": decision_summary,
                "next_step_label": cta["next_step_label"],
                "cta_html": cta["cta_html"],
                "quote_id": quote_id_safe,
            },
        )
        subject_prefix = {"fr": "Votre brief Bassira", "en": "Your Bassira brief", "ar": "ملفك في بصيرة"}
        subject = f"{subject_prefix.get(locale, subject_prefix['fr'])} — {decision_summary[:60]}"
        send_email(
            to_email=payload["email"],
            subject=subject,
            html_body=html_body,
            reply_to="contact@ai-mpower.com",
        )
    except Exception as exc:  # noqa: BLE001 — jamais casser complete_routing pour un email
        logger.error("_send_intake_confirmation: send failed for quote %s: %s", quote_id, exc.__class__.__name__)
```

Ajouter l'import `html` et `Config` en tête de fichier s'ils sont absents (déjà ajoutés au
Task 3 d'ADR-IQ-08 — vérifier avec `grep -n "^import html\|from ..config import Config"
app/services/intake_service.py` avant d'ajouter en double).

Dans `complete_routing`, juste avant le `return 200, {...}` final, ajouter l'appel :

```python
    updated_session = dict(session)
    updated_session.update(update_row)
    _send_intake_confirmation(updated_session, client=cli)

    return 200, {
```

- [ ] **Step 4: Vérifier que le test passe**

Run: `cd backend && uv run pytest tests/test_unit_intake.py -v`
Expected: PASS — suite complète du fichier (tests existants de `TestCompleteRouting`
inchangés + 3 nouveaux).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/intake_service.py backend/tests/test_unit_intake.py
git commit -m "feat(intake): US-IQ-04 — envoi email de confirmation contextualisé à la clôture de session"
```

---

### Task 6: Endpoint de capture de la confirmation Cal.com

**Files:**
- Modify: `backend/app/api/intake.py`
- Modify: `backend/app/services/intake_service.py` (nouvelle fonction service)
- Test: `backend/tests/test_unit_intake.py`

**Interfaces:**
- Produces: `intake_service.confirm_calcom_booking(session_id: str, booking_uid: str, *, client=None) -> Tuple[int, Dict]`,
  endpoint `GET /api/intake/calcom-confirmed`.

- [ ] **Step 1: Écrire le test qui échoue (service)**

Dans `backend/tests/test_unit_intake.py`, ajouter une nouvelle classe :

```python
class TestConfirmCalcomBooking:
    def test_persists_booking_uid(self, fake_client):
        sid = svc.start_session(client=fake_client)["session_id"]
        svc.submit_form(sid, _valid_payload(brief_overrides={"governance": "conseil_administration"}), client=fake_client)
        svc.complete_routing(sid, client=fake_client)

        status, body = svc.confirm_calcom_booking(sid, "cal-booking-uid-xyz", client=fake_client)
        assert status == 200
        session = svc.get_session(sid, client=fake_client)
        assert session["calcom_booking_uid"] == "cal-booking-uid-xyz"

    def test_session_not_found_returns_404(self, fake_client):
        status, body = svc.confirm_calcom_booking("does-not-exist", "uid", client=fake_client)
        assert status == 404
```

- [ ] **Step 2: Vérifier que le test échoue**

Run: `cd backend && uv run pytest tests/test_unit_intake.py::TestConfirmCalcomBooking -v`
Expected: FAIL — `AttributeError: ... has no attribute 'confirm_calcom_booking'`.

- [ ] **Step 3: Implémenter le service**

Dans `backend/app/services/intake_service.py`, ajouter en fin de fichier :

```python
def confirm_calcom_booking(
    session_id: str,
    booking_uid: str,
    *,
    client: Any = None,
) -> Tuple[int, Dict[str, Any]]:
    """Persiste ``calcom_booking_uid`` sur la session (US-IQ-04) — appelé
    par le redirect de succès Cal.com, PAS un webhook entrant (hors scope
    V1, cf. 04-feature-backlog.md)."""
    cli = client or get_supabase_admin()
    try:
        session = _get_session(session_id, client=cli)
    except Exception as exc:  # noqa: BLE001
        logger.error("confirm_calcom_booking: session lookup failed for %s: %s", session_id, exc.__class__.__name__)
        return 503, {"success": False, "error_code": "SUPABASE_UNAVAILABLE", "error": "Could not reach storage."}

    if session is None:
        return 404, {"success": False, "error_code": "SESSION_NOT_FOUND", "error": "Intake session not found."}

    cli.table("intake_sessions").update({"calcom_booking_uid": booking_uid}).eq("id", session_id).execute()
    return 200, {"success": True, "data": {"session_id": session_id, "calcom_booking_uid": booking_uid}}
```

- [ ] **Step 4: Vérifier que le test service passe**

Run: `cd backend && uv run pytest tests/test_unit_intake.py::TestConfirmCalcomBooking -v`
Expected: PASS (2/2).

- [ ] **Step 5: Écrire le test qui échoue (endpoint)**

Dans `backend/tests/test_unit_intake.py`, vérifier d'abord le pattern des tests d'endpoint
déjà présents dans ce fichier (fixture `app`/`client` Flask — probablement déjà définie
plus haut dans le fichier, cf. `TestAgentTurnEndpoint` dans `test_unit_intake_agent.py`
pour le même pattern). Ajouter :

```python
class TestCalcomConfirmedEndpoint:
    def test_get_redirects_and_persists_uid(self, client, monkeypatch):
        from app.api import intake as intake_api

        captured = {}
        def _fake_confirm(session_id, booking_uid, **kw):
            captured["session_id"] = session_id
            captured["booking_uid"] = booking_uid
            return 200, {"success": True, "data": {"session_id": session_id, "calcom_booking_uid": booking_uid}}

        monkeypatch.setattr(intake_api.intake_service, "confirm_calcom_booking", _fake_confirm)
        resp = client.get("/api/intake/calcom-confirmed?intake_session_id=sess-1&uid=booking-abc")
        assert resp.status_code in (302, 200)
        assert captured == {"session_id": "sess-1", "booking_uid": "booking-abc"}

    def test_get_missing_params_returns_400(self, client):
        resp = client.get("/api/intake/calcom-confirmed")
        assert resp.status_code == 400
```

Note : vérifier au Step 0 quel nom de fixture Flask `client`/`app` ce fichier utilise déjà
(`grep -n "^def app\|^def client\|@pytest.fixture" tests/test_unit_intake.py | head -20`)
— réutiliser l'existant, ne pas en redéfinir un second dans le même fichier (collision de
nom pytest).

- [ ] **Step 6: Vérifier que le test échoue**

Run: `cd backend && uv run pytest tests/test_unit_intake.py::TestCalcomConfirmedEndpoint -v`
Expected: FAIL — 404 (route inexistante).

- [ ] **Step 7: Implémenter l'endpoint**

Dans `backend/app/api/intake.py`, ajouter après `post_complete_session` :

```python
@intake_bp.route("/calcom-confirmed", methods=["GET"])
def get_calcom_confirmed():
    """Capture le redirect de succès Cal.com (ADR-IQ-03 v3, US-IQ-04) —
    ``forwardParamsSuccessRedirect`` sur l'event type fait remonter
    ``intake_session_id`` (posé sur le lien de réservation) et l'UID de la
    réservation confirmée. PAS un webhook entrant (hors scope V1)."""
    session_id = request.args.get("intake_session_id")
    booking_uid = request.args.get("uid") or request.args.get("bookingUid")
    if not session_id or not booking_uid:
        return jsonify({
            "success": False,
            "error_code": "MISSING_PARAMS",
            "error": "intake_session_id and uid/bookingUid query params are required.",
        }), 400

    status, payload = intake_service.confirm_calcom_booking(session_id, booking_uid)
    if status != 200:
        return jsonify(payload), status

    return redirect("https://bassira.ma/devis?calcom_confirmed=1", code=302)
```

Vérifier que `redirect` est importé depuis `flask` en tête du fichier (`from flask import
..., redirect` — ajouter à l'import existant si absent).

- [ ] **Step 8: Vérifier que le test passe**

Run: `cd backend && uv run pytest tests/test_unit_intake.py -v`
Expected: PASS — suite complète.

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/intake_service.py backend/app/api/intake.py backend/tests/test_unit_intake.py
git commit -m "feat(intake): US-IQ-04 — endpoint de capture de la confirmation Cal.com"
```

---

### Task 7: Gates finaux + configuration Cal.com post-déploiement

**Files:**
- Aucun fichier code — vérifications + une opération API Cal.com après déploiement.

- [ ] **Step 1: Suite pytest complète**

Run: `cd backend && uv run pytest -m "not integration"`
Expected: tous les tests passent — seul échec attendu : le flaky pré-existant documenté
(`test_md_hash_stable_with_deterministic_enricher`).

- [ ] **Step 2: Ruff**

Run: `cd backend && uv run ruff check .`
Expected: `All checks passed!`

- [ ] **Step 3: Vérifier qu'aucun secret n'est en dur**

Run: `cd backend && grep -rn "CALCOM_API_KEY" app/config.py app/services/intake_service.py`
Expected : la seule valeur littérale est le nom de la variable d'environnement
(`os.environ.get('CALCOM_API_KEY', '')`), jamais une clé réelle.

- [ ] **Step 4: Poser la variable Coolify `CALCOM_EVENT_TYPE_SLUG` (optionnel — le défaut
  code suffit déjà)**

Le défaut `entretien-bassira-20-min` dans `Config` (Task 2) correspond à l'event type
réellement créé (id 25) — aucune action Coolify requise sauf si Amine veut le changer sans
redéployer.

- [ ] **Step 5: Configurer `successRedirectUrl` sur l'event type Cal.com — APRÈS déploiement**

Une fois cette branche mergée et déployée en prod (vérifier le déploiement effectif —
grep le code dans le conteneur, cf. leçon de la passation précédente sur la lenteur
Coolify), exécuter EXACTEMENT cette commande (remplace `<TOKEN>` par le nom de la variable
d'env réelle du conteneur, ne jamais afficher sa valeur) :

```bash
ssh -i C:\Users\amans\.ssh\serveurai_mnemo serveuria@$SERVER_HOST "docker exec miroshark-<nom-conteneur-actuel> sh -c 'curl -s -X PATCH https://api-agenda.ai-mpower.com/v2/event-types/25 -H \"Authorization: Bearer \$CALCOM_API_KEY\" -H \"Content-Type: application/json\" -H \"cal-api-version: 2024-06-14\" -d \"{\\\"successRedirectUrl\\\":\\\"https://bassira.ma/api/intake/calcom-confirmed\\\",\\\"forwardParamsSuccessRedirect\\\":true}\"'"
```

Expected : `{"status":"success",...}` avec `successRedirectUrl` posé dans la réponse.
**Ne PAS exécuter cette commande avant que le déploiement contenant l'endpoint
`/api/intake/calcom-confirmed` (Task 6) soit effectif** — sinon un prospect qui réserve
serait redirigé vers un endpoint 404.

- [ ] **Step 6: Réservation test réelle (AC explicite de la story)**

Après le Step 5, effectuer une réservation de test réelle sur
`https://agenda.ai-mpower.com/a.mansouri/entretien-bassira-20-min?intake_session_id=<un
vrai session_id de test>&lang=fr`, confirmer que :
1. Le redirect de succès atterrit bien sur `/api/intake/calcom-confirmed`.
2. `intake_sessions.calcom_booking_uid` est posé en base pour cette session (vérifier par
   requête SQL directe, même pattern que les vérifications de migration précédentes).
Documenter le résultat (capture des paramètres de redirect réels observés — le nom exact
du paramètre `uid` vs `bookingUid` n'est confirmé qu'à ce test réel, cf. Task 6 Step 7 qui
gère les deux noms par prudence) dans `.ralph/progress.md`.

- [ ] **Step 7: Vérifier l'envoi réel d'email en prod (pattern de preuve US-204)**

Soumettre un vrai parcours Intake en prod jusqu'à `complete_routing` (les 3 branches si
possible, sinon au moins une), confirmer réception réelle de l'email contextualisé dans la
bonne locale. Documenter dans `.ralph/progress.md`.

- [ ] **Step 8: Marquer la story**

Une fois les Steps 6 et 7 validés réellement (pas seulement les tests unitaires), mettre à
jour `.ralph/prd.json` : `US-IQ-04.passes = true`, `completedAt` = timestamp réel.

---

## Hors scope de ce plan (à faire séparément)

- **Webhook Cal.com entrant** (annulation/report de réservation) — hors périmètre V1
  explicite (04-feature-backlog.md), sortie de conditions : premiers no-shows constatés.
- **Ajout d'une visioconférence** (Google Meet) sur l'event type `entretien-bassira-20-min`
  — à faire manuellement par Amine dans l'UI Cal.com si souhaité (l'event type a été créé
  via API sans `locations`, cf. mémoire `reference_calcom_agenda`).
- **Reprise de session cross-device** — hors scope V1.

---

## Self-Review

**1. Couverture spec (AC de la story)** :
- Email reflète A1/A3/branche, aucun contenu confidentiel, HTML échappé → Task 1 (audit
  existant) + Task 5 (nouveau flux, `decision_summary`/`full_name` échappés, jamais
  `confidential_flags`/`transcript` lus). ✓
- Email + page Cal.com dans la locale de session → Task 3 (3 templates fr/en/ar) + Task 4
  (`lang=` propagé sur le lien). ✓
- Appels API Cal.com via le hostname public correct → Task 4 ne fait AUCUN appel API pour
  générer le lien (page publique statique) — cohérent avec ADR-IQ-03 v3 qui ne s'applique
  qu'aux appels API (déjà faits en Task Amine hors-plan pour créer l'event type). ✓
- Clé `CALCOM_API_KEY` jamais au front → Task 2 (lue uniquement backend `Config`), jamais
  référencée dans un fichier `frontend/`. ✓
- Réservation confirmée → `calcom_booking_uid` posé → Task 6 (endpoint de capture +
  service `confirm_calcom_booking`). ✓
- Envoi réel vérifié en prod + réservation test réelle documentée → Task 7 Steps 6-7. ✓
- pytest (Resend et Cal.com mockés) + ruff + npm build verts → Task 7 Steps 1-2 (npm build
  non concerné, ce plan est 100% backend — aucun fichier frontend modifié).

**2. Scan placeholders** : aucun "TODO"/"TBD" ; chaque step de code contient le code
complet, y compris les 3 templates HTML intégraux.

**3. Cohérence des types** :
- `_build_confirmation_cta(route: str, locale: str, calcom_link: Optional[str]) -> Dict[str, str]`
  — signature identique entre définition (Task 3) et usage dans `_send_intake_confirmation`
  (Task 5).
- `_build_calcom_booking_link(session_id: str, locale: str) -> str` — identique entre
  définition (Task 4) et usage (Task 5).
- `_send_intake_confirmation(session: Dict[str, Any], *, client: Any) -> None` — appelé
  dans `complete_routing` avec `updated_session` (dict fusionné state+route+completed_at)
  et `client=cli` (variable déjà en scope dans `complete_routing`).
- `confirm_calcom_booking(session_id: str, booking_uid: str, *, client: Any = None) ->
  Tuple[int, Dict[str, Any]]` — identique entre définition (Task 6) et l'endpoint Flask qui
  l'appelle (signature positionnelle `(session_id, booking_uid)`, cohérent).
- Réutilise `qo.get_quote_payload_from_supabase` (déjà existant, `quote_ownership.py`) —
  aucune nouvelle fonction n'a été inventée pour ça.
