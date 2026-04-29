"""
Convert each `01_attachment.md` of the canonical preset templates to PDF.

Sortie : `01_attachment.pdf` à côté du MD source dans chaque dossier
`backend/app/preset_templates/<id>/`.

Usage : `python scripts/build_attachment_pdfs.py`
       `python scripts/build_attachment_pdfs.py pmf_startup_tech`  # un seul

Dépendance : `pip install reportlab`. Pure Python, pas de compile/native.
"""
from pathlib import Path
import re
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    PageBreak,
    HRFlowable,
)

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "backend" / "app" / "preset_templates"

CANONICAL_IDS = [
    "pmf_startup_tech",
    "crisis_24h_brand",
    "adcheck_pre_launch",
    "policy_brief_stress",
    "product_launch_v2",
]

# ── Styles Bassira (Playful & Soft palette adaptée print) ─────────────────────
BRAND_ORANGE = colors.HexColor("#FF8551")
BRAND_TEXT = colors.HexColor("#2A2A35")
BRAND_MUTED = colors.HexColor("#6B6B7D")
BRAND_BORDER = colors.HexColor("#EAE6DE")

base = getSampleStyleSheet()

H1 = ParagraphStyle(
    "BassiraH1",
    parent=base["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=20,
    leading=24,
    spaceBefore=4,
    spaceAfter=12,
    textColor=BRAND_TEXT,
)

H2 = ParagraphStyle(
    "BassiraH2",
    parent=base["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=14,
    leading=18,
    spaceBefore=14,
    spaceAfter=6,
    textColor=BRAND_TEXT,
)

BODY = ParagraphStyle(
    "BassiraBody",
    parent=base["BodyText"],
    fontName="Helvetica",
    fontSize=10.5,
    leading=15,
    spaceAfter=6,
    textColor=BRAND_TEXT,
    alignment=4,  # justified
)

BULLET = ParagraphStyle(
    "BassiraBullet",
    parent=BODY,
    leftIndent=14,
    bulletIndent=2,
    spaceAfter=3,
)

META = ParagraphStyle(
    "BassiraMeta",
    parent=base["BodyText"],
    fontName="Helvetica-Oblique",
    fontSize=9,
    leading=12,
    textColor=BRAND_MUTED,
    spaceAfter=2,
)


def md_inline_to_html(text: str) -> str:
    """Convert minimal MD inline syntax to ReportLab markup.

    - **bold** → <b>bold</b>
    - *italic* → <i>italic</i>
    - `code`   → <font face="Courier">code</font>
    """
    # Escape the raw `<` and `>` first to keep paragraph parser sane
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+?)`", r'<font face="Courier" size="9.5">\1</font>', text)
    return text


def parse_md_to_flowables(md_path: Path):
    flowables = []
    lines = md_path.read_text(encoding="utf-8").splitlines()
    in_blank = True
    paragraph_buf = []

    def flush_paragraph():
        nonlocal paragraph_buf
        if paragraph_buf:
            text = " ".join(line.strip() for line in paragraph_buf if line.strip())
            if text:
                flowables.append(Paragraph(md_inline_to_html(text), BODY))
        paragraph_buf = []

    for raw in lines:
        line = raw.rstrip()

        # Horizontal rule
        if re.match(r"^---+\s*$", line):
            flush_paragraph()
            flowables.append(Spacer(1, 4))
            flowables.append(
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=BRAND_BORDER,
                    spaceBefore=2,
                    spaceAfter=8,
                )
            )
            in_blank = True
            continue

        # Heading 1 (#)
        if line.startswith("# "):
            flush_paragraph()
            flowables.append(Paragraph(md_inline_to_html(line[2:].strip()), H1))
            in_blank = True
            continue
        # Heading 2 (##)
        if line.startswith("## "):
            flush_paragraph()
            flowables.append(Paragraph(md_inline_to_html(line[3:].strip()), H2))
            in_blank = True
            continue
        # Heading 3 (###) collapsed to H2 visually
        if line.startswith("### "):
            flush_paragraph()
            flowables.append(Paragraph(md_inline_to_html(line[4:].strip()), H2))
            in_blank = True
            continue

        # Bullet (- or *)
        m = re.match(r"^([-*])\s+(.*)$", line)
        if m:
            flush_paragraph()
            flowables.append(
                Paragraph("• " + md_inline_to_html(m.group(2).strip()), BULLET)
            )
            in_blank = False
            continue

        # Numbered list (1.)
        m = re.match(r"^\d+\.\s+(.*)$", line)
        if m:
            flush_paragraph()
            flowables.append(
                Paragraph(md_inline_to_html(line.strip()), BULLET)
            )
            in_blank = False
            continue

        # Italic-only one-line (« — sent via … »)
        if line.startswith("— *") or line.startswith("*— "):
            flush_paragraph()
            flowables.append(Paragraph(md_inline_to_html(line.strip()), META))
            in_blank = True
            continue

        # Blank line → flush paragraph
        if line.strip() == "":
            flush_paragraph()
            in_blank = True
            continue

        # Regular line → accumulate paragraph
        paragraph_buf.append(line)
        in_blank = False

    flush_paragraph()
    return flowables


def add_page_decoration(canv, doc):
    """Header (logo text) + footer (page number + brand)."""
    canv.saveState()

    # Header
    canv.setFont("Helvetica-Bold", 9)
    canv.setFillColor(BRAND_ORANGE)
    canv.drawString(2 * cm, A4[1] - 1.4 * cm, "BASSIRA")
    canv.setFont("Helvetica", 8.5)
    canv.setFillColor(BRAND_MUTED)
    canv.drawRightString(
        A4[0] - 2 * cm,
        A4[1] - 1.4 * cm,
        "Demande de simulation — confidentiel",
    )

    canv.setStrokeColor(BRAND_BORDER)
    canv.setLineWidth(0.4)
    canv.line(2 * cm, A4[1] - 1.6 * cm, A4[0] - 2 * cm, A4[1] - 1.6 * cm)

    # Footer
    page_str = "Page %d" % doc.page
    canv.setFont("Helvetica", 8)
    canv.setFillColor(BRAND_MUTED)
    canv.drawString(2 * cm, 1.2 * cm, page_str)
    canv.drawRightString(
        A4[0] - 2 * cm,
        1.2 * cm,
        "bassira.ai-mpower.com  ·  formulaire /devis",
    )
    canv.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)

    canv.restoreState()


def build_pdf(template_id: str) -> Path:
    md_path = TEMPLATES_DIR / template_id / "01_attachment.md"
    if not md_path.exists():
        raise FileNotFoundError(f"Missing : {md_path}")
    pdf_path = md_path.with_suffix(".pdf")

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"Bassira — {template_id} — Demande de simulation",
        author="Bassira (template canonique)",
    )

    flowables = parse_md_to_flowables(md_path)
    doc.build(flowables, onFirstPage=add_page_decoration, onLaterPages=add_page_decoration)

    return pdf_path


def main():
    targets = sys.argv[1:] or CANONICAL_IDS
    for tid in targets:
        try:
            out = build_pdf(tid)
            print(f"  OK  {tid}  ->  {out.relative_to(ROOT)}  ({out.stat().st_size // 1024} KB)")
        except FileNotFoundError as e:
            print(f"  SKIP {tid}  :  {e}")
        except Exception as e:
            print(f"  FAIL {tid}  :  {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
