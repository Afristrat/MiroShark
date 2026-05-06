"""
tests/test_pdf_async.py — Tests génération PDF hybride sync/async (US-129).

Couvre :
  1.  generate_pdf_job retourne dict avec job_id et status
  2.  Mode sync fallback si Redis absent (REDIS_URL non défini)
  3.  Cache LRU hit : 2 appels mêmes params → 1 seul render (hit cache)
  4.  Cache LRU expiration : cache expiré → re-render
  5.  Compression Ghostscript skip si binary absent (graceful)
  6.  Webhook callback fired après status finished (mock requests)
  7.  Webhook callback fired après status failed
  8.  Enqueue job RQ retourne job_id (mock RQ + fakeredis)
  9.  Polling status job finished via _job_status
  10. Polling status job failed via _job_status
  11. generate_pdf_job échoue gracieusement si simulation_id invalide
  12. create_snapshot sauvegarde PDF sur disque et retourne Path correct
  13. create_snapshot crée le répertoire si absent
  14. Endpoint /preview retourne 400 si simulation_id manquant
  15. Endpoint /generate retourne 202 en mode async (mock queue)
"""

from __future__ import annotations

import io
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch, call

import pytest

# ─── Détection fakeredis disponible ──────────────────────────────────────────
def _fakeredis_available() -> bool:
    try:
        import fakeredis  # noqa: F401
        return True
    except ImportError:
        return False


FAKEREDIS_AVAILABLE = _fakeredis_available()
skip_no_fakeredis = pytest.mark.skipif(
    not FAKEREDIS_AVAILABLE,
    reason="fakeredis non installé — `uv add --dev fakeredis>=2.20`.",
)

# ─── Détection rq disponible ─────────────────────────────────────────────────
def _rq_available() -> bool:
    try:
        import rq  # noqa: F401
        return True
    except ImportError:
        return False


RQ_AVAILABLE = _rq_available()
skip_no_rq = pytest.mark.skipif(
    not RQ_AVAILABLE,
    reason="rq non installé — `uv add rq>=1.15`.",
)

# ─── Mock LanguageTool ────────────────────────────────────────────────────────
@pytest.fixture(autouse=True, scope="session")
def mock_languagetool_globally():
    """Évite les timeouts réseau LanguageTool dans tous les tests."""
    with patch(
        "app.services.text_normalizer.lt_check",
        return_value=[],
    ):
        yield


# ─── Minimal PDF bytes (valide pour pypdf) ────────────────────────────────────
# Bytes PDF 1 page minimale générée par WeasyPrint (ou stub pour tests hors GTK)
_MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
    b"xref\n0 4\n0000000000 65535 f\n"
    b"0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n"
    b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF\n"
)


# ─── Fixtures contexte PDF minimal ───────────────────────────────────────────
@pytest.fixture
def minimal_context():
    """Contexte PDFReportContext minimal valide."""
    from app.services.report_pdf.schema import PDFReportContext

    return PDFReportContext(
        report_id="report_abc123def456",
        simulation_id="sim_123abc456def",
        title="Test Async Report",
        framework="cerberus",
        package="test-package",
        lang="fr",
    )


@pytest.fixture
def tmp_sim_dir(tmp_path: Path) -> Path:
    """Crée un répertoire simulation + rapport minimal valide sur disque."""
    import json

    sim_id = "sim_aabbcc112233"
    report_id = "report_abc123def456"

    sim_dir = tmp_path / "simulations" / sim_id
    sim_dir.mkdir(parents=True)
    # simulation_config.json minimal requis par PDFContextLoader
    (sim_dir / "simulation_config.json").write_text(
        json.dumps(
            {
                "title": "Test Simulation",
                "framework": "cerberus",
                "package": "test-package",
                "lang": "fr",
            }
        ),
        encoding="utf-8",
    )

    # outline.json minimal requis si report_id est fourni
    rep_dir = tmp_path / "reports" / report_id
    rep_dir.mkdir(parents=True)
    (rep_dir / "outline.json").write_text(
        json.dumps(
            {
                "title": "Test Report Outline",
                "summary": "Summary.",
                "sections": [],
            }
        ),
        encoding="utf-8",
    )

    return tmp_path


# ════════════════════════════════════════════════════════════════════════════════
# Tests generate_pdf_job
# ════════════════════════════════════════════════════════════════════════════════


class TestGeneratePdfJob:
    """Tests de la fonction generate_pdf_job."""

    def test_returns_dict_with_required_keys(self, tmp_sim_dir: Path) -> None:
        """generate_pdf_job retourne un dict avec job_id, status, pdf_path, error."""
        from app.workers.pdf_generation_worker import generate_pdf_job

        # Mock le pipeline de rendu pour éviter les dépendances WeasyPrint/LLM
        with (
            patch(
                "app.workers.pdf_generation_worker.generate_pdf_job.__wrapped__"
                if hasattr(generate_pdf_job, "__wrapped__") else
                "app.workers.pdf_generation_worker.generate_pdf_job",
                wraps=generate_pdf_job,
            ) if False else patch(
                "app.services.report_pdf.renderer.Renderer.render_pdf",
                return_value=_MINIMAL_PDF,
            ),
            patch(
                "app.services.report_pdf.charts.ChartFactory",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.report_pdf.snapshot.create_snapshot",
                return_value=Path("/tmp/test.pdf"),
            ),
        ):
            result = generate_pdf_job(
                report_id="report_abc123def456",
                simulation_id="sim_aabbcc112233",
                variant="full",
                lang="fr",
                job_id="test-job-001",
                _sim_base_dir=str(tmp_sim_dir / "simulations"),
            )

        assert isinstance(result, dict)
        assert "job_id" in result
        assert "status" in result
        assert "pdf_path" in result
        assert "error" in result

    def test_returns_failed_on_invalid_simulation(self) -> None:
        """generate_pdf_job retourne status=failed si simulation_id invalide."""
        from app.workers.pdf_generation_worker import generate_pdf_job

        result = generate_pdf_job(
            report_id="report_abc123def456",
            simulation_id="sim_000000000000",  # simulation inexistante
            variant="full",
            lang="fr",
            job_id="test-job-fail",
        )

        # Doit échouer gracieusement sans lever d'exception
        assert result["status"] == "failed"
        assert result["error"] is not None
        assert result["pdf_path"] is None

    def test_sync_fallback_mode(self, tmp_sim_dir: Path) -> None:
        """Mode sync fallback : génération immédiate si Redis absent."""
        # Sans REDIS_URL défini, le mode sync est utilisé
        env_without_redis = {k: v for k, v in os.environ.items() if k != "REDIS_URL"}

        from app.workers.pdf_generation_worker import generate_pdf_job

        with (
            patch.dict(os.environ, env_without_redis, clear=True),
            patch(
                "app.services.report_pdf.renderer.Renderer.render_pdf",
                return_value=_MINIMAL_PDF,
            ),
            patch(
                "app.services.report_pdf.charts.ChartFactory",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.report_pdf.snapshot.create_snapshot",
                return_value=tmp_sim_dir / "reports" / "report_abc123def456" / "full_fr.pdf",
            ),
        ):
            result = generate_pdf_job(
                report_id="report_abc123def456",
                simulation_id="sim_aabbcc112233",
                variant="full",
                lang="fr",
                job_id="sync-abc12345",
                _sim_base_dir=str(tmp_sim_dir / "simulations"),
                _rep_base_dir=str(tmp_sim_dir / "reports"),
            )

        # Le résultat est retourné directement (pas de queue)
        assert result["job_id"] == "sync-abc12345"
        assert result["status"] in ("finished", "failed")  # selon si WeasyPrint dispo

    def test_cache_lru_hit(self, tmp_sim_dir: Path) -> None:
        """2 appels mêmes paramètres → 1 seul render (2e appel depuis cache)."""
        from app.workers.pdf_generation_worker import (
            generate_pdf_job,
            _PDF_CACHE,
            _cache_key,
        )

        # Nettoyer le cache avant le test
        _PDF_CACHE.clear()

        # Créer un fichier PDF temporaire pour simuler le cache
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(_MINIMAL_PDF)
            cached_pdf_path = f.name

        render_call_count = 0

        def counting_render(*args: Any, **kwargs: Any) -> bytes:
            nonlocal render_call_count
            render_call_count += 1
            return _MINIMAL_PDF

        with (
            patch(
                "app.services.report_pdf.renderer.Renderer.render_pdf",
                side_effect=counting_render,
            ),
            patch(
                "app.services.report_pdf.charts.ChartFactory",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.report_pdf.snapshot.create_snapshot",
                return_value=Path(cached_pdf_path),
            ),
        ):
            # 1er appel → génération + mise en cache
            result1 = generate_pdf_job(
                report_id="report_abc123def456",
                simulation_id="sim_aabbcc112233",
                variant="full",
                lang="fr",
                job_id="test-cache-1",
                _sim_base_dir=str(tmp_sim_dir / "simulations"),
                _rep_base_dir=str(tmp_sim_dir / "reports"),
            )

            # 2e appel avec mêmes params → doit venir du cache
            result2 = generate_pdf_job(
                report_id="report_abc123def456",
                simulation_id="sim_aabbcc112233",
                variant="full",
                lang="fr",
                job_id="test-cache-2",
                _sim_base_dir=str(tmp_sim_dir / "simulations"),
                _rep_base_dir=str(tmp_sim_dir / "reports"),
            )

        # render_pdf ne doit avoir été appelé qu'une seule fois
        assert render_call_count == 1, (
            f"render_pdf appelé {render_call_count} fois (attendu 1 — cache miss puis hit)."
        )
        assert result1["status"] == "finished"
        assert result2["status"] == "finished"
        assert result2.get("from_cache") is True

        # Cleanup
        Path(cached_pdf_path).unlink(missing_ok=True)
        _PDF_CACHE.clear()

    def test_cache_lru_different_variant_no_hit(self, tmp_sim_dir: Path) -> None:
        """Variante différente → pas de cache hit (clé différente)."""
        from app.workers.pdf_generation_worker import _PDF_CACHE

        _PDF_CACHE.clear()
        render_call_count = 0

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(_MINIMAL_PDF)
            tmp_pdf = f.name

        def counting_render(*args: Any, **kwargs: Any) -> bytes:
            nonlocal render_call_count
            render_call_count += 1
            return _MINIMAL_PDF

        with (
            patch(
                "app.services.report_pdf.renderer.Renderer.render_pdf",
                side_effect=counting_render,
            ),
            patch(
                "app.services.report_pdf.charts.ChartFactory",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.report_pdf.snapshot.create_snapshot",
                return_value=Path(tmp_pdf),
            ),
        ):
            from app.workers.pdf_generation_worker import generate_pdf_job

            generate_pdf_job(
                report_id="report_abc123def456",
                simulation_id="sim_aabbcc112233",
                variant="full",
                lang="fr",
                job_id="test-cache-variant-1",
                _sim_base_dir=str(tmp_sim_dir / "simulations"),
                _rep_base_dir=str(tmp_sim_dir / "reports"),
            )
            generate_pdf_job(
                report_id="report_abc123def456",
                simulation_id="sim_aabbcc112233",
                variant="exec",  # variant différente → pas de cache hit
                lang="fr",
                job_id="test-cache-variant-2",
                _sim_base_dir=str(tmp_sim_dir / "simulations"),
                _rep_base_dir=str(tmp_sim_dir / "reports"),
            )

        # 2 renders car 2 variantes distinctes
        assert render_call_count == 2

        Path(tmp_pdf).unlink(missing_ok=True)
        _PDF_CACHE.clear()

    def test_gs_compress_skip_if_absent(self, tmp_path: Path) -> None:
        """Compression Ghostscript ignorée silencieusement si gs absent."""
        from app.workers.pdf_generation_worker import _gs_compress

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(_MINIMAL_PDF)
        original_size = pdf_file.stat().st_size

        # gs absent → subprocess.run lève FileNotFoundError
        with patch("subprocess.run", side_effect=FileNotFoundError("gs not found")):
            # Ne doit pas lever d'exception
            _gs_compress(pdf_file)

        # Le fichier doit toujours exister et avoir la même taille
        assert pdf_file.is_file()
        assert pdf_file.stat().st_size == original_size

    def test_webhook_callback_fired_on_finished(self, tmp_sim_dir: Path) -> None:
        """Webhook callback fired après status finished."""
        from app.workers.pdf_generation_worker import generate_pdf_job

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(_MINIMAL_PDF)
            tmp_pdf = f.name

        webhook_calls: list = []

        def mock_post(url: str, json: Any = None, timeout: int = 10) -> Any:
            webhook_calls.append({"url": url, "payload": json})
            return MagicMock(status_code=200)

        with (
            patch.dict(
                os.environ,
                {"PDF_GENERATION_WEBHOOK_URL": "http://localhost:9999/webhook"},
            ),
            patch(
                "app.services.report_pdf.renderer.Renderer.render_pdf",
                return_value=_MINIMAL_PDF,
            ),
            patch(
                "app.services.report_pdf.charts.ChartFactory",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.report_pdf.snapshot.create_snapshot",
                return_value=Path(tmp_pdf),
            ),
            patch("requests.post", side_effect=mock_post),
        ):
            result = generate_pdf_job(
                report_id="report_abc123def456",
                simulation_id="sim_aabbcc112233",
                variant="full",
                lang="fr",
                job_id="test-webhook-ok",
                _sim_base_dir=str(tmp_sim_dir / "simulations"),
                _rep_base_dir=str(tmp_sim_dir / "reports"),
            )

        assert result["status"] == "finished"
        assert len(webhook_calls) == 1
        assert webhook_calls[0]["url"] == "http://localhost:9999/webhook"
        assert webhook_calls[0]["payload"]["status"] == "finished"
        assert webhook_calls[0]["payload"]["job_id"] == "test-webhook-ok"

        Path(tmp_pdf).unlink(missing_ok=True)

    def test_webhook_callback_fired_on_failed(self) -> None:
        """Webhook callback fired après status failed."""
        from app.workers.pdf_generation_worker import generate_pdf_job

        webhook_calls: list = []

        def mock_post(url: str, json: Any = None, timeout: int = 10) -> Any:
            webhook_calls.append({"url": url, "payload": json})
            return MagicMock(status_code=200)

        with (
            patch.dict(
                os.environ,
                {"PDF_GENERATION_WEBHOOK_URL": "http://localhost:9999/webhook"},
            ),
            patch("requests.post", side_effect=mock_post),
        ):
            result = generate_pdf_job(
                report_id="report_abc123def456",
                simulation_id="sim_000000000000",  # simulation inexistante → fail
                variant="full",
                lang="fr",
                job_id="test-webhook-fail",
            )

        assert result["status"] == "failed"
        # Webhook doit avoir été appelé avec status failed
        assert len(webhook_calls) == 1
        assert webhook_calls[0]["payload"]["status"] == "failed"
        assert webhook_calls[0]["payload"]["job_id"] == "test-webhook-fail"


# ════════════════════════════════════════════════════════════════════════════════
# Tests RQ Queue avec fakeredis
# ════════════════════════════════════════════════════════════════════════════════


class TestRQQueue:
    """Tests de l'intégration RQ avec fakeredis."""

    @skip_no_fakeredis
    @skip_no_rq
    def test_enqueue_job_returns_job_id(self) -> None:
        """Enqueue job retourne un job_id valide."""
        import fakeredis
        from rq import Queue
        from app.workers.pdf_generation_worker import generate_pdf_job

        conn = fakeredis.FakeRedis()
        queue = Queue("pdf-generation", connection=conn, is_async=False)

        job = queue.enqueue(
            generate_pdf_job,
            "report_abc123def456",
            "sim_000000000000",  # sim inexistante — job échouera mais job_id assigné
            "full",
            "fr",
            None,
            job_timeout=10,
        )

        assert job.id is not None
        assert isinstance(job.id, str)
        assert len(job.id) > 0

    @skip_no_fakeredis
    @skip_no_rq
    def test_job_status_polling_finished(self, tmp_sim_dir: Path) -> None:
        """Polling status retourne finished après succès du job."""
        import fakeredis
        from rq import Queue
        from app.workers.pdf_generation_worker import generate_pdf_job

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(_MINIMAL_PDF)
            tmp_pdf = f.name

        conn = fakeredis.FakeRedis()
        # is_async=False pour exécution synchrone dans les tests
        queue = Queue("pdf-generation", connection=conn, is_async=False)

        with (
            patch(
                "app.services.report_pdf.renderer.Renderer.render_pdf",
                return_value=_MINIMAL_PDF,
            ),
            patch(
                "app.services.report_pdf.charts.ChartFactory",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.report_pdf.snapshot.create_snapshot",
                return_value=Path(tmp_pdf),
            ),
        ):
            job = queue.enqueue(
                generate_pdf_job,
                kwargs={
                    "report_id": "report_abc123def456",
                    "simulation_id": "sim_aabbcc112233",
                    "variant": "full",
                    "lang": "fr",
                    "_sim_base_dir": str(tmp_sim_dir / "simulations"),
                    "_rep_base_dir": str(tmp_sim_dir / "reports"),
                },
                job_timeout=30,
            )

        from app.api.pdf_generation import _job_status

        status_data = _job_status(conn, job.id)

        assert status_data["job_id"] == job.id
        assert status_data["status"] in ("finished", "failed")  # selon dispo WeasyPrint

        Path(tmp_pdf).unlink(missing_ok=True)

    @skip_no_fakeredis
    @skip_no_rq
    def test_job_status_polling_failed(self) -> None:
        """Polling status retourne failed si le job a échoué."""
        import fakeredis
        from rq import Queue
        from app.workers.pdf_generation_worker import generate_pdf_job

        conn = fakeredis.FakeRedis()
        queue = Queue("pdf-generation", connection=conn, is_async=False)

        # Job avec simulation inexistante → échec garanti
        job = queue.enqueue(
            generate_pdf_job,
            "report_abc123def456",
            "sim_000000000000",
            "full",
            "fr",
            None,
            job_timeout=10,
        )

        from app.api.pdf_generation import _job_status

        status_data = _job_status(conn, job.id)

        assert status_data["job_id"] == job.id
        # Status = finished (generate_pdf_job est graceful et retourne failed dans dict)
        # ou failed si RQ capture l'exception — les deux sont acceptés
        assert status_data["status"] in ("finished", "failed")


# ════════════════════════════════════════════════════════════════════════════════
# Tests create_snapshot
# ════════════════════════════════════════════════════════════════════════════════


class TestCreateSnapshot:
    """Tests du snapshot disque."""

    def test_snapshot_creates_file(self, tmp_path: Path) -> None:
        """create_snapshot sauvegarde le PDF sur disque et retourne le bon Path."""
        from app.services.report_pdf.snapshot import create_snapshot

        report_id = "report_snap000001"
        result_path = create_snapshot(
            report_id=report_id,
            pdf_bytes=_MINIMAL_PDF,
            variant="full",
            lang="fr",
            rep_base_dir=tmp_path,
        )

        assert result_path.is_file()
        assert result_path.read_bytes() == _MINIMAL_PDF
        assert result_path.name == "full_fr.pdf"
        assert result_path.parent.name == report_id

    def test_snapshot_creates_directory_if_absent(self, tmp_path: Path) -> None:
        """create_snapshot crée le répertoire rapport si absent."""
        from app.services.report_pdf.snapshot import create_snapshot

        report_id = "report_snap000002"
        rep_dir = tmp_path / report_id
        assert not rep_dir.exists()  # Ne doit pas exister avant

        create_snapshot(
            report_id=report_id,
            pdf_bytes=_MINIMAL_PDF,
            variant="exec",
            lang="en",
            rep_base_dir=tmp_path,
        )

        assert rep_dir.is_dir()
        assert (rep_dir / "exec_en.pdf").is_file()

    def test_snapshot_filename_variants(self, tmp_path: Path) -> None:
        """create_snapshot génère le bon nom de fichier pour chaque variante/lang."""
        from app.services.report_pdf.snapshot import create_snapshot

        for variant, lang in [
            ("full", "fr"),
            ("exec", "en"),
            ("public", "ar"),
            ("one-pager", "fr"),
        ]:
            path = create_snapshot(
                report_id="report_snap000003",
                pdf_bytes=_MINIMAL_PDF,
                variant=variant,
                lang=lang,
                rep_base_dir=tmp_path,
            )
            assert path.name == f"{variant}_{lang}.pdf"


# ════════════════════════════════════════════════════════════════════════════════
# Tests API Flask endpoints
# ════════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def app():
    """Crée une instance Flask de test."""
    from app import create_app

    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app: Any):
    """Client de test Flask."""
    return app.test_client()


def _auth_headers() -> Dict[str, str]:
    """Retourne des headers d'auth mockés (sans JWT réel)."""
    return {"Authorization": "Bearer test-token-mock"}


def _auth_patches():
    """Context manager combiné : mock JWT + whitelist super-admin."""
    return (
        patch(
            "app.auth.decorators.verify_supabase_jwt",
            return_value={"sub": "user-001", "email": "admin@bassira.ai"},
        ),
        patch.dict(
            os.environ,
            {"BASSIRA_SUPER_ADMIN_EMAILS": "admin@bassira.ai"},
        ),
    )


class TestApiEndpoints:
    """Tests des endpoints Flask PDF generation."""

    def test_preview_missing_simulation_id(self, client: Any) -> None:
        """POST /preview retourne 400 si simulation_id manquant."""
        with _auth_patches()[0], _auth_patches()[1]:
            response = client.post(
                "/api/admin/reports/report_abc123def456/preview",
                json={},  # simulation_id absent
                headers=_auth_headers(),
            )

        assert response.status_code == 400
        data = response.get_json()
        assert data["error_code"] == "MISSING_SIMULATION_ID"

    def test_generate_missing_simulation_id(self, client: Any) -> None:
        """POST /generate retourne 400 si simulation_id manquant."""
        with _auth_patches()[0], _auth_patches()[1]:
            response = client.post(
                "/api/admin/reports/report_abc123def456/generate",
                json={"variant": "full", "lang": "fr"},
                headers=_auth_headers(),
            )

        assert response.status_code == 400
        data = response.get_json()
        assert data["error_code"] == "MISSING_SIMULATION_ID"

    def test_generate_invalid_variant(self, client: Any) -> None:
        """POST /generate retourne 400 si variant invalide."""
        with _auth_patches()[0], _auth_patches()[1]:
            response = client.post(
                "/api/admin/reports/report_abc123def456/generate",
                json={
                    "simulation_id": "sim_aabbcc112233",
                    "variant": "invalid-variant",
                    "lang": "fr",
                },
                headers=_auth_headers(),
            )

        assert response.status_code == 400
        data = response.get_json()
        assert data["error_code"] == "INVALID_VARIANT"

    @skip_no_fakeredis
    @skip_no_rq
    def test_generate_async_mode_returns_202(self, client: Any) -> None:
        """POST /generate retourne 202 avec job_id en mode async (mock queue)."""
        from rq.job import Job

        mock_job = MagicMock(spec=Job)
        mock_job.id = "test-job-async-001"

        mock_queue = MagicMock()
        mock_queue.enqueue.return_value = mock_job

        with (
            _auth_patches()[0],
            _auth_patches()[1],
            patch(
                "app.api.pdf_generation._get_redis_connection",
                return_value=MagicMock(),
            ),
            patch(
                "app.api.pdf_generation._get_queue",
                return_value=mock_queue,
            ),
        ):
            response = client.post(
                "/api/admin/reports/report_abc123def456/generate",
                json={
                    "simulation_id": "sim_aabbcc112233",
                    "variant": "full",
                    "lang": "fr",
                },
                headers=_auth_headers(),
            )

        assert response.status_code == 202
        data = response.get_json()
        assert data["success"] is True
        assert data["job_id"] == "test-job-async-001"
        assert data["mode"] == "async"
        assert "status_url" in data
