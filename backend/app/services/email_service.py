"""Bassira email helper (US-104).

Provides a single ``send_email`` entry point used by every notification
flow (quote received, payment link, deliverable). Preference order :

1. **Resend** (preferred) — when ``RESEND_API_KEY`` is set in env.
   Uses the official ``resend`` Python SDK (added to ``pyproject.toml``).
2. **Legacy SMTP** — falls back to the ``EMAIL_SMTP_*`` env vars used
   by ``quote_service.py`` for US-025. Preserves historical behaviour
   so a deployment without Resend still notifies.
3. **No-op** — if neither is configured, log a warning and return
   ``False``. Best-effort by design : the caller has already persisted
   the lead/quote on disk so no signal is lost.

Templates live under ``backend/app/templates/emails/`` (loaded with
plain ``str.format`` — no Jinja required for 3 simple HTML files).
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Mapping, Optional


logger = logging.getLogger("miroshark.email")


_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "emails"


def render_template(name: str, context: Mapping[str, Any]) -> str:
    """Charge ``templates/emails/<name>.html`` et substitue les placeholders.

    Substitution simple style ``str.format`` : ``{key}`` est remplacé par
    ``context[key]``. Un placeholder absent du context lève ``KeyError`` —
    c'est volontaire pour détecter les bugs de templating en CI.

    Si le fichier n'existe pas, retourne un fallback texte plain.
    """
    path = _TEMPLATE_DIR / f"{name}.html"
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Template %s missing (%s); using fallback", name, exc)
        return _fallback_template(name, context)
    try:
        return raw.format(**context)
    except KeyError as exc:
        logger.error("Template %s missing placeholder %s", name, exc)
        return _fallback_template(name, context)


def _fallback_template(name: str, context: Mapping[str, Any]) -> str:
    """HTML minimal de secours quand le template fichier est introuvable.

    Utilisé quand le template est buggy ou que le repo ne contient pas
    encore le fichier (cas test). Retourne un body lisible côté client.
    """
    safe_ctx = {k: str(v) for k, v in context.items()}
    body = "<br>".join(f"<b>{k}</b>: {v}" for k, v in safe_ctx.items())
    return (
        "<html><body style='font-family:system-ui,sans-serif'>"
        f"<h2>Bassira — {name}</h2>"
        f"<div>{body}</div>"
        "</body></html>"
    )


# ─── Sender backends ─────────────────────────────────────────────────────────


def _send_via_resend(
    to_email: str,
    subject: str,
    html_body: str,
    from_email: str,
    reply_to: Optional[str] = None,
) -> bool:
    """Tente l'envoi via le SDK Resend. Renvoie False si KO."""
    api_key = (os.environ.get("RESEND_API_KEY") or "").strip()
    if not api_key:
        return False
    try:
        import resend  # type: ignore[import]
    except ImportError:
        logger.warning(
            "RESEND_API_KEY set but resend SDK not installed — "
            "run `uv pip install resend>=2.0.0`. Falling back to SMTP."
        )
        return False

    try:
        resend.api_key = api_key
        params: resend.Emails.SendParams = {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }
        if reply_to:
            params["reply_to"] = reply_to
        result = resend.Emails.send(params)
        # Resend returns ``{"id": "..."}`` on success.
        if isinstance(result, dict) and result.get("id"):
            logger.info("Resend email %s sent to %s", result.get("id"), to_email)
            return True
        logger.warning("Resend returned unexpected payload: %r", result)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.error("Resend send failed (%s): %s", exc.__class__.__name__, exc)
        return False


def _send_via_smtp(
    to_email: str,
    subject: str,
    html_body: str,
    from_email: str,
    reply_to: Optional[str] = None,
) -> bool:
    """Fallback SMTP — variables d'env ``EMAIL_SMTP_*`` partagées avec US-025."""
    host = (os.environ.get("EMAIL_SMTP_HOST") or "").strip()
    if not host:
        return False
    port = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
    user = (os.environ.get("EMAIL_SMTP_USER") or "").strip()
    password = (os.environ.get("EMAIL_SMTP_PASSWORD") or "").strip()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.attach(MIMEText("Open this email in an HTML client.", "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.ehlo()
            try:
                smtp.starttls()
                smtp.ehlo()
            except smtplib.SMTPException:
                logger.info("SMTP STARTTLS unavailable on %s:%s", host, port)
            if user and password:
                smtp.login(user, password)
            smtp.sendmail(from_email, [to_email], msg.as_string())
        logger.info("SMTP email sent to %s via %s:%s", to_email, host, port)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "SMTP send failed (%s): %s",
            exc.__class__.__name__, exc,
        )
        return False


# ─── Public entry point ──────────────────────────────────────────────────────


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    *,
    from_email: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> bool:
    """Envoi d'un email — Resend → SMTP → no-op. Best-effort, ne lève jamais.

    ``from_email`` : si absent, on lit ``RESEND_FROM_EMAIL`` puis
    ``EMAIL_FROM`` (legacy). Si rien n'est configuré on tombe sur
    ``noreply@ai-mpower.com`` pour préserver la rétro-compat.
    """
    if not to_email or not isinstance(to_email, str):
        logger.warning("send_email: empty to_email — skipped")
        return False

    sender = (
        from_email
        or os.environ.get("RESEND_FROM_EMAIL")
        or os.environ.get("EMAIL_FROM")
        or "Bassira <noreply@ai-mpower.com>"
    ).strip()

    # 1) Try Resend.
    if _send_via_resend(to_email, subject, html_body, sender, reply_to):
        return True
    # 2) Fallback to SMTP.
    if _send_via_smtp(to_email, subject, html_body, sender, reply_to):
        return True
    # 3) No-op (best-effort).
    logger.warning(
        "No email backend configured (RESEND_API_KEY + EMAIL_SMTP_HOST both empty) — "
        "email to %s skipped (subject: %r)",
        to_email, subject,
    )
    return False
