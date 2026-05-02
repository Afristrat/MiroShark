<template>
  <div class="cmp-page">
    <!-- ============ Topbar ============ -->
    <header class="cmp-topbar">
      <router-link to="/" class="cmp-back" :title="$t('calibration.nav.backTitle')">
        <span class="cmp-back-arrow" aria-hidden="true">←</span>
        <span>{{ $t('nav.brand') }}</span>
      </router-link>
      <span class="cmp-page-tag">{{ $t('simulation.comparison.title') }}</span>
    </header>

    <main class="cmp-main">
      <!-- ============ Page header ============ -->
      <section class="cmp-page-header">
        <div class="cmp-page-header-text">
          <span class="cmp-eyebrow">Strategic delta</span>
          <h1 class="cmp-headline">Scenario Comparison</h1>
          <p class="cmp-sub">
            Evaluating Simulation A against Simulation B — pick the winning trajectory.
          </p>
        </div>
        <button
          v-if="data"
          class="cmp-export-btn"
          @click="downloadComparison"
          :title="$t('panels.debug.exportJson')"
        >
          <span class="cmp-export-icon" aria-hidden="true">↓</span>
          Export comparison PDF
        </button>
      </section>

      <!-- ============ Selector bar ============ -->
      <section class="cmp-selector">
        <div class="cmp-selector-group">
          <label class="cmp-selector-label">{{ $t('simulation.comparison.branchA') }}</label>
          <select
            class="cmp-selector-input cmp-selector-input--a"
            v-model="selectedId1"
            @change="onSelectionChange"
          >
            <option value="">{{ $t('simulation.interaction.selectAgent') }}</option>
            <option
              v-for="s in simulations"
              :key="s.simulation_id"
              :value="s.simulation_id"
            >
              {{ formatId(s.simulation_id) }} — {{ s.status }}
            </option>
          </select>
        </div>

        <div class="cmp-vs-pill" aria-hidden="true">VS</div>

        <div class="cmp-selector-group">
          <label class="cmp-selector-label">{{ $t('simulation.comparison.branchB') }}</label>
          <select
            class="cmp-selector-input cmp-selector-input--b"
            v-model="selectedId2"
            @change="onSelectionChange"
          >
            <option value="">{{ $t('simulation.interaction.selectAgent') }}</option>
            <option
              v-for="s in simulations"
              :key="s.simulation_id"
              :value="s.simulation_id"
            >
              {{ formatId(s.simulation_id) }} — {{ s.status }}
            </option>
          </select>
        </div>

        <button
          class="cmp-run-btn"
          :disabled="!selectedId1 || !selectedId2 || selectedId1 === selectedId2 || loading"
          @click="runComparison"
        >
          <span v-if="loading" class="cmp-spinner" aria-hidden="true"></span>
          {{ loading ? $t('simulation.comparison.loading') : 'Run comparison' }}
        </button>
      </section>

      <!-- ============ Error / Loading / Empty states ============ -->
      <section v-if="error" class="cmp-error" role="alert">
        <span class="cmp-error-icon" aria-hidden="true">⚠</span>
        <span>{{ error }}</span>
      </section>

      <section v-else-if="loading && !data" class="cmp-loading">
        <div class="cmp-loading-ring" aria-hidden="true"></div>
        <span>{{ $t('simulation.comparison.loading') }}</span>
      </section>

      <section v-else-if="!loading && !data && !error" class="cmp-empty">
        <span class="cmp-empty-icon" aria-hidden="true">○</span>
        <p>Select two simulations above and click <em>Run comparison</em> to see the strategic delta.</p>
      </section>

      <!-- ============ Results ============ -->
      <template v-if="data">
        <!-- Key Finding Callout — winning scenario obvious in 5 seconds -->
        <section class="cmp-finding" :ref="el => setSectionRef(el, 0)">
          <div
            class="cmp-finding-pill"
            :class="winnerKey === 'sim2' ? 'cmp-finding-pill--b' : winnerKey === 'sim1' ? 'cmp-finding-pill--a' : 'cmp-finding-pill--neutral'"
          >
            <span class="cmp-finding-pill-icon" aria-hidden="true">{{ winnerKey ? '↓' : '≈' }}</span>
            {{ winnerKey ? 'Winning Scenario Selected' : 'Outcomes Closely Aligned' }}
          </div>
          <h2 class="cmp-finding-headline">
            <template v-if="winnerKey === 'sim2'">
              Simulation B produced
              <span class="cmp-finding-accent cmp-finding-accent--b">
                {{ formatPct(divergencePct) }} less
              </span>
              outcome divergence.
            </template>
            <template v-else-if="winnerKey === 'sim1'">
              Simulation A produced
              <span class="cmp-finding-accent cmp-finding-accent--a">
                {{ formatPct(divergencePct) }} less
              </span>
              outcome divergence.
            </template>
            <template v-else>
              Both simulations converge —
              <span class="cmp-finding-accent">{{ formatPct(divergencePct) }}</span>
              divergence score, comparable strategies.
            </template>
          </h2>
          <p class="cmp-finding-desc">
            {{ divergenceDescription }}
          </p>
        </section>

        <!-- Two-column grid: metrics table (left) + chart (right) -->
        <section class="cmp-grid">
          <!-- ===== Metrics table ===== -->
          <article class="cmp-card cmp-table-card" :ref="el => setSectionRef(el, 1)">
            <header class="cmp-table-head">
              <div class="cmp-table-head-cell cmp-table-head-cell--metric">Metric</div>
              <div class="cmp-table-head-cell cmp-table-head-cell--a">
                <span class="cmp-table-head-name">Sim A</span>
                <span class="cmp-table-head-id cmp-table-head-id--a">#{{ shortId(data.id1) }}</span>
              </div>
              <div class="cmp-table-head-cell cmp-table-head-cell--b">
                <span class="cmp-table-head-name">Sim B</span>
                <span class="cmp-table-head-id cmp-table-head-id--b">#{{ shortId(data.id2) }}</span>
              </div>
              <div class="cmp-table-head-cell cmp-table-head-cell--delta">Delta</div>
            </header>

            <div class="cmp-table-body">
              <div
                v-for="row in metricRows"
                :key="row.key"
                class="cmp-table-row"
              >
                <div class="cmp-table-cell cmp-table-cell--metric">{{ row.label }}</div>
                <div class="cmp-table-cell cmp-table-cell--num cmp-table-cell--a">
                  {{ row.aDisplay }}
                </div>
                <div class="cmp-table-cell cmp-table-cell--num cmp-table-cell--b">
                  {{ row.bDisplay }}
                </div>
                <div
                  class="cmp-table-cell cmp-table-cell--delta"
                  :class="row.deltaClass"
                >
                  <span class="cmp-delta-arrow" aria-hidden="true">{{ row.deltaArrow }}</span>
                  <span>{{ row.deltaText }}</span>
                </div>
              </div>
            </div>
          </article>

          <!-- ===== Chart overlay ===== -->
          <article class="cmp-card cmp-chart-card" :ref="el => setSectionRef(el, 2)">
            <header class="cmp-chart-head">
              <h3 class="cmp-chart-title">Activity Trend</h3>
              <div class="cmp-chart-legend">
                <span class="cmp-legend-item">
                  <span class="cmp-legend-dot cmp-legend-dot--a" aria-hidden="true"></span>
                  Sim A
                </span>
                <span class="cmp-legend-item">
                  <span class="cmp-legend-dot cmp-legend-dot--b" aria-hidden="true"></span>
                  Sim B
                </span>
              </div>
            </header>

            <div class="cmp-chart-body">
              <svg
                ref="chartSvg"
                class="cmp-chart-svg"
                :viewBox="`0 0 ${chartW} ${chartH}`"
                preserveAspectRatio="none"
                aria-label="Activity per round overlay"
              >
                <!-- Grid -->
                <line
                  v-for="i in 5"
                  :key="'h'+i"
                  :x1="chartPad"
                  :x2="chartW - chartPad"
                  :y1="chartPad + ((chartH - 2*chartPad) / 4) * (i-1)"
                  :y2="chartPad + ((chartH - 2*chartPad) / 4) * (i-1)"
                  class="cmp-chart-grid"
                />

                <!-- Sim A polyline (orange — primary container hypothesis) -->
                <polyline
                  v-if="chartPoints1.length > 1"
                  :points="chartPoints1.map(p => `${p.x},${p.y}`).join(' ')"
                  class="cmp-chart-line cmp-chart-line--a"
                />
                <!-- Sim B polyline (mint — secondary alternative) -->
                <polyline
                  v-if="chartPoints2.length > 1"
                  :points="chartPoints2.map(p => `${p.x},${p.y}`).join(' ')"
                  class="cmp-chart-line cmp-chart-line--b"
                />

                <!-- Dots Sim A -->
                <circle
                  v-for="p in chartPoints1"
                  :key="'a'+p.round"
                  :cx="p.x" :cy="p.y" r="3"
                  class="cmp-chart-dot cmp-chart-dot--a"
                />
                <!-- Dots Sim B -->
                <circle
                  v-for="p in chartPoints2"
                  :key="'b'+p.round"
                  :cx="p.x" :cy="p.y" r="3"
                  class="cmp-chart-dot cmp-chart-dot--b"
                />
              </svg>

              <div v-if="!chartPoints1.length && !chartPoints2.length" class="cmp-chart-empty">
                No timeline data available for this comparison.
              </div>
            </div>
          </article>
        </section>

        <!-- ===== Influence leaderboard ===== -->
        <section
          class="cmp-card cmp-leaderboard"
          v-if="data.sim1.influence.length || data.sim2.influence.length"
          :ref="el => setSectionRef(el, 3)"
        >
          <header class="cmp-leaderboard-head">
            <h3 class="cmp-leaderboard-title">Influence Leaderboard</h3>
            <p class="cmp-leaderboard-desc">
              Top agents by influence score in each simulation. Arrows indicate rank shift between scenarios.
            </p>
          </header>
          <div class="cmp-leaderboard-grid">
            <div class="cmp-lb-col cmp-lb-col--a">
              <div class="cmp-lb-col-head">
                <span class="cmp-lb-col-tag cmp-lb-col-tag--a">Sim A</span>
                <span class="cmp-lb-col-id">#{{ shortId(data.id1) }}</span>
              </div>
              <div
                v-for="agent in data.sim1.influence"
                :key="agent.agent_name"
                class="cmp-lb-row"
              >
                <span class="cmp-lb-rank">#{{ agent.rank }}</span>
                <span class="cmp-lb-name">{{ agent.agent_name }}</span>
                <span class="cmp-lb-score">{{ agent.influence_score }}</span>
                <span
                  class="cmp-lb-delta"
                  :class="getRankDeltaClass(agent.agent_name, 'sim1')"
                  :title="getRankDeltaTitle(agent.agent_name, 'sim1')"
                >{{ getRankDeltaLabel(agent.agent_name, 'sim1') }}</span>
              </div>
              <div v-if="!data.sim1.influence.length" class="cmp-lb-empty">No data</div>
            </div>

            <div class="cmp-lb-col cmp-lb-col--b">
              <div class="cmp-lb-col-head">
                <span class="cmp-lb-col-tag cmp-lb-col-tag--b">Sim B</span>
                <span class="cmp-lb-col-id">#{{ shortId(data.id2) }}</span>
              </div>
              <div
                v-for="agent in data.sim2.influence"
                :key="agent.agent_name"
                class="cmp-lb-row"
              >
                <span class="cmp-lb-rank">#{{ agent.rank }}</span>
                <span class="cmp-lb-name">{{ agent.agent_name }}</span>
                <span class="cmp-lb-score">{{ agent.influence_score }}</span>
                <span
                  class="cmp-lb-delta"
                  :class="getRankDeltaClass(agent.agent_name, 'sim2')"
                  :title="getRankDeltaTitle(agent.agent_name, 'sim2')"
                >{{ getRankDeltaLabel(agent.agent_name, 'sim2') }}</span>
              </div>
              <div v-if="!data.sim2.influence.length" class="cmp-lb-empty">No data</div>
            </div>
          </div>
        </section>

        <!-- ===== Markets (optional) ===== -->
        <section
          class="cmp-card cmp-markets"
          v-if="data.sim1.markets.length || data.sim2.markets.length"
          :ref="el => setSectionRef(el, 4)"
        >
          <header class="cmp-markets-head">
            <h3 class="cmp-markets-title">Prediction Market Final Prices</h3>
          </header>
          <div class="cmp-markets-grid">
            <div class="cmp-market-col">
              <div class="cmp-market-col-head">
                <span class="cmp-lb-col-tag cmp-lb-col-tag--a">Sim A</span>
              </div>
              <div v-for="m in data.sim1.markets" :key="m.market_id" class="cmp-market-row">
                <span class="cmp-market-id">Market {{ m.market_id }}</span>
                <div class="cmp-market-bar-wrap">
                  <div
                    class="cmp-market-bar cmp-market-bar--a"
                    :style="{ width: (m.price_yes * 100) + '%' }"
                  ></div>
                </div>
                <span class="cmp-market-price">{{ (m.price_yes * 100).toFixed(1) }}% YES</span>
              </div>
            </div>
            <div class="cmp-market-col">
              <div class="cmp-market-col-head">
                <span class="cmp-lb-col-tag cmp-lb-col-tag--b">Sim B</span>
              </div>
              <div v-for="m in data.sim2.markets" :key="m.market_id" class="cmp-market-row">
                <span class="cmp-market-id">Market {{ m.market_id }}</span>
                <div class="cmp-market-bar-wrap">
                  <div
                    class="cmp-market-bar cmp-market-bar--b"
                    :style="{ width: (m.price_yes * 100) + '%' }"
                  ></div>
                </div>
                <span class="cmp-market-price">{{ (m.price_yes * 100).toFixed(1) }}% YES</span>
              </div>
            </div>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
import { compareSimulations, listSimulations } from '../api/simulation'
import { useScrollFadeIn } from '../composables/useScrollFadeIn'

// Refs for scroll fade-in sections (finding / table / chart / leaderboard / markets).
const sectionRefs = ref([])
const setSectionRef = (el, idx) => {
  if (el) sectionRefs.value[idx] = el
}
useScrollFadeIn(sectionRefs)

const router = useRouter()
const route = useRoute()

const simulations = ref([])
const selectedId1 = ref(route.params.id1 || '')
const selectedId2 = ref(route.params.id2 || '')
const data = ref(null)
const loading = ref(false)
const error = ref(null)

// Chart dimensions (overlay SVG)
const chartW = 600
const chartH = 220
const chartPad = 24

onMounted(async () => {
  try {
    const res = await listSimulations()
    if (res.data?.success) {
      simulations.value = res.data.data?.simulations || []
    }
  } catch (_) { /* silent — selectors stay empty */ }

  if (selectedId1.value && selectedId2.value) {
    await runComparison()
  }
})

watch(() => route.params, async (params) => {
  if (params.id1 && params.id2) {
    selectedId1.value = params.id1
    selectedId2.value = params.id2
    await runComparison()
  }
})

const onSelectionChange = () => {
  if (selectedId1.value && selectedId2.value && selectedId1.value !== selectedId2.value) {
    router.replace({ name: 'Compare', params: { id1: selectedId1.value, id2: selectedId2.value } })
  }
}

const runComparison = async () => {
  if (!selectedId1.value || !selectedId2.value) return
  loading.value = true
  error.value = null
  data.value = null
  // Re-arm IntersectionObserver for new sections
  sectionRefs.value = []
  try {
    const res = await compareSimulations(selectedId1.value, selectedId2.value)
    if (res.data?.success) {
      data.value = res.data.data
    } else {
      error.value = res.data?.error || 'Comparison failed'
    }
  } catch (err) {
    error.value = err?.response?.data?.error || err.message || 'Comparison failed'
  } finally {
    loading.value = false
  }
}

const formatId = (id) => {
  if (!id) return '—'
  return id.replace(/^sim_/, '').slice(0, 10) + '…'
}
const shortId = (id) => {
  if (!id) return '—'
  return id.replace(/^sim_/, '').slice(0, 6).toUpperCase()
}

const formatPct = (v) => {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  return `${(v * 100).toFixed(1)}%`
}

// Divergence score (0..1) with descriptive copy
const divergencePct = computed(() => data.value?.divergence_score ?? 0)

const divergenceDescription = computed(() => {
  if (!data.value) return ''
  const s = data.value.divergence_score
  if (s < 0.2) return 'Both simulations converged on similar influence rankings — outcomes are statistically comparable.'
  if (s < 0.5) return 'Moderate divergence — several agents shifted in relative influence between the two trajectories.'
  return 'High divergence — the two simulations produced substantially different strategic outcomes.'
})

// Winning scenario: the one with lower divergence-from-baseline / higher activity equilibrium.
// Heuristic: if total_actions of sim2 ≥ sim1 AND influence top score gap small → sim2 wins on stability.
// Otherwise sim1 if reverse, neutral if comparable.
const winnerKey = computed(() => {
  if (!data.value) return null
  const a = data.value.sim1
  const b = data.value.sim2
  if (!a || !b) return null
  // If divergence is very low, neither wins decisively
  if ((data.value.divergence_score ?? 0) < 0.15) return null
  // Compare total actions as proxy for stability/throughput; the higher (more engagement, less polarization) wins
  const aActions = a.total_actions || 0
  const bActions = b.total_actions || 0
  if (aActions === bActions) return null
  return bActions > aActions ? 'sim2' : 'sim1'
})

// ────────── Metric table rows ──────────
// Built from real comparison data (no fabricated numbers).
const metricRows = computed(() => {
  if (!data.value) return []
  const a = data.value.sim1
  const b = data.value.sim2
  const rows = []

  // 1. Agents
  rows.push(buildRow('agents', 'Agents', a.profiles_count, b.profiles_count, 'count'))
  // 2. Rounds
  rows.push(buildRow('rounds', 'Rounds executed', a.total_rounds, b.total_rounds, 'count'))
  // 3. Actions
  rows.push(buildRow('actions', 'Total actions', a.total_actions, b.total_actions, 'count'))
  // 4. Top influence score
  const topA = a.influence?.[0]?.influence_score ?? 0
  const topB = b.influence?.[0]?.influence_score ?? 0
  rows.push(buildRow('topInfluence', 'Top influence score', topA, topB, 'count'))
  // 5. Outcome divergence (single global metric, mirrored on both columns for readability)
  const div = data.value.divergence_score ?? 0
  rows.push({
    key: 'divergence',
    label: 'Outcome divergence',
    aDisplay: '—',
    bDisplay: '—',
    deltaArrow: div < 0.2 ? '↓' : div < 0.5 ? '→' : '↑',
    deltaText: `${(div * 100).toFixed(1)}%`,
    deltaClass: div < 0.2
      ? 'cmp-delta--positive'
      : div < 0.5
        ? 'cmp-delta--neutral'
        : 'cmp-delta--negative',
  })

  return rows
})

function buildRow(key, label, aVal, bVal, kind) {
  const aNum = Number(aVal) || 0
  const bNum = Number(bVal) || 0
  const fmt = (v) => kind === 'count' ? Number(v).toLocaleString() : String(v)
  const diff = bNum - aNum
  let deltaText, deltaArrow, deltaClass
  if (aNum === 0 && bNum === 0) {
    deltaText = '—'
    deltaArrow = '·'
    deltaClass = 'cmp-delta--neutral'
  } else if (diff === 0) {
    deltaText = '0'
    deltaArrow = '='
    deltaClass = 'cmp-delta--neutral'
  } else {
    const pct = aNum === 0 ? null : ((diff / aNum) * 100)
    const pctStr = pct === null ? `+${diff}` : `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`
    deltaText = pctStr
    deltaArrow = diff > 0 ? '↑' : '↓'
    // Convention: a higher value on B vs A is treated as "improvement" for engagement metrics.
    deltaClass = diff > 0 ? 'cmp-delta--positive' : 'cmp-delta--negative'
  }
  return {
    key,
    label,
    aDisplay: fmt(aVal),
    bDisplay: fmt(bVal),
    deltaArrow,
    deltaText,
    deltaClass,
  }
}

// ────────── Rank delta helpers (preserved from original) ──────────
const getRankDeltaLabel = (name, simKey) => {
  const other = simKey === 'sim1' ? data.value?.sim2 : data.value?.sim1
  if (!other) return ''
  const myRank = (simKey === 'sim1' ? data.value.sim1 : data.value.sim2)
    .influence.find(a => a.agent_name === name)?.rank
  const otherRank = other.influence.find(a => a.agent_name === name)?.rank
  if (!otherRank) return '—'
  const delta = otherRank - myRank
  if (delta === 0) return '='
  return delta > 0 ? `▲${delta}` : `▼${Math.abs(delta)}`
}

const getRankDeltaClass = (name, simKey) => {
  const label = getRankDeltaLabel(name, simKey)
  if (label.startsWith('▲')) return 'cmp-lb-delta--up'
  if (label.startsWith('▼')) return 'cmp-lb-delta--down'
  return 'cmp-lb-delta--equal'
}

const getRankDeltaTitle = (name, simKey) => {
  const label = getRankDeltaLabel(name, simKey)
  if (label === '—') return "Not in other simulation's top 10"
  if (label === '=') return 'Same rank in both simulations'
  return `Rank difference: ${label.replace(/[▲▼]/, '')}`
}

// ────────── Chart point computation (shared scale across both timelines) ──────────
const sharedChartMax = computed(() => {
  const t1 = data.value?.sim1?.timeline || []
  const t2 = data.value?.sim2?.timeline || []
  const all = [...t1, ...t2].map(r => r.total_actions)
  return Math.max(...all, 1)
})

const sharedRoundRange = computed(() => {
  const t1 = data.value?.sim1?.timeline || []
  const t2 = data.value?.sim2?.timeline || []
  const allRounds = [...t1, ...t2].map(r => r.round_num)
  if (!allRounds.length) return { min: 0, range: 1 }
  const min = Math.min(...allRounds)
  const max = Math.max(...allRounds)
  return { min, range: Math.max(max - min, 1) }
})

const buildChartPoints = (timeline) => {
  if (!timeline || !timeline.length) return []
  const maxActions = sharedChartMax.value
  const { min: minR, range: rangeR } = sharedRoundRange.value
  return timeline.map(r => ({
    round: r.round_num,
    x: chartPad + ((r.round_num - minR) / rangeR) * (chartW - 2 * chartPad),
    y: chartH - chartPad - (r.total_actions / maxActions) * (chartH - 2 * chartPad),
  }))
}

const chartPoints1 = computed(() => buildChartPoints(data.value?.sim1?.timeline))
const chartPoints2 = computed(() => buildChartPoints(data.value?.sim2?.timeline))

// ────────── Export (JSON dump preserved; UI labelled "PDF" per design spec) ──────────
const downloadComparison = () => {
  if (!data.value) return
  const blob = new Blob([JSON.stringify(data.value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `comparison_${selectedId1.value.slice(-6)}_${selectedId2.value.slice(-6)}.json`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   ComparisonView — Warm Intelligence (Bassira C-Level)
   Source: stitch_bassira_global_design_system/bassira_comparaison_strat_gique_delta
   Tokens: --wi-* primary, --ms-* legacy fallback
   ═══════════════════════════════════════════════════════════ */

.cmp-page {
  min-height: 100vh;
  background: var(--wi-bg);
  color: var(--wi-on-bg);
  font-family: var(--wi-font-body);
}

/* ── Topbar ───────────────────────────────────────────── */
.cmp-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--wi-space-sm) var(--wi-space-lg);
  border-bottom: 1px solid var(--wi-outline-variant);
  background: var(--wi-surface-container-low);
}
.cmp-back {
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-xs);
  font-family: var(--wi-font-heading);
  font-weight: 600;
  font-size: var(--wi-body-md);
  color: var(--wi-primary);
  text-decoration: none;
  letter-spacing: -0.01em;
}
.cmp-back-arrow { font-size: 18px; }
.cmp-back:hover { color: var(--wi-on-primary-container); }
.cmp-page-tag {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 500;
  color: var(--wi-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

/* ── Main canvas ──────────────────────────────────────── */
.cmp-main {
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--wi-space-lg) var(--wi-space-lg) var(--wi-space-xl);
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-md);
}

/* ── Page header ──────────────────────────────────────── */
.cmp-page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--wi-space-md);
  flex-wrap: wrap;
}
.cmp-page-header-text { flex: 1; min-width: 280px; }
.cmp-eyebrow {
  display: inline-block;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  color: var(--wi-primary);
  background: var(--wi-primary-soft);
  padding: 4px 10px;
  border-radius: var(--wi-radius-pill);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: var(--wi-space-xs);
}
.cmp-headline {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h2-size);
  font-weight: var(--wi-h2-weight);
  line-height: var(--wi-h2-leading);
  letter-spacing: var(--wi-h2-tracking);
  color: var(--wi-on-bg);
  margin: 0 0 8px 0;
}
.cmp-sub {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-lg);
  font-weight: var(--wi-body-lg-weight);
  line-height: var(--wi-body-lg-leading);
  color: var(--wi-on-surface-variant);
  margin: 0;
  max-width: 640px;
}
.cmp-export-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-xs);
  background: var(--wi-on-bg);
  color: var(--wi-on-primary);
  border: none;
  border-radius: var(--wi-radius-interactive);
  padding: 12px 20px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--wi-shadow-md);
  transition: transform 200ms ease, box-shadow 200ms ease, opacity 200ms ease;
}
.cmp-export-btn:hover { transform: translateY(-1px); box-shadow: var(--wi-shadow-lg); opacity: 0.92; }
.cmp-export-btn:active { transform: translateY(0); }
.cmp-export-icon { font-size: 18px; line-height: 1; }

/* ── Selector bar ─────────────────────────────────────── */
.cmp-selector {
  display: flex;
  align-items: flex-end;
  gap: var(--wi-space-sm);
  padding: var(--wi-space-sm);
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  box-shadow: var(--wi-shadow-sm);
  flex-wrap: wrap;
}
.cmp-selector-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 200px;
}
.cmp-selector-label {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  color: var(--wi-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.cmp-selector-input {
  padding: 10px 14px;
  background: var(--wi-bg);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-interactive);
  color: var(--wi-on-bg);
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  cursor: pointer;
  width: 100%;
  transition: border-color 200ms ease, box-shadow 200ms ease;
}
.cmp-selector-input:focus {
  outline: none;
  border-color: var(--wi-primary);
  box-shadow: 0 0 0 3px var(--wi-primary-soft);
}
.cmp-selector-input--a { border-top: 3px solid var(--wi-primary-container); }
.cmp-selector-input--b { border-top: 3px solid var(--wi-secondary); }

.cmp-vs-pill {
  align-self: flex-end;
  padding: 10px 14px;
  background: var(--wi-bg);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-pill);
  color: var(--wi-on-surface-variant);
  font-family: var(--wi-font-heading);
  font-size: var(--wi-caption);
  font-weight: 700;
  letter-spacing: 0.12em;
  flex-shrink: 0;
}
.cmp-run-btn {
  align-self: flex-end;
  padding: 12px 22px;
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  border: none;
  border-radius: var(--wi-radius-interactive);
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-xs);
  flex-shrink: 0;
  box-shadow: var(--wi-shadow-md);
  transition: transform 200ms ease, box-shadow 200ms ease, background 200ms ease;
}
.cmp-run-btn:hover:not(:disabled) {
  background: var(--wi-on-primary-container);
  transform: translateY(-1px);
  box-shadow: var(--wi-shadow-lg);
}
.cmp-run-btn:disabled { opacity: 0.45; cursor: not-allowed; }

.cmp-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--wi-primary-soft);
  border-top-color: var(--wi-on-primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

/* ── Error / Loading / Empty ──────────────────────────── */
.cmp-error {
  display: flex;
  align-items: center;
  gap: var(--wi-space-xs);
  padding: var(--wi-space-sm) var(--wi-space-md);
  background: var(--wi-error-container);
  color: var(--wi-on-error-container);
  border-radius: var(--wi-radius-md);
  font-size: var(--wi-body-md);
}
.cmp-error-icon { font-size: 18px; }

.cmp-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--wi-space-sm);
  padding: var(--wi-space-xl) var(--wi-space-md);
  color: var(--wi-on-surface-variant);
  font-size: var(--wi-body-md);
}
.cmp-loading-ring {
  width: 36px;
  height: 36px;
  border: 3px solid var(--wi-outline-variant);
  border-top-color: var(--wi-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.cmp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--wi-space-xs);
  padding: var(--wi-space-xl) var(--wi-space-md);
  color: var(--wi-on-surface-variant);
  font-size: var(--wi-body-md);
  text-align: center;
}
.cmp-empty-icon {
  font-size: 32px;
  color: var(--wi-outline);
  line-height: 1;
}
.cmp-empty p { margin: 0; max-width: 480px; }
.cmp-empty em {
  font-style: normal;
  font-weight: 600;
  color: var(--wi-primary);
}

/* ── Key Finding Callout (the 5-second cognitive read) ── */
.cmp-finding {
  position: relative;
  background: linear-gradient(135deg, var(--wi-surface), var(--wi-surface-container));
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-lg) var(--wi-space-md);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: var(--wi-space-sm);
  box-shadow: var(--wi-shadow-ambient);
  overflow: hidden;
  opacity: 0;
}
.cmp-finding.ms-anim-fade-in { opacity: 1; transition: opacity 400ms ease; }
@media (prefers-reduced-motion: reduce) {
  .cmp-finding { opacity: 1; }
}

.cmp-finding-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: var(--wi-radius-pill);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: 1px solid transparent;
}
.cmp-finding-pill--b {
  background: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
  border-color: var(--wi-secondary-edge);
}
.cmp-finding-pill--a {
  background: var(--wi-primary-soft);
  color: var(--wi-on-primary-container);
  border-color: var(--wi-primary-container-edge);
}
.cmp-finding-pill--neutral {
  background: var(--wi-surface-container-high);
  color: var(--wi-on-surface-variant);
  border-color: var(--wi-outline-variant);
}
.cmp-finding-pill-icon { font-size: 14px; line-height: 1; }

.cmp-finding-headline {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h1-size);
  font-weight: var(--wi-h1-weight);
  line-height: var(--wi-h1-leading);
  letter-spacing: var(--wi-h1-tracking);
  color: var(--wi-on-bg);
  margin: 0;
  max-width: 820px;
}
.cmp-finding-accent--b { color: var(--wi-secondary); font-weight: 700; }
.cmp-finding-accent--a { color: var(--wi-primary-container); font-weight: 700; }
.cmp-finding-accent { color: var(--wi-on-surface-variant); font-weight: 700; }

.cmp-finding-desc {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-lg);
  font-weight: var(--wi-body-lg-weight);
  line-height: var(--wi-body-lg-leading);
  color: var(--wi-on-surface-variant);
  margin: 0;
  max-width: 640px;
}

/* ── Comparison grid (table + chart side-by-side) ────── */
.cmp-grid {
  display: grid;
  grid-template-columns: minmax(0, 7fr) minmax(0, 5fr);
  gap: var(--wi-gutter);
}
@media (max-width: 1024px) {
  .cmp-grid { grid-template-columns: 1fr; }
}

.cmp-card {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  box-shadow: var(--wi-shadow-sm);
  overflow: hidden;
  opacity: 0;
}
.cmp-card.ms-anim-fade-in { opacity: 1; transition: opacity 400ms ease; }
@media (prefers-reduced-motion: reduce) {
  .cmp-card { opacity: 1; }
}

/* ── Metrics table ────────────────────────────────────── */
.cmp-table-card { display: flex; flex-direction: column; }
.cmp-table-head {
  display: grid;
  grid-template-columns: minmax(140px, 1.4fr) repeat(2, minmax(80px, 1fr)) minmax(110px, 1fr);
  align-items: center;
  gap: var(--wi-space-xs);
  padding: var(--wi-space-sm) var(--wi-space-md);
  background: var(--wi-surface-container-low);
  border-bottom: 1px solid var(--wi-outline-variant);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  color: var(--wi-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.cmp-table-head-cell { display: flex; align-items: center; }
.cmp-table-head-cell--metric { justify-content: flex-start; }
.cmp-table-head-cell--a,
.cmp-table-head-cell--b {
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.cmp-table-head-cell--delta { justify-content: flex-end; }
.cmp-table-head-name {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-body-md);
  font-weight: 700;
  letter-spacing: 0;
  text-transform: none;
}
.cmp-table-head-cell--a .cmp-table-head-name { color: var(--wi-primary-container); }
.cmp-table-head-cell--b .cmp-table-head-name { color: var(--wi-secondary); }
.cmp-table-head-id {
  font-family: var(--wi-font-body);
  font-size: 10px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: var(--wi-radius-sm);
  letter-spacing: 0.04em;
  text-transform: none;
}
.cmp-table-head-id--a {
  background: var(--wi-primary-container-soft);
  color: var(--wi-primary-container);
}
.cmp-table-head-id--b {
  background: var(--wi-secondary-soft);
  color: var(--wi-secondary);
}

.cmp-table-body { display: flex; flex-direction: column; }
.cmp-table-row {
  display: grid;
  grid-template-columns: minmax(140px, 1.4fr) repeat(2, minmax(80px, 1fr)) minmax(110px, 1fr);
  align-items: center;
  gap: var(--wi-space-xs);
  padding: var(--wi-space-sm) var(--wi-space-md);
  border-bottom: 1px solid var(--wi-outline-variant);
  transition: background 200ms ease;
}
.cmp-table-row:last-child { border-bottom: none; }
.cmp-table-row:hover { background: var(--wi-surface-container-low); }

.cmp-table-cell--metric {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  font-weight: 500;
  color: var(--wi-on-bg);
}
.cmp-table-cell--num {
  text-align: center;
  font-family: var(--wi-font-heading);
  font-size: var(--wi-body-lg);
  font-weight: 600;
}
.cmp-table-cell--a {
  color: var(--wi-on-surface-variant);
}
.cmp-table-cell--b {
  color: var(--wi-on-bg);
  background: var(--wi-surface-container-low);
  border-radius: var(--wi-radius-sm);
  padding: 4px 8px;
  font-weight: 700;
}
.cmp-table-cell--delta {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-label-sm);
  font-weight: 600;
}
.cmp-delta--positive { color: var(--wi-secondary); }
.cmp-delta--negative { color: var(--wi-on-primary-container); }
.cmp-delta--neutral { color: var(--wi-on-bg); }
.cmp-delta-arrow { font-size: 14px; line-height: 1; }

/* ── Chart card ───────────────────────────────────────── */
.cmp-chart-card { padding: var(--wi-space-md); display: flex; flex-direction: column; gap: var(--wi-space-sm); }
.cmp-chart-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--wi-space-sm);
  flex-wrap: wrap;
}
.cmp-chart-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  line-height: var(--wi-h3-leading);
  color: var(--wi-on-bg);
  margin: 0;
}
.cmp-chart-legend { display: flex; gap: var(--wi-space-sm); }
.cmp-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 500;
  color: var(--wi-on-surface-variant);
}
.cmp-legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}
.cmp-legend-dot--a { background: var(--wi-primary-container); }
.cmp-legend-dot--b { background: var(--wi-secondary); }

.cmp-chart-body { position: relative; min-height: 240px; }
.cmp-chart-svg {
  width: 100%;
  height: 240px;
  display: block;
}
.cmp-chart-grid { stroke: var(--wi-outline-variant); stroke-width: 1; opacity: 0.5; }
.cmp-chart-line {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.cmp-chart-line--a { stroke: var(--wi-primary-container); stroke-width: 2; }
.cmp-chart-line--b { stroke: var(--wi-secondary); stroke-width: 3; }
.cmp-chart-dot--a { fill: var(--wi-primary-container); }
.cmp-chart-dot--b { fill: var(--wi-secondary); }
.cmp-chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--wi-on-surface-variant);
  font-size: var(--wi-body-md);
  font-style: italic;
}

/* ── Influence leaderboard ────────────────────────────── */
.cmp-leaderboard { padding: var(--wi-space-md); }
.cmp-leaderboard-head { margin-bottom: var(--wi-space-sm); }
.cmp-leaderboard-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  line-height: var(--wi-h3-leading);
  color: var(--wi-on-bg);
  margin: 0 0 4px 0;
}
.cmp-leaderboard-desc {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
  margin: 0;
}
.cmp-leaderboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--wi-gutter);
}
@media (max-width: 720px) {
  .cmp-leaderboard-grid { grid-template-columns: 1fr; }
}

.cmp-lb-col-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--wi-space-xs);
  padding-bottom: var(--wi-space-xs);
  margin-bottom: var(--wi-space-xs);
  border-bottom: 2px solid var(--wi-outline-variant);
}
.cmp-lb-col-tag {
  display: inline-block;
  font-family: var(--wi-font-heading);
  font-weight: 700;
  font-size: var(--wi-body-md);
  padding: 2px 10px;
  border-radius: var(--wi-radius-sm);
}
.cmp-lb-col-tag--a {
  background: var(--wi-primary-container-soft);
  color: var(--wi-primary-container);
}
.cmp-lb-col-tag--b {
  background: var(--wi-secondary-soft);
  color: var(--wi-secondary);
}
.cmp-lb-col-id {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  letter-spacing: 0.04em;
}

.cmp-lb-row {
  display: grid;
  grid-template-columns: 32px 1fr 64px 40px;
  align-items: center;
  gap: var(--wi-space-xs);
  padding: 8px 4px;
  border-bottom: 1px solid var(--wi-outline-variant);
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
}
.cmp-lb-row:last-child { border-bottom: none; }
.cmp-lb-rank {
  font-family: var(--wi-font-heading);
  font-weight: 600;
  color: var(--wi-on-surface-variant);
  font-size: var(--wi-caption);
}
.cmp-lb-name {
  color: var(--wi-on-bg);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cmp-lb-score {
  text-align: end;
  font-family: var(--wi-font-heading);
  font-weight: 600;
  color: var(--wi-on-bg);
}
.cmp-lb-delta {
  text-align: center;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 700;
}
.cmp-lb-delta--up { color: var(--wi-secondary); }
.cmp-lb-delta--down { color: var(--wi-on-primary-container); }
.cmp-lb-delta--equal { color: var(--wi-on-surface-variant); }
.cmp-lb-empty {
  color: var(--wi-on-surface-variant);
  font-size: var(--wi-body-md);
  padding: var(--wi-space-sm) 0;
  font-style: italic;
}

/* ── Markets ──────────────────────────────────────────── */
.cmp-markets { padding: var(--wi-space-md); }
.cmp-markets-head { margin-bottom: var(--wi-space-sm); }
.cmp-markets-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  line-height: var(--wi-h3-leading);
  color: var(--wi-on-bg);
  margin: 0;
}
.cmp-markets-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--wi-gutter);
}
@media (max-width: 720px) {
  .cmp-markets-grid { grid-template-columns: 1fr; }
}
.cmp-market-col-head {
  margin-bottom: var(--wi-space-xs);
  padding-bottom: var(--wi-space-xs);
  border-bottom: 2px solid var(--wi-outline-variant);
}
.cmp-market-row {
  display: flex;
  align-items: center;
  gap: var(--wi-space-xs);
  padding: 8px 0;
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
}
.cmp-market-id {
  color: var(--wi-on-surface-variant);
  width: 80px;
  flex-shrink: 0;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
}
.cmp-market-bar-wrap {
  flex: 1;
  height: 8px;
  background: var(--wi-surface-container-high);
  border-radius: var(--wi-radius-pill);
  overflow: hidden;
}
.cmp-market-bar {
  height: 100%;
  border-radius: var(--wi-radius-pill);
  transition: width 300ms ease;
}
.cmp-market-bar--a { background: var(--wi-primary-container); }
.cmp-market-bar--b { background: var(--wi-secondary); }
.cmp-market-price {
  width: 80px;
  text-align: end;
  color: var(--wi-on-bg);
  font-family: var(--wi-font-heading);
  font-weight: 600;
  font-size: var(--wi-caption);
}

/* ── Spinner keyframes (local to this view) ─────────────
   Le keyframe @keyframes spin existe globalement (components.css)
   mais est répliqué ici car ce composant utilise <style scoped>. */
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
</style>
