# Brique E2E "round-trip email" (magic link) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un test Playwright qui reçoit un vrai email Resend, extrait le magic link, clique dessus, et vérifie l'atterrissage sur `/client/dashboard` — combler l'alerte de clôture du Lot B compte-client.

**Architecture:** Une fixture `gmail-reader.ts` (Google API `googleapis`, compte de service DWD déjà opérationnel, impersonation `a.mansouri@afriquestrategie.com`) lit une vraie boîte Gmail. Un spec E2E orchestre : création de devis réelle → login admin réel → transitions de statut réelles jusqu'à `paid` → attente de l'email réel → clic sur le lien → assertion dashboard. Aucun code backend modifié.

**Tech Stack:** TypeScript, Playwright (`@playwright/test` déjà présent), `googleapis` (nouvelle devDependency), Node 22 (`node:test` intégré pour le seul check unitaire nécessaire), GAM7 CLI (spike de validation uniquement, pas dans le code final).

## Global Constraints

- Spec source de vérité : `docs/superpowers/specs/2026-07-15-e2e-email-roundtrip-design.md`.
- Aucun nouveau vendor payant ; réutiliser le compte de service DWD `gam-project-ip0f8@gam-project-ip0f8.iam.gserviceaccount.com` (clé : `C:\Users\amans\.gam\oauth2service.json`).
- Seul ajout de dépendance autorisé : `googleapis` (devDependency frontend).
- Tests exécutés contre la prod réelle `https://prospectives.ai-mpower.com` (SOP-011) — jamais de `npm run dev` local.
- Aucun secret affiché en clair : toute commande utilisant `BASSIRA_ADMIN_PASSWORD` passe par `invoke-secret.ps1 -Keys ... -Command '...'` ; dans le code, uniquement `process.env.BASSIRA_ADMIN_PASSWORD`, jamais loggé.
- Correction obligatoire de `docs/05-integrations.md` (RESEND_API_KEY marquée à tort bloquante) dans ce chantier.
- Gates de fin de chantier (Règle N°3, zéro dette) : pytest backend complet (avec le fix du test flaky `test_md_hash_stable_with_deterministic_enricher` déjà identifié séparément — ne pas le refaire ici, hors scope de ce plan), `npm run build`, suite E2E complète incluant le nouveau spec, tous verts avant de clore.

---

### Task 1: Spike — valider l'adressage Gmail `+tag` en conditions réelles

**Files:** aucun fichier de code — validation système pure, documentée inline dans ce plan.

**Interfaces:** Produit une décision go/no-go qui conditionne la confiance dans le `toAddress` utilisé par `gmail-reader.ts` (Task 2). Ne bloque pas Task 2 (le code est écrit de la même façon dans les deux cas — voir note de repli), mais un échec doit être remonté à Amine avant de continuer.

- [ ] **Step 1: Envoyer un email de sonde réel à l'adresse taguée via l'API Resend**

```bash
TAG="e2e-spike-$(date +%s)"
& 'C:\Users\amans\.claude\scripts\invoke-secret.ps1' -Keys RESEND_API_KEY,RESEND_FROM_EMAIL -CommandB64 $(printf '%s' "curl -s -X POST https://api.resend.com/emails -H \"Authorization: Bearer \$env:RESEND_API_KEY\" -H \"Content-Type: application/json\" -d '{\"from\":\"'\$env:RESEND_FROM_EMAIL'\",\"to\":\"a.mansouri+${TAG}@afriquestrategie.com\",\"subject\":\"E2E spike ${TAG}\",\"html\":\"<p>probe</p>\"}'" | base64 | tr -d '\n')
echo "TAG=$TAG"
```

Note : adapter la syntaxe d'invocation du broker à l'environnement d'exécution réel (PowerShell natif si disponible — voir CLAUDE.md global, section coffre de secrets, pour la forme exacte `-CommandB64` à la frontière Bash→PowerShell). Le point important n'est pas la syntaxe exacte mais qu'aucune des deux clés ne soit jamais imprimée en clair.

- [ ] **Step 2: Attendre ~15s, puis vérifier la réception via GAM (lecture seule)**

```bash
sleep 15
"/c/GAM7/gam.exe" user a.mansouri@afriquestrategie.com show messages query "to:a.mansouri+${TAG}@afriquestrategie.com" maxtoshow 3
```

**Décision :**
- Si un message apparaît avec le sujet `E2E spike ${TAG}` → **GO**. `gmail-reader.ts` (Task 2) utilisera `to:<toAddress>` (adresse complète taguée) comme requête de recherche, sans modification supplémentaire.
- Si aucun message n'apparaît en filtrant par l'adresse taguée complète → **repli** : `gmail-reader.ts` doit chercher par `subject:<subjectContains>` uniquement (le sujet contient déjà l'UUID unique du run, cf. Task 4 — garantit l'unicité sans dépendre du `+tag`), et le spec (Task 4) devra alors envoyer le devis avec l'adresse de base `a.mansouri@afriquestrategie.com` (accepter que ce point casse la garantie de non-idempotence — dans ce cas, **arrêter et remonter à Amine** avant Task 4 : il faudra alors un mécanisme de nettoyage Supabase entre les runs, hors scope actuel).

**Ne pas passer à Task 2 sans avoir exécuté ce spike et noté le résultat (GO ou repli) dans le commit de Task 2.**

**Résultat réel (exécuté 2026-07-15) : GO.** Flux complet réel exécuté (création devis
`q_6e401f45` → login admin → 3 transitions → paid) avec adresse
`a.mansouri+e2e-spike-1784077418@afriquestrategie.com`. Vérifié via
`gam.exe user a.mansouri@afriquestrategie.com show messages query "to:a.mansouri+e2e-spike-...@afriquestrategie.com"`
→ 2 messages reçus, `Delivered-To` préserve l'adresse taguée complète, sujet
« Bassira — Votre espace client est prêt » présent. `gmail-reader.ts` (Task 2) utilise donc
`to:<toAddress>` avec l'adresse complète taguée, sans repli nécessaire.

**Découverte annexe (corrigée dans Task 4 ci-dessous)** : `page.goto('/admin/quotes')` en
navigation directe (reload complet) fait courir une race entre la réhydratation de session
Supabase et le guard router, qui rebondit sur `/login` — la navigation doit passer par le menu
SPA (`.app-header__admin-toggle` puis `a[href="/admin/quotes"]`), jamais par un `goto` direct
vers une route protégée après un login fraîchement établi.

---

### Task 2: `gmail-reader.ts` — lecture Gmail via compte de service DWD

**Files:**
- Create: `frontend/tests/e2e/fixtures/gmail-reader.ts`
- Test: `frontend/tests/e2e/fixtures/gmail-reader.test.mjs` (check minimal `node:test`, fonction pure uniquement — pas de véritable appel réseau)
- Modify: `frontend/package.json` (ajout devDependency `googleapis`)

**Interfaces:**
- Consumes: rien des tâches précédentes (fixture autonome).
- Produces (consommé par Task 4) :
  - `extractMagicLink(html: string): string | null` — fonction pure, exportée.
  - `waitForEmail(opts: { toAddress: string; subjectContains: string; timeoutMs?: number }): Promise<{ id: string; html: string }>` — lève une erreur explicite si timeout.
  - `trashMessage(id: string): Promise<void>` — best-effort, ne lève jamais (log warning en cas d'échec).

- [ ] **Step 1: Ajouter la dépendance**

```bash
cd frontend
npm install --save-dev googleapis
```

- [ ] **Step 2: Écrire le check unitaire de la fonction pure (avant l'implémentation)**

```javascript
// frontend/tests/e2e/fixtures/gmail-reader.test.mjs
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { extractMagicLink } from './gmail-reader.ts'

test('extractMagicLink trouve le lien Supabase verify dans le HTML', () => {
  const html = `
    <a href="https://fvfifgstytvxssffvsbs.supabase.co/auth/v1/verify?token=abc&type=magiclink&redirect_to=https://prospectives.ai-mpower.com/client/dashboard" style="color:#a13f0f">
      Accéder à mon espace
    </a>
    <a href="https://bassira.ma">bassira.ma</a>
  `
  const link = extractMagicLink(html)
  assert.equal(
    link,
    'https://fvfifgstytvxssffvsbs.supabase.co/auth/v1/verify?token=abc&type=magiclink&redirect_to=https://prospectives.ai-mpower.com/client/dashboard'
  )
})

test('extractMagicLink retourne null si aucun lien Supabase verify', () => {
  const html = '<a href="https://bassira.ma">bassira.ma</a>'
  assert.equal(extractMagicLink(html), null)
})
```

- [ ] **Step 3: Lancer le check pour vérifier qu'il échoue (le fichier source n'existe pas encore)**

Run: `node --experimental-strip-types --test frontend/tests/e2e/fixtures/gmail-reader.test.mjs`
Expected: FAIL — `Cannot find module './gmail-reader.ts'`

- [ ] **Step 4: Écrire `gmail-reader.ts`**

```typescript
// frontend/tests/e2e/fixtures/gmail-reader.ts
/**
 * Lecture d'une boîte Gmail Workspace via le compte de service à
 * délégation domaine (DWD) déjà opérationnel pour GAM7 — impersonation
 * de a.mansouri@afriquestrategie.com. Aucun nouveau vendor, aucune
 * nouvelle demande d'accès Google (scope Gmail déjà autorisé, cf. spec
 * docs/superpowers/specs/2026-07-15-e2e-email-roundtrip-design.md).
 */
import { google } from 'googleapis'
import { readFileSync } from 'node:fs'

const SERVICE_ACCOUNT_KEY_PATH =
  process.env.GOOGLE_SERVICE_ACCOUNT_KEY_PATH || 'C:\\Users\\amans\\.gam\\oauth2service.json'
const IMPERSONATED_USER = 'a.mansouri@afriquestrategie.com'
const SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

const MAGIC_LINK_RE = /href="(https:\/\/[^"]*supabase\.co\/auth\/v1\/verify[^"]*)"/

export function extractMagicLink(html: string): string | null {
  const match = html.match(MAGIC_LINK_RE)
  return match ? match[1] : null
}

function getGmailClient() {
  const key = JSON.parse(readFileSync(SERVICE_ACCOUNT_KEY_PATH, 'utf-8'))
  const auth = new google.auth.JWT({
    email: key.client_email,
    key: key.private_key,
    scopes: SCOPES,
    subject: IMPERSONATED_USER,
  })
  return google.gmail({ version: 'v1', auth })
}

function decodeBody(payload: any): string {
  if (payload.body?.data) {
    return Buffer.from(payload.body.data, 'base64url').toString('utf-8')
  }
  for (const part of payload.parts || []) {
    if (part.mimeType === 'text/html' && part.body?.data) {
      return Buffer.from(part.body.data, 'base64url').toString('utf-8')
    }
  }
  for (const part of payload.parts || []) {
    const nested = decodeBody(part)
    if (nested) return nested
  }
  return ''
}

export async function waitForEmail(opts: {
  toAddress: string
  subjectContains: string
  timeoutMs?: number
}): Promise<{ id: string; html: string }> {
  const timeoutMs = opts.timeoutMs ?? 30_000
  const pollIntervalMs = 2_000
  const gmail = getGmailClient()
  const deadline = Date.now() + timeoutMs

  while (Date.now() < deadline) {
    const list = await gmail.users.messages.list({
      userId: 'me',
      q: `to:${opts.toAddress} newer_than:1h`,
      maxResults: 5,
    })
    for (const msg of list.data.messages || []) {
      const full = await gmail.users.messages.get({
        userId: 'me',
        id: msg.id!,
        format: 'full',
      })
      const subjectHeader = full.data.payload?.headers?.find(
        (h) => h.name?.toLowerCase() === 'subject'
      )
      const toHeader = full.data.payload?.headers?.find((h) => h.name?.toLowerCase() === 'to')
      if (
        subjectHeader?.value?.includes(opts.subjectContains) &&
        toHeader?.value?.includes(opts.toAddress)
      ) {
        const html = decodeBody(full.data.payload)
        return { id: msg.id!, html }
      }
    }
    await new Promise((resolve) => setTimeout(resolve, pollIntervalMs))
  }
  throw new Error(
    `gmail-reader: email de compte client non reçu dans le délai imparti (${timeoutMs}ms, ` +
      `to=${opts.toAddress}, subject contient "${opts.subjectContains}")`
  )
}

export async function trashMessage(id: string): Promise<void> {
  try {
    const gmail = getGmailClient()
    await gmail.users.messages.trash({ userId: 'me', id })
  } catch (err) {
    console.warn(`gmail-reader: échec trashMessage(${id}), ignoré (best-effort) —`, err)
  }
}
```

- [ ] **Step 5: Relancer le check unitaire pour vérifier qu'il passe**

Run: `node --experimental-strip-types --test frontend/tests/e2e/fixtures/gmail-reader.test.mjs`
Expected: `# pass 2`, `# fail 0`

- [ ] **Step 6: Commit**

```bash
cd frontend
git add package.json package-lock.json tests/e2e/fixtures/gmail-reader.ts tests/e2e/fixtures/gmail-reader.test.mjs
git commit -m "feat(compte-client): fixture gmail-reader (DWD) pour E2E round-trip email"
```

---

### Task 3: Corriger `docs/05-integrations.md` (RESEND_API_KEY périmé)

**Files:**
- Modify: `docs/05-integrations.md:13`

**Interfaces:** aucune — correction documentaire isolée.

- [ ] **Step 1: Lire la ligne actuelle**

Run: `grep -n "Resend" docs/05-integrations.md`
Expected (état constaté avant fix) : `⚠️ JAMAIS configurée en prod (US-204, bloquant)`

- [ ] **Step 2: Corriger**

Remplacer dans `docs/05-integrations.md` ligne 13 la colonne "Config" :
- Avant : `` `RESEND_API_KEY` — ⚠️ **JAMAIS configurée en prod** (US-204, bloquant) ``
- Après : `` `RESEND_API_KEY` — configurée en prod (US-204, `passes=true` depuis 2026-07-09 ; vérifié présente sur le conteneur live 2026-07-15) ``

- [ ] **Step 3: Commit**

```bash
git add docs/05-integrations.md
git commit -m "docs: corrige RESEND_API_KEY périmée dans 05-integrations.md (US-204 déjà résolu)"
```

---

### Task 4: Spec E2E `client-account-email-roundtrip.spec.ts`

**Files:**
- Create: `frontend/tests/e2e/client-account-email-roundtrip.spec.ts`

**Interfaces:**
- Consumes: `extractMagicLink`, `waitForEmail`, `trashMessage` de `./fixtures/gmail-reader.ts` (Task 2).
- Produces: rien (spec terminal).

- [ ] **Step 1: Écrire le spec complet**

```typescript
// frontend/tests/e2e/client-account-email-roundtrip.spec.ts
import { test, expect, type Page } from '@playwright/test'
import { randomUUID } from 'node:crypto'
import { waitForEmail, extractMagicLink, trashMessage } from './fixtures/gmail-reader'

const ADMIN_EMAIL = 'medamine.mansouriidrissi@gmail.com'

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

  const email = await waitForEmail({
    toAddress: customerEmail,
    subjectContains: 'Bassira',
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
```

- [ ] **Step 2: Lancer le spec seul, avec le mot de passe injecté via le broker**

```bash
cd frontend
& 'C:\Users\amans\.claude\scripts\invoke-secret.ps1' -Keys BASSIRA_ADMIN_PASSWORD -Command 'npx playwright test tests/e2e/client-account-email-roundtrip.spec.ts --reporter=list'
```

Expected: `1 passed`. Si échec au niveau `waitForEmail` (timeout), vérifier d'abord le résultat du spike (Task 1) — c'est le point de défaillance le plus probable si l'adressage `+tag` ne s'est pas comporté comme prévu en prod.

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/client-account-email-roundtrip.spec.ts
git commit -m "test(compte-client): E2E round-trip email réel (devis payé → magic link → dashboard)"
```

---

### Task 5: Gates finaux + passation

**Files:** aucun nouveau fichier — vérification only, puis mise à jour `PASSATION.md`.

**Interfaces:** aucune.

- [ ] **Step 1: Suite E2E complète contre la prod**

```bash
cd frontend
& 'C:\Users\amans\.claude\scripts\invoke-secret.ps1' -Keys BASSIRA_ADMIN_PASSWORD -Command 'npx playwright test --reporter=list'
```

Expected: tous les specs verts, y compris `client-account-email-roundtrip.spec.ts`.

- [ ] **Step 2: Build front**

Run: `cd frontend && npm run build`
Expected: exit 0.

- [ ] **Step 3: Mettre à jour `PASSATION.md`**

Nouvelle entrée en tête de fichier documentant : brique E2E email construite et vérifiée (preuve système, pas mémoire — coller la sortie réelle du run Task 5 Step 1), `docs/05-integrations.md` corrigé, alerte de clôture du Lot B définitivement refermée. Remplacer/purger l'entrée précédente du 2026-07-14 ~23h00 si tous ses points restent valides (sinon les reporter).

- [ ] **Step 4: Commit de la passation**

```bash
git add PASSATION.md
git commit -m "docs(passation): brique E2E round-trip email close l'alerte Lot B"
```

---

## Self-Review (fait pendant l'écriture de ce plan)

1. **Couverture spec** : architecture (Task 2), flux 1-7 du spec → Tasks 1 (spike), 4 Step 1 (création devis, login, transitions, email, clic, assertion), 2/4 (nettoyage trash). Gestion d'erreurs → `waitForEmail` lève une erreur explicite (pas de skip silencieux), conforme au spec. Risque `+tag` non validé → Task 1 dédiée, bloquante avant Task 4. `docs/05-integrations.md` → Task 3.
2. **Placeholders** : aucun "TBD"/"TODO" — toutes les étapes de code contiennent le code complet.
3. **Cohérence des types/signatures** : `waitForEmail(opts: {toAddress, subjectContains, timeoutMs?})` et `extractMagicLink(html): string | null` utilisés identiquement entre Task 2 (définition + test) et Task 4 (consommation). `trashMessage(id: string)` idem.
