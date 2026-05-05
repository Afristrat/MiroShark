"""
PDFContextLoader — charge tous les artifacts simulation + report dans un PDFReportContext.

US-119 — Loader complet (charge tous les artifacts).

Ce module centralise la logique de lecture des fichiers disque et leur transformation
en sous-modèles Pydantic v2 conformes au schéma canonique défini dans ``schema.py``.

Stratégie :
    - Chaque artifact JSON/JSONL est chargé indépendamment.
    - ``extra="ignore"`` est actif sur tous les sub-models : les champs inconnus
      du fichier source sont silencieusement ignorés.
    - Fichier obligatoire absent → ``PDFContextLoaderError``.
    - Fichier optionnel absent → warning logger + champ None ou liste vide.
    - JSON malformé → ``PDFContextLoaderError`` avec le chemin et l'erreur brute.

Chemins disque (relatifs à ``backend/``) :
    Simulation : ``app/uploads/simulations/{simulation_id}/``
    Report     : ``app/uploads/reports/{report_id}/``

Usage :
    ctx = PDFContextLoader.load(
        simulation_id="sim_aabbcc112233",
        report_id="report_a1b2c3d4e5f6",
        lang="fr",
    )
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schema import (
    AgentProfile,
    Counterfactual,
    Demographics,
    DemographicSegment,
    DirectorEvent,
    GeneratedArticle,
    Outline,
    Outcome,
    PDFReportContext,
    QualityMetrics,
    Round,
    Section,
    SimConfig,
    SimState,
    SocialEdge,
    SocialNetwork,
    SocialNode,
    Trajectory,
)

logger = logging.getLogger(__name__)

# ─── Répertoires racines ──────────────────────────────────────────────────────
# Calculés à partir de l'emplacement de ce module pour être indépendants de
# l'état de l'application Flask (pas d'import de Config ici).
_THIS_DIR = Path(__file__).resolve().parent              # …/report_pdf/
_BACKEND_DIR = _THIS_DIR.parent.parent.parent            # …/backend/app/../.. = backend/
_UPLOADS_DIR = _BACKEND_DIR / "app" / "uploads"
_SIMULATIONS_DIR = _UPLOADS_DIR / "simulations"
_REPORTS_DIR = _UPLOADS_DIR / "reports"

# ─── Validation des identifiants ─────────────────────────────────────────────
_RE_SIMULATION_ID = re.compile(r"^sim_[a-f0-9]{12}$")
_RE_REPORT_ID = re.compile(r"^report_[a-f0-9]{12}$")


# ═══════════════════════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════════════════════


class PDFContextLoaderError(Exception):
    """Levée quand un artifact obligatoire est absent ou malformé."""


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers I/O internes
# ═══════════════════════════════════════════════════════════════════════════════


def _load_json_file(path: Path, required: bool = False) -> Optional[Any]:
    """
    Charge un fichier JSON depuis ``path``.

    Args:
        path:     Chemin absolu vers le fichier.
        required: Si True, lève ``PDFContextLoaderError`` si absent ou illisible.

    Returns:
        Le contenu parsé, ou None si le fichier est absent et ``required=False``.

    Raises:
        PDFContextLoaderError: Fichier requis absent ou JSON invalide.
    """
    if not path.is_file():
        if required:
            raise PDFContextLoaderError(
                f"Artifact obligatoire absent : {path}"
            )
        logger.warning("Artifact optionnel absent : %s", path)
        return None

    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise PDFContextLoaderError(
            f"JSON malformé dans {path} : {exc}"
        ) from exc
    except OSError as exc:
        raise PDFContextLoaderError(
            f"Impossible de lire {path} : {exc}"
        ) from exc


def _load_jsonl_file(path: Path) -> List[Dict[str, Any]]:
    """
    Charge un fichier JSONL (une entrée JSON par ligne).

    Lignes vides ou invalides sont ignorées avec un warning.

    Returns:
        Liste de dicts, potentiellement vide si le fichier est absent.
    """
    if not path.is_file():
        logger.warning("Artifact JSONL optionnel absent : %s", path)
        return []

    records: List[Dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    logger.warning(
                        "Ligne %d ignorée dans %s (JSON invalide) : %s",
                        lineno, path, exc,
                    )
    except OSError as exc:
        logger.warning("Impossible de lire %s : %s", path, exc)

    return records


def _load_text_file(path: Path) -> Optional[str]:
    """
    Charge le contenu brut d'un fichier texte.

    Returns:
        Contenu en string, ou None si le fichier est absent.
    """
    if not path.is_file():
        logger.warning("Artifact texte optionnel absent : %s", path)
        return None

    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        logger.warning("Impossible de lire %s : %s", path, exc)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Adaptateurs artifact → sub-model
# ═══════════════════════════════════════════════════════════════════════════════


def _parse_sim_config(data: Optional[Any]) -> Optional[SimConfig]:
    """Adapte simulation_config.json → SimConfig."""
    if data is None:
        return None
    if not isinstance(data, dict):
        logger.warning("simulation_config.json n'est pas un objet JSON : %s", type(data))
        return None
    return SimConfig.model_validate(data)


def _parse_sim_state(data: Optional[Any]) -> Optional[SimState]:
    """Adapte state.json → SimState."""
    if data is None:
        return None
    if not isinstance(data, dict):
        logger.warning("state.json n'est pas un objet JSON : %s", type(data))
        return None
    return SimState.model_validate(data)


def _parse_outcome(data: Optional[Any]) -> Optional[Outcome]:
    """Adapte outcome.json → Outcome (avec QualityMetrics imbriqué)."""
    if data is None:
        return None
    if not isinstance(data, dict):
        logger.warning("outcome.json n'est pas un objet JSON : %s", type(data))
        return None
    return Outcome.model_validate(data)


def _parse_quality_metrics(outcome_data: Optional[Any]) -> Optional[QualityMetrics]:
    """Extrait quality_metrics depuis le dict outcome brut."""
    if not isinstance(outcome_data, dict):
        return None
    qm = outcome_data.get("quality_metrics")
    if qm is None:
        return None
    if not isinstance(qm, dict):
        return None
    return QualityMetrics.model_validate(qm)


def _parse_trajectory(data: Optional[Any]) -> Optional[Trajectory]:
    """Adapte trajectory.json → Trajectory (List[Round])."""
    if data is None:
        return None
    if not isinstance(data, dict):
        logger.warning("trajectory.json n'est pas un objet JSON : %s", type(data))
        return None
    return Trajectory.model_validate(data)


def _parse_agent_profiles(data: Any) -> List[AgentProfile]:
    """
    Adapte un artifact profiles → List[AgentProfile].

    Le format attendu est une liste de dicts. Si ce n'est pas le cas,
    retourne une liste vide avec un warning.
    """
    if data is None:
        return []
    if not isinstance(data, list):
        logger.warning(
            "Le fichier profiles n'est pas une liste JSON (type=%s) — ignoré.",
            type(data),
        )
        return []
    profiles: List[AgentProfile] = []
    for item in data:
        if not isinstance(item, dict):
            logger.warning("Entrée profiles non-dict ignorée : %s", item)
            continue
        try:
            profiles.append(AgentProfile.model_validate(item))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Profil ignoré (validation échouée) : %s — %s", item, exc)
    return profiles


def _parse_twitter_csv(path: Path) -> List[AgentProfile]:
    """
    Charge twitter_profiles.csv et l'adapte en List[AgentProfile].

    Colonnes attendues (toutes optionnelles sauf éventuellement 'name') :
        name, archetype, biais, stance, platform, description
    """
    if not path.is_file():
        return []
    profiles: List[AgentProfile] = []
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if not isinstance(row, dict):
                    continue
                # biais peut être une colonne CSV contenant une liste sérialisée
                biais_raw = row.get("biais", "")
                if isinstance(biais_raw, str) and biais_raw:
                    biais = [b.strip() for b in biais_raw.split(",") if b.strip()]
                else:
                    biais = []
                try:
                    profiles.append(AgentProfile(
                        name=row.get("name", ""),
                        archetype=row.get("archetype", ""),
                        biais=biais,
                        stance=row.get("stance", "neutral"),
                        platform=row.get("platform", "twitter"),
                        description=row.get("description", ""),
                    ))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Profil CSV ignoré : %s — %s", row, exc)
    except OSError as exc:
        logger.warning("Impossible de lire %s : %s", path, exc)
    return profiles


def _load_agent_profiles_with_fallback(sim_dir: Path) -> List[AgentProfile]:
    """
    Charge les profils agents selon la chaîne de fallback :
      1. agent_profiles.json
      2. reddit_profiles.json
      3. twitter_profiles.csv
      4. polymarket_profiles.json

    Retourne les profils du premier fichier trouvé et non-vide.
    """
    # 1. agent_profiles.json
    data = _load_json_file(sim_dir / "agent_profiles.json")
    if data is not None:
        profiles = _parse_agent_profiles(data)
        if profiles:
            logger.debug("Profils chargés depuis agent_profiles.json (%d)", len(profiles))
            return profiles

    # 2. reddit_profiles.json
    data = _load_json_file(sim_dir / "reddit_profiles.json")
    if data is not None:
        profiles = _parse_agent_profiles(data)
        if profiles:
            logger.debug("Profils chargés depuis reddit_profiles.json (%d)", len(profiles))
            return profiles

    # 3. twitter_profiles.csv
    profiles = _parse_twitter_csv(sim_dir / "twitter_profiles.csv")
    if profiles:
        logger.debug("Profils chargés depuis twitter_profiles.csv (%d)", len(profiles))
        return profiles

    # 4. polymarket_profiles.json
    data = _load_json_file(sim_dir / "polymarket_profiles.json")
    if data is not None:
        profiles = _parse_agent_profiles(data)
        if profiles:
            logger.debug("Profils chargés depuis polymarket_profiles.json (%d)", len(profiles))
            return profiles

    logger.warning(
        "Aucun fichier de profils trouvé dans %s — agent_profiles sera vide.", sim_dir
    )
    return []


def _parse_social_network(data: Optional[Any]) -> Optional[SocialNetwork]:
    """Adapte network.json → SocialNetwork."""
    if data is None:
        return None
    if not isinstance(data, dict):
        logger.warning("network.json n'est pas un objet JSON : %s", type(data))
        return None
    return SocialNetwork.model_validate(data)


def _parse_demographics(data: Optional[Any]) -> Optional[Demographics]:
    """Adapte demographics.json → Demographics."""
    if data is None:
        return None
    if not isinstance(data, dict):
        logger.warning("demographics.json n'est pas un objet JSON : %s", type(data))
        return None
    return Demographics.model_validate(data)


def _parse_counterfactuals(data: Optional[Any]) -> List[Counterfactual]:
    """
    Adapte counterfactual_injection.json → List[Counterfactual].

    Le fichier peut contenir soit un objet unique (dict) soit une liste.
    """
    if data is None:
        return []
    if isinstance(data, dict):
        try:
            return [Counterfactual.model_validate(data)]
        except Exception as exc:  # noqa: BLE001
            logger.warning("counterfactual ignoré (validation échouée) : %s", exc)
            return []
    if isinstance(data, list):
        result = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                result.append(Counterfactual.model_validate(item))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Counterfactual item ignoré : %s — %s", item, exc)
        return result
    logger.warning(
        "counterfactual_injection.json format inattendu (type=%s) — ignoré.", type(data)
    )
    return []


def _parse_generated_articles(data: Optional[Any]) -> List[GeneratedArticle]:
    """Adapte generated_article.json → List[GeneratedArticle]."""
    if data is None:
        return []
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        logger.warning(
            "generated_article.json format inattendu (type=%s) — ignoré.", type(data)
        )
        return []
    articles = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            articles.append(GeneratedArticle.model_validate(item))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Article ignoré (validation échouée) : %s — %s", item, exc)
    return articles


def _parse_outline(data: Optional[Any], required: bool = False) -> Optional[Outline]:
    """Adapte outline.json → Outline."""
    if data is None:
        if required:
            raise PDFContextLoaderError(
                "outline.json est requis quand report_id est fourni mais le fichier est absent."
            )
        return None
    if not isinstance(data, dict):
        logger.warning("outline.json n'est pas un objet JSON : %s", type(data))
        return None
    return Outline.model_validate(data)


def _load_sections_md(rep_dir: Path) -> Dict[int, str]:
    """
    Charge tous les fichiers section_NN.md dans rep_dir.

    Returns:
        Dict idx (int) → contenu markdown (str).
    """
    sections: Dict[int, str] = {}
    if not rep_dir.is_dir():
        return sections
    pattern = re.compile(r"^section_(\d{2})\.md$")
    for entry in sorted(rep_dir.iterdir()):
        match = pattern.match(entry.name)
        if match:
            idx = int(match.group(1))
            content = _load_text_file(entry)
            if content is not None:
                sections[idx] = content
    return sections


# ═══════════════════════════════════════════════════════════════════════════════
# Classe principale
# ═══════════════════════════════════════════════════════════════════════════════


class PDFContextLoader:
    """
    Charge tous les artifacts d'une simulation (et optionnellement d'un rapport)
    dans un PDFReportContext fortement typé.

    Usage simple :

        ctx = PDFContextLoader.load(
            simulation_id="sim_aabbcc112233",
            report_id="report_a1b2c3d4e5f6",
            lang="fr",
        )

    Usage sans rapport (simulation seule) :

        ctx = PDFContextLoader.load(simulation_id="sim_aabbcc112233")

    Paramètres répertoires personnalisables (utiles pour les tests) :

        ctx = PDFContextLoader.load(
            simulation_id="sim_aabbcc112233",
            sim_base_dir=Path("/path/to/simulations"),
            rep_base_dir=Path("/path/to/reports"),
        )
    """

    @classmethod
    def load(
        cls,
        simulation_id: str,
        report_id: Optional[str] = None,
        lang: str = "fr",
        *,
        sim_base_dir: Optional[Path] = None,
        rep_base_dir: Optional[Path] = None,
    ) -> PDFReportContext:
        """
        Charge tous les artifacts et retourne un PDFReportContext complet.

        Args:
            simulation_id:  Identifiant de la simulation (format sim_<12hex>).
            report_id:      Identifiant du rapport (format report_<12hex>).
                            Si None, un report_id synthétique est généré et
                            les données report ne sont pas chargées.
            lang:           Langue du rendu {fr, en, ar}. Défaut : 'fr'.
            sim_base_dir:   Répertoire racine des simulations (override de défaut).
            rep_base_dir:   Répertoire racine des rapports (override de défaut).

        Returns:
            PDFReportContext valide.

        Raises:
            PDFContextLoaderError: simulation_config.json absent, ou outline.json
                                   absent quand report_id est fourni.
            PDFContextLoaderError: JSON malformé dans un artifact.
        """
        # ── Résolution des répertoires ─────────────────────────────────────
        sim_dir = (sim_base_dir or _SIMULATIONS_DIR) / simulation_id
        rep_dir: Optional[Path] = None
        if report_id is not None:
            rep_dir = (rep_base_dir or _REPORTS_DIR) / report_id

        # ── Génère un report_id si non fourni ─────────────────────────────
        effective_report_id: str
        if report_id is not None:
            effective_report_id = report_id
        else:
            effective_report_id = f"report_{uuid.uuid4().hex[:12]}"

        # ─────────────────────────────────────────────────────────────────────
        # SIMULATION artifacts
        # ─────────────────────────────────────────────────────────────────────

        # simulation_config.json — OBLIGATOIRE
        config_data = _load_json_file(
            sim_dir / "simulation_config.json", required=True
        )
        sim_config = _parse_sim_config(config_data)

        # state.json — optionnel
        state_data = _load_json_file(sim_dir / "state.json")
        sim_state = _parse_sim_state(state_data)

        # outcome.json — optionnel
        outcome_data = _load_json_file(sim_dir / "outcome.json")
        outcome = _parse_outcome(outcome_data)
        quality_metrics = _parse_quality_metrics(outcome_data)

        # trajectory.json — optionnel
        trajectory_data = _load_json_file(sim_dir / "trajectory.json")
        trajectory = _parse_trajectory(trajectory_data)

        # Profils agents — fallback chain : agent_profiles → reddit → twitter csv → polymarket
        agent_profiles = _load_agent_profiles_with_fallback(sim_dir)

        # network.json — optionnel
        network_data = _load_json_file(sim_dir / "network.json")
        social_network = _parse_social_network(network_data)

        # demographics.json — optionnel
        demo_data = _load_json_file(sim_dir / "demographics.json")
        demographics = _parse_demographics(demo_data)

        # counterfactual_injection.json — optionnel
        cf_data = _load_json_file(sim_dir / "counterfactual_injection.json")
        counterfactuals = _parse_counterfactuals(cf_data)

        # generated_article.json — optionnel
        articles_data = _load_json_file(sim_dir / "generated_article.json")
        articles = _parse_generated_articles(articles_data)

        # actions.jsonl — optionnel (stocké brut dans action_log)
        actions_log = _load_jsonl_file(sim_dir / "actions.jsonl")

        # events.jsonl — optionnel (stocké brut dans director_events bruts)
        events_raw = _load_jsonl_file(sim_dir / "events.jsonl")
        # On mappe les events bruts en DirectorEvent si possible
        director_events = []
        for ev in events_raw:
            if isinstance(ev, dict):
                try:
                    director_events.append(
                        DirectorEvent.model_validate(ev)
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("DirectorEvent ignoré : %s — %s", ev, exc)

        # ─────────────────────────────────────────────────────────────────────
        # REPORT artifacts (si report_id fourni)
        # ─────────────────────────────────────────────────────────────────────
        outline: Optional[Outline] = None
        full_report_md: Optional[str] = None
        sections_md: Dict[int, str] = {}
        agent_log: List[Dict[str, Any]] = []

        if rep_dir is not None:
            # outline.json — OBLIGATOIRE si report_id fourni
            outline_data = _load_json_file(rep_dir / "outline.json")
            if outline_data is None:
                raise PDFContextLoaderError(
                    f"outline.json obligatoire absent dans le dossier rapport : {rep_dir}"
                )
            outline = _parse_outline(outline_data)

            # full_report.md — optionnel
            full_report_md = _load_text_file(rep_dir / "full_report.md")

            # section_NN.md — optionnel
            sections_md = _load_sections_md(rep_dir)

            # agent_log.jsonl — optionnel
            agent_log = _load_jsonl_file(rep_dir / "agent_log.jsonl")

        # ─────────────────────────────────────────────────────────────────────
        # Dériver les champs identité depuis sim_config
        # ─────────────────────────────────────────────────────────────────────
        title = (sim_config.title if sim_config else "") or ""
        framework = (sim_config.framework if sim_config else "cerberus") or "cerberus"
        package = (sim_config.package if sim_config else "") or ""

        # La lang passée en paramètre prime sur celle du sim_config
        effective_lang = lang

        # ─────────────────────────────────────────────────────────────────────
        # Assemblage du PDFReportContext
        # ─────────────────────────────────────────────────────────────────────
        ctx = PDFReportContext(
            report_id=effective_report_id,
            simulation_id=simulation_id,
            title=title,
            framework=framework,
            package=package,
            lang=effective_lang,
            # Simulation
            sim_config=sim_config,
            sim_state=sim_state,
            outcome=outcome,
            quality_metrics=quality_metrics,
            trajectory=trajectory,
            agent_profiles=agent_profiles,
            social_network=social_network,
            demographics=demographics,
            counterfactuals=counterfactuals,
            director_events=director_events,
            articles=articles,
            # Report
            outline=outline,
            full_report_md=full_report_md,
            sections_md=sections_md,
            agent_log=agent_log,
        )
        return ctx
