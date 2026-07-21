<template>
  <div class="main-view" :class="{ 'is-mobile': isMobile, 'is-tablet': isTablet }">
    <!-- Dense Header — Tier 2 Analyst console -->
    <header class="app-header">
      <!-- LEFT: Brand + project context (Sim ID + LIVE) -->
      <div class="header-left">
        <button class="brand" type="button" @click="router.push('/')" :title="$t('common.home', 'Home')">
          <span class="brand-mark" aria-hidden="true">⬡</span>
          <span class="brand-name">BASSIRA</span>
        </button>
        <div class="header-divider" aria-hidden="true"></div>
        <div class="project-context">
          <div class="project-name" :title="projectTitle">{{ projectTitle }}</div>
          <div class="project-meta">
            <span class="sim-id">{{ simId }}</span>
            <span class="status-pill" :class="statusClass">
              <span class="status-dot"></span>
              {{ statusText }}
            </span>
          </div>
        </div>
      </div>

      <!-- CENTER: View switcher (icon + label) -->
      <nav class="view-switcher" :aria-label="$t('common.view', 'View')">
        <button
          v-for="mode in viewModes"
          :key="mode.id"
          type="button"
          class="switch-btn"
          :class="{ active: viewMode === mode.id }"
          :aria-pressed="viewMode === mode.id"
          @click="viewMode = mode.id"
        >
          <span class="switch-icon" aria-hidden="true" v-html="mode.icon"></span>
          <span class="switch-label">{{ mode.label }}</span>
        </button>
      </nav>

      <!-- RIGHT: Workflow step + actions -->
      <div class="header-right">
        <div class="workflow-step" :title="stepNames[currentStep - 1]">
          <span class="step-num">{{ currentStep }} / 4</span>
          <span class="step-name">{{ stepNames[currentStep - 1] }}</span>
        </div>
        <div class="header-divider" aria-hidden="true"></div>
        <div class="kbd-hint">
          <span class="kbd">⌘S</span>
          <span class="kbd-label">Save</span>
        </div>
      </div>
    </header>

    <!-- Main Content Area — Resizable split workspace -->
    <main class="content-area" :data-mode="viewMode">
      <!-- Left Panel: Graph -->
      <section
        v-show="viewMode !== 'workbench'"
        class="panel-wrapper left"
        :style="leftPanelStyle"
        :aria-label="$t('charts.graph.title', 'Network Topology')"
      >
        <GraphPanel
          :graph-data="graphData"
          :loading="graphLoading"
          :current-phase="currentPhase"
          @refresh="refreshGraph"
          @toggle-maximize="toggleMaximize('graph')"
        />
      </section>

      <!-- Resize divider — only in split mode on desktop -->
      <div
        v-if="viewMode === 'split' && !isMobile"
        class="resize-divider"
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize panels"
        tabindex="0"
        @mousedown="startResize"
        @keydown="onResizeKey"
      >
        <div class="resize-grip" aria-hidden="true"></div>
      </div>

      <!-- Right Panel: Step Components -->
      <section
        v-show="viewMode !== 'graph'"
        class="panel-wrapper right"
        :style="rightPanelStyle"
        :aria-label="$t('common.workbench', 'Workbench')"
      >
        <!-- US-040 — Step 1.5 review banner. Shown only when the graph
             build has finished and the user has not yet entered Step 2. -->
        <div
          v-if="currentStep === 1 && currentPhase >= 2 && currentProjectId !== 'new'"
          class="review-entities-banner"
        >
          <div class="reb-text">
            <span class="reb-pill">1.5</span>
            <div class="reb-body">
              <div class="reb-title">{{ $t('process.review.banner.title') }}</div>
              <div class="reb-desc">{{ $t('process.review.banner.description') }}</div>
            </div>
          </div>
          <div class="reb-actions">
            <button class="ms-btn ms-btn-secondary ms-btn--sm" type="button" @click="goToReviewEntities">
              {{ $t('process.review.banner.cta') }} →
            </button>
          </div>
        </div>

        <!-- Step 1: Graph Construction -->
        <Step1GraphBuild
          v-if="currentStep === 1"
          :current-phase="currentPhase"
          :project-data="projectData"
          :ontology-progress="ontologyProgress"
          :build-progress="buildProgress"
          :graph-data="graphData"
          :system-logs="systemLogs"
          @next-step="handleNextStep"
        />
        <!-- Step 2: Agent Setup -->
        <Step2EnvSetup
          v-else-if="currentStep === 2"
          :project-data="projectData"
          :graph-data="graphData"
          :system-logs="systemLogs"
          @go-back="handleGoBack"
          @next-step="handleNextStep"
          @add-log="addLog"
        />
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watchEffect, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GraphPanel from '../components/GraphPanel.vue'
import Step1GraphBuild from '../components/Step1GraphBuild.vue'
import Step2EnvSetup from '../components/Step2EnvSetup.vue'
import { generateOntology, getProject, buildGraph, getTaskStatus, getGraphData } from '../api/graph'
import { getPendingUpload, clearPendingUpload } from '../store/pendingUpload'

const route = useRoute()
const router = useRouter()

// Layout State
const viewMode = ref('split') // graph | split | workbench

// View switcher tabs (Stitch dense console — icon + label)
const viewModes = [
  {
    id: 'graph',
    label: 'Graph',
    icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><path d="M12 7v4M12 11l-7 8M12 11l7 8"/></svg>'
  },
  {
    id: 'split',
    label: 'Split',
    icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="8" height="16" rx="1"/><rect x="13" y="4" width="8" height="16" rx="1"/></svg>'
  },
  {
    id: 'workbench',
    label: 'Workbench',
    icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/></svg>'
  }
]

// Step State
const currentStep = ref(1) // 1: Graph Construction, 2: Agent Setup, 3: Start Simulation, 4: Report Generation, 5: Deep Interaction
const stepNames = ['Graph Construction', 'Agent Setup', 'Start Simulation', 'Report Generation']

// Data State
const currentProjectId = ref(route.params.projectId)
const loading = ref(false)
const graphLoading = ref(false)
const error = ref('')
const projectData = ref(null)
const graphData = ref(null)
const currentPhase = ref(-1) // -1: Upload, 0: Ontology, 1: Build, 2: Complete
const ontologyProgress = ref(null)
const buildProgress = ref(null)
const systemLogs = ref([])

// Polling timers
let pollTimer = null
let graphPollTimer = null
let recoveredOrphanedBuild = false

// --- Project context (header dense info) ---
const projectTitle = computed(() => {
  return projectData.value?.name
    || projectData.value?.title
    || (currentProjectId.value && currentProjectId.value !== 'new'
        ? `Project ${String(currentProjectId.value).slice(0, 8)}`
        : 'New Simulation')
})

const simId = computed(() => {
  const pid = currentProjectId.value
  if (!pid || pid === 'new') return 'SIM-NEW'
  return `SIM-${String(pid).slice(0, 8).toUpperCase()}`
})

// --- Resizable split (horizontal drag between left/right panels) ---
const splitRatio = ref(0.5)            // 0..1 — left panel proportion in split mode
const isResizing = ref(false)
const MIN_RATIO = 0.2
const MAX_RATIO = 0.8

const startResize = (event) => {
  event.preventDefault()
  isResizing.value = true
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('mousemove', onResize)
  window.addEventListener('mouseup', stopResize)
}

const onResize = (event) => {
  if (!isResizing.value) return
  const container = document.querySelector('.main-view .content-area')
  if (!container) return
  const rect = container.getBoundingClientRect()
  const ratio = (event.clientX - rect.left) / rect.width
  splitRatio.value = Math.min(MAX_RATIO, Math.max(MIN_RATIO, ratio))
}

const stopResize = () => {
  isResizing.value = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  window.removeEventListener('mousemove', onResize)
  window.removeEventListener('mouseup', stopResize)
}

const onResizeKey = (event) => {
  // Keyboard accessibility: arrow keys nudge the divider in 5% steps.
  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    splitRatio.value = Math.max(MIN_RATIO, splitRatio.value - 0.05)
  } else if (event.key === 'ArrowRight') {
    event.preventDefault()
    splitRatio.value = Math.min(MAX_RATIO, splitRatio.value + 0.05)
  } else if (event.key === 'Home') {
    event.preventDefault()
    splitRatio.value = 0.5
  }
}

// --- Responsive breakpoints ---
const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1280)
const isMobile = computed(() => windowWidth.value < 720)
const isTablet = computed(() => windowWidth.value >= 720 && windowWidth.value < 1080)
const onResizeWindow = () => { windowWidth.value = window.innerWidth }

// --- Computed Layout Styles ---
const leftPanelStyle = computed(() => {
  if (isMobile.value) {
    // Mobile: tabs (single panel visible at a time)
    if (viewMode.value === 'graph') return { width: '100%' }
    if (viewMode.value === 'workbench') return { width: '0%', opacity: 0 }
    return { width: '100%' }
  }
  if (isTablet.value && viewMode.value === 'split') {
    // Tablet: stack — left takes full width above
    return { width: '100%' }
  }
  if (viewMode.value === 'graph') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'workbench') return { width: '0%', opacity: 0, transform: 'translateX(-20px)' }
  return { width: `${splitRatio.value * 100}%`, opacity: 1, transform: 'translateX(0)' }
})

const rightPanelStyle = computed(() => {
  if (isMobile.value) {
    if (viewMode.value === 'workbench') return { width: '100%' }
    if (viewMode.value === 'graph') return { width: '0%', opacity: 0 }
    return { width: '100%' }
  }
  if (isTablet.value && viewMode.value === 'split') {
    return { width: '100%' }
  }
  if (viewMode.value === 'workbench') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'graph') return { width: '0%', opacity: 0, transform: 'translateX(20px)' }
  return { width: `${(1 - splitRatio.value) * 100}%`, opacity: 1, transform: 'translateX(0)' }
})

// --- Status Computed ---
const statusClass = computed(() => {
  if (error.value) return 'error'
  if (currentPhase.value >= 2) return 'completed'
  if (currentPhase.value >= 0) return 'processing'
  return 'idle'
})

const statusText = computed(() => {
  if (error.value) return 'Error'
  if (currentPhase.value >= 2) return 'Ready'
  if (currentPhase.value === 1) return 'Building Graph'
  if (currentPhase.value === 0) return 'Generating Ontology'
  return 'Idle'
})

// --- Helpers ---
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + '.' + new Date().getMilliseconds().toString().padStart(3, '0')
  systemLogs.value.push({ time, msg })
  // Keep last 100 logs
  if (systemLogs.value.length > 100) {
    systemLogs.value.shift()
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

const handleNextStep = (params = {}) => {
  if (currentStep.value < 4) {
    currentStep.value++
    addLog(`Entering Step ${currentStep.value}: ${stepNames[currentStep.value - 1]}`)
    
    // If entering Step 3 from Step 2, log the simulation round configuration
    if (currentStep.value === 3 && params.maxRounds) {
      addLog(`Custom simulation rounds: ${params.maxRounds} rounds`)
    }
  }
}

const handleGoBack = () => {
  if (currentStep.value > 1) {
    currentStep.value--
    addLog(`Returning to Step ${currentStep.value}: ${stepNames[currentStep.value - 1]}`)
  }
}

// --- Data Logic ---

const initProject = async () => {
  addLog('Project view initialized.')
  if (currentProjectId.value === 'new') {
    await handleNewProject()
  } else {
    await loadProject()
  }
}

const handleNewProject = async () => {
  const pending = getPendingUpload()
  const hasFiles = pending.files.length > 0
  const hasTemplate = !!pending.templateSeedText
  const hasUrlDocs = pending.urlDocs && pending.urlDocs.length > 0
  if (!pending.isPending || (!hasFiles && !hasTemplate && !hasUrlDocs)) {
    error.value = 'No pending files found.'
    addLog('Error: No pending files found for new project.')
    return
  }

  try {
    loading.value = true
    currentPhase.value = 0
    ontologyProgress.value = { message: 'Uploading and analyzing docs...' }
    addLog(hasTemplate
      ? `Starting from template "${pending.templateName}"...`
      : hasUrlDocs && !hasFiles
        ? `Starting from ${pending.urlDocs.length} URL document(s)...`
        : 'Starting ontology generation: Uploading files...')

    const formData = new FormData()
    if (hasFiles) {
      pending.files.forEach(f => formData.append('files', f))
    } else if (hasTemplate) {
      const blob = new Blob([pending.templateSeedText], { type: 'text/markdown' })
      const fileName = `${(pending.templateName || 'template').replace(/\s+/g, '_')}.md`
      formData.append('files', blob, fileName)
    }
    if (hasUrlDocs) {
      formData.append('url_docs', JSON.stringify(pending.urlDocs))
    }
    formData.append('simulation_requirement', pending.simulationRequirement)
    const projectName = pending.templateName || pending.files[0]?.name || pending.urlDocs[0]?.title
    if (projectName) formData.append('project_name', projectName)
    
    const res = await generateOntology(formData)
    if (res.success) {
      clearPendingUpload()
      currentProjectId.value = res.data.project_id
      projectData.value = res.data
      
      router.replace({ name: 'Process', params: { projectId: res.data.project_id } })
      ontologyProgress.value = null
      addLog(`Ontology generated successfully for project ${res.data.project_id}`)
      await startBuildGraph()
    } else {
      error.value = res.error || 'Ontology generation failed'
      addLog(`Error generating ontology: ${error.value}`)
    }
  } catch (err) {
    error.value = err.message
    addLog(`Exception in handleNewProject: ${err.message}`)
  } finally {
    loading.value = false
  }
}

const loadProject = async () => {
  try {
    loading.value = true
    addLog(`Loading project ${currentProjectId.value}...`)
    const res = await getProject(currentProjectId.value)
    if (res.success) {
      projectData.value = res.data
      updatePhaseByStatus(res.data.status)
      addLog(`Project loaded. Status: ${res.data.status}`)
      
      if (res.data.status === 'ontology_generated' && !res.data.graph_id) {
        await startBuildGraph()
      } else if (res.data.status === 'graph_building' && res.data.graph_build_task_id) {
        currentPhase.value = 1
        startPollingTask(res.data.graph_build_task_id)
        startGraphPolling()
      } else if (res.data.status === 'graph_completed' && res.data.graph_id) {
        currentPhase.value = 2
        await loadGraph(res.data.graph_id)
      }
    } else {
      error.value = res.error
      addLog(`Error loading project: ${res.error}`)
    }
  } catch (err) {
    error.value = err.message
    addLog(`Exception in loadProject: ${err.message}`)
  } finally {
    loading.value = false
  }
}

const updatePhaseByStatus = (status) => {
  switch (status) {
    case 'created':
    case 'ontology_generated': currentPhase.value = 0; break;
    case 'graph_building': currentPhase.value = 1; break;
    case 'graph_completed': currentPhase.value = 2; break;
    case 'failed': error.value = 'Project failed'; break;
  }
}

const startBuildGraph = async ({ force = false } = {}) => {
  try {
    currentPhase.value = 1
    buildProgress.value = { progress: 0, message: 'Starting build...' }
    addLog('Initiating graph build...')
    
    const res = await buildGraph({ project_id: currentProjectId.value, force })
    if (res.success) {
      addLog(`Graph build task started. Task ID: ${res.data.task_id}`)
      startGraphPolling()
      startPollingTask(res.data.task_id)
    } else {
      error.value = res.error
      addLog(`Error starting build: ${res.error}`)
    }
  } catch (err) {
    error.value = err.message
    addLog(`Exception in startBuildGraph: ${err.message}`)
  }
}

const startGraphPolling = () => {
  addLog('Started polling for graph data...')
  fetchGraphData()
  graphPollTimer = setInterval(fetchGraphData, 10000)
}

const fetchGraphData = async () => {
  try {
    // Refresh project info to check for graph_id
    const projRes = await getProject(currentProjectId.value)
    if (projRes.success && projRes.data.graph_id) {
      const gRes = await getGraphData(projRes.data.graph_id)
      if (gRes.success) {
        graphData.value = gRes.data
        const nodeCount = gRes.data.node_count || gRes.data.nodes?.length || 0
        const edgeCount = gRes.data.edge_count || gRes.data.edges?.length || 0
        addLog(`Graph data refreshed. Nodes: ${nodeCount}, Edges: ${edgeCount}`)
      }
    }
  } catch (err) {
    console.warn('Graph fetch error:', err)
  }
}

const startPollingTask = (taskId) => {
  pollTaskStatus(taskId)
  pollTimer = setInterval(() => pollTaskStatus(taskId), 2000)
}

const pollTaskStatus = async (taskId) => {
  try {
    const res = await getTaskStatus(taskId)
    if (res.success) {
      const task = res.data
      
      // Log progress message if it changed
      if (task.message && task.message !== buildProgress.value?.message) {
        addLog(task.message)
      }
      
      buildProgress.value = { progress: task.progress || 0, message: task.message }
      
      if (task.status === 'completed') {
        addLog('Graph build task completed.')
        stopPolling()
        stopGraphPolling() // Stop polling, do final load
        currentPhase.value = 2
        
        // Final load
        const projRes = await getProject(currentProjectId.value)
        if (projRes.success && projRes.data.graph_id) {
            projectData.value = projRes.data
            await loadGraph(projRes.data.graph_id)
        }
      } else if (task.status === 'failed') {
        stopPolling()
        error.value = task.error
        addLog(`Graph build task failed: ${task.error}`)
      }
    }
  } catch (e) {
    // Graph build tasks are intentionally ephemeral. A deployment can leave a
    // persisted project pointing to a task that no longer exists in memory.
    // Recover once by explicitly rebuilding instead of polling a permanent 404.
    if (e.response?.status === 404 && !recoveredOrphanedBuild) {
      recoveredOrphanedBuild = true
      stopPolling()
      addLog('The previous graph task was interrupted by a restart. Rebuilding the graph...')
      await startBuildGraph({ force: true })
      return
    }
    console.error(e)
  }
}

const loadGraph = async (graphId) => {
  graphLoading.value = true
  addLog(`Loading full graph data: ${graphId}`)
  try {
    const res = await getGraphData(graphId)
    if (res.success) {
      graphData.value = res.data
      addLog('Graph data loaded successfully.')
    } else {
      addLog(`Failed to load graph data: ${res.error}`)
    }
  } catch (e) {
    addLog(`Exception loading graph: ${e.message}`)
  } finally {
    graphLoading.value = false
  }
}

const refreshGraph = () => {
  if (projectData.value?.graph_id) {
    addLog('Manual graph refresh triggered.')
    loadGraph(projectData.value.graph_id)
  }
}

// US-040 — Step 1.5 « Review & refine entities » before agent setup.
const goToReviewEntities = () => {
  if (!currentProjectId.value || currentProjectId.value === 'new') return
  addLog('Opening entity review (Step 1.5)...')
  router.push({
    name: 'ReviewEntities',
    params: { projectId: currentProjectId.value }
  })
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const stopGraphPolling = () => {
  if (graphPollTimer) {
    clearInterval(graphPollTimer)
    graphPollTimer = null
    addLog('Graph polling stopped.')
  }
}

watchEffect(() => {
  const step = currentStep.value
  const status = statusClass.value
  const dot = status === 'processing' ? '\uD83D\uDFE0' : status === 'error' ? '\uD83D\uDD34' : status === 'completed' ? '\uD83D\uDFE2' : ''
  document.title = dot ? `${dot} (${step}/4) Bassira` : `(${step}/4) Bassira`
})

onMounted(() => {
  initProject()
  window.addEventListener('resize', onResizeWindow)
})

onUnmounted(() => {
  document.title = 'Bassira'
  stopPolling()
  stopGraphPolling()
  window.removeEventListener('resize', onResizeWindow)
  // Defensive cleanup if user navigates away mid-drag.
  if (isResizing.value) stopResize()
})
</script>

<style scoped>
/* ─────────────────────────────────────────────────────────────
   MainView — Bassira Strategic Console (Tier 2 Analyst)
   Dark shell first. Density of info = signal of pro confidence.
   Tokens : --wi-* (Warm Intelligence) for warmth, --ms-* (legacy) for logic.
   No hex hardcoded — all colors via CSS custom properties.
   ───────────────────────────────────────────────────────────── */

.main-view {
  /* ──────────────────────────────────────────────────────────
     Local DARK SHELL scope — Tier 2 Analyst console.
     This view is DARK MODE FIRST regardless of global theme.
     Tokens redefined locally so cream global theme is unaffected,
     and so we never depend on user toggling [data-theme="dark"].
     All values trace back to the existing palette in design-tokens.css :
       --ms-orange / --ms-mint / --ms-peach / --ms-rose
       --wi-on-primary-container (terracotta — destructive)
       --wi-secondary-container  (mint — confirmatory)
     ────────────────────────────────────────────────────────── */
  --shell-bg:           var(--ms-shell-bg);
  --shell-bg-deep:      var(--ms-shell-bg-deep);
  --shell-bg-elevated:  var(--ms-shell-bg-elevated);
  --shell-bg-panel:     var(--ms-shell-bg-panel);
  --shell-border:       var(--ms-shell-border);
  --shell-border-soft:  var(--ms-shell-border-soft);
  --shell-text:         var(--ms-shell-text);
  --shell-text-muted:   var(--ms-shell-text-muted);
  --shell-text-subtle:  var(--ms-shell-text-subtle);
  --shell-accent:       var(--ms-orange);
  --shell-accent-soft:  var(--ms-orange-soft);
  --shell-success:      var(--wi-secondary-container);
  --shell-warning:      var(--ms-peach);
  --shell-danger:       var(--ms-rose);
  --shell-confirmatory: var(--ms-mint);                /* validate / confirmatory */
  --shell-destructive:  var(--wi-on-primary-container); /* terracotta — never bright red */

  /* Local fallbacks — always resolved here so we don't rely on global dark mode. */
  --ms-shell-bg:           #0f1117;
  --ms-shell-bg-deep:      #0a0c10;
  --ms-shell-bg-elevated:  #1a1d27;
  --ms-shell-bg-panel:     #151720;
  --ms-shell-border:       #2e3248;
  --ms-shell-border-soft:  rgba(46, 50, 72, 0.5);
  --ms-shell-text:         #fff8f6;
  --ms-shell-text-muted:   #9ea3b5;
  --ms-shell-text-subtle:  #6b7094;

  /* Tints derived from semantic colors (kept as scoped tokens
     to avoid inline rgba() in rules — mirrors design-tokens.css). */
  --shell-tint-confirmatory:        rgba(127, 216, 166, 0.10);
  --shell-tint-confirmatory-strong: rgba(127, 216, 166, 0.30);
  --shell-tint-danger:              rgba(244, 132, 122, 0.10);
  --shell-tint-danger-strong:       rgba(244, 132, 122, 0.30);
  --shell-tint-accent-strong:       rgba(255, 133, 81, 0.30);
  --shell-tint-accent-glow:         rgba(255, 133, 81, 0.10);
  --shell-tint-ink-soft:            rgba(255, 255, 255, 0.04);
  --shell-tint-shadow-deep:         rgba(0, 0, 0, 0.35);
  --shell-tint-overlay-bg:          rgba(0, 0, 0, 0.30);

  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--shell-bg);
  color: var(--shell-text);
  overflow: hidden;
  font-family: var(--ms-font-body);
}

/* ───── Header — dense console bar ───── */
.app-header {
  height: 56px;
  border-bottom: 1px solid var(--shell-border);
  background: var(--shell-bg);
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 24px;
  padding: 0 24px;
  position: relative;
  z-index: 50;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
  justify-content: flex-end;
  min-width: 0;
}

.header-divider {
  width: 1px;
  height: 24px;
  background: var(--shell-border);
  flex-shrink: 0;
}

/* Brand */
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 0;
  background: transparent;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
  transition: background 150ms var(--ms-ease);
  color: var(--shell-text);
}
.brand:hover { background: var(--shell-accent-soft); }
.brand:focus-visible { outline: 2px solid var(--shell-accent); outline-offset: 2px; }

.brand-mark {
  font-size: 18px;
  color: var(--shell-accent);
  line-height: 1;
}

.brand-name {
  font-family: var(--ms-font-display);
  font-weight: 700;
  font-size: 15px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--shell-text);
}

/* Project context — dense pro info block */
.project-context {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.project-name {
  font-family: var(--ms-font-display);
  font-weight: 600;
  font-size: 14px;
  color: var(--shell-text);
  letter-spacing: -0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 280px;
}

.project-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sim-id {
  font-family: var(--ms-font-mono);
  font-size: 10px;
  font-weight: 500;
  color: var(--shell-text-muted);
  letter-spacing: 0.04em;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: var(--ms-font-mono);
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  padding: 2px 7px;
  border-radius: 3px;
  border: 1px solid transparent;
  background: var(--shell-tint-ink-soft);
  color: var(--shell-text-muted);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--shell-text-subtle);
  flex-shrink: 0;
}

.status-pill.processing {
  color: var(--shell-accent);
  border-color: var(--shell-accent-soft);
  background: var(--shell-accent-soft);
}
.status-pill.processing .status-dot {
  background: var(--shell-accent);
  animation: shell-pulse 1.4s infinite;
}
.status-pill.completed {
  color: var(--shell-confirmatory);
  border-color: var(--shell-tint-confirmatory-strong);
  background: var(--shell-tint-confirmatory);
}
.status-pill.completed .status-dot { background: var(--shell-confirmatory); }
.status-pill.idle .status-dot { background: var(--shell-warning); }
.status-pill.error {
  color: var(--shell-danger);
  border-color: var(--shell-tint-danger-strong);
  background: var(--shell-tint-danger);
}
.status-pill.error .status-dot { background: var(--shell-danger); }

@keyframes shell-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ───── View Switcher — icon + label tabs (Stitch style) ───── */
.view-switcher {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px;
  background: var(--shell-tint-overlay-bg);
  border: 1px solid var(--shell-border);
  border-radius: 8px;
}

.switch-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 14px;
  border: 1px solid transparent;
  border-radius: 5px;
  background: transparent;
  color: var(--shell-text-muted);
  font-family: var(--ms-font-mono);
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: color 150ms var(--ms-ease),
              background 150ms var(--ms-ease),
              border-color 150ms var(--ms-ease),
              box-shadow 150ms var(--ms-ease);
}

.switch-btn:hover {
  color: var(--shell-text);
  background: var(--shell-bg-elevated);
}

.switch-btn.active {
  color: var(--shell-accent);
  background: var(--shell-bg-elevated);
  border-color: var(--shell-tint-accent-strong);
  box-shadow: 0 0 12px var(--shell-tint-accent-glow);
}

.switch-btn:focus-visible {
  outline: 2px solid var(--shell-accent);
  outline-offset: 1px;
}

.switch-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}
.switch-icon :deep(svg) { width: 100%; height: 100%; }

.switch-label { white-space: nowrap; }

/* ───── Workflow step indicator ───── */
.workflow-step {
  display: flex;
  flex-direction: column;
  gap: 1px;
  text-align: end;
  min-width: 0;
}

.step-num {
  font-family: var(--ms-font-mono);
  font-size: 10px;
  font-weight: 600;
  color: var(--shell-text-muted);
  letter-spacing: 0.05em;
}

.step-name {
  font-family: var(--ms-font-display);
  font-size: 13px;
  font-weight: 500;
  color: var(--shell-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

/* ───── Keyboard shortcut hint (JetBrains Mono muted cream) ───── */
.kbd-hint {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--shell-text-muted);
  opacity: 0.7;
}

.kbd {
  font-family: var(--ms-font-mono);
  font-size: 10px;
  font-weight: 500;
  padding: 2px 6px;
  background: var(--shell-border);
  color: var(--shell-text);
  border-radius: 3px;
  letter-spacing: 0.02em;
}

.kbd-label {
  font-family: var(--ms-font-mono);
  font-size: 10px;
  letter-spacing: 0.05em;
}

/* ───── Content area + resizable panels ───── */
.content-area {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
  background: var(--shell-bg-deep);
}

.panel-wrapper {
  height: 100%;
  overflow: hidden;
  transition: width 0.4s cubic-bezier(0.25, 0.8, 0.25, 1),
              opacity 0.3s ease,
              transform 0.3s ease;
  will-change: width, opacity, transform;
  position: relative;
}

.panel-wrapper.left {
  background: var(--shell-bg-deep);
  border-inline-end: 1px solid var(--shell-border);
}

.panel-wrapper.right {
  background: var(--shell-bg);
  position: relative;
  z-index: 2;
  box-shadow: -4px 0 24px var(--shell-tint-shadow-deep);
}

/* Disable transition while user is dragging — feels instant */
.content-area:has(.resize-divider:active) .panel-wrapper {
  transition: none;
}

/* ───── Resize divider ───── */
.resize-divider {
  width: 5px;
  flex-shrink: 0;
  cursor: col-resize;
  background: var(--shell-border);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 150ms var(--ms-ease);
}

.resize-divider:hover,
.resize-divider:focus-visible {
  background: var(--shell-accent);
  outline: none;
}

.resize-grip {
  width: 1px;
  height: 32px;
  background: var(--shell-text-subtle);
  border-radius: 1px;
  position: relative;
}

.resize-grip::before,
.resize-grip::after {
  content: '';
  position: absolute;
  width: 1px;
  height: 32px;
  background: var(--shell-text-subtle);
  top: 0;
}
.resize-grip::before { left: -3px; }
.resize-grip::after { left: 3px; }

.resize-divider:hover .resize-grip,
.resize-divider:hover .resize-grip::before,
.resize-divider:hover .resize-grip::after {
  background: var(--shell-text);
}

/* ─── US-040 — Step 1.5 review banner (dark shell adapted) ─── */
.review-entities-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  background: var(--shell-accent-soft);
  border-bottom: 1px solid var(--shell-tint-accent-strong);
  color: var(--shell-text);
  flex-wrap: wrap;
}

.reb-text {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.reb-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--shell-accent);
  color: var(--ms-text-on-color);
  font-family: var(--ms-font-mono);
  font-weight: 700;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 999px;
  flex-shrink: 0;
}

.reb-body {
  flex: 1;
  min-width: 0;
}

.reb-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--shell-text);
}

.reb-desc {
  font-size: 12px;
  color: var(--shell-text);
  opacity: 0.85;
}

.reb-actions {
  display: flex;
  flex-shrink: 0;
}

/* ───── Responsive collapse ─────
   Tablet (<1080px) : split mode stacks panels vertically.
   Mobile (<720px)  : view switcher becomes condensed tabs (hide Split mode);
                       only one panel visible at a time. */

@media (max-width: 1079px) {
  .app-header {
    grid-template-columns: minmax(0, auto) 1fr minmax(0, auto);
    gap: 12px;
    padding: 0 16px;
  }
  .project-name { max-width: 180px; }
  .step-name { display: none; }
  .kbd-hint { display: none; }

  /* Stack panels in split mode on tablet */
  .content-area[data-mode="split"] {
    flex-direction: column;
  }
  .content-area[data-mode="split"] .panel-wrapper {
    width: 100% !important;
    height: 50% !important;
  }
  .content-area[data-mode="split"] .panel-wrapper.left {
    border-inline-end: none;
    border-bottom: 1px solid var(--shell-border);
  }
  .content-area[data-mode="split"] .panel-wrapper.right {
    box-shadow: 0 -4px 24px var(--shell-tint-shadow-deep);
  }
}

@media (max-width: 719px) {
  .app-header {
    height: auto;
    min-height: 56px;
    padding: 8px 12px;
    gap: 8px;
  }
  .brand-name { display: none; }
  .header-divider { display: none; }
  .project-name { max-width: 140px; font-size: 13px; }
  .sim-id { font-size: 9px; }

  .switch-btn {
    padding: 6px 9px;
  }
  .switch-label { display: none; }

  .workflow-step { display: none; }

  /* Mobile : panels are single-view tabs (controlled by viewMode) */
  .content-area .panel-wrapper {
    width: 100% !important;
    height: 100% !important;
    border-inline-end: none !important;
    box-shadow: none !important;
  }
}

/* High-contrast / forced-colors guard rails */
@media (prefers-contrast: more) {
  .switch-btn.active { border-width: 2px; }
  .status-pill { border-width: 2px; }
}
</style>
