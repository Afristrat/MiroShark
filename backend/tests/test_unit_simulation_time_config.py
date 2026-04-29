"""US-037 — SimulationConfigGenerator parses simulation_requirement → adaptive time config.

Covers ``_resolve_time_config`` resolution priority:
    1. ``recommended_settings`` from preset templates (US-042 canonical scenarios)
    2. Regex on ``simulation_requirement`` (FR + EN)
    3. Loose keyword fallback
    4. Legacy default (72 rounds × 60 min)

These tests are pure-Python (no LLM, no Neo4j) so they run in the offline
``pytest tests/`` quality gate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.simulation_config_generator import _resolve_time_config


_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "app" / "preset_templates"


def _load_template(template_id: str) -> dict:
    """Load a preset template JSON by id."""
    path = _TEMPLATES_DIR / f"{template_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ─── Priority 1: 5 canonical US-042 templates honor recommended_settings ─────


@pytest.mark.parametrize(
    "template_id, expected_rounds, expected_mpr",
    [
        ("pmf_startup_tech", 10, 10080),
        ("crisis_24h_brand", 24, 60),
        ("adcheck_pre_launch", 18, 240),
        ("policy_brief_stress", 10, 240),
        ("product_launch_v2", 28, 360),
    ],
)
def test_canonical_templates_honor_recommended_settings(
    template_id, expected_rounds, expected_mpr
):
    """The 5 US-042 canonical templates must short-circuit to template values."""
    tpl = _load_template(template_id)
    rs = tpl.get("recommended_settings", {})
    assert rs.get("rounds") == expected_rounds, (
        f"Template {template_id} drifted: rounds={rs.get('rounds')}"
    )
    assert rs.get("minutes_per_round") == expected_mpr, (
        f"Template {template_id} drifted: mpr={rs.get('minutes_per_round')}"
    )

    rounds, mpr, source = _resolve_time_config(
        simulation_requirement=tpl.get("simulation_requirement", ""),
        recommended_settings=rs,
    )
    assert rounds == expected_rounds
    assert mpr == expected_mpr
    assert source == "template"


# ─── Priority 2: regex on free-form simulation_requirement ───────────────────


def test_regex_24_hours_french_crisis():
    """« simuler une crise sur 24 heures » → 24 rounds × 60 min."""
    rounds, mpr, source = _resolve_time_config(
        "Je veux simuler une crise sur 24 heures",
    )
    assert rounds == 24
    assert mpr == 60
    assert source == "regex"


def test_regex_10_weeks_pmf():
    """« test PMF sur 10 semaines » → 10 rounds × 10080 min (1 semaine/round)."""
    rounds, mpr, source = _resolve_time_config(
        "Test PMF sur 10 semaines avec 50 prospects",
    )
    assert rounds == 10
    assert mpr == 10080
    assert source == "regex"


def test_regex_1_week_launch_to_daily_granularity():
    """« lancement produit pendant 1 semaine » → 1 sem = 7 jours.

    Mapping: 1 semaine match wins on total horizon (10080 min) over the
    week→daily breakdown. We document and assert: 1 round = 1 semaine
    (10080 min). For finer granularity the user should phrase it in days
    ("7 jours" → 42 rounds × 240 min).
    """
    rounds, mpr, source = _resolve_time_config(
        "Lancement produit pendant 1 semaine",
    )
    assert source == "regex"
    # 1 semaine → 1 round × 10080 min (week granularity)
    assert rounds == 1
    assert mpr == 10080

    # And if user phrases it in days for daily resolution:
    rounds_d, mpr_d, source_d = _resolve_time_config(
        "Lancement produit pendant 7 jours",
    )
    assert source_d == "regex"
    # 7 jours × 6 rounds/day (4h each) = 42 rounds × 240 min
    assert rounds_d == 42
    assert mpr_d == 240


def test_regex_5_business_days_policy():
    """« stress test 5 jours ouvrés » → 10 rounds × 240 min (2 sessions/day)."""
    rounds, mpr, source = _resolve_time_config(
        "Stress test 5 jours ouvrés contre opposition + banques",
    )
    assert rounds == 10
    assert mpr == 240
    assert source == "regex"


def test_empty_requirement_falls_back_to_default():
    """No requirement → legacy 72 rounds × 60 min default."""
    rounds, mpr, source = _resolve_time_config(simulation_requirement="")
    assert rounds == 72
    assert mpr == 60
    assert source == "default"

    # None case
    rounds, mpr, source = _resolve_time_config(simulation_requirement=None)
    assert rounds == 72
    assert mpr == 60
    assert source == "default"


# ─── Edge cases ──────────────────────────────────────────────────────────────


def test_zero_minutes_per_round_falls_through_to_regex():
    """If recommended_settings has bad data (mpr=0), we fall back to regex."""
    rounds, mpr, source = _resolve_time_config(
        simulation_requirement="Crise sur 24 heures",
        recommended_settings={"rounds": 12, "minutes_per_round": 0},
    )
    # Bad recommended_settings → regex must take over
    assert source == "regex"
    assert rounds == 24
    assert mpr == 60


def test_zero_rounds_falls_through_to_regex():
    """If recommended_settings has bad data (rounds=0), regex still wins."""
    rounds, mpr, source = _resolve_time_config(
        simulation_requirement="Test PMF sur 10 semaines",
        recommended_settings={"rounds": 0, "minutes_per_round": 10080},
    )
    assert source == "regex"
    assert rounds == 10
    assert mpr == 10080


def test_multiple_durations_picks_longest_horizon():
    """« 5 jours, 10 semaines » → take the longest (10 weeks).

    Documented behaviour: when several timeframes match, we keep the one
    with the largest total wall-clock so the simulation captures the full
    arc rather than truncating to the first mention.
    """
    rounds, mpr, source = _resolve_time_config(
        "Phase initiale 5 jours puis observation longue sur 10 semaines",
    )
    assert source == "regex"
    # 10 semaines × 10080 = 100800 min > 5 jours × 6 × 240 = 7200 min
    assert rounds == 10
    assert mpr == 10080


def test_keyword_fallback_crisis_no_explicit_number():
    """« situation de crise » with no number → keyword fallback to crisis defaults."""
    rounds, mpr, source = _resolve_time_config(
        "Évaluer une situation de crise médiatique sans précédent",
    )
    assert source == "keyword"
    assert rounds == 24
    assert mpr == 60


def test_recommended_settings_takes_priority_over_regex():
    """Even when requirement says "24 heures", explicit template wins."""
    rounds, mpr, source = _resolve_time_config(
        simulation_requirement="Crise 24 heures",
        recommended_settings={"rounds": 48, "minutes_per_round": 30},
    )
    assert source == "template"
    assert rounds == 48
    assert mpr == 30


def test_english_hours_regex():
    """Regex must match English 'hours' too."""
    rounds, mpr, source = _resolve_time_config("Simulate a 24 hours crisis")
    assert source == "regex"
    assert rounds == 24
    assert mpr == 60


def test_english_weeks_regex():
    """Regex must match English 'weeks' too."""
    rounds, mpr, source = _resolve_time_config("Run PMF test over 10 weeks")
    assert source == "regex"
    assert rounds == 10
    assert mpr == 10080
