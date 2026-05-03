/**
 * Helpers partagés entre les specs Playwright (US-010).
 *
 * Conventions Bassira :
 *   - locale via query param ?lang=fr|ar|en (pris en charge par i18n.js)
 *   - localStorage.bassira_locale persiste la sélection (initContext skip)
 *   - <html dir="rtl"> pour AR uniquement
 */

import type { Page } from '@playwright/test'

export type Locale = 'fr' | 'ar' | 'en'

/**
 * Liste des couples (path, key i18n) testés sur les vues critiques.
 * Inclut Home, Calibration, Offers, Quote, Explore.
 */
export const CRITICAL_PAGES: ReadonlyArray<{ path: string; name: string }> = [
  { path: '/', name: 'Home' },
  { path: '/calibration', name: 'Calibration' },
  { path: '/offres', name: 'Offers' },
  { path: '/devis', name: 'Quote' },
  { path: '/explore', name: 'Explore' },
]

/** Ajoute (ou écrase) le query param ?lang= sur un path. */
export function withLocale(path: string, locale: Locale): string {
  const sep = path.includes('?') ? '&' : '?'
  return `${path}${sep}lang=${locale}`
}

/**
 * Va sur `path?lang=<locale>` et attend que le réseau soit calme (idéal
 * pour Vue qui charge ses chunks asynchrones).
 *
 * On préfère `domcontentloaded` plutôt que `networkidle` qui peut traîner
 * indéfiniment quand un endpoint hot-reload reste ouvert.
 */
export async function gotoLocalized(
  page: Page,
  path: string,
  locale: Locale,
): Promise<void> {
  await page.goto(withLocale(path, locale), { waitUntil: 'domcontentloaded' })
  // Laisse Vue monter le composant (le router est en createWebHistory).
  await page.waitForLoadState('load').catch(() => undefined)
}

/**
 * Récupère le texte visible du body (utile pour les regex i18n).
 * Filtre les <script>/<style>/<noscript> via `innerText` côté browser.
 */
export async function getBodyText(page: Page): Promise<string> {
  return page.evaluate(() => document.body?.innerText ?? '')
}

/**
 * Détecte la présence de clés i18n non résolues dans le DOM.
 *
 * Patterns ciblés :
 *   - `process.step1.xxx`     → key brute non interpolée
 *   - `home.hero.title`       → idem
 *   - `{count}` ou `{ count }` → placeholder vue-i18n non résolu
 *
 * False positives connus :
 *   - exemples de code dans la doc (filtrer si besoin via blocklist)
 *   - i18n keys dans des attributs aria-* (innerText les ignore déjà)
 */
export const RAW_I18N_KEY_REGEX = /\b(?:process|home|offers|quote|calibration|explore|nav|common)\.[a-z][a-zA-Z0-9_]*\.[a-z][a-zA-Z0-9_.]*\b/

/**
 * Placeholder vue-i18n non résolu : `{count}`, `{ count }`,
 * mais on évite les `{0}` numériques et les expressions complexes.
 */
export const UNRESOLVED_PLACEHOLDER_REGEX = /\{\s*[a-z][a-zA-Z0-9_]*\s*\}/

/**
 * Liste de chaînes attendues côté i18n (smoke check par locale).
 * Permet d'affirmer que le bundle locale a bien été chargé.
 */
export const I18N_FIXTURES: Record<Locale, {
  home: { title: string; launchCta: string }
  offers: { crisisDrillName: string; faqTitle: RegExp }
  quote: { trustBannerSnippet: string }
  langCode: string
}> = {
  fr: {
    home: {
      // US-087 — la home publique ne promeut plus le self-service.
      // Le hero title est l'accroche prospective ; le CTA principal
      // route vers /models. Le tunnel /devis est promu via le CTA
      // secondaire « Commander une analyse ».
      title: 'Stress-testez votre stratégie',
      launchCta: 'Voir les modèles',
    },
    offers: {
      crisisDrillName: 'Crisis Drill',
      faqTitle: /FAQ|Questions/i,
    },
    quote: {
      trustBannerSnippet: 'directement aux fondateurs',
    },
    langCode: 'FR',
  },
  en: {
    home: {
      title: 'Stress-test your strategy',
      launchCta: 'Browse our models',
    },
    offers: {
      crisisDrillName: 'Crisis Drill',
      faqTitle: /FAQ|Questions/i,
    },
    quote: {
      trustBannerSnippet: 'directly to the founders',
    },
    langCode: 'EN',
  },
  ar: {
    home: {
      title: 'اختبر استراتيجيتك',
      launchCta: 'تصفّح النماذج',
    },
    offers: {
      crisisDrillName: 'Crisis Drill',
      faqTitle: /.+/, // FAQ AR — pas de regex stricte, présence du heading suffit
    },
    quote: {
      trustBannerSnippet: 'مباشرة إلى المؤسّسين',
    },
    langCode: 'AR',
  },
}
