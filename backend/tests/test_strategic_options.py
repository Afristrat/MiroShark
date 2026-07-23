"""Contrats du registre d'options stratégiques sourcées."""

from __future__ import annotations

import json
from pathlib import Path

from app.services.report_pdf.strategic_options import (
    build_strategic_options,
    render_strategic_options_markdown,
    write_ledger,
)
from app.services.report_pdf.loader import PDFContextLoader


REPORT_ID = "report_aabbcc112233"


def test_option_est_ancree_dans_outcome_et_refutable() -> None:
    options = build_strategic_options(
        report_id=REPORT_ID,
        lang="fr",
        outcome={
            "verdict": "Une coalition résiste au projet.",
            "recommendations": ["Tester un pilote avec la coalition la plus exposée."],
        },
    )

    assert len(options) == 1
    option = options[0]
    assert option.action == "Tester un pilote avec la coalition la plus exposée."
    assert option.status == "candidate"
    assert option.moat_status == "unassessed"
    assert {proof.locator for proof in option.evidence} == {"/recommendations/0", "/verdict"}
    assert "Quelle observation vérifiable" in option.refutation_question
    assert len(option.ledger_sha256) == 64


def test_aucune_option_generique_sans_recommandation_sourcee() -> None:
    assert build_strategic_options(
        report_id=REPORT_ID,
        outcome={"verdict": "La dynamique demeure incertaine."},
    ) == []


def test_ledger_est_ecrit_dans_artefacts_simulation(tmp_path: Path) -> None:
    path = write_ledger(
        simulation_dir=tmp_path,
        report_id=REPORT_ID,
        lang="en",
        outcome={"recommendation_list": ["Run a limited pilot before scaling."]},
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert path == tmp_path / "decision_ledgers" / f"{REPORT_ID}.json"
    assert payload["schema_version"] == 1
    assert payload["lang"] == "en"
    assert payload["options"][0]["moat_status"] == "unassessed"
    assert len(payload["ledger_sha256"]) == 64


def test_appendice_fr_expose_preuve_et_limite_de_moat() -> None:
    options = build_strategic_options(
        report_id=REPORT_ID,
        outcome={"recommendations": ["Conduire un pilote contrôlé."]},
    )

    markdown = render_strategic_options_markdown(options, lang="fr")

    assert "## Options stratégiques à valider" in markdown
    assert "outcome.json/recommendations/0" in markdown
    assert "Statut de moat" in markdown
    assert "unassessed" in markdown


def test_loader_restitue_le_registre_durable(tmp_path: Path) -> None:
    sim_dir = tmp_path / "sim_112233aabbcc"
    report_dir = tmp_path / REPORT_ID
    sim_dir.mkdir()
    report_dir.mkdir()
    (sim_dir / "simulation_config.json").write_text(
        json.dumps({"title": "Simulation test", "framework": "cerberus", "lang": "fr"}),
        encoding="utf-8",
    )
    (report_dir / "outline.json").write_text(
        json.dumps({"title": "Rapport test", "summary": "Synthèse", "sections": []}),
        encoding="utf-8",
    )
    write_ledger(
        simulation_dir=sim_dir,
        report_id=REPORT_ID,
        lang="fr",
        outcome={"recommendations": ["Conduire un pilote contrôlé."]},
    )

    context = PDFContextLoader.load(
        simulation_id="sim_112233aabbcc",
        report_id=REPORT_ID,
        sim_base_dir=tmp_path,
        rep_base_dir=tmp_path,
    )

    assert len(context.strategic_options) == 1
    assert context.strategic_options[0].action == "Conduire un pilote contrôlé."
