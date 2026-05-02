<template>
  <div class="report-view">
    <!-- Watermark "BASSIRA · بصيرة" — print only, very subtle cream-on-cream -->
    <div class="report-watermark" aria-hidden="true">BASSIRA · بصيرة</div>

    <!-- Sticky executive toolbar (charcoal — McKinsey board-ready) -->
    <header class="report-toolbar">
      <div class="report-toolbar-inner">
        <div class="toolbar-brand" @click="router.push('/')" role="link" tabindex="0">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M3 3v18h18"></path>
            <path d="M7 14l4-4 4 4 5-6"></path>
          </svg>
          <span class="toolbar-brand-label">Bassira Final Simulation Report</span>
        </div>

        <!-- Discreet view chips: Report | Graph | Network -->
        <nav class="toolbar-views" aria-label="Report views">
          <button
            v-for="mode in viewModes"
            :key="mode.id"
            class="toolbar-chip"
            :class="{ active: viewMode === mode.id }"
            @click="viewMode = mode.id"
            :aria-pressed="viewMode === mode.id"
          >{{ mode.label }}</button>
        </nav>

        <div class="toolbar-actions">
          <span class="toolbar-status" :class="statusClass" :title="statusText">
            <span class="toolbar-status-dot"></span>
            <span class="toolbar-status-label">{{ statusText }}</span>
          </span>
        </div>
      </div>
    </header>

    <main class="report-main">
      <!-- Magazine canvas (1000px max-width) — used in Report mode -->
      <article v-if="viewMode === 'workbench'" class="report-magazine">
        <!-- Title Section -->
        <section class="magazine-card magazine-title">
          <div class="magazine-title-block">
            <span class="magazine-eyebrow">Bassira · Simulation Report</span>
            <h1 class="magazine-h1">{{ projectTitle }}</h1>
            <p class="magazine-lede">{{ projectSummary }}</p>
          </div>

          <dl class="magazine-meta">
            <div class="magazine-meta-item">
              <dt>Simulation ID</dt>
              <dd class="mono">{{ simulationId || '—' }}</dd>
            </div>
            <div class="magazine-meta-item">
              <dt>Report ID</dt>
              <dd class="mono">{{ currentReportId || '—' }}</dd>
            </div>
            <div class="magazine-meta-item">
              <dt>Date generated</dt>
              <dd class="mono">{{ generatedAt }}</dd>
            </div>
            <div class="magazine-meta-item">
              <dt>N rounds</dt>
              <dd class="mono">{{ nRoundsLabel }}</dd>
            </div>
          </dl>
        </section>

        <!-- Executive Summary callout (terracotta border-inline-start) -->
        <section v-if="executiveBullets.length" class="magazine-card magazine-callout">
          <h2 class="magazine-section-heading">Executive Summary</h2>
          <ul class="magazine-callout-list">
            <li v-for="(bullet, idx) in executiveBullets" :key="idx">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="9 12 11 14 15 10"></polyline>
              </svg>
              <span>{{ bullet }}</span>
            </li>
          </ul>
        </section>

        <!-- Body — Step4Report renders the full markdown report (sections, charts, exports) -->
        <section class="magazine-card magazine-body">
          <Step4Report
            :reportId="currentReportId"
            :simulationId="simulationId"
            :systemLogs="systemLogs"
            @add-log="addLog"
            @update-status="updateStatus"
          />
        </section>
      </article>

      <!-- Graph mode -->
      <section v-else-if="viewMode === 'graph'" class="report-fullscreen-panel">
        <GraphPanel
          :graphData="graphData"
          :loading="graphLoading"
          :currentPhase="4"
          :isSimulating="false"
          :simulationId="simulationId"
          @refresh="refreshGraph"
          @toggle-maximize="viewMode = 'workbench'"
        />
      </section>

      <!-- Network mode -->
      <section v-else-if="viewMode === 'network'" class="report-fullscreen-panel">
        <NetworkPanel
          :simulationId="simulationId"
          :isSimulating="false"
        />
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watchEffect, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GraphPanel from '../components/GraphPanel.vue'
import NetworkPanel from '../components/NetworkPanel.vue'
import Step4Report from '../components/Step4Report.vue'
import { getProject, getGraphData } from '../api/graph'
import { getSimulation } from '../api/simulation'
import { getReport } from '../api/report'

const route = useRoute()
const router = useRouter()

// Props
const props = defineProps({
  reportId: String
})

// Layout state — magazine ('workbench') is the McKinsey board-ready default.
const viewMode = ref('workbench')

const viewModes = [
  { id: 'workbench', label: 'Report' },
  { id: 'graph', label: 'Graph' },
  { id: 'network', label: 'Network' }
]

// Data state
const currentReportId = ref(route.params.reportId)
const simulationId = ref(null)
const projectData = ref(null)
const simulationData = ref(null)
const reportMeta = ref(null)
const graphData = ref(null)
const graphLoading = ref(false)
const systemLogs = ref([])
const currentStatus = ref('processing') // processing | completed | error

// --- Derived metadata for the magazine title section ---
const projectTitle = computed(() => {
  return (
    projectData.value?.name ||
    projectData.value?.project_name ||
    reportMeta.value?.title ||
    'Market Sentiment Resilience Under Regulatory Stress'
  )
})

const projectSummary = computed(() => {
  return (
    projectData.value?.description ||
    projectData.value?.summary ||
    reportMeta.value?.summary ||
    'An analysis of simulated agent dynamics and belief drift across multiple socio-economic strata.'
  )
})

const generatedAt = computed(() => {
  const raw =
    reportMeta.value?.created_at ||
    reportMeta.value?.generated_at ||
    simulationData.value?.completed_at ||
    simulationData.value?.created_at
  if (!raw) return '—'
  try {
    const d = new Date(raw)
    if (Number.isNaN(d.getTime())) return raw
    return d.toLocaleString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC',
      timeZoneName: 'short'
    })
  } catch {
    return raw
  }
})

const nRoundsLabel = computed(() => {
  const n = simulationData.value?.n_rounds || simulationData.value?.rounds || reportMeta.value?.n_rounds
  if (n == null) return '—'
  try {
    return Number(n).toLocaleString('en-US')
  } catch {
    return String(n)
  }
})

const executiveBullets = computed(() => {
  // Pulled from report metadata when the backend exposes a synthesised exec summary.
  // Falls back to an empty array (the callout is hidden) so we never fabricate findings.
  const candidates = [
    reportMeta.value?.executive_summary,
    reportMeta.value?.summary_bullets,
    reportMeta.value?.exec_summary
  ]
  for (const c of candidates) {
    if (Array.isArray(c) && c.length) return c.slice(0, 4)
    if (typeof c === 'string' && c.trim()) {
      // Split on newlines or bullet markers, keep first 3.
      return c
        .split(/\n|•|–|—/)
        .map((s) => s.replace(/^[-*\s]+/, '').trim())
        .filter(Boolean)
        .slice(0, 3)
    }
  }
  return []
})

// --- Status ---
const statusClass = computed(() => currentStatus.value)
const statusText = computed(() => {
  if (currentStatus.value === 'error') return 'Error'
  if (currentStatus.value === 'completed') return 'Completed'
  return 'Generating'
})

// --- Helpers ---
const addLog = (msg) => {
  const now = new Date()
  const time =
    now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) +
    '.' +
    now.getMilliseconds().toString().padStart(3, '0')
  systemLogs.value.push({ time, msg })
  if (systemLogs.value.length > 200) systemLogs.value.shift()
}

const updateStatus = (status) => {
  currentStatus.value = status
}

// --- Data logic ---
const loadReportData = async () => {
  try {
    addLog(`Loading report data: ${currentReportId.value}`)

    const reportRes = await getReport(currentReportId.value)
    if (reportRes.success && reportRes.data) {
      const reportData = reportRes.data
      reportMeta.value = reportData
      simulationId.value = reportData.simulation_id

      if (simulationId.value) {
        const simRes = await getSimulation(simulationId.value)
        if (simRes.success && simRes.data) {
          const simData = simRes.data
          simulationData.value = simData

          if (simData.project_id) {
            const projRes = await getProject(simData.project_id)
            if (projRes.success && projRes.data) {
              projectData.value = projRes.data
              addLog(`Project loaded successfully: ${projRes.data.project_id}`)
              if (projRes.data.graph_id) await loadGraph(projRes.data.graph_id)
            }
          }
        }
      }
    } else {
      addLog(`Failed to get report info: ${reportRes.error || 'Unknown error'}`)
    }
  } catch (err) {
    addLog(`Loading error: ${err.message}`)
  }
}

const loadGraph = async (graphId) => {
  graphLoading.value = true
  try {
    const res = await getGraphData(graphId)
    if (res.success) {
      graphData.value = res.data
      addLog('Graph data loaded successfully')
    }
  } catch (err) {
    addLog(`Failed to load graph: ${err.message}`)
  } finally {
    graphLoading.value = false
  }
}

const refreshGraph = () => {
  if (projectData.value?.graph_id) loadGraph(projectData.value.graph_id)
}

watch(
  () => route.params.reportId,
  (newId) => {
    if (newId && newId !== currentReportId.value) {
      currentReportId.value = newId
      loadReportData()
    }
  },
  { immediate: true }
)

watchEffect(() => {
  const status = statusClass.value
  const dot =
    status === 'processing'
      ? '🟠'
      : status === 'error'
      ? '🔴'
      : status === 'completed'
      ? '🟢'
      : ''
  document.title = dot ? `${dot} (4/4) Bassira` : '(4/4) Bassira'
})

onUnmounted(() => {
  document.title = 'Bassira'
})

onMounted(() => {
  addLog('ReportView initialized')
  loadReportData()
})
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   ReportView — Magazine layout (McKinsey board-ready)
   Source design : stitch_bassira_global_design_system/
   bassira_rapport_de_simulation_final/code.html
   Palette : Warm Intelligence (--wi-*) sur fond cream paper-quality.
   Aucune valeur hex hardcodée — tous les colors viennent des tokens
   --wi-*, --ms-* et alias compatibles.
   ═══════════════════════════════════════════════════════════ */

.report-view {
  min-height: 100vh;
  background: var(--wi-bg);
  color: var(--wi-on-bg);
  font-family: var(--wi-font-body);
  position: relative;
  overflow-x: hidden;
}

/* ── Watermark "BASSIRA · بصيرة" : très subtle cream-on-cream, print only ── */
.report-watermark {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--wi-font-heading);
  font-weight: 900;
  font-size: 14vw;
  letter-spacing: -0.02em;
  color: var(--wi-surface-container);
  opacity: 0;
  transform: rotate(-32deg);
  white-space: nowrap;
  user-select: none;
  pointer-events: none;
  z-index: 0;
}

/* ── Sticky executive toolbar — charcoal background, cream text ── */
.report-toolbar {
  position: sticky;
  top: 0;
  z-index: var(--ms-z-sticky);
  background: var(--wi-on-bg);
  color: var(--wi-bg);
  border-bottom: 1px solid var(--wi-on-bg);
  box-shadow: var(--wi-shadow-sm);
}

.report-toolbar-inner {
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: var(--wi-space-md);
  padding: 14px var(--wi-space-md);
}

.toolbar-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  color: var(--wi-bg);
  flex: 0 0 auto;
}

.toolbar-brand:focus-visible {
  outline: 2px solid var(--wi-primary-container);
  outline-offset: 3px;
  border-radius: var(--wi-radius-sm);
}

.toolbar-brand-label {
  font-family: var(--wi-font-body);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  opacity: 0.85;
}

.toolbar-views {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-inline-start: auto;
  background: rgba(250, 247, 242, 0.06);
  padding: 4px;
  border-radius: var(--wi-radius-pill);
}

.toolbar-chip {
  appearance: none;
  border: 0;
  background: transparent;
  color: var(--wi-bg);
  opacity: 0.55;
  font-family: var(--wi-font-body);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  padding: 6px 14px;
  border-radius: var(--wi-radius-pill);
  cursor: pointer;
  transition: opacity var(--ms-transition), background var(--ms-transition);
}

.toolbar-chip:hover {
  opacity: 0.9;
}

.toolbar-chip.active {
  background: var(--wi-bg);
  color: var(--wi-on-bg);
  opacity: 1;
}

.toolbar-chip:focus-visible {
  outline: 2px solid var(--wi-primary-container);
  outline-offset: 2px;
}

.toolbar-actions {
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-sm);
  flex: 0 0 auto;
}

.toolbar-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--wi-font-body);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  opacity: 0.65;
}

.toolbar-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--wi-outline);
}

.toolbar-status.processing .toolbar-status-dot {
  background: var(--wi-primary-container);
  animation: report-pulse 1.4s ease-in-out infinite;
}
.toolbar-status.completed .toolbar-status-dot { background: var(--wi-secondary-container); }
.toolbar-status.error .toolbar-status-dot { background: var(--wi-error); }

@keyframes report-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.18); }
}

/* ── Main canvas ── */
.report-main {
  position: relative;
  z-index: 1;
  padding: var(--wi-space-xl) var(--wi-space-md) var(--wi-space-xl);
}

/* ── Magazine layout (1000px) ── */
.report-magazine {
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-lg);
}

.magazine-card {
  background: var(--wi-surface);
  border-radius: var(--wi-radius-card);
  border: 1px solid var(--wi-outline-variant);
  padding: var(--wi-space-lg);
  box-shadow: var(--wi-shadow-md);
}

/* ── Title Section ── */
.magazine-title {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-md);
}

.magazine-eyebrow {
  font-family: var(--wi-font-body);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--wi-on-primary-container); /* terracotta */
}

.magazine-h1 {
  margin: 8px 0 0;
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h1-size);
  font-weight: var(--wi-h1-weight);
  line-height: var(--wi-h1-leading);
  letter-spacing: var(--wi-h1-tracking);
  color: var(--wi-on-surface);
}

.magazine-lede {
  margin: var(--wi-space-sm) 0 0;
  max-width: 60ch;
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-lg);
  font-weight: var(--wi-body-lg-weight);
  line-height: var(--wi-body-lg-leading);
  color: var(--wi-on-surface-variant);
}

.magazine-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--wi-space-md);
  margin: var(--wi-space-md) 0 0;
  padding-top: var(--wi-space-md);
  border-top: 1px solid var(--wi-outline-variant);
}

.magazine-meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.magazine-meta-item dt {
  font-family: var(--wi-font-body);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--wi-outline);
  margin: 0;
}

.magazine-meta-item dd {
  margin: 0;
  font-size: 13px;
  color: var(--wi-on-surface);
  word-break: break-all;
}

.mono {
  font-family: var(--wi-font-body);
}

.magazine-meta .mono,
.magazine-meta-item dd.mono {
  font-family: var(--ms-font-mono);
  font-size: 12px;
  letter-spacing: 0.02em;
  color: var(--wi-on-surface-variant);
}

/* ── Executive Summary callout (terracotta border-inline-start 4px) ── */
.magazine-callout {
  background: var(--wi-bg);
  border: 1px solid var(--wi-outline-variant);
  border-inline-start: 4px solid var(--wi-primary-container);
  padding: var(--wi-space-lg);
}

.magazine-section-heading {
  margin: 0 0 var(--wi-space-md);
  font-family: var(--wi-font-heading);
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--wi-on-primary-container);
}

.magazine-callout-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
}

.magazine-callout-list li {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  font-size: 15px;
  line-height: 1.7;
  color: var(--wi-on-surface);
}

.magazine-callout-list li svg {
  color: var(--wi-on-primary-container);
  flex: 0 0 auto;
  margin-top: 2px;
}

/* ── Body card hosting Step4Report ──
   Step4Report contient le rendu markdown + boutons export PDF/MD (US-059).
   On wrappe simplement dans une carte magazine et on neutralise son
   double padding pour qu'il vive proprement à l'intérieur. */
.magazine-body {
  padding: 0;
  overflow: hidden;
}

.magazine-body :deep(.report-panel) {
  background: transparent;
  border-radius: 0;
}

/* ── Fullscreen modes (Graph / Network) ── */
.report-fullscreen-panel {
  max-width: 1280px;
  margin: 0 auto;
  height: calc(100vh - 80px);
  background: var(--wi-surface);
  border-radius: var(--wi-radius-card);
  border: 1px solid var(--wi-outline-variant);
  box-shadow: var(--wi-shadow-md);
  overflow: hidden;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .report-toolbar-inner {
    flex-wrap: wrap;
    gap: var(--wi-space-sm);
    padding: 10px var(--wi-space-sm);
  }
  .toolbar-views {
    margin-inline-start: 0;
    order: 3;
    width: 100%;
    justify-content: center;
  }
  .toolbar-actions {
    margin-inline-start: auto;
  }
  .magazine-card {
    padding: var(--wi-space-md);
    border-radius: var(--wi-radius-interactive);
  }
  .magazine-h1 {
    font-size: 32px;
  }
  .report-main {
    padding: var(--wi-space-md) var(--wi-space-sm);
  }
}

/* ── Print styles : board-ready livrable ──
   Remove nav/shadows/sticky, expand collapsibles, force cream bg. */
@media print {
  .report-view {
    background: var(--wi-bg);
  }
  .report-toolbar {
    position: static;
    background: transparent;
    color: var(--wi-on-bg);
    border-bottom: 1px solid var(--wi-outline-variant);
    box-shadow: none;
  }
  .toolbar-brand,
  .toolbar-brand-label,
  .toolbar-status {
    color: var(--wi-on-bg);
    opacity: 1;
  }
  .toolbar-views,
  .toolbar-status-dot {
    display: none !important;
  }
  .report-main {
    padding: var(--wi-space-md) 0;
  }
  .magazine-card {
    box-shadow: none !important;
    border: 1px solid var(--wi-outline-variant);
    break-inside: avoid;
    page-break-inside: avoid;
  }
  .magazine-body :deep(.right-panel),
  .magazine-body :deep(.workflow-overview),
  .magazine-body :deep(.workflow-timeline),
  .magazine-body :deep(.next-step-btn),
  .magazine-body :deep(.export-buttons) {
    display: none !important;
  }
  .magazine-body :deep(.section-body) {
    display: block !important;
  }
  .magazine-body :deep(.collapse-icon) {
    display: none !important;
  }
  .report-watermark {
    opacity: 0.35;
    z-index: 0;
  }
}

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .toolbar-status.processing .toolbar-status-dot {
    animation: none;
  }
  .toolbar-chip {
    transition: none;
  }
}
</style>
