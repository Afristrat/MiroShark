/**
 * Smoke tests — locale FR (US-010)
 *
 * 5 vues critiques en français :
 *   1. Home /
 *   2. Calibration
 *   3. Offers
 *   4. Quote (Step 1 affiché, AUCUNE soumission)
 *   5. Explore
 *
 * Read-only : aucun submit, aucun POST métier déclenché.
 */

import { expect, test } from '@playwright/test'
import { gotoLocalized, I18N_FIXTURES } from './helpers'

const FX = I18N_FIXTURES.fr

test.describe('FR — smoke', () => {
  test('Home / charge avec hero traduit + CTA Voir les modèles (US-087)', async ({ page }) => {
    const response = await page.goto('/?lang=fr', { waitUntil: 'domcontentloaded' })
    expect(response?.status(), 'HTTP status of /').toBeLessThan(400)

    // Le hero title doit être visible et localisé.
    await expect(page.getByText(FX.home.title, { exact: false })).toBeVisible()

    // US-087 — le hero CTA principal route vers /models et n'invite plus
    // au self-service. Le fixture FX.home.launchCta vaut désormais
    // « Voir les modèles ».
    const launchBtn = page.getByText(FX.home.launchCta, { exact: false })
    await expect(launchBtn.first()).toBeVisible()

    // Direction LTR pour FR.
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr')
    await expect(page.locator('html')).toHaveAttribute('lang', 'fr')
  })

  test('/calibration charge et affiche au moins une stat card', async ({ page }) => {
    await gotoLocalized(page, '/calibration', 'fr')

    // Le hero du calibration affiche le headline et le brand.
    await expect(page.locator('h1')).toBeVisible()

    // Au moins une stat card (`.cal-stat-card`) ou un SVG D3 doit être présent.
    const statCards = page.locator('.cal-stat-card, .cal-stats article, svg')
    await expect(statCards.first()).toBeVisible({ timeout: 15_000 })
  })

  test('/offres affiche le carousel 10 packages + prix MAD + FAQ', async ({ page }) => {
    await gotoLocalized(page, '/offres', 'fr')

    // 10 cards packages dans le carousel (refonte L99).
    const cards = page.locator('.offers-card')
    await expect(cards).toHaveCount(10)

    // Crisis Drill visible (nom EN inchangé d'une locale à l'autre).
    await expect(page.getByText(FX.offers.crisisDrillName, { exact: false }).first()).toBeVisible()

    // Au moins une card affiche un prix MAD.
    const crisisCard = page.locator('.offers-card[data-package="crisis_drill_24h"]')
    await expect(crisisCard).toHaveCount(1)
    const crisisText = await crisisCard.textContent()
    expect(crisisText, 'Crisis Drill contient un prix MAD').toMatch(/MAD/)

    // FAQ section visible.
    const faq = page.locator('.offers-faq')
    await expect(faq).toBeVisible()
    await expect(faq.locator('details').first()).toBeVisible()
  })

  test('/devis affiche stepper 3 dots + Step 1 avec 3 radios + banner', async ({ page }) => {
    await gotoLocalized(page, '/devis', 'fr')

    // Banner top "Votre message arrive directement aux fondateurs".
    await expect(page.getByText(FX.quote.trustBannerSnippet, { exact: false })).toBeVisible()

    // Stepper avec 3 steps.
    const steps = page.locator('.quote-step')
    await expect(steps).toHaveCount(3)

    // Step 1 actif et 3 radio options. Les inputs natifs sont visuellement
    // masqués (custom radio Stitch : opacity:0 + label stylé) — on vérifie
    // donc l'attachement DOM, pas la visibilité.
    const radios = page.locator('input[type="radio"]')
    await expect(radios.first()).toBeAttached()
    expect(await radios.count()).toBeGreaterThanOrEqual(3)

    // Et au moins un label de radio est visible (preuve que Step 1 est rendu).
    await expect(page.locator('.quote-radio-group label').first()).toBeVisible()
  })

  test('/explore charge sans erreur 4xx/5xx', async ({ page }) => {
    const response = await page.goto('/explore?lang=fr', { waitUntil: 'domcontentloaded' })
    expect(response?.status(), 'HTTP status of /explore').toBeLessThan(400)

    // h1 ou main visible.
    const heading = page.locator('main, h1, h2').first()
    await expect(heading).toBeVisible()
  })
})
