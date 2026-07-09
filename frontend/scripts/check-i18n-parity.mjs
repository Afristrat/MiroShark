#!/usr/bin/env node
/**
 * Vérifie la parité stricte des clés entre les 3 locales (fr/en/ar) —
 * pattern US-201 (script ad hoc, jamais conservé dans le repo).
 * Réintroduit en US-IQ-01 comme script permanent : zéro clé manquante
 * dans une locale par rapport à fr.json (pivot), zéro clé en trop.
 *
 * Usage : node scripts/check-i18n-parity.mjs
 * Exit code : 0 si parité stricte, 1 sinon (liste les diffs sur stderr).
 */

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const LOCALES_DIR = join(__dirname, '..', 'src', 'locales')
const PIVOT = 'fr'
const LOCALES = ['fr', 'en', 'ar']

function loadLocale(code) {
  const raw = readFileSync(join(LOCALES_DIR, `${code}.json`), 'utf-8')
  return JSON.parse(raw)
}

/** Aplati un objet imbriqué en set de chemins pointés (ex: "quote.temps1.a1.label"). */
function flattenKeys(obj, prefix = '') {
  const keys = new Set()
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k
    if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
      for (const nested of flattenKeys(v, path)) keys.add(nested)
    } else {
      keys.add(path)
    }
  }
  return keys
}

function main() {
  const trees = Object.fromEntries(LOCALES.map((l) => [l, loadLocale(l)]))
  const keySets = Object.fromEntries(
    LOCALES.map((l) => [l, flattenKeys(trees[l])]),
  )

  const pivotKeys = keySets[PIVOT]
  let hasDiff = false

  for (const locale of LOCALES) {
    if (locale === PIVOT) continue
    const localeKeys = keySets[locale]

    const missing = [...pivotKeys].filter((k) => !localeKeys.has(k)).sort()
    const extra = [...localeKeys].filter((k) => !pivotKeys.has(k)).sort()

    if (missing.length > 0) {
      hasDiff = true
      console.error(`\n[${locale}] ${missing.length} clé(s) MANQUANTE(S) (présentes dans ${PIVOT}) :`)
      for (const k of missing) console.error(`  - ${k}`)
    }
    if (extra.length > 0) {
      hasDiff = true
      console.error(`\n[${locale}] ${extra.length} clé(s) EN TROP (absentes de ${PIVOT}) :`)
      for (const k of extra) console.error(`  + ${k}`)
    }
  }

  if (hasDiff) {
    console.error('\ni18n parity: ÉCHEC — voir diffs ci-dessus.')
    process.exit(1)
  }

  console.log(
    `i18n parity: OK — ${pivotKeys.size} clés, parité stricte fr/en/ar.`,
  )
}

main()
