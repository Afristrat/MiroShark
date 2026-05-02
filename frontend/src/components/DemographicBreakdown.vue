<template>
  <div class="demographic-breakdown">
    <!-- Header -->
    <div class="demo-header">
      <div class="demo-title">
        <span class="demo-icon">◇</span>
        <span class="demo-label">{{ $t('charts.demographic.title').toUpperCase() }}</span>
      </div>
      <div class="demo-header-actions">
        <span v-if="meta" class="demo-meta">
          {{ meta.agents_with_stance }}/{{ meta.total_agents }} agents with belief data
        </span>
        <button
          class="demo-export-btn"
          :disabled="!hasData"
          @click="refresh"
          :title="$t('common.retry')"
        >
          ↻ {{ $t('common.retry') }}
        </button>
      </div>
    </div>

    <!-- Tab bar -->
    <div v-if="hasData" class="demo-tabs">
      <button
        v-for="tab in availableTabs"
        :key="tab.key"
        class="demo-tab"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
        <span class="demo-tab-count">{{ tabSegmentCount(tab.key) }}</span>
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="demo-state">
      <div class="pulse-ring"></div>
      <span>{{ $t('charts.common.loading') }}</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="demo-state demo-error-state">{{ error }}</div>

    <!-- No data -->
    <div v-else-if="!hasData" class="demo-state">
      <span>{{ $t('charts.demographic.noData') }}</span>
      <span class="demo-hint">{{ $t('charts.demographic.subtitle') }}</span>
    </div>

    <!-- Main content -->
    <div v-else class="demo-content">
      <!-- Top divergence callout -->
      <div v-if="topDivergence" class="demo-highlight">
        <span class="demo-highlight-label">KEY SUBGROUP DYNAMIC</span>
        <span class="demo-highlight-text">{{ topDivergence.headline }}</span>
      </div>
      <div v-else-if="meta && !meta.has_trajectory" class="demo-highlight demo-highlight-muted">
        <span class="demo-highlight-label">NOTICE</span>
        <span class="demo-highlight-text">
          This simulation has no belief trajectory — stance comparisons will be
          unavailable, but counts and influence remain accurate.
        </span>
      </div>

      <!-- Legend -->
      <div class="demo-legend">
        <span class="legend-item"><span class="legend-dot bullish-dot"></span>Bullish</span>
        <span class="legend-item"><span class="legend-dot neutral-dot"></span>Neutral</span>
        <span class="legend-item"><span class="legend-dot bearish-dot"></span>Bearish</span>
        <span class="legend-sep">·</span>
        <span class="legend-item">Stance mean: -1 ↔ +1</span>
      </div>

      <!-- Segment list for active tab -->
      <div class="demo-segments">
        <div
          v-for="segment in activeSegments"
          :key="segment.label"
          class="demo-row"
        >
          <div class="demo-row-head">
            <span class="demo-row-label">{{ formatSegmentLabel(segment.label) }}</span>
            <span class="demo-row-count">{{ segment.count }} agent{{ segment.count === 1 ? '' : 's' }}</span>
          </div>

          <!-- Stance distribution bar -->
          <div class="stance-bar" v-if="hasStanceData(segment)">
            <div
              class="stance-seg stance-bullish"
              :style="{ width: segment.bullish_pct + '%' }"
              :title="`Bullish: ${segment.bullish_pct}%`"
            ></div>
            <div
              class="stance-seg stance-neutral"
              :style="{ width: segment.neutral_pct + '%' }"
              :title="`Neutral: ${segment.neutral_pct}%`"
            ></div>
            <div
              class="stance-seg stance-bearish"
              :style="{ width: segment.bearish_pct + '%' }"
              :title="`Bearish: ${segment.bearish_pct}%`"
            ></div>
          </div>
          <div v-else class="stance-bar stance-empty"></div>

          <!-- Metrics row -->
          <div class="demo-metrics">
            <span class="metric">
              <span class="metric-label">mean</span>
              <span class="metric-value" :class="stanceClass(segment.final_stance_mean)">
                {{ formatStance(segment.final_stance_mean) }}
              </span>
            </span>
            <span class="metric">
              <span class="metric-label">σ</span>
              <span class="metric-value">{{ formatNumber(segment.final_stance_std) }}</span>
            </span>
            <span class="metric">
              <span class="metric-label">volatility</span>
              <span class="metric-value">{{ formatNumber(segment.stance_volatility) }}</span>
            </span>
            <span class="metric">
              <span class="metric-label">influence</span>
              <span class="metric-value">{{ formatInfluence(segment.influence_mean) }}</span>
            </span>
          </div>
        </div>
      </div>

      <!-- Footer hint -->
      <div class="demo-footer-hint">
        Stance values average each agent's final belief across tracked topics
        (-1 bearish → +1 bullish). Volatility is the mean absolute change from
        round 0 to the final round.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDemographicBreakdown } from '../api/simulation'

const { t } = useI18n()

const props = defineProps({
  simulationId: { type: String, required: true },
  visible: { type: Boolean, default: false },
})

const loading = ref(false)
const error = ref('')
const payload = ref(null)
const activeTab = ref('by_age_range')

const TABS = [
  { key: 'by_age_range', label: 'Age' },
  { key: 'by_gender', label: 'Gender' },
  { key: 'by_country', label: 'Country' },
  { key: 'by_archetype', label: 'Actor type' },
  { key: 'by_platform', label: 'Platform' },
]

const hasData = computed(() => !!payload.value?.dimensions)
const meta = computed(() => payload.value?.meta || null)
const topDivergence = computed(() => payload.value?.top_divergence || null)

const availableTabs = computed(() => {
  if (!hasData.value) return []
  return TABS.filter(t => {
    const dim = payload.value.dimensions[t.key]
    return dim && Object.keys(dim).length > 0
  })
})

const tabSegmentCount = (key) => {
  if (!hasData.value) return 0
  const dim = payload.value.dimensions[key]
  return dim ? Object.keys(dim).length : 0
}

const activeSegments = computed(() => {
  if (!hasData.value) return []
  const dim = payload.value.dimensions[activeTab.value] || {}
  return Object.entries(dim).map(([label, data]) => ({ label, ...data }))
})

const hasStanceData = (segment) =>
  (segment.bullish_pct + segment.neutral_pct + segment.bearish_pct) > 0

const formatSegmentLabel = (raw) => {
  if (!raw) return 'unknown'
  const map = {
    unknown: 'Unknown',
    individual: 'Individual',
    institutional: 'Institutional',
    inactive: 'Inactive',
    male: 'Male',
    female: 'Female',
    other: 'Other',
    twitter: 'X / Twitter',
    reddit: 'Reddit',
    polymarket: 'Polymarket',
  }
  return map[raw] || raw
}

const formatStance = (v) => {
  if (v === null || v === undefined) return '—'
  const sign = v > 0 ? '+' : ''
  return sign + v.toFixed(2)
}

const formatNumber = (v) => {
  if (v === null || v === undefined) return '—'
  return v.toFixed(2)
}

const formatInfluence = (v) => {
  if (v === null || v === undefined) return '—'
  return v.toFixed(0)
}

const stanceClass = (v) => {
  if (v === null || v === undefined) return ''
  if (v > 0.1) return 'stance-val-bullish'
  if (v < -0.1) return 'stance-val-bearish'
  return 'stance-val-neutral'
}

const load = async (opts = {}) => {
  if (!props.simulationId) return
  loading.value = true
  error.value = ''
  try {
    const res = await getDemographicBreakdown(props.simulationId, opts)
    if (res.success && res.data) {
      payload.value = res.data
      const first = availableTabs.value[0]
      if (first && !availableTabs.value.find(t => t.key === activeTab.value)) {
        activeTab.value = first.key
      }
    } else if (res.success && !res.data) {
      payload.value = null
    } else {
      error.value = res.error || 'Failed to load demographic breakdown.'
    }
  } catch (err) {
    error.value = err.message || 'Failed to load demographic breakdown.'
  } finally {
    loading.value = false
  }
}

const refresh = () => load({ refresh: true })

watch(() => props.visible, (val) => { if (val) load() })
watch(() => props.simulationId, () => { if (props.visible) load() })
onMounted(() => { if (props.visible) load() })
</script>

<style scoped>
.demographic-breakdown {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  font-family: var(--wi-font-body, var(--font-mono));
  background: var(--wi-surface, var(--background));
  color: var(--wi-on-surface, var(--foreground));
}

.demo-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--wi-outline-variant, rgba(10,10,10,0.08));
  flex-shrink: 0;
}

.demo-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.demo-icon {
  /* US-053 WI : primary terracotta (sub-groupes / segments) */
  color: var(--wi-primary, var(--ms-status-pink));
  font-size: 14px;
}

.demo-label {
  font-family: var(--wi-font-heading, var(--font-mono));
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant, rgba(10,10,10,0.5));
}

.demo-header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.demo-meta {
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 10px;
  letter-spacing: 1px;
  color: var(--wi-on-surface-variant, rgba(10,10,10,0.45));
}

.demo-export-btn {
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

.demo-export-btn:hover:not(:disabled) {
  border-color: var(--wi-primary, var(--ms-status-pink));
  color: var(--wi-primary, var(--ms-status-pink));
  background: var(--wi-surface-container, transparent);
}

.demo-export-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.demo-tabs {
  display: flex;
  gap: 0;
  padding: 0 12px;
  border-bottom: 1px solid var(--wi-outline-variant, rgba(10,10,10,0.05));
  flex-shrink: 0;
  overflow-x: auto;
}

.demo-tab {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 10px 14px;
  font-family: var(--wi-font-heading, var(--font-mono));
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant, rgba(10,10,10,0.4));
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.demo-tab:hover {
  color: var(--wi-on-surface, rgba(10,10,10,0.7));
}

.demo-tab.active {
  /* US-053 WI : tab actif primary terracotta */
  color: var(--wi-primary, var(--ms-status-pink));
  border-bottom-color: var(--wi-primary, var(--ms-status-pink));
}

.demo-tab-count {
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 9px;
  opacity: 0.6;
  background: var(--wi-surface-container, rgba(10,10,10,0.06));
  padding: 2px 7px;
  border-radius: var(--wi-radius-pill, 8px);
  letter-spacing: 0;
}

.demo-tab.active .demo-tab-count {
  background: color-mix(in srgb, var(--wi-primary, var(--ms-status-pink)) 12%, transparent);
  color: var(--wi-primary, var(--ms-status-pink));
  opacity: 1;
}

.demo-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 8px;
  color: var(--wi-on-surface-variant, rgba(10,10,10,0.45));
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 12px;
  letter-spacing: 1px;
}

/* US-053 WI : error sur token --wi-error */
.demo-error-state {
  color: var(--wi-error, var(--ms-status-danger));
}

.demo-hint {
  font-size: 10px;
  color: var(--wi-on-surface-variant, rgba(10,10,10,0.4));
}

.pulse-ring {
  width: 24px;
  height: 24px;
  /* US-053 WI : ring primary terracotta */
  border: 2px solid color-mix(in srgb, var(--wi-primary, var(--ms-status-pink)) 15%, transparent);
  border-top-color: var(--wi-primary, var(--ms-status-pink));
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* @keyframes spin factorisé dans styles/components.css */

.demo-content {
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  flex: 1;
  padding: 12px 16px 16px;
  gap: 14px;
}

.demo-highlight {
  /* US-053 WI : highlight primary soft, border-left terracotta */
  background: var(--wi-primary-soft, rgba(236,72,153,0.06));
  border-left: 3px solid var(--wi-primary, var(--ms-status-pink));
  border-radius: var(--wi-radius-md, 0);
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.demo-highlight-muted {
  background: var(--wi-surface-container-low, rgba(10,10,10,0.04));
  border-left-color: var(--wi-outline, rgba(10,10,10,0.2));
}

.demo-highlight-label {
  font-family: var(--wi-font-heading, var(--font-mono));
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 2px;
  color: var(--wi-primary, var(--ms-status-pink));
  text-transform: uppercase;
}

.demo-highlight-muted .demo-highlight-label {
  color: var(--wi-on-surface-variant, rgba(10,10,10,0.4));
}

.demo-highlight-text {
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 12px;
  color: var(--wi-on-surface, rgba(10,10,10,0.8));
  line-height: 1.5;
}

.demo-legend {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  font-family: var(--wi-font-heading, var(--font-mono));
  font-size: 11px;
  color: var(--wi-on-surface-variant, rgba(10,10,10,0.45));
  letter-spacing: 0.5px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px 3px 8px;
  background: var(--wi-surface-container-low, transparent);
  border-radius: var(--wi-radius-pill, 9999px);
  font-weight: 600;
  color: var(--wi-on-surface, rgba(10,10,10,0.7));
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

/* US-053 WI : bullish=mint (trust), neutral=outline, bearish=terracotta */
.bullish-dot { background: var(--wi-secondary, var(--ms-status-success)); opacity: 0.9; }
.neutral-dot { background: var(--wi-outline, var(--ms-chart-9)); opacity: 0.85; }
.bearish-dot { background: var(--wi-on-primary-container, var(--ms-status-danger)); opacity: 0.9; }

.legend-sep {
  color: var(--wi-outline-variant, rgba(10,10,10,0.15));
  background: transparent;
  padding: 0;
}

.demo-segments {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.demo-row {
  padding: 12px 14px;
  background: var(--wi-surface-container-low, rgba(10,10,10,0.02));
  border: 1px solid var(--wi-outline-variant, rgba(10,10,10,0.04));
  border-radius: var(--wi-radius-md, 0);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.demo-row-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.demo-row-label {
  font-family: var(--wi-font-heading, var(--font-mono));
  font-size: 13px;
  font-weight: 600;
  color: var(--wi-on-surface, rgba(10,10,10,0.85));
  letter-spacing: 0.3px;
}

.demo-row-count {
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 10px;
  color: var(--wi-on-surface-variant, rgba(10,10,10,0.45));
  letter-spacing: 1px;
}

.stance-bar {
  display: flex;
  height: 10px;
  background: var(--wi-surface-container, rgba(10,10,10,0.04));
  border-radius: var(--wi-radius-pill, 2px);
  overflow: hidden;
}

.stance-bar.stance-empty {
  opacity: 0.4;
}

.stance-seg {
  height: 100%;
  transition: width 0.25s ease;
}

/* US-053 WI : bullish=mint, neutral=outline, bearish=terracotta */
.stance-bullish { background: color-mix(in srgb, var(--wi-secondary, var(--ms-status-success)) 80%, transparent); }
.stance-neutral { background: color-mix(in srgb, var(--wi-outline, var(--ms-chart-9)) 55%, transparent); }
.stance-bearish { background: color-mix(in srgb, var(--wi-on-primary-container, var(--ms-status-danger)) 80%, transparent); }

.demo-metrics {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  padding-top: 2px;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 56px;
}

.metric-label {
  font-family: var(--wi-font-heading, var(--font-mono));
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant, rgba(10,10,10,0.45));
}

.metric-value {
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 13px;
  font-weight: 600;
  color: var(--wi-on-surface, rgba(10,10,10,0.85));
  letter-spacing: 0.5px;
}

/* US-053 WI : stance values cohérents avec stance-seg */
.stance-val-bullish { color: var(--wi-secondary, var(--ms-status-success-strong)); }
.stance-val-bearish { color: var(--wi-on-primary-container, var(--ms-status-danger-strong)); }
.stance-val-neutral { color: var(--wi-outline, var(--ms-chart-9)); }

.demo-footer-hint {
  font-family: var(--wi-font-body, var(--font-mono));
  font-size: 10px;
  color: var(--wi-on-surface-variant, rgba(10,10,10,0.45));
  line-height: 1.6;
  border-top: 1px solid var(--wi-outline-variant, rgba(10,10,10,0.05));
  padding-top: 10px;
  margin-top: 4px;
}
</style>
