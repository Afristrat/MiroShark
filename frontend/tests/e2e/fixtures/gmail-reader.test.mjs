import { test } from 'node:test'
import assert from 'node:assert/strict'
import { extractMagicLink } from './gmail-reader.ts'

test('extractMagicLink trouve le lien Supabase verify dans le HTML', () => {
  const html = `
    <a href="https://fvfifgstytvxssffvsbs.supabase.co/auth/v1/verify?token=abc&type=magiclink&redirect_to=https://bassira.ma/client/dashboard" style="color:#a13f0f">
      Accéder à mon espace
    </a>
    <a href="https://bassira.ma">bassira.ma</a>
  `
  const link = extractMagicLink(html)
  assert.equal(
    link,
    'https://fvfifgstytvxssffvsbs.supabase.co/auth/v1/verify?token=abc&type=magiclink&redirect_to=https://bassira.ma/client/dashboard'
  )
})

test('extractMagicLink retourne null si aucun lien Supabase verify', () => {
  const html = '<a href="https://bassira.ma">bassira.ma</a>'
  assert.equal(extractMagicLink(html), null)
})

test('extractMagicLink trouve le lien sur une instance Supabase self-hébergée (domaine custom)', () => {
  const html =
    '<a href="https://db-miroshark.ai-mpower.com/auth/v1/verify?token=xyz&type=magiclink&redirect_to=https://bassira.ma">Accéder</a>'
  assert.equal(
    extractMagicLink(html),
    'https://db-miroshark.ai-mpower.com/auth/v1/verify?token=xyz&type=magiclink&redirect_to=https://bassira.ma'
  )
})
