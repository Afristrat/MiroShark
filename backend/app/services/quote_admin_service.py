"""Quote admin service (US-102, US-103, US-104).

Lecture, persistance et workflow autour des fichiers de devis stockés sur
le filesystem dans ``backend/uploads/quotes/`` (cf. ``quote_service.py``
qui les écrit lors de la soumission publique US-025).

Architecture :

* **Sidecar status** : à côté de chaque ``quote_<id>.json``, on persiste
  un ``quote_<id>.status.json`` qui contient :

      {
        "status": "received|reviewing|quoted|declined|paid|in_progress|delivered",
        "history": [{"status": ..., "at": ISO8601, "by": email|None, "notes": str|None}],
        "payment_link": "https://buy.stripe.com/…" | None,
        "last_email_sent_at": ISO8601 | None,
        "notes": "free admin notes" | None,
        "delivered_url": "https://notion.so/…" | None
      }

  Si le sidecar n'existe pas, ``read_quote_status`` retombe sur le statut
  par défaut ``received`` (le devis vient juste d'arriver).

* **Transitions valides** :

    received    → reviewing | declined
    reviewing   → quoted    | declined
    quoted      → paid      | declined
    paid        → in_progress | declined
    in_progress → delivered  | declined
    delivered   → (terminal — aucune transition autre que rester)
    declined    → (terminal — pas de retour arrière)

Les fonctions de ce module ne lèvent jamais d'exception côté lecture (le
fail-soft est essentiel pour éviter de bricker la console super-admin si
un sidecar est corrompu).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ..config import Config


logger = logging.getLogger("miroshark.quote_admin")


# ─── Constantes du workflow statut ──────────────────────────────────────────

VALID_STATUSES: Set[str] = {
    "received",
    "reviewing",
    "quoted",
    "declined",
    "paid",
    "in_progress",
    "delivered",
}

DEFAULT_STATUS = "received"

# Mapping des transitions autorisées. Le statut « declined » est toujours
# joignable depuis n'importe quel non-terminal — l'admin doit pouvoir
# annuler à tout moment. delivered est terminal (sauf retour à declined
# pour gérer une régression livrée par erreur, exceptionnel).
ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    "received": {"reviewing", "declined"},
    "reviewing": {"quoted", "declined"},
    "quoted": {"paid", "declined"},
    "paid": {"in_progress", "declined"},
    "in_progress": {"delivered", "declined"},
    "delivered": set(),
    "declined": set(),
}


def is_valid_transition(current: str, next_status: str) -> bool:
    """Indique si la transition ``current → next_status`` est autorisée."""
    if next_status not in VALID_STATUSES:
        return False
    if current == next_status:
        # Idempotent : redéclarer le même statut est toléré.
        return True
    return next_status in ALLOWED_TRANSITIONS.get(current, set())


# ─── Path helpers ────────────────────────────────────────────────────────────


def quotes_dir() -> Path:
    """Retourne le dossier des devis (équivalent de ``_quotes_dir`` du
    service public ``quote_service``).

    Re-imports ``Config`` à chaque appel pour respecter les
    monkeypatch ``WONDERWALL_DATA_DIR`` posés par les tests.
    """
    from ..config import Config as _LiveConfig

    base_dir = getattr(_LiveConfig, "WONDERWALL_DATA_DIR", None)
    if not base_dir:
        sim_dir = getattr(_LiveConfig, "WONDERWALL_SIMULATION_DATA_DIR", None)
        if sim_dir:
            base_dir = os.path.dirname(sim_dir)
        else:
            base_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "uploads"
            )
    path = Path(base_dir) / "quotes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _quote_payload_path(quote_dir: Path, quote_id: str) -> Optional[Path]:
    """Retrouve le fichier ``quote_*_<short>.json`` correspondant à un quote_id.

    Le ``quote_id`` est de la forme ``q_<hex8>`` ; le filename inclut un
    timestamp et le ``hex8`` après ``quote_``. On scan le dossier et on
    matche par suffix.
    """
    if not quote_id or not isinstance(quote_id, str):
        return None
    short = quote_id.replace("q_", "").strip()
    if not short:
        return None
    for entry in quote_dir.iterdir():
        if not entry.is_file():
            continue
        name = entry.name
        if (
            name.startswith("quote_")
            and name.endswith(f"_{short}.json")
            and ".status.json" not in name
        ):
            return entry
    return None


def _status_sidecar_path(quote_payload_path: Path) -> Path:
    """Retourne le chemin du sidecar ``quote_*.status.json`` à côté du fichier."""
    # quote_20260429T190147_22f0e5c6.json → quote_20260429T190147_22f0e5c6.status.json
    return quote_payload_path.with_name(
        quote_payload_path.stem + ".status.json"
    )


# ─── Lecture ─────────────────────────────────────────────────────────────────


def _safe_load_json(path: Path) -> Optional[Dict[str, Any]]:
    """Charge un JSON sans crasher en cas de fichier corrompu."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read JSON %s: %s", path, exc)
    return None


def read_quote_payload(quote_id: str) -> Optional[Dict[str, Any]]:
    """Lit le payload original d'un devis depuis le filesystem."""
    qdir = quotes_dir()
    payload_path = _quote_payload_path(qdir, quote_id)
    if payload_path is None:
        return None
    return _safe_load_json(payload_path)


def read_quote_status(quote_id: str) -> Dict[str, Any]:
    """Lit le sidecar status du devis ; retourne un défaut si absent.

    Le défaut est cohérent avec la sémantique « le devis vient d'arriver
    via le formulaire public » : statut ``received`` + history vide.
    """
    qdir = quotes_dir()
    payload_path = _quote_payload_path(qdir, quote_id)
    if payload_path is None:
        return _default_status_payload()
    sidecar = _status_sidecar_path(payload_path)
    if not sidecar.exists():
        return _default_status_payload()
    data = _safe_load_json(sidecar)
    if data is None:
        return _default_status_payload()
    # Sanitise : impose les clés attendues même si le sidecar est partiel.
    return {
        "status": data.get("status") if data.get("status") in VALID_STATUSES else DEFAULT_STATUS,
        "history": data.get("history") or [],
        "payment_link": data.get("payment_link"),
        "last_email_sent_at": data.get("last_email_sent_at"),
        "notes": data.get("notes"),
        "delivered_url": data.get("delivered_url"),
    }


def _default_status_payload() -> Dict[str, Any]:
    return {
        "status": DEFAULT_STATUS,
        "history": [],
        "payment_link": None,
        "last_email_sent_at": None,
        "notes": None,
        "delivered_url": None,
    }


def list_quotes(
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """Liste les devis du plus récent au plus ancien, avec leur sidecar.

    Retourne ``(items, total)`` où ``items`` est la page demandée (avec
    ``payload`` + ``status``) et ``total`` est le nombre total de devis
    correspondant au filtre.
    """
    qdir = quotes_dir()
    if not qdir.exists():
        return [], 0

    # Liste tous les fichiers payload (exclut les sidecars *.status.json).
    payload_files: List[Path] = []
    for entry in qdir.iterdir():
        if not entry.is_file():
            continue
        name = entry.name
        if (
            name.startswith("quote_")
            and name.endswith(".json")
            and ".status.json" not in name
        ):
            payload_files.append(entry)

    # Tri : plus récent d'abord (filename ISO timestamp en préfixe).
    payload_files.sort(key=lambda p: p.name, reverse=True)

    items: List[Dict[str, Any]] = []
    for path in payload_files:
        payload = _safe_load_json(path)
        if payload is None:
            continue
        sidecar = _status_sidecar_path(path)
        if sidecar.exists():
            status_data = _safe_load_json(sidecar) or _default_status_payload()
            current_status = (
                status_data.get("status")
                if status_data.get("status") in VALID_STATUSES
                else DEFAULT_STATUS
            )
        else:
            current_status = DEFAULT_STATUS
            status_data = _default_status_payload()

        if status_filter and status_filter in VALID_STATUSES:
            if current_status != status_filter:
                continue

        items.append({
            "quote_id": payload.get("quote_id") or _quote_id_from_filename(path.name),
            "filename": path.name,
            "submitted_at": payload.get("submitted_at"),
            "payload": payload,
            "status": {
                "status": current_status,
                "history": status_data.get("history") or [],
                "payment_link": status_data.get("payment_link"),
                "last_email_sent_at": status_data.get("last_email_sent_at"),
                "notes": status_data.get("notes"),
                "delivered_url": status_data.get("delivered_url"),
            },
        })

    total = len(items)
    page = items[offset : offset + limit]
    return page, total


def _quote_id_from_filename(filename: str) -> str:
    """Extrait le ``q_<hex8>`` d'un nom de fichier ``quote_<ts>_<hex8>.json``."""
    base = filename
    if base.endswith(".json"):
        base = base[:-5]
    parts = base.split("_")
    if len(parts) >= 3:
        return f"q_{parts[-1]}"
    return ""


# ─── Écriture / transitions ──────────────────────────────────────────────────


def update_quote_status(
    quote_id: str,
    *,
    new_status: str,
    by_email: Optional[str] = None,
    notes: Optional[str] = None,
    payment_link: Optional[str] = None,
    delivered_url: Optional[str] = None,
    last_email_sent_at: Optional[str] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Met à jour le sidecar status, en validant la transition.

    Returns ``(ok, error_code, new_status_payload)``. En cas d'échec :
      - ``QUOTE_NOT_FOUND`` : aucun fichier payload pour ce quote_id.
      - ``INVALID_STATUS`` : ``new_status`` n'est pas dans VALID_STATUSES.
      - ``INVALID_TRANSITION`` : current → new_status non autorisé.
      - ``WRITE_FAILED`` : erreur disque.
    """
    if new_status not in VALID_STATUSES:
        return False, "INVALID_STATUS", None

    qdir = quotes_dir()
    payload_path = _quote_payload_path(qdir, quote_id)
    if payload_path is None:
        return False, "QUOTE_NOT_FOUND", None

    current_status_payload = read_quote_status(quote_id)
    current_status = current_status_payload["status"]

    if not is_valid_transition(current_status, new_status):
        logger.warning(
            "Invalid transition rejected: %s → %s for quote %s",
            current_status, new_status, quote_id,
        )
        return False, "INVALID_TRANSITION", None

    # Conserve l'ancien historique + ajoute la nouvelle entrée.
    history: List[Dict[str, Any]] = list(current_status_payload.get("history") or [])
    history.append({
        "status": new_status,
        "at": _iso_now(),
        "by": by_email,
        "notes": notes,
    })

    new_payload = {
        "status": new_status,
        "history": history,
        "payment_link": (
            payment_link
            if payment_link is not None
            else current_status_payload.get("payment_link")
        ),
        "last_email_sent_at": (
            last_email_sent_at
            if last_email_sent_at is not None
            else current_status_payload.get("last_email_sent_at")
        ),
        "notes": (
            notes
            if notes is not None
            else current_status_payload.get("notes")
        ),
        "delivered_url": (
            delivered_url
            if delivered_url is not None
            else current_status_payload.get("delivered_url")
        ),
    }

    sidecar = _status_sidecar_path(payload_path)
    try:
        sidecar.write_text(
            json.dumps(new_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.error("Failed to write status sidecar %s: %s", sidecar, exc)
        return False, "WRITE_FAILED", None

    return True, "OK", new_payload


def update_quote_notes(
    quote_id: str,
    *,
    notes: str,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Met à jour uniquement les notes admin (sans transition de statut)."""
    qdir = quotes_dir()
    payload_path = _quote_payload_path(qdir, quote_id)
    if payload_path is None:
        return False, "QUOTE_NOT_FOUND", None

    current = read_quote_status(quote_id)
    new_payload = {**current, "notes": notes}

    sidecar = _status_sidecar_path(payload_path)
    try:
        sidecar.write_text(
            json.dumps(new_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.error("Failed to write notes sidecar %s: %s", sidecar, exc)
        return False, "WRITE_FAILED", None

    return True, "OK", new_payload


def _iso_now() -> str:
    """Timestamp ISO 8601 UTC sans microsecondes."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
