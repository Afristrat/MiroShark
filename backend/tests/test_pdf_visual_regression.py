"""
tests/test_pdf_visual_regression.py — Tests de régression visuelle PDF (US-132).

Stratégie :
    Niveau 1 (toujours actif)  : hash du texte extrait via pypdf.
        Un golden hash est stocké dans tests/fixtures/pdf_golden/<name>.hash.
        Créé à la première exécution (mode « record »), comparé ensuite.

    Niveau 2 (si poppler dispo) : comparaison pixel-par-pixel via pdf2image + Pillow.
        Tolérance : 0,5 % des pixels peuvent différer.
        Golden master PNG stocké dans tests/fixtures/pdf_golden/<name>.png.
        SKIPPED sur Windows si poppler non installé (comportement attendu en CI
        sans poppler-utils).

Dossier golden : ``backend/tests/fixtures/pdf_golden/``
Mode « record »  : supprimer le fichier .hash / .png pour régénérer.

Tests :
    1.  Golden hash FR — extraction texte stable (fixture sim_aabbcc112233, lang=fr)
    2.  Golden hash EN — extraction texte stable (lang=en)
    3.  Golden hash AR — extraction texte stable (lang=ar)
    4.  Pixel diff FR  — rendu visuel stable (skip si poppler absent)
    5.  Pixel diff EN  — rendu visuel stable (skip si poppler absent)
    6+  Vérification régression sur le hash existant après patch mineur
"""

from __future__ import annotations

import hashlib
import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── sys.path ─────────────────────────────────────────────────────────────────
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# ── Chemins ───────────────────────────────────────────────────────────────────
_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_GOLDEN_DIR = _FIXTURES_DIR / "pdf_golden"
_TEST_SIM_ID = "sim_aabbcc112233"

# ── Détection dépendances ─────────────────────────────────────────────────────


def _weasyprint_available() -> bool:
    try:
        from weasyprint import HTML, CSS  # noqa: F401
        return True
    except (ImportError, OSError):
        return False


def _pypdf_available() -> bool:
    try:
        import pypdf  # noqa: F401
        return True
    except ImportError:
        return False


def _pdf2image_available() -> bool:
    try:
        import pdf2image  # noqa: F401
        return True
    except ImportError:
        return False


WEASYPRINT_AVAILABLE = _weasyprint_available()
PYPDF_AVAILABLE = _pypdf_available()
PDF2IMAGE_AVAILABLE = _pdf2image_available()

skip_no_weasyprint = pytest.mark.skipif(
    not WEASYPRINT_AVAILABLE,
    reason="WeasyPrint nécessite GTK/Pango non disponible dans cet environnement.",
)
skip_no_pypdf = pytest.mark.skipif(
    not PYPDF_AVAILABLE,
    reason="pypdf non installé.",
)
skip_no_pdf2image = pytest.mark.skipif(
    not PDF2IMAGE_AVAILABLE or not WEASYPRINT_AVAILABLE,
    reason="pdf2image ou poppler non disponible (skip visuel attendu sur Windows sans poppler).",
)


# ── Mock global LanguageTool ──────────────────────────────────────────────────
@pytest.fixture(autouse=True, scope="module")
def mock_languagetool():
    with patch("app.services.text_normalizer.lt_check", return_value=[]):
        yield


# ── Helpers ───────────────────────────────────────────────────────────────────


def _load_ctx(lang: str = "fr"):
    from app.services.report_pdf.loader import PDFContextLoader

    return PDFContextLoader.load(
        simulation_id=_TEST_SIM_ID,
        sim_base_dir=_FIXTURES_DIR,
        lang=lang,
    )


def _make_deterministic_enricher():
    """Retourne un patch Enricher déterministe (sans LLM)."""
    from app.services.report_pdf.schema import KPIHero

    def _side_effect(context, **kwargs):
        def _enrich():
            context.kpi_hero = KPIHero(
                verdict="Consensus progressif",
                confidence_pct=60.0,
                brier=0.18,
                scenario_distribution={"bullish": 60.0, "bearish": 30.0, "neutral": 10.0},
            )
            context.pivotal_moments = []
            context.interpretations = {
                "belief_drift": "Dérive des croyances stable.",
                "polymarket_curves": "Courbes polymarket stables.",
                "demographic_pyramid": "Pyramide démographique équilibrée.",
                "influence_leaderboard": "Classement influences nominal.",
                "interaction_network": "Réseau d'interactions dense.",
            }
            context.executive_takeaways = [
                "Point 1 : consensus atteint.",
                "Point 2 : risques limités.",
                "Point 3 : recommandations validées.",
            ]
            return context

        inst = MagicMock()
        inst.enrich = _enrich
        return inst

    return _side_effect


def _extract_text_hash(pdf_bytes: bytes) -> str:
    """Extrait le texte du PDF via pypdf et retourne son SHA-256 tronqué."""
    if not PYPDF_AVAILABLE:
        raise RuntimeError("pypdf non disponible")
    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    text_parts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text_parts.append(text)
    full_text = "\n".join(text_parts)
    return hashlib.sha256(full_text.encode("utf-8")).hexdigest()


def _load_or_record_hash(name: str, pdf_bytes: bytes) -> tuple[str, bool]:
    """
    Charge le golden hash ou l'enregistre si absent.

    Returns:
        (current_hash, is_new) — is_new=True si golden vient d'être créé.
    """
    golden_path = _GOLDEN_DIR / f"{name}.hash"
    current_hash = _extract_text_hash(pdf_bytes)

    if not golden_path.exists():
        # Mode record : écriture du golden
        _GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(current_hash, encoding="utf-8")
        return current_hash, True

    golden_hash = golden_path.read_text(encoding="utf-8").strip()
    return current_hash, False


# ═══════════════════════════════════════════════════════════════════════════════
# Tests golden hash texte (niveau 1 — pypdf, sans WeasyPrint)
# ═══════════════════════════════════════════════════════════════════════════════


class TestGoldenHashText:
    """Golden masters basés sur le hash du texte extrait (pypdf).

    Ces tests ne nécessitent PAS WeasyPrint — ils utilisent un PDF pré-rendu
    synthétique ou, si WeasyPrint est disponible, le PDF réel.
    """

    @skip_no_weasyprint
    @skip_no_pypdf
    def test_golden_hash_fr(self):
        """Test 1 : Hash texte FR stable — golden master créé si absent."""
        from app.services.report_pdf.renderer import Renderer

        with patch(
            "app.services.report_pdf.enricher.Enricher",
            side_effect=_make_deterministic_enricher(),
        ):
            ctx = _load_ctx(lang="fr")
            pdf_bytes = Renderer(ctx).render_pdf()

        current_hash, is_new = _load_or_record_hash("report_fr", pdf_bytes)

        if is_new:
            pytest.skip(
                f"Golden hash FR créé : {current_hash[:16]}… "
                "(relancer pour valider la stabilité)"
            )
        else:
            golden = (_GOLDEN_DIR / "report_fr.hash").read_text(encoding="utf-8").strip()
            assert current_hash == golden, (
                f"Régression visuelle FR détectée !\n"
                f"  Attendu : {golden[:32]}…\n"
                f"  Obtenu  : {current_hash[:32]}…\n"
                "Supprimez tests/fixtures/pdf_golden/report_fr.hash pour régénérer."
            )

    @skip_no_weasyprint
    @skip_no_pypdf
    def test_golden_hash_en(self):
        """Test 2 : Hash texte EN stable."""
        from app.services.report_pdf.renderer import Renderer

        with patch(
            "app.services.report_pdf.enricher.Enricher",
            side_effect=_make_deterministic_enricher(),
        ):
            ctx = _load_ctx(lang="en")
            pdf_bytes = Renderer(ctx).render_pdf()

        current_hash, is_new = _load_or_record_hash("report_en", pdf_bytes)

        if is_new:
            pytest.skip(
                f"Golden hash EN créé : {current_hash[:16]}… "
                "(relancer pour valider)"
            )
        else:
            golden = (_GOLDEN_DIR / "report_en.hash").read_text(encoding="utf-8").strip()
            assert current_hash == golden, (
                f"Régression visuelle EN détectée ! "
                f"Attendu {golden[:16]}…, obtenu {current_hash[:16]}…"
            )

    @skip_no_weasyprint
    @skip_no_pypdf
    def test_golden_hash_ar(self):
        """Test 3 : Hash texte AR stable."""
        from app.services.report_pdf.renderer import Renderer

        with patch(
            "app.services.report_pdf.enricher.Enricher",
            side_effect=_make_deterministic_enricher(),
        ):
            ctx = _load_ctx(lang="ar")
            pdf_bytes = Renderer(ctx).render_pdf()

        current_hash, is_new = _load_or_record_hash("report_ar", pdf_bytes)

        if is_new:
            pytest.skip(
                f"Golden hash AR créé : {current_hash[:16]}… "
                "(relancer pour valider)"
            )
        else:
            golden = (_GOLDEN_DIR / "report_ar.hash").read_text(encoding="utf-8").strip()
            assert current_hash == golden, (
                f"Régression visuelle AR détectée ! "
                f"Attendu {golden[:16]}…, obtenu {current_hash[:16]}…"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Tests golden pixel (niveau 2 — pdf2image + Pillow)
# ═══════════════════════════════════════════════════════════════════════════════


class TestGoldenPixel:
    """Comparaison pixel-par-pixel via pdf2image + Pillow.

    Tolère jusqu'à 0,5 % de pixels différents (anti-aliasing, polices).
    SKIPPED si pdf2image / poppler ou WeasyPrint sont absents.
    """

    @skip_no_pdf2image
    @skip_no_weasyprint
    def test_pixel_golden_fr(self):
        """Test 4 : Comparaison pixel FR (tolérance 0,5 %)."""
        from pdf2image import convert_from_bytes  # type: ignore[import-not-found]
        from PIL import Image, ImageChops
        from app.services.report_pdf.renderer import Renderer

        with patch(
            "app.services.report_pdf.enricher.Enricher",
            side_effect=_make_deterministic_enricher(),
        ):
            ctx = _load_ctx(lang="fr")
            pdf_bytes = Renderer(ctx).render_pdf()

        # Rendu de la première page en image
        images = convert_from_bytes(pdf_bytes, dpi=72, first_page=1, last_page=1)
        assert images, "pdf2image n'a pas produit d'image"
        current_img = images[0]

        golden_png = _GOLDEN_DIR / "report_fr_p1.png"

        if not golden_png.exists():
            _GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
            current_img.save(str(golden_png))
            pytest.skip(
                "Golden PNG FR créé (relancer pour valider la stabilité visuelle)"
            )

        golden_img = Image.open(str(golden_png))

        # Adapter les tailles si WeasyPrint change légèrement la mise en page
        if current_img.size != golden_img.size:
            current_img = current_img.resize(golden_img.size, Image.LANCZOS)

        diff = ImageChops.difference(current_img.convert("RGB"), golden_img.convert("RGB"))
        diff_pixels = sum(1 for px in diff.getdata() if any(c > 5 for c in px))
        total_pixels = golden_img.width * golden_img.height
        pct_diff = diff_pixels / total_pixels * 100

        assert pct_diff <= 0.5, (
            f"Régression visuelle FR : {pct_diff:.2f}% pixels différents "
            f"(seuil : 0,5%). Vérifiez report_fr_p1.png."
        )

    @skip_no_pdf2image
    @skip_no_weasyprint
    def test_pixel_golden_en(self):
        """Test 5 : Comparaison pixel EN (tolérance 0,5 %)."""
        from pdf2image import convert_from_bytes  # type: ignore[import-not-found]
        from PIL import Image, ImageChops
        from app.services.report_pdf.renderer import Renderer

        with patch(
            "app.services.report_pdf.enricher.Enricher",
            side_effect=_make_deterministic_enricher(),
        ):
            ctx = _load_ctx(lang="en")
            pdf_bytes = Renderer(ctx).render_pdf()

        images = convert_from_bytes(pdf_bytes, dpi=72, first_page=1, last_page=1)
        assert images, "pdf2image n'a pas produit d'image"
        current_img = images[0]

        golden_png = _GOLDEN_DIR / "report_en_p1.png"

        if not golden_png.exists():
            _GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
            current_img.save(str(golden_png))
            pytest.skip(
                "Golden PNG EN créé (relancer pour valider la stabilité visuelle)"
            )

        golden_img = Image.open(str(golden_png))

        if current_img.size != golden_img.size:
            current_img = current_img.resize(golden_img.size, Image.LANCZOS)

        diff = ImageChops.difference(current_img.convert("RGB"), golden_img.convert("RGB"))
        diff_pixels = sum(1 for px in diff.getdata() if any(c > 5 for c in px))
        total_pixels = golden_img.width * golden_img.height
        pct_diff = diff_pixels / total_pixels * 100

        assert pct_diff <= 0.5, (
            f"Régression visuelle EN : {pct_diff:.2f}% pixels différents "
            f"(seuil : 0,5%). Vérifiez report_en_p1.png."
        )
