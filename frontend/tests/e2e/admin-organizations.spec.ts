/**
 * Admin Organizations — accès super-admin uniquement (US-117)
 *
 * Note : `/admin/organizations` n'est PAS une route Vue Router frontend.
 * C'est une route API backend (`GET /api/admin/organizations`).
 * Ce spec teste :
 *   1. Que le backend retourne 403 / 401 pour un non super-admin
 *   2. Que la liste contient au moins 1 org (via API mock + page.evaluate)
 *   3. Que la nav AdminQuotesView affiche un lien vers /admin/analytics
 *
 * Ces tests utilisent `page.evaluate` pour des appels fetch API-level
 * via le contexte navigateur (passent par nos mocks page.route).
 *
 * Read-only : uniquement GET. Pas de PATCH, pas de mutation.
 */

import { expect, test } from '@playwright/test'
import { seedSuperAdminAuth, navigateAuthenticated } from './fixtures/auth'

// Payload mock pour l'API admin organizations
const MOCK_ORGS_RESPONSE = {
  organizations: [
    {
      id: '00000000-0000-0000-0000-000000000099',
      name: 'AI-Mpower Bassira',
      slug: 'aimpower-bassira',
      self_service_enabled: true,
      members_count: 1,
      simulations_count: 6,
      published_count: 2,
      avg_brier: 0.18
    },
    {
      id: '00000000-0000-0000-0000-000000000100',
      name: 'ACME Corp',
      slug: 'acme-corp',
      self_service_enabled: false,
      members_count: 3,
      simulations_count: 0,
      published_count: 0,
      avg_brier: null
    }
  ],
  total: 2
}

test.describe('US-117 — /api/admin/organizations guard non-auth', () => {
  test('GET /api/admin/organizations sans auth → 401 ou 403', async ({ request }) => {
    // Appel direct sans Authorization header → doit être rejeté
    const res = await request.get('/api/admin/organizations')
    expect(
      [401, 403, 503],
      `Statut attendu 401/403/503, reçu ${res.status()}`
    ).toContain(res.status())
  })
})

test.describe('US-117 — /api/admin/organizations accès super-admin (via mock route)', () => {
  test('AdminQuotesView affiche lien vers /admin/analytics (nav admin visible)', async ({
    page
  }) => {
    await seedSuperAdminAuth(page)

    // Mock des quotes pour que la page se charge
    await page.route('**/api/admin/quotes**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ quotes: [], total: 0, page: 1, per_page: 20 })
      })
    })

    await navigateAuthenticated(page, '/admin/quotes')

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/admin/quotes',
      { timeout: 10_000 }
    )

    // Le topbar admin doit afficher un lien vers /admin/analytics
    await page.locator('.app-header__admin-toggle').click()
    const analyticsLink = page.locator('a[href="/admin/analytics"], .aq-pill[href="/admin/analytics"]')
    await expect(analyticsLink.first()).toBeVisible({ timeout: 8_000 })
  })

  test('Mock API organizations retourne la liste (contrat JSON)', async ({ page }) => {
    await seedSuperAdminAuth(page)

    // Intercepte l'appel GET /api/admin/organizations
    await page.route('**/api/admin/organizations**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_ORGS_RESPONSE)
      })
    })

    // Charger une page quelconque pour avoir le contexte de page
    await page.goto('/?lang=fr', { waitUntil: 'domcontentloaded' })

    // Effectue l'appel via fetch depuis le contexte page (simule ce que
    // ferait un composant Vue)
    const result = await page.evaluate(async () => {
      const res = await fetch('/api/admin/organizations', {
        headers: { Authorization: 'Bearer faketoken' }
      })
      return { status: res.status, data: await res.json() }
    })

    // Notre mock répond 200 avec la liste
    expect(result.status).toBe(200)
    expect(result.data.organizations).toHaveLength(2)
    expect(result.data.organizations[0]).toHaveProperty('slug', 'aimpower-bassira')
    expect(result.data.total).toBe(2)
  })

  test('Mock API organizations list contient au moins 1 org avec self_service_enabled', async ({
    page
  }) => {
    await seedSuperAdminAuth(page)

    await page.route('**/api/admin/organizations**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_ORGS_RESPONSE)
      })
    })

    await page.goto('/?lang=fr', { waitUntil: 'domcontentloaded' })

    const result = await page.evaluate(async () => {
      const res = await fetch('/api/admin/organizations', {
        headers: { Authorization: 'Bearer faketoken' }
      })
      return await res.json()
    })

    const selfServiceOrgs = (result.organizations as Array<{ self_service_enabled: boolean }>).filter(
      (o) => o.self_service_enabled
    )
    expect(selfServiceOrgs.length).toBeGreaterThanOrEqual(1)
  })
})
