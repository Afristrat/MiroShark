/**
 * US-B03 — Régression i18n pour le namespace `research.*`.
 *
 * Les tests E2E Bassira tournent en read-only sur la prod et n'ont pas de
 * credentials Supabase, donc on ne peut pas exercer le watcher
 * ConsoleView en bout-en-bout depuis Playwright. À la place, on valide
 * deux choses critiques :
 *
 *   1. Les 3 locales (fr/en/ar) déclarent toutes les clés `research.*`
 *      utilisées par TopicResearchPanel et le hook ConsoleView (cohérence
 *      structurelle — chaque ajout dans une locale doit exister dans les
 *      deux autres).
 *
 *   2. Aucune valeur n'est vide ni laissée en anglais brut accidentel
 *      pour fr et ar (anti-régression sur les commits qui copient en.json
 *      sans traduire).
 *
 *   3. /console reste protégé par le guard router (régression US-107).
 */

import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { expect, test } from '@playwright/test'

const __dirname = dirname(fileURLToPath(import.meta.url))

type Locale = 'fr' | 'en' | 'ar'

// Clés research.* requises sur les 3 locales — synchronisée manuellement
// avec components/TopicResearchPanel.vue + views/ConsoleView.vue (US-B02/B03).
const REQUIRED_KEYS = [
  'label',
  'subIdle',
  'subStarting',
  'subRunning',
  'subCompleted',
  'subCached',
  'subFailed',
  'subTimeout',
  'loading',
  'verdict.pass',
  'verdict.warn',
  'verdict.deepen',
  'verdict.fail',
  'framework.crisis',
  'framework.market',
  'framework.policy',
  'framework.cerberus',
  'framework.decision',
  'devilAdvocate',
  'useThisBrief',
  'viewSources',
  'hideSources',
  'sourcesTitle',
  'noSources',
  'coverageGap',
  'coverageGapPlural',
  'noBriefSelected',
  'compose.instructions',
  'compose.variantsAriaLabel',
  'compose.rationaleLabel',
  'compose.charsAbbr',
  'compose.sourcesCount',
  'compose.heading',
  'compose.selectedCount',
  'compose.empty',
  'compose.emptyDegraded',
  'compose.textareaAriaLabel',
  'compose.reset',
  'compose.insert',
  'compose.insertWithSources',
  'compose.selectAllSources',
  'compose.deselectAllSources',
  'compose.sourcesSelectedCount',
  'subDegradedCompleted',
  'errors.generic',
  'errors.notConfigured',
  'errors.unreachable',
  'errors.timeout',
  'errors.rateLimited',
  'errors.sessionNotFound',
  'errors.invalidKey',
  'errors.seedTooShort',
  'errors.seedTooLong',
] as const

function loadLocale(locale: Locale): Record<string, unknown> {
  const path = resolve(__dirname, '../../src/locales', `${locale}.json`)
  if (!existsSync(path)) {
    throw new Error(`Locale file missing: ${path}`)
  }
  const raw = readFileSync(path, 'utf-8')
  const parsed = JSON.parse(raw) as Record<string, unknown>
  const research = parsed.research as Record<string, unknown> | undefined
  if (!research) {
    throw new Error(`research.* block missing in ${locale}.json`)
  }
  return research
}

function get(obj: Record<string, unknown>, path: string): unknown {
  return path.split('.').reduce<unknown>((acc, segment) => {
    if (acc && typeof acc === 'object' && segment in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[segment]
    }
    return undefined
  }, obj)
}

test.describe('US-B03 — i18n research.* cohérence', () => {
  const locales: Locale[] = ['fr', 'en', 'ar']

  for (const locale of locales) {
    test(`${locale}.json déclare toutes les clés research.* requises`, () => {
      const block = loadLocale(locale)
      const missing: string[] = []
      const empty: string[] = []
      for (const key of REQUIRED_KEYS) {
        const value = get(block, key)
        if (value === undefined) {
          missing.push(key)
          continue
        }
        if (typeof value !== 'string' || value.trim().length === 0) {
          empty.push(key)
        }
      }
      expect(
        missing,
        `Clés research.* manquantes dans ${locale}.json : ${missing.join(', ')}`,
      ).toEqual([])
      expect(
        empty,
        `Clés research.* vides dans ${locale}.json : ${empty.join(', ')}`,
      ).toEqual([])
    })
  }

  test('fr.json et ar.json ne sont pas copies directes de en.json', () => {
    const en = loadLocale('en')
    const fr = loadLocale('fr')
    const ar = loadLocale('ar')
    // Au moins le label change entre fr/en/ar (sinon = copie paresseuse).
    expect(get(fr, 'label')).not.toEqual(get(en, 'label'))
    expect(get(ar, 'label')).not.toEqual(get(en, 'label'))
    expect(get(ar, 'label')).not.toEqual(get(fr, 'label'))
  })
})

test.describe('US-B03 — /console reste gardé', () => {
  test('/console non authentifié redirige toujours vers /login', async ({ page }) => {
    await page.goto('/console?lang=fr', { waitUntil: 'domcontentloaded' })
    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/login',
      { timeout: 5000 },
    )
    expect(page.url()).toMatch(/\/login/)
    expect(page.url()).toMatch(/redirect=/)
  })
})
