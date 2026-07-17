/**
 * Smoke tests — Route privative /console (US-107)
 *
 * Vérifie le contrat du guard router :
 *   1. /console non authentifié → redirige vers /login?redirect=/console
 *   2. /admin/quotes non authentifié → redirige vers /login?redirect=/admin/quotes
 *
 * Le test ne se connecte pas (pas de credentials Supabase fournis aux
 * tests E2E par design — cf. auth-flow.spec.ts). Il vérifie uniquement
 * que la sortie publique « non auth » est bien gardée.
 */

import { expect, test } from '@playwright/test'

test.describe('US-107 — guards /console + /admin/quotes', () => {
  test('/console non auth redirige vers /login avec ?redirect', async ({ page }) => {
    await page.goto('/console?lang=fr', { waitUntil: 'domcontentloaded' })
    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/login',
      { timeout: 10_000, waitUntil: 'commit' }
    )
    expect(page.url()).toMatch(/\/login/)
    expect(page.url()).toMatch(/redirect=/)
    expect(page.url()).toMatch(/console/)
  })

  test('/admin/quotes non auth redirige vers /login avec ?redirect', async ({ page }) => {
    await page.goto('/admin/quotes?lang=fr', { waitUntil: 'domcontentloaded' })
    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/login',
      { timeout: 10_000, waitUntil: 'commit' }
    )
    expect(page.url()).toMatch(/\/login/)
    expect(page.url()).toMatch(/redirect=/)
    expect(page.url()).toMatch(/admin/)
  })
})
