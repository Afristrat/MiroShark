"""Endpoints admin pdf_branding (US-120).

Blueprint ``admin_branding_bp`` monté sur ``/api/admin/branding``.

Routes :
  GET    /api/admin/branding          — liste les brandings de l'org
  POST   /api/admin/branding          — crée un nouveau branding
  PATCH  /api/admin/branding/<id>     — met à jour (versioning insert)
  POST   /api/admin/branding/<id>/preview  — aperçu PNG/SVG du branding

Sécurité
────────
- Toutes les routes exigent @require_auth.
- Super-admin Bassira (is_super_admin_email) : doit fournir ``org_id``.
- Org admin/owner : peut omettre ``org_id`` si une seule org.
- DELETE n'est pas exposé via HTTP — seul le super-admin peut supprimer
  directement via Supabase service_role (moins risqué).

Preview
───────
- POST /api/admin/branding/<id>/preview génère un SVG simulant le header
  et le footer d'une page A4. Le SVG est retourné en tant que data URI
  PNG (base64) via une conversion simple côté Python, ou directement
  en SVG si la conversion n'est pas disponible.
- Le fallback SVG est toujours disponible — pas de dépendance WeasyPrint
  ni pdf2image en production.
"""

from __future__ import annotations

import base64
import logging
import textwrap
from typing import Any, Dict, Optional

from flask import Blueprint, g, jsonify, request

from ..auth.decorators import (
    is_super_admin_email,
    require_auth,
)
from ..auth.supabase_client import (
    SupabaseConfigError,
    get_supabase_admin,
    get_user_orgs,
)
from ..services import pdf_branding as pb


logger = logging.getLogger("miroshark.api.admin_branding")

# Blueprint admin monté sur /api/admin/branding
admin_branding_bp = Blueprint("admin_branding", __name__)


# ─── Helpers privés ────────────────────────────────────────────────────────


def _err(code: str, message: str, status: int):
    return jsonify({
        "success": False,
        "error_code": code,
        "error": message,
    }), status


def _resolve_org_id(
    user: Dict[str, Any],
    requested_org_id: Optional[str],
) -> tuple[Optional[str], Optional[Any]]:
    """Sélectionne l'org cible pour les opérations branding.

    - Super-admin : doit fournir ``org_id`` explicitement.
    - Org admin/owner : peut omettre si une seule org.
    """
    email = user.get("email") if isinstance(user, dict) else None
    is_super = is_super_admin_email(email)

    if is_super:
        if not requested_org_id:
            return None, _err(
                "ORG_ID_REQUIRED",
                "Super-admin must provide org_id explicitly.",
                400,
            )
        return requested_org_id, None

    user_id = user.get("id") if isinstance(user, dict) else None
    if not user_id:
        return None, _err("INVALID_TOKEN", "Token missing 'sub' claim.", 401)

    try:
        user_orgs = get_user_orgs(user_id)
    except SupabaseConfigError:
        return None, _err(
            "SUPABASE_NOT_CONFIGURED",
            "Backend Supabase admin client is not configured.",
            503,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("get_user_orgs failed: %s", exc.__class__.__name__)
        return None, _err("INTERNAL_AUTH_ERROR", "Could not resolve orgs.", 500)

    eligible = [
        o for o in user_orgs
        if o.get("role") in {"owner", "admin"}
    ]
    if not eligible:
        return None, _err(
            "INSUFFICIENT_ROLE",
            "Only org owner/admin can manage PDF branding.",
            403,
        )

    if requested_org_id:
        match = next(
            (o for o in eligible if str(o.get("id")) == str(requested_org_id)),
            None,
        )
        if match is None:
            return None, _err(
                "ORG_NOT_FOUND_FOR_USER",
                "You are not an admin/owner of this organization.",
                404,
            )
        return requested_org_id, None

    if len(eligible) == 1:
        return eligible[0].get("id"), None

    return None, _err(
        "ORG_ID_REQUIRED",
        "User is admin/owner of multiple orgs — provide org_id in the body.",
        400,
    )


def _build_preview_svg(branding: Dict[str, Any], lang: str = "fr") -> str:
    """Génère un SVG simulant le header et footer d'une page A4 PDF.

    Le SVG est une représentation visuelle du branding :
    - Rectangle A4 (595 × 842 unités SVG)
    - Header (50px) : 3 zones gauche/centre/droite avec les templates rendus
    - Zone contenu (placeholder Lorem Ipsum)
    - Footer (40px) : idem

    Args:
        branding: Dict de la row pdf_branding.
        lang:     Langue pour le disclaimer_text ('fr', 'en', 'ar').

    Returns:
        Contenu SVG complet en chaîne.
    """
    # Récupérer les valeurs avec fallbacks
    palette_primary = branding.get("palette_primary") or "#FF8551"
    palette_bg = branding.get("palette_background") or "#FAF7F2"
    palette_text = branding.get("palette_text") or "#241915"
    font_titles = branding.get("font_titles") or "Outfit"
    font_body = branding.get("font_body") or "Manrope"
    name = branding.get("name") or "Branding"

    # Résoudre les templates (remplacer les placeholders par des exemples)
    def resolve(template: str) -> str:
        if not template:
            return ""
        replacements = {
            "{{logo}}": "◈ " + (branding.get("name") or "Logo"),
            "{{section}}": "Analyse de Scénario",
            "{{page}}": "1",
            "{{total}}": "12",
            "{{report_id}}": "RPT-2026-001",
            "{{client_name}}": "Org. Exemple",
            "{{date}}": "06/05/2026",
            "{{org_name}}": branding.get("name") or "Organisation",
            "{{generated_at}}": "06/05/2026 14:30",
        }
        result = template
        for ph, val in replacements.items():
            result = result.replace(ph, val)
        return result

    header_left = resolve(branding.get("header_left") or "{{logo}}")
    header_center = resolve(branding.get("header_center") or "{{section}}")
    header_right = resolve(branding.get("header_right") or "Page {{page}}/{{total}}")
    footer_left = resolve(branding.get("footer_left") or "{{report_id}} · CONFIDENTIEL")
    footer_center = resolve(branding.get("footer_center") or "{{generated_at}}")
    footer_right = resolve(branding.get("footer_right") or "bassira.ai")

    # Disclaimer multilingue
    disclaimer_text = ""
    disclaimer_raw = branding.get("disclaimer_text")
    if isinstance(disclaimer_raw, dict):
        disclaimer_text = disclaimer_raw.get(lang) or disclaimer_raw.get("fr") or ""
    elif isinstance(disclaimer_raw, str):
        disclaimer_text = disclaimer_raw

    # Dimensions SVG (A4 ratio en px)
    W, H = 595, 842
    HEADER_H = 50
    FOOTER_H = 50
    MARGIN = 20

    # Tronquer les textes longs
    def trunc(s: str, n: int = 40) -> str:
        return s[:n] + "…" if len(s) > n else s

    svg = textwrap.dedent(f"""\
        <svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
             viewBox="0 0 {W} {H}" font-family="{font_body}, sans-serif">

          <!-- Fond de page -->
          <rect width="{W}" height="{H}" fill="{palette_bg}" rx="0"/>

          <!-- ── HEADER ── -->
          <rect x="0" y="0" width="{W}" height="{HEADER_H}"
                fill="{palette_primary}" rx="0"/>

          <!-- Header gauche -->
          <text x="{MARGIN}" y="{HEADER_H // 2 + 5}"
                font-family="{font_titles}, sans-serif"
                font-size="11" font-weight="700" fill="#ffffff"
                dominant-baseline="middle">
            {trunc(header_left, 35)}
          </text>

          <!-- Header centre -->
          <text x="{W // 2}" y="{HEADER_H // 2 + 5}"
                font-family="{font_body}, sans-serif"
                font-size="10" fill="rgba(255,255,255,0.85)"
                text-anchor="middle" dominant-baseline="middle">
            {trunc(header_center, 40)}
          </text>

          <!-- Header droite -->
          <text x="{W - MARGIN}" y="{HEADER_H // 2 + 5}"
                font-family="{font_body}, sans-serif"
                font-size="10" fill="rgba(255,255,255,0.85)"
                text-anchor="end" dominant-baseline="middle">
            {trunc(header_right, 25)}
          </text>

          <!-- ── ZONE CONTENU ── -->
          <rect x="{MARGIN}" y="{HEADER_H + 20}"
                width="{W - 2 * MARGIN}" height="{H - HEADER_H - FOOTER_H - 50}"
                fill="#ffffff" rx="4" opacity="0.6"/>

          <!-- Titre page exemple -->
          <text x="{W // 2}" y="{HEADER_H + 60}"
                font-family="{font_titles}, sans-serif"
                font-size="18" font-weight="600" fill="{palette_text}"
                text-anchor="middle">
            {trunc(name, 40)} — Aperçu
          </text>

          <!-- Lorem Ipsum lignes -->
          <text x="{MARGIN + 16}" y="{HEADER_H + 100}"
                font-size="9" fill="{palette_text}" opacity="0.5">
            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec
          </text>
          <text x="{MARGIN + 16}" y="{HEADER_H + 116}"
                font-size="9" fill="{palette_text}" opacity="0.5">
            accumsan risus vel elit tincidunt, ut sodales velit blandit.
          </text>
          <text x="{MARGIN + 16}" y="{HEADER_H + 132}"
                font-size="9" fill="{palette_text}" opacity="0.5">
            Probabilistic intelligence · Bassira · {name}
          </text>

          <!-- ── FOOTER ── -->
          <rect x="0" y="{H - FOOTER_H}" width="{W}" height="{FOOTER_H}"
                fill="rgba(36, 25, 21, 0.06)"/>
          <line x1="0" y1="{H - FOOTER_H}" x2="{W}" y2="{H - FOOTER_H}"
                stroke="{palette_primary}" stroke-width="2" opacity="0.4"/>

          <!-- Footer gauche -->
          <text x="{MARGIN}" y="{H - FOOTER_H // 2}"
                font-size="8" fill="{palette_text}" opacity="0.7"
                dominant-baseline="middle">
            {trunc(footer_left, 35)}
          </text>

          <!-- Footer centre (disclaimer) -->
          <text x="{W // 2}" y="{H - FOOTER_H // 2}"
                font-size="8" fill="{palette_text}" opacity="0.6"
                text-anchor="middle" dominant-baseline="middle">
            {trunc(disclaimer_text or footer_center, 50)}
          </text>

          <!-- Footer droite -->
          <text x="{W - MARGIN}" y="{H - FOOTER_H // 2}"
                font-size="8" fill="{palette_primary}" opacity="0.9"
                text-anchor="end" dominant-baseline="middle">
            {trunc(footer_right, 25)}
          </text>

        </svg>
    """)

    return svg


# ─── GET /api/admin/branding ──────────────────────────────────────────────────


@admin_branding_bp.route("", methods=["GET"])
@require_auth
def list_branding_endpoint():
    """Liste les brandings PDF d'une org (toutes versions).

    Query params :
        ``org_id`` — requis si super-admin ou admin multi-org.
        ``limit``  — défaut 20.
        ``offset`` — défaut 0.
    """
    user = getattr(g, "current_user", None) or {}
    requested_org_id = request.args.get("org_id")
    org_id, err = _resolve_org_id(user, requested_org_id)
    if err is not None:
        return err
    assert org_id is not None

    try:
        limit = min(int(request.args.get("limit", 20)), 100)
        offset = max(int(request.args.get("offset", 0)), 0)
    except (TypeError, ValueError):
        return _err("INVALID_PARAMS", "limit and offset must be integers.", 400)

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase admin client is not configured.", 503)

    try:
        brandings = pb.list_branding(org_id, client=cli, limit=limit, offset=offset)
    except Exception as exc:  # noqa: BLE001
        logger.error("list_branding failed: %s", exc.__class__.__name__)
        return _err("BRANDING_FETCH_FAILED", "Could not fetch brandings.", 500)

    return jsonify({
        "success": True,
        "data": {
            "brandings": brandings,
            "org_id": org_id,
        },
    }), 200


# ─── POST /api/admin/branding ─────────────────────────────────────────────────


@admin_branding_bp.route("", methods=["POST"])
@require_auth
def create_branding_endpoint():
    """Crée une nouvelle configuration de branding PDF.

    Body JSON (tous les champs sauf ``name`` sont optionnels) :
    {
      "org_id": "uuid",       // requis si super-admin ou multi-org admin
      "name": "string",       // requis
      "logo_url": "...",
      "header_left": "...",
      "header_center": "...",
      "header_right": "...",
      "footer_left": "...",
      "footer_center": "...",
      "footer_right": "...",
      "palette_primary": "#FF8551",
      "palette_secondary": "#006D44",
      "palette_text": "#241915",
      "palette_background": "#FAF7F2",
      "font_titles": "Outfit",
      "font_body": "Manrope",
      "font_mono": "JetBrains Mono",
      "disclaimer_text": {"fr": "...", "en": "...", "ar": "..."}
    }
    """
    body = request.get_json(silent=True) or {}
    name = body.get("name")

    if not isinstance(name, str) or not name.strip():
        return _err("INVALID_NAME", "Field `name` is required and must be a non-empty string.", 400)

    user = getattr(g, "current_user", None) or {}
    requested_org_id = body.get("org_id")
    org_id, err = _resolve_org_id(user, requested_org_id)
    if err is not None:
        return err
    assert org_id is not None

    # Extraire les champs optionnels du body
    optional_fields = {
        k: v for k, v in body.items()
        if k in pb._ALL_FIELDS and k != "name"
    }

    created_by = user.get("id") if isinstance(user, dict) else None

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase admin client is not configured.", 503)

    try:
        branding = pb.create_branding(
            org_id,
            name.strip(),
            client=cli,
            created_by=created_by,
            **optional_fields,
        )
    except ValueError as exc:
        return _err("INVALID_BODY", str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        logger.error("create_branding failed: %s", exc.__class__.__name__)
        return _err("BRANDING_CREATE_FAILED", "Could not create branding.", 500)

    return jsonify({
        "success": True,
        "data": {"branding": branding},
    }), 201


# ─── PATCH /api/admin/branding/<id> ──────────────────────────────────────────


@admin_branding_bp.route("/<branding_id>", methods=["PATCH"])
@require_auth
def update_branding_endpoint(branding_id: str):
    """Met à jour un branding (versioning insert).

    Crée une nouvelle row avec valid_from=now() et marque l'ancienne avec
    valid_to=now(). Tous les champs sont optionnels (seuls les champs
    fournis sont modifiés — les autres sont repris depuis la version
    précédente).

    Body JSON : mêmes champs que POST (sauf org_id immuable).
    """
    if not branding_id:
        return _err("INVALID_ID", "branding_id is required.", 400)

    body = request.get_json(silent=True) or {}
    user = getattr(g, "current_user", None) or {}

    # Vérifier que l'utilisateur a accès à l'org de ce branding
    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase admin client is not configured.", 503)

    # Lire l'org_id du branding pour valider l'accès
    try:
        resp = (
            cli.table("pdf_branding")
            .select("org_id")
            .eq("id", branding_id)
            .limit(1)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        logger.error("update branding fetch failed: %s", exc.__class__.__name__)
        return _err("BRANDING_FETCH_FAILED", "Could not fetch branding.", 500)

    if not rows:
        return _err("BRANDING_NOT_FOUND", "Branding not found.", 404)

    branding_org_id = rows[0].get("org_id") if isinstance(rows[0], dict) else None
    _, err = _resolve_org_id(user, branding_org_id)
    if err is not None:
        return err

    # Extraire les champs optionnels du body
    optional_fields = {
        k: v for k, v in body.items()
        if k in pb._ALL_FIELDS
    }

    if not optional_fields:
        return _err("NO_FIELDS", "At least one field must be provided to update.", 400)

    created_by = user.get("id") if isinstance(user, dict) else None

    try:
        new_branding = pb.update_branding(
            branding_id,
            client=cli,
            created_by=created_by,
            **optional_fields,
        )
    except ValueError as exc:
        return _err("INVALID_BODY", str(exc), 400)
    except KeyError:
        return _err("BRANDING_NOT_FOUND", "Branding not found.", 404)
    except Exception as exc:  # noqa: BLE001
        logger.error("update_branding failed: %s", exc.__class__.__name__)
        return _err("BRANDING_UPDATE_FAILED", "Could not update branding.", 500)

    return jsonify({
        "success": True,
        "data": {"branding": new_branding},
    }), 200


# ─── POST /api/admin/branding/<id>/preview ───────────────────────────────────


@admin_branding_bp.route("/<branding_id>/preview", methods=["POST"])
@require_auth
def preview_branding_endpoint(branding_id: str):
    """Génère un aperçu visuel (SVG encodé base64) du branding.

    Body JSON :
        { "lang": "fr" | "en" | "ar" }  (défaut "fr")

    Retourne :
        { "success": true, "data": { "preview_svg": "<base64>",
                                     "content_type": "image/svg+xml" } }

    Le SVG représente une page A4 avec le header et le footer rendu
    en utilisant la palette, typographie et templates du branding.
    Les placeholders {{...}} sont remplacés par des valeurs d'exemple.
    """
    if not branding_id:
        return _err("INVALID_ID", "branding_id is required.", 400)

    body = request.get_json(silent=True) or {}
    lang = body.get("lang", "fr")
    if lang not in {"fr", "en", "ar"}:
        lang = "fr"

    user = getattr(g, "current_user", None) or {}

    try:
        cli = get_supabase_admin()
    except SupabaseConfigError:
        return _err("SUPABASE_NOT_CONFIGURED", "Backend Supabase admin client is not configured.", 503)

    # Lire le branding
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
        logger.error("preview fetch failed: %s", exc.__class__.__name__)
        return _err("BRANDING_FETCH_FAILED", "Could not fetch branding.", 500)

    if not rows:
        return _err("BRANDING_NOT_FOUND", "Branding not found.", 404)

    branding = rows[0] if isinstance(rows[0], dict) else {}

    # Vérifier l'accès à l'org
    branding_org_id = branding.get("org_id")
    _, err = _resolve_org_id(user, branding_org_id)
    if err is not None:
        return err

    # Générer le SVG
    try:
        svg_content = _build_preview_svg(branding, lang=lang)
        svg_b64 = base64.b64encode(svg_content.encode("utf-8")).decode("ascii")
    except Exception as exc:  # noqa: BLE001
        logger.error("preview SVG generation failed: %s", exc.__class__.__name__)
        return _err("PREVIEW_FAILED", "Could not generate preview.", 500)

    return jsonify({
        "success": True,
        "data": {
            "preview_svg": svg_b64,
            "content_type": "image/svg+xml",
            "lang": lang,
        },
    }), 200
