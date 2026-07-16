"""Persistance durable des artefacts de simulation (US-221, ADR-005).

``backend/uploads/simulations/<sim_id>/`` vit sur un volume Coolify
ÉPHÉMÈRE — tout redéploiement peut le vider. Ce module synchronise chaque
répertoire de simulation vers un bucket Supabase Storage privé
(``simulation-artifacts``) et permet de le RE-MATÉRIALISER localement si le
volume a été vidé.

Design "hydratation de répertoire" (pas un mapping fichier par fichier au
niveau applicatif) :
  - ``sync_directory_to_storage`` : à la fin de chaque phase (prepare, run,
    clôture), upload tous les fichiers du répertoire local vers Storage,
    indexe dans ``simulation_artifacts`` (table de métadonnées requêtable).
  - ``ensure_simulation_dir_hydrated`` : chokepoint appelé en tête de
    n'importe quel accès à un artefact de simulation. Si le répertoire local
    est absent/vide, le reconstruit intégralement depuis Storage à partir de
    ``simulation_artifacts`` (source de la liste des fichiers) — après quoi
    tout le code EXISTANT qui lit des fichiers sous ce répertoire continue
    de fonctionner sans modification.

Contrat de résilience : Supabase non configuré/injoignable → aucune
exception propagée, log + comportement filesystem pur (identique à avant
US-221). Le moteur de simulation ne doit jamais casser à cause du stockage
durable.
"""

from __future__ import annotations

import os
from typing import Any, List

from ..auth.supabase_client import SupabaseConfigError, get_supabase_admin
from ..utils.logger import get_logger

logger = get_logger("miroshark.services.artifact_storage")

BUCKET_ID = "simulation-artifacts"


def _storage_path(simulation_id: str, relative_path: str) -> str:
    return f"simulations/{simulation_id}/{relative_path}"


def sync_directory_to_storage(
    simulation_id: str, local_dir: str, client: Any = None,
) -> int:
    """Upload chaque fichier de ``local_dir`` vers Storage, indexe les métadonnées.

    Best-effort : une erreur sur un fichier individuel n'interrompt pas la
    synchronisation des autres (logué, compté à part). Ne lève jamais.

    Returns:
        Nombre de fichiers effectivement synchronisés (0 si Supabase
        indisponible ou répertoire absent — jamais d'exception).
    """
    if not os.path.isdir(local_dir):
        return 0

    try:
        cli = client or get_supabase_admin()
    except SupabaseConfigError:
        logger.debug("artifact_storage: Supabase non configuré — sync ignorée.")
        return 0

    bucket = cli.storage.from_(BUCKET_ID)
    synced = 0
    for root, _dirs, files in os.walk(local_dir):
        for filename in files:
            local_path = os.path.join(root, filename)
            relative_path = os.path.relpath(local_path, local_dir).replace(os.sep, "/")
            storage_path = _storage_path(simulation_id, relative_path)
            try:
                with open(local_path, "rb") as fh:
                    bucket.upload(storage_path, fh, file_options={"upsert": "true"})
                size_bytes = os.path.getsize(local_path)
                cli.table("simulation_artifacts").upsert(
                    {
                        "simulation_id": simulation_id,
                        "relative_path": relative_path,
                        "storage_path": storage_path,
                        "size_bytes": size_bytes,
                    },
                    on_conflict="simulation_id,relative_path",
                ).execute()
                synced += 1
            except Exception as exc:  # noqa: BLE001 — best-effort, un fichier ne bloque pas les autres
                logger.warning(
                    "artifact_storage: échec sync %s (%s) — %s",
                    relative_path, simulation_id, exc.__class__.__name__,
                )

    logger.info(
        "artifact_storage: %d fichier(s) synchronisé(s) pour %s.",
        synced, simulation_id,
    )
    return synced


def _list_artifacts(simulation_id: str, client: Any) -> List[dict]:
    response = (
        client.table("simulation_artifacts")
        .select("relative_path, storage_path")
        .eq("simulation_id", simulation_id)
        .execute()
    )
    return getattr(response, "data", None) or []


def is_durably_persisted(simulation_id: str, client: Any = None) -> bool:
    """True si au moins un artefact de cette simulation est indexé durablement."""
    try:
        cli = client or get_supabase_admin()
        return len(_list_artifacts(simulation_id, cli)) > 0
    except SupabaseConfigError:
        return False
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "artifact_storage: is_durably_persisted(%s) failed (%s).",
            simulation_id, exc.__class__.__name__,
        )
        return False


def ensure_simulation_dir_hydrated(
    simulation_id: str, local_dir: str, client: Any = None,
) -> bool:
    """Rematérialise ``local_dir`` depuis Storage si absent/vide.

    Appelé en tête de tout accès à un artefact de simulation (chokepoint
    unique — cf. docstring module). Si ``local_dir`` existe déjà avec du
    contenu, ne fait rien (cas nominal : volume Coolify pas encore vidé).

    Returns:
        True si le répertoire est disponible localement après l'appel
        (qu'il ait fallu l'hydrater ou non) ; False si l'hydratation était
        nécessaire mais a échoué (Supabase indisponible ET rien en local —
        le caller retombe sur son comportement 404 existant, inchangé).
    """
    if os.path.isdir(local_dir) and os.listdir(local_dir):
        return True

    try:
        cli = client or get_supabase_admin()
    except SupabaseConfigError:
        logger.debug(
            "artifact_storage: Supabase non configuré — pas d'hydratation possible pour %s.",
            simulation_id,
        )
        return os.path.isdir(local_dir)

    try:
        artifacts = _list_artifacts(simulation_id, cli)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "artifact_storage: liste des artefacts indisponible pour %s (%s).",
            simulation_id, exc.__class__.__name__,
        )
        return os.path.isdir(local_dir)

    if not artifacts:
        return os.path.isdir(local_dir)

    bucket = cli.storage.from_(BUCKET_ID)
    os.makedirs(local_dir, exist_ok=True)
    hydrated = 0
    for artifact in artifacts:
        relative_path = artifact.get("relative_path")
        storage_path = artifact.get("storage_path")
        if not relative_path or not storage_path:
            continue
        dest_path = os.path.join(local_dir, *relative_path.split("/"))
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            content = bucket.download(storage_path)
            with open(dest_path, "wb") as fh:
                fh.write(content)
            hydrated += 1
        except Exception as exc:  # noqa: BLE001 — un fichier manquant ne bloque pas les autres
            logger.warning(
                "artifact_storage: échec hydratation %s (%s) — %s",
                relative_path, simulation_id, exc.__class__.__name__,
            )

    logger.info(
        "artifact_storage: %d fichier(s) rematérialisé(s) depuis Storage pour %s.",
        hydrated, simulation_id,
    )
    return hydrated > 0
