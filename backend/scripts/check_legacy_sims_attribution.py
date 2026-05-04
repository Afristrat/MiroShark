#!/usr/bin/env python3
"""
US-101 — Inventaire des simulations filesystem pré-multitenant.

Ce script lit le dossier ``backend/uploads/simulations/`` et liste toutes
les simulations présentes sur disque (dossiers ``sim_*``) avec leurs
métadonnées exploitables pour la rétro-attribution Supabase :

    - simulation_id (= nom du dossier)
    - created_at    (= mtime ISO 8601 du dossier)
    - package_id    (= ``template_id`` ou ``package_id`` de
                       ``simulation_config.json`` si présent, sinon ``None``)
    - outcome       (= contenu de ``outcome.json`` si présent, sinon ``None``)
    - brier_score   (= ``brier_score`` extrait de ``outcome.json`` si présent)

Modes d'exécution
─────────────────

1. **list** (défaut) — affiche un tableau lisible des sims trouvées.
2. **sql**            — émet directement les ``VALUES (...)`` à coller
                        dans la migration SQL US-101 (à exécuter sur le
                        serveur prod où vivent les vrais dossiers, pas
                        sur la machine de dev d'Amine qui n'a que des
                        sims placeholders).

Le script ne fait QUE de la lecture filesystem — aucune dépendance
Supabase, aucune écriture. Il sert post-migration à vérifier
manuellement que toutes les sims listées ici sont bien présentes dans
``public.simulation_ownership``.

Usage
─────

    # Inventaire lisible
    cd backend && uv run python scripts/check_legacy_sims_attribution.py

    # Génération des VALUES SQL (à coller dans la migration)
    cd backend && uv run python scripts/check_legacy_sims_attribution.py --sql

    # Pointer vers un autre dossier (ex. snapshot prod copié en local)
    cd backend && uv run python scripts/check_legacy_sims_attribution.py \
        --root /path/to/snapshot/uploads/simulations
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


DEFAULT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "uploads", "simulations")
)


@dataclass
class LegacySim:
    simulation_id: str
    created_at_iso: str
    package_id: Optional[str]
    outcome: Optional[Dict[str, Any]]
    brier_score: Optional[float]

    def sql_value_row(self) -> str:
        """Retourne la ligne ``VALUES (...)`` SQL prête à coller.

        Les ``None`` deviennent ``null``, les chaînes sont quotées et
        échappées (apostrophes doublées), le JSON outcome est passé via
        un cast ``::jsonb``.
        """

        def q(s: Optional[str]) -> str:
            if s is None:
                return "null"
            return "'" + str(s).replace("'", "''") + "'"

        if self.outcome is None:
            outcome_sql = "null"
        else:
            payload = json.dumps(self.outcome, ensure_ascii=False, sort_keys=True)
            outcome_sql = q(payload) + "::jsonb"

        brier_sql = "null" if self.brier_score is None else str(self.brier_score)

        return (
            f"  ({q(self.simulation_id)}, "
            f"(select id from target_org), "
            f"{q(self.created_at_iso)}::timestamptz, "
            f"{q(self.package_id)}, "
            f"false, "
            f"{outcome_sql}, "
            f"{brier_sql})"
        )


def _read_json_safely(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
        return None
    except (OSError, json.JSONDecodeError):
        return None


def _extract_package_id(config: Optional[Dict[str, Any]]) -> Optional[str]:
    if not config:
        return None
    for key in ("template_id", "package_id"):
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _mtime_to_iso(path: str) -> str:
    ts = os.path.getmtime(path)
    return (
        datetime.fromtimestamp(ts, tz=timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def discover_legacy_sims(root: str = DEFAULT_ROOT) -> List[LegacySim]:
    """Liste les sims filesystem dans ``root``.

    Ignore les dossiers ne commençant pas par ``sim_`` ainsi que les
    fichiers cachés (``.DS_Store``, etc.).
    """
    if not os.path.isdir(root):
        return []

    sims: List[LegacySim] = []
    for name in sorted(os.listdir(root)):
        if not name.startswith("sim_"):
            continue
        sim_dir = os.path.join(root, name)
        if not os.path.isdir(sim_dir):
            continue

        config = _read_json_safely(os.path.join(sim_dir, "simulation_config.json"))
        package_id = _extract_package_id(config)

        outcome = _read_json_safely(os.path.join(sim_dir, "outcome.json"))
        brier: Optional[float] = None
        if outcome and isinstance(outcome.get("brier_score"), (int, float)):
            brier = float(outcome["brier_score"])

        sims.append(
            LegacySim(
                simulation_id=name,
                created_at_iso=_mtime_to_iso(sim_dir),
                package_id=package_id,
                outcome=outcome,
                brier_score=brier,
            )
        )

    return sims


def emit_list(sims: List[LegacySim]) -> str:
    if not sims:
        return "(aucune simulation filesystem trouvée — rien à rétro-attribuer)"

    lines = [
        f"{len(sims)} simulation(s) filesystem trouvée(s) :",
        "",
        f"  {'simulation_id':<22}  {'created_at':<22}  {'package_id':<24}  outcome  brier",
        f"  {'-'*22}  {'-'*22}  {'-'*24}  -------  -----",
    ]
    for s in sims:
        pkg = s.package_id or "—"
        out = "yes" if s.outcome else "no"
        brier = f"{s.brier_score:.4f}" if s.brier_score is not None else "—"
        lines.append(
            f"  {s.simulation_id:<22}  {s.created_at_iso:<22}  {pkg:<24}  {out:<7}  {brier}"
        )
    return "\n".join(lines)


def emit_sql(sims: List[LegacySim]) -> str:
    if not sims:
        return (
            "-- (aucune simulation filesystem trouvée — la section VALUES "
            "reste vide, voir commentaire 'no sims to backfill' dans la migration)"
        )
    return ",\n".join(s.sql_value_row() for s in sims)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventaire des sims filesystem pré-multitenant (US-101).",
    )
    parser.add_argument(
        "--root",
        default=DEFAULT_ROOT,
        help=f"Racine des sims filesystem (défaut : {DEFAULT_ROOT})",
    )
    parser.add_argument(
        "--sql",
        action="store_true",
        help="Émet les VALUES SQL prêts à coller dans la migration "
        "20260504_002_backfill_legacy_sims.sql",
    )
    args = parser.parse_args()

    sims = discover_legacy_sims(args.root)

    if args.sql:
        print(emit_sql(sims))
    else:
        print(emit_list(sims))

    return 0


if __name__ == "__main__":
    sys.exit(main())
