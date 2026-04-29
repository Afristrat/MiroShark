/**
 * Bassira — Playwright config (US-010)
 *
 * Suite de smoke tests E2E read-only sur la prod
 *   https://prospectives.ai-mpower.com
 *
 * Override possible via la variable d'env BASSIRA_E2E_URL (utile en
 * dev local pour pointer sur http://localhost:5173).
 *
 * IMPORTANT — STRICTEMENT READ-ONLY :
 *   - Pas de création de simulation
 *   - Pas de soumission de devis
 *   - Pas d'écriture qui pollue la prod (leads fantômes)
 *
 * Lancement :
 *   npm run test:e2e          # full run
 *   npm run test:e2e:ui       # mode UI Playwright
 *   npm run test:e2e:list     # liste les tests sans les exécuter
 *
 * Doc complète : voir tests/e2e/README.md
 */

import { defineConfig, devices } from '@playwright/test'

const BASE_URL = process.env.BASSIRA_E2E_URL || 'https://prospectives.ai-mpower.com'
const IS_CI = !!process.env.CI

export default defineConfig({
  testDir: './tests/e2e',

  // Global timeouts — 30 s suffit largement pour des smoke tests sur prod.
  timeout: 30_000,
  expect: {
    timeout: 8_000,
  },

  fullyParallel: true,
  forbidOnly: IS_CI,
  retries: IS_CI ? 1 : 0,
  workers: IS_CI ? 2 : undefined,

  reporter: 'list',

  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    // User-Agent dédié — facilite le filtrage côté analytics si besoin.
    userAgent: 'BassiraE2E/1.0 (+playwright; read-only smoke tests)',
    // Pas de credentials, pas de service worker.
    serviceWorkers: 'block',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  outputDir: 'test-results/',
})
