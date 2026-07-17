<template>
  <div class="main-view" data-cockpit="dark">
    <!-- ───────────── Header cockpit ─────────────
         Aligné sur Stitch bassira_simulation_cockpit : barre dense, sticky,
         avec brand + chip ID, view-switcher segmenté et bloc statut/phase.
         L'analyste passe 30-90 min ici → priorité densité d'info + flow. -->
    <header class="cockpit-header">
      <div class="cockpit-header-left">
        <div class="cockpit-brand" @click="router.push('/')" role="link" tabindex="0">BASSIRA</div>
        <div v-if="currentSimulationId" class="cockpit-sim-chip" :title="currentSimulationId">
          {{ formattedSimId }}
        </div>
      </div>

      <div class="cockpit-header-center">
        <div class="cockpit-view-switcher" role="tablist" :aria-label="$t('simulation.view.stage.config')">
          <button
            v-for="mode in viewModes"
            :key="mode.id"
            type="button"
            role="tab"
            class="cockpit-view-btn"
            :class="{ 'cockpit-view-btn--active': viewMode === mode.id }"
            :aria-selected="viewMode === mode.id"
            @click="viewMode = mode.id"
          >
            <span class="material-symbols-outlined cockpit-view-icon" aria-hidden="true">{{ mode.icon }}</span>
            <span>{{ mode.label }}</span>
          </button>
        </div>
      </div>

      <div class="cockpit-header-right">
        <div class="cockpit-phase">
          <span class="cockpit-phase-label">{{ $t('process.step2.step1.title') }}</span>
          <div class="cockpit-phase-dots" aria-hidden="true">
            <span
              v-for="n in 4"
              :key="n"
              class="cockpit-phase-dot"
              :class="{
                'cockpit-phase-dot--done': n < currentPhase || currentStatus === 'completed',
                'cockpit-phase-dot--active': n === currentPhase && currentStatus !== 'completed'
              }"
            ></span>
          </div>
        </div>
        <span class="cockpit-status" :class="`cockpit-status--${statusClass}`" role="status">
          <span class="cockpit-status-dot"></span>
          <span class="cockpit-status-label">{{ statusText }}</span>
        </span>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="content-area">
      <!-- Initial-fetch skeleton overlay — shown until the simulation /
           project / graph round-trip resolves. Uses .ms-skeleton from
           src/styles/components.css for shimmer + reduced-motion handling. -->
      <div v-if="initialLoading" class="initial-skeleton" aria-hidden="true">
        <div class="skeleton-pane skeleton-pane-left">
          <div class="ms-skeleton sk-toolbar"></div>
          <div class="sk-graph-area">
            <div class="ms-skeleton sk-node sk-node-a"></div>
            <div class="ms-skeleton sk-node sk-node-b"></div>
            <div class="ms-skeleton sk-node sk-node-c"></div>
            <div class="ms-skeleton sk-node sk-node-d"></div>
            <div class="ms-skeleton sk-edge sk-edge-1"></div>
            <div class="ms-skeleton sk-edge sk-edge-2"></div>
          </div>
        </div>
        <div class="skeleton-pane skeleton-pane-right">
          <div class="ms-skeleton sk-line sk-line-title"></div>
          <div class="ms-skeleton sk-line sk-line-sub"></div>
          <div class="ms-skeleton sk-block sk-block-status"></div>
          <div class="ms-skeleton sk-line sk-line-section"></div>
          <div class="ms-skeleton sk-block sk-block-feed"></div>
          <div class="ms-skeleton sk-line sk-line-section"></div>
          <div class="ms-skeleton sk-block sk-block-market"></div>
        </div>
      </div>

      <!-- Left Panel: Graph -->
      <div class="panel-wrapper left" :style="leftPanelStyle">
        <GraphPanel
          :graph-data="graphData"
          :loading="graphLoading"
          :current-phase="2"
          :simulation-id="currentSimulationId"
          @refresh="refreshGraph"
          @toggle-maximize="toggleMaximize('graph')"
        />
      </div>

      <!-- Right Panel: Step2 Agent Setup -->
      <div class="panel-wrapper right" :style="rightPanelStyle">
        <Step2EnvSetup
          :simulation-id="currentSimulationId"
          :project-data="projectData"
          :graph-data="graphData"
          :system-logs="systemLogs"
          @go-back="handleGoBack"
          @next-step="handleNextStep"
          @add-log="addLog"
          @update-status="updateStatus"
          @update-phase="updatePhase"
        />
      </div>

      <!-- ── Panneau À la une (US-058) ── -->
      <aside v-if="showTrending" class="sim-trending-drawer">
        <div class="sim-trending-header">
          <span>◉ {{ $t('trending.label') }}</span>
          <button class="sim-trending-close" type="button" @click="showTrending = false" :title="$t('trending.hideTitle', 'Masquer')">×</button>
        </div>
        <TrendingTopics @select="handleTrendingSelect" />
      </aside>
      <button
        v-else
        class="sim-trending-toggle"
        type="button"
        @click="showTrending = true"
        :title="$t('trending.showTitle', 'Actualités')"
      >
◉
</button>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watchEffect, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
import GraphPanel from '../components/GraphPanel.vue'
import Step2EnvSetup from '../components/Step2EnvSetup.vue'
import TrendingTopics from '../components/TrendingTopics.vue'
import { getProject, getGraphData } from '../api/graph'
import { getSimulation, stopSimulation, getEnvStatus, closeSimulationEnv } from '../api/simulation'

const route = useRoute()
const router = useRouter()

// Props
defineProps({
  simulationId: String
})

// Layout State
const viewMode = ref('split')

// View switcher modes — alignés sur Stitch (Graph / List=split / Summary=workbench).
// On garde les 3 ids existants ('graph' | 'split' | 'workbench') pour préserver
// la logique des computed leftPanelStyle / rightPanelStyle ci-dessous.
const viewModes = computed(() => ([
  { id: 'graph',     icon: 'hub',       label: t('simulation.view.stage.graph') },
  { id: 'split',     icon: 'splitscreen', label: t('simulation.view.stage.config') },
  { id: 'workbench', icon: 'dashboard', label: t('process.step2.step1.title') }
]))

// Trending panel (US-058)
const showTrending = ref(false)
const handleTrendingSelect = ({ url }) => {
  if (!url) return
  router.push({ name: 'Home', query: { url } })
}

// Data State
const currentSimulationId = ref(route.params.simulationId)
const projectData = ref(null)
const graphData = ref(null)
const graphLoading = ref(false)
const systemLogs = ref([])
const currentStatus = ref('processing') // processing | completed | error
const currentPhase = ref(0) // 0: Initializing, 1: Profiles, 2: Config, 3: Orchestrating, 4: Ready

// True until the first project + graph round-trip resolves. Drives the
// skeleton overlay that replaces the panels' bare "Loading..." flicker.
const initialLoading = ref(true)

// Chip ID lisible dans le header (8 derniers chars en MAJ, mono).
// Évite d'afficher un UUID complet qui casse la grille du cockpit.
const formattedSimId = computed(() => {
  const id = currentSimulationId.value || ''
  if (!id) return ''
  const tail = id.length > 8 ? id.slice(-8) : id
  return `SIM-${tail.toUpperCase()}`
})

// --- Computed Layout Styles ---
const leftPanelStyle = computed(() => {
  if (viewMode.value === 'graph') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'workbench') return { width: '0%', opacity: 0, transform: 'translateX(-20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

const rightPanelStyle = computed(() => {
  if (viewMode.value === 'workbench') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'graph') return { width: '0%', opacity: 0, transform: 'translateX(20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

// --- Status Computed ---
const statusClass = computed(() => {
  return currentStatus.value
})

const statusText = computed(() => {
  if (currentStatus.value === 'error') return t('common.error')
  if (currentStatus.value === 'completed') return t('process.common.readyToLaunch')
  switch (currentPhase.value) {
    case 0: return t('process.common.initializing')
    case 1: return t('process.step2.step2.title')
    case 2: return t('process.step2.step3.title')
    case 3: return t('process.step2.step4.title')
    case 4: return t('process.common.readyToLaunch')
    default: return t('process.common.loading')
  }
})

// --- Helpers ---
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + '.' + new Date().getMilliseconds().toString().padStart(3, '0')
  systemLogs.value.push({ time, msg })
  if (systemLogs.value.length > 100) {
    systemLogs.value.shift()
  }
}

const updateStatus = (status) => {
  currentStatus.value = status
}

const updatePhase = (phase) => {
  currentPhase.value = phase
}

// --- Layout Methods ---
const toggleMaximize = (target) => {
  if (viewMode.value === target) {
    viewMode.value = 'split'
  } else {
    viewMode.value = target
  }
}

const handleGoBack = () => {
  // Return to process page
  if (projectData.value?.project_id) {
    router.push({ name: 'Process', params: { projectId: projectData.value.project_id } })
  } else {
    router.push('/')
  }
}

const handleNextStep = (params = {}) => {
  addLog('Entering Step 3: Start Simulation')

  // Log simulation rounds config
  if (params.maxRounds) {
    addLog(`Custom simulation rounds: ${params.maxRounds} rounds`)
  } else {
    addLog('Using auto-configured simulation rounds')
  }

  // Build route params
  const routeParams = {
    name: 'SimulationRun',
    params: { simulationId: currentSimulationId.value }
  }
  
  // If custom rounds, pass via query params
  if (params.maxRounds) {
    routeParams.query = { maxRounds: params.maxRounds }
  }
  
  // Navigate to Step 3 page
  router.push(routeParams)
}

// --- Data Logic ---

/**
 * Check and stop running simulation
 * When user returns from Step 3 to Step 2, assume user wants to exit simulation
 */
const checkAndStopRunningSimulation = async () => {
  if (!currentSimulationId.value) return
  
  try {
    // First check if simulation environment is alive
    const envStatusRes = await getEnvStatus({ simulation_id: currentSimulationId.value })

    if (envStatusRes.success && envStatusRes.data?.env_alive) {
      addLog('Detected running simulation environment, closing...')

      // Try to gracefully close the simulation environment
      try {
        const closeRes = await closeSimulationEnv({
          simulation_id: currentSimulationId.value,
          timeout: 10  // 10 second timeout
        })

        if (closeRes.success) {
          addLog('Simulation environment closed')
        } else {
          addLog(`Failed to close simulation environment: ${closeRes.error || 'Unknown error'}`)
          // If graceful close fails, try force stop
          await forceStopSimulation()
        }
      } catch (closeErr) {
        addLog(`Error closing simulation environment: ${closeErr.message}`)
        // If graceful close errors, try force stop
        await forceStopSimulation()
      }
    } else {
      // Environment not running, but process might still exist, check simulation status
      const simRes = await getSimulation(currentSimulationId.value)
      if (simRes.success && simRes.data?.status === 'running') {
        addLog('Detected simulation status as running, stopping...')
        await forceStopSimulation()
      }
    }
  } catch (err) {
    // Failure to check env status does not affect subsequent flow
    console.warn('Failed to check simulation status:', err)
  }
}

/**
 * Force stop simulation
 */
const forceStopSimulation = async () => {
  try {
    const stopRes = await stopSimulation({ simulation_id: currentSimulationId.value })
    if (stopRes.success) {
      addLog('Simulation force stopped')
    } else {
      addLog(`Failed to force stop simulation: ${stopRes.error || 'Unknown error'}`)
    }
  } catch (err) {
    addLog(`Error force stopping simulation: ${err.message}`)
  }
}

const loadSimulationData = async () => {
  try {
    addLog(`Loading simulation data: ${currentSimulationId.value}`)

    // Get simulation info
    const simRes = await getSimulation(currentSimulationId.value)
    if (simRes.success && simRes.data) {
      const simData = simRes.data

      // Get project info
      if (simData.project_id) {
        const projRes = await getProject(simData.project_id)
        if (projRes.success && projRes.data) {
          projectData.value = projRes.data
          addLog(`Project loaded successfully: ${projRes.data.project_id}`)

          // Get graph data
          if (projRes.data.graph_id) {
            await loadGraph(projRes.data.graph_id)
          }
        }
      }
    } else {
      addLog(`Failed to load simulation data: ${simRes.error || 'Unknown error'}`)
    }
  } catch (err) {
    addLog(`Loading error: ${err.message}`)
  } finally {
    // Hide the initial skeleton overlay once the first round-trip is done,
    // whether it succeeded or not — the panels themselves render their own
    // empty / error states beyond this point.
    initialLoading.value = false
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
  if (projectData.value?.graph_id) {
    loadGraph(projectData.value.graph_id)
  }
}

watchEffect(() => {
  const status = statusClass.value
  const dot = status === 'error' ? '\uD83D\uDD34' : status === 'completed' ? '\uD83D\uDFE2' : '\uD83D\uDFE0'
  document.title = `${dot} (2/4) ${statusText.value} · Bassira`
})

onMounted(async () => {
  addLog('SimulationView initialized')

  // Check and stop running simulation (when user returns from Step 3)
  await checkAndStopRunningSimulation()

  // Load simulation data
  loadSimulationData()
})
</script>

<style scoped>
/* ─────────────────────────────────────────────────────────────
   SimulationView — Cockpit dark first
   Source design : stitch_bassira_global_design_system/
                   bassira_simulation_cockpit/code.html
   Audience : Tier 2 Analyst (sessions 30-90 min) → flow state,
   contrôle, densité d'info. Tokens --wi-* / --ms-* uniquement,
   zéro hex hardcodé.
   ───────────────────────────────────────────────────────────── */

/* Le cockpit s'affiche par défaut en clair (warm) ; en dark mode
   global ([data-theme="dark"] sur <html>), les tokens --wi-bg /
   --wi-surface / --wi-surface-container basculent automatiquement
   vers la palette "0f1117 / 1a1d27 / 22263a" du Stitch. */
.main-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--wi-bg);
  color: var(--wi-on-bg);
  overflow: hidden;
  font-family: var(--wi-font-body);
}

/* ── Header cockpit (sticky, 64px, dense) ── */
.cockpit-header {
  flex-shrink: 0;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--wi-space-md);
  background: var(--wi-surface-dim);
  border-block-end: 1px solid var(--wi-outline-variant);
  position: relative;
  z-index: 100;
}

.cockpit-header-left {
  display: flex;
  align-items: center;
  gap: var(--wi-space-md);
  min-width: 0;
}

.cockpit-brand {
  font-family: var(--wi-font-heading);
  font-weight: 700;
  font-size: var(--wi-label-sm);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--wi-on-bg);
  cursor: pointer;
  user-select: none;
  transition: color var(--ms-transition-fast);
}
.cockpit-brand:hover,
.cockpit-brand:focus-visible { color: var(--wi-primary-container); outline: none; }

.cockpit-sim-chip {
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  font-weight: 500;
  color: var(--wi-on-surface-variant);
  background: var(--wi-surface-container);
  padding: 4px 10px;
  border-radius: var(--wi-radius-sm);
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.cockpit-header-center {
  position: absolute;
  inset-inline-start: 50%;
  transform: translateX(-50%);
}
[dir="rtl"] .cockpit-header-center { transform: translateX(50%); }

.cockpit-view-switcher {
  display: flex;
  background: var(--wi-surface-container);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-md);
  padding: 3px;
  gap: 2px;
}

.cockpit-view-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  padding: 5px 12px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 500;
  color: var(--wi-on-surface-variant);
  cursor: pointer;
  border-radius: var(--wi-radius-sm);
  transition: background var(--ms-transition-fast), color var(--ms-transition-fast);
}
.cockpit-view-btn:hover { color: var(--wi-on-bg); }
.cockpit-view-btn:focus-visible {
  outline: 2px solid var(--wi-primary-container);
  outline-offset: 1px;
}

.cockpit-view-btn--active {
  background: var(--wi-surface-container-highest);
  color: var(--wi-on-bg);
  box-shadow: var(--wi-shadow-sm);
}

.cockpit-view-icon {
  font-size: 16px;
  line-height: 1;
}

.cockpit-header-right {
  display: flex;
  align-items: center;
  gap: var(--wi-space-md);
}

/* Phase progress (dots mint/outline-variant per spec) */
.cockpit-phase {
  display: flex;
  align-items: center;
  gap: var(--wi-space-xs);
}

.cockpit-phase-label {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-caption);
  font-weight: 600;
  color: var(--wi-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.cockpit-phase-dots {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.cockpit-phase-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--wi-radius-pill);
  background: var(--wi-outline-variant);
  transition: background var(--ms-transition-fast), transform var(--ms-transition-fast);
}
.cockpit-phase-dot--done { background: var(--wi-secondary); }
.cockpit-phase-dot--active {
  background: var(--wi-primary-container);
  transform: scale(1.3);
}

/* Status chip (Manrope 600 11px uppercase, colored par status) */
.cockpit-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px;
  font-family: var(--wi-font-body);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border-radius: var(--wi-radius-sm);
  border: 1px solid var(--wi-outline-variant);
  background: var(--wi-surface-container);
  color: var(--wi-on-surface-variant);
}

.cockpit-status-dot {
  width: 7px;
  height: 7px;
  border-radius: var(--wi-radius-pill);
  background: var(--wi-outline);
  flex-shrink: 0;
}

.cockpit-status--processing { color: var(--wi-primary-container); border-color: var(--wi-primary-container); }
.cockpit-status--processing .cockpit-status-dot { background: var(--wi-primary-container); animation: pulse 1.4s ease-in-out infinite; }

.cockpit-status--completed { color: var(--wi-secondary); border-color: var(--wi-secondary); }
.cockpit-status--completed .cockpit-status-dot { background: var(--wi-secondary); }

.cockpit-status--idle { color: var(--ms-peach); border-color: var(--ms-peach); }
.cockpit-status--idle .cockpit-status-dot { background: var(--ms-peach); }

.cockpit-status--error { color: var(--wi-error); border-color: var(--wi-error); }
.cockpit-status--error .cockpit-status-dot { background: var(--wi-error); }

/* @keyframes pulse factorisé dans styles/components.css */

/* ── Main split panels ── */
.content-area {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
  background: var(--wi-bg);
}

.panel-wrapper {
  height: 100%;
  overflow: hidden;
  transition:
    width 0.4s cubic-bezier(0.25, 0.8, 0.25, 1),
    opacity 0.3s ease,
    transform 0.3s ease;
  will-change: width, opacity, transform;
}

/* Left panel = Network Graph cockpit area (--wi-surface) */
.panel-wrapper.left {
  background: var(--wi-surface);
  border-inline-end: 1px solid var(--wi-outline-variant);
}

/* Right panel = Agent Configuration aside (--wi-surface-container) */
.panel-wrapper.right {
  background: var(--wi-surface-container);
  /* Indicateur d'étape active : barre verticale --wi-primary-container 4px,
     posée sur le bord d'attaque du panneau (logical inline-start). */
  border-inline-start: 4px solid var(--wi-primary-container);
}

/* En vue mono-panel (graph plein écran ou workbench), on retire les
   liserés qui n'ont plus de sens visuellement. */
.panel-wrapper.left[style*="100%"] {
  border-inline-end: none;
}
.panel-wrapper.right[style*="100%"] {
  border-inline-start: none;
}

/* ── Initial-fetch skeleton overlay ──
   Sits on top of the two panels until the first project + graph fetch
   resolves. Uses the global `.ms-skeleton` shimmer (defined in
   src/styles/components.css), which already opts out of animation under
   prefers-reduced-motion: reduce. */
.initial-skeleton {
  position: absolute;
  inset: 0;
  display: flex;
  z-index: 5;
  background: var(--wi-bg);
  pointer-events: none;
}

.skeleton-pane {
  flex: 1;
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.skeleton-pane-left {
  background: var(--wi-surface);
  border-inline-end: 1px solid var(--wi-outline-variant);
  position: relative;
}

.sk-toolbar {
  height: 32px;
  width: 60%;
  border-radius: 4px;
}

.sk-graph-area {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.sk-node {
  position: absolute;
  width: 56px;
  height: 56px;
  border-radius: 50%;
}
.sk-node-a { top: 18%; left: 22%; }
.sk-node-b { top: 28%; left: 60%; }
.sk-node-c { top: 60%; left: 30%; }
.sk-node-d { top: 70%; left: 65%; }

.sk-edge {
  position: absolute;
  height: 4px;
  border-radius: 2px;
  transform-origin: left center;
}
.sk-edge-1 {
  top: 26%;
  inset-inline-start: 28%;
  width: 32%;
  transform: rotate(8deg);
}
.sk-edge-2 {
  top: 64%;
  inset-inline-start: 36%;
  width: 28%;
  transform: rotate(-12deg);
}

.skeleton-pane-right {
  background: var(--wi-surface-container);
}

.sk-line {
  height: 14px;
  border-radius: 3px;
}
.sk-line-title { height: 22px; width: 70%; }
.sk-line-sub { width: 50%; }
.sk-line-section { width: 40%; height: 16px; margin-top: 12px; }

.sk-block {
  border-radius: 6px;
}
.sk-block-status { height: 96px; width: 100%; }
.sk-block-feed { height: 180px; width: 100%; }
.sk-block-market { height: 110px; width: 100%; }

/* ── Panneau actualités (US-058) ──
   Drawer "Trending Topics" en bas-droite. Stitch montre un FAB pill
   blanc texte sombre ; on conserve notre drawer rétractable existant
   (logique TrendingTopics.vue + showTrending), mais on aligne les
   surfaces sur les tokens --wi-* du cockpit. */
.sim-trending-drawer {
  position: fixed;
  bottom: 0;
  inset-inline-end: 0;
  width: min(360px, 90vw);
  max-height: 60vh;
  overflow-y: auto;
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-block-end: none;
  border-inline-end: none;
  border-radius: var(--wi-radius-card) var(--wi-radius-card) 0 0;
  box-shadow: var(--wi-shadow-lg);
  z-index: var(--ms-z-popover, 1200);
  padding: 0 0 12px;
}
.sim-trending-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  font-family: var(--wi-font-heading);
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--wi-primary);
  border-bottom: 1px solid var(--wi-outline-variant);
}
.sim-trending-close {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: var(--wi-on-surface-variant);
  line-height: 1;
  padding: 0 4px;
  transition: color var(--ms-transition-fast);
}
.sim-trending-close:hover { color: var(--wi-on-surface); }

/* FAB pill (Stitch montre un pill blanc texte sombre, posé bottom-right). */
.sim-trending-toggle {
  position: fixed;
  bottom: 24px;
  inset-inline-end: 24px;
  z-index: var(--ms-z-popover, 1200);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  height: 44px;
  padding: 0 16px;
  border-radius: var(--wi-radius-pill);
  border: 1px solid var(--wi-outline-variant);
  background: var(--wi-surface);
  color: var(--wi-on-surface);
  box-shadow: var(--wi-shadow-md);
  font-family: var(--wi-font-body);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: transform var(--ms-transition-fast), box-shadow var(--ms-transition-fast), border-color var(--ms-transition-fast);
}
.sim-trending-toggle:hover {
  transform: translateY(-2px);
  box-shadow: var(--ms-shadow-orange);
  border-color: var(--wi-primary-container);
}
.sim-trending-toggle:focus-visible {
  outline: 2px solid var(--wi-primary-container);
  outline-offset: 2px;
}
</style>
