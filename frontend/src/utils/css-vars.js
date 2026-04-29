/**
 * css-vars.js — lecture runtime des design tokens CSS pour configs JS
 *
 * Pourquoi (US-052) :
 *   US-016 a migré 1052 → 257 hex hardcodés en CSS, mais ne pouvait pas
 *   toucher les hex présents en STRINGS JS (template literals, configs D3,
 *   palettes runtime utilisées par d3.scaleOrdinal, canvas fillStyle, etc.).
 *   Ce helper centralise la lecture des variables `--ms-chart-*` et
 *   `--ms-status-*` du DOM via `getComputedStyle(document.documentElement)`,
 *   évitant la duplication des hex et débloquant le futur dark mode (US-027).
 *
 * Pattern d'usage :
 * @example
 *   import { readChartPalette } from '@/utils/css-vars'
 *
 *   const colors = readChartPalette()
 *   const palette = [colors.chart1, colors.chart2, colors.chart3]
 *   ctx.fillStyle = colors.chart3 // '#0A0A0A' (ou la valeur dark mode future)
 *
 * Mémoization :
 *   La palette est lue une seule fois au premier appel et mise en cache. En
 *   dark mode futur, appeler `clearChartPaletteCache()` après bascule du
 *   thème pour forcer une relecture.
 */

// Fallback palette : valeurs identiques à design-tokens.css au moment d'US-052.
// Utilisée uniquement si :
//   - SSR / pas de DOM disponible,
//   - une variable CSS est absente (ex. token retiré par erreur).
// Les couleurs reflètent exactement --ms-chart-1..10 et --ms-status-* du root.
const FALLBACK = Object.freeze({
  chart1: '#FF6B1A',
  chart2: '#43C165',
  chart3: '#0A0A0A',
  chart4: '#FFB347',
  chart5: '#FF4444',
  chart6: '#FF8C42',
  chart7: '#2D9B5E',
  chart8: '#D45B1A',
  chart9: '#7A7A7A',
  chart10: '#B8522E',
  success: '#22c55e',
  warning: '#f59e0b',
  danger: '#ef4444',
  info: '#3b82f6',
  pink: '#ec4899',
  violet: '#7C3AED',
})

// Mapping clé palette → nom de variable CSS
const VAR_MAP = Object.freeze({
  chart1: '--ms-chart-1',
  chart2: '--ms-chart-2',
  chart3: '--ms-chart-3',
  chart4: '--ms-chart-4',
  chart5: '--ms-chart-5',
  chart6: '--ms-chart-6',
  chart7: '--ms-chart-7',
  chart8: '--ms-chart-8',
  chart9: '--ms-chart-9',
  chart10: '--ms-chart-10',
  success: '--ms-status-success',
  warning: '--ms-status-warning',
  danger: '--ms-status-danger',
  info: '--ms-status-info',
  pink: '--ms-status-pink',
  violet: '--ms-status-violet',
})

/** @type {ChartPalette | null} */
let _cache = null

/**
 * @typedef {Object} ChartPalette
 * @property {string} chart1   - Palette catégorielle 1 (orange)
 * @property {string} chart2   - Palette catégorielle 2 (vert)
 * @property {string} chart3   - Palette catégorielle 3 (encre)
 * @property {string} chart4   - Palette catégorielle 4 (peach)
 * @property {string} chart5   - Palette catégorielle 5 (rouge)
 * @property {string} chart6   - Palette catégorielle 6 (orange clair)
 * @property {string} chart7   - Palette catégorielle 7 (vert foncé)
 * @property {string} chart8   - Palette catégorielle 8 (orange brûlé)
 * @property {string} chart9   - Palette catégorielle 9 (gris neutre)
 * @property {string} chart10  - Palette catégorielle 10 (terracotta)
 * @property {string} success  - Statut succès
 * @property {string} warning  - Statut avertissement
 * @property {string} danger   - Statut erreur
 * @property {string} info     - Statut info
 * @property {string} pink     - Accent rose (segments démographiques)
 * @property {string} violet   - Accent violet (insights)
 */

/**
 * Lit la palette de charts depuis les design tokens CSS du DOM.
 *
 * Cache le résultat au premier appel. La lecture utilise
 * `getComputedStyle(document.documentElement)` qui résout les `var()`
 * cascadés (ex. `[data-theme="dark"]` futur).
 *
 * Si une variable est absente (token retiré, environnement sans DOM),
 * la valeur du fallback est utilisée — defensive, jamais d'`undefined`.
 *
 * @returns {ChartPalette} palette figée (Object.freeze)
 */
export function readChartPalette() {
  if (_cache) return _cache

  // SSR / Node : pas de DOM, on retourne directement le fallback
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    _cache = FALLBACK
    return _cache
  }

  const styles = getComputedStyle(document.documentElement)
  /** @type {Record<string, string>} */
  const palette = {}

  for (const [key, varName] of Object.entries(VAR_MAP)) {
    const raw = styles.getPropertyValue(varName)
    const trimmed = raw ? raw.trim() : ''
    palette[key] = trimmed || FALLBACK[key]
  }

  _cache = Object.freeze(palette)
  return _cache
}

/**
 * Vide le cache de la palette pour forcer une relecture au prochain
 * `readChartPalette()`. À appeler après une bascule de thème (ex. dark
 * mode US-027) pour que les nouvelles valeurs de variables CSS soient
 * propagées dans les charts D3 / canvas.
 *
 * @returns {void}
 */
export function clearChartPaletteCache() {
  _cache = null
}
