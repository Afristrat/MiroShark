"""Service report_workflow — Workflow états 7 transitions + audit log immuable (US-126).

Lifecycle des rapports Bassira :
  GENERATING → DRAFT → IN_REVIEW → PENDING_APPROVAL → APPROVED → DELIVERED → ARCHIVED

Fonctionnalités :
  - Validation des transitions légales
  - Locking optimiste sur l'état IN_REVIEW (auto-release 30 min)
  - Audit log immuable : chaque transition insère une row dans report_audit_log
  - Toutes les opérations utilisent le client service_role (bypass RLS)

Usage :
  from app.services.report_workflow import transition, get_report_state, acquire_lock

Design :
  - Chaque fonction prend ``client=`` en paramètre optionnel pour faciliter
    les tests (injection de doublures Supabase).
  - Le client par défaut est ``get_supabase_admin()`` — service_role, bypass RLS.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from ..auth.supabase_client import get_supabase_admin
from ..utils.logger import get_logger


logger = get_logger("miroshark.services.report_workflow")


# ─── Exceptions ────────────────────────────────────────────────────────────


class WorkflowError(Exception):
    """Erreur générique du workflow rapport."""


class IllegalTransitionError(WorkflowError):
    """La transition demandée n'est pas légale depuis l'état courant."""


class LockedReportError(WorkflowError):
    """Le rapport est verrouillé par un autre utilisateur (IN_REVIEW lock)."""


# ─── Constantes ────────────────────────────────────────────────────────────

LEGAL_TRANSITIONS: Dict[str, List[str]] = {
    "GENERATING":        ["DRAFT"],
    "DRAFT":             ["IN_REVIEW", "ARCHIVED"],
    "IN_REVIEW":         ["DRAFT", "PENDING_APPROVAL", "ARCHIVED"],
    "PENDING_APPROVAL":  ["IN_REVIEW", "APPROVED", "ARCHIVED"],
    "APPROVED":          ["DELIVERED", "ARCHIVED"],
    "DELIVERED":         ["ARCHIVED"],
    "ARCHIVED":          [],
}

# Durée d'inactivité après laquelle un lock IN_REVIEW est auto-relâché
LOCK_TIMEOUT_MIN: int = 30

_TABLE_STATES = "report_states"
_TABLE_AUDIT  = "report_audit_log"


# ─── Helpers privés ────────────────────────────────────────────────────────


def _client(client=None):
    """Retourne le client fourni ou le singleton admin."""
    return client or get_supabase_admin()


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _is_lock_stale(locked_at: Optional[str]) -> bool:
    """Retourne True si le lock est trop ancien (> LOCK_TIMEOUT_MIN minutes)."""
    if not locked_at:
        return False
    try:
        if isinstance(locked_at, str):
            # Supabase retourne un ISO 8601 avec offset ou Z
            locked_dt = datetime.fromisoformat(locked_at.replace("Z", "+00:00"))
        elif isinstance(locked_at, datetime):
            locked_dt = locked_at
            if locked_dt.tzinfo is None:
                locked_dt = locked_dt.replace(tzinfo=timezone.utc)
        else:
            return False
        age = _now_utc() - locked_dt
        return age > timedelta(minutes=LOCK_TIMEOUT_MIN)
    except (ValueError, TypeError):
        return False


def _insert_audit_row(
    *,
    report_id: str,
    from_state: Optional[str],
    to_state: str,
    actor_id: Optional[str],
    actor_email: Optional[str],
    ip: Optional[str],
    user_agent: Optional[str],
    snapshot_hash: Optional[str],
    comment: Optional[str],
    cli,
) -> Dict[str, Any]:
    """Insère une ligne dans report_audit_log via service_role (bypass RLS)."""
    row: Dict[str, Any] = {
        "report_id":     report_id,
        "from_state":    from_state,
        "to_state":      to_state,
        "actor_id":      actor_id,
        "actor_email":   actor_email,
        "snapshot_hash": snapshot_hash,
        "comment":       comment,
    }
    if ip:
        row["ip_address"] = ip
    if user_agent:
        row["user_agent"] = user_agent

    resp = cli.table(_TABLE_AUDIT).insert(row).execute()
    data = getattr(resp, "data", None) or []
    return data[0] if data else row


# ─── API publique ──────────────────────────────────────────────────────────


def get_report_state(report_id: str, *, client=None) -> Optional[Dict[str, Any]]:
    """Retourne la row d'état courante du rapport, ou None si absente.

    Args:
        report_id: Identifiant du rapport (format ``report_<12hex>``).
        client:    Client Supabase injecté (None → singleton admin).

    Returns:
        Dict de la row ``report_states`` ou ``None``.
    """
    cli = _client(client)
    resp = (
        cli.table(_TABLE_STATES)
        .select("*")
        .eq("report_id", report_id)
        .limit(1)
        .execute()
    )
    data = getattr(resp, "data", None) or []
    return data[0] if data else None


def transition(
    report_id: str,
    *,
    to_state: str,
    actor_id: str,
    actor_email: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    comment: Optional[str] = None,
    snapshot_hash: Optional[str] = None,
    is_super_admin: bool = False,
    client=None,
) -> Dict[str, Any]:
    """Effectue une transition d'état sur un rapport.

    Logique :
      1. Charger l'état courant (crée une row GENERATING si absente).
      2. Valider que la transition est légale.
      3. Vérifier le lock IN_REVIEW : si le rapport est locked par quelqu'un
         d'autre ET que le lock n'est pas périmé → raise LockedReportError.
         Les super-admins bypassent ce check (``is_super_admin=True``).
      4. Updater report_states.
      5. Insérer une row dans report_audit_log.

    Args:
        report_id:      Identifiant du rapport.
        to_state:       État cible.
        actor_id:       UUID de l'acteur.
        actor_email:    Email de l'acteur (pour l'audit log).
        ip:             Adresse IP (optionnel, pour audit).
        user_agent:     User-Agent HTTP (optionnel, pour audit).
        comment:        Commentaire libre (optionnel).
        snapshot_hash:  Hash SHA-256 du contenu (optionnel, pour preuve).
        is_super_admin: True → bypass du lock IN_REVIEW.
        client:         Client Supabase injecté.

    Returns:
        Dict de la row ``report_states`` mise à jour.

    Raises:
        IllegalTransitionError: Si la transition n'est pas légale.
        LockedReportError:      Si le rapport est locké par un autre user.
        WorkflowError:          Pour toute autre erreur de workflow.
    """
    cli = _client(client)

    # 1. Charger ou créer l'état courant
    current = get_report_state(report_id, client=cli)
    from_state: Optional[str] = None

    if current is None:
        # Premier accès : on ne peut aller que vers GENERATING
        # (la row est créée par le backend au moment du lancement du rapport)
        # → on accepte l'état to_state comme état initial sans from_state
        from_state = None
        current_state = "GENERATING"
    else:
        from_state = current.get("state", "GENERATING")
        current_state = from_state

    # 2. Valider la transition
    allowed = LEGAL_TRANSITIONS.get(current_state, [])
    if to_state not in allowed:
        raise IllegalTransitionError(
            f"Transition '{current_state}' → '{to_state}' is not allowed. "
            f"Legal targets: {allowed}"
        )

    # 3. Vérifier le lock (IN_REVIEW → transition sortante)
    if current and current_state == "IN_REVIEW":
        locked_by = current.get("locked_by")
        locked_at = current.get("locked_at")
        if locked_by and str(locked_by) != str(actor_id):
            # Un autre user a le lock
            if not _is_lock_stale(locked_at):
                # Lock encore valide → on bloque sauf si super-admin
                if not is_super_admin:
                    raise LockedReportError(
                        f"Report '{report_id}' is locked by user '{locked_by}'. "
                        f"Acquire the lock first or wait {LOCK_TIMEOUT_MIN} min."
                    )

    # 4. Updater (ou créer) report_states
    now_iso = _now_utc().isoformat()
    new_version = (current.get("current_version") or 0) + 1 if current else 1
    org_id = current.get("org_id") if current else None

    state_row: Dict[str, Any] = {
        "state":               to_state,
        "current_version":     new_version,
        "last_transition_at":  now_iso,
        "last_transition_by":  actor_id,
        "updated_at":          now_iso,
    }
    # Relâcher le lock si on quitte IN_REVIEW
    if current_state == "IN_REVIEW" and to_state != "IN_REVIEW":
        state_row["locked_by"] = None
        state_row["locked_at"] = None

    if current is None:
        # Créer la row initiale (report_id absent de la table)
        state_row["report_id"]  = report_id
        state_row["state"]      = to_state
        state_row["created_at"] = now_iso
        if org_id:
            state_row["org_id"] = org_id
        resp = cli.table(_TABLE_STATES).insert(state_row).execute()
    else:
        resp = (
            cli.table(_TABLE_STATES)
            .update(state_row)
            .eq("report_id", report_id)
            .execute()
        )

    updated = getattr(resp, "data", None) or []
    new_state_row = updated[0] if updated else {**state_row, "report_id": report_id}

    # 5. Insérer une row audit log
    _insert_audit_row(
        report_id=report_id,
        from_state=from_state,
        to_state=to_state,
        actor_id=actor_id,
        actor_email=actor_email,
        ip=ip,
        user_agent=user_agent,
        snapshot_hash=snapshot_hash,
        comment=comment,
        cli=cli,
    )

    logger.info(
        "report_workflow: transition report_id=%s %s→%s actor=%s",
        report_id, from_state, to_state, actor_id,
    )

    return new_state_row


def acquire_lock(report_id: str, actor_id: str, *, client=None) -> bool:
    """Verrouille le rapport pour révision IN_REVIEW.

    Le lock permet à un seul reviewer d'être actif à la fois. Il est
    associé à ``actor_id`` et horodaté avec ``locked_at``.

    Args:
        report_id: Identifiant du rapport.
        actor_id:  UUID de l'acteur qui prend le lock.
        client:    Client Supabase injecté.

    Returns:
        True si le lock a été acquis (y compris si l'acteur possède déjà
        le lock, renouvellement), False si déjà locked par un autre user
        avec un lock encore valide.
    """
    cli = _client(client)
    current = get_report_state(report_id, client=cli)

    if current is None:
        # Rapport inconnu — on ne peut pas locker
        logger.warning("acquire_lock: report_id=%s not found", report_id)
        return False

    locked_by = current.get("locked_by")
    locked_at = current.get("locked_at")

    # Cas 1 : pas de lock
    if not locked_by:
        pass  # on peut acquérir
    # Cas 2 : l'acteur possède déjà le lock → renouvellement
    elif str(locked_by) == str(actor_id):
        pass  # on renouvelle
    # Cas 3 : lock par un autre user — vérifier si stale
    elif not _is_lock_stale(locked_at):
        return False  # lock actif par un autre user

    now_iso = _now_utc().isoformat()
    resp = (
        cli.table(_TABLE_STATES)
        .update({
            "locked_by":  actor_id,
            "locked_at":  now_iso,
            "updated_at": now_iso,
        })
        .eq("report_id", report_id)
        .execute()
    )
    updated = getattr(resp, "data", None)
    return updated is not None


def release_lock(report_id: str, actor_id: str, *, is_super_admin: bool = False, client=None) -> None:
    """Libère le lock IN_REVIEW d'un rapport.

    Seul le propriétaire du lock peut le relâcher, sauf si ``is_super_admin``
    est True (les super-admins peuvent toujours forcer le relâchement).

    Args:
        report_id:      Identifiant du rapport.
        actor_id:       UUID de l'acteur qui tente de relâcher le lock.
        is_super_admin: True → force le relâchement même si autre propriétaire.
        client:         Client Supabase injecté.

    Raises:
        WorkflowError: Si l'acteur ne possède pas le lock et n'est pas super-admin.
    """
    cli = _client(client)
    current = get_report_state(report_id, client=cli)

    if current is None:
        return  # Rien à faire

    locked_by = current.get("locked_by")
    if not locked_by:
        return  # Pas de lock — pas d'erreur

    if not is_super_admin and str(locked_by) != str(actor_id):
        raise WorkflowError(
            f"Cannot release lock on '{report_id}': "
            f"lock is owned by '{locked_by}', not '{actor_id}'."
        )

    now_iso = _now_utc().isoformat()
    cli.table(_TABLE_STATES).update({
        "locked_by":  None,
        "locked_at":  None,
        "updated_at": now_iso,
    }).eq("report_id", report_id).execute()

    logger.info(
        "report_workflow: lock released report_id=%s by actor=%s (super=%s)",
        report_id, actor_id, is_super_admin,
    )


def auto_release_stale_locks(client=None) -> int:
    """Relâche tous les locks IN_REVIEW périmés (> LOCK_TIMEOUT_MIN minutes).

    Destiné à être appelé par un cron (ou Supabase scheduled function).

    Args:
        client: Client Supabase injecté.

    Returns:
        Nombre de locks relâchés.
    """
    cli = _client(client)

    cutoff = (_now_utc() - timedelta(minutes=LOCK_TIMEOUT_MIN)).isoformat()

    # Sélectionner les rows avec un lock périmé
    resp = (
        cli.table(_TABLE_STATES)
        .select("report_id, locked_by, locked_at")
        .eq("state", "IN_REVIEW")
        .lte("locked_at", cutoff)
        .execute()
    )
    stale_rows = getattr(resp, "data", None) or []

    if not stale_rows:
        return 0

    released = 0
    now_iso = _now_utc().isoformat()
    for row in stale_rows:
        rid = row.get("report_id")
        if not rid:
            continue
        try:
            cli.table(_TABLE_STATES).update({
                "locked_by":  None,
                "locked_at":  None,
                "updated_at": now_iso,
            }).eq("report_id", rid).execute()
            released += 1
            logger.info(
                "report_workflow: auto-released stale lock report_id=%s", rid
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "report_workflow: failed to release stale lock report_id=%s: %s",
                rid, exc.__class__.__name__,
            )

    return released


def list_audit_log(report_id: str, *, limit: int = 50, client=None) -> List[Dict[str, Any]]:
    """Retourne l'historique des transitions d'un rapport.

    Ordonné du plus récent au plus ancien (``created_at desc``).

    Args:
        report_id: Identifiant du rapport.
        limit:     Nombre maximum de rows (défaut 50, max 200).
        client:    Client Supabase injecté.

    Returns:
        Liste de dicts ``report_audit_log``.
    """
    cli = _client(client)
    limit = min(limit, 200)

    resp = (
        cli.table(_TABLE_AUDIT)
        .select("*")
        .eq("report_id", report_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return getattr(resp, "data", None) or []


def init_report_state(
    report_id: str,
    org_id: str,
    *,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    client=None,
) -> Dict[str, Any]:
    """Crée la row report_states initiale (état GENERATING).

    À appeler par le backend lors du lancement d'un rapport.
    Idempotent : si la row existe déjà, retourne l'état courant.

    Args:
        report_id:    Identifiant du rapport.
        org_id:       UUID de l'org propriétaire.
        actor_id:     UUID de l'acteur déclencheur (optionnel).
        actor_email:  Email de l'acteur (optionnel, pour audit log).
        client:       Client Supabase injecté.

    Returns:
        Dict de la row ``report_states``.
    """
    cli = _client(client)
    existing = get_report_state(report_id, client=cli)
    if existing:
        return existing

    now_iso = _now_utc().isoformat()
    row: Dict[str, Any] = {
        "report_id":           report_id,
        "state":               "GENERATING",
        "current_version":     1,
        "last_transition_at":  now_iso,
        "last_transition_by":  actor_id,
        "org_id":              org_id,
        "created_at":          now_iso,
        "updated_at":          now_iso,
    }
    resp = cli.table(_TABLE_STATES).insert(row).execute()
    data = getattr(resp, "data", None) or []
    result = data[0] if data else row

    # Audit log création
    _insert_audit_row(
        report_id=report_id,
        from_state=None,
        to_state="GENERATING",
        actor_id=actor_id,
        actor_email=actor_email,
        ip=None,
        user_agent=None,
        snapshot_hash=None,
        comment="Report lifecycle initialized.",
        cli=cli,
    )

    return result
