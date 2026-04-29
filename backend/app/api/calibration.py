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
from typing import Any, Dict, Iterable, List, Optional

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


# ─── US-045: list-evaluables endpoint ────────────────────────────────────────
#
# Why this lives here (not in simulation.py): conceptually it's a "calibration
# inbox" — the operator opens /calibration, scans which public sims still need
# a verdict, marks them inline, and the aggregate Brier on the same page
# updates immediately. Co-locating it with the brier-score helpers keeps the
# template-id / outcome / trajectory readers in one module so the contract is
# obvious from a single file.


_DEFAULT_LIST_LIMIT = 20
_MAX_LIST_LIMIT = 100

# Allowed values for the ``status`` query parameter.
_ALLOWED_LIST_STATUSES = ("pending", "evaluated", "all")


def _read_simulation_config(sim_dir: str) -> Dict[str, Any]:
    """Return the parsed ``simulation_config.json`` or an empty dict.

    Never raises — a missing or malformed config must not blank out the
    inbox; we still want to surface the sim with whatever fields we have
    (``id``, ``status``, ``created_at``) so the operator can at least
    open it.
    """
    path = os.path.join(sim_dir, "simulation_config.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _read_outcome_for_inbox(sim_dir: str) -> Optional[Dict[str, Any]]:
    """Return ``{label, outcome_url}`` from ``outcome.json`` or ``None``.

    Lighter than ``simulation._read_outcome_file`` — we only need the two
    fields the inbox card renders. We accept both the canonical labels
    (``correct``/``partial``/``incorrect``) and the spec aliases
    (``called_it``/``wrong``) so a sim marked via any frontend
    vocabulary still shows up in the « evaluated » filter.
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
    url = (data.get("outcome_url") or "").strip()
    if url and not (url.startswith("http://") or url.startswith("https://")):
        url = ""
    return {"label": label, "outcome_url": url}


def _build_summary_first_words(
    cfg: Dict[str, Any],
    fallback_id: str,
) -> str:
    """Tweet-sized headline for the inbox card.

    Priority:
      1. First sentence of ``simulation_requirement`` (chopped on ``.``,
         ``!``, ``?``, then capped to 180 chars).
      2. Top-level ``title`` if the config carries one.
      3. The simulation id as the final fallback so a card always has a
         visible label.
    """
    requirement = (cfg.get("simulation_requirement") or "").strip()
    if requirement:
        # Split on the first sentence terminator (with following whitespace
        # so an in-word period like "U.S." doesn't truncate prematurely).
        for terminator in (". ", "! ", "? ", ".\n", "!\n", "?\n"):
            idx = requirement.find(terminator)
            if 0 < idx < 180:
                return requirement[: idx + 1].strip()
        # No clean terminator found — just trim to keep cards visually
        # even on the gallery grid.
        if len(requirement) > 180:
            return requirement[:177].rstrip() + "…"
        return requirement
    title = (cfg.get("title") or "").strip()
    if title:
        return title[:180]
    return fallback_id


def _resolve_template_name(template_id: Optional[str], cache: Dict[str, str]) -> Optional[str]:
    """Look up the human-readable template ``name`` for ``template_id``.

    Cached per-request — a 47-sim inbox would otherwise re-read the
    same template JSON 47 times. Returns ``None`` if the preset is no
    longer on disk or the JSON is malformed; the frontend renders the
    raw id in that case.
    """
    if not template_id:
        return None
    if template_id in cache:
        return cache[template_id] or None
    candidate = _PRESET_TEMPLATES_DIR / f"{template_id}.json"
    name: Optional[str] = None
    if candidate.is_file():
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
            raw = data.get("name")
            if isinstance(raw, str) and raw.strip():
                name = raw.strip()
        except (OSError, json.JSONDecodeError):
            name = None
    cache[template_id] = name or ""
    return name


def _gather_evaluable_simulations(
    *,
    status_filter: str,
    template: Optional[str],
) -> list[dict]:
    """Walk every public simulation, build the inbox payload, apply the
    status + template filters.

    Returns the full filtered list (sorted by ``created_at`` desc); the
    caller is responsible for paginating. We materialise everything
    rather than yielding because the list is bounded by the public sim
    count (≪ 10k in practice) and the caller needs the total to compute
    ``has_more``.
    """
    manager = SimulationManager()
    sims = manager.list_simulations()

    # is_public + completed-or-running statuses only. We accept ``running``
    # in case the operator wants to mark mid-flight (rare but supported by
    # the existing /outcome endpoint), and ``stopped`` because a manually
    # stopped sim is still annotatable. Status ``failed`` is excluded —
    # there is no prediction to score against.
    eligible_statuses = {"completed", "running", "stopped", "paused"}

    template_name_cache: Dict[str, str] = {}
    rows: list[dict] = []

    for state in sims:
        if not bool(getattr(state, "is_public", False)):
            continue

        status_val = (
            state.status.value
            if hasattr(state.status, 'value')
            else str(state.status)
        )
        if status_val not in eligible_statuses:
            continue

        sim_dir = os.path.join(
            Config.WONDERWALL_SIMULATION_DATA_DIR, state.simulation_id
        )

        cfg = _read_simulation_config(sim_dir)
        template_id = cfg.get("template_id") if isinstance(cfg.get("template_id"), str) else None

        # Apply template filter early.
        if template and template_id != template:
            continue

        outcome = _read_outcome_for_inbox(sim_dir)
        has_outcome = outcome is not None

        # Apply status (= pending | evaluated | all) filter.
        if status_filter == "pending" and has_outcome:
            continue
        if status_filter == "evaluated" and not has_outcome:
            continue

        title = (cfg.get("title") or "").strip() or state.simulation_id
        summary = _build_summary_first_words(cfg, fallback_id=state.simulation_id)
        predicted = _read_predicted_bullish_prob(sim_dir)
        template_name = _resolve_template_name(template_id, template_name_cache)

        rows.append({
            "id": state.simulation_id,
            "title": title,
            "template_id": template_id,
            "template_name": template_name,
            "created_at": state.created_at or "",
            "status": status_val,
            "is_public": True,
            "predicted_bullish_pct": predicted,
            "outcome": outcome["label"] if outcome else None,
            "outcome_url": outcome["outcome_url"] if outcome else None,
            "summary_first_words": summary,
        })

    # Most-recent first so the operator sees brand-new sims at the top
    # of the inbox without having to scroll.
    rows.sort(key=lambda r: r["created_at"] or "", reverse=True)
    return rows


@calibration_bp.route('/simulations', methods=['GET'])
def list_calibration_simulations():
    """List the sims a calibration operator can mark inline.

    Companion to ``GET /api/calibration/brier-score`` — that one
    aggregates the Brier; this one feeds the inbox UI on the same page
    so the operator can clear pending verdicts and watch the aggregate
    move in real time.

    Query parameters (all optional):
        status: ``pending`` (default — sims completed/running/stopped
            without an ``outcome.json``), ``evaluated`` (sims with an
            outcome) or ``all``. Anything else is normalised to the
            default rather than 400-ing — frontends can pass typo'd
            values without crashing the page.
        limit: max items per page (default 20, clamped to [1, 100]).
        offset: pagination offset (default 0).
        template: restrict to sims spawned from a given preset id
            (e.g. ``crypto_launch``). Sims without ``template_id`` are
            excluded when this filter is set.

    Public endpoint (no auth) — same posture as the brier-score URL.
    The data is already opted-in to the public gallery, so there is no
    privacy delta in listing it.

    Response shape mirrors the brief — ``data`` for items, ``pagination``
    for paging metadata, ``filters.applied`` so the frontend can echo
    the active filter without re-deriving it.
    """
    try:
        # Pagination — clamp aggressively so a buggy client cannot make
        # the server walk every public sim into one giant response.
        limit_raw = request.args.get('limit', _DEFAULT_LIST_LIMIT, type=int)
        offset_raw = request.args.get('offset', 0, type=int)
        limit = max(1, min(_MAX_LIST_LIMIT, int(limit_raw or _DEFAULT_LIST_LIMIT)))
        offset = max(0, int(offset_raw or 0))

        # Status — normalise unknown values to the default. Surfacing
        # 400 here would break the UI's "the URL has a stale ?status="
        # bookmark; we'd rather silently fall back to ``pending``.
        status_raw = (request.args.get('status') or '').strip().lower()
        status_filter = status_raw if status_raw in _ALLOWED_LIST_STATUSES else "pending"

        template = (request.args.get('template') or '').strip() or None

        rows = _gather_evaluable_simulations(
            status_filter=status_filter,
            template=template,
        )

        total = len(rows)
        page = rows[offset:offset + limit]
        has_more = offset + len(page) < total

        response = jsonify({
            "success": True,
            "data": page,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total,
                "has_more": has_more,
            },
            "filters": {
                "applied": {
                    "status": status_filter,
                    "template": template,
                },
            },
        })
        # Same short-cache window as the public gallery — newly-marked
        # sims should disappear from the « pending » list within ~30 s.
        response.headers["Cache-Control"] = "public, max-age=30"
        return response

    except Exception as exc:
        logger.error(f"calibration: failed to list simulations: {exc}")
        return jsonify({
            "success": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }), 500
