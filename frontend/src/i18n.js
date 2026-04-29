/**
 * MiroShark — internationalization setup
 *
 * Locales :
 *   - fr (pivot, default)
 *   - ar (RTL, polices Tajawal/Almarai chargées dynamiquement)
 *   - en (fallback)
 *
 * Détection de la locale au démarrage, par ordre de priorité :
 *   1. URL parameter ?lang=<code>
 *   2. localStorage.miroshark_locale
 *   3. navigator.language matchant un code supporté
 *   4. fallback fr
 */

import { createI18n } from 'vue-i18n'
import fr from './locales/fr.json'
import ar from './locales/ar.json'
import en from './locales/en.json'

const SUPPORTED_LOCALES = ['fr', 'ar', 'en']
const STORAGE_KEY = 'miroshark_locale'
const RTL_LOCALES = new Set(['ar'])

export function detectLocale() {
  if (typeof window === 'undefined') return 'fr'

  const urlParam = new URLSearchParams(window.location.search).get('lang')
  if (urlParam && SUPPORTED_LOCALES.includes(urlParam)) {
    try {
      window.localStorage.setItem(STORAGE_KEY, urlParam)
    } catch (_) { /* private mode, ignore */ }
    return urlParam
  }

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored && SUPPORTED_LOCALES.includes(stored)) return stored
  } catch (_) { /* ignore */ }

  const nav = (navigator.language || 'fr').slice(0, 2).toLowerCase()
  if (SUPPORTED_LOCALES.includes(nav)) return nav

  return 'fr'
}

export function applyDirection(locale) {
  if (typeof document === 'undefined') return
  const dir = RTL_LOCALES.has(locale) ? 'rtl' : 'ltr'
  document.documentElement.setAttribute('dir', dir)
  document.documentElement.setAttribute('lang', locale)
}

export function setLocale(i18n, locale) {
  if (!SUPPORTED_LOCALES.includes(locale)) return
  i18n.global.locale.value = locale
  applyDirection(locale)
  try {
    window.localStorage.setItem(STORAGE_KEY, locale)
  } catch (_) { /* ignore */ }
}

const initialLocale = detectLocale()
applyDirection(initialLocale)

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: initialLocale,
  fallbackLocale: 'fr',
  messages: { fr, ar, en },
  warnHtmlMessage: false,
})

export default i18n
export { SUPPORTED_LOCALES, RTL_LOCALES }
