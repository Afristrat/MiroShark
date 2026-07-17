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
          >
{{ mode.label }}
</button>
        </nav>

        <div class="toolbar-actions">
          <button
            type="button"
            class="toolbar-action-btn"
            :title="$t('report.actions.viewAgentsAria')"
            :aria-label="$t('report.actions.viewAgentsAria')"
            @click="goToAgentsView"
          >
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
            <span class="toolbar-action-label">{{ $t('report.actions.viewAgents') }}</span>
          </button>

          <button
            type="button"
            class="toolbar-action-btn"
            :class="{ 'is-active': chatOpen }"
            :title="chatOpen ? $t('report.actions.closeChat') : $t('report.actions.openChat')"
            :aria-label="chatOpen ? $t('report.actions.closeChat') : $t('report.actions.openChat')"
            :aria-pressed="chatOpen"
            @click="toggleChat"
          >
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
            </svg>
            <span class="toolbar-action-label">{{ $t('report.actions.openChat') }}</span>
          </button>

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
        <!-- Progress timeline (US-110) — 4 stages with auto-refresh -->
        <ReportProgressTimeline :stages="progressStages" />

        <!-- Title Section -->
        <section class="magazine-card magazine-title">
          <div class="magazine-title-block">
            <span class="magazine-eyebrow">Bassira · Simulation Report</span>
            <h1 class="magazine-h1">{{ projectTitle }}</h1>
            <p class="magazine-lede">{{ projectSummary }}</p>
          </div>

          <dl class="magazine-meta">
            <div class="magazine-meta-item">
              <dt>Référence simulation</dt>
              <dd class="mono" :title="simulationId || ''">{{ simIdShort }}</dd>
            </div>
            <div class="magazine-meta-item">
              <dt>Référence rapport</dt>
              <dd class="mono" :title="currentReportId || ''">{{ reportIdShort }}</dd>
            </div>
            <div class="magazine-meta-item">
              <dt>Date de génération</dt>
              <dd class="mono">{{ generatedAt }}</dd>
            </div>
            <div class="magazine-meta-item">
              <dt>Tours de simulation</dt>
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
            :report-id="currentReportId"
            :simulation-id="simulationId"
            :system-logs="systemLogs"
            :initial-report="reportMeta"
            @add-log="addLog"
            @update-status="updateStatus"
          />
        </section>
      </article>

      <!-- Graph mode -->
      <section v-else-if="viewMode === 'graph'" class="report-fullscreen-panel">
        <GraphPanel
          :graph-data="graphData"
          :loading="graphLoading"
          :current-phase="4"
          :is-simulating="false"
          :simulation-id="simulationId"
          @refresh="refreshGraph"
          @toggle-maximize="viewMode = 'workbench'"
        />
      </section>

      <!-- Network mode -->
      <section v-else-if="viewMode === 'network'" class="report-fullscreen-panel">
        <NetworkPanel
          :simulation-id="simulationId"
          :is-simulating="false"
        />
      </section>
    </main>

    <!-- US-111 — Sliding chat panel (right side, 380px). Toggled by the
         toolbar chat button. Persists history in localStorage. -->
    <ReportChatPanel
      :open="chatOpen"
      :report-id="currentReportId"
      :simulation-id="simulationId"
      @close="closeChat"
    />
  </div>
</template>

<script setup>
import { ref, computed, watchEffect, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GraphPanel from '../components/GraphPanel.vue'
import NetworkPanel from '../components/NetworkPanel.vue'
import Step4Report from '../components/Step4Report.vue'
import ReportProgressTimeline from '../components/ReportProgressTimeline.vue'
import ReportChatPanel from '../components/ReportChatPanel.vue'
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
// Priority: report outline (the actual generated title) > project name > sim
// requirement > simple placeholder. We never fabricate a fake topic here
// (DEFCON 1: zero invented data).
const projectTitle = computed(() => {
  return (
    reportMeta.value?.outline?.title ||
    projectData.value?.name ||
    projectData.value?.project_name ||
    reportMeta.value?.title ||
    simulationData.value?.simulation_requirement ||
    reportMeta.value?.simulation_requirement ||
    '—'
  )
})

const projectSummary = computed(() => {
  return (
    reportMeta.value?.outline?.summary ||
    projectData.value?.description ||
    projectData.value?.summary ||
    reportMeta.value?.summary ||
    ''
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

// Versions abrégées des IDs pour affichage cosmétique (8 derniers caractères
// avec préfixe ellipsé). L'ID complet reste disponible via `:title` au survol.
const simIdShort = computed(() => {
  if (!simulationId.value) return '—'
  const id = simulationId.value
  if (id.length <= 16) return id
  return '…' + id.slice(-8)
})

const reportIdShort = computed(() => {
  if (!currentReportId.value) return '—'
  const id = currentReportId.value
  if (id.length <= 16) return id
  return '…' + id.slice(-8)
})

const nRoundsLabel = computed(() => {
  // Lecture exhaustive selon les noms de champs canoniques (SimState +
  // Outcome + state.json brut). Le Loader US-119 expose context.state.
  const n =
    simulationData.value?.current_round ||
    simulationData.value?.total_rounds ||
    simulationData.value?.n_rounds ||
    simulationData.value?.rounds ||
    simulationData.value?.outcome?.nb_rounds ||
    reportMeta.value?.n_rounds ||
    reportMeta.value?.outcome?.nb_rounds
  if (n == null || n === 0) return '—'
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

// ─────────────────────────────────────────────────────────────────────
// US-110 — Progress timeline (4 stages : graph_build → simulation → agents
// → report). Stage status is computed from the data we already load
// (reportMeta + simulationData + projectData). The timeline auto-refreshes
// every 5s while at least one stage is still in progress.
// ─────────────────────────────────────────────────────────────────────
const progressStages = computed(() => {
  const reportStatus = reportMeta.value?.status
  const simStatus = simulationData.value?.status
  const runnerStatus = simulationData.value?.runner_status
  const completedAt = simulationData.value?.completed_at
  const graphReady = !!(projectData.value?.graph_id || simulationData.value?.graph_id)

  // Stage 1 — graph build : done as soon as a graph_id exists.
  const graphStage = graphReady ? 'done' : 'pending'

  // Stage 2 — simulation : done when runner says completed or completed_at
  // is set on the simulation; in_progress when runner is running/preparing;
  // pending otherwise. Failed → error.
  let simStage = 'pending'
  if (runnerStatus === 'completed' || completedAt) {
    simStage = 'done'
  } else if (
    runnerStatus === 'running' ||
    runnerStatus === 'preparing' ||
    simStatus === 'running' ||
    simStatus === 'preparing'
  ) {
    simStage = 'in_progress'
  } else if (runnerStatus === 'failed' || simStatus === 'failed') {
    simStage = 'error'
  } else if (graphReady) {
    simStage = 'pending'
  }

  // Stage 3 — agent synthesis : we treat the agent step as "done" once the
  // simulation is complete (the interaction view + audit are derivative of
  // the simulation runner's output). When the simulation is still running,
  // this stage is pending. If the report is being generated while the
  // simulation has just completed, this stage is "in_progress" until the
  // report planner kicks in.
  let agentStage = 'pending'
  if (simStage === 'done' && (reportStatus === 'planning' || reportStatus === 'pending')) {
    agentStage = 'in_progress'
  } else if (simStage === 'done') {
    agentStage = 'done'
  } else if (simStage === 'error') {
    agentStage = 'error'
  }

  // Stage 4 — final report : driven directly by reportMeta.status.
  let reportStage = 'pending'
  if (reportStatus === 'completed') reportStage = 'done'
  else if (reportStatus === 'failed') reportStage = 'error'
  else if (reportStatus === 'planning' || reportStatus === 'generating') reportStage = 'in_progress'

  // Cascade logique : si le report final est completed, alors la simulation
  // ET la synthèse agents ont nécessairement abouti. Force-les à done même
  // si simulationData manque le runner_status (cas où on consulte un report
  // archivé sans la state.json fraîche en mémoire SimulationManager).
  if (reportStage === 'done') {
    if (simStage !== 'error') simStage = 'done'
    if (agentStage !== 'error') agentStage = 'done'
  }

  return [
    { id: 'graphBuild', status: graphStage },
    { id: 'simulation', status: simStage },
    { id: 'agents', status: agentStage },
    { id: 'report', status: reportStage }
  ]
})

const allStagesDone = computed(() =>
  progressStages.value.every((s) => s.status === 'done')
)

// Polling — refresh report + simulation every 5s while progression is
// not finished. We never poll once everything is done (avoid wasted
// network on a static document).
let progressTimer = null

const refreshProgress = async () => {
  if (!currentReportId.value) return
  try {
    const reportRes = await getReport(currentReportId.value)
    if (reportRes.success && reportRes.data) {
      reportMeta.value = reportRes.data
      if (reportRes.data.status === 'completed') currentStatus.value = 'completed'
      if (reportRes.data.status === 'failed') currentStatus.value = 'error'
      if (reportRes.data.simulation_id) {
        simulationId.value = reportRes.data.simulation_id
        const simRes = await getSimulation(reportRes.data.simulation_id)
        if (simRes.success && simRes.data) {
          simulationData.value = simRes.data
        }
      }
    }
  } catch (err) {
    addLog(`Progress refresh error: ${err.message}`)
  }
}

const startProgressPolling = () => {
  if (progressTimer) return
  progressTimer = setInterval(() => {
    if (allStagesDone.value) {
      stopProgressPolling()
      return
    }
    refreshProgress()
  }, 5000)
}

const stopProgressPolling = () => {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
}

// US-111 — Sliding chat panel.
const chatOpen = ref(false)
const toggleChat = () => {
  chatOpen.value = !chatOpen.value
}
const closeChat = () => {
  chatOpen.value = false
}

// US-112 — Quick navigation to the agents view (interaction audit +
// sandbox). The InteractionView is already wired to the route name
// 'Interaction' with :reportId. The reciprocal back button lives in
// InteractionView.
const goToAgentsView = () => {
  if (currentReportId.value) {
    router.push({ name: 'Interaction', params: { reportId: currentReportId.value } })
  }
}

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

      // The URL sometimes carries a simulation_id (sim_xxx) instead of a
      // report_id (report_xxx). The backend resolves both — but we MUST
      // realign currentReportId with the canonical report_id, otherwise
      // Step4Report will poll /api/report/sim_xxx/agent-log (404) and never
      // hydrate the panel. Cf US-109.
      if (reportData.report_id && reportData.report_id !== currentReportId.value) {
        currentReportId.value = reportData.report_id
      }

      // Reflect the canonical status from the backend payload immediately.
      if (reportData.status === 'completed') {
        currentStatus.value = 'completed'
      } else if (reportData.status === 'failed') {
        currentStatus.value = 'error'
      }

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
  // Use the actual report title when available so the browser tab reflects
  // the document the user is reading, not a generic phase counter.
  const titleSrc = reportMeta.value?.outline?.title || projectData.value?.name
  const truncated =
    typeof titleSrc === 'string' && titleSrc.trim()
      ? (titleSrc.length > 60 ? titleSrc.slice(0, 57) + '…' : titleSrc)
      : ''
  const base = truncated ? `${truncated} · Bassira` : 'Bassira · Report'
  document.title = dot ? `${dot} ${base}` : base
})

onUnmounted(() => {
  document.title = 'Bassira'
  stopProgressPolling()
})

onMounted(() => {
  addLog('ReportView initialized')
  loadReportData().then(() => {
    if (!allStagesDone.value) {
      startProgressPolling()
    }
  })
})

// React to status transitions: stop the polling as soon as we've reached
// "all done" so we don't waste network on a static document.
watch(allStagesDone, (done) => {
  if (done) stopProgressPolling()
  else if (!progressTimer && currentReportId.value) startProgressPolling()
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

.toolbar-action-btn {
  appearance: none;
  border: 1px solid rgba(250, 247, 242, 0.18);
  background: rgba(250, 247, 242, 0.06);
  color: var(--wi-bg);
  font-family: var(--wi-font-body);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 6px 12px;
  border-radius: var(--wi-radius-pill);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: background var(--ms-transition), border-color var(--ms-transition);
}

.toolbar-action-btn:hover {
  background: rgba(250, 247, 242, 0.14);
  border-color: rgba(250, 247, 242, 0.32);
}

.toolbar-action-btn.is-active {
  background: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
  border-color: var(--wi-primary-container);
}

.toolbar-action-btn:focus-visible {
  outline: 2px solid var(--wi-primary-container);
  outline-offset: 2px;
}

@media (max-width: 768px) {
  .toolbar-action-btn .toolbar-action-label {
    display: none;
  }
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
