<template>
  <div class="belief-drift">
    <!-- Header -->
    <div class="bd-header">
      <div class="bd-title">
        <span class="bd-icon">◎</span>
        <span class="bd-label">{{ $t('charts.belief.title').toUpperCase() }}</span>
      </div>
      <div class="bd-header-actions">
        <button
          class="bd-export-btn"
          :disabled="!hasData || exporting || !copySupported"
          :title="copySupported ? 'Copy chart as PNG (with Bassira watermark)' : 'Image copy not supported in this browser'"
          @click="copyChart"
        >
          {{ copiedFlash ? $t('embed.copied') : $t('embed.copy') }}
        </button>
        <button
          class="bd-export-btn"
          :disabled="!hasData || exporting"
          @click="downloadChart"
          title="Download chart as PNG (with Bassira watermark)"
        >
          Download ↓
        </button>
      </div>
    </div>

    <!-- Legend -->
    <div class="bd-legend">
      <span class="legend-item"><span class="legend-dot bullish-dot"></span>Bullish (&gt;+0.2)</span>
      <span class="legend-item"><span class="legend-dot neutral-dot"></span>Neutral</span>
      <span class="legend-item"><span class="legend-dot bearish-dot"></span>Bearish (&lt;-0.2)</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="bd-state">
      <div class="pulse-ring"></div>
      <span>{{ $t('charts.common.loading') }}</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="bd-state bd-error-state">{{ error }}</div>

    <!-- No trajectory data -->
    <div v-else-if="!hasData" class="bd-state">
      <span>{{ $t('charts.common.noData') }}</span>
      <span class="bd-hint">{{ $t('charts.belief.subtitle') }}</span>
    </div>

    <!-- Chart -->
    <div v-else class="bd-chart-wrap">
      <svg
        :viewBox="`0 0 ${W} ${H}`"
        preserveAspectRatio="xMidYMid meet"
        class="bd-svg"
        ref="svgRef"
        xmlns="http://www.w3.org/2000/svg"
      >
        <!-- Horizontal grid lines + Y labels — WI palette: --wi-outline-variant -->
        <g v-for="pct in [0, 25, 50, 75, 100]" :key="pct">
          <line
            :x1="ML" :y1="yS(pct)"
            :x2="W - MR" :y2="yS(pct)"
            :stroke="gridStroke" stroke-width="1"
          />
          <text
            :x="ML - 5" :y="yS(pct) + 4"
            :fill="axisLabelFill" font-size="9"
            font-family="monospace" text-anchor="end"
          >{{ pct }}%</text>
        </g>

        <!-- Stacked area: bearish (bottom layer) — US-013: --ms-status-danger -->
        <path
          :d="bearishPath"
          :fill="bearishFill"
          :stroke="bearishStroke"
          stroke-width="1"
        />

        <!-- Stacked area: neutral (middle) — US-013: --ms-chart-9 -->
        <path
          :d="neutralPath"
          :fill="neutralFill"
          :stroke="neutralStroke"
          stroke-width="1"
        />

        <!-- Stacked area: bullish (top) — US-013: --ms-status-success -->
        <path
          :d="bullishPath"
          :fill="bullishFill"
          :stroke="bullishStroke"
          stroke-width="1"
        />

        <!-- Consensus vertical line — WI: --wi-on-surface-variant -->
        <line
          v-if="driftData.consensus_round != null"
          :x1="xS(driftData.consensus_round)" :y1="MT"
          :x2="xS(driftData.consensus_round)" :y2="H - MB"
          :stroke="consensusStroke" stroke-width="1.5"
          stroke-dasharray="4,3"
        />
        <text
          v-if="driftData.consensus_round != null"
          :x="xS(driftData.consensus_round) + 4" :y="MT + 12"
          :fill="consensusStroke" font-size="9" font-family="monospace"
        >consensus r{{ driftData.consensus_round }}</text>

        <!-- Director event injection markers — WI: --wi-primary -->
        <g v-for="(evt, idx) in eventMarkers" :key="'evt' + idx">
          <line
            :x1="xS(evt.round)" :y1="MT"
            :x2="xS(evt.round)" :y2="H - MB"
            :stroke="eventStroke" stroke-width="1.5"
            stroke-dasharray="3,2"
          />
          <text
            :x="xS(evt.round) + 4"
            :y="MT + 12 + idx * 11"
            :fill="eventLabelFill" font-size="8" font-family="monospace"
          >⚡ r{{ evt.round }}</text>
        </g>

        <!-- X axis labels -->
        <text
          v-for="r in xTicks"
          :key="'xt' + r"
          :x="xS(r)" :y="H - MB + 13"
          :fill="axisLabelFill" font-size="9"
          font-family="monospace" text-anchor="middle"
        >{{ r }}</text>

        <!-- X axis title -->
        <text
          :x="ML + (W - ML - MR) / 2" :y="H - 2"
          :fill="axisTitleFill" font-size="9"
          font-family="monospace" text-anchor="middle"
        >Round</text>
      </svg>
    </div>

    <!-- Summary line -->
    <div v-if="driftData?.summary" class="bd-summary">
      {{ driftData.summary }}
    </div>

    <!-- Topics footer -->
    <div v-if="driftData?.topics?.length" class="bd-topics">
      Topics: {{ driftData.topics.join(' · ') }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { getBeliefDrift } from '../api/simulation'

import {
  renderSvgToCanvas,
  downloadCanvas,
  copyCanvasToClipboard,
  canCopyImageToClipboard,
  buildTitledHeader,
} from '../utils/chartExport'

// US-013 : palette sémantique lue depuis les design tokens CSS au mount
// (conservée pour chartExport / fallback). Les couleurs effectives du chart
// sont désormais lues à la volée depuis les tokens --wi-* (Warm Intelligence).

// US-053 : helper de lecture des design tokens CSS Warm Intelligence.
// Lu à chaque calcul pour permettre la bascule de thème (dark mode futur)
// sans recharger le composant. Retourne le hex/rgba résolu trimé.
const cssVar = (name) => {
  if (typeof window === 'undefined') return ''
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

const props = defineProps({
  simulationId: { type: String, required: true },
  visible: { type: Boolean, default: false },
  directorEvents: { type: Array, default: () => [] }
})

const loading = ref(false)
const error = ref('')
const driftData = ref(null)
const svgRef = ref(null)
const exporting = ref(false)
const copiedFlash = ref(false)
let copiedFlashTimer = null
const copySupported = canCopyImageToClipboard()

// SVG dimensions and margins
const W = 560
const H = 200
const MT = 14  // margin top
const MB = 26  // margin bottom
const ML = 34  // margin left
const MR = 12  // margin right

const hasData = computed(() =>
  driftData.value?.rounds?.length > 0
)

const minR = computed(() => hasData.value ? driftData.value.rounds[0] : 1)
const maxR = computed(() => hasData.value ? driftData.value.rounds[driftData.value.rounds.length - 1] : 10)

const xS = (r) => {
  const span = Math.max(maxR.value - minR.value, 1)
  return ML + ((r - minR.value) / span) * (W - ML - MR)
}

const yS = (pct) => {
  return MT + (1 - pct / 100) * (H - MT - MB)
}

const xTicks = computed(() => {
  if (!hasData.value) return []
  const rounds = driftData.value.rounds
  if (rounds.length <= 10) return rounds
  const step = Math.ceil(rounds.length / 10)
  return rounds.filter((_, i) => i % step === 0 || i === rounds.length - 1)
})

// Build a closed SVG area path between topPcts and botPcts arrays
const areaPath = (topPcts, botPcts, rounds) => {
  if (!rounds.length) return ''
  const top = rounds.map((r, i) => `${i === 0 ? 'M' : 'L'}${xS(r).toFixed(1)},${yS(topPcts[i]).toFixed(1)}`).join(' ')
  const bot = rounds.slice().reverse().map((r, i) => {
    const orig = rounds.length - 1 - i
    return `L${xS(r).toFixed(1)},${yS(botPcts[orig]).toFixed(1)}`
  }).join(' ')
  return `${top} ${bot} Z`
}

const bearishPath = computed(() => {
  if (!hasData.value) return ''
  const { rounds, bearish } = driftData.value
  return areaPath(bearish, bearish.map(() => 0), rounds)
})

const neutralPath = computed(() => {
  if (!hasData.value) return ''
  const { rounds, bearish, neutral } = driftData.value
  const top = bearish.map((b, i) => b + neutral[i])
  return areaPath(top, bearish, rounds)
})

const bullishPath = computed(() => {
  if (!hasData.value) return ''
  const { rounds, bearish, neutral, bullish } = driftData.value
  const bot = bearish.map((b, i) => b + neutral[i])
  const top = bot.map((b, i) => b + bullish[i])
  return areaPath(top, bot, rounds)
})

const eventMarkers = computed(() => {
  if (!hasData.value || !props.directorEvents?.length) return []
  return props.directorEvents
    .filter(e => e.injected_at_round != null)
    .map(e => ({ round: e.injected_at_round, text: e.event_text }))
})

// US-053 : palette Warm Intelligence pour le chart de dérive.
// Bullish (haut) → mint --wi-secondary, neutral → --wi-outline,
// Bearish (bas) → terracotta --wi-on-primary-container.
// Les fills utilisent 35 %, les strokes 80 % d'opacité.
const _hexToRgba = (hex, alpha) => {
  if (!hex || !hex.startsWith('#')) return hex
  // Supporte #RGB ou #RRGGBB
  let h = hex.slice(1)
  if (h.length === 3) h = h.split('').map(c => c + c).join('')
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return `rgba(${r},${g},${b},${alpha})`
}
// Lazy getters via computed-like patterns. Vue parsera la fct ref en run-time.
const _wi = (name, fallback) => _hexToRgba(cssVar(name) || fallback, 1)
const bullishColor = cssVar('--wi-secondary') || '#006d44'
const bearishColor = cssVar('--wi-on-primary-container') || '#6d2400'
const neutralColor = cssVar('--wi-outline') || '#8a7269'

const bullishFill   = _hexToRgba(bullishColor, 0.35)
const bullishStroke = _hexToRgba(bullishColor, 0.8)
const bearishFill   = _hexToRgba(bearishColor, 0.35)
const bearishStroke = _hexToRgba(bearishColor, 0.8)
const neutralFill   = _hexToRgba(neutralColor, 0.30)
const neutralStroke = _hexToRgba(neutralColor, 0.7)

// Axes / grid / overlay strokes — tokens WI
const gridStroke = _hexToRgba(cssVar('--wi-outline-variant') || '#dec0b6', 0.55)
const axisLabelFill = _hexToRgba(cssVar('--wi-on-surface-variant') || '#57423a', 0.7)
const axisTitleFill = _hexToRgba(cssVar('--wi-on-surface-variant') || '#57423a', 0.55)
const consensusStroke = _hexToRgba(cssVar('--wi-on-surface-variant') || '#57423a', 0.7)
const eventStroke = _hexToRgba(cssVar('--wi-primary') || '#a13f0f', 0.7)
const eventLabelFill = _hexToRgba(cssVar('--wi-primary') || '#a13f0f', 0.85)

const load = async () => {
  if (!props.simulationId) return
  loading.value = true
  error.value = ''
  try {
    const res = await getBeliefDrift(props.simulationId)
    if (res.success && res.data) {
      driftData.value = res.data
    } else if (res.success && !res.data) {
      driftData.value = null
    } else {
      error.value = res.error || 'Failed to load belief drift data.'
    }
  } catch (err) {
    error.value = err.message || 'Failed to load belief drift.'
  } finally {
    loading.value = false
  }
}

// ── Chart export (copy + download, with Bassira watermark) ──

const _buildExportCanvas = () => {
  if (!svgRef.value || !hasData.value) throw new Error('No chart to export')
  const d = driftData.value || {}
  const bullish = d.bullish || []
  const bearish = d.bearish || []
  const parts = []
  if (bullish.length) parts.push(`${bullish[bullish.length - 1]}% bullish`)
  if (bearish.length) parts.push(`${bearish[bearish.length - 1]}% bearish`)
  const { drawHeader, headerHeight } = buildTitledHeader({
    title: 'Belief drift — bullish / neutral / bearish',
    subtitle: parts.length ? `Final: ${parts.join(' · ')}` : null,
    width: W,
  })
  return renderSvgToCanvas(svgRef.value, {
    width: W,
    height: H,
    scale: 2,
    headerHeight,
    drawHeader,
    subtitle: `${props.simulationId} · ${new Date().toLocaleDateString()}`,
  })
}

const _flashCopied = () => {
  copiedFlash.value = true
  if (copiedFlashTimer) clearTimeout(copiedFlashTimer)
  copiedFlashTimer = setTimeout(() => { copiedFlash.value = false }, 1600)
}

async function copyChart() {
  if (exporting.value || !hasData.value) return
  exporting.value = true
  try {
    const canvas = await _buildExportCanvas()
    await copyCanvasToClipboard(canvas)
    _flashCopied()
  } catch (err) {
    console.warn('[drift] copy failed, falling back to download:', err)
    try {
      const canvas = await _buildExportCanvas()
      downloadCanvas(canvas, `bassira-drift-${props.simulationId}.png`)
    } catch (err2) {
      console.error('[drift] download fallback failed:', err2)
    }
  } finally {
    exporting.value = false
  }
}

async function downloadChart() {
  if (exporting.value || !hasData.value) return
  exporting.value = true
  try {
    const canvas = await _buildExportCanvas()
    downloadCanvas(canvas, `bassira-drift-${props.simulationId}.png`)
  } catch (err) {
    console.error('[drift] download failed:', err)
  } finally {
    exporting.value = false
  }
}

watch(() => props.visible, (val) => { if (val) load() })
watch(() => props.simulationId, () => { if (props.visible) load() })
onMounted(() => { if (props.visible) load() })
onBeforeUnmount(() => {
  if (copiedFlashTimer) clearTimeout(copiedFlashTimer)
})
</script>

<style scoped>
.belief-drift {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  font-family: var(--wi-font-body, var(--font-mono));
  background: var(--wi-surface, var(--background));
  color: var(--wi-on-surface, var(--foreground));
}

/* Header */
.bd-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--wi-outline-variant, rgba(10,10,10,0.08));
  flex-shrink: 0;
}

.bd-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bd-icon {
  /* US-053 WI : mint pour signaler la confiance / dérive trackée */
  color: var(--wi-secondary, var(--ms-status-success));
  font-size: 14px;
}

.bd-label {
  font-family: var(--wi-font-heading, var(--font-mono));
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant, rgba(10,10,10,0.5));
}

.bd-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bd-export-btn {
  background: var(--wi-surface-container-low, transparent);
  border: 1px solid var(--wi-outline-variant, rgba(10,10,10,0.15));
  border-radius: var(--wi-radius-md, 8px);
  padding: 4px 10px;
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1px;
  cursor: pointer;
  color: var(--wi-on-surface-variant, rgba(10,10,10,0.5));
  transition: all 0.15s ease;
}

.bd-export-btn:hover:not(:disabled) {
  border-color: var(--wi-primary-container, var(--color-orange));
  color: var(--wi-primary, var(--color-orange));
  background: var(--wi-surface-container, transparent);
}

.bd-export-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* Legend — WI pills cream avec border-left colored par série */
.bd-legend {
  display: flex;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--wi-outline-variant, rgba(10,10,10,0.05));
  flex-shrink: 0;
  flex-wrap: wrap;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px 3px 8px;
  background: var(--wi-surface-container-low, transparent);
  border-radius: var(--wi-radius-pill, 9999px);
  font-family: var(--wi-font-heading, var(--font-mono));
  font-size: 12px;
  font-weight: 600;
  color: var(--wi-on-surface, rgba(10,10,10,0.7));
  letter-spacing: 0.01em;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--wi-radius-sm, 2px);
}

/* US-053 WI : bullish=mint, neutral=outline, bearish=terracotta */
.bullish-dot { background: var(--wi-secondary, var(--ms-status-success)); opacity: 0.85; }
.neutral-dot { background: var(--wi-outline, var(--ms-chart-9)); opacity: 0.7; }
.bearish-dot { background: var(--wi-on-primary-container, var(--ms-status-danger)); opacity: 0.85; }

/* States */
.bd-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 8px;
  padding: 40px;
  font-size: 13px;
  color: rgba(10,10,10,0.35);
  letter-spacing: 1px;
  text-align: center;
}

.bd-error-state { color: var(--wi-error, var(--ms-status-danger-strong)); }

.bd-hint {
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 11px;
  color: var(--wi-on-surface-variant, rgba(10,10,10,0.45));
}

.pulse-ring {
  width: 20px;
  height: 20px;
  /* US-053 WI : ring mint (cohérent avec --bd-icon) */
  border: 2px solid var(--wi-secondary, var(--ms-status-success));
  border-radius: 50%;
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50%       { transform: scale(1.4); opacity: 0.4; }
}

/* Chart */
.bd-chart-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  min-height: 0;
}

.bd-svg {
  width: 100%;
  height: 100%;
  max-height: 220px;
  overflow: visible;
}

/* Summary */
.bd-summary {
  padding: 10px 16px 4px;
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 12px;
  color: var(--wi-on-surface, rgba(10,10,10,0.7));
  letter-spacing: 0.3px;
  line-height: 1.5;
  border-top: 1px solid var(--wi-outline-variant, rgba(10,10,10,0.05));
  flex-shrink: 0;
}

/* Topics */
.bd-topics {
  padding: 4px 16px 10px;
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 10px;
  color: var(--wi-on-surface-variant, rgba(10,10,10,0.45));
  letter-spacing: 0.5px;
  flex-shrink: 0;
}
</style>
