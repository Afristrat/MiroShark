"""
Models API — US-088
Public endpoint to download a branded "Model Brief" PDF for a pre-calibrated model.

GET /api/models/<slug>/pdf-brief?lang=<fr|en|ar>
  → 200 application/pdf      (binary PDF stream, 4-6 pages, A4 portrait)
  → 400 INVALID_LANG          if lang not in (fr, en, ar)
  → 404 MODEL_NOT_FOUND       if no JSON file exists for the slug

Source of truth: backend/app/models_data/<slug>.json (mirrors frontend/src/models).
PDF generator: reportlab (same dependency as US-024 / US-059 to avoid bloating the stack).
"""

from __future__ import annotations

import io
import json
import os
import re
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, make_response, request

from ..utils.logger import get_logger

logger = get_logger("miroshark.api.models")

models_bp = Blueprint("models", __name__)

# ── Constants ────────────────────────────────────────────────────────────────

_SUPPORTED_LANGS = ("fr", "en", "ar")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,80}$")

# Bassira / Causse Warm Intelligence palette (same hex as US-024 PDF + frontend tokens)
_COLOR_ORANGE    = (1.0, 0.522, 0.318)    # #FF8551
_COLOR_TERRACOTA = (0.631, 0.247, 0.059)  # #A13F0F
_COLOR_GREEN     = (0.0,   0.427, 0.267)  # #006D44
_COLOR_CREAM     = (0.98,  0.969, 0.949)  # #FAF7F2
_COLOR_INK       = (0.141, 0.098, 0.082)  # #241915
_COLOR_MUTED     = (0.541, 0.388, 0.227)  # #8A7269

_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models_data")

# ── Arabic font detection (TTF supporting Arabic glyphs) ─────────────────────
# Windows ships Tahoma which has arabic glyphs; Linux distros usually carry
# DejaVuSans (apt install fonts-dejavu) or NotoSansArabic (apt install fonts-noto).
# A bundled fallback under backend/app/static/fonts/ is also accepted.
_ARABIC_FONT_NAME = "BassiraArabic"
_ARABIC_FONT_REGISTERED = False
_ARABIC_FONT_CANDIDATES = (
    # Optional bundled font (preferred — license MUST allow redistribution)
    os.path.join(os.path.dirname(os.path.dirname(__file__)),
                 "static", "fonts", "NotoSansArabic-Regular.ttf"),
    os.path.join(os.path.dirname(os.path.dirname(__file__)),
                 "static", "fonts", "Amiri-Regular.ttf"),
    # Linux system paths
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    # Windows system paths
    "C:/Windows/Fonts/tahoma.ttf",
    "C:\\Windows\\Fonts\\tahoma.ttf",
    # macOS
    "/Library/Fonts/Tahoma.ttf",
    "/System/Library/Fonts/GeezaPro.ttc",
)


def _ensure_arabic_font() -> Optional[str]:
    """Register the first available Arabic-capable TTF font with Reportlab.

    Returns the registered font name on success, or None when no candidate
    was found on this server (the caller can then degrade gracefully).
    """
    global _ARABIC_FONT_REGISTERED
    if _ARABIC_FONT_REGISTERED:
        return _ARABIC_FONT_NAME
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:  # pragma: no cover — reportlab is a hard dep
        return None
    for path in _ARABIC_FONT_CANDIDATES:
        if not os.path.isfile(path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(_ARABIC_FONT_NAME, path))
            _ARABIC_FONT_REGISTERED = True
            logger.info("Arabic font registered for PDF briefs: %s", path)
            return _ARABIC_FONT_NAME
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("Failed to register Arabic font %s: %s", path, exc)
            continue
    return None


def _shape_arabic(text: str) -> str:
    """Apply Arabic shaping + bidi reordering for visual rendering in PDF.

    Reportlab does not handle right-to-left scripts natively. We pre-process
    the string with arabic_reshaper (contextual glyph forms) then python-bidi
    (logical→visual order). If either lib is missing the original string is
    returned (worst case the PDF will look unshaped — Latin parts unaffected).
    """
    if not text:
        return ""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError:  # pragma: no cover — listed in pyproject.toml
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:  # pragma: no cover — defensive
        return text


# ── i18n strings (template chrome — body content comes from JSON) ────────────

_T = {
    "fr": {
        "brand_tagline":     "Prospective stratégique calibrée",
        "doc_kind":          "MODÈLE PRÉ-CALIBRÉ — BRIEF",
        "decision_question": "La question de décision",
        "context":           "Contexte stratégique",
        "agents_section":    "Agents simulés",
        "methodology":       "Méthodologie",
        "methodology_body": (
            "Bassira combine un moteur multi-agent calibré sur des scénarios historiques "
            "vérifiés, une couche de raisonnement contradictoire et des branches "
            "contrefactuelles. Score de Brier illustratif sur ce modèle : "
            "{brier} (0 = parfait, 0,25 = naïf, 1 = aléatoire). La méthodologie complète "
            "et l'historique des scores sont publiés sur calibration.bassira.com — "
            "calibration en cours de constitution sur les modèles publiés en 2026."
        ),
        "insights":          "Insights clés",
        "use_cases":         "Cas d'usage pour décideurs",
        "disclaimer_title":  "Note méthodologique",
        "disclaimer_body": (
            "Ce document présente un modèle pré-calibré illustratif. Les chiffres et "
            "trajectoires cités s'appuient sur des sources publiques nommées et sur la "
            "dynamique observée dans des scénarios historiques équivalents. Une analyse "
            "personnalisée à votre situation (entrants spécifiques, contre-parties "
            "nommées, calendrier propre) requiert une commande dédiée auprès de l'équipe."
        ),
        "cta_title":         "Commander cette analyse",
        "cta_email":         "devis@ai-mpower.com",
        "cta_link":          "bassira.ma/models/{slug}",
        "footer_left":       "Bassira · بصيرة",
        "footer_right":      "Page {page}",
        "cover_kind_label":  "Brief modèle",
        "sector_label":      "Secteur",
        "brier_label":       "Brier illustratif",
        "generated_on":      "Généré le {date}",
        "confidential":      "Document confidentiel · Usage professionnel",
    },
    "en": {
        "brand_tagline":     "Calibrated strategic foresight",
        "doc_kind":          "PRE-CALIBRATED MODEL — BRIEF",
        "decision_question": "The decision question",
        "context":           "Strategic context",
        "agents_section":    "Simulated agents",
        "methodology":       "Methodology",
        "methodology_body": (
            "Bassira combines a multi-agent engine calibrated on verified historical "
            "scenarios, an adversarial-reasoning layer and counterfactual branches. "
            "Illustrative Brier score on this model: {brier} (0 = perfect, 0.25 = naive, "
            "1 = random). The full methodology and score history are published on "
            "calibration.bassira.com — calibration is being assembled on models released in 2026."
        ),
        "insights":          "Key insights",
        "use_cases":         "Decision-maker use cases",
        "disclaimer_title":  "Methodological note",
        "disclaimer_body": (
            "This document presents an illustrative pre-calibrated model. Figures and "
            "trajectories cited rely on named public sources and on the dynamics observed "
            "in equivalent historical scenarios. A personalised analysis tailored to your "
            "situation (specific entrants, named counterparties, your own calendar) "
            "requires a dedicated engagement with the team."
        ),
        "cta_title":         "Order this analysis",
        "cta_email":         "devis@ai-mpower.com",
        "cta_link":          "bassira.ma/models/{slug}",
        "footer_left":       "Bassira · بصيرة",
        "footer_right":      "Page {page}",
        "cover_kind_label":  "Model brief",
        "sector_label":      "Sector",
        "brier_label":       "Illustrative Brier",
        "generated_on":      "Generated on {date}",
        "confidential":      "Confidential document · Professional use",
    },
    "ar": {
        "brand_tagline":     "استشراف استراتيجي معاير",
        "doc_kind":          "نموذج معاير مسبقاً — موجز",
        "decision_question": "سؤال القرار",
        "context":           "السياق الاستراتيجي",
        "agents_section":    "الوكلاء المُحاكَون",
        "methodology":       "المنهجية",
        "methodology_body": (
            "تجمع بصيرة محرّكاً متعدد الوكلاء معايراً على سيناريوهات تاريخية موثّقة، "
            "وطبقة استدلال تعارُضي، وفروعاً تاريخية بديلة. درجة برير التوضيحية لهذا النموذج: "
            "{brier} (0 = مثالي، 0.25 = ساذج، 1 = عشوائي). تُنشر المنهجية الكاملة وتاريخ "
            "الدرجات على calibration.bassira.com — المعايرة قيد التكوين على النماذج "
            "الصادرة في 2026."
        ),
        "insights":          "أبرز الاستنتاجات",
        "use_cases":         "حالات استعمال لصانعي القرار",
        "disclaimer_title":  "ملاحظة منهجية",
        "disclaimer_body": (
            "يُقدّم هذا المستند نموذجاً معايراً مسبقاً للتوضيح. تستند الأرقام والمسارات "
            "المذكورة إلى مصادر عمومية مُسمّاة وإلى الديناميكيات المرصودة في سيناريوهات "
            "تاريخية مماثلة. يتطلّب تحليل مخصّص لوضعكم (داخلون محدّدون، أطراف مقابلة مُسمّاة، "
            "تقويمكم الخاص) طلباً مخصّصاً لدى الفريق."
        ),
        "cta_title":         "طلب هذا التحليل",
        "cta_email":         "devis@ai-mpower.com",
        "cta_link":          "bassira.ma/models/{slug}",
        "footer_left":       "Bassira · بصيرة",
        "footer_right":      "صفحة {page}",
        "cover_kind_label":  "موجز النموذج",
        "sector_label":      "القطاع",
        "brier_label":       "برير توضيحي",
        "generated_on":      "صدر بتاريخ {date}",
        "confidential":      "مستند سري · للاستعمال المهني",
    },
}

_DATE_FMT = {
    "fr": "%d %B %Y",
    "en": "%B %d, %Y",
    "ar": "%Y-%m-%d",
}


# ── Data helpers ─────────────────────────────────────────────────────────────

def _load_model(slug: str) -> Optional[Dict[str, Any]]:
    """Load the model JSON from backend/app/models_data/<slug>.json."""
    if not _SLUG_RE.match(slug):
        return None
    path = os.path.join(_MODELS_DIR, f"{slug}.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        logger.warning("Failed to load model %s: %s", slug, exc)
        return None


def _pick(field: Any, lang: str, fallback_lang: str = "fr") -> Any:
    """Extract the localised variant of a multilingual field. Falls back to FR."""
    if isinstance(field, dict):
        if lang in field and field[lang]:
            return field[lang]
        return field.get(fallback_lang) or field.get("en") or ""
    return field or ""


def _fmt_brier(value: Any, lang: str) -> str:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return "—"
    s = f"{f:.2f}"
    if lang == "fr":
        s = s.replace(".", ",")
    return s


# ── PDF builder ──────────────────────────────────────────────────────────────

def _build_pdf(model: Dict[str, Any], lang: str) -> bytes:  # noqa: C901
    """Render a 4-6 page A4 portrait Bassira-branded brief PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import Color, HexColor
    from reportlab.platypus import (
        BaseDocTemplate, Frame, PageTemplate,
        Paragraph, Spacer, HRFlowable, KeepTogether,
        Table, TableStyle, PageBreak,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

    T = _T[lang]
    is_rtl = lang == "ar"
    align_default = TA_RIGHT if is_rtl else TA_LEFT
    align_justify = TA_RIGHT if is_rtl else TA_JUSTIFY

    # ── Font selection ──────────────────────────────────────────────────────
    # Latin: built-in Helvetica family (no extra registration required).
    # Arabic: register the first available Arabic-capable TTF on this server.
    font_regular = "Helvetica"
    font_bold    = "Helvetica-Bold"
    font_italic  = "Helvetica-Oblique"
    if is_rtl:
        ar_font = _ensure_arabic_font()
        if ar_font:
            font_regular = ar_font
            font_bold    = ar_font  # one weight; bold via paragraph styling only
            font_italic  = ar_font
        else:
            logger.warning(
                "No Arabic-capable font registered; the Arabic PDF will fall back to "
                "Helvetica and contextual glyphs will not render. Install "
                "fonts-noto-arabic or fonts-dejavu on the server, or place "
                "NotoSansArabic-Regular.ttf in backend/app/static/fonts/."
            )

    def _localise(text: str) -> str:
        """Apply Arabic shaping when needed, otherwise return text unchanged."""
        if is_rtl:
            return _shape_arabic(text)
        return text

    # ── Localised content extraction ────────────────────────────────────────
    title           = _pick(model.get("title"),               lang)
    subtitle        = _pick(model.get("subtitle"),            lang)
    summary_short   = _pick(model.get("summary_short"),       lang)
    context_long    = _pick(model.get("context_long"),        lang)
    decision_q      = _pick(model.get("decision_question"),   lang)
    cta_label       = _pick(model.get("cta_label"),           lang)
    insights        = _pick(model.get("key_insights"),        lang) or []
    use_cases       = _pick(model.get("use_cases_decisionmakers"), lang) or []
    sector          = model.get("sector", "")
    slug            = model.get("slug", "")
    brier           = model.get("brier_illustrative")
    agents          = model.get("agents_simulated") or []
    tags            = model.get("tags") or []

    if not isinstance(insights, list):
        insights = []
    if not isinstance(use_cases, list):
        use_cases = []

    now = datetime.now(tz=timezone.utc)
    try:
        date_str = now.strftime(_DATE_FMT.get(lang, "%Y-%m-%d"))
    except (ValueError, UnicodeEncodeError):
        date_str = now.strftime("%Y-%m-%d")

    brier_str = _fmt_brier(brier, lang)

    # ── Colors ──────────────────────────────────────────────────────────────
    orange  = Color(*_COLOR_ORANGE)
    terra   = Color(*_COLOR_TERRACOTA)
    green   = Color(*_COLOR_GREEN)
    ink     = Color(*_COLOR_INK)
    muted   = Color(*_COLOR_MUTED)
    cream_hex      = HexColor("#FAF7F2")
    terra_soft_hex = HexColor("#FFF3EE")
    mint_soft_hex  = HexColor("#E8F4EF")

    # ── Page geometry — A4 portrait, 2 cm margins ───────────────────────────
    PAGE_W, PAGE_H = A4
    MARGIN = 20 * mm
    CONTENT_W = PAGE_W - 2 * MARGIN

    # ── Styles ──────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    def S(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    # Cover styles
    brand_eyebrow   = S("BE",  fontSize=9,  fontName=font_bold,    textColor=muted, spaceAfter=2*mm,
                        alignment=align_default)
    brand_logo      = S("BL",  fontSize=26, fontName=font_bold,    textColor=orange, leading=30,
                        spaceAfter=1*mm, alignment=align_default)
    brand_tagline   = S("BT",  fontSize=10, fontName=font_italic,  textColor=muted,
                        spaceAfter=18*mm, alignment=align_default)
    cover_kind      = S("CK",  fontSize=10, fontName=font_bold,    textColor=terra,
                        spaceAfter=4*mm, alignment=align_default)
    cover_title     = S("CT",  fontSize=28, fontName=font_bold,    textColor=ink, leading=34,
                        spaceAfter=6*mm, alignment=align_default)
    cover_subtitle  = S("CS",  fontSize=14, fontName=font_regular, textColor=ink, leading=20,
                        spaceAfter=14*mm, alignment=align_default)
    cover_meta_lab  = S("CML", fontSize=8,  fontName=font_bold,    textColor=muted,
                        spaceAfter=1*mm, alignment=align_default)
    S("CMV", fontSize=11, fontName=font_bold,    textColor=ink,
                        spaceAfter=6*mm, alignment=align_default)
    cover_footer    = S("CF",  fontSize=8,  fontName=font_regular, textColor=muted, leading=12,
                        alignment=align_default)

    # Section / body styles
    sec_eyebrow     = S("SE",  fontSize=8,  fontName=font_bold,    textColor=orange,
                        spaceAfter=1*mm, alignment=align_default)
    sec_heading     = S("SH",  fontSize=18, fontName=font_bold,    textColor=ink, leading=22,
                        spaceAfter=4*mm, alignment=align_default)
    body_lg         = S("BL2", fontSize=11, fontName=font_regular, textColor=ink, leading=17,
                        spaceAfter=4*mm, alignment=align_justify)
    body_md         = S("BM",  fontSize=10, fontName=font_regular, textColor=ink, leading=15,
                        spaceAfter=3*mm, alignment=align_justify)
    S("BS",  fontSize=9,  fontName=font_regular, textColor=muted, leading=13,
                        spaceAfter=2*mm, alignment=align_default)
    bullet_md       = S("BUL", fontSize=10, fontName=font_regular, textColor=ink, leading=15,
                        leftIndent=14, spaceAfter=3*mm, alignment=align_default)
    decision_box    = S("DB",  fontSize=12, fontName=font_bold,    textColor=terra,
                        leading=18, spaceAfter=4*mm, alignment=align_default,
                        borderPadding=(8, 10, 8, 10),
                        borderColor=terra, borderWidth=0.7,
                        backColor=terra_soft_hex)
    methodology_box = S("MB",  fontSize=9,  fontName=font_regular, textColor=ink,
                        leading=14, spaceAfter=4*mm, alignment=align_justify,
                        borderPadding=(8, 10, 8, 10),
                        borderColor=green, borderWidth=0.5,
                        backColor=mint_soft_hex)
    cta_box         = S("CB",  fontSize=12, fontName=font_bold,    textColor=terra,
                        leading=18, spaceAfter=2*mm, alignment=TA_CENTER,
                        borderPadding=(10, 12, 10, 12),
                        borderColor=terra, borderWidth=0.8,
                        backColor=terra_soft_hex)

    # ── Page chrome (header bar + footer) ───────────────────────────────────
    def _on_page(canvas, doc):
        canvas.saveState()
        # Top accent bar (orange)
        canvas.setFillColor(orange)
        canvas.rect(0, PAGE_H - 4*mm, PAGE_W, 4*mm, fill=1, stroke=0)
        # Bottom thin terracotta accent
        canvas.setFillColor(terra)
        canvas.rect(0, 0, PAGE_W, 1.5*mm, fill=1, stroke=0)
        # Footer text
        canvas.setFillColor(muted)
        canvas.setFont(font_italic, 7)
        if is_rtl:
            canvas.drawRightString(PAGE_W - MARGIN, 4*mm, _localise(T["footer_left"]))
            canvas.drawString(MARGIN, 4*mm, _localise(T["footer_right"].format(page=doc.page)))
        else:
            canvas.drawString(MARGIN, 4*mm, T["footer_left"])
            canvas.drawRightString(PAGE_W - MARGIN, 4*mm, T["footer_right"].format(page=doc.page))
        # Center confidential ribbon
        canvas.setFont(font_regular, 7)
        canvas.drawCentredString(PAGE_W / 2, 4*mm, _localise(T["confidential"]))
        canvas.restoreState()

    # ── Document setup ──────────────────────────────────────────────────────
    buffer = io.BytesIO()
    doc = BaseDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 4*mm, bottomMargin=MARGIN + 6*mm,
        title=f"Bassira — Brief modèle {slug}",
        author="Bassira (AI-Mpower)",
        subject="Modèle pré-calibré — Brief",
        creator="Bassira PDF Brief Generator",
    )
    frame = Frame(
        MARGIN, MARGIN + 6*mm, CONTENT_W,
        PAGE_H - (MARGIN + 4*mm) - (MARGIN + 6*mm),
        id="main", showBoundary=0,
    )
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=_on_page)])

    story = []

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 1 — COVER
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 18*mm))
    story.append(Paragraph(_xml_safe(_localise(T["doc_kind"])), brand_eyebrow))
    story.append(Paragraph("BASSIRA", brand_logo))
    story.append(Paragraph(_xml_safe(_localise(T["brand_tagline"])), brand_tagline))
    story.append(HRFlowable(width=CONTENT_W, thickness=1.2, color=orange, spaceAfter=10*mm))
    story.append(Paragraph(_xml_safe(_localise(T["cover_kind_label"])), cover_kind))
    story.append(Paragraph(_xml_safe(_localise(title)), cover_title))
    story.append(Paragraph(_xml_safe(_localise(subtitle)), cover_subtitle))

    # Pills row (sector + brier) as a simple table
    sector_display = sector.replace('-', ' ').title() if sector else '—'
    pill_data = [[
        Paragraph(
            f"<b>{_xml_safe(_localise(T['sector_label']))}</b><br/>"
            f"<font size=11>{_xml_safe(_localise(sector_display))}</font>",
            cover_meta_lab,
        ),
        Paragraph(
            f"<b>{_xml_safe(_localise(T['brier_label']))}</b><br/>"
            f"<font size=11>{brier_str}</font>",
            cover_meta_lab,
        ),
    ]]
    pill_tbl = Table(pill_data, colWidths=[CONTENT_W * 0.5, CONTENT_W * 0.5])
    pill_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), cream_hex),
        ("BOX",          (0, 0), (-1, -1), 0.3, muted),
        ("INNERGRID",    (0, 0), (-1, -1), 0.3, muted),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(pill_tbl)
    story.append(Spacer(1, 8*mm))

    # Cover footer block
    story.append(HRFlowable(width=CONTENT_W, thickness=0.4, color=muted, spaceAfter=4*mm))
    story.append(Paragraph(_xml_safe(_localise(T["generated_on"].format(date=date_str))), cover_footer))
    story.append(Paragraph(_xml_safe(_localise(T["confidential"])), cover_footer))
    if tags:
        # Tags are mostly Latin token strings; no shaping needed.
        tags_line = " · ".join(_xml_safe(t) for t in tags[:8])
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(f"<font color='#A13F0F'>{tags_line}</font>", cover_footer))
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 2 — DECISION QUESTION + CONTEXT
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Paragraph(_xml_safe(_localise(T["doc_kind"])), sec_eyebrow))
    story.append(Paragraph(_xml_safe(_localise(T["decision_question"])), sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=orange, spaceAfter=4*mm))
    story.append(Paragraph(_xml_safe(_localise(decision_q)) or "—", decision_box))
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph(_xml_safe(_localise(T["context"])), sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=orange, spaceAfter=4*mm))
    if summary_short:
        story.append(Paragraph(f"<b>{_xml_safe(_localise(summary_short))}</b>", body_lg))
    if context_long:
        story.append(Paragraph(_xml_safe(_localise(context_long)), body_md))
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 3 — AGENTS + METHODOLOGY
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Paragraph(_xml_safe(_localise(T["doc_kind"])), sec_eyebrow))
    story.append(Paragraph(_xml_safe(_localise(T["agents_section"])), sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=orange, spaceAfter=4*mm))
    if agents:
        for agent in agents:
            if not isinstance(agent, dict):
                continue
            role  = agent.get("role_key", "—").replace("_", " ").strip().capitalize()
            prof  = _pick(agent.get("profile"), lang)
            role_safe = _xml_safe(_localise(role))
            prof_safe = _xml_safe(_localise(prof))
            line = f"<b>{role_safe}</b> — {prof_safe}" if prof else f"<b>{role_safe}</b>"
            story.append(Paragraph(f"• {line}", bullet_md))
    else:
        story.append(Paragraph("—", body_md))

    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(_xml_safe(_localise(T["methodology"])), sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=green, spaceAfter=4*mm))
    method_text = T["methodology_body"].format(brier=brier_str)
    story.append(Paragraph(_xml_safe(_localise(method_text)), methodology_box))
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 4 — INSIGHTS + USE CASES
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Paragraph(_xml_safe(_localise(T["doc_kind"])), sec_eyebrow))
    story.append(Paragraph(_xml_safe(_localise(T["insights"])), sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=orange, spaceAfter=4*mm))
    if insights:
        for ins in insights:
            text = ins if isinstance(ins, str) else str(ins)
            story.append(Paragraph(
                f"<font color='#006D44'><b>✓</b></font>  {_xml_safe(_localise(text))}",
                bullet_md,
            ))
    else:
        story.append(Paragraph("—", body_md))

    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(_xml_safe(_localise(T["use_cases"])), sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=orange, spaceAfter=4*mm))
    if use_cases:
        # 2x2 grid of cards (or 1xN if fewer)
        rows: List[List[Any]] = []
        case_style = S("UC", fontSize=9, fontName=font_regular, textColor=ink, leading=13,
                       alignment=align_default)
        cell_pad = []
        for i, uc in enumerate(use_cases[:4]):
            text = uc if isinstance(uc, str) else str(uc)
            cell_pad.append(Paragraph(
                f"<b>{i+1}.</b>  {_xml_safe(_localise(text))}",
                case_style,
            ))
        # group into rows of 2
        for i in range(0, len(cell_pad), 2):
            row = cell_pad[i:i+2]
            if len(row) == 1:
                row.append(Paragraph("", case_style))
            rows.append(row)

        if rows:
            uc_tbl = Table(rows, colWidths=[CONTENT_W * 0.5 - 2*mm, CONTENT_W * 0.5 - 2*mm])
            uc_tbl.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, -1), cream_hex),
                ("BOX",          (0, 0), (-1, -1), 0.3, muted),
                ("INNERGRID",    (0, 0), (-1, -1), 0.3, muted),
                ("LEFTPADDING",  (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING",   (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
                ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(uc_tbl)
    else:
        story.append(Paragraph("—", body_md))
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 5 — DISCLAIMER + CTA
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Paragraph(_xml_safe(_localise(T["doc_kind"])), sec_eyebrow))
    story.append(Paragraph(_xml_safe(_localise(T["disclaimer_title"])), sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=muted, spaceAfter=4*mm))
    story.append(Paragraph(_xml_safe(_localise(T["disclaimer_body"])), body_md))
    story.append(Spacer(1, 8*mm))

    cta_block = []
    cta_block.append(Paragraph(_xml_safe(_localise(T["cta_title"])), sec_heading))
    cta_block.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=terra, spaceAfter=4*mm))
    cta_text = (
        f"{_xml_safe(_localise(cta_label))}<br/><br/>"
        f"<font size=11>{T['cta_email']}</font><br/>"
        f"<font color='#A13F0F' size=10>{T['cta_link'].format(slug=slug)}</font>"
    )
    cta_block.append(Paragraph(cta_text, cta_box))
    story.append(KeepTogether(cta_block))

    doc.build(story)
    return buffer.getvalue()


def _xml_safe(text: Any) -> str:
    """Escape characters that Reportlab Paragraph parser interprets as XML."""
    if text is None:
        return ""
    s = str(text)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s


# ── Flask endpoint ───────────────────────────────────────────────────────────

@models_bp.route("/<slug>/pdf-brief", methods=["GET"])
def get_model_pdf_brief(slug: str):
    """GET /api/models/<slug>/pdf-brief?lang=<fr|en|ar> — branded brief PDF."""
    lang = (request.args.get("lang") or "fr").lower().strip()
    if lang not in _SUPPORTED_LANGS:
        return jsonify({
            "success": False,
            "error_code": "INVALID_LANG",
            "error": f"Unsupported language '{lang}'. Supported: {', '.join(_SUPPORTED_LANGS)}.",
        }), 400

    if not _SLUG_RE.match(slug):
        return jsonify({
            "success": False,
            "error_code": "INVALID_SLUG",
            "error": "Slug must match [a-z0-9][a-z0-9-]{0,80}.",
        }), 400

    model = _load_model(slug)
    if model is None:
        return jsonify({
            "success": False,
            "error_code": "MODEL_NOT_FOUND",
            "error": f"No pre-calibrated model found for slug '{slug}'.",
        }), 404

    try:
        pdf_bytes = _build_pdf(model, lang)
    except Exception as exc:  # pragma: no cover — defensive guard
        logger.error("PDF generation failed for %s [%s]: %s", slug, lang, exc)
        return jsonify({
            "success": False,
            "error_code": "PDF_BUILD_FAILED",
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }), 500

    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="bassira-modele-{slug}-{lang}.pdf"'
    )
    response.headers["Content-Length"] = str(len(pdf_bytes))
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response
