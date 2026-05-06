"""
anonymizer.py — Anonymisation des données sensibles dans les rapports PDF Bassira.

US-131 — 4 variantes PDF (exec/full/public/one-pager).

Fournit deux fonctions publiques :
    anonymize_text(text, state=None)    → str anonymisé
    anonymize_context(context)          → PDFReportContext anonymisé

Règles d'anonymisation :
    - Noms d'organisations (Capitalisé Inc, SA, SAS, LLC, Ltd, Corp, SARL, GmbH)
      → remplacés par [Org A], [Org B], … (cohérent par appel)
    - Agents avec pattern Agent_X ou @username
      → remplacés par [Agent #1], [Agent #2], … (cohérent par appel)
    - Champs textuels des sub-models appliqués récursivement via anonymize_context
    - Watermark désactivée dans le contexte public (watermark_disabled=True)

Usage ::

    from app.services.report_pdf.anonymizer import anonymize_text, anonymize_context

    clean = anonymize_text("Bassira Inc. a analysé le rapport.")
    # → "[Org A] a analysé le rapport."

    public_context = anonymize_context(ctx)
    # Retourne un PDFReportContext avec tous les noms sensibles remplacés.
"""

from __future__ import annotations

import copy
import re
from typing import Optional

from .schema import PDFReportContext

# ─── Patterns de détection ───────────────────────────────────────────────────

# Noms d'organisations : mot(s) Capitalisé(s) suivi d'un suffixe légal
# Exemples : "Bassira Inc.", "ACME Corp", "Dupont SA", "Müller GmbH"
_ORG_SUFFIXES = (
    r"Inc\.?|S\.A\.S?\.?|S\.A\.R\.L\.?|LLC\.?|Ltd\.?|Corp\.?|GmbH\.?|"
    r"SARL\.?|SA\.?|SAS\.?|S\.A\.(?!S)|Conseil|Group|Groupe|Holding|Partners?"
)

_ORG_PATTERN = re.compile(
    r"\b([A-ZÉÀÈÇÔÎÙ][A-Za-zÀ-ÿ\-&']+(?:\s+[A-Za-zÀ-ÿ\-&']+)*)"
    r"\s+(?:" + _ORG_SUFFIXES + r")\b",
    re.UNICODE,
)

# Agents : Agent_X (avec ou sans underscore/chiffre) ou @username
# Note : \b ne fonctionne pas avant @ (non word-char), on utilise un alternant sans \b pour @
_AGENT_PATTERN = re.compile(
    r"(?:\b(Agent[_\-]?\w+)\b|(@[A-Za-z][A-Za-z0-9_]+))",
    re.UNICODE,
)


# ─── Classe interne d'état (dict de substitution cohérent) ───────────────────


class _AnonymizationState:
    """Maintient un mapping cohérent pour un appel donné.

    Garantit que le même nom original → même remplacement dans tout le document.
    """

    def __init__(self) -> None:
        self._org_map: dict[str, str] = {}
        self._agent_map: dict[str, str] = {}
        self._org_labels = _label_generator("Org")
        self._agent_labels = _label_generator_numbered("Agent")

    def org_replacement(self, original: str) -> str:
        if original not in self._org_map:
            self._org_map[original] = f"[{next(self._org_labels)}]"
        return self._org_map[original]

    def agent_replacement(self, original: str) -> str:
        if original not in self._agent_map:
            self._agent_map[original] = f"[{next(self._agent_labels)}]"
        return self._agent_map[original]


def _label_generator(prefix: str):
    """Génère [Org A], [Org B], …, [Org Z], [Org AA], …"""
    import string
    letters = string.ascii_uppercase
    idx = 0
    while True:
        # Calcul de la séquence alphabétique Excel-style
        n = idx
        label = ""
        while True:
            label = letters[n % 26] + label
            n = n // 26 - 1
            if n < 0:
                break
        yield f"{prefix} {label}"
        idx += 1


def _label_generator_numbered(prefix: str):
    """Génère [Agent #1], [Agent #2], …"""
    n = 1
    while True:
        yield f"{prefix} #{n}"
        n += 1


# ─── API publique ─────────────────────────────────────────────────────────────


def anonymize_text(text: str, state: Optional[_AnonymizationState] = None) -> str:
    """Anonymise un texte en masquant les noms d'organisations et d'agents.

    Args:
        text:   Texte à anonymiser.
        state:  État de substitution partagé (pour cohérence multi-champs).
                Si None, un état éphémère est créé (pas de cohérence inter-appels).

    Returns:
        Texte anonymisé avec les organisations et agents remplacés.
    """
    if not text:
        return text

    if state is None:
        state = _AnonymizationState()

    # 1. Remplacer les noms d'organisations
    def _replace_org(match: re.Match) -> str:
        # Le match complet inclut le suffixe légal
        full_match = match.group(0)
        return state.org_replacement(full_match)

    result = _ORG_PATTERN.sub(_replace_org, text)

    # 2. Remplacer les identifiants agents
    # Les groupes : group(1) = Agent_X pattern, group(2) = @username pattern
    def _replace_agent(match: re.Match) -> str:
        # Utiliser le groupe non-None comme clé
        key = match.group(1) or match.group(2)
        return state.agent_replacement(key)

    result = _AGENT_PATTERN.sub(_replace_agent, result)

    return result


def anonymize_context(context: PDFReportContext) -> PDFReportContext:
    """Applique l'anonymisation sur tous les champs textuels d'un PDFReportContext.

    Crée une copie profonde du contexte original et applique anonymize_text sur
    tous les champs string : title, outline, takeaways, interpretations, articles,
    interviews, outcome.verdict, outcome.recommendations, agent_profiles, etc.

    L'état de substitution est partagé sur tout le contexte pour garantir la
    cohérence (même org → même [Org X] partout dans le document).

    Args:
        context: PDFReportContext original (non modifié).

    Returns:
        Nouveau PDFReportContext avec données anonymisées.
        Watermark implicitement désactivée (via champ extra ignoré par Pydantic).
    """
    # Copie profonde pour ne pas muter l'original
    ctx_dict = context.model_dump()
    state = _AnonymizationState()

    # Appliquer sur les champs racine
    ctx_dict["title"] = anonymize_text(ctx_dict.get("title", "") or "", state)

    # Outline
    if ctx_dict.get("outline"):
        outline = ctx_dict["outline"]
        outline["title"] = anonymize_text(outline.get("title", "") or "", state)
        outline["summary"] = anonymize_text(outline.get("summary", "") or "", state)
        for section in outline.get("sections", []):
            section["title"] = anonymize_text(section.get("title", "") or "", state)
            section["content"] = anonymize_text(section.get("content", "") or "", state)

    # Executive takeaways
    ctx_dict["executive_takeaways"] = [
        anonymize_text(t, state) for t in ctx_dict.get("executive_takeaways", [])
    ]

    # Interpretations (dict str → str)
    interps = ctx_dict.get("interpretations", {})
    ctx_dict["interpretations"] = {
        k: anonymize_text(v, state) for k, v in (interps or {}).items()
    }

    # Outcome
    if ctx_dict.get("outcome"):
        out = ctx_dict["outcome"]
        out["verdict"] = anonymize_text(out.get("verdict", "") or "", state)
        out["recommendations"] = [
            anonymize_text(r, state) for r in out.get("recommendations", [])
        ]
        if out.get("scenario_winner"):
            out["scenario_winner"] = anonymize_text(out["scenario_winner"], state)

    # KPI hero
    if ctx_dict.get("kpi_hero"):
        kpi = ctx_dict["kpi_hero"]
        kpi["verdict"] = anonymize_text(kpi.get("verdict", "") or "", state)

    # Agent profiles
    for profile in ctx_dict.get("agent_profiles", []):
        profile["name"] = anonymize_text(profile.get("name", "") or "", state)
        profile["description"] = anonymize_text(profile.get("description", "") or "", state)

    # Articles
    for article in ctx_dict.get("articles", []):
        article["agent_name"] = anonymize_text(article.get("agent_name", "") or "", state)
        article["title"] = anonymize_text(article.get("title", "") or "", state)
        article["content"] = anonymize_text(article.get("content", "") or "", state)

    # Interviews
    for interview in ctx_dict.get("interviews", []):
        interview["agent_name"] = anonymize_text(interview.get("agent_name", "") or "", state)
        interview["questions"] = [
            anonymize_text(q, state) for q in interview.get("questions", [])
        ]
        interview["answers"] = [
            anonymize_text(a, state) for a in interview.get("answers", [])
        ]

    # Pivotal moments
    for pm in ctx_dict.get("pivotal_moments", []):
        pm["agent"] = anonymize_text(pm.get("agent", "") or "", state)
        pm["event"] = anonymize_text(pm.get("event", "") or "", state)

    # Full report markdown
    if ctx_dict.get("full_report_md"):
        ctx_dict["full_report_md"] = anonymize_text(ctx_dict["full_report_md"], state)

    # Reconstruire l'objet Pydantic
    return PDFReportContext.model_validate(ctx_dict)
