"""
Enricher — service LLM d'enrichissement du PDFReportContext.

US-124 — Enricher LLM (insights, pivotal_moments, interpretations narratives par chart).
US-135 — Enricher fixes : KPI Hero réel + sanitize tool_call + pivotal_moments.

Ce module transforme un PDFReportContext brut en un contexte enrichi prêt pour le
rendu PDF. Il orchestre :

1. ``_compute_kpi_hero``        — calcule KPIHero depuis outcome + quality_metrics
2. ``_detect_pivotal_moments``  — scanne la trajectoire et identifie les bascules >0.20
3. ``_generate_chart_narratives`` — génère ~80 mots par chart via LLM (cache LRU 24h)
4. ``_extract_executive_takeaways`` — 3 takeaways C-level via LLM (cache LRU 24h)
5. ``_pass_through_normalizer`` — tous textes générés passent par TextNormalizer(lang)

Sanitize LLM (US-135) :
    ``sanitize_llm_output(text)`` supprime toute balise <tool_call>, <function_call>,
    <thinking>, <scratchpad>, [function_calls]…[/function_calls] et leurs variantes
    échappées avant d'injecter le texte dans le contexte PDF client.
    Appliqué systématiquement sur chaque sortie LLM.

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
import re
import time
from typing import Dict, List, Optional, Tuple

from ...services.text_normalizer import TextNormalizer
from ...utils.llm_client import create_llm_client
from .schema import KPIHero, PDFReportContext, PivotalMoment

logger = logging.getLogger("miroshark.report_pdf.enricher")

# ─── Sanitize LLM output (US-135) ────────────────────────────────────────────

_TAG_PATTERNS: Tuple[re.Pattern, ...] = (
    # Balises <tool_call>...</tool_call> avec attributs optionnels, multiline
    re.compile(r"<tool_call\b[^>]*>.*?</tool_call>", re.DOTALL | re.IGNORECASE),
    # Balises auto-fermées <tool_call ... />
    re.compile(r"<tool_call\b[^>]*/>", re.IGNORECASE),
    # Balises <function_call>...</function_call>
    re.compile(r"<function_call\b[^>]*>.*?</function_call>", re.DOTALL | re.IGNORECASE),
    # Balises <thinking>...</thinking>
    re.compile(r"<thinking\b[^>]*>.*?</thinking>", re.DOTALL | re.IGNORECASE),
    # Balises <scratchpad>...</scratchpad>
    re.compile(r"<scratchpad\b[^>]*>.*?</scratchpad>", re.DOTALL | re.IGNORECASE),
    # Blocs [function_calls]...[/function_calls]
    re.compile(r"\[function_calls\].*?\[/function_calls\]", re.DOTALL | re.IGNORECASE),
    # Versions échappées \<tool_call\>...\</tool_call\>
    re.compile(r"\\<tool_call\\>.*?\\</tool_call\\>", re.DOTALL | re.IGNORECASE),
)


def sanitize_llm_output(text: str) -> str:
    """Supprime toute balise LLM interne (tool_call, thinking, etc.) du texte.

    Appliqué sur **chaque** sortie LLM avant injection dans le contexte PDF client.
    Garantit qu'aucune balise technique brute ne se retrouve dans un livrable client.

    Patterns supprimés :
    - ``<tool_call>...</tool_call>`` (et variantes avec attributs, auto-fermées)
    - ``<function_call>...</function_call>``
    - ``<thinking>...</thinking>``
    - ``<scratchpad>...</scratchpad>``
    - ``[function_calls]...[/function_calls]``
    - Versions échappées ``\\<tool_call\\>...\\</tool_call\\>``

    Parameters
    ----------
    text:
        Texte brut issu du LLM.

    Returns
    -------
    str
        Texte nettoyé, stripped des espaces résiduels.
    """
    if not text:
        return text
    cleaned = text
    for pattern in _TAG_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    return cleaned.strip()


# ─── Constantes ──────────────────────────────────────────────────────────────

_PIVOTAL_THRESHOLD: float = 0.20
"""Variation de score minimale (absolue) pour qualifier un moment pivot."""

_CHART_IDS: Tuple[str, ...] = (
    "belief_drift",
    "polymarket_curves",
    "demographic_pyramid",
    "influence_leaderboard",
    "interaction_network",
    "influence_posture_matrix",
    "stance_flow_sankey",
    "agent_engagement_heatmap",
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
        1. Synthèse outcome depuis trajectory si absent (pure computation)
        2. Synthèse sim_state depuis trajectory si counters manquants
        3. KPI héro        (pure computation, aucun LLM)
        4. Pivotal moments (pure computation, aucun LLM)
        5. Chart narratives (LLM, cache 24h)
        6. Executive takeaways (LLM, cache 24h)
        7. Promotion d'une recommandation lisible si outcome.recommendations vide
        8. Pass TextNormalizer sur tous textes générés

        Returns
        -------
        PDFReportContext
            Le même objet muté (return pour chaînage).
        """
        self._synthesize_outcome_from_trajectory()
        self._synthesize_sim_state_from_trajectory()
        self._compute_kpi_hero()
        self._detect_pivotal_moments()
        self._generate_chart_narratives()
        self._extract_executive_takeaways()
        self._promote_recommendation_from_raw_md()
        self._pass_through_normalizer()
        return self.context

    # ── Méthodes privées ──────────────────────────────────────────────────────

    def _synthesize_outcome_from_trajectory(self) -> None:
        """Synthétise un Outcome minimal si absent mais trajectory présent.

        Quand la simulation termine sans avoir produit ``outcome.json``, le
        rapport affichait "Verdict non disponible" partout (bug B18). On
        reconstruit ici :
        - ``bullish_pct`` / ``bearish_pct`` depuis le dernier round
          (signe du score >0/<0)
        - ``confidence`` = moyenne des |score| du dernier round, sur [0, 1]
        - ``verdict`` court : "Convergence partielle" ou "Polarisation
          structurelle" selon la dispersion finale
        - ``nb_rounds`` depuis len(rounds)
        - ``consensus_reached`` vrai si > 70 % du même signe et écart-type
          < 0.25

        Aucun appel LLM ici, calcul pur et déterministe.
        """
        from .schema import Outcome  # import local pour éviter cycle

        ctx = self.context
        if ctx.outcome is not None and ctx.outcome.verdict:
            return  # outcome déjà fourni — rien à faire

        if ctx.trajectory is None or not ctx.trajectory.rounds:
            return

        last_round = ctx.trajectory.rounds[-1]
        agents = [a for a in last_round.agents if a.agent_id or a.name]
        if not agents:
            return

        n = len(agents)
        bullish_n = sum(1 for a in agents if a.score > 0.05)
        bearish_n = sum(1 for a in agents if a.score < -0.05)
        bullish_pct = round(100.0 * bullish_n / n, 1)
        bearish_pct = round(100.0 * bearish_n / n, 1)

        avg_abs = sum(abs(a.score) for a in agents) / n
        confidence = min(1.0, max(0.0, avg_abs))

        mean_score = sum(a.score for a in agents) / n
        variance = sum((a.score - mean_score) ** 2 for a in agents) / n
        std = variance ** 0.5
        consensus_reached = (
            max(bullish_pct, bearish_pct) > 70.0 and std < 0.25
        )

        if consensus_reached and bullish_pct > bearish_pct:
            verdict = "Convergence majoritaire vers une position constructive"
            scenario_winner = "bullish"
        elif consensus_reached and bearish_pct > bullish_pct:
            verdict = "Convergence majoritaire vers une position de retrait"
            scenario_winner = "bearish"
        elif std >= 0.30:
            verdict = "Polarisation structurelle — pas de consensus"
            scenario_winner = None
        else:
            verdict = "Convergence partielle, signal exploitable mais à valider"
            scenario_winner = "bullish" if mean_score > 0 else "bearish" if mean_score < 0 else None

        existing = ctx.outcome if ctx.outcome is not None else Outcome()
        # Hydrate uniquement les champs vides — préserve ce que la sim a fourni.
        if not existing.verdict:
            existing.verdict = verdict
        if existing.bullish_pct == 0.0:
            existing.bullish_pct = bullish_pct
        if existing.bearish_pct == 0.0:
            existing.bearish_pct = bearish_pct
        if existing.confidence == 0.0:
            existing.confidence = round(confidence, 4)
        if existing.nb_rounds == 0:
            existing.nb_rounds = len(ctx.trajectory.rounds)
        if not existing.consensus_reached:
            existing.consensus_reached = consensus_reached
        if existing.scenario_winner is None and scenario_winner is not None:
            existing.scenario_winner = scenario_winner

        ctx.outcome = existing
        logger.info(
            "Outcome synthétisé depuis trajectory : verdict=%r conf=%.2f bullish=%.1f%% bearish=%.1f%% rounds=%d",
            verdict, confidence, bullish_pct, bearish_pct, len(ctx.trajectory.rounds),
        )

    def _synthesize_sim_state_from_trajectory(self) -> None:
        """Hydrate ``sim_state.current_round`` et ``profiles_count`` si vides.

        Le diagnostic affichait "Rounds exécutés : 0" alors que la trajectoire
        contenait 71 rounds (bug B6). On rabote la valeur depuis la trajectoire
        et le nombre d'agents distincts vus dans la simulation.
        """
        from .schema import SimState

        ctx = self.context
        if ctx.trajectory is None or not ctx.trajectory.rounds:
            return

        sim_state = ctx.sim_state if ctx.sim_state is not None else SimState()

        nb_rounds = len(ctx.trajectory.rounds)
        if sim_state.current_round == 0:
            sim_state.current_round = nb_rounds

        if sim_state.profiles_count == 0:
            # Compte les agents distincts via leur agent_id (ou name si pas d'id)
            seen: set = set()
            for rnd in ctx.trajectory.rounds:
                for a in rnd.agents:
                    key = a.agent_id or a.name
                    if key:
                        seen.add(key)
            if seen:
                sim_state.profiles_count = len(seen)

        # entities_count doit refléter le graphe d'entités, pas les agents.
        # Si on n'a pas d'info plus fine, on laisse à 0 plutôt que dupliquer
        # profiles_count (bug B7).

        ctx.sim_state = sim_state

    def _promote_recommendation_from_raw_md(self) -> None:
        """Si ``outcome.recommendations`` est vide, tente d'extraire une
        "Recommandation unique pour le décideur" du markdown brut (bug B12).

        Le ReportAgent produit parfois un markdown narratif (annexe 7.3)
        contenant en clair ::

            **Recommandation unique pour le décideur :**
            Ne produisez aucune slide supplémentaire ; …

        Cette information ne remontait jamais dans la section 6
        "Recommandations C-Level" qui affichait "Aucune recommandation".
        Ici on parse le markdown brut et on remplit ``recommendations``.
        """
        from .schema import Outcome

        ctx = self.context
        outcome = ctx.outcome if ctx.outcome is not None else Outcome()
        if outcome.recommendations:
            return  # déjà rempli

        raw_md = ctx.full_report_md or ""
        if not raw_md:
            return

        # Cherche les blocs "Recommandation …:" ou "Recommandations:" suivis
        # d'un texte. On capture jusqu'au prochain titre de section ou ligne
        # vide doublée.
        patterns = (
            re.compile(
                r"\*\*Recommandation(?:s)?\s*(?:unique\s+)?(?:pour\s+le\s+d[ée]cideur)?\s*:?\*\*\s*\n+(.+?)(?=\n\s*\n|\n#)",
                re.DOTALL | re.IGNORECASE,
            ),
            re.compile(
                r"^##+\s*Recommandation[s]?[^\n]*\n+(.+?)(?=\n##|\Z)",
                re.DOTALL | re.MULTILINE | re.IGNORECASE,
            ),
        )

        extracted: List[str] = []
        for pat in patterns:
            for m in pat.finditer(raw_md):
                text = m.group(1).strip()
                # Strip bullets et numéros en début de ligne
                lines = [
                    re.sub(r"^[\s\-\*•·]+|^\d+[\.\)]\s*", "", line).strip()
                    for line in text.splitlines()
                    if line.strip()
                ]
                # Reflow en une seule phrase si court, sinon garder structure
                joined = " ".join(lines).strip()
                if joined and len(joined) > 20:
                    # Limite à ~600 chars pour rester actionnable et lisible
                    if len(joined) > 600:
                        joined = joined[:597].rstrip() + "…"
                    extracted.append(joined)
                if len(extracted) >= 5:
                    break
            if extracted:
                break

        if extracted:
            outcome.recommendations = extracted
            ctx.outcome = outcome
            logger.info("Promu %d recommandation(s) depuis full_report_md.", len(extracted))

    def _compute_kpi_hero(self) -> None:
        """Calcule et stocke le KPIHero dans context.kpi_hero.

        Source : context.outcome (verdict, bullish_pct, bearish_pct)
                + context.quality_metrics (brier via brier_score si présent,
                  sinon proxy 1-coherence)

        US-135 — Corrections :
        - ``confidence_pct`` : dérivé de ``outcome.bullish_pct`` (ou 100 - bearish_pct
          si bullish absent) — NON plus de ``outcome.confidence`` qui est souvent 0.0.
        - ``brier`` : utilise ``quality_metrics.brier_score`` si l'attribut existe,
          sinon proxy ``1 - coherence``. Compatible avec l'extension future du schéma.
        """
        outcome = self.context.outcome

        verdict = ""
        confidence_pct = 0.0
        brier = 0.0
        scenario_distribution: Dict[str, float] = {}

        if outcome is not None:
            verdict = outcome.verdict

            # Confidence : préférence donnée à outcome.confidence (calculée comme
            # moyenne des |score| par _synthesize_outcome_from_trajectory en
            # absence de verdict explicite), puis fallback sur bullish_pct.
            if outcome.confidence is not None and outcome.confidence > 0.0:
                confidence_pct = round(float(outcome.confidence) * 100.0, 1)
            elif outcome.bullish_pct is not None and outcome.bullish_pct > 0.0:
                confidence_pct = round(float(outcome.bullish_pct), 1)
            elif outcome.bearish_pct is not None and outcome.bearish_pct > 0.0:
                confidence_pct = round(100.0 - float(outcome.bearish_pct), 1)
            else:
                confidence_pct = 0.0

            # Brier score : préfère brier_score explicite si disponible (extension future
            # du schéma QualityMetrics), sinon proxy 1-coherence si coherence > 0
            # (sinon on laisse à 0.0 plutôt que de produire un Brier=1.0 trompeur
            # qui ferait croire à une prédiction "totalement fausse").
            qm = outcome.quality_metrics
            qm_alt = self.context.quality_metrics
            qm_effective = qm if qm is not None else qm_alt
            if qm_effective is not None:
                brier_score_attr = getattr(qm_effective, "brier_score", None)
                if brier_score_attr is not None:
                    brier = round(float(brier_score_attr), 4)
                elif qm_effective.coherence > 0:
                    brier = round(1.0 - qm_effective.coherence, 4)
                else:
                    # Pas de signal qualité disponible → fallback Brier dérivé
                    # de l'écart-type des scores finaux (proxy raisonnable).
                    brier = self._brier_from_trajectory_dispersion()
            else:
                brier = self._brier_from_trajectory_dispersion()

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

    def _brier_from_trajectory_dispersion(self) -> float:
        """Proxy Brier dérivé de la dispersion des scores finaux.

        Si la simulation ne fournit pas de ``quality_metrics``, on utilise
        l'écart-type des scores au dernier round comme indicateur de
        fiabilité. Plus la dispersion est élevée, plus l'incertitude (et
        donc le Brier) est grande.

        Échelle : std ∈ [0, ~1] → Brier ∈ [0, ~0.5]. On clamp à [0, 1].
        Si la trajectoire est vide → renvoie 0.0 (au lieu de 1.0 qui
        suggérerait à tort une prédiction totalement fausse).
        """
        if self.context.trajectory is None or not self.context.trajectory.rounds:
            return 0.0
        last = self.context.trajectory.rounds[-1]
        scores = [a.score for a in last.agents if a.agent_id or a.name]
        if not scores:
            return 0.0
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std = variance ** 0.5
        # Mapping std → Brier sur [0, 0.5]
        brier = min(1.0, max(0.0, std * 0.5))
        return round(brier, 4)

    def _detect_pivotal_moments(self) -> None:
        """Scanne la trajectoire et détecte les bascules de score > SEUIL=0.20.

        Pour chaque agent, compare son score au round N avec son score au round N-1.
        Si la variation absolue dépasse ``_PIVOTAL_THRESHOLD``, un PivotalMoment est
        créé et ajouté à context.pivotal_moments.

        Améliorations bug B9 :
        - Résolution du nom lisible via ``agent_profiles`` + suffixe ID si nécessaire
        - Description d'événement contextualisée ("bascule positive ⟶ adhésion",
          "bascule négative ⟶ retrait") au lieu du libellé générique "bascule".

        La liste finale est triée par round ascendant.
        """
        if self.context.trajectory is None:
            return

        rounds = self.context.trajectory.rounds
        if len(rounds) < 2:
            return

        name_lookup = self._build_agent_name_lookup()

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
                        display_name = self._resolve_agent_display_name(
                            agent_state.name, agent_id, name_lookup
                        )
                        event_label = self._pivot_event_label(delta)
                        moments.append(
                            PivotalMoment(
                                round=rnd.round_idx,
                                agent=display_name,
                                event=event_label,
                                delta_score=round(delta, 4),
                            )
                        )
                        logger.debug(
                            "Pivotal moment détecté : round=%d agent=%r delta=%.4f",
                            rnd.round_idx,
                            display_name,
                            delta,
                        )

                prev_scores[agent_id] = current_score

        moments.sort(key=lambda m: m.round)
        self.context.pivotal_moments = moments

    def _build_agent_name_lookup(self) -> Dict[str, str]:
        """Construit un index ``agent_id → nom lisible`` depuis profiles + trajectory.

        Préférence : profile.name s'il est non vide, sinon le premier name
        rencontré dans la trajectoire pour cet agent_id.
        """
        lookup: Dict[str, str] = {}
        for profile in self.context.agent_profiles:
            if profile.name:
                # Les profiles n'ont pas d'agent_id explicite — on indexe par nom
                # pour permettre la résolution inverse via les états trajectoire
                # qui partagent ce même nom.
                lookup[profile.name] = profile.name

        if self.context.trajectory:
            for rnd in self.context.trajectory.rounds:
                for a in rnd.agents:
                    if a.agent_id and a.name and a.agent_id not in lookup:
                        lookup[a.agent_id] = a.name
        return lookup

    @staticmethod
    def _resolve_agent_display_name(
        name: str, agent_id: str, lookup: Dict[str, str]
    ) -> str:
        """Retourne un nom lisible : ``name`` si présent, sinon résolution via
        lookup, sinon agent_id préfixé d'un ``#`` pour signaler que c'est un ID.
        """
        if name and not name.isdigit() and len(name) > 2:
            # Cas idéal : déjà un vrai nom
            return name
        resolved = lookup.get(agent_id) or lookup.get(name)
        if resolved:
            return resolved
        if agent_id:
            return f"Agent #{agent_id}"
        return f"Agent #{name}" if name else "Agent anonyme"

    @staticmethod
    def _pivot_event_label(delta: float) -> str:
        """Étiquette descriptive d'une bascule selon son signe et son ampleur."""
        if delta >= 0.30:
            return "bascule forte ⟶ adhésion"
        if delta >= _PIVOTAL_THRESHOLD:
            return "bascule positive"
        if delta <= -0.30:
            return "bascule forte ⟶ retrait"
        if delta <= -_PIVOTAL_THRESHOLD:
            return "bascule négative"
        return "bascule"

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
        """Génère 3 takeaways C-level.

        Stratégie (US-135) :
        1. Si ``outline.executive_summary`` ou ``outline.takeaways`` existe
           (extension future du schéma), les utiliser directement.
        2. Sinon, générer via LLM avec prompt strict + sanitize.
        3. Sinon (LLM indisponible), fallback : découper ``outline.summary``
           en 3 phrases.

        Source : outline.summary + outcome.verdict + pivotal_moments.
        Cache : (verdict_hash, moments_hash, lang) — TTL 24h.
        Stocké dans context.executive_takeaways.
        """
        # — Priorité 1 : données déjà disponibles dans l'outline (extension future) —
        outline = self.context.outline
        if outline is not None:
            # Champs optionnels futurs (getattr pour ne pas casser si absents)
            outline_takeaways = getattr(outline, "takeaways", None)
            outline_exec_summary = getattr(outline, "executive_summary", None)

            if outline_takeaways and isinstance(outline_takeaways, list) and len(outline_takeaways) >= 3:
                self.context.executive_takeaways = [str(t) for t in outline_takeaways[:3]]
                logger.debug("Executive takeaways depuis outline.takeaways")
                return

            if outline_exec_summary and isinstance(outline_exec_summary, list) and len(outline_exec_summary) >= 3:
                self.context.executive_takeaways = [str(t) for t in outline_exec_summary[:3]]
                logger.debug("Executive takeaways depuis outline.executive_summary")
                return

        # — Priorité 2 : génération LLM avec cache —
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
            # cached est une string séparée par \n — on rehydrate
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

        if chart_id == "influence_posture_matrix":
            if ctx.trajectory and ctx.trajectory.rounds:
                # Compter agents par quadrant (champions / sceptiques bruyants /
                # adoptants discrets / indifférents) sur les 20 plus actifs
                agent_final: Dict[str, float] = {}
                agent_inf: Dict[str, float] = {}
                prev: Dict[str, float] = {}
                for rnd in ctx.trajectory.rounds:
                    for a in rnd.agents:
                        k = a.agent_id or a.name
                        if not k:
                            continue
                        if k in prev:
                            agent_inf[k] = agent_inf.get(k, 0.0) + abs(a.score - prev[k])
                        prev[k] = a.score
                        agent_final[k] = a.score
                if not agent_final:
                    return "Aucun agent."
                top = sorted(agent_inf.keys(), key=lambda k: agent_inf.get(k, 0), reverse=True)[:20]
                if not top:
                    return "Aucun agent influent."
                mean_inf = sum(agent_inf.get(k, 0) for k in top) / len(top)
                champ = sum(1 for k in top if agent_final.get(k, 0) >= 0 and agent_inf.get(k, 0) >= mean_inf)
                scept = sum(1 for k in top if agent_final.get(k, 0) <  0 and agent_inf.get(k, 0) >= mean_inf)
                disc  = sum(1 for k in top if agent_final.get(k, 0) >= 0 and agent_inf.get(k, 0) <  mean_inf)
                indif = len(top) - champ - scept - disc
                return (
                    f"Matrice 20 agents les + actifs : champions={champ}, "
                    f"sceptiques bruyants={scept}, adoptants discrets={disc}, "
                    f"indifférents={indif}."
                )
            return "Trajectoire absente."

        if chart_id == "stance_flow_sankey":
            if ctx.trajectory and ctx.trajectory.rounds:
                rounds = ctx.trajectory.rounds
                n = len(rounds)
                def _cnt(agents):
                    a = sum(1 for x in agents if x.score >  0.10)
                    r = sum(1 for x in agents if x.score < -0.10)
                    return a, r, len(agents) - a - r
                d_a, d_r, d_o = _cnt(rounds[0].agents)
                m_a, m_r, m_o = _cnt(rounds[n // 2].agents)
                f_a, f_r, f_o = _cnt(rounds[-1].agents)
                return (
                    f"Cinétique 3 jalons : Début (A={d_a}, R={d_r}, O={d_o}) "
                    f"→ Milieu (A={m_a}, R={m_r}, O={m_o}) "
                    f"→ Fin (A={f_a}, R={f_r}, O={f_o})."
                )
            return "Trajectoire absente."

        if chart_id == "agent_engagement_heatmap":
            if ctx.trajectory and ctx.trajectory.rounds:
                # Activité = somme |score| par agent
                activity: Dict[str, float] = {}
                for rnd in ctx.trajectory.rounds:
                    for a in rnd.agents:
                        k = a.agent_id or a.name
                        if k:
                            activity[k] = activity.get(k, 0.0) + abs(a.score)
                if not activity:
                    return "Aucun agent."
                top = sorted(activity.items(), key=lambda kv: kv[1], reverse=True)[:5]
                names = [k[:20] for k, _ in top]
                return f"Top 5 agents engagés (activité cumulée) : {', '.join(names)}."
            return "Trajectoire absente."

        return f"Chart {chart_id}: données non disponibles."

    def _call_llm_for_chart(self, chart_id: str, summary: str, lang: str) -> str:
        """Appelle le LLM pour générer une narrative de chart.

        Retourne _LLM_FALLBACK en cas d'erreur.
        Applique ``sanitize_llm_output`` sur la réponse avant retour (US-135).
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
            if not result:
                return _LLM_FALLBACK
            sanitized = sanitize_llm_output(result)
            return sanitized if sanitized else _LLM_FALLBACK
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
        Applique ``sanitize_llm_output`` sur chaque ligne (US-135).

        Si le LLM est indisponible et qu'un résumé outline est disponible,
        utilise ``outline.summary`` splitté en phrases comme fallback gracieux.
        """
        if self.llm is None:
            return self._fallback_takeaways_from_summary(summary)

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
                return self._fallback_takeaways_from_summary(summary)

            lines = [
                sanitize_llm_output(line.strip().lstrip("123. )-").strip())
                for line in result.strip().splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            # Filtre les lignes vides après sanitize
            lines = [l for l in lines if l]
            # Garde exactement 3 takeaways ; complète ou tronque si besoin
            while len(lines) < 3:
                lines.append(_LLM_FALLBACK)
            return lines[:3]

        except Exception as exc:
            logger.warning("LLM indisponible pour executive takeaways : %s", exc)
            return self._fallback_takeaways_from_summary(summary)

    def _fallback_takeaways_from_summary(self, summary: str) -> List[str]:
        """Fallback gracieux : 3 takeaways dérivés du verdict + de la trajectoire
        si le résumé outline est absent.

        Ordre de préférence :
        1. Extraction de phrases depuis ``outline.summary`` (3 premières).
        2. Sinon, takeaways synthétisés depuis l'outcome + pivots.
        3. Sinon, message générique unique (pas répété trois fois).
        """
        if summary and summary.strip():
            sentences = [
                s.strip()
                for s in re.split(r"[.!?;]+", summary)
                if s.strip() and len(s.strip()) > 10
            ]
            if len(sentences) >= 3:
                return sentences[:3]

        # Synthèse depuis l'outcome et la trajectoire (toujours dispos après
        # _synthesize_outcome_from_trajectory).
        ctx = self.context
        outcome = ctx.outcome
        synth: List[str] = []

        if outcome and outcome.verdict:
            synth.append(outcome.verdict)

        if outcome and outcome.nb_rounds:
            if outcome.bullish_pct > outcome.bearish_pct:
                tilt = f"Le camp positif domine la dernière étape ({outcome.bullish_pct:.0f} % contre {outcome.bearish_pct:.0f} %)."
            elif outcome.bearish_pct > outcome.bullish_pct:
                tilt = f"Le camp défensif l'emporte au dernier round ({outcome.bearish_pct:.0f} % contre {outcome.bullish_pct:.0f} %)."
            else:
                tilt = "Aucun camp ne s'impose clairement à l'issue de la simulation."
            synth.append(tilt)

        pivots = ctx.pivotal_moments
        if pivots:
            top_pivot = max(pivots, key=lambda p: abs(p.delta_score))
            synth.append(
                f"Bascule la plus marquante : {top_pivot.agent} au round {top_pivot.round} "
                f"(Δ {top_pivot.delta_score:+.2f})."
            )

        # Compléter si nécessaire avec un message unique non répété
        if not synth:
            return [
                _LLM_FALLBACK,
                "Les takeaways exécutifs nécessitent une analyse humaine complémentaire.",
                "Voir la section 4 « Dynamique observée » pour les détails par round.",
            ]
        while len(synth) < 3:
            # Petits compléments contextuels variés
            extras = [
                "Voir la section 4 « Dynamique observée » pour les détails par round.",
                "Les takeaways exécutifs gagneront en précision avec un LLM analytique connecté.",
                "Les recommandations C-Level se trouvent en section 6.",
            ]
            synth.append(extras[len(synth) - 1])
        return synth[:3]


# ─── Factory helper ───────────────────────────────────────────────────────────


def _safe_create_llm_client():
    """Retourne le client LLM par défaut. Retourne None si non configuré."""
    try:
        return create_llm_client()
    except Exception as exc:
        logger.warning("LLMClient non disponible (config manquante) : %s", exc)
        return None
