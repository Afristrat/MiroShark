#!/usr/bin/env python3
"""US-114 — Rétro-attribution des devis filesystem → table Supabase ``quote_ownership``.

Ce script lit ``backend/uploads/quotes/quote_*.json`` et insère une ligne
``quote_ownership`` pour chaque devis non encore lié à une org. Par défaut,
tous les devis sont attribués à l'organisation Bassira interne
``aimpower-bassira`` (slug seedé en étape A de ``supabase/seed.sql``).

Idempotent : ré-exécutable autant de fois que nécessaire — la clé primaire
``quote_id`` empêche tout doublon, les insertions dupliquées sont silencées.

Usage
─────

    # Inventaire lisible (pas d'écriture)
    cd backend && uv run python ../scripts/migrate_quotes_to_supabase.py --dry-run

    # Migration effective vers l'org par défaut (aimpower-bassira)
    cd backend && uv run python ../scripts/migrate_quotes_to_supabase.py --apply

    # Migration vers un slug d'org explicite
    cd backend && uv run python ../scripts/migrate_quotes_to_supabase.py \
        --apply --org-slug acme-corp

    # Pointer vers un autre dossier (snapshot prod)
    cd backend && uv run python ../scripts/migrate_quotes_to_supabase.py \
        --apply --quotes-dir /snap/uploads/quotes

Variables d'environnement requises pour ``--apply`` :
    - SUPABASE_URL
    - SUPABASE_SERVICE_ROLE_KEY

Ces variables sont automatiquement chargées depuis l'environnement Coolify
en prod, ou depuis un ``.env`` local si python-dotenv est en place.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


# Layout repo : ``scripts/migrate_quotes_to_supabase.py`` → racine = parent.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
DEFAULT_QUOTES_DIR = _BACKEND_DIR / "uploads" / "quotes"


def _load_quote_payloads(quotes_dir: Path) -> List[Dict[str, Any]]:
    """Lit tous les ``quote_*.json`` (hors sidecars ``*.status.json``)."""
    if not quotes_dir.is_dir():
        print(f"[INFO] No quotes directory at {quotes_dir} — nothing to do.")
        return []
    out: List[Dict[str, Any]] = []
    for entry in sorted(quotes_dir.iterdir()):
        if not entry.is_file():
            continue
        name = entry.name
        if not (name.startswith("quote_") and name.endswith(".json")):
            continue
        if ".status.json" in name:
            continue
        try:
            with open(entry, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                out.append(data)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[WARN] Could not read {entry}: {exc}", file=sys.stderr)
    return out


def _read_status_for(quotes_dir: Path, quote_id: str) -> str:
    """Lit le statut courant depuis le sidecar (fallback ``received``)."""
    short = quote_id.replace("q_", "")
    for entry in quotes_dir.iterdir():
        if (
            entry.is_file()
            and entry.name.startswith("quote_")
            and entry.name.endswith(f"_{short}.status.json")
        ):
            try:
                with open(entry, "r", encoding="utf-8") as f:
                    data = json.load(f)
                status = data.get("status")
                if isinstance(status, str) and status:
                    return status
            except (OSError, json.JSONDecodeError):
                pass
    return "received"


def _resolve_org_id(client: Any, slug: str) -> Optional[str]:
    """Résout un slug d'org en UUID via Supabase."""
    response = (
        client.table("organizations")
        .select("id")
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    if not rows:
        return None
    return rows[0].get("id")


def _print_summary(quotes: List[Dict[str, Any]], target_slug: str) -> None:
    print("=" * 70)
    print(f"Found {len(quotes)} quote(s) on filesystem.")
    print(f"Default target org slug: {target_slug}")
    print("-" * 70)
    for q in quotes:
        qid = q.get("quote_id") or "(no id)"
        email = q.get("email") or "(no email)"
        package = q.get("package") or "(no package)"
        submitted = q.get("submitted_at") or "(no date)"
        print(f"  {qid:<14} {package:<22} {email:<38} {submitted}")
    print("=" * 70)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rétro-attribuer les devis filesystem à une org Supabase (US-114)",
    )
    parser.add_argument(
        "--quotes-dir",
        type=Path,
        default=DEFAULT_QUOTES_DIR,
        help=f"Dossier des devis (default: {DEFAULT_QUOTES_DIR})",
    )
    parser.add_argument(
        "--org-slug",
        type=str,
        default="aimpower-bassira",
        help="Slug de l'org cible (default: aimpower-bassira)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Effectue les inserts (sinon dry-run pour inventaire seulement)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inventaire seulement, ne touche pas Supabase (default)",
    )
    args = parser.parse_args(argv)

    quotes_dir = args.quotes_dir.resolve()
    quotes = _load_quote_payloads(quotes_dir)
    _print_summary(quotes, args.org_slug)

    if not quotes:
        return 0

    if not args.apply or args.dry_run:
        print("[DRY-RUN] Re-run with `--apply` to insert into Supabase.")
        return 0

    # Charge le client Supabase admin via le module backend.
    sys.path.insert(0, str(_BACKEND_DIR))
    try:
        from app.auth.supabase_client import (
            SupabaseConfigError,
            get_supabase_admin,
        )
        from app.services.quote_ownership import link_quote_to_org
    except ImportError as exc:
        print(f"[ERROR] Could not import backend modules: {exc}", file=sys.stderr)
        return 2

    try:
        client = get_supabase_admin()
    except SupabaseConfigError as exc:
        print(f"[ERROR] Supabase not configured: {exc}", file=sys.stderr)
        return 3

    org_id = _resolve_org_id(client, args.org_slug)
    if not org_id:
        print(
            f"[ERROR] Org with slug '{args.org_slug}' not found in Supabase. "
            "Run supabase/seed.sql section [A] first.",
            file=sys.stderr,
        )
        return 4
    print(f"[INFO] Resolved org_id = {org_id} for slug '{args.org_slug}'.")

    inserted = 0
    skipped = 0
    failed = 0
    for q in quotes:
        qid = q.get("quote_id")
        if not qid:
            failed += 1
            continue
        status = _read_status_for(quotes_dir, qid)
        try:
            ok = link_quote_to_org(
                qid,
                org_id,
                customer_email=q.get("email") or None,
                package_id=q.get("package") or None,
                status=status,
                client=client,
            )
            if ok:
                inserted += 1
                print(f"  [+] {qid} → linked (status={status})")
            else:
                skipped += 1
                print(f"  [=] {qid} → already linked (skipped)")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  [!] {qid} → failed: {exc.__class__.__name__}: {exc}")

    print("=" * 70)
    print(f"Done. inserted={inserted} skipped={skipped} failed={failed}")
    return 0 if failed == 0 else 5


if __name__ == "__main__":
    raise SystemExit(main())
