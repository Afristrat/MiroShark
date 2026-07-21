"""Unit tests pour le template ``she_start_cohort_replay`` (US-017 + US-018).

Vérifie que :

  1. Le template apparaît dans la liste retournée par
     ``GET /api/templates/list`` avec les bons compteurs.
  2. ``GET /api/templates/she_start_cohort_replay`` renvoie les 3 variants
     avec leurs détails (Ground Truth Replay, Cohort Twin, Blind Spot Hunt).
  3. Les paramètres scientifiques par défaut sont là : 10 rounds, 50 agents
     (35 candidates + 5 mentors + 3 jurés + 2 banquiers + 5 observateurs),
     marché de prédiction PMF.
  4. Les fichiers seed (seed_template.md, personas.md, README.md) existent
     bien sur le disque dans le sous-dossier ``she_start_cohort_replay/``.
  5. Les slots Director Mode aux rounds 3, 5, 7 sont bien déclarés.

Tests offline — aucun service externe requis.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from flask import Flask


_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


TEMPLATE_ID = "she_start_cohort_replay"
TEMPLATES_DIR = _BACKEND / "app" / "preset_templates"
TEMPLATE_JSON = TEMPLATES_DIR / f"{TEMPLATE_ID}.json"
TEMPLATE_SUBDIR = TEMPLATES_DIR / TEMPLATE_ID


@pytest.fixture(scope="module")
def client():
    """Flask test client — la fixture ``client`` standard du Ralph loop."""
    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_list_contains_she_start_template(client):
    """``GET /api/templates/list`` doit inclure ``she_start_cohort_replay``."""
    resp = client.get("/api/templates/list")
    assert resp.status_code == 200, resp.data

    payload = resp.get_json()
    assert payload["success"] is True

    ids = [t["id"] for t in payload["data"]]
    assert TEMPLATE_ID in ids, (
        f"Le template {TEMPLATE_ID} doit apparaître dans /api/templates/list "
        f"(IDs présents : {ids})"
    )

    entry = next(t for t in payload["data"] if t["id"] == TEMPLATE_ID)
    # Le résumé doit signaler la présence des 3 variants A/B/C.
    assert entry.get("has_variants") is True
    assert entry.get("variants_count") == 3
    # Cohérence de la fiche d'identité.
    assert entry["estimated_agents"] == 50
    assert entry["estimated_rounds"] == 10


def test_get_template_returns_three_variants(client):
    """``GET /api/templates/she_start_cohort_replay`` renvoie les 3 variants."""
    resp = client.get(f"/api/templates/{TEMPLATE_ID}")
    assert resp.status_code == 200, resp.data

    payload = resp.get_json()
    assert payload["success"] is True

    template = payload["data"]
    assert template["id"] == TEMPLATE_ID
    assert "variants" in template, "Le champ 'variants' doit être exposé."

    variants = template["variants"]
    assert len(variants) == 3, f"On attend 3 variants A/B/C, reçu {len(variants)}"

    variant_ids = [v["id"] for v in variants]
    expected_ids = {"ground_truth_replay", "cohort_twin", "blind_spot_hunt"}
    assert set(variant_ids) == expected_ids, (
        f"Les IDs attendus sont {expected_ids}, reçu {variant_ids}"
    )

    # Variant A — Ground Truth Replay : 1 run, 35 candidates.
    a = next(v for v in variants if v["id"] == "ground_truth_replay")
    assert a["letter"] == "A"
    assert a["runs"] == 1
    assert a["agents"]["candidates"] == 35
    assert a["agents"]["total"] == 50

    # Variant B — Cohort Twin : 5 runs en parallèle.
    b = next(v for v in variants if v["id"] == "cohort_twin")
    assert b["letter"] == "B"
    assert b["runs"] == 5
    assert b["agents"]["candidates"] == 35

    # Variant C — Blind Spot Hunt : 5 leaders réels retirés (30 candidates).
    c = next(v for v in variants if v["id"] == "blind_spot_hunt")
    assert c["letter"] == "C"
    assert c["runs"] == 1
    assert c["agents"]["candidates"] == 30, (
        "Variant C masque 5 leaders réels → 30 candidates"
    )
    assert c["leaders_removed"], (
        "Variant C doit déclarer au moins une note sur les leaders à masquer."
    )


def test_template_has_default_scientific_parameters():
    """rounds=10, 50 personas par défaut, marché de prédiction PMF."""
    data = json.loads(TEMPLATE_JSON.read_text(encoding="utf-8"))

    # 10 rounds = 10 semaines.
    assert data["rounds"]["count"] == 10
    assert data["rounds"]["unit"] == "week"
    assert data["estimated_rounds"] == 10

    # 50 personas par défaut sur le Variant A (référence).
    assert data["agents"]["total"] == 50
    breakdown = data["agents"]["breakdown"]
    assert breakdown["candidates"] == 35
    assert breakdown["mentors"] == 5
    assert breakdown["jurors"] == 3
    assert breakdown["bankers"] == 2
    assert breakdown["observers"] == 5
    assert sum(breakdown.values()) == 50, "35+5+3+2+5 doit faire 50"

    # Marché de prédiction par défaut = PMF S10 (cible 30 %).
    market_q = data["default_market_question"].lower()
    assert "pmf" in market_q
    assert "s10" in market_q
    assert "30" in market_q  # cible 30 %

    # Slots Director Mode injectables aux rounds 3, 5, 7.
    slot_rounds = [s["round"] for s in data["director_event_slots"]]
    assert slot_rounds == [3, 5, 7], (
        f"Les slots Director Mode doivent être aux S3/S5/S7, reçu {slot_rounds}"
    )


def test_seed_template_files_exist_on_disk():
    """Les 3 fichiers du sous-dossier (seed_template.md, personas.md, README.md)
    doivent exister."""
    assert TEMPLATE_SUBDIR.is_dir(), (
        f"Le sous-dossier {TEMPLATE_SUBDIR} doit exister"
    )

    seed = TEMPLATE_SUBDIR / "seed_template.md"
    personas = TEMPLATE_SUBDIR / "personas.md"
    readme = TEMPLATE_SUBDIR / "README.md"

    assert seed.is_file(), f"{seed} doit exister sur le disque"
    assert personas.is_file(), f"{personas} doit exister sur le disque"
    assert readme.is_file(), f"{readme} doit exister sur le disque"

    seed_text = seed.read_text(encoding="utf-8")
    # Le template doit contenir les 35 fiches candidates et les sections clés.
    assert "Candidate 35" in seed_text, "35 fiches candidates attendues"
    assert "Mentor 05" in seed_text, "5 fiches mentors attendues"
    assert "Critère PMF observable" in seed_text
    # Slots événements S3/S5/S7 explicites.
    assert "événement_S3" in seed_text
    assert "événement_S5" in seed_text
    assert "événement_S7" in seed_text

    personas_text = personas.read_text(encoding="utf-8")
    # Les 8 codes archétypes mentors doivent tous être présents.
    for code in ("M-BRA", "M-GRO", "M-JUR", "M-FUN", "M-TEC", "M-OPS", "M-LEA", "M-AFR"):
        assert code in personas_text, f"Archétype {code} manquant dans personas.md"


def test_template_paths_in_json_match_real_files():
    """Les champs ``seed_template_path`` / ``personas_path`` / ``readme_path``
    du JSON doivent pointer vers des fichiers qui existent réellement."""
    data = json.loads(TEMPLATE_JSON.read_text(encoding="utf-8"))

    for field in ("seed_template_path", "personas_path", "readme_path"):
        rel_path = data.get(field)
        assert rel_path, f"Le champ {field} doit être renseigné dans le JSON"
        full = TEMPLATES_DIR / rel_path
        assert full.is_file(), (
            f"{field}={rel_path} doit pointer vers un fichier existant ({full})"
        )


def test_template_api_expands_declared_seed_sources():
    """Un lancement de template reÃ§oit le contenu, jamais un simple pointeur fichier."""
    from app.api.templates import templates_bp

    app = Flask(__name__)
    app.register_blueprint(templates_bp, url_prefix="/api/templates")
    resp = app.test_client().get("/api/templates/adcheck_pre_launch")
    assert resp.status_code == 200, resp.data
    seed = resp.get_json()["data"]["seed_document"]
    assert "Demande de simulation Bassira" in seed
    assert "Engine config" in seed
