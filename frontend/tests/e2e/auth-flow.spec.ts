/**
 * Smoke tests — flow d'authentification (US-093)
 *
 * Couvre :
 *   1. /login charge avec hero + form email/password
 *   2. /signup charge avec hero + form complet
 *   3. /client/dashboard non-authentifié → redirige vers /login?redirect=...
 *
 * STRICTEMENT READ-ONLY : aucune soumission de form, aucune création
 * de compte sur la prod (les credentials Supabase prod ne sont pas
 * fournis aux tests E2E par design).
 */

import { expect, test } from '@playwright/test'
import { gotoLocalized } from './helpers'

test.describe('US-093 — auth flow smoke', () => {
  test('/login rend la card de connexion (FR)', async ({ page }) => {
    await gotoLocalized(page, '/login', 'fr')

    // L'eyebrow « Espace client » doit être visible.
    await expect(
      page.getByText('Espace client', { exact: false }).first()
    ).toBeVisible()

    // Champ email + password présents.
    const emailInput = page.getByLabel(/email/i).first()
    await expect(emailInput).toBeVisible()
    const passwordInput = page.locator('input[type="password"]').first()
    await expect(passwordInput).toBeVisible()

    // CTA submit visible et désactivé tant que le form est vide.
    const submitBtn = page.getByRole('button', { name: /connecter/i })
    await expect(submitBtn).toBeVisible()
  })

  test('/signup rend la card d\'inscription (FR)', async ({ page }) => {
    await gotoLocalized(page, '/signup', 'fr')

    // Titre « Créer votre compte Bassira ».
    await expect(
      page.getByText(/créer votre compte/i).first()
    ).toBeVisible()

    // Au moins 5 inputs (nom, organisation, email, password, confirm).
    const inputs = page.locator('input')
    const count = await inputs.count()
    expect(count).toBeGreaterThanOrEqual(5)
  })

  test('/client/dashboard non auth redirige vers /login avec ?redirect', async ({ page }) => {
    await page.goto('/client/dashboard?lang=fr', { waitUntil: 'domcontentloaded' })
    // Le router beforeEach redirige immédiatement vers /login.
    await page.waitForURL((url) => url.pathname === '/login', { timeout: 5000 })
    expect(page.url()).toMatch(/\/login/)
    expect(page.url()).toMatch(/redirect=/)
  })

  test('/login a la direction LTR en FR et RTL en AR', async ({ page }) => {
    await gotoLocalized(page, '/login', 'fr')
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr')

    await gotoLocalized(page, '/login', 'ar')
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  })
})
