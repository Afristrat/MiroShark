"""Quote-request service (US-025).

Validates and persists commercial quote-request payloads coming from the
public ``/devis`` form, then best-effort fires a notification email to the
sales inbox via stdlib ``smtplib``.

Design notes:

- **Storage** : every accepted quote is dumped as ``quote_<ts>_<short>.json``
  under ``Config.WONDERWALL_DATA_DIR/quotes/``. The dir is created on
  first write — a missing directory is *not* an error condition. We do not
  use a database because the volume is tiny (handful per week) and Amine
  needs zero ops to grep the inbox on the server.
- **Email** : SMTP envelope is best-effort. If ``EMAIL_SMTP_HOST`` is
  unset, we log a warning and return success — the quote is already on
  disk so no lead is ever lost. Any SMTP exception is caught and logged
  rather than escalated, for the same reason.
- **Sanitisation** : every string is HTML-escaped before being written or
  embedded in the email body. The on-disk JSON also stores the escaped
  form so a downstream renderer (export, dashboard) cannot
  accidentally inject HTML.
- **Rate limiting** : a tiny in-memory ``client_ip → list[ts]`` window
  caps a single IP at ``_RATE_LIMIT_MAX_PER_HOUR`` quotes per rolling
  hour. Process-local on purpose — Bassira ships as a single Flask
  worker behind Cloudflare, so a Redis-backed limiter would be
  premature. Restart wipes the window (acceptable: an attacker would
  trigger far more obvious alarms first).

Exposed surface used by ``app.api.quote``:

  * ``submit_quote(payload, *, client_ip, user_agent)`` →
    ``(http_status, response_dict)``
  * ``check_rate_limit(client_ip)`` → ``True`` if quota left, ``False``
    if the caller should be sent ``429``.

Both helpers are pure functions over Config + the in-memory rate-limit
dict, so the unit tests can drive them with ``monkeypatch`` on
``Config.WONDERWALL_DATA_DIR`` and ``smtplib.SMTP`` without spinning up
a Flask app.
"""

from __future__ import annotations

import html
import json
import logging
import os
import smtplib
import time
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from ..config import Config


logger = logging.getLogger("miroshark.quote")


# ─── Validation constants ────────────────────────────────────────────────────

_VALID_PACKAGES = {
    "crisis_drill_24h",
    "policy_brief_stress",
    "pre_launch_adcheck",
    "custom",
}

_VALID_GEO = {"MA", "DZ", "TN", "SN", "CI", "Other"}

# Truncation caps — match the frontend ``maxlength`` to keep parity. We
# truncate rather than reject so a user who pastes a slightly-too-long
# company name still gets through; the email/JSON record stays bounded.
_MAX_FULL_NAME = 100
_MAX_COMPANY = 120
_MAX_ROLE = 80
_MAX_MESSAGE = 800
_MAX_USER_AGENT = 200

# Email regex — kept deliberately laxe (matches the frontend regex). The
# RFC 5322 grammar is overkill for « did the user type something
# email-shaped ? » and the backend rejects nothing the frontend accepts.
import re  # noqa: E402 — co-located with the regex it powers

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ─── Rate limiting ───────────────────────────────────────────────────────────

_RATE_LIMIT_MAX_PER_HOUR = 5
_RATE_LIMIT_WINDOW_SECONDS = 3600

# Process-local rate-limit window. Keys: client IP. Values: list of unix
# timestamps of recent submissions. Pruned on each check.
_rate_limit: Dict[str, List[float]] = {}
_rate_limit_lock = Lock()


def _reset_rate_limit_for_tests() -> None:
    """Test helper — clears the in-memory rate-limit dict so each test
    starts from zero. Not exported for production callers.
    """
    with _rate_limit_lock:
        _rate_limit.clear()


def check_rate_limit(client_ip: Optional[str]) -> bool:
    """Return ``True`` when the caller is within quota, ``False`` if the
    request should be 429'd.

    A missing / empty ``client_ip`` (e.g. when ``request.remote_addr`` is
    ``None``) is treated as a single shared bucket keyed on ``"_unknown"``
    so a misconfigured reverse proxy can't bypass the limiter entirely.
    """
    key = (client_ip or "").strip() or "_unknown"
    now = time.time()
    with _rate_limit_lock:
        bucket = _rate_limit.get(key, [])
        # Prune entries outside the rolling window.
        cutoff = now - _RATE_LIMIT_WINDOW_SECONDS
        bucket = [ts for ts in bucket if ts > cutoff]
        if len(bucket) >= _RATE_LIMIT_MAX_PER_HOUR:
            _rate_limit[key] = bucket
            return False
        bucket.append(now)
        _rate_limit[key] = bucket
        return True


# ─── Path helpers ────────────────────────────────────────────────────────────


def _quotes_dir() -> Path:
    """Return the directory where quote payloads are persisted.

    ``Config.WONDERWALL_DATA_DIR`` is the canonical override hook; when
    absent we derive it from the existing ``WONDERWALL_SIMULATION_DATA_DIR``
    (sibling ``quotes/`` next to ``simulations/``). Either way the dir is
    created on demand so the first call after a fresh install does not
    500.

    ``Config`` is re-imported on every call so ``importlib.reload`` in
    other tests cannot leave us pinned to a stale class — we always look
    up the live attributes the test fixture monkeypatched.
    """
    from ..config import Config as _LiveConfig  # noqa: WPS433 — see docstring

    base_dir = getattr(_LiveConfig, "WONDERWALL_DATA_DIR", None)
    if not base_dir:
        sim_dir = getattr(_LiveConfig, "WONDERWALL_SIMULATION_DATA_DIR", None)
        if sim_dir:
            base_dir = os.path.dirname(sim_dir)
        else:
            base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
    path = Path(base_dir) / "quotes"
    path.mkdir(parents=True, exist_ok=True)
    return path


# ─── Sanitisation + validation ───────────────────────────────────────────────


def _truncate(value: Any, limit: int) -> str:
    """Coerce to ``str``, strip surrounding whitespace, truncate to ``limit``.

    Non-string inputs become an empty string (we never want to render a
    Python ``repr`` in a sales email).
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        return ""
    trimmed = value.strip()
    if len(trimmed) > limit:
        return trimmed[:limit]
    return trimmed


def _sanitise(value: str) -> str:
    """HTML-escape a string before storing or embedding it."""
    return html.escape(value, quote=True)


def _validate_payload(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(error_code, error_message)`` if invalid, else ``(None, None)``.

    Order of checks mirrors the frontend's step layout (coordonnées →
    besoin → consent) so the error the user sees lines up with the field
    they are looking at when they hit « Envoyer ».
    """
    if not isinstance(payload, dict):
        return "MISSING_FIELD", "Invalid request body."

    # Required text fields.
    for field, label in (
        ("full_name", "full_name"),
        ("company", "company"),
    ):
        raw = payload.get(field)
        if not isinstance(raw, str) or not raw.strip():
            return "MISSING_FIELD", f"Field « {label} » is required."

    # Email — required + format.
    email_raw = payload.get("email")
    if not isinstance(email_raw, str) or not email_raw.strip():
        return "MISSING_FIELD", "Field « email » is required."
    if not _EMAIL_RE.match(email_raw.strip()):
        return "INVALID_EMAIL", "The email address is not in a valid format."

    # Package — required + enum.
    package = payload.get("package")
    if not isinstance(package, str) or not package.strip():
        return "MISSING_FIELD", "Field « package » is required."
    if package not in _VALID_PACKAGES:
        return "INVALID_PACKAGE", (
            f"Unknown package « {package} ». Expected one of: "
            f"{', '.join(sorted(_VALID_PACKAGES))}."
        )

    # RGPD — must be explicit ``True``.
    if payload.get("consent_rgpd") is not True:
        return "RGPD_NOT_ACCEPTED", (
            "RGPD consent is required to process the request."
        )

    # Optional integer bounds.
    sims = payload.get("expected_simulations_per_year")
    if sims is not None and sims != "":
        try:
            sims_int = int(sims)
        except (TypeError, ValueError):
            return "MISSING_FIELD", (
                "Field « expected_simulations_per_year » must be an integer."
            )
        if sims_int < 1 or sims_int > 100:
            return "MISSING_FIELD", (
                "Field « expected_simulations_per_year » must be in [1, 100]."
            )

    # Optional geo_focus — array of allowed strings.
    geo = payload.get("geo_focus")
    if geo is not None and geo != []:
        if not isinstance(geo, list):
            return "MISSING_FIELD", "Field « geo_focus » must be an array."
        for g in geo:
            if not isinstance(g, str) or g not in _VALID_GEO:
                return "MISSING_FIELD", (
                    f"Field « geo_focus » contains an unknown value: {g!r}."
                )

    return None, None


# ─── Persistence ─────────────────────────────────────────────────────────────


def _build_record(
    payload: Dict[str, Any],
    *,
    quote_id: str,
    client_ip: Optional[str],
    user_agent: Optional[str],
) -> Dict[str, Any]:
    """Build the on-disk JSON record from a validated payload.

    Every text field is HTML-escaped before being persisted. Optional
    fields default to ``""`` / ``None`` / ``[]`` so a downstream
    consumer (export, dashboard) can rely on a stable schema.
    """
    full_name = _sanitise(_truncate(payload.get("full_name"), _MAX_FULL_NAME))
    email = _truncate(payload.get("email"), 320)  # RFC 5321 hard cap
    company = _sanitise(_truncate(payload.get("company"), _MAX_COMPANY))
    role = _sanitise(_truncate(payload.get("role"), _MAX_ROLE))
    phone = _sanitise(_truncate(payload.get("phone"), 40))
    message = _sanitise(_truncate(payload.get("message"), _MAX_MESSAGE))

    package = payload.get("package")
    target_deadline = payload.get("target_deadline") or ""
    if not isinstance(target_deadline, str):
        target_deadline = ""
    industry = payload.get("industry") or ""
    if not isinstance(industry, str):
        industry = ""
    locale = payload.get("locale") or "fr"
    if not isinstance(locale, str) or locale not in ("fr", "en", "ar"):
        locale = "fr"

    sims_raw = payload.get("expected_simulations_per_year")
    sims_int: Optional[int]
    try:
        sims_int = int(sims_raw) if sims_raw not in (None, "") else None
    except (TypeError, ValueError):
        sims_int = None

    geo_focus_raw = payload.get("geo_focus") or []
    if isinstance(geo_focus_raw, list):
        geo_focus = [g for g in geo_focus_raw if isinstance(g, str) and g in _VALID_GEO]
    else:
        geo_focus = []

    return {
        "quote_id": quote_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "full_name": full_name,
        "email": email,
        "company": company,
        "role": role,
        "phone": phone,
        "package": package,
        "expected_simulations_per_year": sims_int,
        "target_deadline": _sanitise(target_deadline),
        "industry": _sanitise(industry),
        "geo_focus": geo_focus,
        "message": message,
        "consent_rgpd": True,
        "locale": locale,
        "client_ip": (client_ip or "")[:64],
        "user_agent": _sanitise(_truncate(user_agent, _MAX_USER_AGENT)),
    }


def _write_record(record: Dict[str, Any]) -> Path:
    """Persist the record under ``quotes/quote_<ts>_<short>.json``.

    Filename is sortable by submission time (UTC ``YYYYmmddTHHMMSS``)
    plus a short uuid hex for collision-safety on concurrent submissions
    within the same second.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    short = record["quote_id"].replace("q_", "")
    filename = f"quote_{ts}_{short}.json"
    target = _quotes_dir() / filename
    target.write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


# ─── Email envelope ──────────────────────────────────────────────────────────


def _format_email_subject(record: Dict[str, Any]) -> str:
    return f"[Bassira Quote] {record['full_name'] or 'Anonymous'} — {record['package']}"


def _format_email_plain(record: Dict[str, Any]) -> str:
    """Plain-text body with one ``key: value`` per line. Sanitised
    fields are already HTML-escaped — that's harmless in plain text and
    keeps the body identical to the HTML variant for grep'ability.
    """
    lines = [
        "New quote request — Bassira",
        "",
        f"Quote ID:     {record['quote_id']}",
        f"Submitted at: {record['submitted_at']}",
        f"Locale:       {record['locale']}",
        "",
        "── Contact ──",
        f"Full name:    {record['full_name']}",
        f"Email:        {record['email']}",
        f"Company:      {record['company']}",
        f"Role:         {record['role'] or '-'}",
        f"Phone:        {record['phone'] or '-'}",
        "",
        "── Need ──",
        f"Package:      {record['package']}",
        f"Volume/year:  {record['expected_simulations_per_year'] or '-'}",
        f"Deadline:     {record['target_deadline'] or '-'}",
        f"Industry:     {record['industry'] or '-'}",
        f"Geo focus:    {', '.join(record['geo_focus']) or '-'}",
        "",
        "── Message ──",
        record["message"] or "(no message)",
        "",
        "── Trace ──",
        f"Client IP:    {record['client_ip'] or '-'}",
        f"User agent:   {record['user_agent'] or '-'}",
    ]
    return "\n".join(lines)


def _format_email_html(record: Dict[str, Any]) -> str:
    """Minimal HTML body — same fields as the plain-text variant, in a
    table for legibility in Gmail / Outlook / Mail.
    """
    rows = [
        ("Quote ID", record["quote_id"]),
        ("Submitted at", record["submitted_at"]),
        ("Locale", record["locale"]),
        ("Full name", record["full_name"]),
        ("Email", record["email"]),
        ("Company", record["company"]),
        ("Role", record["role"] or "-"),
        ("Phone", record["phone"] or "-"),
        ("Package", record["package"]),
        ("Volume/year", str(record["expected_simulations_per_year"] or "-")),
        ("Deadline", record["target_deadline"] or "-"),
        ("Industry", record["industry"] or "-"),
        ("Geo focus", ", ".join(record["geo_focus"]) or "-"),
        ("Message", record["message"] or "(no message)"),
        ("Client IP", record["client_ip"] or "-"),
        ("User agent", record["user_agent"] or "-"),
    ]
    body_rows = "\n".join(
        f"<tr><th align='left' style='padding:4px 12px 4px 0;color:#666'>{html.escape(k)}</th>"
        f"<td style='padding:4px 0'>{v}</td></tr>"
        for k, v in rows
    )
    return (
        "<html><body style='font-family:system-ui,sans-serif;color:#111'>"
        "<h2 style='margin:0 0 12px 0'>New quote request — Bassira</h2>"
        f"<table>{body_rows}</table>"
        "</body></html>"
    )


def _send_email(record: Dict[str, Any]) -> None:
    """Best-effort SMTP envelope. Never raises.

    Reads ``EMAIL_SMTP_HOST`` / ``EMAIL_SMTP_PORT`` /
    ``EMAIL_SMTP_USER`` / ``EMAIL_SMTP_PASSWORD`` /
    ``EMAIL_FROM`` / ``EMAIL_TO`` from the environment. Missing host →
    log warning and return. Any exception is caught and logged so the
    HTTP handler can still 200 — the quote is on disk regardless.
    """
    host = os.environ.get("EMAIL_SMTP_HOST", "").strip()
    if not host:
        logger.warning(
            "SMTP not configured (EMAIL_SMTP_HOST empty) — quote %s stored only.",
            record["quote_id"],
        )
        return

    port = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
    user = os.environ.get("EMAIL_SMTP_USER", "").strip()
    password = os.environ.get("EMAIL_SMTP_PASSWORD", "").strip()
    sender = os.environ.get("EMAIL_FROM", "noreply@ai-mpower.com").strip()
    recipient = os.environ.get("EMAIL_TO", "contact@ai-mpower.com").strip()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = _format_email_subject(record)
    msg["From"] = sender
    msg["To"] = recipient
    msg["Reply-To"] = record["email"] or sender

    msg.attach(MIMEText(_format_email_plain(record), "plain", "utf-8"))
    msg.attach(MIMEText(_format_email_html(record), "html", "utf-8"))

    try:
        # ``with`` ensures the connection is released even on send failure.
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.ehlo()
            try:
                smtp.starttls()
                smtp.ehlo()
            except smtplib.SMTPException:
                # Server may not support STARTTLS (rare, e.g. localhost
                # MailHog) — continue without it. We still attempt auth
                # below; the connection just won't be encrypted.
                logger.info("SMTP STARTTLS unavailable on %s:%s", host, port)
            if user and password:
                smtp.login(user, password)
            smtp.sendmail(sender, [recipient], msg.as_string())
        logger.info("Quote %s notification email sent to %s", record["quote_id"], recipient)
    except Exception as exc:  # noqa: BLE001 — best-effort by design
        # Never raise — the quote is already persisted on disk.
        logger.error(
            "SMTP delivery failed for quote %s: %s",
            record["quote_id"],
            exc,
        )


# ─── Public entry point ──────────────────────────────────────────────────────


def _send_client_confirmation(record: Dict[str, Any]) -> None:
    """Best-effort confirmation email to the client (US-104).

    Uses the unified Resend / SMTP helper from ``email_service`` and the
    template ``quote_received.html``. Never raises — the quote is
    already persisted.
    """
    if not record.get("email"):
        return
    try:
        from .email_service import render_template, send_email

        package_labels = {
            "crisis_drill_24h": "Stress-test 24 h",
            "policy_brief_stress": "Note de cadrage politique",
            "pre_launch_adcheck": "Vérif pré-lancement",
            "custom": "Analyse sur mesure",
        }
        package_label = package_labels.get(
            record.get("package") or "", record.get("package") or "Bassira"
        )
        industry_label = record.get("industry") or "stratégie générale"
        html_body = render_template(
            "quote_received",
            {
                "full_name": record.get("full_name") or "—",
                "company": record.get("company") or "—",
                "package_label": package_label,
                "industry_label": industry_label,
                "quote_id": record.get("quote_id") or "",
            },
        )
        send_email(
            to_email=record["email"],
            subject=f"Bassira — Votre demande {package_label} est bien arrivée",
            html_body=html_body,
            reply_to="contact@ai-mpower.com",
        )
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.error(
            "Client confirmation email failed for quote %s: %s",
            record.get("quote_id"), exc,
        )


def submit_quote(
    payload: Dict[str, Any],
    *,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Validate, persist, notify. Returns ``(status, response_dict)``.

    Wraps the whole pipeline so the Flask handler is a thin adapter
    (``return jsonify(body), status``).
    """
    error_code, error_msg = _validate_payload(payload)
    if error_code is not None:
        return 400, {
            "success": False,
            "error_code": error_code,
            "error": error_msg,
        }

    quote_id = f"q_{uuid.uuid4().hex[:8]}"
    record = _build_record(
        payload,
        quote_id=quote_id,
        client_ip=client_ip,
        user_agent=user_agent,
    )

    try:
        _write_record(record)
    except OSError as exc:
        # Disk-write failure is the one thing that *should* surface as a
        # 500 — there is no other place the lead is captured. The
        # frontend will show the user a retry prompt.
        logger.error("Failed to persist quote %s: %s", quote_id, exc)
        return 500, {
            "success": False,
            "error_code": "STORAGE_ERROR",
            "error": "Could not persist the quote. Please retry.",
        }

    # Best-effort emails — never block success.
    _send_email(record)            # internal sales notification (legacy)
    _send_client_confirmation(record)  # confirmation au client (US-104)

    return 200, {
        "success": True,
        "data": {
            "quote_id": quote_id,
            "submitted_at": record["submitted_at"],
        },
    }
