"""Contrats Redis/RQ et snapshot canonique de la génération PDF (US-208)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

_MINIMAL_PDF = b"%PDF-1.4\n%%EOF\n"


@pytest.fixture
def app() -> Any:
    from app import create_app

    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app: Any) -> Any:
    return app.test_client()


def _auth_patches() -> tuple[Any, Any]:
    return (
        patch(
            "app.auth.decorators.verify_supabase_jwt",
            return_value={"sub": "user-001", "email": "admin@bassira.ai"},
        ),
        patch.dict("os.environ", {"BASSIRA_SUPER_ADMIN_EMAILS": "admin@bassira.ai"}),
    )


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token-mock"}


def _payload() -> dict[str, str]:
    return {"simulation_id": "sim_aabbcc112233", "variant": "full", "lang": "fr"}


def _input_digest_patch() -> Any:
    return patch("app.api.pdf_generation._render_input_digest", return_value="digest-v1")


def test_create_snapshot_uses_current_immutable_contract(tmp_path: Path) -> None:
    """Le contrat canonique crée un répertoire versionné, pas un fichier variant/lang."""
    from app.services.report_pdf.snapshot import create_snapshot

    result = create_snapshot(
        "report_snapshot_contract",
        version=1,
        markdown="# Rapport\n",
        pdf_bytes=_MINIMAL_PDF,
        branding=None,
        chart_pngs={"belief_drift": b"png"},
        base_dir=tmp_path,
    )

    snapshot_dir = Path(result["path"])
    assert result["version"] == 1
    assert (snapshot_dir / "full.md").read_text(encoding="utf-8") == "# Rapport\n"
    assert (snapshot_dir / "full.pdf").read_bytes() == _MINIMAL_PDF
    assert (snapshot_dir / "charts" / "belief_drift.png").read_bytes() == b"png"


def test_worker_writes_deterministic_draft_artifact_not_approved_snapshot(tmp_path: Path) -> None:
    from app.workers.pdf_generation_worker import _PDF_CACHE, generate_pdf_job

    _PDF_CACHE.clear()
    renderer = MagicMock()
    renderer.render_pdf.return_value = _MINIMAL_PDF
    charts = MagicMock()

    with (
        patch("app.services.report_pdf.loader.PDFContextLoader.load", return_value=MagicMock()),
        patch("app.services.report_pdf.charts.ChartFactory", return_value=charts),
        patch("app.services.report_pdf.renderer.Renderer", return_value=renderer),
    ):
        result = generate_pdf_job(
            report_id="report_abc123def456",
            simulation_id="sim_aabbcc112233",
            variant="exec",
            lang="fr",
            job_id="pdf-test",
            _artifact_base_dir=str(tmp_path),
        )

    pdf_path = tmp_path / "pdf-test.pdf"
    assert result["status"] == "finished"
    assert result["pdf_path"] == str(pdf_path)
    assert pdf_path.read_bytes() == _MINIMAL_PDF
    renderer.render_pdf.assert_called_once_with(charts_factory=charts, variant="exec")


def test_worker_raises_to_mark_rq_job_failed() -> None:
    from app.workers.pdf_generation_worker import generate_pdf_job

    with patch("app.services.report_pdf.loader.PDFContextLoader.load", side_effect=ValueError("boom")):
        with pytest.raises(ValueError, match="boom"):
            generate_pdf_job("report_abc123def456", "sim_aabbcc112233", job_id="pdf-failure")


def test_render_input_digest_changes_only_when_rendered_content_changes() -> None:
    from app.api.pdf_generation import _job_id, _job_metadata, _render_input_digest

    context = MagicMock()
    context.model_dump.return_value = {"title": "Version A", "lang": "fr"}
    branding = {"id": "brand-v1", "palette_primary": "#123456"}
    with (
        patch("app.services.report_pdf.loader.PDFContextLoader.load", return_value=context),
        patch("app.workers.pdf_generation_worker._load_branding", return_value=branding),
    ):
        first = _render_input_digest(
            "report_abc123def456", "sim_aabbcc112233", "full", "fr", "brand-v1"
        )
        same = _render_input_digest(
            "report_abc123def456", "sim_aabbcc112233", "full", "fr", "brand-v1"
        )
        context.model_dump.return_value = {"title": "Version B", "lang": "fr"}
        changed = _render_input_digest(
            "report_abc123def456", "sim_aabbcc112233", "full", "fr", "brand-v1"
        )

    assert first == same
    assert changed != first
    first_job = _job_id(
        _job_metadata(
            "report_abc123def456", "sim_aabbcc112233", "full", "fr", "brand-v1", first
        )
    )
    same_job = _job_id(
        _job_metadata(
            "report_abc123def456", "sim_aabbcc112233", "full", "fr", "brand-v1", same
        )
    )
    changed_job = _job_id(
        _job_metadata(
            "report_abc123def456", "sim_aabbcc112233", "full", "fr", "brand-v1", changed
        )
    )
    assert first_job == same_job
    assert changed_job != first_job


def test_generate_without_redis_uses_sync_fallback_and_warns(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    with (
        _auth_patches()[0],
        _auth_patches()[1],
        _input_digest_patch(),
        patch("app.api.pdf_generation.logger.warning") as warning,
        patch("app.workers.pdf_generation_worker.generate_pdf_job", return_value={"pdf_path": "/internal/path.pdf"}),
    ):
        response = client.post("/api/admin/reports/report_abc123def456/generate", json=_payload(), headers=_headers())

    assert response.status_code == 200
    assert response.get_json() == {"success": True, "job_id": response.get_json()["job_id"], "status": "finished", "mode": "sync"}
    assert "REDIS_URL absente" in warning.call_args.args[0]
    assert "pdf_path" not in response.get_json()


def test_configured_redis_down_fails_closed(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.pdf_generation import RedisUnavailable

    monkeypatch.setenv("REDIS_URL", "redis://unavailable:6379/0")
    with (
        _auth_patches()[0],
        _auth_patches()[1],
        _input_digest_patch(),
        patch("app.api.pdf_generation._get_redis_connection", side_effect=RedisUnavailable()),
    ):
        response = client.post("/api/admin/reports/report_abc123def456/generate", json=_payload(), headers=_headers())

    assert response.status_code == 503
    assert response.get_json()["error_code"] == "REDIS_UNAVAILABLE"


def test_enqueue_sets_retry_ttls_metadata_and_deterministic_id(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.pdf_generation import _job_id, _job_metadata

    monkeypatch.setenv("REDIS_URL", "redis://configured:6379/0")
    queue = MagicMock()
    queue.enqueue_call.return_value = MagicMock(id="pdf-job")
    redis_conn = MagicMock()
    redis_conn.set.return_value = True
    metadata = _job_metadata(
        "report_abc123def456", "sim_aabbcc112233", "full", "fr", None, "digest-v1"
    )
    with (
        _auth_patches()[0],
        _auth_patches()[1],
        _input_digest_patch(),
        patch("app.api.pdf_generation._get_redis_connection", return_value=redis_conn),
        patch("app.api.pdf_generation._get_queue", return_value=queue),
        patch("app.api.pdf_generation._get_existing_job", return_value=None),
    ):
        response = client.post("/api/admin/reports/report_abc123def456/generate", json=_payload(), headers=_headers())

    assert response.status_code == 202
    kwargs = queue.enqueue_call.call_args.kwargs
    assert kwargs["job_id"] == _job_id(metadata)
    assert kwargs["meta"] == metadata
    assert kwargs["result_ttl"] == 7 * 24 * 60 * 60
    assert kwargs["failure_ttl"] == 7 * 24 * 60 * 60
    assert kwargs["timeout"] == 300
    assert kwargs["retry"].max == 2
    assert kwargs["retry"].intervals == [30, 120]
    redis_conn.set.assert_called_once_with(
        f"pdf-generation:enqueue:{_job_id(metadata)}",
        _job_id(metadata),
        nx=True,
        ex=60,
    )


def test_identical_request_reuses_existing_job(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://configured:6379/0")
    queue = MagicMock()
    existing = MagicMock(id="pdf-existing")
    with (
        _auth_patches()[0],
        _auth_patches()[1],
        _input_digest_patch(),
        patch("app.api.pdf_generation._get_redis_connection", return_value=MagicMock()),
        patch("app.api.pdf_generation._get_queue", return_value=queue),
        patch("app.api.pdf_generation._get_existing_job", return_value=existing),
    ):
        response = client.post("/api/admin/reports/report_abc123def456/generate", json=_payload(), headers=_headers())

    assert response.status_code == 202
    assert response.get_json()["job_id"] == "pdf-existing"
    queue.enqueue_call.assert_not_called()


def test_request_with_inflight_lock_reuses_deterministic_id(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.pdf_generation import _job_id, _job_metadata

    monkeypatch.setenv("REDIS_URL", "redis://configured:6379/0")
    redis_conn = MagicMock()
    redis_conn.set.return_value = False
    queue = MagicMock()
    metadata = _job_metadata(
        "report_abc123def456", "sim_aabbcc112233", "full", "fr", None, "digest-v1"
    )
    with (
        _auth_patches()[0],
        _auth_patches()[1],
        _input_digest_patch(),
        patch("app.api.pdf_generation._get_redis_connection", return_value=redis_conn),
        patch("app.api.pdf_generation._get_queue", return_value=queue),
        patch("app.api.pdf_generation._get_existing_job", return_value=None),
    ):
        response = client.post("/api/admin/reports/report_abc123def456/generate", json=_payload(), headers=_headers())

    assert response.status_code == 202
    assert response.get_json()["job_id"] == _job_id(metadata)
    queue.enqueue_call.assert_not_called()


def test_status_rejects_other_report_and_never_exposes_trace_or_path(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://configured:6379/0")
    job = MagicMock()
    job.meta = {"report_id": "report_other"}
    job.exc_info = "Traceback /private/absolute/path"
    with (
        _auth_patches()[0],
        _auth_patches()[1],
        patch("app.api.pdf_generation._get_redis_connection", return_value=MagicMock()),
        patch("rq.job.Job.fetch", return_value=job),
    ):
        response = client.get("/api/admin/reports/report_abc123def456/jobs/pdf-foreign", headers=_headers())

    assert response.status_code == 404
    body = response.get_json()
    assert body["error_code"] == "JOB_NOT_FOUND"
    assert "private" not in str(body)
    assert "pdf_path" not in body


def test_status_failed_uses_safe_error_code(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://configured:6379/0")
    job = MagicMock()
    job.meta = {"report_id": "report_abc123def456"}
    job.get_status.return_value = "failed"
    job.exc_info = "Traceback /private/absolute/path"
    with (
        _auth_patches()[0],
        _auth_patches()[1],
        patch("app.api.pdf_generation._get_redis_connection", return_value=MagicMock()),
        patch("rq.job.Job.fetch", return_value=job),
    ):
        response = client.get("/api/admin/reports/report_abc123def456/jobs/pdf-failed", headers=_headers())

    assert response.status_code == 200
    assert response.get_json() == {"job_id": "pdf-failed", "status": "failed", "error_code": "PDF_GENERATION_FAILED"}
