/**
 * Parcours de qualification /devis « 3 temps » A1-A8 (US-IQ-01).
 *
 * Vérifie, dans les 3 locales (fr/en/ar) :
 *   - Les 3 écrans (Temps 1/2/3) s'enchaînent et affichent leur micro-copy
 *     de réciprocité.
 *   - A1 (≥15 caractères) et A2 (≥2 options) bloquent le passage du
 *     Temps 1 côté client — le CTA « suivant » reste désactivé sinon.
 *   - A7 (pays + segment) + l'identité bloquent la soumission du Temps 3.
 *   - RTL correct en arabe (`<html dir="rtl">`).
 *
 * IMPORTANT — STRICTEMENT READ-ONLY (même politique que
 * tunnel-commercial.spec.ts) : on remplit les champs jusqu'à activer le
 * bouton final, mais ON NE CLIQUE JAMAIS submit → aucun POST business
 * réel, aucun lead fantôme sur la cible testée (prod ou preview local).
 */

import { expect, test } from '@playwright/test'
import { gotoLocalized, Locale } from './helpers'

const LOCALES: Locale[] = ['fr', 'en', 'ar']

test.describe('Parcours intake /devis — 3 temps (US-IQ-01)', () => {
  for (const locale of LOCALES) {
    test(`(${locale}) Temps 1 → 2 → 3 : navigation + validations client`, async ({ page }) => {
      await gotoLocalized(page, '/devis', locale)

      // RTL correct en arabe.
      if (locale === 'ar') {
        await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
      }

      // ── Temps 1 — La décision (A1-A3) ──
      const steps = page.locator('.quote-step')
      await expect(steps).toHaveCount(3)
      await expect(page.locator('.quote-reciprocity')).toBeVisible()

      const nextBtn = page.locator('.quote-step-content button[type="submit"]')
      await expect(nextBtn).toBeDisabled()

      // A1 trop court : toujours désactivé.
      const decision = page.locator('.quote-step-content textarea').first()
      await decision.fill('Trop court')
      await expect(nextBtn).toBeDisabled()

      // A1 valide (≥15 caractères) mais A2 encore incomplet.
      await decision.fill('Lancer la filiale Sénégal maintenant ou attendre 2027')
      await expect(nextBtn).toBeDisabled()

      // A2 — 2 options minimum.
      const optionInputs = page.locator('.quote-option-row input[type="text"]')
      await expect(optionInputs).toHaveCount(2)
      await optionInputs.nth(0).fill('Lancer maintenant')
      await optionInputs.nth(1).fill('Attendre 2027')

      await expect(nextBtn).toBeEnabled()
      await nextBtn.click()

      // ── Temps 2 — Le passé (rien de bloquant, A4/A5 optionnels) ──
      await expect(page.locator('.quote-reciprocity')).toBeVisible()
      const nextBtn2 = page.locator('.quote-step-content button[type="submit"]')
      await expect(nextBtn2).toBeEnabled()
      await nextBtn2.click()

      // ── Temps 3 — L'enjeu et la matière (A6-A8) + identité ──
      await expect(page.locator('.quote-reciprocity')).toBeVisible()
      const submitBtn = page.locator('.quote-step-content button[type="submit"]')
      await expect(submitBtn).toBeDisabled()

      // A7 — au moins un pays (1er checkbox du 1er groupe) + un segment
      // (1er input texte de l'écran, avant les 3 champs d'identité).
      // L'input natif est masqué (chip custom, cf. .quote-checkbox-chip) —
      // on clique le label visible, pas l'input (même pattern que les
      // radios de l'ancien Step 1, cf. git history de ce fichier).
      await page.locator('.quote-checkbox-group .quote-checkbox-chip').first().click()
      const texts = page.locator('.quote-step-content input[type="text"]')
      await texts.nth(0).fill('Grand public urbain') // A7 segment
      await texts.nth(1).fill('Karim Bensaid') // identité : nom complet
      await texts.nth(2).fill('Banque Populaire MA') // identité : organisation

      await page.locator('input[type="email"]').fill('karim@example.com')
      await page.locator('.quote-consent-stitch input[type="checkbox"]').check()

      await expect(submitBtn).toBeEnabled()
      // GARDE-FOU : jamais de clic sur submit — lecture seule, aucun lead
      // fantôme créé par la suite E2E.
    })
  }
})

test('US-IQ-05 — porte AAR remplace A3 par l’issue réelle et reste en lecture seule', async ({ page }) => {
  await gotoLocalized(page, '/devis?entry=aar', 'fr')
  await expect(page.getByText('Quelle a été l’issue réelle ?')).toBeVisible()
  await expect(page.getByText(/chiffrée dès l’envoi/)).toBeVisible()
  await expect(page.locator('input[type="date"]')).toHaveCount(0)
  await page.locator('.quote-step-content textarea').first().fill('Lancer la filiale Sénégal maintenant ou attendre 2027')
  const options = page.locator('.quote-option-row input')
  await options.nth(0).fill('Lancer maintenant')
  await options.nth(1).fill('Attendre')
  const next = page.locator('.quote-step-content button[type="submit"]')
  await expect(next).toBeDisabled()
  await page.locator('.quote-step-content textarea').nth(1).fill('La filiale a atteint son seuil de rentabilité en neuf mois.')
  await expect(next).toBeEnabled()
})

test.describe('Écran Assistant — clôtures mockées (US-IQ-02 frontend)', () => {
  async function fillAndSubmit(page: import('@playwright/test').Page, locale: Locale) {
    await gotoLocalized(page, '/devis', locale)
    const decision = page.locator('.quote-step-content textarea').first()
    await decision.fill('Lancer la filiale Sénégal maintenant ou attendre 2027')
    const optionInputs = page.locator('.quote-option-row input[type="text"]')
    await optionInputs.nth(0).fill('Lancer maintenant')
    await optionInputs.nth(1).fill('Attendre 2027')
    await page.locator('.quote-step-content button[type="submit"]').click()
    await page.locator('.quote-step-content button[type="submit"]').click() // Temps 2 → 3
    await page.locator('.quote-checkbox-group .quote-checkbox-chip').first().click()
    const texts = page.locator('.quote-step-content input[type="text"]')
    await texts.nth(0).fill('Grand public urbain')
    await texts.nth(1).fill('Karim Bensaid')
    await texts.nth(2).fill('Banque Populaire MA')
    await page.locator('input[type="email"]').fill('karim@example.com')
    await page.locator('.quote-consent-stitch input[type="checkbox"]').check()
  }

  test('(fr) clôture route=meeting — lien Cal.com cliquable affiché', async ({ page }) => {
    await page.route('**/api/intake/session', (r) =>
      r.fulfill({ json: { success: true, data: { session_id: 'sess-mock-1', state: 'started', locale: 'fr' } } }),
    )
    await page.route('**/api/intake/session/sess-mock-1/form', (r) =>
      r.fulfill({ json: { success: true, data: { session_id: 'sess-mock-1', quote_id: 'q_mock1', state: 'form_submitted' } } }),
    )
    await page.route('**/api/intake/session/sess-mock-1/agent/turn', (r) =>
      r.fulfill({
        json: {
          success: true,
          data: {
            session_id: 'sess-mock-1', state: 'completed', agent_turns: 1,
            message: 'Merci, votre brief est transmis.', close: true,
            confidential_flags: [], route: 'meeting',
            calcom_link: 'https://agenda.ai-mpower.com/a.mansouri/entretien-bassira-20-min?email=karim%40example.com',
          },
        },
      }),
    )

    await fillAndSubmit(page, 'fr')
    await page.locator('.quote-step-content button[type="submit"]').click() // Temps 3 submit
    await expect(page.getByRole('link', { name: /voir mon créneau/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /voir mon créneau/i })).toHaveAttribute(
      'href', /agenda\.ai-mpower\.com/,
    )
  })

  test('(fr) clôture route=self_service — package recommandé affiché', async ({ page }) => {
    await page.route('**/api/intake/session', (r) =>
      r.fulfill({ json: { success: true, data: { session_id: 'sess-mock-2', state: 'started', locale: 'fr' } } }),
    )
    await page.route('**/api/intake/session/sess-mock-2/form', (r) =>
      r.fulfill({ json: { success: true, data: { session_id: 'sess-mock-2', quote_id: 'q_mock2', state: 'form_submitted' } } }),
    )
    await page.route('**/api/intake/session/sess-mock-2/agent/turn', (r) =>
      r.fulfill({
        json: {
          success: true,
          data: {
            session_id: 'sess-mock-2', state: 'completed', agent_turns: 1,
            message: 'Merci, votre brief est transmis.', close: true,
            confidential_flags: [], route: 'self_service',
            package_recommendation: { package_id: 'adcheck_lite', rationale: 'Test de concept publicitaire.' },
          },
        },
      }),
    )

    await fillAndSubmit(page, 'fr')
    await page.locator('.quote-step-content button[type="submit"]').click()
    await expect(page.locator('.quote-step-content')).toContainText('Adcheck Lite')
  })

  test('(fr) gateway LLM indisponible — bannière neutre de repli, pas d\'erreur', async ({ page }) => {
    await page.route('**/api/intake/session', (r) =>
      r.fulfill({ json: { success: true, data: { session_id: 'sess-mock-3', state: 'started', locale: 'fr' } } }),
    )
    await page.route('**/api/intake/session/sess-mock-3/form', (r) =>
      r.fulfill({ json: { success: true, data: { session_id: 'sess-mock-3', quote_id: 'q_mock3', state: 'form_submitted' } } }),
    )
    await page.route('**/api/intake/session/sess-mock-3/agent/turn', (r) =>
      r.fulfill({
        json: {
          success: true,
          data: {
            session_id: 'sess-mock-3', state: 'completed', route: 'quote_48h', agent_unavailable: true,
          },
        },
      }),
    )

    await fillAndSubmit(page, 'fr')
    await page.locator('.quote-step-content button[type="submit"]').click()
    await expect(page.getByText(/nous revenons vers vous sous 48/i)).toBeVisible()
    await expect(page.locator('.quote-error')).toHaveCount(0)
  })
})
