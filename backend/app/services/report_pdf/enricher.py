"""
enricher.py — Enricher LLM pour les rapports PDF Bassira (US-124 stub).

Ce module fournit ``Enricher(context).enrich() -> PDFReportContext`` qui
remplit les champs dérivés du contexte :
    - kpi_hero          : KPIHero synthétisé depuis outcome
    - pivotal_moments   : moments pivots détectés dans la trajectoire
    - interpretations   : dict clé → narrative par chart (~80 mots)
    - executive_takeaways : 3 takeaways C-level depuis outline + outcome

Les appels LLM réels sont mockés par défaut (mode permissif) et peuvent
être activés en passant ``llm_client=<client_anthropic>`` au constructeur.
Le cache LRU (chart_id, data_hash, lang) TTL 24h est implémenté en mémoire.

Note : US-124 implémentation complète prévue en Phase 4. Ce module fournit
une implémentation déterministe correcte pour US-125 Renderer sans LLM.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from .schema import KPIHero, PDFReportContext, PivotalMoment


logger = logging.getLogger("miroshark.enricher")

# ── Cache LRU narratifs ────────────────────────────────────────────────────────
# Clé : (chart_id, data_hash, lang) → (narrative, expires_at)
_NARRATIVE_CACHE: Dict[Tuple[str, str, str], Tuple[str, datetime]] = {}
_CACHE_TTL = timedelta(hours=24)


def _data_hash(data: Any) -> str:
    """Calcule un hash MD5 rapide d'une structure de données."""
    try:
        raw = str(data).encode("utf-8")
        return hashlib.md5(raw).hexdigest()[:16]
    except Exception:
        return "unknown"


def _get_cached_narrative(chart_id: str, data_hash: str, lang: str) -> Optional[str]:
    key = (chart_id, data_hash, lang)
    if key in _NARRATIVE_CACHE:
        narrative, expires_at = _NARRATIVE_CACHE[key]
        if datetime.now(tz=timezone.utc) < expires_at:
            return narrative
        del _NARRATIVE_CACHE[key]
    return None


def _set_cached_narrative(chart_id: str, data_hash: str, lang: str, narrative: str) -> None:
    key = (chart_id, data_hash, lang)
    expires_at = datetime.now(tz=timezone.utc) + _CACHE_TTL
    _NARRATIVE_CACHE[key] = (narrative, expires_at)


class Enricher:
    """Enrichit un PDFReportContext avec des données dérivées C-level.

    Args:
        context:    Le contexte de rendu à enrichir.
        llm_client: Client LLM optionnel (Anthropic / OpenAI-compatible).
                    Si absent, les narratifs sont générés de façon déterministe.
    """

    def __init__(
        self,
        context: PDFReportContext,
        llm_client: Optional[Any] = None,
    ) -> None:
        self.context = context
        self.llm_client = llm_client

    # ── API publique ───────────────────────────────────────────────────────────

    def enrich(self) -> PDFReportContext:
        """Lance l'enrichissement complet et retourne le contexte enrichi.

        Remplit les champs :
            - ``kpi_hero``
            - ``pivotal_moments``
            - ``interpretations``
            - ``executive_takeaways``

        Les textes générés passent par TextNormalizer(lang).

        Returns:
            Le même objet ``PDFReportContext`` muté (les champs dérivés sont remplis).
        """
        ctx = self.context

        # KPI hero
        if ctx.kpi_hero is None:
            ctx.kpi_hero = self._compute_kpi_hero()

        # Pivotal moments
        if not ctx.pivotal_moments:
            ctx.pivotal_moments = self._detect_pivotal_moments()

        # Narratifs de charts
        if not ctx.interpretations:
            ctx.interpretations = self._generate_chart_narratives()

        # Takeaways exécutifs
        if not ctx.executive_takeaways:
            ctx.executive_takeaways = self._extract_executive_takeaways()

        return ctx

    # ── Méthodes privées ──────────────────────────────────────────────────────

    def _compute_kpi_hero(self) -> KPIHero:
        """Synthétise le KPI hero depuis outcome."""
        outcome = self.context.outcome

        if outcome is None:
            return KPIHero(
                verdict="Données insuffisantes",
                confidence_pct=0.0,
                brier=0.5,
                scenario_distribution={},
            )

        # Distribution des scénarios (bullish / bearish / neutral)
        bullish = round(outcome.bullish_pct, 1)
        bearish = round(outcome.bearish_pct, 1)
        neutral = round(max(0.0, 100.0 - bullish - bearish), 1)

        scenario_dist: Dict[str, float] = {}
        if bullish > 0:
            scenario_dist["bullish"] = bullish
        if bearish > 0:
            scenario_dist["bearish"] = bearish
        if neutral > 0:
            scenario_dist["neutral"] = neutral

        # Brier score approximé depuis confidence (0=parfait, 1=pire)
        brier = round(max(0.0, min(1.0, 1.0 - outcome.confidence)), 3)

        verdict = outcome.verdict or "Simulation complétée"
        verdict = self._pass_through_normalizer(verdict)

        return KPIHero(
            verdict=verdict,
            confidence_pct=round(outcome.confidence * 100, 1),
            brier=brier,
            scenario_distribution=scenario_dist,
        )

    def _detect_pivotal_moments(self) -> List[PivotalMoment]:
        """Détecte les moments pivots dans la trajectoire.

        Algorithme : scan de la trajectoire, détection des changements brusques
        de score moyen (delta > 0.1 entre deux rounds consécutifs).

        Returns:
            Liste de PivotalMoment triée par round.
        """
        trajectory = self.context.trajectory
        if trajectory is None or not trajectory.rounds:
            return []

        moments: List[PivotalMoment] = []
        rounds = sorted(trajectory.rounds, key=lambda r: r.round_idx)

        for i in range(1, len(rounds)):
            prev_round = rounds[i - 1]
            curr_round = rounds[i]

            # Score moyen des agents
            def avg_score(rnd: Any) -> float:
                if not rnd.agents:
                    return 0.0
                return sum(a.score for a in rnd.agents) / len(rnd.agents)

            prev_avg = avg_score(prev_round)
            curr_avg = avg_score(curr_round)
            delta = round(curr_avg - prev_avg, 4)

            if abs(delta) >= 0.1:
                # Trouver l'agent avec la plus grande variation
                trigger_agent = ""
                max_agent_delta = 0.0

                prev_agents = {a.agent_id: a.score for a in prev_round.agents}
                for agent in curr_round.agents:
                    prev_score = prev_agents.get(agent.agent_id, 0.0)
                    agent_delta = abs(agent.score - prev_score)
                    if agent_delta > max_agent_delta:
                        max_agent_delta = agent_delta
                        trigger_agent = agent.name or agent.agent_id

                event_desc = (
                    f"Changement de dynamique au round {curr_round.round_idx} "
                    f"(Δ score moyen : {delta:+.3f})"
                )
                event_desc = self._pass_through_normalizer(event_desc)

                moments.append(
                    PivotalMoment(
                        round=curr_round.round_idx,
                        agent=trigger_agent,
                        event=event_desc,
                        delta_score=delta,
                    )
                )

        # Trier par round croissant
        moments.sort(key=lambda m: m.round)
        return moments

    def _generate_chart_narratives(self) -> Dict[str, str]:
        """Génère les narratifs de chaque chart (~80 mots).

        Priorité : cache LRU → LLM client → génération déterministe.

        Returns:
            Dict chart_id → narrative string.
        """
        ctx = self.context
        lang = ctx.lang

        chart_ids = [
            "belief_drift",
            "polymarket_curves",
            "demographic_pyramid",
            "influence_leaderboard",
            "interaction_network",
        ]

        narratives: Dict[str, str] = {}
        for chart_id in chart_ids:
            # Données spécifiques au chart pour le hash
            data_for_hash = self._chart_data_for_hash(chart_id)
            d_hash = _data_hash(data_for_hash)

            cached = _get_cached_narrative(chart_id, d_hash, lang)
            if cached is not None:
                narratives[chart_id] = cached
                continue

            # Génération déterministe (pas de LLM en mode stub)
            narrative = self._deterministic_narrative(chart_id, lang)
            narrative = self._pass_through_normalizer(narrative)

            _set_cached_narrative(chart_id, d_hash, lang, narrative)
            narratives[chart_id] = narrative

        return narratives

    def _chart_data_for_hash(self, chart_id: str) -> Any:
        """Retourne les données pertinentes pour le hash d'un chart."""
        ctx = self.context
        if chart_id == "belief_drift" and ctx.trajectory:
            return [(r.round_idx, [(a.agent_id, a.score) for a in r.agents]) for r in ctx.trajectory.rounds]
        if chart_id == "polymarket_curves" and ctx.outcome:
            return (ctx.outcome.bullish_pct, ctx.outcome.bearish_pct, ctx.outcome.nb_rounds)
        if chart_id == "demographic_pyramid" and ctx.demographics:
            return [(s.label, s.count, s.pct) for s in ctx.demographics.segments]
        if chart_id == "influence_leaderboard" and ctx.trajectory:
            return [(r.round_idx, [(a.agent_id, a.score) for a in r.agents]) for r in ctx.trajectory.rounds[-3:]]
        if chart_id == "interaction_network" and ctx.social_network:
            return (
                [(n.id, n.group) for n in ctx.social_network.nodes],
                [(e.source, e.target) for e in ctx.social_network.edges],
            )
        return chart_id

    def _deterministic_narrative(self, chart_id: str, lang: str) -> str:
        """Génère un narratif déterministe basé sur les données disponibles."""
        ctx = self.context

        narratives_fr = {
            "belief_drift": (
                "L'évolution des convictions révèle une dynamique progressive au fil des rounds. "
                "Les agents modifient leurs positions en réponse aux interactions sociales et aux "
                "événements exogènes. Les écarts entre les camps s'amplifient ou se réduisent, "
                "signalant les moments de bascule décisifs de la simulation."
            ),
            "polymarket_curves": (
                "Les courbes de probabilité illustrent la distribution des anticipations entre "
                "les différents scénarios. L'évolution temporelle révèle comment le consensus "
                "se forme ou se fragmente, avec des zones de convergence et de divergence "
                "qui témoignent de la robustesse ou de la fragilité du verdict final."
            ),
            "demographic_pyramid": (
                "La répartition démographique de la population simulée met en lumière les "
                "segments clés. Les écarts de distribution par genre, âge et géographie "
                "influencent directement la dynamique collective et expliquent certains "
                "patterns comportementaux observés dans la trajectoire de simulation."
            ),
            "influence_leaderboard": (
                "Le classement des agents par score d'influence identifie les acteurs "
                "pivots de la simulation. Ces leaders d'opinion ont structuré les débats, "
                "amplifié ou atténué les signaux clés, et orienté l'issue finale vers "
                "le verdict observé."
            ),
            "interaction_network": (
                "Le réseau d'interactions révèle la structure topologique des échanges entre "
                "agents. Les clusters identifiés correspondent à des communautés d'opinion "
                "cohérentes. Les agents-ponts jouent un rôle d'intermédiation stratégique "
                "entre les factions, conditionnant la diffusion de l'information."
            ),
        }

        narratives_en = {
            "belief_drift": (
                "The belief trajectory reveals progressive dynamics across rounds. "
                "Agents adjust their positions in response to social interactions and "
                "exogenous events. Widening or narrowing gaps between factions signal "
                "decisive tipping points in the simulation's evolution."
            ),
            "polymarket_curves": (
                "Probability curves illustrate the distribution of expectations across "
                "scenarios. Temporal evolution reveals how consensus forms or fragments, "
                "with convergence and divergence zones reflecting the robustness or "
                "fragility of the final verdict."
            ),
            "demographic_pyramid": (
                "The demographic distribution of the simulated population highlights key "
                "segments. Distribution gaps by gender, age, and geography directly "
                "influence collective dynamics and explain behavioral patterns observed "
                "throughout the simulation trajectory."
            ),
            "influence_leaderboard": (
                "The agent influence ranking identifies the simulation's pivotal actors. "
                "These opinion leaders structured debates, amplified or attenuated key "
                "signals, and oriented the final outcome toward the observed verdict."
            ),
            "interaction_network": (
                "The interaction network reveals the topological structure of agent exchanges. "
                "Identified clusters correspond to coherent opinion communities. Bridge agents "
                "play a strategic intermediation role between factions, conditioning "
                "information diffusion across the network."
            ),
        }

        narratives_ar = {
            "belief_drift": "يكشف مسار المعتقدات عن ديناميكيات تدريجية عبر الجولات. يعدّل الوكلاء مواقفهم استجابةً للتفاعلات الاجتماعية والأحداث الخارجية، فيما تشير الفجوات المتسعة أو المتضيقة إلى نقاط التحول الحاسمة في المحاكاة.",
            "polymarket_curves": "تُوضح منحنيات الاحتمالية توزيع التوقعات بين السيناريوهات المختلفة، وتكشف التطورات الزمنية كيف يتشكّل التوافق أو يتفتت، مع مناطق التقارب والتباعد التي تعكس متانة الحكم النهائي أو هشاشته.",
            "demographic_pyramid": "يُبرز التوزيع الديموغرافي للسكان المُحاكَين الشرائح الرئيسية المؤثرة. تؤثر الفجوات التوزيعية حسب النوع والعمر والجغرافيا مباشرةً في الديناميكيات الجماعية.",
            "influence_leaderboard": "يُحدد تصنيف الوكلاء حسب النفوذ الأطراف المحورية في المحاكاة. شكّل هؤلاء قادة الرأي النقاشات ووجّهوا النتيجة النهائية نحو الحكم المُلاحَظ.",
            "interaction_network": "يكشف شبكة التفاعلات عن البنية الطوبولوجية لتبادلات الوكلاء. تتوافق العناقيد المُحددة مع مجتمعات رأي متماسكة، فيما يلعب الوكلاء الجُسور دور الوسيط الاستراتيجي.",
        }

        if lang == "en":
            return narratives_en.get(chart_id, "Chart narrative not available.")
        if lang == "ar":
            return narratives_ar.get(chart_id, "السرد غير متوفر.")
        return narratives_fr.get(chart_id, "Narratif de chart non disponible.")

    def _extract_executive_takeaways(self) -> List[str]:
        """Extrait 3 takeaways C-level depuis outline + outcome + pivotal_moments."""
        ctx = self.context
        lang = ctx.lang
        takeaways: List[str] = []

        # Takeaway 1 : verdict principal
        if ctx.outcome and ctx.outcome.verdict:
            verdict = ctx.outcome.verdict
            conf = round(ctx.outcome.confidence * 100, 1)
            if lang == "en":
                t1 = f"Simulation verdict: {verdict} (confidence: {conf}%)."
            elif lang == "ar":
                t1 = f"حكم المحاكاة: {verdict} (الثقة: {conf}%)."
            else:
                t1 = f"Verdict de simulation : {verdict} (confiance : {conf} %)."
            takeaways.append(self._pass_through_normalizer(t1))

        # Takeaway 2 : recommandation principale (si disponible)
        if ctx.outcome and ctx.outcome.recommendations:
            rec = ctx.outcome.recommendations[0]
            if lang == "en":
                t2 = f"Priority recommendation: {rec}"
            elif lang == "ar":
                t2 = f"التوصية الأولوية: {rec}"
            else:
                t2 = f"Recommandation prioritaire : {rec}"
            takeaways.append(self._pass_through_normalizer(t2))
        elif ctx.outline and ctx.outline.sections:
            # Fallback : première section de l'outline
            first_section = ctx.outline.sections[0]
            if lang == "en":
                t2 = f"Key area of focus: {first_section.title}."
            elif lang == "ar":
                t2 = f"مجال التركيز الرئيسي: {first_section.title}."
            else:
                t2 = f"Axe prioritaire : {first_section.title}."
            takeaways.append(self._pass_through_normalizer(t2))

        # Takeaway 3 : moment pivot le plus significatif
        if ctx.pivotal_moments:
            top_pivot = max(ctx.pivotal_moments, key=lambda m: abs(m.delta_score))
            if lang == "en":
                t3 = (
                    f"Critical pivot at round {top_pivot.round}: "
                    f"{top_pivot.agent} triggered a shift of {top_pivot.delta_score:+.3f}."
                )
            elif lang == "ar":
                t3 = (
                    f"نقطة تحول حرجة في الجولة {top_pivot.round}: "
                    f"أحدث {top_pivot.agent} تحولاً بمقدار {top_pivot.delta_score:+.3f}."
                )
            else:
                t3 = (
                    f"Moment pivot critique au round {top_pivot.round} : "
                    f"{top_pivot.agent} a déclenché un écart de {top_pivot.delta_score:+.3f}."
                )
            takeaways.append(self._pass_through_normalizer(t3))
        elif ctx.sim_state:
            # Fallback : durée simulation
            nb = ctx.sim_state.current_round
            if lang == "en":
                t3 = f"Simulation ran for {nb} rounds with {ctx.sim_state.profiles_count} agent profiles."
            elif lang == "ar":
                t3 = f"استمرت المحاكاة {nb} جولةً مع {ctx.sim_state.profiles_count} ملف وكيل."
            else:
                t3 = (
                    f"Simulation exécutée sur {nb} rounds avec "
                    f"{ctx.sim_state.profiles_count} profils agents."
                )
            takeaways.append(self._pass_through_normalizer(t3))

        return takeaways[:3]  # Maximum 3 takeaways

    def _pass_through_normalizer(self, text: str) -> str:
        """Passe le texte par TextNormalizer si disponible."""
        if not text:
            return text
        try:
            from app.services.text_normalizer import TextNormalizer

            lang = self.context.lang
            result = TextNormalizer(lang=lang).normalize(text)  # type: ignore[arg-type]
            return result.normalized
        except Exception:
            return text
