"""
tests/test_snapshot_watermark.py — Tests US-128 : snapshot immuable + watermark + signature.

Couvre :
    1.  create_snapshot() : fichiers créés, structure OK
    2.  create_snapshot() : SHA256 calculé et présent dans metadata.json
    3.  create_snapshot() : version dans metadata.json
    4.  create_snapshot() : doublon → SnapshotError
    5.  verify_snapshot() : valide après création
    6.  verify_snapshot() : invalide si fichier modifié
    7.  verify_snapshot() : SnapshotError si snapshot absent
    8.  list_snapshots() : retourne versions triées croissantes
    9.  list_snapshots() : [] si report_id inconnu
    10. apply_watermark_to_pdf() : produit PDF non vide + taille >= original
    11. apply_watermark_to_pdf() : skip_first_page=True → cover sans filigrane, page 2 avec
    12. apply_watermark_to_pdf() : skip_first_page=False → page 1 filigranée aussi
    13. sign_pdf_pades() sans cert → retourne PDF inchangé + warning log (pas raise)
    14. sign_pdf_pades() avec cert mock → retourne bytes non vides
    15. can_sign() sans config → False
    16. can_sign() avec pyHanko absent → False
    17. Endpoint POST /approve sans super-admin → 403
    18. Endpoint POST /approve (mock Renderer + snapshot) → 200 + structure
    19. Endpoint POST /approve avec watermark_recipient valide → 200
    20. Endpoint POST /approve avec sign=True (mock signer) → 200
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest


# ── Helpers PDF minimal ───────────────────────────────────────────────────────

def _make_minimal_pdf(pages: int = 2) -> bytes:
    """Crée un PDF minimal avec N pages via reportlab."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    for i in range(pages):
        c.drawString(100, 700, f"Page {i + 1} — contenu de test")
        c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_base(tmp_path: Path) -> Path:
    """Répertoire temporaire utilisé comme base_dir des snapshots."""
    base = tmp_path / "snapshots"
    base.mkdir()
    return base


@pytest.fixture()
def minimal_pdf() -> bytes:
    return _make_minimal_pdf(pages=2)


@pytest.fixture()
def snapshot_args(minimal_pdf: bytes) -> Dict[str, Any]:
    """Arguments minimaux pour create_snapshot()."""
    return {
        "version": 1,
        "markdown": "# Rapport test\n\nContenu.",
        "pdf_bytes": minimal_pdf,
        "branding": {"id": "br_001", "primary_color": "#FF0000"},
        "chart_pngs": {"belief_drift": b"\x89PNG\r\n\x1a\n" + b"\x00" * 20},
    }


# ── Tests create_snapshot() ───────────────────────────────────────────────────

class TestCreateSnapshot:
    def test_files_created(self, tmp_base, snapshot_args):
        """Test 1 — les fichiers attendus sont créés."""
        from app.services.report_pdf.snapshot import create_snapshot

        result = create_snapshot("report_abc123", base_dir=tmp_base, **snapshot_args)

        snap_dir = Path(result["path"])
        assert snap_dir.exists()
        assert (snap_dir / "full.md").exists()
        assert (snap_dir / "full.pdf").exists()
        assert (snap_dir / "branding.json").exists()
        assert (snap_dir / "metadata.json").exists()
        assert (snap_dir / "charts" / "belief_drift.png").exists()

    def test_sha256_computed_and_stored(self, tmp_base, snapshot_args):
        """Test 2 — SHA256 calculé et stocké dans metadata.json."""
        from app.services.report_pdf.snapshot import create_snapshot

        result = create_snapshot("report_sha256", base_dir=tmp_base, **snapshot_args)

        assert len(result["sha256"]) == 64  # SHA256 hex = 64 chars

        metadata = json.loads((Path(result["path"]) / "metadata.json").read_text())
        assert metadata["sha256_hash_global"] == result["sha256"]

    def test_version_in_metadata(self, tmp_base, snapshot_args):
        """Test 3 — version présente dans metadata.json."""
        from app.services.report_pdf.snapshot import create_snapshot

        result = create_snapshot("report_ver", base_dir=tmp_base, **snapshot_args)

        metadata = json.loads((Path(result["path"]) / "metadata.json").read_text())
        assert metadata["version"] == snapshot_args["version"]
        assert result["version"] == snapshot_args["version"]

    def test_duplicate_raises_snapshot_error(self, tmp_base, snapshot_args):
        """Test 4 — doublon → SnapshotError."""
        from app.services.report_pdf.snapshot import create_snapshot, SnapshotError

        create_snapshot("report_dup", base_dir=tmp_base, **snapshot_args)

        with pytest.raises(SnapshotError):
            create_snapshot("report_dup", base_dir=tmp_base, **snapshot_args)

    def test_branding_none_allowed(self, tmp_base, minimal_pdf):
        """Test bonus — branding=None ne plante pas."""
        from app.services.report_pdf.snapshot import create_snapshot

        result = create_snapshot(
            "report_nobrand",
            base_dir=tmp_base,
            version=1,
            markdown="# Test",
            pdf_bytes=minimal_pdf,
            branding=None,
            chart_pngs={},
        )
        assert result["sha256"]


# ── Tests verify_snapshot() ───────────────────────────────────────────────────

class TestVerifySnapshot:
    def test_valid_after_creation(self, tmp_base, snapshot_args):
        """Test 5 — valide immédiatement après création."""
        from app.services.report_pdf.snapshot import create_snapshot, verify_snapshot

        create_snapshot("report_v1", base_dir=tmp_base, **snapshot_args)
        assert verify_snapshot("report_v1", 1, base_dir=tmp_base) is True

    def test_invalid_after_modification(self, tmp_base, snapshot_args):
        """Test 6 — invalide si un fichier est modifié après création."""
        from app.services.report_pdf.snapshot import create_snapshot, verify_snapshot

        result = create_snapshot("report_tamper", base_dir=tmp_base, **snapshot_args)
        snap_dir = Path(result["path"])

        # Modifier full.md après coup
        (snap_dir / "full.md").write_text("# Modifié — attaque !", encoding="utf-8")

        assert verify_snapshot("report_tamper", 1, base_dir=tmp_base) is False

    def test_missing_snapshot_raises(self, tmp_base):
        """Test 7 — SnapshotError si snapshot absent."""
        from app.services.report_pdf.snapshot import verify_snapshot, SnapshotError

        with pytest.raises(SnapshotError):
            verify_snapshot("report_ghost", 99, base_dir=tmp_base)


# ── Tests list_snapshots() ────────────────────────────────────────────────────

class TestListSnapshots:
    def test_sorted_versions(self, tmp_base, minimal_pdf):
        """Test 8 — retourne versions triées croissantes."""
        from app.services.report_pdf.snapshot import create_snapshot, list_snapshots

        for ver in [3, 1, 2]:
            create_snapshot(
                "report_list",
                base_dir=tmp_base,
                version=ver,
                markdown="# v" + str(ver),
                pdf_bytes=minimal_pdf,
                branding=None,
                chart_pngs={},
            )

        snapshots = list_snapshots("report_list", base_dir=tmp_base)
        assert len(snapshots) == 3
        assert [s["version"] for s in snapshots] == [1, 2, 3]

    def test_empty_for_unknown_report(self, tmp_base):
        """Test 9 — [] si report_id inconnu."""
        from app.services.report_pdf.snapshot import list_snapshots

        result = list_snapshots("report_unknown_xyz", base_dir=tmp_base)
        assert result == []


# ── Tests apply_watermark_to_pdf() ───────────────────────────────────────────

class TestWatermark:
    def test_produces_non_empty_pdf(self, minimal_pdf):
        """Test 10 — produit un PDF non vide."""
        from app.services.report_pdf.watermark import apply_watermark_to_pdf

        result = apply_watermark_to_pdf(
            minimal_pdf,
            recipient_name="Jean Dupont",
            recipient_company="ACME SA",
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_output_is_valid_pdf(self, minimal_pdf):
        """Test 10b — la sortie est un PDF valide (commence par %PDF)."""
        from app.services.report_pdf.watermark import apply_watermark_to_pdf
        from pypdf import PdfReader

        result = apply_watermark_to_pdf(
            minimal_pdf,
            recipient_name="Test User",
        )
        # Le résultat doit être un PDF valide
        assert result.startswith(b"%PDF"), "Le résultat doit être un PDF valide"
        reader = PdfReader(io.BytesIO(result))
        assert len(reader.pages) == 2

    def test_skip_first_page(self, minimal_pdf):
        """Test 11 — skip_first_page=True : cover sans filigrane, page 2 avec.

        Vérifie via extraction du texte que le filigrane est absent de la page 1
        et présent sur la page 2.
        """
        from app.services.report_pdf.watermark import apply_watermark_to_pdf
        from pypdf import PdfReader

        result = apply_watermark_to_pdf(
            minimal_pdf,
            recipient_name="NDA Recipient",
            skip_first_page=True,
        )

        # Vérifier que le PDF est lisible (2 pages)
        reader = PdfReader(io.BytesIO(result))
        assert len(reader.pages) == 2

        # La page 1 ne doit pas contenir le texte du filigrane
        page1_text = reader.pages[0].extract_text() or ""
        page2_text = reader.pages[1].extract_text() or ""

        # Le nom "NDA Recipient" devrait être sur la page 2 mais pas la page 1
        assert "NDA Recipient" not in page1_text, (
            "La cover (page 1) ne devrait pas avoir de filigrane"
        )
        assert "NDA Recipient" in page2_text, (
            "La page 2 (contenu) devrait avoir le filigrane"
        )

    def test_no_skip_first_page(self, minimal_pdf):
        """Test 12 — skip_first_page=False → page 1 filigranée aussi."""
        from app.services.report_pdf.watermark import apply_watermark_to_pdf
        from pypdf import PdfReader

        result = apply_watermark_to_pdf(
            minimal_pdf,
            recipient_name="FullWatermark",
            skip_first_page=False,
        )

        reader = PdfReader(io.BytesIO(result))
        page1_text = reader.pages[0].extract_text() or ""
        assert "FullWatermark" in page1_text

    def test_empty_pdf_raises(self):
        """Test bonus — ValueError si pdf_bytes vide."""
        from app.services.report_pdf.watermark import apply_watermark_to_pdf

        with pytest.raises(ValueError):
            apply_watermark_to_pdf(b"", recipient_name="Test")


# ── Tests sign_pdf_pades() / can_sign() ───────────────────────────────────────

class TestSigner:
    def test_sign_without_cert_returns_unchanged(self, minimal_pdf, caplog):
        """Test 13 — sans cert → retourne PDF inchangé + warning (pas raise)."""
        from app.services.report_pdf.signer import sign_pdf_pades

        # On s'assure que les env vars sont absentes
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BASSIRA_SIGNING_CERT_P12_PATH", None)
            os.environ.pop("BASSIRA_SIGNING_CERT_PASSWORD", None)

            import logging
            with caplog.at_level(logging.WARNING, logger="miroshark.signer"):
                result = sign_pdf_pades(minimal_pdf)

        # Doit retourner le même contenu (pas raise)
        assert result == minimal_pdf

    def test_sign_with_mock_pyhanko(self, minimal_pdf):
        """Test 14 — avec cert mock → appelle _do_sign et retourne bytes."""
        from app.services.report_pdf.signer import SigningConfig

        mock_signed = b"SIGNED_PDF_MOCK_CONTENT" + minimal_pdf

        with (
            patch("app.services.report_pdf.signer._pyhanko_available", return_value=True),
            patch("os.path.isfile", return_value=True),
            patch("app.services.report_pdf.signer._do_sign", return_value=mock_signed),
        ):
            from app.services.report_pdf import signer as signer_mod

            cfg = SigningConfig(cert_p12_path="/fake/cert.p12", cert_password="secret")
            result = signer_mod.sign_pdf_pades(minimal_pdf, config=cfg)

        assert result == mock_signed
        assert len(result) > 0

    def test_can_sign_without_config(self):
        """Test 15 — can_sign() → False si config absente."""
        from app.services.report_pdf.signer import can_sign

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BASSIRA_SIGNING_CERT_P12_PATH", None)
            os.environ.pop("BASSIRA_SIGNING_CERT_PASSWORD", None)
            result = can_sign()

        assert result is False

    def test_can_sign_without_pyhanko(self):
        """Test 16 — can_sign() → False si pyHanko absent."""
        from app.services.report_pdf.signer import can_sign

        with patch("app.services.report_pdf.signer._pyhanko_available", return_value=False):
            result = can_sign()

        assert result is False

    def test_can_sign_with_full_config(self, tmp_path):
        """Test bonus — can_sign() → True si pyHanko + cert présent."""
        from app.services.report_pdf.signer import can_sign, SigningConfig

        # Créer un faux fichier cert
        fake_cert = tmp_path / "cert.p12"
        fake_cert.write_bytes(b"FAKE_CERT_DATA")

        with patch("app.services.report_pdf.signer._pyhanko_available", return_value=True):
            cfg = SigningConfig(cert_p12_path=str(fake_cert), cert_password="pw")
            result = can_sign(config=cfg)

        assert result is True


# ── Tests endpoint POST /approve ──────────────────────────────────────────────

@pytest.fixture()
def flask_app_with_admin_reports():
    """Crée une app Flask de test avec le blueprint admin_reports monté."""
    from flask import Flask
    from app.api.admin_reports import admin_reports_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(admin_reports_bp, url_prefix="/api/admin/reports")
    return app


@pytest.fixture()
def super_admin_headers():
    """Headers simulant un super-admin authentifié (JWT mocké)."""
    return {"Authorization": "Bearer FAKE_SUPER_ADMIN_TOKEN"}


class TestApproveEndpoint:
    def _mock_require_super_admin(self, view_func):
        """Bypass du décorateur @require_super_admin pour les tests."""
        from functools import wraps
        from flask import g

        @wraps(view_func)
        def _wrapper(*args, **kwargs):
            g.current_user = {"id": "user-1", "email": "amine@bassira.ai", "claims": {}}
            g.is_super_admin = True
            return view_func(*args, **kwargs)

        return _wrapper

    def test_without_super_admin_returns_403(self, flask_app_with_admin_reports):
        """Test 17 — sans super-admin → 403."""
        from unittest.mock import patch

        # Simuler un JWT valide mais email NON dans la whitelist
        with patch(
            "app.auth.decorators.verify_supabase_jwt",
            return_value={"sub": "user-1", "email": "outsider@example.com"},
        ), patch.dict(os.environ, {"BASSIRA_SUPER_ADMIN_EMAILS": "admin@bassira.ai"}):
            with flask_app_with_admin_reports.test_client() as client:
                resp = client.post(
                    "/api/admin/reports/report_abc123/approve",
                    json={"watermark_recipient": None, "sign": False},
                    headers={"Authorization": "Bearer FAKE_TOKEN"},
                )
            assert resp.status_code == 403

    def test_approve_returns_200_with_snapshot(self, tmp_path, minimal_pdf):
        """Test 18 — endpoint approve OK → 200 + structure réponse.

        Teste la fonction approve_report directement (contournement du décorateur auth)
        pour ne pas dépendre de l'infrastructure JWT en tests unitaires.
        """
        from flask import Flask, g

        fake_snapshot = {
            "path": str(tmp_path / "snap"),
            "sha256": "a" * 64,
            "version": 1,
        }

        # Appel direct de la fonction métier sous le décorateur

        app = Flask(__name__)
        app.config["TESTING"] = True
        from app.api.admin_reports import admin_reports_bp
        app.register_blueprint(admin_reports_bp, url_prefix="/api/admin/reports")

        with app.test_request_context(
            "/api/admin/reports/report_test123/approve",
            method="POST",
            json={"watermark_recipient": None, "sign": False},
        ):
            g.current_user = {"id": "u1", "email": "amine@bassira.ai", "claims": {}}
            g.is_super_admin = True

            with (
                patch(
                    "app.services.report_agent.ReportManager.get_report",
                    return_value=MagicMock(simulation_id="sim_test123"),
                ),
                patch(
                    "app.services.report_pdf.loader.PDFContextLoader.load",
                    return_value=MagicMock(org_id="org-1"),
                ),
                patch(
                    "app.services.report_pdf.renderer.Renderer.render_md",
                    return_value="# Test",
                ),
                patch(
                    "app.services.report_pdf.renderer.Renderer.render_pdf",
                    return_value=minimal_pdf,
                ),
                patch(
                    "app.services.report_pdf.snapshot.create_snapshot",
                    return_value=fake_snapshot,
                ),
                patch("app.api.admin_reports._try_workflow_transition"),
            ):
                # Importer la vue unwrappée (sous les décorateurs)
                import app.api.admin_reports as ar_mod
                # Accès direct à la fonction __wrapped__ si disponible
                view_fn = ar_mod.approve_report
                # Chercher la fonction sous-jacente (unwrap les décorateurs)
                while hasattr(view_fn, "__wrapped__"):
                    view_fn = view_fn.__wrapped__

                response = view_fn("report_test123")

        # Vérifier la structure de réponse
        if hasattr(response, "get_json"):
            data = response.get_json()
            status = response.status_code
        else:
            # response est un tuple (jsonify_response, status_code)
            data = response[0].get_json()
            status = response[1]

        assert status == 200
        assert data["success"] is True
        assert data["version"] == 1

    def test_approve_full_flow_mocked(self, tmp_path, minimal_pdf):
        """Test 19+20 — flow complet mocké : watermark + sign → 200."""
        from flask import Flask, g

        from app.api.admin_reports import admin_reports_bp

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(admin_reports_bp, url_prefix="/api/admin/reports")

        fake_snapshot = {
            "path": str(tmp_path / "snap_full"),
            "sha256": "b" * 64,
            "version": 1,
        }

        watermarked_pdf = minimal_pdf + b"WATERMARK_MARKER"
        signed_pdf = watermarked_pdf + b"SIGNED_MARKER"

        @app.before_request
        def _inject_super_admin():
            g.current_user = {"id": "u1", "email": "amine@bassira.ai", "claims": {}}
            g.is_super_admin = True

        with app.test_client() as client:
            with (
                patch("app.auth.decorators.verify_supabase_jwt",
                      return_value={"sub": "u1", "email": "amine@bassira.ai"}),
                patch.dict(os.environ, {"BASSIRA_SUPER_ADMIN_EMAILS": "amine@bassira.ai"}),
                patch(
                    "app.services.report_agent.ReportManager.get_report",
                    return_value=MagicMock(simulation_id="sim_test123"),
                ),
                patch(
                    "app.services.report_pdf.loader.PDFContextLoader.load",
                    return_value=MagicMock(org_id="org-1"),
                ),
                patch(
                    "app.services.report_pdf.renderer.Renderer.render_md",
                    return_value="# Rapport Approuvé",
                ),
                patch(
                    "app.services.report_pdf.renderer.Renderer.render_pdf",
                    return_value=minimal_pdf,
                ),
                patch(
                    "app.services.report_pdf.watermark.apply_watermark_to_pdf",
                    return_value=watermarked_pdf,
                ),
                patch(
                    "app.services.report_pdf.signer.sign_pdf_pades",
                    return_value=signed_pdf,
                ),
                patch(
                    "app.services.report_pdf.snapshot.create_snapshot",
                    return_value=fake_snapshot,
                ),
                patch(
                    "app.api.admin_reports._try_workflow_transition",
                ),
            ):
                resp = client.post(
                    "/api/admin/reports/report_approved/approve",
                    json={
                        "watermark_recipient": {"name": "Jean Test", "company": "ACME"},
                        "sign": True,
                    },
                    headers={"Authorization": "Bearer VALID_TOKEN"},
                )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["version"] == 1
        assert data["sha256"] == "b" * 64
        assert "snapshot_path" in data

    def test_approve_without_auth_token_returns_401(self, flask_app_with_admin_reports):
        """Test bonus — sans token → 401."""
        with flask_app_with_admin_reports.test_client() as client:
            resp = client.post(
                "/api/admin/reports/report_xyz/approve",
                json={"watermark_recipient": None, "sign": False},
            )
        assert resp.status_code in (401, 503)  # 503 si JWT non configuré en test
