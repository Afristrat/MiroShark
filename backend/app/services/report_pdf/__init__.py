"""
report_pdf — sous-package de génération de rapports PDF Bassira.

Modules :
    schema  — PDFReportContext (Pydantic v2) + tous les sub-models typés.
              Source de vérité du contexte de rendu pour le pipeline PDF.
    loader  — PDFContextLoader : charge tous les artifacts disque dans un
              PDFReportContext (US-119).
"""

from .schema import (
    PDFReportContext,
    SimConfig,
    SimState,
    Outcome,
    QualityMetrics,
    Round,
    AgentState,
    Trajectory,
    AgentProfile,
    SocialNode,
    SocialEdge,
    SocialNetwork,
    DemographicSegment,
    Demographics,
    Counterfactual,
    DirectorEvent,
    GeneratedArticle,
    AgentInterview,
    Section,
    Outline,
    KPIHero,
    PivotalMoment,
)
from .loader import PDFContextLoader, PDFContextLoaderError

__all__ = [
    # schema
    "PDFReportContext",
    "SimConfig",
    "SimState",
    "Outcome",
    "QualityMetrics",
    "Round",
    "AgentState",
    "Trajectory",
    "AgentProfile",
    "SocialNode",
    "SocialEdge",
    "SocialNetwork",
    "DemographicSegment",
    "Demographics",
    "Counterfactual",
    "DirectorEvent",
    "GeneratedArticle",
    "AgentInterview",
    "Section",
    "Outline",
    "KPIHero",
    "PivotalMoment",
    # loader
    "PDFContextLoader",
    "PDFContextLoaderError",
]
