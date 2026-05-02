<template>
  <div class="what-if">
    <!-- Header -->
    <div class="wi-header">
      <div class="wi-title">
        <span class="wi-icon">◐</span>
        <span class="wi-label">{{ $t('panels.whatIf.title').toUpperCase() }}</span>
      </div>
      <div class="wi-header-actions">
        <button
          class="wi-export-btn"
          :disabled="!hasChartData || exporting || !copySupported"
          :title="copySupported ? 'Copy chart as PNG (with Bassira watermark)' : 'Image copy not supported in this browser'"
          @click="copyChart"
        >
          {{ copiedFlash ? $t('embed.copied') : $t('embed.copy') }}
        </button>
        <button
          class="wi-export-btn"
          :disabled="!hasChartData || exporting"
          @click="downloadChart"
          title="Download chart as PNG (with Bassira watermark)"
        >
          Download ↓
        </button>
      </div>
    </div>

    <div class="wi-hint">
      Pick up to {{ MAX_PICKS }} agents to remove, then recompute to see how
      consensus would have shifted. Uses existing trajectory data — no re-run.
    </div>

    <!-- Loading agents -->
    <div v-if="agentsLoading" class="wi-state">
      <div class="pulse-ring"></div>
      <span>{{ $t('simulation.interaction.loading') }}</span>
    </div>

    <!-- No agents -->
    <div v-else-if="!agents.length" class="wi-state">
      <span>{{ $t('charts.influence.noData') }}</span>
    </div>

    <template v-else>
      <!-- Agent picker row -->
      <div class="wi-picker">
        <div class="wi-picker-header">
          <span class="wi-picker-title">Top agents by influence</span>
          <button
            v-if="selectedNames.length"
            class="wi-clear"
            @click="clearSelection"
          >Clear ({{ selectedNames.length }})</button>
        </div>
        <div class="wi-agent-grid">
          <label
            v-for="a in agents"
            :key="a.agent_name"
            class="wi-agent-card"
            :class="{
              selected: selectedSet.has(a.agent_name),
              disabled: !selectedSet.has(a.agent_name) && selectedNames.length >= MAX_PICKS
            }"
          >
            <input
              type="checkbox"
              class="wi-check"
              :checked="selectedSet.has(a.agent_name)"
              :disabled="!selectedSet.has(a.agent_name) && selectedNames.length >= MAX_PICKS"
              @change="toggleAgent(a.agent_name)"
            />
            <span class="wi-rank">#{{ a.rank }}</span>
            <span class="wi-agent-name">{{ a.agent_name }}</span>
            <span class="wi-agent-score">{{ a.influence_score }}</span>
          </label>
        </div>
        <div class="wi-actions">
          <button
            class="wi-recompute"
            :disabled="!selectedNames.length || computing"
            @click="compute"
          >
            <span v-if="computing" class="wi-spinner"></span>
            {{ computing ? 'Recomputing...' : 'Recompute counterfactual' }}
          </button>
        </div>
      </div>

      <!-- Error -->
      <div v-if="error" class="wi-state wi-error">{{ error }}</div>

      <!-- Chart + summary -->
      <div v-if="hasChartData" class="wi-result">
        <div class="wi-chart-wrap">
          <svg
            :viewBox="`0 0 ${W} ${H}`"
            preserveAspectRatio="xMidYMid meet"
            class="wi-svg"
            ref="svgRef"
            xmlns="http://www.w3.org/2000/svg"
          >
            <!-- Grid -->
            <g v-for="pct in [0, 25, 50, 75, 100]" :key="'g' + pct">
              <line
                :x1="ML" :y1="yS(pct)"
                :x2="W - MR" :y2="yS(pct)"
                stroke="var(--wi-outline-variant)" stroke-width="1"
              />
              <text
                :x="ML - 5" :y="yS(pct) + 4"
                fill="var(--wi-on-surface-variant)" font-size="9"
                font-family="var(--ms-font-mono)" text-anchor="end"
              >{{ pct }}%</text>
            </g>

            <!-- 50% consensus line -->
            <line
              :x1="ML" :y1="yS(50)"
              :x2="W - MR" :y2="yS(50)"
              stroke="var(--wi-outline)" stroke-width="1"
              stroke-dasharray="2,3"
            />

            <!-- Original bullish curve (muted, dashed) -->
            <path
              :d="originalPath"
              fill="none"
              stroke="var(--wi-outline)"
              stroke-width="1.5"
              stroke-dasharray="5,3"
            />

            <!-- Counterfactual bullish curve (terracotta, solid highlight) -->
            <path
              :d="counterfactualPath"
              fill="none"
              stroke="var(--wi-on-primary-container)"
              stroke-width="2.2"
            />

            <!-- Endpoint dots -->
            <circle
              v-if="origEnd"
              :cx="origEnd.x" :cy="origEnd.y"
              r="3"
              fill="var(--wi-outline)"
            />
            <circle
              v-if="cfEnd"
              :cx="cfEnd.x" :cy="cfEnd.y"
              r="4"
              fill="var(--wi-on-primary-container)"
              stroke="var(--wi-bg)" stroke-width="1.5"
            />

            <!-- Consensus markers — orig in gray, cf in green (design bicolor) -->
            <g v-if="origData?.consensus_round != null">
              <line
                :x1="xS(origData.consensus_round)" :y1="MT"
                :x2="xS(origData.consensus_round)" :y2="H - MB"
                stroke="var(--wi-outline)" stroke-width="1"
                stroke-dasharray="3,3"
              />
              <text
                :x="xS(origData.consensus_round) + 4" :y="MT + 10"
                fill="var(--wi-on-surface-variant)" font-size="9"
                font-family="var(--ms-font-mono)"
              >orig r{{ origData.consensus_round }}</text>
            </g>
            <g v-if="cfData?.consensus_round != null && cfData.consensus_round !== origData?.consensus_round">
              <line
                :x1="xS(cfData.consensus_round)" :y1="MT"
                :x2="xS(cfData.consensus_round)" :y2="H - MB"
                stroke="var(--wi-secondary)" stroke-width="1.2"
                stroke-dasharray="3,3"
              />
              <text
                :x="xS(cfData.consensus_round) + 4" :y="MT + 22"
                fill="var(--wi-secondary)" font-size="9"
                font-family="var(--ms-font-mono)"
              >cf r{{ cfData.consensus_round }}</text>
            </g>

            <!-- X axis -->
            <text
              v-for="r in xTicks"
              :key="'xt' + r"
              :x="xS(r)" :y="H - MB + 13"
              fill="var(--wi-on-surface-variant)" font-size="9"
              font-family="var(--ms-font-mono)" text-anchor="middle"
            >{{ r }}</text>
            <text
              :x="ML + (W - ML - MR) / 2" :y="H - 2"
              fill="var(--wi-outline)" font-size="9"
              font-family="var(--ms-font-mono)" text-anchor="middle"
            >Round — bullish %</text>
          </svg>

          <div class="wi-legend">
            <span class="wi-legend-item">
              <span class="wi-legend-swatch orig"></span>
              Original ({{ origData?.agent_count ?? '–' }} agents)
            </span>
            <span class="wi-legend-item">
              <span class="wi-legend-swatch cf"></span>
              Counterfactual ({{ cfData?.agent_count ?? '–' }} agents)
            </span>
          </div>
        </div>

        <!-- Impact summary -->
        <div class="wi-impact">
          <div class="wi-impact-row">
            <span class="wi-impact-label">Final bullish share</span>
            <span class="wi-impact-values">
              <span class="wi-val orig">{{ fmtPct(origData?.final_bullish_pct) }}</span>
              <span class="wi-arrow">→</span>
              <span class="wi-val cf">{{ fmtPct(cfData?.final_bullish_pct) }}</span>
              <span
                v-if="result?.delta_final_bullish != null"
                class="wi-delta"
                :class="deltaClass(result.delta_final_bullish)"
              >{{ fmtDelta(result.delta_final_bullish) }} pts</span>
            </span>
          </div>
          <div class="wi-impact-row">
            <span class="wi-impact-label">Consensus round</span>
            <span class="wi-impact-values">
              <span class="wi-val orig">{{ fmtRound(origData?.consensus_round) }}</span>
              <span class="wi-arrow">→</span>
              <span class="wi-val cf">{{ fmtRound(cfData?.consensus_round) }}</span>
              <span
                v-if="result?.delta_consensus_round != null"
                class="wi-delta"
                :class="deltaClass(result.delta_consensus_round, true)"
              >{{ fmtDelta(result.delta_consensus_round) }} rounds</span>
            </span>
          </div>
          <div v-if="result?.impact" class="wi-impact-badge-row">
            <span
              class="wi-impact-badge"
              :class="'impact-' + result.impact"
            >{{ impactLabel(result.impact) }} influence</span>
          </div>
          <div v-if="result?.summary" class="wi-summary">
            {{ result.summary }}
          </div>
          <div v-if="result?.excluded_unresolved?.length" class="wi-warn">
            Couldn't match: {{ result.excluded_unresolved.join(', ') }}
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { getInfluenceLeaderboard, getCounterfactualDrift } from '../api/simulation'

const { t } = useI18n()
import {
  renderSvgToCanvas,
  downloadCanvas,
  copyCanvasToClipboard,
  canCopyImageToClipboard,
  buildTitledHeader,
} from '../utils/chartExport'

const props = defineProps({
  simulationId: { type: String, required: true },
  visible: { type: Boolean, default: false }
})

const MAX_PICKS = 3
const TOP_AGENTS = 12

const agents = ref([])
const agentsLoading = ref(false)
const selectedNames = ref([])
const selectedSet = computed(() => new Set(selectedNames.value))

const result = ref(null)
const computing = ref(false)
const error = ref('')
const svgRef = ref(null)
const exporting = ref(false)
const copiedFlash = ref(false)
let copiedFlashTimer = null
const copySupported = canCopyImageToClipboard()

// SVG dimensions
const W = 560
const H = 220
const MT = 14
const MB = 26
const ML = 34
const MR = 12

const origData = computed(() => result.value?.original || null)
const cfData = computed(() => result.value?.counterfactual || null)

const hasChartData = computed(() =>
  !!(origData.value?.rounds?.length && cfData.value?.rounds?.length)
)

const allRounds = computed(() => {
  const s = new Set()
  ;(origData.value?.rounds || []).forEach((r) => s.add(r))
  ;(cfData.value?.rounds || []).forEach((r) => s.add(r))
  return Array.from(s).sort((a, b) => a - b)
})

const minR = computed(() => allRounds.value.length ? allRounds.value[0] : 1)
const maxR = computed(() => allRounds.value.length ? allRounds.value[allRounds.value.length - 1] : 10)

const xS = (r) => {
  const span = Math.max(maxR.value - minR.value, 1)
  return ML + ((r - minR.value) / span) * (W - ML - MR)
}

const yS = (pct) => {
  return MT + (1 - pct / 100) * (H - MT - MB)
}

const xTicks = computed(() => {
  const rs = allRounds.value
  if (!rs.length) return []
  if (rs.length <= 10) return rs
  const step = Math.ceil(rs.length / 10)
  return rs.filter((_, i) => i % step === 0 || i === rs.length - 1)
})

const linePath = (rounds, values) => {
  if (!rounds || !rounds.length) return ''
  return rounds.map((r, i) =>
    `${i === 0 ? 'M' : 'L'}${xS(r).toFixed(1)},${yS(values[i]).toFixed(1)}`
  ).join(' ')
}

const originalPath = computed(() => {
  if (!origData.value) return ''
  return linePath(origData.value.rounds, origData.value.bullish)
})

const counterfactualPath = computed(() => {
  if (!cfData.value) return ''
  return linePath(cfData.value.rounds, cfData.value.bullish)
})

const origEnd = computed(() => {
  if (!origData.value?.rounds?.length) return null
  const rs = origData.value.rounds
  const vs = origData.value.bullish
  return { x: xS(rs[rs.length - 1]), y: yS(vs[vs.length - 1]) }
})

const cfEnd = computed(() => {
  if (!cfData.value?.rounds?.length) return null
  const rs = cfData.value.rounds
  const vs = cfData.value.bullish
  return { x: xS(rs[rs.length - 1]), y: yS(vs[vs.length - 1]) }
})

const fmtPct = (v) => (v == null ? '–' : `${v}%`)
const fmtRound = (v) => (v == null ? 'no consensus' : `r${v}`)
const fmtDelta = (v) => {
  if (v == null) return '–'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v}`
}
const deltaClass = (v, invert = false) => {
  if (v == null) return 'neutral'
  const positive = invert ? v < 0 : v > 0
  const negative = invert ? v > 0 : v < 0
  if (positive) return 'positive'
  if (negative) return 'negative'
  return 'neutral'
}
const impactLabel = (kind) => {
  if (kind === 'strong') return 'Strong'
  if (kind === 'moderate') return 'Moderate'
  return 'Minimal'
}

const loadAgents = async () => {
  if (!props.simulationId) return
  agentsLoading.value = true
  try {
    const res = await getInfluenceLeaderboard(props.simulationId)
    if (res?.success && res.data?.agents) {
      agents.value = res.data.agents.slice(0, TOP_AGENTS)
    } else {
      agents.value = []
    }
  } catch {
    agents.value = []
  } finally {
    agentsLoading.value = false
  }
}

const toggleAgent = (name) => {
  const i = selectedNames.value.indexOf(name)
  if (i === -1) {
    if (selectedNames.value.length >= MAX_PICKS) return
    selectedNames.value = [...selectedNames.value, name]
  } else {
    selectedNames.value = selectedNames.value.filter((n) => n !== name)
  }
}

const clearSelection = () => {
  selectedNames.value = []
  result.value = null
}

const compute = async () => {
  if (!selectedNames.value.length) return
  computing.value = true
  error.value = ''
  try {
    const res = await getCounterfactualDrift(props.simulationId, selectedNames.value)
    if (res?.success && res.data) {
      result.value = res.data
    } else if (res?.success && !res.data) {
      error.value = res.message || 'No trajectory data available for this simulation.'
    } else {
      error.value = res?.error || 'Failed to compute counterfactual.'
    }
  } catch (err) {
    error.value = err?.message || 'Failed to compute counterfactual.'
  } finally {
    computing.value = false
  }
}

// ── Chart export (copy + download as PNG, with Bassira watermark) ──

const _buildExportCanvas = () => {
  if (!svgRef.value || !hasChartData.value) {
    throw new Error('No chart to export')
  }
  const removed = selectedNames.value.length
    ? `Removed ${selectedNames.value.join(', ')}`
    : 'Counterfactual drift'
  const deltaStr = result.value?.delta_final_bullish != null
    ? `${result.value.delta_final_bullish >= 0 ? '+' : ''}${result.value.delta_final_bullish} pts on bullish share`
    : null
  const { drawHeader, headerHeight } = buildTitledHeader({
    title: `What If? — ${removed}`,
    subtitle: deltaStr,
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
  if (exporting.value || !hasChartData.value) return
  exporting.value = true
  try {
    const canvas = await _buildExportCanvas()
    await copyCanvasToClipboard(canvas)
    _flashCopied()
  } catch (err) {
    console.warn('[what-if] copy failed, falling back to download:', err)
    try {
      const canvas = await _buildExportCanvas()
      downloadCanvas(canvas, `bassira-whatif-${props.simulationId}.png`)
    } catch (err2) {
      console.error('[what-if] download fallback failed:', err2)
    }
  } finally {
    exporting.value = false
  }
}

async function downloadChart() {
  if (exporting.value || !hasChartData.value) return
  exporting.value = true
  try {
    const canvas = await _buildExportCanvas()
    downloadCanvas(canvas, `bassira-whatif-${props.simulationId}.png`)
  } catch (err) {
    console.error('[what-if] download failed:', err)
  } finally {
    exporting.value = false
  }
}

watch(() => props.visible, (val) => {
  if (val && !agents.value.length) loadAgents()
})
watch(() => props.simulationId, () => {
  if (props.visible) {
    agents.value = []
    selectedNames.value = []
    result.value = null
    loadAgents()
  }
})
onMounted(() => { if (props.visible) loadAgents() })
onBeforeUnmount(() => {
  if (copiedFlashTimer) clearTimeout(copiedFlashTimer)
})
</script>

<style scoped>
/* ── Container — refonte Warm Intelligence ── */
.what-if {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  font-family: var(--wi-font-body);
  background: var(--wi-bg);
  color: var(--wi-on-bg);
}

/* ── Header ── */
.wi-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--wi-space-sm);
  border-bottom: 1px solid var(--wi-outline-variant);
  flex-shrink: 0;
}

.wi-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wi-icon {
  font-size: 14px;
  color: var(--wi-on-primary-container);
}

.wi-label {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-label-sm);
  font-weight: var(--wi-label-sm-weight);
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
}

/* Header action cluster */
.wi-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ── Export button ── */
.wi-export-btn {
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
  color: var(--wi-on-surface-variant);
  padding: 6px 12px;
  border-radius: var(--wi-radius-pill);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 1px;
  cursor: pointer;
  transition: background var(--ms-transition-fast), border-color var(--ms-transition-fast), color var(--ms-transition-fast);
}
.wi-export-btn:hover:not(:disabled) {
  border-color: var(--wi-on-primary-container);
  color: var(--wi-on-primary-container);
  background: var(--wi-primary-container-soft);
}
.wi-export-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.wi-hint {
  padding: 8px var(--wi-space-sm);
  font-size: var(--wi-caption);
  line-height: 1.5;
  color: var(--wi-on-surface-variant);
  border-bottom: 1px solid var(--wi-outline-variant);
  letter-spacing: 0.3px;
}

/* ── States ── */
.wi-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  text-align: center;
  color: var(--wi-outline);
  font-size: var(--wi-body-md);
  letter-spacing: 1px;
}
.wi-state.wi-error { color: var(--wi-error); }

.pulse-ring {
  width: 20px;
  height: 20px;
  border: 2px solid var(--wi-on-primary-container);
  border-radius: 50%;
  animation: wi-pulse 1.2s ease-in-out infinite;
}
@keyframes wi-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.4); opacity: 0.4; }
}

.wi-picker {
  padding: var(--wi-space-sm);
  border-bottom: 1px solid var(--wi-outline-variant);
}

.wi-picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.wi-picker-title {
  font-size: var(--wi-caption);
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
  font-weight: 600;
}
.wi-clear {
  background: none;
  border: none;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  letter-spacing: 1px;
  color: var(--wi-on-surface-variant);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--wi-radius-sm);
  transition: color var(--ms-transition-fast), background var(--ms-transition-fast);
}
.wi-clear:hover {
  color: var(--wi-on-primary-container);
  background: var(--wi-primary-container-soft);
}

.wi-agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 6px;
}

/* ── Agent card ── */
.wi-agent-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-interactive);
  background: var(--wi-surface);
  cursor: pointer;
  font-size: var(--wi-caption);
  color: var(--wi-on-surface);
  transition: background-color var(--ms-transition-fast), border-color var(--ms-transition-fast);
}
.wi-agent-card:hover:not(.disabled) {
  background: var(--wi-surface-container-low);
  border-color: var(--wi-primary-container-edge);
}
.wi-agent-card.selected {
  background: var(--wi-primary-container-soft);
  border-color: var(--wi-on-primary-container);
  color: var(--wi-on-surface);
}
.wi-agent-card.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.wi-check { margin: 0; cursor: inherit; accent-color: var(--wi-on-primary-container); }

.wi-rank {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  min-width: 24px;
  font-weight: 700;
  font-family: var(--ms-font-mono);
}
.wi-agent-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}
.wi-agent-score {
  font-size: var(--wi-caption);
  color: var(--wi-on-primary-container);
  font-weight: 700;
  font-family: var(--ms-font-mono);
}

.wi-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

/* ── Recompute primary CTA ── */
.wi-recompute {
  background: var(--wi-on-primary-container);
  color: var(--wi-bg);
  border: 1px solid var(--wi-on-primary-container);
  border-radius: var(--wi-radius-interactive);
  padding: 10px 18px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: opacity var(--ms-transition-fast), box-shadow var(--ms-transition-fast);
}
.wi-recompute:hover:not(:disabled) {
  opacity: 0.92;
  box-shadow: var(--wi-shadow-md);
}
.wi-recompute:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.wi-spinner {
  width: 10px;
  height: 10px;
  border: 2px solid var(--wi-primary-container-soft);
  border-top-color: var(--wi-bg);
  border-radius: 50%;
  animation: wi-spin 0.8s linear infinite;
}
@keyframes wi-spin { to { transform: rotate(360deg); } }

.wi-result {
  padding: 12px var(--wi-space-sm) var(--wi-space-sm);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.wi-chart-wrap {
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-md);
  padding: 12px 8px 6px;
}

.wi-svg { width: 100%; height: auto; display: block; }

.wi-legend {
  display: flex;
  gap: 16px;
  padding: 6px 8px 0;
  font-size: var(--wi-caption);
  letter-spacing: 1px;
  color: var(--wi-on-surface-variant);
}
.wi-legend-item { display: inline-flex; align-items: center; gap: 6px; }
.wi-legend-swatch {
  width: 18px;
  height: 2px;
  display: inline-block;
}
.wi-legend-swatch.orig {
  background: repeating-linear-gradient(
    90deg,
    var(--wi-outline) 0,
    var(--wi-outline) 4px,
    transparent 4px,
    transparent 7px
  );
}
.wi-legend-swatch.cf {
  background: var(--wi-on-primary-container);
  height: 3px;
}

/* ── Impact panel ── */
.wi-impact {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-md);
  background: var(--wi-surface);
}

.wi-impact-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--wi-caption);
  gap: 12px;
}
.wi-impact-label {
  color: var(--wi-on-surface-variant);
  letter-spacing: 2px;
  text-transform: uppercase;
  font-size: var(--wi-caption);
  font-weight: 600;
}
.wi-impact-values {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--ms-font-mono);
}
.wi-val.orig { color: var(--wi-on-surface-variant); }
.wi-val.cf { color: var(--wi-on-surface); font-weight: 700; }
.wi-arrow { color: var(--wi-outline); }

/* ── Delta pill ── */
.wi-delta {
  padding: 2px 8px;
  font-size: var(--wi-caption);
  font-weight: 700;
  letter-spacing: 0.5px;
  border: 1px solid transparent;
  border-radius: var(--wi-radius-pill);
}
.wi-delta.positive {
  color: var(--wi-on-primary-container);
  border-color: var(--wi-primary-container-edge);
  background: var(--wi-primary-container-soft);
}
.wi-delta.negative {
  color: var(--wi-on-error-container);
  border-color: var(--wi-on-error-container);
  background: var(--wi-error-container);
}
.wi-delta.neutral {
  color: var(--wi-on-surface-variant);
  border-color: var(--wi-outline-variant);
  background: var(--wi-surface-container-low);
}

.wi-impact-badge-row { margin-top: 4px; }
.wi-impact-badge {
  display: inline-block;
  padding: 4px 12px;
  font-size: var(--wi-caption);
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  border: 1px solid transparent;
  border-radius: var(--wi-radius-pill);
}
.wi-impact-badge.impact-strong {
  color: var(--wi-on-primary-container);
  background: var(--wi-primary-container-soft);
  border-color: var(--wi-primary-container-edge);
}
.wi-impact-badge.impact-moderate {
  color: var(--wi-secondary);
  background: var(--wi-secondary-soft);
  border-color: var(--wi-secondary-edge);
}
.wi-impact-badge.impact-minimal {
  color: var(--wi-on-surface-variant);
  background: var(--wi-surface-container-low);
  border-color: var(--wi-outline-variant);
}

.wi-summary {
  font-size: var(--wi-caption);
  line-height: 1.55;
  color: var(--wi-on-surface);
  padding-top: 8px;
  border-top: 1px solid var(--wi-outline-variant);
  letter-spacing: 0.2px;
}

.wi-warn {
  font-size: var(--wi-caption);
  color: var(--wi-on-primary-container);
  padding-top: 2px;
  letter-spacing: 1px;
}
</style>
