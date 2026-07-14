/**
 * Client Dashboard /client/dashboard — tests multitenant (US-117)
 *
 * Couvre :
 *   1. Guard non-auth → redirect /login
 *   2. Rendu avec auth user normal → page dashboard chargée + org info
 *   3. Bouton « Lancer une simulation moi-même » conditionnel :
 *      - Visible si super-admin (pointe vers /console)
 *      - Visible si self_service_enabled = true
 *   4. Bouton « Commander une nouvelle analyse » → /devis (toujours présent)
 *   5. Section « Mes demandes » (Lot B, US-B5) : visible avec devis, absente
 *      si aucun devis — GET /api/client/quotes mocké.
 *
 * Read-only : aucun PATCH, aucun POST, pas d'issue marcage.
 * Les appels API (/api/client/auth/me + /api/client/simulations +
 * /api/client/quotes) sont mockés.
 */

import { expect, test } from '@playwright/test'
import { seedSuperAdminAuth, seedRegularUserAuth, navigateAuthenticated } from './fixtures/auth'

// Mock de réponse GET /api/client/simulations
const MOCK_SIMULATIONS_RESPONSE = {
  simulations: [],
  total: 0,
  page: 1,
  per_page: 20
}

type QuoteFixture = {
  quote_id: string
  package_id: string
  status: string
  created_at: string
}

/**
 * Helper : mock les appels API nécessaires au rendu du ClientDashboard.
 * `quotes` (Lot B) est vide par défaut, pour ne pas changer le comportement
 * des tests existants qui ne s'attendent pas à la section "Mes demandes".
 */
async function mockDashboardApis(
  page: import('@playwright/test').Page,
  quotes: QuoteFixture[] = []
): Promise<void> {
  await page.route('**/api/client/simulations**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_SIMULATIONS_RESPONSE)
    })
  })
  await page.route('**/api/client/stats**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ total: 0, published: 0, brier_avg: null })
    })
  })
  await page.route('**/api/client/quotes**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: { quotes, total: quotes.length, limit: 50, offset: 0 }
      })
    })
  })
}

test.describe('US-117 — /client/dashboard guard (non-auth)', () => {
  test('/client/dashboard sans auth → redirect /login avec ?redirect', async ({ page }) => {
    await page.goto('/client/dashboard?lang=fr', { waitUntil: 'domcontentloaded' })
    await page.waitForURL((url: URL): boolean => url.pathname === '/login', {
      timeout: 8_000
    })
    expect(page.url()).toMatch(/\/login/)
    expect(page.url()).toMatch(/redirect=/)
  })
})

test.describe('US-117 — /client/dashboard avec user normal (no self-service)', () => {
  test('/client/dashboard avec auth → page chargée (eyebrow + hero)', async ({ page }) => {
    await seedRegularUserAuth(page)
    await mockDashboardApis(page)

    // Navigation 2 phases via « Mon espace » dans le header
    await navigateAuthenticated(page, '/client/dashboard', 'a[href="/client/dashboard"]')

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/client/dashboard',
      { timeout: 10_000 }
    )
    expect(page.url()).toMatch(/\/client\/dashboard/)

    // L'eyebrow « Espace client » ou la hero section doit être visible
    const eyebrow = page.locator('.dash-hero-eyebrow, .dash-hero').first()
    await expect(eyebrow).toBeVisible({ timeout: 10_000 })
  })

  test('/client/dashboard avec auth → org info visible ou banner pending', async ({
    page
  }) => {
    await seedRegularUserAuth(page)
    await mockDashboardApis(page)

    await navigateAuthenticated(page, '/client/dashboard', 'a[href="/client/dashboard"]')

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/client/dashboard',
      { timeout: 10_000 }
    )

    // Soit le nom de l'org est affiché, soit le banner « en attente »
    const orgInfo = page.locator('.dash-hero-org, .dash-banner, .dash-hero-subtitle').first()
    await expect(orgInfo).toBeVisible({ timeout: 10_000 })
  })

  test('/client/dashboard user normal → bouton Commander une analyse visible', async ({
    page
  }) => {
    await seedRegularUserAuth(page)
    await mockDashboardApis(page)

    await navigateAuthenticated(page, '/client/dashboard', 'a[href="/client/dashboard"]')

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/client/dashboard',
      { timeout: 10_000 }
    )

    // Bouton « Commander une nouvelle analyse » → /devis (toujours présent)
    const orderCta = page.getByRole('link', { name: /commander/i }).first()
    const orderCtaAlt = page.locator('.dash-order-cta, a[href="/devis"]').first()

    const mainVisible = await orderCta.isVisible().catch(() => false)
    const altVisible = await orderCtaAlt.isVisible().catch(() => false)

    expect(
      mainVisible || altVisible,
      'Le bouton Commander une analyse doit être visible'
    ).toBe(true)
  })
})

test.describe('US-117 — /client/dashboard avec super-admin', () => {
  test('/client/dashboard super-admin → page chargée', async ({ page }) => {
    await seedSuperAdminAuth(page)
    await mockDashboardApis(page)

    await navigateAuthenticated(page, '/client/dashboard', 'a[href="/client/dashboard"]')

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/client/dashboard',
      { timeout: 10_000 }
    )
    expect(page.url()).toMatch(/\/client\/dashboard/)

    // La page doit être rendue
    const hero = page.locator('.dash-main, .dash-hero').first()
    await expect(hero).toBeVisible({ timeout: 10_000 })
  })

  test('/client/dashboard super-admin → bouton « Lancer une simulation » visible', async ({
    page
  }) => {
    await seedSuperAdminAuth(page)
    await mockDashboardApis(page)

    await navigateAuthenticated(page, '/client/dashboard', 'a[href="/client/dashboard"]')

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/client/dashboard',
      { timeout: 10_000 }
    )

    // Le super-admin a accès au self-service → bouton « Lancer une simulation moi-même »
    // qui pointe vers /console (US-107 ClientDashboard CTA)
    const selfServiceCta = page.locator(
      'a[href="/console"], .dash-self-service-cta, [data-testid="launch-console"]'
    ).first()
    const ctaByText = page.getByRole('link', { name: /lancer une simulation/i }).first()

    const ctaVisible = await selfServiceCta.isVisible().catch(() => false)
    const ctaByTextVisible = await ctaByText.isVisible().catch(() => false)

    expect(
      ctaVisible || ctaByTextVisible,
      'Le bouton Lancer une simulation doit être visible pour le super-admin'
    ).toBe(true)
  })

  test('/client/dashboard super-admin → bouton Commander une analyse visible', async ({
    page
  }) => {
    await seedSuperAdminAuth(page)
    await mockDashboardApis(page)

    await navigateAuthenticated(page, '/client/dashboard', 'a[href="/client/dashboard"]')

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/client/dashboard',
      { timeout: 10_000 }
    )

    // Bouton « Commander une nouvelle analyse » → /devis (toujours présent)
    const orderCta = page.getByRole('link', { name: /commander/i }).first()
    const orderCtaAlt = page.locator('.dash-order-cta, a[href="/devis"]').first()

    const mainVisible = await orderCta.isVisible().catch(() => false)
    const altVisible = await orderCtaAlt.isVisible().catch(() => false)

    expect(
      mainVisible || altVisible,
      'Le bouton Commander une analyse doit être visible'
    ).toBe(true)
  })
})

test.describe('Lot B (US-B5) — section "Mes demandes"', () => {
  test('avec devis → section visible, statut traduit, CTA rapport si livré', async ({ page }) => {
    await seedRegularUserAuth(page)
    await mockDashboardApis(page, [
      {
        quote_id: 'q_e2e00001',
        package_id: 'crisis_drill_24h',
        status: 'delivered',
        created_at: '2026-07-12T10:00:00Z'
      },
      {
        quote_id: 'q_e2e00002',
        package_id: 'pmf_discovery',
        status: 'reviewing',
        created_at: '2026-07-14T09:00:00Z'
      }
    ])

    await navigateAuthenticated(page, '/client/dashboard', 'a[href="/client/dashboard"]')
    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/client/dashboard',
      { timeout: 10_000 }
    )

    const quotesSection = page.locator('.dash-quotes')
    await expect(quotesSection).toBeVisible({ timeout: 10_000 })

    const cards = page.locator('.dash-quote-card')
    await expect(cards).toHaveCount(2)

    // Statut traduit (fr), jamais la valeur SQL brute "delivered"/"reviewing".
    await expect(cards.filter({ hasText: 'crisis_drill_24h' })).toContainText('Livré')
    await expect(cards.filter({ hasText: 'pmf_discovery' })).toContainText("En cours d'analyse")

    // CTA rapport uniquement sur le devis livré.
    const reportCta = cards.filter({ hasText: 'crisis_drill_24h' }).locator('.dash-quote-cta--primary')
    await expect(reportCta).toBeVisible()
    await expect(reportCta).toHaveAttribute('href', '/report/q_e2e00001')

    const noCta = cards.filter({ hasText: 'pmf_discovery' }).locator('.dash-quote-cta--primary')
    await expect(noCta).toHaveCount(0)
  })

  test('sans devis → section "Mes demandes" absente', async ({ page }) => {
    await seedRegularUserAuth(page)
    await mockDashboardApis(page, [])

    await navigateAuthenticated(page, '/client/dashboard', 'a[href="/client/dashboard"]')
    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/client/dashboard',
      { timeout: 10_000 }
    )

    // La hero doit être chargée (signal que la page est bien rendue) avant
    // d'affirmer l'absence de la section.
    await expect(page.locator('.dash-hero-eyebrow, .dash-hero').first()).toBeVisible({
      timeout: 10_000
    })
    await expect(page.locator('.dash-quotes')).toHaveCount(0)
  })
})
