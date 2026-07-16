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
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schema import (
    AgentProfile,
    Counterfactual,
    Demographics,
    DirectorEvent,
    GeneratedArticle,
    Outline,
    Outcome,
    PDFReportContext,
    QualityMetrics,
    SimConfig,
    SimState,
    SocialNetwork,
    Trajectory,
)

logger = logging.getLogger(__name__)

# ─── Répertoires racines ──────────────────────────────────────────────────────
# Calculés à partir de l'emplacement de ce module pour être indépendants de
# l'état de l'application Flask (pas d'import de Config ici).
_THIS_DIR = Path(__file__).resolve().parent              # …/report_pdf/
_BACKEND_DIR = _THIS_DIR.parent.parent.parent            # backend/
# Aligné sur SimulationManager.SIMULATION_DATA_DIR qui résout à
# `backend/uploads/simulations/` via `../../uploads/simulations` depuis
# `backend/app/services/simulation_manager.py`. Pas de préfixe `app/`.
# Régression critique en prod corrigée 2026-05-06 (export-pdf US-133).
_UPLOADS_DIR = _BACKEND_DIR / "uploads"
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


def _normalize_sim_config(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalise les noms de champs de simulation_config.json vers le schéma canonique.

    Format production (SimulationConfigGenerator.to_dict()) :
        simulation_requirement  → title
        time_config.total_simulation_hours + time_config.minutes_per_round → dérivé
        source_documents / sources_docs / document_sources → sources

    Format schéma (fixtures tests) :
        title, sources, package, framework, lang — déjà corrects, pas de mapping.
    """
    normalized = dict(data)

    # ── title : priorité au champ canonique, fallback sur simulation_requirement ──
    if not normalized.get("title"):
        sim_req = normalized.get("simulation_requirement", "")
        if sim_req:
            normalized["title"] = str(sim_req)

    # ── sources : plusieurs noms de champs possibles en production ──
    if not normalized.get("sources"):
        for key in ("source_documents", "sources_docs", "document_sources", "documents"):
            val = normalized.get(key)
            if val and isinstance(val, list):
                normalized["sources"] = [str(s) for s in val if s]
                break

    # ── framework : peut être absent ou sous un alias ──
    if not normalized.get("framework"):
        normalized["framework"] = (
            normalized.get("scenario_framework")
            or normalized.get("analysis_framework")
            or "cerberus"
        )

    # ── lang : peut être absent ──
    if not normalized.get("lang"):
        normalized["lang"] = normalized.get("language") or "fr"

    # ── package : peut être sous 'package_id' ──
    if not normalized.get("package"):
        normalized["package"] = normalized.get("package_id") or ""

    return normalized


def _parse_sim_config(data: Optional[Any]) -> Optional[SimConfig]:
    """Adapte simulation_config.json → SimConfig (gère les deux formats : schema + production)."""
    if data is None:
        return None
    if not isinstance(data, dict):
        logger.warning("simulation_config.json n'est pas un objet JSON : %s", type(data))
        return None
    normalized = _normalize_sim_config(data)
    return SimConfig.model_validate(normalized)


def _normalize_sim_state(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalise les noms de champs de state.json vers le schéma canonique.

    Aliases observés en production :
        round / round_number / current_round_number → current_round
        agent_count / agents_count / num_agents    → profiles_count
        entity_count / num_entities                → entities_count
    """
    normalized = dict(data)

    # ── current_round : plusieurs aliases ──
    if "current_round" not in normalized or normalized["current_round"] == 0:
        for key in ("round", "round_number", "current_round_number", "last_round"):
            val = normalized.get(key)
            if val is not None:
                try:
                    as_int = int(val)
                    if as_int > 0:
                        normalized["current_round"] = as_int
                        break
                except (TypeError, ValueError):
                    pass

    # ── profiles_count : plusieurs aliases ──
    if not normalized.get("profiles_count"):
        for key in ("agent_count", "agents_count", "num_agents", "n_agents"):
            val = normalized.get(key)
            if val is not None:
                try:
                    normalized["profiles_count"] = int(val)
                    break
                except (TypeError, ValueError):
                    pass

    # ── entities_count : plusieurs aliases ──
    if not normalized.get("entities_count"):
        for key in ("entity_count", "num_entities", "n_entities"):
            val = normalized.get(key)
            if val is not None:
                try:
                    normalized["entities_count"] = int(val)
                    break
                except (TypeError, ValueError):
                    pass

    return normalized


def _parse_sim_state(data: Optional[Any]) -> Optional[SimState]:
    """Adapte state.json → SimState (gère les aliases de champs production)."""
    if data is None:
        return None
    if not isinstance(data, dict):
        logger.warning("state.json n'est pas un objet JSON : %s", type(data))
        return None
    normalized = _normalize_sim_state(data)
    return SimState.model_validate(normalized)


def _normalize_outcome(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalise les noms de champs de outcome.json vers le schéma canonique.

    Aliases observés en production :
        final_verdict / conclusion / summary_verdict → verdict
        bullish_percentage / pct_bullish / bull_pct   → bullish_pct
        bearish_percentage / pct_bearish / bear_pct   → bearish_pct
        recommendation_list / recommendation          → recommendations
        num_rounds / n_rounds / total_rounds          → nb_rounds
    """
    normalized = dict(data)

    # ── verdict ──
    if not normalized.get("verdict"):
        for key in ("final_verdict", "conclusion", "summary_verdict", "final_conclusion"):
            val = normalized.get(key)
            if val and isinstance(val, str):
                normalized["verdict"] = val
                break

    # ── bullish_pct ──
    if "bullish_pct" not in normalized:
        for key in ("bullish_percentage", "pct_bullish", "bull_pct", "bullish"):
            val = normalized.get(key)
            if val is not None:
                try:
                    normalized["bullish_pct"] = float(val)
                    break
                except (TypeError, ValueError):
                    pass

    # ── bearish_pct ──
    if "bearish_pct" not in normalized:
        for key in ("bearish_percentage", "pct_bearish", "bear_pct", "bearish"):
            val = normalized.get(key)
            if val is not None:
                try:
                    normalized["bearish_pct"] = float(val)
                    break
                except (TypeError, ValueError):
                    pass

    # ── recommendations ──
    if not normalized.get("recommendations"):
        for key in ("recommendation_list", "recommendation", "action_items", "actionable_recommendations"):
            val = normalized.get(key)
            if val:
                if isinstance(val, list):
                    normalized["recommendations"] = [str(r) for r in val if r]
                elif isinstance(val, str):
                    normalized["recommendations"] = [val]
                break

    # ── nb_rounds ──
    if not normalized.get("nb_rounds"):
        for key in ("num_rounds", "n_rounds", "total_rounds", "rounds_count"):
            val = normalized.get(key)
            if val is not None:
                try:
                    normalized["nb_rounds"] = int(val)
                    break
                except (TypeError, ValueError):
                    pass

    return normalized


def _parse_outcome(data: Optional[Any]) -> Optional[Outcome]:
    """Adapte outcome.json → Outcome (gère les aliases de champs production)."""
    if data is None:
        return None
    if not isinstance(data, dict):
        logger.warning("outcome.json n'est pas un objet JSON : %s", type(data))
        return None
    normalized = _normalize_outcome(data)
    return Outcome.model_validate(normalized)


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


def _normalize_trajectory(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalise trajectory.json vers le format canonique {rounds: [...]}.

    Format production (SimulationRunner) :
        {
            "snapshots": [
                {
                    "round_num": 1,
                    "belief_positions": {"AgentA": {"topic1": 0.6}, ...},
                    "agent_stances": {"AgentA": "bullish", ...}
                },
                ...
            ],
            "topics": ["topic1", ...]
        }

    Format schéma (fixtures tests) :
        {"rounds": [{"round_idx": 0, "agents": [...], "summary": "..."}, ...]}
    """
    # Déjà au format canonique — retourner tel quel
    if "rounds" in data and isinstance(data["rounds"], list):
        return data

    # Format production avec snapshots
    snapshots = data.get("snapshots") or []
    if not snapshots:
        return {"rounds": []}

    rounds = []
    for snap in snapshots:
        if not isinstance(snap, dict):
            continue
        round_num = snap.get("round_num") or snap.get("round_idx") or 0
        belief_positions = snap.get("belief_positions") or {}
        agent_stances_map = snap.get("agent_stances") or {}

        # Construire la liste d'AgentState depuis belief_positions ou agent_stances
        agents = []
        all_agent_names = set(belief_positions.keys()) | set(agent_stances_map.keys())
        for agent_name in sorted(all_agent_names):
            stance = agent_stances_map.get(agent_name, "neutral")
            # Score = moyenne des positions sur tous les topics
            positions = belief_positions.get(agent_name)
            score = 0.0
            if positions and isinstance(positions, dict):
                vals = [v for v in positions.values() if isinstance(v, (int, float))]
                if vals:
                    score = sum(vals) / len(vals)
            agents.append({
                "agent_id": agent_name,
                "name": agent_name,
                "stance": stance if stance else "neutral",
                "score": float(score),
                "message": "",
                "platform": "",
            })

        rounds.append({
            "round_idx": int(round_num),
            "agents": agents,
            "summary": snap.get("summary") or "",
        })

    return {"rounds": rounds}


def _parse_trajectory(data: Optional[Any]) -> Optional[Trajectory]:
    """Adapte trajectory.json → Trajectory (gère les formats production et schéma)."""
    if data is None:
        return None
    if not isinstance(data, dict):
        logger.warning("trajectory.json n'est pas un objet JSON : %s", type(data))
        return None
    normalized = _normalize_trajectory(data)
    return Trajectory.model_validate(normalized)


def _normalize_agent_profile(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalise un dict brut de profil agent vers le schéma AgentProfile canonique.

    Format production (reddit_profiles.json / agent_profiles.json) :
        realname / username / user_name → name
        persona (str ou dict avec .archetype) → archetype + description
        interested_topics → description (si pas d'autre description)
        profession → description
        platform déduit de la source

    Format schéma (fixtures tests) :
        name, archetype, biais, stance, platform, description — déjà corrects.
    """
    normalized = dict(item)

    # ── name : plusieurs aliases ──
    if not normalized.get("name"):
        for key in ("realname", "username", "user_name", "agent_name", "handle"):
            val = normalized.get(key)
            if val and isinstance(val, str):
                normalized["name"] = val
                break

    # ── archetype : peut être nested dans persona ──
    if not normalized.get("archetype"):
        persona = normalized.get("persona")
        if isinstance(persona, dict):
            arch = persona.get("archetype") or persona.get("type") or persona.get("role")
            if arch:
                normalized["archetype"] = str(arch)
        elif isinstance(persona, str) and persona:
            # persona est une chaîne libre → utiliser comme description si vide
            pass  # géré ci-dessous

    # ── stance : aliases ──
    if not normalized.get("stance") or normalized.get("stance") == "neutral":
        for key in ("initial_stance", "belief", "position"):
            val = normalized.get(key)
            if val and isinstance(val, str):
                normalized["stance"] = val
                break

    # ── platform : inféré depuis la clé source si absent ──
    if not normalized.get("platform"):
        # Déduit du champ 'source' ou 'type'
        src = normalized.get("source") or normalized.get("platform_type") or ""
        if src:
            normalized["platform"] = str(src)
        # Sinon laisser vide (le schéma accepte "")

    # ── description : assemblage depuis bio + profession + topics + persona ──
    if not normalized.get("description"):
        parts = []
        bio = normalized.get("bio", "")
        profession = normalized.get("profession", "")
        topics = normalized.get("interested_topics", [])
        persona = normalized.get("persona")

        if bio and isinstance(bio, str):
            parts.append(bio)
        if profession and isinstance(profession, str) and profession != "Unknown":
            parts.append(f"Profession : {profession}")
        if topics and isinstance(topics, list):
            parts.append(f"Sujets : {', '.join(str(t) for t in topics[:5])}")
        if not parts and isinstance(persona, str) and persona:
            parts.append(persona[:300])

        if parts:
            normalized["description"] = " — ".join(parts)

    # ── biais : peut être sous 'cognitive_biases' ou 'biases' ──
    if not normalized.get("biais"):
        for key in ("cognitive_biases", "biases", "bias"):
            val = normalized.get(key)
            if val:
                if isinstance(val, list):
                    normalized["biais"] = [str(b) for b in val if b]
                elif isinstance(val, str):
                    normalized["biais"] = [val]
                break

    return normalized


def _parse_agent_profiles(data: Any) -> List[AgentProfile]:
    """
    Adapte un artifact profiles → List[AgentProfile].

    Gère les deux formats :
    - Format schéma (fixtures) : champs canoniques directs
    - Format production : realname/username, persona.archetype, bio, profession, etc.

    Si le format n'est pas une liste, retourne une liste vide avec un warning.
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
            normalized = _normalize_agent_profile(item)
            profiles.append(AgentProfile.model_validate(normalized))
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


def _normalize_article_dict(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Normalise un dict brut d'article vers le schéma GeneratedArticle canonique.

    Format production (endpoint /generate-article) :
        {"article_text": "# Titre...\n\n_Dek_\n\nCorps...", "generated_at": "..."}

    Format schéma (fixtures tests) :
        {"agent_name": "...", "platform": "...", "round": 1, "title": "...",
         "content": "...", "stance": "..."}

    Retourne None si le dict est vide ou inutilisable.
    """
    if not item:
        return None

    normalized = dict(item)

    # ── Format production : article_text est un Markdown free-form ──
    article_text = normalized.get("article_text")
    if article_text and isinstance(article_text, str):
        # Extraire le titre : première ligne non vide
        lines = [ln.strip() for ln in article_text.splitlines() if ln.strip()]
        title_line = lines[0] if lines else ""
        # Supprimer le # Markdown si présent
        if title_line.startswith("#"):
            title_line = title_line.lstrip("#").strip()

        normalized.setdefault("title", title_line or "Article généré")
        normalized.setdefault("content", article_text)
        normalized.setdefault("agent_name", "")
        normalized.setdefault("platform", "")
        normalized.setdefault("round", 0)
        normalized.setdefault("stance", "")

    # ── Aliases champs canoniques ──
    if not normalized.get("content"):
        for key in ("body", "text", "article_body", "article_content"):
            val = normalized.get(key)
            if val and isinstance(val, str):
                normalized["content"] = val
                break

    if not normalized.get("title"):
        for key in ("headline", "article_title", "subject"):
            val = normalized.get(key)
            if val and isinstance(val, str):
                normalized["title"] = val
                break

    if not normalized.get("agent_name"):
        for key in ("author", "agent", "writer"):
            val = normalized.get(key)
            if val and isinstance(val, str):
                normalized["agent_name"] = val
                break

    # Si ni content ni title trouvés, l'article est inutilisable
    if not normalized.get("content") and not normalized.get("title"):
        return None

    return normalized


def _parse_generated_articles(data: Optional[Any]) -> List[GeneratedArticle]:
    """
    Adapte generated_article.json → List[GeneratedArticle].

    Gère les formats :
    - Format production : dict unique avec 'article_text' (texte Markdown libre)
    - Format schéma : list de dicts avec champs canoniques
    - Format mixte : list contenant des dicts production ou schéma
    """
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
            normalized = _normalize_article_dict(item)
            if normalized is None:
                continue
            articles.append(GeneratedArticle.model_validate(normalized))
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


def _extract_critical_posts(
    sim_dir: Path,
    root_actions_log: List[Dict[str, Any]],
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """
    Extrait les posts critiques (top N par score/engagement) depuis les actions.

    Sources lues dans l'ordre de priorité :
    1. {sim_dir}/{platform}/actions.jsonl  (format production — CREATE_POST)
    2. {sim_dir}/actions.jsonl             (format fixture/legacy — action ∈ {post, tweet, comment, message})

    Retourne une liste de dicts normalisés :
        {"round": int, "agent": str, "platform": str, "content": str, "score": float}
    triée par score décroissant, limitée à top_n.
    """
    posts: List[Dict[str, Any]] = []

    # ── Source 1 : sous-dossiers plateforme (format production) ──
    for platform_name in ("twitter", "reddit", "polymarket"):
        platform_actions_path = sim_dir / platform_name / "actions.jsonl"
        if platform_actions_path.is_file():
            records = _load_jsonl_file(platform_actions_path)
            post_map: Dict[str, Dict[str, Any]] = {}
            engagement_map: Dict[str, float] = {}

            for rec in records:
                if not isinstance(rec, dict):
                    continue
                atype = (rec.get("action_type") or "").upper()
                args = rec.get("action_args") or {}
                pid = args.get("post_id")

                if atype == "CREATE_POST" and pid is not None:
                    post_map[str(pid)] = {
                        "round": rec.get("round") or 0,
                        "agent": rec.get("agent_name") or "",
                        "platform": platform_name,
                        "content": (args.get("content") or "").strip(),
                        "score": 0.0,
                    }
                elif atype in ("LIKE_POST", "REPOST", "QUOTE_POST", "CREATE_COMMENT"):
                    if pid is not None:
                        weight = 3.0 if atype in ("REPOST", "QUOTE_POST") else (2.0 if atype == "CREATE_COMMENT" else 1.0)
                        engagement_map[str(pid)] = engagement_map.get(str(pid), 0.0) + weight

            for pid, post in post_map.items():
                post["score"] = engagement_map.get(pid, 0.0)
                if post["content"]:
                    posts.append(post)

    # ── Source 2 : actions.jsonl racine (format fixture/legacy) ──
    if not posts:
        action_types_post = {"post", "comment", "tweet", "message", "publish"}
        for rec in root_actions_log:
            if not isinstance(rec, dict):
                continue
            action = (rec.get("action") or rec.get("action_type") or "").lower()
            if action not in action_types_post:
                continue
            content = (
                rec.get("content")
                or rec.get("text")
                or rec.get("body")
                or (rec.get("action_args") or {}).get("content")
                or ""
            ).strip()
            if not content:
                continue
            agent = (
                rec.get("agent")
                or rec.get("agent_name")
                or rec.get("author")
                or ""
            )
            score = float(rec.get("score") or rec.get("upvotes") or rec.get("likes") or 0)
            posts.append({
                "round": rec.get("round") or 0,
                "agent": agent,
                "platform": rec.get("platform") or "",
                "content": content,
                "score": score,
            })

    # Tri par score décroissant + limitation
    posts.sort(key=lambda p: p["score"], reverse=True)
    return posts[:top_n]


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
        # US-221 : rematérialise depuis Supabase Storage si le volume local
        # (éphémère Coolify) a été vidé — un rapport doit rester générable.
        from ..artifact_storage import ensure_simulation_dir_hydrated
        ensure_simulation_dir_hydrated(simulation_id, str(sim_dir))
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

        # actions.jsonl — optionnel (racine, format legacy/fixtures)
        actions_log = _load_jsonl_file(sim_dir / "actions.jsonl")

        # Posts critiques — extraits depuis les actions (plateforme ou racine)
        critical_posts = _extract_critical_posts(
            sim_dir=sim_dir,
            root_actions_log=actions_log,
            top_n=10,
        )

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

        # Les posts critiques sont injectés dans agent_log avec un type distinctif
        # afin d'être disponibles pour le rendu sans modifier le schéma.
        # Le schéma PDFReportContext utilise extra="ignore" → les champs extras
        # sur les items agent_log sont transparents.
        if critical_posts:
            agent_log = list(agent_log)  # copie défensive
            agent_log.append({
                "_type": "critical_posts",
                "posts": critical_posts,
            })

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
