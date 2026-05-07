"""
Locale-aware LLM prompt helpers (US-043).

Bassira cible Maghreb-Afrique francophone. Les prompts système des LLM
sont historiquement en anglais (héritage du fork upstream MiroShark) et
forçaient le LLM à répondre en anglais même quand l'UI était en français.

Pour un produit dont la valeur est de présenter un rapport directement
exploitable à un DG francophone marocain ou un conseiller cabinet à Dakar,
c'est un blocage produit.

Ce helper expose :

- `LOCALE_FULL_NAMES` : mapping `code → label humain` pour interpolation.
- `get_request_locale(default='fr')` : lit le header `X-Bassira-Locale`
  côté Flask request context. Default `fr` pour la démo. Validé contre
  les codes supportés (`fr`, `ar`, `en`) — fallback `fr` si invalide.
- `localize_system_prompt(prompt, locale='fr')` : append une instruction
  forte de réponse dans la locale demandée. Préserve les identifiants
  techniques (PascalCase, UPPER_SNAKE_CASE) qui restent en anglais.

Usage typique dans un endpoint Flask :

    from app.utils.locale_prompt import get_request_locale, localize_system_prompt
    locale = get_request_locale()
    system = localize_system_prompt(ONTOLOGY_SYSTEM_PROMPT, locale)
    messages = [{"role": "system", "content": system}, ...]
"""

from typing import Final, Mapping


# Mapping code → label humain riche (utilisé dans l'instruction LLM).
# AR inclut le toponyme « العربية » pour donner au LLM un ancrage clair sur
# la variante de l'arabe (standard moderne + accessible aux dialectes
# Maghreb).
LOCALE_FULL_NAMES: Final[Mapping[str, str]] = {
    "fr": "français",
    "ar": "arabe (العربية)",
    "en": "English",
}

DEFAULT_LOCALE: Final[str] = "fr"


def get_request_locale(default: str = DEFAULT_LOCALE) -> str:
    """Read `X-Bassira-Locale` header from the current Flask request.

    Returns `default` if the header is missing, the request context is
    unavailable (background thread / subprocess), or the value is not a
    supported locale code.
    """
    try:
        from flask import request, has_request_context

        if not has_request_context():
            return default

        raw = request.headers.get("X-Bassira-Locale", "")
    except Exception:
        # Outside a Flask context (e.g. pytest unit, background worker)
        return default

    code = raw.strip().lower()
    if code in LOCALE_FULL_NAMES:
        return code
    return default


def localize_system_prompt(prompt: str, locale: str = DEFAULT_LOCALE) -> str:
    """Append a strong reply-language instruction to a system prompt.

    The instruction targets the *output* language only; identifiers
    expected by the schema (PascalCase entity types, UPPER_SNAKE_CASE
    relation types, snake_case attribute names, JSON keys) remain in
    English so downstream parsers keep working.

    Idempotent : if the instruction is already present (sentinel string
    detected), returns the prompt unchanged. Useful when a prompt is
    composed and might pass through this helper twice.
    """
    if locale not in LOCALE_FULL_NAMES:
        locale = DEFAULT_LOCALE

    sentinel = "[bassira-locale-instruction]"
    if sentinel in prompt:
        return prompt

    full_name = LOCALE_FULL_NAMES[locale]

    instruction = (
        f"\n\n<!-- {sentinel} -->\n"
        f"**RÉPONSE — LANGUE OBLIGATOIRE** : Tu réponds exclusivement "
        f"en **{full_name}** (code `{locale}`), quelle que soit la langue "
        f"du document d'entrée ou du contexte fourni. Tous les contenus "
        f"libres (descriptions, examples, summary, prose narrative, posts "
        f"d'agents, justifications, titres) sont produits en {full_name}. "
        f"\n"
        f"**Exception identifiants techniques** : les noms de types "
        f"d'entités (PascalCase), de relations (UPPER_SNAKE_CASE), "
        f"d'attributs (snake_case), et toutes les clés JSON restent en "
        f"anglais conformément au schéma — c'est le seul cas où l'anglais "
        f"est conservé.\n"
        f"\n"
        f"**Citations issues du contexte (US-138)** : si tu rapportes du "
        f"texte produit par les agents simulés (posts, dialogues, articles) "
        f"qui se trouve dans une autre langue que {full_name}, tu DOIS le "
        f"traduire intégralement en {full_name} avant de l'inclure dans ta "
        f"réponse. Ne JAMAIS recopier de fragment dans la langue source. "
        f"Conserve les noms propres (personnes, organisations, lieux), les "
        f"acronymes (CGEM, OCP, FMI, BCEAO, CFCIM, etc.), les marques et "
        f"hashtags tels quels — tout le reste passe en {full_name}, y "
        f"compris les expressions idiomatiques et la syntaxe des verbes.\n"
        f"\n"
        f"Si le document fourni est dans une autre langue que {full_name}, "
        f"traduis-le mentalement avant de produire ta réponse, mais ne "
        f"renvoie JAMAIS le texte original — uniquement ta réponse en "
        f"{full_name}.\n"
        f"\n"
        f"**Contrôle qualité avant de répondre** : relis ta sortie pour "
        f"vérifier qu'aucun mot anglais résiduel ne subsiste hors de la "
        f"liste des exceptions ci-dessus (noms propres, acronymes, "
        f"identifiants techniques). Si tu trouves un fragment anglais, "
        f"corrige-le AVANT de finaliser ta réponse."
    )

    return prompt + instruction
