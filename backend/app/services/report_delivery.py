"""Service report_delivery — URL signée TTL + email Resend + tracking téléchargements (US-130).

Fonctionnalités :
  - Génération de tokens HMAC SHA256 avec TTL
  - Vérification des tokens (HMAC + expiry)
  - Création d'une livraison (row + email Resend)
  - Journalisation des téléchargements (IP + géo)
  - Re-envoi (invalide l'ancien token, génère un nouveau)
  - Auto-archivage après 90 jours (cron)

Secret HMAC : variable d'env BASSIRA_DELIVERY_HMAC_SECRET (bytes hex).
Si absente → log warning + fallback dev (insecure).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from ..auth.supabase_client import get_supabase_admin
from .email_service import render_template, send_email

logger = logging.getLogger("miroshark.services.report_delivery")

# ─── Secret HMAC ────────────────────────────────────────────────────────────

_HMAC_SECRET: Optional[bytes] = None

_FALLBACK_SECRET_HEX = "6261737369726164657620666661616c6c6261636b73656372657430303030"


def _get_hmac_secret() -> bytes:
    """Retourne le secret HMAC depuis l'env ou le fallback dev."""
    global _HMAC_SECRET  # noqa: PLW0603
    if _HMAC_SECRET is not None:
        return _HMAC_SECRET

    raw = os.environ.get("BASSIRA_DELIVERY_HMAC_SECRET", "").strip()
    if not raw:
        logger.warning(
            "BASSIRA_DELIVERY_HMAC_SECRET non configuré — "
            "utilisation du secret fallback DEV (insecure en production)."
        )
        _HMAC_SECRET = bytes.fromhex(_FALLBACK_SECRET_HEX)
    else:
        try:
            # Accepte une valeur hex ou un string UTF-8 brut
            _HMAC_SECRET = bytes.fromhex(raw) if all(c in "0123456789abcdefABCDEF" for c in raw) else raw.encode("utf-8")
        except Exception:  # noqa: BLE001
            _HMAC_SECRET = raw.encode("utf-8")

    return _HMAC_SECRET


# ─── Tables ─────────────────────────────────────────────────────────────────

_TABLE_DELIVERIES = "report_deliveries"
_TABLE_DOWNLOADS  = "report_downloads"

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _client(client=None):
    return client or get_supabase_admin()


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _to_iso(dt: datetime) -> str:
    return dt.isoformat()


def _from_iso(s: str) -> datetime:
    # Python ≤ 3.10 ne gère pas 'Z' directement
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# ─── Token HMAC ─────────────────────────────────────────────────────────────


def generate_signing_token(
    report_id: str,
    version: int,
    recipient_email: str,
    expires_in_seconds: int,
) -> str:
    """Génère un token HMAC SHA256 opaque pour la livraison d'un rapport.

    Format du token :
        base64url( payload_json ) + "." + base64url( hmac_digest[:24] )

    Le payload encode : report_id, version, recipient_email, exp (timestamp UTC).
    Le HMAC couvre le payload complet pour garantir l'intégrité.

    Returns:
        Token string (sûr pour URL sans encodage supplémentaire).
    """
    exp_ts = int(_now_utc().timestamp()) + expires_in_seconds
    # Ajouter un nonce pour que deux livraisons vers le même destinataire
    # aient des tokens distincts (résiste aux token-clobber attacks).
    nonce = secrets.token_hex(8)

    payload = {
        "rid": report_id,
        "ver": version,
        "eml": recipient_email,
        "exp": exp_ts,
        "nonce": nonce,
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).rstrip(b"=").decode("ascii")

    # HMAC SHA256 du payload b64
    secret = _get_hmac_secret()
    sig_bytes = hmac.new(secret, payload_b64.encode("ascii"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig_bytes).rstrip(b"=").decode("ascii")

    return f"{payload_b64}.{sig_b64}"


def verify_signing_token(token: str) -> Optional[Dict[str, Any]]:
    """Vérifie un token HMAC et retourne le payload si valide.

    Contrôles :
        1. Format (2 segments séparés par un point)
        2. HMAC (comparaison en temps constant)
        3. Expiry (exp < now → None)

    Returns:
        Dict ``{"rid", "ver", "eml", "exp", "nonce"}`` si valide, None sinon.
    """
    if not token or token.count(".") != 1:
        return None

    payload_b64, sig_b64 = token.split(".", 1)

    # Recalculer le HMAC attendu
    secret = _get_hmac_secret()
    expected_sig_bytes = hmac.new(secret, payload_b64.encode("ascii"), hashlib.sha256).digest()
    expected_sig_b64 = base64.urlsafe_b64encode(expected_sig_bytes).rstrip(b"=").decode("ascii")

    # Comparaison en temps constant (anti-timing)
    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        logger.debug("verify_signing_token: HMAC invalide")
        return None

    # Décode le payload
    try:
        padding = "=" * (4 - len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8")
        payload = json.loads(payload_json)
    except Exception:  # noqa: BLE001
        logger.debug("verify_signing_token: décodage payload échoué")
        return None

    # Vérification expiry
    exp_ts = payload.get("exp", 0)
    if int(_now_utc().timestamp()) > exp_ts:
        logger.debug("verify_signing_token: token expiré (exp=%s)", exp_ts)
        return None

    return payload


# ─── API publique ─────────────────────────────────────────────────────────────


def create_delivery(
    report_id: str,
    version: int,
    recipient_email: str,
    recipient_name: str,
    *,
    expiry_days: int = 7,
    language: str = "fr",
    sent_by: Optional[str] = None,
    report_title: Optional[str] = None,
    client=None,
) -> Dict[str, Any]:
    """Crée une livraison de rapport et envoie l'email Resend.

    Args:
        report_id:       Identifiant du rapport.
        version:         Version du snapshot à livrer.
        recipient_email: Adresse email du destinataire.
        recipient_name:  Nom affiché dans l'email.
        expiry_days:     Durée de validité du lien (défaut : 7 jours).
        language:        Langue de l'email : 'fr', 'en', ou 'ar'.
        sent_by:         UUID de l'utilisateur qui déclenche la livraison.
        report_title:    Titre du rapport (pour le sujet de l'email).
        client:          Client Supabase (injection de test).

    Returns:
        Dict ``{"id", "report_id", "version", "signing_token", "expires_at", "email_status"}``.
    """
    expires_in_seconds = expiry_days * 24 * 3600
    token = generate_signing_token(report_id, version, recipient_email, expires_in_seconds)
    expires_at = _now_utc() + timedelta(seconds=expires_in_seconds)

    cli = _client(client)

    # Insérer la livraison en base
    row: Dict[str, Any] = {
        "report_id":       report_id,
        "version":         version,
        "recipient_email": recipient_email,
        "recipient_name":  recipient_name,
        "signing_token":   token,
        "expires_at":      _to_iso(expires_at),
        "language":        language,
        "email_status":    "pending",
    }
    if sent_by:
        row["sent_by"] = sent_by

    resp = cli.table(_TABLE_DELIVERIES).insert(row).execute()
    data = resp.data
    if not data:
        raise RuntimeError(f"Supabase insert delivery failed: {resp}")
    delivery = data[0]
    delivery_id = delivery["id"]

    # Construire le lien de téléchargement
    base_url = os.environ.get("BASSIRA_PUBLIC_URL", "https://bassira.ma").rstrip("/")
    download_url = f"{base_url}/r/{token}"

    # Titre par défaut
    if not report_title:
        report_title = f"Rapport #{report_id[:8]}"

    # Rendre le template email
    html_body = render_template(
        "report_delivery",
        {
            "recipient_name": recipient_name or recipient_email,
            "report_title":   report_title,
            "download_url":   download_url,
            "expires_days":   str(expiry_days),
            "language":       language,
        },
    )

    # Sujet multilingue
    subject_map = {
        "fr": f"Votre rapport Bassira est prêt — {report_title}",
        "en": f"Your Bassira report is ready — {report_title}",
        "ar": f"تقريرك من Bassira جاهز — {report_title}",
    }
    subject = subject_map.get(language, subject_map["fr"])

    # Envoi email (best-effort)
    ok = send_email(recipient_email, subject, html_body)
    email_status = "sent" if ok else "failed"
    sent_at = _to_iso(_now_utc()) if ok else None

    # Mettre à jour le statut email
    update_data: Dict[str, Any] = {"email_status": email_status}
    if sent_at:
        update_data["sent_at"] = sent_at
    cli.table(_TABLE_DELIVERIES).update(update_data).eq("id", delivery_id).execute()
    delivery["email_status"] = email_status
    delivery["sent_at"] = sent_at

    logger.info(
        "Delivery créée: delivery_id=%s report_id=%s version=%d email=%s status=%s",
        delivery_id, report_id, version, recipient_email, email_status,
    )
    return delivery


def log_download(
    delivery_id: str,
    ip: Optional[str],
    user_agent: Optional[str],
    country_code: Optional[str],
    *,
    referer: Optional[str] = None,
    client=None,
) -> None:
    """Journalise un téléchargement dans report_downloads."""
    cli = _client(client)
    row: Dict[str, Any] = {"delivery_id": delivery_id}
    if ip:
        row["ip_address"] = ip
    if user_agent:
        row["user_agent"] = user_agent
    if country_code:
        row["country_code"] = country_code
    if referer:
        row["referer"] = referer
    cli.table(_TABLE_DOWNLOADS).insert(row).execute()
    logger.debug("Download journalisé: delivery_id=%s ip=%s country=%s", delivery_id, ip, country_code)


def list_deliveries(report_id: str, *, client=None) -> List[Dict[str, Any]]:
    """Liste les livraisons pour un rapport, triées par date décroissante."""
    cli = _client(client)
    resp = (
        cli.table(_TABLE_DELIVERIES)
        .select("*")
        .eq("report_id", report_id)
        .order("created_at", desc=True)
        .execute()
    )
    rows = resp.data or []
    # Enrichir le statut (expired si expires_at < now)
    now_ts = _now_utc().timestamp()
    for row in rows:
        exp_str = row.get("expires_at", "")
        if exp_str:
            try:
                exp_ts = _from_iso(exp_str).timestamp()
                if exp_ts < now_ts and row.get("email_status") == "sent":
                    row["display_status"] = "expired"
                else:
                    row["display_status"] = row.get("email_status", "pending")
            except Exception:  # noqa: BLE001
                row["display_status"] = row.get("email_status", "pending")
        else:
            row["display_status"] = row.get("email_status", "pending")
    return rows


def list_downloads(delivery_id: str, *, client=None) -> List[Dict[str, Any]]:
    """Liste les téléchargements pour une livraison, triés par date décroissante."""
    cli = _client(client)
    resp = (
        cli.table(_TABLE_DOWNLOADS)
        .select("*")
        .eq("delivery_id", delivery_id)
        .order("downloaded_at", desc=True)
        .execute()
    )
    return resp.data or []


def re_send_link(
    delivery_id: str,
    *,
    expiry_days: int = 7,
    report_title: Optional[str] = None,
    client=None,
) -> Dict[str, Any]:
    """Invalide l'ancien token et envoie un nouveau lien de téléchargement.

    Le token de la livraison existante est régénéré avec un nouveau TTL.

    Returns:
        La livraison mise à jour avec le nouveau token.
    """
    cli = _client(client)

    # Récupérer la livraison existante
    resp = cli.table(_TABLE_DELIVERIES).select("*").eq("id", delivery_id).execute()
    rows = resp.data or []
    if not rows:
        raise ValueError(f"Delivery introuvable : {delivery_id}")
    delivery = rows[0]

    report_id       = delivery["report_id"]
    version         = delivery["version"]
    recipient_email = delivery["recipient_email"]
    recipient_name  = delivery.get("recipient_name", "")
    language        = delivery.get("language", "fr")

    # Générer un nouveau token
    expires_in_seconds = expiry_days * 24 * 3600
    new_token  = generate_signing_token(report_id, version, recipient_email, expires_in_seconds)
    expires_at = _now_utc() + timedelta(seconds=expires_in_seconds)

    # Construire le lien
    base_url     = os.environ.get("BASSIRA_PUBLIC_URL", "https://bassira.ma").rstrip("/")
    download_url = f"{base_url}/r/{new_token}"

    if not report_title:
        report_title = f"Rapport #{report_id[:8]}"

    # Rendre le template
    html_body = render_template(
        "report_delivery",
        {
            "recipient_name": recipient_name or recipient_email,
            "report_title":   report_title,
            "download_url":   download_url,
            "expires_days":   str(expiry_days),
            "language":       language,
        },
    )
    subject_map = {
        "fr": f"Votre rapport Bassira est prêt — {report_title}",
        "en": f"Your Bassira report is ready — {report_title}",
        "ar": f"تقريرك من Bassira جاهز — {report_title}",
    }
    subject = subject_map.get(language, subject_map["fr"])

    ok = send_email(recipient_email, subject, html_body)
    email_status = "sent" if ok else "failed"

    # Mettre à jour la livraison
    update_data: Dict[str, Any] = {
        "signing_token": new_token,
        "expires_at":    _to_iso(expires_at),
        "email_status":  email_status,
    }
    if ok:
        update_data["sent_at"] = _to_iso(_now_utc())

    cli.table(_TABLE_DELIVERIES).update(update_data).eq("id", delivery_id).execute()

    logger.info(
        "Re-send: delivery_id=%s report_id=%s email=%s status=%s",
        delivery_id, report_id, recipient_email, email_status,
    )
    delivery.update(update_data)
    return delivery


def auto_archive_after_90_days(*, client=None) -> int:
    """Archive les livraisons de plus de 90 jours (cron job).

    Met à jour ``email_status = 'archived'`` pour les livraisons dont
    ``expires_at < now() - 90 jours``.

    Returns:
        Nombre de rows archivées.
    """
    cli = _client(client)
    threshold = _now_utc() - timedelta(days=90)
    threshold_iso = _to_iso(threshold)

    resp = (
        cli.table(_TABLE_DELIVERIES)
        .update({"email_status": "archived"})
        .lt("expires_at", threshold_iso)
        .neq("email_status", "archived")
        .execute()
    )
    count = len(resp.data or [])
    if count:
        logger.info("auto_archive_after_90_days: %d livraisons archivées", count)
    return count
