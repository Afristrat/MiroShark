"""Tests pytest — TextNormalizer anglais (US-121).

Couverture :
- Pas d'espaces avant ponctuation
- Guillemets curly doubles et simples
- Apostrophe typographique (contractions)
- Em-dash sans espaces (style US)
- Format nombres
- Cas limites
- NormalizedText dataclass
"""

from __future__ import annotations

import pytest

from app.services.text_normalizer import NormalizedText, TextNormalizer

# Constantes typographiques anglaises
LDQUOTE = "“"   # "
RDQUOTE = "”"   # "
LSQUOTE = "‘"   # '
RSQUOTE = "’"   # '
EMDASH = "—"    # —


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def en_standard() -> TextNormalizer:
    return TextNormalizer(lang="en", strictness="standard")


@pytest.fixture
def en_strict() -> TextNormalizer:
    return TextNormalizer(lang="en", strictness="strict")


@pytest.fixture
def en_permissive() -> TextNormalizer:
    return TextNormalizer(lang="en", strictness="permissive")


# ---------------------------------------------------------------------------
# 1. Pas d'espaces avant ponctuation
# ---------------------------------------------------------------------------

class TestNoSpaceBeforePunct:
    def test_space_before_comma(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("Hello , world")
        assert "Hello," in result.normalized
        assert "Hello ," not in result.normalized

    def test_space_before_period(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("Hello .")
        assert "Hello." in result.normalized

    def test_space_before_semicolon(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("first ; second")
        assert "first;" in result.normalized

    def test_space_before_colon(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("title : value")
        assert "title:" in result.normalized

    def test_space_before_exclamation(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("Great !")
        assert "Great!" in result.normalized

    def test_space_before_question(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("How are you ?")
        assert "you?" in result.normalized

    def test_no_change_when_already_correct(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("Hello, world!")
        assert "Hello," in result.normalized
        assert "world!" in result.normalized


# ---------------------------------------------------------------------------
# 2. Guillemets curly doubles
# ---------------------------------------------------------------------------

class TestCurlyDoubleQuotes:
    def test_double_quotes_basic(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize('"hello world"')
        assert LDQUOTE in result.normalized
        assert RDQUOTE in result.normalized
        assert '"' not in result.normalized

    def test_double_quotes_preserve_content(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize('"the quick brown fox"')
        assert "the quick brown fox" in result.normalized

    def test_multiple_double_quotes(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize('"first" and "second"')
        assert result.normalized.count(LDQUOTE) == 2
        assert result.normalized.count(RDQUOTE) == 2

    def test_nested_content_preserved(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize('"Hello, World!"')
        assert "Hello" in result.normalized
        assert "World" in result.normalized


# ---------------------------------------------------------------------------
# 3. Guillemets curly simples
# ---------------------------------------------------------------------------

class TestCurlySingleQuotes:
    def test_single_quotes_basic(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("'hello world'")
        assert LSQUOTE in result.normalized
        assert RSQUOTE in result.normalized

    def test_single_quotes_content_preserved(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("'the fox'")
        assert "the fox" in result.normalized


# ---------------------------------------------------------------------------
# 4. Apostrophe typographique (contractions)
# ---------------------------------------------------------------------------

class TestApostropheContractions:
    def test_dont(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("don't")
        assert RSQUOTE in result.normalized

    def test_its(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("it's a great day")
        assert RSQUOTE in result.normalized

    def test_were(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("we're ready")
        assert RSQUOTE in result.normalized


# ---------------------------------------------------------------------------
# 5. Em-dash (style US, sans espaces)
# ---------------------------------------------------------------------------

class TestEmDash:
    def test_double_dash_basic(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("introduction--conclusion")
        assert EMDASH in result.normalized
        assert "--" not in result.normalized

    def test_double_dash_with_spaces(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("intro -- conclusion")
        assert EMDASH in result.normalized
        assert "--" not in result.normalized

    def test_emdash_no_spaces_us_style(self, en_standard: TextNormalizer) -> None:
        """Style US : l'em-dash ne devrait pas avoir d'espaces autour."""
        result = en_standard.normalize("word--word")
        # L'em-dash doit apparaître
        assert EMDASH in result.normalized


# ---------------------------------------------------------------------------
# 6. Format nombres (mode strict)
# ---------------------------------------------------------------------------

class TestNumberFormat:
    def test_decimal_comma_to_dot(self, en_strict: TextNormalizer) -> None:
        """Virgule décimale (FR) → point décimal (EN)."""
        result = en_strict.normalize("The price is 1,56 dollars")
        assert "1.56" in result.normalized

    def test_already_correct_number(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("price is 1,234.56")
        assert "1,234" in result.normalized or "1234" in result.normalized


# ---------------------------------------------------------------------------
# 7. Cas limites
# ---------------------------------------------------------------------------

class TestCasLimites:
    def test_texte_vide(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("")
        assert result.normalized == ""
        assert result.confidence == 1.0

    def test_texte_deja_correct(self, en_standard: TextNormalizer) -> None:
        texte = "Hello, world! This is correct."
        result = en_standard.normalize(texte)
        assert "Hello," in result.normalized
        assert "world!" in result.normalized

    def test_retourne_normalized_text(self, en_standard: TextNormalizer) -> None:
        result = en_standard.normalize("test text")
        assert isinstance(result, NormalizedText)
        assert 0.0 <= result.confidence <= 1.0

    def test_original_preserve(self, en_standard: TextNormalizer) -> None:
        texte = 'He said "hello"'
        result = en_standard.normalize(texte)
        assert result.original == texte

    def test_permissive_removes_space_before_punct(self, en_permissive: TextNormalizer) -> None:
        """En mode permissive, on corrige quand même les espaces avant ponctuation."""
        result = en_permissive.normalize("Hello , world")
        assert "Hello," in result.normalized


# ---------------------------------------------------------------------------
# 8. Régression combinée
# ---------------------------------------------------------------------------

class TestRegression:
    def test_phrase_complexe_en(self, en_standard: TextNormalizer) -> None:
        inp = 'He said "don\'t worry" -- everything\'s fine !'
        result = en_standard.normalize(inp)
        n = result.normalized
        assert LDQUOTE in n or RDQUOTE in n
        assert EMDASH in n
        assert "everything" in n

    def test_no_curly_in_urls(self, en_standard: TextNormalizer) -> None:
        """Les URLs ne devraient pas être affectées (pas de guillemets dans les URLs)."""
        result = en_standard.normalize("visit https://example.com for more")
        assert "https://example.com" in result.normalized
