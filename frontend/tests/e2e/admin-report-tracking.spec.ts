/**
 * Admin Report Tracking /admin/reports/:id/tracking — tests E2E (US-130)
 *
 * Couvre :
 *   1. Guard non-auth → redirect /login
 *   2. Guard user normal (non super-admin) → redirect /client/dashboard
 *   3. Accès super-admin → page rendue avec h1 visible
 *   4. Bouton « Livrer » → modal s'ouvre avec les champs requis
 *   5. Re-send button visible dans la table (avec livraisons mockées)
 *   6. Sélecteur de langue FR/EN/AR dans le modal
 *
 * Stratégie de mock :
 *   - seedSuperAdminAuth / seedRegularUserAuth / navigateAuthenticated (pattern US-117)
 *   - L'API /api/admin/reports/:id/deliveries est mockée via page.route
 *   - Aucun appel réseau vers le backend prod
 */

import { expect, test } from '@playwright/test'
import {
  seedSuperAdminAuth,
  seedRegularUserAuth,
  navigateAuthenticated,
} from './fixtures/auth'

const TEST_REPORT_ID = 'rep-test-us130'
const TARGET_PATH    = `/admin/reports/${TEST_REPORT_ID}/tracking`

// ── Mock de l'API deliveries ─────────────────────────────────────────────────

async function mockDeliveryApi(page: import('@playwright/test').Page): Promise<void> {
  const mockDeliveries = [
    {
      id: 'del-001',
      report_id: TEST_REPORT_ID,
      version: 1,
      recipient_email: 'client@example.com',
      recipient_name: 'Alice Martin',
      language: 'fr',
      email_status: 'sent',
      display_status: 'sent',
      sent_at: '2026-05-01T10:00:00Z',
      expires_at: '2026-05-08T10:00:00Z',
    },
    {
      id: 'del-002',
      report_id: TEST_REPORT_ID,
      version: 1,
      recipient_email: 'expired@example.com',
      recipient_name: 'Bob Dupont',
      language: 'en',
      email_status: 'sent',
      display_status: 'expired',
      sent_at: '2026-04-01T10:00:00Z',
      expires_at: '2026-04-08T10:00:00Z',
    },
  ]

  await page.route(`**/api/admin/reports/${TEST_REPORT_ID}/deliveries`, async (route) => {
    const method = route.request().method()
    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: { deliveries: mockDeliveries } }),
      })
    } else {
      await route.continue()
    }
  })

  // Mock deliver endpoint
  await page.route(`**/api/admin/reports/${TEST_REPORT_ID}/deliver`, async (route) => {
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: {
          id: 'del-003',
          report_id: TEST_REPORT_ID,
          version: 1,
          recipient_email: 'new@example.com',
          recipient_name: 'New Client',
          language: 'fr',
          email_status: 'sent',
          display_status: 'sent',
          sent_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 7 * 86400 * 1000).toISOString(),
        },
      }),
    })
  })

  // Mock resend endpoint
  await page.route(`**/api/admin/reports/${TEST_REPORT_ID}/deliveries/*/resend`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: {
          id: 'del-001',
          report_id: TEST_REPORT_ID,
          signing_token: 'newtoken.newsig',
          email_status: 'sent',
        },
      }),
    })
  })

  // Mock downloads endpoint
  await page.route(`**/api/admin/reports/${TEST_REPORT_ID}/deliveries/*/downloads`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: {
          downloads: [
            {
              id: 'dl-001',
              delivery_id: 'del-001',
              downloaded_at: '2026-05-02T14:30:00Z',
              ip_address: '1.2.3.4',
              user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120',
              country_code: 'MA',
            },
          ],
        },
      }),
    })
  })
}

// ═══════════════════════════════════════════════════════════════════════════════
// 1. Guard non-auth
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('US-130 — /admin/reports/:id/tracking guards (non-auth)', () => {
  test('tracking sans auth → redirect /login avec ?redirect contenant admin', async ({ page }) => {
    await page.goto(`${TARGET_PATH}?lang=fr`, { waitUntil: 'domcontentloaded' })
    await page.waitForURL((url: URL): boolean => url.pathname === '/login', { timeout: 8_000 })
    expect(page.url()).toMatch(/\/login/)
    expect(page.url()).toMatch(/redirect=/)
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// 2. Guard user normal (non super-admin)
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('US-130 — /admin/reports/:id/tracking guard user normal', () => {
  test('tracking avec user normal → redirect /client/dashboard', async ({ page }) => {
    await seedRegularUserAuth(page)

    await page.goto('/?lang=fr', { waitUntil: 'domcontentloaded' })
    await page.waitForSelector('a[href="/client/dashboard"]', { timeout: 15_000 })

    await page.evaluate((path: string) => {
      const appEl = document.querySelector('#app')
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const vueApp = (appEl as any)?.__vue_app__
      if (vueApp) {
        const router = vueApp.config.globalProperties.$router
        if (router) {
          router.push(`${path}?lang=fr`)
          return
        }
      }
      window.location.href = `${path}?lang=fr`
    }, TARGET_PATH)

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/client/dashboard',
      { timeout: 10_000 },
    )
    expect(page.url()).toMatch(/\/client\/dashboard/)
    expect(page.url()).toMatch(/not-super-admin/)
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// 3. Accès super-admin — page rendue
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('US-130 — /admin/reports/:id/tracking accès super-admin', () => {
  test('tracking super-admin → h1 "Suivi des livraisons" ou "Delivery Tracking" visible', async ({
    page,
  }) => {
    await seedSuperAdminAuth(page)
    await mockDeliveryApi(page)

    await navigateAuthenticated(page, TARGET_PATH, 'a[href="/client/dashboard"]')

    await page.waitForURL(
      (url: URL): boolean => url.pathname.startsWith('/admin/reports/'),
      { timeout: 10_000 },
    )

    const h1 = page.locator('h1').first()
    await expect(h1).toBeVisible({ timeout: 10_000 })
    await expect(h1).toContainText(/suivi|tracking/i)
  })

  // ─── 4. Modal « Livrer » s'ouvre avec les champs requis ──────────────────

  test('tracking super-admin → modal "Livrer" s\'ouvre avec champs email + nom', async ({
    page,
  }) => {
    await seedSuperAdminAuth(page)
    await mockDeliveryApi(page)

    await navigateAuthenticated(page, TARGET_PATH, 'a[href="/client/dashboard"]')

    await page.waitForURL(
      (url: URL): boolean => url.pathname.startsWith('/admin/reports/'),
      { timeout: 10_000 },
    )

    // Cliquer sur le bouton "Livrer à un destinataire"
    const deliverBtn = page.locator('button:has-text("Livrer"), button:has-text("Deliver")').first()
    await expect(deliverBtn).toBeVisible({ timeout: 8_000 })
    await deliverBtn.click()

    // Modal doit apparaître (role dialog)
    const modal = page.locator('[role="dialog"]').first()
    await expect(modal).toBeVisible({ timeout: 5_000 })

    // Champ email obligatoire
    const emailInput = page.locator('input#art-recipient-email')
    await expect(emailInput).toBeVisible({ timeout: 5_000 })

    // Champ nom
    const nameInput = page.locator('input#art-recipient-name')
    await expect(nameInput).toBeVisible({ timeout: 5_000 })
  })

  // ─── 5. Re-send button visible dans la table ──────────────────────────────

  test('tracking super-admin → bouton "Renvoyer le lien" visible pour chaque livraison', async ({
    page,
  }) => {
    await seedSuperAdminAuth(page)
    await mockDeliveryApi(page)

    await navigateAuthenticated(page, TARGET_PATH, 'a[href="/client/dashboard"]')

    await page.waitForURL(
      (url: URL): boolean => url.pathname.startsWith('/admin/reports/'),
      { timeout: 10_000 },
    )

    // Attendre que la table soit chargée (au moins une ligne)
    const resendBtn = page.locator('button:has-text("Renvoyer"), button:has-text("Resend")').first()
    await expect(resendBtn).toBeVisible({ timeout: 12_000 })
  })

  // ─── 6. Sélecteur de langue FR/EN/AR dans le modal ───────────────────────

  test('tracking super-admin → modal contient sélecteur langue FR/EN/AR', async ({ page }) => {
    await seedSuperAdminAuth(page)
    await mockDeliveryApi(page)

    await navigateAuthenticated(page, TARGET_PATH, 'a[href="/client/dashboard"]')

    await page.waitForURL(
      (url: URL): boolean => url.pathname.startsWith('/admin/reports/'),
      { timeout: 10_000 },
    )

    // Ouvrir le modal
    const deliverBtn = page.locator('button:has-text("Livrer"), button:has-text("Deliver")').first()
    await expect(deliverBtn).toBeVisible({ timeout: 8_000 })
    await deliverBtn.click()

    const modal = page.locator('[role="dialog"]').first()
    await expect(modal).toBeVisible({ timeout: 5_000 })

    // Sélecteur de langue FR/EN/AR
    const frBtn = modal.locator('button:has-text("FR")').first()
    const enBtn = modal.locator('button:has-text("EN")').first()
    const arBtn = modal.locator('button:has-text("AR")').first()

    await expect(frBtn).toBeVisible({ timeout: 5_000 })
    await expect(enBtn).toBeVisible({ timeout: 5_000 })
    await expect(arBtn).toBeVisible({ timeout: 5_000 })
  })
})
