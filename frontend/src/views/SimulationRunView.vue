<template>
  <!-- data-theme="dark" : cinema mode immersif pour l'analyste qui regarde
       la simulation se dérouler. Tokens --wi-* basculent automatiquement. -->
  <div class="sim-run" data-theme="dark">
    <!-- Slim progress bar (top of page, heartbeat visuel) -->
    <div
      class="sim-run__progress"
      :aria-label="$t('simulation.run.title')"
      role="progressbar"
      :aria-valuenow="progressPercent"
      aria-valuemin="0"
      aria-valuemax="100"
    >
      <div
        class="sim-run__progress-fill"
        :style="{ width: progressPercent + '%' }"
      ></div>
    </div>

    <!-- TopAppBar — Stitch "STRATOS EXECUTION" : brand + nav + heartbeat
         counter + actions. Nav-switcher conservé pour garder le contrat
         existant (graph / network / split / workbench). -->
    <header class="sim-run__topbar">
      <div class="sim-run__topbar-left">
        <div class="sim-run__brand" @click="router.push('/')">BASSIRA</div>
        <nav class="sim-run__nav" aria-label="Simulation views">
          <button
            v-for="mode in viewModes"
            :key="mode.key"
            class="sim-run__nav-link"
            :class="{ 'sim-run__nav-link--active': viewMode === mode.key }"
            @click="viewMode = mode.key"
          >
            {{ mode.label }}
          </button>
        </nav>
      </div>

      <!-- Round counter heartbeat (Outfit 700 64px) — centered absolutely
           pour rester aligné au pixel près quel que soit l'état des panneaux. -->
      <div class="sim-run__heartbeat" aria-live="polite">
        <span
          class="sim-run__heartbeat-dot"
          :class="{ 'sim-run__heartbeat-dot--pulse': isSimulating }"
          aria-hidden="true"
        ></span>
        <span class="sim-run__heartbeat-num">{{ formattedRound }}</span>
        <span
          v-if="totalRounds > 0"
          class="sim-run__heartbeat-total"
        >/ {{ String(totalRounds).padStart(2, '0') }}</span>
      </div>

      <div class="sim-run__topbar-right">
        <span class="sim-run__status" :class="`sim-run__status--${currentStatus}`">
          <span class="sim-run__status-dot" aria-hidden="true"></span>
          {{ statusText }}
        </span>
        <button
          v-if="isSimulating"
          class="sim-run__stop-btn"
          :disabled="stopInFlight"
          @click="handleStopSimulation"
        >
          <span v-if="stopInFlight" class="sim-run__spinner" aria-hidden="true"></span>
          {{ stopInFlight ? $t('simulation.run.paused') : $t('simulation.run.stop') }}
        </button>
      </div>
    </header>

    <!-- Main content : 2-panneau split (graph + workbench) inchangé -->
    <main class="sim-run__main">
      <div class="sim-run__panel sim-run__panel--left" :style="leftPanelStyle">
        <GraphPanel
          v-if="viewMode !== 'network'"
          :graph-data="graphData"
          :loading="graphLoading"
          :current-phase="3"
          :is-simulating="isSimulating"
          :simulation-id="currentSimulationId"
          @refresh="refreshGraph"
          @toggle-maximize="toggleMaximize('graph')"
        />
        <NetworkPanel
          v-else
          :simulation-id="currentSimulationId"
          :is-simulating="isSimulating"
        />
      </div>

      <div class="sim-run__panel sim-run__panel--right" :style="rightPanelStyle">
        <Step3Simulation
          :simulation-id="currentSimulationId"
          :max-rounds="maxRounds"
          :minutes-per-round="minutesPerRound"
          :project-data="projectData"
          :graph-data="graphData"
          :system-logs="systemLogs"
          @go-back="handleGoBack"
          @next-step="handleNextStep"
          @add-log="addLog"
          @update-status="updateStatus"
          @update-progress="handleProgress"
        />
      </div>
    </main>

    <!-- Phase complete toast (mint, bottom-right) — fade in 200ms -->
    <transition name="sim-run-toast">
      <div v-if="showCompleteToast" class="sim-run__toast" role="status">
        <span class="sim-run__toast-icon" aria-hidden="true"></span>
        <div class="sim-run__toast-body">
          <div class="sim-run__toast-title">{{ $t('simulation.run.completed') }}</div>
          <div class="sim-run__toast-sub">{{ $t('process.step3.events.totalEvents') }} — Round {{ currentRound }}</div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, watchEffect, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
import GraphPanel from '../components/GraphPanel.vue'
import NetworkPanel from '../components/NetworkPanel.vue'
import Step3Simulation from '../components/Step3Simulation.vue'
// Imports BeliefDriftChart / InfluenceLeaderboard préservés (utilisés par
// Step3Simulation en interne — ne pas retirer de la chaîne d'imports).
import BeliefDriftChart from '../components/BeliefDriftChart.vue' // eslint-disable-line no-unused-vars
import InfluenceLeaderboard from '../components/InfluenceLeaderboard.vue' // eslint-disable-line no-unused-vars
import { getProject, getGraphData } from '../api/graph'
import { getSimulation, getSimulationConfig, stopSimulation, closeSimulationEnv, getEnvStatus } from '../api/simulation'

const route = useRoute()
const router = useRouter()

// Props
const props = defineProps({
  simulationId: String
})

// Layout State
const viewMode = ref('split')

const viewModes = computed(() => [
  { key: 'graph',     label: t('simulation.view.stage.graph') },
  { key: 'network',   label: t('charts.network.title') },
  { key: 'split',     label: t('simulation.view.stage.config') },
  { key: 'workbench', label: t('simulation.view.stage.config') }
])

// Data State
const currentSimulationId = ref(route.params.simulationId)
// Get maxRounds from query params at initialization, ensuring child component gets the value immediately
const maxRounds = ref(route.query.maxRounds ? parseInt(route.query.maxRounds) : null)
const minutesPerRound = ref(30) // Default 30 minutes per round
const projectData = ref(null)
const graphData = ref(null)
const graphLoading = ref(false)
const systemLogs = ref([])
const currentStatus = ref('processing') // processing | completed | error

// Round heartbeat (header) — alimenté par Step3Simulation via update-progress.
// On garde des refs locales pour que le compteur reste indépendant de la
// remontée full runStatus (perf : pas besoin de tout l'objet pour 2 chiffres).
const currentRound = ref(0)
const totalRounds = ref(maxRounds.value || 0)
// US-138 — masque les compteurs avec "—" tant que le premier polling backend
// n'a pas répondu. Sans ce flag, le user revenant sur la page voyait "00 / 48"
// pendant 1-2s (init UI), confondu avec un worker mort qui ne polle plus.
const hasReceivedRealStatus = ref(false)

const stopInFlight = ref(false)
const showCompleteToast = ref(false)

// --- Computed Layout Styles ---
const leftPanelStyle = computed(() => {
  if (viewMode.value === 'graph' || viewMode.value === 'network') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'workbench') return { width: '0%', opacity: 0, transform: 'translateX(-20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

const rightPanelStyle = computed(() => {
  if (viewMode.value === 'workbench') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'graph' || viewMode.value === 'network') return { width: '0%', opacity: 0, transform: 'translateX(20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

// --- Status Computed ---
const statusText = computed(() => {
  if (currentStatus.value === 'error') return t('common.error')
  if (currentStatus.value === 'completed') return t('simulation.run.completed')
  return t('simulation.run.running')
})

const isSimulating = computed(() => currentStatus.value === 'processing')

const formattedRound = computed(() => {
  if (!hasReceivedRealStatus.value) return '—'
  return String(currentRound.value || 0).padStart(2, '0')
})

const progressPercent = computed(() => {
  if (!hasReceivedRealStatus.value) return 0
  const total = totalRounds.value || maxRounds.value || 0
  if (!total) return 0
  return Math.min(100, Math.round((currentRound.value / total) * 100))
})

// --- Helpers ---
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + '.' + new Date().getMilliseconds().toString().padStart(3, '0')
  systemLogs.value.push({ time, msg })
  if (systemLogs.value.length > 200) {
    systemLogs.value.shift()
  }
}

const updateStatus = (status) => {
  currentStatus.value = status
}

// Reçoit le tick de Step3Simulation (mirror du runStatus côté enfant).
// US-138 — runnerStatus 'loading' est le sentinel envoyé pendant le mount
// avant que le premier polling backend ait répondu. Tant qu'on n'a pas reçu
// un statut réel, on n'écrit pas dans currentRound (sinon le heartbeat
// affiche prématurément "00" au lieu du sentinel "—").
const handleProgress = ({ currentRound: cr, totalRounds: tr, runnerStatus: rs }) => {
  if (rs && rs !== 'loading') {
    hasReceivedRealStatus.value = true
  }
  if (typeof cr === 'number') currentRound.value = cr
  if (typeof tr === 'number' && tr > 0) totalRounds.value = tr
}

// Stop simulation depuis le header (raccourci au bouton Pause de Step3).
// Réutilise la même API qu'handleGoBack — pas de duplication de logique.
const handleStopSimulation = async () => {
  if (stopInFlight.value) return
  stopInFlight.value = true
  addLog('Stop requested from top bar — closing simulation environment...')
  try {
    const envStatusRes = await getEnvStatus({ simulation_id: currentSimulationId.value })
    if (envStatusRes.success && envStatusRes.data?.env_alive) {
      try {
        await closeSimulationEnv({ simulation_id: currentSimulationId.value, timeout: 10 })
        addLog('Simulation environment closed')
      } catch (closeErr) {
        addLog('Graceful close failed, attempting force stop...')
        await stopSimulation({ simulation_id: currentSimulationId.value })
        addLog('Simulation force stopped')
      }
    } else if (isSimulating.value) {
      await stopSimulation({ simulation_id: currentSimulationId.value })
      addLog('Simulation stopped')
    }
    currentStatus.value = 'completed'
  } catch (err) {
    addLog(`Stop failed: ${err.message}`)
  } finally {
    stopInFlight.value = false
  }
}

// --- Layout Methods ---
const toggleMaximize = (target) => {
  if (viewMode.value === target) {
    viewMode.value = 'split'
  } else {
    viewMode.value = target
  }
}

const handleGoBack = async () => {
  // Before returning to Step 2, close the running simulation
  addLog('Preparing to return to Step 2, closing simulation...')

  // Stop polling
  stopGraphRefresh()

  try {
    // Try to gracefully close the simulation environment first
    const envStatusRes = await getEnvStatus({ simulation_id: currentSimulationId.value })

    if (envStatusRes.success && envStatusRes.data?.env_alive) {
      addLog('Closing simulation environment...')
      try {
        await closeSimulationEnv({
          simulation_id: currentSimulationId.value,
          timeout: 10
        })
        addLog('Simulation environment closed')
      } catch (closeErr) {
        addLog(`Failed to close simulation environment, attempting force stop...`)
        try {
          await stopSimulation({ simulation_id: currentSimulationId.value })
          addLog('Simulation force stopped')
        } catch (stopErr) {
          addLog(`Force stop failed: ${stopErr.message}`)
        }
      }
    } else {
      // Environment not running, check if process needs to be stopped
      if (isSimulating.value) {
        addLog('Stopping simulation process...')
        try {
          await stopSimulation({ simulation_id: currentSimulationId.value })
          addLog('Simulation stopped')
        } catch (err) {
          addLog(`Failed to stop simulation: ${err.message}`)
        }
      }
    }
  } catch (err) {
    addLog(`Failed to check simulation status: ${err.message}`)
  }

  // Return to Step 2 (Agent Setup)
  router.push({ name: 'Simulation', params: { simulationId: currentSimulationId.value } })
}

const handleNextStep = () => {
  // Step3Simulation component handles report generation and routing directly
  // This method serves as a fallback
  addLog('Entering Step 4: Report Generation')
}

// --- Data Logic ---
const loadSimulationData = async () => {
  try {
    addLog(`Loading simulation data: ${currentSimulationId.value}`)

    // Get simulation info
    const simRes = await getSimulation(currentSimulationId.value)
    if (simRes.success && simRes.data) {
      const simData = simRes.data

      // Get simulation config to obtain minutes_per_round
      try {
        const configRes = await getSimulationConfig(currentSimulationId.value)
        if (configRes.success && configRes.data?.time_config?.minutes_per_round) {
          minutesPerRound.value = configRes.data.time_config.minutes_per_round
          addLog(`Time config: ${minutesPerRound.value} minutes per round`)
        }
      } catch (configErr) {
        addLog(`Failed to get time config, using default: ${minutesPerRound.value} min/round`)
      }

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
  }
}

const loadGraph = async (graphId) => {
  // When simulating, auto-refresh without showing fullscreen loading to avoid flicker
  // Show loading for manual refresh or initial load
  if (!isSimulating.value) {
    graphLoading.value = true
  }

  try {
    const res = await getGraphData(graphId)
    if (res.success) {
      graphData.value = res.data
      if (!isSimulating.value) {
        addLog('Graph data loaded successfully')
      }
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

// --- Auto Refresh Logic ---
let graphRefreshTimer = null

const startGraphRefresh = () => {
  if (graphRefreshTimer) return
  addLog('Enabled real-time graph refresh (30s)')
  // Refresh immediately, then every 30 seconds
  graphRefreshTimer = setInterval(refreshGraph, 30000)
}

const stopGraphRefresh = () => {
  if (graphRefreshTimer) {
    clearInterval(graphRefreshTimer)
    graphRefreshTimer = null
    addLog('Stopped real-time graph refresh')
  }
}

watch(isSimulating, (newValue) => {
  if (newValue) {
    startGraphRefresh()
  } else {
    stopGraphRefresh()
  }
}, { immediate: true })

// Phase complete toast — fire when status flips to completed.
// Auto-dismiss after 4s, accessible via aria-live (role=status sur le toast).
let toastTimer = null
watch(currentStatus, (status) => {
  if (status === 'completed') {
    showCompleteToast.value = true
    if (toastTimer) clearTimeout(toastTimer)
    toastTimer = setTimeout(() => {
      showCompleteToast.value = false
    }, 4000)
  }
})

watchEffect(() => {
  const status = currentStatus.value
  const dot = status === 'processing' ? '🟠' : status === 'error' ? '🔴' : status === 'completed' ? '🟢' : ''
  document.title = dot ? `${dot} (3/4) Bassira` : '(3/4) Bassira'
})

onMounted(() => {
  addLog('SimulationRunView initialized')

  // Log maxRounds config (value obtained from query params at initialization)
  if (maxRounds.value) {
    addLog(`Custom simulation rounds: ${maxRounds.value}`)
  }

  loadSimulationData()
})

onUnmounted(() => {
  stopGraphRefresh()
  if (toastTimer) clearTimeout(toastTimer)
})
</script>

<style scoped>
/* ───────────── Sim Run — Cinema dark cockpit ─────────────
   Toutes les couleurs sont issues des tokens --wi-* (palette Warm
   Intelligence) en variant data-theme="dark" forcé sur la racine.
   Aucun hex hardcodé. Tous les composants enfants conservent leur
   propre style — on ne touche qu'au cadre. */

.sim-run {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--wi-surface-dim);
  color: var(--wi-on-surface);
  font-family: var(--wi-font-body);
  overflow: hidden;
  position: relative;
}

/* ─── Slim progress bar (heartbeat visuel global) ─── */
.sim-run__progress {
  position: absolute;
  top: 0;
  inset-inline: 0;
  height: 3px;
  background: var(--wi-outline-variant);
  opacity: 0.35;
  z-index: 60;
  pointer-events: none;
}
.sim-run__progress-fill {
  height: 100%;
  background: var(--wi-primary-container);
  transition: width 300ms cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 12px var(--wi-primary-container);
}

/* ─── TopAppBar ─── */
.sim-run__topbar {
  position: relative;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--wi-space-sm) var(--wi-space-lg);
  padding-top: calc(var(--wi-space-sm) + 4px); /* leaves room for progress bar */
  background: var(--wi-surface-dim);
  border-bottom: 1px solid var(--wi-outline-variant);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.sim-run__topbar-left {
  display: flex;
  align-items: center;
  gap: var(--wi-space-md);
  min-width: 0;
}

.sim-run__brand {
  font-family: var(--wi-font-heading);
  font-weight: 700;
  font-size: var(--wi-h3-size);
  letter-spacing: -0.01em;
  text-transform: uppercase;
  color: var(--wi-primary-container);
  cursor: pointer;
  transition: opacity var(--ms-transition, 200ms ease);
}
.sim-run__brand:hover { opacity: 0.85; }

.sim-run__nav {
  display: none;
  gap: var(--wi-space-md);
}
@media (min-width: 920px) {
  .sim-run__nav { display: flex; }
}

.sim-run__nav-link {
  background: transparent;
  border: none;
  padding: 4px 0;
  cursor: pointer;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: var(--wi-label-sm-weight);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--wi-outline);
  border-bottom: 2px solid transparent;
  transition: color var(--ms-transition, 200ms ease), border-color var(--ms-transition, 200ms ease);
}
.sim-run__nav-link:hover {
  color: var(--wi-primary-container);
}
.sim-run__nav-link--active {
  color: var(--wi-primary-container);
  border-bottom-color: var(--wi-primary-container);
}

/* ─── Heartbeat round counter (centered, Outfit 700 64px) ─── */
.sim-run__heartbeat {
  position: absolute;
  inset-inline-start: 50%;
  transform: translateX(-50%);
  top: 50%;
  margin-top: -34px; /* offset for the progress bar */
  display: flex;
  align-items: center;
  gap: var(--wi-space-xs);
  font-family: var(--wi-font-heading);
  font-weight: 700;
  font-size: 64px;
  line-height: 1;
  color: var(--wi-primary-container);
  pointer-events: none;
  letter-spacing: -0.02em;
}

.sim-run__heartbeat-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--wi-primary-container);
  flex-shrink: 0;
  box-shadow: 0 0 0 0 var(--wi-primary-container);
}
.sim-run__heartbeat-dot--pulse {
  animation: sim-run-pulse 1.6s ease-in-out infinite;
}

.sim-run__heartbeat-num {
  font-variant-numeric: tabular-nums;
}

.sim-run__heartbeat-total {
  font-size: 24px;
  font-weight: 500;
  color: var(--wi-outline);
  margin-inline-start: 4px;
  letter-spacing: 0;
}

@keyframes sim-run-pulse {
  0%   { box-shadow: 0 0 0 0 var(--wi-primary-container); opacity: 1; }
  70%  { box-shadow: 0 0 0 14px transparent; opacity: 0.6; }
  100% { box-shadow: 0 0 0 0 transparent; opacity: 1; }
}

/* ─── Right cluster (status + stop) ─── */
.sim-run__topbar-right {
  display: flex;
  align-items: center;
  gap: var(--wi-space-sm);
}

.sim-run__status {
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-xs);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: var(--wi-label-sm-weight);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--wi-outline);
}
.sim-run__status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--wi-outline);
}
.sim-run__status--processing { color: var(--wi-primary-container); }
.sim-run__status--processing .sim-run__status-dot {
  background: var(--wi-primary-container);
  animation: sim-run-pulse 1.2s ease-in-out infinite;
}
.sim-run__status--completed { color: var(--wi-secondary-container); }
.sim-run__status--completed .sim-run__status-dot { background: var(--wi-secondary-container); }
.sim-run__status--error { color: var(--wi-error); }
.sim-run__status--error .sim-run__status-dot { background: var(--wi-error); }

/* Stop simulation : ghost button bordé terracotta (= --wi-on-primary-container)
   selon le brief ; l'inject d'événement reste exposé par Step3Simulation
   (action "Director Mode") pour préserver la logique existante. */
.sim-run__stop-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-xs);
  background: transparent;
  color: var(--wi-on-primary-container);
  border: 1px solid var(--wi-on-primary-container);
  padding: 8px 16px;
  border-radius: var(--wi-radius-interactive);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
  transition: background var(--ms-transition, 200ms ease), color var(--ms-transition, 200ms ease);
}
.sim-run__stop-btn:hover:not(:disabled) {
  background: var(--wi-on-primary-container);
  color: var(--wi-on-primary);
}
.sim-run__stop-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.sim-run__spinner {
  width: 12px;
  height: 12px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: sim-run-spin 0.8s linear infinite;
}
@keyframes sim-run-spin { to { transform: rotate(360deg); } }

/* ─── Main split panels (logique inchangée) ─── */
.sim-run__main {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
  background: var(--wi-bg);
}

.sim-run__panel {
  height: 100%;
  overflow: hidden;
  transition:
    width 0.4s cubic-bezier(0.25, 0.8, 0.25, 1),
    opacity 0.3s ease,
    transform 0.3s ease;
  will-change: width, opacity, transform;
}
.sim-run__panel--left {
  border-inline-end: 1px solid var(--wi-outline-variant);
}

/* ─── Phase complete toast (mint, bottom-right) ─── */
.sim-run__toast {
  position: fixed;
  bottom: var(--wi-space-lg);
  inset-inline-end: var(--wi-space-lg);
  z-index: 1400;
  display: flex;
  align-items: center;
  gap: var(--wi-space-sm);
  padding: var(--wi-space-sm) var(--wi-space-md);
  background: var(--wi-surface);
  border: 1px solid var(--wi-secondary);
  border-radius: var(--wi-radius-interactive);
  box-shadow: var(--wi-shadow-lg);
  min-width: 240px;
}
.sim-run__toast-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--wi-secondary-container);
  flex-shrink: 0;
  position: relative;
}
/* Pure CSS checkmark — pas d'emoji conformément au standard Bassira. */
.sim-run__toast-icon::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 10px;
  height: 5px;
  border-inline-start: 2px solid var(--wi-on-secondary-container);
  border-block-end: 2px solid var(--wi-on-secondary-container);
  transform: translate(-50%, -65%) rotate(-45deg);
}
.sim-run__toast-body { display: flex; flex-direction: column; gap: 2px; }
.sim-run__toast-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-label-sm);
  font-weight: 600;
  color: var(--wi-secondary-container);
  letter-spacing: 0.01em;
}
.sim-run__toast-sub {
  font-size: var(--wi-caption);
  color: var(--wi-outline);
  font-family: var(--wi-font-body);
}

/* Toast transition (200ms fade-in selon le brief) */
.sim-run-toast-enter-active,
.sim-run-toast-leave-active {
  transition: opacity 200ms ease-out, transform 200ms ease-out;
}
.sim-run-toast-enter-from,
.sim-run-toast-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

/* ─── Reduced motion ─── */
@media (prefers-reduced-motion: reduce) {
  .sim-run__heartbeat-dot--pulse,
  .sim-run__status--processing .sim-run__status-dot {
    animation: none;
  }
  .sim-run__panel,
  .sim-run__progress-fill,
  .sim-run__stop-btn,
  .sim-run-toast-enter-active,
  .sim-run-toast-leave-active {
    transition: none;
  }
}
</style>
