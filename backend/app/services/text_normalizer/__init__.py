"""TextNormalizer — service de normalisation typographique multilingue.

Langues supportées : ``'fr'`` (français), ``'en'`` (anglais), ``'ar'`` (arabe).

Usage minimal ::

    from app.services.text_normalizer import TextNormalizer

    normalizer = TextNormalizer(lang='fr')
    result = normalizer.normalize("c'est l'avenir : 5 facteurs")
    print(result.normalized)
    # → c'est l'avenir : 5 facteurs  (apostrophes + espace insécable fine)

Avec strictness ::

    normalizer = TextNormalizer(lang='fr', strictness='strict')
    result = normalizer.normalize('ETAT DE SANTE : 1234,56 EUR')
    print(result.normalized)
    # → ÉTAT DE SANTÉ : 1 234,56 EUR

Architecture :
- ``fr.py``  → règles françaises (accents majuscules, espaces insécables, guillemets…)
- ``en.py``  → règles anglaises (curly quotes, em-dash US…)
- ``ar.py``  → règles arabes (ponctuation arabe, chiffres hindis optionnels)
- ``languagetool_client.py`` → client HTTP LanguageTool (spell + grammar)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Literal

from .ar import normalize_ar
from .en import normalize_en
from .fr import normalize_fr
from .languagetool_client import Issue, check as lt_check

__all__ = [
    "TextNormalizer",
    "NormalizedText",
    "Issue",
]

logger = logging.getLogger("miroshark.text_normalizer")

_SUPPORTED_LANGS = {"fr", "en", "ar"}
_STRICTNESS_LEVELS = {"strict", "standard", "permissive"}

Strictness = Literal["strict", "standard", "permissive"]


@dataclass
class NormalizedText:
    """Résultat complet d'une normalisation typographique.

    Attributes
    ----------
    original:
        Texte d'entrée non modifié.
    normalized:
        Texte avec toutes les règles typographiques appliquées.
    spell_issues:
        Problèmes d'orthographe détectés (LanguageTool ou fallback).
    grammar_issues:
        Problèmes de grammaire détectés.
    style_issues:
        Suggestions de style.
    confidence:
        Score de confiance global (0.0–1.0).
        1.0 = aucun problème détecté, 0.0 = nombreux problèmes.
    """

    original: str
    normalized: str
    spell_issues: List[Issue] = field(default_factory=list)
    grammar_issues: List[Issue] = field(default_factory=list)
    style_issues: List[Issue] = field(default_factory=list)
    confidence: float = 1.0


def _compute_confidence(
    text: str,
    spell: List[Issue],
    grammar: List[Issue],
    style: List[Issue],
) -> float:
    """Calcule un score de confiance basé sur le ratio problèmes/mots."""
    if not text:
        return 1.0

    word_count = max(1, len(text.split()))
    total_issues = len(spell) * 3 + len(grammar) * 2 + len(style)
    # Pondération : 3 fautes d'ortho ↔ 1.0 problème par mot = confiance 0.0
    ratio = total_issues / (word_count * 3)
    return max(0.0, round(1.0 - ratio, 3))


class TextNormalizer:
    """Factory de normalisation typographique multilingue.

    Parameters
    ----------
    lang:
        Code langue : ``'fr'``, ``'en'`` ou ``'ar'``.
    strictness:
        Niveau d'application des règles :

        - ``'strict'``     — toutes les règles, y compris le formatage des nombres.
        - ``'standard'``   — règles usuelles (défaut).
        - ``'permissive'`` — uniquement les corrections critiques (accents FR).

    Raises
    ------
    ValueError
        Si la langue ou le niveau de strictness n'est pas supporté.
    """

    def __init__(
        self,
        lang: str,
        strictness: Strictness = "standard",
    ) -> None:
        if lang not in _SUPPORTED_LANGS:
            raise ValueError(
                f"Langue '{lang}' non supportée. "
                f"Langues disponibles : {sorted(_SUPPORTED_LANGS)}"
            )
        if strictness not in _STRICTNESS_LEVELS:
            raise ValueError(
                f"Strictness '{strictness}' invalide. "
                f"Valeurs acceptées : {sorted(_STRICTNESS_LEVELS)}"
            )
        self.lang = lang
        self.strictness = strictness

    def normalize(self, text: str) -> NormalizedText:
        """Normalise *text* selon les règles de la langue configurée.

        Parameters
        ----------
        text:
            Texte brut à normaliser. Peut être vide.

        Returns
        -------
        NormalizedText
            Dataclass contenant le texte normalisé, les issues détectées
            et le score de confiance.
        """
        if not text:
            return NormalizedText(
                original=text,
                normalized=text,
                confidence=1.0,
            )

        # — Normalisation typographique —
        if self.lang == "fr":
            normalized = normalize_fr(text, strictness=self.strictness)
        elif self.lang == "en":
            normalized = normalize_en(text, strictness=self.strictness)
        else:  # ar
            normalized = normalize_ar(text, strictness=self.strictness)

        # — Vérification LanguageTool (best-effort, fallback gracieux) —
        all_issues = lt_check(normalized, self.lang)

        spell_issues = [i for i in all_issues if i.severity == "error"]
        grammar_issues = [i for i in all_issues if i.severity == "warning"]
        style_issues = [i for i in all_issues if i.severity == "info"]

        confidence = _compute_confidence(
            normalized, spell_issues, grammar_issues, style_issues
        )

        return NormalizedText(
            original=text,
            normalized=normalized,
            spell_issues=spell_issues,
            grammar_issues=grammar_issues,
            style_issues=style_issues,
            confidence=confidence,
        )
