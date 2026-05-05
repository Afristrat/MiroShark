"""Normaliseur typographique pour l'anglais.

Règles appliquées :
1. Guillemets typographiques « curly » "…" '…'.
2. Em-dash — (sans espaces, style US) à la place de --.
3. Pas d'espaces avant la ponctuation (règle corrective).
4. Format nombres : 1,234.56 (virgule milliers + point décimal).
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Constantes typographiques anglaises
# ---------------------------------------------------------------------------
LDQUOTE = "“"   # "
RDQUOTE = "”"   # "
LSQUOTE = "‘"   # '
RSQUOTE = "’"   # '
EMDASH = "—"    # —

# ---------------------------------------------------------------------------
# Patterns de remplacement
# ---------------------------------------------------------------------------

# Guillemets doubles droits
_DQUOTE_RE = re.compile(r'"([^"]*)"')

# Guillemets simples droits : apostr./guillemets
_SQUOTE_RE = re.compile(r"'([^']+)'")

# Apostrophe droite entre lettres (contraction anglaise)
_APOS_RE = re.compile(r"(?<=[A-Za-z])'(?=[A-Za-z])")

# Double tiret → em-dash (sans espaces, style US)
_DOUBLE_DASH_RE = re.compile(r'\s*--\s*')

# Espace avant ponctuation (à corriger)
_SPACE_BEFORE_PUNCT_RE = re.compile(r'\s+([,.;:!?])')

# Nombres format EN : garantir point décimal + virgule milliers
_DECIMAL_COMMA_RE = re.compile(r'\b(\d+),(\d{1,2})\b(?!\d)')  # ex : 1,56
_NUMBER_RE = re.compile(r'\b(\d{1,3})(?:\.(\d{3}))+(?:\.(\d+))?\b')


def _apply_double_quotes(text: str) -> str:
    """Convertit les guillemets doubles droits en typographiques anglais."""
    def _repl(m: re.Match) -> str:
        return f"{LDQUOTE}{m.group(1)}{RDQUOTE}"
    return _DQUOTE_RE.sub(_repl, text)


def _apply_single_quotes(text: str) -> str:
    """Convertit les guillemets simples droits en typographiques anglais."""
    def _repl(m: re.Match) -> str:
        return f"{LSQUOTE}{m.group(1)}{RSQUOTE}"
    return _SQUOTE_RE.sub(_repl, text)


def _apply_apostrophe(text: str) -> str:
    """Remplace l'apostrophe droite de contraction par l'apostrophe typographique."""
    return _APOS_RE.sub(RSQUOTE, text)


def _apply_emdash(text: str) -> str:
    """Remplace -- par — (em-dash US, sans espaces)."""
    return _DOUBLE_DASH_RE.sub(EMDASH, text)


def _apply_no_space_before_punct(text: str) -> str:
    """Supprime les espaces superflus avant la ponctuation."""
    return _SPACE_BEFORE_PUNCT_RE.sub(r'\1', text)


def _apply_number_format(text: str) -> str:
    """Normalise les nombres au format anglais : 1,234.56."""
    # Convertir les virgules décimales (style FR) en points
    def _fix_decimal(m: re.Match) -> str:
        return f"{m.group(1)}.{m.group(2)}"
    text = _DECIMAL_COMMA_RE.sub(_fix_decimal, text)
    return text


def normalize_en(text: str, strictness: str = "standard") -> str:
    """Applique les règles typographiques anglaises sur *text*.

    Parameters
    ----------
    text:
        Texte à normaliser.
    strictness:
        ``'strict'``, ``'standard'`` ou ``'permissive'``.

    Returns
    -------
    str
        Texte normalisé.
    """
    if not text:
        return text

    # Étape 1 — Suppression espaces avant ponctuation (corrective)
    result = _apply_no_space_before_punct(text)

    if strictness == "permissive":
        return result

    # Étape 2 — Guillemets doubles typographiques
    result = _apply_double_quotes(result)

    # Étape 3 — Guillemets simples typographiques (hors apostrophes)
    result = _apply_single_quotes(result)

    # Étape 4 — Apostrophes de contraction
    result = _apply_apostrophe(result)

    # Étape 5 — Em-dash
    result = _apply_emdash(result)

    if strictness == "strict":
        # Étape 6 — Format nombres
        result = _apply_number_format(result)

    return result
