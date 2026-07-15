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
