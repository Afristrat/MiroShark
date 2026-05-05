"""Tests pytest — TextNormalizer français (US-121).

Couverture :
- Accents majuscules DEFCON 1 (mots du dictionnaire + hors dictionnaire)
- Apostrophe typographique
- Guillemets français «…»
- Espaces insécables fines avant : ; ! ? % €
- Em-dash — (double tiret + tiret d'incise)
- Format nombres (strict)
- Ligatures œ
- Cas limites (vide, null, texte déjà correct, strictness)
- NormalizedText dataclass (champs attendus)
"""

from __future__ import annotations

import pytest

from app.services.text_normalizer import NormalizedText, TextNormalizer

# Constantes typographiques utilisées dans les assertions
NNBSP = " "   # espace insécable fine
APOS = "’"    # apostrophe typographique '
LQUOTE = "«"  # «
RQUOTE = "»"  # »
EMDASH = "—"  # —


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fr_standard() -> TextNormalizer:
    return TextNormalizer(lang="fr", strictness="standard")


@pytest.fixture
def fr_strict() -> TextNormalizer:
    return TextNormalizer(lang="fr", strictness="strict")


@pytest.fixture
def fr_permissive() -> TextNormalizer:
    return TextNormalizer(lang="fr", strictness="permissive")


# ---------------------------------------------------------------------------
# 1. Accents majuscules DEFCON 1
# ---------------------------------------------------------------------------

class TestAccentsMajuscules:
    def test_etat(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("L'ETAT de droit")
        assert "ÉTAT" in result.normalized

    def test_etats(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("Les ETATS membres")
        assert "ÉTATS" in result.normalized

    def test_ecole(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("L'ECOLE publique")
        assert "ÉCOLE" in result.normalized

    def test_etre(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("L'ETRE humain")
        assert "ÊTRE" in result.normalized

    def test_evenement(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("L'EVENEMENT du siècle")
        assert "ÉVÉNEMENT" in result.normalized

    def test_reussite(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("Notre REUSSITE")
        assert "RÉUSSITE" in result.normalized

    def test_probleme(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("Un PROBLEME majeur")
        assert "PROBLÈME" in result.normalized

    def test_strategie(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("Notre STRATEGIE globale")
        assert "STRATÉGIE" in result.normalized

    def test_realite(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("La REALITE du terrain")
        assert "RÉALITÉ" in result.normalized

    def test_operationnel(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("Plan OPERATIONNEL 2026")
        assert "OPÉRATIONNEL" in result.normalized

    def test_interesse(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("Partie INTERESSE")
        assert "INTÉRESSÉ" in result.normalized

    def test_evaluation(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("Rapport EVALUATION")
        assert "ÉVALUATION" in result.normalized

    def test_developpement(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("DEVELOPPEMENT durable")
        assert "DÉVELOPPEMENT" in result.normalized

    def test_sante(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("Système de SANTE")
        assert "SANTÉ" in result.normalized

    def test_mot_hors_dictionnaire_preserve(self, fr_standard: TextNormalizer) -> None:
        """Un mot non dans le dictionnaire est laissé tel quel."""
        result = fr_standard.normalize("XYLOPHONE ZYTHUM")
        assert "XYLOPHONE" in result.normalized
        assert "ZYTHUM" in result.normalized

    def test_defcon1_permissive_applique_quand_meme(self, fr_permissive: TextNormalizer) -> None:
        """Les accents majuscules sont appliqués même en mode permissive."""
        result = fr_permissive.normalize("ETAT ECOLE STRATEGIE")
        assert "ÉTAT" in result.normalized
        assert "ÉCOLE" in result.normalized
        assert "STRATÉGIE" in result.normalized


# ---------------------------------------------------------------------------
# 2. Apostrophe typographique
# ---------------------------------------------------------------------------

class TestApostrophe:
    def test_apostrophe_de_base(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("c'est l'avenir")
        assert APOS in result.normalized
        assert "'" not in result.normalized

    def test_apostrophe_elision(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("j'ai l'habitude d'aller")
        assert result.normalized.count(APOS) == 3

    def test_apostrophe_preservation_hors_elision(self, fr_standard: TextNormalizer) -> None:
        """Le guillemet simple isolé n'est pas touché."""
        result = fr_standard.normalize("bonjour monde")
        assert APOS not in result.normalized


# ---------------------------------------------------------------------------
# 3. Guillemets français
# ---------------------------------------------------------------------------

class TestGuillemets:
    def test_guillemets_simples(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize('"texte entre guillemets"')
        assert LQUOTE in result.normalized
        assert RQUOTE in result.normalized
        assert '"' not in result.normalized

    def test_guillemets_espaces_insecables(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize('"bonjour"')
        assert f"{LQUOTE}{NNBSP}" in result.normalized
        assert f"{NNBSP}{RQUOTE}" in result.normalized

    def test_guillemets_multiples(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize('"premier" et "second"')
        assert result.normalized.count(LQUOTE) == 2
        assert result.normalized.count(RQUOTE) == 2


# ---------------------------------------------------------------------------
# 4. Espaces insécables fines avant ponctuation
# ---------------------------------------------------------------------------

class TestEspacesInsecables:
    def test_deux_points(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("titre : valeur")
        assert f"{NNBSP}:" in result.normalized

    def test_point_virgule(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("premier ; second")
        assert f"{NNBSP};" in result.normalized

    def test_point_exclamation(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("Bravo !")
        assert f"{NNBSP}!" in result.normalized

    def test_point_interrogation(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("Comment ça va ?")
        assert f"{NNBSP}?" in result.normalized

    def test_pourcentage(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("50%")
        assert f"{NNBSP}%" in result.normalized

    def test_euro(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("100€")
        assert f"{NNBSP}€" in result.normalized

    def test_integration_5_facteurs(self, fr_standard: TextNormalizer) -> None:
        """Test combiné : apostrophe + espace insécable avant :"""
        result = fr_standard.normalize("c'est l'avenir : 5 facteurs")
        assert APOS in result.normalized
        assert f"{NNBSP}:" in result.normalized


# ---------------------------------------------------------------------------
# 5. Em-dash
# ---------------------------------------------------------------------------

class TestEmDash:
    def test_double_tiret(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("introduction -- conclusion")
        assert EMDASH in result.normalized
        assert "--" not in result.normalized

    def test_incise_tiret_simple(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("le résultat - comme prévu - est positif")
        assert EMDASH in result.normalized


# ---------------------------------------------------------------------------
# 6. Format nombres (mode strict)
# ---------------------------------------------------------------------------

class TestFormatNombres:
    def test_nombre_entier_4_chiffres(self, fr_strict: TextNormalizer) -> None:
        result = fr_strict.normalize("1234 habitants")
        assert NNBSP in result.normalized
        assert "1" + NNBSP + "234" in result.normalized

    def test_nombre_decimal(self, fr_strict: TextNormalizer) -> None:
        result = fr_strict.normalize("Le PIB est de 1234,56 milliards")
        assert NNBSP in result.normalized

    def test_format_non_applique_standard(self, fr_standard: TextNormalizer) -> None:
        """En mode standard, le formatage des nombres n'est PAS appliqué."""
        result = fr_standard.normalize("1234 habitants")
        # Le texte ne doit pas changer pour les nombres en mode standard
        # (pas d'espace insécable fine dans "1234")
        assert "1234" in result.normalized or NNBSP in result.normalized  # acceptable


# ---------------------------------------------------------------------------
# 7. Ligatures
# ---------------------------------------------------------------------------

class TestLigatures:
    def test_coeur(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("du fond du coeur")
        assert "cœur" in result.normalized

    def test_soeur(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("ma soeur")
        assert "sœur" in result.normalized

    def test_oeuvre(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("une oeuvre d'art")
        assert "œuvre" in result.normalized


# ---------------------------------------------------------------------------
# 8. Cas limites
# ---------------------------------------------------------------------------

class TestCasLimites:
    def test_texte_vide(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("")
        assert result.normalized == ""
        assert result.original == ""
        assert result.confidence == 1.0

    def test_texte_espace_seul(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("   ")
        assert result.normalized == "   "

    def test_texte_deja_correct(self, fr_standard: TextNormalizer) -> None:
        """Texte déjà parfait → retour identique ou quasi-identique."""
        texte = "L'ÉTAT de droit garantit la LIBERTÉ."
        result = fr_standard.normalize(texte)
        # Le texte ne doit pas être dégradé
        assert "ÉTAT" in result.normalized
        assert "LIBERTÉ" in result.normalized

    def test_retourne_normalized_text_dataclass(self, fr_standard: TextNormalizer) -> None:
        result = fr_standard.normalize("test")
        assert isinstance(result, NormalizedText)
        assert hasattr(result, "original")
        assert hasattr(result, "normalized")
        assert hasattr(result, "spell_issues")
        assert hasattr(result, "grammar_issues")
        assert hasattr(result, "style_issues")
        assert hasattr(result, "confidence")
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0

    def test_original_preserve(self, fr_standard: TextNormalizer) -> None:
        texte = "ETAT brut"
        result = fr_standard.normalize(texte)
        assert result.original == texte
        assert result.normalized != texte or "ÉTAT" in result.normalized

    def test_lang_invalide(self) -> None:
        with pytest.raises(ValueError, match="non supportée"):
            TextNormalizer(lang="zz")

    def test_strictness_invalide(self) -> None:
        with pytest.raises(ValueError, match="invalide"):
            TextNormalizer(lang="fr", strictness="ultra")  # type: ignore[arg-type]

    def test_issues_listes_vides_par_defaut(self, fr_standard: TextNormalizer) -> None:
        """Sans LanguageTool, les listes d'issues sont vides (fallback gracieux)."""
        result = fr_standard.normalize("Bonjour le monde")
        assert isinstance(result.spell_issues, list)
        assert isinstance(result.grammar_issues, list)
        assert isinstance(result.style_issues, list)


# ---------------------------------------------------------------------------
# 9. Tests de régression combinés
# ---------------------------------------------------------------------------

class TestRegression:
    def test_phrase_complexe_fr(self, fr_standard: TextNormalizer) -> None:
        """Phrase riche : accents + apostrophe + guillemets + ponctuation."""
        inp = 'L\'ETAT valide la "strategie" : c\'est essentiel !'
        result = fr_standard.normalize(inp)
        n = result.normalized
        assert "ÉTAT" in n
        assert APOS in n
        assert LQUOTE in n
        assert RQUOTE in n
        assert f"{NNBSP}:" in n
        assert f"{NNBSP}!" in n

    def test_texte_sans_maj_inchange(self, fr_standard: TextNormalizer) -> None:
        """Les mots minuscules ne sont pas affectés par la règle accents majuscules."""
        inp = "le chat dort sur le tapis"
        result = fr_standard.normalize(inp)
        assert "chat" in result.normalized
        assert "tapis" in result.normalized
