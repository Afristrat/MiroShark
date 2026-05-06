"""
snapshot.py — Snapshots immuables de rapports approuvés (US-128).

Crée, vérifie et liste des snapshots SHA256-authentifiés de rapports PDF Bassira.

Structure du snapshot :
    snapshots/<report_id>/v<version>/
        full.md                      # markdown final
        full.pdf                     # PDF rendu
        branding.json                # snapshot du row pdf_branding (ou {})
        charts/<chart_name>.png      # charts au moment du snapshot
        metadata.json                # {sha256_hash_global, generated_at, template_version,
                                     #  branding_version, fonts_versions}

Le SHA256 global est calculé sur la concaténation triée (par nom relatif) des
contenus de tous les fichiers du snapshot SAUF metadata.json lui-même.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("miroshark.snapshot")

# Base par défaut (relative à backend/ à l'exécution)
_DEFAULT_BASE: Optional[Path] = None


def _default_base_dir() -> Path:
    """Retourne le répertoire racine par défaut des snapshots.

    Résolu à l'exécution pour que les tests puissent surcharger
    la constante sans problème d'ordre d'import.
    """
    global _DEFAULT_BASE
    if _DEFAULT_BASE is None:
        _DEFAULT_BASE = (
            Path(__file__).resolve().parent.parent.parent.parent  # backend/
            / "uploads"
            / "report_snapshots"
        )
    return _DEFAULT_BASE


# ─── Exception ───────────────────────────────────────────────────────────────


class SnapshotError(Exception):
    """Levée en cas d'erreur irrécupérable lors du snapshot."""


# ─── Helpers privés ──────────────────────────────────────────────────────────


def _snapshot_dir(report_id: str, version: int, base_dir: Optional[Path]) -> Path:
    """Retourne le chemin absolu du répertoire d'un snapshot."""
    root = base_dir if base_dir is not None else _default_base_dir()
    return root / report_id / f"v{version}"


def _compute_global_sha256(snapshot_path: Path) -> str:
    """Calcule le SHA256 global sur tous les fichiers du snapshot (hors metadata.json).

    Ordre déterministe : noms relatifs triés lexicographiquement.
    """
    hasher = hashlib.sha256()
    files = sorted(
        (p for p in snapshot_path.rglob("*") if p.is_file() and p.name != "metadata.json"),
        key=lambda p: str(p.relative_to(snapshot_path)),
    )
    for f in files:
        # Inclure le nom relatif pour détecter toute suppression/renommage.
        hasher.update(str(f.relative_to(snapshot_path)).encode("utf-8"))
        hasher.update(f.read_bytes())
    return hasher.hexdigest()


# ─── API publique ─────────────────────────────────────────────────────────────


def create_snapshot(
    report_id: str,
    *,
    version: int,
    markdown: str,
    pdf_bytes: bytes,
    branding: Optional[Dict],
    chart_pngs: Dict[str, bytes],
    base_dir: Optional[Path] = None,
) -> Dict:
    """Crée un snapshot immuable d'un rapport approuvé.

    Args:
        report_id:   Identifiant du rapport (ex. ``report_abc123``).
        version:     Numéro de version (entier ≥ 1).
        markdown:    Texte Markdown final (GFM, avec front-matter).
        pdf_bytes:   Bytes du PDF rendu (avec watermark/signature si applicable).
        branding:    Row pdf_branding actif (dict) ou ``None``.
        chart_pngs:  Mapping ``{chart_name: png_bytes}``.
        base_dir:    Répertoire racine des snapshots. Défaut :
                     ``backend/uploads/report_snapshots/``.

    Returns:
        ``{"path": str, "sha256": str, "version": int}``

    Raises:
        SnapshotError: Si la version existe déjà ou en cas d'erreur I/O.
    """
    snap_dir = _snapshot_dir(report_id, version, base_dir)

    if snap_dir.exists():
        raise SnapshotError(
            f"Snapshot v{version} existe déjà pour report_id={report_id} : {snap_dir}"
        )

    try:
        snap_dir.mkdir(parents=True, exist_ok=False)

        # full.md
        (snap_dir / "full.md").write_text(markdown, encoding="utf-8")

        # full.pdf
        (snap_dir / "full.pdf").write_bytes(pdf_bytes)

        # branding.json
        branding_data = branding if isinstance(branding, dict) else {}
        (snap_dir / "branding.json").write_text(
            json.dumps(branding_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # charts/
        if chart_pngs:
            charts_dir = snap_dir / "charts"
            charts_dir.mkdir(exist_ok=True)
            for name, png_bytes in chart_pngs.items():
                safe_name = name.replace("/", "_").replace("\\", "_")
                (charts_dir / f"{safe_name}.png").write_bytes(png_bytes)

        # SHA256 global (avant écriture metadata.json)
        sha256_hex = _compute_global_sha256(snap_dir)

        # metadata.json
        generated_at = datetime.now(tz=timezone.utc).isoformat()
        metadata = {
            "sha256_hash_global": sha256_hex,
            "generated_at": generated_at,
            "template_version": "1.0.0",
            "branding_version": str(branding_data.get("id", "default")) if branding_data else "default",
            "fonts_versions": {},
            "report_id": report_id,
            "version": version,
        }
        (snap_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    except SnapshotError:
        raise
    except Exception as exc:
        # Nettoyage partiel en cas d'erreur
        import shutil
        if snap_dir.exists():
            shutil.rmtree(snap_dir, ignore_errors=True)
        raise SnapshotError(f"Échec création snapshot v{version} : {exc}") from exc

    logger.info(
        "Snapshot créé : report_id=%s version=%d sha256=%s path=%s",
        report_id, version, sha256_hex[:16] + "…", snap_dir,
    )

    return {
        "path": str(snap_dir),
        "sha256": sha256_hex,
        "version": version,
    }


def verify_snapshot(
    report_id: str,
    version: int,
    *,
    base_dir: Optional[Path] = None,
) -> bool:
    """Vérifie qu'un snapshot n'a pas été altéré.

    Recalcule le SHA256 global et le compare à celui stocké dans
    ``metadata.json``.

    Returns:
        ``True`` si le snapshot est intact, ``False`` sinon.

    Raises:
        SnapshotError: Si le snapshot n'existe pas ou si metadata.json
                       est absent/illisible.
    """
    snap_dir = _snapshot_dir(report_id, version, base_dir)
    if not snap_dir.exists():
        raise SnapshotError(
            f"Snapshot introuvable : report_id={report_id} version={version}"
        )

    metadata_path = snap_dir / "metadata.json"
    if not metadata_path.exists():
        raise SnapshotError(
            f"metadata.json absent du snapshot v{version} (report_id={report_id})"
        )

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SnapshotError(f"metadata.json illisible : {exc}") from exc

    stored_hash = metadata.get("sha256_hash_global", "")
    if not stored_hash:
        raise SnapshotError("sha256_hash_global absent de metadata.json")

    computed_hash = _compute_global_sha256(snap_dir)
    ok = computed_hash == stored_hash

    if not ok:
        logger.warning(
            "Snapshot ALTÉRÉ : report_id=%s version=%d stored=%s computed=%s",
            report_id, version, stored_hash[:16] + "…", computed_hash[:16] + "…",
        )
    else:
        logger.debug(
            "Snapshot vérifié OK : report_id=%s version=%d", report_id, version
        )

    return ok


def list_snapshots(
    report_id: str,
    *,
    base_dir: Optional[Path] = None,
) -> List[Dict]:
    """Liste les versions de snapshots existantes pour un rapport.

    Returns:
        Liste de dicts ``{"version": int, "path": str, "generated_at": str, "sha256": str}``
        triée par version croissante.
    """
    root = base_dir if base_dir is not None else _default_base_dir()
    report_root = root / report_id
    if not report_root.exists():
        return []

    result: List[Dict] = []
    for entry in report_root.iterdir():
        if not entry.is_dir() or not entry.name.startswith("v"):
            continue
        try:
            ver = int(entry.name[1:])
        except ValueError:
            continue

        metadata_path = entry / "metadata.json"
        generated_at = ""
        sha256_hex = ""
        if metadata_path.exists():
            try:
                meta = json.loads(metadata_path.read_text(encoding="utf-8"))
                generated_at = meta.get("generated_at", "")
                sha256_hex = meta.get("sha256_hash_global", "")
            except (json.JSONDecodeError, OSError):
                pass

        result.append({
            "version": ver,
            "path": str(entry),
            "generated_at": generated_at,
            "sha256": sha256_hex,
        })

    result.sort(key=lambda d: d["version"])
    return result
