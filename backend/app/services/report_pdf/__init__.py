"""
report_pdf — sous-package de génération de rapports PDF Bassira.

Modules :
    schema     — PDFReportContext (Pydantic v2) + tous les sub-models typés.
                 Source de vérité du contexte de rendu pour le pipeline PDF.
    loader     — PDFContextLoader : charge tous les artifacts disque dans un
                 PDFReportContext (US-119).
    jinja_env  — get_jinja_env() : Environment Jinja2 avec filter |normalize
                 et FileSystemLoader sur les templates pdf_report/ (US-123).
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
from .jinja_env import get_jinja_env, render_section, render_full_report

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
    # jinja_env
    "get_jinja_env",
    "render_section",
    "render_full_report",
]
