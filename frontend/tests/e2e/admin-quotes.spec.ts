/**
 * Admin Quotes /admin/quotes — tests multitenant (US-117)
 *
 * Couvre :
 *   1. Guard non-auth → redirect /login
 *   2. Guard user normal (non super-admin) → redirect /client/dashboard
 *   3. Accès super-admin → page rendue avec h1, filtres, topbar analytics link
 *
 * Read-only : aucun PATCH status, aucun envoi d'email déclenché.
 *
 * Note sur la stratégie de mock :
 * Les tests super-admin naviguent via le lien header (Vue Router push,
 * pas de rechargement). La vue appelle `loadQuotes()` via onMounted.
 * La réponse API peut être vide (prod) ou mockée selon le test.
 * Les tests structurels (h1, filtres, topbar) ne dépendent pas de données.
 */

import { expect, test } from '@playwright/test'
import { seedSuperAdminAuth, seedRegularUserAuth, navigateAuthenticated } from './fixtures/auth'

test.describe('US-117 — /admin/quotes guards (non-auth)', () => {
  test('/admin/quotes sans auth → redirect /login avec ?redirect contenant admin', async ({
    page
  }) => {
    await page.goto('/admin/quotes?lang=fr', { waitUntil: 'domcontentloaded' })
    await page.waitForURL((url: URL): boolean => url.pathname === '/login', {
      timeout: 8_000
    })
    expect(page.url()).toMatch(/\/login/)
    expect(page.url()).toMatch(/redirect=/)
    expect(page.url()).toMatch(/admin/)
  })
})

test.describe('US-117 — /admin/quotes guard user normal (non super-admin)', () => {
  test('/admin/quotes avec user normal → redirect /client/dashboard (not-super-admin)', async ({
    page
  }) => {
    // User non super-admin → guard requiresSuperAdmin KO
    await seedRegularUserAuth(page)

    // Phase 1 : stabiliser le store auth sur page publique
    await page.goto('/?lang=fr', { waitUntil: 'domcontentloaded' })
    await page.waitForSelector('a[href="/client/dashboard"]', { timeout: 15_000 })

    // Phase 2 : navigation côté client vers /admin/quotes via Vue Router
    await page.evaluate(() => {
      const appEl = document.querySelector('#app')
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const vueApp = (appEl as any)?.__vue_app__
      if (vueApp) {
        const router = vueApp.config.globalProperties.$router
        if (router) {
          router.push('/admin/quotes?lang=fr')
          return
        }
      }
      window.location.href = '/admin/quotes?lang=fr'
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

test.describe('US-117 — /admin/quotes accès super-admin', () => {
  /**
   * Tests structurels ne dépendant PAS des données de la liste.
   * La page peut afficher « Aucun devis » ou des données réelles —
   * ce qui compte est que la structure (h1, filtres, topbar) est rendue.
   */

  test('/admin/quotes avec super-admin → h1 visible', async ({ page }) => {
    await seedSuperAdminAuth(page)

    await navigateAuthenticated(page, '/admin/quotes')

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/admin/quotes',
      { timeout: 10_000 }
    )

    // H1 « Tous les devis reçus » visible
    const h1 = page.locator('h1').first()
    await expect(h1).toBeVisible({ timeout: 10_000 })
    await expect(h1).toContainText(/devis/i)
  })

  test('/admin/quotes super-admin → filtre status visible', async ({ page }) => {
    await seedSuperAdminAuth(page)

    await navigateAuthenticated(page, '/admin/quotes')

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/admin/quotes',
      { timeout: 10_000 }
    )

    // Section filtres avec select statut
    const filtersSection = page.locator('.aq-filters')
    await expect(filtersSection).toBeVisible({ timeout: 10_000 })

    const statusSelect = page.locator('.aq-filters select')
    await expect(statusSelect).toBeVisible()
  })

  test('/admin/quotes super-admin → lien /admin/analytics visible dans topbar', async ({
    page
  }) => {
    await seedSuperAdminAuth(page)

    await navigateAuthenticated(page, '/admin/quotes')

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/admin/quotes',
      { timeout: 10_000 }
    )

    // Le topbar de AdminQuotesView affiche un lien vers /admin/analytics
    await page.locator('.app-header__admin-toggle').click()
    const analyticsLink = page.locator('a[href="/admin/analytics"]').first()
    await expect(analyticsLink).toBeVisible({ timeout: 8_000 })
  })

  test('/admin/quotes super-admin → table OU état vide visibles', async ({ page }) => {
    await seedSuperAdminAuth(page)

    await navigateAuthenticated(page, '/admin/quotes')

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/admin/quotes',
      { timeout: 10_000 }
    )

    // Après chargement, soit la table soit l'état vide doit être visible
    // (on ne mockne pas l'API prod — on accepte les deux cas)
    const table = page.locator('.aq-table, table')
    const emptyState = page.locator('.aq-empty, .aq-loading')

    const tableVisible = await table.first().isVisible().catch(() => false)
    const emptyVisible = await emptyState.first().isVisible().catch(() => false)

    // Au moins l'un des deux doit être visible (la vue s'est bien chargée)
    expect(
      tableVisible || emptyVisible,
      'La table ou l\'état vide doit être visible (la vue est rendue)'
    ).toBe(true)
  })

  test('/admin/quotes super-admin → subtitle visible (sous-titre console admin)', async ({
    page
  }) => {
    await seedSuperAdminAuth(page)

    await navigateAuthenticated(page, '/admin/quotes')

    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/admin/quotes',
      { timeout: 10_000 }
    )

    // Sous-titre « Console super-admin Bassira »
    const subtitle = page.locator('.aq-sub, .aq-hero p').first()
    await expect(subtitle).toBeVisible({ timeout: 8_000 })
    await expect(subtitle).toContainText(/super-admin|Bassira|commercial/i)
  })
})
