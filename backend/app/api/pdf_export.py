"""
PDF Export API — US-024
Generates a branded AIMPOWER PDF report for a finished simulation.

POST /api/simulation/<simulation_id>/export-pdf
  → 200 application/pdf   (binary PDF stream)
  → 404 if simulation not found
  → 500 on generation error
"""

from __future__ import annotations

import io
import json
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import jsonify, make_response

from . import simulation_bp
from ..services.simulation_manager import SimulationManager
from ..utils.logger import get_logger
from ..utils.validation import validate_simulation_id

logger = get_logger("miroshark.api.pdf_export")

# ── Palette AIMPOWER / Bassira ─────────────────────────────────────────────
_COLOR_ORANGE = (1.0, 0.42, 0.10)       # #FF6B1A
_COLOR_BLUE   = (0.659, 0.773, 0.855)   # #A8C5DA
_COLOR_BG     = (1.0, 0.984, 0.969)     # #FFFBF7
_COLOR_INK    = (0.063, 0.063, 0.063)   # #101010  (near-black)
_COLOR_MUTED  = (0.40, 0.40, 0.40)      # #666666


# ── Helpers ────────────────────────────────────────────────────────────────

def _load_json_file(path: str) -> Optional[Dict[str, Any]]:
    """Silently load a JSON file; return None if missing or malformed."""
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
    except Exception:
        pass
    return None


def _truncate(text: str, max_chars: int = 600) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "…"


# ── PDF builder ────────────────────────────────────────────────────────────

def _build_pdf(simulation_id: str) -> bytes:  # noqa: C901 — intentionally long builder
    """Generate the branded PDF and return raw bytes."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import Color, HexColor
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        PageTemplate,
        Paragraph,
        Spacer,
        HRFlowable,
        KeepTogether,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

    # ── Load simulation data ───────────────────────────────────────────────
    manager = SimulationManager()
    sim_dir = manager._get_simulation_dir(simulation_id, create=False)

    config   = _load_json_file(os.path.join(sim_dir, "simulation_config.json")) or {}
    outcome  = _load_json_file(os.path.join(sim_dir, "outcome.json")) or {}
    state    = manager.get_simulation(simulation_id)

    # Collect simulation requirement from the project
    sim_requirement = ""
    try:
        from ..models.project import ProjectManager
        if state and state.project_id:
            project = ProjectManager.get_project(state.project_id)
            if project:
                sim_requirement = project.simulation_requirement or ""
    except Exception:
        pass

    # Friendly title — prefer config title, fall back to sim id
    sim_title = (
        config.get("title")
        or config.get("simulation_title")
        or simulation_id
    )
    package = config.get("package") or config.get("preset") or "—"
    nb_rounds = outcome.get("rounds") or outcome.get("nb_rounds") or (
        state.current_round if state else 0
    )

    verdict     = outcome.get("verdict") or outcome.get("final_verdict") or "—"
    bullish_pct = outcome.get("bullish_pct") or outcome.get("bullish") or "—"
    bearish_pct = outcome.get("bearish_pct") or outcome.get("bearish") or "—"
    recommendations: list[str] = outcome.get("recommendations") or []

    now = datetime.now(tz=timezone.utc).strftime("%d %B %Y, %H:%M UTC")

    # ── ReportLab colours ─────────────────────────────────────────────────
    orange = Color(*_COLOR_ORANGE)
    blue   = Color(*_COLOR_BLUE)
    bg     = Color(*_COLOR_BG)
    ink    = Color(*_COLOR_INK)
    muted  = Color(*_COLOR_MUTED)

    # ── Page geometry ─────────────────────────────────────────────────────
    PAGE_W, PAGE_H = A4
    MARGIN_L = 22 * mm
    MARGIN_R = 22 * mm
    MARGIN_T = 20 * mm
    MARGIN_B = 20 * mm
    CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

    # ── Styles ────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    def _style(name: str, **kwargs) -> ParagraphStyle:
        base = ParagraphStyle(name, parent=styles["Normal"], **kwargs)
        return base

    cover_brand = _style(
        "CoverBrand",
        fontSize=26,
        fontName="Helvetica-Bold",
        textColor=orange,
        alignment=TA_LEFT,
        spaceAfter=2 * mm,
    )
    cover_sub = _style(
        "CoverSub",
        fontSize=10,
        fontName="Helvetica",
        textColor=muted,
        alignment=TA_LEFT,
        spaceAfter=10 * mm,
    )
    cover_title = _style(
        "CoverTitle",
        fontSize=20,
        fontName="Helvetica-Bold",
        textColor=ink,
        alignment=TA_LEFT,
        leading=26,
        spaceAfter=6 * mm,
    )
    cover_meta = _style(
        "CoverMeta",
        fontSize=9,
        fontName="Helvetica",
        textColor=muted,
        alignment=TA_LEFT,
        spaceAfter=2 * mm,
    )
    cover_confidential = _style(
        "CoverConfidential",
        fontSize=9,
        fontName="Helvetica-Oblique",
        textColor=orange,
        alignment=TA_LEFT,
        spaceAfter=8 * mm,
    )
    section_heading = _style(
        "SectionHeading",
        fontSize=13,
        fontName="Helvetica-Bold",
        textColor=orange,
        spaceBefore=8 * mm,
        spaceAfter=3 * mm,
    )
    body = _style(
        "Body",
        fontSize=10,
        fontName="Helvetica",
        textColor=ink,
        leading=15,
        spaceAfter=4 * mm,
    )
    label = _style(
        "Label",
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=muted,
        spaceAfter=1 * mm,
    )
    value = _style(
        "Value",
        fontSize=10,
        fontName="Helvetica",
        textColor=ink,
        spaceAfter=3 * mm,
    )
    bullet_style = _style(
        "Bullet",
        fontSize=10,
        fontName="Helvetica",
        textColor=ink,
        leading=15,
        leftIndent=12,
        spaceAfter=3 * mm,
    )
    footer_style = _style(
        "Footer",
        fontSize=8,
        fontName="Helvetica-Oblique",
        textColor=muted,
        alignment=TA_CENTER,
    )

    # ── Page callbacks (header bar + footer) ──────────────────────────────
    def _on_page(canvas, doc):
        canvas.saveState()
        # Top orange bar (4 mm)
        canvas.setFillColor(orange)
        canvas.rect(0, PAGE_H - 4 * mm, PAGE_W, 4 * mm, fill=1, stroke=0)
        # Bottom blue bar (2 mm)
        canvas.setFillColor(blue)
        canvas.rect(0, 0, PAGE_W, 2 * mm, fill=1, stroke=0)
        # Footer text
        canvas.setFont("Helvetica-Oblique", 8)
        canvas.setFillColor(muted)
        footer_text = "Généré par Bassira — prospectives.ai-mpower.com"
        canvas.drawCentredString(PAGE_W / 2, 6 * mm, footer_text)
        # Page number (skip cover = page 1)
        if doc.page > 1:
            canvas.drawRightString(PAGE_W - MARGIN_R, 6 * mm, f"Page {doc.page}")
        canvas.restoreState()

    # ── Document ──────────────────────────────────────────────────────────
    buffer = io.BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T + 4 * mm,   # clear the orange bar
        bottomMargin=MARGIN_B + 8 * mm,  # clear footer
    )
    frame = Frame(
        MARGIN_L,
        MARGIN_B + 8 * mm,
        CONTENT_W,
        PAGE_H - MARGIN_T - 4 * mm - MARGIN_B - 8 * mm,
        id="main",
    )
    doc.addPageTemplates([PageTemplate(id="normal", frames=[frame], onPage=_on_page)])

    # ── Story ─────────────────────────────────────────────────────────────
    story = []

    # ── PAGE DE GARDE ─────────────────────────────────────────────────────
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph("AIMPOWER", cover_brand))
    story.append(Paragraph("Intelligence multi-agents — rapport de simulation", cover_sub))
    story.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=orange, spaceAfter=8 * mm))

    story.append(Paragraph(_truncate(sim_title, 200), cover_title))

    story.append(Paragraph(f"<b>Simulation ID :</b> {simulation_id}", cover_meta))
    story.append(Paragraph(f"<b>Package :</b> {package}", cover_meta))
    story.append(Paragraph(f"<b>Date de génération :</b> {now}", cover_meta))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("CONFIDENTIEL — usage interne uniquement.", cover_confidential))

    story.append(Spacer(1, 20 * mm))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=blue, spaceAfter=0))
    story.append(Spacer(1, 50 * mm))

    # ── RÉSUMÉ EXÉCUTIF ───────────────────────────────────────────────────
    story.append(Paragraph("Résumé exécutif", section_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=blue, spaceAfter=3 * mm))

    if sim_requirement:
        story.append(Paragraph("Objectif de simulation", label))
        story.append(Paragraph(_truncate(sim_requirement, 800), body))
    else:
        story.append(Paragraph("Aucune description de scénario disponible pour cette simulation.", body))

    story.append(Paragraph("Package utilisé", label))
    story.append(Paragraph(str(package), value))

    # ── RÉSULTATS ─────────────────────────────────────────────────────────
    story.append(Paragraph("Résultats", section_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=blue, spaceAfter=3 * mm))

    results_block = []
    results_block.append(Paragraph("Verdict final", label))
    results_block.append(Paragraph(str(verdict), value))

    if bullish_pct != "—":
        results_block.append(Paragraph("Croyance haussière (bullish)", label))
        pct = f"{bullish_pct}%" if not str(bullish_pct).endswith("%") else str(bullish_pct)
        results_block.append(Paragraph(pct, value))

    if bearish_pct != "—":
        results_block.append(Paragraph("Croyance baissière (bearish)", label))
        pct = f"{bearish_pct}%" if not str(bearish_pct).endswith("%") else str(bearish_pct)
        results_block.append(Paragraph(pct, value))

    results_block.append(Paragraph("Nombre de rounds simulés", label))
    results_block.append(Paragraph(str(nb_rounds) if nb_rounds else "—", value))

    story.append(KeepTogether(results_block))

    # ── RECOMMANDATIONS ───────────────────────────────────────────────────
    if recommendations:
        reco_block = []
        reco_block.append(Paragraph("Recommandations", section_heading))
        reco_block.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=blue, spaceAfter=3 * mm))
        for rec in recommendations[:10]:
            if isinstance(rec, str):
                reco_block.append(Paragraph(f"• {_truncate(rec, 300)}", bullet_style))
            elif isinstance(rec, dict):
                text = rec.get("text") or rec.get("recommendation") or str(rec)
                reco_block.append(Paragraph(f"• {_truncate(text, 300)}", bullet_style))
        story.append(KeepTogether(reco_block))
    else:
        story.append(Paragraph("Recommandations", section_heading))
        story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=blue, spaceAfter=3 * mm))
        story.append(Paragraph(
            "Aucune recommandation disponible pour cette simulation. "
            "Lancez une simulation complète pour obtenir des recommandations détaillées.",
            body,
        ))

    # ── Build ─────────────────────────────────────────────────────────────
    doc.build(story)
    return buffer.getvalue()


# ── Flask endpoint ─────────────────────────────────────────────────────────

@simulation_bp.route("/<simulation_id>/export-pdf", methods=["POST"])
def export_simulation_pdf(simulation_id: str):
    """
    POST /api/simulation/<simulation_id>/export-pdf

    Generate and return a branded AIMPOWER PDF for the given simulation.

    Returns:
        200  application/pdf   — binary PDF stream
        404  if the simulation does not exist
        500  on internal generation error
    """
    try:
        # validate_simulation_id is already called by the before_request hook
        # on simulation_bp, but we keep the direct call for belt-and-suspenders
        # safety when this function is invoked in tests without the hook.
        try:
            validate_simulation_id(simulation_id)
        except ValueError as exc:
            return jsonify({
                "success": False,
                "error_code": "INVALID_SIMULATION_ID",
                "error": str(exc),
            }), 400

        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)

        if not state:
            return jsonify({
                "success": False,
                "error_code": "SIMULATION_NOT_FOUND",
                "error": f"Simulation introuvable : {simulation_id}",
            }), 404

        pdf_bytes = _build_pdf(simulation_id)

        response = make_response(pdf_bytes)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = (
            f'attachment; filename="bassira-{simulation_id}.pdf"'
        )
        response.headers["Content-Length"] = str(len(pdf_bytes))
        return response

    except Exception as exc:
        logger.error("PDF export failed for %s: %s", simulation_id, exc)
        return jsonify({
            "success": False,
            "error_code": "PDF_EXPORT_FAILED",
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }), 500
