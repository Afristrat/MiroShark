"""Regression tests for the native-language report editorial contract."""

from app.services.report_editorial import (
    compose_report_system_prompt,
    editorial_violations,
    report_editorial_contract,
)
from app.services.report_agent import Report, ReportStatus
from app.utils.locale_prompt import normalize_locale


def test_normalize_locale_is_safe_outside_a_request_context():
    assert normalize_locale("AR") == "ar"
    assert normalize_locale(None) == "fr"
    assert normalize_locale("unsupported") == "fr"


def test_editorial_contract_is_native_for_all_supported_languages():
    assert "français soutenu" in report_editorial_contract("fr")
    assert "formal, plain English" in report_editorial_contract("en")
    assert "العربية الفصحى" in report_editorial_contract("ar")


def test_editorial_contract_is_composed_before_locale_instruction():
    prompt = compose_report_system_prompt("Base report task", "fr")
    assert prompt.startswith("Base report task")
    assert "casse phrase" in prompt


def test_editorial_validation_detects_the_failures_reported_by_users():
    markdown = "# A Strategic Simulation Report\n\nLa conclusion: elle est certaine — à tort."
    violations = editorial_violations(markdown, "fr")
    assert "title_case_heading" in violations
    assert "french_spacing" in violations
    assert "em_dash" in violations


def test_editorial_validation_accepts_native_arabic_markdown():
    markdown = "# قراءة في ديناميات المحاكاة\n\nتعرض هذه الفقرة دليلاً ثم آلية ثم دلالة عملية."
    assert editorial_violations(markdown, "ar") == []


def test_report_metadata_persists_the_captured_locale():
    report = Report(
        report_id="report_123456789abc",
        simulation_id="sim_123456789abc",
        graph_id="graph_123",
        simulation_requirement="Test",
        status=ReportStatus.PENDING,
        locale="ar",
    )

    assert report.to_dict()["locale"] == "ar"
