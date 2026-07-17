/**
 * Console privative /console — tests multitenant (US-117)
 *
 * Complète console.spec.ts (US-107 — guards non-auth) avec des tests
 * de rendu authentifié (super-admin seed via localStorage mock).
 *
 * Stratégie d'auth :
 *   - `seedSuperAdminAuth(page)` pose une session fake en localStorage ET
 *     mock les appels réseau Supabase + API backend via `page.route()`.
 *   - `seedRegularUserAuth(page)` simule un user sans self_service_enabled.
 *
 * Read-only : aucun upload, aucun POST simulation déclenché.
 */

import { expect, test } from '@playwright/test'
import { navigateAuthenticated, seedSuperAdminAuth, seedRegularUserAuth } from './fixtures/auth'

test.describe('US-117 — /console guards (non-auth)', () => {
  // Ces tests dupliquent intentionnellement la couverture de console.spec.ts
  // pour valider que les guards sont stables après les refactors US-107+.

  test('/console sans auth → redirect /login avec ?redirect contenant console', async ({
    page
  }) => {
    await page.goto('/console?lang=fr', { waitUntil: 'domcontentloaded' })
    await page.waitForURL((url: URL): boolean => url.pathname === '/login', {
      timeout: 8_000
    })
    expect(page.url()).toMatch(/\/login/)
    expect(page.url()).toMatch(/redirect=/)
    expect(page.url()).toMatch(/console/)
  })
})

test.describe('US-117 — /console avec auth super-admin', () => {
  /**
   * Stratégie de navigation pour les routes protégées avec auth injectée :
   * 1. Injecter la session (addInitScript + page.route mock)
   * 2. Charger une page publique (/) pour que l'app monte et que
   *    auth.init() + fetchSuperStatus() + fetchProfile() s'exécutent
   * 3. Attendre un signal DOM prouvant que le store est STABLE :
   *    - Pour super-admin : le lien nav « Console » ou « ADMIN » apparaît
   *      (ils sont conditionnels à isSuperAdmin dans AppHeader)
   *    - Pour user normal : le lien « Mon espace » (isAuthenticated only)
   * 4. Naviguer vers la route protégée via router.push (client-side nav,
   *    pas de rechargement complet → le store Pinia est préservé)
   *
   * Évite la race condition entre auth.init()+fetchSuperStatus() (async)
   * et le guard router.
   */

  test('/console avec super-admin → page chargée (h1 ou console-main visible)', async ({
    page
  }) => {
    await seedSuperAdminAuth(page)

    await navigateAuthenticated(page, '/console')

    // Vérifier que l'URL est bien /console
    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/console',
      { timeout: 10_000 }
    )
    expect(page.url()).toMatch(/\/console/)

    // La page doit contenir le hero console ou un h1
    const hero = page.locator('.console-main, .console-hero, h1').first()
    await expect(hero).toBeVisible({ timeout: 10_000 })
  })

  test('/console avec super-admin → bouton Lancer visible', async ({ page }) => {
    await seedSuperAdminAuth(page)

    await navigateAuthenticated(page, '/console')

    await page.waitForURL((url: URL): boolean => url.pathname === '/console', {
      timeout: 10_000
    })

    // Chercher un bouton « Lancer » ou un CTA de lancement
    const launchBtn = page.locator(
      'button.launch-btn, button[type="submit"], .console-launch-btn'
    ).first()
    const launchByText = page.getByRole('button', { name: /lancer/i }).first()

    const btnVisible = await launchBtn.isVisible().catch(() => false)
    const textBtnVisible = await launchByText.isVisible().catch(() => false)

    expect(
      btnVisible || textBtnVisible,
      'Un bouton Lancer (ou équivalent) doit être visible sur /console authentifié'
    ).toBe(true)
  })

  test('/console avec user normal (no self-service) → redirect /client/dashboard', async ({
    page
  }) => {
    // User normal sans self_service_enabled → guard requiresSelfService KO
    await seedRegularUserAuth(page)

    // Stabilise le store puis navigue avec l'instance Vue Router montée.
    // Un pushState manuel contourne le routeur et peut déclencher un reload
    // qui perd la session mockée avant l'évaluation du guard.
    await navigateAuthenticated(page, '/console')

    // Doit rediriger vers /client/dashboard?reason=no-self-service
    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/client/dashboard',
      { timeout: 10_000 }
    )
    expect(page.url()).toMatch(/\/client\/dashboard/)
    expect(page.url()).toMatch(/no-self-service/)
  })
})
