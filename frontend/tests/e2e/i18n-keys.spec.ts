/**
 * Test transversal i18n — détection des clés brutes (US-010)
 *
 * Pour chaque (page critique × locale), vérifie qu'aucune clé i18n brute
 * (ex: `process.step1.title`, `home.hero.title`) ni placeholder vue-i18n
 * non résolu (ex: `{count}`) n'apparaît dans le DOM rendu.
 *
 * False positives connus :
 *   - les regex sont volontairement larges. Si un test échoue de manière
 *     suspecte, ajouter le pattern à la blocklist locale ci-dessous.
 *
 * Read-only.
 */

import { expect, test } from '@playwright/test'
import {
  CRITICAL_PAGES,
  getBodyText,
  gotoLocalized,
  Locale,
  RAW_I18N_KEY_REGEX,
  UNRESOLVED_PLACEHOLDER_REGEX,
} from './helpers'

const LOCALES: Locale[] = ['fr', 'en', 'ar']

/**
 * Whitelist : termes qui peuvent matcher RAW_I18N_KEY_REGEX mais ne sont
 * PAS des clés brutes (ex: une URL, un nom de variable affiché à dessein).
 *
 * Si un de ces patterns matche une clé suspecte, on l'exclut.
 */
const WHITELIST = [
  /home\.bassira\.ai/i, // domaine fictif si jamais cité
]

function isWhitelisted(match: string): boolean {
  return WHITELIST.some((re) => re.test(match))
}

test.describe('i18n keys — aucune clé brute dans le DOM', () => {
  for (const locale of LOCALES) {
    for (const { path, name } of CRITICAL_PAGES) {
      test(`${name} (${locale}) ne contient ni clé brute ni placeholder vue-i18n`, async ({ page }) => {
        await gotoLocalized(page, path, locale)

        // Récupère le texte rendu (innerText filtre script/style).
        const bodyText = await getBodyText(page)

        // 1) Clé i18n brute du type `process.step1.foo` ou `home.hero.title`.
        const rawMatches = bodyText.match(new RegExp(RAW_I18N_KEY_REGEX, 'g')) || []
        const filtered = rawMatches.filter((m) => !isWhitelisted(m))
        expect(
          filtered,
          `Clés i18n brutes détectées sur ${path} (${locale}) : ${filtered.join(', ')}`,
        ).toEqual([])

        // 2) Placeholder vue-i18n non résolu : `{count}`.
        const placeholderMatch = bodyText.match(UNRESOLVED_PLACEHOLDER_REGEX)
        expect(
          placeholderMatch,
          `Placeholder vue-i18n non résolu détecté sur ${path} (${locale}) : ${placeholderMatch?.[0]}`,
        ).toBeNull()
      })
    }
  }
})
