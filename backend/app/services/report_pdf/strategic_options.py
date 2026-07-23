"""Registre d'options stratégiques fondées sur les artefacts d'une simulation.

Le module ne produit ni conseil générique ni « moat » automatique. Il convertit
uniquement les recommandations effectivement produites par la simulation en
options candidates, chacune avec une preuve immuable et une question qui permet
de la réfuter. Le registre est sérialisable dans les artefacts durables.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .schema import DecisionEvidence, PivotalMoment, StrategicOption


_COPY = {
    "fr": {
        "refute": "Quelle observation vérifiable démontrerait que cette option aggrave la dynamique observée ou ne produit aucun effet mesurable ?",
        "validate": "Définir avec le décideur un protocole de test, un seuil de succès et une date de revue avant toute généralisation.",
    },
    "en": {
        "refute": "Which verifiable observation would show that this option worsens the observed dynamic or produces no measurable effect?",
        "validate": "Agree with the decision-maker on a test protocol, success threshold, and review date before any wider rollout.",
    },
    "ar": {
        "refute": "ما الملاحظة القابلة للتحقق التي ستثبت أن هذا الخيار يزيد الديناميكية المرصودة سوءاً أو لا يحقق أثراً قابلاً للقياس؟",
        "validate": "يُتفق مع صاحب القرار على بروتوكول اختبار وعتبة نجاح وتاريخ مراجعة قبل أي تعميم.",
    },
}


def _sha256(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _evidence(artifact: str, locator: str, excerpt: str) -> DecisionEvidence:
    return DecisionEvidence(
        artifact=artifact,
        locator=locator,
        excerpt=excerpt,
        sha256=_sha256({"artifact": artifact, "locator": locator, "excerpt": excerpt}),
    )


def _as_recommendations(outcome: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(outcome, Mapping):
        return []
    raw = outcome.get("recommendations") or outcome.get("recommendation_list") or []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    return [item.strip() for item in raw if isinstance(item, str) and item.strip()]


def build_strategic_options(
    *,
    report_id: str,
    outcome: Mapping[str, Any] | None,
    pivotal_moments: Iterable[PivotalMoment] = (),
    lang: str = "fr",
) -> list[StrategicOption]:
    """Construit des options candidates sans inventer d'action ni de preuve.

    Les seules actions admissibles proviennent de ``outcome.json``. Une option
    est donc absente quand le moteur ne formule aucune recommandation, plutôt que
    remplacée par un texte générique hors-sujet.
    """
    copy = _COPY.get(lang, _COPY["fr"])
    verdict = ""
    if isinstance(outcome, Mapping) and isinstance(outcome.get("verdict"), str):
        verdict = outcome["verdict"].strip()

    moments = list(pivotal_moments)
    options: list[StrategicOption] = []
    for index, action in enumerate(_as_recommendations(outcome), start=1):
        evidence = [_evidence("outcome.json", f"/recommendations/{index - 1}", action)]
        if verdict:
            evidence.append(_evidence("outcome.json", "/verdict", verdict))
        if moments:
            moment = moments[0]
            excerpt = f"round={moment.round}; agent={moment.agent}; event={moment.event}; delta={moment.delta_score}"
            evidence.append(_evidence("trajectory.json", f"/rounds/{moment.round}", excerpt))

        seed = {"report_id": report_id, "index": index, "action": action}
        option_id = f"opt_{_sha256(seed)[:12]}"
        ledger_payload = {
            "option_id": option_id,
            "action": action,
            "status": "candidate",
            "moat_status": "unassessed",
            "evidence": [item.model_dump() for item in evidence],
            "refutation_question": copy["refute"],
            "next_validation": copy["validate"],
        }
        options.append(
            StrategicOption.model_validate(
                {**ledger_payload, "ledger_sha256": _sha256(ledger_payload)}
            )
        )
    return options


def ledger_payload(*, report_id: str, lang: str, options: Iterable[StrategicOption]) -> dict[str, Any]:
    """Retourne le document durable, avec empreinte du registre complet."""
    body = {
        "schema_version": 1,
        "report_id": report_id,
        "lang": lang if lang in _COPY else "fr",
        "options": [option.model_dump() for option in options],
    }
    return {**body, "ledger_sha256": _sha256(body)}


def write_ledger(
    *,
    simulation_dir: Path,
    report_id: str,
    outcome: Mapping[str, Any] | None,
    lang: str,
) -> Path:
    """Écrit le registre dans le dossier simulation synchronisé vers Storage."""
    options = build_strategic_options(report_id=report_id, outcome=outcome, lang=lang)
    target = simulation_dir / "decision_ledgers" / f"{report_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(ledger_payload(report_id=report_id, lang=lang, options=options), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def render_strategic_options_markdown(options: Iterable[StrategicOption], *, lang: str) -> str:
    """Rend l'appendice visible dans le rapport web et dans son export Markdown."""
    items = list(options)
    if not items:
        return ""
    headings = {
        "fr": ("## Options stratégiques à valider", "Option", "Preuves", "Réfutation", "Prochaine validation", "Statut de moat"),
        "en": ("## Strategic options to validate", "Option", "Evidence", "Refutation", "Next validation", "Moat status"),
        "ar": ("## خيارات استراتيجية قيد التحقق", "الخيار", "الأدلة", "سؤال الدحض", "التحقق التالي", "حالة الميزة الدفاعية"),
    }
    title, option_label, evidence_label, refutation_label, validation_label, moat_label = headings.get(lang, headings["fr"])
    lines = [title, ""]
    for index, option in enumerate(items, start=1):
        lines.extend([f"### {option_label} {index}", "", option.action, "", f"**{evidence_label}.**"])
        lines.extend(
            f"- `{proof.artifact}{proof.locator}` · SHA-256 `{proof.sha256}`"
            for proof in option.evidence
        )
        lines.extend([
            "",
            f"**{refutation_label}.** {option.refutation_question}",
            "",
            f"**{validation_label}.** {option.next_validation}",
            "",
            f"**{moat_label}.** `{option.moat_status}` · `{option.status}`",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"
