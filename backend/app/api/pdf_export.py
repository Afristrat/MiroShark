"""
PDF Export API — US-024 / US-059
Generates a branded Bassira PDF report for a finished simulation.

POST /api/simulation/<simulation_id>/export-pdf
  body (optional JSON): { "graph_image_b64": "<base64 PNG>" }
  → 200 application/pdf   (binary PDF stream)
  → 404 if simulation not found
  → 500 on generation error

GET /api/simulation/<simulation_id>/export-md
  → 200 text/markdown

Sections (PDF + MD):
  1. Page de garde + disclaimer
  2. Résumé exécutif
  3. ⚠ Disclaimer légal (section dédiée)
  4. Résultats & verdict
  5. Agents & profils
  6. Posts clés
  7. Top influenceurs
  8. Sources utilisées
  9. Image du graphe (PDF seulement si fournie)
  10. Méthodologie
  11. Recommandations
"""

from __future__ import annotations

import base64
import io
import json
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flask import jsonify, make_response, request

from . import simulation_bp
from ..services.simulation_manager import SimulationManager
from ..utils.logger import get_logger
from ..utils.validation import validate_simulation_id

logger = get_logger("miroshark.api.pdf_export")

# ── Palette Bassira ────────────────────────────────────────────────────────
_COLOR_ORANGE    = (1.0, 0.522, 0.318)    # #FF8551
_COLOR_TERRACOTA = (0.631, 0.247, 0.059)  # #A13F0F
_COLOR_GREEN     = (0.0,   0.427, 0.267)  # #006D44
_COLOR_CREAM     = (0.98,  0.969, 0.949)  # #FAF7F2
_COLOR_INK       = (0.141, 0.098, 0.082)  # #241915
_COLOR_MUTED     = (0.541, 0.388, 0.227)  # #8A7269

_DISCLAIMER_TEXT = (
    "AVERTISSEMENT — SIMULATION PROBABILISTE : Ce rapport est le résultat "
    "d'une simulation multi-agents à base d'intelligence artificielle. "
    "Les scénarios, tendances et résultats présentés constituent des projections "
    "probabilistes basées sur les données fournies et les paramètres de simulation. "
    "Ils ne représentent en aucun cas des certitudes, des prédictions garanties, "
    "ni des conseils financiers, juridiques ou stratégiques. "
    "Bassira (AI-Mpower) décline toute responsabilité quant aux décisions prises "
    "sur la base de ce document. Ce rapport est strictement confidentiel et "
    "destiné à l'usage interne de l'organisation commanditaire uniquement."
)

_DISCLAIMER_SHORT = "Simulation probabiliste — ne constitue pas une certitude. Bassira © 2026."


# ── Data helpers ──────────────────────────────────────────────────────────

def _load_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
    except Exception:
        pass
    return None


def _truncate(text: str, max_chars: int = 600) -> str:
    if not text:
        return ""
    text = str(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "…"


def _read_top_posts(sim_dir: str, top_n: int = 5) -> List[Dict]:
    """Read top posts from reddit/actions.jsonl sorted by engagement."""
    posts: List[Dict] = []
    for platform in ("reddit", "twitter"):
        log_path = os.path.join(sim_dir, platform, "actions.jsonl")
        if not os.path.isfile(log_path):
            continue
        try:
            with open(log_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if obj.get("action") in ("post", "comment", "tweet"):
                            posts.append({
                                "platform": platform,
                                "author": obj.get("author") or obj.get("agent_name") or "—",
                                "content": _truncate(
                                    obj.get("content") or obj.get("text") or obj.get("body") or "", 300
                                ),
                                "round": obj.get("round", 0),
                                "score": obj.get("score") or obj.get("upvotes") or 0,
                            })
                    except Exception:
                        pass
        except Exception:
            pass
    posts.sort(key=lambda p: p.get("score", 0), reverse=True)
    return posts[:top_n]


def _read_profiles(sim_dir: str, top_n: int = 10) -> List[Dict]:
    """Read agent profiles from reddit_profiles.json or polymarket_profiles.json."""
    for fname in ("reddit_profiles.json", "polymarket_profiles.json"):
        data = _load_json(os.path.join(sim_dir, fname))
        if data:
            profiles = data if isinstance(data, list) else data.get("profiles", [])
            result = []
            for p in profiles[:top_n]:
                if not isinstance(p, dict):
                    continue
                result.append({
                    "name": p.get("name") or p.get("username") or p.get("agent_name") or "—",
                    "type": p.get("type") or p.get("role") or p.get("archetype") or "—",
                    "stance": p.get("stance") or p.get("belief") or "—",
                    "platform": p.get("platform") or fname.split("_")[0],
                })
            if result:
                return result
    return []


def _read_influence(sim_dir: str, top_n: int = 5) -> List[Dict]:
    """Extract top influencers from trajectory.json."""
    traj = _load_json(os.path.join(sim_dir, "trajectory.json"))
    if not traj:
        return []
    try:
        rounds = traj if isinstance(traj, list) else traj.get("rounds", [])
        influence: Dict[str, float] = {}
        for r in rounds:
            for agent in (r.get("agents") or []):
                name = agent.get("name") or agent.get("agent_name") or ""
                if not name:
                    continue
                score = float(agent.get("influence_score") or agent.get("influence") or 0)
                influence[name] = max(influence.get(name, 0), score)
        ranked = sorted(influence.items(), key=lambda x: x[1], reverse=True)
        return [{"name": n, "score": round(s, 3)} for n, s in ranked[:top_n]]
    except Exception:
        return []


def _read_sources(sim_dir: str) -> List[str]:
    """Extract source URLs/files from simulation_config.json."""
    config = _load_json(os.path.join(sim_dir, "simulation_config.json")) or {}
    sources: List[str] = []
    for key in ("url_docs", "urls", "documents", "files", "seed_documents"):
        val = config.get(key)
        if not val:
            continue
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    sources.append(item)
                elif isinstance(item, dict):
                    url = item.get("url") or item.get("title") or item.get("filename") or ""
                    if url:
                        sources.append(url)
    return list(dict.fromkeys(sources))[:10]  # deduplicate, cap at 10


def _detect_framework(config: Dict) -> str:
    for key in ("framework", "scenario_framework", "preset_framework"):
        if config.get(key):
            return str(config[key])
    return "cerberus"


# ── PDF builder ──────────────────────────────────────────────────────────

def _build_pdf(simulation_id: str, graph_image_b64: str = "") -> bytes:  # noqa: C901
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import Color, HexColor
    from reportlab.platypus import (
        BaseDocTemplate, Frame, PageTemplate,
        Paragraph, Spacer, HRFlowable, KeepTogether,
        Image as RLImage, PageBreak,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

    # ── Load data ─────────────────────────────────────────────────────────
    manager = SimulationManager()
    sim_dir = manager._get_simulation_dir(simulation_id, create=False)

    config  = _load_json(os.path.join(sim_dir, "simulation_config.json")) or {}
    outcome = _load_json(os.path.join(sim_dir, "outcome.json")) or {}
    state   = manager.get_simulation(simulation_id)

    sim_requirement = ""
    try:
        from ..models.project import ProjectManager
        if state and state.project_id:
            project = ProjectManager.get_project(state.project_id)
            if project:
                sim_requirement = project.simulation_requirement or ""
    except Exception:
        pass

    sim_title   = config.get("title") or config.get("simulation_title") or simulation_id
    package     = config.get("package") or config.get("preset") or "—"
    framework   = _detect_framework(config)
    nb_rounds   = outcome.get("rounds") or outcome.get("nb_rounds") or (state.current_round if state else 0)
    nb_agents   = outcome.get("nb_agents") or config.get("nb_agents") or (state.profiles_count if state else 0)
    verdict     = outcome.get("verdict") or outcome.get("final_verdict") or "—"
    bullish_pct = outcome.get("bullish_pct") or outcome.get("bullish") or ""
    bearish_pct = outcome.get("bearish_pct") or outcome.get("bearish") or ""
    recommendations: list = outcome.get("recommendations") or []
    now = datetime.now(tz=timezone.utc).strftime("%d %B %Y, %H:%M UTC")

    profiles   = _read_profiles(sim_dir)
    top_posts  = _read_top_posts(sim_dir)
    influencers = _read_influence(sim_dir)
    sources    = _read_sources(sim_dir)

    # ── Colors ────────────────────────────────────────────────────────────
    orange     = Color(*_COLOR_ORANGE)
    terra      = Color(*_COLOR_TERRACOTA)
    green      = Color(*_COLOR_GREEN)
    cream      = Color(*_COLOR_CREAM)
    ink        = Color(*_COLOR_INK)
    muted      = Color(*_COLOR_MUTED)

    # ── Page geometry ─────────────────────────────────────────────────────
    PAGE_W, PAGE_H = A4
    MARGIN_L = 22 * mm
    MARGIN_R = 22 * mm
    MARGIN_T = 20 * mm
    MARGIN_B = 20 * mm
    CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

    # ── Styles ────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    def S(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    cover_brand   = S("CB",  fontSize=22, fontName="Helvetica-Bold",   textColor=orange,  spaceAfter=2*mm)
    cover_title   = S("CT",  fontSize=18, fontName="Helvetica-Bold",   textColor=ink,     leading=24, spaceAfter=6*mm)
    cover_meta    = S("CM",  fontSize=9,  fontName="Helvetica",         textColor=muted,   spaceAfter=2*mm)
    cover_discl   = S("CD",  fontSize=8,  fontName="Helvetica-Oblique", textColor=terra,   spaceAfter=4*mm)
    sec_heading   = S("SH",  fontSize=13, fontName="Helvetica-Bold",    textColor=orange,  spaceBefore=8*mm, spaceAfter=3*mm)
    sec_sub       = S("SS",  fontSize=11, fontName="Helvetica-Bold",    textColor=ink,     spaceBefore=4*mm, spaceAfter=2*mm)
    body          = S("BD",  fontSize=10, fontName="Helvetica",         textColor=ink,     leading=15, spaceAfter=4*mm)
    body_small    = S("BS",  fontSize=9,  fontName="Helvetica",         textColor=ink,     leading=13, spaceAfter=2*mm)
    label_s       = S("LB",  fontSize=8,  fontName="Helvetica-Bold",    textColor=muted,   spaceAfter=1*mm)
    value_s       = S("VL",  fontSize=10, fontName="Helvetica",         textColor=ink,     spaceAfter=3*mm)
    bullet_s      = S("BU",  fontSize=10, fontName="Helvetica",         textColor=ink,     leading=15, leftIndent=12, spaceAfter=3*mm)
    discl_full    = S("DF",  fontSize=9,  fontName="Helvetica",         textColor=terra,   leading=14, spaceAfter=4*mm,
                      borderPadding=(6, 8, 6, 8), borderColor=terra, borderWidth=0.5, backColor=HexColor("#FFF3EE"))
    mono_s        = S("MN",  fontSize=9,  fontName="Courier",           textColor=muted,   spaceAfter=2*mm)

    # ── Page callbacks ────────────────────────────────────────────────────
    def _on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(orange)
        canvas.rect(0, PAGE_H - 4*mm, PAGE_W, 4*mm, fill=1, stroke=0)
        canvas.setFillColor(terra)
        canvas.rect(0, 0, PAGE_W, 2*mm, fill=1, stroke=0)
        canvas.setFont("Helvetica-Oblique", 7)
        canvas.setFillColor(muted)
        canvas.drawCentredString(PAGE_W / 2, 4*mm, _DISCLAIMER_SHORT)
        if doc.page > 1:
            canvas.setFont("Helvetica", 7)
            canvas.drawRightString(PAGE_W - MARGIN_R, 4*mm, f"Page {doc.page}")
        canvas.restoreState()

    # ── Document ──────────────────────────────────────────────────────────
    buffer = io.BytesIO()
    doc = BaseDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T + 4*mm, bottomMargin=MARGIN_B + 10*mm,
    )
    frame = Frame(
        MARGIN_L, MARGIN_B + 10*mm, CONTENT_W,
        PAGE_H - MARGIN_T - 4*mm - MARGIN_B - 10*mm,
        id="main",
    )
    doc.addPageTemplates([PageTemplate(id="normal", frames=[frame], onPage=_on_page)])

    story = []

    # ─────────────────────────────────────────────────────────────────────
    # 1. PAGE DE GARDE
    # ─────────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("BASSIRA", cover_brand))
    story.append(Paragraph("Rapport de simulation multi-agents", S("sub", fontSize=10, fontName="Helvetica", textColor=muted, spaceAfter=8*mm)))
    story.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=orange, spaceAfter=8*mm))
    story.append(Paragraph(_truncate(sim_title, 200), cover_title))
    story.append(Paragraph(f"<b>Simulation ID :</b> {simulation_id}", cover_meta))
    story.append(Paragraph(f"<b>Package :</b> {package}", cover_meta))
    story.append(Paragraph(f"<b>Cadre analytique :</b> {framework.title()}", cover_meta))
    story.append(Paragraph(f"<b>Date de génération :</b> {now}", cover_meta))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("⚠ CONFIDENTIEL — Simulation probabiliste · Usage interne uniquement", cover_discl))
    story.append(Spacer(1, 30*mm))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=muted, spaceAfter=0))
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    # 2. DISCLAIMER LÉGAL
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("⚠ Avertissement légal — nature probabiliste de ce rapport", sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=terra, spaceAfter=4*mm))
    story.append(Paragraph(_DISCLAIMER_TEXT, discl_full))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        "Les simulations Bassira s'appuient sur des agents IA autonomes dont les "
        "comportements émergent de l'interaction entre leurs profils, le contexte "
        "fourni et les paramètres de simulation. Aucun résultat ne peut être "
        "considéré comme une prédiction déterministe de la réalité.",
        body,
    ))

    # ─────────────────────────────────────────────────────────────────────
    # 3. RÉSUMÉ EXÉCUTIF
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Résumé exécutif", sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=orange, spaceAfter=3*mm))

    story.append(Paragraph("Objectif de simulation", label_s))
    story.append(Paragraph(_truncate(sim_requirement, 800) or "Non spécifié.", body))

    story.append(Paragraph("Paramètres clés", label_s))
    meta_line = (
        f"Package : <b>{package}</b>  ·  "
        f"Cadre : <b>{framework.title()}</b>  ·  "
        f"Rounds : <b>{nb_rounds or '—'}</b>  ·  "
        f"Agents : <b>{nb_agents or '—'}</b>"
    )
    story.append(Paragraph(meta_line, body_small))

    # ─────────────────────────────────────────────────────────────────────
    # 4. RÉSULTATS & VERDICT
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Résultats & Verdict", sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=orange, spaceAfter=3*mm))

    results_block = []
    results_block.append(Paragraph("Verdict final", label_s))
    results_block.append(Paragraph(str(verdict), S("VV", fontSize=14, fontName="Helvetica-Bold", textColor=terra, spaceAfter=4*mm)))
    if bullish_pct:
        results_block.append(Paragraph("Croyance haussière", label_s))
        results_block.append(Paragraph(str(bullish_pct), value_s))
    if bearish_pct:
        results_block.append(Paragraph("Croyance baissière", label_s))
        results_block.append(Paragraph(str(bearish_pct), value_s))
    results_block.append(Paragraph("Rounds simulés", label_s))
    results_block.append(Paragraph(str(nb_rounds) if nb_rounds else "—", value_s))
    story.append(KeepTogether(results_block))

    # ─────────────────────────────────────────────────────────────────────
    # 5. AGENTS & PROFILS
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Agents & Profils", sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=orange, spaceAfter=3*mm))
    if profiles:
        story.append(Paragraph(f"{len(profiles)} profils d'agents extraits :", body_small))
        for p in profiles:
            line = (
                f"<b>{p['name']}</b> · {p['type']} · "
                f"Position : {p['stance']}"
            )
            story.append(Paragraph(f"• {line}", bullet_s))
    else:
        story.append(Paragraph("Aucun profil d'agent disponible pour cette simulation.", body))

    # ─────────────────────────────────────────────────────────────────────
    # 6. POSTS CLÉS
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Messages & Posts clés", sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=orange, spaceAfter=3*mm))
    if top_posts:
        story.append(Paragraph("Messages les plus influents générés pendant la simulation :", body_small))
        for i, post in enumerate(top_posts, 1):
            story.append(Paragraph(f"Post #{i} — <b>{post['author']}</b> ({post['platform']}, round {post['round']})", label_s))
            story.append(Paragraph(_truncate(post['content'], 400), S(f"PC{i}", fontSize=10, fontName="Helvetica-Oblique",
                                   textColor=ink, leading=14, leftIndent=8, spaceAfter=4*mm,
                                   borderPadding=(4, 6, 4, 6), borderColor=muted, borderWidth=0.3)))
    else:
        story.append(Paragraph("Aucun post disponible (simulation non complète ou log absent).", body))

    # ─────────────────────────────────────────────────────────────────────
    # 7. TOP INFLUENCEURS
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Top Influenceurs", sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=orange, spaceAfter=3*mm))
    if influencers:
        story.append(Paragraph("Agents ayant exercé la plus forte influence sur la dynamique collective :", body_small))
        for rank, inf in enumerate(influencers, 1):
            story.append(Paragraph(
                f"{rank}. <b>{inf['name']}</b> — score d'influence : {inf['score']}",
                bullet_s,
            ))
    else:
        story.append(Paragraph("Données d'influence non disponibles (trajectory.json absent).", body))

    # ─────────────────────────────────────────────────────────────────────
    # 8. SOURCES UTILISÉES
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Sources & Graines de réalité", sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=orange, spaceAfter=3*mm))
    if sources:
        story.append(Paragraph("Documents et URLs ayant alimenté le graphe de connaissance :", body_small))
        for src in sources:
            story.append(Paragraph(f"• {_truncate(src, 120)}", mono_s))
    else:
        story.append(Paragraph("Sources non enregistrées dans la configuration de cette simulation.", body))

    # ─────────────────────────────────────────────────────────────────────
    # 9. IMAGE DU GRAPHE
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Graphe de connaissance", sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=orange, spaceAfter=3*mm))
    if graph_image_b64:
        try:
            img_bytes = base64.b64decode(graph_image_b64)
            img_buffer = io.BytesIO(img_bytes)
            img = RLImage(img_buffer, width=CONTENT_W, height=CONTENT_W * 0.6)
            story.append(img)
            story.append(Paragraph("Capture du graphe d'entités au moment de l'export.", S("IC", fontSize=8,
                fontName="Helvetica-Oblique", textColor=muted, alignment=TA_CENTER, spaceAfter=4*mm)))
        except Exception as e:
            logger.warning("Graph image decode failed: %s", e)
            story.append(Paragraph("Graphe non disponible (erreur de décodage de l'image fournie).", body))
    else:
        story.append(Paragraph(
            "Pour inclure une capture du graphe dans ce rapport, envoyez l'image "
            "en base64 dans le corps de la requête POST (champ graph_image_b64).",
            body,
        ))

    # ─────────────────────────────────────────────────────────────────────
    # 10. MÉTHODOLOGIE
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Méthodologie", sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=orange, spaceAfter=3*mm))

    story.append(Paragraph("Cadre analytique", label_s))
    framework_desc = {
        "cerberus": "Cadre Cerberus — 3 agents archétypaux (Challenger, Defender, Arbiter) modélisant la tension dialectique autour d'une question.",
        "market":   "Cadre Market — agents Bull, Bear, Neutral simulant la formation des croyances sur un marché.",
        "crisis":   "Cadre Crisis — agents Amplifier, Attenuator, Moderator simulant la propagation et l'atténuation d'une crise réputationnelle.",
        "policy":   "Cadre Policy — agents Progressive, Conservative, Technocrat simulant le débat politique et réglementaire.",
        "decision": "Cadre Decision — agents Optimist, Skeptic, Pragmatist simulant les dynamiques de prise de décision organisationnelle.",
    }.get(framework.lower(), f"Cadre {framework} — simulation multi-agents.")
    story.append(Paragraph(framework_desc, body))

    story.append(Paragraph("Score de calibration Brier", label_s))
    story.append(Paragraph(
        "Le score de Brier mesure la précision des prévisions probabilistes : "
        "0 = parfait, 1 = aléatoire, 0.25 = référence naïve. "
        "Bassira affiche un score moyen de 0,18 sur l'ensemble des simulations vérifiées "
        "(voir bassira.ai/calibration pour le détail).",
        body,
    ))

    story.append(Paragraph("Limites", label_s))
    story.append(Paragraph(
        "Cette simulation repose sur les données fournies par l'utilisateur (graines de réalité). "
        "La qualité des résultats est directement proportionnelle à la qualité et l'exhaustivité "
        "des sources utilisées. Les agents IA sont des proxies de comportements collectifs — "
        "ils ne modélisent pas des individus réels identifiables.",
        body,
    ))

    # ─────────────────────────────────────────────────────────────────────
    # 11. RECOMMANDATIONS
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Recommandations", sec_heading))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=orange, spaceAfter=3*mm))
    if recommendations:
        reco_block = []
        for rec in recommendations[:10]:
            text = (rec if isinstance(rec, str) else
                    rec.get("text") or rec.get("recommendation") or str(rec))
            reco_block.append(Paragraph(f"• {_truncate(text, 400)}", bullet_s))
        story.append(KeepTogether(reco_block))
    else:
        story.append(Paragraph(
            "Aucune recommandation structurée disponible. "
            "Lancez une simulation complète avec le cadre cerberus ou policy "
            "pour obtenir des recommandations actionables.",
            body,
        ))

    doc.build(story)
    return buffer.getvalue()


# ── Markdown builder ──────────────────────────────────────────────────────

def _build_markdown(simulation_id: str) -> str:
    manager = SimulationManager()
    sim_dir = manager._get_simulation_dir(simulation_id, create=False)

    config  = _load_json(os.path.join(sim_dir, "simulation_config.json")) or {}
    outcome = _load_json(os.path.join(sim_dir, "outcome.json")) or {}
    state   = manager.get_simulation(simulation_id)

    sim_requirement = ""
    try:
        from ..models.project import ProjectManager
        if state and state.project_id:
            project = ProjectManager.get_project(state.project_id)
            if project:
                sim_requirement = project.simulation_requirement or ""
    except Exception:
        pass

    sim_title   = config.get("title") or config.get("simulation_title") or simulation_id
    package     = config.get("package") or config.get("preset") or "—"
    framework   = _detect_framework(config)
    nb_rounds   = outcome.get("rounds") or outcome.get("nb_rounds") or (state.current_round if state else 0)
    nb_agents   = outcome.get("nb_agents") or config.get("nb_agents") or (state.profiles_count if state else 0)
    verdict     = outcome.get("verdict") or outcome.get("final_verdict") or "—"
    bullish_pct = outcome.get("bullish_pct") or outcome.get("bullish") or ""
    bearish_pct = outcome.get("bearish_pct") or outcome.get("bearish") or ""
    recommendations: list = outcome.get("recommendations") or []
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    profiles    = _read_profiles(sim_dir)
    top_posts   = _read_top_posts(sim_dir)
    influencers = _read_influence(sim_dir)
    sources     = _read_sources(sim_dir)

    lines = []
    def h(level, text): lines.append(f"{'#' * level} {text}\n")
    def p(text):         lines.append(f"{text}\n")
    def hr():            lines.append("---\n")
    def bl(text):        lines.append(f"- {text}")
    def kv(key, val):    lines.append(f"**{key}** : {val}")
    def nl():            lines.append("")

    h(1, f"Rapport de simulation — {sim_title}")
    p(f"> Généré par Bassira · {now}")
    nl()
    hr()
    nl()

    # Disclaimer
    h(2, "⚠️ Avertissement légal")
    p(f"> {_DISCLAIMER_TEXT}")
    nl()
    hr()
    nl()

    # Résumé exécutif
    h(2, "Résumé exécutif")
    kv("Simulation ID", f"`{simulation_id}`")
    nl()
    kv("Package", package)
    nl()
    kv("Cadre analytique", framework.title())
    nl()
    kv("Rounds simulés", str(nb_rounds) if nb_rounds else "—")
    nl()
    kv("Agents", str(nb_agents) if nb_agents else "—")
    nl()
    nl()
    if sim_requirement:
        h(3, "Objectif")
        p(sim_requirement)
        nl()

    # Résultats
    hr()
    h(2, "Résultats & Verdict")
    kv("Verdict", f"**{verdict}**")
    nl()
    if bullish_pct:
        kv("Croyance haussière", str(bullish_pct))
        nl()
    if bearish_pct:
        kv("Croyance baissière", str(bearish_pct))
        nl()
    nl()

    # Agents
    hr()
    h(2, "Agents & Profils")
    if profiles:
        for p_ in profiles:
            bl(f"**{p_['name']}** · {p_['type']} · Position : {p_['stance']}")
            nl()
    else:
        p("_Aucun profil disponible._")
    nl()

    # Posts clés
    hr()
    h(2, "Messages & Posts clés")
    if top_posts:
        for i, post in enumerate(top_posts, 1):
            h(3, f"Post #{i} — {post['author']} ({post['platform']}, round {post['round']})")
            p(f"> {post['content']}")
            nl()
    else:
        p("_Aucun post disponible._")
    nl()

    # Influenceurs
    hr()
    h(2, "Top Influenceurs")
    if influencers:
        for rank, inf in enumerate(influencers, 1):
            bl(f"**#{rank} {inf['name']}** — score : `{inf['score']}`")
            nl()
    else:
        p("_Données d'influence non disponibles._")
    nl()

    # Sources
    hr()
    h(2, "Sources & Graines de réalité")
    if sources:
        for src in sources:
            bl(src)
            nl()
    else:
        p("_Sources non enregistrées._")
    nl()

    # Méthodologie
    hr()
    h(2, "Méthodologie")
    h(3, "Score de calibration Brier")
    p("Score moyen Bassira : **0,18** (0 = parfait, 0,25 = naïf, 1 = aléatoire).")
    p("Voir [bassira.ai/calibration](https://bassira.ai/calibration) pour le détail complet.")
    nl()
    h(3, "Cadre analytique")
    p(f"Cadre : **{framework.title()}**")
    nl()
    h(3, "Limites")
    p(
        "Les résultats sont proportionnels à la qualité des sources fournies. "
        "Les agents sont des proxies de dynamiques collectives — pas de modélisation d'individus réels."
    )
    nl()

    # Recommandations
    hr()
    h(2, "Recommandations")
    if recommendations:
        for rec in recommendations[:10]:
            text = (rec if isinstance(rec, str) else
                    rec.get("text") or rec.get("recommendation") or str(rec))
            bl(_truncate(text, 500))
            nl()
    else:
        p("_Aucune recommandation structurée disponible._")
    nl()

    hr()
    p(f"*Bassira (AI-Mpower) · {now} · `{simulation_id}`*")

    return "\n".join(lines)


# ── Flask endpoints ──────────────────────────────────────────────────────

@simulation_bp.route("/<simulation_id>/export-pdf", methods=["POST"])
def export_simulation_pdf(simulation_id: str):
    """POST /api/simulation/<id>/export-pdf — PDF enrichi 10 sections."""
    try:
        try:
            validate_simulation_id(simulation_id)
        except ValueError as exc:
            return jsonify({"success": False, "error_code": "INVALID_SIMULATION_ID", "error": str(exc)}), 400

        manager = SimulationManager()
        if not manager.get_simulation(simulation_id):
            return jsonify({"success": False, "error_code": "SIMULATION_NOT_FOUND",
                            "error": f"Simulation introuvable : {simulation_id}"}), 404

        body = request.get_json(silent=True) or {}
        graph_b64 = body.get("graph_image_b64") or ""

        pdf_bytes = _build_pdf(simulation_id, graph_image_b64=graph_b64)
        response = make_response(pdf_bytes)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f'attachment; filename="bassira-{simulation_id}.pdf"'
        response.headers["Content-Length"] = str(len(pdf_bytes))
        return response

    except Exception as exc:
        logger.error("PDF export failed for %s: %s", simulation_id, exc)
        return jsonify({"success": False, "error_code": "PDF_EXPORT_FAILED",
                        "error": str(exc), "traceback": traceback.format_exc()}), 500


@simulation_bp.route("/<simulation_id>/export-md", methods=["GET"])
def export_simulation_markdown(simulation_id: str):
    """GET /api/simulation/<id>/export-md — rapport Markdown."""
    try:
        try:
            validate_simulation_id(simulation_id)
        except ValueError as exc:
            return jsonify({"success": False, "error_code": "INVALID_SIMULATION_ID", "error": str(exc)}), 400

        manager = SimulationManager()
        if not manager.get_simulation(simulation_id):
            return jsonify({"success": False, "error_code": "SIMULATION_NOT_FOUND",
                            "error": f"Simulation introuvable : {simulation_id}"}), 404

        md_content = _build_markdown(simulation_id)
        response = make_response(md_content)
        response.headers["Content-Type"] = "text/markdown; charset=utf-8"
        response.headers["Content-Disposition"] = f'attachment; filename="bassira-{simulation_id}.md"'
        return response

    except Exception as exc:
        logger.error("MD export failed for %s: %s", simulation_id, exc)
        return jsonify({"success": False, "error_code": "MD_EXPORT_FAILED",
                        "error": str(exc)}), 500
