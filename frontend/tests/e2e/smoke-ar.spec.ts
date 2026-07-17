/**
 * Smoke tests — locale AR (US-010)
 *
 * 5 vues critiques en arabe + vérification RTL.
 *   1. Home / (RTL)
 *   2. Calibration
 *   3. Offers
 *   4. Quote (Step 1, AUCUNE soumission)
 *   5. Explore
 *
 * Spécificités AR :
 *   - <html dir="rtl"> sur toutes les pages
 *   - <html lang="ar">
 *   - Le LanguageSwitcher affiche AR comme code actif
 *
 * Read-only.
 */

import { expect, test } from '@playwright/test'
import { gotoLocalized, I18N_FIXTURES } from './helpers'

const FX = I18N_FIXTURES.ar

test.describe('AR — smoke + RTL', () => {
  test('Home / charge en RTL avec hero traduit + CTA arabe', async ({ page }) => {
    const response = await page.goto('/?lang=ar', { waitUntil: 'domcontentloaded' })
    expect(response?.status(), 'HTTP status of /').toBeLessThan(400)

    // Vérification RTL stricte : c'est le test load-bearing pour AR.
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
    await expect(page.locator('html')).toHaveAttribute('lang', 'ar')

    // Le hero AR doit être présent (texte arabe).
    await expect(page.getByText(FX.home.title, { exact: false })).toBeVisible()

    // US-087 — le CTA hero principal route vers /models et n'invite plus
    // au self-service. Le fixture FX.home.launchCta vaut désormais
    // « تصفّح النماذج » (« Voir les modèles » en arabe).
    const launchBtn = page.getByText(FX.home.launchCta, { exact: false })
    await expect(launchBtn.first()).toBeVisible()

    // Le language switcher montre AR comme actif.
    const switcherCode = page.locator('.lang-switcher__code')
    await expect(switcherCode).toHaveText(FX.langCode)
  })

  test('/calibration RTL + stats visibles', async ({ page }) => {
    await gotoLocalized(page, '/calibration', 'ar')

    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
    await expect(page.locator('h1')).toBeVisible()

    // /calibration alias MethodologieView (US-201, ADR-002) : au moins une
    // carte de contenu (`.mt-card`) doit être présente.
    const statCards = page.locator('.mt-card')
    await expect(statCards.first()).toBeVisible({ timeout: 15_000 })
  })

  test('/offres RTL + carousel 10 packages + FAQ', async ({ page }) => {
    await gotoLocalized(page, '/offres', 'ar')

    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')

    const cards = page.locator('.offers-card')
    await expect(cards).toHaveCount(10)

    const faq = page.locator('.offers-faq')
    await expect(faq).toBeVisible()
    await expect(faq.locator('details').first()).toBeVisible()
  })

  test('/devis RTL affiche les champs structurés du Temps 1 en arabe', async ({ page }) => {
    await gotoLocalized(page, '/devis', 'ar')

    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')

    // Banner AR : "تصل رسالتكم مباشرة إلى المؤسّسين"
    await expect(page.getByText(FX.quote.trustBannerSnippet, { exact: false })).toBeVisible()

    const steps = page.locator('.quote-step')
    await expect(steps).toHaveCount(3)

    await expect(page.locator('.quote-step-content textarea').first()).toBeVisible()
    await expect(page.locator('.quote-option-row input[type="text"]')).toHaveCount(2)
    await expect(page.locator('.quote-step-content input[type="date"]')).toBeAttached()
  })

  test('/explore RTL et pas d\'erreur 4xx/5xx', async ({ page }) => {
    const response = await page.goto('/explore?lang=ar', { waitUntil: 'domcontentloaded' })
    expect(response?.status(), 'HTTP status of /explore').toBeLessThan(400)

    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')

    const heading = page.locator('main, h1, h2').first()
    await expect(heading).toBeVisible()
  })
})
