import { expect, test } from '@playwright/test'

const durablePath = '**/api/report/sim-us227/market-resolutions'
const legacyPath = '**/api/simulation/sim-us227/polymarket/**'

async function mount(page, live = false) {
  await page.evaluate(async (isLive) => {
    const { mountUs227 } = await import('/tests/e2e/fixtures/us227-harness.js')
    mountUs227({ live: isLive })
  }, live)
}

test('US-227 restitue les données durables et réserve le polling au direct', async ({ page }) => {
  let durableCalls = 0
  let legacyCalls = 0
  const resolved = {
      market_id: 1,
      question: 'Question durable',
      verdict: 'YES',
      justification: 'Les éléments de la simulation convergent.',
      confidence: 0.9,
      evidence: [{ round: 2, type: 'digest', ref: 'round:2:0' }],
      price_series: [{ round: 1, price_yes: 0.45 }, { round: 2, price_yes: 0.7 }],
      resolved_at: '2026-07-18T00:00:00+00:00',
  }
  let data = {
    simulation_id: 'sim-us227',
    resolutions: [resolved],
    final_wealth: [{ user_id: 7, cash_balance: 12.34567, open_position_value: 0, wealth: 12.34567, complete: true }],
    complete: true,
  }

  await page.route(durablePath, async (route) => {
    durableCalls += 1
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ success: true, data }) })
  })
  await page.route(legacyPath, async (route) => {
    legacyCalls += 1
    const url = route.request().url()
    const response = url.endsWith('/markets')
      ? { markets: [{ market_id: 9, question: 'Question directe', price_yes: 0.4, trade_count: 1, outcome_a: 'YES', outcome_b: 'NO' }] }
      : { market: { market_id: 9, question: 'Question directe', outcome_a: 'YES', outcome_b: 'NO' }, points: [{ price_yes: 0.4 }, { price_yes: 0.6 }] }
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ success: true, data: response }) })
  })

  await page.goto('/?lang=fr')
  await mount(page)

  await expect(page.getByTestId('adjudication-outcome')).toContainText('OUI')
  await expect(page.getByTestId('adjudication-date')).toBeVisible()
  await expect(page.getByTestId('adjudication-justification')).toContainText('Les éléments de la simulation convergent.')
  await expect(page.getByTestId('convergence-score')).toContainText('90.0%')
  await expect(page.getByTestId('adjudication-evidence')).toContainText('round:2:0')
  await expect(page.getByTestId('final-wealth')).toContainText('12,35')
  await expect(page.getByTestId('latest-point')).toBeVisible()
  await expect(page.getByTestId('chart-stats')).toContainText('POINTS DE PRIX')
  await expect(page.getByTestId('chart-stats')).not.toContainText('ÉCHANGES')
  await expect(page.getByTestId('chart-stats')).not.toContainText('VOLUME')
  expect(legacyCalls).toBe(0)

  data = { ...data, resolutions: [{ ...resolved, verdict: 'UNRESOLVED', confidence: null, evidence: [], resolved_at: null }] }
  await page.reload()
  await mount(page)
  await expect(page.getByTestId('unresolved-status')).toBeVisible()
  await expect(page.getByTestId('adjudication-outcome')).toHaveCount(0)
  await expect(page.getByTestId('adjudication-date')).toHaveCount(0)
  await expect(page.getByTestId('convergence-score')).toHaveCount(0)

  data = { ...data, resolutions: [], final_wealth: [], complete: false }
  await page.reload()
  await mount(page)
  await expect(page.getByText('Aucune question pour le moment.')).toBeVisible()

  data = { ...data, resolutions: [{ ...resolved, verdict: 'YES', price_series: [{ round: 1, price_yes: 0.7 }] }] }
  await page.reload()
  await mount(page)
  await expect(page.getByTestId('latest-point')).toBeVisible()

  data = { ...data, resolutions: [{ ...resolved, price_series: [] }] }
  await page.reload()
  await mount(page)
  await expect(page.getByTestId('no-price-series')).toBeVisible()
  await expect(page.getByText('50.0%', { exact: true })).toHaveCount(0)
  await expect(page.getByTestId('latest-point')).toHaveCount(0)
  expect(legacyCalls).toBe(0)

  const durableCallsBeforeLive = durableCalls
  await page.reload()
  await mount(page, true)
  await expect.poll(() => legacyCalls).toBeGreaterThanOrEqual(2)
  await page.waitForTimeout(4100)
  expect(legacyCalls).toBeGreaterThanOrEqual(4)
  expect(durableCalls).toBe(durableCallsBeforeLive)
})
