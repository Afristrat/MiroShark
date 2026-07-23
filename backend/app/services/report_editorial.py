"""Stable editorial contract shared by all report-generation paths."""

from __future__ import annotations

import re

from ..utils.locale_prompt import normalize_locale


_CONTRACTS = {
    "fr": """
## Contrat éditorial français — obligatoire
Rédige en français soutenu, direct et lisible par un décideur. Les titres sont
en casse phrase : seule l'initiale du premier mot et les noms propres prennent
une majuscule. Emploie les espaces insécables de la typographie française avant
« : », « ; », « ? » et « ! ». N'utilise ni tiret cadratin, ni formule creuse,
ni titre en capitalisation anglaise, ni conclusion automatique. Chaque paragraphe
suit : fait observé, mécanisme, implication. Distingue explicitement observation,
interprétation et incertitude. N'invente aucune source, citation ou donnée.
""",
    "en": """
## English editorial contract — mandatory
Write formal, plain English for an executive reader. Use sentence case for every
title; never use Title Case except for proper nouns. Do not use em dashes, generic
AI transitions or automatic conclusions. Each paragraph follows: observed evidence,
mechanism, implication. Distinguish simulation observations, interpretations and
uncertainty. Do not invent sources, quotations or facts.
""",
    "ar": """
## العقد التحريري العربي — إلزامي
اكتب بالعربية الفصحى المعاصرة الواضحة للقارئ التنفيذي. صغ العناوين العربية
طبيعياً من دون زخرفة أو نقل حرفي عن الفرنسية أو الإنجليزية. لا تستخدم شرطة طويلة
أو عبارات إنشائية عامة أو خاتمة آلية. يبني كلّ فقرة على دليل مُلاحظ ثم آلية ثم
دلالة عملية. ميّز بوضوح بين ما رُصد في المحاكاة وما يُفسَّر منها وما يبقى غير
يقيني. لا تخترع مصادر أو اقتباسات أو وقائع.
""",
}


def report_editorial_contract(locale: str | None) -> str:
    """Return native-language report instructions."""
    return _CONTRACTS[normalize_locale(locale)]


def compose_report_system_prompt(base_prompt: str, locale: str | None) -> str:
    """Attach stable editorial requirements before language localisation."""
    return f"{base_prompt.rstrip()}\n{report_editorial_contract(locale)}\n"


def editorial_violations(markdown: str, locale: str | None) -> list[str]:
    """Detect only mechanical editorial failures; never rewrite prose blindly."""
    language = normalize_locale(locale)
    violations: list[str] = []
    if "—" in markdown:
        violations.append("em_dash")
    if language in {"fr", "en"}:
        for heading in re.findall(r"^#{1,2}\s+(.+?)\s*$", markdown, re.MULTILINE):
            words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'-]*", heading)
            non_initial = [word for word in words[1:] if len(word) > 2 and word.isalpha()]
            if len(non_initial) >= 2 and sum(word[0].isupper() for word in non_initial) >= 2:
                violations.append("title_case_heading")
                break
    if language == "fr" and re.search(r"(?<!\s)[:;!?](?!\w)", markdown):
        violations.append("french_spacing")
    return violations
