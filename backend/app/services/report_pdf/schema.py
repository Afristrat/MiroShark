"""
PDFReportContext — schéma Pydantic v2 exhaustif pour le rendu PDF Bassira.

Ce module constitue la source de vérité du contexte passé au pipeline de
génération PDF. Il mappe l'ensemble des 20+ artifacts produits par la
simulation (state.json, outcome.json, trajectory.json, profiles.json,
agent_log.jsonl, etc.) et les données report (outline, markdown_content,
sections) dans un objet unique fortement typé.

Sous-models et leurs sources artifact :
    SimConfig        ← simulation_config.json (titre, package, framework…)
    SimState         ← state.json (status, current_round, profiles_count…)
    Outcome          ← outcome.json (verdict, confidence, recommendations…)
    QualityMetrics   ← outcome.json > quality_metrics
    Round            ← trajectory.json > rounds[i]
    AgentState       ← trajectory.json > rounds[i].agents[j]
    Trajectory       ← trajectory.json (liste de Round)
    AgentProfile     ← profiles.json (archetype, biais, stance, platform)
    SocialNode       ← social_network.json > nodes
    SocialEdge       ← social_network.json > edges
    SocialNetwork    ← social_network.json
    DemographicSegment ← demographics.json > segments
    Demographics     ← demographics.json
    Counterfactual   ← counterfactual.json (injection what-if)
    DirectorEvent    ← director_events.jsonl / director_log
    GeneratedArticle ← actions.jsonl (articles générés par les agents)
    AgentInterview   ← interviews.jsonl (chain of thought par agent)
    Section          ← report > outline.sections[i]
    Outline          ← report > outline (title + summary + sections)
    KPIHero          ← dérivé de outcome.json (KPI carte hero PDF)
    PivotalMoment    ← dérivé de trajectory (moments pivots identifiés)
    PDFReportContext ← objet racine assemblant tous les sub-models
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# ─── Regexes de validation des identifiants ──────────────────────────────────
# Formats générés dans simulation_manager.py et report_agent.py :
#   simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
#   report_id     = f"report_{uuid.uuid4().hex[:12]}"
_RE_SIMULATION_ID = re.compile(r"^sim_[a-f0-9]{12}$")
_RE_REPORT_ID = re.compile(r"^report_[a-f0-9]{12}$")

# ─── Littéraux métier ─────────────────────────────────────────────────────────
FrameworkLiteral = Literal["cerberus", "market", "crisis", "policy", "decision"]
LangLiteral = Literal["fr", "en", "ar"]


# ═══════════════════════════════════════════════════════════════════════════════
# Sub-models — configuration & état simulation
# ═══════════════════════════════════════════════════════════════════════════════


class SimConfig(BaseModel):
    """
    Configuration d'une simulation.

    Source : simulation_config.json (généré par SimulationConfigGenerator).

    Champs :
        title         — titre humain de la simulation (simulation_requirement)
        package       — slug du package commandé (ex. 'crisis-drill-24h')
        framework     — cadre analytique parmi {cerberus, market, crisis, policy, decision}
        lang          — langue du rendu {fr, en, ar}
        sources       — liste des sources documentaires utilisées (titres ou URLs)
        params        — paramètres bruts transmis au script Wonderwall (dict libre)
    """

    title: str = Field(default="", description="Titre / simulation_requirement.")
    package: str = Field(default="", description="Slug du package commandé.")
    framework: FrameworkLiteral = Field(
        default="cerberus",
        description="Cadre analytique parmi {cerberus, market, crisis, policy, decision}.",
    )
    lang: LangLiteral = Field(
        default="fr",
        description="Langue du rendu {fr, en, ar}.",
    )
    sources: List[str] = Field(
        default_factory=list,
        description="Sources documentaires utilisées (titres ou URLs).",
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Paramètres bruts transmis au script Wonderwall.",
    )


class SimState(BaseModel):
    """
    État d'exécution d'une simulation au moment de la génération du rapport.

    Source : state.json (SimulationState.to_dict()).

    Champs :
        status          — statut runtime ('completed', 'running', etc.)
        current_round   — numéro du dernier round exécuté
        profiles_count  — nombre de profils agents générés
        entities_count  — nombre d'entités Neo4j extraites
        entity_types    — liste des types d'entités présents dans le graphe
    """

    status: str = Field(default="completed", description="Statut runtime de la simulation.")
    current_round: int = Field(default=0, ge=0, description="Dernier round exécuté.")
    profiles_count: int = Field(default=0, ge=0, description="Nombre de profils agents.")
    entities_count: int = Field(default=0, ge=0, description="Nombre d'entités Neo4j.")
    entity_types: List[str] = Field(
        default_factory=list,
        description="Types d'entités présents dans le graphe.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Sub-models — outcome & métriques qualité
# ═══════════════════════════════════════════════════════════════════════════════


class QualityMetrics(BaseModel):
    """
    Métriques de qualité de la simulation.

    Source : outcome.json > quality_metrics.

    Champs :
        coherence     — cohérence interne du scénario [0.0, 1.0]
        diversity     — diversité des opinions agents [0.0, 1.0]
        plausibility  — plausibilité des dynamiques [0.0, 1.0]
        alignment     — alignement avec les données sources [0.0, 1.0]
    """

    coherence: float = Field(default=0.0, ge=0.0, le=1.0)
    diversity: float = Field(default=0.0, ge=0.0, le=1.0)
    plausibility: float = Field(default=0.0, ge=0.0, le=1.0)
    alignment: float = Field(default=0.0, ge=0.0, le=1.0)


class Outcome(BaseModel):
    """
    Verdict de simulation et métriques synthétiques.

    Source : outcome.json.

    Champs :
        verdict             — conclusion principale de la simulation
        bullish_pct         — pourcentage d'agents « bullish » à la fin [0, 100]
        bearish_pct         — pourcentage d'agents « bearish » à la fin [0, 100]
        nb_rounds           — nombre de rounds exécutés
        recommendations     — liste de recommandations actionables
        confidence          — score de confiance global [0.0, 1.0]
        quality_metrics     — métriques qualité (sous-objet QualityMetrics)
        scenario_winner     — agent/camp ayant convergé en position dominante
        consensus_reached   — si un consensus a été atteint
    """

    verdict: str = Field(default="", description="Conclusion principale.")
    bullish_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    bearish_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    nb_rounds: int = Field(default=0, ge=0)
    recommendations: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    quality_metrics: QualityMetrics = Field(default_factory=QualityMetrics)
    scenario_winner: Optional[str] = Field(default=None)
    consensus_reached: bool = Field(default=False)


# ═══════════════════════════════════════════════════════════════════════════════
# Sub-models — trajectoire
# ═══════════════════════════════════════════════════════════════════════════════


class AgentState(BaseModel):
    """
    État d'un agent à un round donné.

    Source : trajectory.json > rounds[i].agents[j].

    Champs :
        agent_id    — identifiant unique de l'agent
        name        — nom lisible de l'agent
        stance      — position courante (ex. 'bullish', 'bearish', 'neutral')
        score       — score de conviction numérique
        message     — dernier message publié par l'agent
        platform    — plateforme d'expression ('twitter', 'reddit', …)
    """

    agent_id: str = Field(default="", description="Identifiant unique de l'agent.")
    name: str = Field(default="", description="Nom lisible.")
    stance: str = Field(default="neutral", description="Position courante.")
    score: float = Field(default=0.0, description="Score de conviction.")
    message: str = Field(default="", description="Dernier message publié.")
    platform: str = Field(default="", description="Plateforme d'expression.")


class Round(BaseModel):
    """
    Un round de simulation.

    Source : trajectory.json > rounds[i].

    Champs :
        round_idx   — numéro du round (0-indexé)
        agents      — liste des états agents à ce round
        summary     — résumé synthétique du round (optionnel)
    """

    round_idx: int = Field(default=0, ge=0)
    agents: List[AgentState] = Field(default_factory=list)
    summary: str = Field(default="")


class Trajectory(BaseModel):
    """
    Trajectoire complète de la simulation (tous les rounds).

    Source : trajectory.json.

    Champs :
        rounds   — liste ordonnée de Round (round_idx croissant)
    """

    rounds: List[Round] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# Sub-models — profils agents
# ═══════════════════════════════════════════════════════════════════════════════


class AgentProfile(BaseModel):
    """
    Profil Wonderwall d'un agent simulé.

    Source : profiles.json (WonderwallProfileGenerator).

    Champs :
        name        — nom de l'agent
        archetype   — archétype Cerberus/Market/… (ex. 'Challenger', 'Bull')
        biais       — liste de biais cognitifs déclarés
        stance      — position initiale de l'agent
        platform    — plateforme principale de l'agent
        description — description narrative de l'agent
    """

    name: str = Field(default="")
    archetype: str = Field(default="")
    biais: List[str] = Field(default_factory=list, description="Biais cognitifs déclarés.")
    stance: str = Field(default="neutral")
    platform: str = Field(default="")
    description: str = Field(default="")


# ═══════════════════════════════════════════════════════════════════════════════
# Sub-models — réseau social
# ═══════════════════════════════════════════════════════════════════════════════


class SocialNode(BaseModel):
    """
    Nœud du réseau social d'interactions agents.

    Source : social_network.json > nodes.

    Champs :
        id          — identifiant unique du nœud
        name        — nom lisible de l'agent
        group       — groupe/camp de l'agent
        weight      — poids du nœud (influence relative)
    """

    id: str = Field(default="")
    name: str = Field(default="")
    group: str = Field(default="")
    weight: float = Field(default=1.0, ge=0.0)


class SocialEdge(BaseModel):
    """
    Arête du réseau social (interaction entre deux agents).

    Source : social_network.json > edges.

    Champs :
        source      — id du nœud source
        target      — id du nœud cible
        weight      — poids de l'interaction (fréquence ou intensité)
        sentiment   — sentiment de l'interaction ('positive', 'negative', 'neutral')
    """

    source: str = Field(default="")
    target: str = Field(default="")
    weight: float = Field(default=1.0, ge=0.0)
    sentiment: str = Field(default="neutral")


class SocialNetwork(BaseModel):
    """
    Réseau social d'interactions entre agents.

    Source : social_network.json.

    Champs :
        nodes   — liste des nœuds (agents)
        edges   — liste des arêtes (interactions)
    """

    nodes: List[SocialNode] = Field(default_factory=list)
    edges: List[SocialEdge] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# Sub-models — démographie
# ═══════════════════════════════════════════════════════════════════════════════


class DemographicSegment(BaseModel):
    """
    Segment démographique d'agents simulés.

    Source : demographics.json > segments.

    Champs :
        label       — libellé du segment (ex. '18-24 ans', 'Femmes', 'Casablanca')
        count       — nombre d'agents dans ce segment
        pct         — pourcentage [0.0, 100.0]
        dimension   — dimension démographique ('genre', 'age', 'geo', …)
    """

    label: str = Field(default="")
    count: int = Field(default=0, ge=0)
    pct: float = Field(default=0.0, ge=0.0, le=100.0)
    dimension: str = Field(default="")


class Demographics(BaseModel):
    """
    Données démographiques de la population simulée.

    Source : demographics.json.

    Champs :
        segments    — liste des segments par genre/âge/géo
        total       — nombre total d'agents simulés
    """

    segments: List[DemographicSegment] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)


# ═══════════════════════════════════════════════════════════════════════════════
# Sub-models — injection what-if & événements directeur
# ═══════════════════════════════════════════════════════════════════════════════


class Counterfactual(BaseModel):
    """
    Scénario contrefactuel (injection what-if).

    Source : counterfactual.json.

    Champs :
        hypothesis      — hypothèse contrefactuelle injectée
        round_injected  — round auquel l'injection a eu lieu
        delta_verdict   — différence de verdict observée vs baseline
        delta_confidence — différence de confiance [−1.0, 1.0]
        notes           — notes narratives sur l'impact observé
    """

    hypothesis: str = Field(default="")
    round_injected: int = Field(default=0, ge=0)
    delta_verdict: str = Field(default="")
    delta_confidence: float = Field(default=0.0, ge=-1.0, le=1.0)
    notes: str = Field(default="")


class DirectorEvent(BaseModel):
    """
    Événement exogène injecté par le directeur de simulation.

    Source : director_events.jsonl / director_log.

    Champs :
        round       — round auquel l'événement a été injecté
        event_type  — type d'événement ('shock', 'news', 'rumor', …)
        description — description de l'événement
        impact      — impact estimé sur la trajectoire
    """

    round: int = Field(default=0, ge=0)
    event_type: str = Field(default="")
    description: str = Field(default="")
    impact: str = Field(default="")


# ═══════════════════════════════════════════════════════════════════════════════
# Sub-models — contenus générés & interviews
# ═══════════════════════════════════════════════════════════════════════════════


class GeneratedArticle(BaseModel):
    """
    Article généré par un agent simulé pendant la simulation.

    Source : actions.jsonl (actions de type 'article' ou 'publish').

    Champs :
        agent_name  — nom de l'agent auteur
        platform    — plateforme de publication
        round       — round de publication
        title       — titre de l'article
        content     — contenu de l'article
        stance      — position exprimée dans l'article
    """

    agent_name: str = Field(default="")
    platform: str = Field(default="")
    round: int = Field(default=0, ge=0)
    title: str = Field(default="")
    content: str = Field(default="")
    stance: str = Field(default="")


class AgentInterview(BaseModel):
    """
    Chain of thought d'un agent (interview narrative post-simulation).

    Source : interviews.jsonl.

    Champs :
        agent_name      — nom de l'agent interviewé
        archetype       — archétype de l'agent
        questions       — liste de questions posées à l'agent
        answers         — liste de réponses correspondantes
        final_stance    — position finale de l'agent
    """

    agent_name: str = Field(default="")
    archetype: str = Field(default="")
    questions: List[str] = Field(default_factory=list)
    answers: List[str] = Field(default_factory=list)
    final_stance: str = Field(default="")


# ═══════════════════════════════════════════════════════════════════════════════
# Sub-models — outline du rapport
# ═══════════════════════════════════════════════════════════════════════════════


class Section(BaseModel):
    """
    Section d'un rapport.

    Source : report > outline.sections[i].

    Champs :
        idx         — index 0-basé de la section
        title       — titre de la section
        content     — contenu markdown de la section
    """

    idx: int = Field(default=0, ge=0)
    title: str = Field(default="")
    content: str = Field(default="")


class Outline(BaseModel):
    """
    Plan structuré du rapport.

    Source : report > outline (ReportOutline.to_dict()).

    Champs :
        title       — titre principal du rapport
        summary     — résumé exécutif (chapeau)
        sections    — liste ordonnée de Section
    """

    title: str = Field(default="")
    summary: str = Field(default="")
    sections: List[Section] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# Sub-models — KPI hero & moments pivots
# ═══════════════════════════════════════════════════════════════════════════════


class KPIHero(BaseModel):
    """
    KPI carte héro du rapport PDF (page de couverture).

    Source : dérivé de outcome.json.

    Champs :
        verdict             — verdict principal (phrase courte)
        confidence_pct      — confiance en pourcentage [0, 100]
        brier               — score de Brier [0.0, 1.0] (0 = parfait)
        scenario_distribution — répartition des agents par camp {str: float}
    """

    verdict: str = Field(default="")
    confidence_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    brier: float = Field(default=0.0, ge=0.0, le=1.0)
    scenario_distribution: Dict[str, float] = Field(default_factory=dict)


class PivotalMoment(BaseModel):
    """
    Moment pivot identifié dans la trajectoire de simulation.

    Source : dérivé de trajectory.json (analyse post-run).

    Champs :
        round       — numéro du round du moment pivot
        agent       — agent déclencheur
        event       — description de l'événement pivot
        delta_score — variation de score de consensus induite
    """

    round: int = Field(default=0, ge=0)
    agent: str = Field(default="")
    event: str = Field(default="")
    delta_score: float = Field(default=0.0)


class ScoredRecommendation(BaseModel):
    """
    Recommandation stratégique scorée sur 4 frameworks de négociation.

    Source : dérivée de l'analyse trajectory + outcome par l'enricher (L99 v2).
    Si l'outcome ne produit pas de recommandations, l'enricher synthétise 3 pistes
    contextualisées (artefact reproductible / segmentation / découplage incitatif)
    et les score selon ZOPA / BATNA / MESO / WATNA.

    Champs :
        title             — intitulé court de la piste
        action            — description de l'action principale à engager
        owner             — owner pressenti (rôle, pas nom de personne)
        horizon           — horizon de déploiement (court / moyen / long terme)
        kpi_primary       — KPI primaire de suivi
        risk              — risque principal et mitigation
        zopa              — score ZOPA [0, 10]
        zopa_rationale    — justification courte du score ZOPA
        batna             — score BATNA [0, 10]
        batna_rationale   — justification courte du score BATNA
        meso              — score MESO [0, 10]
        meso_rationale    — justification courte du score MESO
        watna             — score WATNA [0, 10]
        watna_rationale   — justification courte du score WATNA
        composite         — moyenne pondérée des 4 scores [0, 10]
        composite_note    — note synthétique sur le score composite
    """

    title: str = Field(default="")
    action: str = Field(default="")
    owner: str = Field(default="")
    horizon: str = Field(default="")
    kpi_primary: str = Field(default="")
    risk: str = Field(default="")
    zopa: float = Field(default=0.0, ge=0.0, le=10.0)
    zopa_rationale: str = Field(default="")
    batna: float = Field(default=0.0, ge=0.0, le=10.0)
    batna_rationale: str = Field(default="")
    meso: float = Field(default=0.0, ge=0.0, le=10.0)
    meso_rationale: str = Field(default="")
    watna: float = Field(default=0.0, ge=0.0, le=10.0)
    watna_rationale: str = Field(default="")
    composite: float = Field(default=0.0, ge=0.0, le=10.0)
    composite_note: str = Field(default="")


# ═══════════════════════════════════════════════════════════════════════════════
# Objet racine — PDFReportContext
# ═══════════════════════════════════════════════════════════════════════════════


class PDFReportContext(BaseModel):
    """
    Contexte complet de rendu PDF pour un rapport Bassira.

    Cet objet est instancié par le pipeline PDF juste avant le rendu WeasyPrint
    ou ReportLab. Il centralise tous les artifacts simulation + report dans un
    objet fortement typé, serializable JSON (model_dump_json / model_validate_json).

    ── Identité ──────────────────────────────────────────────────────────────
        report_id       — identifiant du rapport  (format: report_<12hex>)
        simulation_id   — identifiant de la sim   (format: sim_<12hex>)
        title           — titre principal du rapport
        framework       — cadre analytique {cerberus, market, crisis, policy, decision}
        package         — slug du package commandé
        lang            — langue du rendu {fr, en, ar}

    ── Config & état simulation ──────────────────────────────────────────────
        sim_config      — SimConfig (simulation_config.json)
        sim_state       — SimState (state.json)
        outcome         — Outcome (outcome.json)
        quality_metrics — QualityMetrics (outcome.json > quality_metrics)
        trajectory      — Trajectory (trajectory.json)
        agent_profiles  — List[AgentProfile] (profiles.json)
        social_network  — SocialNetwork (social_network.json)
        demographics    — Demographics (demographics.json)
        counterfactuals — List[Counterfactual] (counterfactual.json)
        director_events — List[DirectorEvent] (director_events.jsonl)
        articles        — List[GeneratedArticle] (actions.jsonl)
        interviews      — List[AgentInterview] (interviews.jsonl)

    ── Données report ────────────────────────────────────────────────────────
        outline         — Outline (ReportOutline.to_dict())
        full_report_md  — markdown complet assemblé
        sections_md     — dict idx → markdown d'une section
        agent_log       — entrées brutes de agent_log.jsonl

    ── Données dérivées ──────────────────────────────────────────────────────
        kpi_hero            — KPIHero (dérivé de outcome)
        pivotal_moments     — List[PivotalMoment] (dérivé de trajectory)
        interpretations     — dict clé → interprétation narrative
        executive_takeaways — liste de takeaways exécutifs
    """

    # ── Identité ──────────────────────────────────────────────────────────────
    report_id: str = Field(
        description="Identifiant unique du rapport (format report_<12hex>).",
    )
    simulation_id: str = Field(
        description="Identifiant unique de la simulation (format sim_<12hex>).",
    )
    title: str = Field(default="", description="Titre principal du rapport.")
    framework: FrameworkLiteral = Field(
        default="cerberus",
        description="Cadre analytique {cerberus, market, crisis, policy, decision}.",
    )
    package: str = Field(default="", description="Slug du package commandé.")
    lang: LangLiteral = Field(
        default="fr",
        description="Langue du rendu {fr, en, ar}.",
    )

    # ── Config & état simulation ──────────────────────────────────────────────
    sim_config: Optional[SimConfig] = Field(
        default=None,
        description="Configuration de la simulation (simulation_config.json).",
    )
    sim_state: Optional[SimState] = Field(
        default=None,
        description="État d'exécution de la simulation (state.json).",
    )
    outcome: Optional[Outcome] = Field(
        default=None,
        description="Verdict et métriques de la simulation (outcome.json).",
    )
    quality_metrics: Optional[QualityMetrics] = Field(
        default=None,
        description="Métriques qualité (outcome.json > quality_metrics).",
    )
    trajectory: Optional[Trajectory] = Field(
        default=None,
        description="Trajectoire complète par rounds (trajectory.json).",
    )
    agent_profiles: List[AgentProfile] = Field(
        default_factory=list,
        description="Profils Wonderwall des agents (profiles.json).",
    )
    social_network: Optional[SocialNetwork] = Field(
        default=None,
        description="Réseau social d'interactions (social_network.json).",
    )
    demographics: Optional[Demographics] = Field(
        default=None,
        description="Données démographiques de la population (demographics.json).",
    )
    counterfactuals: List[Counterfactual] = Field(
        default_factory=list,
        description="Scénarios contrefactuels injectés (counterfactual.json).",
    )
    director_events: List[DirectorEvent] = Field(
        default_factory=list,
        description="Événements exogènes du directeur (director_events.jsonl).",
    )
    articles: List[GeneratedArticle] = Field(
        default_factory=list,
        description="Articles générés par les agents (actions.jsonl).",
    )
    interviews: List[AgentInterview] = Field(
        default_factory=list,
        description="Interviews chain-of-thought des agents (interviews.jsonl).",
    )

    # ── Données report ────────────────────────────────────────────────────────
    outline: Optional[Outline] = Field(
        default=None,
        description="Plan structuré du rapport (ReportOutline).",
    )
    full_report_md: Optional[str] = Field(
        default=None,
        description="Markdown complet assemblé du rapport.",
    )
    sections_md: Dict[int, str] = Field(
        default_factory=dict,
        description="Dict idx → markdown d'une section individuelle.",
    )
    agent_log: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Entrées brutes de agent_log.jsonl.",
    )

    # ── Données dérivées ──────────────────────────────────────────────────────
    kpi_hero: Optional[KPIHero] = Field(
        default=None,
        description="KPI carte héro (dérivé de outcome).",
    )
    pivotal_moments: List[PivotalMoment] = Field(
        default_factory=list,
        description="Moments pivots identifiés dans la trajectoire.",
    )
    interpretations: Dict[str, str] = Field(
        default_factory=dict,
        description="Dict clé → interprétation narrative (ex. 'consensus', 'polarisation').",
    )
    executive_takeaways: List[str] = Field(
        default_factory=list,
        description="Liste de takeaways exécutifs pour la page de couverture.",
    )
    scored_recommendations: List[ScoredRecommendation] = Field(
        default_factory=list,
        description="Recommandations C-Level scorées ZOPA/BATNA/MESO/WATNA (L99 v2).",
    )

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("report_id")
    @classmethod
    def validate_report_id(cls, v: str) -> str:
        """Valide le format report_<12hex>."""
        if not _RE_REPORT_ID.match(v):
            raise ValueError(
                f"report_id invalide : '{v}'. Format attendu : report_<12 caractères hexadécimaux>."
            )
        return v

    @field_validator("simulation_id")
    @classmethod
    def validate_simulation_id(cls, v: str) -> str:
        """Valide le format sim_<12hex>."""
        if not _RE_SIMULATION_ID.match(v):
            raise ValueError(
                f"simulation_id invalide : '{v}'. Format attendu : sim_<12 caractères hexadécimaux>."
            )
        return v

    @field_validator("lang")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        """Valide que lang est dans {fr, en, ar}."""
        # Pydantic Literal gère déjà ce cas ; ce validator ajoute un message
        # d'erreur explicitement francophone pour les logs Bassira.
        allowed = {"fr", "en", "ar"}
        if v not in allowed:
            raise ValueError(
                f"lang invalide : '{v}'. Valeurs autorisées : {sorted(allowed)}."
            )
        return v

    @field_validator("framework")
    @classmethod
    def validate_framework(cls, v: str) -> str:
        """Valide que framework est dans {cerberus, market, crisis, policy, decision}."""
        allowed = {"cerberus", "market", "crisis", "policy", "decision"}
        if v not in allowed:
            raise ValueError(
                f"framework invalide : '{v}'. Valeurs autorisées : {sorted(allowed)}."
            )
        return v

    model_config = {
        # Autorise les champs extra pour absorber des clés inconnues
        # provenant d'anciens artifacts sans planter la validation.
        "extra": "ignore",
        # Valide les assignments après construction (utile pour les mises à jour
        # partielles lors de l'assemblage progressif du contexte PDF).
        "validate_assignment": True,
    }
