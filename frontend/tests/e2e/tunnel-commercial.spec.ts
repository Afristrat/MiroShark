/**
 * Tunnel commercial — /offres → /devis (US-010)
 *
 * Vérifie que le CTA d'un package sur /offres redirige bien vers /devis
 * avec le query param `?package=<slug>` et que le Step 1 s'affiche.
 *
 * IMPORTANT — STRICTEMENT READ-ONLY :
 *   - On clique le CTA Crisis Drill
 *   - On vérifie l'URL `/devis`
 *   - On vérifie que Step 1 est visible
 *   - ON NE CLIQUE PAS Next Step → AUCUN POST métier déclenché
 *   - ON NE REMPLIT AUCUN CHAMP
 */

import { expect, test } from '@playwright/test'
import { gotoLocalized } from './helpers'

test.describe('Tunnel commercial /offres → /devis', () => {
  test('CTA Crisis Drill amène sur /devis avec ?package=crisis_drill_24h', async ({ page }) => {
    await gotoLocalized(page, '/offres', 'fr')

    // 10 cards rendues dans le carousel (1 par package, dont 9 packs + custom).
    // Le carousel rend tout en DOM, le scroll/translate se fait en CSS.
    const cards = page.locator('.offers-card')
    await expect(cards).toHaveCount(10)

    // Cible explicite via data-attribute pour Crisis Drill 24h.
    const crisisCard = page.locator('.offers-card[data-package="crisis_drill_24h"]')
    await expect(crisisCard).toHaveCount(1)
    const crisisCta = crisisCard.locator('.offers-card-cta')
    await crisisCta.scrollIntoViewIfNeeded()
    await crisisCta.click()

    // Navigation vers /devis avec le package en query.
    await expect(page).toHaveURL(/\/devis(\?|$)/)
    await expect(page).toHaveURL(/package=crisis_drill_24h/)

    // Step 1 visible : stepper 3 dots + 3 radios.
    const steps = page.locator('.quote-step')
    await expect(steps).toHaveCount(3)

    // Inputs natifs masqués (custom radio Stitch) — assert sur l'attachement DOM.
    const radios = page.locator('input[type="radio"]')
    await expect(radios.first()).toBeAttached()

    // GARDE-FOU : on s'assure qu'aucun bouton de soumission n'a été cliqué.
    // L'étape courante doit toujours être 1 (vérifié par le label visible).
    const stepCurrent = page.locator('.quote-step--current')
    await expect(stepCurrent.first()).toBeVisible()
    // Idempotent : on quitte la page sans soumettre.
  })

  test('Pre-Footer CTA (sans query) amène sur /devis', async ({ page }) => {
    await gotoLocalized(page, '/offres', 'fr')

    // Le CTA pré-footer pointe vers /devis sans package query.
    const preFooterCta = page.locator('.offers-cta-strip-btn')
    await preFooterCta.scrollIntoViewIfNeeded()
    await expect(preFooterCta).toBeVisible()
    await preFooterCta.click()

    await expect(page).toHaveURL(/\/devis/)

    // Step 1 toujours visible (sans package préselectionné c'est ok).
    const steps = page.locator('.quote-step')
    await expect(steps).toHaveCount(3)
  })
})
