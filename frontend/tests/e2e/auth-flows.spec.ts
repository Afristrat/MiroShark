/**
 * Auth flows — /login + /signup (US-117)
 *
 * Couvre les nouvelles routes d'authentification multitenant introduites
 * en US-093 + US-096 :
 *   - /login : form email/password + Google OAuth + Magic Link
 *   - /signup : form complet + validation client-side
 *   - Mémorisation du `?next=` / `?redirect=` intent
 *   - Validation format email côté client
 *
 * STRICTEMENT READ-ONLY : aucun submit réel, aucune création de compte.
 * Tests UI-only + assertions DOM.
 */

import { expect, test } from '@playwright/test'
import { gotoLocalized } from './helpers'

test.describe('US-117 — /login UI', () => {
  test('/login rend le form email + password + bouton Se connecter (FR)', async ({ page }) => {
    await gotoLocalized(page, '/login', 'fr')

    // Eyebrow « Espace client »
    await expect(
      page.getByText('Espace client', { exact: false }).first()
    ).toBeVisible()

    // Titre principal
    await expect(
      page.getByText('Connexion', { exact: false }).first()
    ).toBeVisible()

    // Champ email
    const emailInput = page.locator('input[type="email"]').first()
    await expect(emailInput).toBeVisible()

    // Champ password
    const passwordInput = page.locator('input[type="password"]').first()
    await expect(passwordInput).toBeVisible()

    // Bouton submit
    const submitBtn = page.getByRole('button', { name: /connecter/i })
    await expect(submitBtn).toBeVisible()
  })

  test('/login affiche le bouton Google OAuth (FR)', async ({ page }) => {
    await gotoLocalized(page, '/login', 'fr')

    // Bouton Google doit être présent
    const googleBtn = page.locator('.auth-provider--google')
    await expect(googleBtn).toBeVisible()
    await expect(googleBtn).toContainText('Google')
  })

  test('/login affiche le bouton Magic Link (FR)', async ({ page }) => {
    await gotoLocalized(page, '/login', 'fr')

    // Bouton Magic Link
    const magicBtn = page.locator('.auth-provider--magic')
    await expect(magicBtn).toBeVisible()
    await expect(magicBtn).toContainText(/lien magique/i)
  })

  test('/login?next=/console mémorise l\'intent dans l\'URL', async ({ page }) => {
    // Navigation avec un paramètre next= (intent de redirect post-login)
    await page.goto('/login?next=/console&lang=fr', { waitUntil: 'domcontentloaded' })
    await page.waitForLoadState('load').catch(() => undefined)

    // La page /login doit charger (pas de redirect)
    expect(page.url()).toMatch(/\/login/)

    // Le formulaire est toujours visible
    await expect(page.locator('input[type="email"]').first()).toBeVisible()
  })

  test('/login?redirect=/console mémorise l\'intent (query param redirect)', async ({ page }) => {
    await page.goto('/login?redirect=%2Fconsole&lang=fr', { waitUntil: 'domcontentloaded' })
    await page.waitForLoadState('load').catch(() => undefined)

    expect(page.url()).toMatch(/\/login/)
    await expect(page.locator('input[type="email"]').first()).toBeVisible()
  })

  test('bouton Magic Link désactivé si email invalide', async ({ page }) => {
    await gotoLocalized(page, '/login', 'fr')

    const magicBtn = page.locator('.auth-provider--magic')
    await expect(magicBtn).toBeVisible()

    // Sans email → Magic Link désactivé (disabled attribut présent ou opacity)
    // Le composant désactive si !emailRe.test(email) — email vide → disabled
    const isDisabled = await magicBtn.evaluate((el: HTMLButtonElement) => el.disabled)
    expect(isDisabled, 'Magic Link doit être désactivé sans email valide').toBe(true)
  })

  test('bouton Magic Link activé après saisie d\'un email valide', async ({ page }) => {
    await gotoLocalized(page, '/login', 'fr')

    // Saisir un email valide
    const emailInput = page.locator('input[type="email"]').first()
    await emailInput.fill('test@example.com')

    // Magic Link doit devenir actif
    const magicBtn = page.locator('.auth-provider--magic')
    await expect(magicBtn).toBeEnabled({ timeout: 3_000 })
  })

  test('/login a la direction LTR en FR et RTL en AR', async ({ page }) => {
    await gotoLocalized(page, '/login', 'fr')
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr')

    await gotoLocalized(page, '/login', 'ar')
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  })

  test('/login contient un lien vers /signup', async ({ page }) => {
    await gotoLocalized(page, '/login', 'fr')

    // Lien « Créer un compte »
    const signupLink = page.getByRole('link', { name: /créer un compte/i })
    await expect(signupLink).toBeVisible()
    await expect(signupLink).toHaveAttribute('href', /signup/)
  })
})

test.describe('US-117 — /signup UI', () => {
  test('/signup rend le form complet (5 champs min) en FR', async ({ page }) => {
    await gotoLocalized(page, '/signup', 'fr')

    // Eyebrow « Création de compte »
    await expect(
      page.getByText('Création de compte', { exact: false }).first()
    ).toBeVisible()

    // Titre « Créer votre compte Bassira »
    await expect(
      page.getByText(/créer votre compte/i).first()
    ).toBeVisible()

    // Au moins 5 inputs (nom, orga, email, password, confirm password)
    const inputs = page.locator('input')
    const count = await inputs.count()
    expect(count, 'Au moins 5 champs dans le form signup').toBeGreaterThanOrEqual(5)
  })

  test('/signup form contient les champs clés (nom + orga + email + passwords)', async ({
    page
  }) => {
    await gotoLocalized(page, '/signup', 'fr')

    // Champs nom + organisation, vérifiés par leur nom accessible plutôt que
    // par le type HTML implicite, que le navigateur peut omettre du DOM sérialisé.
    await expect(page.getByRole('textbox', { name: 'Nom complet', exact: true })).toBeVisible()
    await expect(
      page.getByRole('textbox', { name: 'Nom de votre organisation', exact: true })
    ).toBeVisible()

    // Champ email
    await expect(page.locator('input[type="email"]').first()).toBeVisible()

    // Champs password
    const passwordInputs = page.locator('input[type="password"]')
    const pwCount = await passwordInputs.count()
    expect(pwCount, 'Au moins 2 champs password (password + confirm)').toBeGreaterThanOrEqual(2)
  })

  test('/signup bouton submit visible', async ({ page }) => {
    await gotoLocalized(page, '/signup', 'fr')

    // CTA « Créer mon compte »
    const submitBtn = page.getByRole('button', { name: /créer mon compte/i })
    await expect(submitBtn).toBeVisible()
  })

  test('/signup contient un lien vers /login', async ({ page }) => {
    await gotoLocalized(page, '/signup', 'fr')

    // Lien « Se connecter »
    const loginLink = page.getByRole('link', { name: /se connecter/i })
    await expect(loginLink.first()).toBeVisible()
  })

  test('/signup est LTR en FR', async ({ page }) => {
    await gotoLocalized(page, '/signup', 'fr')
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr')
  })
})
