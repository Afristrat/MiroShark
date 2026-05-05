"""Normaliseur typographique pour l'arabe.

Règles appliquées :
1. Ponctuation arabe : , → ،  ; → ؛  ? → ؟  % → ٪
2. Conversion optionnelle chiffres latins → chiffres hindi (٠١٢٣٤٥٦٧٨٩).
3. Attribut dir="rtl" pour un rendu HTML downstream.

Note : pas d'apostrophe typographique (l'arabe n'en utilise pas).
Note : la police Tajawal est recommandée en aval pour le rendu.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Tables de correspondance
# ---------------------------------------------------------------------------

# Ponctuation latine → ponctuation arabe
_PUNCT_MAP: dict[str, str] = {
    ",": "،",    # virgule arabe
    ";": "؛",    # point-virgule arabe
    "?": "؟",    # point d'interrogation arabe
    "%": "٪",    # symbole pourcentage arabe
}

# Chiffres latins → chiffres hindi (est arabisants)
_HINDI_DIGITS: dict[str, str] = {
    "0": "٠",
    "1": "١",
    "2": "٢",
    "3": "٣",
    "4": "٤",
    "5": "٥",
    "6": "٦",
    "7": "٧",
    "8": "٨",
    "9": "٩",
}

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Virgule latine (hors contexte numérique : 1,234)
# On ne convertit la virgule que si elle n'est pas entre deux chiffres
_COMMA_RE = re.compile(r'(?<!\d),(?!\d)')

# Point-virgule latin
_SEMICOLON_RE = re.compile(r';')

# Point d'interrogation latin (pas ?! — on convertit juste le ?)
_QUESTION_RE = re.compile(r'\?')

# Pourcentage latin
_PERCENT_RE = re.compile(r'%')

# Chiffres latins
_DIGITS_RE = re.compile(r'[0-9]')


def _apply_arabic_punctuation(text: str) -> str:
    """Remplace la ponctuation latine par la ponctuation arabe."""
    text = _COMMA_RE.sub("،", text)
    text = _SEMICOLON_RE.sub("؛", text)
    text = _QUESTION_RE.sub("؟", text)
    text = _PERCENT_RE.sub("٪", text)
    return text


def _apply_hindi_digits(text: str) -> str:
    """Convertit les chiffres latins en chiffres hindis (optionnel)."""
    return _DIGITS_RE.sub(lambda m: _HINDI_DIGITS[m.group(0)], text)


def normalize_ar(
    text: str,
    strictness: str = "standard",
    use_hindi_digits: bool = False,
) -> str:
    """Applique les règles typographiques arabes sur *text*.

    Parameters
    ----------
    text:
        Texte à normaliser.
    strictness:
        ``'strict'``, ``'standard'`` ou ``'permissive'``.
    use_hindi_digits:
        Si ``True``, convertit les chiffres latins en chiffres hindis.
        Défaut ``False`` (les chiffres latins sont courants en arabe moderne).

    Returns
    -------
    str
        Texte normalisé.
    """
    if not text:
        return text

    result = text

    # Étape 1 — Ponctuation arabe (toujours appliquée)
    result = _apply_arabic_punctuation(result)

    if strictness == "permissive":
        return result

    # Étape 2 — Chiffres hindis (option utilisateur)
    if use_hindi_digits:
        result = _apply_hindi_digits(result)

    return result


def get_html_dir_attr() -> str:
    """Retourne l'attribut HTML de direction pour le rendu RTL."""
    return 'dir="rtl"'
