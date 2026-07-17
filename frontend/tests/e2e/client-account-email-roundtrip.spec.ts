import { test, expect, type Page } from '@playwright/test'
import { randomUUID } from 'node:crypto'
import { waitForEmail, extractMagicLink, trashMessage } from './fixtures/gmail-reader'

const ADMIN_EMAIL = 'medamine.mansouriidrissi@gmail.com'

test.skip(
  process.env.BASSIRA_E2E_WRITE !== '1',
  'Test d’intégration mutatif : définir BASSIRA_E2E_WRITE=1 pour autoriser les écritures en production.'
)

async function createQuote(baseURL: string, customerEmail: string, tag: string) {
  const res = await fetch(`${baseURL}/api/quote`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      full_name: `E2E Roundtrip ${tag}`,
      company: 'E2E Roundtrip Co',
      email: customerEmail,
      package: 'custom',
      consent_rgpd: true,
    }),
  })
  const body = await res.json()
  if (!res.ok || !body?.data?.quote_id) {
    throw new Error(`createQuote failed: ${res.status} ${JSON.stringify(body)}`)
  }
  return body.data.quote_id as string
}

async function loginAsAdmin(page: Page) {
  await page.goto('/login')
  await page.locator('input[type="email"]').fill(ADMIN_EMAIL)
  await page.locator('input[type="password"]').fill(process.env.BASSIRA_ADMIN_PASSWORD || '')
  await page.locator('button[type="submit"]').click()
  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 15_000 })
}

async function advanceQuoteToPaid(page: Page, quoteId: string) {
  // Navigation SPA (router-link), jamais page.goto('/admin/quotes') : un
  // reload complet fait courir une race entre la réhydratation Supabase
  // et le guard router, qui rebondit sur /login (constaté au spike Task 1).
  await page.locator('.app-header__admin-toggle').click()
  await page.locator('a[href="/admin/quotes"]').click()
  await page.waitForURL((url) => url.pathname === '/admin/quotes', { timeout: 15_000 })
  const row = page.locator('tr', { has: page.locator('.aq-id', { hasText: quoteId }) })
  await row.locator('.aq-action').click()

  // received → reviewing → quoted → paid : le premier bouton de
  // transition est toujours l'étape d'avancement (cf. ALLOWED_TRANSITIONS
  // backend, où l'élément "declined" est systématiquement en 2e position).
  for (let i = 0; i < 3; i++) {
    const advanceBtn = page.locator('.aq-transition-btn').first()
    await expect(advanceBtn).toBeEnabled({ timeout: 10_000 })
    await advanceBtn.click()
    await page.waitForTimeout(500) // laisse le PATCH + re-render se stabiliser
  }
}

test('round-trip complet : devis payé → email réel → magic link → dashboard', async ({
  page,
  context,
  baseURL,
}) => {
  test.setTimeout(90_000)

  const tag = `e2e-${randomUUID()}`
  const customerEmail = `a.mansouri+${tag}@afriquestrategie.com`

  const quoteId = await createQuote(baseURL!, customerEmail, tag)

  await loginAsAdmin(page)
  await advanceQuoteToPaid(page, quoteId)

  // 'Bassira' seul est trop générique : createQuote() déclenche aussi un
  // email de confirmation de devis ("... Votre demande ... est bien
  // arrivée") au même destinataire, avec le même préfixe de sujet — le
  // matching doit cibler le seul template contenant le magic link
  // (cf. client_account_service.py::_SUBJECT_BY_LOCALE).
  const email = await waitForEmail({
    toAddress: customerEmail,
    subjectContains: 'espace client est prêt',
    timeoutMs: 30_000,
  })
  const magicLink = extractMagicLink(email.html)
  expect(magicLink, 'magic link introuvable dans le corps HTML reçu').not.toBeNull()

  // Nouveau contexte : la session admin ne doit pas contaminer ce test.
  const clientContext = await context.browser()!.newContext()
  const clientPage = await clientContext.newPage()
  await clientPage.goto(magicLink!)

  await clientPage.waitForURL(
    (url) => url.pathname === '/client/dashboard',
    { timeout: 15_000 }
  )
  const eyebrow = clientPage.locator('.dash-hero-eyebrow, .dash-hero').first()
  await expect(eyebrow).toBeVisible({ timeout: 10_000 })

  await clientContext.close()
  await trashMessage(email.id)
})
