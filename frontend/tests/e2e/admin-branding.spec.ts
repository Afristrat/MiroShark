/**
 * Admin Branding /admin/branding — tests E2E (US-120)
 *
 * Couvre :
 *   1. Guard non-auth → redirect /login
 *   2. Guard user normal (non super-admin) → redirect /client/dashboard
 *   3. Accès super-admin → page rendue avec h1, topbar, contrôles
 *   4. Bouton « Nouveau branding » → modal s'ouvre avec le formulaire
 *   5. Sélecteur de langue dans le panneau aperçu (FR/EN/AR)
 *
 * Stratégie de mock :
 *   - Même pattern que admin-quotes.spec.ts (US-117) :
 *     seedSuperAdminAuth / seedRegularUserAuth / navigateAuthenticated
 *   - L'API /api/admin/branding est mockée via page.route pour éviter
 *     tout appel réseau vers le backend prod.
 *   - Les tests structurels (h1, modal) ne dépendent pas de données réelles.
 */

import { expect, test } from '@playwright/test'
import { seedSuperAdminAuth, seedRegularUserAuth, navigateAuthenticated } from './fixtures/auth'

// ── Mock de l'API branding ───────────────────────────────────────────────────

async function mockBrandingApi(page: import('@playwright/test').Page): Promise<void> {
  await page.route('**/api/admin/branding**', async (route) => {
    const method = route.request().method()
    const url = route.request().url()

    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            brandings: [
              {
                id: 'test-branding-001',
                org_id: '00000000-0000-0000-0000-000000000099',
                name: 'Rapport Standard Bassira',
                valid_from: '2026-05-01T00:00:00Z',
                valid_to: null,
                palette_primary: '#FF8551',
                palette_background: '#FAF7F2',
              }
            ],
            org_id: '00000000-0000-0000-0000-000000000099'
          }
        })
      })
    } else if (method === 'POST' && url.includes('/preview')) {
      // Mock preview endpoint
      // Générer un SVG base64 minimal
      const svgContent = '<svg xmlns="http://www.w3.org/2000/svg" width="595" height="842"><rect width="595" height="50" fill="#FF8551"/><text x="10" y="30" fill="white" font-size="14">Rapport Standard Bassira</text></svg>'
      const svgB64 = Buffer.from(svgContent).toString('base64')
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            preview_svg: svgB64,
            content_type: 'image/svg+xml',
            lang: 'fr'
          }
        })
      })
    } else if (method === 'POST') {
      // Mock create endpoint
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            branding: {
              id: 'new-branding-uuid',
              name: 'Nouveau Branding Test',
              org_id: '00000000-0000-0000-0000-000000000099',
              valid_from: new Date().toISOString(),
              valid_to: null,
            }
          }
        })
      })
    } else if (method === 'PATCH') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            branding: {
              id: 'updated-branding-uuid',
              name: 'Branding Mis à Jour',
              org_id: '00000000-0000-0000-0000-000000000099',
              valid_from: new Date().toISOString(),
              valid_to: null,
            }
          }
        })
      })
    } else {
      await route.continue()
    }
  })
}

// ═══════════════════════════════════════════════════════════════════════════════
// 1. Guard non-auth
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('US-120 — /admin/branding guards (non-auth)', () => {
  test('/admin/branding sans auth → redirect /login avec ?redirect contenant admin', async ({
    page
  }) => {
    await page.goto('/admin/branding?lang=fr', { waitUntil: 'domcontentloaded' })
    await page.waitForURL((url: URL): boolean => url.pathname === '/login', {
      timeout: 8_000
    })
    expect(page.url()).toMatch(/\/login/)
    expect(page.url()).toMatch(/redirect=/)
    expect(page.url()).toMatch(/admin/)
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// 2. Guard user normal
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('US-120 — /admin/branding guard user normal (non super-admin)', () => {
  test('/admin/branding avec user normal → redirect /client/dashboard', async ({
    page
  }) => {
    await seedRegularUserAuth(page)

    // Phase 1 : stabiliser le store auth sur page publique
    await page.goto('/?lang=fr', { waitUntil: 'domcontentloaded' })
    await page.waitForSelector('a[href="/client/dashboard"]', { timeout: 15_000 })

    // Phase 2 : navigation côté client vers /admin/branding via Vue Router
    await page.evaluate(() => {
      const appEl = document.querySelector('#app')
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const vueApp = (appEl as any)?.__vue_app__
      if (vueApp) {
        const router = vueApp.config.globalProperties.$router
        if (router) {
          router.push('/admin/branding?lang=fr')
          return
        }
      }
      window.location.href = '/admin/branding?lang=fr'
    })

    // Doit rediriger vers /client/dashboard?reason=not-super-admin
    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/client/dashboard',
      { timeout: 10_000 }
    )
    expect(page.url()).toMatch(/\/client\/dashboard/)
    expect(page.url()).toMatch(/not-super-admin/)
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// 3. Accès super-admin
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('US-120 — /admin/branding accès super-admin', () => {
  test('/admin/branding avec super-admin → h1 "Branding PDF" visible', async ({ page }) => {
    await seedSuperAdminAuth(page)
    await mockBrandingApi(page)

    await navigateAuthenticated(
      page,
      '/admin/branding',
      'a[href="/client/dashboard"]'
    )

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/admin/branding',
      { timeout: 10_000 }
    )

    // H1 doit contenir « Branding » ou équivalent
    const h1 = page.locator('h1').first()
    await expect(h1).toBeVisible({ timeout: 10_000 })
    await expect(h1).toContainText(/branding/i)
  })

  test('/admin/branding super-admin → topbar avec liens admin visibles', async ({ page }) => {
    await seedSuperAdminAuth(page)
    await mockBrandingApi(page)

    await navigateAuthenticated(
      page,
      '/admin/branding',
      'a[href="/client/dashboard"]'
    )

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/admin/branding',
      { timeout: 10_000 }
    )

    // Le topbar contient un lien vers /admin/quotes
    const quotesLink = page.locator('a[href="/admin/quotes"]').first()
    await expect(quotesLink).toBeVisible({ timeout: 8_000 })
  })

  test('/admin/branding super-admin → contrôle org_id et bouton nouveau visible', async ({
    page
  }) => {
    await seedSuperAdminAuth(page)
    await mockBrandingApi(page)

    await navigateAuthenticated(
      page,
      '/admin/branding',
      'a[href="/client/dashboard"]'
    )

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/admin/branding',
      { timeout: 10_000 }
    )

    // Input org_id visible
    const orgInput = page.locator('input#ab-org-id')
    await expect(orgInput).toBeVisible({ timeout: 8_000 })

    // Bouton « Nouveau branding » visible
    const newBtn = page.locator('button:has-text("Nouveau branding"), button:has-text("New branding")').first()
    await expect(newBtn).toBeVisible({ timeout: 8_000 })
  })

  test('/admin/branding super-admin → modal s\'ouvre au clic sur "Nouveau branding"', async ({
    page
  }) => {
    await seedSuperAdminAuth(page)
    await mockBrandingApi(page)

    await navigateAuthenticated(
      page,
      '/admin/branding',
      'a[href="/client/dashboard"]'
    )

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/admin/branding',
      { timeout: 10_000 }
    )

    // Cliquer sur « Nouveau branding »
    const newBtn = page.locator('button:has-text("Nouveau branding"), button:has-text("New branding")').first()
    await expect(newBtn).toBeVisible({ timeout: 8_000 })
    await newBtn.click()

    // Le modal doit apparaître (role dialog)
    const modal = page.locator('[role="dialog"]').first()
    await expect(modal).toBeVisible({ timeout: 5_000 })

    // Le champ « Nom » dans le modal doit être visible
    const nameInput = page.locator('input#ab-name')
    await expect(nameInput).toBeVisible({ timeout: 5_000 })
  })

  test('/admin/branding super-admin → modal contient sélecteur langue FR/EN/AR', async ({
    page
  }) => {
    await seedSuperAdminAuth(page)
    await mockBrandingApi(page)

    await navigateAuthenticated(
      page,
      '/admin/branding',
      'a[href="/client/dashboard"]'
    )

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/admin/branding',
      { timeout: 10_000 }
    )

    // Ouvrir le modal
    const newBtn = page.locator('button:has-text("Nouveau branding"), button:has-text("New branding")').first()
    await expect(newBtn).toBeVisible({ timeout: 8_000 })
    await newBtn.click()

    const modal = page.locator('[role="dialog"]').first()
    await expect(modal).toBeVisible({ timeout: 5_000 })

    // Sélecteur de langue FR/EN/AR dans le panneau aperçu
    const frBtn = modal.locator('button:has-text("FR")').first()
    const enBtn = modal.locator('button:has-text("EN")').first()
    const arBtn = modal.locator('button:has-text("AR")').first()

    await expect(frBtn).toBeVisible({ timeout: 5_000 })
    await expect(enBtn).toBeVisible({ timeout: 5_000 })
    await expect(arBtn).toBeVisible({ timeout: 5_000 })
  })

  test('/admin/branding super-admin → table OU état vide visibles après chargement', async ({
    page
  }) => {
    await seedSuperAdminAuth(page)
    await mockBrandingApi(page)

    await navigateAuthenticated(
      page,
      '/admin/branding',
      'a[href="/client/dashboard"]'
    )

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/admin/branding',
      { timeout: 10_000 }
    )

    // Remplir l'org_id et charger
    const orgInput = page.locator('input#ab-org-id')
    await expect(orgInput).toBeVisible({ timeout: 8_000 })

    // Attendre que l'API mock réponde (la liste est pré-remplie avec l'org du super-admin)
    // Si la table ou l'état vide est visible → la vue s'est bien chargée
    const table = page.locator('.ab-table, table')
    const emptyState = page.locator('.ab-state, .ab-preview-placeholder')

    const tableVisible = await table.first().isVisible().catch(() => false)
    const emptyVisible = await emptyState.first().isVisible().catch(() => false)

    // Au moins l'un doit être visible
    expect(
      tableVisible || emptyVisible,
      'La table ou l\'état vide doit être visible (vue rendue correctement)'
    ).toBe(true)
  })
})
