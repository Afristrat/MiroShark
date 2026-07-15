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

// Domaine variable : instance Supabase self-hébergée (db-miroshark.ai-mpower.com)
// ou managée (*.supabase.co) — seul le chemin /auth/v1/verify est stable.
const MAGIC_LINK_RE = /href="(https:\/\/[^"]*\/auth\/v1\/verify[^"]*)"/

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
