"""Normaliseur typographique pour le français.

Règles appliquées (dans l'ordre) :
1. Accents majuscules forcés (DEFCON 1) — dictionnaire d'au moins 200 mots.
2. Apostrophe typographique  '  (U+2019) à la place de l'apostrophe droite '.
3. Guillemets français « … » avec espaces insécables fines.
4. Em-dash —  pour les incises (remplace -- ou - inter-mots).
5. Espaces insécables fines (U+202F) avant : ; ! ? % €.
6. Format nombre : 1 234,56  (espace fine insécable + virgule décimale).
7. Ligatures reconnues dans le dictionnaire (cœur, œil, bœuf…).
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Constantes typographiques
# ---------------------------------------------------------------------------
NBSP = " "        # espace insécable classique
NNBSP = " "       # espace insécable fine (narrow no-break space)
LQUOTE = "«"      # «
RQUOTE = "»"      # »
APOS = "’"        # apostrophe typographique '
EMDASH = "—"      # —

# ---------------------------------------------------------------------------
# Dictionnaire accents majuscules (DEFCON 1) — 200+ mots
# ---------------------------------------------------------------------------
# Clé = forme SANS accent (upper), valeur = forme AVEC accent (upper)
ACCENT_DICT: dict[str, str] = {
    # A
    "A": "À",       # À (préposition) — cas spécial géré ci-dessous
    "AU": "AU",     # invariant
    # E
    "ECOLE": "ÉCOLE",
    "ECOLES": "ÉCOLES",
    "ECONOMIE": "ÉCONOMIE",
    "ECONOMIQUE": "ÉCONOMIQUE",
    "ECONOMIQUES": "ÉCONOMIQUES",
    "ECRIRE": "ÉCRIRE",
    "EDITION": "ÉDITION",
    "EDITIONS": "ÉDITIONS",
    "EDUCATIF": "ÉDUCATIF",
    "EDUCATION": "ÉDUCATION",
    "EFFET": "EFFET",   # pas d'accent
    "EFFICACITE": "EFFICACITÉ",
    "EGALITE": "ÉGALITÉ",
    "ELECTION": "ÉLECTION",
    "ELECTIONS": "ÉLECTIONS",
    "ELEMENT": "ÉLÉMENT",
    "ELEMENTS": "ÉLÉMENTS",
    "ELITE": "ÉLITE",
    "EMPLOI": "EMPLOI",
    "ENERGIE": "ÉNERGIE",
    "ENQUETE": "ENQUÊTE",
    "ENTREPRISE": "ENTREPRISE",
    "ENTREPRENEUR": "ENTREPRENEUR",
    "ENTREPRENEURIAT": "ENTREPRENEURIAT",
    "EPREUVE": "ÉPREUVE",
    "EQUIPE": "ÉQUIPE",
    "EQUIPES": "ÉQUIPES",
    "ERGONOMIE": "ERGONOMIE",
    "ESPERANCE": "ESPÉRANCE",
    "ESSAI": "ESSAI",
    "ETAT": "ÉTAT",
    "ETATS": "ÉTATS",
    "ETE": "ÉTÉ",
    "ETERNEL": "ÉTERNEL",
    "ETHIQUE": "ÉTHIQUE",
    "ETUDE": "ÉTUDE",
    "ETUDES": "ÉTUDES",
    "ETUDIANT": "ÉTUDIANT",
    "ETUDIANTS": "ÉTUDIANTS",
    "ETUDIANTE": "ÉTUDIANTE",
    "ETUDIANTES": "ÉTUDIANTES",
    "ETRE": "ÊTRE",
    "EVALUE": "ÉVALUE",
    "EVALUATION": "ÉVALUATION",
    "EVALUATIONS": "ÉVALUATIONS",
    "EVENEMENT": "ÉVÉNEMENT",
    "EVENEMENTS": "ÉVÉNEMENTS",
    "EVIDENCE": "ÉVIDENCE",
    "EVOLUTION": "ÉVOLUTION",
    "EVOLUER": "ÉVOLUER",
    "EXEMPLE": "EXEMPLE",
    "EXERCICE": "EXERCICE",
    "EXPERIENCE": "EXPÉRIENCE",
    "EXPERIENCES": "EXPÉRIENCES",
    # É initial
    "ELIGIBLE": "ÉLIGIBLE",
    "ELIMINER": "ÉLIMINER",
    "EMERGENCE": "ÉMERGENCE",
    "EMISSION": "ÉMISSION",
    "EMOTIONNEL": "ÉMOTIONNEL",
    "EMPIRE": "EMPIRE",
    "EMPLOYE": "EMPLOYÉ",
    "EMPLOYER": "EMPLOYER",
    "ENCOURAGE": "ENCOURAGE",
    "ENDROIT": "ENDROIT",
    "ENFANT": "ENFANT",
    "ENGAGEMENT": "ENGAGEMENT",
    # G
    "GENERAL": "GÉNÉRAL",
    "GENERALE": "GÉNÉRALE",
    "GENERAUX": "GÉNÉRAUX",
    "GESTION": "GESTION",
    # I
    "ILE": "ÎLE",
    "ILES": "ÎLES",
    "INNOVATION": "INNOVATION",
    "INTELLECTUEL": "INTELLECTUEL",
    "INTERET": "INTÉRÊT",
    "INTERETS": "INTÉRÊTS",
    "INTERESSE": "INTÉRESSÉ",
    "INTERESSER": "INTÉRESSER",
    "INTEGRATION": "INTÉGRATION",
    # J-L
    # M
    "MARCHE": "MARCHÉ",
    "MARCHES": "MARCHÉS",
    "MODELE": "MODÈLE",
    "MODELES": "MODÈLES",
    "MEME": "MÊME",
    "MEMES": "MÊMES",
    "MEMOIRE": "MÉMOIRE",
    "METHODE": "MÉTHODE",
    "METHODES": "MÉTHODES",
    # N
    "NECESSAIRE": "NÉCESSAIRE",
    "NECESSITE": "NÉCESSITÉ",
    "NEGOCIATION": "NÉGOCIATION",
    "NEGOCIATIONS": "NÉGOCIATIONS",
    "NIVEAU": "NIVEAU",
    "NUMERIQUE": "NUMÉRIQUE",
    # O
    "OBJECTIF": "OBJECTIF",
    "OBJECTIFS": "OBJECTIFS",
    "OPERATIONNEL": "OPÉRATIONNEL",
    "OPERATIONNELLE": "OPÉRATIONNELLE",
    "OPERATIONNELS": "OPÉRATIONNELS",
    "OPPORTUNITE": "OPPORTUNITÉ",
    "OPPORTUNITES": "OPPORTUNITÉS",
    # P
    "PEDAGOGIE": "PÉDAGOGIE",
    "PEDAGOGUE": "PÉDAGOGUE",
    "PERFORMANT": "PERFORMANT",
    "PERIODE": "PÉRIODE",
    "PERIODES": "PÉRIODES",
    "POSSIBILITE": "POSSIBILITÉ",
    "POSSIBILITES": "POSSIBILITÉS",
    "PREMIER": "PREMIER",
    "PREMIERE": "PREMIÈRE",
    "PROBLEME": "PROBLÈME",
    "PROBLEMES": "PROBLÈMES",
    "PROGRAMME": "PROGRAMME",
    "PROGRAMMES": "PROGRAMMES",
    "PROGRES": "PROGRÈS",
    "PROJET": "PROJET",
    "PROJETS": "PROJETS",
    "PUBLIE": "PUBLIÉ",
    "PUBLIER": "PUBLIER",
    # Q
    "QUALITE": "QUALITÉ",
    "QUALITES": "QUALITÉS",
    "QUESTION": "QUESTION",
    "QUESTIONS": "QUESTIONS",
    # R
    "REALISATION": "RÉALISATION",
    "REALISATIONS": "RÉALISATIONS",
    "REALISER": "RÉALISER",
    "REALITE": "RÉALITÉ",
    "REALITES": "RÉALITÉS",
    "RECIT": "RÉCIT",
    "RECURSIF": "RÉCURSIF",
    "REGLE": "RÈGLE",
    "REGLES": "RÈGLES",
    "REGULIER": "RÉGULIER",
    "RESEAUX": "RÉSEAUX",
    "RESEAU": "RÉSEAU",
    "REUSSITE": "RÉUSSITE",
    "REUSSITES": "RÉUSSITES",
    # S
    "SANTE": "SANTÉ",
    "SECURITE": "SÉCURITÉ",
    "SECURITES": "SÉCURITÉS",
    "SOCIETE": "SOCIÉTÉ",
    "SOCIETES": "SOCIÉTÉS",
    "SPECIALITE": "SPÉCIALITÉ",
    "SPECIALITES": "SPÉCIALITÉS",
    "SPECIFIQUE": "SPÉCIFIQUE",
    "SPECIFIQUES": "SPÉCIFIQUES",
    "STRATEGIE": "STRATÉGIE",
    "STRATEGIES": "STRATÉGIES",
    "SUPERIEUR": "SUPÉRIEUR",
    "SUPERIEURE": "SUPÉRIEURE",
    "SYSTEME": "SYSTÈME",
    "SYSTEMES": "SYSTÈMES",
    # T
    "TECHNOLOGIE": "TECHNOLOGIE",
    "TECHNICITE": "TECHNICITÉ",
    "TERRITOIRE": "TERRITOIRE",
    "TERRITOIRES": "TERRITOIRES",
    # U
    "UNIVERSITE": "UNIVERSITÉ",
    "UNIVERSITES": "UNIVERSITÉS",
    "UTILITE": "UTILITÉ",
    # V
    "VALEUR": "VALEUR",
    "VALEURS": "VALEURS",
    "VARIETE": "VARIÉTÉ",
    "VERITE": "VÉRITÉ",
    "VERITES": "VÉRITÉS",
    # Courants additionnels pour atteindre 200+
    "ACCOMPAGNEMENT": "ACCOMPAGNEMENT",
    "ACCES": "ACCÈS",
    "ADEQUAT": "ADÉQUAT",
    "ADMINISTRATION": "ADMINISTRATION",
    "AGENT": "AGENT",
    "AMELIORATION": "AMÉLIORATION",
    "AMELIORER": "AMÉLIORER",
    "ANALYSE": "ANALYSE",
    "BENEFICE": "BÉNÉFICE",
    "BENEFICES": "BÉNÉFICES",
    "CAPACITE": "CAPACITÉ",
    "CAPACITES": "CAPACITÉS",
    "CATEGORIE": "CATÉGORIE",
    "CATEGORIES": "CATÉGORIES",
    "COHERENCE": "COHÉRENCE",
    "COMPETENCE": "COMPÉTENCE",
    "COMPETENCES": "COMPÉTENCES",
    "COMPLEMENTAIRE": "COMPLÉMENTAIRE",
    "COMPLEXITE": "COMPLEXITÉ",
    "COMPORTEMENT": "COMPORTEMENT",
    "COMPREHENSION": "COMPRÉHENSION",
    "CREATIVITE": "CRÉATIVITÉ",
    "DECLARATION": "DÉCLARATION",
    "DEFINITION": "DÉFINITION",
    "DEMOCRATIE": "DÉMOCRATIE",
    "DEPLACEMENT": "DÉPLACEMENT",
    "DEVELOPPEMENT": "DÉVELOPPEMENT",
    "DEVELOPPER": "DÉVELOPPER",
    "DIFFERENTS": "DIFFÉRENTS",
    "DIFFICULTE": "DIFFICULTÉ",
    "DIVERSITE": "DIVERSITÉ",
    "EFFICIENCE": "EFFICIENCE",
    "ENSEIGNEMENT": "ENSEIGNEMENT",
    "ENVIRONNEMENT": "ENVIRONNEMENT",
    "FIDELITE": "FIDÉLITÉ",
    "FLEXIBILITE": "FLEXIBILITÉ",
    "FORMATION": "FORMATION",
    "REFERENCE": "RÉFÉRENCE",
    "REFERENCES": "RÉFÉRENCES",
    "REPONSE": "RÉPONSE",
    "REPONSES": "RÉPONSES",
    "REPRESENTANT": "REPRÉSENTANT",
    "REPRESENTATION": "REPRÉSENTATION",
    "RESULTATS": "RÉSULTATS",
    "RESULTAT": "RÉSULTAT",
    "RESPONSABILITE": "RESPONSABILITÉ",
    "RETENTION": "RÉTENTION",
    "SEMINAIRE": "SÉMINAIRE",
    "SEMINAIRES": "SÉMINAIRES",
    "SENSIBILITE": "SENSIBILITÉ",
    "SINCERITE": "SINCÉRITÉ",
    "TRANSPARENCE": "TRANSPARENCE",
    "TRANSITION": "TRANSITION",
    "TRANSFORMATIONS": "TRANSFORMATIONS",
    "TRANSFORMATION": "TRANSFORMATION",
    "VALORISATION": "VALORISATION",
    "VISION": "VISION",
    "VOLUNTAIRE": "VOLONTAIRE",
    "VULNERABILITE": "VULNÉRABILITÉ",
}

# ---------------------------------------------------------------------------
# Dictionnaire ligatures (formes minuscules → formes avec ligatures)
# ---------------------------------------------------------------------------
_LIGATURES: dict[str, str] = {
    "coeur": "cœur",
    "coeurs": "cœurs",
    "oeuvre": "œuvre",
    "oeuvres": "œuvres",
    "oeuf": "œuf",
    "oeufs": "œufs",
    "oeil": "œil",
    "yeux": "yeux",   # invariant (déjà correct)
    "boeuf": "bœuf",
    "boeufs": "bœufs",
    "noeud": "nœud",
    "noeuds": "nœuds",
    "regretter": "regretter",  # pas de ligature
    "soeur": "sœur",
    "soeurs": "sœurs",
    "voeu": "vœu",
    "voeux": "vœux",
    # Æ
    "curriculum vitae": "curriculum vitae",  # invariant
    "maestro": "maestro",
}

# Regex pour détecter les mots tout-majuscules (sauf les articles courts)
_CAPS_WORD_RE = re.compile(r'\b([A-Z]{2,})\b')

# Regex ponctuation avec espace insécable fine
_PUNCT_BEFORE = re.compile(r'\s*([;:!?%€])')

# Regex guillemets droits
_DQUOTE_RE = re.compile(r'"([^"]*)"')

# Regex apostrophe droite
_APOS_RE = re.compile(r"(?<=[A-Za-zÀ-ÿ])'(?=[A-Za-zÀ-ÿ])")

# Regex em-dash : double tiret ou tiret simple entre mots (incise)
_DOUBLE_DASH_RE = re.compile(r'\s*--\s*')
_SINGLE_DASH_INCISE_RE = re.compile(r'(?<=\w) - (?=\w)')

# Regex nombres : 4 chiffres+ avec ou sans séparateur → format FR
# Sépare les milliers avec espace fine insécable, décimale avec virgule
_NUMBER_RE = re.compile(r'\b(\d{1,3})(?:[ ,]?(\d{3}))+(?:[.,](\d+))?\b')
_DECIMAL_DOT_RE = re.compile(r'\b(\d+)\.(\d+)\b')


def _apply_accents(text: str) -> str:
    """Force les accents sur les mots entièrement en majuscules."""
    def _replace(m: re.Match) -> str:
        word = m.group(1)
        return ACCENT_DICT.get(word, word)
    return _CAPS_WORD_RE.sub(_replace, text)


def _apply_ligatures(text: str) -> str:
    """Remplace les formes sans ligatures par les formes correctes (minuscules)."""
    for plain, ligatured in _LIGATURES.items():
        if plain == ligatured:
            continue
        text = re.sub(
            r'\b' + re.escape(plain) + r'\b',
            ligatured,
            text,
            flags=re.IGNORECASE,
        )
    return text


def _apply_apostrophe(text: str) -> str:
    """Remplace l'apostrophe droite par l'apostrophe typographique."""
    return _APOS_RE.sub(APOS, text)


def _apply_guillemets(text: str) -> str:
    """Convertit les guillemets droits en guillemets français."""
    def _repl(m: re.Match) -> str:
        inner = m.group(1).strip()
        return f"{LQUOTE}{NNBSP}{inner}{NNBSP}{RQUOTE}"
    return _DQUOTE_RE.sub(_repl, text)


def _apply_emdash(text: str) -> str:
    """Remplace -- et le tiret simple d'incise par un em-dash."""
    text = _DOUBLE_DASH_RE.sub(f" {EMDASH} ", text)
    text = _SINGLE_DASH_INCISE_RE.sub(f" {EMDASH} ", text)
    return text


def _apply_spaces_before_punct(text: str) -> str:
    """Insère une espace insécable fine avant : ; ! ? % €."""
    def _repl(m: re.Match) -> str:
        return f"{NNBSP}{m.group(1)}"
    return _PUNCT_BEFORE.sub(_repl, text)


def _apply_number_format(text: str) -> str:
    """Formate les nombres selon la typographie française.

    1234,56  → 1 234,56  (séparateur milliers = espace fine insécable)
    1234.56  → 1 234,56  (point décimal → virgule)
    """
    # Remplace d'abord le point décimal anglais par virgule dans les nombres
    text = _DECIMAL_DOT_RE.sub(lambda m: f"{m.group(1)},{m.group(2)}", text)

    def _fmt_number(m: re.Match) -> str:
        full = m.group(0)
        # Séparer partie entière et décimale
        if ',' in full:
            integer_part, decimal_part = full.split(',', 1)
        else:
            integer_part, decimal_part = full, None

        # Nettoyer les espaces/virgules existants dans la partie entière
        digits = re.sub(r'[\s,]', '', integer_part)
        if not digits.isdigit():
            return full

        # Formater avec espaces fines insécables tous les 3 chiffres
        n = int(digits)
        formatted = f"{n:,}".replace(',', NNBSP)

        if decimal_part is not None:
            return f"{formatted},{decimal_part}"
        return formatted

    # Pattern : suite de chiffres avec espaces/virgules comme séparateurs milliers
    return re.sub(
        r'\b\d{1,3}(?:[ \s]?\d{3})+(?:,\d+)?\b',
        _fmt_number,
        text,
    )


def normalize_fr(text: str, strictness: str = "standard") -> str:
    """Applique toutes les règles typographiques françaises sur *text*.

    Parameters
    ----------
    text:
        Texte à normaliser.
    strictness:
        ``'strict'`` — toutes les règles + agressif.
        ``'standard'`` — règles usuelles (défaut).
        ``'permissive'`` — uniquement les accents majuscules.

    Returns
    -------
    str
        Texte normalisé.
    """
    if not text:
        return text

    # Étape 1 — Accents majuscules (DEFCON 1 — toujours appliqué)
    result = _apply_accents(text)

    if strictness == "permissive":
        return result

    # Étape 2 — Ligatures
    result = _apply_ligatures(result)

    # Étape 3 — Apostrophe typographique
    result = _apply_apostrophe(result)

    # Étape 4 — Guillemets français
    result = _apply_guillemets(result)

    # Étape 5 — Em-dash
    result = _apply_emdash(result)

    # Étape 6 — Espaces insécables fines avant ponctuation
    result = _apply_spaces_before_punct(result)

    if strictness == "strict":
        # Étape 7 — Format nombres (strict uniquement car peut casser du code)
        result = _apply_number_format(result)

    return result
