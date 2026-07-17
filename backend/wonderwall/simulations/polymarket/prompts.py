"""Localized, registry-backed L99 prompt for the conviction arena."""
from __future__ import annotations

from wonderwall.simulations.base import BasePromptBuilder
from wonderwall.simulations.social_media.prompts import SUPPORTED_LOCALES, _COMMON


def _arena(locale: str, policy: str, data: str) -> str:
    return _COMMON[locale].format(policy=policy, data=data)


_PROMPTS = {
    "fr": _arena("fr", """- Évalue séparément chaque question à partir des connaissances du persona, de son incertitude, des prix, de son portefeuille et des observations disponibles.
- `buy_shares` exige un écart motivé entre estimation personnelle et prix ; `sell_shares` exige un changement de conviction, d'exposition ou de faits.
- `create_market` exige une question résoluble, non dupliquée et pertinente ; `comment_on_market` exige une contribution informative fidèle au persona.
- Le sentiment social est un indice faible à confronter, jamais une preuve ni un signal automatique. N'applique aucune taille, stratégie contrariante ou prise de bénéfice universelle.
- Compare les questions actives, puis choisis une seule action. Respecte les contraintes de solde, de position et d'identifiant exposées par les outils.""", "nombre_de_questions={market_count}\ntolérance_au_risque={risk_tolerance}"),
    "en": _arena("en", """- Evaluate each question independently using the persona's knowledge, uncertainty, prices, portfolio, and available observations.
- `buy_shares` requires a grounded gap between personal estimate and price; `sell_shares` requires changed conviction, exposure, or facts.
- `create_market` requires a resolvable, non-duplicate, relevant question; `comment_on_market` requires an informative contribution faithful to the persona.
- Social sentiment is weak evidence to cross-check, never proof or an automatic signal. Apply no universal position size, contrarian strategy, or profit-taking rule.
- Compare active questions, then choose one action. Respect balance, position, and identifier constraints exposed by the tools.""", "question_count={market_count}\nrisk_tolerance={risk_tolerance}"),
    "ar": _arena("ar", """- قيّم كل سؤال بصورة مستقلة اعتماداً على معرفة الشخصية وعدم يقينها والأسعار والمحفظة والملاحظات المتاحة.
- يتطلب `buy_shares` فرقاً مبرراً بين تقدير الشخصية والسعر، ويتطلب `sell_shares` تغيراً في القناعة أو الانكشاف أو الوقائع.
- يتطلب `create_market` سؤالاً قابلاً للحسم وغير مكرر وذا صلة، ويتطلب `comment_on_market` مساهمة مفيدة وأمينة للشخصية.
- المزاج الاجتماعي قرينة ضعيفة تُفحص، وليس دليلاً أو إشارة آلية. لا تطبق حجماً موحداً أو استراتيجية معاكسة أو قاعدة عامة لجني الربح.
- قارن الأسئلة النشطة ثم اختر فعلاً واحداً. احترم قيود الرصيد والمراكز والمعرفات التي تعرضها الأدوات.""", "عدد_الأسئلة={market_count}\nتحمل_المخاطر={risk_tolerance}"),
}


class PolymarketPromptBuilder(BasePromptBuilder):
    def __init__(self, locale: str = "fr", market_count: int = 1, platforms: str = "Polymarket") -> None:
        self.locale = locale if locale in SUPPORTED_LOCALES else "fr"
        self.market_count = max(0, int(market_count))
        self.platforms = platforms

    def build_system_prompt(self, user_info) -> str:
        other = user_info.profile.get("other_info", {}) if isinstance(user_info.profile, dict) else {}
        persona = str(other.get("user_profile") or user_info.name or "—")
        risk_tolerance = str(other.get("risk_tolerance") or "non précisée")
        from app.services import prompt_registry
        template = prompt_registry.get("arena.polymarket.system", self.locale) or _PROMPTS[self.locale]
        return template.format(persona=persona, risk_tolerance=risk_tolerance, market_count=self.market_count, platforms=self.platforms, name_str=f"Your name is {user_info.name}." if user_info.name else "", profile_str=f"Background: {persona}", risk_str=risk_tolerance)
