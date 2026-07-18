<template>
  <div class="pm-panel">
    <!-- Header — matches .lb-header in InfluenceLeaderboard -->
    <div class="pm-header">
      <div class="pm-header-left">
        <img src="/pm.png" :alt="$t('charts.polymarket.logoAlt')" class="pm-logo" />
        <span class="pm-header-title">{{ $t('charts.polymarket.title') }}</span>
        <span v-if="live" class="pm-live-dot"><span class="pm-live-pulse"></span>{{ $t('charts.polymarket.live') }}</span>
      </div>
      <div v-if="selected" class="pm-header-actions">
        <button
          class="pm-export-btn"
          :disabled="exporting || !copySupported || !selected.points.length"
          :title="copySupported ? $t('charts.polymarket.copyChartTitle') : $t('charts.polymarket.copyUnsupportedTitle')"
          @click="copyChart"
        >
          {{ copiedFlash ? $t('embed.copied') : $t('embed.copy') }}
        </button>
        <button
          class="pm-export-btn"
          :disabled="exporting || !selected.points.length"
          :title="$t('charts.polymarket.downloadChartTitle')"
          @click="downloadChart"
        >
          {{ $t('charts.polymarket.download') }} ↓
        </button>
      </div>
    </div>

      <!-- Body: market list (left) + chart (right) -->
      <div class="pm-body">
        <!-- Market list -->
        <aside class="pm-market-list">
          <div v-if="marketsLoading && !markets.length" class="pm-empty">{{ $t('charts.common.loading') }}</div>
          <div v-else-if="marketsError" class="pm-empty pm-error">{{ $t('charts.polymarket.loadError') }}</div>
          <div v-else-if="!markets.length" class="pm-empty">
            <div class="pm-empty-title">{{ $t('charts.polymarket.noMarkets') }}</div>
            <div class="pm-empty-hint">{{ $t('charts.polymarket.subtitle') }}</div>
          </div>
          <button
            v-for="m in markets"
            :key="m.market_id"
            :data-testid="`market-${m.market_id}`"
            class="pm-market-row"
            :class="{ 'pm-market-row-active': selectedId === m.market_id }"
            @click="selectMarket(m.market_id)"
          >
            <div class="pm-market-q">{{ marketQuestion(m) }}</div>
            <div class="pm-market-meta">
              <span class="pm-market-price" :class="priceClass(m.price_yes)">
                {{ formatPct(m.price_yes) }}
              </span>
              <span class="pm-market-trades">{{ live ? $t('charts.polymarket.trades', { count: m.trade_count }) : $t('charts.polymarket.pricePoints', { count: m.point_count }) }}</span>
              <span v-if="m.resolved" class="pm-market-resolved">{{ outcomeLabel(m.winning_outcome) }}</span>
            </div>
          </button>
        </aside>

        <!-- Chart -->
        <section class="pm-chart-section">
          <div v-if="selectedError" class="pm-empty pm-error">{{ $t('charts.polymarket.loadPriceError') }}</div>
          <div v-else-if="!selected" class="pm-placeholder">
            <div class="pm-placeholder-icon">◎</div>
            <div class="pm-placeholder-text">{{ $t('charts.polymarket.selectQuestion') }}</div>
          </div>
          <template v-else>
            <!-- Question + price header -->
            <div class="pm-chart-header">
              <div class="pm-chart-q">{{ marketQuestion(selected.market) }}</div>
              <div class="pm-chart-price-row">
                <div class="pm-chart-price" :class="priceClass(latestPrice)">
                  {{ formatPct(latestPrice) }}
                  <span v-if="latestPrice !== null" class="pm-chart-outcome-label">{{ $t('charts.polymarket.chance', { outcome: outcomeLabel(selected.market.outcome_a || 'YES') }) }}</span>
                </div>
                <div v-if="priceDelta !== null" class="pm-chart-delta" :class="deltaClass(priceDelta)">
                  {{ priceDelta >= 0 ? '▲' : '▼' }} {{ formatPct(Math.abs(priceDelta)) }}
                </div>
              </div>
              <div class="pm-chart-stats" data-testid="chart-stats">
                <template v-if="live">
                  <span class="pm-stat"><span class="pm-stat-k">{{ $t('charts.polymarket.tradesLabel') }}</span><span class="pm-stat-v">{{ Math.max(selected.points.length - 1, 0) }}</span></span>
                  <span class="pm-stat"><span class="pm-stat-k">{{ $t('charts.polymarket.volume') }}</span><span class="pm-stat-v">{{ tradeVolume.toFixed(1) }}</span></span>
                  <span class="pm-stat"><span class="pm-stat-k">{{ $t('charts.polymarket.outcomes') }}</span><span class="pm-stat-v">{{ outcomeLabel(selected.market.outcome_a || 'YES') }}/{{ outcomeLabel(selected.market.outcome_b || 'NO') }}</span></span>
                </template>
                <span v-else class="pm-stat"><span class="pm-stat-k">{{ $t('charts.polymarket.pricePointsLabel') }}</span><span class="pm-stat-v">{{ selected.points.length }}</span></span>
                <span v-if="selected.market.resolved" class="pm-stat pm-stat-resolved">{{ $t('charts.polymarket.adjudicated', { outcome: outcomeLabel(selected.market.winning_outcome) }) }}</span>
              </div>
            </div>

            <div v-if="!selected.points.length" class="pm-no-series" data-testid="no-price-series">{{ $t('charts.polymarket.noPriceSeries') }}</div>

            <div v-if="selected.resolution" class="pm-resolution" data-testid="resolution-details">
              <template v-if="selected.market.resolved">
                <span class="pm-resolution-item" data-testid="adjudication-outcome">{{ $t('charts.polymarket.issue', { outcome: outcomeLabel(selected.market.winning_outcome) }) }}</span>
                <span v-if="selected.resolution.resolved_at" class="pm-resolution-item" data-testid="adjudication-date">{{ $t('charts.polymarket.closedAt', { date: formatDate(selected.resolution.resolved_at) }) }}</span>
              </template>
              <span v-else class="pm-resolution-item" data-testid="unresolved-status">{{ $t('charts.polymarket.notFinalized') }}</span>
              <p v-if="selected.resolution.justification" class="pm-resolution-justification" data-testid="adjudication-justification">{{ selected.resolution.justification }}</p>
              <span v-if="selected.resolution.confidence !== null && selected.resolution.confidence !== undefined" class="pm-resolution-item" data-testid="convergence-score">{{ $t('charts.polymarket.convergenceScore', { score: formatPct(selected.resolution.confidence) }) }}</span>
              <ul v-if="selected.resolution.evidence?.length" class="pm-evidence" data-testid="adjudication-evidence">
                <li v-for="(item, index) in selected.resolution.evidence" :key="`${item.ref}-${index}`">{{ evidenceLabel(item) }}</li>
              </ul>
            </div>

            <div v-if="!live && durableEnvelope.final_wealth.length" class="pm-final-wealth" data-testid="final-wealth">
              <div class="pm-final-wealth-title">{{ $t('charts.polymarket.finalWealth') }}</div>
              <ul>
                <li v-for="entry in durableEnvelope.final_wealth" :key="entry.user_id">
                  <span>{{ $t('charts.polymarket.participant', { id: entry.user_id }) }}</span>
                  <strong>{{ formatWealth(entry.wealth) }}</strong>
                </li>
              </ul>
            </div>

            <!-- SVG chart -->
            <div class="pm-chart-wrap">
              <svg
                ref="chartSvg"
                :viewBox="`0 0 ${W} ${H}`"
                preserveAspectRatio="none"
                class="pm-chart-svg"
                xmlns="http://www.w3.org/2000/svg"
                @mousemove="handleHover"
                @mouseleave="hoverPoint = null"
              >
                <defs>
                  <linearGradient :id="gradId" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" :stop-color="lineColor" stop-opacity="0.35" />
                    <stop offset="100%" :stop-color="lineColor" stop-opacity="0" />
                  </linearGradient>
                </defs>

                <!-- Grid lines at 0/25/50/75/100 — WI: --wi-outline-variant -->
                <g v-for="pct in [0, 25, 50, 75, 100]" :key="pct">
                  <line
                    :x1="ML" :y1="yScale(pct / 100)"
                    :x2="W - MR" :y2="yScale(pct / 100)"
                    :stroke="gridStroke" stroke-width="1"
                    :stroke-dasharray="pct === 50 ? '' : '2,3'"
                  />
                  <text
                    :x="W - MR + 8" :y="yScale(pct / 100) + 4"
                    :fill="axisLabelFill" font-size="10"
                    font-family="'Space Mono', ui-monospace, monospace"
                  >{{ pct }}%</text>
                </g>

                <!-- Area fill -->
                <path v-if="hasPath" :d="areaPath" :fill="`url(#${gradId})`" />

                <!-- Line -->
                <path
                  v-if="hasPath"
                  :d="linePath"
                  fill="none"
                  :stroke="lineColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />

                <!-- Latest point dot -->
                <circle
                  v-if="selected.points.length"
                  :cx="xScale(selected.points.length - 1)"
                  :cy="yScale(latestPrice)"
                  r="4"
                  :fill="lineColor"
                  data-testid="latest-point"
                />
                <circle
                  v-if="selected.points.length"
                  :cx="xScale(selected.points.length - 1)"
                  :cy="yScale(latestPrice)"
                  r="8"
                  :fill="lineColor"
                  fill-opacity="0.2"
                />

                <!-- Hover crosshair + tooltip — WI: --wi-on-surface-variant -->
                <g v-if="hoverPoint !== null && hasPath">
                  <line
                    :x1="xScale(hoverPoint)" :y1="MT"
                    :x2="xScale(hoverPoint)" :y2="H - MB"
                    :stroke="crosshairStroke" stroke-width="1" stroke-dasharray="2,3"
                  />
                  <circle
                    :cx="xScale(hoverPoint)"
                    :cy="yScale(selected.points[hoverPoint].price_yes)"
                    r="4"
                    :fill="lineColor"
                    stroke="var(--wi-surface, var(--lp))" stroke-width="2"
                  />
                </g>
              </svg>

              <!-- Hover tooltip -->
              <div v-if="hoverPoint !== null && hoverTooltipStyle" class="pm-tooltip" :style="hoverTooltipStyle">
                <div class="pm-tooltip-price" :class="priceClass(selected.points[hoverPoint].price_yes)">
                  {{ formatPct(selected.points[hoverPoint].price_yes) }}
                </div>
                <div v-if="selected.points[hoverPoint].side" class="pm-tooltip-trade">
                  {{ selected.points[hoverPoint].side.toUpperCase() }}
                  {{ selected.points[hoverPoint].outcome }}
                  · {{ $t('charts.polymarket.shares', { count: selected.points[hoverPoint].shares?.toFixed(1) }) }}
                </div>
                <div v-else class="pm-tooltip-trade">{{ $t('charts.polymarket.origin') }}</div>
                <div class="pm-tooltip-time">{{ formatTime(selected.points[hoverPoint].t) }}</div>
              </div>
            </div>
          </template>
        </section>
      </div>
    </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { getPolymarketMarkets, getPolymarketMarketPrices } from '../api/simulation'
import { getMarketResolutions } from '../api/report'

import {
  renderSvgToCanvas,
  downloadCanvas,
  copyCanvasToClipboard,
  canCopyImageToClipboard,
  wrapText,
} from '../utils/chartExport'
import { readChartPalette } from '../utils/css-vars'

// Palette lue une seule fois au setup. US-052 : auparavant les hex étaient
// hardcodés (#43C165, #FF4444, #FF6B1A, #0A0A0A) → désormais via design tokens
// pour rester synchrones avec --ms-chart-*. Voir frontend/src/utils/css-vars.js.
const palette = readChartPalette()

// US-053 : helper de lecture des design tokens Warm Intelligence à la volée.
// Permet la bascule de thème (dark mode futur) sans recharger le composant.
const cssVar = (name) => {
  if (typeof window === 'undefined') return ''
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

// Couleurs WI dérivées des tokens. Yes (price ≥ 0.55) → mint --wi-secondary,
// No (price ≤ 0.45) → terracotta --wi-on-primary-container, neutre → orange
// --wi-primary-container. Override de la palette ms-chart pour le rendu inline.
const wiColors = {
  yes: cssVar('--wi-secondary') || palette.chart2,        // bullish / positive
  no: cssVar('--wi-on-primary-container') || palette.chart5, // bearish / negative
  neutral: cssVar('--wi-primary-container') || palette.chart1, // neutral
  ink: cssVar('--wi-on-surface') || palette.chart3,
}

// Helpers RGB pour stroke/fill avec alpha (axes et grid)
const _hexToRgba = (hex, alpha) => {
  if (!hex || !hex.startsWith('#')) return hex
  let h = hex.slice(1)
  if (h.length === 3) h = h.split('').map(c => c + c).join('')
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return `rgba(${r},${g},${b},${alpha})`
}
const gridStroke = _hexToRgba(cssVar('--wi-outline-variant') || '#dec0b6', 0.5)
const axisLabelFill = _hexToRgba(cssVar('--wi-on-surface-variant') || '#57423a', 0.7)
const crosshairStroke = _hexToRgba(cssVar('--wi-on-surface-variant') || '#57423a', 0.4)

const props = defineProps({
  simulationId: { type: String, required: true },
  visible: { type: Boolean, default: false },
  live: { type: Boolean, default: false },
})

const { t, locale } = useI18n()

const W = 900
const H = 360
const ML = 16
const MR = 44
const MT = 16
const MB = 24

const markets = ref([])
const marketsLoading = ref(false)
const marketsError = ref('')
const selectedId = ref(null)
const selected = ref(null)
const selectedError = ref('')
const durableEnvelope = ref({ resolutions: [], final_wealth: [], complete: false })
const pollTimer = ref(null)
const hoverPoint = ref(null)
const hoverTooltipStyle = ref(null)
const chartSvg = ref(null)
const exporting = ref(false)
const copiedFlash = ref(false)
let copiedFlashTimer = null
const copySupported = canCopyImageToClipboard()

const gradId = computed(() => `pm-grad-${selectedId.value ?? 'x'}`)

const latestPrice = computed(() => {
  if (!selected.value?.points?.length) return null
  return selected.value.points[selected.value.points.length - 1].price_yes
})

const priceDelta = computed(() => {
  const pts = selected.value?.points
  if (!pts || pts.length < 2) return null
  return pts[pts.length - 1].price_yes - pts[0].price_yes
})

const lineColor = computed(() => {
  const p = latestPrice.value
  // US-053 WI : Yes → mint, No → terracotta, neutre → orange
  if (p >= 0.55) return wiColors.yes
  if (p <= 0.45) return wiColors.no
  return wiColors.neutral
})

const tradeVolume = computed(() => {
  const pts = selected.value?.points || []
  return pts.reduce((sum, p) => sum + (p.shares || 0), 0)
})

const xScale = (i) => {
  const pts = selected.value?.points || []
  if (pts.length <= 1) return (ML + W - MR) / 2
  const w = W - ML - MR
  return ML + (i / (pts.length - 1)) * w
}

const yScale = (price) => {
  const h = H - MT - MB
  return MT + (1 - price) * h
}

const hasPath = computed(() => (selected.value?.points?.length || 0) >= 2)

const linePath = computed(() => {
  const pts = selected.value?.points || []
  return pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${xScale(i).toFixed(2)},${yScale(p.price_yes).toFixed(2)}`).join(' ')
})

const areaPath = computed(() => {
  const pts = selected.value?.points || []
  if (pts.length < 2) return ''
  const top = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${xScale(i).toFixed(2)},${yScale(p.price_yes).toFixed(2)}`).join(' ')
  const baseY = (H - MB).toFixed(2)
  return `${top} L${xScale(pts.length - 1).toFixed(2)},${baseY} L${xScale(0).toFixed(2)},${baseY} Z`
})

function marketQuestion(market) {
  return market.question || t('charts.polymarket.questionFallback', { id: market.market_id })
}

function outcomeLabel(outcome) {
  if (outcome === 'YES') return t('charts.polymarket.yes')
  if (outcome === 'NO') return t('charts.polymarket.no')
  if (outcome === 'INVALID') return t('charts.polymarket.invalid')
  return outcome || ''
}

function evidenceLabel(item) {
  return t('charts.polymarket.evidenceEntry', {
    round: item.round,
    type: item.type,
    ref: item.ref,
  })
}

function formatDate(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat(locale.value, { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function formatWealth(value) {
  if (!Number.isFinite(value)) return '—'
  return new Intl.NumberFormat(locale.value, { maximumFractionDigits: 2 }).format(value)
}

function formatPct(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  return `${(v * 100).toFixed(1)}%`
}

function priceClass(p) {
  if (p >= 0.55) return 'pm-up'
  if (p <= 0.45) return 'pm-down'
  return 'pm-neutral'
}

function deltaClass(d) {
  if (d > 0.005) return 'pm-up'
  if (d < -0.005) return 'pm-down'
  return 'pm-neutral'
}

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return String(t)
  return d.toLocaleString()
}

async function fetchMarkets({ autoSelect = false } = {}) {
  if (!props.simulationId) return
  marketsLoading.value = true
  marketsError.value = ''
  try {
    const res = await getPolymarketMarkets(props.simulationId)
    const data = res?.data?.data || res?.data || {}
    markets.value = Array.isArray(data.markets) ? data.markets : []
    if (autoSelect && markets.value.length && selectedId.value === null) {
      const topMarket = [...markets.value].sort((a, b) => (b.trade_count || 0) - (a.trade_count || 0))[0]
      selectedId.value = topMarket.market_id
    }
  } catch (err) {
    marketsError.value = err?.response?.data?.error || err?.message || 'Failed to load markets'
  } finally {
    marketsLoading.value = false
  }
}

async function fetchSelected() {
  if (!props.simulationId || selectedId.value === null) return
  try {
    const res = await getPolymarketMarketPrices(props.simulationId, selectedId.value)
    const payload = res?.data?.data || res?.data
    if (payload?.market) {
      selected.value = payload
      selectedError.value = ''
    }
  } catch (err) {
    selectedError.value = err?.response?.data?.error || err?.message || 'Failed to load prices'
  }
}

function durableMarket(resolution) {
  const points = Array.isArray(resolution.price_series) ? resolution.price_series : []
  return {
    market_id: resolution.market_id,
    question: resolution.question,
    price_yes: points.at(-1)?.price_yes ?? null,
    point_count: points.length,
    resolved: resolution.verdict !== 'UNRESOLVED',
    winning_outcome: resolution.verdict,
  }
}

function selectDurableMarket(id) {
  const resolution = durableEnvelope.value.resolutions.find((item) => item.market_id === id)
  if (!resolution) return
  const points = Array.isArray(resolution.price_series) ? resolution.price_series : []
  selected.value = { market: durableMarket(resolution), points, resolution }
  selectedError.value = ''
}

async function fetchDurableResolutions() {
  if (!props.simulationId) return
  marketsLoading.value = true
  marketsError.value = ''
  try {
    const res = await getMarketResolutions(props.simulationId)
    const data = res?.data?.data || res?.data || {}
    durableEnvelope.value = {
      resolutions: Array.isArray(data.resolutions) ? data.resolutions : [],
      final_wealth: Array.isArray(data.final_wealth) ? data.final_wealth : [],
      complete: data.complete === true,
    }
    markets.value = durableEnvelope.value.resolutions.map(durableMarket)
    if (markets.value.length) {
      selectedId.value = markets.value[0].market_id
      selectDurableMarket(selectedId.value)
    }
  } catch (_) {
    marketsError.value = 'load_error'
  } finally {
    marketsLoading.value = false
  }
}

function selectMarket(id) {
  selectedId.value = id
  selected.value = null
  hoverPoint.value = null
  if (props.live) fetchSelected()
  else selectDurableMarket(id)
}

function startPolling() {
  if (!props.live) return
  if (pollTimer.value) clearInterval(pollTimer.value)
  pollTimer.value = setInterval(async () => {
    await fetchMarkets()
    if (selectedId.value !== null) await fetchSelected()
  }, 4000)
}

function handleHover(event) {
  const pts = selected.value?.points || []
  if (!pts.length) {
    hoverPoint.value = null
    hoverTooltipStyle.value = null
    return
  }
  const rect = event.currentTarget.getBoundingClientRect()
  const relX = (event.clientX - rect.left) / rect.width
  const svgX = relX * W
  const clamped = Math.max(ML, Math.min(W - MR, svgX))
  const frac = (clamped - ML) / (W - ML - MR)
  const idx = Math.round(frac * (pts.length - 1))
  hoverPoint.value = Math.max(0, Math.min(pts.length - 1, idx))

  const tx = (xScale(hoverPoint.value) / W) * rect.width
  const ty = (yScale(pts[hoverPoint.value].price_yes) / H) * rect.height
  const leftSide = tx > rect.width / 2
  hoverTooltipStyle.value = {
    left: leftSide ? `${tx - 160}px` : `${tx + 12}px`,
    top: `${Math.max(8, ty - 60)}px`,
  }
}

// ── Chart export (copy + download as PNG, with Bassira watermark) ──

const PX = 32 // header horizontal padding

// Colour matching `priceClass` / `deltaClass` used in the live panel.
// US-053 WI : aligné sur la palette warm intelligence du chart inline.
const _priceColor = (p) => {
  if (p >= 0.55) return wiColors.yes
  if (p <= 0.45) return wiColors.no
  return wiColors.neutral
}

const _buildExportCanvas = async () => {
  if (!chartSvg.value || !selected.value) {
    throw new Error(t('charts.polymarket.noChartToExport'))
  }
  const m = selected.value.market
  const pts = selected.value.points || []
  const question = marketQuestion(m)
  const priceVal = latestPrice.value
  const priceColor = _priceColor(priceVal)
  const priceStr = formatPct(priceVal)
  const exportOutcomeLabel = outcomeLabel(m.outcome_a || 'YES')
  const delta = priceDelta.value
  const deltaStr = delta != null ? `${delta >= 0 ? '▲' : '▼'} ${(Math.abs(delta) * 100).toFixed(1)}%` : null
  const deltaColor = delta == null
    ? null
    : (delta > 0.005 ? wiColors.yes : (delta < -0.005 ? wiColors.no : wiColors.neutral))

  const stats = props.live
    ? [
      { k: t('charts.polymarket.tradesLabel'), v: String(Math.max(pts.length - 1, 0)) },
      { k: t('charts.polymarket.volume'), v: tradeVolume.value.toFixed(1) },
      { k: t('charts.polymarket.outcomes'), v: `${outcomeLabel(m.outcome_a || 'YES')}/${outcomeLabel(m.outcome_b || 'NO')}` },
    ]
    : [{ k: t('charts.polymarket.pricePointsLabel'), v: String(pts.length) }]
  if (m.resolved) stats.push({ k: t('charts.polymarket.adjudicatedLabel'), v: outcomeLabel(m.winning_outcome) })

  // ── Measure title height so the header sizes to its content ──
  // Fonts: Young Serif 44px for the title, Space Mono for everything else.
  const titleFont = '700 44px "Young Serif", Georgia, serif'
  const titleLineHeight = 54
  const measureCanvas = document.createElement('canvas')
  const measureCtx = measureCanvas.getContext('2d')
  measureCtx.font = titleFont
  const titleLines = wrapText(measureCtx, question, W - PX * 2)

  // Layout: 36 (top) + title + 22 (gap) + 60 (price row) + 18 (gap) + 42 (stats) + 28 (bottom)
  const titleBlock = titleLines.length * titleLineHeight
  const headerHeight = 36 + titleBlock + 22 + 60 + 18 + 42 + 28

  const drawHeader = (ctx) => {
    let y = 36

    // ── Title ── Young Serif, largest element. US-053 WI : ink --wi-on-surface
    ctx.fillStyle = wiColors.ink
    ctx.font = titleFont
    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'
    for (const line of titleLines) {
      ctx.fillText(line, PX, y)
      y += titleLineHeight
    }
    y += 22 - (titleLineHeight - 44) // tighten after last baseline

    // ── Big orange price ──
    ctx.fillStyle = priceColor
    ctx.font = '700 56px "Space Mono", "JetBrains Mono", ui-monospace, monospace'
    ctx.textBaseline = 'alphabetic'
    const priceBaseline = y + 46
    ctx.fillText(priceStr, PX, priceBaseline)
    const priceWidth = ctx.measureText(priceStr).width

    // "CHANCE YES" label next to the price
    ctx.fillStyle = 'rgba(10, 10, 10, 0.5)'
    ctx.font = '400 13px "Space Mono", "JetBrains Mono", ui-monospace, monospace'
    ctx.fillText(t('charts.polymarket.chance', { outcome: exportOutcomeLabel }), PX + priceWidth + 18, priceBaseline - 4)

    // Delta pill, right-aligned to keep from colliding with the label
    if (deltaStr) {
      ctx.font = '700 15px "Space Mono", "JetBrains Mono", ui-monospace, monospace'
      const dw = ctx.measureText(deltaStr).width + 24
      const dh = 32
      const dx = W - PX - dw
      const dy = priceBaseline - 34
      // Tinted background (12% opacity of the delta colour)
      ctx.fillStyle = deltaColor + '1f' // 1f = ~12% alpha
      ctx.fillRect(dx, dy, dw, dh)
      ctx.fillStyle = deltaColor
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(deltaStr, dx + dw / 2, dy + dh / 2)
      ctx.textAlign = 'left'
    }

    y = priceBaseline + 14 + 18 // below the price baseline, gap

    // ── Stats row ──
    const colW = (W - PX * 2) / stats.length
    stats.forEach((s, i) => {
      const cx = PX + i * colW
      // Label (uppercase small)
      ctx.fillStyle = 'rgba(10, 10, 10, 0.45)'
      ctx.font = '700 10px "Space Mono", "JetBrains Mono", ui-monospace, monospace'
      ctx.textAlign = 'left'
      ctx.textBaseline = 'top'
      ctx.fillText(s.k, cx, y)
      // Value — US-053 WI : ink --wi-on-surface
      ctx.fillStyle = wiColors.ink
      ctx.font = '700 14px "Space Mono", "JetBrains Mono", ui-monospace, monospace'
      ctx.fillText(s.v, cx, y + 16)
    })
  }

  return renderSvgToCanvas(chartSvg.value, {
    width: W,
    height: H,
    scale: 2,
    headerHeight,
    drawHeader,
    subtitle: `${props.simulationId || 'simulation'} · ${new Date().toLocaleDateString()}`,
  })
}

const _flashCopied = () => {
  copiedFlash.value = true
  if (copiedFlashTimer) clearTimeout(copiedFlashTimer)
  copiedFlashTimer = setTimeout(() => { copiedFlash.value = false }, 1600)
}

async function copyChart() {
  if (exporting.value) return
  exporting.value = true
  try {
    const canvas = await _buildExportCanvas()
    await copyCanvasToClipboard(canvas)
    _flashCopied()
  } catch (err) {
    // Fall back to download so the user doesn't lose the image
    console.warn('[markets] copy failed, falling back to download:', err)
    try {
      const canvas = await _buildExportCanvas()
      const fname = `markets-${selected.value?.market?.market_id ?? 'x'}-${props.simulationId || 'sim'}.png`
      downloadCanvas(canvas, fname)
    } catch (err2) {
      console.error('[markets] download fallback failed:', err2)
    }
  } finally {
    exporting.value = false
  }
}

async function downloadChart() {
  if (exporting.value) return
  exporting.value = true
  try {
    const canvas = await _buildExportCanvas()
    const marketId = selected.value?.market?.market_id ?? 'x'
    const fname = `bassira-market-${marketId}-${props.simulationId || 'sim'}.png`
    downloadCanvas(canvas, fname)
  } catch (err) {
    console.error('[markets] download failed:', err)
  } finally {
    exporting.value = false
  }
}

// Parent uses v-if, so the component only exists while the overlay is visible.
// Kick off polling on mount; stop it on unmount.
const start = async () => {
  hoverPoint.value = null
  selected.value = null
  selectedId.value = null
  durableEnvelope.value = { resolutions: [], final_wealth: [], complete: false }
  if (props.live) {
    await fetchMarkets({ autoSelect: true })
    if (selectedId.value !== null) await fetchSelected()
    startPolling()
  } else {
    await fetchDurableResolutions()
  }
}

watch(() => props.simulationId, () => {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
  start()
})

watch(() => props.live, () => {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
  start()
})

onMounted(() => { start() })

onBeforeUnmount(() => {
  if (pollTimer.value) clearInterval(pollTimer.value)
  if (copiedFlashTimer) clearTimeout(copiedFlashTimer)
})
</script>

<style scoped>
/* Bassira-native Polymarket panel — renders inline inside the parent
   .influence-overlay, matching the other toolbar overlays (Influence/Drift/
   Network/Demographics/What If?/Branch). No fixed positioning, no modal. */

.pm-panel {
  width: 100%;
  height: 100%;
  background: var(--wi-surface, var(--background));
  color: var(--wi-on-surface, var(--foreground));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: var(--wi-font-body, var(--font-mono));
}

/* ── Header — mirrors .lb-header ── */
.pm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--wi-outline-variant, rgba(10, 10, 10, 0.08));
  flex-shrink: 0;
}

.pm-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Header action cluster — mirrors .export-btn in InfluenceLeaderboard */
.pm-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pm-export-btn {
  background: var(--wi-surface-container-low, transparent);
  border: 1px solid var(--wi-outline-variant, rgba(10, 10, 10, 0.15));
  border-radius: var(--wi-radius-md, 8px);
  color: var(--wi-on-surface-variant, rgba(10, 10, 10, 0.5));
  padding: 4px 10px;
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.pm-export-btn:hover:not(:disabled) {
  border-color: var(--wi-primary-container, var(--color-orange));
  color: var(--wi-primary, var(--color-orange));
  background: var(--wi-surface-container, transparent);
}

.pm-export-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.pm-logo {
  width: 14px;
  height: 14px;
  border-radius: 2px;
}

.pm-header-title {
  font-family: var(--wi-font-heading, var(--font-mono));
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant, rgba(10, 10, 10, 0.5));
}

.pm-live-dot {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  background: var(--wi-surface-container-low, transparent);
  border: 1px solid var(--wi-primary-container, var(--color-orange));
  border-radius: var(--wi-radius-pill, 9999px);
  color: var(--wi-on-primary-container, var(--color-orange));
  font-family: var(--wi-font-heading, var(--font-mono));
  font-size: 10px;
  letter-spacing: 2px;
  font-weight: 700;
  margin-inline-start: 8px;
  text-transform: uppercase;
}

.pm-live-pulse {
  width: 6px;
  height: 6px;
  background: var(--wi-primary-container, var(--color-orange));
  border-radius: 50%;
  animation: pm-pulse 1.4s ease-in-out infinite;
}

@keyframes pm-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.3; transform: scale(1.3); }
}

.pm-body {
  flex: 1;
  display: grid;
  grid-template-columns: 320px 1fr;
  overflow: hidden;
}

/* Market list — subtler separator, rows match .lb-row treatment */
.pm-market-list {
  border-inline-end: 1px solid var(--wi-outline-variant, rgba(10, 10, 10, 0.08));
  overflow-y: auto;
  padding: 0;
  background: var(--wi-surface, var(--background));
}

.pm-market-row {
  width: 100%;
  text-align: start;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--wi-outline-variant, rgba(10, 10, 10, 0.04));
  border-inline-start: 3px solid transparent;
  padding: 10px 14px;
  cursor: pointer;
  color: inherit;
  font-family: var(--wi-font-body, var(--font-mono));
  transition: background 0.1s ease;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pm-market-row:hover {
  background: var(--wi-surface-container-low, rgba(10, 10, 10, 0.02));
}

/* Active row — left-accent terracotta WI */
.pm-market-row-active {
  background: var(--wi-surface-container, rgba(10, 10, 10, 0.02));
  border-inline-start-color: var(--wi-primary-container, var(--color-orange));
}

.pm-market-q {
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 12px;
  line-height: 1.4;
  color: var(--wi-on-surface, var(--color-black));
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pm-market-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  font-family: var(--font-mono);
}

.pm-market-price {
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.5px;
}

/* US-053 WI : Yes=mint, No=terracotta, neutre=orange */
.pm-up { color: var(--wi-secondary, var(--color-green)); }
.pm-down { color: var(--wi-on-primary-container, var(--color-red)); }
.pm-neutral { color: var(--wi-primary-container, var(--color-orange)); }

.pm-market-trades {
  color: rgba(10, 10, 10, 0.5);
  font-size: 10px;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.pm-market-resolved {
  margin-inline-start: auto;
  padding: 2px 8px;
  background: var(--wi-on-surface, var(--color-black));
  color: var(--wi-surface, var(--color-white));
  font-size: 9px;
  letter-spacing: 1px;
  border-radius: var(--wi-radius-pill, 0);
  text-transform: uppercase;
}

.pm-empty {
  padding: 36px 20px;
  text-align: center;
  color: rgba(10, 10, 10, 0.55);
  font-family: var(--font-mono);
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pm-empty-title {
  color: var(--wi-on-surface, var(--color-black));
  font-family: var(--wi-font-heading, var(--font-mono));
  font-weight: 600;
  font-size: 12px;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.pm-empty-hint {
  font-size: 11px;
  color: var(--wi-on-surface-variant, rgba(10, 10, 10, 0.5));
  line-height: 1.5;
}

.pm-error {
  color: var(--wi-error, var(--color-red));
}

/* Chart section */
.pm-chart-section {
  padding: 20px 24px 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: var(--wi-surface, var(--color-white));
}

.pm-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--wi-on-surface-variant, rgba(10, 10, 10, 0.35));
  font-family: var(--wi-font-heading, var(--font-mono));
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.pm-placeholder-icon {
  font-size: 36px;
  color: var(--wi-primary-container, var(--color-orange));
  opacity: 0.4;
}

.pm-chart-header {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--wi-outline-variant, rgba(10, 10, 10, 0.12));
}

.pm-chart-q {
  font-family: var(--wi-font-heading, var(--font-display));
  font-size: 22px;
  font-weight: 600;
  line-height: 1.25;
  color: var(--wi-on-surface, var(--color-black));
}

.pm-chart-price-row {
  display: flex;
  align-items: baseline;
  gap: 14px;
}

.pm-chart-price {
  font-family: var(--font-mono);
  font-size: 40px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.01em;
}

.pm-chart-outcome-label {
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 10px;
  color: var(--wi-on-surface-variant, rgba(10, 10, 10, 0.5));
  margin-inline-start: 10px;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.pm-chart-delta {
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.5px;
  padding: 3px 10px;
  border-radius: var(--wi-radius-pill, 0);
}

/* US-053 WI : delta tints sur palette warm */
.pm-chart-delta.pm-up {
  background: color-mix(in srgb, var(--wi-secondary, var(--ms-chart-2)) 12%, transparent);
}

.pm-chart-delta.pm-down {
  background: color-mix(in srgb, var(--wi-on-primary-container, var(--ms-chart-5)) 12%, transparent);
}

.pm-chart-delta.pm-neutral {
  background: color-mix(in srgb, var(--wi-primary-container, var(--ms-chart-1)) 12%, transparent);
}

.pm-chart-stats {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  margin-top: 6px;
  font-family: var(--font-mono);
}

.pm-stat {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.pm-stat-k {
  font-family: var(--wi-font-heading, var(--font-mono));
  font-size: 9px;
  letter-spacing: 2px;
  color: var(--wi-on-surface-variant, rgba(10, 10, 10, 0.45));
  font-weight: 600;
  text-transform: uppercase;
}

.pm-stat-v {
  font-size: 12px;
  font-family: var(--wi-font-body, var(--font-mono));
  color: var(--wi-on-surface, var(--color-black));
  font-weight: 700;
}

.pm-stat-resolved {
  padding: 6px 12px;
  background: var(--wi-secondary, var(--color-green));
  color: var(--wi-on-secondary, var(--color-white));
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 2px;
  border-radius: var(--wi-radius-pill, 0);
  align-self: center;
  text-transform: uppercase;
}

.pm-chart-wrap {
  flex: 1;
  min-height: 320px;
  position: relative;
  background: var(--wi-surface-container-low, rgba(10, 10, 10, 0.02));
  border: 1px solid var(--wi-outline-variant, rgba(10, 10, 10, 0.06));
  border-radius: var(--wi-radius-md, 0);
  padding: 4px;
}

.pm-resolution,
.pm-final-wealth,
.pm-no-series {
  border: 1px solid var(--wi-outline-variant, rgba(10, 10, 10, 0.12));
  border-radius: var(--wi-radius-md, 8px);
  padding: 12px;
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 12px;
}

.pm-resolution {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
}

.pm-resolution-item,
.pm-final-wealth-title {
  color: var(--wi-on-surface, var(--color-black));
  font-weight: 700;
}

.pm-resolution-justification,
.pm-evidence,
.pm-final-wealth ul {
  width: 100%;
  margin: 0;
}

.pm-evidence,
.pm-final-wealth ul {
  padding-inline-start: 18px;
}

.pm-final-wealth li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.pm-no-series {
  color: var(--wi-on-surface-variant, rgba(10, 10, 10, 0.55));
}

.pm-chart-svg {
  width: 100%;
  height: 100%;
  display: block;
}

/* Tooltip — WI surface, soft shadow, radius md */
.pm-tooltip {
  position: absolute;
  min-width: 150px;
  padding: 10px 12px;
  background: var(--wi-surface, var(--color-white));
  border: 1px solid var(--wi-outline-variant, rgba(10, 10, 10, 0.12));
  border-radius: var(--wi-radius-md, 0);
  box-shadow: var(--wi-shadow-md, none);
  pointer-events: none;
  z-index: 5;
  font-family: var(--wi-font-body, var(--font-mono));
}

.pm-tooltip-price {
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 16px;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: 0.5px;
}

.pm-tooltip-trade {
  font-size: 10px;
  color: var(--wi-on-surface, rgba(10, 10, 10, 0.65));
  margin-top: 4px;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.pm-tooltip-time {
  font-size: 10px;
  color: var(--wi-on-surface-variant, rgba(10, 10, 10, 0.45));
  margin-top: 2px;
  font-family: var(--wi-font-body, var(--font-mono));
}

/* Scrollbar in light theme */
.pm-market-list::-webkit-scrollbar,
.pm-chart-section::-webkit-scrollbar {
  width: 10px;
}
.pm-market-list::-webkit-scrollbar-track,
.pm-chart-section::-webkit-scrollbar-track {
  background: var(--wi-surface-container-low, var(--color-gray));
}
.pm-market-list::-webkit-scrollbar-thumb,
.pm-chart-section::-webkit-scrollbar-thumb {
  background: var(--wi-outline-variant, rgba(10, 10, 10, 0.2));
  border-radius: var(--wi-radius-pill, 0);
}
</style>
