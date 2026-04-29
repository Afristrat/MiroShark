"""Public Brier-score / calibration-plot endpoint (US-020).

MiroShark's value proposition is *predictive accuracy on social systems*.
The ``POST /api/simulation/<id>/outcome`` endpoint already lets the
operator annotate completed public simulations with a real-world
outcome (``correct`` / ``partial`` / ``incorrect``) plus an evidence URL,
and ``GET /api/simulation/public?verified=1`` already lets the gallery
filter to those marked sims.

This module is the *aggregate calibration layer* on top of those marks
— it walks every public simulation that has both:

  * an ``outcome.json`` artifact (operator-marked outcome), and
  * a ``trajectory.json`` artifact (so we can derive the final bullish
    share — the model's predicted ``YES`` probability),

then computes:

  * **Brier score** — ``mean((Y_i − p_i)^2)`` where ``p_i`` is the
    final bullish probability the simulation converged to and ``Y_i ∈
    {0.0, 0.5, 1.0}`` mirrors the operator-marked outcome
    (``incorrect`` → 0.0, ``partial`` → 0.5, ``correct`` → 1.0). Lower
    is better; 0.25 is a coin-flip baseline.
  * **Accuracy** — fraction of marked sims that landed on
    ``correct`` or ``partial``.
  * **Calibration plot** — 10 fixed-width buckets over [0, 1] of
    predicted probability. For each bucket we report the mean
    prediction (≈ bucket centre once enough sims accumulate), the
    observed frequency of correct/partial outcomes, and ``n``. This is
    the data a frontend renders as the calibration line — perfect
    calibration is the diagonal.

The endpoint is **public** (no auth) because calibration is the
commercial argument: prospects pull this URL to see how often
MiroShark's belief drift actually predicts the outcome before they pay.
The backing data has already been opted-in to the public gallery (each
input sim has ``is_public=True``), so there is no privacy delta.

Storage assumptions (documented contract — all already enforced
elsewhere in the codebase):

  * Outcomes live at ``<sim_dir>/outcome.json`` with at minimum a
    ``label`` field in {``correct``, ``partial``, ``incorrect``}; this
    is the artifact ``POST /api/simulation/<id>/outcome`` writes and
    that ``_read_outcome_file`` already validates.
  * The "predicted YES probability" is derived from the final
    ``trajectory.json`` snapshot exactly as the gallery card already
    does (``bullish_pct / 100``) — the same number a viewer sees on the
    /explore page, so the calibration plot is honest about what the
    product actually showed.
  * The template filter looks for an optional ``template_id`` key in
    ``simulation_config.json``. Sims without that key are excluded from
    template-filtered queries (instead of leaking into "all" buckets).
    The unfiltered query returns every marked sim regardless.

Math notes:

  * We use the legacy 2-class Brier (``(Y - p)^2``), not the multi-class
    variant — every prediction here is a single binary "did the bullish
    framing win?" question. ``Y = 0.5`` for ``partial`` is a deliberate
    encoding choice so partial calls neither punish nor reward as
    severely as a clear win/miss.
  * Buckets are the canonical 10 bins ``[0, 0.1), [0.1, 0.2), … ,
    [0.9, 1.0]`` (the last one is closed so ``p = 1.0`` lands in the
    final bucket rather than off-grid). Bucket centres reported as
    0.05, 0.15, …, 0.95 so a frontend can plot directly without
    re-deriving.
"""

from __future__ import annotations

import json
import os
import traceback
from pathlib import Path
from typing import Iterable, List, Optional

from flask import Blueprint, jsonify, request

from ..config import Config
from ..services.simulation_manager import SimulationManager
from ..utils.logger import get_logger


# Where the canonical preset templates live (read for the dropdown filter).
_PRESET_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "preset_templates"


calibration_bp = Blueprint('calibration', __name__)
logger = get_logger('miroshark.api.calibration')


# ─── Constants ───────────────────────────────────────────────────────────────

# Map operator-marked label → numeric outcome Y used in the Brier score.
# We accept both the canonical labels written by ``POST /<id>/outcome``
# (``correct``/``partial``/``incorrect``) and the spec aliases
# (``called_it``/``partial``/``wrong``) so downstream tooling can use
# either vocabulary without a translation layer here.
_LABEL_TO_Y = {
    "correct": 1.0,
    "called_it": 1.0,
    "partial": 0.5,
    "incorrect": 0.0,
    "wrong": 0.0,
}

# 10 fixed-width buckets over [0, 1]. Bucket i covers [i/10, (i+1)/10);
# the last bucket is closed so p == 1.0 lands at index 9 rather than
# overshooting the grid.
_NUM_BUCKETS = 10


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _read_outcome_label(sim_dir: str) -> Optional[str]:
    """Return the canonical outcome label (``correct``/``partial``/
    ``incorrect``) for a simulation, or ``None`` if the artifact is
    missing or malformed.

    We re-implement (rather than reuse ``_read_outcome_file`` from the
    simulation module) so the calibration pipeline does not pull the
    full sanitising pass — we only need the label, and we want to stay
    permissive about the spec aliases (``called_it``/``wrong``).
    """
    path = os.path.join(sim_dir, "outcome.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f) or {}
    except Exception:
        return None
    label = (data.get("label") or "").strip().lower()
    if label not in _LABEL_TO_Y:
        return None
    return label


def _read_predicted_bullish_prob(sim_dir: str) -> Optional[float]:
    """Compute the final bullish-framing probability ∈ [0, 1] from the
    last usable snapshot in ``trajectory.json``.

    Mirrors the per-card derivation in ``_build_gallery_card_payload``:
    a stance is bullish when its mean topic position > 0.2, bearish when
    < -0.2, neutral otherwise — and the bullish *share* of agents is
    what the gallery card exposes as the "% bullish" headline. We
    interpret that share as the model's predicted YES probability.

    Returns ``None`` when there is no trajectory, no snapshots, or no
    snapshot has computable belief positions — those sims simply don't
    contribute to the Brier score (we cannot pretend they had a
    prediction).
    """
    path = os.path.join(sim_dir, "trajectory.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            traj = json.load(f) or {}
    except Exception:
        return None
    snapshots = traj.get("snapshots") or []
    if not snapshots:
        return None
    # Walk in reverse so the *final* belief state is what calibration
    # measures — that's what the operator actually saw on the share
    # card before annotating the outcome.
    for snap in reversed(snapshots):
        positions = snap.get("belief_positions") or {}
        if not positions:
            continue
        stances = []
        for p in positions.values():
            if p:
                stances.append(sum(p.values()) / len(p))
        if not stances:
            continue
        total = len(stances)
        n_bullish = sum(1 for s in stances if s > 0.2)
        return n_bullish / total
    return None


def _read_template_id(sim_dir: str) -> Optional[str]:
    """Return the template id stored on a simulation, if any.

    Hypothesis (documented contract): the creation flow may write a
    top-level ``template_id`` key into ``simulation_config.json`` when
    the simulation was spawned from a preset template (matching the
    file-name id in ``backend/app/preset_templates/``). When absent,
    the simulation is treated as "ad-hoc" and is excluded from
    template-filtered queries.
    """
    path = os.path.join(sim_dir, "simulation_config.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            cfg = json.load(f) or {}
    except Exception:
        return None
    tid = cfg.get("template_id")
    if not isinstance(tid, str):
        return None
    return tid.strip() or None


def _in_date_range(
    created_at: str,
    *,
    date_from: Optional[str],
    date_to: Optional[str],
) -> bool:
    """Check whether an ISO timestamp falls inside ``[from, to]``.

    Both bounds are optional; ``from``/``to`` are compared as
    ``YYYY-MM-DD`` strings (ISO-8601 sorts lexicographically, so
    ``"2026-04-01" <= "2026-04-22T10:12:34" <= "2026-04-30"`` works as
    expected without parsing).
    """
    if not created_at:
        # No created_at on a state shouldn't crash the filter — but if
        # the caller has narrowed the window, we cannot place this sim
        # inside it, so we drop it.
        return date_from is None and date_to is None
    day = created_at[:10]
    if date_from and day < date_from:
        return False
    if date_to and day > date_to:
        return False
    return True


def _bucket_index(p: float) -> int:
    """Map a predicted probability ∈ [0, 1] to its bucket index ∈ [0, 9].

    Closed-on-the-right at the top end so ``p == 1.0`` lands in bucket
    9 rather than off-grid.
    """
    if p >= 1.0:
        return _NUM_BUCKETS - 1
    if p <= 0.0:
        return 0
    return min(int(p * _NUM_BUCKETS), _NUM_BUCKETS - 1)


def _compute_calibration(
    samples: Iterable[tuple[float, float, str]],
) -> dict:
    """Aggregate (predicted_prob, outcome_y, label) tuples into the
    response payload — Brier, accuracy, label counts, calibration plot.

    Pulled out as a pure function so the unit tests can drive it with a
    hand-picked dataset and an exact expected Brier without touching
    disk.
    """
    samples = list(samples)
    n = len(samples)

    # Empty result still returns a valid 200 — the frontend renders an
    # empty calibration plot rather than treating "no data" as an
    # error. Brier is ``None`` because the average of an empty set is
    # mathematically undefined.
    if n == 0:
        empty_plot = []
        for i in range(_NUM_BUCKETS):
            centre = round((i + 0.5) / _NUM_BUCKETS, 4)
            empty_plot.append({
                "bucket": centre,
                "predicted": centre,
                "observed": None,
                "n": 0,
            })
        return {
            "brier": None,
            "n": 0,
            "n_called_it": 0,
            "n_partial": 0,
            "n_wrong": 0,
            "accuracy": None,
            "calibration_plot": empty_plot,
        }

    n_called_it = 0
    n_partial = 0
    n_wrong = 0
    sq_err_sum = 0.0
    correct_or_partial = 0

    # Bucket accumulators: sum of predictions, sum of observed Y, count.
    pred_sums = [0.0] * _NUM_BUCKETS
    obs_sums = [0.0] * _NUM_BUCKETS
    counts = [0] * _NUM_BUCKETS

    for predicted_prob, y, label in samples:
        sq_err_sum += (y - predicted_prob) ** 2
        if label in ("correct", "called_it"):
            n_called_it += 1
            correct_or_partial += 1
        elif label == "partial":
            n_partial += 1
            correct_or_partial += 1
        else:  # incorrect / wrong
            n_wrong += 1

        idx = _bucket_index(predicted_prob)
        pred_sums[idx] += predicted_prob
        # Observed for the calibration plot uses the binary "did the
        # call land?" view — partial counts as a hit so the line
        # visualises the same accuracy notion as the headline accuracy
        # field. Brier itself still uses Y=0.5 for partial above.
        obs_sums[idx] += 1.0 if label in ("correct", "called_it", "partial") else 0.0
        counts[idx] += 1

    plot = []
    for i in range(_NUM_BUCKETS):
        centre = round((i + 0.5) / _NUM_BUCKETS, 4)
        if counts[i] == 0:
            plot.append({
                "bucket": centre,
                "predicted": centre,
                "observed": None,
                "n": 0,
            })
        else:
            plot.append({
                "bucket": centre,
                "predicted": round(pred_sums[i] / counts[i], 4),
                "observed": round(obs_sums[i] / counts[i], 4),
                "n": counts[i],
            })

    return {
        "brier": round(sq_err_sum / n, 4),
        "n": n,
        "n_called_it": n_called_it,
        "n_partial": n_partial,
        "n_wrong": n_wrong,
        "accuracy": round(correct_or_partial / n, 4),
        "calibration_plot": plot,
    }


def _gather_samples(
    *,
    template: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
) -> list[tuple[float, float, str]]:
    """Walk every public simulation, collect those with both an outcome
    annotation and a derivable predicted bullish probability, and
    return ``(predicted_prob, y, label)`` tuples after applying the
    template + date filters.
    """
    manager = SimulationManager()
    sims = manager.list_simulations()
    samples: list[tuple[float, float, str]] = []
    for state in sims:
        # Calibration is computed over *publishable* simulations only —
        # the same set the gallery exposes. A private sim can have an
        # outcome.json (the operator can mark before publishing) but it
        # has no business influencing the public Brier.
        if not bool(getattr(state, "is_public", False)):
            continue

        sim_dir = os.path.join(
            Config.WONDERWALL_SIMULATION_DATA_DIR, state.simulation_id
        )

        if not _in_date_range(
            getattr(state, "created_at", "") or "",
            date_from=date_from,
            date_to=date_to,
        ):
            continue

        if template:
            tid = _read_template_id(sim_dir)
            if tid != template:
                continue

        label = _read_outcome_label(sim_dir)
        if label is None:
            continue

        predicted = _read_predicted_bullish_prob(sim_dir)
        if predicted is None:
            # No trajectory ⇒ no prediction we can score against.
            continue

        y = _LABEL_TO_Y[label]
        samples.append((predicted, y, label))

    return samples


# ─── Routes ──────────────────────────────────────────────────────────────────


def _list_available_templates() -> List[dict]:
    """Scan the preset_templates directory and return [{id, name}] sorted
    by name. Used by the calibration page to populate the « filter by
    template » dropdown so the user can isolate the Brier of one scenario
    vs another. Cheap (one disk listing on a directory of ~10 small
    files), so we just rebuild it on each request rather than caching —
    keeps the endpoint stateless and reload-friendly when Amine adds a
    new template.
    """
    out: List[dict] = []
    if not _PRESET_TEMPLATES_DIR.is_dir():
        return out
    for path in _PRESET_TEMPLATES_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        tid = data.get("id") or path.stem
        name = data.get("name") or tid
        out.append({"id": str(tid), "name": str(name)})
    out.sort(key=lambda t: t["name"].lower())
    return out


@calibration_bp.route('/brier-score', methods=['GET'])
def brier_score():
    """Aggregate Brier score + 10-bucket calibration plot over every
    publicly-marked simulation.

    Query parameters (all optional):
        template: restrict to simulations spawned from a given preset
            template id (e.g. ``corporate_crisis``). Sims without a
            ``template_id`` key in their config are excluded when this
            filter is set.
        from: ``YYYY-MM-DD`` lower bound on the simulation
            ``created_at`` day (inclusive).
        to:   ``YYYY-MM-DD`` upper bound (inclusive).

    Response shape::

        {
          "success": true,
          "brier": 0.234,
          "n": 12,
          "n_called_it": 7,
          "n_partial": 3,
          "n_wrong": 2,
          "accuracy": 0.583,
          "calibration_plot": [
            {"bucket": 0.05, "predicted": 0.05, "observed": 0.0, "n": 1},
            ...
            {"bucket": 0.95, "predicted": 0.95, "observed": 1.0, "n": 1}
          ]
        }

    When no simulations match the filter, ``brier`` and ``accuracy`` are
    ``null`` (mathematically undefined on an empty set), ``n`` is 0,
    and the calibration plot still has 10 entries with ``n: 0`` so the
    frontend can render an empty grid. Always returns 200 — "no data"
    is not an error condition for a calibration dashboard.
    """
    try:
        template = (request.args.get('template') or '').strip() or None
        date_from = (request.args.get('from') or '').strip() or None
        date_to = (request.args.get('to') or '').strip() or None

        samples = _gather_samples(
            template=template,
            date_from=date_from,
            date_to=date_to,
        )
        result = _compute_calibration(samples)

        # Populate the « filter by template » dropdown so the frontend
        # CalibrationView can render a usable select even when no
        # simulation is yet marked verified (which is the day-1 state).
        result["filters"] = {
            "templates_available": _list_available_templates(),
            "applied": {
                "template": template,
                "from": date_from,
                "to": date_to,
            },
        }

        response = jsonify({
            "success": True,
            **result,
        })
        # Calibration data drifts slowly — cache for a minute so a
        # /explore landing page that polls this URL doesn't re-walk
        # every sim directory on every hit.
        response.headers["Cache-Control"] = "public, max-age=60"
        return response

    except Exception as exc:
        logger.error(f"calibration: failed to compute brier score: {exc}")
        return jsonify({
            "success": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }), 500
