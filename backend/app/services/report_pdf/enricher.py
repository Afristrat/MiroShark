"""
Enricher — service LLM d'enrichissement du PDFReportContext.

US-124 — Enricher LLM (insights, pivotal_moments, interpretations narratives par chart).

Ce module transforme un PDFReportContext brut en un contexte enrichi prêt pour le
rendu PDF. Il orchestre :

1. ``_compute_kpi_hero``        — calcule KPIHero depuis outcome + quality_metrics
2. ``_detect_pivotal_moments``  — scanne la trajectoire et identifie les bascules >0.20
3. ``_generate_chart_narratives`` — génère ~80 mots par chart via LLM (cache LRU 24h)
4. ``_extract_executive_takeaways`` — 3 takeaways C-level via LLM (cache LRU 24h)
5. ``_pass_through_normalizer`` — tous textes générés passent par TextNormalizer(lang)

Architecture du cache :
    Pas de ``functools.lru_cache`` (incompatible avec des clés unhashable comme des
    dicts). Cache dict TTL implémenté manuellement avec ``time.time()`` — même
    pattern que ``_ENRICH_CACHE`` dans ``simulation.py`` (US-057).
    Clé : tuple ``(chart_id, data_hash, lang)`` ou ``(verdict, moments_hash, lang)``.
    TTL : 24h (86 400 s).

Fallback LLM :
    Si le LLM lève une exception (réseau, quota, clé absente), les méthodes
    retombent gracieusement sur un texte de remplacement. Aucun crash ne doit
    sortir de ce service.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Dict, List, Optional, Tuple

from ...services.text_normalizer import TextNormalizer
from ...utils.llm_client import create_llm_client
from .schema import KPIHero, PDFReportContext, PivotalMoment

logger = logging.getLogger("miroshark.report_pdf.enricher")

# ─── Constantes ──────────────────────────────────────────────────────────────

_PIVOTAL_THRESHOLD: float = 0.20
"""Variation de score minimale (absolue) pour qualifier un moment pivot."""

_CHART_IDS: Tuple[str, ...] = (
    "belief_drift",
    "polymarket_curves",
    "demographic_pyramid",
    "influence_leaderboard",
    "interaction_network",
)

_LLM_FALLBACK = "Analyse non disponible. Voir données brutes ci-dessous."
"""Texte de remplacement si le LLM est indisponible."""

_CACHE_TTL = 86_400  # 24 heures en secondes
_narrative_cache: Dict[Tuple, Dict] = {}
_takeaway_cache: Dict[Tuple, Dict] = {}


# ─── Helpers cache ───────────────────────────────────────────────────────────


def _cache_get(store: Dict, key: tuple) -> Optional[str]:
    """Retourne la valeur en cache si non expirée, sinon None."""
    entry = store.get(key)
    if entry and entry["expires_at"] > time.time():
        return entry["value"]
    return None


def _cache_put(store: Dict, key: tuple, value: str) -> None:
    """Stocke une valeur dans le cache avec TTL 24h."""
    store[key] = {"value": value, "expires_at": time.time() + _CACHE_TTL}


def _short_hash(text: str) -> str:
    """SHA-256 tronqué à 16 chars pour clé de cache."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ─── Classe principale ────────────────────────────────────────────────────────


class Enricher:
    """Service d'enrichissement LLM du PDFReportContext.

    Parameters
    ----------
    context:
        Le contexte PDF à enrichir (sera muté in-place).
    llm_client:
        Client LLM injecté (utile pour les tests). Si None, la factory
        ``create_llm_client()`` est utilisée.
    """

    def __init__(
        self,
        context: PDFReportContext,
        llm_client=None,
    ) -> None:
        self.context = context
        self.llm = llm_client if llm_client is not None else _safe_create_llm_client()
        self._normalizer = TextNormalizer(lang=context.lang, strictness="standard")

    # ── API publique ──────────────────────────────────────────────────────────

    def enrich(self) -> PDFReportContext:
        """Enrichit le contexte in-place et le retourne (chainable).

        Séquence :
        1. KPI héro        (pure computation, aucun LLM)
        2. Pivotal moments (pure computation, aucun LLM)
        3. Chart narratives (LLM, cache 24h)
        4. Executive takeaways (LLM, cache 24h)
        5. Pass TextNormalizer sur tous textes générés

        Returns
        -------
        PDFReportContext
            Le même objet muté (return pour chaînage).
        """
        self._compute_kpi_hero()
        self._detect_pivotal_moments()
        self._generate_chart_narratives()
        self._extract_executive_takeaways()
        self._pass_through_normalizer()
        return self.context

    # ── Méthodes privées ──────────────────────────────────────────────────────

    def _compute_kpi_hero(self) -> None:
        """Calcule et stocke le KPIHero dans context.kpi_hero.

        Source : context.outcome (verdict, bullish_pct, bearish_pct, confidence)
                + context.quality_metrics (brier via quality_metrics.coherence proxy)
                + context.outcome.quality_metrics.coherence

        Le champ ``brier`` du KPIHero utilise ``outcome.quality_metrics`` si présent,
        sinon ``context.quality_metrics``, sinon 0.0.
        """
        outcome = self.context.outcome

        verdict = ""
        confidence_pct = 0.0
        brier = 0.0
        scenario_distribution: Dict[str, float] = {}

        if outcome is not None:
            verdict = outcome.verdict
            confidence_pct = round(outcome.confidence * 100.0, 1)

            # Brier score : cherche dans outcome.quality_metrics d'abord,
            # puis context.quality_metrics. Le schema ne contient pas de champ
            # brier_score explicite ; on utilise `coherence` comme proxy du
            # score global (valeur [0,1], 0 = parfait pour Brier).
            qm = outcome.quality_metrics
            if qm is not None:
                brier = round(1.0 - qm.coherence, 4)
            elif self.context.quality_metrics is not None:
                brier = round(1.0 - self.context.quality_metrics.coherence, 4)

            # Distribution des scénarios : bullish / bearish / neutral (déduit)
            bullish = outcome.bullish_pct
            bearish = outcome.bearish_pct
            neutral = max(0.0, round(100.0 - bullish - bearish, 1))
            if bullish > 0 or bearish > 0:
                scenario_distribution = {
                    "bullish": round(bullish, 1),
                    "bearish": round(bearish, 1),
                    "neutral": neutral,
                }

        self.context.kpi_hero = KPIHero(
            verdict=verdict,
            confidence_pct=confidence_pct,
            brier=brier,
            scenario_distribution=scenario_distribution,
        )
        logger.debug("KPIHero calculé : verdict=%r confidence=%.1f%%", verdict, confidence_pct)

    def _detect_pivotal_moments(self) -> None:
        """Scanne la trajectoire et détecte les bascules de score > SEUIL=0.20.

        Pour chaque agent, compare son score au round N avec son score au round N-1.
        Si la variation absolue dépasse ``_PIVOTAL_THRESHOLD``, un PivotalMoment est
        créé et ajouté à context.pivotal_moments.

        La liste finale est triée par round ascendant.
        """
        if self.context.trajectory is None:
            return

        rounds = self.context.trajectory.rounds
        if len(rounds) < 2:
            return

        # Index : agent_id → score au round précédent
        prev_scores: Dict[str, float] = {}
        moments: List[PivotalMoment] = []

        for rnd in rounds:
            for agent_state in rnd.agents:
                agent_id = agent_state.agent_id or agent_state.name
                current_score = agent_state.score
                prev_score = prev_scores.get(agent_id)

                if prev_score is not None:
                    delta = current_score - prev_score
                    if abs(delta) >= _PIVOTAL_THRESHOLD:
                        moments.append(
                            PivotalMoment(
                                round=rnd.round_idx,
                                agent=agent_state.name or agent_id,
                                event="bascule",
                                delta_score=round(delta, 4),
                            )
                        )
                        logger.debug(
                            "Pivotal moment détecté : round=%d agent=%r delta=%.4f",
                            rnd.round_idx,
                            agent_state.name,
                            delta,
                        )

                prev_scores[agent_id] = current_score

        moments.sort(key=lambda m: m.round)
        self.context.pivotal_moments = moments

    def _generate_chart_narratives(self) -> None:
        """Génère une narrative ~80 mots pour chacun des 5 charts via LLM.

        Clé de cache : (chart_id, hash(data_summary), lang) — TTL 24h.
        Si le LLM échoue : fallback texte générique (pas de crash).
        Résultats stockés dans context.interpretations[chart_id].
        """
        lang = self.context.lang

        for chart_id in _CHART_IDS:
            summary = self._build_chart_summary(chart_id)
            cache_key = (chart_id, _short_hash(summary), lang)

            cached = _cache_get(_narrative_cache, cache_key)
            if cached is not None:
                self.context.interpretations[chart_id] = cached
                logger.debug("Cache HIT chart narrative : %s", chart_id)
                continue

            narrative = self._call_llm_for_chart(chart_id, summary, lang)
            _cache_put(_narrative_cache, cache_key, narrative)
            self.context.interpretations[chart_id] = narrative

    def _extract_executive_takeaways(self) -> None:
        """Génère 3 takeaways C-level via LLM.

        Source : outline.summary + outcome.verdict + pivotal_moments.
        Cache : (verdict_hash, moments_hash, lang) — TTL 24h.
        Stocké dans context.executive_takeaways.
        """
        lang = self.context.lang
        verdict = self.context.outcome.verdict if self.context.outcome else ""
        summary = self.context.outline.summary if self.context.outline else ""
        moments_repr = "; ".join(
            f"round {m.round} ({m.agent}, Δ{m.delta_score:+.2f})"
            for m in self.context.pivotal_moments[:5]
        )

        cache_key = (
            _short_hash(verdict + summary),
            _short_hash(moments_repr),
            lang,
        )

        cached = _cache_get(_takeaway_cache, cache_key)
        if cached is not None:
            # cached est une string JSON-like séparée par \n — on rehydrate
            self.context.executive_takeaways = [t for t in cached.split("\n") if t.strip()]
            logger.debug("Cache HIT executive takeaways")
            return

        takeaways = self._call_llm_for_takeaways(verdict, moments_repr, summary, lang)
        joined = "\n".join(takeaways)
        _cache_put(_takeaway_cache, cache_key, joined)
        self.context.executive_takeaways = takeaways

    def _pass_through_normalizer(self) -> None:
        """Passe tous les textes générés par TextNormalizer(lang).

        Traite :
        - context.interpretations (dict chart_id → narrative)
        - context.executive_takeaways (list de str)
        """
        normalizer = self._normalizer

        normalized_interps: Dict[str, str] = {}
        for chart_id, text in self.context.interpretations.items():
            normalized_interps[chart_id] = normalizer.normalize(text).normalized
        self.context.interpretations = normalized_interps

        normalized_takeaways: List[str] = []
        for text in self.context.executive_takeaways:
            normalized_takeaways.append(normalizer.normalize(text).normalized)
        self.context.executive_takeaways = normalized_takeaways

    # ── Helpers internes ──────────────────────────────────────────────────────

    def _build_chart_summary(self, chart_id: str) -> str:
        """Construit un résumé textuel court des données pour un chart donné.

        Limite volontairement à ~300 chars pour rester dans le contexte LLM court.
        """
        ctx = self.context

        if chart_id == "belief_drift":
            if ctx.trajectory and ctx.trajectory.rounds:
                rounds = ctx.trajectory.rounds
                n = len(rounds)
                first_scores = {
                    a.name or a.agent_id: a.score
                    for a in (rounds[0].agents or [])
                    if (a.name or a.agent_id)
                }
                last_scores = {
                    a.name or a.agent_id: a.score
                    for a in (rounds[-1].agents or [])
                    if (a.name or a.agent_id)
                }
                deltas = [
                    f"{name}: {first_scores.get(name, 0):.2f}→{last_scores.get(name, score):.2f}"
                    for name, score in last_scores.items()
                    if name in first_scores
                ]
                return f"{n} rounds. Trajectoires agents: {', '.join(deltas[:6])}"
            return "Trajectoire absente."

        if chart_id == "polymarket_curves":
            if ctx.outcome:
                o = ctx.outcome
                return (
                    f"Verdict: {o.verdict[:80]}. "
                    f"Bullish {o.bullish_pct:.1f}%, bearish {o.bearish_pct:.1f}%."
                )
            return "Outcome absent."

        if chart_id == "demographic_pyramid":
            if ctx.demographics and ctx.demographics.segments:
                segs = ctx.demographics.segments[:8]
                parts = [f"{s.label} {s.pct:.1f}%" for s in segs]
                return f"Total agents: {ctx.demographics.total}. Segments: {', '.join(parts)}"
            return "Données démographiques absentes."

        if chart_id == "influence_leaderboard":
            if ctx.trajectory and ctx.trajectory.rounds:
                last_round = ctx.trajectory.rounds[-1]
                agents_sorted = sorted(
                    last_round.agents or [],
                    key=lambda a: abs(a.score),
                    reverse=True,
                )
                top = [f"{a.name or a.agent_id} ({a.score:.2f})" for a in agents_sorted[:8]]
                return f"Top influenceurs round final: {', '.join(top)}"
            return "Trajectoire absente."

        if chart_id == "interaction_network":
            if ctx.social_network:
                n_nodes = len(ctx.social_network.nodes)
                n_edges = len(ctx.social_network.edges)
                return f"Réseau social: {n_nodes} nœuds, {n_edges} arêtes."
            return "Réseau social absent."

        return f"Chart {chart_id}: données non disponibles."

    def _call_llm_for_chart(self, chart_id: str, summary: str, lang: str) -> str:
        """Appelle le LLM pour générer une narrative de chart.

        Retourne _LLM_FALLBACK en cas d'erreur.
        """
        if self.llm is None:
            return _LLM_FALLBACK

        prompt = (
            f"En tant qu'analyste C-level, interprète ce graphe en {lang} en 80 mots maximum, "
            f"ton professionnel sobre, mets en avant 1 insight clé et 1 nuance. "
            f"Données : {summary}"
        )
        messages = [{"role": "user", "content": prompt}]

        try:
            result = self.llm.chat(messages=messages, max_tokens=200, temperature=0.3)
            return result.strip() if result else _LLM_FALLBACK
        except Exception as exc:
            logger.warning("LLM indisponible pour chart %s : %s", chart_id, exc)
            return _LLM_FALLBACK

    def _call_llm_for_takeaways(
        self,
        verdict: str,
        moments: str,
        summary: str,
        lang: str,
    ) -> List[str]:
        """Appelle le LLM pour générer 3 takeaways C-level.

        Retourne une liste de 3 strings. En cas d'erreur LLM : 3 fallbacks.
        """
        if self.llm is None:
            return [_LLM_FALLBACK, _LLM_FALLBACK, _LLM_FALLBACK]

        prompt = (
            f"Synthétise en 3 takeaways C-level (1 phrase chacun, ton ferme) en {lang} "
            f"les enseignements clés de cette simulation. "
            f"Verdict : {verdict[:200]}. "
            f"Pivotal moments : {moments[:300]}. "
            f"Outline summary : {summary[:300]}. "
            f"Réponds UNIQUEMENT avec 3 lignes numérotées, sans commentaire."
        )
        messages = [{"role": "user", "content": prompt}]

        try:
            result = self.llm.chat(messages=messages, max_tokens=300, temperature=0.3)
            if not result:
                return [_LLM_FALLBACK, _LLM_FALLBACK, _LLM_FALLBACK]

            lines = [
                line.strip().lstrip("123. )-").strip()
                for line in result.strip().splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            # Garde exactement 3 takeaways ; complète ou tronque si besoin
            while len(lines) < 3:
                lines.append(_LLM_FALLBACK)
            return lines[:3]

        except Exception as exc:
            logger.warning("LLM indisponible pour executive takeaways : %s", exc)
            return [_LLM_FALLBACK, _LLM_FALLBACK, _LLM_FALLBACK]


# ─── Factory helper ───────────────────────────────────────────────────────────


def _safe_create_llm_client():
    """Retourne le client LLM par défaut. Retourne None si non configuré."""
    try:
        return create_llm_client()
    except Exception as exc:
        logger.warning("LLMClient non disponible (config manquante) : %s", exc)
        return None
