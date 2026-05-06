"""
snapshot.py — Snapshot PDF Bassira (US-128).

Sauvegarde le PDF final généré dans le dossier report sur le filesystem
et retourne le chemin absolu du fichier.

API publique :
    ``create_snapshot(report_id, pdf_bytes, variant, lang) -> Path``

Le fichier est écrit dans :
    app/uploads/reports/<report_id>/<variant>_<lang>.pdf

Si le dossier n'existe pas, il est créé automatiquement.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("miroshark.snapshot")

# Répertoires racines (mêmes calculs que loader.py)
_THIS_DIR = Path(__file__).resolve().parent          # …/report_pdf/
_BACKEND_DIR = _THIS_DIR.parent.parent.parent         # …/backend/
_UPLOADS_DIR = _BACKEND_DIR / "app" / "uploads"
_REPORTS_DIR = _UPLOADS_DIR / "reports"


def create_snapshot(
    report_id: str,
    pdf_bytes: bytes,
    variant: str = "full",
    lang: str = "fr",
    *,
    rep_base_dir: Optional[Path] = None,
) -> Path:
    """Sauvegarde le PDF dans le dossier report et retourne le chemin absolu.

    Args:
        report_id:    Identifiant du rapport (format report_<12hex>).
        pdf_bytes:    Bytes PDF à sauvegarder.
        variant:      Variante du rapport {full, exec, public, one-pager}.
        lang:         Langue du rapport {fr, en, ar}.
        rep_base_dir: Override du répertoire racine des rapports (tests).

    Returns:
        Path absolu du fichier PDF sauvegardé.

    Raises:
        OSError: Si l'écriture sur disque échoue.
    """
    base = rep_base_dir or _REPORTS_DIR
    rep_dir = base / report_id
    rep_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{variant}_{lang}.pdf"
    pdf_path = rep_dir / filename

    pdf_path.write_bytes(pdf_bytes)
    logger.info(
        "Snapshot PDF sauvegardé : %s (%d bytes).",
        pdf_path,
        len(pdf_bytes),
    )
    return pdf_path
