"""
watermark.py — Filigrane diagonal pâle sur PDF Bassira (US-128).

Applique un filigrane « confidentiel » sur chaque page de contenu d'un PDF
(la cover page est ignorée par défaut).

Implémentation :
    - Ouverture du PDF via pypdf (PdfReader / PdfWriter).
    - Pour chaque page cible : création d'un overlay PDF minimal via reportlab
      (canvas avec texte diagonal 36pt, gris #888888, opacité 0.08).
    - Merge page originale + overlay via pypdf page.merge_page().

Dépendances :
    - pypdf >= 4  (déjà présent dans pyproject.toml)
    - reportlab >= 4.5 (déjà présent dans pyproject.toml)
"""

from __future__ import annotations

import io
import logging
from typing import Optional

logger = logging.getLogger("miroshark.watermark")


def apply_watermark_to_pdf(
    pdf_bytes: bytes,
    *,
    recipient_name: str,
    recipient_company: Optional[str] = None,
    additional_text: str = "CONFIDENTIEL · NDA",
    skip_first_page: bool = True,
) -> bytes:
    """Applique un filigrane diagonal pâle sur chaque page du PDF.

    Args:
        pdf_bytes:        Bytes du PDF original.
        recipient_name:   Nom du destinataire.
        recipient_company: Entreprise du destinataire (optionnel).
        additional_text:  Texte complémentaire (défaut : «CONFIDENTIEL · NDA»).
        skip_first_page:  Si True, la première page (cover) n'est pas filigranée.

    Returns:
        Bytes du PDF avec filigranes.

    Raises:
        ImportError: Si pypdf ou reportlab ne sont pas installés.
        ValueError:  Si pdf_bytes est vide.
    """
    if not pdf_bytes:
        raise ValueError("pdf_bytes ne peut pas être vide")

    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise ImportError("pypdf >= 4 est requis pour le filigrane") from exc

    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import HexColor
    except ImportError as exc:
        raise ImportError("reportlab >= 4.5 est requis pour le filigrane") from exc

    # Construire le texte du filigrane
    parts = [recipient_name]
    if recipient_company:
        parts.append(recipient_company)
    parts.append(additional_text)
    watermark_text = " — ".join(parts)

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()

    for page_index, page in enumerate(reader.pages):
        if skip_first_page and page_index == 0:
            # Cover : ajout sans filigrane
            writer.add_page(page)
            continue

        # Dimensions de la page cible
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        # Créer l'overlay filigrane via reportlab
        overlay_buffer = io.BytesIO()
        c = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))

        # Style : gris #888888, opacité ~8 %
        c.setFillColor(HexColor("#888888"))
        c.setFillAlpha(0.08)

        # Police : Helvetica (fallback universel — Outfit non dispo en reportlab standard)
        c.setFont("Helvetica", 36)

        # Rotation -30° centré sur la page
        c.saveState()
        c.translate(page_width / 2, page_height / 2)
        c.rotate(-30)

        # Mesurer la largeur du texte pour centrer
        text_width = c.stringWidth(watermark_text, "Helvetica", 36)
        c.drawString(-text_width / 2, 0, watermark_text)

        c.restoreState()
        c.save()

        # Merger l'overlay sur la page
        overlay_buffer.seek(0)
        overlay_reader = PdfReader(overlay_buffer)
        overlay_page = overlay_reader.pages[0]

        # Attacher d'abord la page au writer : pypdf >= 6 déprécie la
        # mutation d'une page encore rattachée au PdfReader source.
        writer.add_page(page)
        writer.pages[-1].merge_page(overlay_page)

    # Exporter le PDF final
    output_buffer = io.BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)
    result = output_buffer.read()

    logger.info(
        "Filigrane appliqué : %d pages (skip_first=%s) — texte=%r",
        len(reader.pages),
        skip_first_page,
        watermark_text[:40],
    )

    return result
