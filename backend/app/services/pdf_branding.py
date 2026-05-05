"""Service pdf_branding Supabase (US-120).

Helpers métier autour de la table ``public.pdf_branding`` :

  - ``get_active_branding(org_id, *, client)`` — branding actif de l'org
  - ``create_branding(org_id, name, *, client, **fields)`` — insert
  - ``list_branding(org_id, *, client, limit, offset)`` — toutes les versions
  - ``update_branding(branding_id, *, client, **fields)`` — versioning insert
  - ``validate_placeholders(text)`` — whitelist XSS + placeholders autorisés

Architecture de versioning
──────────────────────────
La table est append-only. Un "update" crée une NOUVELLE row avec
``valid_from = now()`` et met ``valid_to = now()`` sur l'ancienne version.
Cela préserve l'historique complet pour l'audit.

Toutes les fonctions acceptent un client Supabase admin injecté (``client=``)
pour l'injection de doublures en tests pytest (pattern établi en US-115).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..auth.supabase_client import get_supabase_admin
from ..utils.logger import get_logger


logger = get_logger("miroshark.pdf_branding")


# ─── Constantes ─────────────────────────────────────────────────────────────

# Placeholders autorisés dans les templates header/footer.
# Tout autre placeholder (ou balise HTML) est refusé.
_ALLOWED_PLACEHOLDERS: set[str] = {
    "{{logo}}",
    "{{section}}",
    "{{page}}",
    "{{total}}",
    "{{report_id}}",
    "{{client_name}}",
    "{{date}}",
    "{{org_name}}",
    "{{generated_at}}",
}

# Regex pour extraire les placeholders {{...}} d'un template
_PLACEHOLDER_RE = re.compile(r"\{\{[^}]*\}\}")

# Regex pour détecter des balises HTML (détection XSS basique)
_HTML_TAG_RE = re.compile(r"<[a-zA-Z/!][^>]*>")

# Champs template autorisés dans create/update
_TEMPLATE_FIELDS = {
    "header_left", "header_center", "header_right",
    "footer_left", "footer_center", "footer_right",
}

# Tous les champs autorisés dans un branding
_ALL_FIELDS = _TEMPLATE_FIELDS | {
    "name", "logo_url",
    "palette_primary", "palette_secondary", "palette_text", "palette_background",
    "font_titles", "font_body", "font_mono",
    "disclaimer_text",
}


# ─── Helpers internes ────────────────────────────────────────────────────────

def _iso_now() -> str:
    """Retourne l'heure UTC courante en ISO 8601 sans microseconde."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _row_to_dict(row: Any) -> Dict[str, Any]:
    """Convertit une row Supabase (dict ou objet) en dict Python."""
    if isinstance(row, dict):
        return row
    if hasattr(row, "__dict__"):
        return row.__dict__
    return {}


# ─── Validation ─────────────────────────────────────────────────────────────

def validate_placeholders(text: str) -> tuple[bool, str]:
    """Valide un template header/footer.

    Règles :
    1. Aucune balise HTML (protection XSS).
    2. Tous les placeholders ``{{...}}`` trouvés doivent figurer dans
       la whitelist ``_ALLOWED_PLACEHOLDERS``.

    Returns:
        ``(True, "")`` si valide.
        ``(False, reason)`` si invalide avec le motif de rejet.
    """
    if not isinstance(text, str):
        return False, "Template must be a string."

    # Check XSS : aucune balise HTML
    if _HTML_TAG_RE.search(text):
        return False, "HTML tags are not allowed in templates."

    # Check placeholders
    found = _PLACEHOLDER_RE.findall(text)
    for ph in found:
        if ph not in _ALLOWED_PLACEHOLDERS:
            allowed = ", ".join(sorted(_ALLOWED_PLACEHOLDERS))
            return False, (
                f"Unknown placeholder '{ph}'. "
                f"Allowed: {allowed}"
            )

    return True, ""


def _validate_all_templates(fields: Dict[str, Any]) -> Optional[str]:
    """Valide tous les champs template présents dans ``fields``.

    Retourne un message d'erreur si un champ est invalide, None sinon.
    """
    for field in _TEMPLATE_FIELDS:
        value = fields.get(field)
        if value is None:
            continue
        ok, reason = validate_placeholders(str(value))
        if not ok:
            return f"Invalid field '{field}': {reason}"
    return None


# ─── Fonctions publiques ─────────────────────────────────────────────────────

def get_active_branding(
    org_id: str,
    *,
    client: Any = None,
) -> Optional[Dict[str, Any]]:
    """Retourne le branding PDF actif pour une org.

    « Actif » = ``valid_from <= now()`` ET ``(valid_to IS NULL OR valid_to > now())``.
    Si plusieurs versions valides existent, la plus récente (valid_from DESC) est
    retournée en premier.

    Args:
        org_id: UUID de l'organisation.
        client: Client Supabase admin (injecté par les tests). Si absent,
                utilise ``get_supabase_admin()``.

    Returns:
        Dict de la row branding ou ``None`` si aucune version active.
    """
    cli = client or get_supabase_admin()
    now = _iso_now()

    try:
        resp = (
            cli.table("pdf_branding")
            .select("*")
            .eq("org_id", org_id)
            .lte("valid_from", now)
            .or_(f"valid_to.is.null,valid_to.gt.{now}")
            .order("valid_from", desc=True)
            .limit(1)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if rows:
            return _row_to_dict(rows[0])
        return None
    except Exception as exc:  # noqa: BLE001
        logger.error("get_active_branding failed for org_id=%s: %s", org_id, exc.__class__.__name__)
        raise


def create_branding(
    org_id: str,
    name: str,
    *,
    client: Any = None,
    created_by: Optional[str] = None,
    **fields: Any,
) -> Dict[str, Any]:
    """Crée une nouvelle configuration de branding PDF.

    Args:
        org_id:     UUID de l'organisation.
        name:       Nom de la configuration (ex : « Rapport Standard »).
        client:     Client Supabase admin.
        created_by: UUID de l'utilisateur créateur (audit).
        **fields:   Champs optionnels (header_left, palette_primary, etc.).

    Returns:
        La row créée en base.

    Raises:
        ValueError: Si des champs inconnus sont fournis ou si un template
                    contient des placeholders non autorisés.
    """
    cli = client or get_supabase_admin()

    # Validation des champs
    unknown = set(fields.keys()) - _ALL_FIELDS - {"name"}
    if unknown:
        raise ValueError(f"Unknown branding fields: {sorted(unknown)}")

    error = _validate_all_templates(fields)
    if error:
        raise ValueError(error)

    payload: Dict[str, Any] = {
        "org_id": org_id,
        "name": name.strip(),
        "valid_from": _iso_now(),
    }
    if created_by:
        payload["created_by"] = created_by

    # Copier les champs optionnels (exclure name déjà posé)
    for key, val in fields.items():
        if key != "name":
            payload[key] = val

    try:
        resp = (
            cli.table("pdf_branding")
            .insert(payload)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if rows:
            return _row_to_dict(rows[0])
        raise RuntimeError("Insert returned no data.")
    except Exception as exc:  # noqa: BLE001
        logger.error("create_branding failed for org_id=%s: %s", org_id, exc.__class__.__name__)
        raise


def list_branding(
    org_id: str,
    *,
    client: Any = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Liste toutes les versions de branding d'une org (historique complet).

    Args:
        org_id:  UUID de l'organisation.
        client:  Client Supabase admin.
        limit:   Nombre max de rows à retourner (défaut 20).
        offset:  Décalage pour la pagination.

    Returns:
        Liste de dicts, triée par ``valid_from DESC``.
    """
    cli = client or get_supabase_admin()

    try:
        resp = (
            cli.table("pdf_branding")
            .select("*")
            .eq("org_id", org_id)
            .order("valid_from", desc=True)
            .limit(limit)
            .offset(offset)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        return [_row_to_dict(r) for r in rows]
    except Exception as exc:  # noqa: BLE001
        logger.error("list_branding failed for org_id=%s: %s", org_id, exc.__class__.__name__)
        raise


def update_branding(
    branding_id: str,
    *,
    client: Any = None,
    created_by: Optional[str] = None,
    **fields: Any,
) -> Dict[str, Any]:
    """Met à jour un branding par versioning insert.

    Logique :
    1. Lit la row existante (``branding_id``).
    2. La marque comme expirée : ``valid_to = now()``.
    3. Crée une nouvelle row avec les données fusionnées + ``valid_from = now()``.

    Args:
        branding_id: UUID de la row branding à « mettre à jour ».
        client:      Client Supabase admin.
        created_by:  UUID de l'utilisateur modifiant (audit).
        **fields:    Champs à modifier.

    Returns:
        La nouvelle row créée.

    Raises:
        ValueError: Si des champs inconnus sont fournis ou templates invalides.
        KeyError:   Si ``branding_id`` n'existe pas.
    """
    cli = client or get_supabase_admin()

    unknown = set(fields.keys()) - _ALL_FIELDS
    if unknown:
        raise ValueError(f"Unknown branding fields: {sorted(unknown)}")

    error = _validate_all_templates(fields)
    if error:
        raise ValueError(error)

    # 1. Lire la row existante
    try:
        resp = (
            cli.table("pdf_branding")
            .select("*")
            .eq("id", branding_id)
            .limit(1)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        logger.error("update_branding fetch failed for id=%s: %s", branding_id, exc.__class__.__name__)
        raise

    if not rows:
        raise KeyError(f"pdf_branding row not found: {branding_id}")

    existing = _row_to_dict(rows[0])
    now = _iso_now()

    # 2. Marquer l'ancienne version comme expirée
    try:
        cli.table("pdf_branding").update({"valid_to": now}).eq("id", branding_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.error("update_branding expire failed for id=%s: %s", branding_id, exc.__class__.__name__)
        raise

    # 3. Créer la nouvelle version (merge ancienne + nouveaux champs)
    new_payload: Dict[str, Any] = {
        "org_id": existing.get("org_id"),
        "name": fields.get("name", existing.get("name")),
        "logo_url": fields.get("logo_url", existing.get("logo_url")),
        "header_left": fields.get("header_left", existing.get("header_left")),
        "header_center": fields.get("header_center", existing.get("header_center")),
        "header_right": fields.get("header_right", existing.get("header_right")),
        "footer_left": fields.get("footer_left", existing.get("footer_left")),
        "footer_center": fields.get("footer_center", existing.get("footer_center")),
        "footer_right": fields.get("footer_right", existing.get("footer_right")),
        "palette_primary": fields.get("palette_primary", existing.get("palette_primary")),
        "palette_secondary": fields.get("palette_secondary", existing.get("palette_secondary")),
        "palette_text": fields.get("palette_text", existing.get("palette_text")),
        "palette_background": fields.get("palette_background", existing.get("palette_background")),
        "font_titles": fields.get("font_titles", existing.get("font_titles")),
        "font_body": fields.get("font_body", existing.get("font_body")),
        "font_mono": fields.get("font_mono", existing.get("font_mono")),
        "disclaimer_text": fields.get("disclaimer_text", existing.get("disclaimer_text")),
        "valid_from": now,
        "valid_to": None,
    }
    if created_by:
        new_payload["created_by"] = created_by

    try:
        resp2 = (
            cli.table("pdf_branding")
            .insert(new_payload)
            .execute()
        )
        rows2 = getattr(resp2, "data", None) or []
        if rows2:
            return _row_to_dict(rows2[0])
        raise RuntimeError("Versioned insert returned no data.")
    except Exception as exc:  # noqa: BLE001
        logger.error("update_branding insert failed: %s", exc.__class__.__name__)
        raise
