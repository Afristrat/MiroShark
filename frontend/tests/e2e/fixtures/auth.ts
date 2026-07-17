/**
 * Fixtures d'authentification pour les tests E2E multitenant (US-117)
 *
 * Stratégie :
 *   1. `seedSuperAdminAuth(page)` — injecte une fausse session Supabase en
 *      localStorage (clé `bassira_supabase_auth`) + mock les API backend
 *      `/api/client/auth/me` et `/api/admin/me/super-status` pour simuler
 *      un super-admin complet.
 *   2. `seedRegularUserAuth(page)` — même chose mais isSuperAdmin = false.
 *
 * Stratégie d'injection : l'`addInitScript` s'exécute dans le contexte
 * navigateur AVANT tout JS de l'app. Le script construit un JWT fake
 * côté browser (btoa disponible) et l'écrit dans localStorage. Il
 * intercepte aussi Supabase JS avant son initialisation pour que
 * `supabase.auth.getSession()` retourne directement notre session sans
 * appel réseau — évitant le cas race entre init() et le guard router.
 *
 * IMPORTANT : appelez ces helpers AVANT tout `page.goto(...)`.
 *
 * URL Supabase prod : https://fvfifgstytvxssffvsbs.supabase.co
 * (extraite du bundle index-CtrTJkxa.js — si le bundle est rebuild,
 *  vérifier que l'URL n'a pas changé ; en pratique elle est stable
 *  sur toute la durée de vie du projet).
 */

import type { Page } from '@playwright/test'

// Email super-admin tel qu'enregistré dans la whitelist backend prod.
// (cf. mémo passation — BASSIRA_SUPER_ADMIN_EMAILS)
export const SUPER_ADMIN_EMAIL = 'medamine.mansouriidrissi@gmail.com'
export const REGULAR_USER_EMAIL = 'testuser@acme-bassira.com'

// UUID fictif stable pour les tests (non-présent en base Supabase prod)
const FAKE_USER_ID = '00000000-0000-0000-0000-000000000042'
const FAKE_ORG_ID = '00000000-0000-0000-0000-000000000099'

// URL du projet Supabase (utilisée pour le matching des routes cross-origin)
const SUPABASE_URL_PATTERN = '**/*.supabase.co/**'

/**
 * Script d'injection de session — s'exécute dans le contexte BROWSER.
 * Reçoit les données de session via `addInitScript(fn, args)`.
 *
 * Stratégie : on injecte la session dans localStorage ET on monkey-patch
 * le `fetch` global pour intercepter les appels Supabase Auth avant que
 * le SDK initialise. Ainsi, `supabase.auth.getSession()` reçoit
 * directement notre session sans race condition.
 */
type SessionParams = {
  email: string
  userId: string
  orgId: string
  expiresAt: number
  storageKey: string
  isSuperAdmin: boolean
  orgName: string
  orgSlug: string
  selfServiceEnabled: boolean
}

/**
 * Injecte une session super-admin dans le navigateur.
 *
 * - `addInitScript` pose la session en localStorage ET patch `fetch` pour
 *   intercepter `supabase.auth.getSession()` avant l'init du store.
 * - `page.route` intercepte les appels réseau Supabase Auth cross-origin.
 * - `page.route` intercepte `/api/client/auth/me` et `/api/admin/me/super-status`.
 *
 * À appeler AVANT `page.goto(...)`.
 */
export async function seedSuperAdminAuth(page: Page): Promise<void> {
  const params: SessionParams = {
    email: SUPER_ADMIN_EMAIL,
    userId: FAKE_USER_ID,
    orgId: FAKE_ORG_ID,
    expiresAt: Math.floor(Date.now() / 1000) + 3600,
    storageKey: 'bassira_supabase_auth',
    isSuperAdmin: true,
    orgName: 'AI-Mpower Bassira',
    orgSlug: 'aimpower-bassira',
    selfServiceEnabled: true
  }

  await _injectAuthSession(page, params)
}

/**
 * Injecte une session utilisateur normal (non super-admin) dans le navigateur.
 *
 * À appeler AVANT `page.goto(...)`.
 */
export async function seedRegularUserAuth(page: Page): Promise<void> {
  const params: SessionParams = {
    email: REGULAR_USER_EMAIL,
    userId: FAKE_USER_ID,
    orgId: FAKE_ORG_ID,
    expiresAt: Math.floor(Date.now() / 1000) + 3600,
    storageKey: 'bassira_supabase_auth',
    isSuperAdmin: false,
    orgName: 'ACME Corp',
    orgSlug: 'acme-corp',
    selfServiceEnabled: false
  }

  await _injectAuthSession(page, params)
}

/**
 * Helper interne : injecte une session pour n'importe quel rôle.
 */
async function _injectAuthSession(page: Page, params: SessionParams): Promise<void> {
  // ── 1. addInitScript : exécuté dans le browser AVANT tout JS de l'app ──
  await page.addInitScript((p: SessionParams) => {
    // Construire un JWT fake (structurellement valide : 3 segments base64)
    // La signature est arbitraire — Supabase JS ne vérifie pas la crypto côté client.
    const now = Math.floor(Date.now() / 1000)
    const headerB64 = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).replace(/=/g, '')
    const payloadB64 = btoa(JSON.stringify({
      sub: p.userId,
      email: p.email,
      aud: 'authenticated',
      role: 'authenticated',
      exp: p.expiresAt,
      iat: now
    })).replace(/=/g, '')
    const fakeJwt = `${headerB64}.${payloadB64}.fakesig`

    const sessionObj = {
      access_token: fakeJwt,
      refresh_token: 'fakerefreshtoken',
      expires_in: 3600,
      expires_at: p.expiresAt,
      token_type: 'bearer',
      user: {
        id: p.userId,
        aud: 'authenticated',
        role: 'authenticated',
        email: p.email,
        email_confirmed_at: '2026-01-01T00:00:00.000Z',
        created_at: '2026-01-01T00:00:00.000Z',
        updated_at: '2026-01-01T00:00:00.000Z'
      }
    }

    // Écrire dans localStorage (lu par Supabase JS au démarrage)
    try {
      localStorage.setItem(p.storageKey, JSON.stringify(sessionObj))
    } catch (_e) {
      // Contexte sandboxé
    }

    // Monkey-patch fetch global pour intercepter les appels Supabase Auth
    // AVANT que le SDK initialise. Cela résout la race condition entre
    // init() et le guard router.
    const _originalFetch = window.fetch.bind(window)
    window.fetch = function patchedFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
      const url = typeof input === 'string' ? input : (input instanceof URL ? input.href : (input as Request).url)

      // Intercepter les appels Supabase Auth (/auth/v1/...)
      if (url.includes('.supabase.co/auth/v1') || url.includes('/auth/v1/')) {
        // Ne pas intercepter OAuth / magic link / callback (navigation réelle)
        if (url.includes('/callback') || url.includes('/authorize') || url.includes('/otp')) {
          return _originalFetch(input, init)
        }
        // Retourner la session fake pour getSession / refreshToken
        return Promise.resolve(new Response(JSON.stringify(sessionObj), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        }))
      }

      // Intercepter /api/client/auth/me
      if (url.includes('/api/client/auth/me')) {
        const meResponse = {
          user_id: p.userId,
          email: p.email,
          orgs: [{
            id: p.orgId,
            name: p.orgName,
            slug: p.orgSlug,
            role: 'owner',
            self_service_enabled: p.selfServiceEnabled
          }]
        }
        return Promise.resolve(new Response(JSON.stringify(meResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        }))
      }

      // Intercepter /api/admin/me/super-status
      if (url.includes('/api/admin/me/super-status')) {
        const superStatus = { is_super_admin: p.isSuperAdmin, email: p.email }
        return Promise.resolve(new Response(JSON.stringify(superStatus), {
          status: p.isSuperAdmin ? 200 : 403,
          headers: { 'Content-Type': 'application/json' }
        }))
      }

      return _originalFetch(input, init)
    }
  }, params)

  // ── 2. page.route : backup pour les appels qui passent malgré le patch ──
  // (Playwright intercepte aussi côté réseau en cas de bypass du patch)
  await page.route(SUPABASE_URL_PATTERN, async (route) => {
    const url = route.request().url()
    if (url.includes('/callback') || url.includes('/authorize') || url.includes('/otp')) {
      await route.continue()
      return
    }
    // Construire la session côté Node.js pour la réponse réseau
    const now = Math.floor(Date.now() / 1000)
    const headerB64 = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url')
    const payloadB64 = Buffer.from(JSON.stringify({
      sub: params.userId,
      email: params.email,
      aud: 'authenticated',
      role: 'authenticated',
      exp: params.expiresAt,
      iat: now
    })).toString('base64url')
    const sessionBody = {
      access_token: `${headerB64}.${payloadB64}.fakesig`,
      refresh_token: 'fakerefreshtoken',
      expires_in: 3600,
      expires_at: params.expiresAt,
      token_type: 'bearer',
      user: {
        id: params.userId,
        aud: 'authenticated',
        role: 'authenticated',
        email: params.email,
        email_confirmed_at: '2026-01-01T00:00:00.000Z',
        created_at: '2026-01-01T00:00:00.000Z',
        updated_at: '2026-01-01T00:00:00.000Z'
      }
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(sessionBody)
    })
  })

  // ── 3. Mock API backend /api/client/auth/me ──
  await page.route('**/api/client/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: params.userId,
        email: params.email,
        orgs: [
          {
            id: params.orgId,
            name: params.orgName,
            slug: params.orgSlug,
            role: 'owner',
            self_service_enabled: params.selfServiceEnabled
          }
        ]
      })
    })
  })

  // ── 4. Mock /api/admin/me/super-status ──
  await page.route('**/api/admin/me/super-status', async (route) => {
    await route.fulfill({
      status: params.isSuperAdmin ? 200 : 403,
      contentType: 'application/json',
      body: JSON.stringify({
        is_super_admin: params.isSuperAdmin,
        email: params.email
      })
    })
  })
}

/**
 * Efface la session du localStorage (utile en afterEach si besoin).
 * En pratique chaque test ouvre un contexte frais — ce helper est optionnel.
 */
export async function clearAuth(page: Page): Promise<void> {
  await page.evaluate(() => {
    try {
      localStorage.removeItem('bassira_supabase_auth')
    } catch (_e) {
      // Ignore
    }
  })
}

/**
 * Navigue vers une route protégée APRÈS que le store auth soit stable.
 *
 * Stratégie 2 phases :
 *   1. goto('/') → attendez le signal DOM indiquant que l'auth est prête
 *   2. Cliquez sur le lien dans le header (Vue Router push) ou naviguez
 *      directement si le lien n'est pas disponible.
 *
 * À utiliser après `seedSuperAdminAuth(page)` ou `seedRegularUserAuth(page)`.
 *
 * @param page        - Page Playwright
 * @param targetPath  - Chemin cible (ex: '/console', '/admin/quotes')
 */
export async function navigateAuthenticated(
  page: Page,
  targetPath: string
): Promise<void> {
  // Phase 1 : charger une page publique
  await page.goto('/?lang=fr', { waitUntil: 'domcontentloaded' })

  // Phase 2 : attendre que l'auth soit stable (signal DOM)
  await page.waitForSelector('a[href="/client/dashboard"]', { timeout: 15_000 })

  // Phase 3 : fermer les modales d'onboarding si présentes
  const onbDialog = page.locator('[role="dialog"].onb-root, .onb-root')
  if (await onbDialog.isVisible().catch(() => false)) {
    const passerBtn = onbDialog.getByText('Passer').first()
    if (await passerBtn.isVisible().catch(() => false)) {
      await passerBtn.click({ force: true })
    } else {
      await page.keyboard.press('Escape')
    }
    await onbDialog.waitFor({ state: 'hidden', timeout: 3_000 }).catch(() => undefined)
  }

  // Phase 4 : utiliser directement l'instance Vue Router déjà montée.
  // Les clics dans le menu super-admin replié introduisent une course sous
  // forte concurrence Playwright entre l'ouverture du menu et la navigation.
  await page.evaluate((path: string) => {
    const appEl = document.querySelector('#app')
    const vueApp = (appEl as Element & { __vue_app__?: { config: { globalProperties: { $router?: { push: (target: string) => unknown } } } } })?.__vue_app__
    const router = vueApp?.config.globalProperties.$router
    if (!router) throw new Error('Vue Router indisponible')
    return router.push(`${path}${path.includes('?') ? '&' : '?'}lang=fr`)
  }, targetPath)
}
