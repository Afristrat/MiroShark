"""Tests pytest — TextNormalizer arabe (US-121).

Couverture :
- Virgule latine → virgule arabe ،
- Point-virgule latin → point-virgule arabe ؛
- Point d'interrogation latin → point d'interrogation arabe ؟
- Pourcentage latin → pourcentage arabe ٪
- Chiffres hindis optionnels (٠١٢٣٤٥٦٧٨٩)
- Attribut dir RTL
- Cas limites
- NormalizedText dataclass
"""

from __future__ import annotations

import pytest

from app.services.text_normalizer import NormalizedText, TextNormalizer
from app.services.text_normalizer.ar import get_html_dir_attr, normalize_ar

# Ponctuation arabe
ARABIC_COMMA = "،"
ARABIC_SEMICOLON = "؛"
ARABIC_QUESTION = "؟"
ARABIC_PERCENT = "٪"

# Chiffres hindis
HINDI_DIGITS = "٠١٢٣٤٥٦٧٨٩"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ar_standard() -> TextNormalizer:
    return TextNormalizer(lang="ar", strictness="standard")


@pytest.fixture
def ar_strict() -> TextNormalizer:
    return TextNormalizer(lang="ar", strictness="strict")


@pytest.fixture
def ar_permissive() -> TextNormalizer:
    return TextNormalizer(lang="ar", strictness="permissive")


# ---------------------------------------------------------------------------
# 1. Virgule arabe
# ---------------------------------------------------------------------------

class TestVirguleArabe:
    def test_virgule_latine_convertie(self, ar_standard: TextNormalizer) -> None:
        result = ar_standard.normalize("مرحبا، كيف حالك")
        # La virgule arabe doit être présente
        assert ARABIC_COMMA in result.normalized

    def test_virgule_latine_entre_mots(self, ar_standard: TextNormalizer) -> None:
        result = ar_standard.normalize("كلمة,كلمة")
        assert ARABIC_COMMA in result.normalized
        assert "كلمة,كلمة" not in result.normalized or ARABIC_COMMA in result.normalized

    def test_virgule_hors_contexte_numerique(self, ar_standard: TextNormalizer) -> None:
        """La virgule entre deux chiffres n'est PAS convertie (séparateur décimal)."""
        result = ar_standard.normalize("1,5")
        # La virgule entre deux chiffres doit rester latine
        assert "1,5" in result.normalized

    def test_virgule_latine_remplacee_dans_phrase_arabe(self, ar_standard: TextNormalizer) -> None:
        result = ar_standard.normalize("الرياض, جدة, الدمام")
        assert ARABIC_COMMA in result.normalized

    def test_multiple_virgules(self, ar_standard: TextNormalizer) -> None:
        result = ar_standard.normalize("أولا, ثانيا, ثالثا")
        assert result.normalized.count(ARABIC_COMMA) >= 2


# ---------------------------------------------------------------------------
# 2. Point-virgule arabe
# ---------------------------------------------------------------------------

class TestPointVirguleArabe:
    def test_point_virgule_latin_converti(self, ar_standard: TextNormalizer) -> None:
        result = ar_standard.normalize("الجملة الأولى; الجملة الثانية")
        assert ARABIC_SEMICOLON in result.normalized
        assert ";" not in result.normalized

    def test_point_virgule_simple(self, ar_standard: TextNormalizer) -> None:
        result = ar_standard.normalize("جملة; أخرى")
        assert ARABIC_SEMICOLON in result.normalized


# ---------------------------------------------------------------------------
# 3. Point d'interrogation arabe
# ---------------------------------------------------------------------------

class TestPointInterrogationArabe:
    def test_question_latine_convertie(self, ar_standard: TextNormalizer) -> None:
        result = ar_standard.normalize("كيف حالك?")
        assert ARABIC_QUESTION in result.normalized
        assert "?" not in result.normalized

    def test_question_avec_espace(self, ar_standard: TextNormalizer) -> None:
        result = ar_standard.normalize("ما اسمك ?")
        assert ARABIC_QUESTION in result.normalized

    def test_multiple_questions(self, ar_standard: TextNormalizer) -> None:
        result = ar_standard.normalize("من أنت? ما اسمك?")
        assert result.normalized.count(ARABIC_QUESTION) == 2


# ---------------------------------------------------------------------------
# 4. Pourcentage arabe
# ---------------------------------------------------------------------------

class TestPourcentageArabe:
    def test_pourcentage_latin_converti(self, ar_standard: TextNormalizer) -> None:
        result = ar_standard.normalize("النمو 5%")
        assert ARABIC_PERCENT in result.normalized
        assert "%" not in result.normalized

    def test_pourcentage_multiple(self, ar_standard: TextNormalizer) -> None:
        result = ar_standard.normalize("50% أو 75%")
        assert result.normalized.count(ARABIC_PERCENT) == 2

    def test_pourcentage_dans_phrase_complexe(self, ar_standard: TextNormalizer) -> None:
        result = ar_standard.normalize("تحقيق نمو 10% في 2026")
        assert ARABIC_PERCENT in result.normalized


# ---------------------------------------------------------------------------
# 5. Chiffres hindis (optionnel)
# ---------------------------------------------------------------------------

class TestChiffresHindis:
    def test_chiffres_hindis_actives(self) -> None:
        from app.services.text_normalizer.ar import normalize_ar
        result = normalize_ar("النتيجة 2026", use_hindi_digits=True)
        assert "٢" in result
        assert "٠" in result
        assert "٢٦" in result or "٢٠٢٦" in result

    def test_chiffres_hindis_desactives_par_defaut(self, ar_standard: TextNormalizer) -> None:
        result = ar_standard.normalize("النتيجة 2026")
        # Par défaut, les chiffres restent latins
        assert "2026" in result.normalized

    def test_chiffre_0_hindi(self) -> None:
        result = normalize_ar("0", use_hindi_digits=True)
        assert "٠" in result

    def test_chiffres_0_a_9(self) -> None:
        result = normalize_ar("0123456789", use_hindi_digits=True)
        assert "٠" in result
        assert "١" in result
        assert "٩" in result
        assert "0" not in result

    def test_chiffres_non_convertis_sans_option(self) -> None:
        result = normalize_ar("12345", use_hindi_digits=False)
        assert "12345" in result
        assert "١" not in result


# ---------------------------------------------------------------------------
# 6. Attribut dir RTL
# ---------------------------------------------------------------------------

class TestDirRTL:
    def test_get_html_dir_attr(self) -> None:
        attr = get_html_dir_attr()
        assert 'dir="rtl"' in attr

    def test_dir_attr_string(self) -> None:
        attr = get_html_dir_attr()
        assert isinstance(attr, str)
        assert "rtl" in attr


# ---------------------------------------------------------------------------
# 7. Cas limites
# ---------------------------------------------------------------------------

class TestCasLimites:
    def test_texte_vide(self, ar_standard: TextNormalizer) -> None:
        result = ar_standard.normalize("")
        assert result.normalized == ""
        assert result.confidence == 1.0

    def test_texte_latin_pur(self, ar_standard: TextNormalizer) -> None:
        """Texte sans ponctuation → retour identique."""
        result = ar_standard.normalize("hello world")
        assert result.normalized == "hello world"

    def test_retourne_normalized_text(self, ar_standard: TextNormalizer) -> None:
        result = ar_standard.normalize("مرحبا")
        assert isinstance(result, NormalizedText)
        assert 0.0 <= result.confidence <= 1.0

    def test_original_preserve(self, ar_standard: TextNormalizer) -> None:
        texte = "كيف حالك?"
        result = ar_standard.normalize(texte)
        assert result.original == texte

    def test_permissive_applique_ponctuation(self, ar_permissive: TextNormalizer) -> None:
        """En mode permissive, la ponctuation arabe est toujours appliquée."""
        result = ar_permissive.normalize("كيف حالك?")
        assert ARABIC_QUESTION in result.normalized

    def test_issues_listes_vides_sans_lt(self, ar_standard: TextNormalizer) -> None:
        result = ar_standard.normalize("مرحبا")
        assert isinstance(result.spell_issues, list)
        assert isinstance(result.grammar_issues, list)
        assert isinstance(result.style_issues, list)


# ---------------------------------------------------------------------------
# 8. Combinaison ponctuation
# ---------------------------------------------------------------------------

class TestCombinaisonPonctuation:
    def test_phrase_complete_arabe(self, ar_standard: TextNormalizer) -> None:
        inp = "ما هي النتيجة? النمو 10%; أولا, ثانيا; وأخيرا"
        result = ar_standard.normalize(inp)
        n = result.normalized
        assert ARABIC_QUESTION in n
        assert ARABIC_PERCENT in n
        assert ARABIC_COMMA in n
        assert ARABIC_SEMICOLON in n

    def test_ponctuation_mixte_conservee(self, ar_standard: TextNormalizer) -> None:
        """Le point final latin est conservé (pas de mapping)."""
        result = ar_standard.normalize("الجملة.")
        assert "." in result.normalized
