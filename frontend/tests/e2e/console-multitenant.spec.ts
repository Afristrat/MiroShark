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
import { seedSuperAdminAuth, seedRegularUserAuth } from './fixtures/auth'

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

    // Étape 1 : page publique pour init auth store complet
    await page.goto('/?lang=fr', { waitUntil: 'domcontentloaded' })

    // Signal : lien « Console » dans le header (visible uniquement si
    // isSuperAdmin || self_service_enabled — injecté par fetchSuperStatus)
    // Ou « ADMIN » (super-admin only). Attente jusqu'à 15s (fetchSuperStatus async)
    await page.waitForSelector(
      'a.app-header__link[href="/console"], a[href="/admin/quotes"]',
      { timeout: 15_000 }
    )

    // Étape 2 : navigation côté client vers /console (pas de rechargement)
    await page.evaluate(() => { window.history.pushState({}, '', '/console') })
    await page.dispatchEvent('body', 'popstate')

    // Alternativement : click sur le lien Console du header
    const consoleLink = page.locator('a.app-header__link[href="/console"]').first()
    if (await consoleLink.isVisible().catch(() => false)) {
      await consoleLink.click()
    } else {
      // Fallback : navigate directement
      await page.goto('/console?lang=fr', { waitUntil: 'domcontentloaded' })
    }

    await page.waitForLoadState('load').catch(() => undefined)

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

    // Pré-charger une page publique pour stabiliser le store auth
    await page.goto('/?lang=fr', { waitUntil: 'domcontentloaded' })
    await page.waitForSelector(
      'a.app-header__link[href="/console"], a[href="/admin/quotes"]',
      { timeout: 15_000 }
    )

    // Si une modale d'onboarding bloque les interactions, la fermer.
    // La modale a un bouton « Passer » ou peut être fermée via Escape.
    const onbDialog = page.locator('[role="dialog"].onb-root, .onb-root')
    if (await onbDialog.isVisible().catch(() => false)) {
      const passerBtn = onbDialog.getByText('Passer').first()
      if (await passerBtn.isVisible().catch(() => false)) {
        await passerBtn.click({ force: true })
      } else {
        await page.keyboard.press('Escape')
      }
      // Attendre que le dialog disparaisse
      await onbDialog.waitFor({ state: 'hidden', timeout: 3_000 }).catch(() => undefined)
    }

    // Cliquer sur le lien Console du header (vue-router push, pas de rechargement)
    const consoleLink = page.locator('a.app-header__link[href="/console"]').first()
    await consoleLink.click()

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

    // Pré-charger une page publique pour stabiliser le store auth
    await page.goto('/?lang=fr', { waitUntil: 'domcontentloaded' })
    // Signal : lien « Mon espace » visible pour user normal authentifié
    await page.waitForSelector('a[href="/client/dashboard"]', {
      timeout: 15_000
    })

    // Navigation côté client vers /console
    // (le store Pinia est stable et persisté en mémoire)
    await page.evaluate(() => {
      // Utilise l'API vue-router via window.__vueRouter si disponible
      // Sinon pushState + popstate pour déclencher le guard
      window.history.pushState({}, '', '/console?lang=fr')
      window.dispatchEvent(new PopStateEvent('popstate'))
    })

    // Doit rediriger vers /client/dashboard?reason=no-self-service
    await page.waitForURL(
      (url: URL): boolean => url.pathname === '/client/dashboard',
      { timeout: 10_000 }
    )
    expect(page.url()).toMatch(/\/client\/dashboard/)
    expect(page.url()).toMatch(/no-self-service/)
  })
})
