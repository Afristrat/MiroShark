"""Internal admin analytics endpoint (US-065).

Exposes ``GET /api/admin/analytics`` — a single aggregate read
that powers the founders/operators dashboard at ``/admin/analytics``
on the SPA. The dashboard's audience is the Bassira team itself
(Amine + co-operators), and the goal is "read the platform state in
30 seconds". So the endpoint computes everything in one pass:

  * **KPIs** — total simulations on disk, completed (``outcome.json``
    present), completed in the last 30 days, and total persisted
    quote requests (``WONDERWALL_DATA_DIR/quotes/quote_*.json``).
  * **Funnel** — coarse acquisition → activation → completion shape
    derived from the same disk inputs (visits is reported as ``null``
    until we wire a real analytics provider; the dashboard renders
    "—" rather than fabricating a number).
  * **30-day time series** — daily ``completed`` count keyed by the
    ``mtime`` of each ``outcome.json``. Sparse on a fresh deploy,
    which is the desired behaviour (the chart should be honest).
  * **Top packages** — top 5 ``template_id`` values across every
    simulation that carries one in ``simulation_config.json``.

Auth: gated on ``BASSIRA_ADMIN_TOKEN`` via the shared
``require_admin_token`` decorator from ``app.api.simulation`` —
same fail-closed semantics as ``POST /publish`` / ``POST /resolve``
/ ``POST /outcome``. Internal-only by design; never expose to
unauthenticated clients.

Robustness contract: when the data dirs are missing (fresh install,
test env without ``uploads/``), every counter/list resolves to
``0`` / ``[]`` rather than raising. A 500 here would brick the
ops dashboard, which is exactly when we *most* want a signal.
"""

from __future__ import annotations

import json
import os
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, jsonify

from ..config import Config
from ..utils.logger import get_logger

from .simulation import require_admin_token


admin_bp = Blueprint("admin", __name__)
logger = get_logger("miroshark.api.admin")


# ─── Path helpers ────────────────────────────────────────────────────────────


def _simulations_dir() -> str:
    """Return the directory containing per-simulation subfolders.

    Resolved per-call so a test that monkeypatches ``Config`` after
    module import still sees the override.
    """
    return getattr(Config, "WONDERWALL_SIMULATION_DATA_DIR", "") or ""


def _quotes_dir() -> str:
    """Return the directory where quote payloads are persisted.

    Mirrors the resolution logic in ``app.services.quote_service`` so
    a deployment that sets ``WONDERWALL_DATA_DIR`` (sibling
    ``quotes/``) and one that only sets the simulation dir both work
    out of the box.
    """
    base_dir = getattr(Config, "WONDERWALL_DATA_DIR", None)
    if not base_dir:
        sim_dir = _simulations_dir()
        if sim_dir:
            base_dir = os.path.dirname(sim_dir)
    if not base_dir:
        return ""
    return os.path.join(base_dir, "quotes")


# ─── Disk scans (defensive — never raise) ────────────────────────────────────


def _list_simulation_dirs() -> List[str]:
    """Return absolute paths to every simulation subdirectory.

    A simulation is any direct subdir of
    ``WONDERWALL_SIMULATION_DATA_DIR``. Hidden / dotfile entries are
    skipped so a stray ``.DS_Store`` does not inflate the count.
    """
    sims_root = _simulations_dir()
    if not sims_root or not os.path.isdir(sims_root):
        return []
    out: List[str] = []
    try:
        for name in os.listdir(sims_root):
            if name.startswith("."):
                continue
            path = os.path.join(sims_root, name)
            if os.path.isdir(path):
                out.append(path)
    except OSError as exc:
        logger.warning("Could not scan simulations dir %s: %s", sims_root, exc)
    return out


def _outcome_mtime(sim_dir: str) -> Optional[float]:
    """Return the ``mtime`` of ``<sim_dir>/outcome.json`` or ``None``."""
    path = os.path.join(sim_dir, "outcome.json")
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def _read_template_id(sim_dir: str) -> Optional[str]:
    """Return the ``template_id`` from ``simulation_config.json``.

    Defensive: parse failures or missing keys resolve to ``None`` so a
    single corrupt file does not poison the aggregation.
    """
    cfg_path = os.path.join(sim_dir, "simulation_config.json")
    if not os.path.isfile(cfg_path):
        return None
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f) or {}
    except (OSError, json.JSONDecodeError):
        return None
    tid = cfg.get("template_id")
    if not isinstance(tid, str):
        return None
    tid = tid.strip()
    return tid or None


def _count_quotes() -> int:
    """Count ``quote_*.json`` files persisted under the quotes dir."""
    qdir = _quotes_dir()
    if not qdir or not os.path.isdir(qdir):
        return 0
    n = 0
    try:
        for name in os.listdir(qdir):
            if name.startswith("quote_") and name.endswith(".json"):
                n += 1
    except OSError as exc:
        logger.warning("Could not scan quotes dir %s: %s", qdir, exc)
    return n


# ─── Aggregation ─────────────────────────────────────────────────────────────


def _build_time_series_30d(completed_mtimes: List[float]) -> List[Dict[str, Any]]:
    """Return a 30-element list ``[{date: YYYY-MM-DD, completed: n}, …]``.

    Always 30 entries (one per day, oldest → today) so the frontend can
    render a stable bar chart even when no completions exist that day.
    Dates are computed in UTC to keep the series deterministic across
    operator timezones.
    """
    today = datetime.now(timezone.utc).date()
    bucket: Dict[str, int] = {}
    cutoff = time.time() - 30 * 86400
    for mtime in completed_mtimes:
        if mtime < cutoff:
            continue
        day = datetime.fromtimestamp(mtime, tz=timezone.utc).date().isoformat()
        bucket[day] = bucket.get(day, 0) + 1
    series: List[Dict[str, Any]] = []
    for offset in range(29, -1, -1):
        day = (today.fromordinal(today.toordinal() - offset)).isoformat()
        series.append({"date": day, "completed": int(bucket.get(day, 0))})
    return series


def _build_top_packages(sim_dirs: List[str], limit: int = 5) -> List[Dict[str, Any]]:
    """Aggregate ``template_id`` across every simulation, top ``limit``."""
    counter: Counter = Counter()
    for sd in sim_dirs:
        tid = _read_template_id(sd)
        if tid:
            counter[tid] += 1
    return [{"package": pkg, "n": n} for pkg, n in counter.most_common(limit)]


def _build_kpis(
    sim_dirs: List[str],
    completed_mtimes: List[float],
    quotes_count: int,
) -> Dict[str, int]:
    """Compute the four headline numbers shown in the KPI row."""
    cutoff = time.time() - 30 * 86400
    last_30d = sum(1 for m in completed_mtimes if m >= cutoff)
    return {
        "total": len(sim_dirs),
        "completed": len(completed_mtimes),
        "last_30d": last_30d,
        "quotes": quotes_count,
    }


def _build_funnel(kpis: Dict[str, int]) -> List[Dict[str, Any]]:
    """Render the canonical 4-step funnel.

    ``visits`` is intentionally ``None`` until a real analytics provider
    is wired (we refuse to invent a number). The frontend renders
    ``null`` as "—" so the gap is visible to the operator.
    """
    return [
        {"step": "visits", "n": None},
        {"step": "simulations", "n": kpis["total"]},
        {"step": "completed", "n": kpis["completed"]},
        {"step": "quotes", "n": kpis["quotes"]},
    ]


# ─── Route ───────────────────────────────────────────────────────────────────


@admin_bp.route("/analytics", methods=["GET"])
@require_admin_token
def get_admin_analytics():
    """Return the aggregate analytics payload for the ops dashboard.

    Response shape (always ``data`` populated, never ``null``)::

        {
          "success": true,
          "data": {
            "kpis": {"total": N, "completed": N, "last_30d": N, "quotes": N},
            "funnel": [{"step": "visits", "n": null|N}, …],
            "time_series": [{"date": "YYYY-MM-DD", "completed": N}, … (30)],
            "top_packages": [{"package": "<id>", "n": N}, … (≤5)]
          }
        }

    Never raises 500 from a missing dir — fresh installs render zero,
    and that is a valid (and correct) state.
    """
    try:
        sim_dirs = _list_simulation_dirs()
        completed_mtimes: List[float] = []
        for sd in sim_dirs:
            mtime = _outcome_mtime(sd)
            if mtime is not None:
                completed_mtimes.append(mtime)

        quotes_count = _count_quotes()
        kpis = _build_kpis(sim_dirs, completed_mtimes, quotes_count)
        funnel = _build_funnel(kpis)
        time_series = _build_time_series_30d(completed_mtimes)
        top_packages = _build_top_packages(sim_dirs)

        return jsonify({
            "success": True,
            "data": {
                "kpis": kpis,
                "funnel": funnel,
                "time_series": time_series,
                "top_packages": top_packages,
            },
        }), 200
    except Exception as exc:  # noqa: BLE001 — last-resort safety net
        logger.error("admin analytics failed: %s\n%s", exc, traceback.format_exc())
        return jsonify({
            "success": False,
            "error_code": "ADMIN_ANALYTICS_FAILED",
            "error": "Could not compute analytics.",
        }), 500
