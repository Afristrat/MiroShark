<template>
  <div class="main-view">
    <!-- Header -->
    <header class="app-header">
      <div class="header-left">
        <div class="brand" @click="router.push('/')">MIROSHARK</div>
      </div>
      
      <div class="header-center">
        <div class="view-switcher">
          <button
            v-for="mode in ['graph', 'split', 'workbench']"
            :key="mode"
            class="switch-btn"
            :class="{ active: viewMode === mode }"
            @click="viewMode = mode"
          >
            {{ { graph: $t('simulation.view.stage.graph'), split: $t('simulation.view.stage.config'), workbench: $t('simulation.view.stage.config') }[mode] }}
          </button>
        </div>
      </div>

      <div class="header-right">
        <div class="workflow-step">
          <span class="step-num">{{ $t('process.step2.step1.title') }}</span>
          <span class="step-name">{{ $t('simulation.view.stage.config') }}</span>
        </div>
        <div class="step-divider"></div>
        <span class="status-indicator" :class="statusClass">
          <span class="dot"></span>
          {{ statusText }}
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
          :graphData="graphData"
          :loading="graphLoading"
          :currentPhase="2"
          :simulationId="currentSimulationId"
          @refresh="refreshGraph"
          @toggle-maximize="toggleMaximize('graph')"
        />
      </div>

      <!-- Right Panel: Step2 Agent Setup -->
      <div class="panel-wrapper right" :style="rightPanelStyle">
        <Step2EnvSetup
          :simulationId="currentSimulationId"
          :projectData="projectData"
          :graphData="graphData"
          :systemLogs="systemLogs"
          @go-back="handleGoBack"
          @next-step="handleNextStep"
          @add-log="addLog"
          @update-status="updateStatus"
          @update-phase="updatePhase"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watchEffect, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
import GraphPanel from '../components/GraphPanel.vue'
import Step2EnvSetup from '../components/Step2EnvSetup.vue'
import { getProject, getGraphData } from '../api/graph'
import { getSimulation, stopSimulation, getEnvStatus, closeSimulationEnv } from '../api/simulation'

const route = useRoute()
const router = useRouter()

// Props
const props = defineProps({
  simulationId: String
})

// Layout State
const viewMode = ref('split')

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
  document.title = `${dot} (2/4) ${statusText.value} · MiroShark`
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
.main-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #FAFAFA;
  overflow: hidden;
  font-family: var(--font-display);
}

/* Header */
.app-header {
  height: 60px;
  border-bottom: 2px solid rgba(10,10,10,0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 22px;
  background: #0A0A0A;
  z-index: 100;
  position: relative;
}

.brand {
  font-family: var(--font-mono);
  font-weight: 800;
  font-size: 18px;
  letter-spacing: 3px;
  text-transform: uppercase;
  cursor: pointer;
  color: #FAFAFA;
}

.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.view-switcher {
  display: flex;
  background: rgba(250,250,250,0.08);
  padding: 4px;
  gap: 4px;
}

.switch-btn {
  border: 2px solid transparent;
  background: transparent;
  padding: 6px 16px;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 3px;
  color: rgba(250,250,250,0.5);
  cursor: pointer;
  transition: all 0.2s;
}

.switch-btn.active {
  background: #0A0A0A;
  color: #FAFAFA;
  border: 2px solid #FF6B1A;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.workflow-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.step-num {
  font-family: var(--font-mono);
  font-weight: 700;
  color: rgba(250,250,250,0.4);
}

.step-name {
  font-weight: 700;
  color: #FAFAFA;
}

.step-divider {
  width: 1px;
  height: 14px;
  background-color: rgba(250,250,250,0.12);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 3px;
  color: rgba(250,250,250,0.5);
  font-weight: 500;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(250,250,250,0.2);
}

.status-indicator.processing .dot { background: #FF6B1A; animation: pulse 1s infinite; }
.status-indicator.completed .dot { background: #43C165; }
.status-indicator.idle .dot { background: #FFB347; }
.status-indicator.error .dot { background: #FF4444; }

@keyframes pulse { 50% { opacity: 0.5; } }

/* Content */
.content-area {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
}

.panel-wrapper {
  height: 100%;
  overflow: hidden;
  transition: width 0.4s cubic-bezier(0.25, 0.8, 0.25, 1), opacity 0.3s ease, transform 0.3s ease;
  will-change: width, opacity, transform;
}

.panel-wrapper.left {
  border-right: 2px solid rgba(10,10,10,0.08);
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
  background: #FAFAFA;
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
  border-right: 2px solid rgba(10, 10, 10, 0.08);
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
  left: 28%;
  width: 32%;
  transform: rotate(8deg);
}
.sk-edge-2 {
  top: 64%;
  left: 36%;
  width: 28%;
  transform: rotate(-12deg);
}

.skeleton-pane-right {
  background: #FAFAFA;
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
</style>

