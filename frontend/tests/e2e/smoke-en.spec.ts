/**
 * Smoke tests — locale EN (US-010)
 *
 * 5 vues critiques en anglais :
 *   1. Home /
 *   2. Calibration
 *   3. Offers
 *   4. Quote (Step 1 affiché, AUCUNE soumission)
 *   5. Explore
 *
 * Read-only.
 */

import { expect, test } from '@playwright/test'
import { gotoLocalized, I18N_FIXTURES } from './helpers'

const FX = I18N_FIXTURES.en

test.describe('EN — smoke', () => {
  test('Home / loads with translated hero + Browse our models CTA (US-087)', async ({ page }) => {
    const response = await page.goto('/?lang=en', { waitUntil: 'domcontentloaded' })
    expect(response?.status(), 'HTTP status of /').toBeLessThan(400)

    await expect(page.getByText(FX.home.title, { exact: false })).toBeVisible()

    const launchBtn = page.getByText(FX.home.launchCta, { exact: false })
    await expect(launchBtn.first()).toBeVisible()

    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr')
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  })

  test('/calibration charge et affiche au moins une stat card', async ({ page }) => {
    await gotoLocalized(page, '/calibration', 'en')

    await expect(page.locator('h1')).toBeVisible()

    // /calibration alias MethodologieView (US-201, ADR-002) : at least one
    // content card (`.mt-card`) must be present.
    const statCards = page.locator('.mt-card')
    await expect(statCards.first()).toBeVisible({ timeout: 15_000 })
  })

  test('/offres affiche le carousel 10 packages + FAQ', async ({ page }) => {
    await gotoLocalized(page, '/offres', 'en')

    const cards = page.locator('.offers-card')
    await expect(cards).toHaveCount(10)

    await expect(page.getByText(FX.offers.crisisDrillName, { exact: false }).first()).toBeVisible()

    const faq = page.locator('.offers-faq')
    await expect(faq).toBeVisible()
    await expect(faq.locator('details').first()).toBeVisible()
  })

  test('/devis affiche le stepper et les champs structurés du Temps 1 en anglais', async ({ page }) => {
    await gotoLocalized(page, '/devis', 'en')

    await expect(page.getByText(FX.quote.trustBannerSnippet, { exact: false })).toBeVisible()

    const steps = page.locator('.quote-step')
    await expect(steps).toHaveCount(3)

    await expect(page.locator('.quote-step-content textarea').first()).toBeVisible()
    await expect(page.locator('.quote-option-row input[type="text"]')).toHaveCount(2)
    await expect(page.locator('.quote-step-content input[type="date"]')).toBeAttached()
  })

  test('/explore charge sans erreur 4xx/5xx', async ({ page }) => {
    const response = await page.goto('/explore?lang=en', { waitUntil: 'domcontentloaded' })
    expect(response?.status(), 'HTTP status of /explore').toBeLessThan(400)

    const heading = page.locator('main, h1, h2').first()
    await expect(heading).toBeVisible()
  })
})
